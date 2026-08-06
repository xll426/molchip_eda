# RTLCoder (arXiv / LAD 2024) 论文深度讲解

> **RTLCoder: Outperforming GPT-3.5 in Design RTL Generation with Our Open-Source Dataset and Lightweight Solution**
> Shang Liu, Wenji Fang, Yao Lu, Qijun Zhang, Hongce Zhang, Zhiyao Xie
> 香港科技大学（HKUST）及广州校区
> IEEE LAD 2024 · arXiv: 2312.08617v5 · 原文：[2312.08617_RTLCoder.pdf](./2312.08617_RTLCoder.pdf)
> 代码：https://github.com/hkust-zhiyao/RTL-Coder
> 模型：https://huggingface.co/ishorn5

> 本文是 5 页 LAD 2024 Workshop 会议版的完整讲解。更完整的 14 页 TCAD 2025 期刊扩展版（含 4-bit 量化、完整 prompt 示例、Gradient Splitting 伪代码、逐题热力图）见 [论文深度讲解_RTLCoder-TCAD2025.md](./论文深度讲解_RTLCoder-TCAD2025.md)。两版共享同一套代码、数据和权重。

---

## 1. 一句话定位

**RTLCoder 不改进模型架构，它用 GPT-3.5 蒸馏出 27,000 条 Verilog 指令-代码训练对，再让 7B 开源模型在多候选之间学会偏好高分代码——仅用 4 张 RTX 4090 训练，就在 VerilogEval Machine 上以 62.5% pass@1 超过 GPT-4（60.0%），且数据集、训练代码、两个基座的微调权重全部开源。**

这句话里有四个技术承重点：

1. **GPT-3.5 蒸馏数据** -- 不是从网上爬，而是用 teacher model 生成 (instruction, code) 对，经语法检查过滤出高质量子集。本质是把 teacher 的知识蒸馏进一个更小、更可控的模型。
2. **多候选质量偏好训练** -- 每条 instruction 生成 K=3 个候选答案，外部 checker（Pyverilog 语法检查 + Rouge-L 相似度）打分，模型通过 pairwise margin loss 学会给高分候选更高的生成概率。这解决的是 MLE（Maximum Likelihood Estimation，最大似然估计）训练的 exposure bias。
3. **Gradient Splitting 显存优化** -- 把多候选训练的激活内存从 $O(K)$ 降到 $O(1)$，使 7B 模型的全参数微调仅需 4 张消费级 RTX 4090（24GB），不需要 A100 集群。
4. **全开源** -- 数据集 RTLCoder-27K + 训练脚本 + 推理脚本 + Mistral/DeepSeek 两个基座的微调权重全部公开。在它之前，唯一接近 GPT-3.5 的开源 RTL 模型是 NVIDIA 的 VerilogEval，但数据集和模型均未公开。

---

## 2. EDA 阶段映射（①-⑰）

参照 [芯片流程.md](../芯片流程.md) 的 17 阶段标准编号：

| 阶段 | 覆盖 | 说明 |
|------|:---:|------|
| **① RTL 设计** | ✅ **核心** | 自然语言设计规格 → 7B causal LM 自回归生成完整 Verilog module。这是 RTLCoder 唯一主动介入的阶段 |
| ② RTL 功能仿真 | ⚠️ **评测用** | 训练时不跑仿真（只用 Pyverilog 语法检查）；benchmark 评测时用 Icarus/VCS + testbench 验证功能正确性 |
| ③ 逻辑综合 | ⚠️ **间接** | RTLLM benchmark 用 Synopsys VCS 和 Design Compiler 检查语法与可综合性。**训练目标不含任何综合/PPA 信息** |
| ④ 门级仿真 | ❌ | 无 SDF（Standard Delay Format，标准延时格式）反标，不检查毛刺、建立/保持违例、X 传播 |
| ⑤ STA（Static Timing Analysis，静态时序分析） | ❌ | 不计算路径延迟 |
| ⑥ 形式验证 | ❌ | 不做等价性证明 |
| ⑦ 布局规划 Floorplan | ❌ | — |
| ⑧ 标准单元摆放 Placement | ❌ | — |
| ⑨ CTS（Clock Tree Synthesis，时钟树综合） | ❌ | — |
| ⑩ 布线 Routing | ❌ | — |
| ⑪ 后仿真 | ❌ | 无 SPEF（Standard Parasitic Exchange Format，标准寄生参数交换格式） |
| ⑫ DRC（Design Rule Check，设计规则检查）/ LVS（Layout Versus Schematic，版图与原理图一致性检查） | ❌ | — |
| ⑬ 签核 Signoff | ❌ | — |
| ⑭-⑰ 流片→制造→封装测试→芯片 | ❌ | — |

