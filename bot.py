import asyncio
import re
from urllib.parse import urljoin
from playwright.async_api import async_playwright

PREFIXOS_PRIORITARIOS = ('+358', '+351', '+1')
PREFIXOS_ACEITOS = ('+1', '+351', '+358', '+44', '+33', '+31', '+49')

FONTES_SMS = [
    {"nome": "Quackr PT P1", "url": "https://quackr.io/pt/temporary-numbers", "tipo": "quackr"},
    {"nome": "Quackr Global", "url": "https://quackr.io/temporary-numbers", "tipo": "quackr"},
    {"nome": "SMS-Man Gratis PT", "url": "https://sms-man.com/pt/free-numbers", "tipo": "smsman"},
    {"nome": "SMS-Man Gratis EN", "url": "https://sms-man.com/free-numbers", "tipo": "smsman"},
    {"nome": "Receive-SMSS", "url": "https://receive-smss.com/", "tipo": "padrao"},
    {"nome": "SMSToMe", "url": "https://smstome.com/country/usa", "tipo": "padrao"},
    {"nome": "AnonymSMS", "url": "https://anonymsms.com/", "tipo": "padrao"},
    {"nome": "TempSMSS", "url": "https://tempsmss.com/", "tipo": "padrao"},
    {"nome": "SMS24", "url": "https://sms24.me/en/countries/us", "tipo": "padrao"},
    {"nome": "OnlineSMS", "url": "https://online-sms.org/", "tipo": "padrao"},
    {"nome": "Receive-SMS.cc", "url": "https://receive-sms.cc/", "tipo": "padrao"},
    {"nome": "SMS-Online.co", "url": "https://sms-online.co/", "tipo": "padrao"}
]

def extrair_numero_inteligente(texto, href=""):
    num_texto = re.findall(r'\+\d{10,15}', texto)
    for num in num_texto:
        if any(num.startswith(p) for p in PREFIXOS_ACEITOS):
            return num

    num_href = re.findall(r'\+\d{10,15}', href)
    for num in num_href:
        if any(num.startswith(p) for p in PREFIXOS_ACEITOS):
            return num

    for alvo in [texto, href]:
        digitos = re.findall(r'\b\d{10,15}\b', alvo)
        for dig in digitos:
            texto_lc = alvo.lower()
            if any(k in texto_lc for k in ['finland', 'finlandia']):
                cand = '+358' + dig if not dig.startswith('358') else '+' + dig
            elif any(k in texto_lc for k in ['usa', 'us', 'america']):
                cand = '+1' + dig if not dig.startswith('1') else '+' + dig
            elif any(k in texto_lc for k in ['portugal', 'pt']):
                cand = '+351' + dig if not dig.startswith('351') else '+' + dig
            else:
                cand = '+' + dig

            if any(cand.startswith(p) for p in PREFIXOS_ACEITOS) and 11 <= len(cand) <= 16:
                return cand
    return None

def analisar_recencia_texto(texto):
    """
    Avalia se o card do número possui indicação de recência no site (ex: 'added 10 mins ago').
    Retorna True se for um número novo ou recém-adicionado.
    """
    texto_lc = texto.lower()
    
    # Termos de alta prioridade (Número muito recente)
    padroes_novos = [
        r'just now', r'agora', r'min ago', r'mins ago', r'minutos', 
        r'new', r'novo', r'1h ago', r'2h ago', r'recent'
    ]
    
    # Termos de número antigo (Descartar)
    padroes_antigos = [
        r'days ago', r'dias atrás', r'week ago', r'weeks ago', 
        r'month ago', r'months ago', r'year ago', r'anos'
    ]

    if any(re.search(p, texto_lc) for p in padroes_antigos):
        return False, "Antigo (Dias/Meses online)"

    if any(re.search(p, texto_lc) for p in padroes_novos):
        return True, "Recém-adicionado (Poucas horas ou minutos)"

    return True, "Sem indicador explícito de tempo"

async def configurar_contexto(browser):
    context = await browser.new_context(
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
        viewport={"width": 1280, "height": 800},
        locale="pt-BR"
    )
    await context.route("**/*.{png,jpg,jpeg,gif,webp,svg,mp4,mp3,woff,woff2,ttf,otf,css}", lambda route: route.abort())
    return context

