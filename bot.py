import time
import requests
from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor

# Simulação de cabeçalho do Chrome rodando num dispositivo Samsung com Android 13
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Linux; Android 13; SM-S918B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36',
    'Accept-Language': 'pt-PT,pt-BR;q=0.9,en-US;q=0.8,en;q=0.7'
}

# --- FONTE 1: QUACKR ---
def raspar_quackr():
    numeros = []
    try:
        url = "https://quackr.io/pt/"
        res = requests.get(url, headers=HEADERS, timeout=8)
        soup = BeautifulSoup(res.text, 'html.parser')
        
        for link in soup.find_all('a', href=True):
            href = link['href']
            if '/pt/temporary-numbers/' in href or '/temporary-numbers/' in href:
                url_completa = href if href.startswith('http') else f"https://quackr.io{href}"
                num_texto = link.text.strip().replace('\n', '')
                if url_completa not in [n['link'] for n in numeros]:
                    numeros.append({'numero': num_texto, 'link': url_completa, 'fonte': 'Quackr'})
    except Exception:
        pass
    return numeros

# --- FONTE 2: SMS-MAN ---
def raspar_smsman():
    numeros = []
    try:
        url = "https://sms-man.com/pt/free-numbers"
        res = requests.get(url, headers=HEADERS, timeout=8)
        soup = BeautifulSoup(res.text, 'html.parser')
        
        for card in soup.find_all('a', href=True):
            href = card['href']
            if '/free-numbers/' in href:
                url_completa = href if href.startswith('http') else f"https://sms-man.com{href}"
                num_texto = card.text.strip()
                if url_completa not in [n['link'] for n in numeros]:
                    numeros.append({'numero': num_texto, 'link': url_completa, 'fonte': 'SMS-Man'})
    except Exception:
        pass
    return numeros

# --- FONTE 3: VEEPN ---
def raspar_veepn():
    numeros = []
    try:
        url = "https://veepn.com/pt/online-sms/usa/13513553580/"
        res = requests.get(url, headers=HEADERS, timeout=8)
        numeros.append({
            'numero': '+1 351 355 3580', 
            'link': url, 
            'fonte': 'VeePN'
        })
    except Exception:
        pass
    return numeros

# --- FILTRO ANTI-QUEIMADO (ANALISA SE O GOOGLE JÁ USOU O NÚMERO) ---
def analisar_numero(item):
    link = item['link']
    try:
        res = requests.get(link, headers=HEADERS, timeout=8)
        txt = res.text.lower()
        
        # Conta envios do Google no histórico
        contagem = txt.count('google') + txt.count('youtube') + txt.count('g-')
        
        # Se recebeu 2 ou mais SMS, descarta
        if contagem >= 2:
            return None
        
        item['usos_google'] = contagem
        return item
    except Exception:
        return None

# --- ESCUTA DO CÓDIGO DE VERIFICAÇÃO ---
def aguardar_codigo_sms(link_numero):
    print("\n⏳ [ESCUTA ATIVA INICIADA] Procurando SMS do YouTube (checa a cada 3s)...")
    
    for _ in range(40): # Tenta por 2 minutos
        try:
            res = requests.get(link_numero, headers=HEADERS, timeout=5)
            soup = BeautifulSoup(res.text, 'html.parser')
            texto_pagina = soup.get_text()
            
            for linha in texto_pagina.split('\n'):
                linha_clean = linha.strip()
                if ("google" in linha_clean.lower() or "g-" in linha_clean.lower() or "youtube" in linha_clean.lower()) and any(c.isdigit() for c in linha_clean):
                    print("\n" + "🟢"*30)
                    print(f"🎉 CÓDIGO RECEBIDO: {linha_clean}")
                    print("🟢"*30 + "\n")
                    return True
        except Exception:
            pass
            
        time.sleep(3)
        print("...", end="", flush=True)
        
    print("\n\n❌ O SMS não apareceu no limite de tempo. Execute o robô novamente!")
    return False

# --- EXECUÇÃO DO BOT ---
if __name__ == "__main__":
    print("\n⚡ [MODO ANDROID 13] Iniciando varredura simultânea nos 3 sites...")
    
    todos_numeros = []
    
    # 1. Busca simultânea em paralelo
    with ThreadPoolExecutor(max_workers=3) as executor:
        f1 = executor.submit(raspar_quackr)
        f2 = executor.submit(raspar_smsman)
        f3 = executor.submit(raspar_veepn)
        
        todos_numeros.extend(f1.result())
        todos_numeros.extend(f2.result())
        todos_numeros.extend(f3.result())
        
    print(f"🔍 {len(todos_numeros)} número(s) encontrado(s). Filtrando os mais limpos...")
    
    # 2. Filtragem de histórico em paralelo
    numero_limpo = None
    with ThreadPoolExecutor(max_workers=5) as executor:
        resultados = list(executor.map(analisar_numero, todos_numeros))
        for res in resultados:
            if res is not None:
                numero_limpo = res
                break
                
    # 3. Retorno do resultado e abertura da escuta
    if numero_limpo:
        status_texto = "🟢 VIRGEM (0/2 USOS)" if numero_limpo['usos_google'] == 0 else "🟡 USADO 1 VEZ (1/2 USOS)"
        
        print("\n" + "="*50)
        print(f"📱 NÚMERO SELECIONADO: {numero_limpo['numero']}")
        print(f"🌐 FONTE: {numero_limpo['fonte']}")
        print(f"📊 STATUS: {status_texto}")
        print("="*50)
        print("\n👉 COPIE O NÚMERO ACIMA E COLE NO YOUTUBE AGORA!\n")
        
        aguardar_codigo_sms(numero_limpo['link'])
    else:
        print("\n❌ Nenhum número virgem disponível no momento. Tente rodar o workflow novamente em instantes.")
