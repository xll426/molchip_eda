# OpenLLM-RTL 论文深度讲解

> **OpenLLM-RTL: Open Dataset and Benchmark for LLM-Aided Design RTL Generation (Invited Paper)**
> Shang Liu, Yao Lu, Wenji Fang, Mengming Li, Zhiyao Xie
> Hong Kong University of Science and Technology (HKUST)
> ICCAD 2024 (Invited) · arXiv: 2503.15112 v1 (Mar 19, 2025)
> 原文：[2503.15112_OpenLLM-RTL.pdf](./2503.15112_OpenLLM-RTL.pdf)
> 代码：RTLLM-2.0: <https://github.com/hkust-zhiyao/RTLLM> | AssertEval: <https://github.com/hkust-zhiyao/AssertLLM> | RTLCoder-Data: <https://github.com/hkust-zhiyao/RTL-Coder>

---

## 1. 一句话定位

**OpenLLM-RTL 不是一个新模型，而是一篇把三条独立工作线整合起来的 ICCAD 2024 invited paper**——它系统地发布了 (1) RTLLM-2.0（50 题 RTL 生成评测集），(2) AssertEval（18 题 SVA 断言生成评测集），(3) RTLCoder-Data（80K raw + 7K verified 训练样本），构建了从训练数据→RTL 生成评测→验证评测的开源全栈框架。实验表明，用 80K raw 数据微调 DeepSeek-Coder-6.7B 可以在 Eval-Machine pass@1 上超越 GPT-4（64.7% vs 60.0%），且 7K verified 数据的训练效果超过 50K raw 数据。

这句话里的技术承重点：

1. **三个组件，一个框架** — RTLLM-2.0 覆盖「生成的 RTL 好不好」，AssertEval 覆盖「生成的验证断言好不好」，RTLCoder-Data 覆盖「训练数据从哪来」。三者覆盖了 LLM-assisted RTL 设计的完整生命周期。
2. **数据质量 > 数据数量** — 使用 assertion-based 自动化功能检查筛选出的 7K verified 数据，训练效果超过 50K raw 数据，训练时间不到后者的 20%。
3. **小模型可以超越大模型** — 7B 参数的 DeepSeek-Coder，用 80K 数据微调后在 Eval-Machine pass@1 上比 GPT-4 高 4.7 个百分点。
4. **自动化数据功能验证** — 用 LLM 生成 assertion + 商业 FPV 工具验证的方式来检查训练数据中 code 的功能正确性，这是一个前人未探索过的方向。

---

## 2. EDA 阶段映射（①-⑰）

OpenLLM-RTL 的三个组件分别作用于不同阶段：

| 阶段 | RTLLM-2.0 | AssertEval | RTLCoder-Data | 说明 |
|------|:---:|:---:|:---:|------|
| **① RTL 设计** | ✅ **核心** | ❌ | ✅ 辅助 | RTLLM-2.0 评测 LLM 生成 RTL 的能力；RTLCoder-Data 为训练 RTL 生成模型提供数据 |
| **② RTL 功能仿真** | ✅ | ❌ | ❌ | RTLLM-2.0 用配套 testbench 验证功能 |
| **③ 逻辑综合** | ✅ | ❌ | ❌ | 语法检查 + PPA 提取 |
| **⑥ 形式验证** | ❌ | ✅ **核心** | ✅ 辅助 | AssertEval 用 FPV 评测 assertion 质量；RTLCoder-Data 用 FPV 做数据质量筛选 |
| ④ 门级仿真 | ❌ | ❌ | ❌ | — |
| ⑤ STA | ❌ | ❌ | ❌ | — |
| ⑦~⑰ 物理设计到流片 | ❌ | ❌ | ❌ | — |

**覆盖率：3/17。** OpenLLM-RTL 的独特价值在于把 RTL 生成（阶段 ①）和 RTL 验证（阶段 ②/⑥）放在同一个框架下评估，同时提供了填补训练数据空白的 RTLCoder-Data。

> 关键边界：AssertEval 不评估 LLM 生成的 RTL 本身——它评估 LLM 从设计规格生成 SVA 断言的能力。这两件事在芯片流程中是完全不同的角色（designer vs. verification engineer）。

---

## 3. 输入 / 输出