async def processar_fonte(fonte, browser, semaphore):
    async with semaphore:
        context = await configurar_contexto(browser)
        page = await context.new_page()
        numeros_encontrados = []
        
        try:
            await page.goto(fonte["url"], timeout=30000, wait_until="domcontentloaded")
            await page.wait_for_timeout(1500)
            
            elementos_dom = await page.evaluate('''() => {
                const seletores = 'a, .number-card, .card, tr, .col-md-4, .col-sm-6, .col-12, .free-number-card, [class*="number"]';
                const itens = [];
                document.querySelectorAll(seletores).forEach(el => {
                    const a = el.tagName === 'A' ? el : el.querySelector('a');
                    const href = a ? (a.getAttribute('href') || '') : '';
                    const text = el.innerText || el.textContent || '';
                    if (text && text.length < 350) {
                        itens.push({ href: href.trim(), text: text.trim() });
                    }
                });
                return itens;
            }''')
            
            base_url_limpa = fonte["url"].rstrip('/')
            
            for item in elementos_dom:
                href = item['href']
                text = item['text']
                num_valido = extrair_numero_inteligente(text, href)
                
                if num_valido and href and href not in ['#', '/', '']:
                    link_direto = urljoin(fonte["url"], href)
                    if link_direto.rstrip('/') == base_url_limpa:
                        continue
                        
                    eh_recente, status_tempo = analisar_recencia_texto(text)
                    
                    if eh_recente and not any(n['numero'] == num_valido for n in numeros_encontrados):
                        numeros_encontrados.append({
                            'numero': num_valido, 
                            'link': link_direto, 
                            'fonte': fonte['nome'],
                            'status_tempo': status_tempo
                        })
        except Exception:
            pass
        finally:
            await context.close()
            
        print(f"  ├─ {fonte['nome']}: {len(numeros_encontrados)} número(s) recentes/válidos")
        return numeros_encontrados

async def analisar_caixa_sms(item, browser, semaphore):
    async with semaphore:
        context = await configurar_contexto(browser)
        page = await context.new_page()
        
        item['fossil'] = False
        item['usos_google'] = 0
        item['leitura_ok'] = False
        
        try:
            await page.goto(item['link'], timeout=25000, wait_until="domcontentloaded")
            await page.wait_for_timeout(1500)
            
            resultado = await page.evaluate('''() => {
                const elems = document.querySelectorAll('table, .messages, .sms-list, .messages-list, .chat-box, body');
                let texto = '';
                elems.forEach(el => texto += ' ' + (el.innerText || ''));
                return { texto: texto, tamanho: texto.length };
            }''')
            
            conteudo_lc = resultado['texto'].lower()
            item['leitura_ok'] = resultado['tamanho'] > 50
            
            # Padrões do Google/Gmail/YouTube
            padroes_google = [
                r'\bg-\d{5,6}\b', r'google', r'gmail', r'youtube', 
                r'g-account', r'código de verificação', r'google verification'
            ]
            
            item['usos_google'] = sum(len(re.findall(p, conteudo_lc, re.IGNORECASE)) for p in padroes_google)
            
            # Checa se há mensagens de meses/anos atrás
            termos_fossil = ['year ago', 'years ago', 'month ago', 'months ago', 'ano atrás', 'meses atrás']
            item['fossil'] = any(t in conteudo_lc for t in termos_fossil)

        except Exception:
            item['usos_google'] = 999
            item['leitura_ok'] = False
        finally:
            await context.close()
            
        return item

def exibir_relatorio(analisados):
    print("\n" + "="*70)
    print("🔥 NÚMEROS RECÉM-POSTADOS E SEM REGISTROS DE GOOGLE/YOUTUBE")
    print("="*70)

    # Filtro rigoroso: Leitura OK, Não-fóssil e ZERO ocorrências do Google
    aprovados = [
        i for i in analisados 
        if i.get('leitura_ok', False) 
        and not i.get('fossil', False)
        and i.get('usos_google', 999) == 0
    ]

    if aprovados:
        for i, item in enumerate(aprovados, 1):
            print(f"{i}. 📱 {item['numero']} 🟢 [FRESH / 0 REGISTROS GOOGLE]")
            print(f"   ⏱️ Status de Entrada: {item['status_tempo']}")
            print(f"   🌐 Fonte: {item['fonte']}")
            print(f"   🔗 Link: {item['link']}")
            print("-" * 70)
    else:
        print("❌ Nenhum número recém-adicionado e 100% limpo no momento.")
        print("💡 Dica: Os sites atualizam números em horários aleatórios. Rode o script novamente em alguns minutos.")

async def main():
    print("\n⚡ [BOT SMS v19 - DETECTAR FRESCURA & HORÁRIO] Iniciando...")
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        semaphore = asyncio.Semaphore(6)
        
        print("\n🌐 Fase 1: Varrendo plataformas buscando números recém-adicionados...")
        tasks = [processar_fonte(f, browser, semaphore) for f in FONTES_SMS]
        resultados = await asyncio.gather(*tasks)
        
        todos = []
        for lista in resultados:
            for item in lista:
                if not any(c['numero'] == item['numero'] for c in todos):
                    todos.append(item)
                    
        print(f"\n🔍 Fase 2: Analisando {len(todos)} números filtrados por recência...")
        
        if todos:
            tasks_analise = [analisar_caixa_sms(c, browser, semaphore) for c in todos]
            analisados = await asyncio.gather(*tasks_analise)
            exibir_relatorio(analisados)
        else:
            exibir_relatorio([])
            
        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
