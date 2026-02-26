import signal
import sys
from gunicorn import glogging


# Gunicorn configuration
timeout = 90  # Worker heartbeat timeout - must exceed max request duration
graceful_timeout = 60  # Grace period for workers to finish after receiving SIGTERM

# Access logging configuration
accesslog = 'logs/access.log'
access_log_format = '%({X-Real-IP}i)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" %(D)s'
# Format explanation:
# %({X-Real-IP}i)s - Real client IP from X-Real-IP header (set by nginx proxy)
# %(l)s - '-' (remote log name, usually just a dash)
# %(u)s - User name (from HTTP auth, usually just a dash)
# %(t)s - Date/time of request
# %(r)s - Request line (method, path, protocol)
# %(s)s - Status code
# %(b)s - Response length in bytes
# %(f)s - Referer header
# %(a)s - User agent
# %(D)s - Request time in microseconds
