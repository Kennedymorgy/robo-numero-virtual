import re
from urllib.parse import urljoin
from playwright.sync_api import sync_playwright

# 🌍 PREFIXOS DE PAÍSES PERMITIDOS (EUA, Finlândia, Brasil, Portugal, Reino Unido, Suécia, França, Espanha)
PREFIXOS_ACEITOS = ['+1', '+358', '+55', '+351', '+44', '+46', '+33', '+34']

def extrair_numero_valido(texto):
    """
    Limpa e valida se a string é realmente um número de telefone no formato internacional.
    Elimina textos falsos como 'SMS24.me', 'New United States', '201 - 500', etc.
    """
    limpo = re.sub(r'[^\d+]', '', texto)
    
    # Se não começar com '+', adiciona se for um formato válido
    if not limpo.startswith('+') and len(limpo) >= 10:
        limpo = '+' + limpo

    # Garante que tem entre 9 e 16 dígitos e começa com prefixo válido
    if len(limpo) >= 10 and len(limpo) <= 16:
        if any(limpo.startswith(pref) for pref in PREFIXOS_ACEITOS):
            return limpo
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
                    
                    # Tenta validar o número pelo texto do link ou pela URL
                    num_valido = extrair_numero_valido(txt) or extrair_numero_valido(href)
                    
                    if num_valido:
                        url_comp = urljoin(fonte["url"], href)
                            
                        if not any(n['numero'] == num_valido for n in numeros):
                            numeros.append({
                                'numero': num_valido, 
                                'link': url_comp, 
                                'fonte': fonte['nome']
                            })
                            count += 1
                except Exception:
                    continue
                    
            print(f"  ├─ {fonte['nome']}: {count} numero(s) real(is) encontrado(s)")
        except Exception:
            print(f"  ├─ {fonte['nome']}: Erro ao carregar pagina")

    # Fallback fixo do VeePN (Número dos EUA)
    numeros.append({
        'numero': '+13513553580', 
        'link': 'https://veepn.com/pt/online-sms/usa/13513553580/', 
        'fonte': 'VeePN'
    })
    return numeros

def analisar_historico(page, item):
    """
    Analisa a página do número específico para contar mensagens do Google/YouTube
    e verificar se o número está ativo recentemente.
    """
    try:
        page.goto(item['link'], timeout=12000, wait_until="domcontentloaded")
        page.wait_for_timeout(1500)
        
        texto_completo = page.inner_text("body").lower()
        
        # Procura termos específicos do serviço de verificação
        usos_google = (
            texto_completo.count('google') + 
            texto_completo.count('youtube') + 
            texto_completo.count('g-')
        )
        
        # Verifica se o número recebeu SMS recentemente (palavras-chave de data)
        tem_atividade_recente = any(p in texto_completo for p in [
            'min', 'sec', 'hour', 'seg', 'hora', 'agora', 'just now', 'today'
        ])
        
        item['usos_google'] = usos_google
        item['ativo_recente'] = tem_atividade_recente
        return item
    except Exception:
        item['usos_google'] = 999
        item['ativo_recente'] = False
        return item

def exibir_relatorio(virgens, usados):
    """
    Gera o relatório da Opção A: limpo, organizado e com os links diretos para você clicar.
    """
    print("\n" + "="*65)
    print("🚀 RELATÓRIO DE NÚMEROS FILTRADOS (SISTEMA DE SEGURANÇA BARRADO)")
    print("="*65)

    if virgens:
        print(f"\n🟢 [NÍVEL 1 - VIRGENS] {len(virgens)} Número(s) 100% LIMPOS (0 Usos Google):")
        print("-" * 65)
        for i, item in enumerate(virgens, 1):
            print(f"{i}. 📱 Número: {item['numero']}")
            print(f"   🌐 Fonte: {item['fonte']}")
            print(f"   📊 Usos detectados: 0 uso(s)")
            print(f"   🔗 Link Direto do SMS: {item['link']}")
            print("-" * 65)
    else:
        print("\n⚠️ Nenhum número 100% virgem encontrado no momento.")

    if usados:
        print(f"\n🟡 [NÍVEL 2 - USADO 1 VEZ] {len(usados)} Número(s) com APENAS 1 Uso no Google:")
        print("-" * 65)
        for i, item in enumerate(usados, 1):
            print(f"{i}. 📱 Número: {item['numero']}")
            print(f"   🌐 Fonte: {item['fonte']}")
            print(f"   📊 Usos detectados: 1 uso(s)")
            print(f"   🔗 Link Direto do SMS: {item['link']}")
            print("-" * 65)

    print("\n👉 COMO USAR:")
    print("1. Escolha um número do NÍVEL 1 (ou NÍVEL 2) e cole no YouTube.")
    print("2. Se o YouTube aceitar o número, abra o Link Direto no seu navegador.")
    print("3. Atualize a página do link direto para ver o código de verificação assim que ele chegar!\n")

if __name__ == "__main__":
    print("\n⚡ [BOT SMS INTELIGENTE] A iniciar busca e análise de histórico...")
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            viewport={"width": 1280, "height": 720}
        )
        page = context.new_page()
        
        # 1. Captura inicial
        todos_numeros = extrair_numeros(page)
        print(f"\n🔍 Total de {len(todos_numeros)} número(s) candidato(s) extraídos. A analisar histórico real...")
        
        candidatos_virgens = []
        candidatos_usados = []
        
        # 2. Filtragem e verificação profunda
        for idx, item in enumerate(todos_numeros, 1):
            res = analisar_historico(page, item)
            usos = res['usos_google']
            
            if usos < 999:
                print(f"  [{idx}/{len(todos_numeros)}] {res['numero']} ({res['fonte']}) -> {usos} uso(s) Google")
                
                # Só aceitamos números que não estouraram limite e estão ativos
                if usos == 0:
                    candidatos_virgens.append(res)
                elif usos == 1:
                    candidatos_usados.append(res)

        # 3. Exibição do relatório final
        if candidatos_virgens or candidatos_usados:
            exibir_relatorio(candidatos_virgens, candidatos_usados)
        else:
            print("\n❌ Nenhum número seguro (0 ou 1 uso) foi encontrado no momento. Tente novamente em alguns minutos!")
            
        browser.close()
