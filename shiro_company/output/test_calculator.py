import pytest
from calculator import Calculator

def test_addition():
    calc = Calculator()
    assert calc.calculate("2 + 3") == 5
    assert calc.calculate("10 + 0") == 10

def test_subtraction():
    calc = Calculator()
    assert calc.calculate("5 - 3") == 2
    assert calc.calculate("0 - 5") == -5

def test_multiplication():
    calc = Calculator()
    assert calc.calculate("4 * 3") == 12
    assert calc.calculate("7 * 0") == 0

def test_division():
    calc = Calculator()
    assert calc.calculate("10 / 2") == 5
    assert calc.calculate("15 / 3") == 5

def test_division_by_zero():
    calc = Calculator()
    with pytest.raises(ValueError):
        calc.calculate("5 / 0")

def test_float_operations():
    calc = Calculator()
    assert calc.calculate("3.5 + 2.5") == 6.0
    assert calc.calculate("10.5 / 3") == 3.5

def test_negative_numbers():
    calc = Calculator()
    assert calc.calculate("-5 + 3") == -2
    assert calc.calculate("10 + -3") == 7

def test_invalid_expression():
    calc = Calculator()
    with pytest.raises(ValueError):
        calc.calculate("invalid")