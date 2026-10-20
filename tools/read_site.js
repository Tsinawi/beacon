// Reads a community website into pages.json: text and image URLs for the home page
// plus the pages that matter for social content (amenities, floor plans, gallery, ...).
//
//   NODE_PATH=$(npm root -g) node tools/read_site.js https://example.com out/example
//
// Each page loads in a fresh browser, which gets past Cloudflare checks that block
// a second navigation in the same session (seen on RentCafe sites such as liveatglens.com).

const fs = require('fs');
const path = require('path');
const { chromium } = require('playwright');

const UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36';
const WANTED = /amenit|feature|floor|plan|gallery|photo|neighbo|map|direction|special|pet|availab|about/i;
const SKIP = /login|portal|apply|privacy|terms|accessib|contact|thank|blog|feed|wp-json|xmlrpc|resident/i;

async function readPage(url) {
  const browser = await chromium.launch({ headless: true, args: ['--disable-blink-features=AutomationControlled'] });
  try {
    const ctx = await browser.newContext({ userAgent: UA, viewport: { width: 1366, height: 900 }, locale: 'en-US' });
    await ctx.addInitScript(() => { Object.defineProperty(navigator, 'webdriver', { get: () => undefined }); });
    const page = await ctx.newPage();
    await page.goto(url, { waitUntil: 'domcontentloaded', timeout: 45000 });
    for (let i = 0; i < 20; i++) {
      await page.waitForTimeout(2000);
      if (!/just a moment|attention required/i.test(await page.title())) break;
    }
    await page.waitForTimeout(2500);
    for (let i = 0; i < 10; i++) { await page.mouse.wheel(0, 1500); await page.waitForTimeout(350); }
    const title = await page.title();
    if (/just a moment|attention required/i.test(title)) return { url, blocked: true, title };
    return await page.evaluate(() => {
      const abs = u => { try { return new URL(u, location.href).href; } catch (e) { return null; } };
      const images = new Set();
      const add = u => { const a = u && abs(u.trim().split(' ')[0]); if (a && /^https?:/.test(a)) images.add(a); };
      document.querySelectorAll('img').forEach(img => {
        add(img.currentSrc || img.src); add(img.getAttribute('data-src')); add(img.getAttribute('data-lazy-src'));
        const ss = img.getAttribute('srcset') || img.getAttribute('data-srcset');
        if (ss) { const parts = ss.split(',').map(s => s.trim()).filter(Boolean); add(parts[parts.length - 1]); }
      });
      document.querySelectorAll('[style*="background"]').forEach(el => {
        const m = /url\(["']?([^"')]+)["']?\)/.exec(el.getAttribute('style') || ''); if (m) add(m[1]);
      });
      document.querySelectorAll('#onetrust-consent-sdk, [id*="cookie"], [class*="cookie"]').forEach(el => el.remove());
      const links = [...document.querySelectorAll('a[href]')].map(a => ({ href: abs(a.getAttribute('href')), text: (a.innerText || '').trim().slice(0, 60) })).filter(l => l.href);
      return { url: location.href, title: document.title, text: document.body.innerText, images: [...images], links };
    });
  } catch (e) {
    return { url, error: String(e && e.message || e) };
  } finally {
    await browser.close();
  }
}

async function wordpressPages(base) {
  try {
    const r = await fetch(new URL('/wp-json/wp/v2/pages?per_page=100&_fields=link,slug', base), { headers: { 'user-agent': UA } });
    if (!r.ok) return null;
    const j = await r.json();
    return Array.isArray(j) ? j.map(p => p.link) : null;
  } catch (e) { return null; }
}

(async () => {
  const [base, outDir, maxArg] = process.argv.slice(2);
  if (!base || !outDir) { console.error('usage: node read_site.js <website> <outDir> [maxPages]'); process.exit(2); }
  const maxPages = Number(maxArg) || 8;
  fs.mkdirSync(outDir, { recursive: true });
  const host = new URL(base).host.replace(/^www\./, '');
  const home = await readPage(base);
  const pages = [home];
  const candidates = new Set();
  for (const l of (home.links || [])) {
    let u; try { u = new URL(l.href); } catch (e) { continue; }
    if (u.host.replace(/^www\./, '') !== host) continue;
    u.hash = ''; u.search = '';
    const key = u.pathname + ' ' + l.text;
    if (u.pathname === '/' || SKIP.test(key) || !WANTED.test(key)) continue;
    candidates.add(u.href);
  }
  const wp = await wordpressPages(base);
  if (wp) for (const link of wp) if (WANTED.test(link) && !SKIP.test(link)) candidates.add(link);
  for (const url of [...candidates].slice(0, maxPages)) pages.push(await readPage(url));
  const out = { website: base, readAt: new Date().toISOString(), platform: wp ? 'wordpress' : (JSON.stringify(home).includes('rentcafe') ? 'rentcafe' : 'unknown'),
    pages: pages.map(({ links, ...p }) => p) };
  fs.writeFileSync(path.join(outDir, 'pages.json'), JSON.stringify(out, null, 1));
  for (const p of out.pages) console.log(p.blocked ? 'BLOCKED' : p.error ? 'ERROR  ' : 'OK     ', p.url, p.images ? `${p.images.length} images` : (p.error || ''));
})();
