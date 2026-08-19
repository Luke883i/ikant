"""Compatibility module alias. Canonical human dashboard lives in ikant.human_dashboard."""
import sys as _sys
from . import human_dashboard as _impl
_sys.modules[__name__] = _impl
