# RTLLM 论文深度讲解

> **RTLLM: An Open-Source Benchmark for Design RTL Generation with Large Language Model**
> Yao Lu, Shang Liu, Qijun Zhang, Zhiyao Xie
> Hong Kong University of Science and Technology (HKUST)
> ASP-DAC 2024 · arXiv: 2308.05345 v3 (Nov 11, 2023)
> 原文：[2308.05345_RTLLM.pdf](./2308.05345_RTLLM.pdf)
> 代码：<https://github.com/hkust-zhiyao/RTLLM>

---

## 1. 一句话定位

**RTLLM 不是一个需要训练的模型，而是一个开源的 RTL 生成评测集（benchmark）**——它定义了 30 个数字设计题目，每个题目提供自然语言设计规格、配套 testbench、人工参考 RTL 三件套，构建了 Syntax（语法）→ Functionality（功能）→ Quality（PPA 质量）三级递进式评测体系。实验表明 GPT-4 + self-planning 达到 90% 语法正确率和 19/30 功能通过率。

这句话里的技术承重点：

1. **Benchmark 而非模型** — RTLLM 本身不训练，不生成代码。任何 LLM 都可以接入框架，由自动化脚本完成综合、仿真、PPA 提取全流程评测。
2. **三级递进评测** — 语法不对无法综合，不综合无法仿真，不仿真无法取 PPA。每级有严格的前置依赖，防止虚假分数的出现。
3. **Self-planning 提示方法** — 把 RTL 生成拆为「先写计划 + 语法注意事项」→「再写代码」两步，无需额外数据或训练。GPT-3.5 加上 self-planning 后功能通过率从 10/30 升至 14/30。
4. **人工参考设计** — 每道题都有 hand-crafted 的正确 RTL，用于 PPA 对比，使「生成代码好不好」有了定量参考系。

---

## 2. EDA 阶段映射（①-⑰）

参照 [芯片流程.md](../芯片流程.md) 的 17 阶段标准编号：

| 阶段 | 覆盖 | 说明 |
|------|:---:|------|
| **① RTL 设计** | ✅ **核心** | LLM 根据自然语言规格 L 生成 Verilog RTL V |
| **② RTL 功能仿真** | ✅ | 用 RTLLM 配套 testbench + Synopsys VCS 验证功能 |
| **③ 逻辑综合** | ✅ | 用 Synopsys Design Compiler 检查语法 + 获取 PPA 数据 |
| ④ 门级仿真 | ❌ | 综合后不做带 SDF 反标的门级仿真 |
| **⑤ STA（静态时序分析）** | ✅ 辅助 | 逻辑综合时附带分析 WNS（最差负 slack），不是独立 STA 流程 |
| ⑥ 形式验证 | ❌ | 不检查 RTL 与网表的逻辑等价性 |
| ⑦ 布局规划 (Floorplan) | ❌ | — |
| ⑧ 标准单元摆放 (Placement) | ❌ | — |
| ⑨ 时钟树综合 (CTS) | ❌ | — |
| ⑩ 布线 (Routing) | ❌ | — |
| ⑪ 后仿真 | ❌ | — |
| ⑫ 物理验证 (DRC+LVS) | ❌ | — |
| ⑬ 签核 (Signoff) | ❌ | — |
| ⑭ 流片 | ❌ | — |
| ⑮ 制造 | ❌ | — |
| ⑯ 封装 + 测试 | ❌ | — |
| ⑰ 芯片到手 | ❌ | — |

**覆盖率：3/17。** RTLLM 止于逻辑综合阶段的 PPA 报告。它不涉及物理设计（⑦~⑩）、不做门级仿真与时序验证（④⑤）、不做形式验证（⑥）。

> 关键边界：论文将时钟频率设得极高（确保所有设计出现负 slack），使 WNS 成为一个可比较的时序指标。这**不是 signoff 级别的 STA**——只是为不同 LLM 的生成结果提供一个相对时序排序。

---

## 3. 输入 / 输出

### 3.1 给 LLM 的输入

每道题的输入是一个自然语言设计规格文件 `design_description.txt`。以下以 `multi_16bit`（16 位乘法器）为例：

