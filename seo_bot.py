import os
import requests
import datetime
import re
import json
import urllib.parse

ANO_ATUAL = datetime.datetime.now().year

HEADERS_DESKTOP = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7",
}

COOKIES_YT = {
    "CONSENT": "YES+1",
    "SOCS": "CAI"
}

def limpar_titulo_anti_strike(titulo):
    """
    Substitui palavras de alto risco por termos seguros e otimizados para SEO.
    Protege o canal contra diretrizes da comunidade sem perder o apelo do título.
    """
    substituicoes = {
        r'\bHACK\b': 'Showcase',
        r'\bHACKS\b': 'Gameplay',
        r'\bCHEAT\b': 'Features',
        r'\bCHEATS\b': 'Highlights',
        r'\bFREE MONEY\b': 'Unlimited Gems',
        r'\bFREE COINS\b': 'Max Resources',
        r'\bCRACK\b': 'Full Version',
        r'\bGENERATOR\b': 'Tool'
    }
    
    titulo_limpo = titulo
    for padrao, sub in substituicoes.items():
        titulo_limpo = re.sub(padrao, sub, titulo_limpo, flags=re.IGNORECASE)
    return titulo_limpo

def eh_codigo_css_ou_hex(tag):
    """Filtra códigos de cores (hex) e termos do código-fonte do YouTube."""
    tag_clean = tag.lower().replace("#", "").strip()
    # Verifica se é código Hexadecimal (ex: 0f0f0f, fff, 606060)
    if re.match(r'^[0-9a-f]{3}$', tag_clean) or re.match(r'^[0-9a-f]{6}$', tag_clean):
        return True
    
    termos_invalidos = {'menu', 'masthead', 'country', 'yt', 'a11y', 'youtube', 'search', 'logo', 'zippy', 'player', 'header', 'button', 'icon'}
    if tag_clean in termos_invalidos:
        return True
        
    return False

def raspar_youtube_real(termo_busca, categoria):
    """Entra no YouTube real, extrai os títulos reais e hashtags legítimas das descrições."""
    query_encoded = urllib.parse.quote(termo_busca)
    url = f"https://www.youtube.com/results?search_query={query_encoded}"
    
    titulos_reais = []
    video_ids = []
    hashtags_raspadas = []

    try:
        response = requests.get(url, headers=HEADERS_DESKTOP, cookies=COOKIES_YT, timeout=10)
        if response.status_code == 200:
            match = re.search(r'var ytInitialData = ({.*?});</script>', response.text)
            if match:
                data = json.loads(match.group(1))
                contents = data.get('contents', {}).get('twoColumnSearchResultsRenderer', {}).get('primaryContents', {}).get('sectionListRenderer', {}).get('contents', [])
                
                for section in contents:
                    item_list = section.get('itemSectionRenderer', {}).get('contents', [])
                    for item in item_list:
                        if 'videoRenderer' in item:
                            vr = item['videoRenderer']
                            title = vr.get('title', {}).get('runs', [{}])[0].get('text', '')
                            v_id = vr.get('videoId', '')
                            
                            if title and len(title) > 10 and title not in titulos_reais:
                                # Aplica o Filtro Anti-Strike no título extraído
                                titulo_seguro = limpar_titulo_anti_strike(title)
                                titulos_reais.append(titulo_seguro)
                                if v_id:
                                    video_ids.append(v_id)
                            
                            if len(titulos_reais) >= 3:
                                break
                    if len(titulos_reais) >= 3:
                        break
    except Exception as e:
        print(f"[-] Erro na varredura inicial: {e}")

    # Entra nos 3 vídeos do topo e extrai apenas as hashtags reais da descrição
    for v_id in video_ids[:3]:
        try:
            v_url = f"https://www.youtube.com/watch?v={v_id}"
            v_res = requests.get(v_url, headers=HEADERS_DESKTOP, cookies=COOKIES_YT, timeout=5)
            if v_res.status_code == 200:
                # Isola a descrição do vídeo para não pegar o CSS do site
                desc_match = re.search(r'"shortDescription":"(.*?)","isCrawlable"', v_res.text)
                texto_analise = desc_match.group(1) if desc_match else v_res.text
                
                # Separa hashtags grudadas (ex: #avakin#modapk -> #avakin #modapk)
                texto_formatado = re.sub(r'#', ' #', texto_analise)
                tags_brutas = re.findall(r'#([a-zA-Z0-9_]+)', texto_formatado)
                
                for tag in tags_brutas:
                    if eh_codigo_css_ou_hex(tag):
                        continue
                        
                    ht_clean = f"#{tag}"
                    ht_lower = ht_clean.lower()
                    
                    if categoria == "android" and ("ppsspp" in ht_lower or "psp" in ht_lower):
                        continue
                        
                    if len(tag) > 2 and ht_clean not in hashtags_raspadas:
                        hashtags_raspadas.append(ht_clean)
        except Exception:
            pass

    return titulos_reais, hashtags_raspadas

