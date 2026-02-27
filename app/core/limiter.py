"""
Shared rate limiter instance.

Imported by endpoint modules so they can apply @limiter.limit() decorators.
The limiter is attached to app.state in main.py.
"""

from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
