"""Core exception hierarchy."""


class OSINTError(Exception):
    """Base error for the framework."""


class DiscoveryError(OSINTError):
    """Search/discovery failures."""


class CollectionError(OSINTError):
    """Page/image collection failures."""


class ExtractionError(OSINTError):
    """HTML extraction failures."""


class StorageError(OSINTError):
    """Report storage failures."""


class ConfigurationError(OSINTError):
    """Invalid configuration."""
