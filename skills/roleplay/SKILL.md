---
name: roleplay
description: This skill should be used when the user asks to "/roleplay", "推进剧情", "角色代入", "多角色认知", "信息隔离", "代入思考", or discusses roleplay workflow with multiple characters. Provides information isolation framework for character cognitive simulation.
version: 1.0.0
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

---

## 执行流程

### Step 1: 加载 L1 真相

读取项目中的状态文件：
- `runtime.yaml` → 当前场景
- `characters/*.yaml` → 角色定义
- `world_base.yaml` → 世界设定（含 GodOnly 知识）
- `Arguments.yaml` → 档位定义

### Step 2: 派生 L2 视图

**关键：这是信息隔离的核心。必须由主控 Agent 执行。**

对每个在场角色生成独立的 L2 视图：

```yaml
character_id: ""
filtered_scene:
  observable_entities: {该角色能感知的其他角色}
  environment: {环境描述}
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
```

**过滤规则**：
- `access: "God Only"` → 不进入任何 L2
- `access: "Condition: 修行者"` → 只进入修行者角色的 L2
- 数值 → 档位（如 1550 → "Adept 级别"）

### Step 3: 并行启动角色代入 Agent

使用 Agent 工具，每个角色一个独立调用：

```
Agent Prompt 结构：

你是角色代入引擎。代入以下角色进行思考。

## 角色身份
{角色名称、定位、心智模型}

## 你能感知的
{L2.filtered_scene}

## 你知道的事情
{L2.accessible_knowledge}

## 你的身体状态
{L2.embodiment_state}

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

### Step 4: 验证 L3 输出

验证每个 Agent 输出：
- `referenced_fact_ids ⊆ accessible_knowledge`
- 不引用 GodOnly 知识
- 不描述感官失能的感知

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

### Step 7: 记录事件与更新状态

**事件记录**：
- 在 `records/` 目录下创建事件记录文件
- 文件命名：`{YYYYMMDD}_{HHmmss}_{场景关键字}.yaml`
- 记录：时间戳、参与角色、事件摘要、各角色行动、叙事文本

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