**覆盖率：1/17（若评测用的功能仿真算半个，则为 1.5/17）。** RTLCoder 是一个纯 RTL 设计辅助工具。它的训练目标只有一个：让模型在给定自然语言规格时，生成语法正确且功能尽可能正确的 Verilog 代码。

> ⚠️ RTLCoder 和 MAGE、ChipSeek 的根本区别：MAGE 把仿真反馈用在推理时迭代修复（推理时工具调用），ChipSeek 把 EDA 反馈做成 RL reward 更新参数（训练时工具调用）。RTLCoder 的训练信号来自**静态语法检查器**（Pyverilog），比 MAGE 的仿真反馈更粗糙，比 ChipSeek 的 PPA reward 更基础。它的定位是"数据+微调"路线的最简基线——没有推理时工具调用，没有 RL。

---

## 3. 输入 / 输出

### 3.1 训练输入

**(a) 数据生成阶段的关键词 prompt 示例**

论文用树状层次 prompt 让 GPT-3.5 输出 RTL 设计关键词，最终获得约 350 个关键词，覆盖组合逻辑、时序逻辑、FSM、算术单元、存储、接口等类别。

```text
[Prompt P_key 示意]
Provide categories and examples of frequently used block keywords
in RTL design. Output in a tree structure with subfields.
```

**(b) 训练数据条目（JSONL 格式，来自 Resyn-27K）**

```json
{"Instruction": "Please act as a professional verilog designer. Design a 1-bit half adder with inputs a, b and outputs sum, carry.",
 "Response": ["module half_adder(input a, input b, output sum, output carry); assign sum = a ^ b; assign carry = a & b; endmodule"]}
```

训练时拼接方式：`source = Instruction + "\n"`，`target = Response[-1] + eos_token`。loss 只监督 target token（Response 部分），source token（Instruction 部分）全部设为 ignore index。

**(c) Quality-Scoring 训练数据**

```json
{"Instruction": "Generate a 2-input AND gate.",
 "Input": "module and2(input a, input b, output y);",
 "Response": ["assign y = a & b; endmodule", "assign y = a | b; endmodule"],
 "Score": [1.0, 0.0]}
```

评分规则：参考代码（来自 GPT-3.5 且通过语法检查的）得满分 1；模型生成的候选若通过 Pyverilog 语法检查也得 1；未通过的用 Rouge-L 与参考代码的相似度作为分数。**注意：评分完全不涉及功能正确性**——论文承认 "currently generating testbenches for functionality verification cannot be automated"。

### 3.2 推理输入

```text
Please act as a professional verilog designer and provide a half adder.
Only output the complete Verilog module.
module half_adder(
    input a,
    input b,
    output sum,
    output carry
);
```

### 3.3 推理输出

```verilog
module half_adder(
    input a,
    input b,
    output sum,
    output carry
);
    assign sum = a ^ b;
    assign carry = a & b;
endmodule
```

本地实测（RTLCoder-v1.1 GGUF 4-bit，纯 CPU 推理，4 线程）：Icarus 编译通过，testbench PASS 4/4 vectors。单条约 41 秒，API 成本 0。

---

## 4. 方法与架构

### 4.1 数据生成流水线（三阶段，对应论文 Figure 1）

```text
┌─────────────────────────────────────────────────────────────────────────┐
│ Stage 1: 领域关键词准备                                                  │
│ ─────────────────────────────────────────────────────────────────────── │
│  树状层次 Prompt P_key → GPT-3.5 → 关键词池 L_key (~350 个)             │
│  例：Combinational → adder → carry-lookahead adder, ripple-carry adder  │
├─────────────────────────────────────────────────────────────────────────┤
│ Stage 2: 指令生成                                                        │
│ ─────────────────────────────────────────────────────────────────────── │
│  ② 关键词 → P_ext^key → GPT-3.5 → 设计指令                              │
│  ③ 现有源码 → P_ext^code → GPT-3.5 → 设计指令（反向生成）               │
│       │                                                                  │
│       ▼                                                                  │
│  初始指令池 L_ins ──▶ ④ 变异增强 (P_mut) ──▶ ⑤ 指令检查 ──▶ 新指令     │
│    单电路变异 (P_smut): 同硬件类型不同功能 / 同功能不同硬件实现          │
│    电路组合 (P_cmut): 并行组合 / 串行组合                                │
│    过滤规则: invalid-word (非RTL内容) + Rouge-L 相似度 < 0.7            │
│       │                                                                  │
│       ▼                                                                  │
│  最终指令池 L_ins: >50,000 条                                            │
├─────────────────────────────────────────────────────────────────────────┤
│ Stage 3: 参考代码生成                                                    │
│ ─────────────────────────────────────────────────────────────────────── │
│  ⑥ 每条指令 → GPT-3.5 生成 ≥5 个候选代码                                │
│  ⑦ Pyverilog 语法检查 → 至少一个通过才保留该指令                        │
│        全部 5 个失败 → 丢弃该指令                                        │
│       │                                                                  │
│       ▼                                                                  │
│  RTLCoder-27K: >27,000 条 (Instruction, Response) 对                    │
└─────────────────────────────────────────────────────────────────────────┘
```

