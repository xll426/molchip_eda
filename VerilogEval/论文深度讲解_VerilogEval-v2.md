# VerilogEval (v2 / Revisiting) 论文深度讲解

> **Revisiting VerilogEval: A Year of Improvements in Large-Language Models for Hardware Code Generation**
> Nathaniel Pinckney, Christopher Batten, Mingjie Liu, Haoxing Ren, Brucek Khailany
> NVIDIA Corporation / Cornell University
> arXiv:2408.11053v2 (2025-02-03)
> 原文：[2408.11053_Revisiting_VerilogEval.pdf](./2408.11053_Revisiting_VerilogEval.pdf)
> 代码：https://github.com/NVlabs/verilog-eval (main branch, commit `c498220d`)
> 姊妹篇：[VerilogEval v1](./论文深度讲解_VerilogEval-v1.md)

---

## 1. 一句话定位

**Revisiting VerilogEval 把 v1 从单一的 code completion 升级为 code completion + specification-to-RTL 双任务评测基准，引入 Makefile 驱动的文件化工作流、0--4 shot 上下文学习（ICL）与 11 类细粒度失败分类，系统复评 14 个新模型的硬件代码生成能力——核心发现是开源 Llama3.1 405B（0-shot pass@1 = 57.0%）已追平闭源 GPT-4o（56.1%），但 ICL 收益非单调、采样协议差异会翻转模型排名。**

这句话里的 5 个承重点，后面逐一拆解：

1. **双任务升级** — 从"给定 module header 补全 body"扩展为 + "给定自然语言 spec 自写完整模块（含端口）"，后一种更接近真实设计工作流，且更适配 instruction-tuned 模型。
2. **0--4 shot ICL + 非单调效应** — 首次在该 benchmark 中系统研究上下文示例的数量影响，发现 1-shot 对某些模型有益（GPT-4o 从 56.1% 跃至 60.7%）、对另一些有害（Llama3 70B 从 39.1% 跌至 36.5%）。
3. **11 类失败分类** — 从简单的 pass/fail 二元判定拆成编译期（S/C/c/e/m/n/p/w）和运行期（r/R/T）三类错误码，可指导 prompt tuning。
4. **Makefile 文件化工作流** — 每题独立目录 + `make -j` 并行展开，支持多模型 sweep、中断续跑和人工检查，成为后续 ChipBench 的直接脚手架。
5. **14 个新模型复评** — GPT-4o、Llama3.1 405B/70B/8B、RTL-Coder 6.7B 等，绘制一年内模型能力演进曲线：开源模型已追上闭源，领域专用小模型（RTL-Coder 6.7B $\approx$ 34%）接近大通用模型。

---

## 2. EDA 阶段映射（①-⑰）

参照 [芯片流程.md](../芯片流程.md) 的 17 阶段标准编号：

| 阶段 | 覆盖 | 说明 |
|------|:---:|------|
| **① RTL 设计** | ✅ **核心** | 两种任务对应两种设计模式：code completion（补全已有接口，相当于改代码）和 spec-to-RTL（独立设计完整模块含端口，相当于从零写） |
| **② RTL 功能仿真** | ✅ | 仍用 Icarus 差分仿真判定，但把"通过/失败"二元结果细化为按日志关键字分类的 11 类失败类型 |
| ③ 逻辑综合 | ❌ | 同 v1，不跑综合，不检查可综合性——生成的代码可能含不可综合结构（如 `initial` 块、延时语句）而仍判为 pass |
| ④ 门级仿真 | ❌ | 没有综合网表，无从做门级验证 |
| ⑤ STA（静态时序分析） | ❌ | 不评估时序，PPA 完全不在评测目标内 |
| ⑥ 形式验证 | ❌ | 只做仿真覆盖，不做等价性检查或属性证明 |
| ⑦ 布局规划（Floorplan） | ❌ | 不涉及物理设计 |
| ⑧ 标准单元摆放（Placement） | ❌ | 不涉及 |
| ⑨ 时钟树综合（CTS） | ❌ | 不涉及 |
| ⑩ 布线（Routing） | ❌ | 不涉及 |
| ⑪ 后仿真 | ❌ | 不涉及 |
| ⑫ 物理验证（DRC + LVS） | ❌ | 不涉及 |
| ⑬ 签核（Signoff） | ❌ | 不涉及 |
| ⑭ 流片 | ❌ | 不涉及 |
| ⑮ 制造 | ❌ | 不涉及 |
| ⑯ 封装 + 测试 | ❌ | 不涉及 |
| ⑰ 芯片到手 | ❌ | 不涉及 |

**覆盖率：2/17。** 同 v1，只覆盖数字前端最前面的设计+仿真闭环。v2 的增量在于 spec-to-RTL 任务让模型承担了"端口/接口设计"——这是真实流程中架构师与 RTL 工程师交接的关键动作，但验证深度仍停在功能仿真层。

> v2 相比 v1 新增的"失败分类"中 `c`（clk 未绑定）、`r`（reset 问题）直指芯片流程中上电/复位行为这类硬件独有的陷阱——通用代码生成 benchmark 几乎不涉及，但它们是芯片失败的首要原因之一。

---

## 3. 输入 / 输出

### 3.1 两种任务的输入格式

v2 提供两类任务，模型输入格式完全不同：