### 3.1 组件 1：RTLLM-2.0（RTL 生成评测）

输入与 RTLLM v1.0 相同：自然语言设计规格 `design_description.txt`。输出为三级评测结果（Syntax → Functionality → Quality）。详见 [论文深度讲解_RTLLM.md](./论文深度讲解_RTLLM.md)。

RTLLM-2.0 与 v1.0 的关键差异：

- 题目数：30 → 50
- 分类体系：从 Arithmetic/Logic 两类平铺 → 四大类（Arithmetic / Memory / Control / Miscellaneous）
- 新增设计示例：BCD 加法器、64 位减法器、3-bit/4-bit 比较器、fixed_point_adder/subtractor、float_multi、LFSR、barrel_shifter、LIFO buffer、ROM、ring_counter、up_down_counter、sequence_detector、clkgenerator、instr_reg、square_wave、freq_divbyeven/odd/frac

### 3.2 组件 2：AssertEval（断言生成评测）

**输入**：18 个开源设计的完整规格文档（specification document，含功能描述、微架构、波形图等多模态信息），以及对应的 golden RTL 实现。

```text
设计类型分布：
  Cryptographic Unit:  AES(15页/11信号), sha3(17/9), tiny_aes(17/4)
  Processor Core:      amber(26/14), lxp32(59/22), minsoc(22/14)
  Arithmetic Unit:     ecg(9/12), mac(24/34), pairing(13/8), tiny_pairing(17/10)
  Communication:       ethernet(42/54), i2c(15/24), sockit(29/15), uart(10/11)
  Memory Controller:   hpdmc(8/4), sdc(26/53), sdr_ctrl(28/46)
```

规格文档高度非结构化，assertion 相关信息分散在多个章节中（Summary、IO ports、Registers、Operation、Architecture、Usage examples、Waveform diagrams），且包含多模态数据。

**输出**：三个维度的 assertion 评测结果：
1. **Syntax**：生成的 assertion 是否有语法错误
2. **FPV pass/fail**：在 golden RTL（bug-free）上跑 FPV，通过=语义正确，失败=断言有误
3. **COI coverage**：Cone of Influence 覆盖率——断言覆盖了设计逻辑的百分比。COI 度量的是与 property 有结构连接的逻辑占比

### 3.3 组件 3：RTLCoder-Data（训练数据集）

**输入**：数字 IC 设计关键词池 L_key（数百个常用逻辑组件关键词）+ 开源 Verilog 源码 L_code。

**输出**：
- **Raw dataset: 80K** 条 instruction-code pair（instruction = 自然语言设计问题，code = 对应 Verilog RTL）。生成流程使用 GPT 完成三个阶段的自动化：关键词准备 → 指令生成（关键词扩展 + 源码启发 + mutation） → 代码生成。
- **Verified dataset: 7K** 条。从 raw 数据中通过 syntax checker + assertion-based functionality checker 筛选。功能检查流程：用 LLM 生成 assertion → 结合 code 喂给 FPV 工具（JasperGold）→ assertion 全部通过则视为 likely correct。

**关键特征**：
- 每条 instruction-code pair 的 token 长度一般在 2048 以内
- 与 VerilogEval/RTLLM 的 Rouge-L 相似度主要在 0.25 左右（低语义重叠，即数据集与评测集之间的信息泄露风险较低）
- 训练时排除 Rouge-L > 0.5 的样本以进一步防止数据泄露

### 3.4 数据多样性

| 数据集 | CR | CR:POS |
|------|:---:|:---:|
| RTLCoder-Data Raw (80K) | **4.21** | **7.33** |
| RTLCoder-Data Verified (7K) | 4.32 | 7.45 |
| MG-Verilog [55] | 5.80 | 9.16 |
| Goh et al. [15] | 5.27 | 10.1 |

CR（Compression Ratio）和 CR:POS（Part-of-Speech CR）越低表示多样性越高。RTLCoder-Data 的两个版本在多样性上均优于其他开源 Verilog instruction-code 数据集。

---

## 4. Benchmark 构建方法

### 4.1 RTLLM-2.0 的构建扩展

RTLLM-2.0 从 RTLLM v1.0 的 30 题扩展到 50 题。新增设计的选择原则包括：

