# -*- coding: utf-8 -*-
"""Compatibility shim for test runners importing src.pas.*.

Some CI runners resolve tests as modules under ``src`` (e.g. ``src.pas...``)
while editable installs expose only the real package root. Extend this package
path so ``src.pas`` maps to the actual ``pas`` package.
"""

from __future__ import annotations

import os
from pkgutil import extend_path

__path__ = extend_path(__path__, __name__)

_here = os.path.abspath(os.path.dirname(__file__))
_src_root = os.path.abspath(os.path.join(_here, os.pardir))
if _src_root not in __path__:
    __path__.append(_src_root)
