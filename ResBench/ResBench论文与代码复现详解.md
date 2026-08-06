# ResBench：论文、代码、数据与开放复现边界详解

> 论文：*ResBench: Benchmarking LLM-Generated FPGA Designs with Resource Awareness*  
> 作者：Ce Guo、Tong Zhao  
> 会议：HEART 2025，Kumamoto，2025-05-26 至 2025-05-28  
> DOI：`10.1145/3728179.3728192`  
> 本地论文：[HEART2025_ResBench.pdf](./HEART2025_ResBench.pdf)  
> 官方原文：<https://www.doc.ic.ac.uk/~cg1710/pub/2025/heart25tz.pdf>  
> 上游代码：<https://github.com/jultrishyyy/ResBench>  
> 本地审计日期：2026-08-02  
> 本地 commit：`a4a9644f9e2867be4c2569b0e3d96e19b596bba7`

---

```text
┌─────────────────────────────────────────────────────────────────┐
│ P1 任务定义                                                        │
├─────────────────────────────────────────────────────────────────┤
│ Input      │ 自然语言 FPGA 设计规格 + 固定模块头 + 隐藏/公开 testbench   │
├─────────────────────────────────────────────────────────────────┤
│ Output     │ 多个功能正确的 Verilog 候选 + 目标 FPGA 上的最小 LUT 资源   │
├─────────────────────────────────────────────────────────────────┤
│ Supervision│ testbench 行为仿真通过与否 + Vivado 综合后的 utilization report│
├─────────────────────────────────────────────────────────────────┤
│ Why-hard   │ 不仅要生成能过测试的 RTL，还要在功能等价候选中比较真实硬件资源；│
│            │ 单一 LUT 指标可能把成本转移到 DSP/BRAM，且需要商业综合工具链   │
└─────────────────────────────────────────────────────────────────┘
```

## 0. 先给结论

ResBench 值得分享，而且适合接在 VerilogEval、RTLLM、AutoChip、ChipSeek 之后讲。它把问题从“RTL 能不能过测试”推进到：

> 在功能正确的多个 RTL 候选里，哪个候选映射到指定 FPGA 后占用更少资源？

论文贡献和本地仓库实物基本对应：

- 56 个 Verilog 题目；
- 12 个应用类别；
- 每题包含自然语言规格、模块头和手写 testbench；
- 每个模型每题保存 15 个候选；
- 功能通过后，用 Vivado 2023.1 面向 `xc7z020clg400-1` 综合；
- 论文主资源指标是每题 15 个正确候选中的最小 LUT 数；
- 仓库发布了九个模型的 7,560 份历史候选、功能状态和大部分资源统计。

但“仓库有完整结果”不等于“当前代码能一键重跑”。本次代码审计发现两个会在主流程早期直接阻断的错误：

1. `setup.py` 从错误模块导入 `run_resource_usage`；
2. `functional_correctness.py` 的 `write_tcl()` 读取不存在的全局 `top_module`。

此外还有数据字段大小写漂移、失败日志过滤恒真的布尔表达式、Windows 专用 `vivado.bat`、无 timeout、九模型生成接口未开放、Pass@k 绘图语义与论文主指标不同等问题。

因此本项目当前应标为：

| 维度 | 状态 |
|---|---|
| 原论文可追溯 | 完成 |
| benchmark 数据可审阅 | 完成，56/56 题 |
| 作者历史输出可审阅 | 完成，9×56×15 = 7,560 份 |
| 论文 Table 4 静态重计数 | 完成，与发布 CSV 一致 |
| 论文 Table 5 静态核对 | 基本一致，但发现至少一处论文/CSV 数值差异 |
| 当前代码静态审计 | 完成 |
| 本轮重新调用九个模型 | 未做，也没有必要为整理文档重复调用 |
| 本轮 Vivado 仿真/综合 | 未做；当前环境和代码入口均不满足 |
| 复现等级 | **R1：论文—代码—数据/历史 artifact 可核，未完成新执行** |

机器可读审计记录见：[runs/static_audit_20260802.json](./runs/static_audit_20260802.json)。

---

## 1. 本文采用的证据口径

本文把证据分成四层，避免把论文结果、作者保存结果和本轮实测混写：

| 标签 | 含义 | ResBench 中的例子 |
|---|---|---|
| 论文报告 | 论文正文、图、表给出的主张 | GPT-o1-mini 在功能和 LUT win 数上领先 |
| 源码事实 | 当前 commit 的真实实现 | 温度 `1.5`、`top_p=0.75`、Vivado part 固定 |
| 数据事实 | 对 JSON/CSV 的只读统计 | 56 题、7,560 份候选、4,621 份标记为通过 |
| 本地执行 | 本轮真正启动模型/仿真/综合得到的日志 | 本轮没有新模型或 Vivado 执行 |

特别注意：

- [solutions/solutions.json](./solutions/solutions.json) 是作者随仓库发布的实验 artifact；
- [evaluate/solution_pass_analysis.csv](./evaluate/solution_pass_analysis.csv) 和 [evaluate/solution_resource_analysis.csv](./evaluate/solution_resource_analysis.csv) 是作者保存的汇总；
- 本文对它们做了静态重计数，但不能把这些数写成“2026-08-02 本地重跑 Vivado 得到”；
- 本项目目录没有单独的 `模型推理.md`，所以不存在需要重复执行的本地推理链；可复用的现成证据就是上述作者 artifact。