- **功能多样性**：增加 BCD 加法器、浮点乘法器、fixed_point 单元等更专业的算术模块
- **存储模块独立化**：将存储相关设计（RAM、ROM、LIFO buffer、barrel_shifter、LFSR）单独成类
- **控制逻辑细化**：增加 ring_counter、up_down_counter、sequence_detector 等更丰富的控制模块
- **频率分频器系列**：从 v1.0 的单个 freq_div 扩展到 freq_divbyeven/odd/frac，覆盖不同分频场景

四类分类体系的改良意义：v1.0 的 Arithmetic/Logic 二分过于粗糙，比如 FIFO（异步存储）被归入 Logic，但实际上应该体现其存储特性。新的四分类让不同 LLM 在不同设计类型上的优劣势更容易被观察到。

### 4.2 AssertEval 的构建思路

18 个设计来自真实开源项目，规格文档保留原始形态（高度非结构化、含波形图等）。这是有意为之——真实的 IC 设计规格就是这样的，评测不应该用人工预处理的干净格式。

每个设计提供：
- **Specification document**：完整的自然语言规格，含 Summary、IO ports、Registers、Operation、Architecture、Usage examples、Waveform
- **Golden RTL implementation**：根据规格严格实现、已验证无 bug 的 RTL（作为 FPV 的 reference）
- **FPV script**：Cadence JasperGold 的一键执行脚本

评测流程：

```text
SPEC Doc (含文本+波形图)
    │
    ▼
[SVA Generation Method]  ← 待评测的 assertion 生成方法
    │
    ▼
Generated SVAs
    │
    ▼
[Formal Property Verification]
  Golden RTL + Generated SVAs → JasperGold FPV
    │
    ▼
Evaluation Metrics:
  1. Syntax (能否被工具解析)
  2. FPV pass/fail (语义是否正确)
  3. COI Coverage (覆盖了多少逻辑)
```

### 4.3 RTLCoder-Data 的构建流水线

数据生成分为三个阶段：

```text
Stage 1: Keywords Preparation
  GPT → digital IC keywords pool L_key (数百个常用逻辑组件关键词)

Stage 2: Instruction Generation
  ① 关键字扩展: L_key → GPT → 完整设计指令
  ② 源码启发: L_code (开源 Verilog) → GPT → 相关设计问题
  ③ 指令积累: ①② → 初始 L_ins
  ④ 变异扩增: L_ins 采样 → 两种 mutation → 新指令
  ⑤ 质量检查: 规则过滤 → 通过则加入 L_ins

Stage 3: Reference Code Generation
  ⑥ L_ins → GPT → reference Verilog code
  ⑦ [可选] Functionality Checker:
      instruction → LLM → assertions + code → FPV → pass? → verified
```

80K raw 数据的生成相比 RTLCoder v1 的改进：扩大了 L_code 源码池（Stage 2 中 process ③）、继续 mutation 扩增（process ④）、移除了耗时的多样性检查步骤（实践证明不影响最终多样性）。

7K verified 数据的筛选：syntax checker + assertion-based functionality checker。功能检查使用 AssertLLM 的技术生成 assertion，然后用 JasperGold FPV 验证。这是一个创新性的尝试——用 LLM-assisted verification 来检验 LLM-generated training data 的正确性。

---

## 5. 关键公式

### 5.1 pass@k（与 RTLLM v1 一致）

生成 k 次中有 c 次通过时，pass@k 的无偏估计为：

$$
\text{pass@k} = 1 - \frac{\binom{n-c}{k}}{\binom{n}{k}}
$$

- $n$：总生成次数
- $c$：n 次中通过目标检查的次数
- $k$：采样次数（k=1,5,10）

本论文对 VerilogEval benchmark 使用 pass@1/pass@5/pass@10 三档报告；对 RTLLM V1.1 沿用原始的 pass@5 判定逻辑。对每个被评测模型，测试 temperature={0.2, 0.5, 0.8} 三种条件，报告最佳结果。

### 5.2 数据多样性度量

论文使用两种压缩比来衡量数据集多样性，值越低表示多样性越高：

**CR（Compression Ratio）**：

$$
\text{CR} = \frac{\text{compressed\_size}}{\text{original\_size}}
$$

基于文本压缩算法识别内容冗余，值越低说明内容重复越少。

