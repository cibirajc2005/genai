"""Small process-local fallback for optional agent persistence tables.

Database storage remains authoritative when installed. This store keeps the feature
usable on fresh deployments until the additive Supabase migration is applied.
"""

from collections import deque
from threading import Lock

_runs: deque[dict] = deque(maxlen=100)
_reviews: deque[dict] = deque(maxlen=100)
_lock = Lock()


def remember_run(item: dict) -> None:
    with _lock:
        _runs.appendleft(item)


def recent_runs() -> list[dict]:
    with _lock:
        return list(_runs)


def remember_review(item: dict) -> None:
    with _lock:
        _reviews.appendleft(item)