---

## 2. 论文要解决什么问题

### 2.1 传统 HDL benchmark 的盲点

典型 RTL 生成 benchmark 主要问两个问题：

1. 生成代码能否编译；
2. 生成代码能否通过 testbench 或形式验证。

这能排除语法错误和功能错误，却不能区分下面两个都正确的设计：

```text
实现 A：直接展开复杂算术表达式 → LUT 很多
实现 B：先做代数化简或使用 FPGA 原生 DSP → LUT 很少
```

在软件代码里，两个函数只要返回值相同就可能都被接受；在 FPGA 里，LUT、FF、DSP、BRAM 和 I/O 数决定设计是否能放入器件，以及还能复制多少并行实例。

### 2.2 ResBench 的核心问题

ResBench 同时评价：

```text
自然语言规格
    ↓
LLM 生成多个 Verilog 候选
    ↓
testbench 功能验证
    ├─ 失败：不进入资源比较
    └─ 通过：进入 FPGA 综合
                ↓
       LUT / FF / DSP / BRAM / IO
                ↓
      同题正确候选中取最小 LUT
```

这不是训练一种新模型，而是提出一套资源感知 benchmark 和评价框架。

---

## 3. 论文方法总览

论文 Figure 2 的工作流已从本地 PDF 中提取：

![ResBench 论文 Figure 2：生成、仿真、综合和资源统计](./figures/paper_fig2_workflow.png)

流程由三个数据对象贯穿：

| 数据对象 | 内容 | 当前仓库 |
|---|---|---|
| `problems.json` | 规格、固定模块头、testbench | 已开放 |
| generated Verilog | 每模型、每题、每次采样的完整 RTL | 已保存九模型历史输出 |
| `solutions.json` | RTL、功能状态、资源统计 | 已开放，但脚本默认期待它位于根目录 |

### 3.1 阶段 A：候选生成

每一题向模型提供：

- 自然语言 `Problem`；
- 不允许修改的 `Module header`；
- 只返回 `{"solution": "<verilog>"}` 的格式约束。

论文对所有模型设置温度 `1.5`，希望增加 15 个候选之间的多样性。

### 3.2 阶段 B：功能验证

每个候选与该题手工 testbench 一起进入 Vivado behavioral simulation。只有仿真输出包含 `All tests passed` 才标记为通过。

### 3.3 阶段 C：资源综合

通过功能验证的候选面向如下器件综合：

```text
AMD Zynq-7000
part = xc7z020clg400-1
Vivado = 2023.1（论文配置）
```

框架读取 utilization report，并提取：

- Slice LUTs；
- Slice Registers / FF；
- DSPs；
- Block RAM Tile；
- Bonded IOB。

### 3.4 阶段 D：同题资源比较

论文对第 `i` 个候选设计定义：

```text
LUT(d_i) = 实际 LUT 数，若设计功能正确且可综合
         = ∞，否则
```

然后：

```text
LUT_min = min(LUT(d_0), LUT(d_1), ..., LUT(d_14))
```

因此错误设计不会因为“什么逻辑都没实现，所以 LUT=0”而胜出。

---

## 4. benchmark 数据：56 题到底是什么

对 [problems.json](./problems.json) 的本地静态统计如下：

| 类别 | 题数 | 代表题 |
|---|---:|---|
| Combinational Logic | 8 | parity、mux、Gray code、decoder |
| Finite State Machines | 4 | 三状态 FSM、交通灯、电梯、售货机 |
| Mathematical Functions | 5 | 整数平方根、Fibonacci、模幂、整数 log2 |
| Basic Arithmetic Operations | 5 | 加、乘、绝对差、模、减 |
| Bitwise and Logical Operations | 4 | 位运算、移位、取反、循环移位 |
| Pipelining | 5 | 流水加法器、乘法器、累加器、FIR |
| Polynomial Evaluation | 5 | 二次/三次多项式与可化简表达式 |
| Machine Learning | 5 | 矩阵向量乘、ReLU、梯度下降、MSE、卷积 |
| Financial Computing | 4 | 复利、DDM、现值、汇率转换 |
| Encryption | 3 | Caesar、模加、Feistel |
| Physics | 4 | 自由落体、动能、势能、波长 |
| Climate | 4 | 碳足迹、热指数、AQI、辐照均值 |
| 合计 | **56** | 12 类 |

本地确认：

- 56 个 module 名均唯一；
- 56 题都有 testbench；
- 56 个 testbench 都包含 `All tests passed` marker；
- 55 个 testbench显式包含 `$finish`；
- 54 题使用字段 `Module header`；
- `ddm` 和 `feistel_cipher` 两题使用 `Module Header`。

最后一条不是排版差异，而是会直接影响生成脚本的 schema 漂移，后文单独分析。

### 4.1 数据不是只有“基础门电路题”

ResBench 的组会价值在于它主动加入高层应用表达式。例如：

- `compound_interest` 会引入幂和定点/整数近似；
- `mse_loss` 涉及多元素差值、平方与求平均；
- `heat_index` 有多项交叉项；
- `polynomial_5` 可把 `(a+b)^2-(a-b)^2` 化简成 `4ab`；
- 流水线题还要求时序/延迟语义，而不只是组合输出。

因此它确实能制造不同实现之间的资源分歧，但也会放大位宽、溢出、定点口径和 testbench 覆盖不足的问题。

---

