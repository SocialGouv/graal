"""Shared executors for offloading CPU-bound work.

Why this exists
---------------
The web API runs on an asyncio event loop (FastAPI/Uvicorn). CPU-bound work
(TF-IDF, clustering, large pandas operations, etc.) must not run on the event
loop, otherwise it will block unrelated requests (e.g. S3 listing endpoints).

We therefore provide dedicated executors for specific workloads.
"""

from __future__ import annotations

import os
import threading
from concurrent.futures import ThreadPoolExecutor

_db_build_executor: ThreadPoolExecutor | None = None
_lock = threading.Lock()


def shutdown_db_build_executor(
    *, wait: bool = True, cancel_futures: bool = True
) -> None:
    """Shutdown the process-wide similarity DB build executor.

    This is important for long-lived processes and test suites:
    - prevents leaking threads/resources
    - avoids cross-test global state contamination

    This function is idempotent and safe to call multiple times.

    Args:
        wait: Whether to wait for currently running tasks to complete.
        cancel_futures: Whether to cancel pending futures.
    """

    global _db_build_executor

    with _lock:
        executor = _db_build_executor
        _db_build_executor = None

    if executor is None:
        return

    executor.shutdown(wait=wait, cancel_futures=cancel_futures)


def get_db_build_executor() -> ThreadPoolExecutor:
    """Return a process-wide executor dedicated to similarity DB builds.

    Notes:
        - We keep this separate from the default asyncio executor to avoid
          starving unrelated `asyncio.to_thread(...)` calls (e.g. S3 config I/O).
        - Default worker count is conservative; tune via DB_BUILD_MAX_WORKERS.
    """

    global _db_build_executor

    if _db_build_executor is None:
        with _lock:
            if _db_build_executor is None:
                max_workers = int(os.getenv("DB_BUILD_MAX_WORKERS", "2"))
                if max_workers < 1:
                    max_workers = 1
                _db_build_executor = ThreadPoolExecutor(
                    max_workers=max_workers,
                    thread_name_prefix="graal-db-build",
                )

    return _db_build_executor
