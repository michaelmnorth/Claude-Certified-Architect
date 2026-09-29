"""FastAPI calculator: serves the UI from static/ and evaluates expressions at /api/calc."""

import ast
import math
import operator
import re
from decimal import ROUND_FLOOR, Decimal, localcontext
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

STATIC_DIR = Path(__file__).parent / "static"


def _divide(a: Decimal, b: Decimal) -> Decimal:
    # Decimal reports 0/0 as InvalidOperation, so check for zero explicitly.
    if b == 0:
        raise ZeroDivisionError
    return a / b


BINARY_OPS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: _divide,
    # Decimal's // truncates toward zero; floor it to match Python's int behaviour.
    ast.FloorDiv: lambda a, b: _divide(a, b).to_integral_value(rounding=ROUND_FLOOR),
    ast.Pow: operator.pow,
}
UNARY_OPS = {ast.UAdd: operator.pos, ast.USub: operator.neg}
MAX_RESULT_DIGITS = 300  # Rejects powers like 9**9**9 before they are computed.
PERCENT = re.compile(r"(\d+\.?\d*|\.\d+)%")  # "50%" -> "(50/100)"


def evaluate(expression: str) -> int | float:
    """Safely evaluate an arithmetic expression without using eval().

    Numbers are computed as Decimals, so 0.1+0.2 is exactly 0.3 and whole-number
    results come back as exact ints.
    """
    tree = ast.parse(PERCENT.sub(r"(\1/100)", expression), mode="eval")
    with localcontext(prec=MAX_RESULT_DIGITS + 20):
        result = _eval_node(tree.body)
    if not result.is_finite():
        raise ValueError("Result is too large")
    if result == result.to_integral_value():
        return int(result)
    return float(result)


def _eval_node(node: ast.AST) -> Decimal:
    if isinstance(node, ast.Constant) and type(node.value) in (int, float):
        return Decimal(repr(node.value))
    if isinstance(node, ast.UnaryOp) and type(node.op) in UNARY_OPS:
        return UNARY_OPS[type(node.op)](_eval_node(node.operand))
    if isinstance(node, ast.BinOp) and type(node.op) in BINARY_OPS:
        left, right = _eval_node(node.left), _eval_node(node.right)
        if isinstance(node.op, ast.Pow) and left != 0:
            if abs(float(right) * math.log10(abs(left))) > MAX_RESULT_DIGITS:
                raise ValueError("Result is too large")
        return BINARY_OPS[type(node.op)](left, right)
    raise ValueError("Only numbers, + - * / // ** ( ) and % (percent) are allowed")


class CalcRequest(BaseModel):
    expression: str = Field(min_length=1, max_length=200)


class CalcResponses(BaseModel):
    """The normalized response returned by the calculator API."""

    expression: str
    result: int | float

    def __str__(self) -> str:
        """Return a concise, human-readable representation of the result."""
        return f"{self.expression} = {self.result}"


app = FastAPI(title="Calculator")


@app.post("/api/calc")
def calc(request: CalcRequest) -> CalcResponses:
    try:
        result = evaluate(request.expression)
    except ZeroDivisionError:
        raise HTTPException(status_code=400, detail="Cannot divide by zero")
    except SyntaxError:
        raise HTTPException(status_code=400, detail="Invalid expression")
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc) or "Invalid expression")
    except (ArithmeticError, TypeError):
        # e.g. (-8)**0.5, which has no real-number answer.
        raise HTTPException(status_code=400, detail="Invalid operation")
    return CalcResponses(expression=request.expression, result=result)


# Mounted last so /api routes take priority; html=True serves index.html at "/".
app.mount("/", StaticFiles(directory=STATIC_DIR, html=True), name="static")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8000)
