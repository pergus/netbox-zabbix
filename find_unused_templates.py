import os
import re

def list_templates(template_dir):
    templates = []
    for root, _, files in os.walk(template_dir):
        for f in files:
            if f.endswith('.html'):
                path = os.path.relpath(os.path.join(root, f), template_dir)
                templates.append(path.replace('\\', '/'))  # Normalize Windows paths
    return sorted(templates)

def find_referenced_templates(code_dir):
    referenced = set()
    pattern = re.compile(r"""['"]([^'"]+\.html)['"]""")
    for root, _, files in os.walk(code_dir):
        for f in files:
            if f.endswith('.py'):
                try:
                    with open(os.path.join(root, f), 'r', encoding='utf-8') as file:
                        content = file.read()
                    for match in pattern.findall(content):
                        referenced.add(match)
                except Exception as e:
                    print(f"Error reading {f}: {e}")
    return sorted(referenced)

def main():
    template_dir = os.path.join('netbox_zabbix', 'templates')
    code_dir = 'netbox_zabbix'

    templates = list_templates(template_dir)
    referenced = find_referenced_templates(code_dir)

    print(f"\nTotal templates found in {template_dir}: {len(templates)}")
    print(f"Total templates referenced in code: {len(referenced)}\n")

    # Templates on disk but not referenced in code
    unused = [t for t in templates if t not in referenced]

    if unused:
        print("Templates NOT referenced in code:")
        for t in unused:
            print("  " + t)
    else:
        print("All templates are referenced in code.")

if __name__ == '__main__':
    main()

