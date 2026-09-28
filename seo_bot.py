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
    """Substitui termos sensíveis para proteger a conta contra políticas do YouTube."""
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
    """Filtra apenas hashtags reais e de valor."""
    ht = ht_raw.lower().replace("#", "").strip()
    if len(ht) < 2 or ht.isdigit() or ht in LIXO_SISTEMA_E_CANANIS or eh_hex_color(ht):
        return False
    return True

def buscar_autocomplete_yt(termo, lang="pt", country="BR"):
    """Consulta o serviço oficial de autocomplete do YouTube."""
    url = f"http://suggestqueries.google.com/complete/search?client=firefox&ds=yt&q={urllib.parse.quote(termo)}&gl={country}&hl={lang}"
    try:
        r = requests.get(url, headers=HEADERS_DESKTOP, timeout=5)
        if r.status_code == 200:
            return r.json()[1]
    except Exception:
        pass
    return []

# ==============================================================================
# SISTEMA DE MINERAÇÃO E EXTRAÇÃO (PENTA-BOT)
# ==============================================================================

def bot_1_minerador_topo(jogo, categoria):
    """BOT 1: Coleta os melhores títulos do topo e detecta termos de mods virais."""
    termo_busca = f"{jogo} mod apk" if categoria == "android" else f"{jogo} ppsspp iso"
    url = f"https://www.youtube.com/results?search_query={urllib.parse.quote(termo_busca)}"

    titulos = []
    video_ids = []

    try:
        res = requests.get(url, headers=HEADERS_DESKTOP, cookies=COOKIES_YT, timeout=10)
        if res.status_code == 200:
            match = re.search(r'var ytInitialData\s*=\s*({.*?});</script>', res.text, re.DOTALL)
            if not match:
                match = re.search(r'window\["ytInitialData"\]\s*=\s*({.*?});', res.text, re.DOTALL)
                
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
        m = re.findall(r'\b(sky ava|sky mod|sky|cheto|ev loader|bully|vip|mod menu|xp|auto farm|textures|save data|camera ps5|60fps)\b', t, re.IGNORECASE)
        for item in m:
            if item.lower() not in mod_terms_titulos:
                mod_terms_titulos.append(item.lower())

    return titulos, video_ids, mod_terms_titulos

def bot_2_super_raspador_hashtags(video_ids, jogo):
    """BOT 2: Raspador de hashtags reais da descrição de até 10 vídeos concorrentes."""
    todas_hashtags_consolidadas = []
    seen = set()
    maior_pacote_unico = []
    max_count = 0

    session = requests.Session()
    session.headers.update(HEADERS_DESKTOP)

    for v_id in video_ids[:10]:
        try:
            url = f"https://www.youtube.com/watch?v={v_id}"
            res = session.get(url, cookies=COOKIES_YT, timeout=6)
            if res.status_code == 200:
                html = res.text
                html_clean = html.replace('\\u0023', '#').replace('\u0023', '#').replace('\\u0026', '&').replace('&amp;', '&')

                texto_alvo = ""
                matches_json = re.findall(r'"text":"([^"]+)"', html_clean)
                if matches_json:
                    texto_alvo += " " + " ".join(matches_json)

                desc_match = re.search(r'"shortDescription":"(.*?)","isCrawlable"', html_clean)
                if desc_match:
                    texto_alvo += " " + desc_match.group(1)

                texto_formatado = re.sub(r'#', ' #', texto_alvo)
                raw_hts = re.findall(r'#([a-zA-Z0-9_\u00C0-\u00FF]+)', texto_formatado)

                hashtags_deste_video = []
                for ht in raw_hts:
                    if eh_hashtag_valida(ht, jogo):
                        ht_formated = f"#{ht}"
                        ht_lower = ht_formated.lower()
                        
                        if ht_lower not in [h.lower() for h in hashtags_deste_video]:
                            hashtags_deste_video.append(ht_formated)

                        if ht_lower not in seen:
                            seen.add(ht_lower)
                            todas_hashtags_consolidadas.append(ht_formated)

                if len(hashtags_deste_video) > max_count:
                    max_count = len(hashtags_deste_video)
                    maior_pacote_unico = hashtags_deste_video
        except Exception:
            pass

    if len(todas_hashtags_consolidadas) >= len(maior_pacote_unico) and todas_hashtags_consolidadas:
        return todas_hashtags_consolidadas[:15]
    return maior_pacote_unico[:15]