## 5. 论文 Figure 1：为什么“0 LUT”不等于“零成本”

论文用 `polynomial_5` 对比两种实现。PDF 中两张子图已分别提取：

| Qwen-2.5 候选 | GPT-4 候选 |
|---|---|
| ![Qwen 候选](./figures/paper_fig1_qwen.png) | ![GPT-4 候选](./figures/paper_fig1_gpt4.png) |
| 论文报告：213 LUT | 论文报告：0 LUT + 1 DSP |

GPT-4 先把：

```text
(a+b)^2 - (a-b)^2
```

化简为：

```text
4ab
```

从而让乘法映射到 DSP，而不是大量 LUT。

这个例子既说明 ResBench 有价值，也暴露了指标解释边界：

- 只最小化 LUT，可能把成本转移到 DSP；
- `0 LUT` 不等于硬件无成本；
- 在 DSP 紧张的设计上，`0 LUT + 1 DSP` 未必比若干 LUT 更优；
- 更完整的评价应使用多目标 Pareto front，而不是只给单一 LUT win。

论文承认框架能提取其他资源，但主实验的排序仍以 LUT 为主。

---

## 6. 评价模型与采样配置

论文 Table 4 和发布 artifact 覆盖九个保留模型：

| 类型 | 模型 |
|---|---|
| 通用模型 | GPT-3.5-turbo、GPT-4、GPT-4o、GPT-o1-mini、Llama 3.1、Qwen-Max、Qwen-Plus |
| 代码模型 | Qwen2.5-Coder-32B-Instruct、Codestral |
| HDL 专用模型 | VeriGen 做过测试，但论文称无法为全部题产生合法 Verilog，后续表中省略 |

统一设置：

| 参数 | 论文/代码 |
|---|---|
| 每题候选数 | 15 |
| 温度 | 1.5 |
| 当前生成脚本 `top_p` | 0.75 |
| 当前生成脚本 `max_tokens` | 3000 |
| SystemVerilog | prompt 明确要求不要使用 |
| 返回格式 | JSON，键为 `solution` |

有两个命名细节必须保留原样说明：

1. 论文正文一处写 `Llama3.1-450B`，Table 4 和发布 JSON 均写 `llama3.1-405B`；结合真实模型命名，应以 405B artifact 为准，并把 450B 视为论文文字错误。
2. `gpt-4`、`gpt-4o` 等没有快照日期或 provider 请求 ID，服务端模型版本不可冻结，今天重调 API 也不是严格复现 2025 年结果。

---

## 7. 论文功能结果与发布 artifact 重计数

论文不用标准 Pass@k 作为 Table 4 主指标，而是直接统计每类的：

```text
pass / 可综合但功能错误 / synthesis error
```

每模型总样本数都是：

```text
56 题 × 15 候选 = 840
```

对发布 [solutions.json](./solutions/solutions.json) 只读重计数得到：

| 模型 | pass | 功能错误* | “synthesis error”* | 通过率 | 至少一个候选通过的题数 |
|---|---:|---:|---:|---:|---:|
| GPT-3.5-turbo | 362 | 147 | 331 | 43.10% | 38/56 |
| GPT-4 | 542 | 188 | 110 | 64.52% | 46/56 |
| GPT-4o | 619 | 156 | 65 | 73.69% | 51/56 |
| GPT-o1-mini | **631** | 131 | 78 | **75.12%** | **51/56** |
| Llama3.1-405B | 460 | 161 | 219 | 54.76% | 48/56 |
| Qwen-Max | 535 | 173 | 132 | 63.69% | 48/56 |
| Qwen-Plus | 425 | 178 | 237 | 50.60% | 47/56 |
| Qwen2.5-Coder-32B-Instruct | 505 | 102 | 233 | 60.12% | 48/56 |
| Codestral | 542 | 136 | 162 | 64.52% | 42/56 |
| 总计 | **4,621** | **1,372** | **1,567** | 61.12% | — |

带星号的两列是按仓库 `count_pass.py` 的字符串规则重现的分类，不是本轮重新执行 Vivado 后对错误类型的独立判断。

这些数与作者发布的 [solution_pass_analysis.csv](./evaluate/solution_pass_analysis.csv) 以及论文 Table 4 对应。

### 7.1 论文的主要观察

- GPT-o1-mini 总通过数最高，并在 12 个类别中拿到最多功能 win；
- 组合逻辑对多数模型相对容易；
- 流水线、金融、加密等类别更困难且波动更大；
- GPT-3.5-turbo 在论文的 Pipelining 类别中 75 个候选无一通过；
- 数学函数中既有大量功能错误，也有大量前端/仿真失败。

### 7.2 不能把上述通过率直接叫 Pass@1

`631/840` 是 840 个独立候选中通过的比例，不是按 56 道题估计的标准 HumanEval pass@1。

仓库另有 [evaluate/plot_pass.py](./evaluate/plot_pass.py)，它把每题保存顺序中的前 `k` 个候选拿出来，只要其中一个通过就把该题记为 1。对保存顺序重算可得到：

