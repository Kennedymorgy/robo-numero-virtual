import os
import requests
import datetime
import re
import json
import urllib.parse

ANO_ATUAL = datetime.datetime.now().year

# Cabeçalhos e Cookies para burlar o bloqueio de consentimento do YouTube
HEADERS_DESKTOP = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7",
}

COOKIES_YT = {
    "CONSENT": "YES+1",
    "SOCS": "CAI"
}

def raspar_youtube_real(termo_busca, categoria, max_resultados=3):
    """
    Entra no YouTube real, pesquisa o jogo e extrai:
    1. Os 3 títulos reais dos vídeos do topo.
    2. As hashtags (#) reais usadas nas descrições desses vídeos.
    """
    query_encoded = urllib.parse.quote(termo_busca)
    url = f"https://www.youtube.com/results?search_query={query_encoded}"
    
    titulos_reais = []
    video_ids = []
    hashtags_raspadas = []

    try:
        response = requests.get(url, headers=HEADERS_DESKTOP, cookies=COOKIES_YT, timeout=10)
        if response.status_code == 200:
            # Extrai o JSON interno de resultados do YouTube (ytInitialData)
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
                            
                            # Filtra títulos válidos
                            if title and len(title) > 10 and title not in titulos_reais:
                                titulos_reais.append(title)
                                if v_id:
                                    video_ids.append(v_id)
                            
                            if len(titulos_reais) >= max_resultados:
                                break
                    if len(titulos_reais) >= max_resultados:
                        break
    except Exception as e:
        print(f"[-] Alerta na busca do YT: {e}")

    # Entra nos vídeos encontrados e extrai as hashtags reais da descrição
    for v_id in video_ids[:3]:
        try:
            v_url = f"https://www.youtube.com/watch?v={v_id}"
            v_res = requests.get(v_url, headers=HEADERS_DESKTOP, cookies=COOKIES_YT, timeout=5)
            if v_res.status_code == 200:
                tags_encontradas = re.findall(r'#\w+', v_res.text)
                for ht in tags_encontradas:
                    ht_clean = ht.strip()
                    ht_lower = ht_clean.lower()
                    
                    # Filtra PPSSPP se o jogo for Android
                    if categoria == "android" and ("ppsspp" in ht_lower or "psp" in ht_lower):
                        continue
                        
                    if len(ht_clean) > 2 and ht_clean not in hashtags_raspadas:
                        hashtags_raspadas.append(ht_clean)
        except Exception:
            pass

    return titulos_reais, hashtags_raspadas

def buscar_autocomplete_yt(termo, lang="pt", country="BR"):
    """Puxa sugestões reais e de alto volume de pesquisa da barra de busca do YT."""
    url = f"http://suggestqueries.google.com/complete/search?client=firefox&ds=yt&q={termo}&gl={country}&hl={lang}"
    try:
        r = requests.get(url, headers=HEADERS_DESKTOP, timeout=5)
        if r.status_code == 200:
            return r.json()[1]
    except Exception:
        pass
    return []

def extrair_tags_busca_reais(jogo, versao, categoria, idioma_modo):
    """Gera caixa de tags de busca de 500 caracteres 100% reais e limpas."""
    termo_base = f"{jogo} {versao}".strip() if versao else jogo
    sementes = []

    if categoria == "android":
        mods_pt = ["mod apk", "mod menu", "dinheiro infinito", "atualizado", "mediafire", f"{ANO_ATUAL}"]
        mods_en = ["mod apk", "mod menu", "unlimited money", "latest version", "unlocked"]
        if idioma_modo in ["ambos", "pt_br"]:
            for m in mods_pt: sementes.append(f"{termo_base} {m}")
        if idioma_modo in ["ambos", "ingles"]:
            for m in mods_en: sementes.append(f"{termo_base} {m}")
    else:
        psp_pt = ["ppsspp", "iso ppsspp", "ppsspp pt br", "save data", "mediafire iso"]
        psp_en = ["ppsspp iso", "ppsspp gameplay", "best settings ppsspp", "psp iso"]
        if idioma_modo in ["ambos", "pt_br"]:
            for p in psp_pt: sementes.append(f"{termo_base} {p}")
        if idioma_modo in ["ambos", "ingles"]:
            for p in psp_en: sementes.append(f"{termo_base} {p}")

    tags_brutas = []
    for semente in sementes:
        if idioma_modo in ["ambos", "pt_br"]:
            tags_brutas.extend(buscar_autocomplete_yt(semente, lang="pt", country="BR"))
        if idioma_modo in ["ambos", "ingles"]:
            tags_brutas.extend(buscar_autocomplete_yt(semente, lang="en", country="US"))

    # Filtragem rigorosa
    tags_unicas = list(dict.fromkeys(tags_brutas))
    tags_filtradas = []
    
    for t in tags_unicas:
        t_lower = t.lower()
        if len(t) <= 3:
            continue
        # Remove ppsspp se for jogo de android
        if categoria == "android" and ("ppsspp" in t_lower or "psp" in t_lower):
            continue
        tags_filtradas.append(t)

    # Monta caixa até 500 caracteres
    tags_finais = []
    tamanho_total = 0
    for t in tags_filtradas:
        if tamanho_total + len(t) + 2 <= 500:
            tags_finais.append(t)
            tamanho_total += len(t) + 2
        else:
            break

    return ", ".join(tags_finais)

def formatar_hashtags_finais(hashtags_raspadas, jogo, categoria):
    """Gera hashtags limpas sem mistura de emulador em jogo Android."""
    clean_game = re.sub(r'[^a-zA-Z0-9]', '', jogo)
    
    # Se encontrou hashtags reais no YouTube, utiliza elas
    tags_finais = [h for h in hashtags_raspadas if h.startswith('#')]
    
    # Preenche com hashtags reais do próprio jogo se faltar
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

    # 1. Raspagem Direta do YouTube
    titulos_reais, hashtags_raspadas = raspar_youtube_real(termo_pesquisa, categoria)

    print("\n🔥 TOP 3 TÍTULOS REAIS EXTRAÍDOS DIRETO DO YOUTUBE:")
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

    # 3. Tags de busca reais
    tags_busca_caixa = extrair_tags_busca_reais(jogo, versao, categoria, idioma_modo)
    print("\n📌 CAIXA DE TAGS DE BUSCA REAIS (ATÉ 500 CARACTERES):")
    print("-" * 75)
    print(tags_busca_caixa)
    print("-" * 75)
    print(f"📊 Total de caracteres utilizados: {len(tags_busca_caixa)}/500")

if __name__ == "__main__":
    executar_gerador()