```text
Implement the design of unsigned 16bit multiplier based on
shifting and adding operation.

module multi_16bit(
    input clk,
    input rst_n,
    input start,
    input [15:0] ain,
    input [15:0] bin,
    output reg [31:0] yout,
    output reg done
);
```

规格要求：模块名、I/O 信号名与位宽必须与 testbench 中的实例化完全一致——否则自动化评测脚本无法编译和仿真。

### 3.2 给评测系统的输入

- **生成的 RTL 文件**（LLM 的输出 V）
- **配套 testbench** `testbench.v`（每题自带，定义输入激励与期望输出）
- **人工参考 RTL** `designer_RTL.v`（用于 PPA 对比基线）
- **综合脚本**（调用 Synopsys Design Compiler，选项 `compile_ultra`）
- **仿真脚本**（调用 Synopsys VCS）

### 3.3 输出

三级评测结果，逐级递进：

```
    Level 3 — Quality：area / power / WNS（与人工 reference 的比值）
              ▲ 只有功能正确的设计才参与 PPA 比较
    Level 2 — Functionality：通过 testbench（是/否）
              ▲ 只有语法正确的设计才能被仿真工具编译
    Level 1 — Syntax：Design Compiler 综合通过（是/否）
```

每级之间有严格的前置依赖：语法不对→无法仿真→PPA 数字无意义。

### 3.4 题目规模与分类

RTLLM v1.0 含 30 个设计，11 个算术单元 + 19 个逻辑单元。参考 RTL 行数 17~518 行，综合网表 cell 数 6~2,435 个。

| 类型 | 设计数 | 示例 |
|------|:---:|------|
| Arithmetic | 11 | accu, adder_8bit/16bit/32bit/64bit, multi_8bit/16bit, multi_pipe_4bit/8bit, div_8bit/16bit |
| Logic | 19 | JC_counter, right_shifter, mux, counter_12, freq_div, signal_generator, serial2parallel, parallel2serial, pulse_detect, edge_detect, FSM, width_8to16, traffic_light, calendar, RAM, asyn_fifo, ALU, PE, risc_cpu |

其中 risc_cpu（518 行 RTL，407 cells）和 ALU（111 行 RTL，2,435 cells）是最复杂的两道题。

---

## 4. Benchmark 构建方法

### 4.1 设计收集原则

RTLLM 的 30 个设计来源于常见数字电路教材与实践中的经典模块，覆盖了从简单组合逻辑（8 位加法器，26 行 RTL）到复杂时序系统（简化 RISC CPU，518 行 RTL）的连续难度梯度。

同一功能类型提供多种实现要求以确保评测粒度：

- **加法器系列**：基本版（adder_8bit）、1 位全加器实现（adder_16bit）、超前进位（adder_32bit）、4 级流水线脉动进位（adder_64bit）
- **乘法器系列**：Booth-4 乘法器（multi_8bit）、移位相加乘法器（multi_16bit）、流水线乘法器（multi_pipe_4bit/8bit）
- **除法器系列**：Radix-2 除法器（div_8bit）、减法迭代除法器（div_16bit）

### 4.2 每个设计的「三件套」

对于每个设计，RTLLM 提供三个独立文件：

- **design_description.txt（记为 L）**：自然语言功能描述，要求人类设计师读后能写出正确 RTL。显式给定模块名和所有 I/O 信号的名称与位宽，确保 testbench 可以自动实例化。
- **testbench.v（记为 T）**：包含多组测试用例，每组有明确的输入激励值与期望输出值。testbench 的采样策略是覆盖典型场景而非穷举——通过 testbench 不代表功能 100% 正确。
- **designer_RTL.v（记为 V_H）**：人类工程师手工编写的参考 Verilog 设计。所有参考设计均已通过配套 testbench 验证。V_H 的 PPA 数值作为生成设计 V 的对比基线。

### 4.3 评测流程自动化

整个评测流程分为三个阶段，用户只需提供 LLM 接口：

