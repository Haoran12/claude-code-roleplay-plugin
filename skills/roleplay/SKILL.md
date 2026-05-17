---
name: roleplay
description: This skill should be used when the user asks to "/roleplay", "推进剧情", "角色代入", "多角色认知", "信息隔离", "代入思考", or discusses roleplay workflow with multiple characters. Provides information isolation framework for character cognitive simulation.
version: 1.1.0
---

# Roleplay Skill - 信息隔离角色代入

本 skill 定义多角色代入的信息隔离框架，确保每个角色的认知边界不被突破。

---

## 核心概念

### 三层数据语义

```
L1 Truth Store（客观真相）
    │ 程序派生（主控 Agent 执行）
    ▼
L2 Per-Character Access（角色可触及的客观）
    │ Agent 工具并行调用
    ▼
L3 Subjective State（角色主观心智）
    │ 验证 + 合并
    ▼
L4 Outcome（事件结果）
    │ SurfaceRealizer
    ▼
Narrative Text（叙事文本）
```

### 信息隔离铁律

| 规则 | 检查方式 |
|------|----------|
| Omniscience Leakage | Agent 输出的 referenced_fact_ids ⊆ accessible_knowledge |
| God Only | GodOnly 知识不进入任何角色的 L2 |
| Embodiment | 感官失能时不描述对应感知 |
| Cross-Character | Agent prompt 不含其他角色的 L2 |
| Environment Consistency | 角色感知与 L2 体感档位一致 |
| Positive Enumeration | L2 视图只包含角色**知道/能感知**的内容，严禁出现任何否定式提及（见下） |

### 正面枚举铁律（Positive Enumeration）

**核心原则：不知道 = 不提及。沉默是唯一的隔离。**

L2 视图和 Agent Prompt 中**严禁**出现以下任何形式的否定式表述：

| 禁止形式 | 错误示例 | 正确做法 |
|----------|----------|----------|
| "你不知道X" | "你不知道沈烟的真实身份" | 不提及沈烟的身份信息，只列出该角色能观察到的表象 |
| "你无法感知X" | "你无法感知灵力波动" | 不提及灵力波动，只描述可感知的现象 |
| "你不应该知道X" | "你不应该知道这个秘密" | 不提及该秘密的存在 |
| "X对你来说是未知的" | "幕后主使对你未知" | 不提及幕后主使 |
| "注意不要提及X" | "注意不要暴露你知道X" | 不在 prompt 中出现 X |
| "X被隐藏/遮挡" | "真相被隐藏" | 不提及真相，只描述可见的表象 |
| 列出"不知道"的清单 | "你不知道的事情：A、B、C" | 不列出任何"不知道"的清单 |

**执行规则**：
1. `accessible_knowledge` 只正面枚举角色**知道**的事实，不出现任何"不知道"
2. `filtered_scene` 只描述角色**能感知**的现象，不出现任何"无法感知"
3. Agent Prompt 中不包含任何否定式提及、警告、约束来"提醒"角色不知道某事
4. 如果某条信息被过滤掉，L2 视图中**不留痕迹**——不说明为什么缺失，不暗示缺失的存在
5. 角色对其他角色的认知，只描述可观察的表象（外貌、行为、已展示的能力），不标注"真实情况未知"

**为什么这很重要**：在 prompt 中写"你不知道X"等于告诉角色 X 的存在，这比直接告知 X 更危险——角色既知道了秘密的存在，又被要求假装不知道，这会导致认知矛盾和信息泄漏。

---

## 执行流程

### Step 1: 加载 L1 真相

读取项目中的状态文件：
- `runtime.yaml` → 当前场景（工作目录根目录）
- `characters/*.yaml` → 角色定义
- `worldview/*.yaml` → 世界总体设定和大事件记录
- `social/*.yaml` → 制度、风俗、文化现象等社会设定
- `location_and_faction/*.yaml` → 地区和势力设定
- `others/*.yaml` → 其他设定文件
- `records/*.yaml` → 历史事件记录

**目录结构约定**：
```
项目根目录/
├── runtime.yaml           # 当前运行状态（必需）
├── characters/            # 角色定义（必需）
│   └── *.yaml
├── worldview/             # 世界总体设定和大事件
│   └── *.yaml
├── social/                # 制度、风俗、文化现象
│   └── *.yaml
├── location_and_faction/  # 地区和势力设定
│   └── *.yaml
├── others/                # 其他设定文件
│   └── *.yaml
└── records/               # 历史事件记录
    └── *.yaml
```

### Step 1.5: 环境推断与初始化

**触发条件**：runtime.yaml 中缺少完整环境信息，或用户输入了新的场景

**地理气候匹配**：

