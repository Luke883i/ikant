"""Compatibility module alias. Canonical host lives in ikant.runtime_host."""
import sys as _sys
from . import runtime_host as _impl
_sys.modules[__name__] = _impl
