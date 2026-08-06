# EDAid (Multi-Agent ChatEDA) 论文深度讲解

> **Divergent Thoughts toward One Goal: LLM-based Multi-Agent Collaboration System for Electronic Design Automation**
> Haoyuan Wu, Haisheng Zheng, Zhuolun He, Bei Yu
> The Chinese University of Hong Kong; Shanghai Artificial Intelligence Lab; ChatEDA Tech
> NAACL 2025 Main Conference, Long Papers, pp. 1710--1721
> 原文：[NAACL2025_Multi-Agent_ChatEDA.pdf](./NAACL2025_Multi-Agent_ChatEDA.pdf)
> 代码：https://github.com/wuhy68/ChatEDAv1

---

## 1. 一句话定位

**EDAid 是在 ChatEDA 单 Agent 基础上引入多 Agent 协作机制的后端流程自动化系统——** 用 3 个"意见分歧的"R0 Agent 各自生成 EDA 脚本候选，再由 1 个 R1 Decision Agent 按 yes-token 概率选出最佳方案。ChipLlama-70B + EDAid 多 Agent 组合在 ChatEDA-bench 和 iEDA-bench 上均达到 **100% 准确率**，比单 Agent（94% / 96%）提升 6 个百分点，彻底消除了 50 题 benchmark 上的长尾错误。

这句话里的五个承重点，后面逐一拆解：

1. **多 Agent 分歧-裁决机制** — 不是"一个 Agent 反复改"，而是让 3 个 Agent 在不同 few-shot 上下文下独立生成方案，再由裁判选出最佳。这本质上是 Self-Consistency 策略在 EDA 领域的应用。
2. **ChipLlama 专家模型** — 基于 Llama3（8B/70B），用 MathInstruct 80K + CodeInstruct 100K + EDAInstruct 8K 混合指令微调，强化 EDA 流程推理与跨平台泛化。
3. **Demo Retrieval + Random Grouping** — 从示例数据库中检索相关 EDA 工具使用案例，随机分组给不同 R0 Agent，利用 LLM 对 prompt 的敏感性自然产生分歧思维。
4. **Yes-token Probability 决策** — R1 不依赖外部评分器，直接用 LLM 输出 `yes` token 的 logit 概率作为置信度，选概率最高的候选脚本。
5. **跨平台泛化** — 不仅在 OpenROAD（ChatEDA-bench）上评估，还构建了 iEDA-bench（50 题，基于中科院计算所的 iEDA 平台），证明跨 EDA 平台的泛化能力。

---

## 2. EDA 阶段映射（①-⑰）

参照 [芯片流程.md](../芯片流程.md) 的 17 阶段标准编号：

| 阶段 | 覆盖 | 说明 |
|------|:---:|------|
| **① RTL 设计** | ❌ | EDAid 不生成 RTL，假设已有可综合 RTL |
| ② RTL 功能仿真 | ❌ | 不包含仿真验证 |
| **③ 逻辑综合** | ✅ **核心** | `run_synthesis(clock_period=...)`，多 Agent 可探索不同参数组合 |
| ④ 门级仿真 | ❌ | — |
| ⑤ STA | △ | 被底层 EDA 工具自动执行，EDAid 不直接控制 |
| ⑥ 形式验证 | ❌ | — |
| **⑦ 布局规划 (Floorplan)** | ✅ **核心** | `floorplan(...)`，R1 裁决机制可纠正跳过 floorplan 的错误 |
| **⑧ 标准单元摆放 (Placement)** | ✅ **核心** | `placement(density=...)`，裁决机制纠正参数阶段错位 |
| **⑨ 时钟树综合 (CTS)** | ✅ **核心** | `cts(tns_end_percent=...)` |
| **⑩ 布线 (Routing)** | ✅ **核心** | `global_route()` + `detail_route()` |
| ⑪ 后仿真 | ❌ | — |
| ⑫ 物理验证 (DRC+LVS) | ❌ | — |
| **⑬ 签核 (Signoff)** | △ 部分 | `final_report()` + `get_metric()` 读取 PPA 指标 |
| ⑭ 流片 | ❌ | — |
| ⑮ 制造 | ❌ | — |
| ⑯ 封装+测试 | ❌ | — |
| ⑰ 芯片到手 | ❌ | — |

**覆盖率：5/17（核心覆盖） + 2/17（部分/间接覆盖）。** 与 ChatEDA 完全一致的阶段覆盖。EDAid 的改进不在覆盖更多阶段，而在同一阶段上的可靠性大幅提升——通过多 Agent 冗余消除了单 Agent 在长链工具调用中的中间步骤错误。

**新增亮点**：EDAid 额外在 iEDA 平台（中科院计算所开发的开源 EDA 平台）上构建了 iEDA-bench（50 题），证明了跨 EDA 平台的泛化能力——这是原 ChatEDA（仅 OpenROAD）做不到的。

> ⚠️ EDAid 的 100% 准确率是指 50 道题上生成的脚本被判定为正确。R1 的决策是基于语言模型概率的判断（LLM verifier），不是基于真实 EDA 工具执行结果（execution verifier）。候选选择阶段不运行 OpenROAD/iEDA。

---

## 3. 输入 / 输出

### 3.1 输入

EDAid 继承了 ChatEDA 的全部输入（自然语言需求 + API 文档），并新增核心输入：

**EDA Tool Usage Demo Database（工具使用示例库）**：每个示例是一个三元组 `(Q, C, A)`：
- **Q (Query)**：用户需求文本
- **C (Context / Planning Steps)**：任务分解步骤
- **A (Answer / Script)**：生成的 Python 脚本

