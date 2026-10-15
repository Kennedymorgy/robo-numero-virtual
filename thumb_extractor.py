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
    """Remove caracteres inválidos para salvar o nome do arquivo da imagem."""
    return re.sub(r'[\\/*?:"<>|]', "", nome).strip()

def baixar_imagem(url, caminho_saida):
    """Tenta baixar a imagem. Se a versão em 1080p (maxresdefault) não existir, pega a versão HD (hqdefault)."""
    try:
        r = requests.get(url, headers=HEADERS_DESKTOP, timeout=10)
        if r.status_code == 200 and len(r.content) > 1000:  # Garante que não é uma imagem genérica/quebrada
            with open(caminho_saida, 'wb') as f:
                f.write(r.content)
            return True
    except Exception:
        pass
    return False

def extrair_thumbnails_topo(busca_termo, limite=10):
    print("=" * 80)
    print(f"🖼️ EXTRAINDO THUMBNAILS DOS TOP {limite} VÍDEOS: '{busca_termo.upper()}'")
    print("=" * 80)

    url = f"https://www.youtube.com/results?search_query={urllib.parse.quote(busca_termo)}"
    
    # Cria pasta para salvar as imagens
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
                            
                            if v_id and title:
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
        print("⚠️ Nenhum vídeo encontrado. Verifique a conexão ou a busca.")
        return

    print(f"\n🔍 Encontrados {len(videos_encontrados)} vídeos no topo. Baixando capas em alta qualidade...\n")

    for idx, vid in enumerate(videos_encontrados, 1):
        v_id = vid["id"]
        titulo_limpo = limpar_nome_arquivo(vid["titulo"])[:40]  # Limita o tamanho do nome do arquivo
        
        # O YouTube possui padrão de URLs para thumbnails:
        url_maxres = f"https://i.ytimg.com/vi/{v_id}/maxresdefault.jpg"  # Full HD (1080p)
        url_hq = f"https://i.ytimg.com/vi/{v_id}/hqdefault.jpg"          # HD Padrão (480p)

        nome_arquivo = f"{idx:02d}_{v_id}_{titulo_limpo}.jpg"
        caminho_final = os.path.join(pasta_saida, nome_arquivo)

        # Tenta baixar a MaxRes primeiro; se não existir, baixa a HQ
        sucesso = baixar_imagem(url_maxres, caminho_final)
        if not sucesso:
            sucesso = baixar_imagem(url_hq, caminho_final)

        if sucesso:
            print(f"✅ [{idx:02d}/{limite}] Baixada com sucesso: {nome_arquivo}")
            print(f"   🔗 Link original: https://youtu.be/{v_id}")
        else:
            print(f"❌ [{idx:02d}/{limite}] Falha ao baixar thumbnail do vídeo: {v_id}")

    print("\n" + "=" * 80)
    print(f"📁 TODAS AS THUMBNAILS FORAM SALVAS NA PASTA: '{pasta_saida}/'")
    print("=" * 80)

if __name__ == "__main__":
    # Pega o termo das variáveis de ambiente ou usa um valor padrão de teste
    termo = os.getenv("SEARCH_QUERY", "GTA 5 Lite PC Fraco").strip()
    extrair_thumbnails_topo(termo, limite=10)
