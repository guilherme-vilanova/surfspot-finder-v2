"""Shared Flask extensions, instantiated once and bound to the app in factory.py."""

from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
