"""
Utility functions for retry logic.
"""

import random
from typing import Type, Tuple, Optional
from loguru import logger

from src.core.simple_config import settings


class RetryableError(Exception):
    """Base class for errors that should trigger a retry."""
    pass


class NonRetryableError(Exception):
    """Base class for errors that should not trigger a retry."""
    pass


class RetryConfig:
    """Configuration for retry behavior."""

    def __init__(
        self,
        max_attempts: int = None,
        initial_delay: float = None,
        max_delay: float = None,
        backoff_multiplier: float = None,
        jitter: bool = None,
        timeout: float = None
    ):
        """
        Initialize retry configuration.

        Args:
            max_attempts: Maximum number of retry attempts
            initial_delay: Initial delay between retries in seconds
            max_delay: Maximum delay between retries in seconds
            backoff_multiplier: Exponential backoff multiplier
            jitter: Whether to add jitter to prevent thundering herd
            timeout: Request timeout in seconds
        """
        self.max_attempts = max_attempts or settings.mcp_retry_max_attempts
        self.initial_delay = initial_delay or settings.mcp_retry_initial_delay
        self.max_delay = max_delay or settings.mcp_retry_max_delay
        self.backoff_multiplier = backoff_multiplier or settings.mcp_retry_backoff_multiplier
        self.jitter = jitter if jitter is not None else settings.mcp_retry_jitter
        self.timeout = timeout or settings.mcp_request_timeout


def calculate_delay(attempt: int, config: RetryConfig) -> float:
    """
    Calculate the delay for the next retry attempt using exponential backoff.

    Args:
        attempt: Current attempt number (0-based)
        config: Retry configuration

    Returns:
        Delay in seconds
    """
    # Calculate exponential backoff delay
    delay = config.initial_delay * (config.backoff_multiplier ** attempt)

    # Cap at maximum delay
    delay = min(delay, config.max_delay)

    # Add jitter if enabled (±20% random variation)
    if config.jitter:
        jitter_factor = 0.8 + 0.4 * random.random()  # Random between 0.8 and 1.2
        delay *= jitter_factor

    return delay


def is_retryable_error(error: Exception) -> bool:
    """
    Determine if an error should trigger a retry.

    Args:
        error: The exception that occurred

    Returns:
        True if the error is retryable, False otherwise
    """
    # Always retry RetryableError
    if isinstance(error, RetryableError):
        return True

    # Never retry NonRetryableError
    if isinstance(error, NonRetryableError):
        return False

    # Check for HTTP-related errors by name (avoid direct imports)
    error_name = type(error).__name__
    error_module = type(error).__module__

    # Handle HTTP client errors generically
    if 'httpx' in error_module or 'requests' in error_module:
        # Retry connection errors, timeouts, and network issues
        if error_name in (
            'ConnectError', 'TimeoutException', 'NetworkError',
            'PoolTimeout', 'ReadTimeout', 'WriteTimeout', 'ConnectTimeout',
            'ConnectionError', 'Timeout', 'RequestException'
        ):
            return True

        # Handle HTTP status errors
        if error_name in ('HTTPStatusError', 'HTTPError'):
            # Try to get status code from the error
            if hasattr(error, 'response') and hasattr(error.response, 'status_code'):
                status_code = error.response.status_code
                # Retry on server errors (5xx) and specific client errors
                if status_code >= 500:
                    return True
                if status_code in (408, 429):  # Request Timeout, Too Many Requests
                    return True
            return False

    # Retry on general network/connection issues
    if isinstance(error, (OSError, ConnectionError, TimeoutError)):
        return True

    # Don't retry other errors by default
    return False


def should_retry(
    error: Exception,
    retryable_exceptions: Optional[Tuple[Type[Exception], ...]] = None
) -> bool:
    """
    Check if an error should trigger a retry.

    Args:
        error: The exception that occurred
        retryable_exceptions: Additional exception types to consider retryable

    Returns:
        True if the error is retryable, False otherwise
    """
    # Check if error is retryable
    is_retryable = is_retryable_error(error)

    # Also check custom retryable exceptions
    if not is_retryable and retryable_exceptions:
        is_retryable = isinstance(error, retryable_exceptions)

    return is_retryable


def log_retry_attempt(func_name: str, attempt: int, max_attempts: int, error: Exception, delay: float) -> None:
    """Log a retry attempt."""
    logger.warning(
        f"Function {func_name} failed (attempt {attempt + 1}/{max_attempts}). "
        f"Error: {type(error).__name__}: {error}. "
        f"Retrying in {delay:.2f}s..."
    )


def log_final_failure(func_name: str, max_attempts: int, error: Exception) -> None:
    """Log final failure after all retries exhausted."""
    logger.error(
        f"Function {func_name} failed after {max_attempts} attempts. "
        f"Final error: {type(error).__name__}: {error}"
    )


def log_non_retryable_error(func_name: str, error: Exception) -> None:
    """Log non-retryable error."""
    logger.error(
        f"Function {func_name} failed with non-retryable error: "
        f"{type(error).__name__}: {error}"
    )