**Code Completion（代码补全，v1 同款）：**

```verilog
// Implement the Verilog module based on the following description. Assume
// that signals are positive clock/clk triggered unless otherwise stated.
//
// A "population count" circuit counts the number of '1's in an input vector.
// Build a population count circuit for a 3-bit input vector.

module TopModule (
    input [2:0] in,
    output [1:0] out
);
// 模型只补全这里
```

**Specification-to-RTL（规格到 RTL，v2 新增）：**

```text
Question:
Implement a hardware module named TopModule with the following interface.
All input and output ports are one bit unless otherwise specified.

- input in (3 bits)
- output out (2 bits)

Implement a population count circuit that counts the number of '1's in
the input vector and outputs the count.

Enclose your code with [BEGIN] and [DONE]. Only output the code snippet
and do NOT output anything else.

Answer:
```

关键差异：spec-to-RTL 不给模块头，模型必须自己写 `module TopModule(...)`、端口声明、类型与位宽。这更接近"从规格独立设计"的真实动作，且给了模型接口设计自由度——可以用 `logic`、可选择 wire/reg 语义、可自定信号类型。

**可选 ICL 示例（0--4 shot）：**

两种任务均有 1/2/3/4-shot 文件，论文主要解释 0--3 shot：

| shot | 新增示例 | 主要能力 |
|---:|---|---|
| 1 | 组合 incrementer | 简单接口与组合赋值 |
| 2 | 带同步 reset 的 registered incrementer | 时序逻辑与 reset |
| 3 | 两个连续 1 检测 FSM | 状态、next-state、输出逻辑 |

file 的 4-shot 示例使用另一组组合（XOR、registered incrementer、参数化 incrementer、FSM），不是简单在 3-shot 上追加，因此做 sweep 时不能假设 prompt 严格嵌套。

**ICL 示例样式（以 1-shot spec-to-RTL 为例）：**

```
Question:
Implement a hardware module named TopModule...
The module should implement an incrementer which increments the input
by one and writes the result to the output...

Answer:
[BEGIN]
module TopModule (input logic [7:0] in_, output logic [7:0] out);
    assign out = in_ + 1;
endmodule
[DONE]
```

### 3.2 数据集变化（vs v1）

| 维度 | v1 | v2 |
|---|---|---|
| 题目数量 | Human 156 + Machine 143 | **仅 Human 156**（machine 移除） |
| 题目修订 | 无 | **14 题**描述/testbench 修订 |
| 数据格式 | 单个 JSONL | 每题 4 个文件（prompt/ref/test/ifc） |
| 任务模式 | 仅 code completion | code completion + spec-to-RTL |

移除 machine 的原因：作者认为 machine 描述过于冗长、与真实代码生成部署不一致，保留它会导致分数虚高并混淆模型真实能力的评估。

14 题修订涉及：`Prob034_dff8`（reference 初值）、`Prob045_edgedetect2`、`Prob068_countbcd`、`Prob074_ece241_2014_q4`、`Prob079_fsm3onehot`、`Prob082_lfsr32`、`Prob086_lfsr5`、`Prob099_m2014_q6c`、`Prob104_mt2015_muxdff`、`Prob124_rule110`、`Prob134_2014_q3c`、`Prob143_fsm_onehot`、`Prob145_circuit8`、`Prob150_review2015_fsmonehot`。

### 3.3 采样协议

论文使用两种温度协议：

| 协议 | temperature | top_p | 每题 n | 含义 |
|---|---:|---:|---:|---|
| 高温 | 0.8 | 0.95 | 20 | 每题 20 次通过比例的跨题均值（与 v1 的 pass@1 数学等价） |
| 低温 | 0.0 | 0.01 | 1 | 接近 deterministic/greedy 的单次成功率 |

### 3.4 输出

每题每个 sample 的输出物：

- `<Prob>_sampleYY.sv`：生成的 Verilog 文件
- `<Prob>_sampleYY-sv-generate.log`：完整的 prompt/response 日志（含 token 统计和 cost）
- `<Prob>_sampleYY-sv-iv-test.log`：Icarus 编译/仿真日志

聚合输出：`summary.txt`（每题 pass 率 + 失败分类）+ `summary.csv`（机器可读）。

---

## 4. Benchmark 构建方法

### 4.1 整体 Pipeline（Figure 2）

```text
configure.ac / Makefile.in
  --with-model --with-task --with-examples --with-samples
  --with-temperature --with-top-p --with-dataset
        │
        ▼
 Makefile 为每题 × 每 sample 展开生成规则（make -j 并行）
        │
        ▼
 sv-generate ──► 拼接 system prompt + ICL 示例 + coding rules + 题目
        │          调用 LLM API（OpenAI / NVIDIA NIM / manual）
        ▼
 提取代码（[BEGIN]..[DONE] / Markdown fence / completion 风格）
        │
        ├─ code completion: 从 _ifc.txt 自动补全模块头
        └─ spec-to-RTL:     直接保存完整模块
        │
        ▼
 iverilog -g2012 -s tb → vvp → timeout 30
        │
        ▼
 sv-iv-analyze ──► 按日志关键字分类失败
        │           S/C/c/e/m/n/p/w 编译类
        │           r/R/T 运行类
        ▼
 summary.txt/csv + count_failures.py 失败分布图
```

