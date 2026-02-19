# OpenClaw VM Full Setup Runbook (Docker + Playwright + Skills)

Purpose: end-to-end install and hardening guide for running OpenClaw on a VM, with Docker-based execution, browser/Playwright stability, and skills configured for practical use.

Primary references in `docs2.md`:
- `https://docs.openclaw.ai/install/docker`
- `https://docs.openclaw.ai/install/macos-vm`
- `https://docs.openclaw.ai/install/gcp`
- `https://docs.openclaw.ai/install/hetzner`
- `https://docs.openclaw.ai/start/setup`
- `https://docs.openclaw.ai/gateway/configuration`
- `https://docs.openclaw.ai/gateway/security`
- `https://docs.openclaw.ai/gateway/troubleshooting`
- `https://docs.openclaw.ai/tools/browser`
- `https://docs.openclaw.ai/tools/browser-linux-troubleshooting`
- `https://docs.openclaw.ai/tools/skills`
- `https://docs.openclaw.ai/tools/skills-config`
- `https://docs.openclaw.ai/cli/skills`

## 1) Recommended Architecture

- Host OpenClaw Gateway on a Linux VM.
- Use Docker for tool sandboxing and browser automation dependencies.
- Keep OpenClaw state persistent under `~/.openclaw`.
- Keep agent workspace persistent under `~/.openclaw/workspace`.
- Start local-first in config (`gateway.mode=local`, loopback bind), then explicitly open remote access with auth.

## 2) VM Choices

- GCP/Hetzner: good default for production VPS workflows.
- macOS VM path (Lume) is mainly for macOS-specific features/testing, not the simplest production baseline.
- Podman is supported, but Docker path has the most direct browser/Playwright guidance.

## 3) Provision VM (Linux VPS Baseline)

Install base packages and Docker:

```bash
sudo apt-get update
sudo apt-get install -y git curl ca-certificates
curl -fsSL https://get.docker.com | sudo sh
docker --version
docker compose version
```

Clone OpenClaw repository and prepare persistent dirs:

```bash
git clone <openclaw-repo-url>
cd <openclaw-repo>
mkdir -p ~/.openclaw ~/.openclaw/workspace
```

## 4) Docker Setup (Gateway + Sandbox)

From repo root:

```bash
./docker-setup.sh
```

Important env knobs from Docker docs:

- `OPENCLAW_DOCKER_APT_PACKAGES`: extra apt dependencies during image build.
- `OPENCLAW_EXTRA_MOUNTS`: extra bind mounts.
- `OPENCLAW_HOME_VOLUME`: persist `/home/node` (important for browser caches).

Bring up services:

```bash
docker compose up -d
```

Check UI:

- `http://127.0.0.1:18789/` (or forwarded equivalent).

## 5) Playwright/Browser Nuances (Critical)

If browser automation fails, prioritize these fixes:

1. Ensure browser binary exists (Linux):

```bash
sudo apt install chromium
# or install stable Chrome .deb if chromium/snap path is problematic
```

2. Set explicit browser executable in config when auto-detect fails:

```json
{
  "browser": {
    "enabled": true,
    "executablePath": "/usr/bin/google-chrome-stable"
  }
}
```

3. Persist browser cache for Playwright:

- Set `PLAYWRIGHT_BROWSERS_PATH=/home/node/.cache/ms-playwright` in compose/runtime env.
- Persist `/home/node` using `OPENCLAW_HOME_VOLUME`, or mount cache path via `OPENCLAW_EXTRA_MOUNTS`.

4. If running attach-only mode (existing browser session model):

```json
{
  "browser": {
    "enabled": true,
    "attachOnly": true
  }
}
```

Common error signature:
- `Failed to start Chrome CDP on port 18800` indicates browser binary/deps/profile startup issue.

## 6) Initial OpenClaw Setup Flow

Run guided setup:

```bash
openclaw onboard --install-daemon
```

Then verify:

```bash
openclaw status
openclaw gateway status
openclaw doctor
openclaw logs --follow
openclaw dashboard
```

Config and state locations:

- `~/.openclaw/openclaw.json`
- `~/.openclaw/.env`
- `~/.openclaw/workspace`

## 7) Skills Setup (Local + Shared)

Skills locations:

- Shared/global: `~/.openclaw/skills`
- Workspace-scoped: `<workspace>/skills`
- Skill definition file: `SKILL.md`

Useful commands:

```bash
openclaw skills list
openclaw skills list --eligible
openclaw skills info <name>
openclaw skills check
```

Skills config in `~/.openclaw/openclaw.json`:

```json
{
  "skills": {
    "allowBundled": ["gemini", "peekaboo"],
    "load": {
      "extraDirs": ["~/.openclaw/skills"],
      "watch": true,
      "watchDebounceMs": 500
    },
    "install": {
      "preferBrew": true
    }
  }
}
```

Nuance:
- Tool allow/deny is controlled by `tools` policy, not skills alone.
- If a skill needs binaries, ensure `exec` policy allows execution in the chosen sandbox/host context.

## 8) Security Baseline For VM Deployments

Run audit:

```bash
openclaw security audit
```

Baseline recommendations:

- Use strict auth for non-loopback binds (`gateway.auth.token` or password env).
- Keep DM/group policy restrictive (`pairing`/allowlist-first).
- Enable sandboxing for agents handling untrusted input.
- Keep tool profile minimal unless explicitly required.
- Store keys in env (`~/.openclaw/.env`), not prompts or plaintext docs.

## 9) Remote Access Pattern

Before exposing publicly:

- Confirm `openclaw status --all` is healthy.
- Confirm auth is enforced (`OPENCLAW_GATEWAY_TOKEN` or password equivalent).
- Verify logs for denied/unauthorized requests and fix before production exposure.

## 10) Operations And Recovery

Daily checks:

```bash
openclaw status
openclaw models status
openclaw channels status --probe
```

Troubleshooting ladder:

```bash
openclaw status
openclaw gateway status
openclaw logs --follow
openclaw doctor --repair
```

If browser tools fail:

- Verify browser binary and path.
- Verify Playwright cache persistence.
- Verify sandbox/image dependencies.
- Rebuild Docker image after changing browser/dependency env vars.

If skills appear missing:

- Check directories and `SKILL.md` validity.
- Run `openclaw skills check`.
- Confirm tool policy permits required execution paths.

## 11) Cloud VM Notes (GCP/Hetzner)

GCP and Hetzner guides both follow this same high-level pattern:

1. Create VM.
2. SSH in.
3. Install Docker.
4. Clone repo.
5. Create persistent host dirs (`~/.openclaw`, `~/.openclaw/workspace`).
6. Configure `.env` and compose.
7. Build + `docker compose up -d`.
8. Verify health/status/logs.

Use cloud-specific docs for provider-native details (firewall rules, machine type, service accounts, private networking).

## 12) macOS VM Notes (Lume)

Quick commands from docs:

```bash
lume create openclaw --os macos --ipsw latest
lume run openclaw --no-display
```

Then install OpenClaw in-VM and follow the same status/doctor/log verification flow.

