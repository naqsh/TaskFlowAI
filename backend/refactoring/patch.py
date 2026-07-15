"""Deterministic AST patching for structural refactors (ADR-004)."""

from __future__ import annotations

import ast
from dataclasses import dataclass

from backend.refactoring.sandbox import RefactoringSandbox, SandboxError


@dataclass(frozen=True, slots=True)
class RenameRequest:
    old_name: str
    new_name: str
    file_path: str


class _RenameTransformer(ast.NodeTransformer):
    def __init__(self, old_name: str, new_name: str) -> None:
        self.old_name = old_name
        self.new_name = new_name
        self.changed = False

    def visit_Name(self, node: ast.Name) -> ast.Name:
        if node.id == self.old_name:
            self.changed = True
            return ast.copy_location(ast.Name(id=self.new_name, ctx=node.ctx), node)
        return node

    def visit_FunctionDef(self, node: ast.FunctionDef) -> ast.AST:
        self.generic_visit(node)
        if node.name == self.old_name:
            self.changed = True
            node.name = self.new_name
        return node

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> ast.AST:
        self.generic_visit(node)
        if node.name == self.old_name:
            self.changed = True
            node.name = self.new_name
        return node

    def visit_ClassDef(self, node: ast.ClassDef) -> ast.AST:
        self.generic_visit(node)
        if node.name == self.old_name:
            self.changed = True
            node.name = self.new_name
        return node

    def visit_Attribute(self, node: ast.Attribute) -> ast.AST:
        self.generic_visit(node)
        if node.attr == self.old_name:
            self.changed = True
            return ast.copy_location(
                ast.Attribute(value=node.value, attr=self.new_name, ctx=node.ctx),
                node,
            )
        return node


class DeterministicPatchService:
    """Apply mechanical transforms via AST (prefer over LLM text guessing)."""

    def __init__(self, sandbox: RefactoringSandbox) -> None:
        self._sandbox = sandbox

    def rename_symbol(self, request: RenameRequest) -> bool:
        path = self._sandbox.resolve(request.file_path)
        if not path.is_file():
            msg = f"Cannot patch missing file: {request.file_path}"
            raise SandboxError(msg)
        if not request.new_name.isidentifier():
            msg = f"Invalid new symbol name: {request.new_name}"
            raise SandboxError(msg)

        source = path.read_text(encoding="utf-8")
        try:
            tree = ast.parse(source, filename=str(path))
        except SyntaxError as exc:
            msg = f"Cannot parse {request.file_path}: {exc}"
            raise SandboxError(msg) from exc

        transformer = _RenameTransformer(request.old_name, request.new_name)
        new_tree = transformer.visit(tree)
        if not transformer.changed:
            return False
        ast.fix_missing_locations(new_tree)
        rewritten = ast.unparse(new_tree) + "\n"
        ast.parse(rewritten, filename=str(path))
        path.write_text(rewritten, encoding="utf-8")
        return True