示例库通过 embedding 模型向量化所有 Q，构建向量索引用于语义检索。

**具体例子（端到端贯穿本文）**：

```
用户输入：
Can you help me to experiment with different combinations of clock
periods and channel values for the "router" design on the platform
"asap7"?
```

**检索到的相关 Demo（模拟）**：
- Demo 1: "Perform grid search for floorplan and placement parameters on nangate45"
- Demo 2: "Run the flow from setup to detail routing for aes on asap7"
- Demo 3: "Optimize CTS parameters for router design on sky130"

这些 Demo 被随机分组成 Group A、Group B、Group C，分别给 3 个 R0 Agent。

### 3.2 中间产物

**Divergent Thought 候选**（3 份各自的 Task Planning + Script）：

Agent A（正确——yes 概率 0.82）：
```
Planning:
Step 1: setup("router", "asap7")
Step 2: run_synthesis(clock_period=...)
Step 3: floorplan(macro_place_channel=...)
Step 4: placement()
Step 5: cts()
Step 6: global_route()
Step 7: detail_route()
→ 参数正确传递到 floorplan
```

Agent B（错误——yes 概率 0.41）：
```
Planning:
Step 1: setup(...)
Step 2: run_synthesis(...)
Step 3: floorplan()    ← 忘记传 macro_place_channel 参数
Step 4: placement()
...
Step 6: global_route(channel_value)  ← 错误！global_route 没有这个参数
```

Agent C（错误——yes 概率 0.32）：
```
Planning:
Step 1: setup(...)
Step 2: run_synthesis(...)
Step 3: floorplan()
Step 4: placement(tns_end_percent=40)  ← 错误！这是 CTS 的参数
...
```

### 3.3 输出

R1 Decision Agent 选出 Agent A（yes 概率最高 = 0.82），其生成的 Python 脚本：

```python
tool = chateda()
clock_periods = [1, 2, 3, 4, 5]
channel_values = [5, 10, 15]
for clock_period in clock_periods:
    for channel_value in channel_values:
        tool.setup(design_name="router", platform="asap7")
        tool.run_synthesis(clock_period=clock_period)
        tool.floorplan(macro_place_channel=channel_value)
        tool.placement()
        tool.cts()
        tool.global_route()
        tool.detail_route()
        performance = tool.get_metric("route", ["performance"])
```

---

## 4. 方法与架构

### 4.1 整体 Pipeline

```text
┌──────────────────────────────────────────────────────────────────┐
│                        EDAid 多 Agent 系统                        │
│                                                                   │
│   EDA Task (自然语言) + API Document                              │
│         │                                                         │
│         ▼                                                         │
│   ┌──────────────────────────────────────┐                       │
│   │   Demo Database (向量检索)            │                       │
│   │   ┌─────────┐ ┌─────────┐ ┌────────┐ │                       │
│   │   │ Group A │ │ Group B │ │ Group C│ │                       │
│   │   │ (K个示例)│ │ (K个示例)│ │ (K个示例)│ │                       │
│   │   └────┬────┘ └────┬────┘ └───┬────┘ │                       │
│   └────────┼───────────┼──────────┼──────┘                       │
│            │            │           │                              │
│            ▼            ▼           ▼                              │
│   ┌────────────┐ ┌────────────┐ ┌────────────┐                   │
│   │ Agent-R0-A │ │ Agent-R0-B │ │ Agent-R0-C │  ← 3 个 R0       │
│   │ ChipLlama  │ │ ChipLlama  │ │ ChipLlama  │    Divergent      │
│   │            │ │            │ │            │    Thoughts       │
│   │ Planning A │ │ Planning B │ │ Planning C │    Agents         │
│   │    ↓       │ │    ↓       │ │    ↓       │                   │
│   │ Script A   │ │ Script B   │ │ Script C   │                   │
│   └─────┬──────┘ └─────┬──────┘ └─────┬──────┘                   │
│         └──────────────┼──────────────┘                          │
│                        │                                          │
│         O = {Script_A, Script_B, Script_C}                        │
│                        │                                          │
│                        ▼                                          │
│   ┌────────────────────────────────────────┐                     │
│   │ Agent-R1 (Decision Making)              │                     │
│   │ ChipLlama                               │                     │
│   │                                         │                     │
│   │ 逐个分析每个候选脚本 → 计算 yes-token   │                     │
│   │ logit 概率 → 选概率最高的脚本          │                     │
│   │                                         │                     │
│   │ System prompt KV Cache 共享（加速）      │                     │
│   └──────────────────┬─────────────────────┘                     │
│                      │                                            │
│                      ▼                                            │
│   最终 EDA Script → 执行 (OpenROAD / iEDA) → GDSII / PPA        │
└──────────────────────────────────────────────────────────────────┘
```

对应论文 Figure 4：给定 EDA 任务，多个 Agent（divergent-thoughts agents R0 + decision-making agent R1）协作生成 EDA 脚本，最终脚本通过 API 连接 EDA 工具。

### 4.2 核心模块逐个详解

#### 模块 1：ChipLlama 模型（单 Agent 的"大脑"）

**做什么**：理解用户需求、做任务规划、生成 EDA 脚本。与 AutoMage 的本质区别在于基座模型和训练数据构成。

**为什么换到 Llama3**：Llama3 的通用能力（推理、代码生成）显著强于 Llama2。AutoMage 选 Llama2 是因为当时的 CodeLlama 有 EDA 知识丢失问题，但 Llama3 时代这个问题不再突出。

