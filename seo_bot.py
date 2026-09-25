import os
import requests
import datetime
import re
import urllib.parse

ANO_ATUAL = datetime.datetime.now().year

# Cabeçalho simulando Android 13 Premium (Galaxy S23 Ultra) para evitar bloqueios
HEADERS_ANDROID13 = {
    "User-Agent": "Mozilla/5.0 (Linux; Android 13; SM-S918B Build/TP1A.220624.014) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Mobile Safari/537.36",
    "Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8"
}

def extrair_top_titulos_youtube(termo_busca):
    """Entra no YouTube em tempo real e captura os 3 títulos reais no topo das pesquisas."""
    query_encoded = urllib.parse.quote(termo_busca)
    url = f"https://www.youtube.com/results?search_query={query_encoded}"
    
    try:
        r = requests.get(url, headers=HEADERS_ANDROID13, timeout=6)
        if r.status_code == 200:
            # Busca os títulos reais no JSON embutido na página do YouTube
            titulos_encontrados = re.findall(r'"title":\{"runs":\[\{"text":"([^"]+)"\}', r.text)
            
            titulos_unicos = []
            for t in titulos_encontrados:
                # Filtra frases muito curtas ou irrelevantes do sistema
                if len(t) > 12 and t not in titulos_unicos and not t.startswith("http"):
                    titulos_unicos.append(t)
                if len(titulos_unicos) >= 3:
                    break
            return titulos_unicos
    except Exception:
        pass
    return []

def buscar_autocomplete_yt(termo, lang="pt", country="BR"):
    """Puxa as sugestões brutas e reais em tempo real da barra de pesquisa."""
    url = f"http://suggestqueries.google.com/complete/search?client=firefox&ds=yt&q={termo}&gl={country}&hl={lang}"
    try:
        r = requests.get(url, headers=HEADERS_ANDROID13, timeout=5)
        if r.status_code == 200:
            return r.json()[1]
    except Exception:
        pass
    return []

def gerar_sementes_brutas(jogo, versao, categoria, idioma_modo):
    """Gera variações de busca pesadas para capturar termos como Cheto, Sky, Mod Menu, etc."""
    sementes = []
    
    termo_base = f"{jogo} {versao}".strip() if versao else jogo

    if categoria == "android":
        mods_pt = ["mod apk", "mod menu", "dinheiro infinito", "cheto", "sky", "mediafire", "atualizado", "apk mod", "2026"]
        mods_en = ["mod apk", "mod menu", "unlimited money", "cheto", "aim tool", "long line", "latest version", "unlocked"]
        
        if idioma_modo in ["ambos", "pt_br"]:
            for m in mods_pt:
                sementes.append(f"{termo_base} {m}")
        if idioma_modo in ["ambos", "ingles"]:
            for m in mods_en:
                sementes.append(f"{termo_base} {m}")
                
    else: # PPSSPP
        psp_pt = ["ppsspp", "iso ppsspp", "ppsspp pt br", "save data 100", "texturas hd", "dublado", "mediafire iso"]
        psp_en = ["ppsspp iso", "ppsspp gameplay", "best settings ppsspp", "hd texture ppsspp", "psp iso download"]
        
        if idioma_modo in ["ambos", "pt_br"]:
            for p in psp_pt:
                sementes.append(f"{termo_base} {p}")
        if idioma_modo in ["ambos", "ingles"]:
            for p in psp_en:
                sementes.append(f"{termo_base} {p}")

    sementes.append(f"{jogo} {ANO_ATUAL}")
    return list(dict.fromkeys(sementes))

def gerar_hashtags_profissionais(jogo, categoria):
    """Gera 20 hashtags fortes e bilíngues para a descrição."""
    clean_game = re.sub(r'[^a-zA-Z0-9]', '', jogo)
    
    tags_base = [
        f"#{clean_game}", f"#{clean_game}Mod", f"#{clean_game}ModApk", f"#{clean_game}2026",
        f"#{clean_game}Gameplay", f"#{clean_game}Update", f"#{clean_game}Download",
        f"#{clean_game}Android", f"#{clean_game}PPSSPP", f"#{clean_game}Cheto",
        "#AndroidGames", "#ModMenu", "#ModApk", "#UnlimitedMoney", "#Gaming",
        "#MobileGaming", "#PPSSPP", "#PSP", "#Mediafire", f"#{ANO_ATUAL}Games"
    ]
    return " ".join(tags_base[:20])

