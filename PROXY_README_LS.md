# OpenClaw Playwright HU Proxy Setup (Working State)

This document records the exact setup that currently works for routing only Playwright/browser traffic through an HU VM proxy while leaving non-browser app traffic direct.

## Goal

- Route only OpenClaw managed browser traffic through HU proxy.
- Keep normal container/app network traffic unproxied.
- Keep setup reproducible via Docker compose.

## Current Working Architecture

1. OpenClaw container runs normally.
2. Browser launch path injects Chromium args:
   - `--proxy-server=...`
   - `--lang=...`
   - `--accept-lang=...`
3. HU VM runs Squid on `185.65.68.104:3128`.
4. Squid uses no auth, but only allows one source IP:
   - `132.226.216.143` (OpenClaw VM egress IP)

## OpenClaw Repo Changes

Key files:

- `src/browser/config.ts`
  - Adds first-class browser proxy/lang support:
    - `browser.proxyServer`
    - `browser.lang`
    - `browser.acceptLanguage`
    - `browser.timezoneId`
  - Keeps env fallback support:
    - `HU_PLAYWRIGHT_PROXY_URL`
    - `HU_BROWSER_LANG`
    - `HU_BROWSER_ACCEPT_LANGUAGE`
    - `HU_BROWSER_TIMEZONE`
  - Rejects authenticated SOCKS5 in launch path (Chromium limitation here).
- `src/config/types.browser.ts`
  - Adds `proxyServer`, `lang`, `acceptLanguage` keys.
- `src/config/zod-schema.ts`
  - Adds schema fields for those keys.
- `src/config/schema.labels.ts`
  - Adds labels for new browser keys.
- `src/browser/chrome.ts`
  - Applies `TZ` env when `browser.timezoneId` is set.
- `src/browser/config.test.ts`
  - Tests env fallback, config precedence, and proxy validation.
- `docker-compose.yml`
  - Passes HU_* env vars through to container.
- `.env.example`
  - Documents Option 1 (HTTP proxy) and first-class config key preference.

## Runtime Values in OpenClaw VM

In local `.env`:

```env
HU_PLAYWRIGHT_PROXY_URL=http://185.65.68.104:3128
HU_BROWSER_LANG=hu-HU
HU_BROWSER_ACCEPT_LANGUAGE=hu-HU,hu
HU_BROWSER_TIMEZONE=Europe/Budapest
```

Apply:

```bash
sudo docker compose up -d --build
```

## HU VM Setup That Works

Service: Squid (native install, not Docker)

Port:

- `3128`

Access control:

- No auth.
- Allow only source IP `132.226.216.143/32`.
- Deny all others.

Reference `squid.conf` shape:

```conf
http_port 3128

acl openclaw_vm src 132.226.216.143/32

acl SSL_ports port 443
acl Safe_ports port 80
acl Safe_ports port 443
acl Safe_ports port 1025-65535
acl CONNECT method CONNECT

http_access deny !Safe_ports
http_access deny CONNECT !SSL_ports
http_access allow openclaw_vm
http_access deny all

via off
forwarded_for delete
request_header_access X-Forwarded-For deny all
```

## Verification Commands

### Container/app traffic stays direct

```bash
sudo docker exec openclaw-gateway curl -sS --max-time 20 https://api.ipify.org
```

Expected: OpenClaw VM public IP (not HU proxy IP).

### Proxy path is reachable from container

```bash
sudo docker exec openclaw-gateway sh -lc 'curl -sS --max-time 20 -x "$HU_PLAYWRIGHT_PROXY_URL" https://api.ipify.org'
```

Expected: `185.65.68.104`.

### Playwright browser egress uses HU proxy

```bash
sudo docker exec -i openclaw-gateway node - <<'NODE'
(async () => {
  const { chromium } = require('playwright-core');
  const browser = await chromium.launch({
    headless: true,
    args: [`--proxy-server=${process.env.HU_PLAYWRIGHT_PROXY_URL}`],
  });
  const page = await browser.newPage();
  await page.goto('https://api.ipify.org', { waitUntil: 'domcontentloaded', timeout: 30000 });
  console.log((await page.textContent('body')).trim());
  await browser.close();
})();
NODE
```

Expected: `185.65.68.104`.

## Important Limitation

- Authenticated SOCKS5 in this Chromium launch path produced `ERR_NO_SUPPORTED_PROXIES`.
- HTTP CONNECT proxy without auth + source-IP allowlist is the stable solution used now.

## Pull/Update Checklist (So It Does Not Break)

1. Keep your fork branch as source of truth; do not rely on upstream to keep these changes.
2. After pulling upstream changes, verify these files did not lose custom logic:
   - `src/browser/config.ts`
   - `src/browser/config.test.ts`
   - `src/config/types.browser.ts`
   - `src/config/zod-schema.ts`
   - `docker-compose.yml`
3. Ensure `.env` still has your proxy/lang/timezone values.
4. Rebuild:
   - `sudo docker compose up -d --build`
5. Re-run the three verification blocks above.
6. If HU VM egress IP changes, update Squid allowlist IP accordingly.

## Rollback

If needed, disable browser proxy quickly by clearing env var:

```bash
sed -i 's|^HU_PLAYWRIGHT_PROXY_URL=.*|HU_PLAYWRIGHT_PROXY_URL=|' .env
sudo docker compose up -d --build
```

This restores direct browser egress.
