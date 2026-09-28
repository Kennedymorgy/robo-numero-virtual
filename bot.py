import asyncio
import re
from urllib.parse import urljoin
from playwright.async_api import async_playwright

# 🌍 PREFIXOS PERMITIDOS (EUA, Portugal, Finlândia, UK, França, Holanda, Alemanha)
PREFIXOS_ACEITOS = ['+1', '+351', '+358', '+44', '+33', '+31', '+49']

# Fontes configuradas
FONTES_SMS = [
    {"nome": "Quackr PT", "url": "https://quackr.io/pt/temporary-numbers", "tipo": "quackr"},
    {"nome": "SMS-Man Gratis", "url": "https://sms-man.com/pt/free-numbers", "tipo": "smsman"},
    {"nome": "Receive-SMSS", "url": "https://receive-smss.com/", "tipo": "padrao"},
    {"nome": "SMSToMe", "url": "https://smstome.com/country/usa", "tipo": "padrao"},
    {"nome": "AnonymSMS", "url": "https://anonymsms.com/", "tipo": "padrao"},
    {"nome": "TempSMSS", "url": "https://tempsmss.com/", "tipo": "padrao"},
    {"nome": "SMS24", "url": "https://sms24.me/en/countries/us", "tipo": "padrao"},
    {"nome": "OnlineSMS", "url": "https://online-sms.org/", "tipo": "padrao"},
    {"nome": "Receive-SMS.cc", "url": "https://receive-sms.cc/", "tipo": "padrao"},
    {"nome": "SMS-Online.co", "url": "https://sms-online.co/", "tipo": "padrao"}
]

# Seletores comuns onde ficam guardadas as caixas/tabelas de mensagens SMS nos sites
SELETORES_CONTAINER_SMS = [
    "table", ".messages", ".sms-list", ".messages-list", 
    ".list-group", "article", "main", ".number-messages"
]

def extrair_numero_limpo(texto):
    """Extrai e sanitiza os dígitos para formato E.164 rigoroso."""
    if not texto:
        return None
    
    limpo = re.sub(r'[^\d+]', '', texto)
    if not limpo.startswith('+') and len(limpo) >= 10:
        limpo = '+' + limpo

    if 10 <= len(limpo) <= 16:
        if limpo.startswith('+41'):  # Descarta Suíça
            return None
        if any(limpo.startswith(pref) for pref in PREFIXOS_ACEITOS):
            return limpo
    return None

def construir_link_direto(base_url, href, numero_limpo):
    """Garante a montagem correta da URL para a caixa de mensagens."""
    if not href or href == "#" or "javascript" in href:
        return None
        
    url_completa = urljoin(base_url, href)
    digitos = re.sub(r'\D', '', numero_limpo)
    
    if len(digitos) >= 7 and (digitos[-7:] in url_completa or digitos in url_completa):
        return url_completa
    elif any(x in href.lower() for x in ['number', 'num', 'sms', 'receive', 'phone', 'free-numbers', 'temporary-numbers']) and len(href) > 3:
        return url_completa
    return url_completa

async def configurar_contexto_anti_cloudflare(browser):
    """Cria contexto emulando dispositivo móvel Android para bypass de verificações."""
    context = await browser.new_context(
        user_agent="Mozilla/5.0 (Linux; Android 13; SM-S918B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Mobile Safari/537.36",
        viewport={"width": 412, "height": 915},
        is_mobile=True,
        has_touch=True,
        locale="pt-BR",
        timezone_id="America/Sao_Paulo",
        device_scale_factor=2.5,
        extra_http_headers={
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
            "Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7",
            "Accept-Encoding": "gzip, deflate, br",
            "Sec-Ch-Ua": '"Not.A/Brand";v="8", "Chromium";v="114", "Google Chrome";v="114"',
            "Sec-Ch-Ua-Mobile": "?1",
            "Sec-Ch-Ua-Platform": '"Android"',
            "Upgrade-Insecure-Requests": "1"
        }
    )
    
    await context.add_init_script("""
        Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
        window.navigator.chrome = { runtime: {} };
        Object.defineProperty(navigator, 'plugins', { get: () => [1, 2, 3] });
        Object.defineProperty(navigator, 'languages', { get: () => ['pt-BR', 'pt', 'en-US', 'en'] });
    """)
    return context

