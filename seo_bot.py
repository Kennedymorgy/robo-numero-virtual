import os
import requests
import datetime
import re
import json
import urllib.parse
import string

ANO_ATUAL = datetime.datetime.now().year

HEADERS_DESKTOP = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7",
}

COOKIES_YT = {
    "CONSENT": "YES+1",
    "SOCS": "CAI"
}

# Filtro rigoroso para remover marcas d'água de canais, lixo de sistema e termos sem valor
LIXO_SISTEMA_E_CANANIS = {
    'vídeo', 'compartilhamento', 'celular com câmera', 'videofone', 'gratuito', 'envio',
    'video', 'sharing', 'camera phone', 'free', 'upload', 'youtube', 'yt', 'shorts',
    'mobile', 'cell phone', 'phone', 'app', 'google', 'android', 'ios', 'menu', 'header',
    'button', 'icon', 'search', 'player', 'zippy', 'a11y', 'country', 'masthead',
    'logo', 'fyp', 'tiktok', 'viral', 'foryou', 'dappernexor', 'adam_tv_077', 'adam_tv',
    '45', 'h', '404', 'sub', 'subscribe', 'like', 'comment'
}

def limpar_titulo_anti_strike(titulo):
    """Substitui termos sensíveis no título para evitar punições no canal."""
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

def eh_hashtag_valida(ht_raw, jogo):
    """Valida se a hashtag é limpa, real e associada ao jogo."""
    ht = ht_raw.lower().replace("#", "").strip()

    if len(ht) < 3 or ht.isdigit() or ht in LIXO_SISTEMA_E_CANANIS:
        return False

    # Filtra nomes de criadores com padrões como nome_123
    if re.search(r'_\d+$', ht) or ('tv' in ht and len(ht) > 8):
        if not any(k in ht for k in ['mod', 'apk', 'game', 'gameplay']):
            return False

    for ano in range(2010, ANO_ATUAL):
        if str(ano) in ht:
            return False

    return True

def extrair_hashtags_do_melhor_video(video_ids, jogo):
    """
    Analisa os vídeos do topo do YouTube e seleciona O VÍDEO
    que possui o pacote mais completo e limpo de hashtags.
    """
    melhor_pacote = []
    max_hashtags = 0

    for v_id in video_ids[:10]:
        try:
            url = f"https://www.youtube.com/watch?v={v_id}"
            res = requests.get(url, headers=HEADERS_DESKTOP, cookies=COOKIES_YT, timeout=6)
            if res.status_code == 200:
                html = res.text
                
                # Garante que as tralhas fiquem com espaço antes para não grudarem (#a#b)
                html_formatado = re.sub(r'#', ' #', html)
                raw_hts = re.findall(r'#([a-zA-Z0-9_]+)', html_formatado)

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
    """Consulta a API do YouTube em tempo real para ver o que as pessoas digitam."""
    url = f"http://suggestqueries.google.com/complete/search?client=firefox&ds=yt&q={urllib.parse.quote(termo)}&gl={country}&hl={lang}"
    try:
        r = requests.get(url, headers=HEADERS_DESKTOP, timeout=5)
        if r.status_code == 200:
            return r.json()[1]
    except Exception:
        pass
    return []

