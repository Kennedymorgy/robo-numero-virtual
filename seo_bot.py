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
    """Filtra palavras de alto risco nos títulos mantendo o SEO forte."""
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

def eh_numero_isolado_invalido(tag):
    """Elimina tags com números soltos ou lixo de raspagem como '036', '041', '43'."""
    tag_str = tag.strip()
    if re.search(r'\b\d{2,3}\b$', tag_str):
        if not re.search(r'\bv?\d+\.\d+', tag_str) and not re.search(r'\bv\d+', tag_str, re.IGNORECASE):
            return True
    return False

def extrair_keywords_html_video(html):
    """Extrai as tags/keywords reais programadas no código fonte dos 3 primeiros vídeos."""
    tags = []
    # Método 1: JSON "keywords":["tag1","tag2"]
    kw_match = re.search(r'"keywords":\s*\[(.*?)\]', html)
    if kw_match:
        raw_kws = kw_match.group(1)
        kws = re.findall(r'"([^"]+)"', raw_kws)
        tags.extend(kws)
    
    # Método 2: Meta Tag <meta name="keywords" content="...">
    meta_match = re.search(r'<meta\s+name="keywords"\s+content="([^"]+)"', html, re.IGNORECASE)
    if meta_match:
        meta_kws = [k.strip() for k in meta_match.group(1).split(',')]
        tags.extend(meta_kws)
        
    return tags

def eh_hashtag_valida(tag, jogo, categoria):
    """Valida se a hashtag é limpa e sem ruídos."""
    tag_clean = tag.lower().replace("#", "").strip()
    
    if re.match(r'^[0-9a-f]{3}$', tag_clean) or re.match(r'^[0-9a-f]{6}$', tag_clean):
        return False
        
    termos_invalidos_ui = {'menu', 'masthead', 'country', 'yt', 'a11y', 'youtube', 'search', 'logo', 'zippy', 'player', 'header', 'button', 'icon'}
    if tag_clean in termos_invalidos_ui:
        return False

    for ano in range(2010, ANO_ATUAL):
        if str(ano) in tag_clean:
            return False

    ruidos = {
        'ledlights', 'colors', 'pink', 'chromakey', 'mood', 'nosound', 'led', 'asmr',
        'nosoundvideo', 'nightlight', 'asmrlight', 'magenta', 'light', 'relax',
        'sbtbrasil', 'georgechabo', 'tiktok', 'viral', 'fyp', 'foryou', 'shorts'
    }
    if tag_clean in ruidos:
        return False

    palavras_jogo = [p for p in re.findall(r'\w+', jogo.lower()) if len(p) > 2]
    termos_nicho = {'mod', 'apk', 'modmenu', 'gameplay', 'update', 'download', 'game', 'android', 'ios', 'ppsspp', 'iso', 'mediafire', 'cheat', 'showcase', 'gaming', 'unlimited', 'line', 'aim', 'money'}

    tem_relacao_jogo = any(pj in tag_clean for pj in palavras_jogo) or len(palavras_jogo) == 0
    tem_relacao_nicho = any(tn in tag_clean for tn in termos_nicho)

    return tem_relacao_jogo or tem_relacao_nicho

def raspar_dados_top_videos(termo_busca, jogo, categoria):
    """
    Mineração de Elite:
    1. Raspa os TOP 3 VÍDEOS e extrai TODAS as tags/keywords internas que eles usaram.
    2. Garante a descrição mais rica e cheia de hashtags.
    """
    query_encoded = urllib.parse.quote(termo_busca)
    url = f"https://www.youtube.com/results?search_query={query_encoded}"
    
    titulos_reais = []
    video_ids = []
    
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
                            
                            if title and len(title) > 8 and title not in titulos_reais:
                                titulos_reais.append(limpar_titulo_anti_strike(title))
                                if v_id:
                                    video_ids.append(v_id)
                            
                            if len(video_ids) >= 10:
                                break
                    if len(video_ids) >= 10:
                        break
    except Exception as e:
        print(f"[-] Erro na busca inicial: {e}")

    tags_top3_videos = []
    videos_com_hashtags = []

    # Raspa cirurgicamente os TOP 3 VÍDEOS para extrair as palavras-chave reais
    for idx, v_id in enumerate(video_ids[:8]):
        try:
            v_url = f"https://www.youtube.com/watch?v={v_id}"
            v_res = requests.get(v_url, headers=HEADERS_DESKTOP, cookies=COOKIES_YT, timeout=8)
            if v_res.status_code == 200:
                html = v_res.text
                
                # 1. Keywords reais dos TOP 3 Vídeos
                if idx < 3:
                    kws = extrair_keywords_html_video(html)
                    for k in kws:
                        k_clean = k.strip()
                        if len(k_clean) > 2 and not eh_numero_isolado_invalido(k_clean):
                            if k_clean.lower() not in [t.lower() for t in tags_top3_videos]:
                                tags_top3_videos.append(k_clean)

                # 2. Hashtags da descrição
                desc_match = re.search(r'"shortDescription":"(.*?)","isCrawlable"', html)
                texto_desc = desc_match.group(1) if desc_match else html
                
                texto_formatado = re.sub(r'#', ' #', texto_desc)
                tags_encontradas = re.findall(r'#([a-zA-Z0-9_]+)', texto_formatado)
                
                ht_validas_video = []
                for ht in tags_encontradas:
                    if eh_hashtag_valida(ht, jogo, categoria):
                        ht_full = f"#{ht}"
                        if ht_full.lower() not in [h.lower() for h in ht_validas_video]:
                            ht_validas_video.append(ht_full)
                
                if ht_validas_video:
                    videos_com_hashtags.append(ht_validas_video)
        except Exception:
            pass

    hashtags_finais = []
    if videos_com_hashtags:
        videos_com_hashtags.sort(key=lambda x: len(x), reverse=True)
        seen_ht = set()
        for bloco in videos_com_hashtags:
            for ht in bloco:
                if ht.lower() not in seen_ht:
                    seen_ht.add(ht.lower())
                    hashtags_finais.append(ht)

    return titulos_reais, hashtags_finais, tags_top3_videos

