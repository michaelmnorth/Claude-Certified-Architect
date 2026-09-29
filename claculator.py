"""FastAPI calculator: serves the UI from static/ and evaluates expressions at /api/calc."""

import ast
import math
import operator
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

STATIC_DIR = Path(__file__).parent / "static"

BINARY_OPS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
}
UNARY_OPS = {ast.UAdd: operator.pos, ast.USub: operator.neg}
MAX_RESULT_DIGITS = 300  # Rejects powers like 9**9**9 before they are computed.


def evaluate(expression: str) -> float:
    """Safely evaluate an arithmetic expression without using eval()."""
    tree = ast.parse(expression, mode="eval")
    result = _eval_node(tree.body)
    if isinstance(result, float) and not math.isfinite(result):
        raise ValueError("Result is too large")
    return result


def _eval_node(node: ast.AST) -> float:
    if isinstance(node, ast.Constant) and type(node.value) in (int, float):
        return node.value
    if isinstance(node, ast.UnaryOp) and type(node.op) in UNARY_OPS:
        return UNARY_OPS[type(node.op)](_eval_node(node.operand))
    if isinstance(node, ast.BinOp) and type(node.op) in BINARY_OPS:
        left, right = _eval_node(node.left), _eval_node(node.right)
        if isinstance(node.op, ast.Pow) and abs(left) > 1 and right * math.log10(abs(left)) > MAX_RESULT_DIGITS:
            raise ValueError("Result is too large")
        return BINARY_OPS[type(node.op)](left, right)
    raise ValueError("Only numbers and + - * / // % ** ( ) are allowed")


class CalcRequest(BaseModel):
    expression: str = Field(min_length=1, max_length=200)


class CalcResponses(BaseModel):
    """The normalized response returned by the calculator API."""

    expression: str
    result: float

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
    except (ValueError, OverflowError, TypeError) as exc:
        raise HTTPException(status_code=400, detail=str(exc) or "Invalid expression")
    return CalcResponses(expression=request.expression, result=result)


# Mounted last so /api routes take priority; html=True serves index.html at "/".
app.mount("/", StaticFiles(directory=STATIC_DIR, html=True), name="static")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8000)