| 模型 | ordered pass@1 | ordered pass@5 | ordered pass@10 | ordered pass@15 |
|---|---:|---:|---:|---:|
| GPT-3.5-turbo | 39.29% | 64.29% | 64.29% | 67.86% |
| GPT-4 | 66.07% | 76.79% | 78.57% | 82.14% |
| GPT-4o | 78.57% | 85.71% | 91.07% | 91.07% |
| GPT-o1-mini | 69.64% | 89.29% | 89.29% | 91.07% |
| Llama3.1-405B | 53.57% | 80.36% | 85.71% | 85.71% |
| Qwen-Max | 66.07% | 78.57% | 83.93% | 85.71% |
| Qwen-Plus | 55.36% | 73.21% | 80.36% | 83.93% |
| Qwen2.5-Coder | 58.93% | 73.21% | 82.14% | 85.71% |
| Codestral | 64.29% | 71.43% | 75.00% | 75.00% |

这里特意写 `ordered`，因为脚本不是从 `n=15` 样本中计算无偏估计公式，而是直接取保存数组的前 `k` 项。论文也明确说 Table 4 主分析不用 Pass@k。

仓库保存的总体曲线如下，但它是上游 artifact，不是本轮新绘制：

![作者发布的 overall pass@k 图](./figures/overall_pass_at_k.png)

---

## 8. 资源结果怎么读

论文 Table 5 只展示不同模型之间 LUT 最小值有差异的题，完全相同的题为节省篇幅被省略。

论文报告的 LUT win 数：

| 模型 | win 数 |
|---|---:|
| GPT-o1-mini | **19** |
| GPT-4 | 12 |
| Llama3.1-405B | 11 |
| GPT-4o | 10 |
| Qwen-Max | 10 |
| Qwen-Plus | 9 |
| Codestral | 8 |
| GPT-3.5-turbo | 7 |
| Qwen2.5-Coder | 7 |

这里的 win 是“某题取得表中最小 LUT”计数；并列最小值可以让多个模型都计入。

### 8.1 论文与发布 CSV 的一处明确差异

对 Table 5 和 [solution_resource_analysis.csv](./evaluate/solution_resource_analysis.csv) 逐项核对时，发现：

| 题目 | 模型 | 论文 Table 5 | 发布 CSV |
|---|---|---:|---:|
| `power` | GPT-4o | 93 LUT | **74 LUT** |

因此不能简单声称“CSV 与论文 Table 5 字节级一致”。可能原因包括：

- 论文排版前后重新跑过综合；
- 保存 JSON/CSV 更新过，但论文表未同步；
- 不同候选集合或 Vivado run 状态；
- 人工转表错误。

仓库没有每次 Vivado 综合的原始 `.rpt`、日志、Vivado seed 和 run manifest，当前无法从最低层证据判定哪一个值才是最终权威值。

### 8.2 78 个功能通过候选没有数值 LUT

发布 artifact 中：

```text
功能 pass == true                     4,621
同时有 numeric optimized.LUT         4,543
pass 但没有 numeric optimized.LUT        78
```

这些候选在资源汇总中会表现为无有效值/无穷大。它说明功能通过不保证后续综合成功，也说明应该把下面三个状态分开存：

```text
simulation_pass
synthesis_pass
resource_report_parsed
```

当前 schema 主要依赖 `pass` 字符串和空字典，状态表达不够明确。

---

## 9. 从入口到结果：当前代码真实调用链

README 推荐的逻辑入口是 [setup.py](./setup.py)：

```text
setup.py
  ├─ -generate_solutions MODEL K API_KEY
  │    └─ generate_solutions.py
  ├─ -functional_correctness
  │    ├─ functional_correctness.py
  │    ├─ evaluate/count_pass.py
  │    └─ evaluate/plot_pass.py
  └─ -resource_usage
       ├─ resource_usage.py（设计意图）
       └─ evaluate/count_resource.py
```

但当前代码实际在 import 阶段已经偏离这张设计图，详见第 14 节。

### 9.1 文件—职责对照

| 文件 | 设计职责 | 是否含论文关键逻辑 |
|---|---|---|
| [generate_solutions.py](./generate_solutions.py) | OpenAI chat 调用和 JSON 增量保存 | 是，prompt/采样参数 |
| [functional_correctness.py](./functional_correctness.py) | 生成 Vivado simulation Tcl、判定功能 | 是，testbench 和 pass marker |
| [resource_usage.py](./resource_usage.py) | 生成 synthesis Tcl、解析 utilization | 是，part 和资源字段 |
| [evaluate/count_pass.py](./evaluate/count_pass.py) | 按类别汇总三种功能状态 | 是，对应 Table 4 |
| [evaluate/count_resource.py](./evaluate/count_resource.py) | 每题每模型取最小 LUT | 是，对应 Table 5 |
| [evaluate/plot_pass.py](./evaluate/plot_pass.py) | ordered first-k 曲线和热图 | 论文主表之外的辅助分析 |
| [problems.json](./problems.json) | 56 题输入和 testbench | benchmark 核心资产 |
| [solutions/solutions.json](./solutions/solutions.json) | 九模型历史结果 | 论文结果的主要开放 artifact |

---

## 10. 生成阶段源码详解

### 10.1 Prompt 结构

`call_LLMs()` 拼接：

```text
System：你是 Verilog coding assistant，只返回带 solution 键的 JSON
User：
  - 不支持 SystemVerilog
  - 给出 Problem
  - 给出固定 Module header
  - 要求高效实现
  - 再次要求 JSON only
```

该 prompt 没有把 testbench 给模型，符合 benchmark 隐藏判题逻辑；但 testbench 本身已公开在 `problems.json`，所以公开后再做模型比较必须考虑数据污染与人工针对性优化。