```text
Stage 1: RTL 生成
  L → [LLM F] → V = F(L)
  若使用 self-planning: L → [LLM] → plan P, 然后 (L, P) → [LLM] → V

Stage 2: 功能验证
  V + T → [Synopsys VCS] → pass/fail

Stage 3: 质量评估
  V → [Design Compiler] → gate-level netlist → area/power/WNS
  与 V_H 的 PPA 数值对比 → quality ratio
```

### 4.4 与先前数据集的规模对比

| 工作 | 设计数 | RTL 行数 {中位数, 均值, 最大值, 总和} | 网表 cell 数 {中位数, 均值, 最大值, 总和} |
|------|:---:|------|------|
| Thakur et al. [5] | 17 | {16, 19, 48, 0.3K} | {9.5, 45, 335, 0.7K} |
| Chip-Chat [6] | 8 | {42, 42, 72, 0.3K} | {37, 44, 110, 0.4K} |
| Chip-GPT [7] | 8 | 未公开 | 未公开 |
| **RTLLM** | **30** | **{52, 86, 518, 2.5K}** | **{121, 408, 2,435, 11.8K}** |

RTLLM 在题数、设计规模和复杂度上均明显超过先前工作。

---

## 5. 关键公式

### 5.1 设计生成问题形式化

给定自然语言描述 L，目标是通过 ML 模型 F 生成设计 RTL V：

$$
V = F(L)
$$

- $L$：自然语言设计规格
- $F$：基于 LLM 的生成模型
- $V$：生成的 RTL 代码

引入 prompt 工程技术 P 和可选的人工修正 H 后，完整表达式为：

$$
V = H(F(P(L)))
$$

- $P(\cdot)$：prompt 工程变换函数（如 self-planning 的两阶段展开）
- $H(\cdot)$：人工修正函数（论文实验中不使用，即 H 为恒等映射）

### 5.2 pass@k 无偏估计

生成 k 次中有 c 次通过时，pass@k 的无偏估计为：

$$
\text{pass@k} = 1 - \frac{\binom{n-c}{k}}{\binom{n}{k}}
$$

- $n$：总生成次数（论文设置 n=5）
- $c$：n 次中通过目标检查的次数
- $k$：选取的尝试次数（k=1 即一次生成就成功的概率，k=5 即五次中有至少一次成功的概率）

**工程直觉**：直接算 c/k 会低估 LLM 的真实成功率——"生成 5 次过了 1 次"意味着"给我 5 次机会我能做对这道题"的概率远高于 20%。如果一次尝试就成功的概率是 p，那 5 次中至少成功一次的概率是 1-(1-p)^5，而不是 1/5。pass@k 的公式是无偏估计，源自 OpenAI Codex 论文，是工业界评测代码生成能力的标准做法。

**为什么这么设计**：LLM 生成代码有随机性（temperature sampling），同一道题不同轮次可能拿到截然不同的结果。pass@k 捕捉的是「给 k 次尝试机会的通过概率」，比单次通过率更能反映模型的真实潜力。对于 RTL 生成，这个指标尤其合理——工程师可以通过多轮生成来筛选结果。

### 5.3 论文的 pass@k 实际使用方式

论文的 setting 是：每题生成 n=5 次，功能正确性只要 5 次中有至少 1 次通过 testbench 即算该题通过。这等价于 pass@5 的判定逻辑（不是严格使用上述公式计算概率值，而是直接报「c=0 vs c>=1」的二元结果）。

---

## 6. 评测协议与打分

### 6.1 三级评测协议

RTLLM 定义了三个逐级递进的评测目标，每个目标的通过条件是下一目标的前置条件：

**Level 1 — Syntax Goal（语法目标）**

生成的 RTL V 必须能被逻辑综合工具正确综合为门级网表（无语法错误）。统计 5 次生成中语法正确的次数。论文报告为百分比形式（如 GPT-3.5: 55%）。

**Level 2 — Functionality Goal（功能目标）**

从语法正确的候选中，任意一个通过配套 testbench 中的所有测试用例即算该题通过。统计所有 30 题中的通过题数。注意 testbench 只采样了有限测试用例，通过 testbench 不代表功能数学上 100% 正确。

**Level 3 — Quality Goal（质量目标）**

