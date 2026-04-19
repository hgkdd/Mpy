import ast
import operator as op
import re


_ALLOWED_BINOPS = {
    ast.Add: op.add,
    ast.Sub: op.sub,
    ast.Mult: op.mul,
    ast.Div: op.truediv,
    ast.FloorDiv: op.floordiv,
    ast.Mod: op.mod,
    ast.Pow: op.pow,
}

_ALLOWED_UNARYOPS = {
    ast.UAdd: op.pos,
    ast.USub: op.neg,
}

_SI_PREFIXES = {
    "T": 1e12,
    "G": 1e9,
    "M": 1e6,
    "k": 1e3,
    "m": 1e-3,
    "u": 1e-6,
    "n": 1e-9,
    "p": 1e-12,
}


def _replace_si_tokens(expr: str) -> str:
    """
    Ersetzt Tokens wie 10M, 2.45G, 100kHz, 3.3V, -20dBm
    durch numerische Werte oder durch die nackte Zahl mit optional
    stehen gelassenem Einheitensuffix.

    Beispiele:
        10M     -> 10000000.0
        2.45GHz -> 2450000000.0
        3.3V    -> 3.3
        -20dBm  -> -20
    """

    number_re = re.compile(
        r"""
        (?P<prefix_boundary>^|(?<=[\s\(\)\+\-\*/%,]))
        (?P<number>
            [+-]?
            (?:
                (?:\d+(?:\.\d*)?) |
                (?:\.\d+)
            )
            (?:[eE][+-]?\d+)?
        )
        (?P<prefix>[TGMkmunp]?)
        (?P<unit>[A-Za-z][A-Za-z0-9/_-]*)?
        (?P<suffix_boundary>$|(?=[\s\(\)\+\-\*/%,]))
        """,
        re.VERBOSE,
    )

    def repl(match: re.Match) -> str:
        left = match.group("prefix_boundary")
        number = match.group("number")
        prefix = match.group("prefix") or ""
        unit = match.group("unit") or ""
        right = match.group("suffix_boundary")

        value = float(number)

        if prefix:
            value *= _SI_PREFIXES[prefix]

        # Einheit wird hier bewusst ignoriert.
        # Beispiele:
        #   3.3V   -> 3.3
        #   2.45GHz -> 2.45e9
        #   -20dBm -> -20
        #
        # Für "Freq / Hz" ist das meist genau richtig.
        return f"{left}{value}{right}"

    return number_re.sub(repl, expr)


def safe_numeric_eval(expr: str) -> float:
    """
    Sichere Auswertung einfacher numerischer Ausdrücke mit SI-Präfixen.

    Erlaubt:
        1e9
        1e9/4
        10M
        2.45G
        100kHz
        3.3V
        -20dBm
        (2.45G + 100M) / 2

    Nicht erlaubt:
        abs(1)
        x + 1
        __import__('os').system(...)
        self.x
    """
    if not isinstance(expr, str):
        raise TypeError("expr must be a string")

    expr = expr.strip()
    if not expr:
        raise ValueError("empty expression")

    normalized = _replace_si_tokens(expr)
    tree = ast.parse(normalized, mode="eval")

    def _eval(node):
        if isinstance(node, ast.Expression):
            return _eval(node.body)

        if isinstance(node, ast.Constant):
            if isinstance(node.value, (int, float)):
                return node.value
            raise ValueError("Only numeric constants are allowed")

        if isinstance(node, ast.Num):
            return node.n

        if isinstance(node, ast.BinOp):
            fn = _ALLOWED_BINOPS.get(type(node.op))
            if fn is None:
                raise ValueError("Operator not allowed")
            return fn(_eval(node.left), _eval(node.right))

        if isinstance(node, ast.UnaryOp):
            fn = _ALLOWED_UNARYOPS.get(type(node.op))
            if fn is None:
                raise ValueError("Unary operator not allowed")
            return fn(_eval(node.operand))

        raise ValueError(f"Expression element not allowed: {type(node).__name__}")

    return float(_eval(tree))


if __name__ == "__main__":
    tests = [
        "1e9",
        "1e9/4",
        "10M",
        "2.45G",
        "100k",
        "3m",
        "3.3V",
        "2.45GHz",
        "100 kHz",
        "-20dBm",
        "(2.45G + 100M) / 2",
    ]

    for s in tests:
        try:
            print(f"{s!r:>20} -> {safe_numeric_eval(s)}")
        except Exception as e:
            print(f"{s!r:>20} -> ERROR: {e}")