import puppeteer from 'puppeteer-extra';
import StealthPlugin from 'puppeteer-extra-plugin-stealth';
import fs from 'fs';

// Ativa o plugin stealth para esconder qualquer vestígio de robô
puppeteer.use(StealthPlugin());

async function iniciarCelularVirtual() {
  console.log('📱 Iniciando o Celular Virtual (Modo Humano)...');

  // Inicia o navegador (pode rodar headless ou com interface)
  const browser = await puppeteer.launch({
    headless: false, // Deixe false para você ver o celular simulado abrindo
    args: [
      '--no-sandbox',
      '--disable-setuid-sandbox',
      '--disable-infobars',
      '--window-size=412,915' // Tamanho padrão de tela de celular moderno
    ]
  });

  const page = await browser.newPage();

  // 1. Emula um Dispositivo Móvel Real (Ex: Moto G / Pixel)
  await page.emulate({
    name: 'Pixel 5',
    userAgent: 'Mozilla/5.0 (Linux; Android 11; Pixel 5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36',
    viewport: {
      width: 412,
      height: 915,
      deviceScaleFactor: 2.75,
      isMobile: true,
      hasTouch: true,
      isLandscape: false
    }
  });

  // 2. Define Geolocalização do Brasil (São Paulo, por exemplo)
  await page.setGeolocation({ latitude: -23.5505, longitude: -46.6333 });
  await page.setExtraHTTPHeaders({ 'Accept-Language': 'pt-BR,pt;q=9' });

  // 3. Injeta Cookies Salvos (se você tiver o arquivo cookies.json gerado anteriormente)
  if (fs.existsSync('cookies.json')) {
    const cookiesString = fs.readFileSync('cookies.json', 'utf8');
    const cookies = JSON.parse(cookiesString);
    await page.setCookie(...cookies);
    console.log('🍪 Cookies injetados com sucesso! Sessão restaurada.');
  } else {
    console.log('⚠️ Nenhum arquivo de cookies.json encontrado. Criando nova sessão...');
  }

  // 4. Acessa o YouTube ou seu site fingindo ser humano
  console.log('🌐 Navegando para o YouTube...');
  await page.goto('https://m.youtube.com', { waitUntil: 'networkidle2' });

  // Simula um atraso humano aleatório (aguarda entre 3 a 6 segundos fingindo ler a tela)
  const delayAleatorio = Math.floor(Math.random() * 3000) + 3000;
  await new Promise(resolve => setTimeout(resolve, delayAleatorio));

  console.log('✅ Celular virtual pronto e navegando como humano!');
  
  // Salva os cookies atualizados no final da sessão para reuso futuro
  const cookiesAtuais = await page.cookies();
  fs.writeFileSync('cookies.json', JSON.stringify(cookiesAtuais, null, 2));

  // await browser.close();
}

iniciarCelularVirtual();
