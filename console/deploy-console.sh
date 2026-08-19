#!/usr/bin/env bash
# Deploy the Morning Console to the tasks droplet: /var/www/tasks/morning/
# (served at https://tasks.benmartel.com/morning/). State + token live in
# /var/www/tasks-private/ (outside the docroot). Token source of truth:
# BRIEF_CONSOLE_TOKEN in ~/.claude/.env — pushed into morning-config.php here.
set -euo pipefail
HOST="${TASKS_HOST:-root@178.128.155.186}"
DOCROOT="${TASKS_DOCROOT:-/var/www/tasks}"
PRIVDIR="${TASKS_PRIVDIR:-/var/www/tasks-private}"
cd "$(dirname "$0")"

set -a; . "$HOME/.claude/.env"; set +a
[ -n "${BRIEF_CONSOLE_TOKEN:-}" ] || { echo "BRIEF_CONSOLE_TOKEN missing from ~/.claude/.env"; exit 1; }

echo "==> console php -> $HOST:$DOCROOT/morning/"
rsync -az --exclude='deploy-console.sh' --exclude='.DS_Store' ./ "$HOST:$DOCROOT/morning/"

echo "==> private config + state perms"
ssh "$HOST" "mkdir -p $PRIVDIR \
  && printf '<?php define(%s, %s);\n' \"'MORNING_TOKEN'\" \"'$BRIEF_CONSOLE_TOKEN'\" > $PRIVDIR/morning-config.php \
  && touch $PRIVDIR/morning-state.json \
  && chown -R www-data:www-data $PRIVDIR $DOCROOT/morning \
  && chmod 640 $PRIVDIR/morning-config.php $PRIVDIR/morning-state.json"
echo "==> done: https://tasks.benmartel.com/morning/"
