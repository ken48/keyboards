#!/bin/bash
set -euo pipefail


PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
BUILD_DIR=".build"

WARMUP_TMP_DIR="$PROJECT_DIR/$BUILD_DIR/tmp"
mkdir -p "$WARMUP_TMP_DIR"
WARMUP_JSON="$WARMUP_TMP_DIR/warmup.json"
PYTHON=${WARMPY_PYTHON:?Set WARMPY_PYTHON explicitly}

IFS=$'\n\t'

if [[ $# -ne 1 ]]; then
  echo "Usage: $0 <deps_yaml_or_dir>"
  exit 1
fi

INPUT="$1"

if [[ -z "$INPUT" ]]; then
  echo "ERROR: input is empty"
  exit 1
fi

if [[ -f "$INPUT" ]]; then
  DEPS_YAML="$INPUT"
elif [[ -d "$INPUT" ]]; then
  DEPS_YAML="$INPUT/warmpy_build_deps.yaml"
else
  echo "ERROR: input not found: $INPUT"
  exit 1
fi

# Canonicalize deps yaml path (INPUT may be relative and we cd later)
DEPS_YAML="$(cd "$(dirname "$DEPS_YAML")" && pwd)/$(basename "$DEPS_YAML")"


# Generate app icon (warmpy.icns) from assets/warmpy_icon.png if iconutil is available (macOS)
if command -v iconutil >/dev/null 2>&1; then
  ICON_PNG="$PROJECT_DIR/assets/warmpy_icon.png"
  ICONSET_DIR="$PROJECT_DIR/.build/tmp/warmpy.iconset"
  mkdir -p "$ICONSET_DIR"
  # Create required sizes
  sips -z 16 16     "$ICON_PNG" --out "$ICONSET_DIR/icon_16x16.png" >/dev/null
  sips -z 32 32     "$ICON_PNG" --out "$ICONSET_DIR/icon_16x16@2x.png" >/dev/null
  sips -z 32 32     "$ICON_PNG" --out "$ICONSET_DIR/icon_32x32.png" >/dev/null
  sips -z 64 64     "$ICON_PNG" --out "$ICONSET_DIR/icon_32x32@2x.png" >/dev/null
  sips -z 128 128   "$ICON_PNG" --out "$ICONSET_DIR/icon_128x128.png" >/dev/null
  sips -z 256 256   "$ICON_PNG" --out "$ICONSET_DIR/icon_128x128@2x.png" >/dev/null
  sips -z 256 256   "$ICON_PNG" --out "$ICONSET_DIR/icon_256x256.png" >/dev/null
  sips -z 512 512   "$ICON_PNG" --out "$ICONSET_DIR/icon_256x256@2x.png" >/dev/null
  sips -z 512 512   "$ICON_PNG" --out "$ICONSET_DIR/icon_512x512.png" >/dev/null
  cp "$ICON_PNG" "$ICONSET_DIR/icon_512x512@2x.png"
  iconutil -c icns "$ICONSET_DIR" -o "$PROJECT_DIR/assets/warmpy.icns" >/dev/null
fi

# 2) stable working dir
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

BUILD_DIR="$SCRIPT_DIR/.build"
VENV_DIR="$BUILD_DIR/venv"

PIP_DEPS_TXT="$BUILD_DIR/pip_deps.txt"
EXTRA_INCLUDES_JSON="$BUILD_DIR/extra_includes.json"
WARMUP_JSON="$BUILD_DIR/warmup.json"

echo "== WarmPy build =="
echo "project_dir : $SCRIPT_DIR"
echo "deps_input : $INPUT"
echo "deps_yaml   : $DEPS_YAML"
echo

# 3) YAML must exist (иначе стоп)
if [[ ! -f "$DEPS_YAML" ]]; then
  echo "ERROR: deps yaml not found: $DEPS_YAML"
  exit 1
fi

# 4) clean build dirs
rm -rf "$BUILD_DIR" dist build
mkdir -p "$BUILD_DIR"

$PYTHON -m venv .build/venv
source .build/venv/bin/activate

python -m pip install --upgrade pip wheel
python -m pip install setuptools py2app pillow pyyaml pyobjc-framework-Cocoa

PIP_DEPS_TXT="$BUILD_DIR/pip_deps.txt"
EXTRA_INCLUDES_JSON="$BUILD_DIR/extra_includes.json"

python - <<PY
import json
from pathlib import Path
import yaml

deps_path = Path(r"$DEPS_YAML")
build_dir = Path(r"$BUILD_DIR")
pip_out = Path(r"$PIP_DEPS_TXT")
inc_out = Path(r"$EXTRA_INCLUDES_JSON")
warmup_out = Path(r"$WARMUP_JSON")

data = yaml.safe_load(deps_path.read_text(encoding="utf-8")) or {}

pip_deps = data.get("pip") or []
includes = data.get("includes") or []
hidden = data.get("hidden_imports") or []
warmup = data.get("warmup") or data.get("imports") or []
warmup_extra = data.get("warmup_extra") or []

for key, val in [("pip", pip_deps), ("includes", includes), ("hidden_imports", hidden), ("warmup/imports", warmup), ("warmup_extra", warmup_extra)]:
    if not isinstance(val, list) or not all(isinstance(x, str) for x in val):
        raise SystemExit(f"ERROR: '{key}' must be a list of strings")

extra = []
for seq in (includes, hidden, warmup, warmup_extra):
    for m in seq:
        m = m.strip()
        if m and m not in extra:
            extra.append(m)

build_dir.mkdir(parents=True, exist_ok=True)
pip_out.write_text("\n".join(pip_deps) + "\n", encoding="utf-8")
inc_out.write_text(json.dumps(extra), encoding="utf-8")
warmup_list = []
for m in list(warmup) + list(warmup_extra):
    m = str(m).strip()
    if m and m not in warmup_list:
        warmup_list.append(m)
warmup_out.write_text(json.dumps({"warmup": warmup_list}, indent=2), encoding="utf-8")
PY

if [[ -s ".build/pip_deps.txt" ]]; then
  python -m pip install -r .build/pip_deps.txt
fi

# Generate icns from yellow PNG
ICON_PNG="assets/warmpy_icon.png"
ICNS_OUT="assets/warmpy.icns"
ICONSET_DIR=".build/warmpy.iconset"
rm -rf "$ICONSET_DIR"
mkdir -p "$ICONSET_DIR"
for size in 16 32 128 256 512; do
  sips -z $size $size "$ICON_PNG" --out "$ICONSET_DIR/icon_${size}x${size}.png" >/dev/null
  sips -z $((size*2)) $((size*2)) "$ICON_PNG" --out "$ICONSET_DIR/icon_${size}x${size}@2x.png" >/dev/null
done
iconutil -c icns "$ICONSET_DIR" -o "$ICNS_OUT"




python setup.py py2app
mv .build/dist/main.app .build/dist/warmpy.app

# Rename the actual executable inside the bundle so Activity Monitor shows "warmpy"
APP_PATH=".build/dist/warmpy.app"
if [[ -f "$APP_PATH/Contents/MacOS/main" ]]; then
  mv "$APP_PATH/Contents/MacOS/main" "$APP_PATH/Contents/MacOS/warmpy"
fi

# Update Info.plist to match executable name + display names
PLIST="$APP_PATH/Contents/Info.plist"
/usr/libexec/PlistBuddy -c "Set :CFBundleExecutable warmpy" "$PLIST" 2>/dev/null ||   /usr/libexec/PlistBuddy -c "Add :CFBundleExecutable string warmpy" "$PLIST"

/usr/libexec/PlistBuddy -c "Set :CFBundleName WarmPy" "$PLIST" 2>/dev/null ||   /usr/libexec/PlistBuddy -c "Add :CFBundleName string WarmPy" "$PLIST"

/usr/libexec/PlistBuddy -c "Set :CFBundleDisplayName WarmPy" "$PLIST" 2>/dev/null ||   /usr/libexec/PlistBuddy -c "Add :CFBundleDisplayName string WarmPy" "$PLIST"

# Copy generated warmup.json into bundle Resources (build artifact; not kept in repo)
APP_PATH=".build/dist/warmpy.app"
RES_DIR="$APP_PATH/Contents/Resources"
mkdir -p "$RES_DIR"
cp -f "$WARMUP_JSON" "$RES_DIR/warmup.json"

# Ensure status template images are present in bundle Resources
cp -f "$PROJECT_DIR/assets/warmpyStatusTemplate.png" "$RES_DIR/warmpyStatusTemplate.png"
cp -f "$PROJECT_DIR/assets/warmpyStatusTemplate@2x.png" "$RES_DIR/warmpyStatusTemplate@2x.png"



echo "Build complete: .build/dist/warmpy.app"