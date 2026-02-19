# OpenClaw Setup Guide For AI Coding Assistants

Source basis: `docs2.md` (crawled OpenClaw docs, 307 pages).
Scope: setup, configuration, auth, security baseline, operations, troubleshooting.
Excluded: deep channel-specific integrations and advanced plugin internals unless needed for setup.

## 1) Primary Setup Path (Recommended)

Use the onboarding flow first, then verify health.

```bash
# install (Linux/macOS)
curl -fsSL https://openclaw.ai/install.sh | bash

# install (Windows PowerShell)
iwr -useb https://openclaw.ai/install.ps1 | iex

# guided setup (models + config + daemon/service where supported)
openclaw onboard --install-daemon
```

Then run:

```bash
openclaw status
openclaw doctor
openclaw logs --follow
openclaw dashboard
```

Default dashboard URL is typically `http://127.0.0.1:18789/`.

## 2) Core Files And Paths

- Main config: `~/.openclaw/openclaw.json`
- Workspace (default): `~/.openclaw/workspace`
- Env file: `~/.openclaw/.env`
- Logs (typical): `/tmp/openclaw/openclaw-*.log`

## 3) Config Editing Model

Prefer CLI mutations over manual JSON edits when possible:

```bash
openclaw config get <path>
openclaw config set <path> <value>
openclaw config unset <path>
openclaw configure
```

Common setup keys:

- `agents.defaults.workspace`
- `agents.defaults.model.primary`
- `gateway.mode`
- `gateway.bind`
- `gateway.auth.*`

## 4) Model Provider Setup

Pick one provider first, validate, then add failover.

### OpenAI API key path

```bash
openclaw onboard --openai-api-key "$OPENAI_API_KEY"
openclaw models status
openclaw models list
openclaw models set <provider/model>
```

### Anthropic API key path

```bash
openclaw onboard --anthropic-api-key "$ANTHROPIC_API_KEY"
openclaw models status
openclaw models set <provider/model>
```

Manual env placement (if needed):

```bash
cat >> ~/.openclaw/.env << 'EOF'
OPENAI_API_KEY=...
ANTHROPIC_API_KEY=...
EOF
```

## 5) Security Baseline (Use This By Default)

Run audit first:

```bash
openclaw security audit
```

Recommended baseline for initial setup:

- Keep gateway local/loopback unless remote access is explicitly required.
- Require auth for non-loopback binds.
- Keep DM policy restrictive (pairing/allowlist), not open.
- Keep sandboxing enabled for risky tools and command execution.
- Do not store secrets in prompts, chat history, or repo files.
- Prefer env vars (`~/.openclaw/.env`) for API keys and tokens.

## 6) Runtime And Process Operations

Core run/inspect commands:

```bash
openclaw gateway
openclaw gateway status
openclaw status --all
openclaw health --json
openclaw logs --follow
openclaw doctor --repair
```

If service mode is installed, use your platform service manager as needed.

## 7) Troubleshooting Ladder (Assistant Playbook)

Use this sequence in order:

```bash
openclaw status
openclaw gateway status
openclaw logs --follow
openclaw doctor
openclaw channels status --probe
openclaw models status
```

Typical diagnosis buckets:

- Gateway not running/bound
- Auth or model credential mismatch
- Provider unavailable/rate-limited
- Channel connected but delivery blocked
- Policy/sandbox restrictions preventing tool execution

## 8) Optional Deployment Modes

Use only if local onboarding path is not enough:

- Docker: containerized gateway/sandbox workflow.
- Podman: rootless or service-based workflow.
- Node source workflow: for development/bleeding edge setups.
- VM/cloud installs (Fly/Hetzner/GCP/etc.): only for explicit remote hosting needs.

For AI assistants: default to local setup first, then migrate to container/remote.

## 9) Assistant Decision Rules For Setup Tasks

- Start with `openclaw onboard`; avoid manual config bootstrapping unless onboarding fails.
- After every config/auth change, run `openclaw status` and `openclaw models status`.
- Before changing multiple things, snapshot config by copying `~/.openclaw/openclaw.json` to a dated backup.
- Prefer smallest viable fix, then re-check logs/status.
- For remote binds, verify auth + security settings before exposing network access.

## 10) Minimal Command Pack (Keep Handy)

```bash
openclaw onboard --install-daemon
openclaw configure
openclaw config get <path>
openclaw config set <path> <value>
openclaw status --deep
openclaw health --json
openclaw logs --follow
openclaw doctor --repair
openclaw models status
openclaw models list
openclaw models set <provider/model>
openclaw channels status --probe
openclaw security audit
```
