"""
This module contains validator functions for use with `attrs` class definitions.
"""


def gt_zero(instance, attribute, value):
    """Validates that an attribute's value is greater than zero."""
    if value <= 0:
        raise ValueError(f"{attribute} must be greater than zero")


def gte_zero(instance, attribute, value):
    """Validates that an attribute's value is greater than or equal to zero."""
    if value < 0:
        raise ValueError(f"{attribute} must be greater than or equal to zero")


def range_val(min_val, max_val):
    """Validates that an attribute's value is between two values, inclusive ([min_val, max_val])."""

    def validator(instance, attribute, value):
        if value < min_val or value > max_val:
            raise ValueError(f"{attribute} must be in range [{min_val}, {max_val}]")

    return validator


def contains(items):
    """Validates that an item is part of a given list."""

    def validator(instance, attribute, value):
        if value not in items:
            raise ValueError(f"Item {value} not found in list for {attribute}: {items}")

    return validator