**CR:POS**：同上，但压缩对象是词性标注（POS tag）序列而非原始文本，用于捕获句法层面的重复模式。

### 5.3 训练损失

论文采用标准的 instruction-supervised fine-tuning，使用交叉熵损失：

$$
\mathcal{L} = -\sum_{t=1}^{T} \log p(y_t \mid x, y_{<t})
$$

- $x$：instruction 部分（自然语言设计问题）
- $y_t$：code 部分在第 t 个 token 的 ground-truth
- $T$：code 部分的 token 总数

注意 instruction 部分不参与 loss 计算——loss 只在 code 部分往回传播。

---

## 6. 评测协议与打分

### 6.1 VerilogEval 评测

使用 VerilogEval benchmark 的两个子集：

- **Eval-Machine**：机器生成的 Verilog 题目（侧重于语法与标准模式）
- **Eval-Human**：人工编写的 Verilog 题目（侧重于真实设计场景）

对每个子集报告 pass@1/pass@5/pass@10。所有结果取 temperature={0.2, 0.5, 0.8} 三个条件中的最佳值。

### 6.2 RTLLM V1.1 评测

沿用 RTLLM 原论文的评测协议：每题生成 5 次，Syntax 统计 5 次中通过综合的次数百分比，Functionality 统计 5 次中至少一次通过 testbench 的题目数（pass@5 逻辑）。两者分开报告。

### 6.3 核心结果表

| 模型类型 | 模型名称 | 参数量 | Eval-Machine (%) | Eval-Human (%) | RTLLM V1.1 |
|------|------|:---:|:---:|:---:|:---:|
| | | | k=1 / k=5 / k=10 | k=1 / k=5 / k=10 | Syntax / Func |
| 闭源基线 | GPT-3.5 | N/A | 46.7 / 69.1 / 74.1 | 26.7 / 45.8 / 51.7 | 89.7 / 37.9 |
| 闭源基线 | **GPT-4** | N/A | **60.0** / 70.6 / 73.5 | **43.5** / **55.8** / **58.9** | **100** / **65.5** |
| 闭源基线 | ChipNeMo [25] | 13B | 43.4 / N/A / N/A | 22.4 / N/A / N/A | N/A |
| 闭源基线 | VerilogEval [27] | 16B | 46.2 / 67.3 / 73.7 | 28.8 / 45.9 / 52.3 | N/A |
| 闭源基线 | BetterV [38] | 7B | 64.2 / 75.4 / 79.1 | 40.9 / 50.0 / 53.3 | N/A |
| 开源基线 | CodeGen2 [33] | 16B | 5.00 / 9.00 / 13.9 | 0.90 / 4.10 / 7.25 | 72.4 / 6.90 |
| 开源基线 | StarCoder [24] | 15B | 46.8 / 54.5 / 59.6 | 18.1 / 26.1 / 30.4 | 93.1 / 27.6 |
| 开源基线 | Thakur et al. [45] | 16B | 44.0 / 52.6 / 59.2 | 30.3 / 43.9 / 49.6 | 86.2 / 24.1 |
| 开源基线 | Mistral-7B [19] | 7B | 36.9 / 48.8 / 57.4 | 4.49 / 12.6 / 18.6 | 72.4 / 20.7 |
| 开源基线 | DeepSeek-Coder [16] | 6.7B | 54.1 / 63.8 / 67.5 | 30.2 / 42.2 / 46.2 | 89.6 / 34.5 |
| Scoring训练 | Mistral-Scoring (27K) | 7B | 62.5 / 72.2 / 76.6 | 36.7 / 45.5 / 49.2 | 96.6 / 48.3 |
| Scoring训练 | DeepSeek-Scoring (27K) | 6.7B | 61.2 / 76.5 / 81.8 | 41.6 / 50.1 / 53.4 | 93.1 / 48.3 |
| Direct训练 | Mistral-Direct (27K) | 7B | 58.9 / 70.0 / 74.1 | 34.4 / 42.3 / 45.1 | 89.7 / 41.4 |
| Direct训练 | DeepSeek-Direct (5K) | 6.7B | 53.7 / 71.7 / 77.1 | 32.9 / 45.8 / 52.4 | 93.1 / 41.4 |
| Direct训练 | DeepSeek-Direct (27K) | 6.7B | 59.8 / 73.6 / 77.2 | 39.1 / 48.3 / 51.3 | 86.2 / 44.8 |
| Direct训练 | DeepSeek-Direct (50K) | 6.7B | 62.6 / 75.6 / 80.5 | 38.9 / 48.7 / 51.8 | 89.7 / 55.2 |
| Direct训练 | **DeepSeek-Direct (80K)** | **6.7B** | **64.7** / **76.6** / **80.8** | 42.8 / **51.6** / **55.0** | 93.1 / 48.3 |
| Verified数据 | DeepSeek-Direct (7K verified) | 7B | 61.3 / 76.3 / 80.8 | 38.9 / 50.1 / 55.3 | **100** / 48.3 |

