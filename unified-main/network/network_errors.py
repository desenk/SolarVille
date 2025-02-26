# Branch: unified-main
# File: network/network_errors.py

"""
Network error classes for SolarVille system.
Provides specific exception types for different network failure scenarios.
"""

class NetworkError(Exception):
    """Base exception for all network-related errors"""
    pass

class ConnectionFailedError(NetworkError):
    """Raised when connection to a peer fails"""
    pass

class TimeoutError(NetworkError):
    """Raised when a request times out"""
    pass

class ResponseError(NetworkError):
    """Raised when a response has an error status code"""
    pass

class AuthenticationError(NetworkError):
    """Raised when authentication fails"""
    pass

class DeserializationError(NetworkError):
    """Raised when response data cannot be deserialized"""
    pass

class SynchronizationError(NetworkError):
    """Raised when timestamp synchronization fails"""
    pass

class PeerUnavailableError(NetworkError):
    """Raised when a peer is unavailable for trading"""
    pass

class NetworkRecoveryError(NetworkError):
    """Raised when network recovery attempts fail"""
    pass