from datetime import datetime, timedelta, timezone


class RateLimiter:
    def __init__(self, sustained_rate: float = 1000.0, burst_size: int = 1000):
        """
        A rate limiter which can be used to ensure that a user does not exhaust their
        allowed request quota within a given time window.

        Args:
            sustained_rate (float): The rate at which requests are allowed (requests per minute).
            burst_size (int): The maximum number of requests allowed in a burst, before sustained rate limiting is applied.
        """
        self.sustained_rate = sustained_rate
        self.burst_size = burst_size

        self._request_cost = timedelta(seconds=60.0 / sustained_rate)  # Cost of a single request in seconds
        self._max_age = burst_size * self._request_cost  # Maximum window for requests

    def try_make_request(self, watermark: datetime | float | None) -> tuple[bool, datetime]:
        """
        Attempts to make a request within the rate limit window, and returns an indicator
        of whether the request is allowed, and the updated watermark.
        """
        current_time = datetime.now(timezone.utc)  # Always timezone-aware

        # Ensure watermark is offset-aware or set to a default
        if watermark is None:
            watermark = current_time - self._max_age
        if isinstance(watermark, float):
            watermark = datetime.fromtimestamp(watermark, tz=timezone.utc)

        watermark = max(current_time - self._max_age, watermark)

        # Check if the request can be made and update the watermark if allowed
        if watermark + self._request_cost <= current_time:
            watermark += self._request_cost
            return True, watermark

        return False, watermark
