# Local dev setup

## TLS with mkcert

mkcert lets you issue locally-trusted certs signed by a CA that only exists on your machine.

Install it (one time, per machine):

```
sudo apt install mkcert libnss3-tools
mkcert -install
```

The `-install` step adds mkcert's CA to your system and browser trust stores so browsers stop complaining. It also writes the CA certificate to `~/.local/share/mkcert/rootCA.pem` — the stack mounts this into the traefik container so traefik can trust the nginx TLS cert when making internal OIDC requests.

Generate certs for all the domains the stack uses and drop them where nginx expects them:

```
sudo mkdir -p /tmp/certs
mkcert \
  -cert-file /tmp/certs/fullchain.pem \
  -key-file  /tmp/certs/privkey.pem \
  localhost "*.localhost" auth.localhost clients.localhost "*.clients.localhost" \
  kiosk.mnta.in "*.kiosk.mnta.in" auth.kiosk.mnta.in clients.kiosk.mnta.in "*.clients.kiosk.mnta.in"
sudo mv /tmp/certs /opt/certs
```

If you already have a cert at `/opt/certs` that is missing the `auth.*` subdomains, just run the command above again — it overwrites in place.


---

## OIDC / Dex

The stack runs a local [Dex](https://dexidp.io/) instance at `auth.localhost`. It acts as the OIDC provider so you don't need any external identity service during development.

Dex config lives in `dex/config.yml`. It ships with one static user:

| field    | value           |
|----------|-----------------|
| email    | admin@local.dev |
| password | password        |

The traefik-oidc-auth middleware is wired to Dex. Any request to the stack that isn't under `/client` will trigger an auth redirect. Log in with the credentials above and you're through.

To swap in a real IdP for production, see the "Production deployment" section below rather than editing this file directly - `traefik/dynamic.yml` is the tracked local-dev default and is expected to keep pointing at Dex.

---

## /etc/hosts

Make sure `auth.localhost` (and any other `*.localhost` subdomains you use) resolve locally. On most systems `*.localhost` already resolves to `127.0.0.1` without any hosts file changes, but if something isn't resolving add it manually:

```
echo "127.0.0.1 auth.localhost" | sudo tee -a /etc/hosts
```

---

## Production deployment

Production runs `docker-compose.prod.yaml` directly (not the top-level
`docker-compose.yaml` - that file only adds the local Dex/mkcert dev extras).
On a host that already has its own reverse proxy on ports 80/443 (e.g.
zoraxy, Caddy, another nginx), this project's bundled `nginx` container and
local Dex are not used at all; instead:

1. Copy the templates and fill in real values (both are gitignored, so they
   survive `git pull` untouched):
   ```
   cp docker-compose.override.yaml.example docker-compose.override.yaml
   cp traefik/dynamic.prod.yml.example traefik/dynamic.prod.yml
   ```
2. Edit `traefik/dynamic.prod.yml` with your real IdP's `Provider.Url`,
   `ClientId`, `ClientSecret`, and `BypassAuthenticationRule` host.
3. Edit `docker-compose.override.yaml`'s `traefik.ports` if you want the
   external proxy to reach Traefik on something other than `127.0.0.1:8080`.
4. Run with both files:
   ```
   docker compose -f docker-compose.prod.yaml -f docker-compose.override.yaml up --build -d
   ```

`docker-compose.prod.yaml` and `traefik/dynamic.yml` stay as the generic,
tracked defaults (nginx included, Dex-based auth) for anyone self-hosting
without a pre-existing reverse proxy - just run
`docker compose -f docker-compose.prod.yaml up --build -d` with no override.
