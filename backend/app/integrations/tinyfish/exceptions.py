class TinyFishError(Exception):
    """Base TinyFish integration error."""


class TinyFishConfigError(TinyFishError):
    """API key or base URL missing."""


class TinyFishAuthError(TinyFishError):
    """Missing or invalid API key."""


class TinyFishRateLimitError(TinyFishError):
    def __init__(self, message: str, retry_after: float | None = None):
        super().__init__(message)
        self.retry_after = retry_after


class TinyFishRunError(TinyFishError):
    """Browser run failed or timed out."""


class TinyFishSSRFError(TinyFishError):
    """URL is not allowed as a browser destination."""