### 10.2 循环顺序

源码循环为：

```python
for _ in range(k):
    for category in prompt_data:
        for problem in category:
            call model once
```

所以每题 `solutions` 数组第 1、2、…、15 项来自 15 个全题轮次，而不是对同一题连续采 15 次。这会让 provider 时间漂移和限流状态跨题交织。

### 10.3 保存策略

每得到一个响应就立刻覆盖写回 `solutions.json`。优点是长任务中断后已有数据不丢；缺点是：

- 没有 run ID；
- 没有 timestamp；
- 没有请求参数随样本保存；
- 没有 response model/version；
- 没有 token usage；
- 没有 seed；
- 重跑同一模型名会继续 append，无法自动区分实验批次。

### 10.4 多模型开放边界

当前脚本只构造：

```python
OpenAI(api_key=api_key)
```

没有 `base_url`、Anthropic、DashScope、Together、Mistral 或本地 Hugging Face adapter。README 也说明标准脚本目前只支持 OpenAI GPT。

因此九模型完整生成实验所用的 provider-specific 调用代码没有全部开放。传入 `llama3.1-405B` 或 `qwen-max` 字符串并不会让标准 OpenAI endpoint 自动拥有这些模型。

---

## 11. 功能验证阶段源码详解

### 11.1 生成的 Vivado Tcl

源码意图是：

```tcl
create_project temp_project ./temp_project -force -part xc7z020clg400-1
add_files temp.v
add_files -fileset sim_1 testbench.v
set_property top <testbench module> [get_filesets sim_1]
launch_simulation -simset sim_1 -mode behavioral
run 3000ns
```

### 11.2 Pass 判定

当前唯一通过条件是：

```python
"All tests passed" in stdout_plus_stderr
```

它没有同时要求：

- subprocess return code 为 0；
- 没有 compile/elaboration error；
- testbench 正常到达 `$finish`；
- marker 只出现一次且来自预期 testbench。

对当前手写 testbench 来说 marker 规则简单实用，但不等价于一个安全、强隔离、抗提示注入的评价器。

### 11.3 “Sandbox Evaluation” 的实际含义

论文图中写有 Sandbox Evaluation，但当前源码只是把候选写到固定的工作目录文件，并直接启动 Vivado：

```text
temp.v
testbench.v
run_testbench.tcl
temp_project/
```

没有容器、系统调用过滤、每样本临时目录或权限隔离。因此这里更准确的理解是“自动化评价区”，不应解释为安全意义上的恶意代码 sandbox。

---

## 12. 资源统计阶段源码详解

### 12.1 综合脚本

`resource_usage.py` 对通过候选写出：

```tcl
create_project temp_project -force -part xc7z020clg400-1
add_files temp.v
set_property top <从代码 regex 提取的 module> [current_fileset]
synth_design -top <module>
report_utilization -file resource_usage.rpt
```

它没有实现：

- 时钟约束；
- I/O delay；
- 明确的 synthesis strategy；
- seed 或 directive；
- place/route；
- timing、功耗或拥塞评价。

所以 ResBench 是“综合后资源估计 benchmark”，不是完整 FPGA implementation PPA benchmark。

### 12.2 `optimized` 与 `primitives`

保存结构有两套统计：

```json
{
  "optimized": {"LUT": 2, "FF": 0, "DSP": 0, "BRAM": 0, "IO": 9},
  "primitives": {"LUT": 2, "FF": 0, "DSP": 0, "BRAM": 0, "IO": 9}
}
```

主表使用 `optimized.LUT`。

`parse_primitives_section()` 实际只累加：

- 名称以 `LUT` 开头的 primitive；
- `IBUF` 和 `OBUF`。

FF、DSP、BRAM 在 primitives 分支中没有具体解析规则，默认仍是 0。不能把 `primitives.FF/DSP/BRAM=0` 当成严格测量结果。

---

## 13. 论文、数据和代码的逐项对应

| 论文概念 | 当前实现/资产 | 对应程度 |
|---|---|---|
| 56 题、12 类 | `problems.json` | 完整对应 |
| 规格 + 模块头 + testbench | 每个问题字典 | 54 题字段一致，2 题键名漂移 |
| 每题 15 候选 | `solutions.json` | 九模型全部为 15 |
| 温度 1.5 | `generate_solutions.py` | 对应 |
| 九模型主表 | 历史 artifact | 对应；完整多 provider runner 不在仓库 |
| Vivado 2023.1 | README/论文说明 | 代码不检查具体版本 |
| Zynq XC7Z020 part | 两个 Tcl 模板 | 对应 |
| 功能通过才综合 | `pass == "true"` gate | 对应设计意图 |
| 错误候选 LUT=∞ | 空资源字典 → 汇总时默认 inf | 间接对应 |
| Table 4 | `count_pass.py` + pass CSV | 计数对应 |
| Table 5 | `count_resource.py` + resource CSV | 基本对应；发现 `power/GPT-4o` 差异 |
| 自动化全流程 | `setup.py` | 设计上存在，当前代码不能按 README 直接启动 |

---

## 14. 代码审计发现的关键问题

### 14.1 阻断级：`setup.py` 从错误模块导入

入口写的是：

```python
from functional_correctness import run_functional_correctness, run_resource_usage
```

但 `run_resource_usage()` 定义在 [resource_usage.py](./resource_usage.py)，不在 [functional_correctness.py](./functional_correctness.py)。

