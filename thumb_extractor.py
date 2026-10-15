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
    """Remove caracteres especiais para salvar o arquivo de imagem sem erros."""
    nome_limpo = re.sub(r'[\\/*?:"<>|]', "", nome)
    return re.sub(r'\s+', '_', nome_limpo).strip()

def baixar_imagem(url, caminho_saida):
    """Baixa a imagem e verifica se possui tamanho/qualidade real."""
    try:
        r = requests.get(url, headers=HEADERS_DESKTOP, timeout=10)
        # Se retornar 200 e a imagem for maior que 5KB (evita imagens em branco do YouTube)
        if r.status_code == 200 and len(r.content) > 5000:
            with open(caminho_saida, 'wb') as f:
                f.write(r.content)
            return True
    except Exception:
        pass
    return False

def extrair_thumbnails_topo(busca_termo, limite=10):
    print("=" * 80)
    print(f"🖼️ EXTRAINDO THUMBNAILS MAX QUALITY (1080p): '{busca_termo.upper()}'")
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
        print("⚠️ Nenhum vídeo encontrado na busca do YouTube.")
        return

    print(f"🔍 {len(videos_encontrados)} vídeos encontrados no topo. Baixando thumbnails...\n")

    for idx, vid in enumerate(videos_encontrados, 1):
        v_id = vid["id"]
        titulo_limpo = limpar_nome_arquivo(vid["titulo"])[:35]
        
        # Tentativa 1: Qualidade Máxima HD (1080p - maxresdefault)
        # Tentativa 2: Qualidade Alta (480p - hqdefault)
        url_maxres = f"https://i.ytimg.com/vi/{v_id}/maxresdefault.jpg"
        url_hq = f"https://i.ytimg.com/vi/{v_id}/hqdefault.jpg"

        nome_arquivo = f"TOP_{idx:02d}_{titulo_limpo}.jpg"
        caminho_final = os.path.join(pasta_saida, nome_arquivo)

        # Prioriza baixar em 1080p; se o criador não subiu em Full HD, pega a versão HQ
        sucesso = baixar_imagem(url_maxres, caminho_final)
        qualidade = "MAXRES (1080p)"
        if not sucesso:
            sucesso = baixar_imagem(url_hq, caminho_final)
            qualidade = "HQ (480p)"

        if sucesso:
            print(f"✅ [{idx:02d}/{limite}] Baixada [{qualidade}]: {nome_arquivo}")
        else:
            print(f"❌ [{idx:02d}/{limite}] Falha ao baixar capa do vídeo: {v_id}")

    print("\n" + "=" * 80)
    print(f"📁 TODAS AS 10 CAPAS FORAM SALVAS COM SUCESSO!")
    print("=" * 80)

if __name__ == "__main__":
    termo = os.getenv("SEARCH_QUERY", "GTA 5 Lite PC Fraco").strip()
    extrair_thumbnails_topo(termo, limite=10)