对功能正确的设计，用 Design Compiler 综合并提取 area/power/WNS，与人工参考设计 V_H 的 PPA 对比。为防止"捷径"（如故意产生小面积但功能错误的设计），只有两级均通过的候选才参与 quality 比较。

论文将所有设计的时钟频率设得极高，确保**所有设计出现负 slack**，使 WNS 变成一个可比较的时序指标（不同设计间 slack 范围可对齐）。

### 6.2 核心结果：语法与功能

| 方法 | Syntax rate | Functionality (pass@5) |
|------|:---:|:---:|
| GPT-3.5 | 55% | 10/30 |
| GPT-4 | 81% | 15/30 |
| Thakur et al. (CodeGen-16B FT) | 40% | 5/30 |
| StarCoder (15B) | 27% | 5/30 |
| GPT-3.5 + self-planning | 73% | 14/30 |
| GPT-4 + self-planning | **90%** | **19/30** |

总体排名：GPT-4 + self-planning > GPT-4 > GPT-3.5 + self-planning > GPT-3.5 > Thakur et al. >= StarCoder。

这张表说明：self-planning 对 GPT-3.5 的提升（55%→73% syntax, 10/30→14/30 func）使其接近 GPT-4 的水平（81% syntax, 15/30 func），且两个学术模型（Thakur et al.、StarCoder）与商业 LLM 存在显著差距。

### 6.3 PPA 质量对比

下表对语法与功能均正确的设计，比较 area/power/WNS。只统计每个 LLM 获得"最优 PPA"的设计数（绿标），不直接做 PPA 求和（因为不同设计面积/功耗跨度巨大，直接求和会导致大设计主导排名）。

| 方法 | Best Area 数 | Best Power 数 | Best Timing 数 |
|------|:---:|:---:|:---:|
| Designer Reference (V_H) | 3 | 7 | 5 |
| GPT-3.5 | 2 | 2 | 5 |
| **GPT-4** | **8** | **5** | **6** |
| Thakur et al. | 2 | 1 | 2 |
| GPT-3.5 + self-planning | 5 | 7 | 5 |

GPT-4 在 best area 上以 8 个设计领先（接近其他所有方法之和），GPT-3.5 + self-planning 在 best power 上与 designer reference 持平（7 个）。

论文作者明确提醒：由于面积/功耗/时序之间存在强 trade-off，这种简单计数各维度最优的方法是一个**直接但不够严格的比较**——一个在面积上最优的设计可能在时序上较差，单独计数的求和不能反映多目标 Pareto 前沿。

### 6.4 实验设置细节

- **生成策略**：每题对 LLM 查询 5 次（5 个并行 session，完全相同输入），收集全部 5 个输出。不使用人工修正，不进行第二轮重试。
- **逻辑综合**：Synopsys Design Compiler，`compile_ultra` 选项。
- **功能仿真**：Synopsys VCS。
- **频率设置**：所有设计统一设极高时钟频率，确保出现负 slack 以便时序比较。

---

## 7. 创新点

### 创新点 1：首个完整的三级 RTL 评测体系

在 RTLLM 之前，RTL 生成评测最多做到「功能对不对」（如 VerilogEval 的仿真通过率）。RTLLM 是第一个引入 **PPA 质量对比**的评测集——不仅问"能跑吗"，还问"跑得好不好"。

这对实际工程的意义：语法对+功能对但面积是 reference 的 5 倍 = 实际产品中无法使用。PPA 评价需要综合工具（Design Compiler）+ 工艺库，引入了真实物理约束。

### 创新点 2：Self-planning 两阶段提示

方法极其简单但效果显著——证明对 LLM 而言，「先规划后执行」比「直接生成代码」有效得多。

```text
Round 1 (Plan):
  Input: L + "先分析需求，给出实现计划，列出需避免的语法错误"
  Output: 自然语言计划 P + 语法注意事项

Round 2 (Generate):
  Input: L + P + "根据以上计划生成可综合 Verilog RTL"
  Output: 可综合的 RTL V
```

