#!/usr/bin/env python3
"""
Roleplay 数值计算工具集
- 日期差计算、纪念日/生日判断
- 属性档位转换
- 缓存机制：会话级缓存，新会话自动失效
"""

import os
import re
import json
import yaml
from datetime import datetime, date
from typing import Dict, List, Optional, Tuple, Any
from functools import lru_cache

# ============================================================================
# 缓存管理
# ============================================================================

_session_cache: Dict[str, Any] = {}

def clear_session_cache():
    """清除会话缓存 - 新会话开始时调用"""
    global _session_cache
    _session_cache = {}
    get_tier_config.cache_clear()
    parse_date_string.cache_clear()

# ============================================================================
# 日期解析与计算
# ============================================================================

# 常见日期格式模式
DATE_PATTERNS = [
    (r'^(\d{4})-(\d{1,2})-(\d{1,2})$', '%Y-%m-%d'),           # 1003-07-15
    (r'^(\d{4})/(\d{1,2})/(\d{1,2})$', '%Y/%m/%d'),           # 1003/07/15
    (r'^(\d{4})\.(\d{1,2})\.(\d{1,2})$', '%Y.%m.%d'),         # 1003.07.15
    (r'^(\d{4})年(\d{1,2})月(\d{1,2})日$', '%Y年%m月%d日'),    # 1003年7月15日
    (r'^(\d{4})-(\d{1,2})$', '%Y-%m'),                         # 1003-07 (仅年月)
    (r'^(\d{4})$', '%Y'),                                       # 1003 (仅年)
]

# 特殊日期格式（需要特殊处理）
SPECIAL_DATE_PATTERNS = [
    # BC 日期: BC 1288-02-02 -> 负年份
    (r'^BC\s*(\d+)-(\d{1,2})-(\d{1,2})$', 'bc_full'),
    # 短年份: 371-03-22 -> 补全为 0371
    (r'^(\d{1,3})-(\d{1,2})-(\d{1,2})$', 'short_year'),
    # 年号日期: 天宝三年-07-15 (需要年号映射)
    (r'^([^\d]+)(\d+)-(\d{1,2})-(\d{1,2})$', 'era_date'),
]


class ParsedDate:
    """解析后的日期对象，支持 BC 日期和虚构纪年"""
    def __init__(self, year: int, month: int, day: int, is_bc: bool = False, era: str = None):
        self.year = year
        self.month = month
        self.day = day
        self.is_bc = is_bc
        self.era = era  # 年号（如 "天宝"）

    def to_date(self) -> Optional[date]:
        """转换为标准 date 对象（BC 日期返回 None）"""
        if self.is_bc or self.year < 1:
            return None
        try:
            return date(self.year, self.month, self.day)
        except ValueError:
            return None

    def __str__(self):
        prefix = "BC " if self.is_bc else ""
        era_prefix = f"{self.era}" if self.era else ""
        return f"{prefix}{era_prefix}{self.year:04d}-{self.month:02d}-{self.day:02d}"


@lru_cache(maxsize=128)
def parse_date_string(date_str: str) -> Optional[date]:
    """
    解析日期字符串，支持多种格式
    返回标准 date 对象
    """
    if not date_str:
        return None

    date_str = str(date_str).strip()

    # 先尝试特殊格式
    for pattern, format_type in SPECIAL_DATE_PATTERNS:
        match = re.match(pattern, date_str, re.IGNORECASE)
        if match:
            parsed = _parse_special_date(match, format_type)
            if parsed:
                return parsed.to_date()

    # 标准格式
    for pattern, fmt in DATE_PATTERNS:
        if re.match(pattern, date_str):
            try:
                dt = datetime.strptime(date_str, fmt)
                return dt.date()
            except ValueError:
                continue

    # 尝试 ISO 格式
    try:
        return date.fromisoformat(date_str)
    except ValueError:
        pass

    return None


