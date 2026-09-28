import asyncio
import re
from urllib.parse import urljoin
from playwright.async_api import async_playwright

# 🌍 PREFIXOS PERMITIDOS (EUA, Portugal, Finlândia, UK, França, Holanda, Alemanha)
PREFIXOS_ACEITOS = ['+1', '+351', '+358', '+44', '+33', '+31', '+49']

# Fontes configuradas (incluindo 2 novas fontes ativas)
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
    """Garante a montagem correta da URL para a caixa de mensagens, corrigindo Quackr e SMS-Man."""
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
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "none",
            "Sec-Fetch-User": "?1",
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

async def raspar_quackr(page, base_url):
    """Captura os números do Quackr garantindo a extração do link direto."""
    numeros = []
    for pagina in range(1, 4):
        url_pag = f"{base_url}?page={pagina}" if pagina > 1 else base_url
        try:
            await page.goto(url_pag, timeout=30000, wait_until="domcontentloaded")
            await page.mouse.wheel(0, 500)
            await page.wait_for_timeout(1500)
            
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
        await page.goto(base_url, timeout=30000, wait_until="domcontentloaded")
        await page.mouse.wheel(0, 800)
        await page.wait_for_timeout(2000)
        
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
                await page.goto(fonte["url"], timeout=25000, wait_until="domcontentloaded")
                await page.mouse.wheel(0, 400)
                await page.wait_for_timeout(1500)
                
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

# 🤖 ROBÔS TIPO A: 7 Trabalhadores dedicados à Verificação de Canal YouTube
async def analisar_historico_youtube(item, browser, semaphore):
    async with semaphore:
        context = await configurar_contexto_anti_cloudflare(browser)
        page = await context.new_page()
        try:
            await page.goto(item['link'], timeout=20000, wait_until="domcontentloaded")
            await page.wait_for_timeout(1000)
            
            corpo_texto = (await page.inner_text("body")).lower()
            mencoes_yt = corpo_texto.count('youtube')
            codigos_yt = len(re.findall(r'\byoutube\b.*\b\d{6}\b', corpo_texto))
            
            item['usos_youtube'] = max(mencoes_yt, codigos_yt)
        except Exception:
            item['usos_youtube'] = 0
        finally:
            await context.close()
        return item

# 🤖 ROBÔS TIPO B: 3 Trabalhadores dedicados à Criação de Conta Google / Gmail
async def analisar_historico_google_conta(item, browser, semaphore):
    async with semaphore:
        context = await configurar_contexto_anti_cloudflare(browser)
        page = await context.new_page()
        try:
            await page.goto(item['link'], timeout=20000, wait_until="domcontentloaded")
            await page.wait_for_timeout(1000)
            
            corpo_texto = (await page.inner_text("body")).lower()
            mencoes_g = corpo_texto.count('google') + corpo_texto.count('gmail')
            codigos_g = len(re.findall(r'\bg-\d{5,6}\b', corpo_texto))
            
            item['usos_google_conta'] = max(mencoes_g, codigos_g)
        except Exception:
            item['usos_google_conta'] = 0
        finally:
            await context.close()
        return item

def exibir_relatorio(aprovados_yt, aprovados_google):
    print("\n" + "="*70)
    print("🚀 RELATÓRIO FINAL: NÚMEROS APROVADOS (SISTEMA DE 10 ROBÔS)")
    print("="*70)

    print("\n🔴 [GRUPO 1: VERIFICAÇÃO DE CANAL YOUTUBE - 7 ROBÔS TRABALHANDO]")
    if aprovados_yt:
        for i, item in enumerate(aprovados_yt, 1):
            usos = item['usos_youtube']
            status = "🟢 [VIRGEM - 0 USOS YOUTUBE]" if usos == 0 else "🟡 [1 USO YOUTUBE DETETADO]"
            print(f"{i}. 📱 {item['numero']} {status}")
            print(f"   🌐 Fonte: {item['fonte']}")
            print(f"   🔗 Link Direto do SMS: {item['link']}")
            print("-" * 70)
    else:
        print("   ❌ Nenhum número virgem para YouTube localizado nesta rodada.")

    print("\n🔵 [GRUPO 2: CRIAÇÃO DE CONTA GOOGLE / GMAIL - 3 ROBÔS TRABALHANDO]")
    if aprovados_google:
        for i, item in enumerate(aprovados_google, 1):
            usos = item['usos_google_conta']
            status = "🟢 [VIRGEM - 0 USOS GOOGLE]" if usos == 0 else "🟡 [1 USO GOOGLE DETETADO]"
            print(f"{i}. 📱 {item['numero']} {status}")
            print(f"   🌐 Fonte: {item['fonte']}")
            print(f"   🔗 Link Direto do SMS: {item['link']}")
            print("-" * 70)
    else:
        print("   ❌ Nenhum número virgem para criar conta Google localizado nesta rodada.")

async def main():
    print("\n⚡ [BOT YOUTUBE & GOOGLE MULTI-ROBÔ v10] Iniciando com 10 Workers paralelos...")
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        
        # Configuração da infraestrutura de 10 Robôs em paralelo
        semaphore_coleta = asyncio.Semaphore(10)
        semaphore_yt = asyncio.Semaphore(7)       # 7 Robôs dedicados ao YouTube
        semaphore_google = asyncio.Semaphore(3)   # 3 Robôs dedicados a Criar Conta Google
        
        print("\n🌐 Fase 1: Coletando números nas 10 fontes de SMS...")
        tasks_fontes = [processar_fonte(f, browser, semaphore_coleta) for f in FONTES_SMS]
        resultados = await asyncio.gather(*tasks_fontes)
        
        todos_candidatos = []
        for lista in resultados:
            for item in lista:
                if not any(c['numero'] == item['numero'] for c in todos_candidatos):
                    todos_candidatos.append(item)
                    
        print(f"\n🔍 Fase 2: {len(todos_candidatos)} candidatos reunidos. Processando com os 10 robôs em paralelo...")
        
        if todos_candidatos:
            # Separação das tarefas entre as 2 equipes de robôs
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
