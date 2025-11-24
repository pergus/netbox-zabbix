"""
NetBox Zabbix Plugin — Config Rendering

This module provides custom Django template filters for rendering Python
dicts, lists, and primitive values as HTML tables within templates. It
includes functions to handle nested structures, merge multiple dicts, and
display lists of primitives in a compact, readable table format.

Filters and helpers:
    - render_cell_v1: Renders a single dict or list into a table for a cell.
    - render_cell: Renders dicts, lists of dicts, or primitives compactly.
    - config_to_table: Django template filter to render dicts or lists of
      dicts as full HTML tables, handling nested structures appropriately.

Intended for use in templates where structured configuration or data needs
to be displayed cleanly in tabular form.


"""

# Imports
import json


# Django imports
from django import template
from django.utils.safestring import mark_safe


register = template.Library()


def render_cell_v1(value):
    """
    Render a Python dict or list as an HTML table for display in a single table cell.
    
    Behavior:
        - Dict: rendered as a vertical table (key/value pairs stacked vertically).
        - List of dicts: each dict rendered as its own vertical table.
        - Primitive values: rendered as plain text.
    
    Args:
        value (dict | list | str | any): The object to render. Strings are
            attempted to be parsed as JSON first.
    
    Returns:
        str: Safe HTML string representing the table or value.
    """
    if isinstance( value, str ):
        try:
            value = json.loads( value )
        except json.JSONDecodeError:
            return value

    if isinstance( value, dict ):
        rows = "".join( f"<tr> <td>{key}</td> <td>{value}</td> </tr>" for key, value in value.items() )
        return mark_safe( f"<table class='table table-sm table-borderless mb-0'>{rows}</table>" )

    if isinstance( value, list ):
        tables = []
        for item in value:
            if isinstance( item, dict ):
                tables.append( render_cell( item ) )
            else:
                tables.append( f"<div>{item}</div>" )
        return mark_safe( "".join( tables ) )

    return str( value )


def render_cell(value):
    """
    Render a Python dict or list as a compact HTML table.
    
    Behavior:
        - Single dict: vertical table.
        - List of dicts: merge all dicts into a single vertical table.
        - List of primitives: vertical table of values.
        - Primitive values: rendered as plain text.
    
    Args:
        value (dict | list | str | any): The object to render. Strings are
            attempted to be parsed as JSON first.
    
    Returns:
        str: Safe HTML string representing the table or value.
    """
    if isinstance(value, str):
        try:
            value = json.loads(value)
        except json.JSONDecodeError:
            return value

    # Single dict
    if isinstance(value, dict):
        rows = "".join(f"<tr><td>{k}</td><td>{v}</td></tr>" for k, v in value.items())
        return mark_safe(f"<table class='table table-sm table-borderless mb-0'>{rows}</table>")

    # List
    if isinstance(value, list):
        if not value:
            return ""

        # List of dicts
        if all(isinstance(item, dict) for item in value):
            # Merge all key/value pairs
            merged_items = {}
            for item in value:
                merged_items.update(item)
            rows = "".join(f"<tr><td>{k}</td><td>{v}</td></tr>" for k, v in merged_items.items())
            return mark_safe(f"<table class='table table-sm table-borderless mb-0'>{rows}</table>")

        # List of primitives
        rows = "".join(f"<tr><td>{item}</td></tr>" for item in value)
        return mark_safe(f"<table class='table table-sm table-borderless mb-0'>{rows}</table>")

    # Fallback
    return str(value)


@register.filter(name="config_to_table")
def config_to_table(value):
    """
    Django template filter to render a dict or list of dicts as an HTML table.
    
    Handles nested structures:
        - A single dict is converted to a one-row table.
        - A list of dicts is rendered as a table with a column for each key.
        - Nested dicts or lists inside cells are rendered compactly using `render_cell`.
        - Lists of primitives are displayed as single-column tables.
    
    Args:
        value (dict | list | str | any): The object to render. Strings are
            attempted to be parsed as JSON first.
    
    Returns:
        str: Safe HTML string containing a full table.
    """
    if isinstance( value, str ):
        try:
            value = json.loads( value )
        except json.JSONDecodeError:
            return value

    if isinstance( value, dict ):
        value = [value]

    if not isinstance( value, list ) or not value:
        return "" if value is None else str( value )

    # If it's a list of primitives, display as a simple list
    if not isinstance( value[0], dict ):
        rows = "".join( f"<tr><td>{v}</td></tr>" for v in value )
        return mark_safe( f"<table class='table table-sm table-hover'><tbody>{rows}</tbody></table>" )

    # Collect all keys
    keys = []
    for item in value:
        for key in item.keys():
            if key not in keys:
                keys.append( key )

    header_html = "".join( f"<th>{k}</th>" for k in keys )
    rows_html = ""
    for item in value:
        row_cells = []
        for key in keys:
            cell_value = item.get( key, "" )
            # Render nested dicts or lists compactly
            if isinstance( cell_value, dict ) or isinstance( cell_value, list ):
                cell_value = render_cell( cell_value )
            row_cells.append( f"<td>{cell_value}</td>" )
        rows_html += f"<tr>{''.join( row_cells )}</tr>"

    table_html = f"""
        <table class="table table-sm table-hover">
            <thead><tr>{header_html}</tr></thead>
            <tbody>{rows_html}</tbody>
        </table>
    """
    return mark_safe( table_html )
