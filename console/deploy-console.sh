#!/usr/bin/env bash
# Deploy the Morning Console to the tasks droplet: /var/www/morning/
# (served at https://tasks.benmartel.com/morning/ via its own nginx location).
# NOT inside /var/www/tasks — the tasks app deploys with rsync --delete and
# wiped the console once (2026-08-20) when it lived there. State + token live
# in /var/www/tasks-private/. Token source of truth: BRIEF_CONSOLE_TOKEN in
# ~/.claude/.env — pushed into morning-config.php here (with the preview keys).
set -euo pipefail
HOST="${TASKS_HOST:-root@178.128.155.186}"
DOCROOT="${MORNING_ROOT:-/var/www/morning}"
PRIVDIR="${TASKS_PRIVDIR:-/var/www/tasks-private}"
cd "$(dirname "$0")"

set -a; . "$HOME/.claude/.env"; set +a
[ -n "${BRIEF_CONSOLE_TOKEN:-}" ] || { echo "BRIEF_CONSOLE_TOKEN missing from ~/.claude/.env"; exit 1; }

echo "==> console php -> $HOST:$DOCROOT/"
rsync -az --exclude='deploy-console.sh' --exclude='.DS_Store' ./ "$HOST:$DOCROOT/"

echo "==> private config (token + preview keys) + state perms"
CFG=$(mktemp)
cat > "$CFG" << EOF
<?php
define('MORNING_TOKEN', '$BRIEF_CONSOLE_TOKEN');
define('MORNING_ANTHROPIC_KEY', '${ANTHROPIC_API_KEY:-}');
define('MORNING_OPENAI_KEY', '${OPENAI_API_KEY:-}');
EOF
ssh "$HOST" "mkdir -p $PRIVDIR"
rsync -az "$CFG" "$HOST:$PRIVDIR/morning-config.php"
rm -f "$CFG"
ssh "$HOST" "touch $PRIVDIR/morning-state.json $PRIVDIR/morning-versions.json \
  && chown -R www-data:www-data $PRIVDIR $DOCROOT \
  && chmod 640 $PRIVDIR/morning-config.php $PRIVDIR/morning-state.json $PRIVDIR/morning-versions.json"
echo "==> done: https://tasks.benmartel.com/morning/"
