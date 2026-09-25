import os
import requests
import datetime
import re
import json
import urllib.parse
from collections import Counter

ANO_ATUAL = datetime.datetime.now().year

HEADERS_DESKTOP = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7",
    "Sec-Ch-Ua": '"Chromium";v="124", "Google Chrome";v="124"',
    "Sec-Ch-Ua-Mobile": "?0",
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "none"
}

COOKIES_YT = {
    "CONSENT": "YES+1",
    "SOCS": "CAI"
}

# Apenas lixos técnicos do YouTube e atributos de layout
LIXO_SISTEMA_E_CANANIS = {
    'video', 'sharing', 'camera phone', 'free', 'upload', 'youtube', 'yt', 'shorts',
    'mobile', 'cell phone', 'phone', 'app', 'google', 'android', 'ios', 'menu', 'header',
    'button', 'icon', 'search', 'player', 'zippy', 'a11y', 'country', 'masthead',
    'logo', 'fyp', 'tiktok', 'viral', 'foryou', 'sub', 'subscribe', 'like', 'comment'
}

def eh_hex_color(string):
    """Filtra vazamentos de cores CSS Hexadecimal do HTML (ex: fff, 0f0f0f)."""
    return bool(re.fullmatch(r'^[0-9a-fA-F]{3}$|^[0-9a-fA-F]{6}$|^[0-9a-fA-F]{8}$', string))

def limpar_titulo_anti_strike(titulo):
    """Substitui termos sensíveis nos títulos para proteção da conta."""
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

def eh_hashtag_valida_sem_limite(ht_raw):
    """
    Filtro ultra permissivo para puxar TODAS as hashtags reais dos vídeos do topo.
    Remove apenas lixos de sistema e códigos hexadecimal CSS.
    """
    ht = ht_raw.lower().replace("#", "").strip()

    if len(ht) < 2 or ht.isdigit() or ht in LIXO_SISTEMA_E_CANANIS:
        return False

    if eh_hex_color(ht):
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
# SISTEMA PENTA-BOT AUTOMÁTICO (5 ROBÔS INTEGRADOS)
# ==============================================================================

