import asyncio
import re
from urllib.parse import urljoin, urlparse
from playwright.async_api import async_playwright

# 🌍 PREFIXOS PERMITIDOS E ORDEM DE PRIORIDADE NO RELATÓRIO
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
    """
    Extrai o número de telefone de forma precisa e limpa sem concatenar strings 
    que causam duplicidade de dígitos no final.
    """
    # 1. Procura no texto visível primeiro
    num_texto = re.findall(r'\+\d{10,15}', texto)
    for num in num_texto:
        if any(num.startswith(p) for p in PREFIXOS_ACEITOS):
            return num

    # 2. Procura no href se o texto não tiver o '+'
    num_href = re.findall(r'\+\d{10,15}', href)
    for num in num_href:
        if any(num.startswith(p) for p in PREFIXOS_ACEITOS):
            return num

    # 3. Procura sequências de dígitos no texto e no href separadamente
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
    """Emula um navegador real com suporte adequado a SPAs (React/Vue/Nuxt)."""
    context = await browser.new_context(
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        viewport={"width": 1280, "height": 800},
        locale="pt-BR",
        timezone_id="America/Sao_Paulo"
    )
    # Cancela apenas mídias pesadas para não interromper a renderização do JS
    await context.route("**/*.{png,jpg,jpeg,gif,webp,svg,mp4,mp3}", lambda route: route.abort())
    return context

async def processar_fonte(fonte, browser, semaphore):
    """Extrai números de várias fontes garantindo links diretos e caixas válidas."""
    async with semaphore:
        context = await configurar_contexto_anti_cloudflare(browser)
        page = await context.new_page()
        numeros_encontrados = []
        
        try:
            await page.goto(fonte["url"], timeout=30000, wait_until="domcontentloaded")
            await page.wait_for_timeout(2000)
            
            # Rolagem para carregar conteúdos dinâmicos
            await page.evaluate("window.scrollBy(0, 1000)")
            await page.wait_for_timeout(1000)
            
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
        except Exception as e:
            print(f"  ├─ ⚠️ {fonte['nome']}: Timeout ou bloqueio ({type(e).__name__})")
        finally:
            await context.close()
            
        print(f"  ├─ {fonte['nome']}: {len(numeros_encontrados)} número(s) com caixa individual localizados")
        return numeros_encontrados

async def extrair_dados_caixa_sms(page):
    """Lê todas as mensagens da caixa e verifica se o carregamento foi bem sucedido."""
    try:
        await page.wait_for_timeout(2500)
        await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        await page.wait_for_timeout(1000)
        
        resultado = await page.evaluate('''() => {
            const seletores = [
                'table', '.messages', '.sms-list', '.messages-list', 
                '.list-group', 'article', 'main', '.number-messages', 
                '.chat-box', '.sms-card', '.table-responsive', 'tbody', '.msg-item'
            ];
            let acumulado = '';
            let contadorMensagens = 0;

            for (const sel of seletores) {
                const elems = document.querySelectorAll(sel);
                elems.forEach(el => {
                    const txt = el.innerText || el.textContent || '';
                    if (txt.length > 10) {
                        acumulado += ' ' + txt;
                        contadorMensagens++;
                    }
                });
            }

            if (!acumulado || acumulado.trim().length < 30) {
                acumulado = document.body.innerText || '';
            }

            return {
                texto: acumulado,
                tamanho: acumulado.length
            };
        }''')
        
        texto_lc = resultado['texto'].lower()
        
        # Garante que a caixa foi lida com sucesso (evita falsos positivos por falha de renderização)
        sucesso_leitura = resultado['tamanho'] > 60
        
        termos_antigos = [
            'year ago', 'years ago', 'month ago', 'months ago',
            'ano atrás', 'anos atrás', 'mês atrás', 'meses atrás',
            'há 1 ano', 'há 2 anos', 'há 3 anos', 'há 1 mês', 'há 2 meses',
            '2021', '2022', '2023', '2024', '2025'
        ]
        eh_antigo = any(termo in texto_lc for termo in termos_antigos)
        
        return texto_lc, sucesso_leitura, eh_antigo
    except Exception:
        return "", False, True

async def analisar_historico_youtube(item, browser, semaphore):
    """Analisa rigorosamente se o número possui QUALQUER registro de uso para YouTube/Google."""
    async with semaphore:
        context = await configurar_contexto_anti_cloudflare(browser)
        page = await context.new_page()
        item['fossil'] = False
        item['usos_youtube'] = 0
        item['leitura_ok'] = False
        
        try:
            await page.goto(item['link'], timeout=25000, wait_until="domcontentloaded")
            conteudo_caixa, sucesso_leitura, eh_antigo = await extrair_dados_caixa_sms(page)
            
            item['fossil'] = eh_antigo
            item['leitura_ok'] = sucesso_leitura
            
            if not sucesso_leitura:
                # SE NÃO CONSEGUIU LER A CAIXA DE SMS, DESCARTE INCONDICIONALMENTE!
                item['usos_youtube'] = 999 
            else:
                # Procura qualquer código, palavra-chave ou menção ao Google/YouTube
                padroes = [
                    r'\bg-\d{5,6}\b',
                    r'youtube',
                    r'google',
                    r'gmail',
                    r'yt\b'
                ]
                
                total_usos = 0
                for padrao in padroes:
                    matches = re.findall(padrao, conteudo_caixa, flags=re.IGNORECASE)
                    total_usos += len(matches)
                
                item['usos_youtube'] = total_usos
        except Exception:
            item['usos_youtube'] = 999
            item['fossil'] = True
            item['leitura_ok'] = False
        finally:
            await context.close()
        return item

