import re
from urllib.parse import urljoin
from playwright.sync_api import sync_playwright

# 🌍 PREFIXOS PERMITIDOS
PREFIXOS_ACEITOS = ['+1', '+358', '+55', '+351', '+44', '+46', '+33', '+34']

def extrair_numero_valido(texto):
    limpo = re.sub(r'[^\d+]', '', texto)
    if not limpo.startswith('+') and len(limpo) >= 10:
        limpo = '+' + limpo

    if 10 <= len(limpo) <= 16:
        if any(limpo.startswith(pref) for pref in PREFIXOS_ACEITOS):
            return limpo
    return None

def calcular_idade_em_minutos(texto):
    """
    Identifica há quanto tempo o número foi ADICIONADO ao site.
    Retorna o tempo em minutos.
    """
    texto_lower = texto.lower()
    
    # Procura por padrões como: "added 10 mins ago", "15 minutes ago", "2 hours ago", "há 10 min"
    match_min = re.search(r'(\d+)\s*(min|minute|minuto)s?\b', texto_lower)
    match_hor = re.search(r'(\d+)\s*(hour|hora|hr)s?\b', texto_lower)
    match_day = re.search(r'(\d+)\s*(day|dia)s?\b', texto_lower)

    if match_min:
        return int(match_min.group(1))
    elif match_hor:
        return int(match_hor.group(1)) * 60
    elif match_day:
        return int(match_day.group(1)) * 1440
    
    # Se disser "just now" ou "agora"
    if any(p in texto_lower for p in ['just now', 'agora', 'new', 'novo']):
        return 1
        
    return 999999  # Se não encontrar carimbo de tempo, assume que é antigo/desconhecido

def extrair_numeros(page):
    numeros = []
    fontes = [
        {"nome": "AnonymSMS", "url": "https://anonymsms.com/"},
        {"nome": "TempSMSS", "url": "https://tempsmss.com/"},
        {"nome": "Receive-SMSS", "url": "https://receive-smss.com/"},
        {"nome": "SMS24", "url": "https://sms24.me/en/countries/us"},
        {"nome": "SMSToMe", "url": "https://smstome.com/country/usa"},
        {"nome": "Quackr", "url": "https://quackr.io/temporary-numbers"}
    ]

    print("\n🌐 A varrer sites buscando NÚMEROS RECÉM-CRIADOS...")

    for fonte in fontes:
        try:
            page.goto(fonte["url"], timeout=15000, wait_until="domcontentloaded")
            page.wait_for_timeout(2000)
            
            # Captura elementos de bloco/cards que contêm o número e o tempo de publicação
            elementos = page.locator("a, div, article, li").all()
            count = 0
            
            for el in elementos:
                try:
                    txt = el.inner_text().strip()
                    href = el.get_attribute("href") or ""
                    
                    num_valido = extrair_numero_valido(txt) or extrair_numero_valido(href)
                    
                    if num_valido:
                        url_comp = urljoin(fonte["url"], href) if href else fonte["url"]
                        idade_min = calcular_idade_em_minutos(txt)
                        
                        if not any(n['numero'] == num_valido for n in numeros):
                            numeros.append({
                                'numero': num_valido, 
                                'link': url_comp, 
                                'fonte': fonte['nome'],
                                'idade_minutos': idade_min
                            })
                            count += 1
                except Exception:
                    continue
                    
            print(f"  ├─ {fonte['nome']}: {count} número(s) analisado(s)")
        except Exception:
            print(f"  ├─ {fonte['nome']}: Erro ao carregar página")

    return numeros

def analisar_historico_profundo(page, item):
    try:
        page.goto(item['link'], timeout=12000, wait_until="domcontentloaded")
        page.wait_for_timeout(1000)
        
        texto_bruto = page.inner_text("body")
        texto_lower = texto_bruto.lower()
        
        # Tenta pegar a idade na página interna do número caso não tenha pego na home
        if item['idade_minutos'] == 999999:
            item['idade_minutos'] = calcular_idade_em_minutos(texto_bruto)
            
        usos_google = (
            texto_lower.count('youtube') + 
            texto_lower.count('google') + 
            len(re.findall(r'\bg-\d{5,6}\b', texto_lower))
        )
        
        item['usos_google'] = usos_google
        return item
    except Exception:
        item['usos_google'] = 999
        return item

def exibir_relatorio(perfeitos):
    print("\n" + "="*70)
    print("🔥 RELATÓRIO: NÚMEROS RECÉM-ADICIONADOS (< 12 HORAS DE VIDA)")
    print("="*70)

    if perfeitos:
        for i, item in enumerate(perfeitos, 1):
            horas = item['idade_minutos'] // 60
            mins = item['idade_minutos'] % 60
            tempo_str = f"{horas}h {mins}m" if horas > 0 else f"{mins} min"
            
            print(f"{i}. 📱 {item['numero']} 🔥 [CRIADO HÁ: {tempo_str}]")
            print(f"   🌐 Fonte: {item['fonte']}")
            print(f"   📊 Registros Detectados: {item['usos_google']}")
            print(f"   🔗 Link Direto: {item['link']}")
            print("-" * 70)
    else:
        print("\n❌ NENHUM NÚMERO NOVO (< 12H) ENCONTRADO NO MOMENTO.")
        print("💡 Dica: Os sites atualizam números ao longo do dia. Tente rodar o bot mais tarde!")

if __name__ == "__main__":
    print("\n⚡ [BOT YOUTUBE INTELIGENTE v3] Filtrando apenas números NOVOS do dia...")
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            viewport={"width": 1280, "height": 720}
        )
        page = context.new_page()
        
        todos = extrair_numeros(page)
        print(f"\n🔍 Total de {len(todos)} candidatos. Filtrando por IDADE DE CRIAÇÃO e histórico...")
        
        filtrados_frescos = []
        
        for idx, item in enumerate(todos, 1):
            res = analisar_historico_profundo(page, item)
            
            # FILTRO RÍGIDO: Só aceita se tiver menos de 720 minutos (12 horas) e 0 usos de Google
            if res['idade_minutos'] <= 720 and res['usos_google'] == 0:
                filtrados_frescos.append(res)
                print(f"  ├─ 🟢 [ACEITO] {res['numero']} (Adicionado há {res['idade_minutos']} min)")
            else:
                print(f"  ├─ 🔴 [DESCARTADO/VELHO] {res['numero']} (Idade: {res['idade_minutos']} min | Usos: {res['usos_google']})")

        # Ordena colocando os números mais NOVOS em primeiro lugar
        filtrados_frescos.sort(key=lambda x: x['idade_minutos'])
        
        exibir_relatorio(filtrados_frescos)
        browser.close()
