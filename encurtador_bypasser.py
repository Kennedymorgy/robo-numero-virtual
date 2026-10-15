import os
import sys
import re
import time
from playwright.sync_api import sync_playwright

def passar_encurtador(url_encurtada):
    print("=" * 80)
    print(f"🔓 DESCRIPTOGRAFANDO LINK E BURLANDO ENCURTADOR")
    print(f"🔗 URL Alvo: {url_encurtada}")
    print("=" * 80)

    link_final = None

    with sync_playwright() as p:
        # Inicia o navegador invisível
        browser = p.chromium.launch(
            headless=True,
            args=[
                '--no-sandbox',
                '--disable-setuid-sandbox',
                '--disable-dev-shm-usage',
                '--disable-blink-features=AutomationControlled'
            ]
        )
        
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            viewport={'width': 1280, 'height': 720}
        )

        page = context.new_page()

        try:
            print("[1/4] Acessando a página do encurtador...")
            page.goto(url_encurtada, wait_until="domcontentloaded", timeout=30000)
            time.sleep(3)

            # Estratégia 1: Detecta se a página redirecionou diretamente para o Mediafire/Drive/Mega
            if any(dom in page.url for dom in ["mediafire.com", "drive.google.com", "mega.nz", "mega.io"]):
                link_final = page.url
                print(f"✅ Link final encontrado diretamente: {link_final}")

            # Estratégia 2: Caso tenha timer e botões do EncurtaNet (ex: #btn-poster, #get-link, .btn)
            if not link_final:
                print("[2/4] Aguardando temporizador e contagem regressiva de segundos...")
                time.sleep(12) # Tempo padrão dos encurtadores (10s)

                print("[3/4] Procurando botões de redirecionamento ('Obter Link' / 'Get Link')...")
                
                # Tenta clicar nos seletores comuns de botões de encurtadores
                seletores = [
                    "#btn-poster", "#get-link", "a#get-link", ".btn-success", 
                    "a[href*='mediafire']", "a[href*='drive.google']", "a[href*='mega']"
                ]

                for seletor in seletores:
                    try:
                        elemento = page.query_selector(seletor)
                        if elemento and elemento.is_visible():
                            print(f"🎯 Botão encontrado no seletor '{seletor}'. Clicando...")
                            
                            # Captura novos links que abrem ao clicar
                            with page.expect_popup(timeout=5000) as popup_info:
                                elemento.click()
                            popup_page = popup_info.value
                            popup_page.wait_for_load_state("domcontentloaded")
                            
                            if any(dom in popup_page.url for dom in ["mediafire.com", "drive.google.com", "mega.nz", "mega.io"]):
                                link_final = popup_page.url
                                break
                    except Exception:
                        pass

            # Estratégia 3: Varredura de links diretos dentro do HTML do site
            if not link_final:
                print("[4/4] Analisando o código-fonte da página em busca do link de download final...")
                html = page.content()
                
                # Busca padrões de links do Mediafire, Mega ou Google Drive soltos no código
                matches = re.findall(r'https?://(?:www\.)?(?:mediafire\.com|drive\.google\.com|mega\.nz|mega\.io)[^\s"\'<>]+', html)
                if matches:
                    link_final = matches[0]

        except Exception as e:
            print(f"⚠️ Aviso de execução: {e}")

        browser.close()

    print("\n" + "=" * 80)
    if link_final:
        print(f"🎉 SUCESSO! LINK DIRETO EXTRAÍDO:")
        print(f"👉 {link_final}")
    else:
        print("❌ Não foi possível capturar o link automático nesta tentativa.")
        print("💡 Dica: Verifique se o link precisa de resolução manual de CAPTCHA.")
    print("=" * 80)

if __name__ == "__main__":
    url_input = os.getenv("SHORT_URL", "").strip()
    if not url_input:
        print("❌ Nenhuma URL fornecida!")
        sys.exit(1)

    passar_encurtador(url_input)
