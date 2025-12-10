#!/usr/bin/env python3
import json
import re

# 定义新版本号（字符串形式）
version = '1.3.7'
def update_manifest_toml(toml_file_path):
    """更新 TOML 文件中 [addon] 部分的 version 字段"""
    
    # TOML 中的版本号通常是字符串 "X.Y.Z"
    new_version_code = f'version = "{version}"'

    try:
        with open(toml_file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # 使用正则匹配并替换 [addon] 块下的 version 字段
        # r'^version\s*=\s*".*?"$' 匹配以 version = "..." 开头的整行，^ $ 确保整行匹配
        # re.M (MULTILINE) 标志很重要，确保 ^ 和 $ 能匹配每行的开头和结尾
        content_new = re.sub(
            r'^version\s*=\s*".*?"$', 
            new_version_code, 
            content, 
            count=1,  # 只替换一次，防止误伤
            flags=re.M | re.I # 多行模式和忽略大小写
        )

        if content != content_new:
            with open(toml_file_path, 'w', encoding='utf-8') as f:
                f.write(content_new)
            print(f"[✓] TOML 文件已更新: {toml_file_path} -> version = {version}")
        else:
            print(f"[i] TOML 文件未找到匹配的 version 字段或版本号已是最新")
            
    except FileNotFoundError:
        print(f"[!] 错误: 文件未找到 - {toml_file_path}")
    except Exception as e:
        print(f"[!] 更新 TOML 文件时发生错误: {e}")
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

def update_addon_names(init_file_path, toml_file_path):
    """
    将 __init__.py 文件中的 bl_info['name'] 和 
    blender_manifest.toml 中的 id, name, tagline 字段统一修改为 "Kourin_tool"。
    """
    new_name = "Kourin_tool"

    # --- 1. 更新 __init__.py (bl_info['name']) ---
    print("\n>>> 正在更新 __init__.py 中的名称...")
    try:
        with open(init_file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # 正则表达式: 查找 "name": 后面跟着的字符串，并替换为新的名称
        # r'"name"\s*:\s*".*?"'
        new_name_code = f'"name": "{new_name}"'
        
        content_new = re.sub(
            r'"name"\s*:\s*".*?"',
            new_name_code,
            content,
            count=1 # 只替换 bl_info 中的第一个 name 字段
        )

        if content != content_new:
            with open(init_file_path, 'w', encoding='utf-8') as f:
                f.write(content_new)
            print(f"[✓] Python 文件已更新: {init_file_path} -> name = \"{new_name}\"")
        else:
            print(f"[i] Python 文件中的 'name' 字段已是最新或未找到匹配项。")

    except FileNotFoundError:
        print(f"[!] 错误: 未找到文件 - {init_file_path}")
    except Exception as e:
        print(f"[!] 更新 {init_file_path} 时发生错误: {e}")

    # --- 2. 更新 blender_manifest.toml (id, name, tagline) ---
    print("\n>>> 正在更新 TOML 文件中的 id, name, tagline...")
    try:
        with open(toml_file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()

        new_lines = []
        replaced_count = 0
        
        # 定义需要替换的字段及其目标值
        replacements = {
            "id": f'id = "{new_name}"',
            "name": f'name = "{new_name}"',
            "tagline": f'tagline = "{new_name}"'
        }
        
        # 遍历每一行进行替换
        for line in lines:
            line_stripped = line.strip()
            
            is_replaced = False
            for field, new_value in replacements.items():
                # 使用 startsWith 检查，确保只修改行首字段，避免修改注释或其他内容
                if line_stripped.startswith(f"{field} = "):
                    # 保持原始行的缩进，只替换内容
                    leading_space = line[:len(line) - len(line.lstrip())]
                    new_lines.append(leading_space + new_value + "\n")
                    replaced_count += 1
                    is_replaced = True
                    break
            
            if not is_replaced:
                new_lines.append(line)

        # 写入文件
        if replaced_count > 0:
            with open(toml_file_path, 'w', encoding='utf-8') as f:
                f.writelines(new_lines)
            print(f"[✓] TOML 文件已更新: {toml_file_path} -> 成功替换 {replaced_count} 个字段为 \"{new_name}\"")
        else:
            print(f"[i] TOML 文件中的 id, name, tagline 字段未找到或已是最新。")

    except FileNotFoundError:
        print(f"[!] 错误: 未找到文件 - {toml_file_path}")
    except Exception as e:
        print(f"[!] 更新 {toml_file_path} 时发生错误: {e}")
# 执行更新
TOML_FILE = "blender_manifest.toml"
INIT_FILE = "__init__.py"
update_json()
update_bl_info("__init__.py")
update_manifest_toml("blender_manifest.toml")
update_addon_names(INIT_FILE, TOML_FILE)