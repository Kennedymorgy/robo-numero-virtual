import time
import re
from playwright.sync_api import sync_playwright

def extrair_numeros(page):
    numeros = []
    
    fontes = [
        {"nome": "Receive-SMSS", "url": "https://receive-smss.com/"},
        {"nome": "SMSToMe", "url": "https://smstome.com/country/usa"},
        {"nome": "AnonymSMS", "url": "https://anonymsms.com/"},
        {"nome": "Quackr", "url": "https://quackr.io/temporary-numbers"},
        {"nome": "TempSMSS", "url": "https://tempsmss.com/"},
        {"nome": "SMS24", "url": "https://sms24.me/en/countries/us"}
    ]

    print("\n🌐 A varrer sites de SMS com navegacao Playwright...")

    for fonte in fontes:
        try:
            page.goto(fonte["url"], timeout=15000, wait_until="domcontentloaded")
            page.wait_for_timeout(2000)
            
            links = page.locator("a").all()
            count = 0
            
            for link in links:
                try:
                    href = link.get_attribute("href") or ""
                    txt = link.inner_text().strip()
                    
                    if any(c.isdigit() for c in txt) and len(txt) >= 7:
                        if href.startswith("http"):
                            url_comp = href
                        else:
                            base = fonte["url"].rstrip('/')
                            url_comp = f"{base}/{href.lstrip('/')}"
                            
                        if url_comp not in [n['link'] for n in numeros]:
                            numeros.append({'numero': txt, 'link': url_comp, 'fonte': fonte['nome']})
                            count += 1
                except Exception:
                    continue
                    
            print(f"  ├─ {fonte['nome']}: {count} numero(s) encontrado(s)")
        except Exception:
            print(f"  ├─ {fonte['nome']}: Erro ao carregar pagina")

    # Fallback fixo do VeePN
    numeros.append({'numero': '+1 351 355 3580', 'link': 'https://veepn.com/pt/online-sms/usa/13513553580/', 'fonte': 'VeePN'})
    return numeros

def analisar_historico(page, item):
    try:
        page.goto(item['link'], timeout=10000, wait_until="domcontentloaded")
        texto = page.content().lower()
        contagem = texto.count('google') + texto.count('youtube') + texto.count('g-')
        item['usos_google'] = contagem
        return item
    except Exception:
        item['usos_google'] = 999
        return item

def aguardar_codigo_sms(page, link_numero):
    print("\n⏳ [ESCUTA ATIVA INICIADA] A verificar rececao do SMS do YouTube (a cada 3s)...")
    
    for _ in range(40): # 2 minutos no maximo
        try:
            page.goto(link_numero, timeout=8000, wait_until="domcontentloaded")
            texto = page.inner_text("body")
            
            for linha in texto.split('\n'):
                linha_clean = linha.strip()
                if ("google" in linha_clean.lower() or "g-" in linha_clean.lower() or "youtube" in linha_clean.lower()) and any(c.isdigit() for c in linha_clean):
                    print("\n" + "🟢"*30)
                    print(f"🎉 CODIGO RECEBIDO: {linha_clean}")
                    print("🟢"*30 + "\n")
                    return True
        except Exception:
            pass
            
        time.sleep(3)
        print(".", end="", flush=True)
        
    print("\n\n❌ O SMS nao foi recebido no tempo limite. Execute o workflow novamente!")
    return False

if __name__ == "__main__":
    print("\n⚡ [MODO COMPLETO] A iniciar bot de captura de SMS...")
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            viewport={"width": 1280, "height": 720}
        )
        page = context.new_page()
        
        numeros_encontrados = extrair_numeros(page)
        print(f"\n🔍 Total de {len(numeros_encontrados)} numero(s) capturado(s). A analisar historico...")
        
        cand_perfeito = None
        cand_usado = None
        
        for idx, item in enumerate(numeros_encontrados, 1):
            res = analisar_historico(page, item)
            usos = res['usos_google']
            if usos < 999:
                num_fmt = res['numero'].replace('\n', ' ')
                print(f"  [{idx}/{len(numeros_encontrados)}] {num_fmt[:22]} ({res['fonte']}) -> {usos} uso(s) Google")
                
                if usos == 0 and not cand_perfeito:
                    cand_perfeito = res
                elif usos == 1 and not cand_usado:
                    cand_usado = res
                    
        escolhido = cand_perfeito if cand_perfeito else cand_usado
        
        if escolhido:
            status_texto = "🟢 VIRGEM (0/2 USOS)" if escolhido['usos_google'] == 0 else "🟡 UTILIZADO 1 VEZ (1/2 USOS)"
            print("\n" + "="*50)
            print(f"📱 NUMERO SELECCIONADO: {escolhido['numero'].strip()}")
            print(f"🌐 FONTE: {escolhido['fonte']}")
            print(f"📊 STATUS: {status_texto}")
            print(f"🔗 LINK: {escolhido['link']}")
            print("="*50)
            print("\n👉 COPIE O NUMERO ACIMA E COLE NO YOUTUBE AGORA!\n")
            
            aguardar_codigo_sms(page, escolhido['link'])
        else:
            print("\n❌ Nenhum numero valido encontrado abaixo do limite. Execute novamente!")
            
        browser.close()
