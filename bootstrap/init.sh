#!/bin/bash
set -euxo pipefail

python3 -m flask db upgrade # this does not actually return error codes properly!
python3 -m flask cron_setup

if [[ ! -f prebuilt.flag ]]; then
    ./bootstrap/init_build.sh
fi

/usr/local/bin/supervisord -c /etc/supervisord.conf
