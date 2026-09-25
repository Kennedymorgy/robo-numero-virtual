import os
import requests
import datetime
import re
import json
import urllib.parse
from collections import Counter

ANO_ATUAL = datetime.datetime.now().year

HEADERS_DESKTOP = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7",
}

COOKIES_YT = {
    "CONSENT": "YES+1",
    "SOCS": "CAI"
}

LIXO_SISTEMA_E_CANANIS = {
    'vídeo', 'compartilhamento', 'celular com câmera', 'videofone', 'gratuito', 'envio',
    'video', 'sharing', 'camera phone', 'free', 'upload', 'youtube', 'yt', 'shorts',
    'mobile', 'cell phone', 'phone', 'app', 'google', 'android', 'ios', 'menu', 'header',
    'button', 'icon', 'search', 'player', 'zippy', 'a11y', 'country', 'masthead',
    'logo', 'fyp', 'tiktok', 'viral', 'foryou', 'dappernexor', 'adam_tv_077', 'adam_tv',
    '45', 'h', '404', 'sub', 'subscribe', 'like', 'comment'
}

def eh_hex_color(string):
    """Filtra vazamentos de cores CSS Hexadecimal do HTML do YouTube."""
    return bool(re.fullmatch(r'^[0-9a-fA-F]{3}$|^[0-9a-fA-F]{6}$|^[0-9a-fA-F]{8}$', string))

def limpar_titulo_anti_strike(titulo):
    """Higieniza termos sensíveis nos títulos para proteção da conta."""
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
    """Garante apenas hashtags reais, sem códigos de sistema ou anos antigos."""
    ht = ht_raw.lower().replace("#", "").strip()

    if len(ht) < 2 or ht.isdigit() or ht in LIXO_SISTEMA_E_CANANIS:
        return False

    if eh_hex_color(ht):
        return False

    if re.search(r'_\d+$', ht) or ('tv' in ht and len(ht) > 8):
        if not any(k in ht for k in ['mod', 'apk', 'game', 'gameplay', 'sky', 'cheto', 'ava', 'menu']):
            return False

    for ano in range(2010, ANO_ATUAL):
        if str(ano) in ht:
            return False

    return True

def buscar_autocomplete_yt(termo, lang="pt", country="BR"):
    """Consulta o serviço de autocomplete oficial do YouTube."""
    url = f"http://suggestqueries.google.com/complete/search?client=firefox&ds=yt&q={urllib.parse.quote(termo)}&gl={country}&hl={lang}"
    try:
        r = requests.get(url, headers=HEADERS_DESKTOP, timeout=5)
        if r.status_code == 200:
            return r.json()[1]
    except Exception:
        pass
    return []

# ==============================================================================
# SISTEMA PENTA-BOT (5 ROBÔS EM CONJUNTO)
# ==============================================================================

def bot_1_minerador_topo(jogo, categoria):
    """
    BOT 1: Coleta os 4 melhores títulos do topo (anti-strike) e
    detecta termos de mods virais nos títulos (ex: Cheto, Sky Ava, EV Loader).
    """
    termo_busca = f"{jogo} mod apk" if categoria == "android" else f"{jogo} ppsspp"
    url = f"https://www.youtube.com/results?search_query={urllib.parse.quote(termo_busca)}"

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
        print(f"[-] Bot 1 Aviso: {e}")

    mod_terms_titulos = []
    for t in titulos:
        m = re.findall(r'\b(sky ava|sky mod|sky|cheto|ev loader|bully|vip|mod menu|xp|auto farm)\b', t, re.IGNORECASE)
        for item in m:
            if item.lower() not in mod_terms_titulos:
                mod_terms_titulos.append(item.lower())

    return titulos, video_ids, mod_terms_titulos

