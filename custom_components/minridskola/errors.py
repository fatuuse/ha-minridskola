"""Exceptions for Min Ridskola."""
from __future__ import annotations


class MinRidskolaError(Exception):
    """Base error."""


class ConnectError(MinRidskolaError):
    """Site unreachable or returned an unexpected HTTP status."""


class AuthError(MinRidskolaError):
    """Sign-in failed or session expired."""


class ParseError(MinRidskolaError):
    """Page was fetched but expected data was not found.

    Must never be turned into an empty result, as that would remove entities.
    """
