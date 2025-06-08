"""
Core types and functional utilities for the application.
"""

from typing import Any, Callable, Dict, Iterable, List, Optional, TypeVar, Union
from functools import reduce, wraps
import time
from contextlib import contextmanager

__author__ = "Lâm Quang Trí"
__copyright__ = "Copyright 2025, Lâm Quang Trí"
__credits__ = ["Lâm Quang Trí"]

__maintainer__ = "Lâm Quang Trí"
__email__ = "quangtri.lam.9@gmail.com"
__status__ = "Development"


# Type variables for generic functions
T = TypeVar("T")
U = TypeVar("U")
V = TypeVar("V")

# Common type aliases
JSON = Dict[str, Any]
JSONList = List[JSON]


class Result:
    """Functional Result type for error handling."""

    def __init__(self, value: Any = None, error: Optional[Exception] = None):
        self._value = value
        self._error = error
        self._is_success = error is None

    @classmethod
    def success(cls, value: Any) -> "Result":
        """Create a successful result."""
        return cls(value=value)

    @classmethod
    def failure(cls, error: Exception) -> "Result":
        """Create a failed result."""
        return cls(error=error)

    @property
    def is_success(self) -> bool:
        """Check if result is successful."""
        return self._is_success

    @property
    def is_failure(self) -> bool:
        """Check if result is a failure."""
        return not self._is_success

    @property
    def value(self) -> Any:
        """Get the value (raises exception if failure)."""
        if self._is_success:
            return self._value
        raise self._error

    @property
    def error(self) -> Optional[Exception]:
        """Get the error."""
        return self._error

    def map(self, func: Callable[[Any], Any]) -> "Result":
        """Map function over successful result."""
        if self._is_success:
            try:
                return Result.success(func(self._value))
            except Exception as e:
                return Result.failure(e)
        return self

    def flat_map(self, func: Callable[[Any], "Result"]) -> "Result":
        """Flat map function over successful result."""
        if self._is_success:
            try:
                return func(self._value)
            except Exception as e:
                return Result.failure(e)
        return self

    def or_else(self, default: Any) -> Any:
        """Get value or default if failure."""
        return self._value if self._is_success else default

    def on_failure(self, func: Callable[[Exception], Any]) -> "Result":
        """Execute function on failure."""
        if self._is_success:
            return self
        try:
            func(self._error)
        except Exception:
            pass  # Ignore exceptions in error handlers
        return self


class Maybe:
    """Functional Maybe type for null safety."""

    def __init__(self, value: Any):
        self._value = value

    @classmethod
    def of(cls, value: Any) -> "Maybe":
        """Create Maybe instance."""
        return cls(value)

    @classmethod
    def none(cls) -> "Maybe":
        """Create empty Maybe."""
        return cls(None)

    @property
    def is_present(self) -> bool:
        """Check if value is present."""
        return self._value is not None

    @property
    def is_empty(self) -> bool:
        """Check if value is empty."""
        return self._value is None

    def get(self) -> Any:
        """Get the value (raises exception if empty)."""
        if self._value is None:
            raise ValueError("Maybe is empty")
        return self._value

    def map(self, func: Callable[[Any], Any]) -> "Maybe":
        """Map function over non-empty value."""
        if self._value is not None:
            try:
                return Maybe.of(func(self._value))
            except Exception:
                return Maybe.none()
        return self

    def flat_map(self, func: Callable[[Any], "Maybe"]) -> "Maybe":
        """Flat map function over non-empty value."""
        if self._value is not None:
            try:
                return func(self._value)
            except Exception:
                return Maybe.none()
        return self

    def filter(self, predicate: Callable[[Any], bool]) -> "Maybe":
        """Filter value with predicate."""
        if self._value is not None:
            try:
                return self if predicate(self._value) else Maybe.none()
            except Exception:
                return Maybe.none()
        return self

    def or_else(self, default: Any) -> Any:
        """Get value or default if empty."""
        return self._value if self._value is not None else default

    def if_present(self, func: Callable[[Any], Any]) -> "Maybe":
        """Execute function if value is present."""
        if self._value is not None:
            try:
                func(self._value)
            except Exception:
                pass  # Ignore exceptions in side effects
        return self


# Functional utility functions
def safe_call(func: Callable[..., T]) -> Callable[..., Result]:
    """Decorator to safely call function and return Result."""

    @wraps(func)
    def wrapper(*args, **kwargs) -> Result:
        try:
            result = func(*args, **kwargs)
            return Result.success(result)
        except Exception as e:
            return Result.failure(e)

    return wrapper


