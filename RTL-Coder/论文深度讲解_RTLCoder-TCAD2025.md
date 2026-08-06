# RTLCoder (TCAD 2025) 论文深度讲解

> **RTLCoder: Fully Open-Source and Efficient LLM-Assisted RTL Code Generation Technique**
> Shang Liu, Wenji Fang, Yao Lu, Jing Wang, Qijun Zhang, Hongce Zhang, Zhiyao Xie
> 香港科技大学（HKUST）及广州校区
> IEEE TCAD, Vol. 44, No. 4, April 2025 · DOI: 10.1109/TCAD.2024.3483089 · 原文：[TCAD2025_RTLCoder.pdf](./TCAD2025_RTLCoder.pdf)
> 代码：https://github.com/hkust-zhiyao/RTL-Coder
> 模型：https://huggingface.co/ishorn5

> 本文是 TCAD 2025 期刊版（14 页）的完整讲解，是 RTLCoder 方法论的最完整版本。相比于 5 页的 [LAD 2024 会议版](./论文深度讲解_RTLCoder-arXiv.md)，本文新增了：完整 prompt 示例与可视化、数据分布与多样性量化（CR/CR:POS）、Gradient Splitting 的 Algorithm 1 完整伪代码、4-bit 量化部署与评测、逐题详测热力图、beam search vs sampling 解码消融、通用代码能力影响分析、以及扩写的未来方向讨论。两版共享同一套代码仓库、数据集和模型权重。

---

## 1. 一句话定位

**RTLCoder 是 LLM 辅助 RTL 代码生成领域的开源基线方案：用 GPT-3.5 蒸馏出 27,000 条 Verilog 指令-代码训练对，通过 Quality-Scoring 偏好训练（MLE + 成对 margin loss）和 Gradient Splitting 显存优化，在仅 7B 参数、4 张消费级 GPU 的条件下，以 pass@1 62.5% 在 VerilogEval Machine 上超过 GPT-4；4-bit 量化后模型仅 4GB，可在笔记本 CPU 上运行；数据集、训练脚本、FP16 和 4-bit 权重全部开源。**

拆解五个承重点：

1. **GPT-3.5 蒸馏 + 提纯** -- teacher 生成 instruction-code 对，但只保留通过语法检查的子集。本质是 knowledge distillation with quality filtering：student 只学 teacher 的正确答案，过滤掉 teacher 的犯错分布。
2. **Quality-Scoring 训练** -- 在 MLE 基础上叠成对排序损失，让模型不只学会"写 Verilog"，还学会"判断哪种写法更好"。解决的是 MLE 的 exposure bias。
3. **Gradient Splitting** -- 链式法则拆分计算图，把多候选训练的激活峰值内存从 $O(K)$ 降到 $O(1)$。Algorithm 1 的完整伪代码是 TCAD 版的核心新增。
4. **4-bit 量化部署** -- GPTQ 量化到 INT4，模型仅 4GB，可纯 CPU 推理。EvalMachine Pass@1 仅从 61.2% 降到 59.6%（-1.6 个百分点），仍超过 GPT-3.5。
5. **全开源** -- 数据、训练脚本、推理脚本、Mistral/DeepSeek 两个基座的 FP16 权重和 INT4 权重全部公开。TCAD 版首次完整报告量化模型的 benchmark 性能。

---

## 2. EDA 阶段映射（①-⑰）

参照 [芯片流程.md](../芯片流程.md) 的 17 阶段标准编号：

| 阶段 | 覆盖 | RTLCoder 做了什么 / 为什么没做 |
|------|:---:|------------------------------|
| **① RTL 设计** | ✅ **核心** | 自然语言规格 → 7B causal LM 自回归生成完整 Verilog module |
| **② RTL 功能仿真** | ⚠️ **评测用** | 训练时不跑仿真（只有 Pyverilog 语法检查）；benchmark 评测时用 Icarus/VCS + testbench 验证，RTLLM benchmark 报告 Function Pass@5 |
| **③ 逻辑综合** | ⚠️ **间接** | RTLLM benchmark 使用 Synopsys VCS 和 Design Compiler 分别检查 Syn-VCS（语法+接口兼容）和 Syn-DC（物理可综合性）。**训练目标不含任何综合/PPA 信息**——TCAD 版新增 Syn-VCS vs Syn-DC 的细粒度区分 |
| ④ 门级仿真 | ❌ | 无 SDF（Standard Delay Format，标准延时格式）反标，不检查毛刺、建立/保持违例、X 传播 |
| ⑤ STA（Static Timing Analysis，静态时序分析） | ❌ | 不计算路径延迟。RTLLM 的 Syn-DC 只检查"可综合"，不检查"能通过 STA" |
| ⑥ 形式验证 | ❌ | 不做等价性证明。TCAD 版 Section V 将此列为未来方向：用 LLM 自动生成 SVA（SystemVerilog Assertions）+ Jasper 等形式工具做功能验证 |
| ⑦ 布局规划 Floorplan | ❌ | — |
| ⑧ 标准单元摆放 Placement | ❌ | — |
| ⑨ CTS（Clock Tree Synthesis，时钟树综合） | ❌ | — |
| ⑩ 布线 Routing | ❌ | — |
| ⑪ 后仿真 | ❌ | 无 SPEF（Standard Parasitic Exchange Format，标准寄生参数交换格式） |
| ⑫ DRC（Design Rule Check，设计规则检查）/ LVS（Layout Versus Schematic，版图与原理图一致性检查） | ❌ | — |
| ⑬ 签核 Signoff | ❌ | — |
| ⑭-⑰ 流片→制造→封装测试→芯片 | ❌ | — |

**覆盖率：1/17（或 2/17 若将评测用的仿真 + 综合检查各算半个）。** RTLCoder 是纯粹的 RTL 设计辅助工具，比 MAGE 多了一个间接的综合检查（评测时），但比 ChipSeek 少了 EDA 工具的 PPA 奖励进训练环。

> ⚠️ 与 MAGE、ChipSeek 的定位三角：MAGE 把仿真反馈用在推理时迭代纠错（推理时工具调用），ChipSeek 把 EDA 反馈做成 RL reward 更新参数（训练时工具调用），RTLCoder 的训练信号来自**静态语法检查**（训练和推理都不真跑 EDA 工具环）。三者在"训练时 vs 推理时 vs 都不做 EDA 调用"三个象限各占一角。

---

## 3. 输入 / 输出

### 3.1 数据生成阶段的完整 prompt 示例（TCAD 版新增）

#### Stage 1: 关键词准备 Prompt (Figure 2)

```text
[P_key - 根节点 prompt]
Please provide categories and examples of frequently used block keywords
in RTL design. Output in a tree structure:
- Category 1: name
  - sub-category 1: keywords
  - sub-category 2: keywords
- Category 2: name
  ...
```

GPT-3.5 响应示例 (Figure 3)：

```text
- Combinational Logic: AND gate, OR gate, NAND gate, NOR gate, XOR gate,
  XNOR gate, Multiplexer (MUX), Demultiplexer (DEMUX), Encoder, Decoder,
  Priority Encoder, Magnitude Comparator, ...
- Sequential Logic: D Flip-Flop, JK Flip-Flop, T Flip-Flop, SR Latch,
  D Latch, Register, Shift Register, Counter (Binary, BCD, Ring, Johnson),
  ...
- Arithmetic Units: Half Adder, Full Adder, Ripple Carry Adder, ...
- Finite State Machines: Mealy, Moore, Sequence Detector, ...
- Memory: RAM, ROM, FIFO, LIFO, Register File, CAM, ...
- Interface: UART, SPI, I2C, AHB, AXI, ...
```

