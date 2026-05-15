#!/usr/bin/env python3
"""
Roleplay 角色状态计算器
从角色文件和 runtime.yaml 读取数据，进行批量计算
"""

import os
import sys
import json
import yaml
from pathlib import Path
from typing import Dict, Any, List, Optional

# 添加脚本目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from rp_calc import (
    parse_date_string,
    calculate_character_age,
    get_character_tiers,
    get_tier_delta,
    clear_session_cache,
    get_tier_config
)


def load_yaml(file_path: str) -> Dict[str, Any]:
    """加载 YAML 文件"""
    with open(file_path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f) or {}


def find_character_files(base_dir: str = "xdworld/characters") -> List[str]:
    """查找所有角色文件"""
    char_dir = Path(base_dir)
    if not char_dir.exists():
        return []

    return [str(f) for f in char_dir.glob("*.yaml") if not f.name.startswith(".")]


def get_current_date_from_runtime(runtime_path: str = "xdworld/runtime.yaml") -> Optional[str]:
    """从 runtime.yaml 获取当前日期"""
    if not os.path.exists(runtime_path):
        return None

    runtime = load_yaml(runtime_path)

    # 尝试多个可能的日期字段
    current_scene = runtime.get("current_scene", {})
    environment = runtime.get("environment", {})

    date_str = (
        current_scene.get("date") or
        environment.get("time") or
        runtime.get("date")
    )

    if date_str:
        # 处理带时间的格式，如 "1003-07-14T20:30"
        if "T" in str(date_str):
            date_str = str(date_str).split("T")[0]

    return date_str


def process_character(
    char_file: str,
    current_date: str,
    config_path: Optional[str] = None
) -> Dict[str, Any]:
    """
    处理单个角色文件

    Returns:
        {
            "name": str,
            "file": str,
            "age": dict or None,
            "tiers": dict,
            "warnings": list
        }
    """
    result = {
        "name": os.path.basename(char_file).replace(".yaml", ""),
        "file": char_file,
        "age": None,
        "tiers": {},
        "warnings": []
    }

    try:
        char_data = load_yaml(char_file)

        # 提取角色数据（处理嵌套结构）
        char_inner = char_data
        for key in char_data:
            if isinstance(char_data[key], dict) and "name" in char_data[key]:
                char_inner = char_data[key]
                result["name"] = char_inner.get("name", result["name"])
                break

        # 计算年龄
        birthday = char_inner.get("birthday")
        if birthday and current_date:
            # 处理 birthday 可能是字典的情况（如孟缘有多个生日）
            birthday_str = None
            birthday_note = None

            if isinstance(birthday, str):
                birthday_str = birthday
            elif isinstance(birthday, dict):
                # 尝试找到主要的生日字段
                # 常见格式: {"枝叶成灵": "421-05-22", "建木本体诞生": "221-04"}
                # 优先使用第一个值或标记为"主要"的字段
                for key, value in birthday.items():
                    if isinstance(value, str):
                        birthday_str = value
                        birthday_note = key
                        break
                    elif isinstance(value, dict):
                        # 可能是 {"成灵": {"time": "421-05"}} 格式
                        if "time" in value:
                            birthday_str = value["time"]
                            birthday_note = key
                            break

            if birthday_str:
                age_result = calculate_character_age(birthday_str, current_date)
                if "error" not in age_result:
                    if birthday_note:
                        age_result["birthday_type"] = birthday_note
                    result["age"] = age_result

                    # 检查年龄是否与设定一致
                    stated_age = char_inner.get("age")
                    if stated_age is not None:
                        calc_age = age_result.get("age_years")
                        if calc_age is not None and abs(calc_age - stated_age) > 1:
                            result["warnings"].append(
                                f"年龄不一致: 设定={stated_age}, 计算={calc_age}"
                            )
                else:
                    result["warnings"].append(age_result.get("error", "年龄计算失败"))

        # 计算属性档位
        result["tiers"] = get_character_tiers(char_inner, config_path)

    except Exception as e:
        result["warnings"].append(f"处理错误: {str(e)}")

    return result


def compare_characters(
    char1_data: Dict[str, Any],
    char2_data: Dict[str, Any],
    config_path: Optional[str] = None
) -> Dict[str, Any]:
    """
    比较两个角色的属性差距

    Returns:
        {
            "char1_name": str,
            "char2_name": str,
            "comparisons": {
                "physique": {"delta": ..., "tier_gap": ...},
                ...
            },
            "overall_assessment": str
        }
    """
    # 提取角色名称和属性
    char1_name = char1_data.get("name", "Unknown")
    char2_name = char2_data.get("name", "Unknown")

    # 处理嵌套结构
    char1_inner = char1_data
    for key in char1_data:
        if isinstance(char1_data[key], dict) and "name" in char1_data[key]:
            char1_inner = char1_data[key]
            char1_name = char1_inner.get("name", char1_name)
            break

    char2_inner = char2_data
    for key in char2_data:
        if isinstance(char2_data[key], dict) and "name" in char2_data[key]:
            char2_inner = char2_data[key]
            char2_name = char2_inner.get("name", char2_name)
            break

    attrs1 = char1_inner.get("attributes", {})
    attrs2 = char2_inner.get("attributes", {})

    comparisons = {}
    total_gap = 0
    gap_count = 0

    for attr in attrs1:
        if attr in attrs2:
            v1 = attrs1[attr]
            v2 = attrs2[attr]
            if isinstance(v1, (int, float)) and isinstance(v2, (int, float)):
                delta_result = get_tier_delta(v1, v2, config_path)
                comparisons[attr] = delta_result
                if delta_result["tier_gap"] >= 0:
                    total_gap += delta_result["tier_gap"]
                    gap_count += 1

    # 整体评估
    if gap_count > 0:
        avg_gap = total_gap / gap_count
        if avg_gap < 0.5:
            overall = "势均力敌"
        elif avg_gap < 1.5:
            overall = "略有差距"
        elif avg_gap < 2.5:
            overall = "差距明显"
        else:
            overall = "实力悬殊"
    else:
        overall = "无法比较"

    return {
        "char1_name": char1_name,
        "char2_name": char2_name,
        "comparisons": comparisons,
        "overall_assessment": overall
    }


