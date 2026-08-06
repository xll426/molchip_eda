# VeriGen Benchmark 论文深度讲解

> **Benchmarking Large Language Models for Automated Verilog RTL Code Generation**
> Shailja Thakur, Baleegh Ahmad, Zhenxing Fan, Hammond Pearce, Benjamin Tan, Ramesh Karri, Brendan Dolan-Gavitt, Siddharth Garg
> New York University, University of Calgary
> DATE 2023 · arXiv: 2212.11140 v1（2022-12-13），共 7 页
> 原文：[2212.11140_VeriGen.pdf](./2212.11140_VeriGen.pdf)
> 代码：https://github.com/shailja-thakur/VGen
> 模型权重：https://huggingface.co/shailja

---

## 1. 一句话定位

**VGen/VeriGen 是第一个系统性地从 GitHub BigQuery（覆盖 280 万仓库）抓取 Verilog 代码 + 70 本教材 PDF 构建专用语料（约 400MB），微调 CodeGen（2B/6B/16B）等五种 decoder-only 模型，在自建 17 题 benchmark 上用 Icarus Verilog 的编译/testbench 通过率（而非 BLEU）做可执行评测，证明领域微调能将 Verilog 功能正确率从 1.09% 拉到 27.0%，且 CodeGen-16B 微调后（41.9%）超过同期商业 code-davinci-002（35.4%）的工作。**

逐条拆解这句话里的技术承重点：

1. **"系统性地构建专用语料"** -- 不是随便下载几个 GitHub 仓库，而是通过 Google BigQuery 的 GitHub snapshot（覆盖 280 万仓库）用 SQL 检索 + MinHash/Jaccard 去重 + 教材 PDF OCR + 重叠滑窗，形成 50K 文件 / 300MB GitHub 语料 + 约 100MB 教材语料。这是后来绝大多数 RTL LLM 工作的数据 pipeline 模板。

2. **"微调五种 decoder-only 模型"** -- 从 355M 的 MegatronLM 到 16B 的 CodeGen，跨度近 50 倍。不是训一个新模型，而是在通用/代码预训练模型上做领域持续训练（1 epoch for CodeGen，9 epochs for MegatronLM）。训练目标是标准的 next-token cross-entropy，没有任何 compiler-in-the-loop 或 RL。

3. **"自建 17 题 benchmark"** -- 分 Basic（4 题）/Intermediate（8 题）/Advanced（5 题）三档，每题配 L/M/H 三档 prompt 详细度。覆盖组合逻辑、时序逻辑、FSM（Finite State Machine，有限状态机）、RAM（Random Access Memory，随机存取存储器）、算术、移位。

4. **"Icarus Verilog 编译/testbench 通过率"** -- 不用 BLEU（Bilingual Evaluation Understudy，双语评估基准）/CodeBLEU/文本相似度，而是仿真器编译 + 实际执行 + testbench 判定。语法正确 = iverilog 编译通过；功能正确 = vvp 仿真输出以 "all tests passed" 结尾。这是 RTL LLM 评测的黄金标准范式。

5. **"41.9% vs 35.4%"** -- 这 6.5 个百分点的差距在当时的语境下意义重大：它证明开源模型 + 领域微调能超过商业 API 的 code-davinci-002（基于 GPT-3，约 175B 参数），且 16B 参数的微调模型在 RTL 领域可以匹敌甚至超过 10 倍以上参数量的通用代码模型。

---

## 2. EDA 阶段映射（①-⑰）

参照 [芯片流程](../芯片流程.md) 的 17 阶段标准编号：

| 阶段 | 覆盖 | 说明 |
|------|:---:|------|
| **① RTL 设计** | ✅ **核心** | 从 L/M/H 三档 prompt（含功能注释 + module header + 端口声明）自回归生成完整 Verilog module |
| **② RTL 功能仿真** | ✅ **核心** | Icarus Verilog v11.0 编译 + vvp 仿真执行 + testbench 判定。compilation success = iverilog 无错误；functional success = stdout 以 "all tests passed" 结尾 |
| ③ 逻辑综合 | ❌ | 不调 Yosys / Design Compiler / Genus。生成的代码"仿真通过"不等于"可综合"——比如 `initial` 块赋初值、组合环、意外锁存器、敏感表不全，仿真器全都能跑，综合器直接报错 |
| ④ 门级仿真 | ❌ | 无 SDF（Standard Delay Format，标准延时格式）反标。看不到毛刺、建立/保持违例、X 传播、多驱冲突 |
| ⑤ STA（Static Timing Analysis，静态时序分析） | ❌ | 不计算任何路径延迟。论文关注的"时序"是逻辑时序（如该用非阻塞赋值 `<=` 用了阻塞赋值 `=`），不是物理时序 |
| ⑥ 形式验证 | ❌ | 不做 SAT/SMT 等价性证明 |
| ⑦ 布局规划 (Floorplan) | ❌ | —— |
| ⑧ 标准单元摆放 (Placement) | ❌ | —— |
| ⑨ 时钟树综合 (CTS) | ❌ | —— |
| ⑩ 布线 (Routing) | ❌ | —— |
| ⑪ 后仿真 | ❌ | 无 SPEF（Standard Parasitic Exchange Format，标准寄生参数交换格式）信息。RTL 仿真假设零延迟，后仿真需要真实走线 RC |
| ⑫ 物理验证 DRC + LVS | ❌ | —— |
| ⑬ 签核 (Signoff) | ❌ | —— |
| ⑭-⑰ 流片 → 制造 → 封装测试 → 芯片 | ❌ | —— |

**覆盖率：2/17。** VGen 是一个**纯数字前端 spec/prompt → RTL → 功能仿真验证**的工具链。它在阶段 ①/② 之间做的是**单向生成 + 评测**，不是迭代闭环。

> ⚠️ 关键定位：VGen 的目标是 **benchmarking**（评测），不是 **automated design closure**（自动设计收敛）。它研究的问题是"LLM 能不能写可编译/功能正确的 Verilog"，而不是"LLM 能不能生成可综合/时序收敛/面积优化的 Verilog"。这是 VGen 和 MAGE/ChipSeek 的根本分野——后者追求从仿真反馈中迭代修复直到功能完全正确，VGen 只做一次生成 + 评测 + 统计分析。