最终约 350 个关键词，分布见论文 Figure 10(a)：组合逻辑 ~23%、时序逻辑 ~18%、FSM ~15%、算术单元 ~14%、存储 ~12%、接口 ~10%、其他 ~8%。

#### Stage 2: 关键词扩展 Prompt (Figure 4-5)

```text
[P_ext^key - few-shot prompt]
Given the following digital design keyword: "Pulse width modulators (PWM)",
please generate a complete Verilog design instruction.

Example:
Keyword: "Traffic Light Controller"
Instruction: Please act as a professional Verilog designer. Design a traffic
light controller for a two-way intersection. The controller should cycle
through green, yellow, red states with configurable timing for each state.
Include a reset signal to return to the initial state.
```

GPT-3.5 的 PWM 响应 (Figure 5)：

```text
Please act as a professional Verilog designer. Create a module that
implements a Pulse Width Modulator (PWM). The PWM module takes a clock
signal, a reset signal, and an 8-bit duty cycle value as inputs. It outputs
a single PWM signal. The PWM module should increment an 8-bit counter on
each clock cycle. When the counter value is less than the duty cycle value,
the PWM output is high; otherwise, it is low. The PWM period is determined
by the counter rollover at 255.
```

#### Stage 2: 源码反向生成 Prompt (Figure 6-7)

```text
[P_ext^code]
Please analyze the following Verilog code snippet and generate a natural
language instruction that describes its functionality in detail.

[Verilog code snippet]
```

#### Stage 2: 变异 Prompt (Figure 8-9)

```text
[P_smut - 单电路变异]
The rewritten task should achieve different circuit functionality but
require similar methods or components in the given instruction.

[Given Instruction]
Please act as a professional Verilog coder. Create a module that implements
a finite state machine (FSM), used for 5-bit sequence detection.

[New Instruction]
Please act as a professional Verilog designer. Create a module that
implements a FSM, used for 5-bit sequence detection, but with a twist.
The module should detect two different 5-bit sequences, "01010" and "10101",
and output a signal indicating which sequence was detected...
```

```text
[P_cmut - 电路组合]
Combine two circuit designs together [二进制计数器 + 比较器]:
- Parallel: add control logic to select between functionalities
- Serial: feed one output into the other's input
```

### 3.2 训练数据格式

**(a) 普通 SFT 条目（JSONL，来自 RTLCoder-27K）**

```json
{"Instruction": "Please act as a professional verilog designer. Design a 1-bit half adder with inputs a, b and outputs sum, carry.",
 "Response": ["module half_adder(input a, input b, output sum, output carry); assign sum = a ^ b; assign carry = a & b; endmodule"]}
```

训练拼接：`source = Instruction + "\n"`, `target = Response[-1] + eos_token`。loss mask 掉 source token，只监督 target token。

**(b) Quality-Scoring 条目**

```json
{"Instruction": "Generate a 2-input AND gate.",
 "Input": "module and2(input a, input b, output y);",
 "Response": ["assign y = a & b; endmodule", "assign y = a | b; endmodule"],
 "Score": [1.0, 0.0]}
```

评分规则：参考代码和通过 Pyverilog 语法检查的候选得满分 1；未通过的用 Rouge-L 与参考代码的相似度作为分数。仓库真实样本的分值形态如 `[0.404, 0.355, 0.002, 1.0]`。

### 3.3 推理输入与输出

推理输入与 arXiv 版相同。TCAD 版新增了 4-bit 量化模型的完整推理评测：EvalMachine Pass@1 从 61.2% 降到 59.6%（-1.6pp），EvalHuman 从 41.6% 降到 38.1%（-3.5pp），但仍超过 GPT-3.5（46.7%/26.7%）。

---

## 4. 方法与架构

### 4.1 数据生成流水线（TCAD 版 Figure 1，含完整标注）

```text
┌─────────────────────────────────────────────────────────────────────────┐
│ Stage 1: RTL Domain Keywords Preparation                                 │
│ ─────────────────────────────────────────────────────────────────────── │
│  ❶ P_key (树状层次 prompt) → GPT-3.5 → L_key (~350 个关键词)           │
│  覆盖: Combinational, Sequential, Arithmetic, FSM, Memory, Interface... │
│  分布: Figure 10(a)                                                     │
├─────────────────────────────────────────────────────────────────────────┤
│ Stage 2: Instruction Generation                                         │
│ ─────────────────────────────────────────────────────────────────────── │
│  ❷ P_ext^key (few-shot) + L_key → GPT-3.5 → Design Instructions         │
│  ❸ P_ext^code (code→description) + L_code → GPT-3.5 → Instructions      │
│     ┌─ 两种方法互补：关键词→高抽象概括，源码→细粒度信号行为             │
│     │                                                                     │
│     ▼                                                                     │
│  初始 L_ins（数百条）                                                      │
│     │                                                                     │
│     ❹ P_mut 变异增强                                                      │
│     ├─ P_smut: 单电路变异 (同硬件不同功能 / 同功能不同硬件)              │
│     └─ P_cmut: 电路组合 (并行/串行)                                      │
│     │                                                                     │
│     ❺ Instruction Checker                                                │
│     ├─ invalid-word 过滤 (非RTL内容: "image", "text" 等)                │
│     └─ Rouge-L 相似度过滤 (>0.7 丢弃)                                    │
│     │                                                                     │
│     ▼                                                                     │
│  最终 L_ins: >50,000 条指令                                               │
├─────────────────────────────────────────────────────────────────────────┤
│ Stage 3: Reference Code Generation                                       │
│ ─────────────────────────────────────────────────────────────────────── │
│  ❻ 每条指令 → GPT-3.5 生成 ≥5 个 Verilog 候选                           │
│  ❼ Pyverilog syntax checker → 至少一个候选通过才保留                     │
│     全部失败 → 丢弃该指令                                                │
│     │                                                                     │
│     ▼                                                                     │
│  RTLCoder-27K: >27,000 条 (Instruction, Response) 对                    │
│  Token 分布 (Figure 12a): instruction 平均 78 tokens, code 平均 345     │
│  Circuit 类型分布 (Figure 10b): 数据通路 28%, 时序逻辑 22%, FSM 15%, ...│
└─────────────────────────────────────────────────────────────────────────┘
```

### 4.2 训练流程（TCAD 版 Figure 11，两阶段对比）

```text
┌─────────────────────────────────────────────────────────────────────────┐
│ (a) 传统 MLE 训练 (Figure 11a)                                           │
│ ─────────────────────────────────────────────────────────────────────── │
│  x_i → Model → P(y_i^t | x_i, y_i^{<t}) → loss_mle = -Σ log P(...)     │
│  只见过 reference token y_i^{<t}，没见过自己生成的 token                 │
│  → exposure bias：训推 token 分布不匹配                                  │
├─────────────────────────────────────────────────────────────────────────┤
│ (b) RTLCoder Quality-Scoring 训练 (Figure 11b)                           │
│ ─────────────────────────────────────────────────────────────────────── │
│  For each instruction x_i:                                               │
│    ① Pre-trained model → Beam search (K=3) → candidates {y_i,k}         │
│    ② Pack with reference y_i → score by Pyverilog + Rouge-L → {z_i,k}  │
│    ③ loss = loss_mle + loss_compare                                     │
│       loss_compare = Σ_{z_k < z_τ} max(s_k - s_τ + λ, 0)               │
│       s_k = softmax(length_normalized_log_prob)                         │
│    ④ Gradient Splitting (Algorithm 1) → update π                         │
├─────────────────────────────────────────────────────────────────────────┤
│ 训练配置 (全参数微调):                                                    │
│   Adam: lr=1e-5, β1=0.9, β2=0.999, no weight decay                     │
│   context=2048, global batch=256 (token 分布保证 2048 够用, Fig 12a)    │
│   4× RTX 4090 (24GB), FP16, DeepSpeed Stage-2                           │
│   无 Gradient Splitting → 不可训练 (显存不够)                           │
└─────────────────────────────────────────────────────────────────────────┘
```

