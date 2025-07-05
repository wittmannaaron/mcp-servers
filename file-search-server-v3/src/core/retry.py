"""
Retry logic with exponential backoff for resilient network operations.
"""

import asyncio
import functools
import time
from typing import Any, Callable, Optional, Type, Tuple

from src.core.retry_utils import (
    RetryConfig, RetryableError, NonRetryableError,
    calculate_delay, should_retry,
    log_retry_attempt, log_final_failure, log_non_retryable_error
)


def retry_with_backoff(
    config: Optional[RetryConfig] = None,
    retryable_exceptions: Optional[Tuple[Type[Exception], ...]] = None
) -> Callable:
    """
    Decorator that adds retry logic with exponential backoff to async functions.

    Args:
        config: Retry configuration. If None, uses default settings.
        retryable_exceptions: Additional exception types to consider retryable.

    Returns:
        Decorated function with retry logic
    """
    if config is None:
        config = RetryConfig()

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs) -> Any:
            last_exception = None

            for attempt in range(config.max_attempts):
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    last_exception = e

                    # Check if this is the last attempt
                    if attempt == config.max_attempts - 1:
                        log_final_failure(func.__name__, config.max_attempts, e)
                        raise

                    # Check if error is retryable
                    if not should_retry(e, retryable_exceptions):
                        log_non_retryable_error(func.__name__, e)
                        raise

                    # Calculate delay for next attempt
                    delay = calculate_delay(attempt, config)
                    log_retry_attempt(func.__name__, attempt, config.max_attempts, e, delay)

                    # Wait before retrying
                    await asyncio.sleep(delay)

            # This should never be reached, but just in case
            if last_exception:
                raise last_exception

        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs) -> Any:
            last_exception = None

            for attempt in range(config.max_attempts):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_exception = e

                    # Check if this is the last attempt
                    if attempt == config.max_attempts - 1:
                        log_final_failure(func.__name__, config.max_attempts, e)
                        raise

                    # Check if error is retryable
                    if not should_retry(e, retryable_exceptions):
                        log_non_retryable_error(func.__name__, e)
                        raise

                    # Calculate delay for next attempt
                    delay = calculate_delay(attempt, config)
                    log_retry_attempt(func.__name__, attempt, config.max_attempts, e, delay)

                    # Wait before retrying
                    time.sleep(delay)

            # This should never be reached, but just in case
            if last_exception:
                raise last_exception

        # Return appropriate wrapper based on whether function is async
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper

    return decorator


async def retry_async_operation(
    operation: Callable,
    *args,
    config: Optional[RetryConfig] = None,
    retryable_exceptions: Optional[Tuple[Type[Exception], ...]] = None,
    **kwargs
) -> Any:
    """
    Retry an async operation with exponential backoff.

    Args:
        operation: The async function to retry
        *args: Positional arguments for the operation
        config: Retry configuration
        retryable_exceptions: Additional exception types to consider retryable
        **kwargs: Keyword arguments for the operation

    Returns:
        Result of the operation

    Raises:
        The last exception if all retries fail
    """
    if config is None:
        config = RetryConfig()

    @retry_with_backoff(config, retryable_exceptions)
    async def wrapped_operation():
        return await operation(*args, **kwargs)

    return await wrapped_operation()


def retry_sync_operation(
    operation: Callable,
    *args,
    config: Optional[RetryConfig] = None,
    retryable_exceptions: Optional[Tuple[Type[Exception], ...]] = None,
    **kwargs
) -> Any:
    """
    Retry a sync operation with exponential backoff.

    Args:
        operation: The function to retry
        *args: Positional arguments for the operation
        config: Retry configuration
        retryable_exceptions: Additional exception types to consider retryable
        **kwargs: Keyword arguments for the operation

    Returns:
        Result of the operation

    Raises:
        The last exception if all retries fail
    """
    if config is None:
        config = RetryConfig()

    @retry_with_backoff(config, retryable_exceptions)
    def wrapped_operation():
        return operation(*args, **kwargs)

    return wrapped_operation()