因此 README 的标准 `python setup.py ...` 在 import 阶段就不能按当前源码工作。

正确设计应分别导入：

```python
from functional_correctness import run_functional_correctness
from resource_usage import run_resource_usage
```

本文只记录问题，没有擅自修改上游研究代码，也没有把修补后的结果混成作者原始实现。

### 14.2 阻断级：`top_module` 作用域错误

`write_tcl()` 直接引用 `top_module`，但 `run_functional_correctness()` 中赋值的是函数局部变量：

```python
top_module = extract_top_module_name(...)
write_tcl()
```

局部变量不会自动成为模块全局变量，因此 `write_tcl()` 按当前实现会遇到 `NameError`。

稳妥接口应是：

```python
def write_tcl(top_module):
    ...
```

### 14.3 数据级：两个模块头字段大小写不一致

生成器读取：

```python
item.get("Module header", "")
```

但两题使用 `Module Header`：

| 类别 | module |
|---|---|
| Financial Computing | `ddm` |
| Encryption | `feistel_cipher` |

按当前生成器，这两题会把空字符串作为固定模块头发给模型。

### 14.4 错误日志过滤表达式恒真

失败分支写成：

```python
line for line in output_log.split("\n") if "error" or "fail" in line.lower()
```

因为非空字符串 `"error"` 永远为真，所有日志行都会被保留。预期表达式应是：

```python
if "error" in line.lower() or "fail" in line.lower()
```

结果影响：

- `pass` 字段被塞入完整 Vivado 日志；
- `solutions.json` 体积增大；
- 错误分类依赖日志里是否恰好出现特定短语；
- 同一种错误可能产生大量不同字符串。

### 14.5 “synthesis error” 分类与真实阶段并不完全等价

`count_pass.py` 把包含：

```text
Detected error while running simulation
```

的状态计为 `syntax_error`，论文表头又称 `synthesis error`。

然而功能脚本运行的是 Vivado behavioral simulation 前端，没有先单独执行 `synth_design`。这里可能混合：

- Verilog 语法错误；
- elaboration 错误；
- testbench 连接错误；
- simulator 启动错误；
- Vivado 环境错误。

所以该列更准确的名字应是“未进入有效功能比较的前端/仿真失败”，而不是严格的 FPGA synthesis failure。

### 14.6 Windows 路径绑定

两条 runner 都使用：

```python
os.path.join(os.environ["vivado"], "vivado.bat")
```

这绑定 Windows batch launcher。Linux 上通常是 `vivado` 可执行文件，而不是 `vivado.bat`。

### 14.7 无 timeout 和独立工作区

两次 `subprocess.run()` 都没有 timeout，并复用固定文件和固定 project 名。如果某题：

- 仿真不结束；
- Vivado 卡住；
- 残留 project 锁；
- 上一次 report 未清理；

整批任务可能停住或读到陈旧产物。

### 14.8 `setup.py` 的组合参数边界

入口的嵌套逻辑还有两个边界：

- `-generate_solutions` 与 `-resource_usage` 同时给出、但不加 `-functional_correctness` 时，不会进入资源分析；
- 不生成、同时给 `-functional_correctness -resource_usage` 时，资源函数会在 functional 嵌套分支运行一次，随后在独立 resource 分支再运行一次。

### 14.9 绘图脚本把 Pass@15 固化后循环写 15 次

`plot_pass.py` 先构建：

```python
category_pass_k[cat][llm] = kdict[15]
```

随后 `for k in 1..15`，却没有按 `k` 重建数据，所以：

```text
per_category_pass_k1_heatmap.png
...
per_category_pass_k15_heatmap.png
```

理论上都会画同一份 Pass@15 热图，只是文件名不同。

### 14.10 当前脚本不会保存总体曲线

`overall_pass_at_k.png` 的 `savefig` 代码被注释。仓库现有图片应理解为作者先前运行或手动调整后提交的 artifact，而不是当前默认脚本一运行必然生成。

### 14.11 没有根 LICENSE

本地 commit 根目录未见 `LICENSE`。论文允许学术阅读不等于代码自动拥有明确的开源许可。使用数据和代码进行再发布前应联系作者或等待补充许可证。

---

## 15. Testbench 与 benchmark 有效性边界

### 15.1 功能正确只相对于有限测试向量

每题 testbench 是手写 directed tests，不是形式等价证明。一个候选可以：

- 只覆盖公开测试向量；
- 在未测输入上错误；
- 对 X/Z、溢出、除零、负数边界处理错误；
- 流水线延迟与测试预期偶然对齐。

因此论文的 `pass` 应读成：

> 通过 ResBench 当前公开 testbench。

而不是：

> 对所有输入和时序状态都已证明等价。

### 15.2 公开 testbench 的污染风险

`problems.json` 直接包含完整 testbench。发布 benchmark 后：

- 模型训练语料可能收录仓库；
- 提示工程可以针对 testbench；
- 新模型与论文模型的可比性会随时间下降。

后续版本应采用：

```text
公开规格 + 少量公开 tests
隐藏 tests
形式属性或 reference equivalence
版本化污染声明
```

### 15.3 LUT 比较必须先保证语义和时序一致

对流水线设计，仅对最终数值做有限比较可能允许：

- 延迟级数不一致；
- 吞吐率不一致；
- valid/ready 行为不一致；
- 复位语义不一致。

