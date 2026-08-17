# Deploying the capture API

This is a Coolify app now. There is no SSH step and no deploy script.

- Coolify app: `turbohistory-api`, uuid `dt0o3de99yjqke04qxrif2rd`
- Project: Turbo History / production, on the Hetzner box (89.167.109.218)
- Source: this repo, branch `main`, base directory `/api`, Dockerfile build pack, port 8080
- Data: bind mount `/opt/turbohistory-api/data` -> `/data`. `subscribers.db` lives there.
  Never let a deploy create a fresh volume instead - the API comes up healthy and empty.

Deploy (after pushing to `main`):

    curl -X POST "$COOLIFY_API_URL/api/v1/deploy?uuid=dt0o3de99yjqke04qxrif2rd" \
      -H "Authorization: Bearer $COOLIFY_API_TOKEN"

Two things Coolify gets wrong for a path-based domain, both already fixed in the app's
custom labels. If routing ever breaks after a Coolify upgrade, check these first:

1. Coolify adds a Traefik `stripprefix` middleware for `/api`, which would hand the app
   `/subscribe` instead of `/api/subscribe` - every route 404s while the app reports
   healthy. The middleware is removed from the router's chain.
2. Coolify sets no router priority, so Traefik falls back to rule length. Both routers
   are pinned to `priority=200`.

Verify a deploy with:

    curl -s https://turbohistory.com/api/health                  # 200
    curl -s https://turbohistory.com/api/subscribers/count       # subscriber count, not 0
