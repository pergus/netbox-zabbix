#!/usr/bin/env python3
"""
check_try.py - Static analysis tool to ensure certain functions are always called inside try-except blocks.

Purpose:
    This script scans Python source code to detect calls to specific functions that are not wrapped
    in a try-except block. It helps enforce safe usage of functions that may raise exceptions.

Usage:
    python check_try.py -f <function_def_file(s)> -t <target_file_or_directory(s)>

Arguments:
    -f, --functions-file   One or more Python files that define the functions to check.
    -t, --targets          One or more Python files or directories to scan for function calls.

Behavior:
    - The script extracts function definitions from the provided function files.
    - It scans all target files recursively if directories are given.
    - For each call to a monitored function not inside a try-except block, it reports:
        - Function name
        - File and line number
        - The source code line where the call occurs

Output:
    Uses Rich to display tables with violations for easy readability.
    If no violations are found, nothing is reported for that file.

Notes:
    - Skips the files where functions are defined to avoid false positives.
"""


import ast
import argparse
from pathlib import Path
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich import box

console = Console()

def extract_functions(file_path):
    """Extract top-level function names from a Python file."""
    functions = set()
    with open(file_path, "r") as f:
        tree = ast.parse(f.read(), filename=file_path)
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef):
            functions.add(node.name)
    return functions

def get_python_files(paths):
    """Return a list of Python files from a list of paths (file or directory)."""
    files = []
    for path in paths:
        p = Path(path)
        if p.is_dir():
            files.extend(p.rglob("*.py"))
        elif p.is_file() and p.suffix == ".py":
            files.append(p)
    return files

def find_calls(tree, functions_to_check):
    """Find calls to functions in the tree that are not inside a try-except."""
    violations = []

    class CallVisitor(ast.NodeVisitor):
        def __init__(self):
            self.try_stack = []

        def visit_Try(self, node):
            self.try_stack.append(True)
            for n in node.body:
                self.visit(n)
            self.try_stack.pop()
            for handler in node.handlers:
                for n in handler.body:
                    self.visit(n)
            for n in node.orelse:
                self.visit(n)
            for n in node.finalbody:
                self.visit(n)

        def visit_Call(self, node):
            func_name = ""
            if isinstance(node.func, ast.Name):
                func_name = node.func.id
            elif isinstance(node.func, ast.Attribute):
                func_name = node.func.attr
            if func_name in functions_to_check and not self.try_stack:
                violations.append((func_name, node.lineno, ast.get_source_segment(source_code, node)))
            self.generic_visit(node)

    visitor = CallVisitor()
    visitor.visit(tree)
    return violations

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Check function calls are wrapped in try-except.")
    parser.add_argument("-f", "--functions-file", nargs="+", required=True,
                        help="Python file(s) that define the functions to check")
    parser.add_argument("-t", "--targets", nargs="+", required=True,
                        help="Target file(s) or directories to scan")
    args = parser.parse_args()

    # Extract function names from function-defining files
    functions_to_check = set()
    for func_file in args.functions_file:
        functions_to_check.update(extract_functions(func_file))

    console.print(Panel(f"Functions to check: {', '.join(sorted(functions_to_check))}", title="Function Scanner"))

    target_files = get_python_files(args.targets)
    function_files = [str(Path(f).resolve()) for f in args.functions_file]

    for file_path in target_files:
        file_path_resolved = str(file_path.resolve())
        # Skip function-defining files
        if file_path_resolved in function_files:
            continue
        with open(file_path, "r") as f:
            source_code = f.read()
            filename = f.name

        tree = ast.parse(source_code, filename=str(file_path))
        violations = find_calls(tree, functions_to_check)
        if violations:
            console.print(Panel(f"Violations in {file_path}"))
            table = Table(show_header=True, header_style="none", box=box.SQUARE)
            table.add_column("Function")
            table.add_column("Location")
            table.add_column("Code")
            for func_name, lineno, code in violations:
                table.add_row(func_name, f"{filename}:{str(lineno)}", code.strip() if code else "")
            console.print(table)
