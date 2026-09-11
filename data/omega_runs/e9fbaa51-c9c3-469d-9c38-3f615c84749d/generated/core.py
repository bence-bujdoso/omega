"""Core domain logic."""


def add(a, b):
    return a + b


def subtract(a, b):
    return a - b


class Store:
    """A tiny in-memory item store."""

    def __init__(self):
        self._items = []

    def add(self, item):
        self._items.append(item)
        return item

    def all(self):
        return list(self._items)

    def count(self):
        return len(self._items)
