"""Resolve the same saved specification from public and QA playback routes."""
from urllib.parse import urlsplit, unquote


def playback_job_id(url: str) -> str | None:
    parts=urlsplit(url).path.strip('/').split('/')
    if len(parts)==3 and parts[0]=='studio' and parts[1] in ('play','verify'):
        return unquote(parts[2])
    return None
