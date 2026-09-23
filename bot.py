import time
import re
import requests
from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor, as_completed

# Cabeçalhos de navegador reais para evitar bloqueios de Cloudflare e WAF no GitHub Actions
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
    'Accept-Language': 'pt-PT,pt;q=0.9,en-US;q=0.8,en;q=0.7',
    'Accept-Encoding': 'gzip, deflate, br',
    'Connection': 'keep-alive',
    'Upgrade-Insecure-Requests': '1',
    'Sec-Fetch-Dest': 'document',
    'Sec-Fetch-Mode': 'navigate',
    'Sec-Fetch-Site': 'none',
    'Sec-Fetch-User': '?1',
    'Cache-Control': 'max-age=0'
}

def criar_sessao():
    session = requests.Session()
    session.headers.update(HEADERS)
    return session

session = criar_sessao()

# --- 1. FONTE: SMSTOME ---
def raspar_smstome():
    numeros = []
    urls = ["https://smstome.com/country/usa", "https://smstome.com/country/canada", "https://smstome.com/"]
    for url in urls:
        try:
            res = session.get(url, timeout=10)
            if res.status_code == 200:
                soup = BeautifulSoup(res.text, 'html.parser')
                for a in soup.find_all('a', href=True):
                    href = a['href']
                    if '-phone-number' in href or '/country/' in href:
                        url_comp = href if href.startswith('http') else f"https://smstome.com{href}"
                        num_text = a.text.strip()
                        if url_comp not in [n['link'] for n in numeros] and 'smstome.com' in url_comp:
                            if any(c.isdigit() for c in num_text):
                                numeros.append({'numero': num_text, 'link': url_comp, 'fonte': 'SMSToMe'})
        except Exception:
            pass
    print(f"  ├─ SMSToMe: {len(numeros)} número(s) encontrado(s)")
    return numeros

# --- 2. FONTE: ANONYMSMS ---
def raspar_anonymsms():
    numeros = []
    try:
        url = "https://anonymsms.com/"
        res = session.get(url, timeout=10)
        if res.status_code == 200:
            soup = BeautifulSoup(res.text, 'html.parser')
            for a in soup.find_all('a', href=True):
                href = a['href']
                if '/number/' in href or '/usa-' in href or '/united-states-' in href:
                    url_comp = href if href.startswith('http') else f"https://anonymsms.com{href}"
                    num_text = a.text.strip()
                    if url_comp not in [n['link'] for n in numeros]:
                        numeros.append({'numero': num_text or 'AnonymSMS', 'link': url_comp, 'fonte': 'AnonymSMS'})
    except Exception:
        pass
    print(f"  ├─ AnonymSMS: {len(numeros)} número(s) encontrado(s)")
    return numeros

# --- 3. FONTE: TEMPSMSS ---
def raspar_tempsmss():
    numeros = []
    try:
        url = "https://tempsmss.com/"
        res = session.get(url, timeout=10)
        if res.status_code == 200:
            soup = BeautifulSoup(res.text, 'html.parser')
            for a in soup.find_all('a', href=True):
                href = a['href']
                if '/number/' in href or '/temp-' in href or 'phone' in href:
                    url_comp = href if href.startswith('http') else f"https://tempsmss.com{href}"
                    if url_comp not in [n['link'] for n in numeros] and url_comp != "https://tempsmss.com/":
                        numeros.append({'numero': a.text.strip() or 'TempSMSS', 'link': url_comp, 'fonte': 'TempSMSS'})
    except Exception:
        pass
    print(f"  ├─ TempSMSS: {len(numeros)} número(s) encontrado(s)")
    return numeros

# --- 4. FONTE: SMS24 ---
def raspar_sms24():
    numeros = []
    try:
        url = "https://sms24.me/en/countries/us"
        res = session.get(url, timeout=10)
        if res.status_code == 200:
            soup = BeautifulSoup(res.text, 'html.parser')
            for a in soup.find_all('a', href=True):
                href = a['href']
                if '/en/numbers/' in href or '/numbers/' in href:
                    url_comp = href if href.startswith('http') else f"https://sms24.me{href}"
                    if url_comp not in [n['link'] for n in numeros]:
                        numeros.append({'numero': a.text.strip() or 'SMS24', 'link': url_comp, 'fonte': 'SMS24.me'})
    except Exception:
        pass
    print(f"  ├─ SMS24.me: {len(numeros)} número(s) encontrado(s)")
    return numeros

# --- 5. FONTE: RECEIVE-SMSS ---
def raspar_receive_smss():
    numeros = []
    try:
        url = "https://receive-smss.com/"
        res = session.get(url, timeout=10)
        if res.status_code == 200:
            soup = BeautifulSoup(res.text, 'html.parser')
            for a in soup.find_all('a', href=True):
                href = a['href']
                if re.search(r'/\d+|-phone-number|/usa|/canada', href):
                    url_comp = href if href.startswith('http') else f"https://receive-smss.com{href}"
                    if url_comp not in [n['link'] for n in numeros] and url_comp != "https://receive-smss.com/":
                        numeros.append({'numero': a.text.strip() or 'Receive-SMSS', 'link': url_comp, 'fonte': 'Receive-SMSS'})
    except Exception:
        pass
    print(f"  ├─ Receive-SMSS: {len(numeros)} número(s) encontrado(s)")
    return numeros