def buscar_autocomplete_yt(termo, lang="pt", country="BR"):
    """Puxa sugestões em tempo real do autocomplete do YouTube."""
    url = f"http://suggestqueries.google.com/complete/search?client=firefox&ds=yt&q={urllib.parse.quote(termo)}&gl={country}&hl={lang}"
    try:
        r = requests.get(url, headers=HEADERS_DESKTOP, timeout=5)
        if r.status_code == 200:
            return r.json()[1]
    except Exception:
        pass
    return []

def extrair_tags_busca_reais(jogo, versao, categoria, idioma_modo):
    """Gera caixa de tags com alta densidade (450 a 500 caracteres) através de varredura ampla."""
    termo_clean = re.sub(r'[^a-zA-Z0-9 ]', '', jogo).strip()
    v_clean = versao.strip()
    
    # 16 Variações de busca reais para garantir preenchimento total das tags
    sementes = [
        f"{termo_clean}",
        f"{termo_clean} mod apk",
        f"{termo_clean} mod menu",
        f"{termo_clean} {ANO_ATUAL}",
        f"{termo_clean} atualizado",
        f"{termo_clean} dinheiro infinito",
        f"{termo_clean} gameplay",
        f"{termo_clean} download mediafire",
        f"{termo_clean} android",
        f"{termo_clean} novo evento",
        f"{termo_clean} apk mod",
        f"{termo_clean} cheto",
        f"{termo_clean} long line",
        f"{termo_clean} xp booster",
    ]
    
    if v_clean:
        sementes.insert(0, f"{termo_clean} {v_clean}")

    if categoria == "ppsspp":
        sementes.extend([f"{termo_clean} ppsspp", f"{termo_clean} iso mediafire", f"{termo_clean} save data 100"])

    tags_coletadas = []
    for s in sementes:
        if idioma_modo in ["ambos", "pt_br"]:
            tags_coletadas.extend(buscar_autocomplete_yt(s, lang="pt", country="BR"))
        if idioma_modo in ["ambos", "ingles"]:
            tags_coletadas.extend(buscar_autocomplete_yt(s, lang="en", country="US"))

    # Remove duplicados mantendo a ordem dos termos mais buscados
    seen = set()
    tags_filtradas = []
    for t in tags_coletadas:
        t_lower = t.lower()
        if t_lower in seen or len(t) <= 3:
            continue
        if categoria == "android" and ("ppsspp" in t_lower or "psp" in t_lower):
            continue
        seen.add(t_lower)
        tags_filtradas.append(t)

    # Constrói a caixa respeitando o limite rigoroso de 500 caracteres
    tags_finais = []
    tamanho_total = 0
    for t in tags_filtradas:
        custo = len(t) + 2 if tags_finais else len(t)
        if tamanho_total + custo <= 500:
            tags_finais.append(t)
            tamanho_total += custo
        else:
            break

    return ", ".join(tags_finais)

def formatar_hashtags_finais(hashtags_raspadas, jogo, categoria):
    """Monta a lista com 20 hashtags organizadas."""
    clean_game = re.sub(r'[^a-zA-Z0-9]', '', jogo)
    
    tags_finais = [h for h in hashtags_raspadas if h.startswith('#')]
    
    tags_base = [
        f"#{clean_game}", f"#{clean_game}Mod", f"#{clean_game}ModApk", f"#{clean_game}{ANO_ATUAL}",
        f"#{clean_game}Gameplay", f"#{clean_game}Update", f"#{clean_game}Download",
        f"#{clean_game}Android", f"#{clean_game}ModMenu", "#AndroidGames", "#ModMenu",
        "#ModApk", "#UnlimitedMoney", "#Gaming", "#MobileGaming", "#Mediafire"
    ]
    
    if categoria == "ppsspp":
        tags_base.extend([f"#{clean_game}PPSSPP", "#PPSSPP", "#PSP", "#PPSSPPISO"])

    for tb in tags_base:
        if tb not in tags_finais:
            tags_finais.append(tb)

    return " ".join(tags_finais[:20])