| 维度 | AutoMage/AutoMage2 | ChipLlama |
|------|-------------------|-----------|
| Base Model | Llama2 | **Llama3**（8B / 70B） |
| 训练数据 | ~1500 EDA + ~110K Code | **80K Math + 100K Code + 8K EDA** = 188K |
| 训练方式 | QLoRA | QLoRA（相同技术栈） |
| 跨平台 | 仅 OpenROAD | OpenROAD + iEDA |
| 训练重点 | EDA 工具使用 | **整体 EDA 流程理解**，而非单个 API 调用 |

**为什么需要 MathInstruct（80K）**：EDA 流程中频繁涉及参数优化——如"时钟周期从 1ns 到 5ns，步长 1ns，搜索最优值"——本质是组合搜索/优化问题。数学推理能力直接影响 LLM 生成 EDA 脚本的质量。消融实验（Table 2）证明了这一点：不加 MathInstruct 时，iEDA 跨平台准确率仅 50%，加上后飙升至 76%。

**训练超参数**（与 AutoMage 一致）：
- 学习率：$1 \times 10^{-4}$，constant schedule，warm-up ratio 0.03
- Batch size：128，sequence length：4096
- 1 epoch，16 块 A100 80G
- 优化器：paged AdamW 8-bit

#### 模块 2：Few-shot CoT Prompting

**做什么**：用检索到的 EDA 工具使用示例引导 ChipLlama 逐步推理——先做任务规划，再生成脚本。

**与 AutoMage2 的 Zero-shot CoT 的区别**：AutoMage2 只用一句 "Let's think step by step" 激发推理，没有示例。EDAid 使用 few-shot CoT——在 prompt 中插入多个 `(Q, C, A)` 三元组作为"教学案例"。

Few-shot CoT prompt 模板（来自论文 Figure 3）：
```text
### System: You are an AI assistant, capable of utilizing numerous
tools and functions. User will give you a task. Your job is to
generate a Python script to complete the task...
<<<APIs Document>>>

### User: <<<EDA Task 1 (示例)>>>
### Assistant: <<<Solution 1>>>

### User: <<<EDA Task 2 (示例)>>>
### Assistant: <<<Solution 2>>>

...

### User: <<<当前真实 EDA Task>>>
Let's first describe and explain what the task is asking. Then,
analyze how to complete the task step by step using the provided
tools and functions. Finally, generate the Python script according
to your analysis.
### Assistant:
```

**为什么出奇制胜**：Few-shot CoT 不仅提高单 Agent 准确率（Table 3），还是"分歧思维"的来源——不同的示例组合意味着不同的 prompt，引导 LLM 走向不同的推理路径。

#### 模块 3：Divergent-Thoughts Agents（R0 角色 × 3）

**做什么**：3 个 R0 Agent 各自基于不同的 few-shot CoT prompt，独立生成任务规划和 EDA 脚本候选。

**分歧的来源**：不是模型随机性（greedy decoding 下输出确定），而是 **不同的 few-shot 上下文**：
1. 从 Demo Database 中用 embedding 检索 Top-K 相关示例
2. 随机选取子集组成 Demo Group A / B / C
3. 每个 Agent 看到不同的"教学案例"→ 生成不同的 Planning Steps → 不同的 Script

论文 Figure 6 提供了真实案例：三个 Agent 对"实验不同时钟周期和 channel 值对 router 设计的影响"这个任务，一个正确生成、一个把 `macro_place_channel` 参数错放到 `global_route`、一个跳过 floorplan 直接 placement。

#### 模块 4：Decision-Making Agent（R1 角色）

**做什么**：从多个候选脚本中选出最可能正确的那一个。

**工作流程**：
```text
输入: O = {Script_A, Script_B, Script_C}

对每个 Script_i:
  1. 构造 prompt: "给定这个 EDA Task 和候选 Script，这个脚本能完成任务吗？"
  2. 输入 R1 Decision Agent (ChipLlama)
  3. Agent 分析脚本逻辑，判断是否正确
  4. 计算 LLM 输出 "yes" token 的概率 (vs "no" token)

选择 P(yes) 最高的 Script
```

**Yes-token Probability 计算**（论文未给编号公式，以下是对其算法行为的形式化）：

$$
P(\text{yes} \mid \text{task}, \text{script}) = \frac{\exp(\text{logit}_{\text{yes}})}{\exp(\text{logit}_{\text{yes}}) + \exp(\text{logit}_{\text{no}})}
$$

- $\text{logit}_{\text{yes}}$、$\text{logit}_{\text{no}}$：LLM 最后一层输出的 `yes` 和 `no` token 的原始 logits
- 本质上是一个二分类 softmax，表示模型认为"该脚本能完成任务"的概率

**KV Cache 优化**：所有候选的 system prompt 部分相同（API 文档 + 任务描述），只有 candidate script 不同。因此 system prompt 的 KV Cache 只计算一次，后续候选复用，大幅降低多候选推理开销。

**重要特性**：R1 的决策是 LLM-based verifier，不运行 EDA 工具。这意味着如果所有 R0 都错了，R1 也只能从错误中选——"垃圾进、垃圾出"。100% 准确率的前提是至少有一个 R0 生成了正确脚本。

### 4.3 模块职责矩阵

