import math
import random
import time
import tkinter as tk

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


# Initialize module-level properties that read/write through to runtime.
# This is needed because __getattr__ only fires when the attribute is NOT found
# in the module dict. We use property-like objects via a descriptor isn't possible
# on modules, so we keep _RUNTIME_ATTRS and ensure they are NOT in module globals.
# Tests that do `self.mod.simulation_running = False` will write into the module
# dict, shadowing __getattr__. To support this, moveIt/reset_simulation read from
# both the module dict and runtime.

# We accept that test code may write directly to module attrs. The actual
# simulation code in engine.py/bootstrap.py uses `runtime` directly, which is
# correct. The wrappers below always read from `runtime` before calling.

simulation_running = None  # sentinel; actual access should go through runtime
simulation_speed = None
after_id = None
simulation_tick = None
generation = None


def _sync_to_runtime():
    """Push any values that tests may have written to module globals into runtime."""
    import sys
    mod = sys.modules.get(__name__)
    if mod is None:
        # Loaded dynamically (e.g. test's load_main_module), use caller's globals
        return
    for attr in _RUNTIME_ATTRS:
        val = mod.__dict__.get(attr)
        if val is not None:
            setattr(runtime, attr, val)


def _sync_from_runtime():
    """Pull runtime values back into module globals for test compatibility."""
    import sys
    mod = sys.modules.get(__name__)
    if mod is None:
        return
    for attr in _RUNTIME_ATTRS:
        mod.__dict__[attr] = getattr(runtime, attr)


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