### 4.3 Gradient Splitting 完整算法（TCAD 版 Algorithm 1，核心新增）

```text
Algorithm 1: Training Scheme Using Gradients Splitting
─────────────────────────────────────────────────────────
Input:  Single sample (x_i, {y_i,k}, {z_i,k}), forward func s_k = f_π(...),
        loss func L(s, z), GPU batch size J, model params w
Output: ∂L/∂w

 1: Group candidates into Q = ceil(K/J) batches
 2: temp ← []; g_i ← 0
 3: for q ∈ Q:                              // First forward pass
 4:     s_k = f_π(x_i, y_i,k, z_i,k), for k ∈ q
 5:     Empty computation graph             // 释放激活内存
 6: L = L_π(s_1, ..., s_K)                  // 在分数向量上算 loss
 7: temp_k = ∂L/∂s_k, for k = 1..K           // 仅保存标量梯度
 8: for q ∈ Q:                              // Second forward + backward
 9:     s_k = f_π(x_i, y_i,k, z_i,k), for k ∈ q
10:     g_i += Σ_{k∈q} temp_k · ∂s_k/∂w     // Vector-Jacobian product
11:     Empty computation graph
12: Return g_i
```

**时间-空间权衡**：
- 传统方法：K 个候选同时 forward → 保存 K 份完整激活图 → 反向传播 → $O(K)$ 显存
- Gradient Splitting：forward 两次（第一次收集 $s_k$，第二次做 VJP）+ 中间只存 K 个标量 $\text{temp}_k$ → $O(1)$ 显存（相对于 K）
- 额外开销：多了一次 forward pass（约 +50% 前向 FLOPs），但避免了无法训练的问题

论文直接声明："Under the hardware constraint, the training is impossible without the proposed gradient-splitting method."（Section IV-C）

### 4.4 数据多样性评估（TCAD 版 Table II，新增）

| Dataset | CR | CR:POS | 说明 |
|---------|-----|--------|------|
| **RTLCoder-27K** | **3.57** | **8.12** | 本文数据集 |
| Goh et al. | 5.85 | 9.90 | 仅含module名，无功能描述 |
| MG-Verilog | 6.37 | 10.45 | 多粒度描述集 |
| Magicoder-OSS-75K (Python) | 3.40 | 7.80 | 广泛使用的Python数据集（对照） |

CR（Compression Ratio）和 CR:POS 值越低意味着多样性越高。RTLCoder-27K 的多样性（CR=3.57）与 Python 数据集 Magicoder（CR=3.40）相当，显著优于同期 Verilog 数据集 MG-Verilog（CR=6.37）和 Goh et al.（CR=5.85）。这验证了三阶段数据管线在多样性上的有效性。

### 4.5 模块职责矩阵

| 阶段 | 谁做 | 用什么 | 关键点 |
|------|------|--------|--------|
| 关键词生成 | GPT-3.5 | 树状层次 prompt (Fig 2) | ~350 关键词，10+ 类别 |
| 指令生成 | GPT-3.5 | few-shot P_ext (Fig 4,6) | 关键词→高抽象，源码→细粒度（互补） |
| 指令变异 | GPT-3.5 | P_smut + P_cmut (Fig 8,9) | 规模×复杂度自动扩张 |
| 指令过滤 | 规则脚本 | invalid-word + Rouge-L | 全自动，>50K 条指令 |
| 参考代码生成 | GPT-3.5 | — | 每条 ≥5 候选，语法筛 |
| 多样性评估 | gzip + NLTK | CR/CR:POS | 验证非冗余（新增于 TCAD） |
| MLE 训练 | 7B base model | Adam + DS2 + 4×4090 | 从 36.9% → 58.9% |
| 候选评分 | Pyverilog + Rouge-L | 语法 check + 文本相似度 | **非功能验证** |
| Quality-scoring | 7B base model | Grad Splitting (Alg 1) | +3.6pp，显存 O(K)→O(1) |
| 量化部署 | GPTQ | 4-bit → 4GB | EvalMachine 仅 -1.6pp |
| 评测 | Icarus/VCS/DC | pass@k + Syn-VCS/Syn-DC | TCAD 新增逐题热力图 |

---

## 5. 关键公式

### 5.1 MLE 损失

$$
\mathcal{L}_{\text{MLE}} = -\sum_{t=1}^{T} \log P_{\pi}\!\left(y_i^t \mid x_i,\ y_i^{<t}\right)
$$

- $\pi$：模型参数（Mistral-7B-v0.1 或 DeepSeek-Coder-6.7B）
- $x_i$：第 $i$ 条自然语言指令
- $y_i^t$：参考代码的第 $t$ 个 token
- 仅计算 response token 的 loss，instruction token 设为 ignore index

### 5.2 长度归一化对数概率

$$
p_{i,k} = \frac{\sum_{t} \log P_{\pi}\!\left(y_{i,k}^t \mid x_i,\ y_{i,k}^{<t}\right)}{\|y_{i,k}\|}
$$

- $p_{i,k}$：模型对第 $i$ 条指令的第 $k$ 个候选的**长度归一化**对数概率
- $\|y_{i,k}\|$：候选代码的 token 长度

**为什么必须归一化**：模型的总 log 概率 $\sum_t \log P(y_t)$ 天然随序列长度线性增长。一个 200 token 的 FSM 代码总 logP 可能比 20 token 的 assign 语句高一个数量级，但这不反映代码质量——只是长度效应。除以 $\|y_{i,k}\|$ 后变成"平均每个 token 的对数似然"，长序列不被偏袒。这和 RLHF 中 reward model 的长度惩罚是同构设计。

**工程直觉**：如果不归一化，$\mathcal{L}_{\text{compare}}$ 会让模型把所有候选写成尽可能长的代码（因为长代码 $p_{i,k}$ 天然更大 → $s_{i,k}$ 更大），导致灾难性的啰嗦退化。

### 5.3 Softmax 选择概率

$$
s_{i,k} = \frac{\exp(p_{i,k})}{\sum_{\tau=1}^{K} \exp(p_{i,\tau})}
$$

- $s_{i,k}$：在 $K$ 个候选之间，模型"选择"第 $k$ 个候选的 softmax 概率
- $K$：每个 instruction 的候选数（论文设 $K=3$）

**为什么 softmax 而不是直接用 $p_{i,k}$**：$\mathcal{L}_{\text{compare}}$ 需要"候选间的相对偏好"而非绝对似然。softmax 把 $p_{i,k}$ 转成 $\sum_k s_{i,k} = 1$ 的概率分布，使 pairwise margin loss 可以直接操作。$p_{i,k}$ 本身的值域是整个实数轴，不适合直接做 margin 比较。

### 5.4 比较损失