### 4.2 训练流程（MLE + Quality-Scoring）

```text
┌─────────────────────────────────────────────────────────────────────────┐
│ Step 1: 普通 MLE 训练（Direct Training）                                 │
│ ─────────────────────────────────────────────────────────────────────── │
│  RTLCoder-27K → Mistral-7B / DeepSeek-Coder-6.7B 全参数 SFT            │
│  loss_mle = -Σ_t log P(y_t | x, y_<t)                                   │
│  配置: Adam lr=1e-5, β1=0.9, β2=0.999, no weight decay                 │
│        context=2048, global batch=256, 4×RTX 4090 (24GB), DS Stage-2   │
│       │                                                                  │
│       ▼                                                                  │
│  产物: RTLCoder-Mistral-Direct / RTLCoder-DeepSeek-Direct               │
│  性能: EvalMachine Pass@1 58.9%/59.8%，已接近甚至超过 GPT-3.5          │
├─────────────────────────────────────────────────────────────────────────┤
│ Step 2: Quality-Scoring 训练                                            │
│ ─────────────────────────────────────────────────────────────────────── │
│  对每条 instruction x_i:                                                 │
│    ① 用 Direct 模型 Beam search 生成 K=3 个候选 {y_i,k}                 │
│    ② 候选 + 参考代码 → Pyverilog 语法检查 + Rouge-L 评分 → {z_i,k}     │
│    ③ 计算 loss = loss_mle + loss_compare                                │
│       loss_compare = Σ_{z_k<z_τ} max(s_k - s_τ + λ, 0)                 │
│       s_k = softmax(p_k), p_k 是长度归一化的对数概率                    │
│       │                                                                  │
│       ▼                                                                  │
│  产物: RTLCoder-Mistral / RTLCoder-DeepSeek                             │
│  性能: EvalMachine Pass@1 62.5%/61.2%，超过 GPT-4 (60.0%)              │
└─────────────────────────────────────────────────────────────────────────┘
```

### 4.3 Gradient Splitting 原理

arXiv 版正文对 Gradient Splitting 的描述只有一句："we decompose the computation graph calculation and use the gradient accumulation-alike method to reduce the space complexity from O(K) to O(1)."

原理是链式法则拆分：

$$
\frac{\partial L}{\partial w} = \sum_{k} \frac{\partial L}{\partial s_k} \cdot \frac{\partial s_k}{\partial w}
$$

不把 K 个候选同时放进计算图，而是分组前向收集 $s_k$，在 $s$ 向量上算 $L$ 和 $\partial L/\partial s_k$，再逐组重算前向 + vector-Jacobian product 累积梯度。这是**时间换空间**：多了前向计算次数，但激活内存不随 K 增长。完整 Algorithm 1 伪代码见 TCAD 2025 版。

### 4.4 模块职责矩阵

| 阶段 | 谁做 | 用什么工具 | 关键点 |
|------|------|-----------|--------|
| 关键词生成 | GPT-3.5 | 树状层次 prompt | 覆盖 RTL 领域的广度 |
| 指令生成 | GPT-3.5 | few-shot prompt | 描述既要明确又不能像代码翻译 |
| 指令变异 | GPT-3.5 | P_smut / P_cmut | 规模+复杂度的自动化扩张 |
| 指令过滤 | 规则脚本 | invalid-word + Rouge-L | 自动化，不完美但够用 |
| 参考代码生成 | GPT-3.5 | — | 每条指令 ≥5 个答案，语法筛 |
| MLE 训练 | 7B 基座模型 | 4×RTX 4090 + DS Stage-2 | 从 36.9% → 58.9% 的飞跃 |
| 候选评分 | Pyverilog + Rouge-L | 语法检查 + 相似度 | **不是功能验证，只是语法+表面相似** |
| Quality-scoring 训练 | 7B 基座 | Gradient Splitting | +3.6 个百分点的增量 |
| 推理评测 | 微调后模型 | Icarus/VCS + testbench | pass@1 / pass@5 / pass@10 |