| 气候带 | 纬度范围 | 1月 | 4月 | 7月 | 10月 |
|--------|----------|-----|-----|-----|------|
| 热带 (tropical) | 0-23.5° | 温暖 | 炎热 | 酜热 | 炎热 |
| 亚热带 (subtropical) | 23.5-35° | 寒冷 | 温暖 | 酜热 | 凉爽 |
| 暖温带 (warm_temperate) | 35-45° | 严寒 | 微寒转暖 | 炎热 | 凉爽 |
| 寒温带 (cold_temperate) | 45-55° | 极寒 | 寒冷 | 温暖 | 寒冷 |
| 寒带 (frigid) | 55-90° | 极寒 | 严寒 | 微寒 | 严寒 |

**地形修正**：

| 地形 | 温度 | 湿度 | 风速 |
|------|------|------|------|
| 湖泊/河流 | -2°C | +10% | +1 m/s |
| 森林/竹林 | -3°C | +5% | -2 m/s |
| 山地 | -5°C/500m | - | +3 m/s |
| 城市/城镇 | +2°C | -5% | -1 m/s |
| 沙漠 | +5°C | -20% | +2 m/s |
| 海边 | - | +15% | +3 m/s |

**光照计算**：

| 时间 | 太阳位置 | 光照状态 |
|------|----------|----------|
| 05:00-07:00 | 东方升起 | 晨曦，光线柔和 |
| 07:00-11:00 | 东南向高空 | 上午，光线明亮 |
| 11:00-13:00 | 正南当空 | 正午，光线最强 |
| 13:00-17:00 | 西南向移动 | 午后，光线渐斜 |
| 17:00-19:00 | 西方低垂 | 黄昏，光线橙红 |
| 19:00-21:00 | 落入地平线 | 暮色，光线昏暗 |
| 21:00-05:00 | 地平线下 | 夜色，依赖月光/星光/灯火 |

### Step 2: 派生 L2 视图

**关键：这是信息隔离的核心。必须由主控 Agent 执行。**

对每个在场角色生成独立的 L2 视图：

```yaml
character_id: ""
filtered_scene:
  observable_entities: {该角色能感知的其他角色}

  environment:
    # 时空感知
    location: "洞庭湖畔竹林"
    time_of_day: "午后"
    season: "盛夏"

    # 体感气象（档位化）
    body_sensation:
      temperature: "酷热难耐"
      humidity: "闷热潮湿"
      wind: "几乎无风"
      comfort: "极不舒适，汗水难蒸发"

    # 降水感知
    precipitation:
      status: "无降水"

    # 光影感知
    illumination:
      brightness: "明亮但有遮蔽"
      light_source: "日光透过竹叶"
      shadows: "竹影斑驳"
      visibility: "良好"
      celestial_visible:
        sun: "透过竹叶可见"
        moon: null
        stars: null

    # 空气感知
    atmosphere:
      quality: "清新"
      breath_feeling: "呼吸顺畅"
      smell: "竹叶清香混合湖水气息"

    # 身体影响
    physical_impact:
      immediate:
        - "汗水浸湿后背"
        - "额头微汗"
        - "衣衫贴身不适"
      risks:
        - "长时间暴晒可能中暑"
      mitigations:
        - "竹林提供部分遮阴"

accessible_knowledge:
  - {Public 知识}
  - {角色自身经历}
  - {过滤掉 GodOnly 知识}

embodiment_state:
  senses: {档位描述，非数值}
  physical: {身体状态}

prior_subjective_state:
  beliefs: {心智模型}
  goals: {当前目标}

# 法术影响（按 access 过滤）
magical_effects: []
```

**体感档位翻译表**：

| 温度范围 | 档位 | 典型影响 |
|----------|------|----------|
| ≥35°C | 酜热 | 大汗淋漓，体力流失快 |
| 30-35°C | 炎热 | 持续出汗，需补水 |
| 25-30°C | 温暖 | 舒适，活动自如 |
| 15-25°C | 凉爽 | 最舒适 |
| 5-15°C | 微寒 | 需添衣 |
| 0-5°C | 寒冷 | 手脚发凉 |
| -10-0°C | 严寒 | 冻伤风险 |
| <-10°C | 极寒 | 生存威胁 |

**能见度档位**：

| 条件 | 档位 | 影响 |
|------|------|------|
| 晴朗无雾 | 极佳 | 远眺数里 |
| 薄雾/轻尘 | 良好 | 百步清晰 |
| 中雾/沙尘/小雨 | 受限 | 十步模糊 |
| 浓雾/暴雪/沙暴 | 极差 | 面目难辨 |
| 无光（深夜无月） | 黑暗 | 伸手不见五指 |