### 4.2 核心组件详解

**构建系统升级（v2 最大架构变化）：**

从 v1 的 Python 脚本直调改为 **autotools（configure.ac + Makefile.in）** 驱动的文件化工作流：

- `configure --with-model=gpt4o --with-task=spec-to-rtl --with-examples=1 --with-samples=20` 生成 Makefile
- 每题独立目录：`ProbXXX/` 含 prompt、reference、testbench、interface 四个文件
- `make -j4` 并行展开 156 题 $\times$ 每 sample 的生成+仿真规则
- 文件级依赖支持中断后续跑：已完成的 sample 不会重新生成
- 结果结构可追溯：每题每个 sample 的所有中间产物都在独立目录中

**sv-generate（模型调用器）：**

支持三种模型调用模式：
- **OpenAI API**：gpt-3.5-turbo / gpt-4 / gpt-4-turbo / gpt-4o
- **NVIDIA NIM**：Llama2/3/3.1、CodeLlama、Gemma/CodeGemma、Mistral/Mixtral
- **Manual**：写 `_fullprompt.txt` + `_systemprompt.txt`，等外部推理程序写 `_response.txt`，再解析为 `.sv`（用于接入本地模型）

代码提取逻辑：优先 `[BEGIN]...[DONE]`，其次 Markdown fence，最后 module-completion 风格。对 RTL-Coder 有特殊后处理：因其会在 `endmodule` 后继续重复代码，脚本做了特定修补。

**sv-iv-analyze（Icarus 日志解析器 + 失败分类器）：**

扫描 `iverilog` stderr 和 `vvp` stdout，按优先级做**单标签**分类：命中某一类即 `break`，不再检查后续类别。这意味着编译错误会遮蔽潜在运行错误——分类柱状图应从下往上读。

**count_failures.py（失败汇总）：**

用 pandas 汇总多个 `summary.csv` 绘制论文 Figure 5 的失败分布柱状图。需要注意：`sv-iv-analyze` 写 CSV 时默认不带 header，直接 `pd.read_csv()` 会把第一个 problem 行当 header 吃掉——复核失败统计时需显式传 `header=None`。

### 4.3 评测模型清单（14 个）

| 模型 | 规模 | 类型 |
|---|---|---|
| GPT-4o | 未公开 | 闭源通用 |
| GPT-4 Turbo (gpt-4-1106-preview) | 未公开 | 闭源通用 |
| GPT-4 (gpt-4-0613) | 未公开 | 闭源通用 |
| Mistral Large | 未公开 | 闭源通用 |
| Llama3.1 405B | 405B | 开源通用 |
| Llama3.1 70B | 70B | 开源通用 |
| Llama3 70B | 70B | 开源通用 |
| Llama2 70B | 70B | 开源通用 |
| CodeLlama 70B | 70B | 开源代码专用 |
| DeepSeek Coder 33B | 33B | 开源代码专用 |
| DeepSeek Coder 6.7B | 6.7B | 开源代码专用 |
| Llama3.1 8B | 8B | 开源通用 |
| CodeGemma 7B | 7B | 开源代码专用 |
| RTL-Coder 6.7B | 6.7B | 开源 Verilog RTL 专用 |

---

## 5. 关键公式

### 5.1 pass@1（低温协议）

低温下 $T=0.0$, $n=1$，等价于 greedy 解码的单次成功率：

$$
\text{pass@1}_{\text{low}} = \frac{1}{N_{\text{probs}}} \sum_{i=1}^{N_{\text{probs}}} \mathbb{1}[\text{生成}_i \text{ 通过仿真}]
$$

- $N_{\text{probs}}$：题目总数（156）
- $\mathbb{1}[\cdot]$：指示函数，通过为 1，否则为 0

### 5.2 pass@1（高温协议）

高温下 $T=0.8$, $n=20$，pass@1 是每题 20 个候选中通过比例的跨题均值：

$$
\text{pass@1}_{\text{high}} = \frac{1}{N_{\text{probs}}} \sum_{i=1}^{N_{\text{probs}}} \frac{c_i}{n}, \quad n=20
$$

- $c_i$：第 $i$ 题 20 个候选中通过功能仿真的个数

**与 v1 的数学关系**：v1 的 pass@1 无偏估计 $= 1 - \binom{n-c}{1}/\binom{n}{1} = c/n$，恰好等于通过比例。所以两者的高温 pass@1 数学等价。但需要注意：**这不是 "20 次里只要一次通过就算成功"（后者更接近 pass@20），而是 "平均每次尝试的成功率"**。

### 5.3 失败分类规则

`sv-iv-analyze` 按以下优先级匹配日志字符串：