$$
\mathcal{L}_{\text{compare}} = \sum_{z_{i,k} < z_{i,\tau}} \max\!\left(s_{i,k} - s_{i,\tau} + \lambda,\ 0\right)
$$

- $z_{i,k}$：外部评分（Pyverilog：满分 1；Rouge-L 相似度：$(0, 1)$）
- 遍历所有 $z_k < z_\tau$ 的候选对：（质量差, 质量好）
- $\lambda$：margin 阈值——好候选的 $s$ 必须比差候选至少高 $\lambda$，否则产生正 loss

**机制**：如果模型给低分候选分配了比高分候选更高的选择概率（$s_{\text{差}} > s_{\text{好}}$），loss 惩罚这个差值。直观上：模型被推动去重排候选概率分布，使排序顺序与外部质量分数一致。

**为什么是 pairwise margin 而不是 listwise**：
1. 评分精度低（Pyverilog pass/fail + Rouge-L 相似度），pairwise 只要求相对排序，不要求精确分值差
2. 实现简单，pairwise 对的数量是 $O(K^2)$（$K=3$ 时只有 3-6 对），计算开销可忽略
3. 同一候选可能和参考代码同时得 1——此时 $z_k = z_\tau$，不产生比较对

### 5.5 总损失

$$
\mathcal{L}_{\text{total}} = \mathcal{L}_{\text{MLE}} + \mathcal{L}_{\text{compare}}
$$

两个分量的分工：
- $\mathcal{L}_{\text{MLE}}$：监督信号——教会模型"spec 对应的 Verilog 长什么样"
- $\mathcal{L}_{\text{compare}}$：偏好信号——教会模型"自己的多个想法里哪个更好"

两者的权重是 1:1（无超参平衡系数）。这个设计选择论文未做消融，隐含假设是两个 loss 的量级天然可比。

### 5.6 Gradient Splitting 的数学基础

$$
\frac{\partial \mathcal{L}}{\partial w} = \sum_{k=1}^{K} \frac{\partial \mathcal{L}}{\partial s_{i,k}} \cdot \frac{\partial s_{i,k}}{\partial w}
$$

- $w$：模型参数
- $\frac{\partial \mathcal{L}}{\partial s_{i,k}}$：一个标量——loss 对候选 $k$ 的 softmax 概率的导数。维度 = 1，不需要计算图
- $\frac{\partial s_{i,k}}{\partial w}$：需要通过候选 $k$ 的完整前向计算获得（vector-Jacobian product）

**关键洞察**：$\frac{\partial \mathcal{L}}{\partial s_{i,k}}$ 的计算不需要候选 $k$ 的计算图——它只依赖 $s$ 向量（K 个标量）。因此可以：
1. 第一遍 forward：收集所有 $s_{i,k}$（释放大图）
2. 在小向量上算 $L$ 和 $\frac{\partial L}{\partial s_{i,k}}$
3. 第二遍 forward：逐组重算 $s_{i,k}$，用存好的 $\frac{\partial L}{\partial s_{i,k}}$ 做 dot product + backward

**代价**：多了一遍 forward pass（+50% 前向 FLOPs）。但激活内存从 $O(K)$ 降到 $O(1)$，使 4 张 24GB 消费级 GPU 可以训练 7B 模型。

### 5.7 Pass@k 无偏估计

$$
\text{pass@}k = \mathbb{E}_{\text{Problems}} \left[ 1 - \frac{\binom{n - c_i}{k}}{\binom{n}{k}} \right]
$$

- $n$：每个题目的总采样次数（VerilogEval 设 $n=20$）
- $c_i$：通过 testbench 的次数
- $k = 1, 5, 10$

当 $k=1$ 时简化为 $\mathbb{E}[c_i/n]$，即单次采样通过率的期望。

**与 MAGE 的对比**：RTLCoder 的 pass@1 是一次前向生成的结果，与 vanilla LLM 的 pass@1 成本完全可比。MAGE 的 pass@1 背靠 20 候选采样 + 多轮 debug，两者不在同一量级。

### 5.8 Rouge-L 相似度（训练集与 benchmark 去重）

TCAD 版新增了训练集与 benchmark 的 Rouge-L 相似度分布分析（Figure 12b）。Rouge-L > 0.5 的训练样本被过滤，共计约 100 条。

Rouge-L 基于最长公共子序列（LCS）：

$$
\text{Rouge-L} = \frac{(1+\beta^2) \cdot R_{LCS} \cdot P_{LCS}}{R_{LCS} + \beta^2 \cdot P_{LCS}}
$$

其中 $R_{LCS} = LCS(X,Y)/|X|$（召回率），$P_{LCS} = LCS(X,Y)/|Y|$（精确率）。Figure 12b 显示绝大多数训练样本与 benchmark 的 Rouge-L 低于 0.3。

### 5.9 多样性指标 CR 与 CR:POS（TCAD 版新增）

$$
\text{CR}(D) = \frac{\text{Size of } D^{\oplus}}{\text{Compressed Size of } D^{\oplus}}
$$

- $D^{\oplus}$：将所有文本串联成一个文件
- 压缩算法：gzip
- CR:POS 类似，但先提取词性标签序列再压缩

CR 和 CR:POS 是论文引用的"最佳词法多样性度量"。低值 = 高多样性。RTLCoder-27K 的 CR=3.57 与 Magicoder Python 数据集（3.40）接近，显著低于同期 Verilog 数据集 MG-Verilog（6.37）和 Goh et al.（5.85）。

---

## 6. 训练与实验设置

### 6.1 是否需要训练

**需要训练**。RTLCoder 提供三条训练路线：

| 路线 | 脚本 | 数据 | 目的 |
|------|------|------|------|
| 普通 MLE | `train/mle.py` | 每条规格对应一个参考 RTL | 学习 spec → RTL 映射 |
| Quality-Scoring | `train/mle_scoring.py` | 同一规格有 K 个候选及质量分数 | 让模型偏向高质量候选 |
| Gradient Splitting | `train/mle_scoring_grad_split.py` | 同上 | 降低多候选训练显存峰值 |

训练配置：
- 基座模型：Mistral-7B-v0.1（32 层，hidden 4096，32 query heads，8 KV heads，FFN 14336）或 DeepSeek-Coder-6.7B-Instruct
- 优化器：Adam，$\beta_1=0.9$，$\beta_2=0.999$，$\text{lr}=1 \times 10^{-5}$，无 weight decay
- context length = 2048（基于 Figure 12a 的 token 分布分析：instruction 平均 78 tokens, code 平均 345 tokens，总长 < 2048）
- global batch size = 256
- 硬件：4 张 RTX 4090（24GB），FP16，DeepSpeed Stage-2
- 训练为全参数微调，非 LoRA

若只使用作者已发布的 FP16 或 4-bit 量化权重，则不需要训练。

### 6.2 实验设置

**Benchmark**：
- VerilogEval (Machine 143 题 / Human 156 题)，pass@k 指标（k=1,5,10）
- RTLLM V1.1（29 题），pass@5 指标；分 Syn-VCS、Syn-DC、Functionality 三个子指标
- 生成参数：top_p=0.95, temperature ∈ {0.2, 0.5, 0.8}，对每个模型报告三种温度中的最佳成绩

**Baseline**：GPT-3.5、GPT-4（闭源）；VerilogEval [NVIDIA]、ChipNeMo、BetterV（闭源）；Codegen2-16B、StarCoder-15B、Thakur et al. 16B、Mistral-7B base、DeepSeek-Coder-6.7B base、Goh et al.（开源）

