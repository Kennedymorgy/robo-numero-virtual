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

# Lixo de sistema, canais genéricos e consoles que gastam espaço das suas tags
LIXO_PLATA FORMAS_E_CANANIS = {
    'vídeo', 'compartilhamento', 'celular com câmera', 'videofone', 'gratuito', 'envio',
    'video', 'sharing', 'camera phone', 'free', 'upload', 'youtube', 'yt', 'shorts',
    'mobile', 'cell phone', 'phone', 'app', 'google', 'menu', 'header', 'button', 'icon',
    'search', 'player', 'zippy', 'a11y', 'country', 'masthead', 'logo', 'fyp', 'tiktok',
    'viral', 'foryou', 'sub', 'subscribe', 'like', 'comment',
    'ps3', 'ps4', 'ps5', 'xbox 360', 'xbox one', 'xbox series', 'nintendo', 'switch',
    'brksedu', 'alanzoka', 'gameplayrj', 'lipao', 'dazinho', 'combination'
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

def eh_hashtag_valida(ht_raw):
    ht = ht_raw.lower().replace("#", "").strip()
    if len(ht) < 2 or ht.isdigit() or ht in LIXO_PLATA FORMAS_E_CANANIS or eh_hex_color(ht):
        return False
    return True

def buscar_autocomplete_yt(termo, lang="pt", country="BR"):
    """Consulta o serviço oficial de autocomplete do YouTube em tempo real."""
    url = f"http://suggestqueries.google.com/complete/search?client=firefox&ds=yt&q={urllib.parse.quote(termo)}&gl={country}&hl={lang}"
    try:
        r = requests.get(url, headers=HEADERS_DESKTOP, timeout=5)
        if r.status_code == 200:
            return r.json()[1]
    except Exception:
        pass
    return []

# ==============================================================================
# SISTEMA DE 6 BOTS DEDICADOS POR PLATAFORMA (ANDROIDE, PPSSPP, PC)
# ==============================================================================

# --- PLATAFORMA 1: ANDROID ---
def bot_1_minerador_android(jogo_clean, idioma_modo):
    """BOT 1: Minera exclusivamente buscas reais de Android APK."""
    queries_pt = [
        f"{jogo_clean} mod apk", f"{jogo_clean} mod menu", f"{jogo_clean} dinheiro infinito",
        f"{jogo_clean} mediafire", f"{jogo_clean} atualizado", f"como baixar {jogo_clean} mod"
    ]
    queries_en = [
        f"{jogo_clean} mod apk", f"{jogo_clean} mod menu", f"{jogo_clean} unlimited money",
        f"{jogo_clean} mediafire link", f"{jogo_clean} latest version", f"{jogo_clean} gameplay android"
    ]
    resultados = []
    if idioma_modo in ["ambos", "pt_br"]:
        for q in queries_pt:
            resultados.extend(buscar_autocomplete_yt(q, "pt", "BR"))
    if idioma_modo in ["ambos", "ingles"]:
        for q in queries_en:
            resultados.extend(buscar_autocomplete_yt(q, "en", "US"))
    return resultados

def bot_2_filtro_android(buscas_brutas, jogo_clean):
    """BOT 2: Filtra e consolida tags estritas para Android."""
    frequencia = Counter()
    termo_map = {}
    for cand in buscas_brutas:
        c_clean = re.sub(r'[^\w\s\-\/]', '', cand).strip()
        c_lower = c_clean.lower()
        if len(c_clean) <= 3 or c_lower in LIXO_PLATA FORMAS_E_CANANIS or "ppsspp" in c_lower or "pc " in c_lower:
            continue
        if any(p in c_lower for p in jogo_clean.lower().split()):
            frequencia[c_lower] += 1
            if c_lower not in termo_map:
                termo_map[c_lower] = c_clean
    return termo_map, frequencia

# --- PLATAFORMA 2: PPSSPP ---
def bot_3_minerador_ppsspp(jogo_clean, idioma_modo):
    """BOT 3: Minera exclusivamente buscas reais de PPSSPP / PSP."""
    queries_pt = [
        f"{jogo_clean} ppsspp iso", f"{jogo_clean} psp mediafire", f"como baixar {jogo_clean} ppsspp",
        f"{jogo_clean} psp android", f"{jogo_clean} ppsspp save data", f"{jogo_clean} ppsspp texturas hd"
    ]
    queries_en = [
        f"{jogo_clean} ppsspp iso download", f"{jogo_clean} psp mediafire", f"how to download {jogo_clean} ppsspp",
        f"{jogo_clean} ppsspp android", f"{jogo_clean} ppsspp best settings"
    ]
    resultados = []
    if idioma_modo in ["ambos", "pt_br"]:
        for q in queries_pt:
            resultados.extend(buscar_autocomplete_yt(q, "pt", "BR"))
    if idioma_modo in ["ambos", "ingles"]:
        for q in queries_en:
            resultados.extend(buscar_autocomplete_yt(q, "en", "US"))
    return resultados

def bot_4_filtro_ppsspp(buscas_brutas, jogo_clean):
    """BOT 4: Filtra e consolida tags estritas para PPSSPP."""
    frequencia = Counter()
    termo_map = {}
    for cand in buscas_brutas:
        c_clean = re.sub(r'[^\w\s\-\/]', '', cand).strip()
        c_lower = c_clean.lower()
        if len(c_clean) <= 3 or c_lower in LIXO_PLATA FORMAS_E_CANANIS or "apk" in c_lower:
            continue
        if any(p in c_lower for p in jogo_clean.lower().split()):
            frequencia[c_lower] += 1
            if c_lower not in termo_map:
                termo_map[c_lower] = c_clean
    return termo_map, frequencia

# --- PLATAFORMA 3: PC ---
def bot_5_minerador_pc(jogo_clean, idioma_modo):
    """BOT 5: Minera exclusivamente buscas reais de Jogos para PC."""
    queries_pt = [
        f"{jogo_clean} pc fraco", f"{jogo_clean} como baixar", f"{jogo_clean} pc",
        f"{jogo_clean} download mediafire", f"{jogo_clean} gameplay pt br",
        f"{jogo_clean} requisitos minimos", f"como rodar {jogo_clean} em pc fraco"
    ]
    queries_en = [
        f"{jogo_clean} low end pc", f"{jogo_clean} pc download", f"how to run {jogo_clean} on low end pc",
        f"{jogo_clean} system requirements", f"{jogo_clean} pc gameplay", f"{jogo_clean} full game pc"
    ]
    resultados = []
    if idioma_modo in ["ambos", "pt_br"]:
        for q in queries_pt:
            resultados.extend(buscar_autocomplete_yt(q, "pt", "BR"))
    if idioma_modo in ["ambos", "ingles"]:
        for q in queries_en:
            resultados.extend(buscar_autocomplete_yt(q, "en", "US"))
    return resultados

def bot_6_filtro_pc(buscas_brutas, jogo_clean):
    """BOT 6: Filtra e consolida tags estritas para PC (Elimina lixo de celula e consoles)."""
    frequencia = Counter()
    termo_map = {}
    
    # Bloqueia vazamento de pesquisas de celular em tags de PC
    termos_bloqueados_pc = ['celular', 'mobile', 'apk', 'android', 'ps3', 'ps4', 'xbox', 'emulator']

    for cand in buscas_brutas:
        c_clean = re.sub(r'[^\w\s\-\/]', '', cand).strip()
        
        # Atualiza ano
        for ano_antigo in range(2015, ANO_ATUAL):
            c_clean = re.sub(r'\b' + str(ano_antigo) + r'\b', str(ANO_ATUAL), c_clean, flags=re.IGNORECASE)

        c_lower = c_clean.lower()

        if len(c_clean) <= 3 or c_lower in LIXO_PLATA FORMAS_E_CANANIS:
            continue

        if any(b in c_lower for b in termos_bloqueados_pc):
            continue

        if any(p in c_lower for p in jogo_clean.lower().split()):
            pontos = 1
            if any(k in c_lower for k in ['pc fraco', 'como baixar', 'download', 'requisitos', 'gameplay', 'low end']):
                pontos += 3
            frequencia[c_lower] += pontos
            if c_lower not in termo_map:
                termo_map[c_lower] = c_clean

    return termo_map, frequencia

# ==============================================================================
# PROCESSADOR GERAL & MOTOR DE MONTAGEM
# ==============================================================================

def extrair_titulos_reais_topo(jogo_clean, categoria):
    """Extrai títulos reais do topo do YouTube com base na categoria exata."""
    if categoria == "pc":
        termo = f"{jogo_clean} pc fraco"
    elif categoria == "android":
        termo = f"{jogo_clean} mod apk"
    else:
        termo = f"{jogo_clean} ppsspp iso"

    url = f"https://www.youtube.com/results?search_query={urllib.parse.quote(termo)}"
    titulos = []
    
    try:
        res = requests.get(url, headers=HEADERS_DESKTOP, cookies=COOKIES_YT, timeout=8)
        if res.status_code == 200:
            match = re.search(r'var ytInitialData\s*=\s*({.*?});</script>', res.text, re.DOTALL)
            if match:
                data = json.loads(match.group(1))
                contents = data.get('contents', {}).get('twoColumnSearchResultsRenderer', {}).get('primaryContents', {}).get('sectionListRenderer', {}).get('contents', [])
                for section in contents:
                    item_list = section.get('itemSectionRenderer', {}).get('contents', [])
                    for item in item_list:
                        if 'videoRenderer' in item:
                            title = item['videoRenderer'].get('title', {}).get('runs', [{}])[0].get('text', '')
                            if title and len(title) > 8 and title not in titulos:
                                titulos.append(limpar_titulo_anti_strike(title))
                        if len(titulos) >= 4:
                            break
    except Exception:
        pass

    return titulos

def montar_caixa_tags_500(termo_map, frequencia):
    """Garante exatamente até 500 caracteres ordenados por relevância."""
    termos_ordenados = sorted(frequencia.keys(), key=lambda x: frequencia[x], reverse=True)
    tags_finais = []
    tamanho_total = 0

    for t_key in termos_ordenados:
        t_orig = termo_map[t_key]
        custo = len(t_orig) + 2 if tags_finais else len(t_orig)
        if tamanho_total + custo <= 500:
            tags_finais.append(t_orig)
            tamanho_total += custo
        else:
            break

    return ", ".join(tags_finais)

def gerar_descricao_seo(jogo_clean, versao, categoria, tags_caixa):
    """Gera a descrição otimizada para o YouTube."""
    ver_str = f" {versao}" if versao else ""
    cat_label = "PC (PC Fraco / Otimizado)" if categoria == "pc" else ("Android Mod APK" if categoria == "android" else "PPSSPP / PSP ISO")

    desc = []
    desc.append(f"🎮 {jogo_clean.upper()}{ver_str} - {cat_label} ({ANO_ATUAL})")
    desc.append("=" * 60)

    if categoria == "pc":
        desc.append(f"Confira no vídeo de hoje a gameplay e demonstração de {jogo_clean}{ver_str} rodando no PC! Veja como baixar, configurar e testar no seu PC fraco ou forte com a melhor performance.")
        desc.append(f"\nFull gameplay and tutorial for {jogo_clean}{ver_str} on PC! Check performance, system requirements, and installation guide.")
        desc.append("\n💻 REQUISITOS MÍNIMOS RECOMENDADOS:")
        desc.append("• Sistema Operacional: Windows 10 / 11 (64 bits)")
        desc.append("• Processador: Dual Core 2.0 GHz / Intel Core i3")
        desc.append("• Memória RAM: 2 GB / 4 GB RAM")
        desc.append("• Placa de Vídeo: Intel HD Graphics / Integrated GPU")
    elif categoria == "android":
        desc.append(f"Confira a demonstração completa de {jogo_clean}{ver_str} totalmente atualizado! Aprenda o passo a passo de instalação no seu Android.")
    else:
        desc.append(f"Confira a melhor configuração, ISO e Save Data para {jogo_clean}{ver_str} no emulador PPSSPP! Gameplay fluída em 60 FPS.")

    desc.append("\n" + "=" * 60)
    desc.append("⬇️ ÁREA DE DOWNLOAD & SUPORTE / DOWNLOAD LINKS:")
    desc.append("👉 Link do Jogo / Official Download Link: [INSERIR_LINK_AQUI]")
    desc.append("💬 Grupo do Telegram (Suporte & Pedidos): https://t.me/k404_modapk")
    desc.append("📲 Comunidade WhatsApp: https://chat.whatsapp.com/FoYriHLCUtTA6idPH8crz7")
    desc.append("=" * 60)

    desc.append("\n🔍 PESQUISAS RELACIONADAS / RELATED SEARCHES (SEO CLOUD):")
    desc.append(f"{tags_caixa}")

    clean_hash = re.sub(r'[^a-zA-Z0-9]', '', jogo_clean)
    desc.append(f"\n📌 HASHTAGS:\n#{clean_hash} #{clean_hash}{categoria.upper()} #{clean_hash}Gameplay #Download #{ANO_ATUAL}")

    return "\n".join(desc)

def executar_gerador():
    jogo_raw = os.getenv("GAME_NAME", "GTA 5 Lite").strip()
    versao = os.getenv("GAME_VERSION", "").strip()
    categoria = os.getenv("CATEGORY", "pc").strip().lower()
    idioma_modo = os.getenv("LANGUAGE_MODE", "ambos").strip().lower()

    # Formatação limpa do nome do jogo
    jogo_clean = re.sub(r'[\(\)]', '', jogo_raw).strip()

    print("=" * 80)
    print(f"🤖 ROBÔ SEO YOUTUBE TURBO 5.0 (SISTEMA COM 6 BOTS): {jogo_clean.upper()} {versao}")
    print(f"📂 Categoria: {categoria.upper()} | Público Idioma: {idioma_modo.upper()}")
    print("=" * 80)

    # Execução baseada na plataforma selecionada
    if categoria == "android":
        print("[+] Ativando BOTS 1 & 2 (Especialistas em Android APK)...")
        buscas = bot_1_minerador_android(jogo_clean, idioma_modo)
        termo_map, freq = bot_2_filtro_android(buscas, jogo_clean)
    elif categoria == "ppsspp":
        print("[+] Ativando BOTS 3 & 4 (Especialistas em PPSSPP / PSP)...")
        buscas = bot_3_minerador_ppsspp(jogo_clean, idioma_modo)
        termo_map, freq = bot_4_filtro_ppsspp(buscas, jogo_clean)
    else:  # PC
        print("[+] Ativando BOTS 5 & 6 (Especialistas em Jogos para PC)...")
        buscas = bot_5_minerador_pc(jogo_clean, idioma_modo)
        termo_map, freq = bot_6_filtro_pc(buscas, jogo_clean)

    # 1. Títulos do topo em tempo real
    titulos = extrair_titulos_reais_topo(jogo_clean, categoria)
    print("\n🔥 TOP TÍTULOS DE ALTA PERFORMANCE (ANTI-STRIKE & SEO REAL):")
    print("-" * 80)
    if titulos:
        for i, t in enumerate(titulos, 1):
            print(f"{i}. 🚀 {t}")
    else:
        v_str = f" {versao}" if versao else ""
        if categoria == "pc":
            print(f"1. 🚀 COMO BAIXAR {jogo_clean.upper()}{v_str} PARA PC FRACO (SEM PLACA DE VÍDEO) - {ANO_ATUAL}")
            print(f"2. 🚀 {jogo_clean.upper()}{v_str} PC FRACO - GAMEPLAY PT-BR + DOWNLOAD MEDIAFIRE")
            print(f"3. 🚀 HOW TO DOWNLOAD AND RUN {jogo_clean.upper()}{v_str} ON LOW END PC ({ANO_ATUAL})")
            print(f"4. 🚀 {jogo_clean.upper()}{v_str} FULL PC PERFORMANCE TEST & TUTORIAL")

    # 2. Caixa de Tags 500 Caracteres
    tags_500 = montar_caixa_tags_500(termo_map, freq)
    print("\n📌 CAIXA DE TAGS DE BUSCA (500 CARACTERES - PT-BR & EN-US MISTURADOS E REAIS):")
    print("-" * 80)
    print(tags_500)
    print("-" * 80)
    print(f"📊 Total de caracteres utilizados: {len(tags_500)}/500")

    # 3. Descrição SEO
    descricao = gerar_descricao_seo(jogo_clean, versao, categoria, tags_500)
    print("\n📝 DESCRIÇÃO COMPLETA PARA O YOUTUBE (BILINGUE + LINKS + HASHTAGS):")
    print("-" * 80)
    print(descricao)
    print("=" * 80)

if __name__ == "__main__":
    executar_gerador()
