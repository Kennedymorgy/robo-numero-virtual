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

# Bloqueio rigoroso de lixo de sistema, canais de terceiros e marcas d'água
LIXO_SISTEMA_E_CANANIS = {
    'vídeo', 'compartilhamento', 'celular com câmera', 'videofone', 'gratuito', 'envio',
    'video', 'sharing', 'camera phone', 'free', 'upload', 'youtube', 'yt', 'shorts',
    'mobile', 'cell phone', 'phone', 'app', 'google', 'android', 'ios', 'menu', 'header',
    'button', 'icon', 'search', 'player', 'zippy', 'a11y', 'country', 'masthead',
    'logo', 'fyp', 'tiktok', 'viral', 'foryou', 'dappernexor', 'adam_tv_077', 'adam_tv',
    '45', 'h', '404', 'sub', 'subscribe', 'like', 'comment'
}

def limpar_titulo_anti_strike(titulo):
    """Filtra termos de alto risco no título sem perder o apelo de SEO."""
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

def eh_numero_ou_versao_invalida(tag):
    """Filtra fragmentos de versão antigos ou números quebrados soltos."""
    tag_str = tag.strip().lower()
    if re.search(r'\b\d{2,3}\b$', tag_str):
        if not re.search(r'\bv?\d+\.\d+', tag_str) and not re.search(r'\bv\d+', tag_str):
            return True
    return False

def eh_hashtag_valida_e_forte(ht_raw, jogo, categoria):
    """Garante que apenas hashtags reais e conectadas ao jogo sejam aceitas."""
    ht = ht_raw.lower().replace("#", "").strip()

    if len(ht) < 3 or ht.isdigit() or ht in LIXO_SISTEMA_E_CANANIS:
        return False

    if re.search(r'_\d+$', ht) or ('tv' in ht and len(ht) > 8):
        if not any(k in ht for k in ['mod', 'apk', 'game', 'gameplay']):
            return False

    for ano in range(2010, ANO_ATUAL):
        if str(ano) in ht:
            return False

    palavras_jogo = [p for p in re.findall(r'\w+', jogo.lower()) if len(p) > 2]
    termos_nicho = {
        'mod', 'apk', 'modmenu', 'gameplay', 'update', 'download', 'game', 'android', 'ios',
        'ppsspp', 'iso', 'mediafire', 'cheat', 'showcase', 'gaming', 'unlimited', 'money',
        'coins', 'gems', 'vip', 'skyava', 'skyavakin', 'bullmod', 'cheto', 'longlines', 'aimbot'
    }

    tem_relacao = any(pj in ht for pj in palavras_jogo) or any(tn in ht for tn in termos_nicho)
    return tem_relacao

def extrair_keywords_video(html):
    """Extrai as tags ocultas programadas no código HTML do vídeo."""
    tags = []
    kw_match = re.search(r'"keywords":\s*\[(.*?)\]', html)
    if kw_match:
        raw_kws = kw_match.group(1)
        kws = re.findall(r'"([^"]+)"', raw_kws)
        tags.extend(kws)
    
    meta_match = re.search(r'<meta\s+name="keywords"\s+content="([^"]+)"', html, re.IGNORECASE)
    if meta_match:
        meta_kws = [k.strip() for k in meta_match.group(1).split(',')]
        tags.extend(meta_kws)

    tags_limpas = []
    for t in tags:
        t_clean = t.strip()
        t_lower = t_clean.lower()
        if t_lower not in LIXO_SISTEMA_E_CANANIS and len(t_clean) > 2 and not eh_numero_ou_versao_invalida(t_clean):
            tags_limpas.append(t_clean)
            
    return tags_limpas

def buscar_autocomplete_yt(termo, lang="pt", country="BR"):
    """Consulta em tempo real na API do YouTube para capturar buscas em alta."""
    url = f"http://suggestqueries.google.com/complete/search?client=firefox&ds=yt&q={urllib.parse.quote(termo)}&gl={country}&hl={lang}"
    try:
        r = requests.get(url, headers=HEADERS_DESKTOP, timeout=6)
        if r.status_code == 200:
            return r.json()[1]
    except Exception:
        pass
    return []

