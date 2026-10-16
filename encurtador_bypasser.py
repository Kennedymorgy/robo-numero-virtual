import os
import sys
import re
import time
import json
from bs4 import BeautifulSoup
from curl_cffi import requests

def passar_encurtador_adlinkfly(url_encurtada):
    print("=" * 80)
    print(f"🔓 BURLANDO ENCURTADOR (ADLINKFLY / API ENGINE)")
    print(f"🔗 URL Alvo: {url_encurtada}")
    print("=" * 80)

    link_final = None
    
    # Cria a sessão mantendo os cookies automaticamente
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
        time.sleep(8) # Tempo para os scripts liberarem o formulário

        soup = BeautifulSoup(response.text, 'html.parser')

        # Procura por links de download direto no HTML inicial
        matches = re.findall(r'https?://(?:www\.)?(?:mediafire\.com|drive\.google\.com|mega\.nz|mega\.io)[^\s"\'<>]+', response.text)
        if matches:
            link_final = matches[0]

        # Se não achou direto, busca o formulário do AdLinkFly
        if not link_final:
            form = soup.find('form')
            if form:
                action = form.get('action') or url_encurtada
                if not action.startswith('http'):
                    action = domain_base + (action if action.startswith('/') else '/' + action)

                # Extrai os campos ocultos do formulário (tokens de segurança)
                inputs = form.find_all('input')
                data = {}
                for inp in inputs:
                    name = inp.get('name')
                    value = inp.get('value', '')
                    if name:
                        data[name] = value

                print(f"[3/4] Disparando requisição AJAX para a API do encurtador: {action}")
                
                # Adiciona o cabeçalho AJAX essencial para encurtadores AdLinkFly retornarem JSON
                headers["Content-Type"] = "application/x-www-form-urlencoded; charset=UTF-8"
                headers["X-Requested-With"] = "XMLHttpRequest"
                
                post_response = session.post(action, data=data, headers=headers, timeout=30)
                
                print(f"[4/4] Analisando resposta JSON/Texto do servidor...")
                
                # Tenta ler como JSON (padrão de retorno do AdLinkFly)
                try:
                    json_resp = post_response.json()
                    print(f"📦 Resposta da API recebida: {json.dumps(json_resp)}")
                    
                    # Procura chaves comuns onde o link final costuma vir guardado
                    for key in ['url', 'success_url', 'link', 'data']:
                        if key in json_resp and json_resp[key]:
                            val = json_resp[key]
                            if isinstance(val, str) and val.startswith('http'):
                                link_final = val
                                break
                    
                    # Se vier dentro de um objeto aninhado
                    if not link_final and 'message' in json_resp and isinstance(json_resp['message'], str):
                        msg_match = re.search(r'https?://[^\s"\'<>]+', json_resp['message'])
                        if msg_match:
                            link_final = msg_match.group(0)
                except Exception as json_err:
                    print(f"ℹ️ A resposta não veio em JSON puro. Analisando texto...")

                # Se o JSON não deu match, busca por regex na resposta do POST
                if not link_final:
                    matches_post = re.findall(r'https?://(?:www\.)?(?:mediafire\.com|drive\.google\.com|mega\.nz|mega\.io)[^\s"\'<>]+', post_response.text)
                    if matches_post:
                        link_final = matches_post[0]

        # Varredura final de segurança no HTML bruto se ainda não achar
        if not link_final:
            urls = re.findall(r'https?://[^\s"\'<>]+', response.text)
            for u in urls:
                if any(dom in u for dom in ["mediafire.com", "drive.google.com", "mega.nz", "mega.io"]):
                    link_final = u
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
