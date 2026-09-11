from core import add, subtract, Store


def test_add():
    assert add(2, 3) == 5


def test_subtract():
    assert subtract(10, 4) == 6


def test_store():
    s = Store()
    s.add('a')
    s.add('b')
    assert s.count() == 2
    assert s.all() == ['a', 'b']
