import re
from urllib.parse import urljoin
from playwright.sync_api import sync_playwright

# 🌍 PREFIXOS DE PAÍSES PERMITIDOS
PREFIXOS_ACEITOS = ['+1', '+358', '+55', '+351', '+44', '+46', '+33', '+34']

def extrair_numero_valido(texto):
    """
    Valida e formata números no padrão internacional.
    Filtra textos falsos e categorias dos sites.
    """
    limpo = re.sub(r'[^\d+]', '', texto)
    if not limpo.startswith('+') and len(limpo) >= 10:
        limpo = '+' + limpo

    if 10 <= len(limpo) <= 16:
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
                    
            print(f"  ├─ {fonte['nome']}: {count} numero(s) encontrado(s)")
        except Exception:
            print(f"  ├─ {fonte['nome']}: Erro ao carregar pagina")

    # Fallback fixo do VeePN
    numeros.append({
        'numero': '+13513553580', 
        'link': 'https://veepn.com/pt/online-sms/usa/13513553580/', 
        'fonte': 'VeePN'
    })
    return numeros

def analisar_historico_profundo(page, item):
    """
    Analisa a fundo a página do número:
    - Busca códigos G-XXXXXX e menções a YouTube/Google/Verificação.
    - Avalia a quantidade total de SMS para saber se o número é NOVO/RECÉM-CRIADO.
    """
    try:
        page.goto(item['link'], timeout=12000, wait_until="domcontentloaded")
        page.wait_for_timeout(1500)
        
        texto_bruto = page.inner_text("body")
        texto_lower = texto_bruto.lower()
        
        # 1. Busca por padrões de verificação do Google/YouTube
        mencoes_directas = (
            texto_lower.count('youtube') + 
            texto_lower.count('google') + 
            texto_lower.count('g-')
        )
        
        # 2. Busca por códigos no formato 'G-123456' ou SMS típicos de validação
        codigos_g = len(re.findall(r'\bg-\d{5,6}\b', texto_lower))
        codigos_genericos = len(re.findall(r'\b(código|verification|code|verify)\b', texto_lower))
        
        total_alertas_yt = mencoes_directas + (codigos_g * 2)
        
        # 3. Estimativa de mensagens na página (se tiver pouca mensagem, o número é NOVO no site)
        linhas = [l for l in texto_bruto.split('\n') if len(l.strip()) > 10]
        total_sms_estimado = len(linhas)

        item['usos_youtube'] = total_alertas_yt
        item['total_sms_pagina'] = total_sms_estimado
        item['is_novo'] = total_sms_estimado < 40  # Poucas mensagens = número novo no site
        return item
    except Exception:
        item['usos_youtube'] = 999
        item['total_sms_pagina'] = 999
        item['is_novo'] = False
        return item

def exibir_relatorio(perfeitos, aceitaveis):
    print("\n" + "="*70)
    print("🚀 RELATÓRIO DE NÚMEROS FILTRADOS (FOCO EM VERIFICAÇÃO YOUTUBE)")
    print("="*70)

    if perfeitos:
        print(f"\n🟢 [NÍVEL 1 - RECOMENDADOS YOUTUBE] ({len(perfeitos)} Números Limpos/Novos):")
        print("   (Números sem registros de 'G-' ou 'YouTube' e recém-adicionados aos sites)")
        print("-" * 70)
        for i, item in enumerate(perfeitos, 1):
            tag_novo = "🔥 [NOVO NO SITE]" if item['is_novo'] else "✅ [HISTÓRICO LIMPO]"
            print(f"{i}. 📱 {item['numero']} {tag_novo}")
            print(f"   🌐 Fonte: {item['fonte']}")
            print(f"   📊 Registros de Verificação: {item['usos_youtube']}")
            print(f"   🔗 Link Direto: {item['link']}")
            print("-" * 70)
    else:
        print("\n⚠️ Nenhum número do Nível 1 encontrado nesta varredura.")

    if aceitaveis:
        print(f"\n🟡 [NÍVEL 2 - SEGUNDA OPÇÃO] ({len(aceitaveis)} Números com baixo uso):")
        print("-" * 70)
        for i, item in enumerate(aceitaveis, 1):
            print(f"{i}. 📱 {item['numero']}")
            print(f"   🌐 Fonte: {item['fonte']}")
            print(f"   📊 Registros de Verificação: {item['usos_youtube']}")
            print(f"   🔗 Link Direto: {item['link']}")
            print("-" * 70)

    print("\n💡 INSTRUÇÕES DE USO DA OPÇÃO A:")
    print("1. Escolha de preferência um número marcados como 🔥 [NOVO NO SITE] do NÍVEL 1.")
    print("2. Cole o número na verificação do YouTube.")
    print("3. Abrindo o Link Direto no navegador, atualize a página até o código chegar!")

if __name__ == "__main__":
    print("\n⚡ [BOT YOUTUBE SMS] A iniciar varredura e verificação de histórico de miniatura/canal...")
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            viewport={"width": 1280, "height": 720}
        )
        page = context.new_page()
        
        todos = extrair_numeros(page)
        print(f"\n🔍 Total de {len(todos)} candidato(s) extraídos. A analisar histórico específico de YouTube...")
        
        perfeitos = []
        aceitaveis = []
        
        for idx, item in enumerate(todos, 1):
            res = analisar_historico_profundo(page, item)
            usos = res['usos_youtube']
            
            if usos < 999:
                status = "FRESH/LIMPO" if usos == 0 else f"{usos} alerta(s)"
                print(f"  [{idx}/{len(todos)}] {res['numero']} ({res['fonte']}) -> {status}")
                
                # Se não tem nenhum uso do Google/YouTube, entra para o Nível 1
                if usos == 0:
                    perfeitos.append(res)
                elif usos <= 2 and res['is_novo']:
                    aceitaveis.append(res)

        # Ordena colocando os números mais NOVOS no topo da lista
        perfeitos.sort(key=lambda x: (not x['is_novo'], x['total_sms_pagina']))
        
        if perfeitos or aceitaveis:
            exibir_relatorio(perfeitos, aceitaveis)
        else:
            print("\n❌ Nenhum número seguro para o YouTube encontrado no momento. Execute novamente em alguns instantes!")
            
        browser.close()
