#!/bin/bash
set -euxo pipefail

python3 -m flask db upgrade # this does not actually return error codes properly!
python3 -m flask cron_setup

# Seed the cached leaderboards once so they're populated immediately after
# deploy, rather than only after the daily leaderboard_recalc cron job first
# runs. Non-critical: never let a seeding hiccup block the site from starting.
python3 -m flask leaderboard_recalc || true

if [[ ! -f prebuilt.flag ]]; then
    ./bootstrap/init_build.sh
fi

/usr/local/bin/supervisord -c /etc/supervisord.conf
