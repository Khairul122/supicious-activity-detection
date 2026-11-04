"""Uji aturan multitier: lapisan atas boleh memanggil lapisan tepat di bawahnya saja.

presentation -> business -> data. Tidak boleh ada impor ke arah sebaliknya, dan
presentation tidak boleh melompati business untuk mengakses data secara langsung.
Jalankan: python -m unittest discover -s web/tests
"""
import ast
import unittest
from pathlib import Path

APP = Path(__file__).resolve().parents[1] / "app"
FORBIDDEN = {
    "presentation": ("data",),
    "business": ("presentation",),
    "data": ("business", "presentation"),
}


def imported_layers(path):
    tree = ast.parse(path.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module:
            parts = node.module.split(".")
            yield from (p for p in parts if p in FORBIDDEN)
        elif isinstance(node, ast.Import):
            for alias in node.names:
                yield from (p for p in alias.name.split(".") if p in FORBIDDEN)


class MultitierTest(unittest.TestCase):
    def test_layer_dependencies(self):
        violations = []
        for layer, forbidden in FORBIDDEN.items():
            for path in (APP / layer).rglob("*.py"):
                for used in imported_layers(path):
                    if used in forbidden:
                        violations.append(f"{path.relative_to(APP)} mengimpor lapisan {used}")
        self.assertEqual(violations, [])

    def test_sql_only_in_data_layer(self):
        offenders = []
        for layer in ("presentation", "business"):
            for path in (APP / layer).rglob("*.py"):
                text = path.read_text(encoding="utf-8")
                if any(k in text for k in ("sqlite3", "pymysql", "SELECT ", "INSERT ", "UPDATE sesi", "CREATE TABLE")):
                    offenders.append(str(path.relative_to(APP)))
        self.assertEqual(offenders, [])


if __name__ == "__main__":
    unittest.main()
