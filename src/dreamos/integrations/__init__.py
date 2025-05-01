"""Initialize the integrations package."""


# Maybe define base exceptions here later
class IntegrationError(Exception):
    "Base exception for integration client errors."
    pass


class APIError(IntegrationError):
    "Exception for API-specific errors (e.g., 4xx, 5xx)."
    pass
