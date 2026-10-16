import os
import sys
import re
import time
from bs4 import BeautifulSoup
from curl_cffi import requests

def passar_encurtador_adlinkfly(url_encurtada):
    print("=" * 80)
    print(f"🔓 BURLANDO ENCURTADOR (ADLINKFLY / SHRTSLUG ENGINE)")
    print(f"🔗 URL Alvo: {url_encurtada}")
    print("=" * 80)

    link_final = None
    
    # Cria a sessão mantendo os cookies automaticamente entre as requisições
    session = requests.Session(impersonate="chrome120")
    
    domain_base = "/".join(url_encurtada.split("/")[:3])
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
        "Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.9,en;q=0.9",
        "Referer": url_encurtada,
        "Origin": domain_base
    }

    try:
        print("[1/4] Acessando a página inicial e capturando os cookies de sessão...")
        response = session.get(url_encurtada, headers=headers, timeout=30)
        
        if response.status_code != 200:
            print(f"❌ Erro HTTP {response.status_code}: A página bloqueou a conexão.")
            return

        print("[2/4] Aguardando o temporizador interno do encurtador...")
        time.sleep(8) # Tempo para os scripts de contagem liberarem o form

        soup = BeautifulSoup(response.text, 'html.parser')

        # Procura por links de download direto logo de cara no HTML inicial
        matches = re.findall(r'https?://(?:www\.)?(?:mediafire\.com|drive\.google\.com|mega\.nz|mega\.io)[^\s"\'<>]+', response.text)
        if matches:
            link_final = matches[0]

        # Se não achou direto, busca o formulário padrão do AdLinkFly
        if not link_final:
            form = soup.find('form')
            if form:
                action = form.get('action') or url_encurtada
                if not action.startswith('http'):
                    action = domain_base + (action if action.startswith('/') else '/' + action)

                # Extrai todos os campos ocultos (como _token de segurança)
                inputs = form.find_all('input')
                data = {}
                for inp in inputs:
                    name = inp.get('name')
                    value = inp.get('value', '')
                    if name:
                        data[name] = value

                print(f"[3/4] Submetendo formulário com tokens de sessão para: {action}")
                headers["Content-Type"] = "application/x-www-form-urlencoded"
                
                post_response = session.post(action, data=data, headers=headers, timeout=30)
                
                # Procura links na resposta do POST
                matches_post = re.findall(r'https?://(?:www\.)?(?:mediafire\.com|drive\.google\.com|mega\.nz|mega\.io)[^\s"\'<>]+', post_response.text)
                if matches_post:
                    link_final = matches_post[0]
                else:
                    # Tenta capturar redirecionamento via script JavaScript na resposta
                    soup_post = BeautifulSoup(post_response.text, 'html.parser')
                    for script in soup_post.find_all('script'):
                        if script.string:
                            js_match = re.search(r'(?:window\.location\.href|location\.replace)\s*=\s*["\'](https?://[^"\']+)["\']', script.string)
                            if js_match:
                                potential_url = js_match.group(1)
                                if not any(bad in potential_url for bad in ["shrtslug", "encurta", "adfly"]):
                                    link_final = potential_url
                                    break

        # Varredura profunda em todos os scripts da página se ainda persistir
        if not link_final:
            print("[4/4] Varredura profunda em blocos de script JavaScript...")
            for script in soup.find_all('script'):
                if script.string:
                    urls = re.findall(r'https?://[^\s"\'<>]+', script.string)
                    for u in urls:
                        if any(dom in u for dom in ["mediafire.com", "drive.google.com", "mega.nz", "mega.io"]):
                            link_final = u
                            break
                if link_final:
                    break

    except Exception as e:
        print(f"⚠️ Erro de execução: {e}")

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

    passar_encurtador_adlinkfly(url_input)