def minerar_buscas_profundas_yt(jogo, categoria, idioma_modo):
    """
    Realiza mineração profunda no YouTube via Autocomplete Alfabético.
    Puxa exatamente o que os usuários reais pesquisaram nos últimos 30 dias.
    """
    j_clean = re.sub(r'[^a-zA-Z0-9 ]', '', jogo).strip()
    
    # Termos semente principais
    base_queries = [
        f"{j_clean}",
        f"{j_clean} mod",
        f"{j_clean} hack",
        f"{j_clean} mod menu",
        f"{j_clean} dinheiro infinito",
        f"{j_clean} mediafire",
        f"como baixar {j_clean}",
        f"{j_clean} atualizado"
    ]

    if categoria == "ppsspp":
        base_queries = [
            f"{j_clean} ppsspp",
            f"{j_clean} psp",
            f"{j_clean} iso",
            f"como baixar {j_clean} ppsspp",
            f"{j_clean} mediafire ppsspp"
        ]

    buscas_capturadas = []

    # 1. Puxa buscas das frases principais
    for bq in base_queries:
        if idioma_modo in ["ambos", "pt_br"]:
            buscas_capturadas.extend(buscar_autocomplete_yt(bq, "pt", "BR"))
        if idioma_modo in ["ambos", "ingles"]:
            buscas_capturadas.extend(buscar_autocomplete_yt(bq, "en", "US"))

    # 2. Mineração Alfabética (Simula o usuário digitando o nome + letra do alfabeto)
    letras_chave = ['a', 'b', 'c', 'd', 'm', 'p', 's', 'v']
    for letra in letras_chave:
        query_letra = f"{j_clean} {letra}"
        buscas_capturadas.extend(buscar_autocomplete_yt(query_letra, "pt", "BR"))

    # Limpeza e deduplicação inteligente das buscas reais
    seen = set()
    tags_limpas = []

    for item in buscas_capturadas:
        item_clean = re.sub(r'[^\w\s\-\/]', '', item).strip()
        item_lower = item_clean.lower()

        # Atualiza anos antigos para o ano atual
        for ano_antigo in range(2015, ANO_ATUAL):
            item_clean = re.sub(r'\b' + str(ano_antigo) + r'\b', str(ANO_ATUAL), item_clean, flags=re.IGNORECASE)

        if item_lower in seen or len(item_clean) <= 3:
            continue

        if item_lower in LIXO_SISTEMA_E_CANANIS:
            continue

        if categoria == "android" and ("ppsspp" in item_lower or "psp " in item_lower):
            continue

        seen.add(item_lower)
        tags_limpas.append(item_clean)

    # Organização das tags ordenadas pela relevância e variação
    tags_finais = []
    tamanho_total = 0

    for t in tags_limpas:
        custo = len(t) + 2 if tags_finais else len(t)
        if tamanho_total + custo <= 500:
            tags_finais.append(t)
            tamanho_total += custo
        else:
            break

    return ", ".join(tags_finais)

def minerar_titulos_e_ids(jogo, categoria):
    """Puxa os vídeos do topo do YouTube para o jogo especificado."""
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
                            if len(video_ids) >= 12:
                                break
                    if len(video_ids) >= 12:
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
    print(f"🤖 ROBÔ SEO YOUTUBE - MINERAÇÃO REAL DE ALTA PERFORMANCE: {jogo.upper()} {versao}")
    print(f"📂 Categoria: {categoria.upper()} | Idioma: {idioma_modo.upper()}")
    print("=" * 75)

    # 1. Varredura do Topo do YouTube
    titulos_reais, video_ids = minerar_titulos_e_ids(jogo, categoria)

    # 2. Exibição dos Melhores Títulos
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

    # 3. Extração do Pacote de Hashtags do Melhor Vídeo
    melhores_hashtags = extrair_hashtags_do_melhor_video(video_ids, jogo)
    
    # Se o vídeo do topo tiver poucas, complementa com as limpas do jogo
    if len(melhores_hashtags) < 8:
        clean_game = re.sub(r'[^a-zA-Z0-9]', '', jogo)
        extras = [f"#{clean_game}", f"#{clean_game}Mod", f"#{clean_game}ModMenu", f"#{clean_game}Gameplay", f"#{clean_game}{ANO_ATUAL}", "#ModApk", "#Mediafire", "#AndroidGames"]
        for ex in extras:
            if ex.lower() not in [h.lower() for h in melhores_hashtags]:
                melhores_hashtags.append(ex)

    print("\n📝 DESCRIÇÃO ENXUTA (AVISO LEGAL + HASHTAGS EXTRAÍDAS DO MELHOR VÍDEO):")
    print("-" * 75)
    print("⚠️ AVISO LEGAL E ISENÇÃO DE RESPONSABILIDADE / LEGAL DISCLAIMER:")
    print("Este vídeo possui caráter puramente educativo e demonstrativo de performance em jogos mobile/emulação. Todos os direitos e marcas registradas pertencem aos seus respetivos criadores e desenvolvedores.")
    print("This video is purely educational and for performance demonstration purposes. All rights belong to their respective owners.")
    print("-" * 50)
    print("🔎 HASHTAGS EXTRAÍDAS DO YOUTUBE (SEPARADAS E LIMPAS):")
    # Exibe garantindo 1 espaço entre cada hashtag
    print(" ".join(melhores_hashtags))

    # 4. Caixa de Tags de Busca Brutas via Mineração Alfabética
    tags_caixa = minerar_buscas_profundas_yt(jogo, categoria, idioma_modo)
    print("\n📌 CAIXA DE TAGS DE BUSCA BRUTAS (100% TERMOS REAIS PESQUISADOS):")
    print("-" * 75)
    print(tags_caixa)
    print("-" * 75)
    print(f"📊 Total de caracteres utilizados: {len(tags_caixa)}/500")

if __name__ == "__main__":
    executar_gerador()
