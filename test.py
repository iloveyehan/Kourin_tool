import os
from pathlib import Path

# 动态收集 ui/ 目录下所有 .py 文件（非递归）
SOURCES = [str(p) for p in Path("ui").glob("*.py")]

# 如果想要递归子目录，改成 rglob：
# SOURCES = [str(p) for p in Path("ui").rglob("*.py")]

LANGS = ["en", "vi"]

for lang in LANGS:
    ts_path = f"translations/{lang}.ts"
    sources_str = " ".join(SOURCES)
    cmd = f"pyside6-lupdate {sources_str} -ts {ts_path}"
    print(f"Running: {cmd}")
    os.system(cmd)
    print(f"Updated {ts_path}")
