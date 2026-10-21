"""WSGI settings: run gunicorn -c backend/gunicorn.conf.py 'backend.app:create_app()'."""
import os

bind = os.getenv('TRIPGENIE_BIND', '127.0.0.1:5001')
workers = 2
timeout = 30
accesslog = '-'
errorlog = '-'
# Route paths only: omit query strings, bodies, headers, and referrers.
access_log_format = '%({x-request-id}o)s %(m)s %(U)s %(s)s %(L)s'