def construir_descricao(jogo, versao, categoria, hashtags_str):
    site_url = "https://k-404modapk.blogspot.com"
    v_str = f" {versao}" if versao else ""
    
    desc = f"""🔥 PROCURANDO POR {jogo.upper()}{v_str}? VOCÊ ESTÁ NO LUGAR CERTO! 
🚀 LOOKING FOR {jogo.upper()}{v_str}? YOU ARE IN THE RIGHT PLACE!

--------------------------------------------------
🎮 BEM-VINDO(A) AO CANAL! / WELCOME TO THE CHANNEL!
Aperte o play e confira a apresentação mais completa e detalhada de {jogo.upper()}{v_str}! Gráficos incríveis, alta performance e recursos exclusivos rodando com 100% de fluidez.

Press play and check out the most complete and detailed gameplay of {jogo.upper()}{v_str}! Incredible graphics, top performance, and exclusive features running super smooth.

🌐 DOWNLOAD DIRETO & INFORMAÇÕES NO SITE OFICIAL / OFFICIAL SITE:
👉 {site_url}

✨ DESTAQUES DO CONTEÚDO / CONTENT HIGHLIGHTS:
• Otimização máxima de FPS e desempenho.
• Análise completa dos novos recursos e novidades.
• Compatibilidade total atualizada.
• Top FPS optimization and smooth performance.
• Full analysis of new features and updates.

--------------------------------------------------
🔎 HASHTAGS RELACIONADAS DO VÍDEO (EXTRAÍDAS DO YOUTUBE):
{hashtags_str}

--------------------------------------------------
⚠️ AVISO LEGAL E ISENÇÃO DE RESPONSABILIDADE / LEGAL DISCLAIMER:
Este vídeo possui caráter puramente educativo e demonstrativo de performance em jogos mobile/emulação. Todos os direitos e marcas registradas pertencem aos seus respetivos criadores e desenvolvedores.
This video is purely educational and for performance demonstration purposes. All rights belong to their respective owners.
--------------------------------------------------
"""
    return desc

def executar_gerador():
    jogo = os.getenv("GAME_NAME", "8 Ball Pool").strip()
    versao = os.getenv("GAME_VERSION", "").strip()
    categoria = os.getenv("CATEGORY", "android").strip().lower()
    idioma_modo = os.getenv("LANGUAGE_MODE", "ambos").strip().lower()

    termo_pesquisa = f"{jogo} mod apk" if categoria == "android" else f"{jogo} ppsspp"

    print("=" * 75)
    print(f"🤖 ROBÔ SEO INTELIGENTE YOUTUBE REAL: {jogo.upper()} {versao}")
    print(f"📂 Categoria: {categoria.upper()} | Idioma: {idioma_modo.upper()}")
    print("=" * 75)

    # 1. Raspagem do YouTube com Filtro Anti-Strike
    titulos_reais, hashtags_raspadas = raspar_youtube_real(termo_pesquisa, categoria)

    print("\n🔥 TOP 3 TÍTULOS REAIS DO YOUTUBE (COM FILTRO ANTI-STRIKE SEGURO):")
    print("-" * 75)
    if titulos_reais:
        for i, t in enumerate(titulos_reais[:3], 1):
            print(f"{i}. 🚀 {t}")
    else:
        v_str = f" {versao}" if versao else ""
        print(f"1. 🚀 {jogo.upper()}{v_str} MOD MENU SHOWCASE ATUALIZADO")
        print(f"2. 🔥 {jogo.upper()}{v_str} NOVO MOD APK MEDIAFIRE")
        print(f"3. ⚡ {jogo.upper()}{v_str} GAMEPLAY & TUTORIAL COMPLETO")

    # 2. Descrição e Hashtags
    hashtags_str = formatar_hashtags_finais(hashtags_raspadas, jogo, categoria)
    print("\n📝 DESCRIÇÃO COM HASHTAGS REAIS DO JOGO:")
    print("-" * 75)
    print(construir_descricao(jogo, versao, categoria, hashtags_str))

    # 3. Caixa de Tags de Busca
    tags_busca_caixa = extrair_tags_busca_reais(jogo, versao, categoria, idioma_modo)
    print("\n📌 CAIXA DE TAGS DE BUSCA REAIS (ATÉ 500 CARACTERES):")
    print("-" * 75)
    print(tags_busca_caixa)
    print("-" * 75)
    print(f"📊 Total de caracteres utilizados: {len(tags_busca_caixa)}/500")

if __name__ == "__main__":
    executar_gerador()
