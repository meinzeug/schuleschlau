"""Bound large synchronous image operations within one API worker."""

import threading

# Synchronous endpoints hold this until their worker finishes, even when an
# ASGI client disconnects. The current deployment has one API worker; this
# process-local slot does not coordinate a multiworker deployment.
SYNC_IMAGE_SLOT = threading.BoundedSemaphore(1)