def bot_3_autocomplete_deep(jogo, categoria, idioma_modo, mod_terms_titulos):
    """BOT 3: Mineração alfabética e bilingue nas buscas reais do YouTube."""
    j_clean = re.sub(r'[^a-zA-Z0-9 ]', '', jogo).strip()

    if categoria == "android":
        base_queries_pt = [
            f"{j_clean} mod apk", f"{j_clean} mod menu", f"{j_clean} dinheiro infinito",
            f"{j_clean} mediafire", f"{j_clean} atualizado", f"como baixar {j_clean} mod",
            f"{j_clean} sem key", f"{j_clean} link direto"
        ]
        base_queries_en = [
            f"{j_clean} mod apk", f"{j_clean} mod menu", f"{j_clean} unlimited money",
            f"{j_clean} mediafire link", f"{j_clean} latest version", f"how to download {j_clean} mod",
            f"{j_clean} gameplay android", f"{j_clean} unlocked"
        ]
    else:  # PPSSPP
        base_queries_pt = [
            f"{j_clean} ppsspp iso", f"{j_clean} psp mediafire", f"como baixar {j_clean} ppsspp",
            f"{j_clean} psp android", f"{j_clean} ppsspp save data", f"{j_clean} ppsspp texturas"
        ]
        base_queries_en = [
            f"{j_clean} ppsspp iso download", f"{j_clean} psp mediafire", f"how to download {j_clean} ppsspp",
            f"{j_clean} ppsspp android", f"{j_clean} ppsspp best settings", f"{j_clean} ppsspp cheats"
        ]

    for term in mod_terms_titulos:
        base_queries_pt.append(f"{j_clean} {term}")
        base_queries_en.append(f"{j_clean} {term}")

    buscas = []
    if idioma_modo in ["ambos", "pt_br"]:
        for bq in base_queries_pt:
            buscas.extend(buscar_autocomplete_yt(bq, "pt", "BR"))
    if idioma_modo in ["ambos", "ingles"]:
        for bq in base_queries_en:
            buscas.extend(buscar_autocomplete_yt(bq, "en", "US"))

    return buscas

def bot_4_inteligencia_cruzada(buscas_bot3, video_ids, jogo, categoria, mod_terms_titulos):
    """BOT 4: Cruza termos buscados e gera caixa de 500 caracteres perfeita."""
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

    termos_fora_de_foco = ['rosto', 'face ideas', 'outfit ideas', 'look', 'maquiagem', 'cabelo']

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
        if any(k in c_lower for k in ['mod', 'apk', 'menu', 'mediafire', 'dinheiro', 'cheto', 'iso', 'unlimited']):
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

def bot_5_gerador_descricao_e_ctr(jogo, versao, categoria, idioma_modo, hashtags, tags_caixa):
    """
    BOT 5: Gera a Descrição SEO Completa Otimizada + Gatilhos para Thumbnail.
    """
    ver_str = f" v{versao}" if versao else ""
    cat_str = "Android Mod APK" if categoria == "android" else "PPSSPP / PSP ISO"

    # 1. Estrutura da Descrição
    desc = []
    desc.append(f"🎮 {jogo.upper()}{ver_str} - {cat_str} ({ANO_ATUAL})")
    desc.append("=" * 60)
    
    if categoria == "android":
        desc.append(f"Confira no vídeo de hoje a demonstração completa do {jogo}{ver_str} totalmente atualizado! Aprenda passo a passo como baixar e instalar a versão mais recente diretamente no seu dispositivo Android de forma rápida e segura.")
        desc.append("\nCheck out today's full showcase of the updated {jogo}{ver_str}! Learn step-by-step how to download and install the latest version directly on your Android device safely and easily.")
        desc.append("\n✨ DESTAQUES / FEATURES:")
        desc.append("• Versão Atualizada / Updated Version")
        desc.append("• Menu Fluído & Interface Limpa")
        desc.append("• Suporte Completo para Android (10 ao 14)")
        desc.append("• Link Direto / Direct Download Link")
    else:
        desc.append(f"Confira a melhor configuração, ISO e Save Data para {jogo}{ver_str} no emulador PPSSPP! Gameplay fluída em 60 FPS sem travamentos no Android.")
        desc.append(f"\nBest PPSSPP settings, ISO, Save Data, and Textures for {jogo}{ver_str}! Smooth 60 FPS gameplay on Android & PC.")
        desc.append("\n✨ DESTAQUES / FEATURES:")
        desc.append("• ISO Compactada / Highly Compressed ISO")
        desc.append("• Save Data + Texturas HD (Opcional)")
        desc.append("• Configuração Anti-Lags (60 FPS Fix)")
        desc.append("• Compatível com PPSSPP Gold")

    desc.append("\n" + "=" * 60)
    desc.append("⬇️ ÁREA DE DOWNLOAD & SUPORTE / DOWNLOAD LINKS:")
    desc.append("👉 Download (Site Oficial / Official Link): [INSERIR_LINK_AQUI]")
    desc.append("💬 Grupo do Telegram (Suporte & Pedidos): https://t.me/k404_modapk")
    desc.append("📲 Comunidade WhatsApp: https://chat.whatsapp.com/FoYriHLCUtTA6idPH8crz7")
    desc.append("=" * 60)

    desc.append("\n🔍 PESQUISAS RELACIONADAS / RELATED SEARCHES (SEO CLOUD):")
    # Usa as tags extraídas do autocomplete para criar um parágrafo SEO forte
    desc.append(f"{tags_caixa}")

    desc.append("\n📌 HASHTAGS:")
    if hashtags:
        desc.append(" ".join(hashtags))
    else:
        clean_g = re.sub(r'[^a-zA-Z0-9]', '', jogo)
        desc.append(f"#{clean_g} #{clean_g}Mod #{clean_g}Android #{clean_g}PPSSPP #ModApk #{ANO_ATUAL}")

    return "\n".join(desc)