**消融设计**：
- Direct training vs 完整 RTLCoder（验证 quality-scoring 贡献）
- 10K 子集 vs 27K 全量（验证数据规模效应）
- **TCAD 新增**：Sampling vs Beam Search (beam=5) 解码方法消融（Table V）
- **TCAD 新增**：4-bit 量化 vs FP16 性能对比
- **TCAD 新增**：跨语言灾难性遗忘分析（Table VI：Verilog, Python, Cpp, Shell）

### 6.3 关键实验结果

#### 主表（TCAD Table III）

| 模型 | EM Pass@1 | EM Pass@5 | EM Pass@10 | EH Pass@1 | RTLLM Func@5 |
|------|----------:|----------:|-----------:|----------:|-------------:|
| Mistral-7B base | 36.9% | 48.8% | 57.4% | 4.49% | 20.7% |
| DeepSeek-Coder-6.7B base | 54.1% | 63.8% | 67.5% | 30.2% | 34.5% |
| RTLCoder-Mistral-Direct | 58.9% | 70.0% | 74.1% | 34.4% | 41.4% |
| RTLCoder-DeepSeek-Direct | 59.8% | 73.6% | 77.2% | 39.1% | 44.8% |
| **RTLCoder-Mistral** | **62.5%** | **72.2%** | **76.6%** | **36.7%** | **48.3%** |
| **RTLCoder-DeepSeek** | **61.2%** | **76.5%** | **81.8%** | **41.6%** | **48.3%** |
| RTLCoder-DeepSeek-4bit | 59.6% | — | — | 38.1% | — |
| GPT-3.5 | 46.7% | 69.1% | 74.1% | 26.7% | 37.9% |
| GPT-4 | 60.0% | 70.6% | 73.5% | 43.5% | 65.5% |

读法：

1. **数据是主力**：从 base model 到 Direct training，EvalMachine Pass@1 从 36.9%/54.1% 飞跃到 58.9%/59.8%，+22~25 个百分点。
2. **Quality-scoring 是锦上添花**：从 Direct 到完整 RTLCoder，额外 +2.7~3.6 个百分点。数据贡献是 quality-scoring 的 6~7 倍。
3. **4-bit 量化的代价**：EvalMachine -1.6pp，EvalHuman -3.5pp。EvalHuman 退化更大——可能因为量化损害了长距离依赖能力，而 EvalHuman 的描述更抽象。
4. **RTLCoder-Mistral 在 EvalMachine 上超过 GPT-4 2.5 个百分点（62.5% vs 60.0%）**；RTLCoder-DeepSeek 超过 1.2 个百分点。

#### RTLLM V1.1 详细结果（TCAD Table IV）

| 模型 | Syn-VCS | Syn-DC | Functionality |
|------|---------|--------|---------------|
| GPT-3.5 | 89.7% | 89.7% | 37.9% |
| GPT-4 | 100% | 100% | 65.5% |
| RTLCoder-Mistral | 100% | 93.1% | 48.3% |

**Syn-VCS vs Syn-DC 的含义**：Syn-VCS 检查 Verilog 语法 + 模块接口与 testbench 兼容（VCS 编译通过）；Syn-DC 检查物理可综合性（Design Compiler 综合通过）。Syn-DC 比 Syn-VCS 更严格——RTLCoder-Mistral 在 Syn-VCS 上 100%，但 Syn-DC 降为 93.1%，意味着有两道题生成的代码"语法对但综合不过"。

#### Beam Search vs Sampling 消融（TCAD Table V，新增）

TCAD 版在 RTLLM V1.1 上比较了 sampling 和 beam search (beam=5) 两种解码方式。结果显示 beam search 下所有模型的 syntax 和 functionality pass@5 均**低于** sampling。这是反直觉的结果——beam search 在机器翻译等任务上通常优于 sampling。

可能原因：Verilog 的 token 选择比自然语言更"刚"——一个错误的分号、缺失的 `end`、端口宽度不匹配都会导致编译/仿真失败。beam search 维护整体序列概率最高的路径，但这个"高概率"可能对应"语法上常见的 token 组合"而非"语义上正确的 token 组合"。Sampling 的随机性反而能跳出局部最优。这与 MAGE 的高温采样发现（$T=0.85$ 优于 $T=0$）在精神上一致。

#### 跨语言灾难性遗忘分析（TCAD Table VI，新增）

| 模型 | Verilog (EH) | Python (HE+) | Cpp | Shell |
|------|------------:|-------------:|----:|------:|
| Mistral-7B base | 4.49% | 28.7% | 28.3% | 22.4% |
| RTLCoder-Mistral | 36.7% | 26.2% | 19.5% | 12.5% |
| DeepSeek-Coder-6.7B base | 30.2% | 71.6% | 63.4% | 44.7% |
| RTLCoder-DeepSeek | 41.6% | 71.0% | 62.5% | 43.8% |

Mistral 在 Cpp（-8.8pp）和 Shell（-9.9pp）上退化显著，DeepSeek-Coder 几乎无退化（-0.6pp ~ -0.9pp）。**原因**：DeepSeek-Coder 在预训练时已是代码专用模型，Verilog fine-tune 只是在其代码能力上增加一种新语言；Mistral 是通用模型，Verilog fine-tune 会覆盖其部分通用能力。

实践指导：如果下游任务需要保留多语言能力，选 DeepSeek-Coder 做基座；如果只做 Verilog 且追求推理速度（Mistral 的 GQA + rolling buffer KV cache 更快），选 Mistral。

---

## 7. 创新点

### 创新点 1：三阶段合成数据管线 + 多样性量化（TCAD 新增可视化与量化指标）

arXiv 版描述了流程，TCAD 版补齐了：
- **完整 prompt 示例**（Figure 2-9）：$P_{key}$、$P_{ext}^{key}$、$P_{ext}^{code}$、$P_{smut}$、$P_{cmut}$ 的完整文本——研究者可以直接复用
- **关键词类别分布**（Figure 10a）：饼图量化各类别占比
- **训练数据电路类型分布**（Figure 10b）：与 RTLLM-1.1（Figure 10c）和 VerilogEval（Figure 10d）的对比，验证覆盖度
- **Token 长度分布**（Figure 12a）：instruction 平均 78 token，code 平均 345 token，证明 max context=2048 是合理的
- **多样性正式评估**（Table II）：CR/CR:POS 指标首次量化"27K 有多多样"，且与 Python 数据集 Magicoder 相当

### 创新点 2：Quality-Scoring 训练的完整公式化（TCAD 版 Section III-B）

将 arXiv 版零散的文字描述升级为 $p_{i,k}$、$s_{i,k}$、$\mathcal{L}_{\text{compare}}$ 的正式定义，并使两阶段训练（传统 MLE vs Quality-Scoring）在 Figure 11 中可视化对比。TCAD 版还首次解释了 exposure bias 如何具体在 RTL 生成中表现：模型生成低质量代码时会陷入"废话重复"（duplication）——这在自然语言生成中可以用 repetition penalty 解决，但在 RTL 代码中很多正确代码本身就包含重复结构（如 generate 块、多位宽赋值），不能简单用 repetition penalty。

### 创新点 3：Gradient Splitting 的 Algorithm 1 + 形式化推导（TCAD 版核心新增）

arXiv 版只有一句话"decompose the computation graph"。TCAD 版给出完整伪代码（见上文 4.3 节 Algorithm 1）和链式法则推导（公式 5.6），使方法可完全复现。

关键声明："Without the proposed gradient-splitting method, the training is impossible."（Section IV-C）——这不是可选的优化，而是物理前提。

