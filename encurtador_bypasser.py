import os
import sys
import re
import time
from bs4 import BeautifulSoup
from curl_cffi import requests

def passar_encurtador(url_encurtada):
    print("=" * 80)
    print(f"🔓 BURLANDO ENCURTADOR COM CURL_CFFI (BYPASS CLOUDFLARE)")
    print(f"🔗 URL Alvo: {url_encurtada}")
    print("=" * 80)

    link_final = None

    # Cria sessão com impressão digital real do Chrome 120
    session = requests.Session(impersonate="chrome120")
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
        "Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.9,en;q=0.9",
        "Referer": url_encurtada
    }

    try:
        print("[1/3] Acessando a página do encurtador...")
        response = session.get(url_encurtada, headers=headers, timeout=30)
        
        if response.status_code != 200:
            print(f"❌ Erro HTTP {response.status_code}: A página bloqueou a requisição.")
            return

        print("[2/3] Analisando o conteúdo e aguardando timer simulado...")
        time.sleep(6) # Aguarda o tempo necessário para o encurtador liberar o link

        soup = BeautifulSoup(response.text, 'html.parser')

        # Estratégia A: Procura por links de download direto (Mediafire, Mega, Drive, etc.) no HTML
        matches = re.findall(r'https?://(?:www\.)?(?:mediafire\.com|drive\.google\.com|mega\.nz|mega\.io)[^\s"\'<>]+', response.text)
        if matches:
            link_final = matches[0]

        # Estratégia B: Se não achou direto, procura por formulários de redirecionamento (comum em AdLinkFly/Shrtslug)
        if not link_final:
            form = soup.find('form')
            if form:
                action = form.get('action') or url_encurtada
                inputs = form.find_all('input')
                data = {inp.get('name'): inp.get('value') for inp in inputs if inp.get('name')}
                
                print("[3/3] Enviando requisição de liberação para o formulário...")
                post_response = session.post(action, data=data, headers=headers, timeout=30)
                
                # Procura links na resposta do POST
                matches_post = re.findall(r'https?://(?:www\.)?(?:mediafire\.com|drive\.google\.com|mega\.nz|mega\.io)[^\s"\'<>]+', post_response.text)
                if matches_post:
                    link_final = matches_post[0]
                else:
                    try:
                        json_data = post_response.json()
                        if 'url' in json_data:
                            link_final = json_data['url']
                    except:
                        pass

        # Se ainda não achou, salva o HTML para inspetoria
        if not link_final:
            os.makedirs("debug", exist_ok=True)
            with open("debug/response_html.html", "w", encoding="utf-8") as f:
                f.write(response.text)
            print("📄 HTML bruto salvo em 'debug/response_html.html' para análise.")

    except Exception as e:
        print(f"⚠️ Erro de execução: {e}")

    print("\n" + "=" * 80)
    if link_final:
        print(f"🎉 SUCESSO! LINK DIRETO EXTRAÍDO:")
        print(f"👉 {link_final}")
    else:
        print("❌ Não foi possível capturar o link automático nesta tentativa.")
    print("=" * 80)

if __name__ == "__main__":
    url_input = os.getenv("SHORT_URL", "").strip()
    if not url_input:
        print("❌ Nenhuma URL fornecida!")
        sys.exit(1)

    passar_encurtador(url_input)