| 模块 | 输入 | 输出 | 用到的模型/工具 | 是否需训练 |
|------|------|------|----------------|:---:|
| Hybird Instruction Tuning | Math 80K + Code 100K + EDA 8K | ChipLlama 权重 | Llama3 + QLoRA | 是 |
| Demo Retrieval | EDA Task embedding | Top-K 相关 Demo | Embedding Model + 向量数据库 | 否 |
| Demo Random Grouping | Top-K Demos | 3 组不同的 Demo Group | 随机采样 | 否 |
| R0 Divergent-Thoughts | 3 组 Few-shot CoT Prompt | 3 份 (Planning + Script) | ChipLlama (greedy decode) | 否（推理） |
| R1 Decision Making | 3 份候选 + EDA Task | 最高 P(yes) 的脚本 | ChipLlama (logit 读取) | 否（推理） |
| EDA Execution | 选中脚本 | GDSII + PPA | OpenROAD / iEDA | 否 |

---

## 5. 关键公式

EDAid 论文的核心公式在 CoT prompting 的概率建模部分。

### 5.1 标准 Prompt 下的脚本生成概率（论文 Equation 1）

$$
p(A \mid Q, T) = \prod_{i=0}^{|A|} p_L(a_i \mid Q, T, A_{<i})
$$

- $A$：生成的 EDA 脚本
- $Q$：EDA 任务（自然语言描述）
- $T$：prompt（含 API 文档和系统指令）
- $p_L$：ChipLlama 模型的概率分布
- $a_i$：脚本的第 $i$ 个 token
- $A_{<i} = \{a_1, a_2, \dots, a_{i-1}\}$：已生成的前缀 token
- $|A|$：脚本长度（token 数）

**工程直觉**：这是标准的自回归语言模型前向公式。关键问题在于：没有任务规划步骤时，LLM 直接从 Q 跳到 A——在长链 EDA 工具调用场景中，这很容易在中间步骤出错。前几步对了但第五步参数传错，后面的 token 都是基于错误的上下文生成的。

### 5.2 Zero-shot CoT Prompt 下的脚本生成概率（论文 Equation 2）

$$
p(A \mid Q, T) = p(A \mid Q, T, C) \cdot p(C \mid Q, T)
$$

- $C$：任务规划步骤（task planning steps）
- $p(C \mid Q, T)$：先生成规划步骤的概率
- $p(A \mid Q, T, C)$：以规划步骤为条件生成脚本的概率

**工程直觉**：CoT 把一次性生成拆成两步——先想清楚怎么做（C），再动手写代码（A）。这就是"三思而后行"的数学表达。在 EDA 场景中，"想清楚"意味着确定 stage 顺序、每个 stage 的参数、参数从哪里来——这些都是在写代码之前必须确定的。

### 5.3 规划步骤生成概率（论文 Equation 3）

$$
p(C \mid Q, T) = \prod_{i=0}^{|C|} p_L(c_i \mid Q, T, C_{<i})
$$

- $c_i$：规划步骤的第 $i$ 个 token
- $C_{<i} = \{c_1, c_2, \dots, c_{i-1}\}$：已生成的前缀规划步骤
- $|C|$：规划步骤长度

### 5.4 以规划为条件的脚本生成概率（论文 Equation 4）

$$
p(A \mid Q, T, C) = \prod_{i=0}^{|A|} p_L(a_i \mid Q, T, C, A_{<i})
$$

- 与 Equation 1 对比：多了 $C$ 作为条件——脚本的每个 token 都在"已知规划"的前提下生成

**为什么这么设计**：标准 prompt（Equation 1）没有规划步骤，LLM 容易在不同的 stage 间混淆参数归属（把 CTS 的 `tns_end_percent` 放到 placement 阶段）。Equation 2-4 的关键在于：规划步骤 $C$ 确定后，参数归属已经明确，脚本生成时的出错概率大幅降低。

### 5.5 Few-shot CoT——分歧思维的来源

论文未给编号公式，以下是对其算法行为的形式化：

在 few-shot CoT 场景下，$T = (Q_i, C_i, A_i)_{i=1}^{N}$ 包含 $N$ 个 EDA 工具使用示例。不同的 Demo Group 排列产生不同的 $T$，从而：

$$
O_k = \arg\max_A p(A \mid Q, T_k), \quad k = 1, 2, 3
$$

- $T_1, T_2, T_3$：三个不同的 few-shot prompt（不同示例子集）
- $O_1, O_2, O_3$：三个 R0 Agent 的候选输出

由于 $T_k$ 不同，即使使用相同的 greedy decoding，三个 Agent 也会产生不同（甚至相互矛盾）的规划路径和脚本。这就是 "divergent thoughts" 的数学根源。

---

## 6. 训练与实验设置

### 6.1 是否需要训练

**需要指令微调。** ChipLlama 通过混合指令微调（Hybrid Instruction Tuning）在 Llama3 基础上训练。

| 数据集 | 规模 | 作用 |
|--------|------|------|
| MathInstruct（CoT 数学推理） | 80K | 强化逻辑推理能力，支撑 EDA 任务规划 |
| CodeInstruct（代码生成） | 100K | 提供编码技能，支撑 EDA 脚本生成 |
| EDAInstruct（EDA 工具使用） | 8K | 提供 EDA 领域知识，支撑跨平台泛化 |
| **总计** | **188K** | 三合一：EDA 知识 + 逻辑推理 + 代码生成 |

**为什么需要 MathInstruct**：这是 EDAid 与 AutoMage 的关键差异。AutoMage 只训练 EDA 工具使用，在跨平台（iEDA）上基本无法工作。ChipLlama 加入数学推理数据后，即使训练数据中只有 OpenROAD 的 API，也能泛化到 iEDA——因为"理解 EDA 流程的逻辑"比"记忆 API 参数"更重要。

