#!/usr/bin/env bash
set -euo pipefail

CONFIG="${1:-/opt/atom/llama-swap/config.yaml}"

if [[ ! -f "$CONFIG" ]]; then
  echo "❌ llama-swap config not found: $CONFIG"
  exit 1
fi

echo "Checking llama-swap YAML syntax:"
echo "  $CONFIG"
echo

python3 - "$CONFIG" <<'PY'
import sys
from pathlib import Path

try:
    import yaml
except ImportError:
    print("❌ Missing Python module: yaml")
    print("Install with:")
    print("  sudo apt update && sudo apt install -y python3-yaml")
    sys.exit(2)

path = Path(sys.argv[1])

try:
    with path.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
except yaml.YAMLError as e:
    print("❌ YAML syntax error:")
    print(e)
    sys.exit(1)

if data is None:
    print("❌ YAML file is empty")
    sys.exit(1)

if not isinstance(data, dict):
    print("❌ Top-level YAML structure should be a mapping/object")
    sys.exit(1)

print("✅ YAML syntax OK")
print(f"✅ Top-level keys: {', '.join(map(str, data.keys()))}")
PY

echo
echo "Checking whether llama-swap container can see the config path..."

if docker ps --format '{{.Names}}' | grep -qx 'llama-swap'; then
  echo "✅ llama-swap container is running"
else
  echo "⚠️  llama-swap container is not currently running"
fi

echo
echo "Done."