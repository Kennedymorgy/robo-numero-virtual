import os
import requests
import datetime
import re

ANO_ATUAL = datetime.datetime.now().year

def buscar_autocomplete_yt(termo, lang="pt", country="BR"):
    """Consulta a API do Autocomplete do YouTube em tempo real."""
    url = f"http://suggestqueries.google.com/complete/search?client=firefox&ds=yt&q={termo}&gl={country}&hl={lang}"
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    try:
        r = requests.get(url, headers=headers, timeout=5)
        if r.status_code == 200:
            return r.json()[1]
    except Exception:
        pass
    return []

def gerar_sementes_busca(jogo, versao, categoria, idioma_modo):
    """Gera combinações profundas de busca incluindo Cheto, Auto Play, Mod Menu, etc."""
    sementes = []
    
    # Termos brutosa Android em PT e EN
    termos_android_pt = [
        "mod apk", "mod menu", "dinheiro infinito", "tudo liberado", 
        "atualizado", "cheto", "auto play", "linha infinita", "mediafire", "apk mod"
    ]
    termos_android_en = [
        "mod apk", "mod menu", "unlimited money", "cheto", "auto play", 
        "long line", "aim tool", "latest version", "unlocked", "gameplay mod"
    ]
    
    # Termos brutosa PPSSPP em PT e EN
    termos_psp_pt = [
        "ppsspp", "iso ppsspp", "ppsspp pt br", "save data", 
        "texturas hd", "dublado", "mediafire iso", "ppsspp mod"
    ]
    termos_psp_en = [
        "ppsspp iso", "ppsspp gameplay", "best settings ppsspp", 
        "save data 100", "hd texture ppsspp", "psp iso download"
    ]

    termo_base = f"{jogo} {versao}".strip() if versao else jogo

    if categoria == "android":
        if idioma_modo in ["ambos", "pt_br"]:
            for t in termos_android_pt:
                sementes.append(f"{termo_base} {t}")
                if versao: sementes.append(f"{jogo} {t} {versao}")
        if idioma_modo in ["ambos", "ingles"]:
            for t in termos_android_en:
                sementes.append(f"{termo_base} {t}")
                if versao: sementes.append(f"{jogo} {t} {versao}")
    else: # PPSSPP
        if idioma_modo in ["ambos", "pt_br"]:
            for t in termos_psp_pt:
                sementes.append(f"{termo_base} {t}")
        if idioma_modo in ["ambos", "ingles"]:
            for t in termos_psp_en:
                sementes.append(f"{termo_base} {t}")

    # Adiciona buscas com ano atual
    sementes.append(f"{jogo} {ANO_ATUAL}")
    if versao:
        sementes.append(f"{jogo} {versao}")

    return list(dict.fromkeys(sementes))

def gerar_titulos_seguros(jogo, versao, categoria):
    """Gera títulos de altíssimo CTR eliminando palavras gatilho de strike."""
    v_str = f" {versao}" if versao else ""
    
    if categoria == "android":
        return [
            f"🚀 {jogo.upper()}{v_str} MOD MENU / FULL SHOWCASE & GAMEPLAY ATUALIZADO!",
            f"🔥 {jogo.upper()}{v_str} - NOVAS FUNÇÕES & RECURSOS ATIVADOS (ANDROID)",
            f"⚡ {jogo.upper()}{v_str} MOD APK (TUDO LIBERADO / UNLIMITED) - ANÁLISE COMPLETA",
            f"🎯 {jogo.upper()}{v_str} BEST MOD MENU SHOWCASE + CONFIGURAÇÃO SEGURA"
        ]
    else: # PPSSPP
        return [
            f"⚔️ {jogo.upper()}{v_str} PPSSPP PT-BR (ISO + SAVE DATA 100%) ATUALIZADO!",
            f"🎮 {jogo.upper()}{v_str} PPSSPP ISO - BEST GRAPHICS & PERFORMANCE SETTINGS",
            f"🔥 {jogo.upper()}{v_str} PSP (TEXTURAS HD / DUBLADO) - SHOWCASE GAMEPLAY",
            f"⚡ {jogo.upper()}{v_str} PPSSPP - COMO CONFIGURAR SEM LAG (ULTRA GRAPHICS)"
        ]