训练方式与 AutoMage 相同：QLoRA（4-bit NF4 + Double Quantization），16 块 A100 80G，1 epoch。

### 6.2 实验设置

**Benchmark（两个）**：
- **ChatEDA-bench**：50 题，目标 API 来自 OpenROAD，三类任务（simple 30%、complex 30%、parameter tuner 40%）
- **iEDA-bench**：50 题，目标 API 来自 iEDA（中科院计算所开发的开源 EDA 平台），同样三类任务分布

**Baseline**：GPT-3.5、GPT-4（通过官方 API 的单 Agent 系统）、AutoMage/AutoMage2（ChatEDA 单 Agent）

**评估指标**：脚本正确率 accuracy——生成的 EDA 脚本能否成功自动化 EDA 流程

**消融设计**：
- Hybrid Instruction Tuning 有无（Table 2）
- Few-shot vs Zero-shot（Table 3）
- Single-Agent vs Multi-Agent（Table 4）

### 6.3 关键实验结果

**主结果（Table 1）——ChatEDA-bench 和 iEDA-bench 上的准确率**：

| 系统 | 驱动 LLM | ChatEDA-bench | iEDA-bench |
|------|---------|:---:|:---:|
| ChatEDA（单 Agent） | GPT-3.5 | 28% | 30% |
| ChatEDA（单 Agent） | GPT-4 | 62% | 70% |
| ChatEDA（单 Agent） | AutoMage-70B | 74% | — |
| ChatEDA（单 Agent） | AutoMage2-70B | 82% | — |
| EDAid（单 Agent） | ChipLlama-8B | 88% | 84% |
| **EDAid（多 Agent）** | **ChipLlama-70B** | **100%** | **100%** |

这张表说明三件事：

1. **ChipLlama 单 Agent 已经大幅超越前人**：ChipLlama-8B（88%）超过 AutoMage2-70B（82%），且 8B 能做到 70B 的事，说明 Llama3 基座 + 混合微调的效果远超 Llama2 + 纯 EDA 微调。
2. **多 Agent 在单 Agent 基础上进一步消除长尾错误**：ChipLlama-70B 单 Agent 是 94% / 96%，多 Agent 拉到 100% / 100%。6 个百分点的提升全部来自原来会出错的那几条——多 Agent 恰好为这些边缘 case 提供了正确的备选方案。
3. **跨平台泛化成立**：iEDA-bench 上的结果证明了混合指令微调策略的有效性——ChipLlama 在从未见过的 iEDA API 上也能达到 100%（多 Agent）。

**消融 1：Hybrid Instruction Tuning（Table 2）**：

| 基座 LLM | Hybrid Tuning | ChatEDA-bench | iEDA-bench |
|---------|:---:|:---:|:---:|
| Llama3-8B | 否 | 78% | 50% |
| Llama3-8B | 是 | 78% | **76%** |
| Llama3-70B | 否 | 88% | 74% |
| Llama3-70B | 是 | **94%** | **96%** |

关键发现：iEDA 跨平台准确率从 50% → 76%（8B）和 74% → 96%（70B），提升幅度远超 OpenROAD 上的提升。说明 Hybrid Tuning 的核心价值在于**跨工具泛化**——通过数学推理和代码能力，让模型学会"理解流程逻辑"而非"记忆 API 参数"。

**消融 2：Few-shot vs Zero-shot（Table 3）**：

| 驱动 LLM | ChatEDA-bench zero/few | iEDA-bench zero/few |
|---------|:---:|:---:|
| GPT-3.5 | 28% / 56% | 30% / 50% |
| GPT-4 | 62% / 82% | 70% / 84% |
| ChipLlama-8B | 74% / 78% | 64% / 76% |
| ChipLlama-70B | 90% / 94% | 90% / 96% |

所有模型在 few-shot 下均有提升。GPT-4 的提升最显著（+20%），说明通用 LLM 的 in-context learning 能力最强，但即使加上 few-shot，GPT-4 的 82% 仍不如 ChipLlama-70B 的 zero-shot 90%。

**消融 3：Single-Agent vs Multi-Agent（Table 4）**：

| 驱动 LLM | Single ChatEDA | Single iEDA | Multi ChatEDA | Multi iEDA |
|---------|:---:|:---:|:---:|:---:|
| ChipLlama-8B | 78% | 76% | **88%** | **84%** |
| ChipLlama-70B | 94% | 96% | **100%** | **100%** |

多 Agent 提升在 8B 上更显著（+10% / +8%），说明模型越弱，多 Agent 的冗余增益越大。70B 上的 100% 意味着 50 题 benchmark 被完美解决。

---

## 7. 创新点

### 创新点 1：从单 Agent 到多 Agent 的 EDA 流程自动化范式升级

原 ChatEDA 是单 Agent：一个 prompt → 一份规划 → 一份脚本 → 中间一步出错 → 整条流程报废。EDAid 引入 3 个 R0 独立生成候选 + 1 个 R1 裁决，本质上是 **Self-Consistency 策略在 EDA 领域的具体化**。

与通用 CoT-SC 的区别：EDAid 的"分歧"不是来自采样随机性（temperature sampling），而是来自**不同的 few-shot 上下文**（不同 Demo Group）。这更可控、更可解释——每个 Agent 的"思考路径"由不同的前置示例引导。

### 创新点 2：Hybrid Instruction Tuning（三数据混合微调）

ChipLlama 不只是微调 EDA 数据（那样会丢失通用推理能力），而是混合三类数据：EDAInstruct（领域知识）+ CodeInstruct（代码生成）+ MathInstruct（数学推理）。实验证明这是跨平台泛化的关键——不加 MathInstruct 时 iEDA 准确率仅 50%，加上后飙升至 76%。

