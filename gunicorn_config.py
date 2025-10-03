import signal
import sys
from gunicorn import glogging


# Gunicorn configuration
timeout = 30  # Worker timeout in seconds
graceful_timeout = 5  # Grace period for workers to finish after receiving SIGTERM
