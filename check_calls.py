#!/usr/bin/env python3
"""
check_calls.py - Static analysis tool to identify unused Python functions, methods, and properties.

This script parses Python files in a directory (optionally recursively) and reports:
    - Functions and methods that are defined but never called.
    - Properties (via @property) that are defined but never accessed.

Usage:
    python check_calls.py [-r]

Arguments:
    -r, --recursive    Analyze subdirectories recursively.

Output:
    The script prints a Rich table showing all unused functions, methods, and properties along with
    their file paths and line numbers. If all are used at least once, it prints a corresponding message.

Notes:
    - It works on plain Python code and uses the `ast` module to parse the syntax tree.
"""

import ast
from pathlib import Path
import argparse
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich import box
from collections import defaultdict, deque

console = Console()


def get_python_files(base_path: Path, recursive=False):
    return list(base_path.rglob("*.py")) if recursive else list(base_path.glob("*.py"))


def extract_definitions(file_path: Path):
    """Extract function/method and property definitions from a Python file."""
    with open(file_path, "r") as f:
        tree = ast.parse(f.read(), filename=str(file_path))

    funcs = {}
    props = {}

    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef):
            # Check if @property
            if any(isinstance(d, ast.Name) and d.id == "property" or
                   isinstance(d, ast.Attribute) and d.attr == "property"
                   for d in node.decorator_list):
                props[node.name] = node.lineno
            else:
                funcs[node.name] = node.lineno
    return funcs, props


def extract_calls(file_path: Path):
    """Extract function/method calls and property accesses."""
    with open(file_path, "r") as f:
        tree = ast.parse(f.read(), filename=str(file_path))

    calls = set()
    prop_accesses = set()

    class Visitor(ast.NodeVisitor):
        def visit_Call(self, node):
            if isinstance(node.func, ast.Name):
                calls.add(node.func.id)
            elif isinstance(node.func, ast.Attribute):
                calls.add(node.func.attr)
            # arguments passed as functions
            for arg in node.args:
                if isinstance(arg, ast.Name):
                    calls.add(arg.id)
            for kw in node.keywords:
                if isinstance(kw.value, ast.Name):
                    calls.add(kw.value.id)
            self.generic_visit(node)

        def visit_Name(self, node):
            # Mark a function name as used if it's a global function
            calls.add(node.id)
            self.generic_visit(node)

        def visit_Attribute(self, node):
            # property accesses
            prop_accesses.add(node.attr)
            self.generic_visit(node)

    Visitor().visit(tree)
    return calls, prop_accesses



def main():
    parser = argparse.ArgumentParser(description="Check for unused functions/methods and properties.")
    parser.add_argument("-r", "--recursive", action="store_true", help="Check subdirectories recursively")
    args = parser.parse_args()

    base_path = Path(".")
    py_files = get_python_files(base_path, recursive=args.recursive)

    all_funcs = defaultdict(list)
    all_props = defaultdict(list)
    call_graph = defaultdict(set)
    used_props = set()

    # Extract all defs and call graphs
    for f in py_files:
        funcs, props = extract_definitions(f)
        calls, prop_accesses = extract_calls(f)

        for name, lineno in funcs.items():
            all_funcs[name].append((str(f), lineno))
            call_graph[name] = set()

        for name, lineno in props.items():
            all_props[name].append((str(f), lineno))

        # Build call graph
        for name in funcs.keys():
            call_graph[name].update(calls)

        used_props.update(prop_accesses)

    # Flatten all calls in files to detect root calls
    all_calls_flat = set()
    for f in py_files:
        calls, _ = extract_calls(f)
        all_calls_flat.update(calls)

    used_funcs = set()
    queue = deque()

    for func in all_funcs:
        if func in all_calls_flat:
            queue.append(func)
            used_funcs.add(func)

    # Transitive usage
    while queue:
        func = queue.popleft()
        for called in call_graph.get(func, []):
            if called in all_funcs and called not in used_funcs:
                used_funcs.add(called)
                queue.append(called)

    # Determine unused
    unused_funcs = {f: loc for f, loc in all_funcs.items() if f not in used_funcs}
    unused_props = {p: loc for p, loc in all_props.items() if p not in used_props}

    # Display results
    if unused_funcs or unused_props:
        console.print(Panel("Unused Functions/Methods/Properties", expand=False))
        table = Table(show_header=True, header_style="none", box=box.SQUARE)
        table.add_column("Function/Method/Property")
        table.add_column("Location")

        for f, locs in unused_funcs.items():
            for file, lineno in locs:
                table.add_row(f, f"{file}:{lineno}")

        for p, locs in unused_props.items():
            for file, lineno in locs:
                table.add_row(p, f"{file}:{lineno}")

        console.print(table)
    else:
        console.print(Panel("All functions/methods/properties are used at least once", expand=False))


if __name__ == "__main__":
    main()