---

## 5. 关键公式

### 5.1 MLE 损失

$$
\mathcal{L}_{\text{MLE}} = -\sum_{t=1}^{T} \log P_{\pi}\!\left(y_i^t \mid x_i,\ y_i^{<t}\right)
$$

- $\pi$：模型参数（Mistral-7B 或 DeepSeek-Coder-6.7B）
- $x_i$：第 $i$ 条自然语言指令
- $y_i^t$：第 $i$ 条参考代码的第 $t$ 个 token
- $y_i^{<t}$：第 $i$ 条参考代码的前 $t-1$ 个 token

**工程直觉**：标准的 causal LM 训练——给前缀，预测下一个 token，交叉熵最小化。loss 只计算 response 部分，instruction 部分的 token 设为 ignore index。

**问题**：训练时模型看到的是 reference token，但推理时看到的是自己生成的 token。reference token 永远正确，自己生成的 token 可能有错——错一步，后面全偏。这就是 **exposure bias**。

### 5.2 长度归一化的对数概率

$$
p_{i,k} = \frac{\sum_{t} \log P_{\pi}\!\left(y_{i,k}^t \mid x_i,\ y_{i,k}^{<t}\right)}{|y_{i,k}|}
$$

- $p_{i,k}$：模型对第 $i$ 条指令的第 $k$ 个候选代码的长度归一化对数概率
- $y_{i,k}$：第 $k$ 个候选代码
- $|y_{i,k}|$：候选代码的 token 数

**为什么归一化**：不同候选的代码长度差异显著（20 token 的 assign 语句 vs 200 token 的 FSM）。不除以长度，长序列自然有更高的总 log 概率（累加了更多项），模型会偏袒长代码。

### 5.3 Softmax 归一化的选择概率

$$
s_{i,k} = \frac{\exp(p_{i,k})}{\sum_{\tau=1}^{K} \exp(p_{i,\tau})}
$$

- $s_{i,k}$：模型"选择"第 $k$ 个候选的概率（softmax 归一化后）
- $K$：每个 instruction 的候选数量（论文设 $K=3$）

**工程直觉**：$s_{i,k}$ 反映的是给定 instruction 下，模型自回归生成时"自然倾向于输出哪个候选"。softmax 把 $p_{i,k}$ 转成 $\sum_k s_{i,k} = 1$ 的概率分布，便于跨候选比较。

### 5.4 比较损失

$$
\mathcal{L}_{\text{compare}} = \sum_{z_{i,k} < z_{i,\tau}} \max\!\left(s_{i,k} - s_{i,\tau} + \lambda,\ 0\right)
$$

- $z_{i,k}$：第 $k$ 个候选的外部质量分数（来自 Pyverilog + Rouge-L）
- $\lambda$：margin 阈值——要求好候选的 $s$ 值比差候选至少高 $\lambda$
- 求和遍历所有 $z_{i,k} < z_{i,\tau}$ 的候选对：（质量差, 质量好）

**机制直观**：如果模型给一个低分候选分配了比高分候选更高的选择概率，loss 就惩罚它。惩罚量 = $s_{\text{差}} - s_{\text{好}} + \lambda$。

举例：`s_bad = 0.6, s_good = 0.4`，但 `z_bad < z_good`（bad 的评分低）。则 $\mathcal{L}_{\text{compare}} = \max(0.6 - 0.4 + \lambda, 0) > 0$，梯度会推往 $s_{\text{bad}} \downarrow, s_{\text{good}} \uparrow$。

**为什么用 pairwise margin loss 而非 listwise 排序损失**：pairwise 实现简单，且对分数精度要求低——只要知道谁比谁好，不需要准确的分数差距。这正好匹配 Pyverilog 那种"过了给 1，没过算相似度"的粗粒度评分。

### 5.5 总损失

$$
\mathcal{L}_{\text{total}} = \mathcal{L}_{\text{MLE}} + \mathcal{L}_{\text{compare}}
$$

两个分量的分工：$\mathcal{L}_{\text{MLE}}$ 让模型"学会写 Verilog"——知道语法、常见模式、spec 和 code 的对应关系。$\mathcal{L}_{\text{compare}}$ 让模型"学会分辨好坏"——在自己的多个候选之间判断哪个更好。两者权重 1:1。