| 优先级 | 码 | 匹配条件 | 含义 |
|---:|---|---|---|
| 1 | `.` | stdout 含 `Mismatches: 0` | 通过 |
| 2 | `S` | stderr 含 `syntax error` | 语法错误 |
| 3 | `c` | stderr 含 `Unable to bind wire/reg` 且含 `clk` | 时钟端口缺失 |
| 4 | `e` | stderr 含 `assignment requires explicit cast` | 类型转换问题 |
| 5 | `0` | stderr 含 `numeric constant size` 且含 `is 0` | 零宽常量 |
| 6 | `w` | stderr 含 `declared here as wire` | wire 当 reg 赋值 |
| 7 | `m` | stderr 含 `Unknown module type` | 缺少/错误模块声明 |
| 8 | `n` | stderr 含 `always` 且含 `no sensitivity` | 敏感列表问题 |
| 9 | `p` | stderr 含其他 `Unable to bind wire/reg` | 端口/信号绑定失败 |
| 10 | `C` | stderr 含 `error` | 通用编译错误 |
| 11 | `r` | 生成代码含 `posedge reset` 等 pattern | 疑似异步 reset |
| 12 | `T` | 日志含 `TIMEOUT` | 仿真超时 |
| 13 | `R` | 其他未匹配但有 mismatch | 通用功能错误 |

**工程直觉**：编译错误（S/C/c/e/m/n/p/w/0）会遮蔽运行错误（r/R/T），所以失败柱状图应从下往上读。例如，`w`（wire/reg 混淆）的减少可能是因为代码语法错误增多导致编译提前失败（`S` 类上升），而非真正修复了类型混淆。

---

## 6. 评测协议与打分

### 6.1 评测执行流程

```text
configure → Makefile
    ↓ 对 156 题 × 20 samples（高温）展开规则
sv-generate 为每个 sample:
    ↓ 拼 system prompt + ICL 示例 + coding rules + problem prompt
    ↓ 调 LLM API → raw response
    ↓ 从 [BEGIN]...[DONE] / fence / completion 提取代码
    ↓ code-completion: 从 _ifc.txt 补模块头 + endmodule
    ↓ spec-to-RTL: 直接写完整模块
sample.sv 就绪
    ↓
iverilog -g2012 -s tb sample.sv test.sv ref.sv → a.out
    ↓
timeout 30 ./a.out → stdout/stderr
    ↓
sv-iv-analyze: 按优先级分类 → pass rate + 失败码
    ↓
summary.txt: 每题总体 pass rate
summary.csv: 每题 × 每 sample 的分类结果
```

Icarus 版本固定为 v12（README 明确说不支持开发版 v13）；每次 simulation 30 秒超时。

### 6.2 完整结果表（Table 2，高温 T=0.8, n=20）

| 模型 | Code 0-shot | Code 1-shot | Spec 0-shot | Spec 1-shot |
|---|---:|---:|---:|---:|
| GPT-4o | 56.1 | 60.7 | 61.4 | **62.6** |
| GPT-4 Turbo | 49.8 | 59.5 | 61.1 | 56.7 |
| GPT-4 | 41.6 | 50.1 | 31.7 | 51.4 |
| Mistral Large | 33.1 | 42.7 | 35.9 | 46.0 |
| **Llama3.1 405B** | **57.0** | 57.9 | 57.1 | 58.3 |
| Llama3.1 70B | 36.3 | 33.0 | 39.0 | 48.5 |
| Llama3 70B | 39.1 | 36.5 | 43.9 | 40.5 |
| Llama2 70B | 1.7 | 13.3 | 5.3 | 19.2 |
| CodeLlama 70B | 29.0 | 27.4 | 25.3 | 27.0 |
| DeepSeek Coder 33B | 29.3 | 37.5 | 19.5 | 38.1 |
| Llama3.1 8B | 4.9 | 12.8 | 16.8 | 26.5 |
| CodeGemma 7B | 8.7 | 16.2 | 9.5 | 22.2 |
| DeepSeek Coder 6.7B | 21.0 | 30.3 | 22.6 | 25.6 |
| RTL-Coder 6.7B | 31.5 | 32.6 | 30.9 | 33.5 |

这张表揭示的 5 个关键洞察：

1. **开源追平闭源**：Llama3.1 405B 在 0-shot code completion 上以 57.0% 超过 GPT-4o（56.1%），这是硬件代码生成领域开源模型首次在综合 benchmark 上全面挑战闭源。
2. **ICL 效应高度模型依赖**：GPT-4o 和 DeepSeek Coder 受益于 ICL（+4--8 个百分点），Llama3 70B 和 CodeLlama 70B 反而下降（-2--3 个百分点）。
3. **spec-to-RTL 更适合 instruction-tuned 模型**：GPT-4、Mistral Large、Llama3.1 8B 在 spec-to-RTL 上显著高于 code completion。
4. **小领域模型竞争力惊人**：RTL-Coder 6.7B（约 34%）接近 Llama3.1 70B（约 36%），参数规模差一个数量级但性能仅差几个百分点。
5. **代际跃迁巨大**：Llama2 70B（1.7%）到 Llama3 70B（39.1%）的一代之内提升了 20+ 倍。

### 6.3 0--3 shot ICL 深度 sweep（Figure 4）

论文选取 4 个代表性模型深入分析 multi-shot 效应：

| 模型 | Code Completion 趋势 | Spec-to-RTL 趋势 |
|---|---|---|
| **GPT-4o** | 0-shot 56% → 1-shot 61% → 3-shot 略回落至约 55% | 稳定在 60--63% |
| **Llama3.1 70B** | 0-shot 36% → 1-shot 33% → 较平稳 | 0-shot 39% → 3-shot 约 49%（大幅提升） |
| **Llama3 70B** | 0-shot 39% → 3-shot 约 31%（持续下降） | 0-shot 44% → 1-shot 略降 → 3-shot 约 47% |
| **RTL-Coder 6.7B** | 稳定在 31--34% | 稳定在 30--35%，微弱提升 |