### 创新点 4：4-bit 量化部署（TCAD 版新增）

使用 GPTQ 把训练后的模型参数从 FP16 量化到 INT4，模型文件从约 13GB 压缩到约 4GB。TCAD 版在 Table III 中首次报告了量化模型的完整基准性能。这体现了 RTLCoder 的设计理念——"轻量化 + 隐私保护"：模型可在笔记本上纯 CPU 运行，设计数据永远不离开工程师的机器。

### 创新点 5：细粒度评测与跨模型分析（TCAD 版新增）

- **Table IV**：RTLLM V1.1 上 RTLCoder-Mistral vs GPT-3.5/GPT-4 逐题对比（29 题，每题的三维度：Syn-VCS、Syn-DC、Functionality）
- **Figure 14**：VerilogEval 逐题热力图——143/156 题中每题 20 次采样的通过/失败可视化，帮助定位"哪些题目是共同难点"
- **Table V**：Sampling vs Beam Search 解码消融
- **Table VI**：跨语言灾难性遗忘分析

### 创新点 6：GPT-4 优势的结构化分析 + 未来路线图（TCAD 版新增 Section V）

TCAD 版新增了"为什么 GPT-4 更强"和"开源模型如何追赶"的专题讨论：

GPT-4 的三大优势：
1. 预训练数据规模远超 Mistral/DeepSeek（量级差距）
2. 模型参数规模更大（scaling law）
3. 使用了 RLHF 对齐——这也是 quality-scoring 被提出的动机之一（模仿 RLHF 的偏好学习）

追赶路线：
1. 扩展数据多样性和覆盖率（含人工检查高质量样本）
2. 引入功能正确性验证（automated testbench generation + assertion-based verification）
3. 用 LLM 自动生成 SVA 断言 + Jasper 等工具做形式验证
4. 用功能检查升级 scoring-based 训练（从语法质量到功能质量）

---

## 8. EDA 缩写表

| 缩写 | 全称 | 一句话解释 |
|------|------|-----------|
| **RTL** | Register Transfer Level | 寄存器传输级，数字设计抽象层：只描述寄存器间数据流动。对应流程 ① |
| **LLM** | Large Language Model | 大语言模型，本文基座为 Mistral-7B-v0.1 / DeepSeek-Coder-6.7B |
| **MLE** | Maximum Likelihood Estimation | 最大似然估计，标准 SFT 损失：最大化 reference token 的对数似然 |
| **Exposure Bias** | 曝光偏差 | 训练时模型见 reference token，推理时见自己生成的 token，分布不匹配导致错误累积 |
| **Beam Search** | 束搜索 | 维护 top-k 最高概率子序列。本文用 beam=5 生成评分候选 |
| **Rouge-L** | Recall-Oriented Understudy for Gisting Evaluation - LCS | 基于最长公共子序列的相似度。本文三重用途：指令去重（>0.7）、候选评分、训练/测试污染检查（>0.5） |
| **Pyverilog** | — | Python 版 Verilog HDL 处理工具包。本文用作**语法检查器** |
| **VCS** | Verilog Compiled Simulator | Synopsys 商业仿真器。RTLLM Syn-VCS：语法+接口兼容性；Functionality：testbench 仿真 |
| **DC / Design Compiler** | — | Synopsys 商业综合工具。RTLLM Syn-DC：**物理可综合性**检查（比 Syn-VCS 更严） |
| **DS / DeepSpeed** | — | 微软分布式训练库。Stage-2 实现优化器状态 + 梯度分片 |
| **GPTQ** | GPT Quantization | 训练后量化方法。把 FP16 权重压缩到 INT4，本文产出 4GB 模型 |
| **GGUF** | GPT-Generated Unified Format | llama.cpp 模型文件格式。本地推理用的 Q4_0 即 4-bit 量化 |
| **CR / CR:POS** | Compression Ratio / Part-of-Speech CR | 文本多样性指标。构建全集文件 → gzip 压缩 → 原始/压缩比。低值 = 高多样性 |
| **FSM** | Finite State Machine | 有限状态机，时序电路的常见型态。约 15% 的训练数据涉及 FSM |
| **SVA** | SystemVerilog Assertions | 硬件断言语言。论文未来方向：用 LLM 自动生成 SVA + 形式工具检查功能正确性 |
| **RLHF** | Reinforcement Learning from Human Feedback | GPT-4 使用的对齐技术。Quality-scoring 是其轻量近似：用自动评分代替人类偏好 |
| **Syn-VCS** | Syntax by VCS | RTLLM 指标：VCS 编译通过（语法 + 接口与 testbench 匹配） |
| **Syn-DC** | Syntax by Design Compiler | RTLLM 指标：DC 综合通过（物理可综合，比 Syn-VCS 更严格） |
| **DPO** | Direct Preference Optimization | 直接偏好优化——一种不需要显式 reward model 的偏好学习方法 |
| **EDA** | Electronic Design Automation | 电子设计自动化，芯片设计工具链总称 |
| **HDL** | Hardware Description Language | 硬件描述语言。本文特指 Verilog |
| **VLSI** | Very Large Scale Integration | 超大规模集成电路 |

---

## 9. 与芯片流程的关系

### 9.1 全流程定位

```text
  架构/微架构规格（人写）
       │
       ▼
┌─────────────────────────────────┐
│  ① RTL 设计  ←── RTLCoder       │
│     (自然语言 → Verilog)         │
│     训练目标: 语法正确 + 偏好高分 │
└────────────┬────────────────────┘
             │  ⚠️ 交接面
             ▼
   ② RTL 功能仿真  ← 评测才跑
             ▼
   ③ 逻辑综合  ← RTLLM 评测中 Syn-DC 检查可综合性
             │    但训练完全不知道综合是什么
             ▼
   ④ 门级仿真 → ⑤ STA → ⑥ 形式验证（TCAD Section V 未来方向）
             ▼
   ⑦-⑬ 后端流程 → ⑭-⑰
```

### 9.2 Syn-VCS vs Syn-DC 的实用含义（TCAD 版新增区分）

TCAD 版在 RTLLM benchmark 上区分了两个"语法"指标：

| 指标 | 检查什么 | 通过条件 |
|------|---------|---------|
| **Syn-VCS** | Verilog 语法 + 模块接口与 testbench 兼容 | VCS 编译通过 |
| **Syn-DC** | 物理可综合性（synthesizable） | Design Compiler 综合通过 |

Syn-DC 比 Syn-VCS 更严格——等于"代码不仅语法对，还能变成门电路"。Table IV 中 GPT-4 两项都是 100%，RTLCoder-Mistral 是 100% / 93.1%（有 2 题综合不过），GPT-3.5 是 93.1% / 89.7%。

**深层含义**：即使模型学会写出"语法对"的代码，它可能仍不知道"什么是可综合的"。训练数据中缺少综合失败的负样本——模型没见过"这种写法综合不过"的反馈。

### 9.3 「语法正确 + testbench 通过」和「能做成芯片」之间隔着什么

**在逻辑综合阶段被拦下的**：
- `initial` 块赋初值是 RTLCoder 训练数据中最常见的不可综合模式——GPT-3.5 生成参考代码时频繁使用（和软件初始化习惯一致），虽然大部分被语法检查过滤，但模型在预训练阶段已内化此模式
- latch 推断是第二常见陷阱——组合逻辑 `always @(*)` 中缺 else 分支，仿真碰巧符合预期（仿真器默认保持旧值），但综合器插入锁存器

