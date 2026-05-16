#!/usr/bin/env python3
"""
Roleplay 工作流集成脚本
提供 roleplay 命令所需的数值计算功能

使用方式：
1. 作为模块导入：from rp_workflow import get_scene_context
2. 命令行：python rp_workflow.py scene
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
    parse_date_detailed,
    calculate_character_age,
    get_character_tiers,
    get_tier_delta,
    get_tier_config,
    clear_session_cache,
    ParsedDate
)


def load_yaml(file_path: str) -> Dict[str, Any]:
    """加载 YAML 文件"""
    with open(file_path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f) or {}


def find_project_structure() -> Dict[str, str]:
    """
    自动检测项目目录结构

    Returns:
        {
            "runtime_path": str,
            "characters_dir": str,
            "config_path": str,
            "base_dir": str
        }
    """
    result = {
        "runtime_path": None,
        "characters_dir": None,
        "config_path": None,
        "social_dir": None,
        "base_dir": None
    }

    # 可能的目录结构
    possible_structures = [
        # 结构1: xdworld 子目录
        {
            "base_dir": "xdworld",
            "runtime": "xdworld/runtime.yaml",
            "characters": "xdworld/characters",
            "config": "xdworld/worldview/Arguments.yaml",
            "social": "xdworld/social"
        },
        # 结构2: 项目根目录
        {
            "base_dir": ".",
            "runtime": "runtime.yaml",
            "characters": "characters",
            "config": "worldview/Arguments.yaml",
            "social": "social"
        }
    ]

    for structure in possible_structures:
        if os.path.exists(structure["runtime"]):
            result["runtime_path"] = structure["runtime"]
            result["base_dir"] = structure["base_dir"]
            result["characters_dir"] = structure["characters"]
            if os.path.exists(structure["config"]):
                result["config_path"] = structure["config"]
            result["social_dir"] = structure.get("social")
            break

    return result


def get_scene_context(
    runtime_path: Optional[str] = None,
    base_dir: Optional[str] = None
) -> Dict[str, Any]:
    """
    获取当前场景上下文，用于 roleplay 工作流

    Args:
        runtime_path: runtime.yaml 路径，None 时自动检测
        base_dir: 项目基础目录，None 时自动检测

    Returns:
        {
            "current_date": str,
            "current_date_parsed": str,
            "location": str,
            "present_characters": [
                {
                    "name": str,
                    "age": int,
                    "age_note": str,  # 如 "今日生日!"
                    "tiers_summary": str,  # 档位摘要
                    "file": str
                }
            ],
            "special_events": [  # 今日特殊事件
                "今天是XXX的生日",
                "今天是XXX周年纪念日"
            ],
            "tier_config_source": str,
            "project_structure": dict  # 检测到的项目结构
        }
    """
    result = {
        "current_date": None,
        "current_date_parsed": None,
        "location": None,
        "present_characters": [],
        "special_events": [],
        "tier_config_source": None,
        "project_structure": None
    }

    # 自动检测项目结构
    if not runtime_path or not base_dir:
        structure = find_project_structure()
        result["project_structure"] = structure
        if not runtime_path:
            runtime_path = structure["runtime_path"]
        if not base_dir:
            base_dir = structure["base_dir"]

    # 加载 runtime
    if not runtime_path or not os.path.exists(runtime_path):
        result["error"] = f"runtime.yaml 不存在: {runtime_path or '未找到'}"
        return result

    runtime = load_yaml(runtime_path)

    # 获取当前日期
    current_scene = runtime.get("current_scene", {})
    environment = runtime.get("environment", {})

    date_str = (
        current_scene.get("date") or
        environment.get("time") or
        runtime.get("date")
    )

    if date_str:
        if "T" in str(date_str):
            date_str = str(date_str).split("T")[0]
        result["current_date"] = date_str

        parsed = parse_date_detailed(date_str)
        if parsed:
            result["current_date_parsed"] = str(parsed)

    # 获取位置
    result["location"] = current_scene.get("location") or environment.get("location")

    # 获取在场角色
    present_chars = runtime.get("present_characters", [])

    # 使用检测到的目录结构
    if result["project_structure"]:
        chars_dir = result["project_structure"].get("characters_dir") or os.path.join(base_dir, "characters")
        config_path = result["project_structure"].get("config_path")
    else:
        chars_dir = os.path.join(base_dir, "characters") if base_dir else "characters"
        config_path = os.path.join(base_dir, "worldview", "Arguments.yaml") if base_dir else "worldview/Arguments.yaml"

    if config_path and os.path.exists(config_path):
        result["tier_config_source"] = config_path

    for char_info in present_chars:
        if isinstance(char_info, dict):
            char_name = char_info.get("name", "")
        else:
            char_name = str(char_info)

        if not char_name:
            continue

        # 查找角色文件
        char_file = find_character_file(chars_dir, char_name)
        if not char_file:
            result["present_characters"].append({
                "name": char_name,
                "error": "角色文件未找到"
            })
            continue

        # 处理角色
        char_data = load_yaml(char_file)
        char_result = process_character_for_scene(
            char_data,
            result["current_date"],
            config_path
        )
        char_result["file"] = char_file
        result["present_characters"].append(char_result)

        # 检查特殊事件
        if char_result.get("is_birthday_today"):
            result["special_events"].append(f"今天是{char_result['name']}的生日")

    return result


def find_character_file(chars_dir: str, char_name: str) -> Optional[str]:
    """查找角色文件"""
    if not os.path.exists(chars_dir):
        return None

    # 尝试多种文件名格式
    possible_names = [
        f"{char_name}.yaml",
        f"{char_name}.yml",
    ]

    # 也尝试拼音/英文转换
    name_mappings = {
        "孟缘": "MengYuan",
        "宋祈": "SongQi",
        "沈烟": "ShenYan",
        "许宁": "XuNing",
        "霍岐": "HuoQi",
        "祁峦": "QiLuan",
        "周俨": "ZhouYan",
        "苍角": "Cangjue",
        "谢离": "XieLi",
        "遐蝶": "Xiadie",
        "扶荫": "Fuyin",
        "陈山止": "ChenShanzhi",
    }

    if char_name in name_mappings:
        possible_names.append(f"{name_mappings[char_name]}.yaml")

    for name in possible_names:
        path = os.path.join(chars_dir, name)
        if os.path.exists(path):
            return path

    return None


def process_character_for_scene(
    char_data: Dict[str, Any],
    current_date: str,
    config_path: Optional[str] = None
) -> Dict[str, Any]:
    """
    为场景上下文处理角色数据

    Returns:
        {
            "name": str,
            "age": int,
            "age_note": str,
            "tiers_summary": str,
            "is_birthday_today": bool
        }
    """
    result = {
        "name": "Unknown",
        "age": None,
        "age_note": "",
        "tiers_summary": "",
        "is_birthday_today": False
    }

    # 提取角色数据
    char_inner = char_data
    for key in char_data:
        if isinstance(char_data[key], dict) and "name" in char_data[key]:
            char_inner = char_data[key]
            result["name"] = char_inner.get("name", key)
            break
        elif isinstance(char_data[key], dict) and key not in ["attributes", "abilities", "experience"]:
            # 可能是角色名作为 key
            result["name"] = key
            char_inner = char_data[key]
            break

    if result["name"] == "Unknown" and char_data:
        # 尝试从第一个 key 获取名称
        first_key = list(char_data.keys())[0]
        if isinstance(char_data[first_key], dict):
            result["name"] = char_data[first_key].get("name", first_key)
            char_inner = char_data[first_key]

    # 计算年龄
    birthday = char_inner.get("birthday")
    if birthday and current_date:
        birthday_str = None
        birthday_type = None

        if isinstance(birthday, str):
            birthday_str = birthday
        elif isinstance(birthday, dict):
            for key, value in birthday.items():
                if isinstance(value, str):
                    birthday_str = value
                    birthday_type = key
                    break
                elif isinstance(value, dict) and "time" in value:
                    birthday_str = value["time"]
                    birthday_type = key
                    break

        if birthday_str:
            age_result = calculate_character_age(birthday_str, current_date)
            if "error" not in age_result:
                result["age"] = age_result.get("age_years")
                result["is_birthday_today"] = age_result.get("is_birthday_today", False)

                if result["is_birthday_today"]:
                    result["age_note"] = "🎂 今日生日!"
                elif birthday_type:
                    result["age_note"] = f"({birthday_type})"

    # 获取档位摘要
    tiers_result = get_character_tiers(char_inner, config_path)
    result["tiers_summary"] = tiers_result.get("summary", "")

    # 如果有多套属性，也添加到摘要
    attr_sets = tiers_result.get("attribute_sets", {})
    if attr_sets:
        for set_name, set_data in attr_sets.items():
            set_summary = []
            for attr, info in set_data.get("attributes", {}).items():
                set_summary.append(f"{attr}: {info['tier']}")
            if set_summary:
                result["tiers_summary"] += f" [{set_name}: {', '.join(set_summary)}]"

    return result


def format_for_l2_view(
    character_name: str,
    runtime_path: Optional[str] = None,
    base_dir: Optional[str] = None
) -> Dict[str, Any]:
    """
    为 L2 视图格式化角色信息

    Args:
        character_name: 角色名称
        runtime_path: runtime.yaml 路径，None 时自动检测
        base_dir: 项目基础目录，None 时自动检测

    Returns:
        {
            "character": str,
            "age_description": str,  # 如 "582岁 (枝叶成灵)"
            "tier_descriptions": {
                "physique": "Adept 级别",
                ...
            },
            "embodiment_notes": []  # 感官/身体状态备注
        }
    """
    # 自动检测项目结构
    structure = find_project_structure()
    if not runtime_path:
        runtime_path = structure["runtime_path"]
    if not base_dir:
        base_dir = structure["base_dir"]

    chars_dir = structure.get("characters_dir") or (os.path.join(base_dir, "characters") if base_dir else "characters")
    config_path = structure.get("config_path")

    char_file = find_character_file(chars_dir, character_name)
    if not char_file:
        return {"error": f"角色文件未找到: {character_name}"}

    # 获取当前日期
    if not runtime_path or not os.path.exists(runtime_path):
        return {"error": f"runtime.yaml 未找到"}

    runtime = load_yaml(runtime_path)
    current_scene = runtime.get("current_scene", {})
    environment = runtime.get("environment", {})
    date_str = (
        current_scene.get("date") or
        environment.get("time") or
        runtime.get("date")
    )
    if date_str and "T" in str(date_str):
        date_str = str(date_str).split("T")[0]

    char_data = load_yaml(char_file)
    scene_info = process_character_for_scene(char_data, date_str, config_path)

    # 构建档位描述
    tiers_result = get_character_tiers(char_data, config_path)
    tier_descriptions = {}

    for attr, info in tiers_result.get("attributes", {}).items():
        tier_descriptions[attr] = f"{info['tier']} 级别"

    # 年龄描述
    age_description = ""
    if scene_info["age"] is not None:
        age_description = f"{scene_info['age']}岁"
        if scene_info["age_note"]:
            age_description += f" {scene_info['age_note']}"

    return {
        "character": character_name,
        "age_description": age_description,
        "tier_descriptions": tier_descriptions,
        "embodiment_notes": [],
        "raw_tiers": tiers_result
    }


# ============================================================================
# CLI 接口
# ============================================================================

def main():
    import argparse

    parser = argparse.ArgumentParser(description="Roleplay 工作流集成")
    subparsers = parser.add_subparsers(dest="command", help="子命令")

    # 场景上下文
    scene_parser = subparsers.add_parser("scene", help="获取场景上下文")
    scene_parser.add_argument("--runtime", default=None, help="runtime.yaml 路径（自动检测）")
    scene_parser.add_argument("--base-dir", default=None, help="基础目录（自动检测）")

    # L2 视图格式化
    l2_parser = subparsers.add_parser("l2", help="为 L2 视图格式化角色信息")
    l2_parser.add_argument("character", help="角色名称")
    l2_parser.add_argument("--runtime", default=None, help="runtime.yaml 路径（自动检测）")
    l2_parser.add_argument("--base-dir", default=None, help="基础目录（自动检测）")

    # 清除缓存
    cache_parser = subparsers.add_parser("clear-cache", help="清除会话缓存")

    args = parser.parse_args()

    if args.command == "scene":
        result = get_scene_context(args.runtime, args.base_dir)
        print(json.dumps(result, ensure_ascii=False, indent=2))

    elif args.command == "l2":
        result = format_for_l2_view(args.character, args.runtime, args.base_dir)
        print(json.dumps(result, ensure_ascii=False, indent=2))

    elif args.command == "clear-cache":
        clear_session_cache()
        print("缓存已清除")

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