资源比较只有在接口、功能、latency 和 throughput 约束都一致时才公平。

---

## 16. 为什么不能用 Yosys 数字直接替代论文结果

旧 [模型梳理.md](./模型梳理.md) 曾写“Yosys/Vivado 类流程”，但当前论文和当前代码的主链都是 Vivado；没有 Yosys runner。

可以另写 Yosys 适配器做开源 smoke，但结果只能标为：

```text
开源替代流程验证
```

不能直接与论文 Table 5 数值比较，原因包括：

- tech mapping 不同；
- LUT 架构和 pack 规则不同；
- DSP inference 不同；
- 优化 pass 不同；
- target library 不同；
- Vivado 版本和器件 family 特定策略不同。

对于组会，最好的对照不是“Yosys 也给一个 LUT 数”，而是比较同一候选在：

```text
Vivado/Zynq-7000
Yosys/generic cells
Yosys+nextpnr/具体 FPGA family
```

下的排名是否稳定。

---

## 17. 当前本地可复现能力

### 17.1 已经具备

- 原论文 PDF；
- 论文 Figure 1、Figure 2 的本地图片；
- 56 题完整 JSON；
- 九模型 7,560 份历史输出；
- 功能三分类 CSV；
- 资源最小值 CSV；
- 总体 first-k 曲线 artifact；
- 生成、功能验证、综合和汇总代码；
- 本文和机器可读静态审计。

### 17.2 缺失或不可冻结

- 九模型统一 provider runner；
- 论文 API endpoint、模型快照、请求 ID、seed；
- VeriGen 失败输出；
- Vivado 2023.1 可执行环境；
- 可确认一致的 Vivado license；
- 每候选原始 simulation log；
- 每候选 synthesis log 和 utilization report；
- run manifest；
- 根目录软件许可证；
- 能按 README 直接工作的 CLI。

### 17.3 为什么本轮没有再跑模型

本轮目标是整理已有论文和开源代码。ResBench 已保存完整九模型历史候选；重新请求今天的闭源 API：

- 成本高；
- 模型版本已漂移；
- 无法还原论文 snapshot；
- 不会修复 Vivado 评价入口；
- 反而容易把“当前复测”和“论文结果”混淆。

所以本文优先对作者 artifact 做全量静态重计数，这是更符合当前任务的证据。

---

## 18. 如果后续要真正重跑，正确顺序是什么

### 阶段 1：先修复 runner，不调用模型

1. 修正 `run_resource_usage` 导入；
2. 给 `write_tcl(top_module)` 显式传参；
3. 统一 `Module header` schema；
4. 把错误过滤表达式改正确；
5. 给 Vivado 命令加 return-code、timeout 和日志路径；
6. 每个样本建立独立临时目录；
7. 保存 Vivado 版本、part、strategy、seed；
8. 为 simulation、synthesis、report parsing 建独立状态字段。

### 阶段 2：只用作者保存候选验证评价器

先复制而不是移动作者 artifact：

```bash
cd /mnt/d/AI4eda/ResBench
cp solutions/solutions.json ./solutions.json
```

再分小批检查：

```text
1 个组合逻辑通过样例
1 个功能错误样例
1 个语法/elaboration 错误样例
1 个 DSP inference 样例
1 个流水线样例
```

只有状态和资源 report 都符合预期，才扩大到 7,560 份。

### 阶段 3：再接新模型

新模型 adapter 至少要保存：

```json
{
  "provider": "...",
  "requested_model": "...",
  "resolved_model": "...",
  "temperature": 1.5,
  "top_p": 0.75,
  "seed": null,
  "timestamp": "...",
  "prompt_sha256": "...",
  "raw_response": "...",
  "parsed_solution": "..."
}
```

### 阶段 4：最终做多目标资源评价

建议同时报告：

- functional pass rate；
- synthesis success rate；
- ordered success 和标准无偏 pass@k，名称分开；
- LUT、FF、DSP、BRAM；
- 时钟频率约束下 WNS/TNS；
- 资源 Pareto front；
- 失败题和资源异常题的定性案例。

---

## 19. 与其他本地项目怎么串起来讲

### 19.1 与 VerilogEval

```text
VerilogEval：自然语言 → RTL → testbench pass
ResBench：   自然语言 → 多个正确 RTL → FPGA resource differentiation
```

ResBench 不是替代 VerilogEval，而是在功能正确之后增加一层硬件代价。

### 19.2 与 RTLLM

RTLLM 已经讨论 functionality、syntax 和 PPA 多目标，但更多围绕设计质量和 benchmark 评估；ResBench 把 FPGA LUT differentiation 做成 56 题统一数据格式并发布九模型候选。

### 19.3 与 AutoChip

AutoChip 在生成环中反馈编译/仿真结果并迭代修复；ResBench 不修模型，而是对一次性高温采样的多个候选做统一评测。

### 19.4 与 ChipSeek

ChipSeek 把 EDA reward 带入 RL/CDPO 训练；ResBench 的 LUT 评价可以作为 reward 原型，但单一 LUT 会诱导“把资源转移到 DSP”的目标投机，必须升级成多资源约束。

---

## 20. 最值得组会讨论的五个问题