### 创新点 3：Demo Retrieval + Random Grouping 实现分歧

不是简单地把相同的 few-shot prompt 给多个 Agent（那样输出会趋同），而是从示例库中检索相关案例后随机分组。利用 LLM 对不同 prompt 的敏感性自然产生分歧——每个 Agent 看到不同的"教学案例"，走向不同的推理路径。

### 创新点 4：Yes-token Probability 作为决策信号

不需要外部评分器或启发式规则——直接用 R1 输出 `yes` token 的 logit 概率作为置信度。好处是多方面的：无需额外训练分类器；概率值反映模型对正确性的"信念强度"；KV Cache 共享降低多候选推理开销。

**代价**：只适用于开源模型（需要读取 logits）。GPT-4 / Claude 等闭源模型不暴露 logit 信息，无法使用这种裁决机制。

### 创新点 5：跨平台 EDA Benchmark（iEDA-bench）

在 ChatEDA-bench（OpenROAD）之外构建了 iEDA-bench（iEDA），用两套不同的 EDA 工具 API 评估泛化能力。这是首次在 EDA 流程自动化领域引入跨平台评测。

---

## 8. EDA 缩写表

| 缩写 | 全称 | 一句话解释 |
|------|------|-----------|
| EDAid | — | 论文提出的多 Agent 协作系统名称 |
| LLM | Large Language Model | 大语言模型 |
| RTL | Register Transfer Level | 寄存器传输级，Verilog/VHDL 描述电路行为 |
| GDSII | Graphic Data System Version II | 芯片版图标准格式，最终发给代工厂 |
| PPA | Power, Performance, Area | 功耗、性能、面积，芯片设计三大优化目标 |
| CoT | Chain of Thought | 思维链，LLM 逐步推理的技术 |
| CoT-SC | CoT with Self-Consistency | 自一致性思维链，生成多个推理路径后投票 |
| KV Cache | Key-Value Cache | Transformer 推理时的键值缓存，复用避免重复计算 |
| ICL | In-Context Learning | 上下文学习，通过 prompt 中的示例引导模型 |
| QLoRA | Quantized LoRA | 量化低秩适配，4-bit 量化 + LoRA |
| NF4 | 4-bit NormalFloat | 信息论最优的 4 位量化数据类型 |
| CTS | Clock Tree Synthesis | 时钟树综合（阶段⑨） |
| WNS | Worst Negative Slack | 最差负时序裕量 |
| TNS | Total Negative Slack | 总负时序裕量 |
| DSE | Design Space Exploration | 设计空间探索，参数优化搜索 |
| PDK | Process Design Kit | 工艺设计套件 |
| iEDA | intelligent EDA | 开源 EDA 平台，中科院计算所开发 |
| ORFS | OpenROAD-flow-scripts | OpenROAD 的流程脚本框架 |

---

## 9. 与芯片流程的关系

### 9.1 在全流程中的位置

EDAid 在芯片流程中的位置与 ChatEDA 完全一致——覆盖 ③→⑦→⑧→⑨→⑩ 的物理实现流水线，加上 ⑬ 的指标读取。

**与 ChatEDA 的核心区别不在"覆盖哪些阶段"，而在"同一阶段的可靠性"。**

单 Agent ChatEDA 的问题：长链工具调用（7+ 步）中，第 5 步可能"忘记"第 2 步的上下文，导致参数归属错误。EDAid 通过多 Agent 冗余消除这类错误——即使某个 Agent 在中间步骤犯错，R1 裁决机制能从其他 Agent 的正确方案中选出答案。

### 9.2 "100% 准确率"和"能做成芯片"之间隔着什么

EDAid 的 100% 是指在 50 道 script-generation benchmark 题上全部正确。但这不等于芯片能成功流片：

1. **LLM verifier 不等于 execution verifier**：R1 是基于语言模型概率选择候选，没有解析真实 EDA 错误日志。有可能 R1 认为"正确"的脚本在实际执行中失败。
2. **Benchmark 有限**：50 道题覆盖了基础场景，但真实工程中的需求千变万化。100% 大概率不成立。
3. **物理验证缺失**：与 ChatEDA 一样，没有 DRC/LVS/后仿真/Signoff STA。生成的 GDSII 未经制造可行性验证。
4. **iEDA-bench 未公开**：iEDA-bench 的完整 prompt、API 文档、实现均不在开源仓库中，无法独立验证跨平台结果。

---

## 10. 讨论与局限

### 10.1 论文自述的局限

1. **推理延迟增加**：多 Agent 需要 4 次 LLM 推理（3 R0 + 1 R1），相比单 Agent 的 1 次，"introduces inference latency"。虽然有 KV Cache 共享，但仍是 3-4 倍计算开销。
2. **依赖开源模型**：Decision-Making 需要读取 logits/概率，闭源模型（GPT-4、Claude）不暴露这些信息。因此 EDAid 的裁决机制只能用开源模型。
3. **Agent 数量饱和**：论文在 Appendix B 中指出，R0 数量少于 3 时性能随数量增加而提升，但达到 3 个后趋于饱和（"performance tends to saturate"），更多 Agent 不会带来显著提升。

### 10.2 代码/复现层面的问题

从复现详解文档提炼的关键问题：

