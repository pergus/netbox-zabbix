from django import template
from django.utils.safestring import mark_safe
import json

register = template.Library()


def render_cell_v1(value):
    """
    Render a dict or list inside a table cell.
    Dicts are rendered vertically for compactness.
    Lists of dicts are rendered as multiple vertical tables.
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
    Render a dict or list inside a table cell.
    - Single dict: vertical table
    - List of dicts: merge all dicts into one vertical table
    - List of primitives: vertical table
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
    Render a list of dicts or a dict as an HTML table with compact nested dicts.
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
