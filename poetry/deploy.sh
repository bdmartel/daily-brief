#!/usr/bin/env bash
# Deploy poetry.benmartel.com (the weekly poetry workshop) to the DO droplet.
# Built by tools/poem_roundup.py into poetry/site/, which calls this after each new week.
# Idempotent: safe to re-run. Static, public, noindex, no gate (the brief it draws on is public too).
# Wildcard *.benmartel.com DNS already points at the droplet. The vhost and cert are made on the
# first run. The sounds the play buttons use are on Cloudflare (tools/sounds.py), not here.
set -euo pipefail
export PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin:$PATH"
HOST="root@178.128.155.186"
DOMAIN="poetry.benmartel.com"
ROOT="/var/www/poetry"
EMAIL="bdmartel@gmail.com"
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
[ -f "$HERE/site/index.html" ] || { echo "site/index.html missing (run tools/poem_roundup.py)" >&2; exit 1; }

echo "==> 1/4  upload"
ssh "$HOST" "mkdir -p $ROOT/app"
rsync -rlt --delete "$HERE/site/" "$HOST:$ROOT/app/"
ssh "$HOST" "chown -R www-data:www-data $ROOT/app && find $ROOT/app -type d -exec chmod 755 {} + && find $ROOT/app -type f -exec chmod 644 {} +"

echo "==> 2/4  nginx bootstrap + cert (first run only)"
if ! ssh "$HOST" "test -d /etc/letsencrypt/live/$DOMAIN"; then
  ssh "$HOST" "cat > /etc/nginx/sites-available/$DOMAIN" <<NGINX
server {
    listen 80; listen [::]:80;
    server_name $DOMAIN;
    root $ROOT/app;
    location ^~ /.well-known/acme-challenge/ { root $ROOT/app; default_type "text/plain"; }
    location / { try_files \$uri \$uri/ =404; }
}
NGINX
  ssh "$HOST" "ln -sf /etc/nginx/sites-available/$DOMAIN /etc/nginx/sites-enabled/$DOMAIN && nginx -t && systemctl reload nginx"
  ssh "$HOST" "certbot certonly --webroot -w $ROOT/app -d $DOMAIN --non-interactive --agree-tos -m $EMAIL --keep-until-expiring"
fi

echo "==> 3/4  nginx TLS vhost"
ssh "$HOST" "cat > /etc/nginx/sites-available/$DOMAIN" <<NGINX
server {
    listen 80; listen [::]:80;
    server_name $DOMAIN;
    location ^~ /.well-known/acme-challenge/ { root $ROOT/app; default_type "text/plain"; }
    location / { return 301 https://\$host\$request_uri; }
}
server {
    listen 443 ssl http2; listen [::]:443 ssl http2;
    server_name $DOMAIN;
    root $ROOT/app;
    index index.html;
    ssl_certificate     /etc/letsencrypt/live/$DOMAIN/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/$DOMAIN/privkey.pem;
    include /etc/letsencrypt/options-ssl-nginx.conf;
    ssl_dhparam /etc/letsencrypt/ssl-dhparams.pem;
    add_header Strict-Transport-Security "max-age=31536000" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header Referrer-Policy "no-referrer" always;
    add_header X-Robots-Tag "noindex, nofollow" always;
    gzip on; gzip_types text/html text/css application/javascript application/json; gzip_min_length 1024;
    location ~ /\. { deny all; }
    # expires, not add_header: an add_header in a location drops the server-level headers above.
    # A week's page changes when the next week is added (the past-weeks list), so always revalidate.
    location / { try_files \$uri \$uri/ =404; expires -1; }
}
NGINX
ssh "$HOST" "nginx -t && systemctl reload nginx"

echo "==> 4/4  verify"
curl -sS -o /dev/null -w "GET / -> HTTP %{http_code}\n" "https://$DOMAIN/"
echo "DONE -> https://$DOMAIN"
