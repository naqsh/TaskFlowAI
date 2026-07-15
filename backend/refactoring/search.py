"""Code search for symbols and call sites (ADR-004 Search stage)."""

from __future__ import annotations

import ast
from dataclasses import dataclass
from pathlib import Path

from backend.refactoring.sandbox import RefactoringSandbox


@dataclass(frozen=True, slots=True)
class SymbolHit:
    file_path: str
    line: int
    col: int
    kind: str  # definition | call | name
    symbol: str
    snippet: str


def _snippet(source: str, lineno: int) -> str:
    lines = source.splitlines()
    if 1 <= lineno <= len(lines):
        return lines[lineno - 1].strip()
    return ""


class CodeSearchService:
    """AST-backed symbol and call-site discovery within the sandbox."""

    def __init__(self, sandbox: RefactoringSandbox) -> None:
        self._sandbox = sandbox

    def find_symbol(self, symbol: str) -> list[SymbolHit]:
        hits: list[SymbolHit] = []
        for path in self._sandbox.iter_python_files():
            hits.extend(self._scan_file(path, symbol))
        return hits

    def _scan_file(self, path: Path, symbol: str) -> list[SymbolHit]:
        try:
            source = path.read_text(encoding="utf-8")
        except OSError:
            return []
        try:
            tree = ast.parse(source, filename=str(path))
        except SyntaxError:
            return []

        rel = self._sandbox.relative_to_root(path)
        hits: list[SymbolHit] = []

        class Visitor(ast.NodeVisitor):
            def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
                if node.name == symbol:
                    hits.append(
                        SymbolHit(
                            file_path=rel,
                            line=node.lineno,
                            col=node.col_offset,
                            kind="definition",
                            symbol=symbol,
                            snippet=_snippet(source, node.lineno),
                        )
                    )
                self.generic_visit(node)

            def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
                if node.name == symbol:
                    hits.append(
                        SymbolHit(
                            file_path=rel,
                            line=node.lineno,
                            col=node.col_offset,
                            kind="definition",
                            symbol=symbol,
                            snippet=_snippet(source, node.lineno),
                        )
                    )
                self.generic_visit(node)

            def visit_ClassDef(self, node: ast.ClassDef) -> None:
                if node.name == symbol:
                    hits.append(
                        SymbolHit(
                            file_path=rel,
                            line=node.lineno,
                            col=node.col_offset,
                            kind="definition",
                            symbol=symbol,
                            snippet=_snippet(source, node.lineno),
                        )
                    )
                self.generic_visit(node)

            def visit_Name(self, node: ast.Name) -> None:
                if node.id == symbol:
                    hits.append(
                        SymbolHit(
                            file_path=rel,
                            line=node.lineno,
                            col=node.col_offset,
                            kind="name",
                            symbol=symbol,
                            snippet=_snippet(source, node.lineno),
                        )
                    )
                self.generic_visit(node)

            def visit_Call(self, node: ast.Call) -> None:
                func = node.func
                if isinstance(func, ast.Name) and func.id == symbol:
                    hits.append(
                        SymbolHit(
                            file_path=rel,
                            line=node.lineno,
                            col=node.col_offset,
                            kind="call",
                            symbol=symbol,
                            snippet=_snippet(source, node.lineno),
                        )
                    )
                elif isinstance(func, ast.Attribute) and func.attr == symbol:
                    hits.append(
                        SymbolHit(
                            file_path=rel,
                            line=node.lineno,
                            col=node.col_offset,
                            kind="call",
                            symbol=symbol,
                            snippet=_snippet(source, node.lineno),
                        )
                    )
                self.generic_visit(node)

        Visitor().visit(tree)
        return hits
