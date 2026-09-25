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

# Bloqueio de termos de sistema, canais de terceiros e ruídos
LIXO_SISTEMA_E_CANANIS = {
    'vídeo', 'compartilhamento', 'celular com câmera', 'videofone', 'gratuito', 'envio',
    'video', 'sharing', 'camera phone', 'free', 'upload', 'youtube', 'yt', 'shorts',
    'mobile', 'cell phone', 'phone', 'app', 'google', 'android', 'ios', 'menu', 'header',
    'button', 'icon', 'search', 'player', 'zippy', 'a11y', 'country', 'masthead',
    'logo', 'fyp', 'tiktok', 'viral', 'foryou', 'dappernexor', 'adam_tv_077', 'adam_tv',
    '45', 'h', '404', 'sub', 'subscribe', 'like', 'comment'
}

def eh_hex_color(string):
    """Filtra vazamentos de cores CSS do HTML do YouTube (ex: fff, 0f0f0f, e3e3e3, FF0033)."""
    return bool(re.fullmatch(r'^[0-9a-fA-F]{3}$|^[0-9a-fA-F]{6}$|^[0-9a-fA-F]{8}$', string))

def limpar_titulo_anti_strike(titulo):
    """Higieniza termos sensíveis nos títulos para proteção contra avisos/strikes."""
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
    return titulo_limpo.strip()

def eh_hashtag_valida(ht_raw, jogo):
    """Garante que apenas hashtags reais do jogo passem pelo filtro."""
    ht = ht_raw.lower().replace("#", "").strip()

    if len(ht) < 3 or ht.isdigit() or ht in LIXO_SISTEMA_E_CANANIS:
        return False

    if eh_hex_color(ht):
        return False

    if re.search(r'_\d+$', ht) or ('tv' in ht and len(ht) > 8):
        if not any(k in ht for k in ['mod', 'apk', 'game', 'gameplay']):
            return False

    for ano in range(2010, ANO_ATUAL):
        if str(ano) in ht:
            return False

    return True

def extrair_hashtags_do_melhor_video(video_ids, jogo):
    """
    Scrape exclusivo da caixa de descrição do vídeo para evitar sujeira de CSS/HTML.
    Localiza o vídeo com maior volume de hashtags válidas.
    """
    melhor_pacote = []
    max_hashtags = 0

    for v_id in video_ids[:8]:
        try:
            url = f"https://www.youtube.com/watch?v={v_id}"
            res = requests.get(url, headers=HEADERS_DESKTOP, cookies=COOKIES_YT, timeout=6)
            if res.status_code == 200:
                html = res.text
                
                # Extrai estritamente o conteúdo da descrição do vídeo
                desc_match = re.search(r'"shortDescription":"(.*?)","isCrawlable"', html)
                texto_alvo = desc_match.group(1) if desc_match else ""
                
                if not texto_alvo:
                    meta_desc = re.search(r'<meta\s+name="description"\s+content="([^"]+)"', html, re.IGNORECASE)
                    texto_alvo = meta_desc.group(1) if meta_desc else ""

                # Corrige hashtags coladas (#a#b -> #a #b)
                texto_formatado = re.sub(r'#', ' #', texto_alvo)
                raw_hts = re.findall(r'#([a-zA-Z0-9_]+)', texto_formatado)

                hashtags_video = []
                for ht in raw_hts:
                    if eh_hashtag_valida(ht, jogo):
                        ht_clean = f"#{ht}"
                        if ht_clean.lower() not in [h.lower() for h in hashtags_video]:
                            hashtags_video.append(ht_clean)

                if len(hashtags_video) > max_hashtags:
                    max_hashtags = len(hashtags_video)
                    melhor_pacote = hashtags_video
        except Exception:
            pass

    return melhor_pacote

def buscar_autocomplete_yt(termo, lang="pt", country="BR"):
    """Consulta em tempo real o serviço de autocomplete do YouTube."""
    url = f"http://suggestqueries.google.com/complete/search?client=firefox&ds=yt&q={urllib.parse.quote(termo)}&gl={country}&hl={lang}"
    try:
        r = requests.get(url, headers=HEADERS_DESKTOP, timeout=5)
        if r.status_code == 200:
            return r.json()[1]
    except Exception:
        pass
    return []

# ==============================================================================
# SISTEMA DE TRIPLE-BOT (3 ENGINES EM CADEIA)
# ==============================================================================