def parse_date_detailed(date_str: str) -> Optional[ParsedDate]:
    """
    解析日期字符串，返回详细信息（包括 BC 标记等）
    用于需要显示原始格式的场景
    """
    if not date_str:
        return None

    date_str = str(date_str).strip()

    # 先尝试特殊格式
    for pattern, format_type in SPECIAL_DATE_PATTERNS:
        match = re.match(pattern, date_str, re.IGNORECASE)
        if match:
            return _parse_special_date(match, format_type)

    # 标准格式
    for pattern, fmt in DATE_PATTERNS:
        if re.match(pattern, date_str):
            try:
                dt = datetime.strptime(date_str, fmt)
                return ParsedDate(dt.year, dt.month, dt.day)
            except ValueError:
                continue

    return None


def _parse_special_date(match, format_type: str) -> Optional[ParsedDate]:
    """解析特殊日期格式"""
    if format_type == 'bc_full':
        # BC 1288-02-02
        year = int(match.group(1))
        month = int(match.group(2))
        day = int(match.group(3))
        return ParsedDate(year, month, day, is_bc=True)

    elif format_type == 'short_year':
        # 371-03-22 -> 补全为 0371
        year_str = match.group(1)
        year = int(year_str.zfill(4))  # 补全到4位
        month = int(match.group(2))
        day = int(match.group(3))
        return ParsedDate(year, month, day)

    elif format_type == 'era_date':
        # 天宝三年-07-15 (暂不支持年号转换，返回 None)
        return None

    return None


def calculate_date_diff(
    start_date_str: str,
    end_date_str: str,
    reference_year: Optional[int] = None
) -> Dict[str, Any]:
    """
    计算两个日期之间的差值

    Args:
        start_date_str: 起始日期（如生日）
        end_date_str: 结束日期（如当前日期）
        reference_year: 参考年份（用于处理虚构纪年，如 1003 年）

    Returns:
        {
            "years": int,
            "months": int,
            "days": int,
            "total_days": int,
            "is_anniversary": bool,
            "is_birthday": bool,
            "start_parsed": str,  # 解析后的标准格式
            "end_parsed": str,
            "start_original": str,  # 原始格式（如 BC 1288）
            "is_bc": bool  # 是否是 BC 日期
        }
    """
    # 尝试详细解析
    start_parsed = parse_date_detailed(start_date_str)
    end_parsed = parse_date_detailed(end_date_str)

    # 如果详细解析失败，尝试标准解析
    start_date = start_parsed.to_date() if start_parsed else parse_date_string(start_date_str)
    end_date = end_parsed.to_date() if end_parsed else parse_date_string(end_date_str)

    if not start_date or not end_date:
        # 检查是否是 BC 日期
        if start_parsed and start_parsed.is_bc:
            return {
                "error": f"BC 日期无法精确计算年份差",
                "years": None,
                "months": None,
                "is_bc": True,
                "start_original": str(start_parsed),
                "start_parsed": str(start_parsed),
                "end_parsed": end_date.isoformat() if end_date else end_date_str
            }
        return {
            "error": f"无法解析日期: start={start_date_str}, end={end_date_str}",
            "years": None,
            "months": None
        }

    # 计算年份差
    years = end_date.year - start_date.year
    months = end_date.month - start_date.month
    days = end_date.day - start_date.day

    # 调整负数
    if days < 0:
        months -= 1
    if months < 0:
        years -= 1
        months += 12

    # 是否生日/周年
    is_birthday = (end_date.month == start_date.month and
                   end_date.day == start_date.day)
    is_anniversary = is_birthday  # 在这个上下文中相同

    # 总天数
    delta = end_date - start_date
    total_days = delta.days

    return {
        "years": years,
        "months": months,
        "days": days,
        "total_days": total_days,
        "is_anniversary": is_anniversary,
        "is_birthday": is_birthday,
        "start_parsed": start_date.isoformat(),
        "end_parsed": end_date.isoformat(),
        "start_original": str(start_parsed) if start_parsed else start_date_str,
        "is_bc": start_parsed.is_bc if start_parsed else False
    }


