import math
import random
import sys
import time
import tkinter as tk
import types

from app import bootstrap as bootstrap_app
from entities.cat import Cat
from entities.charger import Charger
from entities import dirt
from entities.lamp import Lamp
from simulation.astar import AStar
from simulation.counting import Counter
from robot.bot import Bot
from robot.brain import Brain
from simulation import runtime
from simulation.engine import moveIt as _moveIt
from simulation.engine import reset_simulation as _reset_simulation
from simulation.engine import toggle_pause as _toggle_pause
from simulation.factory import (
    add_bot,
    add_cat,
    add_charger,
    add_random_dirt_with_count,
    buttonClicked,
    createObjects,
    remove_bot,
    remove_cat,
    remove_charger,
    remove_dirt,
)
from ui.window import initialise as _initialise


# Runtime state aliases — always delegate to the runtime module directly
# to avoid stale-copy bugs with Python's immutable scalars.
_RUNTIME_ATTRS = frozenset((
    "simulation_running", "simulation_speed", "after_id", "simulation_tick", "generation",
))


def _get_runtime(name):
    return getattr(runtime, name)


def _set_runtime(name, value):
    setattr(runtime, name, value)


# For module-level attribute access (e.g. `main.simulation_running`)
def __getattr__(name):
    if name in _RUNTIME_ATTRS:
        return getattr(runtime, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


# Runtime access architecture:
# - Production: _RuntimeProxyModule intercepts reads/writes for _RUNTIME_ATTRS,
#   delegating them to the runtime module. __getattr__ is a fallback that never
#   fires when the proxy is active.
# - Tests (load_main_module): The proxy is NOT activated because the test module
#   isn't registered in sys.modules. __getattr__ handles reads; direct writes
#   go to __dict__ and are synced via _sync_to_runtime/_sync_from_runtime.


class _RuntimeProxyModule(types.ModuleType):
    def __getattribute__(self, name):
        if name in _RUNTIME_ATTRS:
            return getattr(runtime, name)
        return super().__getattribute__(name)

    def __setattr__(self, name, value):
        if name in _RUNTIME_ATTRS:
            setattr(runtime, name, value)
            return
        super().__setattr__(name, value)


_module = sys.modules.get(__name__)
if _module is not None:
    _module.__class__ = _RuntimeProxyModule


def _sync_to_runtime():
    """Push any values that tests may have written to module globals into runtime."""
    for attr in _RUNTIME_ATTRS:
        val = globals().get(attr)
        if val is not None:
            setattr(runtime, attr, val)


def _sync_from_runtime():
    """Pull runtime values back into module globals for test compatibility."""
    for attr in _RUNTIME_ATTRS:
        globals()[attr] = getattr(runtime, attr)


def initialise(parent):
    return _initialise(parent, tk_module=tk)


def moveIt(*args, **kwargs):
    _sync_to_runtime()
    result = _moveIt(*args, **kwargs)
    _sync_from_runtime()
    return result


def reset_simulation(*args, **kwargs):
    _sync_to_runtime()
    result = _reset_simulation(*args, **kwargs)
    _sync_from_runtime()
    return result


def toggle_pause(*args, **kwargs):
    _sync_to_runtime()
    result = _toggle_pause(*args, **kwargs)
    _sync_from_runtime()
    return result


def run_app(tk_module=None):
    if tk_module is None:
        tk_module = tk
    return bootstrap_app.run_app(tk_module=tk_module)


def main():
    run_app()


if __name__ == "__main__":
    main()
