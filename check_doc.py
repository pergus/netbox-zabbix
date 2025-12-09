#!/usr/bin/env python3
"""
check_doc.py - Static analysis tool to find Python classes, functions, and methods without docstrings.

This script parses Python files in a directory (optionally recursively) and reports:
    - Classes without docstrings.
    - Functions without docstrings.
    - Methods inside classes without docstrings.

Usage:
    python check_doc.py [filename] [-r]

Arguments:
    filename            Optional: check a single Python file (without .py extension)
    -r, --recursive     Recursively check all subdirectories for Python files

Output:
    The script prints a Rich table showing all undocumented classes, functions, and methods,
    including their file paths and line numbers. If everything has a docstring, it prints a
    confirmation message.
"""

import ast
from pathlib import Path
import argparse
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich import box

console = Console()


def get_python_files(base_path: Path, recursive=False):
    """Return a list of Python files to check."""
    if recursive:
        return list(base_path.rglob("*.py"))
    else:
        return list(base_path.glob("*.py"))


def extract_undocumented(file_path: Path):
    """Return list of (type, name, lineno) for classes/functions without docstrings."""
    undocumented = []

    with open(file_path, "r") as f:
        tree = ast.parse(f.read(), filename=str(file_path))

    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if ast.get_docstring(node) is None:
                undocumented.append(("Function", node.name, node.lineno))
        elif isinstance(node, ast.ClassDef):
            if ast.get_docstring(node) is None:
                undocumented.append(("Class", node.name, node.lineno))
            # Also check methods inside the class
            for child in node.body:
                if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    if ast.get_docstring(child) is None:
                        undocumented.append(("Method", f"{node.name}.{child.name}", child.lineno))

    return undocumented


def main():
    parser = argparse.ArgumentParser(
        description="Check for undocumented classes/functions/methods."
    )
    parser.add_argument(
        "filename",
        nargs="?",
        help="Optional: specify a single Python file (without .py extension) to check.",
    )
    parser.add_argument(
        "-r", "--recursive", action="store_true", help="Check subdirectories recursively"
    )
    args = parser.parse_args()

    base_path = Path(".")
    all_undocumented = []

    # Determine which files to check
    if args.filename:
        target_file = base_path / f"{args.filename}.py"
        if not target_file.exists():
            console.print(f"[red]Error:[/red] File '{target_file}' not found.")
            return
        py_files = [target_file]
    else:
        py_files = get_python_files(base_path, recursive=args.recursive)

    # Extract undocumented items
    for f in py_files:
        undocumented = extract_undocumented(f)
        for kind, name, lineno in undocumented:
            all_undocumented.append((kind, name, str(f), lineno))

    # Display results
    if all_undocumented:
        console.print(Panel("Undocumented Classes/Functions/Methods", expand=False))
        table = Table(show_header=True, header_style="none", box=box.SQUARE)
        table.add_column("Type")
        table.add_column("Name")
        table.add_column("Location")
        for kind, name, file, lineno in all_undocumented:
            clickable_location = f"{file}:{lineno}"
            table.add_row(kind, name, clickable_location)
        console.print(table)
    else:
        console.print(Panel("All classes/functions/methods have docstrings", expand=False))


if __name__ == "__main__":
    main()
