"""Compatibility module alias. Canonical CLI lives in ikant.app_cli."""
import sys as _sys
from . import app_cli as _impl
_sys.modules[__name__] = _impl
