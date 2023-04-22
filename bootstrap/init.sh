#!/bin/bash
set -euxo pipefail

python3 -m flask db upgrade # this does not actually return error codes properly!

/usr/local/bin/supervisord -c /etc/supervisord.conf
