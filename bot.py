import asyncio
import re
from urllib.parse import urljoin
from playwright.async_api import async_playwright

# 🌍 PREFIXOS PERMITIDOS (Suíça +41 removida)
PREFIXOS_ACEITOS = ['+1', '+55', '+351', '+44', '+33', '+34', '+358']

# Lista de fontes para varredura
FONTES_SMS = [
    {"nome": "Receive-SMSS", "url": "https://receive-smss.com/"},
    {"nome": "SMSToMe", "url": "https://smstome.com/country/usa"},
    {"nome": "AnonymSMS", "url": "https://anonymsms.com/"},
    {"nome": "Quackr", "url": "https://quackr.io/temporary-numbers"},
    {"nome": "TempSMSS", "url": "https://tempsmss.com/"},
    {"nome": "SMS24", "url": "https://sms24.me/en/countries/us"}
]

def extrair_numero_limpo(texto):
    """Limpa a string e valida se atende aos prefixos aceitos."""
    limpo = re.sub(r'[^\d+]', '', texto)
    if not limpo.startswith('+') and len(limpo) >= 10:
        limpo = '+' + limpo

    if 10 <= len(limpo) <= 16:
        # Rejeita explicitamente Suíça (+41)
        if limpo.startswith('+41'):
            return None
        if any(limpo.startswith(pref) for pref in PREFIXOS_ACEITOS):
            return limpo
    return None

def construir_link_direto(base_url, href, numero_limpo):
    """Garante que o link aponta diretamente para a caixa de SMS individual."""
    if not href or href == "#" or "javascript" in href:
        return None
        
    url_completa = urljoin(base_url, href)
    digitos_numero = re.sub(r'\D', '', numero_limpo)[-7:]
    
    if digitos_numero in url_completa:
        return url_completa
    return None

async def configurar_contexto_stealth(browser):
    """Cria um contexto com headers, cookies e configurações que simulam um usuário real."""
    context = await browser.new_context(
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
        viewport={"width": 1366, "height": 768},
        locale="pt-BR",
        timezone_id="America/Sao_Paulo",
        extra_http_headers={
            "Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7",
            "Sec-Ch-Ua": '"Google Chrome";v="123", "Not:A-Brand";v="8", "Chromium";v="123"',
            "Sec-Ch-Ua-Mobile": "?0",
            "Sec-Ch-Ua-Platform": '"Windows"',
            "Upgrade-Insecure-Requests": "1"
        }
    )
    
    # Adiciona cookies genéricos de sessão para parecer uma navegação recorrente
    await context.add_cookies([
        {
            "name": "session_pref",
            "value": "allow_all",
            "domain": ".receive-smss.com",
            "path": "/"
        }
    ])
    return context

async def processar_fonte(fonte, browser, semaphoro):
    """Worker (Robô) para raspar uma fonte específica de números."""
    async with semaphoro:
        numeros_encontrados = []
        context = await configurar_contexto_stealth(browser)
        page = await context.new_page()
        
        try:
            await page.goto(fonte["url"], timeout=20000, wait_until="domcontentloaded")
            await page.wait_for_timeout(1500)
            
            links = await page.locator("a").all()
            
            for link in links:
                try:
                    href = await link.get_attribute("href") or ""
                    txt = await link.inner_text()
                    
                    num_valido = extrair_numero_limpo(txt) or extrair_numero_limpo(href)
                    
                    if num_valido:
                        link_direto = construir_link_direto(fonte["url"], href, num_valido)
                        if link_direto and not any(n['numero'] == num_valido for n in numeros_encontrados):
                            numeros_encontrados.append({
                                'numero': num_valido,
                                'link': link_direto,
                                'fonte': fonte['nome']
                            })
                except Exception:
                    continue
        except Exception as e:
            print(f"  ├─ ⚠️ {fonte['nome']}: Erro de carregamento ({e})")
        finally:
            await context.close()
            
        return numeros_encontrados

async def analisar_historico_numero(item, browser, semaphoro):
    """Worker (Robô) que faz a leitura completa da página do número."""
    async with semaphoro:
        context = await configurar_contexto_stealth(browser)
        page = await context.new_page()
        
        try:
            await page.goto(item['link'], timeout=15000, wait_until="domcontentloaded")
            await page.wait_for_timeout(1000)
            
            corpo_texto = await page.inner_text("body")
            texto_lower = corpo_texto.lower()
            
            # Análise de padrões de códigos e menções do Google/YouTube
            mencoes = texto_lower.count('youtube') + texto_lower.count('google')
            codigos_g = len(re.findall(r'\bg-\d{5,6}\b', texto_lower))
            
            total_usos = mencoes + codigos_g
            item['usos_google'] = total_usos
            
        except Exception:
            item['usos_google'] = 999  # Se falhar, marca para descarte por segurança
        finally:
            await context.close()
            
        return item

def exibir_relatorio(aprovados):
    print("\n" + "="*70)
    print("🚀 RELATÓRIO FINAL: NÚMEROS VÁLIDOS PARA YOUTUBE (0/2 OU 1/2 USOS)")
    print("="*70)

    if aprovados:
        for i, item in enumerate(aprovados, 1):
            usos = item['usos_google']
            status = "🟢 [VIRGEM - 0/2 USOS]" if usos == 0 else "🟡 [1 USO DETECTADO - 1 VAGA RESTANTE]"
            
            print(f"{i}. 📱 {item['numero']} {status}")
            print(f"   🌐 Fonte: {item['fonte']}")
            print(f"   📊 Verificações detectadas no histórico: {usos}")
            print(f"   🔗 Link Direto do SMS: {item['link']}")
            print("-" * 70)
    else:
        print("\n❌ NENHUM NÚMERO DISPONÍVEL ENCONTRADO NESTA VARREDURA.")

async def main():
    print("\n⚡ [BOT YOUTUBE INTELIGENTE v4] Iniciando com 3 Robôs Simultâneos...")
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        
        # Limita até 3 robôs (operações simultâneas)
        semaphoro = asyncio.Semaphore(3)
        
        print("\n🌐 Fase 1: Coletando números em paralelo nos sites...")
        tasks_ fontes = [processar_fonte(f, browser, semaphoro) for f in FONTES_SMS]
        resultados = await asyncio.gather(*tasks_fontes)
        
        # Agrupa todos os números encontrados sem duplicatas
        todos_candidatos = []
        for lista in resultados:
            for item in lista:
                if not any(c['numero'] == item['numero'] for c in todos_candidatos):
                    todos_candidatos.append(item)
                    
        print(f"\n🔍 Fase 2: {len(todos_candidatos)} candidatos localizados. Analisando páginas com os 3 robôs...")
        
        tasks_analise = [analisar_historico_numero(c, browser, semaphoro) for c in todos_candidatos]
        candidatos_analisados = await asyncio.gather(*tasks_analise)
        
        # Filtra números com 0 ou 1 uso (respeitando o limite de 2 por ano do Google)
        aprovados = [item for item in candidatos_analisados if item['usos_google'] <= 1]
        
        # Ordena colocando os virgens (0 usos) em primeiro lugar
        aprovados.sort(key=lambda x: x['usos_google'])
        
        exibir_relatorio(aprovados)
        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
