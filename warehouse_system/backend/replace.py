import os
import glob

def replace_in_file(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    original = content
    # Special handling depending on file
    if filepath.endswith('seed_shipments.py') or filepath.endswith('inbound.py') or filepath.endswith('outbound.py'):
        if 'from app.core.config import settings' not in content:
            content = content.replace('import', 'from app.core.config import settings\nimport', 1)
        content = content.replace('WAREHOUSE_ID = "WH-001"', 'WAREHOUSE_ID = settings.WAREHOUSE_ID')
    elif filepath.endswith('seed.py'):
        if 'from app.core.config import settings' not in content:
            content = content.replace('import json', 'import json\nfrom app.core.config import settings')
        content = content.replace('"WH-001"', 'settings.WAREHOUSE_ID')
    elif filepath.endswith('head_office_sync.py'):
        content = content.replace('warehouse_id: str = "WH-001"', 'warehouse_id: str = settings.WAREHOUSE_ID')
    elif filepath.endswith('notification_service.py'):
        if 'from app.core.config import settings' not in content:
            content = content.replace('import logging', 'import logging\nfrom app.core.config import settings')
        content = content.replace('"WH-001"', 'settings.WAREHOUSE_ID')
    elif filepath.endswith('main.py'):
        content = content.replace('"WH-001"', 'settings.WAREHOUSE_ID')
    elif filepath.endswith('head_office.py'):
        if 'from app.core.config import settings' not in content:
            content = content.replace('from fastapi', 'from app.core.config import settings\nfrom fastapi')
        content = content.replace('"WH-001"', 'settings.WAREHOUSE_ID')
    elif filepath.endswith('intelligence.py'):
        if 'from app.core.config import settings' not in content:
            content = content.replace('from fastapi', 'from app.core.config import settings\nfrom fastapi')
        content = content.replace('"WH-001"', 'settings.WAREHOUSE_ID')
        
    if content != original:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)

for root, _, files in os.walk('backend'):
    for file in files:
        if file.endswith('.py'):
            replace_in_file(os.path.join(root, file))

print("Replacements done")
