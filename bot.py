import asyncio
import re
from urllib.parse import urljoin
from playwright.async_api import async_playwright

# 🌍 PREFIXOS PERMITIDOS (Suíça +41 excluída)
PREFIXOS_ACEITOS = ['+1', '+55', '+351', '+44', '+33', '+34', '+358', '+46', '+31', '+49']

# Lista expandida com 8 fontes no total (+2 novos sites)
FONTES_SMS = [
    {"nome": "Receive-SMSS", "url": "https://receive-smss.com/"},
    {"nome": "SMSToMe", "url": "https://smstome.com/country/usa"},
    {"nome": "AnonymSMS", "url": "https://anonymsms.com/"},
    {"nome": "Quackr", "url": "https://quackr.io/temporary-numbers"},
    {"nome": "TempSMSS", "url": "https://tempsmss.com/"},
    {"nome": "SMS24", "url": "https://sms24.me/en/countries/us"},
    {"nome": "OnlineSMS", "url": "https://online-sms.org/"},
    {"nome": "TempNumber", "url": "https://temp-number.com/"}
]

def extrair_numero_limpo(texto):
    """Extrai e valida o número telefónico no formato internacional."""
    if not texto:
        return None
    limpo = re.sub(r'[^\d+]', '', texto)
    if not limpo.startswith('+') and len(limpo) >= 10:
        limpo = '+' + limpo

    if 10 <= len(limpo) <= 16:
        if limpo.startswith('+41'):  # Rejeita Suíça
            return None
        if any(limpo.startswith(pref) for pref in PREFIXOS_ACEITOS):
            return limpo
    return None

def construir_link_direto(base_url, href, numero_limpo):
    """Garante a construção de uma URL válida para a caixa de entrada do número."""
    if not href or href == "#" or "javascript" in href:
        return None
        
    url_completa = urljoin(base_url, href)
    digitos = re.sub(r'\D', '', numero_limpo)
    
    # Valida se a URL aponta para a página individual do número
    if len(digitos) >= 7 and (digitos[-7:] in url_completa or digitos in url_completa):
        return url_completa
    elif any(x in href.lower() for x in ['number', 'num', 'sms', 'receive']) and len(href) > 5:
        return url_completa
    return None

async def configurar_contexto_stealth(browser):
    """Configura o navegador para simular navegação humana e evitar bloqueios."""
    context = await browser.new_context(
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        viewport={"width": 1440, "height": 900},
        locale="pt-PT",
        timezone_id="Europe/Lisbon",
        extra_http_headers={
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
            "Accept-Language": "pt-PT,pt;q=0.9,en-US;q=0.8,en;q=0.7",
            "Sec-Ch-Ua": '"Chromium";v="124", "Google Chrome";v="124"',
            "Sec-Ch-Ua-Mobile": "?0",
            "Sec-Ch-Ua-Platform": '"Windows"',
            "Upgrade-Insecure-Requests": "1"
        }
    )
    return context

async def processar_fonte(fonte, browser, semaphoro):
    """Coleta os números disponíveis em cada plataforma."""
    async with semaphoro:
        numeros_encontrados = []
        context = await configurar_contexto_stealth(browser)
        page = await context.new_page()
        
        try:
            await page.goto(fonte["url"], timeout=25000, wait_until="domcontentloaded")
            await page.wait_for_timeout(2000)
            
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
            print(f"  ├─ ⚠️ {fonte['nome']}: Erro ao aceder ({e})")
        finally:
            await context.close()
            
        return numeros_encontrados

async def analisar_historico_numero(item, browser, semaphoro):
    """Mapeia o histórico completo de SMS para verificar a contagem do Google/YouTube."""
    async with semaphoro:
        context = await configurar_contexto_stealth(browser)
        page = await context.new_page()
        
        try:
            await page.goto(item['link'], timeout=20000, wait_until="domcontentloaded")
            await page.wait_for_timeout(1500)
            
            corpo_texto = await page.inner_text("body")
            texto_lower = corpo_texto.lower()
            
            mencoes = texto_lower.count('youtube') + texto_lower.count('google')
            codigos_g = len(re.findall(r'\bg-\d{5,6}\b', texto_lower))
            
            total_usos = max(mencoes, codigos_g)
            item['usos_google'] = total_usos
            
        except Exception:
            item['usos_google'] = 999
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
            status = "🟢 [VIRGEM - 0/2 USOS]" if usos == 0 else "🟡 [1 USO DETETADO - 1 VAGA RESTANTE]"
            
            print(f"{i}. 📱 {item['numero']} {status}")
            print(f"   🌐 Fonte: {item['fonte']}")
            print(f"   📊 Verificações detetadas no histórico: {usos}")
            print(f"   🔗 Link Direto do SMS: {item['link']}")
            print("-" * 70)
    else:
        print("\n❌ NENHUM NÚMERO DISPONÍVEL ENCONTRADO NESTA VARREDURA.")

async def main():
    print("\n⚡ [BOT YOUTUBE INTELIGENTE v5] A iniciar varredura em 8 plataformas...")
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        semaphoro = asyncio.Semaphore(3)
        
        print("\n🌐 Fase 1: Coletando números em paralelo nos sites...")
        tasks_fontes = [processar_fonte(f, browser, semaphoro) for f in FONTES_SMS]
        resultados = await asyncio.gather(*tasks_fontes)
        
        todos_candidatos = []
        for lista in resultados:
            for item in lista:
                if not any(c['numero'] == item['numero'] for c in todos_candidatos):
                    todos_candidatos.append(item)
                    
        print(f"\n🔍 Fase 2: {len(todos_candidatos)} candidato(s) localizado(s). Analisando histórico...")
        
        if todos_candidatos:
            tasks_analise = [analisar_historico_numero(c, browser, semaphoro) for c in todos_candidatos]
            candidatos_analisados = await asyncio.gather(*tasks_analise)
            
            aprovados = [item for item in candidatos_analisados if item['usos_google'] <= 1]
            aprovados.sort(key=lambda x: x['usos_google'])
            exibir_relatorio(aprovados)
        else:
            exibir_relatorio([])
            
        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
