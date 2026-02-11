#!/bin/bash
set -euo pipefail

# --- Pick python interpreter
# Contract:
#   - If WARMPY_PYTHON is set -> must be absolute path to executable
#   - Else -> use python3 from PATH
#   - No other fallbacks

if [[ -n "${WARMPY_PYTHON:-}" ]]; then
  if [[ "$WARMPY_PYTHON" != /* ]]; then
    echo "WARMPY_PYTHON must be an absolute path" >&2
    exit 1
  fi
  if [[ ! -x "$WARMPY_PYTHON" ]]; then
    echo "WARMPY_PYTHON not executable: $WARMPY_PYTHON" >&2
    exit 1
  fi
  PYTHON="$WARMPY_PYTHON"
else
  if ! command -v python3 >/dev/null 2>&1; then
    echo "python3 not found in PATH" >&2
    exit 1
  fi
  PYTHON="$(command -v python3)"
fi

BUILD_DIR=".build"
VENV_DIR="$BUILD_DIR/venv"
MERGED_JSON="$BUILD_DIR/warmpy_build_deps.json"

PLUGINS_DIR=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --plugins-dir)
      PLUGINS_DIR="${2:-}"
      shift 2
      ;;
    -h|--help)
      echo "Usage: ./build.sh --plugins-dir <path>"
      exit 0
      ;;
    *)
      echo "Unknown argument: $1" >&2
      exit 1
      ;;
  esac
done

if [[ -z "$PLUGINS_DIR" ]]; then
  echo "ERROR: --plugins-dir is required" >&2
  exit 1
fi

PLUGINS_DIR="$("$PYTHON" -c 'import os,sys; print(os.path.abspath(os.path.expanduser(sys.argv[1])))' "$PLUGINS_DIR")"

echo "Using python interpreter:"
"$PYTHON" -V
echo "Path:"
echo "$PYTHON"
echo "Plugins dir: $PLUGINS_DIR"

mkdir -p "$BUILD_DIR"
rm -rf "$BUILD_DIR/build" "$BUILD_DIR/dist" "$MERGED_JSON" "$VENV_DIR"

"$PYTHON" -m venv "$VENV_DIR"
# shellcheck disable=SC1090
source "$VENV_DIR/bin/activate"

# ---- Infra deps (hardcoded, project-owned) ----
python -m pip install -U pip wheel
python -m pip install "setuptools<70"
python -m pip install pyobjc pyyaml py2app

# ---- Plugin build deps contract (no heuristics) ----
# Scan PLUGINS_DIR for all files whose names end with 'warmpy_build_deps.yaml', merge:
#   pip:    list[str]  -> installed via pip at build time
#   import: list[str]  -> python module names to force-include in py2app

python - <<'PYSCRIPT' "$PLUGINS_DIR" "$MERGED_JSON"
import json, sys
from pathlib import Path
import yaml

plugins_dir = Path(sys.argv[1])
out_json = Path(sys.argv[2])

pip_list, imp_list = [], []
pip_seen, imp_seen = set(), set()

paths = sorted([p for p in plugins_dir.rglob('*warmpy_build_deps.yaml') if p.name.endswith('warmpy_build_deps.yaml')])

for p in paths:
    data = yaml.safe_load(p.read_text('utf-8')) or {}
    pip_items = data.get('pip') or []
    imp_items = data.get('import') or []

    if not isinstance(pip_items, list):
        raise SystemExit(f"{p}: field 'pip' must be a list")
    if not isinstance(imp_items, list):
        raise SystemExit(f"{p}: field 'import' must be a list")

    for item in pip_items:
        if not isinstance(item, str):
            raise SystemExit(f"{p}: 'pip' items must be strings")
        item = item.strip()
        if item and item not in pip_seen:
            pip_seen.add(item)
            pip_list.append(item)

    for item in imp_items:
        if not isinstance(item, str):
            raise SystemExit(f"{p}: 'import' items must be strings")
        item = item.strip()
        if item and item not in imp_seen:
            imp_seen.add(item)
            imp_list.append(item)

out_json.parent.mkdir(parents=True, exist_ok=True)
out_json.write_text(json.dumps({'pip': pip_list, 'import': imp_list}, indent=2) + "\n", 'utf-8')

print(f"Merged warmpy_build_deps files: {len(paths)}")
print(f"Wrote: {out_json}")
print(f"pip deps: {len(pip_list)}; import deps: {len(imp_list)}")
PYSCRIPT

python - <<'PYSCRIPT' "$MERGED_JSON"
import json, sys, subprocess
from pathlib import Path

p = Path(sys.argv[1])
data = json.loads(p.read_text('utf-8')) if p.exists() else {'pip': []}
deps = data.get('pip') or []

if deps:
    subprocess.check_call([sys.executable, '-m', 'pip', 'install', *deps])
else:
    print('No plugin pip deps to install')
PYSCRIPT

# ---- Write runtime config (only plugins_dir) ----
python - <<'PYSCRIPT' "$PLUGINS_DIR"
from pathlib import Path
import yaml
import sys

plugins_dir = sys.argv[1]
cfg_dir = Path.home() / '.warmpy'
cfg_dir.mkdir(parents=True, exist_ok=True)
try:
    cfg_dir.chmod(0o700)
except Exception:
    pass

cfg_file = cfg_dir / 'config.yaml'
cfg = {'plugins_dir': plugins_dir}
cfg_file.write_text(yaml.safe_dump(cfg), encoding='utf-8')
print('Wrote', cfg_file)
PYSCRIPT

python setup.py py2app
# Rename output bundle to warmpy.app
if [[ -d ".build/dist" ]]; then
  if [[ -d ".build/dist/main.app" ]]; then
    rm -rf ".build/dist/warmpy.app"
    mv ".build/dist/main.app" ".build/dist/warmpy.app"
  fi
fi


echo "Build done. App in $BUILD_DIR/dist/"