def bot_2_super_raspador_hashtags(video_ids, jogo):
    """
    BOT 2: Varre 10 vídeos do topo, extrai hashtags do JSON interno e do HTML,
    desgruda hashtags coladas (#a#b), trata Unicode (\\u0023) e remove lixos de CSS.
    """
    todas_hashtags = []
    seen = set()

    for v_id in video_ids[:10]:
        try:
            url = f"https://www.youtube.com/watch?v={v_id}"
            res = requests.get(url, headers=HEADERS_DESKTOP, cookies=COOKIES_YT, timeout=5)
            if res.status_code == 200:
                html = res.text
                
                # Decodifica unicodes comuns de hashtag
                html_clean = html.replace('\\u0023', '#')

                # Captura de blocos de texto no JSON do YouTube
                texto_alvo = ""
                matches_json = re.findall(r'"text":"([^"]+)"', html_clean)
                if matches_json:
                    texto_alvo += " ".join(matches_json)

                desc_match = re.search(r'"shortDescription":"(.*?)","isCrawlable"', html_clean)
                if desc_match:
                    texto_alvo += " " + desc_match.group(1)

                # Desgruda hashtags grudadas (#a#b -> #a #b)
                texto_formatado = re.sub(r'#', ' #', texto_alvo)
                raw_hts = re.findall(r'#([a-zA-Z0-9_]+)', texto_formatado)

                for ht in raw_hts:
                    if eh_hashtag_valida(ht, jogo):
                        ht_formated = f"#{ht}"
                        ht_lower = ht_formated.lower()
                        if ht_lower not in seen:
                            seen.add(ht_lower)
                            todas_hashtags.append(ht_formated)
        except Exception:
            pass

    return todas_hashtags

def bot_3_autocomplete_deep(jogo, categoria, idioma_modo, mod_terms_titulos):
    """
    BOT 3: Mineração alfabética nas buscas reais do YouTube incluindo
    termos de mods específicos encontrados pelo Bot 1.
    """
    j_clean = re.sub(r'[^a-zA-Z0-9 ]', '', jogo).strip()

    base_queries = [
        f"{j_clean} mod apk",
        f"{j_clean} mod menu",
        f"{j_clean} dinheiro infinito",
        f"{j_clean} mediafire",
        f"{j_clean} atualizado",
        f"como baixar {j_clean} mod",
        f"{j_clean} sem key",
        f"{j_clean} link direto"
    ]

    for term in mod_terms_titulos:
        base_queries.append(f"{j_clean} {term}")

    if categoria == "ppsspp":
        base_queries = [
            f"{j_clean} ppsspp iso",
            f"{j_clean} psp mediafire",
            f"como baixar {j_clean} ppsspp",
            f"{j_clean} psp android"
        ]

    buscas = []
    for bq in base_queries:
        if idioma_modo in ["ambos", "pt_br"]:
            buscas.extend(buscar_autocomplete_yt(bq, "pt", "BR"))
        if idioma_modo in ["ambos", "ingles"]:
            buscas.extend(buscar_autocomplete_yt(bq, "en", "US"))

    return buscas

def bot_4_inteligencia_cruzada(buscas_bot3, video_ids, jogo, categoria, mod_terms_titulos):
    """
    BOT 4: Cruza buscas reais com as palavras-chave ocultas dos vídeos do topo
    e ranqueia os termos mais fortes até atingir 500 caracteres.
    """
    keywords_internas_videos = []
    for v_id in video_ids[:8]:
        try:
            url = f"https://www.youtube.com/watch?v={v_id}"
            res = requests.get(url, headers=HEADERS_DESKTOP, cookies=COOKIES_YT, timeout=5)
            if res.status_code == 200:
                kw_match = re.search(r'"keywords":\s*\[(.*?)\]', res.text)
                if kw_match:
                    kws = re.findall(r'"([^"]+)"', kw_match.group(1))
                    keywords_internas_videos.extend(kws)
        except Exception:
            pass

    todas_candidatas = buscas_bot3 + keywords_internas_videos
    frequencia = Counter()
    termo_limpo_map = {}

    termos_fora_de_foco = ['rosto', 'face ideas', 'outfit ideas', 'look', 'maquiagem', 'cabelo', 'male face', 'female face']

    for cand in todas_candidatas:
        c_clean = re.sub(r'[^\w\s\-\/]', '', cand).strip()
        for ano_antigo in range(2015, ANO_ATUAL):
            c_clean = re.sub(r'\b' + str(ano_antigo) + r'\b', str(ANO_ATUAL), c_clean, flags=re.IGNORECASE)

        c_lower = c_clean.lower()

        if len(c_clean) <= 3 or c_lower in LIXO_SISTEMA_E_CANANIS or eh_hex_color(c_lower):
            continue

        if any(tf in c_lower for tf in termos_fora_de_foco):
            continue

        if categoria == "android" and ("ppsspp" in c_lower or "psp " in c_lower):
            continue

        pontos = 1
        if cand in buscas_bot3 and cand in keywords_internas_videos:
            pontos += 5
        if any(m in c_lower for m in mod_terms_titulos):
            pontos += 4
        if any(k in c_lower for k in ['mod', 'apk', 'menu', 'mediafire', 'dinheiro', 'cheto', 'atualizado', 'sem key']):
            pontos += 2

        frequencia[c_lower] += pontos
        if c_lower not in termo_limpo_map:
            termo_limpo_map[c_lower] = c_clean

    termos_ordenados = sorted(frequencia.keys(), key=lambda x: frequencia[x], reverse=True)

    tags_finais = []
    tamanho_total = 0

    for t_key in termos_ordenados:
        t_orig = termo_limpo_map[t_key]
        custo = len(t_orig) + 2 if tags_finais else len(t_orig)
        if tamanho_total + custo <= 500:
            tags_finais.append(t_orig)
            tamanho_total += custo
        else:
            break

    return ", ".join(tags_finais)

