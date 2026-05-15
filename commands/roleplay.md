---
description: 多角色代入的信息隔离框架，推进剧情发展
argument-hint: 可选的场景描述或角色行动
---

# Roleplay 命令

执行多角色代入工作流，确保信息隔离。

## 当前请求

$ARGUMENTS

---

## 执行流程

### Phase 0: 确定性数值计算（必须调用脚本）

**重要：以下计算必须使用脚本，避免 LLM 误算。**

#### 0.1 获取场景上下文

**触发时机**：每次执行 roleplay 命令时，首先调用。

```bash
python3 {插件目录}/scripts/rp_workflow.py scene
```

输出包含：
- 当前日期、位置
- 在场角色的年龄、档位摘要
- 特殊事件（生日、纪念日）
- 项目目录结构

**使用场景**：
- 需要知道当前日期时
- 需要确认在场角色时
- 需要快速了解角色档位时

#### 0.2 日期计算

**触发时机**：
- 需要计算角色年龄时
- 需要判断是否生日/纪念日时
- 需要计算时间跨度时

```bash
# 日期差计算
python3 {插件目录}/scripts/rp_calc.py date "开始日期" "结束日期"

# 示例
python3 {插件目录}/scripts/rp_calc.py date "371-03-22" "1003-07-14"
# 输出: {"years": 632, "months": 3, ...}
```

支持的日期格式：
- 标准格式：`1003-07-15`
- 短年份：`371-03-22`（自动补全）
- BC 日期：`BC 1288-02-02`

#### 0.3 档位计算

**触发时机**：
- 需要将数值转换为档位描述时
- 需要比较两个角色属性差距时
- 需要在 L2 视图中描述角色能力时

```bash
# 单个数值档位
python3 {插件目录}/scripts/rp_calc.py tier 1550
# 输出: {"tier": "Adept", "description": "中坚力量...", ...}

# 两个数值差距
python3 {插件目录}/scripts/rp_calc.py delta 1550 800
# 输出: {"delta": 750, "delta_description": "差距较大", "tier_gap": 1, ...}
```

#### 0.4 角色信息格式化

**触发时机**：
- 为 L2 视图准备角色信息时
- 需要角色的档位描述时

```bash
python3 {插件目录}/scripts/rp_workflow.py l2 "角色名"
# 示例
python3 {插件目录}/scripts/rp_workflow.py l2 "孟缘"
```

输出：
```json
{
  "character": "孟缘",
  "age_description": "582岁 (枝叶成灵)",
  "tier_descriptions": {
    "physique": "Adept 级别",
    "mana_power": "Master 级别",
    ...
  }
}
```

#### 0.5 角色比较

**触发时机**：
- 需要比较两个角色实力时
- 战斗/对抗场景评估时

```bash
python3 {插件目录}/scripts/rp_character.py compare <角色1.yaml> <角色2.yaml>
```

#### 缓存管理

**触发时机**：
- 档位配置文件更新后
- 会话开始时自动清除旧缓存

```bash
python3 {插件目录}/scripts/rp_calc.py clear-cache
```

---

### Phase 1: 加载状态（L1 真相）

读取项目中的状态文件：
- `runtime.yaml` → 当前场景（工作目录根目录）
- `characters/*.yaml` → 角色定义
- `worldview/*.yaml` → 世界总体设定和大事件记录
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
├── location_and_faction/  # 地区和势力设定
│   └── *.yaml
├── others/                # 其他设定文件
│   └── *.yaml
└── records/               # 历史事件记录
    └── *.yaml