def executar_gerador():
    jogo = os.getenv("GAME_NAME", "Avakin Life").strip()
    versao = os.getenv("GAME_VERSION", "1.0.0").strip()
    categoria = os.getenv("CATEGORY", "android").strip().lower()
    idioma_modo = os.getenv("LANGUAGE_MODE", "ambos").strip().lower()

    print("=" * 80)
    print(f"🤖 ROBÔ SEO YOUTUBE TURBO - SISTEMA PENTA-BOT 2.0: {jogo.upper()} {versao}")
    print(f"📂 Categoria: {categoria.upper()} | Público: {idioma_modo.upper()}")
    print("=" * 80)

    # 1. BOT 1 - Topo e Títulos
    titulos_reais, video_ids, mod_terms_titulos = bot_1_minerador_topo(jogo, categoria)

    print("\n🔥 TOP 4 TÍTULOS DE ALTA PERFORMANCE (ANTI-STRIKE & SEO):")
    print("-" * 80)
    if len(titulos_reais) >= 4:
        for i, t in enumerate(titulos_reais[:4], 1):
            print(f"{i}. 🚀 {t}")
    else:
        v_str = f" v{versao}" if versao else ""
        if categoria == "android":
            fallback = [
                f"{jogo.upper()}{v_str} MOD MENU SHOWCASE ATUALIZADO {ANO_ATUAL}",
                f"{jogo.upper()}{v_str} MOD APK UNLIMITED RESOURCES MEDIAFIRE",
                f"COMO BAIXAR {jogo.upper()}{v_str} MOD ATUALIZADO NO ANDROID",
                f"{jogo.upper()}{v_str} GAMEPLAY & FULL SHOWCASE TUTORIAL"
            ]
        else:
            fallback = [
                f"{jogo.upper()} PPSSPP ISO DOWNLOAD MEDIAFIRE ATUALIZADO",
                f"COMO BAIXAR E INSTALAR {jogo.upper()} NO PPSSPP ANDROID 60FPS",
                f"{jogo.upper()} PPSSPP BEST SETTINGS & SAVE DATA COMPLETE",
                f"{jogo.upper()} PSP ISO + TEXTURES HD SHOWCASE"
            ]
        for i, t in enumerate(fallback, 1):
            print(f"{i}. 🚀 {t}")

    # 2. BOT 2 - Hashtags de Descrição
    hashtags_massivas = bot_2_super_raspador_hashtags(video_ids, jogo)

    # 3. BOT 3 & 4 - Autocomplete Profundo e Caixa de Tags
    buscas_bot3 = bot_3_autocomplete_deep(jogo, categoria, idioma_modo, mod_terms_titulos)
    tags_caixa_final = bot_4_inteligencia_cruzada(buscas_bot3, video_ids, jogo, categoria, mod_terms_titulos)

    print("\n📌 CAIXA DE TAGS DE BUSCA (500 CARACTERES - PRONTA PARA COPIAR):")
    print("-" * 80)
    print(tags_caixa_final)
    print("-" * 80)
    print(f"📊 Total de caracteres utilizados: {len(tags_caixa_final)}/500")

    # 4. BOT 5 - Descrição Completa Gerada Otimizada
    descricao_completa = bot_5_gerador_descricao_e_ctr(jogo, versao, categoria, idioma_modo, hashtags_massivas, tags_caixa_final)

    print("\n📝 DESCRIÇÃO COMPLETA PARA O YOUTUBE (BILINGUE + LINKS + HASHTAGS):")
    print("-" * 80)
    print(descricao_completa)
    print("=" * 80)

if __name__ == "__main__":
    executar_gerador()
