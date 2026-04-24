# -*- coding: utf-8 -*-
"""This is :mod:`mpylab.device.validators`:

    This module provides validator helpers used by parameter handling code.
    A validator checks whether a value satisfies a given rule.

   :author: Christian Albrecht

   :license: GPL-3 or higher


"""


class IN_RANGE(object):
    """Validate that a numeric value is inside a closed interval."""

    def __init__(self, mini, maxi, message=''):
        """
        :param mini: Minimum allowed value.
        :param maxi: Maximum allowed value.
        :param message: Optional error message if validation fails.
        """
        self.min = mini
        self.max = maxi
        if message != '':
            self.message = f'Argument out of Range. Argument must be between {self.min} and {self.max}'
        else:
            self.message = message

    def __call__(self, value):
        """Validate ``value`` and return ``(value, error_message_or_None)``."""
        if not isinstance(value, (int, float)):
            return (value, 'The Validator IN_RANGE can only used for int, long or float')
        if value > self.max or value < self.min:
            return (value, self.message)
        return (value, None)


class IS_LOWER_THAN(object):
    """Validate that a numeric value is strictly smaller than a limit."""

    def __init__(self, maxi, message=''):
        """
        :param maxi: Upper bound (exclusive).
        :param message: Optional error message if validation fails.
        """
        self.max = maxi
        if message != '':
            self.message = f'Argument is greater than or equal {self.max}. Argument must be lower.'
        else:
            self.message = message

    def __call__(self, value):
        """Validate ``value`` and return ``(value, error_message_or_None)``."""
        if not isinstance(value, (int, float)):
            return (value, 'The Validator IS_LOWER_THAN can only used for int, long or float')
        if value >= self.max:
            return (value, self.message)
        return (value, None)


class IS_GREATER_THAN(object):
    """Validate that a numeric value is strictly greater than a limit."""

    def __init__(self, mini, message=''):
        """
        :param mini: Lower bound (exclusive).
        :param message: Optional error message if validation fails.
        """
        self.min = mini
        if message != '':
            self.message = f'Argument is lower than or equal {self.min}. Argument must be greater.'
        else:
            self.message = message

    def __call__(self, value):
        """Validate ``value`` and return ``(value, error_message_or_None)``."""
        if not isinstance(value, (int, float)):
            return (value, 'The Validator IS_GREATER_THAN can only used for int, long or float')
        if value <= self.min:
            return (value, self.message)
        return (value, None)


class IS_LOWER_EQUAL_THAN(object):
    """Validate that a numeric value is less than or equal to a limit."""

    def __init__(self, maxi, message=''):
        """
        :param maxi: Upper bound (inclusive).
        :param message: Optional error message if validation fails.
        """
        self.max = maxi
        if message != '':
            self.message = f'Argument is greater than {self.max}. Argument must be lower or equal.'
        else:
            self.message = message

    def __call__(self, value):
        if not isinstance(value, (int, float)):
            return (value, 'The Validator IS_LOWER_THAN can only used for int, long or float')
        if value > self.max:
            return (value, self.message)
        return (value, None)


class IS_GREATER_EQUAL_THAN(object):
    """Validate that a numeric value is greater than or equal to a limit."""

    def __init__(self, mini, message=''):
        """
        :param mini: Lower bound (inclusive).
        :param message: Optional error message if validation fails.
        """
        self.min = mini
        if message != '':
            self.message = f'Argument is lower than {self.min}. Argument must be greater or equal.'
        else:
            self.message = message

    def __call__(self, value):
        """Validate ``value`` and return ``(value, error_message_or_None)``."""
        if not isinstance(value, (int, float)):
            return (value, 'The Validator IS_GREATER_THAN can only used for int, long or float')
        if value < self.min:
            return (value, self.message)
        return (value, None)


class IS_IN_SET(object):
    """Validate that a value is contained in an allowed set."""

    def __init__(self, seti, message=''):
        """
        :param seti: Allowed values.
        :param message: Optional error message if validation fails.
        """
        self.set = seti
        if message != '':
            self.message = f'Argument must be in Set {self.set}.'
        else:
            self.message = message

    def __call__(self, value):
        """Validate ``value`` and return ``(value, error_message_or_None)``."""
        if not value in self.set:
            return (value, self.message)
        return (value, None)