def calculate_character_age(
    birthday_str: str,
    current_date_str: str
) -> Dict[str, Any]:
    """
    计算角色年龄

    Args:
        birthday_str: 角色生日
        current_date_str: 当前日期（从 runtime.yaml 读取）

    Returns:
        {
            "age_years": int,
            "age_months": int,
            "is_birthday_today": bool,
            "birthday_parsed": str,
            "next_birthday": str  # 下一个生日
        }
    """
    result = calculate_date_diff(birthday_str, current_date_str)

    if "error" in result:
        return result

    # 计算下一个生日
    birthday = parse_date_string(birthday_str)
    current = parse_date_string(current_date_str)

    if birthday and current:
        next_birthday_year = current.year
        next_birthday = birthday.replace(year=next_birthday_year)
        if next_birthday <= current:
            next_birthday = birthday.replace(year=next_birthday_year + 1)

        result["next_birthday"] = next_birthday.isoformat()

    result["age_years"] = result["years"]
    result["age_months"] = result["months"]
    result["is_birthday_today"] = result["is_birthday"]

    return result


# ============================================================================
# 档位计算
# ============================================================================

def parse_range(range_str: str) -> Tuple[float, float]:
    """
    解析范围字符串，如 "[0, 200)" -> (0, 200)
    支持 [a, b], (a, b), [a, b), (a, b] 以及 Infinity
    """
    range_str = range_str.strip()

    # 处理 Infinity
    range_str = range_str.replace("Infinity", "float('inf')")

    # 提取边界和括号类型
    match = re.match(r'([\[\(])\s*(\S+)\s*,\s*(\S+)\s*([\]\)])', range_str)
    if not match:
        raise ValueError(f"无法解析范围: {range_str}")

    left_bracket, left_val, right_val, right_bracket = match.groups()

    # 解析数值
    left = float(left_val) if left_val != "float('inf')" else float('-inf')
    right = float(right_val) if right_val != "float('inf')" else float('inf')

    return (left, right, left_bracket == '[', right_bracket == ']')


@lru_cache(maxsize=1)
def get_tier_config(config_path: Optional[str] = None) -> Dict[str, Any]:
    """
    加载档位配置，带缓存

    Args:
        config_path: Arguments.yaml 的路径，如果为 None 则自动查找

    Returns:
        档位配置字典
    """
    # 检查缓存
    cache_key = f"tier_config_{config_path}"
    if cache_key in _session_cache:
        return _session_cache[cache_key]

    # 自动查找配置文件
    if not config_path:
        possible_paths = [
            "worldview/Arguments.yaml",
            "xdworld/worldview/Arguments.yaml",
            "Arguments.yaml",
            "xdworld/Arguments.yaml"
        ]
        for p in possible_paths:
            if os.path.exists(p):
                config_path = p
                break

    if not config_path or not os.path.exists(config_path):
        # 返回默认配置
        default_config = {
            "tiers": [
                {"name": "Mundane", "range": "[0, 200)", "description": "普通人"},
                {"name": "Apprentice", "range": "[200, 1000)", "description": "基础修行"},
                {"name": "Adept", "range": "[1000, 1800)", "description": "中坚力量"},
                {"name": "Master", "range": "[1800, 2600)", "description": "宗师级别"},
                {"name": "Ascendant", "range": "[2600, 6000)", "description": "仙灵层级"},
                {"name": "Transcendent", "range": "[6000, Infinity)", "description": "极少数存在"}
            ],
            "delta": [
                {"range": "[0, 150)", "description": "难分高下"},
                {"range": "[150, 400)", "description": "有明显差距"},
                {"range": "[400, 1000)", "description": "差距较大"},
                {"range": "[1000, Infinity)", "description": "碾压"}
            ]
        }
        _session_cache[cache_key] = default_config
        return default_config

    # 读取配置文件
    with open(config_path, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)

    # 提取档位定义
    attributes = config.get('Attributes', {})
    tier_config = {
        "tiers": attributes.get('tiers', []),
        "delta": attributes.get('Delta', []),
        "attribute_descriptions": {
            k: v for k, v in attributes.items()
            if k not in ['tiers', 'Delta']
        }
    }

    _session_cache[cache_key] = tier_config
    return tier_config