def construir_descricao_elegante(jogo, versao, categoria, tags_top):
    site_url = "https://k-404modapk.blogspot.com"
    v_str = f" {versao}" if versao else ""
    jogo_clean = re.sub(r'[^a-zA-Z0-9]', '', jogo)
    
    tag1 = tags_top[0] if len(tags_top) > 0 else f"{jogo} mod apk"
    tag2 = tags_top[1] if len(tags_top) > 1 else f"{jogo} mod menu"
    tag3 = tags_top[2] if len(tags_top) > 2 else f"{jogo} atualizado"
    tag4 = tags_top[3] if len(tags_top) > 3 else f"{jogo} gameplay"

    desc = f"""🔥 Procurando por {jogo.upper()}{v_str} MOD APK / MOD MENU? Você está no lugar certo!

Seja bem-vindo(a) ao canal! No vídeo de hoje trazemos uma análise detalhada e apresentação completa das melhores configurações e novos recursos do {jogo.upper()}{v_str}.

🌐 DOWNLOAD E MAIS DETALHES NO SITE OFICIAL:
👉 {site_url}

🎮 DETALHES DO CONTEÚDO EXIBIDO:
• Análise de desempenho e otimização gráfica.
• Exibição completa dos novos recursos e menus.
• Guia de configuração para melhor fluidez no Android/PPSSPP.

📌 TÓPICOS MAIS PESQUISADOS EM DESTAQUE:
✔ {tag1}
✔ {tag2}
✔ {tag3}
✔ {tag4}

--------------------------------------------------
🔎 HASHTAGS PARA ENCONTRAR O VÍDEO:
#{jogo_clean} #{jogo_clean}Mod #{jogo_clean}ModApk #{jogo_clean}PPSSPP #AndroidGames #ModMenu #{ANO_ATUAL}

--------------------------------------------------
⚠️ AVISO LEGAL E ISENÇÃO DE RESPONSABILIDADE:
Este vídeo possui caráter exclusivamente educativo e demonstrativo de performance em jogos mobile/emulação. Todos os direitos e marcas registradas pertencem aos seus respetivos criadores e desenvolvedores oficiais.
--------------------------------------------------
"""
    return desc

def executar_gerador():
    jogo = os.getenv("GAME_NAME", "FR Legends").strip()
    versao = os.getenv("GAME_VERSION", "").strip()
    categoria = os.getenv("CATEGORY", "android").strip().lower()
    idioma_modo = os.getenv("LANGUAGE_MODE", "ambos").strip().lower()

    print("=" * 75)
    print(f"🤖 ROBÔ SEO INTELIGENTE: {jogo.upper()} {versao}")
    print(f"📂 Categoria: {categoria.upper()} | Idioma: {idioma_modo.upper()}")
    print("=" * 75)

    sementes = gerar_sementes_busca(jogo, versao, categoria, idioma_modo)
    
    brutas_tags = []
    for semente in sementes:
        if idioma_modo in ["ambos", "pt_br"]:
            brutas_tags.extend(buscar_autocomplete_yt(semente, lang="pt", country="BR"))
        if idioma_modo in ["ambos", "ingles"]:
            brutas_tags.extend(buscar_autocomplete_yt(semente, lang="en", country="US"))

    # Remover duplicadas mantendo ordem
    tags_unicas = list(dict.fromkeys(brutas_tags))
    tags_filtradas = [t for t in tags_unicas if len(t) > 3]

    # Preencher limite de 500 caracteres do YouTube Studio
    tags_finais = []
    tamanho_total = 0
    for t in tags_filtradas:
        if tamanho_total + len(t) + 2 <= 500:
            tags_finais.append(t)
            tamanho_total += len(t) + 2
        else:
            break

    caixa_tags = ", ".join(tags_finais)

    # Output no Console
    print("\n🚀 TÍTULOS PROTEGIDOS E DE ALTO CTR (SEM RISCO DE BAN/STRIKE):")
    print("-" * 75)
    titulos = gerar_titulos_seguros(jogo, versao, categoria)
    for i, t in enumerate(titulos, 1):
        print(f"{i}. {t}")

    print("\n📝 DESCRIÇÃO COMPLETA E FORMATAÇÃO PREMIUM (COPIE E COLE):")
    print("-" * 75)
    print(construir_descricao_elegante(jogo, versao, categoria, tags_filtradas))

    print("\n📌 CAIXA DE TAGS MAIS BRUTAS DO MOMENTO (500 CARACTERES):")
    print("-" * 75)
    print(caixa_tags)
    print("-" * 75)
    print(f"📊 Total de caracteres utilizados: {len(caixa_tags)}/500")

if __name__ == "__main__":
    executar_gerador()
