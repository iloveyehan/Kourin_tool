#!/usr/bin/env python3
import json
import re

# 定义新版本号（字符串形式）
version = '1.2.5'

def update_json():
    json_file = 'version.json'
    # tuple 形式
    version_tuple = tuple(map(int, version.split('.')))
    version_str = f"({','.join(map(str, version_tuple))})"

    # 去掉最后一个小数点后的版本字符串：1.1.2 -> 1.12
    major_minor_patch = version.split('.')
    if len(major_minor_patch) == 3:
        short_version = f"{major_minor_patch[0]}.{major_minor_patch[1]}{major_minor_patch[2]}"
    else:
        short_version = version  # fallback

    with open(json_file, 'r', encoding='utf-8') as f:
        data = json.load(f)

    data["version"] = version_str

    if "download_url" in data:
        # 替换 URL 中的 vX.Y.Z.zip 或 vX.Y.zip 为新的 vX.YZ.zip
        data["download_url"] = re.sub(
            r'v[\d.]+(?=\.zip)',
            f'v{short_version}',
            data["download_url"]
        )

    with open(json_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    print(f"[✓] 已更新 JSON 文件: version={version_str}, download_url 中版本改为 v{short_version}.zip")


def update_bl_info(py_file_path):
    """更新 Python 文件中的 bl_info 字典中的版本号"""
    version_tuple = tuple(int(x) for x in version.split('.'))
    new_version_code = f"\"version\": {version_tuple}"

    with open(py_file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # 使用正则匹配并替换 bl_info 里的 version 字段
    content_new = re.sub(
        r'"version"\s*:\s*\([^)]+\)',
        new_version_code,
        content
    )

    if content != content_new:
        with open(py_file_path, 'w', encoding='utf-8') as f:
            f.write(content_new)
        print(f"[✓] Python 文件已更新: {py_file_path} -> version = {version_tuple}")
    else:
        print(f"[i] 未找到匹配的 version 字段或版本号已是最新")


# 执行更新
update_json()
update_bl_info("__init__.py")