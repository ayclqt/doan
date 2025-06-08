"""
Core module providing functional programming utilities and types.
"""

from .types import (
    Result,
    Maybe,
    safe_call,
    curry,
    compose,
    pipe,
    partial_apply,
    memoize,
    retry,
    timing,
    exception_handler,
    map_safe,
    filter_map,
    partition,
    group_by,
    flatten,
    take,
    drop,
    chunk,
    validate_not_empty,
    validate_positive,
    validate_range,
    T,
    U,
    V,
    JSON,
    JSONList,
)

__all__ = [
    # Core types
    "Result",
    "Maybe",
    # Function decorators and utilities
    "safe_call",
    "curry",
    "compose",
    "pipe",
    "partial_apply",
    "memoize",
    "retry",
    "timing",
    "exception_handler",
    # List operations
    "map_safe",
    "filter_map",
    "partition",
    "group_by",
    "flatten",
    "take",
    "drop",
    "chunk",
    # Validation utilities
    "validate_not_empty",
    "validate_positive",
    "validate_range",
    # Type variables
    "T",
    "U",
    "V",
    "JSON",
    "JSONList",
]
