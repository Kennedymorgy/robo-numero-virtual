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
        # Inicia o navegador com argumentos avançados anti-detecção
        browser = p.chromium.launch(
            headless=True,  # Mude para False se quiser assistir o navegador abrindo e resolvendo
            args=[
                '--no-sandbox',
                '--disable-setuid-sandbox',
                '--disable-dev-shm-usage',
                '--disable-blink-features=AutomationControlled',
                '--disable-infobars',
                '--start-maximized'
            ]
        )
        
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            viewport={'width': 1366, 'height': 768},
            device_scale_factor=1,
            is_mobile=False,
            has_touch=False
        )

        page = context.new_page()

        # Injeta script para esconder o navigator.webdriver
        page.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")

        try:
            print("[1/4] Acessando a página do encurtador...")
            page.goto(url_encurtada, wait_until="domcontentloaded", timeout=40000)
            
            # Pequena pausa para carregar os scripts iniciais
            time.sleep(3)

            # Estratégia 1: Verifica se já caiu direto no link final
            if any(dom in page.url for dom in ["mediafire.com", "drive.google.com", "mega.nz", "mega.io", "play.google.com"]):
                link_final = page.url
                print(f"✅ Link final encontrado diretamente: {link_final}")

            # Estratégia 2: Aguardar temporizador e lidar com botões de encurtadores
            if not link_final:
                print("[2/4] Aguardando temporizador e elementos da página...")
                
                # Tenta rolar a página para simular comportamento humano
                try:
                    page.evaluate("window.scrollTo(0, document.body.scrollHeight / 2);")
                except:
                    pass

                time.sleep(10) # Aguarda o timer padrão do encurtador

                print("[3/4] Procurando botões de redirecionamento ('Obter Link' / 'Continuar')...")
                
                # Seletores comuns em encurtadores modernos (AdLinkFly / Shrtslug / etc)
                seletores = [
                    "#btn-poster", "#get-link", "a#get-link", ".btn-success", 
                    "button#submit-button", ".get-link", "a.get-link",
                    "button.btn-primary", "input[type='submit']",
                    "a[href*='mediafire']", "a[href*='drive.google']", "a[href*='mega']"
                ]

                # Tenta clicar no primeiro botão válido que aparecer
                for seletor in seletores:
                    try:
                        elemento = page.locator(seletor).first
                        if elemento.is_visible(timeout=2000):
                            print(f"🎯 Botão encontrado com o seletor '{seletor}'. Clicando...")
                            
                            # Clica e aguja nova página ou navegação
                            with page.expect_popup(timeout=5000) as popup_info:
                                elemento.click()
                            
                            popup_page = popup_info.value
                            popup_page.wait_for_load_state("domcontentloaded", timeout=10000)
                            
                            if any(dom in popup_page.url for dom in ["mediafire.com", "drive.google.com", "mega.nz", "mega.io"]):
                                link_final = popup_page.url
                                break
                    except Exception:
                        pass
                
                # Se não abriu popup, verifica se a página atual mudou de URL após o clique
                if not link_final:
                    current_url = page.url
                    if not current_url.startswith(url_encurtada) and not any(bad in current_url for bad in ["shrtslug", "encurta", "adfly"]):
                        link_final = current_url

            # Estratégia 3: Varredura profunda no código-fonte HTML por links diretos
            if not link_final:
                print("[4/4] Analisando o código-fonte da página em busca do link de download final...")
                html = page.content()
                
                matches = re.findall(r'https?://(?:www\.)?(?:mediafire\.com|drive\.google\.com|mega\.nz|mega\.io)[^\s"\'<>]+', html)
                if matches:
                    link_final = matches[0]

            # Se ainda falhar, tira um print para debug
            if not link_final:
                os.makedirs("debug", exist_ok=True)
                page.screenshot(path="debug/erro_debug.png", full_page=True)
                print("📸 Captura de tela salva em 'debug/erro_debug.png' para análise.")

        except Exception as e:
            print(f"⚠️ Aviso de execução: {e}")
            try:
                page.screenshot(path="debug/erro_excecao.png", full_page=True)
            except:
                pass

        browser.close()

    print("\n" + "=" * 80)
    if link_final:
        print(f"🎉 SUCESSO! LINK DIRETO EXTRAÍDO:")
        print(f"👉 {link_final}")
    else:
        print("❌ Não foi possível capturar o link automático nesta tentativa.")
        print("💡 Dica: O encurtador pode estar exigindo CAPTCHA visual humano (Cloudflare/Turnstile).")
    print("=" * 80)

if __name__ == "__main__":
    url_input = os.getenv("SHORT_URL", "https://shrtslug.biz/97rjy").strip()
    if not url_input:
        print("❌ Nenhuma URL fornecida!")
        sys.exit(1)

    passar_encurtador(url_input)
