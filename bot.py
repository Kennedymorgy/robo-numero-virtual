import asyncio
import re
from urllib.parse import urljoin
from playwright.async_api import async_playwright

# 🌍 PREFIXOS PERMITIDOS E ORDEM DE PRIORIDADE
PREFIXOS_PRIORITARIOS = ('+358', '+1', '+351')
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
        digitos_encontrados = re.findall(r'\b\d{10,15}\b', alvo)
        for dig in digitos_encontrados:
            texto_lc = alvo.lower()
            if any(k in texto_lc for k in ['finland', 'finlandia']):
                cand = '+358' + dig if not dig.startswith('358') else '+' + dig
            elif any(k in texto_lc for k in ['usa', 'united-states', 'us', 'america', 'estados-unidos']):
                cand = '+1' + dig if not dig.startswith('1') else '+' + dig
            elif any(k in texto_lc for k in ['portugal', 'pt']):
                cand = '+351' + dig if not dig.startswith('351') else '+' + dig
            elif any(k in texto_lc for k in ['uk', 'united-kingdom', 'gb', 'england']):
                cand = '+44' + dig if not dig.startswith('44') else '+' + dig
            elif any(k in texto_lc for k in ['france', 'francia', 'fr']):
                cand = '+33' + dig if not dig.startswith('33') else '+' + dig
            elif any(k in texto_lc for k in ['netherlands', 'holland', 'holanda', 'nl']):
                cand = '+31' + dig if not dig.startswith('31') else '+' + dig
            elif any(k in texto_lc for k in ['germany', 'alemanha', 'de']):
                cand = '+49' + dig if not dig.startswith('49') else '+' + dig
            else:
                cand = '+' + dig

            if cand.startswith('+41'):
                continue
            if any(cand.startswith(p) for p in PREFIXOS_ACEITOS) and 11 <= len(cand) <= 16:
                return cand

    return None

async def configurar_contexto_anti_cloudflare(browser):
    context = await browser.new_context(
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
        viewport={"width": 1366, "height": 768},
        locale="en-US",
        extra_http_headers={
            "Accept-Language": "en-US,en;q=0.9,pt-BR;q=0.8",
            "Sec-Ch-Ua": '"Google Chrome";v="123", "Not:A-Brand";v="8", "Chromium";v="123"',
            "Sec-Ch-Ua-Mobile": "?0",
            "Sec-Ch-Ua-Platform": '"Windows"',
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "none",
            "Sec-Fetch-User": "?1",
            "Upgrade-Insecure-Requests": "1"
        }
    )
    # Bloqueia recursos desnecessários para aumentar a velocidade e economizar banda
    await context.route("**/*.{png,jpg,jpeg,gif,webp,svg,mp4,mp3,woff,woff2,ttf,otf,css}", lambda route: route.abort())
    return context