---

## 3. 输入 / 输出

### 3.1 训练阶段输入

#### 3.1.1 GitHub Verilog 语料（约 300 MB）

论文通过 Google BigQuery 的 GitHub snapshot（覆盖约 280 万仓库）检索 Verilog 代码。SQL 查询条件：

```sql
FROM bigquery-public-data.github_repos.files AS f
JOIN bigquery-public-data.github_repos.contents AS c
ON f.id = c.id
WHERE NOT c.binary
  AND f.path LIKE '%.v'
  AND c.content LIKE '%endmodule%'
```

过滤管线：
1. 搜索 `.v` 扩展名和 "Verilog" 关键词
2. 保留至少含一对 `module`/`endmodule` 的文件（排除纯 testbench、include 文件、文档中的 Verilog 片段）
3. MinHash + Jaccard similarity 去重/去近重复（避免同一个 IP core 出现在多个仓库中被重复计数）
4. 删除字符数 >= 20K 的大文件（大文件往往是自动生成的寄存器文件、第三方 IP 核，不反映工程师手写 RTL 的风格）
5. 得到约 **50K 文件 / 约 300 MB**

典型的训练样本形态（来自 GitHub 开源仓库的真实代码片段）：

```verilog
module fifo #(parameter WIDTH=8, DEPTH=16)
  (input clk, rst, wr_en, rd_en,
   input [WIDTH-1:0] data_in,
   output reg [WIDTH-1:0] data_out,
   output reg empty, full);
  reg [WIDTH-1:0] mem [0:DEPTH-1];
  reg [4:0] wr_ptr, rd_ptr, count;
  // ... FIFO 实现 ...
endmodule
```

```verilog
module uart_tx (
    input clk, rst,
    input [7:0] tx_data,
    input tx_start,
    output reg tx,
    output reg tx_busy
);
  // ... UART 发送器实现 ...
endmodule
```

注意这些代码的特点：风格多样（工程师手写，没有统一编码规范）、多数可综合（来自实际设计而非 testbench）、包含参数化模块（`#(parameter ...)`）、包含常见数字电路模式（FIFO、UART、SPI、arbiter、FSM）。

#### 3.1.2 70 本 Verilog 教材语料（约 100 MB）

从在线电子图书馆下载 70 本 Verilog 教材 PDF，经 PyMuPDF + OCR（Optical Character Recognition，光学字符识别）提取文本，再清洗：

```
PDF 原文件
  -> PyMuPDF 文本提取 (+ OCR 处理扫描页)
  -> 删除 index / preface / acknowledgments / 附录等无关段落
  -> 正则识别 prose（自然语言解释）+ Verilog code block
  -> 重叠滑窗生成训练样本（window overlap 确保教材中相邻概念不因切窗断裂）
  -> 与 GitHub 语料合并 -> 约 400 MB 总语料
```

教材语料提供的价值不同于 GitHub：自然语言解释（如 "always @(posedge clk) 表示时钟上升沿触发的时序逻辑" 这种规格到实现的语义映射）、小而完整的示例（半加器、计数器、FSM——这些 20-50 行的完整模块更适合让模型学习 Verilog 的层次化模块结构）、规范写法（更接近"标准答案"）、概念教学（阻塞 vs 非阻塞赋值、组合 vs 时序 always 块、wire vs reg 声明等语义区别）。

### 3.2 推理/评测阶段输入（Set I，17 道手设计题）

#### 3.2.1 17 道题目概览

| 题号 | 难度 | 描述 |
|:---:|------|------|
| 1 | Basic | A simple wire |
| 2 | Basic | A 2-input and gate |
| 3 | Basic | A 3-bit priority encoder |
| 4 | Basic | A 2-input multiplexer |
| 5 | Intermediate | A half adder |
| 6 | Intermediate | A 1-to-12 counter |
| 7 | Intermediate | LFSR with taps at 3 and 5 |
| 8 | Intermediate | FSM with two states |
| 9 | Intermediate | Shift left and rotate |
| 10 | Intermediate | Random Access Memory |
| 11 | Intermediate | Permutation |
| 12 | Intermediate | Truth table |
| 13 | Advanced | Signed 8-bit adder with overflow |
| 14 | Advanced | Counter with enable signal |
| 15 | Advanced | FSM to recognize '101' |
| 16 | Advanced | 64-bit arithmetic shift register |
| 17 | Advanced | ABRO FSM |

#### 3.2.2 Prompt 的三档详细度

以 Problem 5（Half Adder，半加器）为例：

**L（Low detail）**——只有功能注释 + module header + 端口声明：
```verilog
// Design a half adder circuit.
module half_adder(input a, input b, output sum, output carry);
```

**M（Medium detail）**——L + 使用信号名描述行为：
```verilog
// Design a half adder circuit.
// The half adder takes two input bits a and b.
// It produces a sum bit and a carry bit.
// The sum bit is the XOR of a and b.
// The carry bit is the AND of a and b.
module half_adder(input a, input b, output sum, output carry);
```

**H（High detail）**——M + 更接近伪代码的详细步骤：
```verilog
// Design a half adder circuit.
// The half adder takes two input bits a and b.
// It produces a sum bit and a carry bit.
// The sum bit is the XOR of inputs a and b:
//   assign sum = a ^ b;
// The carry bit is the AND of inputs a and b:
//   assign carry = a & b;
// Complete the module with endmodule.
module half_adder(input a, input b, output sum, output carry);
```

这三档研究的关键问题是：**模型到底在做高层次设计推理，还是仅仅把伪代码翻译成 Verilog 语法？**

#### 3.2.3 采样协议

| 参数 | 值 |
|------|-----|
| temperature | {0.1, 0.3, 0.5, 0.7, 1.0} |
| completions per prompt (`n`) | {1, 10, 25}（J1-Large 不支持 n=25） |
| max_tokens | 300（J1-Large 限制 256） |
| top_p | 1.0 |