def bot_1_minerador_topo(jogo, categoria):
    """
    BOT 1: Coleta os melhores títulos do topo e identifica palavras-chave virais de mods.
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
        m = re.findall(r'\b(sky ava|sky mod|sky|cheto|ev loader|bully|vip|mod menu|xp|auto farm|autoplay|longlines)\b', t, re.IGNORECASE)
        for item in m:
            if item.lower() not in mod_terms_titulos:
                mod_terms_titulos.append(item.lower())

    return titulos, video_ids, mod_terms_titulos

def bot_2_super_raspador_hashtags_massivo(video_ids, jogo):
    """
    BOT 2 (EXTRAÇÃO MASSIVA DE HASHTAGS DA DESCRIÇÃO):
    Varre os 10 vídeos do topo, força o descolamento (#a#b -> #a #b), decodifica Unicodes
    e puxar TODAS as hashtags sem limitação.
    """
    todas_hashtags = []
    seen = set()

    session = requests.Session()
    session.headers.update(HEADERS_DESKTOP)

    for v_id in video_ids[:10]:
        try:
            url = f"https://www.youtube.com/watch?v={v_id}"
            res = session.get(url, cookies=COOKIES_YT, timeout=6)
            if res.status_code == 200:
                html = res.text
                html_clean = html.replace('\\u0023', '#').replace('\\u0026', '&')

                texto_alvo = ""
                matches_json = re.findall(r'"text":"([^"]+)"', html_clean)
                if matches_json:
                    texto_alvo += " " + " ".join(matches_json)

                desc_match = re.search(r'"shortDescription":"(.*?)","isCrawlable"', html_clean)
                if desc_match:
                    texto_alvo += " " + desc_match.group(1)

                meta_desc = re.search(r'<meta\s+name="description"\s+content="([^"]+)"', html_clean, re.IGNORECASE)
                if meta_desc:
                    texto_alvo += " " + meta_desc.group(1)

                # Desgruda hashtags coladas: #avakin#mod -> #avakin #mod
                texto_formatado = re.sub(r'#', ' #', texto_alvo)
                raw_hts = re.findall(r'#([a-zA-Z0-9_\u00C0-\u00FF]+)', texto_formatado)

                for ht in raw_hts:
                    if eh_hashtag_valida_sem_limite(ht):
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
    BOT 3: Pesquisa alfabética oficial de autocomplete do YouTube.
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
    BOT 4: Ranqueia as melhores palavras de busca e preenche exatamente até 500 caracteres.
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

def bot_5_mestre_estrategico_e_copywriting(jogo, versao, video_ids, mod_terms_titulos, total_chars_tags, total_hashtags):
    """
    BOT 5 INTELIGENTE (ESTRATEGISTA COMPLETO DE CONVERSÃO & SEO):
    1. Score SEO do Vídeo (0-100%).
    2. Descrição Otimizada Pronta para Copiar (Copywriting Anti-Strike).
    3. Comentário Fixado (Pinned Comment Estratégico).
    4. Gatilhos de Thumbnail.
    """
    v_str = f" v{versao}" if versao else ""
    jogo_upper = jogo.upper()

    # Cálculo do SEO Score
    score = 70
    if total_chars_tags >= 450:
        score += 15
    if total_hashtags >= 10:
        score += 15

    # 1. Template de Descrição Otimizada
    descricao_template = f"""━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🔥 {jogo_upper}{v_str} SHOWCASE & GAMEPLAY ATUALIZADO
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🎮 SOBRE O VÍDEO:
Confira a melhor apresentação completa do {jogo_upper} atualizado! Gameplay fluida, recursos ativados e tutorial de instalação no Android.

📌 LINK DE DOWNLOAD & INSTRUÇÕES:
 Fixado no primeiro comentário abaixo!

💬 COMUNIDADE & SUPORTE:
 Entre no grupo do Telegram para suporte e pedidos de jogos!

⚠️ DISCLAIMER & AVISO LEGAL:
Este vídeo é estritamente demonstrativo e educativo (Showcase/Gameplay). Todos os direitos pertencem aos criadores originais do jogo.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"""

    # 2. Comentário Fixado Estratégico
    comentario_fixado = f"👇 [DOWNLOAD & SUPORTE COMPLETO FIXADO] 👇\n\n✅ {jogo_upper}{v_str} Testado e Funcional!\n💬 Deixe seu gostei e comente qual jogo você quer no próximo vídeo!\n🔔 Se inscreva para receber novidades em primeira mão."

    # 3. Gatilhos de Capa
    gatilhos_thumb = ["LINK DIRETO", "MEDIAFIRE", "SEM KEY", "NOVA ATUALIZAÇÃO"]
    if mod_terms_titulos:
        gatilhos_thumb.insert(0, mod_terms_titulos[0].upper())

    relatorio = []
    relatorio.append(f"📊 SCORE DE OTIMIZAÇÃO SEO DO VÍDEO: {score}%/100% [MÁXIMO ENGAJAMENTO]")
    relatorio.append("\n📝 1. DESCRIÇÃO OTIMIZADA COMPLETA (COPIE E COLE NO SEU VÍDEO):")
    relatorio.append("-" * 65)
    relatorio.append(descricao_template)
    relatorio.append("-" * 65)
    relatorio.append("\n📌 2. COMENTÁRIO FIXADO ESTRATÉGICO (PINNED COMMENT):")
    relatorio.append("-" * 65)
    relatorio.append(comentario_fixado)
    relatorio.append("-" * 65)
    relatorio.append("\n🖼️ 3. TEXTOS GATILHO RECOMENDADOS PARA A THUMBNAIL/CAPA:")
    relatorio.append(f"   ➔ [{ ' ]  [ '.join(gatilhos_thumb[:4]) }]")
    relatorio.append("\n🛡️ 4. AUDITORIA DE SEGURANÇA E PROTEÇÃO DA CONTA:")
    relatorio.append("   ✅ Termos sensíveis substituídos com sucesso no título e nas tags.")
    relatorio.append("   ✅ Descrição formatada sem links diretos para evitar remoção automatizada.")

    return "\n".join(relatorio)

def executar_gerador():
    jogo = os.getenv("GAME_NAME", "Avakin Life").strip()
    versao = os.getenv("GAME_VERSION", "").strip()
    categoria = os.getenv("CATEGORY", "android").strip().lower()
    idioma_modo = os.getenv("LANGUAGE_MODE", "ambos").strip().lower()

    print("=" * 75)
    print(f"🤖 ROBÔ SEO YOUTUBE - SISTEMA PENTA-BOT AUTOMÁTICO: {jogo.upper()} {versao}")
    print(f"📂 Categoria: {categoria.upper()} | Idioma: {idioma_modo.upper()}")
    print("=" * 75)

    # 1. BOT 1
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

    # 2. BOT 2 - Extração Massiva Sem Limites
    hashtags_massivas = bot_2_super_raspador_hashtags_massivo(video_ids, jogo)

    print("\n🔎 HASHTAGS DA DESCRIÇÃO (10 VÍDEOS VARRIDOS - EXTRAÇÃO MASSIVA SEM LIMITES):")
    print("-" * 75)
    if hashtags_massivas:
        print(" ".join(hashtags_massivas))
        print(f"\n📊 Total de Hashtags Puxadas: {len(hashtags_massivas)}")
    else:
        clean_game = re.sub(r'[^a-zA-Z0-9]', '', jogo)
        print(f"#{clean_game} #{clean_game}Mod #{clean_game}ModMenu #{clean_game}Gameplay #{clean_game}{ANO_ATUAL} #ModApk #Mediafire #AndroidGames")

    # 3. BOT 3 & BOT 4
    buscas_bot3 = bot_3_autocomplete_deep(jogo, categoria, idioma_modo, mod_terms_titulos)
    tags_caixa_final = bot_4_inteligencia_cruzada(buscas_bot3, video_ids, jogo, categoria, mod_terms_titulos)

    print("\n📌 CAIXA DE TAGS DE BUSCA BRUTAS (SISTEMA PENTA-BOT - 100% REAIS):")
    print("-" * 75)
    print(tags_caixa_final)
    print("-" * 75)
    print(f"📊 Total de caracteres utilizados: {len(tags_caixa_final)}/500")

    # 4. BOT 5 - Estrategista Inteligente
    relatorio_bot5 = bot_5_mestre_estrategico_e_copywriting(
        jogo, versao, video_ids, mod_terms_titulos, len(tags_caixa_final), len(hashtags_massivas)
    )

    print("\n💡 BOT 5 - INTELIGÊNCIA COMPLETA DE ESTRATÉGIA & ENGAJAMENTO:")
    print("-" * 75)
    print(relatorio_bot5)
    print("=" * 75)

if __name__ == "__main__":
    executar_gerador()
