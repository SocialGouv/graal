import threading
import time
from typing import Optional


class RateLimiter:
    def __init__(self, calls_per_minute: float):
        self.interval = 60.0 / calls_per_minute
        self.lock = threading.Lock()
        self.next_allowed_time = time.perf_counter()

    def acquire(self):
        with self.lock:
            now = time.perf_counter()
            # If we're too early for the next call, sleep until allowed
            if now < self.next_allowed_time:
                time.sleep(self.next_allowed_time - now)
            # After sleeping or if we were allowed immediately, set the next allowed time
            self.next_allowed_time = time.perf_counter() + self.interval

    # Implement __getstate__ and __setstate__ to make the class pickleable
    def __getstate__(self):
        # Return the instance state without the lock
        state = self.__dict__.copy()
        # Remove the lock before pickling
        state.pop("lock", None)
        return state

    def __setstate__(self, state):
        # Restore the instance state from the unpickled dictionary
        self.__dict__.update(state)
        # Recreate a new lock since it's not pickleable
        self.lock = threading.Lock()


class TokenBucketRateLimiter:
    def __init__(self, rate_per_minute: int, capacity: Optional[int] = None):
        """
        rate_per_minute: Tokens added per minute
        capacity: Max number of tokens in the bucket
        """
        if capacity is None:
            capacity = rate_per_minute
        self.rate = rate_per_minute / 60.0  # Convert rate to tokens per second
        self.capacity = capacity
        self.tokens = 0
        self.lock = threading.Lock()
        self.last_refill = time.perf_counter()

    def acquire(self, tokens: int = 1):
        with self.lock:
            self._refill()
            while self.tokens < tokens:
                # Not enough tokens, wait until next refill
                sleep_time = (tokens - self.tokens) / self.rate
                time.sleep(sleep_time)
                self._refill()
            self.tokens -= tokens

    def _refill(self):
        now = time.perf_counter()
        elapsed = now - self.last_refill
        # Add tokens based on the elapsed time
        new_tokens = int(elapsed * self.rate)
        if new_tokens > 0:
            self.tokens = min(self.capacity, self.tokens + new_tokens)
            self.last_refill = now

    # Implement __getstate__ and __setstate__ to make the class pickleable
    def __getstate__(self):
        # Return the instance state without the lock
        state = self.__dict__.copy()
        # Remove the lock before pickling
        state.pop("lock", None)
        return state

    def __setstate__(self, state):
        # Restore the instance state from the unpickled dictionary
        self.__dict__.update(state)
        # Recreate a new lock since it's not pickleable
        self.lock = threading.Lock()
        self.tokens = 0