这张表包含了从闭源商业模型到开源微调模型的完整比较。几个关键结论：

1. **数据量对性能的影响**：从 5K 到 80K，Eval-Machine pass@1 从 53.7% 上升到 64.7%，且 80K 时仍未见性能饱和——增大训练集仍是有效的提升路径。

2. **数据质量胜过数据量**：DeepSeek-Direct (7K verified) 在 6/8 个指标上超过 DeepSeek-Direct (50K)，且在 RTLLM Syntax 上达到 100%。用不到 20% 的训练时间达到更好效果。

3. **训练方法的影响**：Scoring-based training（RTLCoder 提出的 code quality feedback 方法）在所有 benchmark 上均优于同数据量的 direct training。

4. **小模型竞争力**：6.7B 的 DeepSeek-Coder 微调后在 Eval-Machine pass@1 上超越 GPT-4（64.7% vs 60.0%）。

### 6.4 训练设置

- **基础模型**：Mistral-7B-v0.1, DeepSeek-Coder-6.7b-Instruct
- **优化器**：Adam (beta_1=0.9, beta_2=0.999), learning rate=1e-5, 无 weight decay
- **上下文长度**：2048 tokens
- **全局 batch size**：256
- **硬件**：4x RTX 4090 (24GB each), DeepSpeed stage-2
- **每条样本效率**：每个 GPU 可容纳 2 x 2048 context length

---

## 7. 创新点

### 创新点 1：首次统一 RTL 生成+验证的全栈开源评测框架

之前的工作（RTLLM v1, VerilogEval）只评测「生成的代码能不能跑」。OpenLLM-RTL 加上了 assertion 生成评测——芯片设计中验证占 60-70% 的工作量，LLM 能否帮忙做验证至少和能否生成 RTL 一样重要。三个组件覆盖了训练数据（RTLCoder-Data）、生成质量评测（RTLLM-2.0）、验证质量评测（AssertEval）的完整生命周期。

### 创新点 2：自动化 assertion-based 训练数据功能验证

用 LLM 生成 assertion + 商业 FPV 工具验证 code 正确性的流水线，前人没有做过。80K → 7K 的筛选率（8.75%）本身就是个重要发现：LLM 生成的「看起来没问题」的 RTL 代码，超过 90% 有实质性缺陷。但实验证明，即便是包含部分错误样本的 raw 80K 数据集，增大规模仍能提升模型性能——错误数据中仍蕴含有用的代码结构信息。

### 创新点 3：系统性的训练因素消融研究

论文不是简单地「微调了一个模型然后报告分数」，而是系统性地研究了三个影响 LLM 性能的因素：
- **数据量**：5K → 27K → 50K → 80K 的性能变化曲线（且 80K 时曲线未饱和）
- **训练方法**：scoring-based vs. direct training 的对比
- **数据质量**：7K verified vs. 50K raw 的对比（质量 > 数量）

这种 engineering 视角的消融研究在 AI4EDA 领域少见，但价值很高。

### 创新点 4：AssertEval——首个 assertion 生成的标准化评测

在 LLM-based assertion generation 这个方向上，之前没有统一的 benchmark 和评测框架。AssertEval 提供的 18 个真实设计 + golden RTL + FPV script + 三维评测指标（Syntax/FPV Pass-Fail/COI Coverage），为该方向的研究提供了标准化的起点。

---

## 8. EDA 缩写表