def engine_1_keywords_html(video_ids):
    """BOT 1: Extrai keywords diretas programadas na estrutura interna do vídeo."""
    keywords = []
    for v_id in video_ids[:5]:
        try:
            url = f"https://www.youtube.com/watch?v={v_id}"
            res = requests.get(url, headers=HEADERS_DESKTOP, cookies=COOKIES_YT, timeout=5)
            if res.status_code == 200:
                html = res.text
                kw_match = re.search(r'"keywords":\s*\[(.*?)\]', html)
                if kw_match:
                    kws = re.findall(r'"([^"]+)"', kw_match.group(1))
                    keywords.extend(kws)
        except Exception:
            pass
    return keywords

def engine_2_autocomplete_deep(jogo, categoria, idioma_modo):
    """BOT 2: Executa varreduras de autocomplete focadas no intenção real do usuário."""
    j_clean = re.sub(r'[^a-zA-Z0-9 ]', '', jogo).strip()
    
    base_queries = [
        f"{j_clean} mod apk",
        f"{j_clean} mod menu",
        f"{j_clean} dinheiro infinito",
        f"{j_clean} mediafire",
        f"{j_clean} atualizado {ANO_ATUAL}",
        f"como baixar {j_clean} mod",
        f"{j_clean} download link",
        f"{j_clean} gameplay android"
    ]

    if categoria == "ppsspp":
        base_queries = [
            f"{j_clean} ppsspp iso",
            f"{j_clean} psp mediafire",
            f"como baixar {j_clean} ppsspp",
            f"{j_clean} psp android",
            f"{j_clean} iso altamente compactado"
        ]

    buscas = []
    for bq in base_queries:
        if idioma_modo in ["ambos", "pt_br"]:
            buscas.extend(buscar_autocomplete_yt(bq, "pt", "BR"))
        if idioma_modo in ["ambos", "ingles"]:
            buscas.extend(buscar_autocomplete_yt(bq, "en", "US"))

    return buscas

def engine_3_cruzador_e_validador(candidatas, jogo, categoria):
    """BOT 3: Valida, higieniza, elimina duplicatas e bloqueia termos irrelevantes."""
    seen = set()
    tags_aprovadas = []

    # Lista de bloqueio para pesquisas fora do nicho de mods/games
    termos_fora_de_foco = ['rosto', 'face ideas', 'outfit ideas', 'look', 'maquiagem', 'cabelo', 'male face', 'female face']

    for c in candidatas:
        c_clean = re.sub(r'[^\w\s\-\/]', '', c).strip()
        
        # Atualiza referências a anos anteriores para o ano atual
        for ano_antigo in range(2015, ANO_ATUAL):
            c_clean = re.sub(r'\b' + str(ano_antigo) + r'\b', str(ANO_ATUAL), c_clean, flags=re.IGNORECASE)

        c_lower = c_clean.lower()

        # Anti-duplicação estrita
        if c_lower in seen or len(c_clean) <= 3:
            continue

        # Bloqueio de lixo, cores hex e termos fora de foco
        if c_lower in LIXO_SISTEMA_E_CANANIS or eh_hex_color(c_lower):
            continue

        if any(tf in c_lower for tf in termos_fora_de_foco):
            continue

        if categoria == "android" and ("ppsspp" in c_lower or "psp " in c_lower):
            continue

        seen.add(c_lower)
        tags_aprovadas.append(c_clean)

    # Organização para preenchimento limite de 500 caracteres
    tags_finais = []
    tamanho_total = 0

    for t in tags_aprovadas:
        custo = len(t) + 2 if tags_finais else len(t)
        if tamanho_total + custo <= 500:
            tags_finais.append(t)
            tamanho_total += custo
        else:
            break

    return ", ".join(tags_finais)

def minerar_titulos_e_ids(jogo, categoria):
    """Coleta o topo do ranking de buscas do YouTube."""
    termo_busca = f"{jogo} mod apk" if categoria == "android" else f"{jogo} ppsspp"
    query_encoded = urllib.parse.quote(termo_busca)
    url = f"https://www.youtube.com/results?search_query={query_encoded}"

    titulos = []
    video_ids = []

    try:
        res = requests.get(url, headers=HEADERS_DESKTOP, cookies=COOKIES_YT, timeout=10)
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
                            
                            if title and len(title) > 8 and title not in titulos:
                                titulos.append(limpar_titulo_anti_strike(title))
                                if v_id:
                                    video_ids.append(v_id)
                            if len(titulos) >= 10:
                                break
                    if len(titulos) >= 10:
                        break
    except Exception as e:
        print(f"[-] Aviso na busca de vídeos: {e}")

    return titulos, video_ids

