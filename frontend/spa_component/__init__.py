"""Streamlit custom component that hosts the built React SPA."""
from pathlib import Path

import streamlit.components.v1 as components

_BUILD = Path(__file__).resolve().parent / "build"
_component = components.declare_component("nightwatch_spa", path=str(_BUILD))


def nightwatch_spa(response=None, key="nightwatch_spa"):
    """Render the SPA. ``response`` is the answer to the JS bridge's last request."""
    return _component(response=response, key=key, default=None)
