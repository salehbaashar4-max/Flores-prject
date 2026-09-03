import re

path = 'c:/Users/DELL/Desktop/Flores prject/backend/app/services/geodata_service.py'
with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

def replacer(match):
    full = match.group(1)
    if ' - ' in full:
        id_name, ar_name = full.split(' - ', 1)
        return f'"name_id": "{id_name.strip()}",\n                "name_ar": "{ar_name.strip()}",'
    return match.group(0)

new_content = re.sub(r'"name":\s*"([^"]+)",', replacer, content)

with open(path, 'w', encoding='utf-8') as f:
    f.write(new_content)