结论不是"加更多示例"，而是"示例内容、任务格式和模型对齐方式需要联合调参"：同一个增量 example 在一题上提升 65 个百分点，在另一题上毁掉 19/20 的通过率。

### 6.4 Case Study: Problem 9 和 Problem 34

论文以两个典型题目深刻展示了 ICL 的微妙性：

**Problem 9（组合逻辑，3-bit population count）** vs **Problem 34（时序逻辑，8 DFF）**。

Llama3 70B code completion 的表现：

- Prob009 0-shot: 0/20 通过（全用不存在的 `clk` 信号——把组合逻辑当成时序逻辑）
- Prob009 1-shot: 13/20 通过（ICL incrementer 示例教会了组合逻辑范式）
- Prob034 0-shot: 20/20 通过
- Prob034 1-shot: 1/20 通过（ICL 示例让模型忘记 DFF 的正确写法，丢失 `endmodule`、混淆 `begin/end` 块边界）

Llama3.1 70B 的进一步 sweep：

- Prob009: 0-shot 0/20 → 1-shot 15/20 → 2-shot 12/20 → 3-shot 15/20
- Prob034: 0-shot 20/20 → 1-shot 20/20 → 2-shot 0/20 → 3-shot 20/20

2-shot 让 Prob034 全部失败（所有 sample 输出英文解释文本导致语法错误），3-shot 又全部恢复。这说明 ICL 不是随 context 长度平滑变化的函数——具体示例的组合对最终行为有离散且非单调的影响。

Llama3.1 405B 对这两题在所有 shot 下均为 20/20，说明大模型更能区分"示例模式"和"当前任务约束"。

### 6.5 失败分类聚合分析（Figure 5）

论文汇总了 Llama2/3/3.1 三代 70B 模型的失败分布：

- **spec-to-RTL 系统性减少 wire/reg 混淆和语法错误**：因为模型可自行定义端口类型（用 `logic` 可同时用于组合和时序赋值）
- **ICL 可能减少某类编译错误但不减少总失败**：被修复的错误被更早出现的其他编译错误遮蔽
- **Llama3.1 70B 在 spec-to-RTL 中随 ICL 增加总体失败明显下降**，而 Llama3 70B 的 code completion 则因 ICL 增加编译失败上升
- 常见失败类型分布：`w`（wire/reg 混淆）>> `S`（语法错误）> `c`（缺 clk）> `m`（缺模块）

每个设置的最大失败数为 $156 \times 20 = 3120$。由于编译错误遮蔽运行错误，失败分类最可靠的用途是定位"prompt 改动后错误分布发生了什么"，而非声称完成了精确根因诊断。

---

## 7. 创新点

### 创新点 1：双任务评测

从单一 code completion 扩展为 + specification-to-RTL，首次在统一题目池上对比两种范式的模型表现。spec-to-RTL 让模型独立完成端口设计，这不仅是难度升级，更揭示了"给定接口约束" vs "自由设计接口"两种场景下模型行为模式的系统性差异——前者 wire/reg 混淆是主要失败源，后者自由度消除了此类错误但引入了端口命名/位宽漂移的新问题。

### 创新点 2：0--4 shot ICL 系统分析 + 非单调效应发现

首次在该 benchmark 中系统研究多 shot 上下文学习的影响，并发现了对后续研究至关重要的非单调效应：同一 ICL 示例组合对某些模型有利、对另一些有害，甚至在同一模型的不同 shot 数之间存在剧烈波动（如 Llama3.1 70B 的 2-shot 让 Prob034 全灭，3-shot 又全恢复）。这直接否定了"ICL 越多越好"的朴素假设。

### 创新点 3：细粒度失败分类机制

将"不通过"从二元布尔值拆成 11 类错误码（S/C/c/e/m/n/p/w/r/R/T），覆盖编译期语法/接口/类型与运行期功能/reset/超时。这允许研究者：
- 定位模型的系统性弱项（如某模型大量产出 wire/reg 混淆）
- 评估 prompt tuning 的具体影响（如 coding rules 应优先压制哪些错误类别）
- 跨模型比较失败模式（如 CodeLlama 70B 的失败更多是语法问题还是功能问题）

### 创新点 4：Makefile 文件化工作流

从 v1 的 Python 脚本直调改为 autotools（configure.ac + Makefile）驱动的逐题文件系统。每个 problem ID 映射到一个独立目录，含 prompt/ref/test/ifc 四个文件的标准化结构。`make -j` 支持并行展开 156 题 $\times$ 每 sample 的生成+仿真任务，中断后可精确续跑。这套架构被 ChipBench 直接继承，成为后续 RTL benchmark 的标准脚手架。

### 创新点 5：14 题修订 + benchmark 维护方法论

论文不仅评测新模型，还修正了 v1 中 14 个问题的描述歧义和 testbench 漏洞。这体现了一个重要的 benchmark 工程理念：**benchmark 本身是需要持续维护的软件系统，题目的版本演化会影响跨时间比较的有效性**。例如 Prob034 的 reference 初值从 `8'hx`（不确定态）改为 `8'h0`（确定初值），这个改动虽小但直接影响仿真通过与否。

