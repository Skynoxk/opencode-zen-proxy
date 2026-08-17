# OpenCode Zen Proxy

Self-contained streaming reverse proxy for the [OpenCode Zen](https://opencode.ai/zen) free tier.

Forwards requests to `https://opencode.ai/zen/v1` while injecting the same `x-opencode-*`
identity headers the real OpenCode CLI sends, so the Zen API attributes traffic to a real
client instead of an anonymous IP (which gets throttled). Streams SSE responses
chunk-by-chunk.

- Python 3 stdlib only — **no pip installs, no dependencies**
- Exposes an OpenAI-compatible endpoint at `http://127.0.0.1:1787/v1`
- Works on any Linux (Kali, Ubuntu, Debian), macOS, or WSL2

## Quick start

```bash
# run in foreground (no install)
python3 opencode-zen-proxy.py

# or install as a systemd service (auto-start on boot)
sudo ./install.sh
```

Verify it's up:

```bash
curl -s http://127.0.0.1:1787/v1/models
```

## Point clients at it

The proxy is OpenAI-compatible, so anything that speaks the OpenAI API works:

```bash
# OpenCode CLI
opencode --model <zen-model> --api-base http://127.0.0.1:1787/v1

# any OpenAI-compatible client (curl)
curl -s http://127.0.0.1:1787/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model":"<zen-model>","messages":[{"role":"user","content":"hi"}]}'
```

Hermes Agent custom provider (`~/.hermes/config.yaml`):

```yaml
custom_providers:
  - name: Opencode.ai
    base_url: http://127.0.0.1:1787/v1
    key_env: HERMES_CUSTOM_OPENCODE_AI_API_KEY   # any value works, proxy is keyless
```

## systemd (Kali / Debian / Ubuntu)

`install.sh` copies the script to `/opt/opencode-zen-proxy/`, installs a hardened
systemd unit, and enables it:

```bash
sudo systemctl status opencode-zen-proxy   # check status
journalctl -u opencode-zen-proxy -f        # follow logs
sudo systemctl restart opencode-zen-proxy  # after editing the script
```

## Notes / warnings

- Binds `127.0.0.1:1787` by default. To let other machines on your LAN reach it,
  change `LISTEN_HOST = "0.0.0.0"` in the script — anyone on your network can then
  burn your Zen quota, so only do this on trusted networks.
- The fake client identity is randomized per process start (not per request), so
  traffic looks like one consistent OpenCode client.
- No API key is sent upstream — Zen is identity-based, which is exactly what this
  proxies around.
- Upstream is `opencode.ai:443`; if it's blocked on your network, the proxy returns
  HTTP 502 with the underlying error.