```

如果找不到文件，询问用户项目结构。

---

### Phase 1.5: 环境推断与初始化

**触发条件**：runtime.yaml 中缺少完整环境信息，或用户输入了新的场景

**执行步骤**：

#### 1. 解析已知信息

从用户输入和 runtime.yaml 提取：
- 时间点（具体时间 / 时段 / 季节 / 月份）
- 地点名称
- 天气关键词（如"暴雨"、"酷热"）
- 特殊环境描述

#### 2. 地理气候匹配

根据地点查询气候带，结合月份推断基础气象：

| 气候带 | 纬度范围 | 1月 | 4月 | 7月 | 10月 |
|--------|----------|-----|-----|-----|------|
| 热带 (tropical) | 0-23.5° | 温暖 | 炎热 | 酷热 | 炎热 |
| 亚热带 (subtropical) | 23.5-35° | 寒冷 | 温暖 | 酷热 | 凉爽 |
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

#### 3. 光照计算

根据时间推断光源位置：

| 时间 | 太阳位置 | 光照状态 |
|------|----------|----------|
| 05:00-07:00 | 东方升起 | 晨曦，光线柔和 |
| 07:00-11:00 | 东南向高空 | 上午，光线明亮 |
| 11:00-13:00 | 正南当空 | 正午，光线最强 |
| 13:00-17:00 | 西南向移动 | 午后，光线渐斜 |
| 17:00-19:00 | 西方低垂 | 黄昏，光线橙红 |
| 19:00-21:00 | 落入地平线 | 暮色，光线昏暗 |
| 21:00-05:00 | 地平线下 | 夜色，依赖月光/星光/灯火 |

**遮挡计算**：
- 地形遮挡（森林、山谷、建筑）→ 光影斑驳/遮蔽
- 云量 → 光线漫射/昏暗
- 雾/尘/降水 → 能见度下降

#### 4. 生成 L1 环境状态

将推断结果写入 runtime.yaml 的 environment 模块：

```yaml
environment:
  inferred: true  # 标记为推断值

  # 基础时空
  location: "洞庭湖畔竹林"
  time: "1003-07-17T14:30"
  time_of_day: "午后"
  season: "盛夏"

  # 气象物理
  weather:
    temperature: 36  # 摄氏度
    humidity: 85     # 百分比
    wind_speed: 2    # m/s
    wind_direction: "东南"

  # 降水
  precipitation:
    type: null | rain | snow | hail | sleet
    intensity: null | light | moderate | heavy
    accumulated: 0  # mm

  # 光照
  illumination:
    primary_source: sun | moon | artificial | magical
    celestial_bodies:
      sun_position: "午后偏西"
      moon_phase: null | waxing | full | waning
      stars_visible: true | false
    visibility_obstruction:
      clouds: 20  # 云量百分比
      fog: null | mist | fog | dense_fog
      dust: null | light_dust | sandstorm
      smoke: null | light | heavy
    artificial_lights: []
    terrain_shadow: "竹林遮蔽约60%天空"

  # 空气
  atmosphere:
    quality: clear | hazy | dusty | smoky | magical_haze
    special_particles: null | pollen | sand | ash | magical_dust

  # 法术影响（如有）
  magical_effects: []
```

#### 5. 低置信度时询问用户

若推断置信度低（如地点未知、气候带无法确定），向用户确认：
- "当前场景设定在什么地区？这将影响气候推断。"
- "现在是几点？白天还是夜晚？"

---

### Phase 2: 确定活跃角色

从 `runtime.yaml` 的 `present_characters` 提取在场角色列表。

**使用脚本获取角色详细信息**：
```bash
python3 {插件目录}/scripts/rp_workflow.py l2 "角色名"
```

---

### Phase 3: 派生 L2 视图（信息隔离核心）

**关键：必须由主控 Agent 执行，不可委托给子 Agent。**

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
      temperature: "酷热难耐"  # 36°C + 高湿 + 无风 → 档位
      humidity: "闷热潮湿"
      wind: "几乎无风"
      comfort: "极不舒适，汗水难蒸发"

    # 降水感知
    precipitation:
      status: "无降水"
      # 若有降水则显示：
      # status: "中雨"
      # sensation: "雨水打湿衣衫"

    # 光影感知
    illumination:
      brightness: "明亮但有遮蔽"
      light_source: "日光透过竹叶"
      shadows: "竹影斑驳"
      visibility: "良好"  # 受雾/尘/降水影响
      celestial_visible:
        sun: "透过竹叶可见"
        moon: null
        stars: null

    # 空气感知
    atmosphere:
      quality: "清新"
      breath_feeling: "呼吸顺畅"
      smell: "竹叶清香混合湖水气息"  # 可选

    # 身体影响（核心）
    physical_impact:
      immediate:
        - "汗水浸湿后背"
        - "额头微汗"
        - "衣衫贴身不适"
      risks:  # 潜在风险
        - "长时间暴晒可能中暑"
      mitigations:  # 自然缓解因素
        - "竹林提供部分遮阴"

  accessible_knowledge:
    - {Public 知识}
    - {角色自身经历}
    - {其他合理可知的知识}
    - {过滤掉 GodOnly 知识}
    - {过滤掉感官失能/环境遮挡的感知}

  embodiment_state:
    senses: {档位描述 - 使用脚本计算}
    physical: {身体状态}

  prior_subjective_state:
    beliefs: {心智模型}
    goals: {当前目标}

  # 法术影响（按 access 过滤）
  magical_effects: []  # 普通人看不到
```

**过滤规则**：
- `access: "God Only"` → 不进入任何 L2
- `access: "Condition: 修行者"` → 只进入修行者角色的 L2
- 数值 → 档位（**使用脚本计算**，如 1550 → "Adept 级别"）

**体感档位翻译表**：

| 温度范围 | 档位 | 典型影响 |
|----------|------|----------|
| ≥35°C | 酷热 | 大汗淋漓，体力流失快 |
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

---

### Phase 4: 并行启动角色代入 Agent

使用 Agent 工具，每个角色一个独立调用：

