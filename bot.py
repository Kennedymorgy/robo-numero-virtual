import asyncio
import re
from urllib.parse import urljoin
from playwright.async_api import async_playwright

# 🌍 PREFIXOS PERMITIDOS E ORDEM DE PRIORIDADE NO RELATÓRIO
PREFIXOS_PRIORITARIOS = ('+358', '+1', '+351')  # Finlândia, EUA e Portugal no topo
PREFIXOS_ACEITOS = ('+1', '+351', '+358', '+44', '+33', '+31', '+49')

FONTES_SMS = [
    {"nome": "Quackr PT P1", "url": "https://quackr.io/pt/temporary-numbers", "tipo": "padrao"},
    {"nome": "Quackr PT P2", "url": "https://quackr.io/pt/temporary-numbers?page=2", "tipo": "padrao"},
    {"nome": "SMS-Man Gratis", "url": "https://sms-man.com/pt/free-numbers", "tipo": "padrao"},
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
    """Identifica o número e seu país combinando o texto visível e o link da página."""
    combo = f"{texto} {href}".lower()
    limpo = re.sub(r'[^\d+]', '', combo)
    
    # 1. Busca números que já começam com +
    com_mais = re.findall(r'\+\d{10,15}', limpo)
    for num in com_mais:
        if num.startswith('+41'):
            continue
        if any(num.startswith(p) for p in PREFIXOS_ACEITOS):
            return num

    # 2. Busca sequências numéricas de 10 a 15 dígitos sem +
    digitos_lista = re.findall(r'\b\d{10,15}\b', combo)
    for dig in digitos_lista:
        if any(k in combo for k in ['finland', 'finlandia']):
            cand = '+358' + dig if not dig.startswith('358') else '+' + dig
        elif any(k in combo for k in ['usa', 'united-states', 'us', 'america']):
            cand = '+1' + dig if not dig.startswith('1') else '+' + dig
        elif any(k in combo for k in ['portugal', 'pt']):
            cand = '+351' + dig if not dig.startswith('351') else '+' + dig
        elif any(k in combo for k in ['uk', 'united-kingdom', 'gb', 'england']):
            cand = '+44' + dig if not dig.startswith('44') else '+' + dig
        elif any(k in combo for k in ['france', 'francia', 'fr']):
            cand = '+33' + dig if not dig.startswith('33') else '+' + dig
        elif any(k in combo for k in ['netherlands', 'holland', 'holanda', 'nl']):
            cand = '+31' + dig if not dig.startswith('31') else '+' + dig
        elif any(k in combo for k in ['germany', 'alemanha', 'de']):
            cand = '+49' + dig if not dig.startswith('49') else '+' + dig
        else:
            cand = '+' + dig

        if cand.startswith('+41'):
            continue
        if any(cand.startswith(p) for p in PREFIXOS_ACEITOS) and 11 <= len(cand) <= 16:
            return cand
            
    return None

async def configurar_contexto_anti_cloudflare(browser):
    """Emula dispositivo móvel Android e bloqueia apenas mídia pesada para máxima velocidade."""
    context = await browser.new_context(
        user_agent="Mozilla/5.0 (Linux; Android 13; SM-S918B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Mobile Safari/537.36",
        viewport={"width": 412, "height": 915},
        is_mobile=True,
        has_touch=True,
        locale="pt-BR",
        timezone_id="America/Sao_Paulo"
    )
    await context.route("**/*.{png,jpg,jpeg,gif,webp,svg,mp4,mp3,woff,woff2,ttf,otf}", lambda route: route.abort())
    return context

async def processar_fonte(fonte, browser, semaphore):
    """Varre todos os links e caixas no DOM de todos os sites configurados."""
    async with semaphore:
        context = await configurar_contexto_anti_cloudflare(browser)
        page = await context.new_page()
        numeros_encontrados = []
        
        try:
            await page.goto(fonte["url"], timeout=18000, wait_until="domcontentloaded")
            await page.wait_for_timeout(1000)
            await page.evaluate("window.scrollBy(0, 1000)")
            await page.wait_for_timeout(500)
            
            # Varredura completa de elementos no DOM
            elementos_dom = await page.evaluate('''() => {
                const seletores = 'a, h3, h4, span, div.number-item, div.card, tr';
                return Array.from(document.querySelectorAll(seletores)).map(el => ({
                    href: el.getAttribute('href') || el.querySelector('a')?.getAttribute('href') || '',
                    text: el.innerText || ''
                }));
            }''')
            
            for item in elementos_dom:
                href = item['href']
                text = item['text']
                num_valido = extrair_numero_inteligente(text, href)
                
                if num_valido:
                    link_direto = urljoin(fonte["url"], href) if (href and href != '#') else fonte["url"]
                    if not any(n['numero'] == num_valido for n in numeros_encontrados):
                        numeros_encontrados.append({
                            'numero': num_valido, 
                            'link': link_direto, 
                            'fonte': fonte['nome']
                        })
        except Exception as e:
            print(f"  ├─ ⚠️ {fonte['nome']}: Tempo esgotado ou bloqueio ({type(e).__name__})")
        finally:
            await context.close()
            
        print(f"  ├─ {fonte['nome']}: {len(numeros_encontrados)} número(s) localizado(s)")
        return numeros_encontrados

async def extrair_dados_caixa_sms(page):
    """Lê todas as mensagens da caixa e identifica se o número é antigo/inativo em qualquer site."""
    try:
        conteudo = await page.evaluate('''() => {
            const seletores = ['table', '.messages', '.sms-list', '.messages-list', '.list-group', 'article', 'main', '.number-messages', '.chat-box'];
            let acumulado = '';
            for (const sel of seletores) {
                const elems = document.querySelectorAll(sel);
                elems.forEach(el => {
                    if (el.innerText && el.innerText.length > 15) {
                        acumulado += ' ' + el.innerText;
                    }
                });
            }
            return acumulado.length > 20 ? acumulado : document.body.innerText;
        }''')
        texto_lc = conteudo.lower()
        
        # 🎯 FILTRO UNIVERSAL DE NÚMEROS ANTIGOS/INATIVOS (Para todos os sites)
        termos_antigos = [
            'year ago', 'years ago', 'month ago', 'months ago',
            'ano atrás', 'anos atrás', 'mês atrás', 'meses atrás',
            'há 1 ano', 'há 2 anos', 'há 3 anos', 'há 1 mês', 'há 2 meses',
            '2021', '2022', '2023', '2024', '2025'
        ]
        eh_antigo = any(termo in texto_lc for termo in termos_antigos)
        
        return texto_lc, eh_antigo
    except Exception:
        return "", False

# 🤖 ANÁLISE YOUTUBE
async def analisar_historico_youtube(item, browser, semaphore):
    async with semaphore:
        context = await configurar_contexto_anti_cloudflare(browser)
        page = await context.new_page()
        item['fossil'] = False
        try:
            await page.goto(item['link'], timeout=14000, wait_until="domcontentloaded")
            await page.wait_for_timeout(600)
            
            conteudo_caixa, eh_antigo = await extrair_dados_caixa_sms(page)
            item['fossil'] = eh_antigo  # Marca se for número antigo
            
            padrao_yt = r'(?:youtube|yt).{0,40}(?:code|código|verific|confirm|\d{6})'
            matches = re.findall(padrao_yt, conteudo_caixa, flags=re.IGNORECASE)
            
            item['usos_youtube'] = len(matches)
        except Exception:
            item['usos_youtube'] = 0
        finally:
            await context.close()
        return item

# 🤖 ANÁLISE CRIAÇÃO CONTA GOOGLE / GMAIL
async def analisar_historico_google_conta(item, browser, semaphore):
    async with semaphore:
        context = await configurar_contexto_anti_cloudflare(browser)
        page = await context.new_page()
        item['fossil'] = False
        try:
            await page.goto(item['link'], timeout=14000, wait_until="domcontentloaded")
            await page.wait_for_timeout(600)
            
            conteudo_caixa, eh_antigo = await extrair_dados_caixa_sms(page)
            item['fossil'] = eh_antigo  # Marca se for número antigo
            
            padrao_google = r'g-\d{5,6}|(?:google|gmail).{0,40}(?:code|código|verific|confirm|\d{6})'
            matches = re.findall(padrao_google, conteudo_caixa, flags=re.IGNORECASE)
            
            item['usos_google_conta'] = len(matches)
        except Exception:
            item['usos_google_conta'] = 0
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

def exibir_relatorio(aprovados_yt, aprovados_google):
    print("\n" + "="*70)
    print("🚀 RELATÓRIO FINAL: NÚMEROS APROVADOS (100% RECENTES & FILTRADOS)")
    print("="*70)

    print("\n🔴 [GRUPO 1: VERIFICAÇÃO DE CANAL YOUTUBE]")
    # 🚫 Descarta todos os números antigos de qualquer site
    yt_filtrados = [i for i in aprovados_yt if not i.get('fossil', False)]
    yt_ordenados = ordenar_por_prioridade(yt_filtrados, 'usos_youtube')
    
    if yt_ordenados:
        for i, item in enumerate(yt_ordenados, 1):
            usos = item['usos_youtube']
            status = "🟢 [VIRGEM - 0 USOS DETETADOS]" if usos == 0 else f"🟡 [{usos} USO(S) DETETADO(S)]"
            print(f"{i}. 📱 {item['numero']} {status}")
            print(f"   🌐 Fonte: {item['fonte']}")
            print(f"   🔗 Link Direto do SMS: {item['link']}")
            print("-" * 70)
    else:
        print("   ❌ Nenhum número recente/virgem para YouTube localizado nesta rodada.")

    print("\n🔵 [GRUPO 2: CRIAÇÃO DE CONTA GOOGLE / GMAIL]")
    # 🚫 Descarta todos os números antigos de qualquer site
    google_filtrados = [i for i in aprovados_google if not i.get('fossil', False)]
    google_ordenados = ordenar_por_prioridade(google_filtrados, 'usos_google_conta')
    
    if google_ordenados:
        for i, item in enumerate(google_ordenados, 1):
            usos = item['usos_google_conta']
            status = "🟢 [VIRGEM - 0 USOS DETETADOS]" if usos == 0 else f"🟡 [{usos} USO(S) DETETADO(S)]"
            print(f"{i}. 📱 {item['numero']} {status}")
            print(f"   🌐 Fonte: {item['fonte']}")
            print(f"   🔗 Link Direto do SMS: {item['link']}")
            print("-" * 70)
    else:
        print("   ❌ Nenhum número recente/virgem para criar conta Google localizado nesta rodada.")

async def main():
    print("\n⚡ [BOT YOUTUBE & GOOGLE TURBO v14] Iniciando busca com filtro universal...")
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        
        semaphore_coleta = asyncio.Semaphore(10)
        semaphore_yt = asyncio.Semaphore(12)
        semaphore_google = asyncio.Semaphore(12)
        
        print("\n🌐 Fase 1: Coletando números de todas as fontes...")
        tasks_fontes = [processar_fonte(f, browser, semaphore_coleta) for f in FONTES_SMS]
        resultados = await asyncio.gather(*tasks_fontes)
        
        todos_candidatos = []
        for lista in resultados:
            for item in lista:
                if not any(c['numero'] == item['numero'] for c in todos_candidatos):
                    todos_candidatos.append(item)
                    
        print(f"\n🔍 Fase 2: {len(todos_candidatos)} candidatos reunidos. Analisando mensagens e filtro de recência...")
        
        if todos_candidatos:
            tasks_yt = [analisar_historico_youtube(dict(c), browser, semaphore_yt) for c in todos_candidatos]
            tasks_google = [analisar_historico_google_conta(dict(c), browser, semaphore_google) for c in todos_candidatos]
            
            res_yt, res_google = await asyncio.gather(
                asyncio.gather(*tasks_yt),
                asyncio.gather(*tasks_google)
            )
            
            aprovados_yt = [item for item in res_yt if item['usos_youtube'] <= 1]
            aprovados_google = [item for item in res_google if item['usos_google_conta'] <= 1]
            
            exibir_relatorio(aprovados_yt, aprovados_google)
        else:
            exibir_relatorio([], [])
            
        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