如果完整跑所有组合（除 J1 外），单模型理论最大生成量：17 tasks x 3 prompts x 5 temperatures x (1 + 10 + 25) = 9,180 completions。论文 Table III/IV 只展示 n=10，并对每个 model/scenario 选择表现最好的 temperature（best-of-temperature）。

### 3.3 输出

#### 3.3.1 生成产物

自回归补全生成的完整 Verilog module。以 half adder 为例，期望输出：

```verilog
module half_adder(input a, input b, output sum, output carry);
    assign sum = a ^ b;
    assign carry = a & b;
endmodule
```

但实际生成经常出现：语法正确但逻辑错误（如 `assign sum = a | b;`）、语法错误（如 `assign sum = a xor b;`——Verilog 没有 xor 关键字）、生成不完整（缺 endmodule）。

#### 3.3.2 评测判定

判分逻辑（来自 evaluator 代码）：
1. 编译成功：`subprocess.run(iverilog ...).stderr` 为空（**不检查 return code**，这是已知缺陷）
2. 功能成功：vvp stdout 最后 17 个字符 **严格等于** `"all tests passed\n"`
3. 多一个空格、多一个换行、testbench 尾日志都会导致功能通过被误判为失败

#### 3.3.3 评测统计

| 聚合维度 | 指标 |
|---------|------|
| compile rate | 可被 Icarus 编译的候选比例 |
| functional rate | 编译通过且 testbench 全过的候选比例 |
| Pass@(scenario\*n) | 某 difficulty × prompt level 下，所有 n 个候选中的成功比例（**不是标准 pass@k 无偏估计**） |
| 按 difficulty 聚合 | 每个难度档位的 compile/functional rate |
| 按 prompt detail 聚合 | 每个详细度档位的 compile/functional rate |
| 按 temperature 聚合 | 每个温度下的 compile/functional rate |

---

## 4. 方法与架构

### 4.1 整体 Pipeline

这节要解决的问题：从原始数据到评测统计，VGen 的数据流经过了哪些步骤、每个步骤的输入输出是什么、用了什么工具/模型。

```text
┌─────────────────────────────────────────────────────────────────────────────┐
│                        训练阶段：语料构建 + 微调                               │
└─────────────────────────────────────────────────────────────────────────────┘

  Google BigQuery                              在线电子图书馆
  (GitHub snapshot,                             70 本 Verilog 教材 PDF
   280 万仓库)                                        │
       │                                              ▼
       ▼                                     PyMuPDF + OCR
  SQL 检索:                                    文本提取
  - path LIKE '%.v'                                  │
  - content LIKE '%endmodule%'                 正则清洗:
       │                                      - 删除 index/preface/
       ▼                                        acknowledgments/附录
  约 50K .v 文件                               - 识别 prose + Verilog blocks
       │                                      - 重叠滑窗分片
       ▼                                            │
  清洗:                                              ▼
  - MinHash + Jaccard 去重/近重复                教材语料
  - 删除字符数 >= 20K 的大文件                   (~100 MB)
  - 保留至少含一对 module/endmodule                │
       │                                            │
       ▼                                            │
  GitHub Verilog 语料                               │
  (~300 MB, ~50K files)                             │
       │                                            │
       └────────────────┬───────────────────────────┘
                        │
                        ▼
              ┌──────────────────┐
              │  合并训练语料     │
              │  ~400 MB total   │
              └────────┬─────────┘
                       │
                       ▼
┌──────────────────────────────────────────────────────────────────┐
│                  微调预训练模型（next-token cross-entropy）        │
│                                                                    │
│  ┌──────────────────┐  ┌──────────────┐  ┌──────────────────────┐│
│  │ MegatronLM-355M  │  │ J1-Large-7B  │  │ CodeGen-2B/6B/16B   ││
│  │ 1xRTX8000 15h    │  │ AI21 商业微调 │  │ 2xRTX8000(2B) 2天   ││
│  │ 9 epochs         │  │              │  │ 4xRTX8000(6B) 4天   ││
│  │                  │  │              │  │ 3xA100(16B) 6天      ││
│  └──────┬───────────┘  └──────┬───────┘  │ DeepSpeed ZeRO       ││
│         │                     │          └──────────┬───────────┘│
│         └─────────────────────┼─────────────────────┘            │
│                               │                                   │
│                    Fine-tuned Verilog models                       │
└───────────────────────────────┬───────────────────────────────────┘
                                │
                                ▼
┌──────────────────────────────────────────────────────────────────────┐
│                    推理/评测阶段：生成 + 评测                          │
└──────────────────────────────────────────────────────────────────────┘

  17 道 Set I 题目
  (Basic 4 + Intermediate 8 + Advanced 5)
         │
         ├─ 每题准备 L/M/H 三档 prompt
         │
         ▼
  ┌──────────────────────────────────────┐
  │  LLM 自回归生成（每个 prompt）        │
  │  - temperature ∈ {0.1,0.3,0.5,0.7,1.0}│
  │  - n ∈ {1, 10, 25}                   │
  │  - max_tokens = 300 (J1 = 256)       │
  │  - top_p = 1.0                       │
  └──────────────┬───────────────────────┘
                 │
                 ▼
  ┌──────────────────────────────────────┐
  │  后处理                               │
  │  - 统计 begin/end 配对               │
  │  - 自动补 end/endmodule              │
  │  - 保存 prompt + completion 为 .v    │
  └──────────────┬───────────────────────┘
                 │
                 ▼
  ┌──────────────────────────────────────┐
  │  Icarus Verilog v11.0 编译            │
  │  $ iverilog -o example               │
  │    candidate.v tb_xxx.v              │
  │                                       │
  │  stderr 为空 → compile pass          │
  │  stderr 非空 → compile fail          │
  └──────────────┬───────────────────────┘
                 │
                 ▼
  ┌──────────────────────────────────────┐
  │  vvp 仿真执行                         │
  │  $ vvp example                       │
  │                                       │
  │  stdout 最后 17 字符 =                │
  │  "all tests passed\n"                │
  │    → functional pass                 │
  │  else → functional fail              │
  └──────────────┬───────────────────────┘
                 │
                 ▼
  ┌──────────────────────────────────────┐
  │  聚合统计                             │
  │  - 按 model/type(PT/FT)/difficulty/  │
  │    prompt_detail/temperature 聚合    │
  │  - 对每个 scenario 选 best temp      │
  │  - 报告 compile rate + functional    │
  │    rate                               │
  └──────────────────────────────────────┘
```

