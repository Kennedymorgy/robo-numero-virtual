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

def eh_hashtag_valida(tag, jogo, categoria):
    """Filtra hashtags irrelevantes, ruídos ou anos desatualizados."""
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
    termos_nicho = {'mod', 'apk', 'modmenu', 'gameplay', 'update', 'download', 'game', 'android', 'ios', 'ppsspp', 'iso', 'mediafire', 'cheat', 'showcase', 'gaming', 'unlimited', 'line', 'aim'}

    tem_relacao_jogo = any(pj in tag_clean for pj in palavras_jogo)
    tem_relacao_nicho = any(tn in tag_clean for tn in termos_nicho)

    return tem_relacao_jogo or tem_relacao_nicho

def raspar_dados_top_videos(termo_busca, jogo, categoria):
    """
    Mineração Inteligente:
    1. Examina até 10 vídeos concorrentes no topo do ranking.
    2. Identifica o vídeo que possui a descrição MAIS CHEIA de hashtags relevantes.
    3. Extrai as tags internas secretas de busca.
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

    videos_com_hashtags = []
    tags_brutas_videos = []

    # Examina os vídeos em busca da descrição mais rica/cheia
    for v_id in video_ids[:8]:
        try:
            v_url = f"https://www.youtube.com/watch?v={v_id}"
            v_res = requests.get(v_url, headers=HEADERS_DESKTOP, cookies=COOKIES_YT, timeout=8)
            if v_res.status_code == 200:
                html = v_res.text
                
                # 1. Keywords brutas do próprio vídeo
                kw_match = re.search(r'"keywords":\s*\[(.*?)\]', html)
                if kw_match:
                    raw_kws = kw_match.group(1)
                    kws = re.findall(r'"([^"]+)"', raw_kws)
                    for k in kws:
                        k_clean = k.strip()
                        if len(k_clean) > 2 and eh_tag_busca_bruta(k_clean, jogo, categoria):
                            if k_clean.lower() not in [t.lower() for t in tags_brutas_videos]:
                                tags_brutas_videos.append(k_clean)

                # 2. Hashtags da descrição do vídeo
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

    # Seleciona o conjunto de hashtags vindo do vídeo mais "cheio" / completo
    hashtags_finais = []
    if videos_com_hashtags:
        # Ordena para priorizar a lista com MAIOR quantidade de hashtags
        videos_com_hashtags.sort(key=lambda x: len(x), reverse=True)
        
        # Pega as hashtags do vídeo mais lotado e complementa com as dos outros se necessário
        seen_ht = set()
        for bloco in videos_com_hashtags:
            for ht in bloco:
                if ht.lower() not in seen_ht:
                    seen_ht.add(ht.lower())
                    hashtags_finais.append(ht)

    return titulos_reais, hashtags_finais, tags_brutas_videos

def buscar_autocomplete_yt(termo, lang="pt", country="BR"):
    """Consulta direta da API de pesquisas em tempo real do YouTube."""
    url = f"http://suggestqueries.google.com/complete/search?client=firefox&ds=yt&q={urllib.parse.quote(termo)}&gl={country}&hl={lang}"
    try:
        r = requests.get(url, headers=HEADERS_DESKTOP, timeout=5)
        if r.status_code == 200:
            return r.json()[1]
    except Exception:
        pass
    return []

def eh_tag_busca_bruta(tag, jogo, categoria):
    """Garante apenas termos de busca brutos de altíssimo interesse."""
    t_lower = tag.lower().strip()
    
    for ano in range(2010, ANO_ATUAL):
        if str(ano) in t_lower:
            return False

    termos_fracos = {'rosto', 'outfit', 'ideas', 'female', 'male', 'creation', 'zombie', 'skin', 'look', 'historias', 'edit'}
    if any(tf in t_lower for tf in termos_fracos) and not any(m in t_lower for m in ['mod', 'apk', 'hack', 'cheat', 'dinheiro', 'download', 'menu']):
        return False

    palavras_jogo = [p for p in re.findall(r'\w+', jogo.lower()) if len(p) > 2]
    tem_relacao = any(pj in t_lower for pj in palavras_jogo)
    
    if categoria == "android" and ("ppsspp" in t_lower or "psp" in t_lower):
        return False

    return tem_relacao

def gerar_caixa_tags_brutas(jogo, versao, categoria, idioma_modo, tags_extraidas_videos):
    """Constrói a caixa de tags combinando termos extraídos de topo com autocompletes reais."""
    termo_clean = re.sub(r'[^a-zA-Z0-9 ]', '', jogo).strip()
    v_clean = versao.strip()
    
    # Sementes ultra-expandidas de pesquisas reais no YouTube
    sementes = [
        f"{termo_clean} mod apk",
        f"{termo_clean} mod menu",
        f"{termo_clean} dinheiro infinito",
        f"{termo_clean} mod apk {ANO_ATUAL}",
        f"{termo_clean} mediafire",
        f"{termo_clean} link direto",
        f"{termo_clean} atualizado {ANO_ATUAL}",
        f"{termo_clean} download",
        f"{termo_clean} gameplay",
        f"{termo_clean} android",
    ]
    if v_clean:
        sementes.insert(0, f"{termo_clean} {v_clean}")
    if categoria == "ppsspp":
        sementes.extend([f"{termo_clean} ppsspp", f"{termo_clean} iso mediafire", f"{termo_clean} psp"])

    tags_auto = []
    for s in sementes:
        if idioma_modo in ["ambos", "pt_br"]:
            tags_auto.extend(buscar_autocomplete_yt(s, lang="pt", country="BR"))
        if idioma_modo in ["ambos", "ingles"]:
            tags_auto.extend(buscar_autocomplete_yt(s, lang="en", country="US"))

    todas_tags = tags_extraidas_videos + tags_auto

    seen = set()
    tags_prioritarias = []
    for t in todas_tags:
        t_clean = re.sub(r'[^\w\s\-\/]', '', t).strip()
        t_lower = t_clean.lower()
        if t_lower in seen or len(t_clean) <= 2:
            continue
        if eh_tag_busca_bruta(t_clean, jogo, categoria):
            seen.add(t_lower)
            tags_prioritarias.append(t_clean)

    # Preenchimento cirúrgico da caixa com limite de 500 caracteres
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
    jogo = os.getenv("GAME_NAME", "8 Ball Pool").strip()
    versao = os.getenv("GAME_VERSION", "").strip()
    categoria = os.getenv("CATEGORY", "android").strip().lower()
    idioma_modo = os.getenv("LANGUAGE_MODE", "ambos").strip().lower()

    termo_pesquisa = f"{jogo} mod apk" if categoria == "android" else f"{jogo} ppsspp"

    print("=" * 75)
    print(f"🤖 ROBÔ SEO ULTRA AVANÇADO YOUTUBE: {jogo.upper()} {versao}")
    print(f"📂 Categoria: {categoria.upper()} | Idioma: {idioma_modo.upper()}")
    print("=" * 75)

    titulos_reais, hashtags_desc, tags_brutas_videos = raspar_dados_top_videos(termo_pesquisa, jogo, categoria)

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

    # 2. Descrição Limpa (Aviso Legal + Hashtags do Vídeo Mais Cheio)
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
    tags_caixa = gerar_caixa_tags_brutas(jogo, versao, categoria, idioma_modo, tags_brutas_videos)
    print("\n📌 CAIXA DE TAGS DE BUSCA BRUTAS (ATÉ 500 CARACTERES):")
    print("-" * 75)
    print(tags_caixa)
    print("-" * 75)
    print(f"📊 Total de caracteres utilizados: {len(tags_caixa)}/500")

if __name__ == "__main__":
    executar_gerador()
