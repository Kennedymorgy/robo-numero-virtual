import asyncio
import re
from playwright.async_api import async_playwright

# Prefixo da Suécia a ignorar automaticamente
EXCLUDED_PREFIXES = ('+46', '46')

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
    'Accept-Language': 'en-US,en;q=0.9',
}

def extract_valid_number(text_or_href):
    """Filtra e valida se o texto ou link corresponde a um número de telefone completo."""
    if not text_or_href:
        return None
    clean = re.sub(r'\D', '', str(text_or_href))
    if 8 <= len(clean) <= 15:
        if not clean.startswith(EXCLUDED_PREFIXES):
            return f"+{clean}"
    return None

async def check_youtube_history(context, href):
    """
    Entra na página individual do número (inbox) e verifica se existem
    mensagens prévias relativas ao YouTube ou Google.
    """
    try:
        page = await context.new_page()
        await page.goto(href, timeout=15000, wait_until="domcontentloaded")
        content = await page.content()
        await page.close()
        
        # Procura por SMS de confirmação do YouTube/Google
        yt_matches = re.findall(r'(youtube|google|g-\d{6})', content, re.IGNORECASE)
        return len(yt_matches)
    except Exception:
        return -1

async def fetch_site_numbers(page, url):
    """Extrai os números e os respetivos links diretos (href) da página inicial."""
    candidates = []
    try:
        await page.goto(url, timeout=20000, wait_until="domcontentloaded")
        links = await page.eval_on_selector_all("a", "els => els.map(e => ({text: e.innerText, href: e.href}))")
        
        seen = set()
        for l in links:
            num = extract_valid_number(l['text']) or extract_valid_number(l['href'])
            if num and num not in seen and l['href'] and l['href'].startswith('http'):
                seen.add(num)
                candidates.append({'number': num, 'href': l['href']})
    except Exception:
        pass
    return candidates

async def worker_robot(site_name, site_url, browser, sem):
    """Robô responsável por raspar o site e validar o histórico de cada número."""
    async with sem:
        context = await browser.new_context(
            user_agent=HEADERS['User-Agent'],
            extra_http_headers={'Accept-Language': HEADERS['Accept-Language']},
            viewport={'width': 1280, 'height': 720}
        )
        
        page = await context.new_page()
        candidates = await fetch_site_numbers(page, site_url)
        await page.close()
        
        approved = []
        for item in candidates:
            # Verifica o histórico de SMS no link do número
            yt_uses = await check_youtube_history(context, item['href'])
            if yt_uses == 0:
                approved.append(item)
                
        await context.close()
        return site_name, approved

async def main():
    print("⚡ [BOT YOUTUBE SMS] A iniciar varredura e validação de histórico (3 Robôs em paralelo)...\n")
    
    sites = [
        ("AnonymSMS", "https://anonymsms.com/"),
        ("Receive-SMSS", "https://receive-smss.com/"),
        ("SMSToMe", "https://smstome.com/"),
        ("Quackr", "https://quackr.io/temporary-numbers"),
        ("TempSMSS", "https://tempsmss.com/")
    ]
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=[
                '--disable-blink-features=AutomationControlled',
                '--no-sandbox',
                '--disable-setuid-sandbox'
            ]
        )
        
        semaphore = asyncio.Semaphore(3)
        tasks = [worker_robot(name, url, browser, semaphore) for name, url in sites]
        results = await asyncio.gather(*tasks)
        
        total_valid = 0
        print("🌐 Resultado da varredura e verificação de histórico:\n")
        for site_name, numbers in results:
            print(f" ├─ {site_name}: {len(numbers)} número(s) aprovado(s) sem histórico no YT")
            for item in numbers:
                print(f" │   ├─ 🟢 [APROVADO] {item['number']} (0 uso(s) no YT)")
                print(f" │   │   └─ 🔗 Link Direto: {item['href']}")
                total_valid += 1
                
        print(f"\n🔍 Total de {total_valid} número(s) com link direto válido.")
        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