# --- 6. FONTE: ONLINE-SMS ---
def raspar_online_sms():
    numeros = []
    try:
        url = "https://online-sms.org/"
        res = session.get(url, timeout=10)
        if res.status_code == 200:
            soup = BeautifulSoup(res.text, 'html.parser')
            for a in soup.find_all('a', href=True):
                href = a['href']
                if '/free-phone-number/' in href or '/real-' in href:
                    url_comp = href if href.startswith('http') else f"https://online-sms.org{href}"
                    if url_comp not in [n['link'] for n in numeros]:
                        numeros.append({'numero': a.text.strip() or 'Online-SMS', 'link': url_comp, 'fonte': 'Online-SMS'})
    except Exception:
        pass
    print(f"  ├─ Online-SMS: {len(numeros)} número(s) encontrado(s)")
    return numeros

# --- 7. FONTE: QUACKR ---
def raspar_quackr():
    numeros = []
    try:
        url = "https://quackr.io/temporary-numbers"
        res = session.get(url, timeout=10)
        if res.status_code == 200:
            soup = BeautifulSoup(res.text, 'html.parser')
            for a in soup.find_all('a', href=True):
                href = a['href']
                if '/temporary-numbers/' in href and len(href.split('/')) > 2:
                    url_comp = href if href.startswith('http') else f"https://quackr.io{href}"
                    if url_comp not in [n['link'] for n in numeros]:
                        numeros.append({'numero': a.text.strip() or 'Quackr', 'link': url_comp, 'fonte': 'Quackr'})
    except Exception:
        pass
    print(f"  ├─ Quackr: {len(numeros)} número(s) encontrado(s)")
    return numeros

# --- 8. FONTE: VEEPN ---
def raspar_veepn():
    numeros = []
    try:
        url = "https://veepn.com/pt/online-sms/usa/13513553580/"
        res = session.get(url, timeout=10)
        if res.status_code == 200:
            numeros.append({'numero': '+1 351 355 3580', 'link': url, 'fonte': 'VeePN'})
    except Exception:
        pass
    print(f"  ├─ VeePN: {len(numeros)} número(s) encontrado(s)")
    return numeros

# --- FILTRO PROFUNDO ANTI-QUEIMADO ---
def analisar_numero(item):
    link = item['link']
    try:
        res = session.get(link, timeout=8)
        if res.status_code != 200:
            return None
            
        txt = res.text.lower()
        # Conta registos do Google, YouTube ou códigos G-XXXXXX
        contagem = txt.count('google') + txt.count('youtube') + txt.count('g-')
        
        item['usos_google'] = contagem
        return item
    except Exception:
        return None

# --- ESCUTA DE SMS EM TEMPO REAL ---
def aguardar_codigo_sms(link_numero):
    print("\n⏳ [ESCUTA ATIVA INICIADA] A verificar receção do SMS do YouTube (de 3 em 3s)...")
    
    for tentativa in range(1, 41): # 40 tentativas = 2 minutos
        try:
            res = session.get(link_numero, timeout=5)
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
        
    print("\n\n❌ O SMS não foi recebido no tempo limite. Execute o workflow novamente!")
    return False

# --- EXECUÇÃO PRINCIPAL ---
if __name__ == "__main__":
    print("\n⚡ [MODO PROFUNDO - ANDROID 13] A iniciar varredura em 8 fontes de SMS...")
    
    todos_numeros = []
    
    with ThreadPoolExecutor(max_workers=8) as executor:
        tarefas = [
            executor.submit(raspar_smstome),
            executor.submit(raspar_anonymsms),
            executor.submit(raspar_tempsmss),
            executor.submit(raspar_sms24),
            executor.submit(raspar_receive_smss),
            executor.submit(raspar_online_sms),
            executor.submit(raspar_quackr),
            executor.submit(raspar_veepn)
        ]
        for t in as_completed(tarefas):
            todos_numeros.extend(t.result())
            
    # Remover URLs duplicadas
    numeros_unicos = []
    links_vistos = set()
    for item in todos_numeros:
        if item['link'] not in links_vistos:
            links_vistos.add(item['link'])
            numeros_unicos.append(item)

    print(f"\n🔍 Total de {len(numeros_unicos)} número(s) capturado(s). A iniciar verificação profunda...")
    
    cand_perfeito = None
    cand_utilizado = None
    
    idx = 0
    with ThreadPoolExecutor(max_workers=10) as executor:
        futuros = {executor.submit(analisar_numero, item): item for item in numeros_unicos}
        for futuro in as_completed(futuros):
            idx += 1
            res = futuro.result()
            if res:
                usos = res['usos_google']
                num_display = res['numero'] if len(res['numero']) < 25 else res['numero'][:22] + "..."
                print(f"  [{idx}/{len(numeros_unicos)}] {num_display} ({res['fonte']}) -> {usos} registo(s) Google")
                
                if usos == 0 and not cand_perfeito:
                    cand_perfeito = res
                elif usos == 1 and not cand_utilizado:
                    cand_utilizado = res

    # Escolhe o melhor número (prioridade para virgem 0/2, depois 1/2)
    escolhido = cand_perfeito if cand_perfeito else cand_utilizado

    if escolhido:
        status_texto = "🟢 VIRGEM (0/2 USOS)" if escolhido['usos_google'] == 0 else "🟡 UTILIZADO 1 VEZ (1/2 USOS)"
        
        print("\n" + "="*50)
        print(f"📱 NÚMERO SELECCIONADO: {escolhido['numero']}")
        print(f"🌐 FONTE: {escolhido['fonte']}")
        print(f"📊 STATUS: {status_texto}")
        print(f"🔗 LINK: {escolhido['link']}")
        print("="*50)
        print("\n👉 COPIE O NÚMERO ACIMA E COLE NO YOUTUBE AGORA!\n")
        
        aguardar_codigo_sms(escolhido['link'])
    else:
        print("\n❌ Todos os números encontrados têm 2 ou mais utilizações no Google. Execute o workflow novamente em instantes!")
