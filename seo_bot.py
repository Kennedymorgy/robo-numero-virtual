import os
import requests
import datetime

# Pega o ano atual automaticamente (ex: 2026)
ANO_ATUAL = datetime.datetime.now().year

def buscar_autocomplete_yt(termo, lang="pt"):
    """Consulta o autocomplete oficial do YouTube em tempo real."""
    gl = "BR" if lang == "pt" else "US"
    hl = "pt" if lang == "pt" else "en"
    url = f"http://suggestqueries.google.com/complete/search?client=firefox&ds=yt&q={termo}&gl={gl}&hl={hl}"
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    
    try:
        r = requests.get(url, headers=headers, timeout=5)
        if r.status_code == 200:
            return r.json()[1]
    except Exception:
        pass
    return []

def gerar_sementes_busca(jogo, versao, categoria):
    """Gera variações estratégicas de pesquisa para puxar as tags mais fortes."""
    sementes = []
    
    if categoria == "android":
        # Sementes em Português
        sementes.extend([
            f"{jogo} mod apk",
            f"{jogo} mod menu",
            f"{jogo} dinheiro infinito",
            f"{jogo} {ANO_ATUAL}",
            f"{jogo} mod apk {ANO_ATUAL}",
            f"{jogo} atualizado"
        ])
        if versao:
            sementes.append(f"{jogo} {versao}")
            sementes.append(f"{jogo} {versao} mod apk")
            
        # Sementes em Inglês (Para atrair tráfego internacional)
        sementes.extend([
            f"{jogo} unlimited money",
            f"{jogo} mod apk {ANO_ATUAL} mediafire",
            f"{jogo} mod menu {ANO_ATUAL}"
        ])
        
    elif categoria == "ppsspp":
        # Sementes específicas para PPSSPP/PSP
        sementes.extend([
            f"{jogo} ppsspp",
            f"{jogo} ppsspp pt br",
            f"{jogo} iso ppsspp",
            f"{jogo} ppsspp download",
            f"{jogo} ppsspp {ANO_ATUAL}",
            f"{jogo} save data ppsspp",
            f"{jogo} texturas hd ppsspp",
            f"{jogo} ppsspp mediafire"
        ])
        if versao:
            sementes.append(f"{jogo} {versao} ppsspp")
            
    return sementes

def construir_descricao(jogo, versao, categoria, tags_principais):
    site_url = "https://k-404modapk.blogspot.com"
    versao_str = f"({versao})" if versao else f"({ANO_ATUAL})"
    
    if categoria == "android":
        tipo_conteudo = "Mod Menu / Recursos Desbloqueados"
    else:
        tipo_conteudo = "ISO Emulação / Tradução PT-BR / Save Data"

    descricao = f"""📥 DOWNLOAD E MAIS DETALHES NO SITE OFICIAL:
👉 {site_url}

🎮 SOBRE O VÍDEO - {jogo.upper()} {versao_str}:
Confira a apresentação completa e gameplay de {jogo} {versao_str}. 
Análise de performance, instalação e novidades do {tipo_conteudo}.

📌 TÓPICOS PESQUISADOS E ABORDADOS:
• {tags_principais[0] if len(tags_principais) > 0 else jogo}
• {tags_principais[1] if len(tags_principais) > 1 else jogo + ' atualizado'}
• {tags_principais[2] if len(tags_principais) > 2 else jogo + ' download'}
• {tags_principais[3] if len(tags_principais) > 3 else jogo + ' gameplay'}

--------------------------------------------------
⚠️ AVISO LEGAL DE DIREITOS E ISENÇÃO DE RESPONSABILIDADE:
Este vídeo possui caráter puramente demonstrativo e educativo, focado em emulação, testes de desempenho e tutoriais de otimização. Todos os direitos sobre o jogo e marcas registradas pertencem aos seus respetivos desenvolvedores e proprietários.
--------------------------------------------------
"""
    return descricao

def executar_gerador():
    jogo = os.getenv("GAME_NAME", "FR Legends").strip()
    versao = os.getenv("GAME_VERSION", "").strip()
    categoria = os.getenv("CATEGORY", "android").strip().lower()

    print("=" * 70)
    print(f"🔥 BUSCANDO AS TAGS MAIS FORTES DA SEMANA PARA: {jogo.upper()}")
    print(f"📂 Categoria: {categoria.upper()} | Versão: {versao if versao else 'Mais recente'}")
    print("=" * 70)

    sementes = gerar_sementes_busca(jogo, versao, categoria)
    
    brutas_tags = []
    for semente in sementes:
        brutas_tags.extend(buscar_autocomplete_yt(semente, lang="pt"))
        brutas_tags.extend(buscar_autocomplete_yt(semente, lang="en"))

    # Remover duplicadas mantendo a ordem de relevância
    tags_unicas = list(dict.fromkeys(brutas_tags))

    # Filtrar tags inúteis ou curtas demais
    tags_filtradas = [t for t in tags_unicas if len(t) > 3]

    # Preencher a caixa de 500 caracteres
    tags_finais = []
    tamanho_total = 0
    for t in tags_filtradas:
        if tamanho_total + len(t) + 2 <= 500:
            tags_finais.append(t)
            tamanho_total += len(t) + 2
        else:
            break

    caixa_tags = ", ".join(tags_finais)

    # 1. Sugestões de Títulos Anti-Strike (Alto CTR)
    print("\n🚀 TÍTULOS DE ALTO CTR E PROTEGIDOS CONTRA STRIKE:")
    print("-" * 70)
    if categoria == "android":
        ver_tag = versao if versao else f"v{ANO_ATUAL}"
        print(f"1. 🔥 {jogo.upper()} {ver_tag} MOD APK (DINHEIRO INFINITO / MOD MENU) ATUALIZADO!")
        print(f"2. COMO BAIXAR E INSTALAR {jogo.upper()} {ver_tag} COM TUDO DESBLOQUEADO")
        print(f"3. {jogo.upper()} MOD MENU {ver_tag} - TUDO LIBERADO (DOWNLOAD DIRETO)")
        print(f"4. 😱 SAIU! {jogo.upper()} {ver_tag} MOD APK ATUALIZADO + GAMEPLAY")
    else:
        print(f"1. ⚔️ {jogo.upper()} PPSSPP PT-BR (ISO + SAVE DATA) ATUALIZADO!")
        print(f"2. COMO BAIXAR E JOGAR {jogo.upper()} NO PPSSPP (TEXTURAS HD / DUBLADO)")
        print(f"3. {jogo.upper()} PPSSPP ISO MEDIAFIRE - TUDO DESBLOQUEADO")
        print(f"4. 🎮 {jogo.upper()} PSP PT-BR - MELHOR CONFIGURAÇÃO SEM LAG")

    # 2. Descrição Pronta
    print("\n📝 DESCRIÇÃO COMPLETA (COPIE E COLE NA DESCRIÇÃO DO VÍDEO):")
    print("-" * 70)
    desc = construir_descricao(jogo, versao, categoria, tags_filtradas)
    print(desc)

    # 3. Caixa de Tags para o YouTube Studio
    print("\n📌 CAIXA DE TAGS MAIS PESQUISADAS (COPIE E COLE NO CAMPO DE TAGS):")
    print("-" * 70)
    print(caixa_tags)
    print("-" * 70)
    print(f"📊 Total de caracteres utilizados: {len(caixa_tags)}/500")

if __name__ == "__main__":
    executar_gerador()