### 4.2 核心模块职责矩阵

| 角色 | 做什么 | 输出 | 关键技术点 |
|------|--------|------|-----------|
| ① 语料采集 Engineer | GitHub BigQuery + 教材 PDF OCR 抽取 | ~50K .v 文件 + 教材文本 | MinHash/Jaccard 去近重复 |
| ② 数据清洗 Pipeline | 去重/去大文件/正则匹配/滑窗 | ~400 MB 训练语料 | 重叠滑窗切分 |
| ③ 模型微调 (Training) | 5 个预训练模型的 next-token 继续训练 | Fine-tuned checkpoints | 因果 LM 目标，DeepSpeed 并行 |
| ④ 推理生成 (Inference) | 自回归 token 生成 | Verilog module candidate | temperature/n/prompt 组合 sweep |
| ⑤ 可执行评测 (Eval) | iverilog 编译 + vvp 仿真 + testbench | compile rate + functional rate | stderr 判编译，stdout 判功能 |

### 4.3 VGen 与其他范式的关键区别

```text
VGen（本文）：
  prompt -> LLM 生成 -> Icarus 编译/仿真 -> compile/functional rate
  特点：单向、无反馈、统计评测

MAGE（DAC 2025）：
  prompt -> 4 Agent 分工 -> 20 候选高温采样 -> 仿真排序 -> State Checkpoint Debug -> 迭代
  特点：多 Agent、仿真反馈闭环、不训练

ChipSeek（2025）：
  prompt -> 生成 -> Yosys 综合 -> PPA reward -> CDPO 微调
  特点：PPA 优化、RL 训练、综合反馈
```

---

## 5. 关键公式

### 5.1 因果语言建模负对数似然损失

论文未给出编号公式，以下是对其训练目标的形式化：

$$
\mathcal{L}(\theta) = -\frac{1}{N}\sum_{i=1}^{N}\sum_{t=1}^{T_i} \log P_{\theta}(x_{i,t} \mid x_{i,<t})
$$

- $\theta$：模型参数（CodeGen 从预训练 weight 初始化）
- $N$：训练样本总数（语料中的连续文本段）
- $T_i$：第 $i$ 个样本的 token 数
- $x_{i,t}$：第 $i$ 个样本的第 $t$ 个 token
- $x_{i,<t}$：$x_{i,1}, \ldots, x_{i,t-1}$，即前缀 token 序列
- $P_{\theta}(x_{i,t} \mid x_{i,<t})$：在给定前缀下，模型预测下一个 token 为 $x_{i,t}$ 的概率

**工程直觉**：这是 GPT 系列自回归模型的标准训练目标。给定 Verilog 代码前缀 "module half_adder(input a, input b, output "，模型要最大化 "sum" 这个 token 的预测概率。所有可学习的知识（Verilog 语法、常见电路模式、命名习惯）都压缩在这个最大化里。

**为什么这么设计**：不是 sequence-to-sequence——VGen 的模型是自回归补全，不是翻译。prompt 到 completion 的界限只在推理阶段有意义，训练阶段它们被拼接成一个连续的 token 序列。没有 compiler feedback：$\mathcal{L}(\theta)$ 只关心 token 预测概率，不关心这些 token 拼起来能不能被 Icarus 编译。编译只是在训练完成后的评测阶段才介入。1 epoch 训练的意味：CodeGen 系列只微调 1 epoch——~400 MB 语料对 16B 参数的模型来说只够"看一眼"。

### 5.2 Temperature 采样

$$
P_T(x_t \mid x_{<t}) = \frac{\exp(z_t / T)}{\sum_{j} \exp(z_j / T)}
$$

- $z_t$：模型输出层在位置 $t$ 的原始 logits（未归一化分数）
- $T$：温度超参数，$T \in \{0.1, 0.3, 0.5, 0.7, 1.0\}$
- $P_T(x_t \mid x_{<t})$：温度缩放后的下一个 token 概率分布

**温度对 RTL 生成的意义**：$T = 0.1$ 时概率分布极度尖锐，几乎等价于 greedy decoding，生成确定性高，适合 Verilog 这种语法刚性强的任务——论文发现 T=0.1 通常是每个模型表现最好的温度。$T = 1.0$ 时不缩放，多样性高但语法错误率上升——对 Verilog 而言高温被证明是"毒药"，随机性更容易破坏 begin/end 配对、信号位宽匹配、敏感表完整性。

**为什么 RTL 不同于软件代码**：软件代码生成通常可以从高温 + 多次采样中获益（采 100 个候选总有一个对的）。RTL 的高温收益更低，因为：(1) Verilog 的"正确"是组合逻辑层的精确真值表映射，不是"语义相似的多种实现"；(2) 一个 token 的错误就改变整个电路行为；(3) 随机性更容易破坏 Verilog 特有的配对结构（module/endmodule、begin/end、case/endcase）。

### 5.3 Nucleus Sampling（top-p）

论文设置 top_p = 1.0（相当于不做 nucleus 过滤），所有 token 按概率采样。这是为了让温度作为唯一的采样随机性来源，消除 top-p 和温度间的交互效应。

### 5.4 论文自定义的 Pass@(scenario\*n)

$$
\text{Pass@}(scenario \times n) = \frac{\text{successful completions in scenario}}{\text{total completions in scenario}}
$$

- $scenario$ = difficulty x prompt detail（如 Basic x Low、Advanced x High）
- $n$：每个 prompt 生成的候选数（论文主结果用 n=10）
- $successful\ completions$：该 scenario 下所有题目 x 所有候选中被判定为 compile pass 或 functional pass 的数量

**这不是标准的 pass@k 无偏估计！** 标准 HumanEval/Codex 的 pass@k 定义是：

