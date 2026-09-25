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

def eh_termo_invalido_ou_hex(termo):
    """Remove códigos hexadecimais de CSS e termos irrelevantes de UI do YouTube."""
    t_clean = termo.lower().replace("#", "").strip()
    if re.match(r'^[0-9a-f]{3}$', t_clean) or re.match(r'^[0-9a-f]{6}$', t_clean):
        return True
    termos_invalidos = {'menu', 'masthead', 'country', 'yt', 'a11y', 'youtube', 'search', 'logo', 'zippy', 'player', 'header', 'button', 'icon'}
    return t_clean in termos_invalidos

def raspar_dados_top_videos(termo_busca, categoria):
    """
    Entra no YouTube, identifica os vídeos no topo do ranking e extrai:
    1. Títulos dos vídeos.
    2. Tags secretas (keywords do próprio vídeo).
    3. Todas as Hashtags da descrição sem limite.
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
                            
                            if title and len(title) > 10 and title not in titulos_reais:
                                titulos_reais.append(limpar_titulo_anti_strike(title))
                                if v_id:
                                    video_ids.append(v_id)
                            
                            if len(titulos_reais) >= 3:
                                break
                    if len(titulos_reais) >= 3:
                        break
    except Exception as e:
        print(f"[-] Erro na busca inicial: {e}")

    hashtags_desc = []
    tags_brutas_videos = []

    # Raspa as entranhas dos 3 vídeos no topo (Tags secretas do vídeo + Hashtags da descrição)
    for v_id in video_ids[:3]:
        try:
            v_url = f"https://www.youtube.com/watch?v={v_id}"
            v_res = requests.get(v_url, headers=HEADERS_DESKTOP, cookies=COOKIES_YT, timeout=8)
            if v_res.status_code == 200:
                html = v_res.text
                
                # 1. Extrai as tags reais/secretas gravadas no código do vídeo ("keywords")
                kw_match = re.search(r'"keywords":\s*\[(.*?)\]', html)
                if kw_match:
                    raw_kws = kw_match.group(1)
                    kws = re.findall(r'"([^"]+)"', raw_kws)
                    for k in kws:
                        k_clean = k.strip()
                        if len(k_clean) > 2 and not eh_termo_invalido_ou_hex(k_clean):
                            if categoria == "android" and ("ppsspp" in k_clean.lower() or "psp" in k_clean.lower()):
                                continue
                            if k_clean.lower() not in [t.lower() for t in tags_brutas_videos]:
                                tags_brutas_videos.append(k_clean)

                # 2. Extrai TODAS as hashtags da descrição do vídeo
                desc_match = re.search(r'"shortDescription":"(.*?)","isCrawlable"', html)
                texto_desc = desc_match.group(1) if desc_match else html
                
                # Desgruda hashtags coladas (#game#mod -> #game #mod)
                texto_formatado = re.sub(r'#', ' #', texto_desc)
                tags_encontradas = re.findall(r'#([a-zA-Z0-9_]+)', texto_formatado)
                
                for ht in tags_encontradas:
                    if eh_termo_invalido_ou_hex(ht):
                        continue
                    ht_full = f"#{ht}"
                    ht_lower = ht_full.lower()
                    
                    if categoria == "android" and ("ppsspp" in ht_lower or "psp" in ht_lower):
                        continue
                        
                    if len(ht) > 2 and ht_lower not in [h.lower() for h in hashtags_desc]:
                        hashtags_desc.append(ht_full)
        except Exception:
            pass

    return titulos_reais, hashtags_desc, tags_brutas_videos

def buscar_autocomplete_yt(termo, lang="pt", country="BR"):
    """Puxa sugestões de pesquisas em tempo real do YouTube."""
    url = f"http://suggestqueries.google.com/complete/search?client=firefox&ds=yt&q={urllib.parse.quote(termo)}&gl={country}&hl={lang}"
    try:
        r = requests.get(url, headers=HEADERS_DESKTOP, timeout=5)
        if r.status_code == 200:
            return r.json()[1]
    except Exception:
        pass
    return []

def gerar_caixa_tags_brutas(jogo, versao, categoria, idioma_modo, tags_extraidas_videos):
    """
    Mineração Avançada de Tags de Busca:
    Combina as tags reais extraídas diretamente dos vídeos tops do YouTube com pesquisas de alta frequência.
    """
    termo_clean = re.sub(r'[^a-zA-Z0-9 ]', '', jogo).strip()
    v_clean = versao.strip()
    
    # Pesquisas de alta intenção e volume no YouTube
    sementes = [
        f"{termo_clean}",
        f"{termo_clean} mod apk",
        f"{termo_clean} mod menu",
        f"{termo_clean} {ANO_ATUAL}",
        f"{termo_clean} dinheiro infinito",
        f"{termo_clean} atualizado",
        f"{termo_clean} mediafire",
        f"{termo_clean} download",
        f"{termo_clean} gameplay",
        f"{termo_clean} android",
    ]
    if v_clean:
        sementes.insert(0, f"{termo_clean} {v_clean}")
    if categoria == "ppsspp":
        sementes.extend([f"{termo_clean} ppsspp", f"{termo_clean} iso mediafire"])

    tags_auto = []
    for s in sementes:
        if idioma_modo in ["ambos", "pt_br"]:
            tags_auto.extend(buscar_autocomplete_yt(s, lang="pt", country="BR"))
        if idioma_modo in ["ambos", "ingles"]:
            tags_auto.extend(buscar_autocomplete_yt(s, lang="en", country="US"))

    # Prioriza as tags secretas extraídas dos vídeos em 1º lugar
    todas_tags = tags_extraidas_videos + tags_auto

    seen = set()
    tags_prioritarias = []
    for t in todas_tags:
        t_clean = re.sub(r'[^\w\s\-\/]', '', t).strip()
        t_lower = t_clean.lower()
        if t_lower in seen or len(t_clean) <= 2 or eh_termo_invalido_ou_hex(t_clean):
            continue
        if categoria == "android" and ("ppsspp" in t_lower or "psp" in t_lower):
            continue
        seen.add(t_lower)
        tags_prioritarias.append(t_clean)

    # Preenche a caixa respeitando o limite de 500 caracteres
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

    # Extração profunda dos vídeos top do YouTube
    titulos_reais, hashtags_desc, tags_brutas_videos = raspar_dados_top_videos(termo_pesquisa, categoria)

    # 1. Títulos Reais
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

    # 2. Descrição Limpa (Apenas Aviso Legal + Hashtags Extraídas)
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
