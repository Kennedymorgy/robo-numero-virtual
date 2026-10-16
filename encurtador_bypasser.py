import os
import sys
import time
import json
import re
from playwright.sync_api import sync_playwright

def passar_encurtador_blog_advanced(url_inicial):
    print("=" * 80)
    print(f"🔓 BURLANDO ENCURTADOR (EXTRATOR COM SCROLL PROFUNDO E IFRAMES)")
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

        # Monitoramento contínuo da rede
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

                if any(dom in current_url for dom in ["mediafire.com", "drive.google.com", "mega.nz", "mega.io"]):
                    link_final = current_url
                    break

                # Scroll progressivo para simular navegação humana e disparar scripts de ad/timer
                print(f"📜 Efetuando rolagem suave pela página...")
                for scroll in range(5):
                    page.evaluate(f"window.scrollTo(0, document.body.scrollHeight * {(scroll + 1) / 5});")
                    time.sleep(1.5)

                print(f"⏳ Aguardando temporizadores da etapa {etapa}...")
                time.sleep(6)

                # Busca por atributos data-url / data-href no HTML
                html_content = page.content()
                matches_data = re.findall(r'data-(?:url|href|link)=["\'](https?://[^"\']+)["\']', html_content)
                for match in matches_data:
                    if any(dom in match for dom in ["mediafire.com", "drive.google.com", "mega.nz", "mega.io"]):
                        link_final = match
                        break

                if link_final:
                    break

                # Tenta localizar e clicar em elementos específicos dentro do frame principal e iFrames
                frames = [page] + page.frames
                clicou = False

                for frame in frames:
                    try:
                        # Seletores focados em botões reais de encurtadores
                        seletores_alvo = [
                            "#btn-main", "#get-link", "a#get-link", "a.get-link", ".btn-success",
                            "#btn-poster", "#gotolink", "#landing-btn", ".download-btn",
                            "button:has-text('Get Link')", "a:has-text('Get Link')",
                            "button:has-text('Obter Link')", "a:has-text('Obter Link')",
                            "button:has-text('Continue')", "a:has-text('Continue')"
                        ]

                        for seletor in seletores_alvo:
                            elementos = frame.locator(seletor)
                            count = elementos.count()
                            for i in range(count):
                                el = elementos.nth(i)
                                if el.is_visible(timeout=1000):
                                    txt = el.inner_text().lower()
                                    print(f"🎯 Botão válido encontrado [{seletor}] (Texto: '{txt[:20]}'). Clicando...")
                                    
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
                        if clicou:
                            break
                    except:
                        continue

                # Se não achou botões padrão, tenta encontrar links que levem a subpáginas de download
                if not clicou:
                    print(f"⚠️ Varrendo links diretos e form actions no código-fonte...")
                    forms = page.locator("form")
                    if forms.count() > 0:
                        for f_idx in range(forms.count()):
                            try:
                                form_el = forms.nth(f_idx)
                                if form_el.is_visible():
                                    print(f"📝 Submetendo formulário da etapa...")
                                    form_el.evaluate("form => form.submit()")
                                    clicou = True
                                    time.sleep(5)
                                    break
                            except:
                                pass

                if link_final:
                    break

        except Exception as e:
            print(f"⚠️ Erro na execução: {e}")

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

    passar_encurtador_blog_advanced(url_input)