$$
\text{pass@}k = \mathbb{E}_{\text{Problems}} \left[ 1 - \frac{\binom{n-c}{k}}{\binom{n}{k}} \right]
$$

其中 $c$ 是每题 n 个样本中通过的个数。论文的 Pass@(scenario\*n) 是把整个 scenario 内所有 completion 的通过数除以总数——这是一种 completion-level fraction，不是 problem-level unbiased estimator。两者在题目数和通过率不均匀时表现不同。

### 5.5 语法通过率与功能通过率的关系

$$
\text{functional rate} \leq \text{compile rate}
$$

这个不等式虽然平凡，但在 VGen 的语境下有深刻的工程含义。以 CodeGen-16B-FT 为例：

| 难度 | Compile Rate | Functional Rate（best scenario） | 差值 |
|------|:---:|:---:|:---:|
| Basic | 0.942 | 0.745 | ~20% |
| Intermediate | 0.728 | 0.270 | ~46% |
| Advanced | 0.596 | 0.294 | ~30% |

**近一半的编译通过代码在仿真中无法通过 testbench。** 这意味着"可编译"远不等于"正确"，任何只用编译率来评估模型的 benchmark 都是不完整的。VGen 的双层评测（先编译后仿真）开创了后来所有 RTL LLM 评测的标准范式。

---

## 6. 训练与实验设置

### 6.1 是否需要训练

**需要训练。** VGen 通过领域微调让通用/代码预训练模型学会 Verilog 语法和常见电路模式。训练目标是标准的 next-token causal LM cross-entropy，输入为 prompt token，标签为同一序列右移一位。

若使用作者已发布的 Hugging Face checkpoint，则不需要再训练。

### 6.2 预训练基线模型

| 模型 | 规模 | 预训练数据 | Layers | Heads | Embed | Context |
|------|------|-----------|--------|-------|-------|---------|
| MegatronLM-355M | 355M | NL | 24 | 16 | 64 | 1024 |
| J1-Large-7B | 7B | NL | 32 | 32 | 128 | 4096 |
| CodeGen-2B | 2B | NL + Code | 32 | 32 | 80 | 2048 |
| CodeGen-6B | 6B | NL + Code | 33 | 16 | 256 | 2048 |
| CodeGen-16B | 16B | NL + Code | 34 | 24 | 256 | 2048 |
| code-davinci-002 | ~175B (GPT-3) | NL + Code | N/A | N/A | N/A | 8000 |

### 6.3 训练基础设施

| 模型 | 硬件 | 时间 | Epochs |
|------|------|------|--------|
| CodeGen-2B | 2x NVIDIA RTX 8000 | 2 天 | 1 |
| CodeGen-6B | 4x NVIDIA RTX 8000 | 4 天 | 1 |
| CodeGen-16B | 3x NVIDIA A100 | 6 天 | 1 |
| MegatronLM-355M | 1x NVIDIA RTX 8000 | 15 小时 | 9 |
| J1-Large-7B | AI21 Studio 商业微调 | -- | -- |

CodeGen-16B 在 16-bit 精度下参数占 30 GB GPU 内存，微调需约 250 GB（含 optimizer states），使用基于 **DeepSpeed** 的模型/数据并行与 ZeRO optimizer state sharding。CodeGen 系列使用 GPT-2 tokenizer。

### 6.4 实验设置

- **Benchmark**：自建 17 题 Set I，分 Basic（4 题）/Intermediate（8 题）/Advanced（5 题）三档
- **Baseline**：各模型的预训练版本（PT），以及商业 code-davinci-002
- **评估指标**：compile rate（Icarus 编译通过比例）、functional rate（testbench 通过比例）、Pass@(scenario\*n)（论文自定义 completion-level fraction）
- **消融设计**：GitHub-only vs GitHub+books 语料对比（报告仅 1.4pp 差异）

### 6.5 关键实验结果

#### Table III：Set I 编译率 Pass@(scenario\*n)，n=10，best temperature

| 模型 | 类型 | Basic | Intermediate | Advanced |
|------|------|-------|--------------|----------|
| MegatronLM-355M | PT | 0.000 | 0.000 | 0.000 |
| MegatronLM-355M | FT | 0.730 | 0.391 | 0.165 |
| CodeGen-2B | PT | 0.080 | 0.065 | 0.176 |
| CodeGen-2B | FT | 0.902 | 0.612 | 0.592 |
| CodeGen-6B | PT | 0.052 | 0.152 | 0.187 |
| CodeGen-6B | FT | **0.987** | 0.689 | 0.599 |
| J1-Large-7B | PT | 0.182 | 0.176 | 0.108 |
| J1-Large-7B | FT | 0.882 | 0.635 | 0.588 |
| CodeGen-16B | PT | 0.132 | 0.203 | 0.240 |
| CodeGen-16B | FT | 0.942 | **0.728** | **0.596** |
| code-davinci-002 | PT | 0.847 | 0.452 | 0.569 |

#### Table IV：Set I 功能正确率 Pass@(scenario\*n)，n=10，best temperature

| 模型 | 类型 | Basic L | Basic M | Basic H | Inter L | Inter M | Inter H | Adv L | Adv M | Adv H |
|------|------|---------|---------|---------|---------|---------|---------|-------|-------|-------|
| MegatronLM-355M | PT | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |
| MegatronLM-355M | FT | 0.170 | 0.591 | 0.245 | 0.043 | 0.018 | 0.025 | 0.000 | 0.000 | 0.000 |
| CodeGen-2B | PT | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.016 | 0.020 |
| CodeGen-2B | FT | 0.835 | 0.350 | 0.630 | 0.130 | 0.092 | 0.163 | 0.132 | 0.048 | 0.068 |
| CodeGen-6B | PT | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.013 | 0.000 | 0.000 | 0.000 |
| CodeGen-6B | FT | **1.000** | 0.500 | 0.760 | 0.135 | 0.150 | 0.168 | 0.284 | 0.164 | 0.164 |
| J1-Large-7B | PT | 0.044 | 0.058 | 0.067 | 0.000 | 0.000 | 0.021 | 0.000 | 0.000 | 0.000 |
| J1-Large-7B | FT | 0.388 | 0.283 | 0.342 | 0.125 | 0.075 | 0.200 | 0.000 | 0.000 | 0.000 |
| CodeGen-16B | PT | 0.000 | 0.085 | 0.055 | 0.035 | 0.003 | 0.045 | 0.012 | 0.000 | 0.016 |
| CodeGen-16B | FT | 0.745 | **0.720** | **0.745** | **0.213** | **0.270** | **0.255** | **0.246** | **0.290** | **0.294** |
| code-davinci-002 | PT | 0.520 | 0.685 | 0.775 | 0.175 | 0.200 | 0.150 | 0.156 | 0.184 | 0.344 |

