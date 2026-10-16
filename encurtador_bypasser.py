import os
import sys
import time
from playwright.sync_api import sync_playwright

def passar_encurtador_multietapas(url_inicial):
    print("=" * 80)
    print(f"🔓 BURLANDO ENCURTADOR MULTI-ETAPAS (MOTOR ANTI-LOOP + IMAGENS)")
    print(f"🔗 URL Inicial: {url_inicial}")
    print("=" * 80)

    link_final = None
    max_etapas = 8
    ultima_url = ""

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=[
                '--no-sandbox',
                '--disable-setuid-sandbox',
                '--disable-dev-shm-usage',
                '--disable-blink-features=AutomationControlled',
                '--disable-infobars'
            ]
        )
        
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            viewport={'width': 1366, 'height': 768}
        )

        page = context.new_page()
        page.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")

        # Interceptador de rede para capturar URLs finais
        def handle_response(response):
            nonlocal link_final
            if not link_final:
                try:
                    url_resp = response.url
                    domains_finais = ["mediafire.com", "drive.google.com", "mega.nz", "mega.io"]
                    if any(d in url_resp for d in domains_finais):
                        link_final = url_resp
                        return

                    if "json" in response.headers.get("content-type", ""):
                        body = response.json()
                        def procurar_url(obj):
                            nonlocal link_final
                            if isinstance(obj, dict):
                                for k, v in obj.items():
                                    if isinstance(v, str) and any(d in v for d in domains_finais):
                                        link_final = v
                                    elif isinstance(v, (dict, list)):
                                        procurar_url(v)
                            elif isinstance(obj, list):
                                for item in obj:
                                    procurar_url(item)
                        procurar_url(body)
                except:
                    pass

        page.on("response", handle_response)

        try:
            print(f"🚀 Acessando URL inicial...")
            page.goto(url_inicial, wait_until="domcontentloaded", timeout=40000)

            for etapa in range(1, max_etapas + 1):
                current_url = page.url
                print(f"\n--- [ETAPA {etapa}/{max_etapas}] URL atual: {current_url} ---")

                # Verifica se travou na mesma URL anterior
                if current_url == ultima_url:
                    print(f"⚠️ A URL não mudou. Tentando estratégia alternativa (rolar página e clicar em imagens)...")
                    try:
                        page.evaluate("window.scrollBy(0, 600);")
                        time.sleep(3)
                        # Tenta clicar em qualquer imagem ou link de anúncio visível
                        imagens = page.locator("img")
                        if imagens.count() > 0:
                            for i in range(min(imagens.count(), 3)):
                                img_el = imagens.nth(i)
                                if img_el.is_visible():
                                    print(f"🖼️ Clicando em imagem/banner da página...")
                                    img_el.click(timeout=2000)
                                    time.sleep(4)
                                    break
                    except:
                        pass
                else:
                    ultima_url = current_url

                # Verifica se já chegou ao destino final
                if any(dom in current_url for dom in ["mediafire.com", "drive.google.com", "mega.nz", "mega.io"]):
                    link_final = current_url
                    break

                print(f"⏳ Aguardando temporizador e scripts da etapa {etapa}...")
                time.sleep(7)

                try:
                    page.evaluate("window.scrollTo(0, document.body.scrollHeight / 2);")
                except:
                    pass

                # Seletores inteligentes priorizando botões reais e links de texto
                seletores = [
                    "button:has-text('Get Link')", "button:has-text('Obter Link')",
                    "button:has-text('Continue')", "button:has-text('Continuar')",
                    "a:has-text('Get Link')", "a:has-text('Obter Link')",
                    "a:has-text('Continue')", "a:has-text('Continuar')",
                    "a#get-link", "#btn-main", ".btn-success", "button.btn-primary"
                ]

                clicou = False
                for seletor in seletores:
                    try:
                        elementos = page.locator(seletor)
                        count = elementos.count()
                        for i in range(count):
                            el = elementos.nth(i)
                            if el.is_visible(timeout=1000):
                                texto_el = el.inner_text().lower()
                                if any(termo in texto_el for termo in ["loading", "wait", "segundos"]):
                                    continue # Ignora botões falsos de loading
                                
                                print(f"🎯 Clicando no elemento [{seletor}] (Texto: '{texto_el[:20]}')...")
                                
                                try:
                                    with page.expect_popup(timeout=3000) as popup_info:
                                        el.click(timeout=3000)
                                    popup_page = popup_info.value
                                    popup_page.wait_for_load_state("domcontentloaded", timeout=10000)
                                    page = popup_page
                                    page.on("response", handle_response)
                                except:
                                    el.click(timeout=3000)
                                    
                                clicou = True
                                time.sleep(5)
                                break
                        if clicou:
                            break
                    except:
                        continue

                if not clicou:
                    print(f"⚠️ Nenhum botão padrão encontrado. Tentando forçar clique em links de redirecionamento...")
                    try:
                        links = page.locator("a[href]")
                        for i in range(min(links.count(), 10)):
                            l = links.nth(i)
                            href = l.get_attribute("href") or ""
                            if not any(bad in href for bad in ["javascript", "#", "facebook", "twitter"]):
                                if l.is_visible():
                                    print(f"🔗 Clicando em link utilitário: {href[:40]}...")
                                    l.click(timeout=2000)
                                    time.sleep(4)
                                    break
                    except:
                        pass

                if link_final:
                    break

        except Exception as e:
        # Se ocorrer qualquer erro genérico
            print(f"⚠️ Erro no fluxo: {e}")

        browser.close()

    print("\n" + "=" * 80)
    if link_final:
        print(f"🎉 SUCESSO! LINK DIRETO EXTRAÍDO:")
        print(f"👉 {link_final}")
    else:
        print("❌ Não foi possível capturar o link final após todas as etapas.")
    print("=" * 80)
    return link_final

if __name__ == "__main__":
    url_input = os.getenv("SHORT_URL", "").strip()
    if not url_input:
        print("❌ Nenhuma URL fornecida!")
        sys.exit(1)

    passar_encurtador_multietapas(url_input)
