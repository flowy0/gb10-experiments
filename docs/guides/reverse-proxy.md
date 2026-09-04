# Reverse Proxy — Caddy (Open Web UI over HTTPS)

Caddy serves **Open Web UI** at `https://chat.testerlab.online` on the LAN. It also listens for a plain-HTTP LAN name (`chat.home.lan`, commented) if you want a no-certificate internal alias.

## Architecture

```
Browser (LAN device)
   │  https://chat.testerlab.online  (Cloudflare DNS: chat -> A <flint-lan-ip>, DNS only)
   ▼
Caddy container (this box, ports 80 + 443)
   │  reverse_proxy open-webui:8080  (shared compose network)
   ▼
Open Web UI -> litellm:4000 -> SGLang main model
```

- **No public traffic.** The Cloudflare name record is DNS-only (grey cloud). Nothing is port-forwarded from the internet; the earlier Cloudflare Tunnel is disabled and commented out.
- **Real certificate.** Let's Encrypt issues a cert for `chat.testerlab.online` using the **DNS-01 challenge** (a temporary TXT record via the Cloudflare API). No inbound port is needed for issuance — only the API token.

## Files & services

| Item | Location / value |
|---|---|
| Proxy config | `caddy/Caddyfile` |
| Custom image build | `caddy/Dockerfile` (caddy + `caddy-dns/cloudflare`) |
| Image | `local/caddy-cloudflare` (build: `docker build -t local/caddy-cloudflare ./caddy`) |
| Compose service | `caddy` (env_file `.env`, ports 80 + 443, volumes `caddy-data`/`caddy-config`) |
| API token | `CF_API_TOKEN` in `/opt/atom/.env` (owner-only perms; **not** committed) |
| Token scope | Cloudflare API token, "Edit zone DNS" for `testerlab.online` only |
| DNS (user-managed, Cloudflare) | `chat` → **A** `$FLINT_LAN_IP`, **DNS only** |
| DNS (user-managed, Cloudflare) | `prometheus` → **A** `$FLINT_LAN_IP`, **DNS only** (added 2026-09-04; cert auto-issued via DNS-01) |
| DNS (user-managed, Cloudflare) | `grafana` → **A** `$FLINT_LAN_IP`, **DNS only** (added 2026-09-04; cert auto-issued via DNS-01) |

## The Caddyfile

```
chat.testerlab.online {
    tls {
        dns cloudflare {env.CF_API_TOKEN}
    }
    reverse_proxy open-webui:8080
}

prometheus.testerlab.online {
    tls {
        dns cloudflare {env.CF_API_TOKEN}
    }
    reverse_proxy prometheus:9090
}

grafana.testerlab.online {
    tls {
        dns cloudflare {env.CF_API_TOKEN}
    }
    reverse_proxy grafana:3000
}

# http://chat.home.lan {
#     reverse_proxy open-webui:8080
# }
```

`http://chat.home.lan` (commented) is the pure-LAN alias — it needs a `chat` name in the UniFi DNS and gives no certificate (or use `tls internal` + trust Caddy's local CA).

## Management

```bash
# start / restart after Caddyfile changes
docker compose up -d --force-recreate caddy

# logs (cert issuance, errors)
docker logs caddy

# verify the certificate
echo | openssl s_client -connect 127.0.0.1:443 -servername chat.testerlab.online 2>/dev/null | openssl x509 -noout -issuer -dates
```

## Adding another service later

Used for **Prometheus** (`prometheus.testerlab.online`, 2026-09-04) and the template below for future ones:

```
api.testerlab.online {
    tls { dns cloudflare {env.CF_API_TOKEN} }
    reverse_proxy litellm:4000
}
```

## The LAN address source

The box's LAN address is defined once in `/opt/atom/.env` as `FLINT_LAN_IP` (untracked, owner-only). Source it from there whenever a config or script needs the address — do not hardcode it. The Cloudflare A record content should match `$FLINT_LAN_IP`.

## Notes & cautions

- **Client-IP gating does not work through docker published ports** — the docker userland proxy rewrites the source address to the bridge gateway, so Caddy `client_ip` matchers see `172.18.x.x` for every client (tested 2026-09-04). Prometheus/Open Web UI are therefore LAN-only by topology, not by per-client matcher. If real per-client restrictions are ever required: run Caddy with `network_mode: host` (real source IPs, proxy to `127.0.0.1:<published port>`) or firewall on the host.
- **The Prometheus UI has no auth** — anyone who can reach the box (LAN devices, Tailscale peers) can query it. The raw `http://<lan-ip>:9090` endpoint stays published for ops/tooling; both it and the hostname are LAN-only.

- **Certificate renewal:** Caddy renews automatically (token needed only at issuance/renewal, ~60-day window). Check `docker logs caddy` if renewal stops working.
- **Do not commit** `CF_API_TOKEN`. It lives only in `/opt/atom/.env` (git-ignored or owner-only).
- **The A record is public** (anyone can resolve the name to the private IP). No traffic reaches the box that way — it is only an address disclosure. Remove the record if that matters.
- **LAN-only by design** — the public Cloudflare Tunnel is disabled (service commented in compose). Re-enabling it opens Open Web UI to the internet; that is a deliberate change.
- Related: [monitoring.md](monitoring.md), [config-conventions.md](config-conventions.md), [main-model.md](main-model.md).