def executar_gerador():
    jogo = os.getenv("GAME_NAME", "Avakin Life").strip()
    versao = os.getenv("GAME_VERSION", "").strip()
    categoria = os.getenv("CATEGORY", "android").strip().lower()
    idioma_modo = os.getenv("LANGUAGE_MODE", "ambos").strip().lower()

    print("=" * 75)
    print(f"🤖 ROBÔ SEO YOUTUBE - SISTEMA TRIPLE BOT AUTOMÁTICO: {jogo.upper()} {versao}")
    print(f"📂 Categoria: {categoria.upper()} | Idioma: {idioma_modo.upper()}")
    print("=" * 75)

    # 1. Varredura do Topo do YouTube
    titulos_reais, video_ids = minerar_titulos_e_ids(jogo, categoria)

    # 2. TOP 4 TÍTULOS DOS 4 PRIMEIROS VÍDEOS
    print("\n🔥 TOP 4 TÍTULOS MAIS POTENTES DO YOUTUBE (ANTI-STRIKE SEGURO):")
    print("-" * 75)
    if len(titulos_reais) >= 4:
        for i, t in enumerate(titulos_reais[:4], 1):
            print(f"{i}. 🚀 {t}")
    else:
        v_str = f" {versao}" if versao else ""
        fallback_titulos = [
            f"{jogo.upper()}{v_str} MOD MENU SHOWCASE ATUALIZADO",
            f"{jogo.upper()}{v_str} NOVO MOD APK MEDIAFIRE",
            f"{jogo.upper()}{v_str} GAMEPLAY & TUTORIAL COMPLETO",
            f"{jogo.upper()}{v_str} UNLIMITED RESOURCES SHOWCASE"
        ]
        for i, t in enumerate(fallback_titulos[:4], 1):
            print(f"{i}. 🚀 {t}")

    # 3. EXTRAÇÃO DE HASHTAGS DA DESCRIÇÃO (100% LIMPAS E ISOLADAS)
    melhores_hashtags = extrair_hashtags_do_melhor_video(video_ids, jogo)

    print("\n📝 DESCRIÇÃO ENXUTA (AVISO LEGAL + HASHTAGS EXTRAÍDAS DO VÍDEO MAIS RICO):")
    print("-" * 75)
    print("⚠️ AVISO LEGAL E ISENÇÃO DE RESPONSABILIDADE / LEGAL DISCLAIMER:")
    print("Este vídeo possui caráter puramente educativo e demonstrativo de performance em jogos mobile/emulação. Todos os direitos e marcas registradas pertencem aos seus respetivos criadores e desenvolvedores.")
    print("This video is purely educational and for performance demonstration purposes. All rights belong to their respective owners.")
    print("-" * 50)
    print("🔎 HASHTAGS EXTRAÍDAS DO YOUTUBE (100% LIMPAS E ORGANIZADAS):")
    if melhores_hashtags:
        print(" ".join(melhores_hashtags))
    else:
        clean_game = re.sub(r'[^a-zA-Z0-9]', '', jogo)
        print(f"#{clean_game} #{clean_game}Mod #{clean_game}ModMenu #{clean_game}Gameplay #{clean_game}{ANO_ATUAL} #ModApk #Mediafire #AndroidGames")

    # 4. SISTEMA TRIPLE BOT PARA TAGS DE BUSCA BRUTAS
    raw_kws_bot1 = engine_1_keywords_html(video_ids)
    raw_kws_bot2 = engine_2_autocomplete_deep(jogo, categoria, idioma_modo)
    
    # O Bot 3 consolida, higieniza, desduplica e valida o resultado final
    candidatas_totais = raw_kws_bot1 + raw_kws_bot2
    tags_caixa_final = engine_3_cruzador_e_validador(candidatas_totais, jogo, categoria)

    print("\n📌 CAIXA DE TAGS DE BUSCA BRUTAS (SISTEMA TRIPLE-BOT - 100% REAIS E RELEVANTES):")
    print("-" * 75)
    print(tags_caixa_final)
    print("-" * 75)
    print(f"📊 Total de caracteres utilizados: {len(tags_caixa_final)}/500")

if __name__ == "__main__":
    executar_gerador()
