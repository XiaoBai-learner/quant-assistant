"""Provider exceptions."""


class ProviderError(RuntimeError):
    """Base error for external data provider failures."""


class ProviderHTTPError(ProviderError):
    """Raised when an HTTP provider returns an invalid response."""


class ProviderParseError(ProviderError):
    """Raised when provider payload parsing fails."""