async def extrair_texto_caixa_sms(page):
    """Isola o container de SMS para evitar ler cabeçalhos, rodapés e botões do site."""
    textos = []
    for seletor in SELETORES_CONTAINER_SMS:
        try:
            elementos = await page.locator(seletor).all()
            for elem in elementos:
                t = await elem.inner_text()
                if t and len(t) > 20:
                    textos.append(t)
        except Exception:
            continue
    
    if textos:
        return " ".join(textos).lower()
    
    # Fallback caso o site use tags não padrão
    return (await page.inner_text("body")).lower()

async def raspar_quackr(page, base_url):
    """Captura os números do Quackr garantindo a extração do link direto."""
    numeros = []
    for pagina in range(1, 4):
        url_pag = f"{base_url}?page={pagina}" if pagina > 1 else base_url
        try:
            await page.goto(url_pag, timeout=25000, wait_until="domcontentloaded")
            await page.mouse.wheel(0, 500)
            await page.wait_for_timeout(1000)
            
            links = await page.locator("a").all()
            for link in links:
                try:
                    href = await link.get_attribute("href") or ""
                    txt = await link.inner_text()
                    num_valido = extrair_numero_limpo(txt) or extrair_numero_limpo(href)
                    if num_valido:
                        link_direto = construir_link_direto(base_url, href, num_valido) or urljoin(base_url, href)
                        if link_direto and not any(n['numero'] == num_valido for n in numeros):
                            numeros.append({'numero': num_valido, 'link': link_direto, 'fonte': 'Quackr PT'})
                except Exception:
                    continue
        except Exception:
            break
    return numeros

async def raspar_smsman(page, base_url):
    """Captura os números do SMS-Man contornando o carregamento dinâmico via DOM."""
    numeros = []
    try:
        await page.goto(base_url, timeout=25000, wait_until="domcontentloaded")
        await page.mouse.wheel(0, 800)
        await page.wait_for_timeout(1500)
        
        elementos = await page.locator("a[href*='free-numbers'], div.card, div, td, span").all()
        for elem in elementos:
            try:
                txt = await elem.inner_text()
                href = await elem.get_attribute("href") or ""
                num_valido = extrair_numero_limpo(txt) or extrair_numero_limpo(href)
                if num_valido:
                    link_direto = construir_link_direto(base_url, href, num_valido) or base_url
                    if not any(n['numero'] == num_valido for n in numeros):
                        numeros.append({'numero': num_valido, 'link': link_direto, 'fonte': 'SMS-Man Gratis'})
            except Exception:
                continue
    except Exception:
        pass
    return numeros

async def processar_fonte(fonte, browser, semaphore):
    """Executa a raspagem com semáforo de alta concorrência."""
    async with semaphore:
        context = await configurar_contexto_anti_cloudflare(browser)
        page = await context.new_page()
        numeros_encontrados = []
        
        try:
            if fonte["tipo"] == "quackr":
                numeros_encontrados = await raspar_quackr(page, fonte["url"])
            elif fonte["tipo"] == "smsman":
                numeros_encontrados = await raspar_smsman(page, fonte["url"])
            else:
                await page.goto(fonte["url"], timeout=20000, wait_until="domcontentloaded")
                await page.mouse.wheel(0, 400)
                await page.wait_for_timeout(1000)
                
                links = await page.locator("a").all()
                for link in links:
                    try:
                        href = await link.get_attribute("href") or ""
                        txt = await link.inner_text()
                        num_valido = extrair_numero_limpo(txt) or extrair_numero_limpo(href)
                        if num_valido:
                            link_direto = construir_link_direto(fonte["url"], href, num_valido)
                            if link_direto and not any(n['numero'] == num_valido for n in numeros_encontrados):
                                numeros_encontrados.append({'numero': num_valido, 'link': link_direto, 'fonte': fonte['nome']})
                    except Exception:
                        continue
        except Exception as e:
            print(f"  ├─ ⚠️ {fonte['nome']}: Erro de carregamento ({e})")
        finally:
            await context.close()
            
        print(f"  ├─ {fonte['nome']}: {len(numeros_encontrados)} número(s) localizado(s)")
        return numeros_encontrados