### 创新点 6：开源与闭源、通用与专用的全面对比

14 个模型的系统评估覆盖了开源/闭源、通用/代码专用/RTL 专用、8B 到 405B 参数规模的完整光谱，绘制了硬件代码生成领域一年内的能力演进曲线。核心结论"开源已追平闭源"在当时的 AI 社区有显著影响力。

---

## 8. EDA 缩写表

| 缩写 | 全称 | 一句话解释 |
|---|---|---|
| RTL | Register-Transfer Level（寄存器传输级） | 用 always/assign/reg 描述寄存器传输行为的硬件描述层级 |
| EDA | Electronic Design Automation（电子设计自动化） | 用软件工具辅助芯片设计、验证、制造的方法论 |
| HDL | Hardware Description Language（硬件描述语言） | 描述数字电路行为的语言，Verilog/SystemVerilog 为主流 |
| FSM | Finite State Machine（有限状态机） | 状态寄存器 + 转移逻辑的时序电路范式，ICL 示例之一 |
| ICL | In-Context Learning（上下文学习） | 在 prompt 中放置少量示例让模型模仿，不更新模型权重 |
| LLM | Large Language Model（大语言模型） | 基于 Transformer 的自回归语言模型 |
| API | Application Programming Interface（应用程序接口） | 模型调用接口，如 OpenAI API |
| NIM | NVIDIA Inference Microservices | NVIDIA 的推理服务框架，sv-generate 支持的后端之一 |
| PPA | Power, Performance, Area（功耗/性能/面积） | 芯片设计的三个核心优化目标，本文不评估 |
| JSONL | JSON Lines | 每行一个 JSON 对象的文本格式 |
| IDE | Integrated Development Environment（集成开发环境） | 代码编辑器，如 VS Code，code completion 任务的灵感来源（Copilot） |
| MBPP | Mostly Basic Python Problems | Python 代码生成 benchmark，v2 spec-to-RTL prompt 格式的参考来源 |

---

## 9. 与芯片流程的关系

### 9.1 在全流程中的位置

与 v1 相同，v2 卡在 17 阶段的**① RTL 设计 $\to$ ② RTL 功能仿真**闭环。但 v2 的 spec-to-RTL 任务让模型承担了更多设计自由度——在真实流程中，这对应于架构师给出规格后 RTL 工程师独立完成模块设计的动作。失败分类中的 `c`（clk 缺失）、`r`（reset 语义错误）直指芯片流程中上电/复位行为——这类问题在软件代码评测中不存在，但在硬件中是导致芯片失败的首要原因之一。

### 9.2 对真实流程的三种启示

1. **ICL 非单调 + 采样协议敏感**：单轮评测的数字高度依赖 prompt 设计和采样设置。在实际工程中做模型选型时，不能只看一篇论文的一个 pass@1 数字，必须固定协议后再横比。
2. **spec-to-RTL 的接口自由度是双刃剑**：减少 wire/reg 混淆的同时可能引入端口命名错误、位宽漂移——在真实流程中，前者导致仿真不过（容易发现），后者可能导致仿真通过但功能错误（更难发现）。
3. **benchmark 通过率已接近饱和**：v2 发布时 VerilogCoder（94%）和 MAGE（95%）已接近解决该数据集，说明它对真实流程前端的区分度已耗尽。后续需要层次化、多模块、形式验证级别的 benchmark。

---

## 10. 评测公平性与可信度分析

### 10.1 协议敏感性与模型排名的不稳定性

v2 的核心发现之一是"排名取决于评测设置"。以 code completion 为例：

| 评测设置 | 最佳模型 | pass@1 |
|---|---|---|
| 高温 0-shot | Llama3.1 405B | 57.0% |
| 高温 1-shot | GPT-4o | 60.7% |
| 低温 0-shot | GPT-4o | 59.0% |
| 低温 1-shot | GPT-4o | 62.8% |

GPT-4o 在 4 种设置中赢了 3 种，但 0-shot 高温下被 Llama3.1 405B 反超。如果只报告一个数字，结论可能截然不同。这提醒使用者：**引用 VerilogEval v2 结果时，必须同时注明 task、shot、temperature 和后处理方式**——裸写"pass@1 = X%"没有可比意义。

### 10.2 高温 pass@1 的语义陷阱

论文报告的"高温 pass@1"实际上是"每题 20 个 sample 中通过比例的跨题均值"（即 $c_i/n$ 的均值），而非"20 次中至少一次通过"。两者在数学上当 $k=1$ 时等价（因为 $1 - \binom{n-c}{1}/\binom{n}{1} = c/n$），但语义含义不同：
- "平均成功率"：反映模型的单次尝试质量
- "至少一次成功率"：反映模型的候选集覆盖质量（更接近 pass@20）

在与其他论文（如 VerilogCoder/MAGE 报告 94--95%）比较时，必须认清资源差异：agent 方法可访问 testbench、仿真日志、波形和多轮修复循环，而 v2 Table 2 是单轮 prompt-response-test。

### 10.3 失败分类的方法论限制

失败分类是**基于日志字符串匹配的启发式单标签分类**，不是完整根因分析：

