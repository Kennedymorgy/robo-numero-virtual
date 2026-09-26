import asyncio
import re
from urllib.parse import urljoin
from playwright.async_api import async_playwright

# 🌍 PREFIXOS PERMITIDOS (Focados em ALTA ACEITAÇÃO: EUA, Portugal, Finlândia, UK, França, Holanda, Alemanha)
PREFIXOS_ACEITOS = ['+1', '+351', '+358', '+44', '+33', '+31', '+49']

# Fontes configuradas com seletores e comportamentos específicos
FONTES_SMS = [
    {"nome": "Quackr PT", "url": "https://quackr.io/pt/temporary-numbers", "tipo": "quackr"},
    {"nome": "SMS-Man Gratis", "url": "https://sms-man.com/pt/free-numbers", "tipo": "smsman"},
    {"nome": "Receive-SMSS", "url": "https://receive-smss.com/", "tipo": "padrao"},
    {"nome": "SMSToMe", "url": "https://smstome.com/country/usa", "tipo": "padrao"},
    {"nome": "AnonymSMS", "url": "https://anonymsms.com/", "tipo": "padrao"},
    {"nome": "TempSMSS", "url": "https://tempsmss.com/", "tipo": "padrao"},
    {"nome": "SMS24", "url": "https://sms24.me/en/countries/us", "tipo": "padrao"},
    {"nome": "OnlineSMS", "url": "https://online-sms.org/", "tipo": "padrao"}
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
    elif any(x in href.lower() for x in ['number', 'num', 'sms', 'receive', 'phone', 'free-numbers']) and len(href) > 5:
        return url_completa
    return None

async def configurar_contexto_anti_cloudflare(browser):
    """Cria um contexto emulando um dispositivo móvel (Android) para burlar proteções Anti-bot e Cloudflare."""
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
    
    # Injeta scripts para ocultar automação do navegador
    await context.add_init_script("""
        Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
        window.navigator.chrome = { runtime: {} };
        Object.defineProperty(navigator, 'plugins', { get: () => [1, 2, 3] });
        Object.defineProperty(navigator, 'languages', { get: () => ['pt-BR', 'pt', 'en-US', 'en'] });
    """)
    return context

async def raspar_quackr(page, base_url):
    """Varre o Quackr PT lidando com paginação e carregamento dinâmico (com scroll mobile)."""
    numeros = []
    for pagina in range(1, 4):
        url_pag = f"{base_url}?page={pagina}" if pagina > 1 else base_url
        try:
            await page.goto(url_pag, timeout=30000, wait_until="domcontentloaded")
            
            # Simula scroll no ecrã para carregar listas dinâmicas em mobile
            await page.mouse.wheel(0, 500)
            await page.wait_for_timeout(1500)
            await page.mouse.wheel(0, -200)
            await page.wait_for_timeout(1000)
            
            links = await page.locator("a").all()
            for link in links:
                try:
                    href = await link.get_attribute("href") or ""
                    txt = await link.inner_text()
                    num_valido = extrair_numero_limpo(txt) or extrair_numero_limpo(href)
                    if num_valido:
                        link_direto = construir_link_direto(base_url, href, num_valido)
                        if link_direto and not any(n['numero'] == num_valido for n in numeros):
                            numeros.append({'numero': num_valido, 'link': link_direto, 'fonte': 'Quackr PT'})
                except Exception:
                    continue
        except Exception:
            break
    return numeros

async def raspar_smsman(page, base_url):
    """Varre o SMS-Man Grátis com foco em cartões e tabelas no layout mobile."""
    numeros = []
    try:
        await page.goto(base_url, timeout=30000, wait_until="domcontentloaded")
        
        # Simula scroll para carregar todos os elementos invisíveis na primeira dobra
        await page.mouse.wheel(0, 600)
        await page.wait_for_timeout(2000)
        
        elementos = await page.locator("a, div, td, span").all()
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
    except Exception as e:
        print(f"  ├─ ⚠️ Erro no SMS-Man: {e}")
    return numeros

async def processar_fonte(fonte, browser, semaphore):
    """Executa a raspagem de cada site com controle de concorrência."""
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
                await page.wait_for_timeout(2000)
                
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
            print(f"  ├─ ⚠️ {fonte['nome']}: Erro ao carregar ({e})")
        finally:
            await context.close()
            
        print(f"  ├─ {fonte['nome']}: {len(numeros_encontrados)} número(s) localizado(s)")
        return numeros_encontrados

async def analisar_historico_numero(item, browser, semaphore):
    """Verifica se o número já recebeu códigos do Google/YouTube."""
    async with semaphore:
        context = await configurar_contexto_anti_cloudflare(browser)
        page = await context.new_page()
        
        try:
            await page.goto(item['link'], timeout=20000, wait_until="domcontentloaded")
            await page.wait_for_timeout(1500)
            
            corpo_texto = await page.inner_text("body")
            texto_lower = corpo_texto.lower()
            
            mencoes = texto_lower.count('youtube') + texto_lower.count('google') + texto_lower.count('gmail')
            codigos_g = len(re.findall(r'\bg-\d{5,6}\b', texto_lower))
            
            item['usos_google'] = max(mencoes, codigos_g)
        except Exception:
            item['usos_google'] = 0
        finally:
            await context.close()
            
        return item

def exibir_relatorio(aprovados):
    print("\n" + "="*70)
    print("🚀 RELATÓRIO FINAL: NÚMEROS VÁLIDOS PARA YOUTUBE (0/2 OU 1/2 USOS)")
    print("="*70)

    if aprovados:
        for i, item in enumerate(aprovados, 1):
            usos = item['usos_google']
            status = "🟢 [VIRGEM - 0/2 USOS]" if usos == 0 else "🟡 [1 USO DETETADO - 1 VAGA RESTANTE]"
            
            print(f"{i}. 📱 {item['numero']} {status}")
            print(f"   🌐 Fonte: {item['fonte']}")
            print(f"   📊 Menções/Códigos detetados: {usos}")
            print(f"   🔗 Link Direto do SMS: {item['link']}")
            print("-" * 70)
    else:
        print("\n❌ NENHUM NÚMERO DISPONÍVEL ENCONTRADO NESTA VARREDURA.")

async def main():
    print("\n⚡ [BOT YOUTUBE BLINDADO v9] Iniciando varredura Mobile com bypass Anti-Cloudflare...")
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        semaphore = asyncio.Semaphore(3)
        
        print("\n🌐 Fase 1: Coletando números em paralelo...")
        tasks_fontes = [processar_fonte(f, browser, semaphore) for f in FONTES_SMS]
        resultados = await asyncio.gather(*tasks_fontes)
        
        todos_candidatos = []
        for lista in resultados:
            for item in lista:
                if not any(c['numero'] == item['numero'] for c in todos_candidatos):
                    todos_candidatos.append(item)
                    
        print(f"\n🔍 Fase 2: {len(todos_candidatos)} candidato(s) recolhido(s). Analisando caixas de SMS...")
        
        if todos_candidatos:
            tasks_analise = [analisar_historico_numero(c, browser, semaphore) for c in todos_candidatos]
            candidatos_analisados = await asyncio.gather(*tasks_analise)
            
            aprovados = [item for item in candidatos_analisados if item['usos_google'] <= 1]
            aprovados.sort(key=lambda x: x['usos_google'])
            exibir_relatorio(aprovados)
        else:
            exibir_relatorio([])
            
        await browser.close()

if __name__ == "__main__":
    asyncio.main() if hasattr(asyncio, 'main') else asyncio.run(main())