| 缩写 | 全称 | 一句话解释 |
|------|------|------|
| **SVA** | SystemVerilog Assertion | SystemVerilog 断言——用形式化语言描述电路应满足的时序性质 |
| **FPV** | Formal Property Verification | 形式属性验证——用数学方法（SAT/SMT）证明断言是否在所有输入下成立 |
| **COI** | Cone of Influence | 影响锥——与某个 property 有结构连接的所有逻辑单元的集合 |
| **PPA** | Power, Performance, Area | 功耗/性能/面积——芯片设计三大核心指标 |
| **RTL** | Register-Transfer Level | 寄存器传输级 |
| **LLM** | Large Language Model | 大语言模型 |
| **CR** | Compression Ratio | 压缩比——数据多样性度量，值越低数据越多样 |
| **CR:POS** | Part-of-Speech Compression Ratio | 词性标注压缩比——句法多样性度量 |
| **Rouge-L** | Recall-Oriented Understudy for Gisting Evaluation (Longest Common Subsequence) | 文本相似度度量，用于检测训练数据与评测集之间的信息泄露 |
| **DeepSpeed** | — | 微软开源的分布式训练优化库，stage-2 指优化器状态+梯度分片 |
| **FSM** | Finite State Machine | 有限状态机 |
| **FIFO** | First In, First Out | 先进先出队列 |
| **LIFO** | Last In, First Out | 后进先出队列 |
| **LFSR** | Linear Feedback Shift Register | 线性反馈移位寄存器——用于生成伪随机序列 |
| **ALU** | Arithmetic Logic Unit | 算术逻辑单元 |
| **PE** | Processing Element | 处理单元 |
| **ROM** | Read-Only Memory | 只读存储器 |
| **RAM** | Random Access Memory | 随机存取存储器 |

---

## 9. 与芯片流程的关系

### 9.1 在全流程中的位置

```text
芯片流程                    OpenLLM-RTL 的角色
────────────────────────────────────────────────────
① RTL 设计                ← RTLLM-2.0 评测 LLM 生成 RTL 的能力
                              RTLCoder-Data 为 LLM 微调提供数据
② RTL 功能仿真             ← RTLLM-2.0 用 testbench 验证功能
③ 逻辑综合                 ← RTLLM-2.0 用 DC 提取 PPA
⑥ 形式验证                 ← AssertEval 评测 LLM 生成 assertion 的能力
                              RTLCoder-Data 用 FPV 做数据质量筛选
④⑤⑦~⑰                    ← 完全不涉及
```

OpenLLM-RTL 框架的独特定位是：它同时覆盖了「designer 做的事」（写 RTL）和「verification engineer 做的事」（写 assertion）——现代芯片设计中这两个角色通常由不同团队负责。

### 9.2 「生成了 assertion」和「芯片被验证了」之间隔着什么

AssertEval 的 FPV pass 只说明 assertion 在 golden RTL（bug-free 的参考实现）上是 true——这不意味着 assertion 能抓到真实的 bug。真正的验证需要：

1. **在待验证的 RTL 上跑 FPV**：RTLLM-generated RTL（可能有 bug）+ assertion，看 assertion 是否 fail
2. **断言的质量评估**：COI coverage 只度量结构覆盖，不度量行为覆盖。一个 assertion 可能 COI=100% 但只检查「clk 永远在 toggle」这种弱性质
3. **Vacuity check**：很多断言虽然是 true，但是 vacuously true（永不触发）。需要 vacuity coverage 作为补充指标

---

## 10. 评测公平性与可信度分析

### 10.1 数据泄露控制

论文使用 Rouge-L 度量训练数据与 VerilogEval/RTLLM 评测集的语义重叠——大部分训练样本的 Rouge-L 值在 0.25 左右，表明语义重叠低。训练时排除 Rouge-L > 0.5 的样本。但 Rouge-L 作为基于最长公共子序列的文本相似度度量，可能无法检测语义等价但表达不同的样本（如换一种自然语言描述表达同样的设计需求），且无法控制 LLM 预训练阶段的数据泄露。

### 10.2 评测协议的一致性

论文对 VerilogEval 使用 pass@1/pass@5/pass@10，对 RTLLM V1.1 使用原始协议的 pass@5 逻辑。两个 bencharmk 的评测口径不完全一致——VerilogEval 报告无偏估计概率值，RTLLM 报告原始计数/百分比。论文统一用「每个模型的最优 temperature 结果」来报告，这可能导致少量 overfitting to temperature。