1. **多 Agent 核心实现未公开**：ChipLlama 权重、训练代码、完整数据、demo retrieval、R0 候选生成、R1 yes-token probability 评分、KV Cache 复用实现——全部不在开源仓库中。
2. **iEDA-bench 缺失**：iEDA 的 API 文档、benchmark 任务、评估代码均未公开，跨平台实验无法复现。
3. **仓库仍是 ChatEDA 初版**：当前代码仓库与初版 ChatEDA 共用，没有任何 EDAid 的多 Agent 实现代码。
4. **wrapper 缺陷继承**：EDAid 使用的仍是同一套存在已知缺陷的 OpenROAD wrapper（`global_route` 不返回 status、`get_metric` 键映射错误等）。

### 10.3 本资料包的批判性分析

1. **"100%"的真实含义**：50 道题全对，确实是一项工程成就。但从 94%（单 Agent）到 100%（多 Agent），提升的 6 个百分点本质上是靠"用计算换正确性"——3 个 Agent 各出一份方案，总有一个是对的（概率上）。这相当于花 3-4 倍计算成本消除 6% 的剩余错误。是否"划算"取决于场景——在芯片设计中，消除每 1% 的错误都可能值得。
2. **与 MAGE 多 Agent 的范式差异**：MAGE 的多 Agent 是功能分工（一个写代码、一个仿真、一个修 bug），EDAid 的多 Agent 是同任务冗余+投票。两种范式互补——前者适合"任务天然可分"的场景，后者适合"单任务容易出错"的场景。
3. **决策 Agent 的脆弱性**：如果所有 R0 都在同一个坑里跌倒（例如都对某个冷门 API 参数不熟悉），R1 也只能从错误中选。100% 建立在 ChipLlama-70B 单 Agent 已达 94% 的强基线上。换到更弱的模型，多 Agent 可能把错误放大而不是缩小。
4. **跨平台泛化的边界**：iEDA-bench 虽然证明了泛化能力，但 OpenROAD 和 iEDA 都是开源平台，API 风格相似。泛化到 Synopsys ICC2 或 Cadence Innovus（商业工具，接口完全不同）的效果未知。

---

## 11. 复现信息

| 项目 | 内容 |
|------|------|
| 论文页 | https://aclanthology.org/2025.naacl-long.83.pdf |
| 代码 | https://github.com/wuhy68/ChatEDAv1 · commit `02bb522a98f7`（已审计） |
| 数据集 | 与 ChatEDA 共用 50 条训练样例和 50 条 benchmark；完整 188K 混合指令数据未公开 |
| 本地状态 | 已静态审计，未复现。缺 ChipLlama 权重、多 Agent 核心实现、iEDA-bench |
| 复现等级 | R0（论文方法可完整梳理）；代码级复现不可行（核心实现未公开） |
| 主要门槛 | ChipLlama 模型权重和训练数据未公开；多 Agent 协作代码未公开；iEDA-bench 未公开；训练需 16 块 A100 80G；OpenROAD wrapper 有已知缺陷需修复 |

---

## 12. 一分钟复述版

1. **动机**：单 Agent ChatEDA 在长链 EDA 工具调用中容易在中间步骤出错——一个参数错位导致整条流程失败。
2. **核心思想**：不让一个 Agent 孤军奋战。3 个 R0 Agent 各自基于不同的 few-shot 上下文生成脚本候选，1 个 R1 Decision Agent 按 yes-token 概率选出最佳方案。
3. **分歧来源**：从 Demo Database 中检索相关 EDA 工具使用示例 → 随机分组 → 不同 Agent 看到不同的"教学案例" → 自然产生分歧思维。
4. **ChipLlama 模型**：Llama3 + MathInstruct 80K + CodeInstruct 100K + EDAInstruct 8K 混合微调，强化 EDA 流程推理和跨平台泛化（不只是记忆 API 参数）。
5. **决策机制**：R1 读取 `yes` vs `no` token 的 logits，用 softmax 转成概率，选最高者。关键是 KV Cache 共享——system prompt 只算一次。
6. **关键结果**：ChipLlama-70B + 多 Agent = ChatEDA-bench 100% + iEDA-bench 100%。单 Agent 基线的 94% → 多 Agent 100%，消除最后 6% 的长尾错误。
7. **Hybrid Tuning 的价值**：不加数学推理数据时，iEDA 跨平台准确率仅 50%。加上后 8B 模型达到 76%，70B 达到 96%。
8. **阶段覆盖**：与 ChatEDA 相同——③⑦⑧⑨⑩ 物理实现流水线 + ⑬ 指标读取。改进在可靠性而非覆盖范围。
9. **最大局限**：多 Agent 核心实现未开源；R1 是 LLM verifier 而非 execution verifier；100% 是 50 题 benchmark 上的结果；推理成本 3-4 倍于单 Agent；只适用开源模型（需要 logits）。
10. **与 ChatEDA 的本质区别**：ChatEDA = 一个聪明的大脑；EDAid = 三个大脑各自思考 + 一个裁判做最终决定。前者快但可能犯错，后者慢但更可靠。

---

## 13. 单 Agent vs 多 Agent 的架构演进

### 13.1 演进全景图

