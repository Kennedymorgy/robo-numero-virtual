import time
import requests
from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Linux; Android 13; SM-S918B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36',
    'Accept-Language': 'pt-PT,pt-BR;q=0.9,en-US;q=0.8,en;q=0.7'
}

# --- FONTE 1: RECEIVE-SMSS ---
def raspar_receive_smss():
    numeros = []
    try:
        url = "https://receive-smss.com/"
        res = requests.get(url, headers=HEADERS, timeout=8)
        if res.status_code == 200:
            soup = BeautifulSoup(res.text, 'html.parser')
            for a in soup.find_all('a', class_='number-boxes-item'):
                href = a.get('href', '')
                num_text = a.text.strip()
                if href:
                    url_comp = href if href.startswith('http') else f"https://receive-smss.com{href}"
                    numeros.append({'numero': num_text, 'link': url_comp, 'fonte': 'Receive-SMSS'})
    except Exception:
        pass
    print(f"  ├─ Receive-SMSS: {len(numeros)} número(s)")
    return numeros

# --- FONTE 2: ONLINE-SMS ---
def raspar_online_sms():
    numeros = []
    try:
        url = "https://online-sms.org/"
        res = requests.get(url, headers=HEADERS, timeout=8)
        if res.status_code == 200:
            soup = BeautifulSoup(res.text, 'html.parser')
            for a in soup.find_all('a', href=True):
                href = a['href']
                if '/free-phone-number/' in href or '/real-' in href:
                    url_comp = href if href.startswith('http') else f"https://online-sms.org{href}"
                    num_text = a.text.strip()
                    if url_comp not in [n['link'] for n in numeros]:
                        numeros.append({'numero': num_text or 'Online-SMS', 'link': url_comp, 'fonte': 'Online-SMS'})
    except Exception:
        pass
    print(f"  ├─ Online-SMS: {len(numeros)} número(s)")
    return numeros

# --- FONTE 3: QUACKR ---
def raspar_quackr():
    numeros = []
    try:
        url = "https://quackr.io/temporary-numbers"
        res = requests.get(url, headers=HEADERS, timeout=8)
        if res.status_code == 200:
            soup = BeautifulSoup(res.text, 'html.parser')
            for link in soup.find_all('a', href=True):
                href = link['href']
                if '/temporary-numbers/' in href and len(href.split('/')) > 2:
                    url_comp = href if href.startswith('http') else f"https://quackr.io{href}"
                    num_text = link.text.strip().replace('\n', '')
                    if url_comp not in [n['link'] for n in numeros]:
                        numeros.append({'numero': num_text, 'link': url_comp, 'fonte': 'Quackr'})
    except Exception:
        pass
    print(f"  ├─ Quackr: {len(numeros)} número(s)")
    return numeros

# --- FONTE 4: VEEPN ---
def raspar_veepn():
    numeros = []
    try:
        url = "https://veepn.com/pt/online-sms/usa/13513553580/"
        res = requests.get(url, headers=HEADERS, timeout=8)
        if res.status_code == 200:
            numeros.append({'numero': '+1 351 355 3580', 'link': url, 'fonte': 'VeePN'})
    except Exception:
        pass
    print(f"  ├─ VeePN: {len(numeros)} número(s)")
    return numeros

# --- FILTRO ANTI-QUEIMADO ---
def analisar_numero(item):
    link = item['link']
    try:
        res = requests.get(link, headers=HEADERS, timeout=8)
        if res.status_code != 200:
            return None
            
        txt = res.text.lower()
        contagem = txt.count('google') + txt.count('youtube') + txt.count('g-')
        
        # Descarta se tiver 2 ou mais SMS do Google
        if contagem >= 2:
            return None
        
        item['usos_google'] = contagem
        return item
    except Exception:
        return None

# --- ESCUTA DO CÓDIGO SMS ---
def aguardar_codigo_sms(link_numero):
    print("\n⏳ [ESCUTA ATIVA INICIADA] Procurando SMS do YouTube (checa a cada 3s)...")
    
    for _ in range(40): # Tenta por até 2 minutos
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
        
    print("\n\n❌ O SMS não apareceu no tempo limite. Execute o workflow novamente!")
    return False

# --- EXECUÇÃO PRINCIPAL ---
if __name__ == "__main__":
    print("\n⚡ [MODO ANDROID 13] Iniciando varredura simultânea...")
    
    todos_numeros = []
    
    with ThreadPoolExecutor(max_workers=4) as executor:
        f1 = executor.submit(raspar_receive_smss)
        f2 = executor.submit(raspar_online_sms)
        f3 = executor.submit(raspar_quackr)
        f4 = executor.submit(raspar_veepn)
        
        todos_numeros.extend(f1.result())
        todos_numeros.extend(f2.result())
        todos_numeros.extend(f3.result())
        todos_numeros.extend(f4.result())
        
    print(f"\n🔍 Total de {len(todos_numeros)} número(s) capturado(s). Filtrando histórico do Google...")
    
    numero_limpo = None
    with ThreadPoolExecutor(max_workers=5) as executor:
        resultados = list(executor.map(analisar_numero, todos_numeros))
        for res in resultados:
            if res is not None:
                numero_limpo = res
                break
                
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
        print("\n❌ Todos os números encontrados já possuem 2 ou mais usos do Google. Tente rodar o workflow novamente em instantes!")