### 10.3 训练数据的功能正确性保证

80K raw 数据未经功能验证，其中包含大量功能错误的样本。论文的实验表明即使如此，增大 raw 数据规模仍能提升模型性能。这暗示 LLM 可以从「代码结构正确但功能错误」的样本中学习到有用的 Verilog 语法和编码模式，但不能证明模型学会了正确的功能映射。

7K verified 数据的功能验证同样不完美：用于验证的 assertion 本身也是由 LLM 生成的（可能存在假阴性——正确的 code 因为错误的 assertion 而 fail FPV），且 FPV 通过不代表功能 100% 正确（assertion 可能不够强）。

### 10.4 商业工具依赖

JasperGold FPV、VCS、Design Compiler 均需商业 license，部分限制了完全开源复现。AssertEval 的 FPV script 为 JasperGold 编写，用户需要拥有 Cadence license 才能运行完整评测。

---

## 11. 复现信息

| 项目 | 内容 |
|------|------|
| 论文页 | arXiv: 2503.15112 v1, ICCAD 2024 Invited, 9 页 |
| RTLLM-2.0 代码 | <https://github.com/hkust-zhiyao/RTLLM>，本地 commit `41b26896e33b` |
| AssertEval 代码 | <https://github.com/hkust-zhiyao/AssertLLM> |
| RTLCoder-Data 代码 | <https://github.com/hkust-zhiyao/RTL-Coder> |
| 本地状态 | RTLLM-2.0 的 50 题/四类目录/description-testbench-reference-Makefile 已核对；AssertEval 代码本地未发现完整目录（在 AssertLLM 仓库中）；RTLCoder-Data 位于独立 RTL-Coder 目录 |
| 复现等级 | **R1**：论文、Git 版本、数据和代码调用链已完成静态核对，未重新训练模型、未运行 FPV/VCS/DC |
| 主要门槛 | 训练需要 4x RTX 4090 (96GB 总显存) + DeepSpeed stage-2；完整评测需要 JasperGold/VCS/DC 商业 license |

详见 [OpenLLM-RTL论文与代码复现详解.md](./OpenLLM-RTL论文与代码复现详解.md)。

---

## 12. 一分钟复述版

OpenLLM-RTL 是一篇 ICCAD 2024 invited paper，把三条独立工作线整合成一个开源框架：

- **RTLLM-2.0**：50 题 RTL 生成评测集，从 v1.0 的 30 题扩展，分四大类（Arithmetic/Memory/Control/Miscellaneous）
- **AssertEval**：18 个真实设计的 assertion 生成评测集，用 FPV 评估生成 assertion 的语法/语义/覆盖率
- **RTLCoder-Data**：80K raw + 7K verified 训练数据——用 LLM 自动生成，用 assertion+FPV 自动筛选

核心实验发现：
- DeepSeek-Coder-6.7B + 80K 数据在 Eval-Machine pass@1 上超越 GPT-4（64.7% vs 60.0%）
- 7K verified 数据效果超过 50K raw 数据（质量 > 数量），训练时间不到 20%
- 80K 数据时性能曲线仍未见饱和（数据量还有提升空间）
- Scoring-based training 在所有 benchmark 上优于 direct training

局限：AssertEval 仅有 18 题、Rouge-L 无法完全检测数据泄露、verified 数据的 assertion 验证本身也是 LLM 生成的（可能存在假阴性）。

---

## 13. RTLLM 1.0 → 2.0 进化

本节总结从 [RTLLM v1.0](./论文深度讲解_RTLLM.md)（arXiv: 2308.05345, 2023）到 RTLLM 2.0 / OpenLLM-RTL（arXiv: 2503.15112, 2025）的核心进化。

### 13.1 题目规模：30 → 50