**为什么 SFT 单独用 MLE 不够（论文的核心论点）**：MLE 假设 reference 是唯一正确答案，但同一个 spec 有大量正确写法。只学一个 reference 会过拟合到 teacher 的编码风格，且学不到"什么代码质量更高"的相对判断能力。

### 5.6 Pass@k 无偏估计

$$
\text{pass@}k = \mathbb{E}_{\text{Problems}} \left[ 1 - \frac{\binom{n - c_i}{k}}{\binom{n}{k}} \right]
$$

- $n$：每个题目的独立采样次数（论文设 $n=20$ 用于 VerilogEval）
- $c_i$：其中通过 testbench 的次数
- $k = 1, 5, 10$

当 $k=1$ 时化简为 $\mathbb{E}[c_i / n]$，即单次采样的期望通过率。

**这个公式在读数字时极其重要**：看到 "RTLCoder-Mistral pass@1 = 62.5%"，意思是"每题独立跑 20 次，平均有 62.5% 的采样通过"。这是对期望的无偏估计，不是"跑一次有 62.5% 概率通过"。

> 对比 MAGE 和 ChipSeek：RTLCoder 的 pass@1 和 vanilla LLM 的 pass@1 在**成本上完全可比**（都是一次前向生成）。这不同于 MAGE 的 pass@1 背后对应 20~50 次 LLM 调用 + 多次仿真。就评测公平性而言，RTLCoder 的数字比 MAGE 的数字"更诚实"。

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
- 基座模型：Mistral-7B-v0.1 或 DeepSeek-Coder-6.7B-Instruct
- 优化器：Adam，$\beta_1=0.9$，$\beta_2=0.999$，$\text{lr}=1 \times 10^{-5}$，无 weight decay
- context length = 2048，global batch size = 256
- 硬件：4 张 RTX 4090（24GB），FP16，DeepSpeed Stage-2

如果只使用作者已发布的权重，则不需要训练。

### 6.2 实验设置

**Benchmark**：
- VerilogEval (Machine 143 题 / Human 156 题)，使用 pass@k 指标（k=1,5,10）
- RTLLM V1.1（29 题），使用 pass@5 指标，分开报告 Syn-VCS 和 Functionality
- 生成参数：top_p=0.95, temperature ∈ {0.2, 0.5, 0.8}，对每个模型报告三种温度中的最佳成绩

**Baseline**：GPT-3.5、GPT-4（闭源）；VerilogEval [NVIDIA]、ChipNeMo、BetterV（闭源）；Codegen2-16B、StarCoder-15B、Thakur et al. 16B、Mistral-7B base（开源）

**消融设计**：
- Direct 训练 vs 完整 RTLCoder（验证 quality-scoring 贡献）
- 10K 子集 vs 27K 全量（验证数据规模效应）

**训练集与测试集去重**：用 Rouge-L 度量相似度，Rouge-L > 0.5 的训练样本被过滤，共计约 100 条。此外生成过程中用了 invalid-word 过滤和 Rouge-L > 0.7 的指令去重。

### 6.3 关键实验结果

| 模型 | EvalMachine Pass@1 | EvalMachine Pass@5 | EvalHuman Pass@1 | EvalHuman Pass@5 | RTLLM Func Pass@5 |
|------|---:|---:|---:|---:|---:|
| Mistral-7B base | 36.9% | 48.8% | 4.49% | 12.6% | 20.7% |
| DeepSeek-Coder-6.7B base | 54.1% | 63.8% | 30.2% | 42.2% | 34.5% |
| RTLCoder-Mistral-Direct | 58.9% | 70.0% | 34.4% | 42.3% | 41.4% |
| RTLCoder-DeepSeek-Direct | 59.8% | 73.6% | 39.1% | 48.3% | 44.8% |
| **RTLCoder-Mistral** | **62.5%** | **72.2%** | **36.7%** | **45.5%** | **48.3%** |
| **RTLCoder-DeepSeek** | **61.2%** | **76.5%** | **41.6%** | **50.1%** | **48.3%** |
| RTLCoder-Mistral-10k | 56.5% | 66.6% | 31.7% | 42.2% | 34.5% |
| RTLCoder-DeepSeek-10k | 55.3% | 70.4% | 36.7% | 47.0% | 37.9% |
| GPT-3.5 | 46.7% | 69.1% | 26.7% | 45.8% | 37.9% |
| GPT-4 | 60.0% | 70.6% | 43.5% | 55.8% | 65.5% |