async def processar_fonte(fonte, browser, semaphore):
    async with semaphore:
        context = await configurar_contexto_anti_cloudflare(browser)
        page = await context.new_page()
        numeros_encontrados = []
        
        try:
            await page.goto(fonte["url"], timeout=35000, wait_until="domcontentloaded")
            await page.wait_for_timeout(2000)
            await page.evaluate("window.scrollBy(0, 1000)")
            
            elementos_dom = await page.evaluate('''() => {
                const seletores = 'a, .number-card, .card, tr, .col-md-4, .col-sm-6, .col-12, .free-number-card, [class*="number"]';
                const itens = [];
                document.querySelectorAll(seletores).forEach(el => {
                    const a = el.tagName === 'A' ? el : el.querySelector('a');
                    const href = a ? (a.getAttribute('href') || '') : '';
                    const text = el.innerText || el.textContent || '';
                    if (text && text.length < 300) {
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
                        
                    if not any(n['numero'] == num_valido for n in numeros_encontrados):
                        numeros_encontrados.append({
                            'numero': num_valido, 
                            'link': link_direto, 
                            'fonte': fonte['nome']
                        })
        except Exception:
            print(f"  ├─ ⚠️ {fonte['nome']}: Timeout ou bloqueio de conexão")
        finally:
            await context.close()
            
        print(f"  ├─ {fonte['nome']}: {len(numeros_encontrados)} número(s) localizados")
        return numeros_encontrados

async def analisar_caixa_sms_completa(item, browser, semaphore):
    """
    Analisa a caixa de SMS verificando requisições do Google/YouTube,
    densidade de uso recente e padrões de data.
    """
    async with semaphore:
        context = await configurar_contexto_anti_cloudflare(browser)
        page = await context.new_page()
        
        item['fossil'] = False
        item['usos_youtube'] = 0
        item['usos_google'] = 0
        item['leitura_ok'] = False
        item['sem_atividade'] = False
        item['alta_rotatividade'] = False
        
        try:
            await page.goto(item['link'], timeout=25000, wait_until="domcontentloaded")
            await page.wait_for_timeout(2000)
            
            resultado = await page.evaluate('''() => {
                const seletores = [
                    'table', '.messages', '.sms-list', '.messages-list', 
                    '.list-group', 'article', 'main', '.number-messages', 
                    '.chat-box', '.sms-card', '.table-responsive', 'tbody', '.msg-item'
                ];
                let acumulado = '';
                let linhas = document.querySelectorAll('tr, .sms-card, .msg-item, .list-group-item');
                let totalMsgs = linhas.length;

                for (const sel of seletores) {
                    const elems = document.querySelectorAll(sel);
                    elems.forEach(el => {
                        acumulado += ' ' + (el.innerText || el.textContent || '');
                    });
                }

                if (!acumulado || acumulado.trim().length < 30) {
                    acumulado = document.body.innerText || '';
                }

                return {
                    texto: acumulado,
                    tamanho: acumulado.length,
                    totalMsgs: totalMsgs
                };
            }''')
            
            conteudo_lc = resultado['texto'].lower()
            sucesso_leitura = resultado['tamanho'] > 60
            item['leitura_ok'] = sucesso_leitura
            
            # Se a caixa tiver pouquíssimas mensagens, pode indicar que acabou de ser limpa
            if resultado['totalMsgs'] < 3 and resultado['tamanho'] < 250:
                item['sem_atividade'] = True

            # Se houver muitas mensagens recebidas juntas, é um número público muito concorrido
            if resultado['totalMsgs'] > 40:
                item['alta_rotatividade'] = True

            # Padrões de datas antigas que indicam inatividade
            termos_antigos = [
                'year ago', 'years ago', 'month ago', 'months ago',
                'ano atrás', 'anos atrás', 'mês atrás', 'meses atrás',
                'há 1 ano', 'há 2 anos', 'há 1 mês'
            ]
            item['fossil'] = any(termo in conteudo_lc for termo in termos_antigos)
            
            if sucesso_leitura:
                # Busca abrangente por códigos do Google/YouTube
                padroes_yt = [
                    r'\bg-\d{5,6}\b', r'youtube', r'yt code', r'código do youtube', 
                    r'verificação do youtube', r'yt-verification'
                ]
                padroes_google = [
                    r'\bg-\d{5,6}\b', r'google', r'gmail', r'g-account', 
                    r'verificação google', r'google verification', r'código de verificação google',
                    r'confirm\s*\d{5,6}'
                ]
                
                item['usos_youtube'] = sum(len(re.findall(p, conteudo_lc, re.IGNORECASE)) for p in padroes_yt)
                item['usos_google'] = sum(len(re.findall(p, conteudo_lc, re.IGNORECASE)) for p in padroes_google)
            else:
                item['usos_youtube'] = 999
                item['usos_google'] = 999

        except Exception:
            item['usos_youtube'] = 999
            item['usos_google'] = 999
            item['fossil'] = True
            item['leitura_ok'] = False
        finally:
            await context.close()
            
        return item

def ordenar_por_prioridade(lista):
    def peso(item):
        num = item['numero']
        prio = 99
        for idx, prefixo in enumerate(PREFIXOS_PRIORITARIOS):
            if num.startswith(prefixo):
                prio = idx
                break
        return (prio, item.get('usos_youtube', 0) + item.get('usos_google', 0))

    return sorted(lista, key=peso)

def exibir_relatorio(analisados, total_coletados):
    print("\n" + "="*70)
    print("🚀 RELATÓRIO FINAL: NÚMEROS APROVADOS (FILTRAGEM DE PRECISÃO)")
    print("="*70)

    # Filtra números que estão ativos, recentes e com boa densidade
    validos = [
        i for i in analisados 
        if i.get('leitura_ok', False) 
        and not i.get('fossil', False)
        and not i.get('sem_atividade', False)
        and not i.get('alta_rotatividade', False)
    ]
    
    yt_aprovados = [i for i in validos if i.get('usos_youtube', 999) == 0]
    google_aprovados = [i for i in validos if i.get('usos_google', 999) == 0]

    yt_ordenados = ordenar_por_prioridade(yt_aprovados)
    google_ordenados = ordenar_por_prioridade(google_aprovados)
    
    print("\n🔴 [GRUPO 1: VERIFICAÇÃO DE CANAL YOUTUBE]")
    if yt_ordenados:
        for i, item in enumerate(yt_ordenados, 1):
            print(f"{i}. 📱 {item['numero']} 🟢 [BAIXA CONCORRÊNCIA - 0 REGISTROS YT]")
            print(f"   🌐 Fonte: {item['fonte']}")
            print(f"   🔗 Link Direto: {item['link']}")
            print("-" * 70)
    else:
        print("   ❌ Nenhum número seguro para YouTube nesta varredura.")

    print("\n🔵 [GRUPO 2: CRIAÇÃO DE CONTA GOOGLE / GMAIL]")
    if google_ordenados:
        for i, item in enumerate(google_ordenados, 1):
            print(f"{i}. 📱 {item['numero']} 🟢 [BAIXA CONCORRÊNCIA - 0 REGISTROS GOOGLE]")
            print(f"   🌐 Fonte: {item['fonte']}")
            print(f"   🔗 Link Direto: {item['link']}")
            print("-" * 70)
    else:
        print("   ❌ Nenhum número seguro para Google Conta nesta varredura.")

    print(f"\n📊 Estatísticas da Varredura:")
    print(f"   • Total de candidatos extraídos: {total_coletados}")
    print(f"   • Validados & Recentes (Ativos): {len(validos)}")
    print(f"   • Aprovados YouTube: {len(yt_ordenados)}")
    print(f"   • Aprovados Google/Gmail: {len(google_ordenados)}")

async def main():
    print("\n⚡ [BOT SMS VERIFICATION v18 - ROBUST FILTER] Iniciando...")
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        
        semaphore_coleta = asyncio.Semaphore(5)
        semaphore_analise = asyncio.Semaphore(6)
        
        print("\n🌐 Fase 1: Coletando links diretos de números...")
        tasks_fontes = [processar_fonte(f, browser, semaphore_coleta) for f in FONTES_SMS]
        resultados = await asyncio.gather(*tasks_fontes)
        
        todos_candidatos = []
        for lista in resultados:
            for item in lista:
                if not any(c['numero'] == item['numero'] for c in todos_candidatos):
                    todos_candidatos.append(item)
                    
        total_coletados = len(todos_candidatos)
        print(f"\n🔍 Fase 2: {total_coletados} números únicos localizados. Analisando caixas de entrada...")
        
        if todos_candidatos:
            tasks_analise = [analisar_caixa_sms_completa(c, browser, semaphore_analise) for c in todos_candidatos]
            analisados = await asyncio.gather(*tasks_analise)
            exibir_relatorio(analisados, total_coletados)
        else:
            exibir_relatorio([], 0)
            
        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
