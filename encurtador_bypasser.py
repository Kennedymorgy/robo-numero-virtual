import os
import sys
import time
import json
from playwright.sync_api import sync_playwright

def passar_encurtador_multietapas(url_inicial):
    print("=" * 80)
    print(f"🔓 BURLANDO ENCURTADOR MULTI-ETAPAS (MOTOR AUTOMATIZADO)")
    print(f"🔗 URL Inicial: {url_inicial}")
    print("=" * 80)

    link_final = None
    max_etapas = 8  # Suporta até 8 páginas de redirecionamento em sequência

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

        # Interceptador de rede global para capturar JSONs de API em qualquer etapa
        def handle_response(response):
            nonlocal link_final
            if not link_final:
                try:
                    if "json" in response.headers.get("content-type", ""):
                        body = response.json()
                        def procurar_url_no_json(obj):
                            nonlocal link_final
                            if isinstance(obj, dict):
                                for k, v in obj.items():
                                    if isinstance(v, str) and v.startswith("http"):
                                        if any(dom in v for dom in ["mediafire.com", "drive.google.com", "mega.nz", "mega.io"]):
                                            link_final = v
                                    elif isinstance(v, (dict, list)):
                                        procurar_url_no_json(v)
                            elif isinstance(obj, list):
                                for item in obj:
                                    procurar_url_no_json(item)
                        procurar_url_no_json(body)
                except:
                    pass

        page.on("response", handle_response)

        try:
            print(f"🚀 Acessando URL inicial...")
            page.goto(url_inicial, wait_until="domcontentloaded", timeout=40000)

            domains_finais = ["mediafire.com", "drive.google.com", "mega.nz", "mega.io"]

            for etapa in range(1, max_etapas + 1):
                current_url = page.url
                print(f"\n--- [ETAPA {etapa}/{max_etapas}] URL atual: {current_url} ---")

                # Verifica se já chegamos ao destino final na URL
                if any(dom in current_url for dom in domains_finais):
                    link_final = current_url
                    break

                # Aguarda o timer/carregamento da página atual
                print(f"⏳ Aguardando temporizador e scripts da etapa {etapa}...")
                time.sleep(6)

                # Rola a página para ativar elementos visíveis
                try:
                    page.evaluate("window.scrollTo(0, document.body.scrollHeight / 2);")
                except:
                    pass

                # Lista de seletores e textos comuns em botões de avanço
                seletores = [
                    "#btn-main", "#get-link", "a#get-link", ".btn-success", 
                    "button#submit-button", ".get-link", "a.get-link",
                    "button.btn-primary", "input[type='submit']",
                    "button:has-text('Continuar')", "button:has-text('Proceed')",
                    "button:has-text('Get Link')", "button:has-text('Obter Link')",
                    "a:has-text('Continuar')", "a:has-text('Get Link')", "a:has-text('Obter Link')",
                    "button", "a.btn"
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
                                print(f"🎯 Clicando no elemento [{seletor}] (Texto: '{texto_el[:20]}')...")
                                
                                # Tenta clicar lidando com novas abas/popups
                                try:
                                    with page.expect_popup(timeout=3000) as popup_info:
                                        el.click(timeout=3000)
                                    popup_page = popup_info.value
                                    popup_page.wait_for_load_state("domcontentloaded", timeout=10000)
                                    page = popup_page  # Alterna o foco para a nova aba
                                    page.on("response", handle_response)
                                except:
                                    el.click(timeout=3000)
                                    
                                clicou = True
                                time.sleep(4)
                                break
                        if clicou:
                            break
                    except:
                        continue

                if not clicou:
                    print(f"⚠️ Nenhum botão interativo encontrado na etapa {etapa}. Tentando recarregar/avançar...")
                    time.sleep(4)

                # Se o link final foi capturado no meio do processo, encerra o loop
                if link_final:
                    break

        except Exception as e:
            print(f"⚠️ Erro durante o fluxo multi-etapas: {e}")

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