# 🤖 ROBÔS TIPO A (10 WORKERS): Verificação de Canal YouTube
async def analisar_historico_youtube(item, browser, semaphore):
    async with semaphore:
        context = await configurar_contexto_anti_cloudflare(browser)
        page = await context.new_page()
        try:
            await page.goto(item['link'], timeout=20000, wait_until="networkidle")
            
            conteudo_caixa = await extrair_texto_caixa_sms(page)
            
            # Regex rigoroso: procura 'youtube' acompanhado de códigos ou palavras de confirmação
            padrao_yt_rigoroso = r'\byoutube\b.{0,30}\b(code|código|verific|confirm|\d{6})\b'
            matches = re.findall(padrao_yt_rigoroso, conteudo_caixa)
            
            item['usos_youtube'] = len(matches)
        except Exception:
            item['usos_youtube'] = 0
        finally:
            await context.close()
        return item

# 🤖 ROBÔS TIPO B (5 WORKERS): Criação de Conta Google / Gmail
async def analisar_historico_google_conta(item, browser, semaphore):
    async with semaphore:
        context = await configurar_contexto_anti_cloudflare(browser)
        page = await context.new_page()
        try:
            await page.goto(item['link'], timeout=20000, wait_until="networkidle")
            
            conteudo_caixa = await extrair_texto_caixa_sms(page)
            
            # Regex rigoroso: procura padrões como G-XXXXXX ou 'google/gmail' associado a códigos
            padrao_google_rigoroso = r'\bg-\d{5,6}\b|\b(google|gmail)\b.{0,30}\b(code|código|verific|confirm|\d{6})\b'
            matches = re.findall(padrao_google_rigoroso, conteudo_caixa)
            
            item['usos_google_conta'] = len(matches)
        except Exception:
            item['usos_google_conta'] = 0
        finally:
            await context.close()
        return item

def exibir_relatorio(aprovados_yt, aprovados_google):
    print("\n" + "="*70)
    print("🚀 RELATÓRIO FINAL: NÚMEROS APROVADOS (FROTA DE 15 ROBÔS PARALELOS)")
    print("="*70)

    print("\n🔴 [GRUPO 1: VERIFICAÇÃO DE CANAL YOUTUBE - 10 ROBÔS ATIVOS]")
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

    print("\n🔵 [GRUPO 2: CRIAÇÃO DE CONTA GOOGLE / GMAIL - 5 ROBÔS ATIVOS]")
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
    print("\n⚡ [BOT YOUTUBE & GOOGLE TURBO v11] Iniciando com frota expandida de robôs...")
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        
        # Frota expandida de trabalhadores em paralelo
        semaphore_coleta = asyncio.Semaphore(15)  # 15 Robôs coletando fontes
        semaphore_yt = asyncio.Semaphore(10)       # 10 Robôs analisando YouTube
        semaphore_google = asyncio.Semaphore(5)    # 5 Robôs analisando Criar Conta Google
        
        print("\n🌐 Fase 1: Coletando números em tempo recorde nas 10 fontes...")
        tasks_fontes = [processar_fonte(f, browser, semaphore_coleta) for f in FONTES_SMS]
        resultados = await asyncio.gather(*tasks_fontes)
        
        todos_candidatos = []
        for lista in resultados:
            for item in lista:
                if not any(c['numero'] == item['numero'] for c in todos_candidatos):
                    todos_candidatos.append(item)
                    
        print(f"\n🔍 Fase 2: {len(todos_candidatos)} candidatos reunidos. Analisando caixas de mensagens com a frota...")
        
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
