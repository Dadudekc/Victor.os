class ConfigurationError(Exception):
    """Raised when there is a problem with required configuration."""

    pass


# Optional alias for legacy imports
CoreConfigurationError = ConfigurationError