```
Agent Prompt 结构：

你是角色代入引擎。代入以下角色进行思考。

## 角色身份
{角色名称、定位、心智模型}
{年龄描述 - 使用脚本计算}

## 你能感知的
{L2.filtered_scene}

## 你知道的事情
{L2.accessible_knowledge}

## 你的身体状态
{L2.embodiment_state}
{档位描述 - 使用脚本计算}

## 当前情境
{用户输入或场景描述}

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

---

### Phase 5: 验证 L3 输出

验证每个 Agent 输出：
- `referenced_fact_ids ⊆ accessible_knowledge`
- 不引用 GodOnly 知识
- 不描述感官失能的感知
- **环境反应合理性**：角色对温度/光照/空气的感知与 L2 体感档位一致

---

### Phase 6: OutcomePlanner

主控 Agent（持有 L1 真相）基于所有 L3 输出决定事件结果。

---

### Phase 7: SurfaceRealizer（叙事文本生成）

**读取叙事风格**：
- 从 `runtime.yaml` 读取 `narrative_style` 配置
- 或从 `style/*.yaml` 读取预设文件
- 默认使用 `early_modern` 风格

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

---

### Phase 8: 判断是否记录事件

**触发事件记录的条件**（满足任一即触发）：

| 条件 | 判断标准 |
|------|----------|
| 场景更换 | `current_scene` 发生变化（地点/时间/氛围重大转变） |
| 剧情转折 | 重大决策、战斗结果、角色关系质变、秘密揭露等 |
| 章节结束 | 用户明确表示"本章结束"或类似意图 |
| 累计阈值 | 同一场景内已执行超过 5 个回合（可在 runtime.yaml 配置 `record_threshold`） |

**不触发记录的情况**：
- 日常对话、探索、等待
- 同一场景内的连续互动
- 用户明确要求"跳过记录"

**轻量状态更新**（每回合执行）：
- 更新 `runtime.yaml` 中的角色位置、活动、即时状态
- 不创建新的事件记录文件

---

### Phase 9: 事件记录（条件触发）

**仅在触发条件满足时执行**：

- 在 `records/` 目录下创建或追加事件记录文件
- 文件命名格式：`{章节序号}_{场景关键字}.yaml` 或 `{YYYYMMDD}_{场景关键字}.yaml`
- 同一场景内的多个回合合并记录到同一文件
- 记录内容示例：

```yaml
timestamp: "1003-07-17T14:30"
scene: "洞庭湖畔"
environment:
  temperature: "酷热"
  weather: "晴朗无风"
summary: "许宁发现孤女，决定收留"
participants:
  - "许宁"
  - "沈烟"
  - "孤女"
events:
  - actor: "许宁"
    action: "发现女童，上前查看"
    outcome: "发现蝴蝶印记，决定带走"
  - actor: "沈烟"
    action: "观察师父举动"
    outcome: "好奇但不发问"
narrative_text: |
  {生成的叙事文本}
```

**状态更新**：
- 更新 `runtime.yaml` 中的 `current_scene` 状态
- 更新 `present_characters` 的位置、活动、状态
- 不在 `runtime.yaml` 中存储详细事件历史

---

## 信息隔离铁律

| 规则 | 检查方式 |
|------|----------|
| Omniscience Leakage | referenced_fact_ids ⊆ accessible_knowledge |
| God Only | GodOnly 知识不进入 L2 |
| Embodiment | 感官失能时不描述对应感知 |
| Cross-Character | Agent prompt 不含其他角色的 L2 |
| Environment Consistency | 角色感知与 L2 体感档位一致 |

---

## 脚本调用总结

| 场景 | 脚本命令 | 输出 |
|------|----------|------|
| 获取场景上下文 | `rp_workflow.py scene` | 日期、位置、角色信息、特殊事件 |
| 日期计算 | `rp_calc.py date "开始" "结束"` | 年份差、是否生日 |
| 档位计算 | `rp_calc.py tier 数值` | 档位名称、描述 |
| 差距计算 | `rp_calc.py delta 数值1 数值2` | 差距描述、档位间隔 |
| L2 视图格式化 | `rp_workflow.py l2 "角色名"` | 年龄描述、档位描述 |
| 角色比较 | `rp_character.py compare 文件1 文件2` | 属性对比、整体评估 |
| 清除缓存 | `rp_calc.py clear-cache` | 无输出 |

**脚本位置**：`{插件目录}/scripts/`

---

## 数值档位翻译

**使用脚本动态计算，档位定义来自 `worldview/Arguments.yaml`**

默认档位范围（仅供参考，实际使用脚本计算）：
| 范围 | 档位 |
|------|------|
| 0-200 | Mundane |
| 200-1000 | Apprentice |
| 1000-1800 | Adept |
| 1800-2600 | Master |
| 2600-6000 | Ascendant |
| 6000+ | Transcendent |

差距档位：
| 范围 | 描述 |
|------|------|
| 0-150 | 难分高下 |
| 150-400 | 有明显差距，可弥补 |
| 400-1000 | 差距较大，难以弥补 |
| 1000+ | 碾压 |