**这张表说明了什么**：
1. 微调后模型在所有 difficulty/prompt 组合上均优于预训练版本，微调是决定性的。
2. CodeGen-16B-FT 在 Intermediate M（0.270）和 Advanced H（0.294）上为 overall 最佳。
3. Basic 题上 CodeGen-6B-FT 达到天花板（1.000），更大的模型在此无额外收益——真正的区分度在 Intermediate 和 Advanced 档位。

#### 核心结论汇总

| 口径 | 数值 |
|------|------|
| 所有预训练模型 completions 功能正确率 | 1.09% |
| 所有微调模型 completions 功能正确率 | 27.0% |
| CodeGen-16B-FT 整体功能正确率 | 41.9% |
| code-davinci-002 整体功能正确率 | 35.4% |
| 最佳预训练编译率 | 11.9% |
| 最佳微调编译率 | 64.6% |
| GitHub+教材 相对 GitHub-only 提升 | 约 1.4 pp |

**解读**：微调显著提升 Verilog 语法与功能正确率；预训练模型几乎无法生成功能正确代码（1.09%），微调后达到 27.0%；最大的 CodeGen-16B 微调后达 41.9%，超过 code-davinci-002 的 35.4%。

#### 关键问题分析

论文对 CodeGen-16B-FT 的 540 个 completion 进行手动分析，发现：
- **Problem 7（LFSR）**：没有候选通过；模型难以将最高位与反馈值正确拼接
- **Problem 9（Shift and Rotate）**：仅 1 个候选通过；模型对移位值覆盖不全或位位置赋值错误
- **Problem 12（Truth table）**：没有候选通过；模型使用了所有输入值但无法形成正确布尔表达式
- 这些失败说明训练语料在特定电路模式（LFSR feedback、shift/rotate、truth-table mapping）上多样性不足

---

## 7. 创新点

### 创新点 1：第一个系统性的 LLM Verilog 生成能力评测框架

在 VGen 之前，LLM 代码生成的研究集中在 Python/Java/C++ 等软件语言，硬件描述语言几乎没人碰。VGen 第一次把以下要素整合成完整评测框架：5 种不同规模/预训练数据的模型（355M 自然语言到 16B 自然语言+代码）、17 道难度分级的自建题、3 种 prompt 详细度、5 档 temperature、3 档候选数、双层可执行评测（编译 + 功能仿真）。论文 Table III 和 Table IV 是当时最全面的 RTL LLM 评测结果表，后续所有工作都以这两张表为 baseline 对比。

### 创新点 2：GitHub + 教材双源语料的构建与消融

VGen 设计了一套从采集到清洗的完整 pipeline：GitHub BigQuery 精确检索 `.v` 文件而非爬虫盲目抓取、MinHash + Jaccard 去近重复解决开源 IP core 跨仓库重复问题、70 本教材 PDF + OCR 把自然语言规格到 Verilog 实现的映射关系注入训练数据。消融实验显示 GitHub-only vs GitHub+books 在 CodeGen-16B 上仅差约 1.4pp——这并非教材无用，而是说明 PDF OCR 噪声损害了教材语料质量、300 MB GitHub 代码已覆盖大部分 Verilog 语法、仅 1 epoch 微调不足以充分吸收教材中的语义映射。

### 创新点 3：可执行测试取代文本相似度

VGen 用 Icarus Verilog（开源编译器）+ 自建 testbench 做可执行评测。编译成功 + testbench 全过 = 功能正确；否则就是不正确。这个方法论选择把"代码对不对"的评判权从文本匹配度交给仿真器——一段语法完全正确但用 `|` 代替 `^` 的代码（在 BLEU 可能得高分）在 Icarus 面前就是错的。它帮助建立了后来整个 RTL LLM 领域的评测标准——RTLCoder、MAGE、AutoChip、ChipSeek 都在用 Icarus/testbench 做功能评测。

### 创新点 4：系统研究 temperature 和 n 对 RTL 生成的影响

论文的 temperature sweep（0.1~1.0，5 档）和候选数 sweep（1/10/25）是当时最系统的 RTL 生成采样研究。关键发现：T=0.1 通常是每个模型表现最好的温度、n=10 是较好的折中、RTL 不同于软件代码——软件代码可以从高温 + 多次采样中获益，但 RTL 语言的刚性语法使高温的随机性更可能破坏代码。这个发现被后来的 MAGE 引用并"推翻"——MAGE 的论点是高温在 RTL 上确实会降低平均质量，但如果有独立的 Judge Agent + 仿真打分来筛选，高温的探索收益就能被保留（MAGE 用 T=0.85 + 20 个候选拿到最好结果）。

### 创新点 5：开源模型 + 领域微调超过商业 API 的早期证据

CodeGen-16B-FT（41.9%）超过 code-davinci-002（35.4%）证明了一个关键命题：**开源模型 + 领域微调可以在垂直领域超过通用大模型。** VGen 开创的"领域微调 vs 通用大模型"对比范式被后续几乎所有工作沿用。

### 创新点 6：prompt 详细度并非单调的发现

以 CodeGen-6B-FT 的 Basic 题为例：L=1.000、M=0.500、H=0.760——**更详细的 prompt 反而导致更差的结果。** 可能原因：M prompt 的行为描述引入了歧义、prompt 变长将 module header 推到更靠后的位置稀释了注意力、模型的训练分布更接近 L 的风格。这个发现对后来 RTL prompt 设计有直接指导：prompt 不是越详细越好，简洁精准的模块头 + 关键行为注释可能是最优策略。