- 单标签设计：编译错误会遮蔽运行错误——某类编译错误减少可能是因为被另一类更早匹配的错误替代
- 字符串匹配脆弱性：reset 检测依赖 `posedge reset`/`negedge reset` 等 pattern，若题目要求异步 reset 则误报，若信号名为 `rst_n`/`areset` 则漏报
- Icarus 版本依赖：不同 Icarus 版本的 warning/error 文本不同，分类结果不可跨版本直接比较
- 论文 Figure 5 的 `count_failures.py` 汇总脚本存在 `pd.read_csv()` 无 header 处理问题，复核失败统计时应显式指定列名

### 10.4 题目修订对可比性的冲击

14 题修订意味着 v2 不是 v1 的真子集评估。同一模型在 v1 和 v2 上的分数差异可能来自：(a) 模型真正进步、(b) prompt 格式变化、(c) Icarus 版本差异、(d) 14 题修订（改变了问题的答案/判定标准）。论文给出的唯一可参考锚点是 GPT-4 在 code completion 0-shot 下从 v1 的 43.5% 降到 v2 的 41.6%（差 1.9 个百分点），作者将其归因于"prompt 中的空白和标点变化"。

### 10.5 数据污染与 benchmark 寿命

v2 发布时（2025-02），HDLBits 题目已高度公开，VerilogEval 已被引用 100+ 次。到 2026 年，这些题目几乎确定已进入各模型训练语料。因此继续用 VerilogEval-human 作为"零污染评测"已不可信——任何高分都应该首先怀疑是否来自记忆而非推理。论文作者也清醒地认识到这一点，在 Section 6（Future Work）明确呼吁下一代 benchmark 需要"真实且复杂的工业设计问题"，避免成为"自然语言 proxy for RTL"。

---

## 11. 复现信息

| 项目 | 内容 |
|---|---|
| 论文页 | https://arxiv.org/abs/2408.11053 |
| 代码 | https://github.com/NVlabs/verilog-eval (main branch, commit `c498220d`) |
| 评测数据 | 156 题 $\times$ 2 任务（code completion + spec-to-RTL），prompt/ref/test/ifc 齐全 |
| ICL 文件 | 1/2/3/4-shot $\times$ 2 任务，`scripts/verilog-example-prefix_*.txt` |
| 论文原始 outputs | **未公开**（本地无 build 目录、summary、samples 或日志） |
| 复现等级 | 数据和代码逻辑已核清 (R1)；具 Icarus v12 + 依赖可离线重放后处理 (条件 R2)；论文完整数字不可复现（缺 14 个模型的原始 responses 和 API 版本信息） |
| 主要门槛 | Icarus v12、Python 3.11、langchain-openai + langchain-nvidia-ai-endpoints（API 模式需凭据）、GNU make + autotools、Linux/GNU shell 环境 |

---

## 12. 一分钟复述版

1. Revisiting VerilogEval 是 v1 的重大升级：code completion + spec-to-RTL 双任务、0--4 shot ICL、11 类失败分类、Makefile 工作流。
2. 评测 14 个模型：GPT-4o（56.1%）、Llama3.1 405B（57.0% 0-shot）、RTL-Coder 6.7B（约 34%）——开源已追平闭源，小领域模型竞争力惊人。
3. ICL 非单调：GPT-4o 受益（+4--8 个百分点），Llama3 70B 反而下降（-2--3 个百分点）；同一个 1-shot example 让 Problem 9 从 0/20 变 13/20，却让 Problem 34 从 20/20 变 1/20。
4. spec-to-RTL 减少 wire/reg 混淆但可能引入新错误；code completion 的给定接口是一把"安全锁"但也限制了模型自由度。
5. 失败分类：S/C/c/e/m/n/p/w 编译期 + r/R/T 运行期，编译错误会遮蔽运行错误，reset 检测是字符串启发式。
6. 模型排名取决于评测设置（0-shot vs 1-shot、高温 vs 低温、code completion vs spec-to-RTL）——只报告一个数字没有可比意义。
7. ChatGPT + Icarus + Makefile 架构成为 ChipBench 的脚手架，14 题修订体现 benchmark 作为软件系统需要持续维护。
8. 已带动 VerilogCoder（94%）、MAGE（95%）等 agent 方法接近解决该数据集，说明需要更复杂的下一代 benchmark。详见 [VerilogEval v1](./论文深度讲解_VerilogEval-v1.md)。

---

## 13. v1 $\to$ v2 到底修了什么

这一节是本资料包对两篇 VerilogEval 论文的关键对比，服务于"用 v1 还是 v2、为什么 v2 的数字不能直接和 v1 对比"的选型决策。

### 13.1 规格描述的歧义修正

v1 中 156 道 human 题有 14 题存在描述歧义或 testbench 漏洞。v2 逐一修正：

| 问题类型 | 具体案例 | 修正 |
|---|---|---|
| 参考实现初值不确定 | Prob034_dff8: reference 初值 `8'hx`（X 态） | 改为 `8'h0`（确定性初值） |
| 端口位宽/索引不一致 | Prob113/Prob116: code completion 用 `[4:1]`，spec-to-RTL 改为 `[3:0]` | 统一为 0-based 索引 |
| 状态编码与输出映射错误 | Prob148: `r[3:1]` / `g[3:1]` 改为 `[2:0]` | 内部索引平移匹配 0-based |
| 输出位宽定义不明确 | Prob092: 输出端口宽度与边界补零方式被重新定义 | 明确位宽与补零规则 |