**过滤规则**：
- `access: "God Only"` → 不进入任何 L2，且 L2 中不提及该信息的存在
- `access: "Condition: 修行者"` → 只进入修行者角色的 L2，非修行者的 L2 中不提及该信息的存在
- 数值 → 档位（如 1550 → "Adept 级别"）
- **正面枚举**：被过滤的信息在 L2 中不留任何痕迹，不使用"你不知道X"等否定式表述
- **对其他角色的描述**：只写可观察的表象（外貌、言行、已展示的能力），不写"真实身份未知"、"实力不明"等暗示信息缺失的标注

### Step 3: 并行启动角色代入 Agent

使用 Agent 工具，每个角色一个独立调用：

```
Agent Prompt 结构：

你是角色代入引擎。代入以下角色进行思考。

## 角色身份
{角色名称、定位}

## 心智模型
{角色 mindModel 完整内容}

## 你能感知的
{L2.filtered_scene}

## 你知道的事情
{L2.accessible_knowledge}

## 你的身体状态
{L2.embodiment_state}

## 你之前的心智状态
{L2.prior_subjective_state}

## 当前情境
{用户输入}

输出格式（JSON）：
{
  "thoughts": "内心独白",
  "emotions": {"primary": "", "intensity": ""},
  "intentions": [{"action": "", "reasoning": ""}],
  "speech": "",
  "referenced_fact_ids": []
}
```

**关键约束**：
- 每个 Agent 只接收自己的 L2 视图
- Agent 之间不共享信息
- Agent 不知道 L1 真相
- **正面枚举约束（最高优先级）**：Agent Prompt 中严禁出现任何否定式提及——不写"你不知道X"、"你无法感知X"、"X对你未知"、"注意不要提及X"。被过滤的信息在 prompt 中不留任何痕迹，不说明为什么缺失，不暗示缺失的存在。对其他角色的描述只写可观察的表象，不写"真实身份未知"等暗示。

### Step 4: 验证 L3 输出

验证每个 Agent 输出：
- `referenced_fact_ids ⊆ accessible_knowledge`
- 不引用 GodOnly 知识
- 不描述感官失能的感知
- **环境反应合理性**：角色对温度/光照/空气的感知与 L2 体感档位一致
- **否定式提及检查**：L3 输出中不得出现"不知道X"、"无法感知X"等表述——如果角色不知道某事，它不会主动提及"不知道"，而是根本不会想到那件事

### Step 5: OutcomePlanner

主控 Agent（持有 L1 真相）基于所有 L3 输出决定事件结果。

### Step 6: SurfaceRealizer（叙事文本生成）

**读取叙事风格**：
- 从 `runtime.yaml` 读取 `narrative_style` 配置
- 或从 `style/*.yaml` 读取预设文件

**风格维度**：
| 维度 | 选项 |
|------|------|
| language | classical / early_modern / modern |
| rhetoric | ornate / balanced / plain |
| psychology | direct / indirect / mixed |
| pacing | detailed / varied / concise |

**叙事约束**：
- 只披露 `narratable_facts` 白名单内的事实
- 不披露 GodOnly 知识
- 输出 `used_fact_ids` 用于验证
- **环境描写一致性**：叙事中的环境描写与 L1 环境状态一致

### Step 7: 判断是否记录事件

**触发事件记录的条件**（满足任一即触发）：

| 条件 | 判断标准 |
|------|----------|
| 场景更换 | `current_scene` 发生变化（地点/时间/氛围重大转变） |
| 剧情转折 | 重大决策、战斗结果、角色关系质变、秘密揭露等 |
| 章节结束 | 用户明确表示"本章结束"或类似意图 |
| 累计阈值 | 同一场景内已执行超过 5 个回合（可配置） |

**不触发记录的情况**：
- 日常对话、探索、等待
- 同一场景内的连续互动
- 用户明确要求"跳过记录"

**轻量状态更新**（每回合执行）：
- 更新 `runtime.yaml` 中的角色位置、活动、即时状态
- 不创建新的事件记录文件

### Step 8: 事件记录（条件触发）

**仅在触发条件满足时执行**：

- 在 `records/` 目录下创建事件记录文件
- 文件命名：`{章节序号}_{场景关键字}.yaml` 或 `{YYYYMMDD}_{场景关键字}.yaml`
- 记录：时间戳、参与角色、事件摘要、各角色行动、叙事文本
- 同一场景内的多个回合合并记录到同一文件

**状态更新**：
- 更新 `runtime.yaml` 中的场景与角色状态
- 不在 `runtime.yaml` 中存储详细事件历史

---

## 数值档位翻译

Agent 不接触原始数值，只读档位：

| 范围 | 档位 |
|------|------|
| 0-200 | Mundane |
| 200-1000 | Apprentice |
| 1000-1800 | Adept |
| 1800-2600 | Master |
| 2600+ | Ascendant |