def minerar_youtube_deep(jogo, categoria, idioma_modo):
    """
    Varre os vídeos do topo do YouTube:
    - Seleciona títulos relevantes
    - Coleta hashtags de até 12 vídeos
    - Extrai as palavras-chave ocultas dos vídeos no topo
    """
    termo_busca = f"{jogo} mod apk" if categoria == "android" else f"{jogo} ppsspp"
    query_encoded = urllib.parse.quote(termo_busca)
    url = f"https://www.youtube.com/results?search_query={query_encoded}"

    titulos_reais = []
    video_ids = []

    try:
        res = requests.get(url, headers=HEADERS_DESKTOP, cookies=COOKIES_YT, timeout=12)
        if res.status_code == 200:
            match = re.search(r'var ytInitialData = ({.*?});</script>', res.text)
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
                            if len(video_ids) >= 12:
                                break
                    if len(video_ids) >= 12:
                        break
    except Exception as e:
        print(f"[-] Erro ao realizar varredura no YouTube: {e}")

    todas_hashtags_coletadas = []
    keywords_top_videos = []

    for idx, v_id in enumerate(video_ids[:10]):
        try:
            v_url = f"https://www.youtube.com/watch?v={v_id}"
            v_res = requests.get(v_url, headers=HEADERS_DESKTOP, cookies=COOKIES_YT, timeout=8)
            if v_res.status_code == 200:
                html = v_res.text
                
                # Extrai palavras-chave ocultas dos 5 primeiros vídeos
                if idx < 5:
                    kws = extrair_keywords_video(html)
                    for k in kws:
                        if k.lower() not in [t.lower() for t in keywords_top_videos]:
                            keywords_top_videos.append(k)

                # Extrai e valida hashtags de descrição
                desc_match = re.search(r'"shortDescription":"(.*?)","isCrawlable"', html)
                texto_desc = desc_match.group(1) if desc_match else html
                texto_formatado = re.sub(r'#', ' #', texto_desc)
                hashtags = re.findall(r'#([a-zA-Z0-9_]+)', texto_formatado)

                for ht in hashtags:
                    if eh_hashtag_valida_e_forte(ht, jogo, categoria):
                        ht_full = f"#{ht}"
                        if ht_full.lower() not in [h.lower() for h in todas_hashtags_coletadas]:
                            todas_hashtags_coletadas.append(ht_full)
        except Exception:
            pass

    return titulos_reais, todas_hashtags_coletadas, keywords_top_videos

def gerar_hashtags_perfeitas(jogo, hashtags_extraidas):
    """Completa a lista até atingir cerca de 18 a 20 hashtags 100% limpas e focadas no jogo."""
    clean_game = re.sub(r'[^a-zA-Z0-9]', '', jogo)
    
    hashtags_base = [
        f"#{clean_game}", f"#{clean_game}Mod", f"#{clean_game}ModMenu", 
        f"#{clean_game}Gameplay", f"#{clean_game}{ANO_ATUAL}", f"#{clean_game}Update",
        f"#{clean_game}Android", f"#{clean_game}Download", "#ModApk", "#Mediafire",
        "#Gameplay", "#AndroidGames", "#ModMenu", "#UnlimitedMoney", "#Gaming",
        "#MobileGaming", f"#{clean_game}APK", f"#{clean_game}Hack"
    ]

    resultado = list(hashtags_extraidas)
    
    for hb in hashtags_base:
        if len(resultado) >= 20:
            break
        if hb.lower() not in [h.lower() for h in resultado]:
            resultado.append(hb)
            
    return resultado[:20]

