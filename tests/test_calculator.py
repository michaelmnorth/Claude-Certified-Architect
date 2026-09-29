import pytest
from fastapi.testclient import TestClient

from claculator import app, evaluate

client = TestClient(app)


@pytest.mark.parametrize(
    ("expression", "expected"),
    [
        ("2+3*4", 14),
        ("(2+3)*4", 20),
        ("-5+2", -3),
        ("2**10", 1024),
        ("2**60", 1152921504606846976),
        ("7//2", 3),
        ("-7//2", -4),
        ("(1+2)/4", 0.75),
        ("0.1+0.2", 0.3),
        ("2**-1", 0.5),
    ],
)
def test_arithmetic(expression, expected):
    assert evaluate(expression) == expected


def test_whole_numbers_are_ints():
    assert type(evaluate("2+3*4")) is int
    assert type(evaluate("6/3")) is int


@pytest.mark.parametrize(
    ("expression", "expected"),
    [
        ("50%", 0.5),
        ("200*10%", 20),
        ("12.5%", 0.125),
        ("-50%", -0.5),
    ],
)
def test_percent(expression, expected):
    assert evaluate(expression) == expected


@pytest.mark.parametrize(
    ("expression", "detail"),
    [
        ("1/0", "Cannot divide by zero"),
        ("0/0", "Cannot divide by zero"),
        ("9**9**9", "Result is too large"),
        ("0.001**-999", "Result is too large"),
        ("2+", "Invalid expression"),
        ("10%3", "Invalid expression"),
        ("(-8)**0.5", "Invalid operation"),
        ('__import__("os")', "Only numbers, + - * / // ** ( ) and % (percent) are allowed"),
        ("True+1", "Only numbers, + - * / // ** ( ) and % (percent) are allowed"),
    ],
)
def test_api_rejects_bad_input(expression, detail):
    response = client.post("/api/calc", json={"expression": expression})
    assert response.status_code == 400
    assert response.json() == {"detail": detail}


def test_api_returns_json_result():
    response = client.post("/api/calc", json={"expression": "2+3*4"})
    assert response.status_code == 200
    assert response.json() == {"expression": "2+3*4", "result": 14}


def test_api_rejects_empty_expression():
    response = client.post("/api/calc", json={"expression": ""})
    assert response.status_code == 422


def test_ui_is_served():
    response = client.get("/")
    assert response.status_code == 200
    assert "<title>Calculator</title>" in response.text