**为什么有效**：
- LLM 在「先想后写」时更不容易遗漏边界条件和状态转换
- 计划阶段不受 Verilog 语法约束（不因语法细节分心），可以专注逻辑设计
- 语法注意事项直接反馈回第二轮，避免了常见低级错误（如在 always 块内声明变量）

**关键区别**：Self-planning 不等于迭代修复。论文**没有**把 VCS 的错误信息回灌给 LLM 做第二轮修正——它只是一次性的思维链分解，不是基于工具反馈的闭环。

### 创新点 3：开源可复现的 benchmark 设计

每道题自带 testbench。语法+功能评测理论上可用开源工具（Icarus Verilog + Yosys）替代商业工具（VCS + Design Compiler）。PPA 评测仍依赖商业工具，但至少前两级门槛降低了。

---

## 8. EDA 缩写表

| 缩写 | 全称 | 一句话解释 |
|------|------|------|
| **PPA** | Power, Performance, Area | 芯片设计三大核心指标：功耗、性能（时序）、面积 |
| **WNS** | Worst Negative Slack | 最差负余量——所有路径中最大的负 slack（负值越大越差），STA 的核心指标 |
| **RTL** | Register-Transfer Level | 寄存器传输级——用 always @(posedge clk) 风格的硬件描述 |
| **VCS** | Verilog Compiled Simulator | Synopsys 的 Verilog 仿真器，商业工具 |
| **DC** | Design Compiler | Synopsys 的逻辑综合工具 |
| **Self-Planning** | — | 两阶段提示：先让 LLM 写计划再写代码，不依赖工具反馈 |
| **testbench** | — | 测试平台——给 DUT 产生激励并检查输出的 Verilog 代码 |
| **reference RTL** | — | 人类工程师手工编写、已通过验证的「标准答案」RTL |
| **LLM** | Large Language Model | 大语言模型，如 GPT-3.5/GPT-4 |
| **pass@k** | — | 生成 k 次至少 1 次成功的概率，用无偏估计公式计算 |
| **FSM** | Finite State Machine | 有限状态机 |
| **FIFO** | First In, First Out | 先入先出队列 |
| **ALU** | Arithmetic Logic Unit | 算术逻辑单元 |
| **PE** | Processing Element | 处理单元 |
| **RISC** | Reduced Instruction Set Computer | 精简指令集计算机 |
| **RAM** | Random Access Memory | 随机存取存储器 |
| **HDL** | Hardware Description Language | 硬件描述语言，包括 Verilog/VHDL/Chisel 等 |

---

## 9. 与芯片流程的关系

### 9.1 在全流程中的位置

RTLLM 作用于芯片流程的**最前端**——阶段 ① RTL 设计：

```text
芯片流程                 RTLLM 的角色
───────────────────────────────────────────────
① RTL 设计             ← LLM 在此生成 Verilog，RTLLM 评测质量
② RTL 功能仿真          ← testbench 验证功能正确性
③ 逻辑综合              ← Design Compiler 检查语法 + 提取 PPA
④~⑥ 门级仿真/STA/形式验证  ← RTLLM 不涉及
⑦~⑩ 物理设计            ← RTLLM 不涉及
⑪~⑰ 后仿真到流片        ← RTLLM 完全不涉及
```

RTLLM 回答的核心问题是：**「LLM 生成的 RTL 代码，在真实芯片流程中能走多远？」**

- 语法错 → 连综合都进不去，止于 ①
- 功能错 → 能综合但仿真不过，止于 ②
- 功能对但 PPA 差 → 能用但不优，实际产品竞争力不足
- 功能对 + PPA 好 → 接近人工设计水平

### 9.2 「仿真通过」和「能做成芯片」之间隔着什么

RTLLM 声称的功能正确仅仅是「通过了配套 testbench 的有限测试用例」，这和真正的芯片签核之间有巨大鸿沟：

1. **没有形式验证**：testbench 无法穷举所有输入组合。一个 16 位乘法器的输入空间是 2^32，testbench 只能覆盖几十个 corner case。门级仿真、STA、形式验证三个环节 RTLLM 全部跳过。
2. **PPA 不是 signoff 级别**：论文刻意把频率设得极高使所有设计出现负 slack，这不代表真实运行频率。面积和功耗也只基于逻辑综合后的粗略估计，不含物理实现后的 IR drop、串扰、工艺变异。
3. **不验证可制造性**：综合通过不代表版图能画出来。DRC/LVS/天线效应/电迁移等物理设计约束，RTLLM 完全不考虑。