def process_all_characters(
    base_dir: str = "xdworld",
    output_format: str = "json"
) -> Dict[str, Any]:
    """
    处理所有角色文件

    Returns:
        {
            "current_date": str,
            "characters": [...],
            "summary": str
        }
    """
    runtime_path = os.path.join(base_dir, "runtime.yaml")
    config_path = os.path.join(base_dir, "worldview", "Arguments.yaml")
    chars_dir = os.path.join(base_dir, "characters")

    current_date = get_current_date_from_runtime(runtime_path)

    if not current_date:
        return {
            "error": "无法从 runtime.yaml 获取当前日期",
            "current_date": None
        }

    char_files = find_character_files(chars_dir)
    characters = []

    for char_file in char_files:
        char_result = process_character(char_file, current_date, config_path)
        characters.append(char_result)

    # 生成摘要
    summary_parts = [f"当前日期: {current_date}", f"角色数量: {len(characters)}"]

    birthdays_today = [
        c["name"] for c in characters
        if c["age"] and c["age"].get("is_birthday_today")
    ]
    if birthdays_today:
        summary_parts.append(f"今日生日: {', '.join(birthdays_today)}")

    warnings = []
    for c in characters:
        warnings.extend([f"{c['name']}: {w}" for w in c.get("warnings", [])])
    if warnings:
        summary_parts.append(f"警告: {len(warnings)} 条")

    return {
        "current_date": current_date,
        "characters": characters,
        "summary": "\n".join(summary_parts)
    }


# ============================================================================
# CLI 接口
# ============================================================================

def main():
    import argparse

    parser = argparse.ArgumentParser(description="Roleplay 角色状态计算器")
    subparsers = parser.add_subparsers(dest="command", help="子命令")

    # 处理所有角色
    all_parser = subparsers.add_parser("all", help="处理所有角色")
    all_parser.add_argument("--base-dir", default="xdworld", help="基础目录")
    all_parser.add_argument("--format", choices=["json", "text"], default="json", help="输出格式")

    # 处理单个角色
    char_parser = subparsers.add_parser("char", help="处理单个角色")
    char_parser.add_argument("file", help="角色文件路径")
    char_parser.add_argument("--runtime", default="xdworld/runtime.yaml", help="runtime.yaml 路径")

    # 比较两个角色
    compare_parser = subparsers.add_parser("compare", help="比较两个角色")
    compare_parser.add_argument("char1", help="第一个角色文件")
    compare_parser.add_argument("char2", help="第二个角色文件")

    # 获取当前日期
    date_parser = subparsers.add_parser("date", help="获取当前日期")
    date_parser.add_argument("--runtime", default="xdworld/runtime.yaml", help="runtime.yaml 路径")

    # 清除缓存
    cache_parser = subparsers.add_parser("clear-cache", help="清除会话缓存")

    args = parser.parse_args()

    if args.command == "all":
        result = process_all_characters(args.base_dir, args.format)
        if args.format == "json":
            print(json.dumps(result, ensure_ascii=False, indent=2))
        else:
            print(result["summary"])
            for c in result.get("characters", []):
                print(f"\n--- {c['name']} ---")
                if c.get("age"):
                    print(f"年龄: {c['age']['age_years']}岁")
                    if c['age'].get('is_birthday_today'):
                        print("🎂 今日生日!")
                if c.get("tiers", {}).get("attributes"):
                    print("属性档位:")
                    for attr, info in c["tiers"]["attributes"].items():
                        print(f"  {attr}: {info['tier']} ({info['value']})")
                for w in c.get("warnings", []):
                    print(f"⚠️ {w}")

    elif args.command == "char":
        current_date = get_current_date_from_runtime(args.runtime)
        config_path = os.path.join(os.path.dirname(args.runtime), "worldview", "Arguments.yaml")
        if not os.path.exists(config_path):
            config_path = None
        result = process_character(args.file, current_date, config_path)
        print(json.dumps(result, ensure_ascii=False, indent=2))

    elif args.command == "compare":
        char1 = load_yaml(args.char1)
        char2 = load_yaml(args.char2)
        result = compare_characters(char1, char2)
        print(json.dumps(result, ensure_ascii=False, indent=2))

    elif args.command == "date":
        current_date = get_current_date_from_runtime(args.runtime)
        if current_date:
            print(f"当前日期: {current_date}")
        else:
            print("无法获取当前日期")

    elif args.command == "clear-cache":
        clear_session_cache()
        print("缓存已清除")

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