```text
┌─────────────────────────────────────────────────────────────────┐
│                 ChatEDA → EDAid 架构演进                          │
│                                                                  │
│  【初版 ChatEDA · IEEE TCAD 2024】                                │
│                                                                  │
│   用户需求 ──→ AutoMage (单Agent) ──→ 一份脚本 ──→ OpenROAD      │
│                Llama2 + QLoRA                                    │
│                ~1500 EDA 指令微调                                │
│                                                                  │
│   问题：一步错，全盘输                                             │
│                                                                  │
│   ═══════════════════════════════════════════════════════════    │
│                                                                  │
│  【EDAid · NAACL 2025】                                           │
│                                                                  │
│                        ┌─→ R0-A (Demo Group A) ─→ Script A ─┐   │
│   用户需求 ─→ Demo     ─┼─→ R0-B (Demo Group B) ─→ Script B ─┼→ R1 → 执行  │
│              Retrieval  └─→ R0-C (Demo Group C) ─→ Script C ─┘   │
│                                                                  │
│   策略：三分歧 + 一裁决 → 消除单点故障                               │
└─────────────────────────────────────────────────────────────────┘
```

### 13.2 为什么需要从单 Agent 升级

初版 ChatEDA 的失败模式是**单轨生成**（论文 Figure 6 展示了真实失败案例）：

```text
一个 prompt → 一个规划 → 一份脚本
→ 中间任何一个 API 或参数错误 → 整条 EDA 流失败
```

两种典型错误：
- **跳过中间步骤**：placement 之前没做 floorplan（stage 依赖违反）
- **参数阶段错位**：把 CTS 专用的 `tns_end_percent` 参数用在 placement 阶段

EDA 后端流程特别容易发生这类错误，因为：stage 必须按依赖顺序执行、同名概念可能属于不同 stage、参数众多且数值范围不同、LLM 在生成第 5 步时可能已经"忘记"第 2 步的上下文。

### 13.3 七维对比

| 维度 | ChatEDA (初版) | EDAid (多 Agent) |
|------|---------------|-----------------|
| **Agent 数量** | 1（AutoMage） | 4（3 R0 + 1 R1） |
| **基座 LLM** | Llama2（7B/13B/34B/70B） | Llama3（8B / 70B） |
| **训练数据** | ~1.5K EDA 指令（AutoMage）<br>+ ~110K 代码指令（AutoMage2） | 80K Math + 100K Code + 8K EDA<br>= 188K 混合指令 |
| **推理策略** | Beam Search（beam width=4）<br>AutoMage2 加 Zero-shot CoT | Few-shot CoT + Multi-Agent<br>（不同 Demo Group 引导分歧） |
| **决策机制** | 单次生成（自回归解码） | 多候选投票（yes-token logit probability） |
| **跨平台** | 仅 OpenROAD（ChatEDA-bench） | OpenROAD + iEDA<br>（ChatEDA-bench + iEDA-bench） |
| **最高准确率** | 82% Grade A（AutoMage2-70B） | **100%**（ChipLlama-70B + Multi-Agent） |

### 13.4 基座模型和训练策略的升级

基座从 Llama2 换到 Llama3 是最关键的单项升级。Llama3 的通用推理和代码能力显著强于 Llama2，这体现在：ChipLlama-8B 单 Agent（78%）已经超过 AutoMage2-70B（82%）。8B 打赢 70B，纯粹是基座能力的跃升。

训练策略从"EDA 专精"变为"三能力融合"：

```text
AutoMage2: EDA 工具使用 + 代码能力（~111.5K）
ChipLlama: 数学推理 + 代码能力 + EDA 知识（188K）
              ↑ 新增维度
```

新增的数学推理数据（80K MathInstruct）是跨平台泛化的关键。不加时 iEDA 准确率仅 50%（8B）和 74%（70B），加上后跃升至 76% 和 96%。这证明了：让模型理解"EDA 流程的逻辑"比让它记忆"特定 API 的参数"更重要。

### 13.5 推理策略的升级

```text
ChatEDA (AutoMage2):
  需求 → Zero-shot CoT ("Let's think step by step") → 脚本

EDAid (ChipLlama):
  需求 → Demo Retrieval → Random Grouping
  → 3 组 Few-shot CoT (各有不同示例)
  → 3 份规划/脚本 → R1 yes-token 裁决 → 最优脚本
```

关键差异：Zero-shot CoT 只有一句引导，Few-shot CoT 有多个"教学案例"引导，且不同的案例产生不同的推理路径。分歧不是随机采样造成的（非确定性），而是不同的 in-context 学习路径造成的（确定性但不同）。

### 13.6 为什么 100% 在 70B 上达成而在 8B 上未达成

ChipLlama-8B + Multi-Agent 是 88%，而 70B 是 100%。差距在于：

- **R0 候选质量**：8B 单 Agent 是 78%，意味着有 22% 的任务 8B 生成错误方案。如果所有 R0 都在某个任务上犯错，R1 无法拯救。70B 单 Agent 是 94%，只有 6% 的任务单个 Agent 会错——这些恰好被多 Agent 的"另一个视角"覆盖了。
- **R1 裁决质量**：70B 的 R1 比 8B 的 R1 更擅长判断"哪个脚本更可能正确"。如果 R1 选错了，即使 R0 中有正确候选也无济于事。

本质上，Multi-Agent 的增益取决于单 Agent 的基线——基线越高（70B 的 94%），冗余越能覆盖剩余的 corner case；基线越低（8B 的 78%），三个 Agent 可能同时在某些任务类型上系统性犯错。

### 13.7 代价：从快但可能出错到慢但更可靠

Multi-Agent 的推理成本是单 Agent 的 3-4 倍（考虑 KV Cache 共享后）。在实时交互场景中，这可能构成瓶颈。但在芯片设计中，一次流片的成本是数百万美元——花几秒钟多跑几次 LLM 推理来避免脚本错误，显然是值得的。EDAid 代表了"用计算换可靠性"的方向：在确定性要求极高的 EDA 场景中，冗余设计优于单点优化。