这些修正意味着 v2 的 156 题和 v1 的 156 题**不是同一个考题集**——同一模型在两版上的 pass rate 差异包含题目变化贡献的成分。

### 13.2 testbench 的漏洞修补

v1 的 testbench 存在若干问题：部分激励不覆盖边界条件、随机种子未固定导致不可复现、仿真超时阈值不合理。v2 的 Makefile 工作流下每个 testbench 独立文件化，修订了 7 个 spec-to-RTL 的 testbench（包括 Prob034、Prob092、Prob094、Prob113、Prob116、Prob148、Prob149），使其与对应 task 的接口定义一致。

### 13.3 in-context learning 设定的变化

v1 **完全没有 ICL**——所有评测是 0-shot，模型只看当前题的 prompt。v2 引入了 0--4 shot ICL：

- 1-shot: 组合 incrementer
- 2-shot: + 带同步 reset 的 registered incrementer
- 3-shot: + 两个连续 1 检测 FSM

ICL 的出现是 v2 最核心的评测协议变化：它直接导致了模型排名的翻转（GPT-4o 在 1-shot 下反超 Llama3.1 405B），也首次系统性地揭示了"ICL 非单调"现象。v1 的任何分数都不能和 v2 的 1-shot 分数直接对比——它们测的是不同协议下不同模型的不同能力维度。

### 13.4 新增的 spec-to-RTL 与 code-completion 双任务

v1 只有 code completion 一种任务：给定模块头、补全模块体。v2 增加 spec-to-RTL：
- 不给模块头，模型自行设计完整模块（包括端口声明、类型选择、模块体）
- prompt 格式从"Verilog 注释风格"改为"Question-Answer 对话风格"
- 模型获得接口设计自由度：可用 `logic` 避免 wire/reg 混淆、可自行决定端口名和位宽

双任务的设计暴露了一个重要事实：模型在 code completion 和 spec-to-RTL 上的相对排序可以完全不同。例如 CodeLlama 70B 在 code completion 0-shot 上 29.0%，spec-to-RTL 0-shot 上 25.3%；而 Mistral Large 在 code completion 上 33.1%，spec-to-RTL 上 35.9%（后者更高）。这说明"模型强不强"的答案依赖于"任务是什么"。

### 13.5 评测脚本的重写

v1 的评测是 Python 脚本直调：一个 `evaluate_functional_correctness()` 函数读 JSONL、调 Icarus、算 pass@k。v2 完全重写为 **autotools + Makefile + 逐题文件系统**架构：

| 维度 | v1 | v2 |
|---|---|---|
| 数据格式 | 单个 JSONL | 每题 4 个独立文件 |
| 调度方式 | Python 进程池 | `configure` + GNU make（`make -j` 并行） |
| 中断续跑 | 不支持 | Make 的依赖检查天然支持 |
| 结果追溯 | 单个 `*_results.jsonl` | 每题独立目录 + `summary.txt/csv` |
| 模型接入 | 用户自备 completion JSONL | OpenAI API / NVIDIA NIM / manual 三种模式 |
| 后处理 | 无（用户负责） | 内置 `[BEGIN]..[DONE]`、fence、module 提取 + RTL-Coder 特殊处理 |
| 错误分析 | 仅 pass/fail | 11 类失败码 |

v2 的架构被 ChipBench 直接继承，成为后续 RTL benchmark 的标准范式。但这也意味着 v2 的代码和 v1 的代码是两个**不同的 evaluator**——它们对同一 completion 可能给出不同的 pass/fail 判定（因后处理逻辑不同、Icarus 调用参数不同、超时阈值不同）。

---

## 14. v1 vs v2 快速对照表

| 维度 | v1（ICCAD 2023） | v2（Revisiting, 2024/2025） |
|---|---|---|
| 任务形态 | 仅 code completion | code completion + **specification-to-RTL** |
| 数据集 | Human 156 + Machine 143 | **仅 Human 156**（machine 移除），修订 14 题 |
| 指标 | pass@1/5/10（$n=20$） | **pass@1**（低温 $n=1$ greedy / 高温 $n=20$ 通过比例均值） |
| ICL | 无 | **0--4 shot**，发现非单调效应 |
| 工作流 | Python 脚本直调 | **autotools + Makefile** 文件化 |
| 失败分析 | 二元 pass/fail | **11 类失败码**单标签分类 |
| 评测模型 | GPT-3.5、GPT-4、CodeGen 系 | 14 个新模型 |
| 主要发现 | GPT-4 最强；合成 SFT 数据有效 | Llama3.1 405B 0-shot 追平 GPT-4o；ICL + 采样协议改变排名 |
| 历史角色 | 确立"功能仿真 + pass@k"范式 | 确立"可维护回归场 + 失败归因"范式，ChipBench 脚手架 |

**一句话总结**：v1 证明了"LLM 能生成可仿真的 Verilog 并能量化评测"，v2 证明了"评测本身需要升级——任务难度、协议严谨性、可维护性和错误归因共同决定结论是否可信"。v1 是科学问题的提出者，v2 是工程方法的完善者；两者共享同一题目池（但 14 题已修订），v2 的分数提升是模型进步 + 协议变化 + 题目修订的混合结果，不能直接与 v1 数字对比。
