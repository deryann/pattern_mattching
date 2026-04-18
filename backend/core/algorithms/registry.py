from __future__ import annotations

from .base import AbstractMatcher

_REGISTRY: dict[str, AbstractMatcher] = {}


class AlgorithmNotFoundError(KeyError):
    pass


def register(matcher: AbstractMatcher) -> None:
    if not matcher.id:
        raise ValueError("matcher.id must be non-empty")
    _REGISTRY[matcher.id] = matcher


def get(algorithm_id: str) -> AbstractMatcher:
    if algorithm_id not in _REGISTRY:
        raise AlgorithmNotFoundError(algorithm_id)
    return _REGISTRY[algorithm_id]


def list_all() -> list[AbstractMatcher]:
    return list(_REGISTRY.values())