async def analisar_historico_google_conta(item, browser, semaphore):
    """Analisa se o número foi utilizado para verificação de Conta Google / Gmail."""
    async with semaphore:
        context = await configurar_contexto_anti_cloudflare(browser)
        page = await context.new_page()
        item['fossil'] = False
        item['usos_google_conta'] = 0
        item['leitura_ok'] = False
        
        try:
            await page.goto(item['link'], timeout=25000, wait_until="domcontentloaded")
            conteudo_caixa, sucesso_leitura, eh_antigo = await extrair_dados_caixa_sms(page)
            
            item['fossil'] = eh_antigo
            item['leitura_ok'] = sucesso_leitura
            
            if not sucesso_leitura:
                item['usos_google_conta'] = 999
            else:
                padroes = [
                    r'\bg-\d{5,6}\b',
                    r'google',
                    r'gmail',
                    r'g-account'
                ]
                
                total_usos = 0
                for padrao in padroes:
                    matches = re.findall(padrao, conteudo_caixa, flags=re.IGNORECASE)
                    total_usos += len(matches)
                
                item['usos_google_conta'] = total_usos
        except Exception:
            item['usos_google_conta'] = 999
            item['fossil'] = True
            item['leitura_ok'] = False
        finally:
            await context.close()
        return item

def ordenar_por_prioridade(lista, chave_usos):
    """Prioriza Finlândia (+358), EUA (+1) e Portugal (+351) no topo do relatório."""
    def peso(item):
        num = item['numero']
        prio = 99
        for idx, prefixo in enumerate(PREFIXOS_PRIORITARIOS):
            if num.startswith(prefixo):
                prio = idx
                break
        return (prio, item.get(chave_usos, 0))

    return sorted(lista, key=peso)

def exibir_relatorio(aprovados_yt, aprovados_google, total_coletados):
    print("\n" + "="*70)
    print("🚀 RELATÓRIO FINAL: NÚMEROS APROVADOS (100% RECENTES & VIRGENS)")
    print("="*70)

    # REQUISITO RÍGIDO: Leitura da caixa confirmada, 0 usos e NÃO ser antigo/fóssil
    yt_filtrados = [
        i for i in aprovados_yt 
        if i.get('usos_youtube', 999) == 0 
        and i.get('leitura_ok', False) 
        and not i.get('fossil', False)
    ]
    yt_ordenados = ordenar_por_prioridade(yt_filtrados, 'usos_youtube')
    
    print("\n🔴 [GRUPO 1: VERIFICAÇÃO DE CANAL YOUTUBE]")
    if yt_ordenados:
        for i, item in enumerate(yt_ordenados, 1):
            print(f"{i}. 📱 {item['numero']} 🟢 [100% VIRGEM - 0 USOS DETETADOS]")
            print(f"   🌐 Fonte: {item['fonte']}")
            print(f"   🔗 Link Direto: {item['link']}")
            print("-" * 70)
    else:
        print("   ❌ TODOS OS NÚMEROS ENCONTRADOS JÁ FORAM USADOS OU NÃO PUDERAM TER A CAIXA VALIDADA.")

    google_filtrados = [
        i for i in aprovados_google 
        if i.get('usos_google_conta', 999) == 0 
        and i.get('leitura_ok', False) 
        and not i.get('fossil', False)
    ]
    google_ordenados = ordenar_por_prioridade(google_filtrados, 'usos_google_conta')
    
    print("\n🔵 [GRUPO 2: CRIAÇÃO DE CONTA GOOGLE / GMAIL]")
    if google_ordenados:
        for i, item in enumerate(google_ordenados, 1):
            print(f"{i}. 📱 {item['numero']} 🟢 [100% VIRGEM - 0 USOS DETETADOS]")
            print(f"   🌐 Fonte: {item['fonte']}")
            print(f"   🔗 Link Direto: {item['link']}")
            print("-" * 70)
    else:
        print("   ❌ TODOS OS NÚMEROS ENCONTRADOS JÁ FORAM USADOS OU NÃO PUDERAM TER A CAIXA VALIDADA.")

    print(f"\n📊 Estatísticas da Varredura:")
    print(f"   • Total de candidatos localizados: {total_coletados}")
    print(f"   • Aprovados para YouTube: {len(yt_ordenados)}")
    print(f"   • Aprovados para Google/Gmail: {len(google_ordenados)}")

async def main():
    print("\n⚡ [BOT SMS VERIFICATION v16 - PRECISÃO MÁXIMA] Iniciando varredura profunda...")
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        
        semaphore_coleta = asyncio.Semaphore(5)
        semaphore_analise = asyncio.Semaphore(6)
        
        print("\n🌐 Fase 1: Extraindo números e validando links diretos de caixas...")
        tasks_fontes = [processar_fonte(f, browser, semaphore_coleta) for f in FONTES_SMS]
        resultados = await asyncio.gather(*tasks_fontes)
        
        todos_candidatos = []
        for lista in resultados:
            for item in lista:
                if not any(c['numero'] == item['numero'] for c in todos_candidatos):
                    todos_candidatos.append(item)
                    
        total_coletados = len(todos_candidatos)
        print(f"\n🔍 Fase 2: {total_coletados} candidatos com link direto localizados. Analisando caixas de mensagens...")
        
        if todos_candidatos:
            tasks_yt = [analisar_historico_youtube(dict(c), browser, semaphore_analise) for c in todos_candidatos]
            tasks_google = [analisar_historico_google_conta(dict(c), browser, semaphore_analise) for c in todos_candidatos]
            
            res_yt, res_google = await asyncio.gather(
                asyncio.gather(*tasks_yt),
                asyncio.gather(*tasks_google)
            )
            
            exibir_relatorio(res_yt, res_google, total_coletados)
        else:
            exibir_relatorio([], [], 0)
            
        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
