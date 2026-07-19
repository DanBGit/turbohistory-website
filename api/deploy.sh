#!/usr/bin/env bash
# Deploy the capture API to the Hetzner box.
#
# Note: docker restart reuses the OLD image, so the container must be removed and
# recreated for a code change to take effect. That caught us once already.
set -euo pipefail

HOST=root@89.167.109.218
SSH="ssh -i $HOME/.ssh/id_ed25519"
HERE="$(cd "$(dirname "$0")" && pwd)"
KEY="$(cat "$HERE/.admin-key")"

$SSH $HOST "mkdir -p /opt/turbohistory-api/data"
scp -i "$HOME/.ssh/id_ed25519" -q "$HERE/app.py" "$HERE/Dockerfile" \
    "$HERE/requirements.txt" $HOST:/opt/turbohistory-api/

$SSH $HOST "cd /opt/turbohistory-api && docker build -q -t turbohistory-api . >/dev/null && \
docker rm -f turbohistory-api >/dev/null 2>&1 || true; \
docker run -d --name turbohistory-api --network coolify --restart always \
  -v /opt/turbohistory-api/data:/data -e TH_ADMIN_KEY='$KEY' \
  -l traefik.enable=true \
  -l 'traefik.http.routers.th-api.rule=Host(\`turbohistory.com\`) && PathPrefix(\`/api\`)' \
  -l traefik.http.routers.th-api.entryPoints=https \
  -l traefik.http.routers.th-api.priority=100 \
  -l traefik.http.routers.th-api.tls=true \
  -l traefik.http.routers.th-api.tls.certresolver=letsencrypt \
  -l traefik.http.routers.th-api.service=th-api \
  -l traefik.http.services.th-api.loadbalancer.server.port=8080 \
  turbohistory-api >/dev/null && echo deployed"

sleep 6
curl -sf https://turbohistory.com/api/health && echo " <- api healthy"
