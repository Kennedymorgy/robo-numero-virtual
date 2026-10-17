import os
import sys
import time
import json
import re
from playwright.sync_api import sync_playwright

def passar_encurtador_ultimate(url_inicial):
    print("=" * 80)
    print(f"🔓 BURLANDO ENCURTADOR (MOTOR COM REGEX GLOBAL E SCRAPING DE DOMÍNIO)")
    print(f"🔗 URL Inicial: {url_inicial}")
    print("=" * 80)

    link_final = None
    max_etapas = 8
    domains_finais = ["mediafire.com", "drive.google.com", "mega.nz", "mega.io"]

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

        # Interceptador global de requisições de rede
        def handle_response(response):
            nonlocal link_final
            if not link_final:
                try:
                    url_resp = response.url
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

                # Verifica se a URL atual já é o destino final
                if any(dom in current_url for dom in domains_finais):
                    link_final = current_url
                    break

                # 1. Varredura Regex Global no HTML atual (Procura o link escondido no código fonte)
                html_atual = page.content()
                for dom in domains_finais:
                    matches = re.findall(rf'https?://[^\s"\'<>]+{dom}[^\s"\'<>]*', html_atual)
                    if matches:
                        link_final = matches[0]
                        print(f"🎯 Link encontrado via varredura de código-fonte!")
                        break
                if link_final:
                    break

                # 2. Rola a página para ativar widgets de timer baseados em scroll
                print(f"📜 Efetuando rolagem progressiva...")
                for scroll in range(3):
                    page.evaluate(f"window.scrollTo(0, document.body.scrollHeight * {(scroll + 1) / 3});")
                    time.sleep(1)

                print(f"⏳ Aguardando temporizador da etapa {etapa} (15 segundos para carregar scripts)...")
                time.sleep(15) # Tempo estendido para garantir que o timer do blog zere

                # Re-examina o HTML após o timer
                html_atual = page.content()
                for dom in domains_finais:
                    matches = re.findall(rf'https?://[^\s"\'<>]+{dom}[^\s"\'<>]*', html_atual)
                    if matches:
                        link_final = matches[0]
                        print(f"🎯 Link encontrado após o temporizador!")
                        break
                if link_final:
                    break

                # 3. Tenta clicar nos botões específicos de encurtadores em blogs
                seletores_blog = [
                    "#get-link", ".get-link", "a#get-link", "a.get-link",
                    "#download", ".download", "#btn-main", ".btn-success",
                    "button:has-text('Get Link')", "a:has-text('Get Link')",
                    "button:has-text('Open Link')", "a:has-text('Open Link')",
                    "button:has-text('Continue')", "a:has-text('Continue')",
                    "button:has-text('Click Here')", "a:has-text('Click Here')"
                ]

                clicou = False
                for sel in seletores_blog:
                    try:
                        el = page.locator(sel).first
                        if el.is_visible(timeout=1500):
                            txt_btn = el.inner_text().lower()
                            print(f"🎯 Clicando no elemento de redirecionamento [{sel}] (Texto: '{txt_btn[:20]}')...")
                            
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
                    except:
                        continue

                if not clicou:
                    print(f"⚠️ Nenhum botão padrão acionado nesta etapa. Avançando ciclo...")

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

    passar_encurtador_ultimate(url_input)