def gerar_caixa_tags_brutas(jogo, versao, categoria, idioma_modo, keywords_top_videos):
    """Gera a caixa de até 500 caracteres variando termos de busca para evitar frases repetidas."""
    j_clean = re.sub(r'[^a-zA-Z0-9 ]', '', jogo).strip()
    v_clean = versao.strip()

    # Múltiplas sementes variadas para capturar pesquisas reais sem repetição engessada
    sementes = [
        f"{j_clean} mod menu",
        f"{j_clean} dinheiro infinito",
        f"como baixar {j_clean} mod",
        f"{j_clean} atualizado {ANO_ATUAL}",
        f"{j_clean} mediafire",
        f"{j_clean} gameplay android",
        f"{j_clean} apk mod",
        f"{j_clean} download link"
    ]
    
    if v_clean:
        sementes.insert(0, f"{j_clean} {v_clean}")

    if categoria == "ppsspp":
        sementes = [
            f"{j_clean} ppsspp iso",
            f"como baixar {j_clean} psp",
            f"{j_clean} ppsspp mediafire",
            f"{j_clean} android gameplay",
            f"{j_clean} iso compactado"
        ]

    tags_auto = []
    for s in sementes:
        if idioma_modo in ["ambos", "pt_br"]:
            tags_auto.extend(buscar_autocomplete_yt(s, lang="pt", country="BR"))
        if idioma_modo in ["ambos", "ingles"]:
            tags_auto.extend(buscar_autocomplete_yt(s, lang="en", country="US"))

    # Mistura as keywords extraídas dos top vídeos com o autocomplete
    candidatas = keywords_top_videos + tags_auto

    seen = set()
    tags_validas = []
    
    for c in candidatas:
        c_clean = re.sub(r'[^\w\s\-\/]', '', c).strip()
        
        # Atualiza anos antigos para o ano atual
        for ano_antigo in range(2015, ANO_ATUAL):
            c_clean = re.sub(r'\b' + str(ano_antigo) + r'\b', str(ANO_ATUAL), c_clean, flags=re.IGNORECASE)

        c_lower = c_clean.lower()

        if c_lower in seen or len(c_clean) <= 2:
            continue

        if c_lower in LIXO_SISTEMA_E_CANANIS or eh_numero_ou_versao_invalida(c_clean):
            continue

        if categoria == "android" and ("ppsspp" in c_lower or "psp " in c_lower):
            continue

        seen.add(c_lower)
        tags_validas.append(c_clean)

    # Montagem cirúrgica respeitando o limite de 500 caracteres
    tags_finais = []
    tamanho_total = 0
    for t in tags_validas:
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

    print("=" * 75)
    print(f"🤖 ROBÔ SEO YOUTUBE - MODO MINERAÇÃO INTELIGENTE: {jogo.upper()} {versao}")
    print(f"📂 Categoria: {categoria.upper()} | Idioma: {idioma_modo.upper()}")
    print("=" * 75)

    titulos_reais, hashtags_extraidas, keywords_top_videos = minerar_youtube_deep(jogo, categoria, idioma_modo)

    # 1. Títulos
    print("\n🔥 TOP 3 TÍTULOS MAIS POTENTES DO YOUTUBE (ANTI-STRIKE SEGURO):")
    print("-" * 75)
    if titulos_reais:
        for i, t in enumerate(titulos_reais[:3], 1):
            print(f"{i}. 🚀 {t}")
    else:
        v_str = f" {versao}" if versao else ""
        print(f"1. 🚀 {jogo.upper()}{v_str} MOD MENU SHOWCASE ATUALIZADO")
        print(f"2. 🔥 {jogo.upper()}{v_str} NOVO MOD APK MEDIAFIRE")
        print(f"3. ⚡ {jogo.upper()}{v_str} GAMEPLAY & TUTORIAL COMPLETO")

    # 2. Descrição Limpa com Hashtags Validadas (Até 20 hashtags)
    hashtags_finais = gerar_hashtags_perfeitas(jogo, hashtags_extraidas)
    
    print("\n📝 DESCRIÇÃO ENXUTA (AVISO LEGAL + HASHTAGS SELECIONADAS):")
    print("-" * 75)
    print("⚠️ AVISO LEGAL E ISENÇÃO DE RESPONSABILIDADE / LEGAL DISCLAIMER:")
    print("Este vídeo possui caráter puramente educativo e demonstrativo de performance em jogos mobile/emulação. Todos os direitos e marcas registradas pertencem aos seus respetivos criadores e desenvolvedores.")
    print("This video is purely educational and for performance demonstration purposes. All rights belong to their respective owners.")
    print("-" * 50)
    print("🔎 HASHTAGS EXTRAÍDAS DO YOUTUBE:")
    print(" ".join(hashtags_finais))

    # 3. Caixa de Tags de Busca Brutas (Variadas e sem repetição engessada)
    tags_caixa = gerar_caixa_tags_brutas(jogo, versao, categoria, idioma_modo, keywords_top_videos)
    print("\n📌 CAIXA DE TAGS DE BUSCA BRUTAS (ATÉ 500 CARACTERES):")
    print("-" * 75)
    print(tags_caixa)
    print("-" * 75)
    print(f"📊 Total de caracteres utilizados: {len(tags_caixa)}/500")

if __name__ == "__main__":
    executar_gerador()
