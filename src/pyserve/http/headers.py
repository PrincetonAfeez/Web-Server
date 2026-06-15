""" Headers module for the pyserve project """

from __future__ import annotations

from collections.abc import Iterable, Iterator


class CaseInsensitiveHeaders:
    def __init__(self, items: Iterable[tuple[str, str]] | None = None) -> None:
        self._items: list[tuple[str, str]] = []
        self._index: dict[str, list[int]] = {}
        for name, value in items or ():
            self.add(name, value)

    @staticmethod
    def normalize(name: str) -> str:
        return name.lower()

    def add(self, name: str, value: str) -> None:
        normalized = self.normalize(name)
        self._index.setdefault(normalized, []).append(len(self._items))
        self._items.append((name, value))

    def get(self, name: str, default: str | None = None) -> str | None:
        indexes = self._index.get(self.normalize(name))
        if not indexes:
            return default
        return self._items[indexes[-1]][1]

    def get_all(self, name: str) -> list[str]:
        return [self._items[index][1] for index in self._index.get(self.normalize(name), [])]

    def raw_items(self) -> list[tuple[str, str]]:
        return list(self._items)

    def items(self) -> Iterator[tuple[str, str]]:
        return iter(self._items)

    def __contains__(self, name: object) -> bool:
        return isinstance(name, str) and self.normalize(name) in self._index

    def __getitem__(self, name: str) -> str:
        value = self.get(name)
        if value is None:
            raise KeyError(name)
        return value

    def __iter__(self) -> Iterator[tuple[str, str]]:
        return self.items()

    def __len__(self) -> int:
        return len(self._items)

    def __repr__(self) -> str:
        return f"{type(self).__name__}({self._items!r})"
