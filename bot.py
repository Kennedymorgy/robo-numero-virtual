import asyncio
import re
from playwright.async_api import async_playwright

# Prefixo da Suécia a ignorar automaticamente
EXCLUDED_PREFIXES = ('+46', '46')

# Headers para simular um navegador real
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
    'Accept-Language': 'en-US,en;q=0.9',
}

async def scrape_anonymsms(page):
    numbers = []
    try:
        await page.goto("https://anonymsms.com/", timeout=20000, wait_until="domcontentloaded")
        elements = await page.query_selector_all("a[href*='/number/']")
        for el in elements:
            text = await el.inner_text()
            clean = re.sub(r'\D', '', text)
            if clean:
                numbers.append(f"+{clean}")
    except Exception:
        pass
    return "AnonymSMS", numbers

async def scrape_receive_smss(page):
    numbers = []
    try:
        await page.goto("https://receive-smss.com/", timeout=20000, wait_until="domcontentloaded")
        elements = await page.query_selector_all(".number-boxes-item a, a[href*='/phone/']")
        for el in elements:
            text = await el.inner_text()
            clean = re.sub(r'\D', '', text)
            if clean:
                numbers.append(f"+{clean}")
    except Exception:
        pass
    return "Receive-SMSS", numbers

async def scrape_smstome(page):
    numbers = []
    try:
        await page.goto("https://smstome.com/", timeout=20000, wait_until="domcontentloaded")
        elements = await page.query_selector_all("a[href*='/country/']")
        for el in elements:
            text = await el.inner_text()
            clean = re.sub(r'\D', '', text)
            if clean:
                numbers.append(f"+{clean}")
    except Exception:
        pass
    return "SMSToMe", numbers

async def scrape_quackr(page):
    numbers = []
    try:
        await page.goto("https://quackr.io/temporary-numbers", timeout=20000, wait_until="domcontentloaded")
        elements = await page.query_selector_all("a[href*='/phone/']")
        for el in elements:
            text = await el.inner_text()
            clean = re.sub(r'\D', '', text)
            if clean:
                numbers.append(f"+{clean}")
    except Exception:
        pass
    return "Quackr", numbers

async def scrape_tempsmss(page):
    numbers = []
    try:
        await page.goto("https://tempsmss.com/", timeout=20000, wait_until="domcontentloaded")
        elements = await page.query_selector_all("a[href*='/number/']")
        for el in elements:
            text = await el.inner_text()
            clean = re.sub(r'\D', '', text)
            if clean:
                numbers.append(f"+{clean}")
    except Exception:
        pass
    return "TempSMSS", numbers

async def worker_robot(site_func, browser, sem):
    """Robô individual que executa a varredura isolada num contexto blindado."""
    async with sem:
        context = await browser.new_context(
            user_agent=HEADERS['User-Agent'],
            extra_http_headers={'Accept-Language': HEADERS['Accept-Language']},
            viewport={'width': 1280, 'height': 720}
        )
        page = await context.new_page()
        site_name, raw_numbers = await site_func(page)
        await context.close()
        
        # Filtro de eliminação de números da Suécia (+46)
        valid_numbers = [num for num in raw_numbers if not num.startswith(EXCLUDED_PREFIXES)]
        return site_name, valid_numbers

async def main():
    print("⚡ [BOT YOUTUBE SMS] A iniciar varredura e validação simultânea (3 Robôs em paralelo)...\n")
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=[
                '--disable-blink-features=AutomationControlled',
                '--no-sandbox',
                '--disable-setuid-sandbox'
            ]
        )
        
        # Semáforo para limitar 3 robôs ativos ao mesmo tempo
        semaphore = asyncio.Semaphore(3)
        
        sources = [
            scrape_anonymsms,
            scrape_receive_smss,
            scrape_smstome,
            scrape_quackr,
            scrape_tempsmss
        ]
        
        # Dispara todas as tarefas simultaneamente em paralelo
        tasks = [worker_robot(source, browser, semaphore) for source in sources]
        results = await asyncio.gather(*tasks)
        
        total_valid = 0
        print("🌐 Resultado da varredura:")
        for site_name, numbers in results:
            unique_nums = list(set(numbers))
            print(f" ├─ {site_name}: {len(unique_nums)} número(s) válidos (Suécia descartada)")
            for num in unique_nums:
                print(f" │   └─ 🟢 [APROVADO] {num}")
                total_valid += 1
                
        print(f"\n🔍 Total de {total_valid} número(s) com link direto válido.")
        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