def curry(func: Callable) -> Callable:
    """Curry a function."""

    @wraps(func)
    def curried(*args, **kwargs):
        if len(args) + len(kwargs) >= func.__code__.co_argcount:
            return func(*args, **kwargs)
        return lambda *more_args, **more_kwargs: curried(
            *(args + more_args), **{**kwargs, **more_kwargs}
        )

    return curried


def compose(*functions: Callable) -> Callable:
    """Compose functions from right to left."""

    def _compose(f: Callable, g: Callable) -> Callable:
        return lambda x: f(g(x))

    return reduce(_compose, functions, lambda x: x)


def pipe(value: T, *functions: Callable[[T], T]) -> T:
    """Pipe value through functions from left to right."""
    return reduce(lambda acc, func: func(acc), functions, value)


def partial_apply(func: Callable, *args, **kwargs) -> Callable:
    """Partially apply function arguments."""

    @wraps(func)
    def wrapper(*more_args, **more_kwargs):
        return func(*args, *more_args, **kwargs, **more_kwargs)

    return wrapper


def memoize(func: Callable) -> Callable:
    """Memoize function results."""
    cache = {}

    @wraps(func)
    def wrapper(*args, **kwargs):
        # Create a key from args and kwargs
        key = str(args) + str(sorted(kwargs.items()))
        if key not in cache:
            cache[key] = func(*args, **kwargs)
        return cache[key]

    return wrapper


def retry(max_attempts: int = 3, delay: float = 1.0) -> Callable:
    """Retry decorator for functions."""

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None
            for attempt in range(max_attempts):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    if attempt < max_attempts - 1:
                        time.sleep(delay)
                    continue
            raise last_exception

        return wrapper

    return decorator


def timing(func: Callable) -> Callable:
    """Timing decorator for functions."""

    @wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.time()
        try:
            result = func(*args, **kwargs)
            end_time = time.time()
            return result, end_time - start_time
        except Exception as e:
            end_time = time.time()
            raise e

    return wrapper


@contextmanager
def exception_handler(default_value: Any = None, log_func: Optional[Callable] = None):
    """Context manager for safe exception handling."""
    try:
        yield
    except Exception as e:
        if log_func:
            log_func(f"Exception handled: {e}")
        return default_value


# Functional list operations
def map_safe(func: Callable[[T], U], items: Iterable[T]) -> List[Result]:
    """Map function safely over items, returning Results."""
    return [safe_call(func)(item) for item in items]


def filter_map(func: Callable[[T], Optional[U]], items: Iterable[T]) -> List[U]:
    """Filter and map in one operation."""
    results = []
    for item in items:
        result = func(item)
        if result is not None:
            results.append(result)
    return results


def partition(
    predicate: Callable[[T], bool], items: Iterable[T]
) -> tuple[List[T], List[T]]:
    """Partition items based on predicate."""
    true_items, false_items = [], []
    for item in items:
        if predicate(item):
            true_items.append(item)
        else:
            false_items.append(item)
    return true_items, false_items


def group_by(key_func: Callable[[T], str], items: Iterable[T]) -> Dict[str, List[T]]:
    """Group items by key function."""
    groups = {}
    for item in items:
        key = key_func(item)
        if key not in groups:
            groups[key] = []
        groups[key].append(item)
    return groups


def flatten(nested_list: Iterable[Iterable[T]]) -> List[T]:
    """Flatten nested list."""
    result = []
    for sublist in nested_list:
        result.extend(sublist)
    return result


def take(n: int, items: Iterable[T]) -> List[T]:
    """Take first n items."""
    result = []
    for i, item in enumerate(items):
        if i >= n:
            break
        result.append(item)
    return result


def drop(n: int, items: List[T]) -> List[T]:
    """Drop first n items."""
    return items[n:]


def chunk(size: int, items: List[T]) -> List[List[T]]:
    """Split list into chunks of given size."""
    return [items[i : i + size] for i in range(0, len(items), size)]


# Validation utilities
def validate_not_empty(value: str, field_name: str = "field") -> Result:
    """Validate that string is not empty."""
    if not value or not value.strip():
        return Result.failure(ValueError(f"{field_name} cannot be empty"))
    return Result.success(value.strip())


def validate_positive(value: Union[int, float], field_name: str = "field") -> Result:
    """Validate that number is positive."""
    if value <= 0:
        return Result.failure(ValueError(f"{field_name} must be positive"))
    return Result.success(value)


def validate_range(
    value: Union[int, float],
    min_val: Union[int, float],
    max_val: Union[int, float],
    field_name: str = "field",
) -> Result:
    """Validate that value is in range."""
    if not (min_val <= value <= max_val):
        return Result.failure(
            ValueError(f"{field_name} must be between {min_val} and {max_val}")
        )
    return Result.success(value)
