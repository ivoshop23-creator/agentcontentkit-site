#!/bin/sh
# API on 127.0.0.1:8000 (restarted if it ever exits), nginx in the foreground on :80
(while true; do python3 /app/app.py; echo "api exited, restarting" >&2; sleep 1; done) &
exec nginx -g 'daemon off;'