---

## 10. 评测公平性与可信度分析

### 10.1 prompt 公平性

RTLLM 对所有 LLM 使用完全相同的设计规格文本（`design_description.txt`），消除了"不同 PD 写出来的规格难易不同"的问题。统一规格是公平评测的基础——因为即便同一个电路设计，不同人类设计师给出的自然语言描述可能差异巨大。

### 10.2 testbench 覆盖度

论文明确指出 testbench 只采样了「合理数量」的测试用例，通过 testbench 不等于功能 100% 正确。这是 RTL 评测中固有的基本矛盾：穷举 testbench 在工程上不可能，但不穷举就存在漏检风险。没有形式验证作为补充，pass@5 报告的功能正确性实际上是下界（实际正确率可能更低）。

### 10.3 PPA 对比的参考基线

PPA 比较以人工 reference V_H 为基线。一个隐含假设是：V_H 的 PPA 是可接受的——但 V_H 是教学级别的参考实现，不同工程师的实现风格可能导致不同 baseline。论文没有讨论 V_H 的 PPA 最优性。

### 10.4 pass@k 的解读陷阱

pass@5 高不一定代表实用。如果 pas@1 只有 10%（即 10 次生成才可能对 1 次），工程师需要手动筛 10 份结果才能找出一个能用的——这在工业界不可接受。pass@1 才是衡量实际效率的更关键指标。

### 10.5 工具链商业依赖

Design Compiler、VCS 均需商业 license，部分限制了完全开源复现。但语法+功能两级理论上可用 Icarus Verilog + Yosys 替代，降低了前两级评测的复现门槛。

---

## 11. 复现信息

| 项目 | 内容 |
|------|------|
| 论文页 | arXiv: 2308.05345 v3, ASP-DAC 2024, 6 页 |
| 代码 | <https://github.com/hkust-zhiyao/RTLLM>，本地 commit `41b26896e33b` |
| 数据集 | 代码仓库内嵌：30 题（v1.0）/ 50 题（v2.0），含 description/testbench/reference RTL |
| 本地状态 | 论文、代码仓库、版本历史、50 题 v2.0 数据和官方保留的 290 份旧版生成 RTL 已完成静态核对 |
| 复现等级 | **R1**：代码、数据、版本和执行入口已核对，但未重新调用 LLM、未运行 VCS/DC |
| 主要门槛 | 商业工具依赖（VCS + Design Compiler）是完整评测的主要障碍；GPT-3.5/GPT-4 API 需要付费密钥 |
| 代码已知问题 | `auto_run.py` 列出 50 任务但按旧版扁平目录访问，无法遍历 v2.0 四级分类目录；硬编码作者路径；`freq_divfrac` 名称错位；timeout 不杀进程；pass@k 均值计算存在额外追加零的问题 |

详见 [RTLLM论文与代码复现详解.md](./RTLLM论文与代码复现详解.md)。

---

## 12. 一分钟复述版

RTLLM 不是模型，是**第一个有 PPA 评价的 RTL 生成 benchmark**。

- 数据集：30 个数字设计（11 算术 + 19 逻辑），每题自带自然语言规格、testbench、人工参考 RTL
- 评测：三级递进——Syntax（综合通过）→ Functionality（仿真通过）→ Quality（PPA 对比）
- 核心发现：GPT-4 最强（81% syntax, 15/30 func），加入 self-planning 后达 90%/19/30；GPT-3.5 + self-planning（73%/14/30）接近 GPT-4 裸模型
- Self-planning 方法：先让 LLM 写设计计划 + 语法注意事项，再让 LLM 根据计划生成 RTL——不训练、不读工具反馈，仅靠 prompt 结构调整
- GPT-4 在 PPA 上也领先，best area 数（8）远超其他方法
- 局限：testbench 非穷举（pass 不代表 100% 正确），PPA 评测依赖商业工具，题目规模偏教学级别
