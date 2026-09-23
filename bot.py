import re
from urllib.parse import urljoin
from playwright.sync_api import sync_playwright

# 🌍 PREFIXOS PERMITIDOS
PREFIXOS_ACEITOS = ['+1', '+358', '+55', '+351', '+44', '+46', '+33', '+34']

def extrair_numero_limpo(texto):
    """
    Extrai apenas os dígitos e o sinal de mais (+) para validar o formato internacional.
    """
    limpo = re.sub(r'[^\d+]', '', texto)
    if not limpo.startswith('+') and len(limpo) >= 10:
        limpo = '+' + limpo

    if 10 <= len(limpo) <= 16:
        if any(limpo.startswith(pref) for pref in PREFIXOS_ACEITOS):
            return limpo
    return None

def construir_link_direto(base_url, href, numero_limpo):
    """
    Garante que o link aponta diretamente para a página do SMS do número,
    evitando redirecionamentos para a página inicial (como acontecia no Quackr).
    """
    if not href or href == "#" or "javascript" in href:
        return None
        
    url_completa = urljoin(base_url, href)
    digitos_numero = re.sub(r'\D', '', numero_limpo)[-7:] # Pega os últimos 7 dígitos
    
    # O link precisa conter os dígitos do número para ser o link da caixa de SMS real
    if digitos_numero in url_completa:
        return url_completa
    return None

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
                    
                    num_valido = extrair_numero_limpo(txt) or extrair_numero_limpo(href)
                    
                    if num_valido:
                        link_direto = construir_link_direto(fonte["url"], href, num_valido)
                        
                        if link_direto and not any(n['numero'] == num_valido for n in numeros):
                            numeros.append({
                                'numero': num_valido, 
                                'link': link_direto, 
                                'fonte': fonte['nome']
                            })
                            count += 1
                except Exception:
                    continue
                    
            print(f"  ├─ {fonte['nome']}: {count} numero(s) com link direto valido")
        except Exception:
            print(f"  ├─ {fonte['nome']}: Erro ao carregar pagina")

    return numeros

def analisar_historico_youtube(page, item):
    """
    Analisa as mensagens recebidas no número para contar usos do Google/YouTube.
    """
    try:
        page.goto(item['link'], timeout=12000, wait_until="domcontentloaded")
        page.wait_for_timeout(1500)
        
        texto_completo = page.inner_text("body").lower()
        
        # Procura por códigos de validação específicos do Google/YouTube
        mencoes_directas = (
            texto_completo.count('youtube') + 
            texto_completo.count('google')
        )
        codigos_g = len(re.findall(r'\bg-\d{5,6}\b', texto_completo))
        
        total_usos = mencoes_directas + codigos_g
        
        item['usos_google'] = total_usos
        return item
    except Exception:
        item['usos_google'] = 999
        return item

def exibir_relatorio(numeros_validos):
    print("\n" + "="*70)
    print("🚀 RELATÓRIO DE NÚMEROS PRONTOS PARA O YOUTUBE (0 OU 1 USO)")
    print("="*70)

    if numeros_validos:
        for i, item in enumerate(numeros_validos, 1):
            usos = item['usos_google']
            status_tag = "🟢 [VIRGEM - 0/2 USOS]" if usos == 0 else "🟡 [1 USO - 1 VAGA RESTANTE]"
            
            print(f"{i}. 📱 {item['numero']} {status_tag}")
            print(f"   🌐 Fonte: {item['fonte']}")
            print(f"   📊 Verificações detectadas no histórico: {usos}")
            print(f"   🔗 Link Direto do SMS: {item['link']}")
            print("-" * 70)
    else:
        print("\n❌ Nenhum número com vaga disponível (0 ou 1 uso) encontrado nesta varredura.")

if __name__ == "__main__":
    print("\n⚡ [BOT YOUTUBE SMS] A iniciar varredura e validação...")
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            viewport={"width": 1280, "height": 720}
        )
        page = context.new_page()
        
        candidatos = extrair_numeros(page)
        print(f"\n🔍 Total de {len(candidatos)} número(s) com link direto válido. A verificar histórico...")
        
        numeros_aprovados = []
        
        for idx, item in enumerate(candidatos, 1):
            res = analisar_historico_youtube(page, item)
            usos = res['usos_google']
            
            # YouTube permite ATÉ 2 USOS POR ANO.
            # Portanto, 0 ou 1 uso ainda funcionam! 2 ou mais são descartados.
            if usos <= 1:
                numeros_aprovados.append(res)
                print(f"  ├─ 🟢 [APROVADO] {res['numero']} ({res['fonte']}) -> {usos} uso(s)")
            else:
                print(f"  ├─ 🔴 [BLOQUEADO] {res['numero']} ({res['fonte']}) -> {usos} uso(s) (Limite estourado)")

        # Ordena colocando os de 0 usos primeiro, depois os de 1 uso
        numeros_aprovados.sort(key=lambda x: x['usos_google'])
        
        exibir_relatorio(numeros_aprovados)
        browser.close()