读法：

1. **数据是主力**：从 base model 到 Direct training（纯 MLE，不加 compare loss），EvalMachine Pass@1 从 36.9%/54.1% 飞跃到 58.9%/59.8%，+22~25 个百分点。这已经是 RTLCoder-27K 数据集本身的价值——即使只做普通 SFT，就已经接近甚至超过 GPT-3.5。
2. **Quality-scoring 是锦上添花**：从 Direct 到完整 RTLCoder，额外 +2.7~3.6 个百分点。数据贡献是 quality-scoring 的 6~7 倍。
3. **10K vs 27K**：数据量从 10K 增加到 27K，所有指标均有提升，说明数据规模与多样性对性能至关重要。
4. **DeepSeek vs Mistral**：DeepSeek-Coder 作为基座在 EvalHuman 上强于 Mistral（预训练含更多代码数据），但推理速度慢于 Mistral（Mistral 使用 grouped-query attention + rolling buffer KV cache）。

---

## 7. 创新点

### 创新点 1：全自动三阶段合成数据管线 + 开源 27K 数据集

在 RTLCoder 之前，Verilog instruction-code 训练数据集极度稀缺。VerilogEval [NVIDIA] 的 8.5K 数据集未公开；Thakur et al. 的 25K 数据只有代码没有 instruction。RTLCoder 是**第一个全开源的大规模 instruction-code 对数据集**。

三阶段设计的核心洞察：关键词管 diversity，变异管 scale，语法检查管 quality。三者各司其职。

论文 Table I 列了所有同期工作的开源状态：只有 RTLCoder 同时在 "New Training Dataset"、"New LLM Model"、"Open-Source" 三列打勾。VerilogEval 有数据和模型但未公开；ChipNeMo 也未公开。

### 创新点 2：Quality-Scoring 训练

这是 RTLCoder 最核心的方法论贡献。逻辑链：

```text
MLE 训练有 exposure bias（训推 token 分布不匹配）
    ↓
模型在推理时会生成多个质量不一的候选
    ↓
应该让模型自己学会在这多个候选里分辨好坏
    ↓
引入外部评分 + pairwise margin loss → 模型内化了质量判断
```

Quality-scoring 的 pairwise margin loss 本质上是轻量级的偏好学习——用自动评分（语法检查 + 文本相似度）代替人类偏好标注，和 RLHF 的 reward model 训练有相似的结构但完全不需要人工。

### 创新点 3：Gradient Splitting 的显存优化

7B 模型全参数微调，4 张 24GB 消费级显卡就能跑，关键靠 Gradient Splitting。在它之前，多候选偏好训练（如 RLHF 的 reward model 训练）通常需要 A100 级别的 GPU 来同时保存 K 个候选的完整计算图（$O(K)$ 显存）。Gradient Splitting 通过链式法则拆分 + 两次前向 pass 将显存降到 $O(1)$，使消费级硬件可训练。

### 创新点 4：全开源——数据 + 训练 + 权重

这在 2024 年的 RTL 生成领域是首创。它直接促成了 RTLCoder 作为后续工作（OriGen、ChipSeek、MAGE）的 baseline 参照。

---

## 8. EDA 缩写表

| 缩写 | 全称 | 一句话解释 |
|------|------|-----------|
| **RTL** | Register Transfer Level | 寄存器传输级，数字设计抽象层：只描述寄存器间数据流动，不指定门电路 |
| **LLM** | Large Language Model | 大语言模型，本文基座为 Mistral-7B-v0.1 和 DeepSeek-Coder-6.7B |
| **HDL** | Hardware Description Language | 硬件描述语言，本文特指 Verilog |
| **VLSI** | Very Large Scale Integration | 超大规模集成电路 |
| **EDA** | Electronic Design Automation | 电子设计自动化，芯片设计工具链总称。本文仅用其仿真/综合工具做**评测** |
| **MLE** | Maximum Likelihood Estimation | 最大似然估计，标准 SFT 损失：最大化 reference token 的对数似然 |
| **SFT** | Supervised Fine-Tuning | 监督微调，本文与 MLE 同义（见论文脚注 2） |
| **Beam Search** | 束搜索 | 维护 top-k 最高概率子序列的解码方法 |
| **Rouge-L** | Recall-Oriented Understudy for Gisting Evaluation - LCS | 基于最长公共子序列的文本相似度。本文用途：指令去重（>0.7）、候选评分、训练/测试污染检查（>0.5） |
| **Pyverilog** | — | Python 版 Verilog HDL 处理工具包。本文用作**语法检查器** |
| **VCS** | Verilog Compiled Simulator | Synopsys 商业仿真器 |
| **DC** | Design Compiler | Synopsys 商业逻辑综合工具 |
| **DS** | DeepSpeed | 微软分布式训练库。Stage-2 实现优化器状态 + 梯度分片 |
| **FSM** | Finite State Machine | 有限状态机，时序电路的常见型态 |
| **GGUF** | GPT-Generated Unified Format | llama.cpp 模型文件格式，4-bit 量化版本用 Q4_0 |
| **Pass@k** | — | 代码生成标准指标：$n$ 次采样中至少 $k$ 次通过的期望比例 |