---

## 8. EDA 缩写表

| 缩写 | 全称 | 一句话解释 |
|------|------|-----------|
| **RTL** | Register-Transfer Level | 寄存器传输级，数字设计的抽象层次：只描述"每个时钟沿数据从哪个寄存器经过什么组合逻辑流到哪个寄存器" |
| **LLM** | Large Language Model | 大语言模型，本文实测 CodeGen 2B/6B/16B、MegatronLM 355M、J1-Large 7B、code-davinci-002 |
| **EDA** | Electronic Design Automation | 电子设计自动化，芯片设计工具链的总称。本文中特指 Icarus Verilog |
| **HDL** | Hardware Description Language | 硬件描述语言，主流是 Verilog/SystemVerilog/VHDL。和软件语言的区别：语句默认并行执行 |
| **FSM** | Finite State Machine | 有限状态机，数字电路设计的核心抽象。Set I 包含 3 道 FSM 题（Problem 8/15/17） |
| **RAM** | Random Access Memory | 随机存取存储器。Problem 10 要求实现 RAM |
| **LFSR** | Linear Feedback Shift Register | 线性反馈移位寄存器，伪随机数生成器电路。Problem 7 是所有模型中通过率最低的题（0/540） |
| **MUX** | Multiplexer | 多路选择器。Problem 4 是 Basic 档的 2-to-1 MUX |
| **DUT** | Design Under Test | 待测设计，testbench 里被例化、被施加激励、被检查输出的那个模块 |
| **TB** | TestBench | 测试平台，非可综合的 Verilog 代码，生成时钟、施加激励、采集 DUT 输出并与期望值比对 |
| **PT** | Pre-Trained | 预训练，指未在 Verilog 语料上微调的原版模型 |
| **FT** | Fine-Tuned | 微调，指在 Verilog 语料上做领域持续训练后的模型 |
| **SDF** | Standard Delay Format | 标准延时格式，综合/布线后生成的每个门/每条路径的延迟清单。VGen 不涉及 |
| **SPEF** | Standard Parasitic Exchange Format | 标准寄生参数交换格式，从版图提取的走线寄生 RC 参数。VGen 不涉及 |
| **STA** | Static Timing Analysis | 静态时序分析，不跑仿真，纯数学枚举所有路径延迟。VGen 不涉及 |
| **BLEU** | Bilingual Evaluation Understudy | 双语评估基准，文本 n-gram 匹配指标。VGen 明确不用 BLEU |
| **OCR** | Optical Character Recognition | 光学字符识别，用于 70 本教材 PDF 中非数字原生页面的文本提取 |
| **GPU** | Graphics Processing Unit | 图形处理单元。VGen 用 RTX8000 和 A100 |
| **API** | Application Programming Interface | 应用程序接口，调用商业 LLM 的付费接口 |
| **PPA** | Power, Performance and Area | 功耗、性能、面积，数字芯片三大核心质量指标。VGen 完全不优化 PPA |
| **RoPE** | Rotary Position Embedding | 旋转位置编码，CodeGen 使用的相对位置编码 |
| **ZeRO** | Zero Redundancy Optimizer | DeepSpeed 的优化器状态分片技术 |
| **MinHash** | Min-wise Independent Permutations Hashing | 近似去重算法，通过多个哈希函数估计文档 Jaccard 相似度 |

---

## 9. 与芯片流程的关系

### 9.1 VGen 在全流程中的位置

```text
  人写规格（自然语言或模块头）
         │
         ▼
┌─────────────────────────────────────┐
│  ① RTL 设计    ← VGen 在这里        │
│        ↓                            │  VGen: 生成候选 -> 编译/仿真评测 -> 统计报告
│  ② RTL 功能仿真                      │  无迭代闭环，无反馈修复
│    （Icarus 编译 + vvp testbench）    │
└────────────┬────────────────────────┘
             │  ⚠️ 交接面：VGen 到此为止，只输出评测统计数据
             ▼
   ③ 逻辑综合  ← 第一道可能推翻 VGen 成果的关卡
             ▼
   ④ 门级仿真  ← 第二道
             ▼
   ⑤ STA  ⑥ 形式验证
             ▼
   ⑦ Floorplan → ⑧ Placement → ⑨ CTS → ⑩ Routing
             ▼
   ⑪ 后仿真 → ⑫ DRC/LVS → ⑬ Signoff → ⑭ 流片 → ... → ⑰ 芯片
```

### 9.2 「功能仿真通过」和「能流片」之间隔着什么

VGen 的 functional pass 只保证**给定 testbench 的全部检查点通过**。以下每种情形都会在 functional pass 的情况下被后续阶段拦截。

**情形 A：用 initial 赋初值**——仿真器认，ASIC 综合器不认。training corpus 中的 GitHub 代码大量使用 `initial` 块做仿真初始化，模型可能学会了这种写法并用于 RTL 设计。

**情形 B：组合逻辑环**——仿真可能收敛，综合必炸。组合环无法做 STA（路径无限长），综合报错。

**情形 C：Latch 推断**——功能"对"，但综合出锁存器。always @(\*) 中缺少 else 分支导致 latch，如果 testbench 恰好只在 sel=1 时检查 out，就发现不了问题。

**情形 D：不完整敏感列表**——敏感列表只有 a 但右边用了 b，RTL 仿真和综合后网表行为不一致。

**情形 E：时序逻辑用阻塞赋值**——同一 always 块内阻塞赋值让多个赋值在零时间内完成，综合后的真实时序行为不同。

**情形 F：跨时钟域无同步器**——RTL 零延迟仿真看不出问题，门级仿真 + SDF 会暴露亚稳态。

**总结**：VGen 的 functional pass = "给定 testbench 范围内，RTL 行为正确"。它**不代表**代码可综合、时序收敛、无 latch、敏感列表完整、CDC 安全、面积/功耗优化。

---

## 10. 讨论与局限

### 10.1 论文自述的局限

