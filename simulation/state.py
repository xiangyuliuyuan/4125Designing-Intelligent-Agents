from dataclasses import dataclass, field
from typing import Optional


@dataclass
class SimulationState:
    agents: list = field(default_factory=list)
    passive_objects: list = field(default_factory=list)
    count: Optional[object] = None
    cats: list = field(default_factory=list)
    debris_count: int = 0
    chargers: list = field(default_factory=list)
    astar: Optional[object] = None
    start_time: float = 0.0
    running: bool = True