| 维度 | RTLLM v1.0 | RTLLM 2.0 |
|------|:---:|:---:|
| 设计总数 | 30 | **50** |
| 分类体系 | Arithmetic (11) + Logic (19) | Arithmetic + Memory + Control + Miscellaneous |
| 最大 RTL 行数 | 518 (risc_cpu) | 518 (risc_cpu) |
| 总 RTL 行数 | ~2.5K | 显著增加（新增 20 题） |
| 新增代表设计 | — | BCD 加法器、浮点乘法器、fixed_point 单元、LFSR、barrel_shifter、LIFO buffer、ROM、ring_counter、up_down_counter、sequence_detector、freq_divbyeven/odd/frac 等 |

分类体系的改善：v1.0 的 Arithmetic/Logic 二分过于粗糙——如 FIFO 归入 Logic 无法体现其存储特性。v2.0 的四分类让不同 LLM 在不同设计类型上的优劣势更容易被观察到。

### 13.2 评测维度扩展：新增 AssertEval

RTLLM v1.0 只评测「LLM 生成的 RTL 对不对」。OpenLLM-RTL 新增 AssertEval，评测「LLM 生成的验证断言对不对」。

| 评测维度 | RTLLM v1.0 | RTLLM 2.0 / OpenLLM-RTL |
|------|:---:|:---:|
| RTL 语法正确性 | ✅ | ✅ |
| RTL 功能正确性 | ✅ | ✅ |
| RTL PPA 质量 | ✅ | ✅ |
| Assertion 语法正确性 | — | ✅ **新增** |
| Assertion 语义正确性 (FPV) | — | ✅ **新增** |
| Assertion 覆盖率 (COI) | — | ✅ **新增** |

这对应芯片流程中的角色分工：v1.0 只覆盖 designer 的工作（写 RTL），v2.0 同时覆盖 verification engineer 的工作（写 assertion）。

### 13.3 三层评价体系的细化

v1.0 的三级评测（Syntax → Functionality → Quality）在 v2.0 中保留，但增加了以下细化：

- **Syntax 评测**：v2.0 在 RTLLM V1.1 评测中直接报告 VCS syntax pass 百分比（如 100% / 89.7%），与 v1.0 的 Design Compiler 语法通过率口径有所不同
- **Functionality 评测**：协议不变（每题 5 次，至少 1 次通过 testbench 算 pass），但 v2.0 通过训练自己的模型（DeepSeek-Direct 7K verified）在 RTLLM V1.1 上达到 100% syntax 正确率
- **Quality 评测**：v2.0 未单独报告 RTLLM-2.0 题目上的 PPA 对比——论文的评测重点转移到了 VerilogEval 和 RTLLM V1.1 的 pass@k 指标。PPA 质量评估在 v2.0 中被相对弱化

### 13.4 从「评测集」到「评测集 + 训练数据」

RTLLM v1.0 是一个纯粹的评测集（benchmark-only）。OpenLLM-RTL 通过引入 RTLCoder-Data，补全了「训练数据」这一环：

```text
RTLLM v1.0:
  只有评测集 → 只能评价已有 LLM，无法自行训练更优模型

RTLLM 2.0 / OpenLLM-RTL:
  RTLCoder-Data (训练数据) → 训练自己的模型 → RTLLM-2.0 (评测集) 评价
                            → AssertEval 评价验证能力
```

这个进化从「只能评价别人的模型」变成了「提供完整的数据+训练+评测生态」——任何研究者都可以用 RTLCoder-Data 训练模型，用 RTLLM-2.0 评测生成能力，用 AssertEval 评测验证能力。

### 13.5 方法论进化小结

| 维度 | RTLLM v1.0 (2023) | RTLLM 2.0 / OpenLLM-RTL (2025) |
|------|------|------|
| 论文类型 | 原创 benchmark 论文 | Invited paper，整合三条工作线 |
| 评测目标 | RTL 生成 | RTL 生成 + Assertion 生成 + 训练数据质量 |
| 开源资产数 | 1（RTLLM 代码仓库） | 3（RTLLM + AssertLLM + RTL-Coder） |
| 题目数 | 30 | 50（RTL）+ 18（Assertion） |
| 训练数据 | 无 | 80K raw + 7K verified |
| 自研模型 | 无（只评测 GPT/StarCoder 等） | 有（DeepSeek-Coder + RTLCoder-Data 微调，在 Eval-Machine pass@1 上超越 GPT-4） |
| 影响力 | 开创了 RTL 生成的三级评测范式 | 建立了从数据到评测的完整开源生态 |
