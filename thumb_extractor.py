import os
import re
import json
import requests
import urllib.parse

HEADERS_DESKTOP = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7",
}

COOKIES_YT = {
    "CONSENT": "YES+1",
    "SOCS": "CAI"
}

def limpar_nome_arquivo(nome):
    nome_limpo = re.sub(r'[\\/*?:"<>|]', "", nome)
    return re.sub(r'\s+', '_', nome_limpo).strip()

def baixar_imagem(url, caminho_saida):
    try:
        r = requests.get(url, headers=HEADERS_DESKTOP, timeout=10)
        if r.status_code == 200 and len(r.content) > 5000:
            with open(caminho_saida, 'wb') as f:
                f.write(r.content)
            return True
    except Exception:
        pass
    return False

def gerar_galeria_html(pasta_saida, lista_thumbs, busca_termo):
    """Cria uma galeria HTML visual para você ver todas as fotos no navegador."""
    html_content = f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Galeria de Thumbnails - {busca_termo}</title>
    <style>
        body {{ font-family: Arial, sans-serif; background-color: #181818; color: #fff; padding: 20px; text-align: center; }}
        h1 {{ margin-bottom: 20px; color: #ff0000; }}
        .grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 20px; max-width: 1200px; margin: 0 auto; }}
        .card {{ background: #282828; border-radius: 10px; overflow: hidden; padding: 10px; box-shadow: 0 4px 10px rgba(0,0,0,0.5); }}
        .card img {{ width: 100%; height: auto; border-radius: 5px; display: block; }}
        .card p {{ font-size: 14px; margin: 10px 0; color: #ddd; word-break: break-word; }}
        .card a {{ display: inline-block; background: #ff0000; color: #fff; text-decoration: none; padding: 8px 15px; border-radius: 5px; font-weight: bold; margin-top: 5px; }}
        .card a:hover {{ background: #cc0000; }}
    </style>
</head>
<body>
    <h1>🖼️ Galeria TOP 15 Thumbnails: "{busca_termo}"</h1>
    <div class="grid">
"""
    for item in lista_thumbs:
        html_content += f"""
        <div class="card">
            <img src="{item['arquivo']}" alt="{item['titulo']}">
            <p><strong>#{item['posicao']}</strong> - {item['titulo']}</p>
            <a href="{item['arquivo']}" download>📥 Baixar Imagem</a>
        </div>
"""
    html_content += """
    </div>
</body>
</html>
"""
    with open(os.path.join(pasta_saida, "index.html"), "w", encoding="utf-8") as f:
        f.write(html_content)

def extrair_thumbnails_topo(busca_termo, limite=15):
    print("=" * 80)
    print(f"🖼️ EXTRAINDO TOP {limite} THUMBNAILS (MAX QUALITY 1080p): '{busca_termo.upper()}'")
    print("=" * 80)

    url = f"https://www.youtube.com/results?search_query={urllib.parse.quote(busca_termo)}"
    pasta_saida = "thumbnails_extraidas"
    os.makedirs(pasta_saida, exist_ok=True)

    videos_encontrados = []

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
                            
                            if v_id and title and v_id not in [v['id'] for v in videos_encontrados]:
                                videos_encontrados.append({
                                    "id": v_id,
                                    "titulo": title
                                })
                            if len(videos_encontrados) >= limite:
                                break
                    if len(videos_encontrados) >= limite:
                        break
    except Exception as e:
        print(f"❌ Erro ao acessar o YouTube: {e}")
        return

    if not videos_encontrados:
        print("⚠️ Nenhum vídeo encontrado.")
        return

    print(f"🔍 {len(videos_encontrados)} vídeos encontrados no topo. Baixando thumbnails...\n")

    lista_para_galeria = []

    for idx, vid in enumerate(videos_encontrados, 1):
        v_id = vid["id"]
        titulo_limpo = limpar_nome_arquivo(vid["titulo"])[:35]
        
        url_maxres = f"https://i.ytimg.com/vi/{v_id}/maxresdefault.jpg"
        url_hq = f"https://i.ytimg.com/vi/{v_id}/hqdefault.jpg"

        nome_arquivo = f"TOP_{idx:02d}_{titulo_limpo}.jpg"
        caminho_final = os.path.join(pasta_saida, nome_arquivo)

        sucesso = baixar_imagem(url_maxres, caminho_final)
        qualidade = "MAXRES (1080p)"
        if not sucesso:
            sucesso = baixar_imagem(url_hq, caminho_final)
            qualidade = "HQ (480p)"

        if sucesso:
            print(f"✅ [{idx:02d}/{limite}] Baixada [{qualidade}]: {nome_arquivo}")
            lista_para_galeria.append({
                "posicao": idx,
                "titulo": vid["titulo"],
                "arquivo": nome_arquivo
            })

    gerar_galeria_html(pasta_saida, lista_para_galeria, busca_termo)

    print("\n" + "=" * 80)
    print(f"📁 TODAS AS {len(lista_para_galeria)} CAPAS E A GALERIA FORAM SALVAS COM SUCESSO!")
    print("=" * 80)

if __name__ == "__main__":
    termo = os.getenv("SEARCH_QUERY", "Avakin Life Mod Menu").strip()
    extrair_thumbnails_topo(termo, limite=15)