**在门级仿真 + STA 被拦下的**：
- 阻塞赋值误用、跨时钟域无同步器、大位宽加法器的时序违例——代码"功能对"但质量差，RTLCoder 完全感知不到

### 9.4 TCAD 版的功能验证未来路线（Section V）

论文给出了一个具体路线：用 LLM 自动生成 SVA (SystemVerilog Assertions) + Cadence Jasper 等形式工具检查。这个方案的矛盾在于：断言本身是 LLM 生成的，正确性不保证，可能错误地过滤正确的训练样本。这个思路后来被同一团队的 AssertLLM 推进——"LLM 生成断言"这条路可行，但断言质量仍是开放问题。

---

## 10. 讨论与局限

### 10.1 论文自述的局限

训练评分的根本局限在 TCAD 版 Section II-D（"Imperfection in Data Functionality Correctness"）中正式讨论：

> "Functionality checking for the Verilog code is practically hardware verification, which has been studied for decades, relies on human engineers, and is difficult to get guaranteed results."

论文的策略不是解决这个问题，而是**接受它**——"this imperfect automated checking can already filter out the most serious mistakes in the dataset."

**技术评估**：在数据量足够大、噪音率不太高时，语法过滤 + 统计学习确实能提取出大部分"正确模式"。但这取决于"噪音率不太高"这个假设——如果某类电路的数据有 90% 是功能错语法对的，模型学到的是"怎样写出看起来对但功能错的代码"。论文未对此做量化分析。

### 10.2 4-bit 量化的性能代价与收益（TCAD 版新增）

| 模型 | EvalMachine Pass@1 | EvalHuman Pass@1 | 模型大小 |
|------|---:|---:|---:|
| RTLCoder-DeepSeek (FP16) | 61.2% | 41.6% | ~13GB |
| RTLCoder-DeepSeek-4bit (INT4) | 59.6% | 38.1% | ~4GB |
| 损失 | -1.6pp | -3.5pp | -70% |

EvalHuman 退化（-3.5pp）明显大于 EvalMachine（-1.6pp）。一种可能解释：EvalHuman 的描述更抽象，需要更多推理能力——这正是量化最容易损伤的（注意力权重的精密度下降影响长距离依赖）。

**工程价值**：4GB 模型意味着可在无 GPU 的笔记本上运行，适合企业内网的隐私敏感场景——"design privacy concerns are addressed"是论文反复强调的价值点。

### 10.3 灾难性遗忘的基座模型差异（TCAD Table VI）

已在 6.3 节详述。核心发现：**DeepSeek-Coder 因预训练已是代码专用模型，Verilog fine-tune 后几乎没有灾难性遗忘**，而 Mistral 作为通用模型在 Cpp 和 Shell 上有 8-10 个百分点的退化。

### 10.4 Beam Search 为何反而不如 Sampling（TCAD Table V）

已在 6.3 节详述。核心发现：Verilog 代码生成中，beam search 维护的"高概率序列"未必对应"语义正确的代码"，sampling 的随机性反而能跳出局部最优。这和 MAGE 的高温采样发现（$T=0.85$ 优于 $T=0$）在精神上一致。

### 10.5 候选数的边际效应

TCAD 版仍未实验 $K > 3$。直觉上：$K=1$ 时 compare loss = 0（没有比较对），退化为纯 MLE；$K$ 增大到一定程度后新增候选和已有候选在 beam search 似然空间中的差距越来越小，compare loss 的信息增量递减。这是一个明显的消融缺口。

### 10.6 数据管线的可复现性风险

数据生成完全依赖 GPT-3.5 的特定版本行为（temperature、prompt、模型版本）。GPT-3.5 版本更新会导致生成数据分布漂移。论文提到"GPT-3.5 is only used for dataset generation"，但这个版本的 GPT-3.5 在 2025 年后可能已不再可用或行为已变。这倒逼研究者要么用开源 teacher 重建数据管线，要么直接用论文公开的 27K 数据集——后者更可行，但失去了"用最新 teacher"的可能。

### 10.7 与 MAGE 和 ChipSeek 的三角对比

| 维度 | RTLCoder | MAGE | ChipSeek |
|------|----------|------|----------|
| 改进位置 | **训练时**（无推理时工具调用） | **推理时**（无训练） | **训练时**（含 EDA 工具） |
| 反馈信号 | 静态语法检查（Pyverilog） | 动态 testbench 仿真（Icarus） | EDA 全工具链 7 维 reward |
| 信号粒度 | 整条代码的语法正确/相似度 | 逐拍信号级 counterexample | 整条代码的组内 advantage |
| 优化目标 | 语法 + 偏好（功能间接） | 功能正确性 | 功能正确性 + PPA |
| 推理成本 | 1 次 forward | 20~50 次 LLM + 多次仿真 | 1 次 forward |
| 训练成本 | 4×4090 + 27K 数据生成 | 0 | 52 A100 GPU 小时 |
| 知识积累 | ✅（参数内化） | ❌（每题独立） | ✅（参数内化） |
| 开源 | 全开源（首个） | 全开源 | 全开源 |

RTLCoder 在这三者中的定位是**最便宜、最基础的基线**——训练信号最弱（语法而非功能/PPA），但部署成本最低、最易复现。

### 10.8 开放问题

1. **训练评分升级**：如果从 Pyverilog 升级到 Icarus 编译（不加 testbench，只做 `iverilog -t null`），能比单纯语法检查多过滤多少质量差的候选？这是成本最低的 scoring 升级。
2. **数据量的边际收益**：10K to 27K 带来了 +3~6pp。27K to 100K 是否还有显著收益？还是已触达 7B 模型的容量上限？
3. **Gradient Splitting 的组大小 $J$ 敏感性**：Algorithm 1 的 $J$ 直接影响"额外前向 pass 次数"和"显存峰值"的 trade-off。论文未给出 $J$ 的具体值和消融。
4. **Quality-scoring 与 DPO 的关系**：$\mathcal{L}_{\text{compare}}$ 和 DPO（Direct Preference Optimization）在数学结构上高度相似。区别在于：DPO 用 human/AI preference pairs，RTLCoder 用 syntax checker + Rouge-L 自动生成 preference。一个自然的扩展是用 testbench pass/fail 作为 preference 信号。
5. **功能验证升级**：TCAD 版提到的断言-based 路线——AssertLLM 已证明 LLM 生成 SVA 断言的可行性。如果把"断言的通过/失败"作为 quality score 的 ground truth，quality-scoring 就能从语法层面升级到功能层面。

---

## 11. 复现信息

| 项目 | 内容 |
|------|------|
| 论文页 | https://zhiyaoxie.com/files/TCAD25_RTLCoder.pdf · DOI: 10.1109/TCAD.2024.3483089 |
| 代码 | https://github.com/hkust-zhiyao/RTL-Coder · commit `b2847073` |
| 数据集 | RTLCoder-27K（`dataset/Resyn27k.json`）· 已开源；25K 条 JSONL 格式 |
| 模型权重 | HF: `ishorn5/RTLCoder-v1.1` (Mistral FP16), `ishorn5/RTLCoder-Deepseek-v1.1` (DeepSeek FP16), `ishorn5/RTLCoder-v1.1-gptq-4bit` (GPU 4-bit), `ishorn5/RTLCoder-v1.1-gguf-4bit` (CPU 4-bit) |
| 本地状态 | 已归档 + 已审计。GGUF 4-bit CPU 推理通过（half-adder, PASS 4/4 vectors） |
| 复现等级 | R3（完整复现：数据生成、训练、推理均可执行） |
| 主要门槛 | 训练需 4 张 RTX 4090（24GB）· 数据生成依赖 GPT-3.5 API · 仓库无 LICENSE |

