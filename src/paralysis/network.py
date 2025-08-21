from pathlib import Path

from requests import Session
from requests_cache import CacheMixin
from requests_ratelimiter import LimiterMixin, SQLiteBucket


class CachedLimiterSession(CacheMixin, LimiterMixin, Session):
    """
    Session class with caching and rate-limiting behavior. Accepts arguments for both
    LimiterSession and CachedSession.
    """


def make_cached_limiter_session(cache_db: str | Path):
    return CachedLimiterSession(
        per_minute=500,
        per_hour=3600,
        cache_name=cache_db,
        bucket_class=SQLiteBucket,
        bucket_kwargs={
            "path": cache_db,
            "isolation_level": "EXCLUSIVE",
            "check_same_thread": False,
        },
    )
