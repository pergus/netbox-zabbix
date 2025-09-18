from django import template

register = template.Library()

#@register.filter(name="array_to_items")
#def array_to_items(value):
#    if isinstance( value, list ):
#        return " ".join( str( v ) for v in value )
#    return value

from django.utils.safestring import mark_safe

@register.filter(name="array_to_items")
def array_to_items(value):
    """
    Render a list of dicts as an HTML table.
    Handles:
        - JSON list string
        - Python list of dicts
    """
    import json

    # Parse JSON string if needed
    if isinstance(value, str):
        try:
            value = json.loads(value)
        except json.JSONDecodeError:
            return value  # Not JSON, return as-is

    # Ensure we have a list of dicts
    if not isinstance(value, (list, tuple)) or not value:
        return "" if value is None else str(value)

    # If it's a list of primitives, display as a simple list
    if not isinstance(value[0], dict):
        rows = "".join(f"<tr><td>{str(v)}</td></tr>" for v in value)
        return mark_safe(f"<table class='table table-sm table-hover'><tbody>{rows}</tbody></table>")

    # Collect all unique keys across all dicts to build headers
    keys = []
    for item in value:
        if isinstance(item, dict):
            for k in item.keys():
                if k not in keys:
                    keys.append(k)

    # Build header
    header_html = "".join(f"<th>{k}</th>" for k in keys)

    # Build rows
    rows_html = ""
    for item in value:
        row_cells = []
        for k in keys:
            row_cells.append(f"<td>{item.get(k, '')}</td>")
        rows_html += "<tr>" + "".join(row_cells) + "</tr>"

    table_html = f"""
        <table class="table table-sm table-hover">
            <thead><tr>{header_html}</tr></thead>
            <tbody>{rows_html}</tbody>
        </table>
    """
    return mark_safe(table_html)