1. **Benchmark 规模小（17 题）**：论文自述 17 题不足以区分现代大模型，且题目部分灵感来自 HDLBits 和课堂练习，未做 decontamination 检查。
2. **Testbench 覆盖率有限**：Basic 题几乎穷举，但 Intermediate/Advanced 题的 testbench 只覆盖问题描述中明确指定的行为。FSM 题不测试同步/异步 reset 的 corner case。
3. **Prompt 质量敏感**：LFSR 等难题的失败可能通过更好的 prompt 解决，指向 prompt engineering 作为未来方向。
4. **训练语料在特定模式上多样性不足**：LFSR feedback、shift/rotate、truth-table mapping 等电路模式的训练数据太少。
5. **仅 1 epoch 微调**：CodeGen 系列只微调 1 epoch，教材语料的消融增益仅 1.4pp。

### 10.2 代码/复现层面的问题

从复现审计中提炼的关键问题：

1. **L/M/H prompt 输出目录冲突**：同题三档 prompt 写入同一目录，先执行者创建目录后，后两档被跳过，无法重算全部结果。
2. **advanced3 的 H prompt 泄漏完整答案**：prompt 文件内包含完整可执行的 Verilog（含 endmodule），评测失去意义。
3. **编译成功只看 stderr 是否为空**：不检查 return code、不管 timeout、warning 会误判为编译失败。
4. **功能成功只看 stdout 最后 17 个字符**：多一个空格/换行/testbench 尾日志就误判。
5. **get_results.py 最终只汇总 advanced5 一题**：其余 16 道题的结果被丢弃。
6. **run_eval.sh 使用 n=20 而论文是 n=25**：默认配置和论文协议不一致。
7. **当前仓库无完整训练脚本/权重**：只有 demo notebook 和 evaluator zip，没有完整 300/400 MB corpus。
8. **训练数据许可证与来源未公开**：70 本教材清单、GitHub 文件 commit/license 未提供。

这些问题意味着：**即使拥有完整的论文语料、模型权重和原始 completions，当前仓库的 evaluator 也无法直接重算 Table III/IV。** 复现等级：**R1**（论文与 artifact 静态核验，不是重新推理或重训）。

### 10.3 本资料包的批判性分析

1. **论文自定义 Pass@(scenario\*n) 不是标准 pass@k**：不能和 VerilogEval/HumanEval 的 pass@k 按名称直接比较。scenario 内的题目权重取决于各题在该 scenario 下的候选数。
2. **数据污染风险**：训练语料来自 GitHub 公开仓库和教材 PDF，Set I 的 17 道题部分灵感来自 HDLBits——存在部分题目或其变体出现在训练语料中的可能性，没有做任何 decontamination 检查。
3. **只覆盖单文件简单模块**：训练语料删除了 >= 20K 字符的大文件（恰好可能是复杂的多模块设计），17 道题全部是单一 module 的独立功能，没有涉及 module instantiation、hierarchy、interface、package 等 Verilog 核心特性。
4. **Temperature best-of 报告可能高估能力**：论文对每个 model/scenario 选 best temperature，这不是固定温度下的公平比较。在真实使用场景中，用户不知道哪个温度最好，只能用固定温度。
5. **人工评估的缺失**：对于 functional pass 的候选，不知道代码风格、是否使用非惯用写法、testbench 覆盖不到的场景下是否有 bug。对于 functional fail 的候选，不知道失败是因为"完全理解错误"还是"差一个边角条件"。

---

## 11. 复现信息

| 项目 | 内容 |
|------|------|
| 论文页 | https://arxiv.org/abs/2212.11140 |
| 代码 | https://github.com/shailja-thakur/VGen，本地 commit `81710f872caf` |
| 数据集 | Google BigQuery + 70 本教材 PDF，未公开完整清单和 license；有 BigQuery/PDF 抽取脚本但无完整 corpus |
| 模型权重 | https://huggingface.co/shailja（CodeGen-2B/6B/16B 微调版本），2B 约 11.23 GB（FP32 两分片），许可证 BigCode OpenRAIL-M |
| 本地状态 | 已审计（静态代码审计 + 论文对照），未重训/未重跑评测 |
| 复现等级 | **R1**（论文与 artifact 静态核验） |
| 主要门槛 | 1）完整 400MB corpus 未公开；2）16B 训练需 3x A100 + 250GB GPU 内存 + 6 天；3）当前 evaluator 代码有多个 bug 无法直接重算 Table III/IV；4）Set I 的 prompt/testbench 有但评估脚本不可靠 |

---

## 12. 一分钟复述版

**VGen/VeriGen 是 2022 年底最早系统研究"LLM 能不能写 Verilog"的工作。** 它做了四件事：

1. 从 GitHub BigQuery（280 万仓库）和 70 本教材 PDF 清洗出约 400MB Verilog 语料
2. 在这个语料上微调了 5 个模型（355M 到 16B，全都用 next-token cross-entropy，没有任何 compiler feedback 或 RL）
3. 设计了 17 道难度分级 + 3 种 prompt 详细度的自建 benchmark
4. 用 Icarus Verilog（开源编译器）+ 自建 testbench 做双层可执行评测（编译 + 功能仿真）

核心发现：领域微调将功能正确率从 1.09% 拉到 27.0%，CodeGen-16B 微调后达 41.9%，超过同期 code-davinci-002 的 35.4%。Temperature=0.1 通常最好，更详细的 prompt 不一定更好，难题（LFSR / truth table / shift-rotate）几乎全败。

它的历史意义不是模型创新（用的就是现成 CodeGen），而是**建立了 RTL LLM 研究的方法论基线**：领域语料构建 pipeline、可执行测试代替文本相似度、采样参数消融、模型规模 scaling 分析——这些后来被 RTLCoder、VerilogEval、MAGE、AutoChip 等所有 RTL LLM 工作继承和扩展。

---

> 扩展版（2308.00708）的 Set II HDLBits 在线评测、GPT-3.5/4/PaLM2 对比、教材多源语料消融、guided system prompt 实验等新增内容，详见 [论文深度讲解_VeriGen-Model.md](./论文深度讲解_VeriGen-Model.md)。
> 原始复现审计详见 [VeriGen论文与代码复现详解.md](./VeriGen论文与代码复现详解.md)。
