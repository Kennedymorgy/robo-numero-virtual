import os
import sys
import yt_dlp

def baixar_video_yt(url, apenas_audio=False):
    pasta_saida = "downloads_videos"
    os.makedirs(pasta_saida, exist_ok=True)

    print("=" * 80)
    print(f"🚀 INICIANDO DOWNLOAD DO VÍDEO DO YOUTUBE")
    print(f"🔗 URL: {url}")
    print("=" * 80)

    # Configurações do yt-dlp para pegar a melhor qualidade disponível (1080p / 4K)
    if apenas_audio:
        ydl_opts = {
            'format': 'bestaudio/best',
            'outtmpl': f'{pasta_saida}/%(title)s.%(ext)s',
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }],
        }
    else:
        ydl_opts = {
            'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
            'outtmpl': f'{pasta_saida}/%(title)s.%(ext)s',
            'merge_output_format': 'mp4',
        }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
        print("\n" + "=" * 80)
        print("✅ DOWNLOAD CONCLUÍDO COM SUCESSO!")
        print(f"📁 Salvo na pasta: '{pasta_saida}/'")
        print("=" * 80)
    except Exception as e:
        print(f"\n❌ Erro ao baixar o vídeo: {e}")

if __name__ == "__main__":
    url_input = os.getenv("VIDEO_URL", "").strip()
    modo_audio = os.getenv("ONLY_AUDIO", "false").strip().lower() == "true"

    if not url_input:
        print("❌ Nenhuma URL fornecida!")
        sys.exit(1)

    baixar_video_yt(url_input, apenas_audio=modo_audio)