def buscar_autocomplete_yt(termo, lang="pt", country="BR"):
    """API de sugestões de pesquisas em tempo real do YouTube."""
    url = f"http://suggestqueries.google.com/complete/search?client=firefox&ds=yt&q={urllib.parse.quote(termo)}&gl={country}&hl={lang}"
    try:
        r = requests.get(url, headers=HEADERS_DESKTOP, timeout=5)
        if r.status_code == 200:
            return r.json()[1]
    except Exception:
        pass
    return []

def eh_tag_valida_geral(tag, jogo, categoria):
    """Filtro final para garantir que apenas tags limpas e sem erros entrem na caixa."""
    t_lower = tag.lower().strip()
    
    # Remove anos desatualizados
    for ano in range(2010, ANO_ATUAL):
        if str(ano) in t_lower:
            return False

    # Remove números bizarros soltos
    if eh_numero_isolado_invalido(t_lower):
        return False

    if categoria == "android" and ("ppsspp" in t_lower or "psp" in t_lower):
        return False

    return True

def gerar_tags_fallback_blindadas(jogo, versao, categoria):
    """Garante 100% que a caixa NUNCA fique em 0/500 caracteres para nenhum jogo."""
    j_clean = re.sub(r'[^a-zA-Z0-9 ]', '', jogo).strip().lower()
    v_clean = versao.strip().lower()
    v_str = f" {v_clean}" if v_clean else ""

    if categoria == "ppsspp":
        return [
            f"{j_clean} ppsspp",
            f"{j_clean} iso ppsspp",
            f"{j_clean} ppsspp download",
            f"{j_clean} iso mediafire",
            f"{j_clean} psp android",
            f"{j_clean} ppsspp {ANO_ATUAL}",
            f"{j_clean} ppsspp brasil",
            f"{j_clean} iso altamente compactado",
            f"{j_clean} ppsspp gameplay",
            f"{j_clean} ppsspp cheats",
            f"{j_clean} iso psp google drive",
            f"{j_clean} ppsspp melhores graficos"
        ]
    else:
        return [
            f"{j_clean} mod apk",
            f"{j_clean} mod menu",
            f"{j_clean} dinheiro infinito",
            f"{j_clean} mod apk {ANO_ATUAL}",
            f"{j_clean} mod apk mediafire",
            f"{j_clean} mod menu {ANO_ATUAL}",
            f"{j_clean} mod apk atualizado",
            f"{j_clean} mod apk link direto",
            f"{j_clean} mod apk download",
            f"{j_clean} gameplay android",
            f"{j_clean} mod apk tudo ilimitado",
            f"{j_clean}{v_str} mod apk",
            f"{j_clean}{v_str} mod menu",
            f"{j_clean} mod apk android",
            f"{j_clean} mod menu mediafire"
        ]

