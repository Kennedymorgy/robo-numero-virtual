import asyncio
import re
from urllib.parse import urljoin
from playwright.async_api import async_playwright

# 🌍 PREFIXOS PERMITIDOS (EUA, Portugal, Finlândia, UK, França, Holanda, Alemanha)
PREFIXOS_ACEITOS = ('+1', '+351', '+358', '+44', '+33', '+31', '+49')

# Fontes configuradas
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
    
    # 1. Procura números que já começam com + (ex: +12025550123 ou +351912345678)
    com_mais = re.findall(r'\+\d{10,15}', re.sub(r'[^\d+]', '', combo))
    for num in com_mais:
        if num.startswith('+41'): # Descarta Suíça
            continue
        if any(num.startswith(p) for p in PREFIXOS_ACEITOS):
            return num

    # 2. Procura sequências numéricas de 10 a 15 dígitos sem +
    digitos_lista = re.findall(r'\b\d{10,15}\b', combo)
    for dig in digitos_lista:
        # Detecta o país com base nas palavras-chave da URL/texto
        if any(k in combo for k in ['usa', 'united-states', 'us', 'america']):
            cand = '+1' + dig if not dig.startswith('1') else '+' + dig
        elif any(k in combo for k in ['portugal', 'pt']):
            cand = '+351' + dig if not dig.startswith('351') else '+' + dig
        elif any(k in combo for k in ['uk', 'united-kingdom', 'gb', 'england']):
            cand = '+44' + dig if not dig.startswith('44') else '+' + dig
        elif any(k in combo for k in ['france', 'francia', 'fr']):
            cand = '+33' + dig if not dig.startswith('33') else '+' + dig
        elif any(k in combo for k in ['finland', 'finlandia']):
            cand = '+358' + dig if not dig.startswith('358') else '+' + dig
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
    """Cria contexto emulando dispositivo móvel Android e bloqueia apenas mídia pesada."""
    context = await browser.new_context(
        user_agent="Mozilla/5.0 (Linux; Android 13; SM-S918B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Mobile Safari/537.36",
        viewport={"width": 412, "height": 915},
        is_mobile=True,
        has_touch=True,
        locale="pt-BR",
        timezone_id="America/Sao_Paulo"
    )
    
    # Bloqueia apenas imagens, vídeos e fontes (MANTÉM JS/CSS para os sites renderizarem)
    await context.route("**/*.{png,jpg,jpeg,gif,webp,svg,mp4,mp3,woff,woff2,ttf,otf}", lambda route: route.abort())
    return context

async def processar_fonte(fonte, browser, semaphore):
    """Varre todos os links da página diretamente no DOM do navegador."""
    async with semaphore:
        context = await configurar_contexto_anti_cloudflare(browser)
        page = await context.new_page()
        numeros_encontrados = []
        
        try:
            await page.goto(fonte["url"], timeout=14000, wait_until="domcontentloaded")
            await page.wait_for_timeout(1000)
            
            # Rola a página para acionar carregamento dinâmico
            await page.evaluate("window.scrollBy(0, 800)")
            await page.wait_for_timeout(500)
            
            # Extração instantânea de todos os links via JS no navegador
            links_dom = await page.evaluate('''() => {
                return Array.from(document.querySelectorAll('a')).map(a => ({
                    href: a.getAttribute('href') || '',
                    text: a.innerText || ''
                }));
            }''')
            
            for item in links_dom:
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

