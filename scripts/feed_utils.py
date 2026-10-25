"""Validated ESPN reads and atomic snapshot publication."""
import csv
import json
import os
import tempfile
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path


def fetch_json(url, array_key='events', attempts=3):
    for attempt in range(attempts):
        try:
            request = urllib.request.Request(url, headers={'User-Agent': 'NBAEdgeResearch/1.0'})
            with urllib.request.urlopen(request, timeout=25) as response:
                payload = json.load(response)
            if not isinstance(payload, dict) or not isinstance(payload.get(array_key), list):
                raise ValueError(f'ESPN response is missing {array_key} array')
            return payload
        except urllib.error.HTTPError as exc:
            if exc.code not in (429, 500, 502, 503, 504) or attempt == attempts - 1:
                raise
        except (urllib.error.URLError, TimeoutError, OSError):
            if attempt == attempts - 1:
                raise
        time.sleep(2 ** attempt)


def atomic_text(path, text):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(dir=path.parent, prefix='.' + path.name)
    try:
        with os.fdopen(fd, 'w', encoding='utf-8', newline='') as output:
            output.write(text)
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def write_rows(path, fields, rows):
    import io
    output = io.StringIO(newline='')
    writer = csv.DictWriter(output, fieldnames=fields, extrasaction='ignore', lineterminator='\n')
    writer.writeheader()
    writer.writerows(rows)
    atomic_text(path, output.getvalue())


def feed_status(data, feed, error=None, rows=None):
    path = Path(data) / f'{feed}_status.json'
    try:
        previous = json.loads(path.read_text())
    except (OSError, ValueError):
        previous = {}
    now = datetime.now(timezone.utc).isoformat()
    status = {'last_attempt_utc': now, 'last_success_utc': previous.get('last_success_utc'),
              'errors': [str(error)] if error else [], 'source': 'ESPN'}
    if error is None:
        status.update(last_success_utc=now, rows=rows)
    atomic_text(path, json.dumps(status, indent=2) + '\n')
