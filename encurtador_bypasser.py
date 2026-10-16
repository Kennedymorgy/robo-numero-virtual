import os
import sys
import time
import json
from playwright.sync_api import sync_playwright

def passar_encurtador_playwright_api(url_encurtada):
    print("=" * 80)
    print(f"🔓 BURLANDO ENCURTADOR (PLAYWRIGHT + NETWORK INTERCEPTION)")
    print(f"🔗 URL Alvo: {url_encurtada}")
    print("=" * 80)

    link_final = None

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

        # Escuta todas as respostas de rede que passam pelo navegador
        def handle_response(response):
            nonlocal link_final
            # Procura quando a API de verificação do encurtador responder
            if "api-endpoint/verify" in response.url or "verify" in response.url:
                try:
                    body = response.json()
                    print(f"📦 Pacote JSON interceptado da API: {json.dumps(body)}")
                    
                    # Varre o JSON em busca do link de destino final
                    for key in ['url', 'success_url', 'link', 'data']:
                        if key in body and isinstance(body[key], str) and body[key].startswith('http'):
                            val = body[key]
                            if not "shrtslug" in val and not "encurta" in val:
                                link_final = val
                                break
                except:
                    pass

        page.on("response", handle_response)

        try:
            print("[1/3] Acessando a página e executando JavaScript (passando no teste de adblock)...")
            page.goto(url_encurtada, wait_until="domcontentloaded", timeout=40000)
            
            print("[2/3] Aguardando o temporizador rodar nativamente...")
            time.sleep(12) # Tempo necessário para o timer interno zerar

            print("[3/3] Simulando clique no botão de liberação...")
            seletores_botao = [
                "#btn-main", "#get-link", "a#get-link", ".btn-success", 
                "button#submit-button", ".get-link", "a.get-link",
                "button.btn-primary", "input[type='submit']", "button"
            ]

            for seletor in seletores_botao:
                try:
                    btn = page.locator(seletor).first
                    if btn.is_visible(timeout=1500):
                        print(f"🎯 Clicando no elemento: {seletor}")
                        btn.click(timeout=3000)
                        time.sleep(4)
                        if link_final:
                            break
                except:
                    pass

            # Verificação extra caso o link venha na URL da página atual
            if not link_final:
                time.sleep(3)
                current_url = page.url
                if any(dom in current_url for dom in ["mediafire.com", "drive.google.com", "mega.nz", "mega.io"]):
                    link_final = current_url

        except Exception as e:
            print(f"⚠️ Erro na execução do Playwright: {e}")

        browser.close()

    print("\n" + "=" * 80)
    if link_final:
        print(f"🎉 SUCESSO! LINK DIRETO EXTRAÍDO:")
        print(f"👉 {link_final}")
    else:
        print("❌ Não foi possível capturar o link final nesta tentativa.")
    print("=" * 80)

if __name__ == "__main__":
    url_input = os.getenv("SHORT_URL", "").strip()
    if not url_input:
        print("❌ Nenhuma URL fornecida!")
        sys.exit(1)

    passar_encurtador_playwright_api(url_input)
