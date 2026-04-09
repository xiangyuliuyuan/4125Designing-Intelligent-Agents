from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from entities import dirt
from entities.charger import Charger
from entities.lamp import Lamp


@dataclass(frozen=True)
class PassiveObjectIndex:
    passive_objects: list
    size: int
    fingerprint: tuple[int, int, int, int, int]
    debris_objects: tuple[Any, ...]
    lamp_objects: tuple[Lamp, ...]
    charger_objects: tuple[Charger, ...]
    cleanable_dirt_entries: tuple[tuple[int, Any], ...]
    debris_count: int


_cached_index: PassiveObjectIndex | None = None


def _fingerprint(passive_objects):
    size = len(passive_objects)
    if size == 0:
        return (0, 0, 0, 0, 0)
    sample_points = (0, size // 3, (2 * size) // 3, size - 1)
    return (size, *(id(passive_objects[idx]) for idx in sample_points))


def _build_index(passive_objects):
    debris_objects = []
    lamp_objects = []
    charger_objects = []
    cleanable_dirt_entries = []

    for idx, obj in enumerate(passive_objects):
        if hasattr(obj, "type") and obj.type == "debris":
            debris_objects.append(obj)
        if isinstance(obj, Lamp):
            lamp_objects.append(obj)
        if isinstance(obj, Charger):
            charger_objects.append(obj)
        if isinstance(obj, (dirt.plusDirt, dirt.Dirt)):
            cleanable_dirt_entries.append((idx, obj))

    return PassiveObjectIndex(
        passive_objects=passive_objects,
        size=len(passive_objects),
        fingerprint=_fingerprint(passive_objects),
        debris_objects=tuple(debris_objects),
        lamp_objects=tuple(lamp_objects),
        charger_objects=tuple(charger_objects),
        cleanable_dirt_entries=tuple(cleanable_dirt_entries),
        debris_count=len(debris_objects),
    )


def get_passive_object_index(passive_objects):
    global _cached_index
    current_fingerprint = _fingerprint(passive_objects)
    if (
        _cached_index is not None
        and _cached_index.passive_objects is passive_objects
        and _cached_index.fingerprint == current_fingerprint
    ):
        return _cached_index

    _cached_index = _build_index(passive_objects)
    return _cached_index


def invalidate_passive_object_index(passive_objects=None):
    global _cached_index
    if _cached_index is None:
        return
    if passive_objects is None or _cached_index.passive_objects is passive_objects:
        _cached_index = None


def count_debris(passive_objects):
    return get_passive_object_index(passive_objects).debris_count
