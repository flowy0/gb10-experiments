#!/usr/bin/env bash
set -uo pipefail

CONFIG="${1:-/opt/atom/llama-swap/config.yaml}"

if [[ ! -f "$CONFIG" ]]; then
  echo "❌ llama-swap config not found: $CONFIG"
  exit 1
fi

echo "Checking llama-swap YAML:"
echo "  $CONFIG"
echo

python3 - "$CONFIG" <<'PY'
import sys
from pathlib import Path

try:
    import yaml
except ImportError:
    print("❌ Missing Python module: yaml")
    print("Install with: sudo apt update && sudo apt install -y python3-yaml")
    sys.exit(2)

path = Path(sys.argv[1])
errors = []

try:
    with path.open("r", encoding="utf-8") as f:
        raw = f.read()
    data = yaml.safe_load(raw)
except yaml.YAMLError as e:
    print(f"❌ YAML syntax error:\n{e}")
    sys.exit(1)

if data is None:
    print("❌ YAML file is empty")
    sys.exit(1)

if not isinstance(data, dict):
    print("❌ Top-level YAML should be a mapping")
    sys.exit(1)

print(f"✅ YAML syntax OK")
print(f"✅ Top-level keys: {', '.join(map(str, data.keys()))}")
print()

# Check top-level keys
if 'models' not in data:
    errors.append("Missing 'models' section")
if 'groups' not in data:
    errors.append("Missing 'groups' section (as top-level key)")

# Check groups: line is at column 0 (not indented)
for i, line in enumerate(raw.split('\n'), 1):
    stripped = line.strip()
    if stripped == 'groups:' and line.startswith(' '):
        errors.append(f"Line {i}: 'groups:' is indented — must be at column 0")
        break

if 'groups' in data and isinstance(data['groups'], dict):
    for group_name, group_data in data['groups'].items():
        if not isinstance(group_data, dict):
            errors.append(f"Group '{group_name}': not a mapping")
            continue
        members = group_data.get('members', [])
        if not members:
            errors.append(f"Group '{group_name}': no active members")
        for member in members:
            if member not in data.get('models', {}):
                errors.append(f"Group '{group_name}': model '{member}' not defined in 'models' section")

# Check for duplicate model keys in raw file
seen_models = set()
if 'models' in data:
    for model_name in data['models']:
        if model_name in seen_models:
            errors.append(f"Duplicate model key: '{model_name}'")
        seen_models.add(model_name)

# Check for models with --np flag (may conflict with --parallel)
if 'models' in data:
    for model_name, model_data in data['models'].items():
        cmd = model_data.get('cmd', '')
        if '--np ' in cmd:
            errors.append(f"Model '{model_name}': uses --np (double dash) — should be -np (single dash) or --parallel")

if errors:
    print(f"❌ {len(errors)} issue(s) found:")
    for e in errors:
        print(f"  • {e}")
    sys.exit(1)
else:
    print("✅ No issues found — config looks valid")
PY

echo
echo "Checking container..."

if docker ps --format '{{.Names}}' 2>/dev/null | grep -qx 'llama-swap'; then
  echo "✅ llama-swap container is running"
else
  echo "⚠️  llama-swap container is not running"
fi

echo
echo "Done."