def construir_descricao_bilingue_emocionante(jogo, versao, categoria):
    site_url = "https://k-404modapk.blogspot.com"
    v_str = f" {versao}" if versao else ""
    
    hashtags = gerar_hashtags_profissionais(jogo, categoria)

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
🔎 HASHTAGS RELACIONADAS DO VÍDEO:
{hashtags}

--------------------------------------------------
⚠️ AVISO LEGAL E ISENÇÃO DE RESPONSABILIDADE / LEGAL DISCLAIMER:
Este vídeo possui caráter puramente educativo e demonstrativo de performance em jogos mobile/emulação. Todos os direitos e marcas registradas pertencem aos seus respetivos criadores e desenvolvedores.
This video is purely educational and for performance demonstration purposes. All rights belong to their respective owners.
--------------------------------------------------
"""
    return desc

def executar_gerador():
    jogo = os.getenv("GAME_NAME", "Avakin Life").strip()
    versao = os.getenv("GAME_VERSION", "").strip()
    categoria = os.getenv("CATEGORY", "android").strip().lower()
    idioma_modo = os.getenv("LANGUAGE_MODE", "ambos").strip().lower()

    print("=" * 75)
    print(f"🤖 ROBÔ SEO INTELIGENTE (ANDROID 13 ENGINE): {jogo.upper()} {versao}")
    print(f"📂 Categoria: {categoria.upper()} | Idioma: {idioma_modo.upper()}")
    print("=" * 75)

    # 1. Scraping dos Títulos Reais no YouTube
    termo_busca_yt = f"{jogo} {versao}".strip() if versao else jogo
    titulos_reais_yt = extrair_top_titulos_youtube(termo_busca_yt)

    print("\n🔥 TOP 3 TÍTULOS REAIS EM ALTA NO YOUTUBE (PULADOS DIRETO DA PESQUISA):")
    print("-" * 75)
    if titulos_reais_yt:
        for i, t in enumerate(titulos_reais_yt, 1):
            print(f"{i}. 🚀 {t}")
    else:
        v_str = f" {versao}" if versao else ""
        print(f"1. 🚀 {jogo.upper()}{v_str} MOD MENU / FULL SHOWCASE & GAMEPLAY ATUALIZADO!")
        print(f"2. 🔥 {jogo.upper()}{v_str} NOVAS FUNÇÕES & RECURSOS ATIVADOS")
        print(f"3. ⚡ {jogo.upper()}{v_str} GAMEPLAY SHOWCASE + BEST CONFIGURATION")

    # 2. Descrição Bilíngue Premium
    print("\n📝 DESCRIÇÃO BILÍNGUE E FORMATAÇÃO PREMIUM (COM 20 HASHTAGS):")
    print("-" * 75)
    print(construir_descricao_bilingue_emocionante(jogo, versao, categoria))

    # 3. Caixa de Tags Reais e Fortes
    sementes = gerar_sementes_brutas(jogo, versao, categoria, idioma_modo)
    brutas_tags = []
    
    for semente in sementes:
        if idioma_modo in ["ambos", "pt_br"]:
            brutas_tags.extend(buscar_autocomplete_yt(semente, lang="pt", country="BR"))
        if idioma_modo in ["ambos", "ingles"]:
            brutas_tags.extend(buscar_autocomplete_yt(semente, lang="en", country="US"))

    tags_unicas = list(dict.fromkeys(brutas_tags))
    tags_filtradas = [t for t in tags_unicas if len(t) > 3]

    tags_finais = []
    tamanho_total = 0
    for t in tags_filtradas:
        if tamanho_total + len(t) + 2 <= 500:
            tags_finais.append(t)
            tamanho_total += len(t) + 2
        else:
            break

    caixa_tags = ", ".join(tags_finais)

    print("\n📌 CAIXA DE TAGS MAIS BRUTAS DO MOMENTO (500 CARACTERES):")
    print("-" * 75)
    print(caixa_tags)
    print("-" * 75)
    print(f"📊 Total de caracteres utilizados: {len(caixa_tags)}/500")

if __name__ == "__main__":
    executar_gerador()
