"""Runnable entry point for task-tracker."""

from core import add, subtract, Store


def main():
    store = Store()
    store.add("hello")
    store.add("world")
    print("Project: task-tracker")
    print("2 + 3 =", add(2, 3))
    print("10 - 4 =", subtract(10, 4))
    print("items:", store.all())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