def bot_5_engajamento_e_comunidade(jogo, versao, hashtags):
    """
    BOT 5: Monta a estrutura da descrição para o vídeo com CTAs de inscrição,
    área de comunidade/suporte e aviso de isenção legal anti-strike.
    """
    v_str = f" {versao}" if versao else ""
    desc = []
    desc.append(f"🎮 {jogo.upper()}{v_str} SHOWCASE & GAMEPLAY ATUALIZADA!\n")
    desc.append("🔔 Se inscreva no canal e ative o sininho para não perder as atualizações diárias!\n")
    desc.append("💬 LINKS E SUPORTE DA COMUNIDADE:")
    desc.append("👉 Grupo no Telegram: [INSERIR LINK DO TELEGRAM]")
    desc.append("👉 Comunidade WhatsApp: [INSERIR LINK DO WHATSAPP]")
    desc.append("👉 Download no Site Oficial: [INSERIR LINK DO BLOG]\n")
    desc.append("⚠️ AVISO LEGAL E ISENÇÃO DE RESPONSABILIDADE / LEGAL DISCLAIMER:")
    desc.append("Este vídeo possui caráter puramente educativo e demonstrativo de performance em jogos mobile/emulação. Todos os direitos e marcas registradas pertencem aos seus respetivos criadores e desenvolvedores.")
    desc.append("This video is purely educational and for performance demonstration purposes. All rights belong to their respective owners.\n")
    desc.append("🔎 HASHTAGS DO VÍDEO:")
    
    if hashtags:
        desc.append(" ".join(hashtags[:20]))
    else:
        clean_game = re.sub(r'[^a-zA-Z0-9]', '', jogo)
        desc.append(f"#{clean_game} #{clean_game}Mod #{clean_game}ModMenu #{clean_game}Gameplay #{clean_game}{ANO_ATUAL} #ModApk #Mediafire #AndroidGames")

    return "\n".join(desc)

def executar_gerador():
    jogo = os.getenv("GAME_NAME", "8 Ball Pool").strip()
    versao = os.getenv("GAME_VERSION", "").strip()
    categoria = os.getenv("CATEGORY", "android").strip().lower()
    idioma_modo = os.getenv("LANGUAGE_MODE", "ambos").strip().lower()

    print("=" * 75)
    print(f"🤖 ROBÔ SEO YOUTUBE - SISTEMA PENTA-BOT (5 ROBÔS): {jogo.upper()} {versao}")
    print(f"📂 Categoria: {categoria.upper()} | Idioma: {idioma_modo.upper()}")
    print("=" * 75)

    # 1. BOT 1 - Topo, Títulos e Mods Virais
    titulos_reais, video_ids, mod_terms_titulos = bot_1_minerador_topo(jogo, categoria)

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

    # 2. BOT 2 - Extração Massiva de Hashtags
    hashtags_massivas = bot_2_super_raspador_hashtags(video_ids, jogo)

    # 3. BOT 3 & BOT 4 - Autocomplete Profundo e Cruzamento de Tags
    buscas_bot3 = bot_3_autocomplete_deep(jogo, categoria, idioma_modo, mod_terms_titulos)
    tags_caixa_final = bot_4_inteligencia_cruzada(buscas_bot3, video_ids, jogo, categoria, mod_terms_titulos)

    # 4. BOT 5 - Estruturação de Descrição, CTA e Comunidade
    descricao_completa = bot_5_engajamento_e_comunidade(jogo, versao, hashtags_massivas)

    print("\n📝 DESCRIÇÃO COMPLETA (BOT 5 - CTA, SUPORTE, DISCLAIMER E HASHTAGS):")
    print("-" * 75)
    print(descricao_completa)

    print("\n📌 CAIXA DE TAGS DE BUSCA BRUTAS (SISTEMA PENTA-BOT - 100% REAIS):")
    print("-" * 75)
    print(tags_caixa_final)
    print("-" * 75)
    print(f"📊 Total de caracteres utilizados: {len(tags_caixa_final)}/500")

if __name__ == "__main__":
    executar_gerador()