---

## 9. 与芯片流程的关系

### 9.1 在全流程中的位置

```text
  架构/微架构规格（人写）
       │
       ▼
┌─────────────────────────────────┐
│  ① RTL 设计  ←── RTLCoder 在这  │
│     (自然语言 → Verilog)         │
└────────────┬────────────────────┘
             │  ⚠️ 交接面：这里开始 RTLCoder 什么都不管
             ▼
   ② RTL 功能仿真  ← 评测时才跑 testbench
             ▼
   ③ 逻辑综合  ← 训练时完全不知道综合是什么
             ▼
   ④ 门级仿真 → ⑤ STA → ⑥ 形式验证
             ▼
   ⑦ Floorplan → ⑧ Placement → ⑨ CTS → ⑩ Routing
             ▼
   ⑪ 后仿真 → ⑫ DRC/LVS → ⑬ Signoff → ⑭-⑰
```

### 9.2 「语法正确 + testbench 通过」和「能做成芯片」之间隔着什么

**在阶段 ③ 逻辑综合被拦下的**：

- `initial` 块赋初值——仿真器认，ASIC 综合报错。GPT-3.5 生成参考代码时频繁使用 `initial` 块（和软件初始化习惯一致），虽然大部分被语法检查过滤，但模型预训练阶段已内化这个模式
- latch 推断——组合逻辑 `always @(*)` 中缺 `else` 分支，仿真行为碰巧符合预期（仿真器默认保持旧值），但综合器会插入锁存器
- 行为级 `for` 循环——仿真器能跑，综合器行为取决于工具

**在阶段 ④ 门级仿真被拦下的**：

- 时序逻辑用阻塞赋值（`=` 而非 `<=`）——RTL 仿真碰巧对（零延迟模型），门级仿真必错
- 跨时钟域无同步器——RTL 仿真必然通过，门级仿真暴露亚稳态导致的 hold violation

**在阶段 ⑤ STA 被拦下的**：RTLCoder 生成的 `assign sum = a + b;` 对 64 位加法——综合器默认给行波进位加法器（慢），STA 报 timing violation。但代码本身"功能对"——这种问题是**质量缺陷**，不是**正确性缺陷**。RTLCoder 完全不感知时序约束。

**结论**：RTLCoder 的 pass@1 指标测量的是"语法 + 功能仿真"，离"可综合 + 满足时序 + 面积合理"还有三道关卡。

---

## 10. 讨论与局限

### 10.1 论文自述的局限

论文承认训练数据的标签质量有限："currently generating testbenches for functionality verification cannot be automated"。训练评分（Pyverilog 语法检查 + Rouge-L 相似度）不能保证功能正确性——一个语法完美但逻辑完全错误的候选在 Pyverilog 下得满分 1，这个错误信号会通过 $\mathcal{L}_{\text{compare}}$ 反向传播到参数。

论文把语法检查的局限表述为可接受的折中："This imperfect automated checking can already filter out the most serious mistakes in the dataset."

### 10.2 代码/复现层面的问题

- 合成训练标签存在明显噪声，不能直接当 golden RTL
- prompt 对生成结果影响大——temperature、top-p、max tokens、截断规则的选择对 pass@k 有显著影响
- DeepSeek 版本可能在完成后继续生成，需要可靠的截断逻辑
- benchmark 题目（VerilogEval/RTLLM）完全公开，存在数据污染风险——论文用 Rouge-L > 0.5 过滤了约 100 条，但只能检测**文本表面相似**，检测不了功能等价但表述不同的题目
- 4-bit 量化版本适合推理，不适合直接继续做全参数微调
- 仓库依赖版本较旧，重建训练环境需要单独锁定 CUDA/PyTorch/Transformers 版本

### 10.3 本资料包的批判性分析