def gerar_caixa_tags_brutas(jogo, versao, categoria, idioma_modo, tags_top3_videos):
    """Mecanismo Inteligente para montar a caixa de 500 caracteres perfeita."""
    termo_clean = re.sub(r'[^a-zA-Z0-9 ]', '', jogo).strip()
    v_clean = versao.strip()
    
    sementes = [
        f"{termo_clean} mod apk",
        f"{termo_clean} mod menu",
        f"{termo_clean} dinheiro infinito",
        f"{termo_clean} mod apk {ANO_ATUAL}",
        f"{termo_clean} mediafire",
        f"{termo_clean} link direto",
        f"{termo_clean} atualizado",
        f"{termo_clean} download",
        f"{termo_clean} gameplay",
        f"{termo_clean}",
    ]
    if v_clean:
        sementes.insert(0, f"{termo_clean} {v_clean}")
    if categoria == "ppsspp":
        sementes = [
            f"{termo_clean} ppsspp",
            f"{termo_clean} iso ppsspp",
            f"{termo_clean} ppsspp mediafire",
            f"{termo_clean} psp android"
        ]

    tags_auto = []
    for s in sementes:
        if idioma_modo in ["ambos", "pt_br"]:
            tags_auto.extend(buscar_autocomplete_yt(s, lang="pt", country="BR"))
        if idioma_modo in ["ambos", "ingles"]:
            tags_auto.extend(buscar_autocomplete_yt(s, lang="en", country="US"))

    # Combina: 1. Tags do TOP 3 VÍDEOS -> 2. Autocomplete do YouTube -> 3. Fallback Premium
    fallback_tags = gerar_tags_fallback_blindadas(jogo, versao, categoria)
    todas_candidatas = tags_top3_videos + tags_auto + fallback_tags

    seen = set()
    tags_prioritarias = []
    for t in todas_candidatas:
        t_clean = re.sub(r'[^\w\s\-\/]', '', t).strip()
        t_lower = t_clean.lower()
        
        if t_lower in seen or len(t_clean) <= 2:
            continue
            
        if eh_tag_valida_geral(t_clean, jogo, categoria):
            seen.add(t_lower)
            tags_prioritarias.append(t_clean)

    # Preenchimento cirúrgico limite 500 caracteres
    tags_finais = []
    tamanho_total = 0
    for t in tags_prioritarias:
        custo = len(t) + 2 if tags_finais else len(t)
        if tamanho_total + custo <= 500:
            tags_finais.append(t)
            tamanho_total += custo
        else:
            break

    return ", ".join(tags_finais)

def executar_gerador():
    jogo = os.getenv("GAME_NAME", "BitLife BR").strip()
    versao = os.getenv("GAME_VERSION", "").strip()
    categoria = os.getenv("CATEGORY", "android").strip().lower()
    idioma_modo = os.getenv("LANGUAGE_MODE", "ambos").strip().lower()

    termo_pesquisa = f"{jogo} mod apk" if categoria == "android" else f"{jogo} ppsspp"

    print("=" * 75)
    print(f"🤖 ROBÔ SEO ULTRA AVANÇADO YOUTUBE: {jogo.upper()} {versao}")
    print(f"📂 Categoria: {categoria.upper()} | Idioma: {idioma_modo.upper()}")
    print("=" * 75)

    titulos_reais, hashtags_desc, tags_top3_videos = raspar_dados_top_videos(termo_pesquisa, jogo, categoria)

    # 1. Títulos
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

    # 2. Descrição Limpa
    print("\n📝 DESCRIÇÃO ENXUTA (AVISO LEGAL + HASHTAGS EXTRAÍDAS):")
    print("-" * 75)
    print("⚠️ AVISO LEGAL E ISENÇÃO DE RESPONSABILIDADE / LEGAL DISCLAIMER:")
    print("Este vídeo possui caráter puramente educativo e demonstrativo de performance em jogos mobile/emulação. Todos os direitos e marcas registradas pertencem aos seus respetivos criadores e desenvolvedores.")
    print("This video is purely educational and for performance demonstration purposes. All rights belong to their respective owners.")
    print("-" * 50)
    print("🔎 HASHTAGS EXTRAÍDAS DO YOUTUBE:")
    if hashtags_desc:
        print(" ".join(hashtags_desc))
    else:
        clean_game = re.sub(r'[^a-zA-Z0-9]', '', jogo)
        print(f"#{clean_game} #{clean_game}Mod #{clean_game}Gameplay #{clean_game}{ANO_ATUAL} #AndroidGames #ModApk")

    # 3. Caixa de Tags de Busca Brutas (Até 500 caracteres)
    tags_caixa = gerar_caixa_tags_brutas(jogo, versao, categoria, idioma_modo, tags_top3_videos)
    print("\n📌 CAIXA DE TAGS DE BUSCA BRUTAS (ATÉ 500 CARACTERES):")
    print("-" * 75)
    print(tags_caixa)
    print("-" * 75)
    print(f"📊 Total de caracteres utilizados: {len(tags_caixa)}/500")

if __name__ == "__main__":
    executar_gerador()
