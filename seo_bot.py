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

# Termos genéricos e lixo de sistema do YouTube para Bloqueio Absoluto
LIXO_YOUTUBE = {
    'vídeo', 'compartilhamento', 'celular com câmera', 'videofone', 'gratuito', 'envio',
    'video', 'sharing', 'camera phone', 'free', 'upload', 'youtube', 'yt', 'shorts',
    'mobile', 'cell phone', 'phone', 'app', 'google', 'android', 'ios', 'menu', 'header',
    'button', 'icon', 'search', 'player', 'zippy', 'a11y', 'country', 'masthead'
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
    """Extrai as tags/keywords reais programadas no código fonte do vídeo."""
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
        
    tags_limpas = []
    for t in tags:
        t_clean = t.strip().lower()
        if t_clean not in LIXO_YOUTUBE and len(t_clean) > 2 and not eh_numero_isolado_invalido(t_clean):
            tags_limpas.append(t.strip())
            
    return tags_limpas

def eh_hashtag_valida(tag, jogo):
    """Valida se a hashtag é limpa e sem ruídos."""
    tag_clean = tag.lower().replace("#", "").strip()
    
    if tag_clean in LIXO_YOUTUBE:
        return False

    if re.match(r'^[0-9a-f]{3}$', tag_clean) or re.match(r'^[0-9a-f]{6}$', tag_clean):
        return False

    for ano in range(2010, ANO_ATUAL):
        if str(ano) in tag_clean:
            return False

    return True

def raspar_dados_top_videos(termo_busca, jogo, categoria):
    """
    Mineração dos TOP Vídeos:
    1. Raspa os títulos do Top 3 ranqueados no YouTube.
    2. Lê as tags ocultas dos TOP 3 vídeos (ex: sky ava, bull mod, cheto, etc).
    """
    query_encoded = urllib.parse.quote(termo_busca)
    url = f"https://www.youtube.com/results?search_query={query_encoded}"
    
    titulos_reais = []
    video_ids = []
    
    try:
        response = requests.get(url, headers=HEADERS_DESKTOP, cookies=COOKIES_YT, timeout=12)
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
                            
                            if len(video_ids) >= 6:
                                break
                    if len(video_ids) >= 6:
                        break
    except Exception as e:
        print(f"[-] Erro na busca inicial: {e}")

    tags_top3_videos = []
    hashtags_finais = []

    # Acessa os 3 primeiros vídeos para extrair as tags secretas do código-fonte
    for idx, v_id in enumerate(video_ids[:3]):
        try:
            v_url = f"https://www.youtube.com/watch?v={v_id}"
            v_res = requests.get(v_url, headers=HEADERS_DESKTOP, cookies=COOKIES_YT, timeout=10)
            if v_res.status_code == 200:
                html = v_res.text
                
                # Extrai keywords dos TOP 3
                kws = extrair_keywords_html_video(html)
                for k in kws:
                    if k.lower() not in [t.lower() for t in tags_top3_videos]:
                        tags_top3_videos.append(k)

                # Extrai Hashtags da descrição
                desc_match = re.search(r'"shortDescription":"(.*?)","isCrawlable"', html)
                texto_desc = desc_match.group(1) if desc_match else html
                texto_formatado = re.sub(r'#', ' #', texto_desc)
                tags_encontradas = re.findall(r'#([a-zA-Z0-9_]+)', texto_formatado)
                
                for ht in tags_encontradas:
                    if eh_hashtag_valida(ht, jogo):
                        ht_full = f"#{ht}"
                        if ht_full.lower() not in [h.lower() for h in hashtags_finais]:
                            hashtags_finais.append(ht_full)
        except Exception:
            pass

    return titulos_reais, hashtags_finais, tags_top3_videos

def buscar_autocomplete_yt(termo, lang="pt", country="BR"):
    """Sugestões de pesquisas reais do YouTube em tempo real."""
    url = f"http://suggestqueries.google.com/complete/search?client=firefox&ds=yt&q={urllib.parse.quote(termo)}&gl={country}&hl={lang}"
    try:
        r = requests.get(url, headers=HEADERS_DESKTOP, timeout=6)
        if r.status_code == 200:
            return r.json()[1]
    except Exception:
        pass
    return []

def eh_tag_valida_geral(tag, jogo, categoria):
    """Filtro rigoroso para garantir tags 100% limpas sem palavras genéricas do YT."""
    t_lower = tag.lower().strip()
    
    # Bloqueia lixo genérico
    if t_lower in LIXO_YOUTUBE:
        return False

    for ano in range(2010, ANO_ATUAL):
        if str(ano) in t_lower:
            return False

    if eh_numero_isolado_invalido(t_lower):
        return False

    if categoria == "android" and ("ppsspp" in t_lower or "psp" in t_lower):
        return False

    return True

def gerar_caixa_tags_brutas(jogo, versao, categoria, idioma_modo, tags_top3_videos):
    """Monta a caixa de tags priorizando as palavras-chave dos vídeos do topo."""
    termo_clean = re.sub(r'[^a-zA-Z0-9 ]', '', jogo).strip()
    
    sementes = [
        f"{termo_clean} mod apk",
        f"{termo_clean} mod menu",
        f"{termo_clean} dinheiro infinito",
        f"{termo_clean} atualizado",
        f"{termo_clean} mediafire",
        f"{termo_clean} mod",
    ]
    if categoria == "ppsspp":
        sementes = [
            f"{termo_clean} ppsspp",
            f"{termo_clean} iso ppsspp",
            f"{termo_clean} psp android"
        ]

    tags_auto = []
    for s in sementes:
        if idioma_modo in ["ambos", "pt_br"]:
            tags_auto.extend(buscar_autocomplete_yt(s, lang="pt", country="BR"))
        if idioma_modo in ["ambos", "ingles"]:
            tags_auto.extend(buscar_autocomplete_yt(s, lang="en", country="US"))

    # Junta: 1. Tags Reais extraídas do Top 3 -> 2. Tags Autocomplete do YouTube
    todas_candidatas = tags_top3_videos + tags_auto

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

    # Monta a string final travada em 500 caracteres
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
    jogo = os.getenv("GAME_NAME", "Avakin Life").strip()
    versao = os.getenv("GAME_VERSION", "").strip()
    categoria = os.getenv("CATEGORY", "android").strip().lower()
    idioma_modo = os.getenv("LANGUAGE_MODE", "ambos").strip().lower()

    termo_pesquisa = f"{jogo} mod apk" if categoria == "android" else f"{jogo} ppsspp"

    print("=" * 75)
    print(f"🤖 ROBÔ SEO ULTRA AVANÇADO YOUTUBE: {jogo.upper()} {versao}")
    print(f"📂 Categoria: {categoria.upper()} | Idioma: {idioma_modo.upper()}")
    print("=" * 75)

    titulos_reais, hashtags_desc, tags_top3_videos = raspar_dados_top_videos(termo_pesquisa, jogo, categoria)

    # 1. Títulos Top Rank
    print("\n🔥 TOP 3 TÍTULOS MAIS FORTES DO YOUTUBE (ANTI-STRIKE SEGURO):")
    print("-" * 75)
    if titulos_reais:
        for i, t in enumerate(titulos_reais[:3], 1):
            print(f"{i}. 🚀 {t}")
    else:
        v_str = f" {versao}" if versao else ""
        print(f"1. 🚀 {jogo.upper()}{v_str} MOD MENU SHOWCASE ATUALIZADO")
        print(f"2. 🔥 {jogo.upper()}{v_str} NOVO MOD APK MEDIAFIRE")
        print(f"3. ⚡ {jogo.upper()}{v_str} GAMEPLAY TUTORIAL COMPLETO")

    # 2. Descrição Limpa
    print("\n📝 DESCRIÇÃO ENXUTA (AVISO LEGAL + HASHTAGS EXTRAÍDAS):")
    print("-" * 75)
    print("⚠️ AVISO LEGAL E ISENÇÃO DE RESPONSABILIDADE / LEGAL DISCLAIMER:")
    print("Este vídeo possui caráter puramente educativo e demonstrativo de performance em jogos mobile/emulação. Todos os direitos e marcas registradas pertencem aos seus respetivos criadores e desenvolvedores.")
    print("This video is purely educational and for performance demonstration purposes. All rights belong to their respective owners.")
    print("-" * 50)
    print("🔎 HASHTAGS EXTRAÍDAS DO YOUTUBE:")
    if hashtags_desc:
        print(" ".join(hashtags_desc[:12]))
    else:
        clean_game = re.sub(r'[^a-zA-Z0-9]', '', jogo)
        print(f"#{clean_game} #{clean_game}Mod #{clean_game}Gameplay #{clean_game}{ANO_ATUAL} #AndroidGames #ModApk")

    # 3. Caixa de Tags de Busca Brutas
    tags_caixa = gerar_caixa_tags_brutas(jogo, versao, categoria, idioma_modo, tags_top3_videos)
    print("\n📌 CAIXA DE TAGS DE BUSCA BRUTAS (ATÉ 500 CARACTERES):")
    print("-" * 75)
    print(tags_caixa)
    print("-" * 75)
    print(f"📊 Total de caracteres utilizados: {len(tags_caixa)}/500")

if __name__ == "__main__":
    executar_gerador()