def get_tier(value: float, config_path: Optional[str] = None) -> Dict[str, Any]:
    """
    根据数值获取档位

    Args:
        value: 属性数值
        config_path: 配置文件路径

    Returns:
        {
            "tier": str,           # 档位名称
            "description": str,    # 档位描述
            "range": str,          # 档位范围
            "value": float         # 原始数值
        }
    """
    config = get_tier_config(config_path)
    tiers = config.get("tiers", [])

    for tier_def in tiers:
        range_str = tier_def.get("range", "")
        try:
            left, right, left_inc, right_inc = parse_range(range_str)

            in_range = True
            if left_inc:
                in_range = in_range and (value >= left)
            else:
                in_range = in_range and (value > left)

            if right_inc:
                in_range = in_range and (value <= right)
            else:
                in_range = in_range and (value < right)

            if in_range:
                return {
                    "tier": tier_def.get("name", "Unknown"),
                    "description": tier_def.get("description", ""),
                    "range": range_str,
                    "value": value
                }
        except ValueError:
            continue

    return {
        "tier": "Unknown",
        "description": "未找到对应档位",
        "range": "N/A",
        "value": value
    }


def get_tier_delta(
    value1: float,
    value2: float,
    config_path: Optional[str] = None
) -> Dict[str, Any]:
    """
    计算两个数值之间的档位差距

    Args:
        value1: 第一个数值
        value2: 第二个数值
        config_path: 配置文件路径

    Returns:
        {
            "delta": float,           # 绝对差值
            "delta_description": str, # 差距描述
            "delta_range": str,       # 差距范围
            "tier1": dict,            # value1 的档位信息
            "tier2": dict,            # value2 的档位信息
            "tier_gap": int           # 档位差距（整数）
        }
    """
    config = get_tier_config(config_path)

    tier1 = get_tier(value1, config_path)
    tier2 = get_tier(value2, config_path)

    delta = abs(value1 - value2)

    # 查找差距描述
    delta_description = "未知差距"
    delta_range = "N/A"

    for delta_def in config.get("delta", []):
        range_str = delta_def.get("range", "")
        try:
            left, right, left_inc, right_inc = parse_range(range_str)

            in_range = True
            if left_inc:
                in_range = in_range and (delta >= left)
            else:
                in_range = in_range and (delta > left)

            if right_inc:
                in_range = in_range and (delta <= right)
            else:
                in_range = in_range and (delta < right)

            if in_range:
                delta_description = delta_def.get("description", "")
                delta_range = range_str
                break
        except ValueError:
            continue

    # 计算档位差距
    tier_names = [t.get("name", "") for t in config.get("tiers", [])]
    try:
        idx1 = tier_names.index(tier1["tier"])
        idx2 = tier_names.index(tier2["tier"])
        tier_gap = abs(idx1 - idx2)
    except ValueError:
        tier_gap = -1  # 未知

    return {
        "delta": delta,
        "delta_description": delta_description,
        "delta_range": delta_range,
        "tier1": tier1,
        "tier2": tier2,
        "tier_gap": tier_gap
    }


