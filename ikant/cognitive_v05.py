"""Compatibility module alias. Canonical cognitive compiler lives in ikant.cognitive_runtime."""
import sys as _sys
from . import cognitive_runtime as _impl
_sys.modules[__name__] = _impl
