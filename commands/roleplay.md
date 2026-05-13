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

### Phase 1: 加载状态（L1 真相）

读取项目中的状态文件：
- `runtime.yaml` 或 `xdworld/runtime.yaml` → 当前场景
- `characters/*.yaml` 或 `xdworld/characters/*.yaml` → 角色定义
- `world_base.yaml` 或 `xdworld/world_base.yaml` → 世界设定
- `Arguments.yaml` 或 `xdworld/Arguments.yaml` → 档位定义

如果找不到文件，询问用户项目结构。

### Phase 2: 确定活跃角色

从 `runtime.yaml` 的 `present_characters` 提取在场角色列表。

### Phase 3: 派生 L2 视图（信息隔离核心）

**关键：必须由主控 Agent 执行，不可委托给子 Agent。**

对每个在场角色生成独立的 L2 视图：

```yaml
character_id: ""
filtered_scene:
  observable_entities: {该角色能感知的其他角色}
  environment: {环境描述}
accessible_knowledge:
  - {Public 知识}
  - {角色自身经历}
  - {其他合理可知的知识}
  - {过滤掉 GodOnly 知识}
  - {过滤掉感官失能/环境遮挡的感知}
embodiment_state:
  senses: {档位描述}
  physical: {身体状态}
prior_subjective_state:
  beliefs: {心智模型}
  goals: {当前目标}
```

**过滤规则**：
- `access: "God Only"` → 不进入任何 L2
- `access: "Condition: 修行者"` → 只进入修行者角色的 L2
- 数值 → 档位（如 1550 → "Adept 级别"）

### Phase 4: 并行启动角色代入 Agent

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

### Phase 5: 验证 L3 输出

验证每个 Agent 输出：
- `referenced_fact_ids ⊆ accessible_knowledge`
- 不引用 GodOnly 知识
- 不描述感官失能的感知

### Phase 6: OutcomePlanner

主控 Agent（持有 L1 真相）基于所有 L3 输出决定事件结果。

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

### Phase 8: 记录事件与更新状态

**事件记录**：
- 在 `records/` 目录下创建事件记录文件
- 文件命名格式：`{YYYYMMDD}_{HHmmss}_{场景关键字}.yaml`
- 记录内容示例：

```yaml
timestamp: "1003-07-17T14:30"
scene: "洞庭湖畔"
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

---

## 数值档位翻译

| 范围 | 档位 |
|------|------|
| 0-200 | Mundane |
| 200-1000 | Apprentice |
| 1000-1800 | Adept |
| 1800-2600 | Master |
| 2600+ | Ascendant |