1. **功能正确之后，RTL benchmark 应如何评价硬件质量？**
2. **单一 LUT 最小化会不会奖励 DSP/BRAM 转移，而不是真正优化？**
3. **公开 testbench 后，如何防止模型记忆和定向过拟合？**
4. **商业 Vivado 指标和开源 Yosys/nextpnr 指标怎样建立可比较口径？**
5. **论文框架图完整，但当前开源入口有阻断错误，artifact verification 与 full reproduction 应如何分级？**

---

## 21. 推荐的组会讲法

### 21.1 15 分钟版本

| 时间 | 内容 |
|---:|---|
| 2 分钟 | VerilogEval 只看功能的盲点 |
| 3 分钟 | 56 题、12 类和三阶段流程 |
| 3 分钟 | `(a+b)^2-(a-b)^2` 的 213 LUT 对 0 LUT+1 DSP 案例 |
| 3 分钟 | 九模型功能结果和 GPT-o1-mini 领先 |
| 2 分钟 | 代码审计：入口、作用域、schema、timeout |
| 2 分钟 | 单 LUT 指标边界和下一步多目标 benchmark |

### 21.2 一句话标题

> **“从能用到好用：ResBench 如何把 LLM 生成 RTL 的评价推进到 FPGA 资源感知”**

### 21.3 不建议的讲法

- 不要说“GPT-o1-mini 的 PPA 最优”：论文主要是综合后 LUT，不含完整 timing/power；
- 不要说“7,560 份都在本地重新跑过”：它们是作者发布 artifact；
- 不要把 ordered first-k 曲线直接叫标准 pass@k estimator；
- 不要把 `0 LUT` 解释为零资源；
- 不要说当前仓库一键可复现，入口有明确阻断错误。

---

## 22. 可复现性分级

本文沿用全局索引的分级：

| 等级 | 定义 | ResBench |
|---|---|---|
| R0 | 只有论文/说明，核心资产不足 | 已超过 |
| R1 | 论文、代码、数据或历史 artifact 可静态核对 | **当前等级** |
| R2 | 至少一个代表样例在本地重新执行成功 | 本轮未达到 |
| R3 | 作者保存产物被本机独立工具全量验证 | 未达到；缺 Vivado 重跑和底层 logs |
| R4 | 论文主表同配置完整重算 | 未达到 |

虽然发布结果很完整，但由于没有本轮新 Vivado 执行，不能仅凭静态重计数把等级抬到 R2/R3。

---

## 23. 文件阅读导航

建议按下面顺序阅读：

1. [HEART2025_ResBench.pdf](./HEART2025_ResBench.pdf)：方法和论文结果；
2. [problems.json](./problems.json)：56 题真实规格和 testbench；
3. [generate_solutions.py](./generate_solutions.py)：prompt 与采样；
4. [functional_correctness.py](./functional_correctness.py)：功能判定；
5. [resource_usage.py](./resource_usage.py)：综合和资源解析；
6. [solutions/solutions.json](./solutions/solutions.json)：历史候选；
7. [evaluate/count_pass.py](./evaluate/count_pass.py)：Table 4 统计；
8. [evaluate/count_resource.py](./evaluate/count_resource.py)：Table 5 统计；
9. [evaluate/plot_pass.py](./evaluate/plot_pass.py)：first-k 辅助曲线；
10. [runs/static_audit_20260802.json](./runs/static_audit_20260802.json)：本文统计的机器可读摘要。

---

## 24. 最终判断

ResBench 的研究价值是真实的：它让 RTL 生成评价从“过不过 testbench”走向“正确实现之间的 FPGA 资源差异”，而且 56 题、九模型、7,560 份候选和资源数据都已开放，足以支撑一场扎实的组会分享。

同时，它也是一个很好的 artifact 审计案例：

- 论文方法图清楚；
- 数据和历史结果很完整；
- Table 4 可以从发布 JSON 静态重计数；
- 但当前主入口不能按 README 直接运行；
- 多 provider 生成代码缺失；
- 资源原始报告缺失；
- 单 LUT 指标存在资源转移问题；
- 论文 Table 5 与发布 CSV 至少有一处数值漂移。

最准确的总结是：

> **ResBench 已达到论文—代码—数据—作者 artifact 的深度可审阅状态，适合组会分享；当前尚未达到论文同配置一键重跑或完整 Vivado 复现。**

---

## 25. P7 组件一句话角色

| 组件 | 一句话角色 |
|---|---|
| `problems.json` | 承载 56 道题目规格、固定模块头和手写 testbench 的 benchmark 核心输入。 |
| `generate_solutions.py` | 按自然语言 prompt 向模型采样 15 个 Verilog 候选并增量保存到 `solutions.json`。 |
| `functional_correctness.py` | 为每个候选生成 Vivado behavioral simulation Tcl 并判定是否输出 `All tests passed`。 |
| `resource_usage.py` | 对通过仿真的候选生成综合 Tcl，调用 Vivado 并解析 utilization report。 |
| `count_pass.py` / `count_resource.py` | 分别把仿真状态和资源数据汇总成论文 Table 4 与 Table 5 的统计表。 |

---

## 26. 讨论问题

1. 如果最小化 LUT 会诱导模型把算术运算推给 DSP，那么资源感知 benchmark 应如何设计多目标代价函数才能避免指标博弈？
2. 在公开 testbench 的情况下，怎样区分“模型真正理解了设计规格”与“针对测试向量过拟合/定向优化”？
3. 当前开源入口存在阻断级 bug 且缺少原始 Vivado 日志，artifact 审计和完整可复现之间应如何分级表述才最严谨？