def get_character_tiers(
    character_data: Dict[str, Any],
    config_path: Optional[str] = None
) -> Dict[str, Any]:
    """
    获取角色所有属性的档位信息

    Args:
        character_data: 角色数据（从 yaml 加载）
        config_path: 配置文件路径

    Returns:
        {
            "character_name": str,
            "attributes": {
                "physique": {"tier": ..., "value": ...},
                ...
            },
            "attribute_sets": {  # 多套属性（如孟缘有本体和人形两套）
                "人形躯体": {...},
                "建木本体": {...}
            },
            "summary": str  # 简要描述
        }
    """
    # 提取角色名称
    char_name = character_data.get("name", "Unknown")
    for key in character_data:
        if isinstance(character_data[key], dict) and "name" in character_data[key]:
            char_name = character_data[key].get("name", key)
            character_data = character_data[key]
            break

    config = get_tier_config(config_path)

    result = {
        "character_name": char_name,
        "attributes": {},
        "attribute_sets": {},  # 多套属性
        "summary_parts": []
    }

    # 标准属性字段名
    standard_attr_fields = ["attributes", "attribute", "attrs"]

    # 查找所有可能的属性字段
    for field_name in character_data:
        field_value = character_data[field_name]

        # 标准属性字段
        if field_name in standard_attr_fields:
            if isinstance(field_value, dict):
                for attr_name, value in field_value.items():
                    if isinstance(value, (int, float)) and not isinstance(value, bool):
                        tier_info = get_tier(value, config_path)
                        result["attributes"][attr_name] = tier_info
                        attr_desc = config.get("attribute_descriptions", {}).get(attr_name, attr_name)
                        result["summary_parts"].append(f"{attr_desc}: {tier_info['tier']} ({value})")

        # 多套属性字段（如 attributes_of_the_Tree）
        elif field_name.startswith("attributes") or field_name.startswith("attribute"):
            if isinstance(field_value, dict):
                set_name = field_name.replace("attributes_", "").replace("attribute_", "")
                if not set_name:
                    set_name = field_name

                set_attrs = {}
                for attr_name, value in field_value.items():
                    if isinstance(value, (int, float)) and not isinstance(value, bool):
                        tier_info = get_tier(value, config_path)
                        set_attrs[attr_name] = tier_info

                if set_attrs:
                    result["attribute_sets"][set_name] = {
                        "attributes": set_attrs,
                        "comment": field_value.get("comment", "")
                    }

    result["summary"] = " | ".join(result["summary_parts"])
    del result["summary_parts"]

    return result


# ============================================================================
# CLI 接口
# ============================================================================

def main():
    """命令行入口"""
    import argparse

    parser = argparse.ArgumentParser(description="Roleplay 数值计算工具")
    subparsers = parser.add_subparsers(dest="command", help="子命令")

    # 日期计算
    date_parser = subparsers.add_parser("date", help="日期计算")
    date_parser.add_argument("start", help="起始日期")
    date_parser.add_argument("end", help="结束日期")

    # 档位计算
    tier_parser = subparsers.add_parser("tier", help="档位计算")
    tier_parser.add_argument("value", type=float, help="属性数值")
    tier_parser.add_argument("--config", help="配置文件路径")

    # 档位差距
    delta_parser = subparsers.add_parser("delta", help="档位差距计算")
    delta_parser.add_argument("value1", type=float, help="第一个数值")
    delta_parser.add_argument("value2", type=float, help="第二个数值")
    delta_parser.add_argument("--config", help="配置文件路径")

    # 清除缓存
    cache_parser = subparsers.add_parser("clear-cache", help="清除会话缓存")

    args = parser.parse_args()

    if args.command == "date":
        result = calculate_date_diff(args.start, args.end)
        print(json.dumps(result, ensure_ascii=False, indent=2))

    elif args.command == "tier":
        result = get_tier(args.value, args.config)
        print(json.dumps(result, ensure_ascii=False, indent=2))

    elif args.command == "delta":
        result = get_tier_delta(args.value1, args.value2, args.config)
        print(json.dumps(result, ensure_ascii=False, indent=2))

    elif args.command == "clear-cache":
        clear_session_cache()
        print("缓存已清除")

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