---

## 12. 一分钟复述版

RTLCoder（HKUST，TCAD 2025）是第一个全开源、7B 参数、性能超过 GPT-3.5 的 Verilog RTL 生成模型。核心方法论是"数据 + 微调"，不涉及任何推理时工具调用或 RL。

核心四招：
1. **三阶段数据管线**：树状层次 prompt 生成 350 个 RTL 关键词 → 指令生成（few-shot + 源码反向 + 变异增强）→ GPT-3.5 生成参考代码 + 语法过滤 → 27K 条开源数据集。TCAD 版新增完整 prompt 示例 + CR/CR:POS 多样性量化（与 Magicoder Python 数据集相当）。
2. **Quality-Scoring 训练**：每条规格生成 K=3 个候选 → Pyverilog 语法检查 + Rouge-L 评分 → $\mathcal{L}_{\text{total}} = \mathcal{L}_{\text{MLE}} + \mathcal{L}_{\text{compare}}$（pairwise margin loss）。数据贡献 +22pp，质量偏好额外 +3~4pp。
3. **Gradient Splitting**：TCAD 版 Algorithm 1 给出完整伪代码——链式法则拆分 $\partial L/\partial w = \sum_k \partial L/\partial s_k \cdot \partial s_k/\partial w$，两次 forward+VJP 替代单次全图反向，显存 $O(K) \to O(1)$。4 张 RTX 4090 可训练 7B。
4. **4-bit 量化**：GPTQ 压缩到 4GB，EvalMachine 仅 -1.6pp，可在笔记本 CPU 上运行。

结果：EvalMachine Pass@1 62.5%（超 GPT-4），EvalHuman 41.6%，RTLLM Func Pass@5 48.3%。TCAD 版新增逐题热力图、beam search 消融（不如 sampling）、跨语言灾难性遗忘分析（DeepSeek 几乎无退化）。

**边界**：训练评分只有语法没有功能、不覆盖综合/PPA/多模块/形式验证、benchmark 污染风险、GPT-3.5 数据管线可复现性风险。

---

## 13. 与 arXiv 版的差异

TCAD 2025 期刊版相较于 arXiv / LAD 2024 会议版（5 页 to 14 页）的增量主要体现在以下七个方面：

### 13.1 数据管线可视化与多样性量化（TCAD 新增）

- **新增 8 张 Figures（Figure 2-9）**：完整展示 $P_{key}$、$P_{ext}^{key}$、$P_{ext}^{code}$、$P_{smut}$、$P_{cmut}$ 的 prompt 文本和 GPT-3.5 响应示例。arXiv 版只有 Figure 1 流程图，没有具体的 prompt 内容。
- **新增数据分布分析（Figure 10）**：关键词类别饼图（10a）、训练数据电路类型分布（10b），并与 RTLLM-1.1（10c）和 VerilogEval（10d）对比，验证覆盖度。
- **新增 Token 分布分析（Figure 12a）**：instruction 平均 78 tokens，code 平均 345 tokens，证明 context length=2048 的合理性。
- **新增多样性量化（Table II）**：引入 CR 和 CR:POS 指标，首次用 gzip 压缩比量化 RTLCoder-27K 的文本多样性，并与 Magicoder（Python 数据集）、MG-Verilog、Goh et al. 对比。结论：RTLCoder-27K 多样性与广泛使用的 Python 数据集 Magicoder 相当（CR=3.57 vs 3.40），显著优于同期 Verilog 数据集。

### 13.2 训练公式的形式化（TCAD 新增）

- arXiv 版对 quality-scoring 只有一段文字描述。
- TCAD 版给出 $p_{i,k}$、$s_{i,k}$、$\mathcal{L}_{\text{compare}}$ 的完整编号公式定义（Section III-B），以及 Figure 11 的两阶段训练可视化对比。
- 新增 exposure bias 在 RTL 生成中的具体表现分析——"废话重复"（duplication）现象的解释。

### 13.3 Gradient Splitting 完整伪代码（TCAD 新增）

- arXiv 版只有一句话："we decompose the computation graph calculation and use the gradient accumulation-alike method to reduce the space complexity from O(K) to O(1)."
- TCAD 版新增：
  - **Algorithm 1**：11 行完整伪代码（grp, forward, compute loss, backward temp, second forward + VJP）
  - 链式法则形式化推导：$\partial L/\partial w = \sum_k \partial L/\partial s_{i,k} \cdot \partial s_{i,k}/\partial w$
  - "Without the proposed gradient-splitting method, the training is impossible." 声明

### 13.4 4-bit 量化部署与评测（TCAD 新增）

- arXiv 版完全不涉及量化。
- TCAD 版新增：
  - GPTQ 量化方法介绍
  - RTLCoder-DeepSeek-4bit 的完整 benchmark 成绩（Table III）
  - 量化损失分析：EvalMachine -1.6pp，EvalHuman -3.5pp
  - 4GB 模型可纯 CPU 推理的工程定位

### 13.5 细粒度评测（TCAD 新增）

- **Table IV**：RTLLM V1.1 逐题详细结果——RTLCoder-Mistral vs GPT-3.5/GPT-4 在 29 个设计上的 Syn-VCS、Syn-DC、Functionality 逐题对比。新增 Syn-VCS vs Syn-DC 的细粒度区分。
- **Figure 14**：VerilogEval 逐题热力图——143/156 题每题 20 次采样的通过/失败可视化。
- **Table V**：Sampling vs Beam Search (beam=5) 解码消融。发现 beam search 在所有模型上均不如 sampling，并给出机制解释。
- **Table VI**：Verilog 训练对通用代码能力的影响分析（Python HumanEval+、Cpp、Shell）。发现 DeepSeek-Coder 几乎无灾难性遗忘，Mistral 有明显退化。

### 13.6 新增 baselines 与更完整的对比（TCAD 新增）

TCAD 版 Table III 中新增了：
- Goh et al. 的开源 Verilog 数据集 baseline
- MG-Verilog 多粒度描述集 baseline
- RTLCoder-4bit 量化模型

arXiv 版 Table II 未包含这些对比项。

### 13.7 GPT-4 优势的结构化分析与未来路线图（TCAD 新增 Section V）

- 新增"为何 GPT-4 更强"的三维度分析：预训练数据规模、模型参数规模、RLHF 对齐
- 新增开源模型追赶路线图：扩展数据覆盖率 → 功能验证自动化 → LLM 生成 SVA + Jasper → 功能检查升级 scoring
- 新增对数据污染、模型泛化、功能正确性标签的深入讨论

### 13.8 不变的部分

以下内容两版完全一致：
- 三阶段数据生成流程的核心逻辑
- RTLCoder-27K 数据集本身（同一份数据）
- 训练超参（Adam lr=1e-5, batch=256, context=2048, 4x4090+DS2）
- 核心实验结果（同一组数字）
- 代码仓库、模型权重
- Quality-scoring 的 pairwise margin loss 设计思路

---

> 对照阅读：[论文深度讲解_RTLCoder-arXiv.md](./论文深度讲解_RTLCoder-arXiv.md) · [MAGE/论文深度讲解.md](../MAGE/论文深度讲解.md) · [ChipSeek/论文深度讲解.md](../ChipSeek/论文深度讲解.md)