async def extrair_texto_caixa_sms(page):
    """Lê as mensagens da caixa de entrada direto no DOM com velocidade máxima."""
    try:
        texto = await page.evaluate('''() => {
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
        return texto.lower()
    except Exception:
        return ""

# 🤖 ROBÔS TIPO A: Verificação de Canal YouTube
async def analisar_historico_youtube(item, browser, semaphore):
    async with semaphore:
        context = await configurar_contexto_anti_cloudflare(browser)
        page = await context.new_page()
        try:
            await page.goto(item['link'], timeout=12000, wait_until="domcontentloaded")
            await page.wait_for_timeout(600)
            
            conteudo_caixa = await extrair_texto_caixa_sms(page)
            
            # Detecta mensagens com 'youtube' e códigos de confirmação
            padrao_yt = r'(?:youtube|yt).{0,40}(?:code|código|verific|confirm|\d{6})'
            matches = re.findall(padrao_yt, conteudo_caixa, flags=re.IGNORECASE)
            
            item['usos_youtube'] = len(matches)
        except Exception:
            item['usos_youtube'] = 0
        finally:
            await context.close()
        return item

# 🤖 ROBÔS TIPO B: Criação de Conta Google / Gmail
async def analisar_historico_google_conta(item, browser, semaphore):
    async with semaphore:
        context = await configurar_contexto_anti_cloudflare(browser)
        page = await context.new_page()
        try:
            await page.goto(item['link'], timeout=12000, wait_until="domcontentloaded")
            await page.wait_for_timeout(600)
            
            conteudo_caixa = await extrair_texto_caixa_sms(page)
            
            # Detecta mensagens com formato G-XXXXXX ou 'google'/'gmail'
            padrao_google = r'g-\d{5,6}|(?:google|gmail).{0,40}(?:code|código|verific|confirm|\d{6})'
            matches = re.findall(padrao_google, conteudo_caixa, flags=re.IGNORECASE)
            
            item['usos_google_conta'] = len(matches)
        except Exception:
            item['usos_google_conta'] = 0
        finally:
            await context.close()
        return item

def exibir_relatorio(aprovados_yt, aprovados_google):
    print("\n" + "="*70)
    print("🚀 RELATÓRIO FINAL: NÚMEROS APROVADOS")
    print("="*70)

    print("\n🔴 [GRUPO 1: VERIFICAÇÃO DE CANAL YOUTUBE]")
    if aprovados_yt:
        for i, item in enumerate(aprovados_yt, 1):
            usos = item['usos_youtube']
            status = "🟢 [VIRGEM - 0 USOS DETETADOS]" if usos == 0 else f"🟡 [{usos} USO(S) DETETADO(S)]"
            print(f"{i}. 📱 {item['numero']} {status}")
            print(f"   🌐 Fonte: {item['fonte']}")
            print(f"   🔗 Link Direto do SMS: {item['link']}")
            print("-" * 70)
    else:
        print("   ❌ Nenhum número virgem para YouTube localizado nesta rodada.")

    print("\n🔵 [GRUPO 2: CRIAÇÃO DE CONTA GOOGLE / GMAIL]")
    if aprovados_google:
        for i, item in enumerate(aprovados_google, 1):
            usos = item['usos_google_conta']
            status = "🟢 [VIRGEM - 0 USOS DETETADOS]" if usos == 0 else f"🟡 [{usos} USO(S) DETETADO(S)]"
            print(f"{i}. 📱 {item['numero']} {status}")
            print(f"   🌐 Fonte: {item['fonte']}")
            print(f"   🔗 Link Direto do SMS: {item['link']}")
            print("-" * 70)
    else:
        print("   ❌ Nenhum número virgem para criar conta Google localizado nesta rodada.")

async def main():
    print("\n⚡ [BOT YOUTUBE & GOOGLE TURBO v12] Coletando e analisando em velocidade máxima...")
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        
        # Limite otimizado para não gargalar a CPU da VM
        semaphore_coleta = asyncio.Semaphore(6)
        semaphore_yt = asyncio.Semaphore(8)
        semaphore_google = asyncio.Semaphore(8)
        
        print("\n🌐 Fase 1: Coletando números de todas as fontes...")
        tasks_fontes = [processar_fonte(f, browser, semaphore_coleta) for f in FONTES_SMS]
        resultados = await asyncio.gather(*tasks_fontes)
        
        todos_candidatos = []
        for lista in resultados:
            for item in lista:
                if not any(c['numero'] == item['numero'] for c in todos_candidatos):
                    todos_candidatos.append(item)
                    
        print(f"\n🔍 Fase 2: {len(todos_candidatos)} candidatos reunidos. Analisando SMS recebidos...")
        
        if todos_candidatos:
            tasks_yt = [analisar_historico_youtube(dict(c), browser, semaphore_yt) for c in todos_candidatos]
            tasks_google = [analisar_historico_google_conta(dict(c), browser, semaphore_google) for c in todos_candidatos]
            
            res_yt, res_google = await asyncio.gather(
                asyncio.gather(*tasks_yt),
                asyncio.gather(*tasks_google)
            )
            
            aprovados_yt = [item for item in res_yt if item['usos_youtube'] <= 1]
            aprovados_yt.sort(key=lambda x: x['usos_youtube'])
            
            aprovados_google = [item for item in res_google if item['usos_google_conta'] <= 1]
            aprovados_google.sort(key=lambda x: x['usos_google_conta'])
            
            exibir_relatorio(aprovados_yt, aprovados_google)
        else:
            exibir_relatorio([], [])
            
        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