1. **训练评分是语法分，不是功能分**。这是 RTLCoder 最核心的局限。对比 MAGE（推理时跑真 testbench）、ChipSeek（训练时 RL reward 含 testbench pass/fail），RTLCoder 的方案在"训练信号质量"上是最弱的——代价是它也最省算力。

2. **基座模型的能力天花板**：RTLCoder 不创造新的 Verilog 生成能力，它**蒸馏并提纯** GPT-3.5 的能力。当基座模型在某类电路上完全不会写时，合成数据里也不会出现那种电路的正确代码，fine-tune 也就学不到。论文间接承认了这一点——结论指出提升方案是"扩展数据多样性、增加功能验证"。

3. **蒸馏优于 teacher 的机制**：RTLCoder 基于 GPT-3.5 的数据训练，结果超过了 GPT-3.5 本身。核心是语法检查过滤掉了 teacher 的"错误输出"，只保留"正确输出"做训练。本质是 **supervised knowledge distillation with quality filtering**——student 只学 teacher 的正确答案，不模仿它的错误分布。这解释了为什么 "Direct" 训练（纯 MLE）就已经接近甚至部分超过 GPT-3.5。

4. **候选数的边际效应**：论文只实验了 $K=3$ 个候选。直觉上：当 $K$ 增大，新候选和已有候选在模型似然空间里的差距越来越小（beam search 本身就是高概率路径搜索），compare loss 的信息增量递减。

5. **单模块假设**：和 MAGE 一样，评测全部是单文件、单模块任务。真实 RTL 设计的层次化结构（顶层例化子模块、参数化、跨模块接口协议）完全不在数据分布里。

---

## 11. 复现信息

| 项目 | 内容 |
|------|------|
| 论文页 | https://arxiv.org/abs/2312.08617 |
| 代码 | https://github.com/hkust-zhiyao/RTL-Coder · commit `b2847073` |
| 数据集 | RTLCoder-27K（`dataset/Resyn27k.json`）· 已开源 |
| 模型权重 | Hugging Face: `ishorn5/RTLCoder-v1.1`, `ishorn5/RTLCoder-Deepseek-v1.1`，含 GGUF 4-bit 版本 |
| 本地状态 | 已归档 + 已审计（GGUF 4-bit CPU 推理通过） |
| 复现等级 | R3（完整复现：数据 + 训练 + 推理均可执行） |
| 主要门槛 | 训练需 4×RTX 4090（24GB）· 数据生成依赖 GPT-3.5 API · 仓库无 LICENSE 文件 |

---

## 12. 一分钟复述版

RTLCoder（HKUST，LAD 2024 / TCAD 2025）是**用 GPT-3.5 蒸馏 27K 条 Verilog 训练数据 + quality-scoring 训练让 7B 本地模型超过 GPT-3.5** 的开源 RTL 生成方案。

核心三招：

1. **三阶段数据管线**：关键词（~350 个）→ 指令生成（few-shot + 源码反向 + 变异增强）+ 语法过滤 → 27K 条 (instruction, code) 对，全部开源。数据本身做 SFT 就能把 EvalMachine Pass@1 从 36.9% 拉到 58.9%。
2. **Quality-scoring 训练**：每条规格生成 K=3 个候选，Pyverilog 语法检查 + Rouge-L 评分，用 pairwise margin loss 让模型偏向高分候选。$\mathcal{L}_{\text{total}} = \mathcal{L}_{\text{MLE}} + \mathcal{L}_{\text{compare}}$。数据贡献 +22pp，quality-scoring 额外 +3~4pp。
3. **Gradient Splitting**：链式法则拆分 $\partial L/\partial w = \sum_k \partial L/\partial s_k \cdot \partial s_k/\partial w$，两组 forward + VJP 替代单次全图反向，显存 $O(K) \to O(1)$。4 张 RTX 4090 (24GB) 可训练 7B。

结果：EvalMachine Pass@1 62.5%（超过 GPT-4 的 60.0%），EvalHuman 41.6%，RTLLM Func Pass@5 48.3%。全开源——首个在 RTL 生成上超过 GPT-3.5 的开源方案。

**边界**：训练评分只有语法没有功能，不覆盖综合/PPA/多模块，benchmark 污染风险，单模块假设，5 页会议版是精简投稿。

---

> 对照阅读：[论文深度讲解_RTLCoder-TCAD2025.md](./论文深度讲解_RTLCoder-TCAD2025.md) · [MAGE/论文深度讲解.md](../MAGE/论文深度讲解.md) · [ChipSeek/论文深度讲解.md](../ChipSeek/论文深度讲解.md)
