# Circuit Foundation Model 综述 论文深度讲解

> **A Survey of Circuit Foundation Model: Foundation AI Models for VLSI Circuit Design and EDA**
> Wenji Fang†, Jing Wang†, Yao Lu, Shang Liu, Yuchao Wu, Yuzhe Ma, Zhiyao Xie*
> Hong Kong University of Science and Technology (HKUST) / HKUST(GZ)
> ACM Transactions on Design Automation of Electronic Systems (TODAES), 2026 · arXiv:2504.03711v2（2026年7月2日）
> 原文：[2504.03711v2.txt](./2504.03711v2.txt)
> 代码：未开源（综述论文）

---

## 1. 一句话定位

**这篇综述首次提出了 "Circuit Foundation Model (CFM)" 这一统一概念，将 AI4EDA 领域近年涌现的「预训练 + 微调」范式系统性地组织起来，覆盖 160+ 篇相关工作（90% 以上发表于 2022 年及以后），把所有 CFM 分为 Encoder-based（预测型，21 篇）和 Decoder-based（生成型，111+ 篇）两大技术路线，从电路数据的独特属性出发，分析了两种范式的输入模态、预训练策略、领域适配技术和下游任务，并提出了从泛化性/可扩展性、数据可用性、Encoder-Decoder 桥接到智能体化 CFM 的系统性挑战与未来路线图。**

这句话里的 5 个承重点，后面逐一拆解：

1. **CFM 概念与二分法** — 论文将 AI4EDA 技术划分为 Type I（传统任务特定监督学习）和 Type II（CFM = 预训练 + 微调），Type II 进一步分为 Encoder-based（图结构编码 + 预测下游任务）和 Decoder-based（LLM 生成能力 + 领域适配）。这是目前该领域最系统、覆盖面最广的分类框架。

2. **电路数据的独特属性** — 论文从数据视角系统阐述了电路区别于自然语言和图像的六大属性：跨阶段功能等价性、多模态表示格式、PPA+功能双重目标、硬件并行执行特性、数据稀缺性、电路可复用性。这些属性直接驱动了 CFM 的设计选择。

3. **Encoder 技术全景** — 覆盖 HLS/RTL/Netlist/Layout 四个阶段的 21 个 encoder，按预训练策略分为对比学习、掩码重建、监督预训练、多模态融合四类。以 DeepGate 系列为 netlist 阶段标杆，CircuitFusion 和 NetTAG 引领多模态和跨阶段对齐方向。

4. **Decoder 技术全景** — 覆盖 RTL 生成、HLS 生成、验证调试、硬件安全、流程自动化、物理设计、架构设计、模拟设计八大应用领域的 111+ 篇解码器工作。关键技术路径包括 prompt engineering、SFT/LoRA、RAG、RLHF/CDPO。

5. **挑战与路线图** — 从模型泛化/可扩展性、数据可用性（含合成数据）、Encoder-Decoder 桥接（GenEDA）、闭环优化与 Agentic CFM 四个维度给出系统性挑战和未来方向。

---

## 2. EDA 阶段映射（①-⑰）

参照 [芯片流程.md](../芯片流程.md) 的 17 阶段标准编号：

| 阶段 | 覆盖 | 说明 |
|------|:---:|------|
| **① RTL 设计** | ✅ **核心** | Decoder 型 CFM 以 RTL 代码生成为最大应用领域（RTLCoder, VerilogCoder, MAGE, OriGen, ChipGPT 等）；Encoder 型覆盖 RTL-stage PPA 预测和功能验证 |
| ② RTL 功能仿真 | ✅ | testbench 生成（VerilogEval benchmark）、断言生成（AssertLLM）、RTL 调试（RTLFixer, MEIC） |
| ③ 逻辑综合 | ✅ **核心** | Netlist encoder 的核心阶段：DeepGate 系列以 AIG 为输入做功能表示学习，支持 SAT 求解、逻辑优化、QoR 预测；Decoder 侧有综合脚本生成（ChatEDA, ChipNeMo） |
| ④ 门级仿真 | ✅ | Encoder 型通过时序/功耗预测辅助门级仿真决策；Decoder 的断言生成可跨阶段复用 |
| ⑤ STA（静态时序分析） | ✅ | Encoder 型做 pre-routing slack prediction、路径延迟预测；属于时序预测类下游任务 |
| ⑥ 形式验证 | ✅ | DeepGate2/3 支持 SAT 求解，FGNN 做算术块识别，GAMORA 做布尔功能推理；Decoder 侧生成断言辅助等价检查 |
| ⑦ 布局规划 (Floorplan) | ✅ | CircuitNet、TAG、HARP 等 encoder 做拥塞/DRC 预测；Decoder 侧 DRC-Coder 生成设计规则检查代码 |
| ⑧ 标准单元摆放 (Placement) | ✅ | TAG 做布局匹配预测、线长估计、寄生电容预测；Circuit GNN 做拥塞和线长预测 |
| ⑨ 时钟树综合 (CTS) | ❌ | 论文未专门覆盖 CTS 阶段的 CFM，属于空白区域 |
| ⑩ 布线 (Routing) | ✅ | Encoder 做 routing congestion 预测、IR drop 预测、可布线性评估 |
| ⑪ 后仿真 | ⚠️ 间接 | 通过 PPA/STA/IR drop 预测间接支撑后仿真决策，无专门的 CFM 直接针对后仿真 |
| ⑫ 物理验证 (DRC + LVS) | ✅ | DRC-Coder 使用图像+文本多模态 LLM 生成 DRC 检查代码；LLM-HD 做 layout hotspot 检测 |
| ⑬ 签核 (Signoff) | ⚠️ 间接 | Encoder 通过 PPA/STA/IR drop 综合评估支撑 signoff 决策；FabGPT 面向制造缺陷分析 |
| ⑭ 流片 | ⚠️ 间接 | FabGPT 涉及 wafer defect 检测和制造数据多模态问答 |
| ⑮ 制造 | ⚠️ 间接 | 制造缺陷检测和良率分析相关 CFM 被提及（FabGPT），但数量极少 |
| ⑯ 封装 + 测试 | ❌ | 论文未覆盖封装测试阶段的 CFM |
| ⑰ 芯片到手 | ❌ | — |

**覆盖率：12/17（含 4 个间接覆盖）。**

这篇综述覆盖了数字芯片 17 阶段流程中从 RTL 到签核的绝大部分环节，是现有 AI4EDA 综述中覆盖面最广的一部。Encoder-based CFM 主要覆盖 HLS、RTL、Netlist、Layout 四个阶段（对应 ①②③⑦⑧⑩），Decoder-based CFM 进一步延伸到验证调试、硬件安全、流程自动化等横切关注点。

> 最容易误读的边界：这篇综述不是提出一个能解决所有 EDA 任务的统一模型，而是对「已有 CFM 工作」的分类和系统化梳理。论文中提到的 encoder 和 decoder 互相独立，目前尚无一个同时具备预测和生成能力、覆盖所有设计阶段的统一 CFM。Encoder-decoder 桥接（如 GenEDA）还在早期探索阶段。

---

## 3. 综述的分类体系（taxonomy）

这节要解决的问题是：面对 160+ 篇 AI4EDA 论文，这篇综述用什么样的分类框架把它们组织成一个脉络清晰的知识体系？

论文构建了一个**三层分类体系**：

### 3.1 第一层：AI4EDA 的两种范式（Type I vs Type II）

论文首先将 AI4EDA 的全部工作划分为两种根本不同的范式：

**Type I：Task-Specific Supervised Predictive AI（传统范式）**

```
Single-Stage Circuit Data → Label Collection → Feature Extraction → ML Model Design → ML Model Training → Single EDA Task
```

- 为每个 EDA 任务**单独收集标注数据**、**单独设计特征**、**单独训练模型**
- 已被广泛研究，覆盖几乎所有设计阶段和主要设计目标（时序、面积、功耗、拥塞、IR drop 等）
- 三大局限：(1) 标注数据难获取 — 粗粒度任务的每个电路只有一个 label，标注过程（如 layout）本身耗时巨大；(2) 模型开发周期长 — 从数据采集到测试上线需数月工程努力；(3) 无法跨任务泛化 — 每个模型只学到任务特定模式

**Type II：Circuit Foundation Model（CFM，本综述焦点）**

```
Phase 1: Pre-Train (unlabeled data → self-supervised → General Circuit Embedding / Pre-trained LLM)
Phase 2: Application (task-specific data → lightweight fine-tuning → predictive/generative EDA tasks)
```

- 核心优势：(1) 从无标注数据中学习电路本质属性；(2) 只需少量标注数据做高效微调；(3) 一个预训练模型可适配多个下游任务；(4) Decoder 型有前所未有的生成能力

论文作者的立场非常明确：**Type II 不是对 Type I 的否定，而是互补**。Type I 在处理特定预测任务上已经很成熟，但 CFM 带来了泛化性、数据效率和生成能力这三个 Type I 不具备的维度。

### 3.2 第二层：CFM 的两大技术路线（Encoder vs Decoder）

这是本综述最核心的二分法：

| 维度 | Encoder-based CFM | Decoder-based CFM |
|------|-------------------|-------------------|
| **数据形式** | 图结构（AIG、网表图、CDFG）+ 多模态 | 文本（HDL 代码、自然语言规格） |
| **模型架构** | GNN / Graph Transformer / 多模态融合网络 | 预训练 LLM（Llama, DeepSeek-Coder, GPT-4 等） |
| **预训练策略** | 从头设计自监督任务（对比学习 / 掩码重建 / 功能监督） | 复用通用 LLM 的预训练，再做领域适配（CPT/SFT/LoRA） |
| **下游任务** | 预测型：PPA 估计、功能推理、SAT 求解、热点检测 | 生成型：RTL 代码、验证断言、EDA 脚本 |
| **开发门槛** | 高（需收集大规模电路图数据、设计专用架构和预训练任务） | 较低（直接复用已有 LLM，重点在领域适配） |
| **数量（截至综述）** | 21 篇 | 111+ 篇 |

两个关键宏观事实：
1. **Decoder 数量远超 Encoder**（约 5:1）—— 因为 encoder 需要从零构建，门槛高得多
2. **两者发展几乎平行、很少交叉** —— 这是论文第 6 节指出的重大缺憾，GenEDA 等桥接工作才刚刚起步

### 3.3 第三层：按设计阶段 / 应用领域进一步细分

**Encoder-based CFM 按设计阶段分为**：

- **HLS Stage（4.1 节）**：ProgSG, HARP 等，输入 C/C++ 代码 + CDFG 图，做设计空间探索（DSE）
- **RTL Stage（4.2 节）**：Design2Vec, SNS v2, CircuitEncoder, CircuitFusion，从 RTL 代码和 AST 图学习表示，支持 PPA 预测和功能验证
- **Netlist Stage（4.3 节）**：最活跃的 encoder 子领域 — DeepGate 系列（1/2/3/4）、FGNN、GAMORA、HOGA、PolarGate、NetTAG、DeepCell、MGVGA 等，以 AIG 或 post-synthesis 网表为输入
- **Layout Stage（4.4 节）**：Circuit GNN, TAG, LLM-HD，处理版图拓扑+几何信息

**Decoder-based CFM 按应用领域分为**：

- **RTL Code Generation（5.1 节）**：最大的 decoder 子领域，包括 benchmark（VerilogEval, RTLLM, CVDP）和生成模型（RTLCoder, ChipGPT, VerilogCoder, OriGen, ChipSeek, MAGE 等）
- **HLS Code Generation（5.3 节）**：C/C++ HLS 代码生成
- **Verification & Debug（5.2 节）**：testbench、断言（SVA）、调试修复
- **Hardware Security（5.4 节）**：CWE 检测、木马检测、安全断言
- **Flow & Layout（5.5 节）**：EDA 流程脚本生成、物理设计辅助
- **Architecture Design（5.6 节）**：系统架构级设计辅助
- **Analog Design（5.7 节）**：模拟电路拓扑生成和优化

### 3.4 分类维度的交叉

论文的精华在于**不只是罗列工作，而是揭示了分类维度之间的交叉关系**：

- **按预训练策略分类**（图 6）：对比学习 vs 掩码重建 vs 监督预训练 vs 多模态融合
- **按多模态融合方式分类**（图 10）：混合模型架构 vs 交叉注意力融合
- **按跨阶段对齐方式分类**（图 10）：对比学习对齐 vs 掩码重建对齐
- **按 Decoder 适配技术分类**：prompt engineering vs SFT vs LoRA vs RAG vs RLHF

---

## 4. 方法与架构

这节要解决的问题是：CFM 的具体工作流程是什么样的？Encoder 和 Decoder 两种范式分别在技术层面如何运作？

### 4.1 整体 Pipeline

#### Encoder-based CFM 的完整流程

```text
                  Phase 1: Pre-Train (Self-supervised, no labels)
  ┌──────────────────────────────────────────────────────────────────────┐
  │                                                                      │
  │   Unlabeled Circuit Data (Graph / Text / Image)                      │
  │       │                                                              │
  │       ▼                                                              │
  │   ┌─────────────────────────────────┐                               │
  │   │ Circuit Encoder                 │                               │
  │   │ (GNN / Graph Transformer /      │                               │
  │   │  Multi-modal Fusion Network)    │                               │
  │   └──────────────┬──────────────────┘                               │
  │                  │                                                   │
  │                  ▼                                                   │
  │   ┌─────────────────────────────────┐                               │
  │   │ Self-supervised Pre-training     │                               │
  │   │ • Contrastive (functional equiv) │                               │
  │   │ • Mask-reconstruction           │                               │
  │   │ • Supervised circuit pretext     │                               │
  │   │ • Multi-modal fusion            │                               │
  │   └──────────────┬──────────────────┘                               │
  │                  │                                                   │
  │                  ▼                                                   │
  │   General Circuit Embedding (dense vector)                          │
  │   "Embeddings of similar circuits will be closer"                   │
  └──────────────────────┬───────────────────────────────────────────────┘
                         │
                  Phase 2: Application (Lightweight Fine-tuning)
                         │
                         ▼
  ┌──────────────────────────────────────────────────────────────────────┐
  │   Task-Specific Circuit Data (small, labeled)                        │
  │       │                                                              │
  │       ▼                                                              │
  │   ┌─────────────────────────────────┐                               │
  │   │ Lightweight Downstream Predictor │                              │
  │   │ (MLP / shallow GNN)             │                               │
  │   └──────────────┬──────────────────┘                               │
  │                  │                                                   │
  │                  ▼                                                   │
  │   Predictive EDA Tasks:                                             │
  │   ✓ Timing  ✓ Area  ✓ Power  ✓ IR Drop                             │
  │   ✓ Congestion  ✓ SAT Solving  ✓ Equivalence Check                 │
  │   ✓ Functional Reasoning  ✓ Hotspot Detection                       │
  └──────────────────────────────────────────────────────────────────────┘
```

#### Decoder-based CFM 的完整流程

```text
                  Phase 1: Pre-Train (on general text/code data)
  ┌──────────────────────────────────────────────────────────────────────┐
  │   Textual Unlabeled Data (Natural language + Code)                   │
  │       │                                                              │
  │       ▼                                                              │
  │   ┌─────────────────────────────────┐                               │
  │   │ LLM Decoder (Auto-Regressive)   │                               │
  │   │ Llama / DeepSeek-Coder / GPT-4  │                               │
  │   │ Mistral / Qwen / StarCoder      │                               │
  │   └──────────────┬──────────────────┘                               │
  │                  │                                                   │
  │                  ▼                                                   │
  │   Pre-trained LLM (general knowledge + code understanding)           │
  └──────────────────────┬───────────────────────────────────────────────┘
                         │
                  Phase 2: Application (Domain Adaptation)
                         │
                         ▼
  ┌──────────────────────────────────────────────────────────────────────┐
  │   Task-Specific Circuit Data                                         │
  │       │                                                              │
  │       ├──→ Prompt Engineering (zero-shot / few-shot / CoT)           │
  │       ├──→ SFT / LoRA fine-tuning on (spec, RTL) pairs              │
  │       ├──→ RAG (retrieval-augmented generation)                     │
  │       └──→ RL Alignment (EDA tool feedback as reward)               │
  │                  │                                                   │
  │                  ▼                                                   │
  │   Generate: RTL / testbench / assertion / script / description       │
  │       │                                                              │
  │       ▼                                                              │
  │   EDA Tool Feedback (compile, simulate, synthesize, formal verify)   │
  │       │                                                              │
  │       ├──→ Single-agent iteration (self-debug loop)                 │
  │       └──→ Multi-agent collaborative repair                        │
  │                  │                                                   │
  │                  ▼                                                   │
  │   Final synthesizable / verifiable hardware artifact                 │
  └──────────────────────────────────────────────────────────────────────┘
```

### 4.2 核心模块逐个详解

#### 模块 A：Circuit Encoder（电路编码器）

**这个模块存在的理由**：电路天然是图结构（gate 和 wire），不是序列，无法直接用 Transformer 编码。需要一个专门的编码器把电路结构转化为有意义的向量表示。

**架构演进路线**（以 Netlist Stage 为例）：

1. **DeepGate [116]（DAC 2022）**：开创性工作，使用带注意力机制的递归 GNN 处理 AIG 图。按 AND/NOT 门逻辑做 forward + reversed 传播，用 signal probability 作为监督信号（通过随机逻辑仿真获取标签）。每个 node embedding 融合了 gate type + 邻域信息。

2. **DeepGate2 [123]（ICCAD 2023）**：引入 pairwise truth table Hamming distance 作为监督，用单轮 GNN + self-attention 替代多轮递归。新增 functionality-aware loss，最小化功能等价 gate 对之间的 embedding 距离。这是 encoder 理解 "电路功能等价性" 的关键设计。

3. **DeepGate3 [107]（DAC 2024）**：用 Graph Transformer 替代纯 GNN，以 DeepGate2 作为 node tokenizer，再加一层 Graph Transformer 做 graph-level pooling。新增 fan-in cone 级别的预训练任务（预测子图的 size 和 depth），大幅提升可扩展性。

4. **DeepGate4 [124]（ICLR 2025）**：引入 GNN-based sparse transformer，利用图稀疏性降低 Transformer 的时间/内存复杂度。按 logic level 将电路划分为 cones 再分别处理，加入 level 和 out-degree 等结构编码。

**其他 Encoder 的设计亮点**：

- **GAMORA [54]**：多任务预训练（同时识别 adder root/leaf nodes、XOR functions、MAJ functions），用共享表示提升跨任务泛化
- **HOGA [119]**：hop-wise 特征预计算 + 门控自注意力，避免了递归聚合的昂贵计算，支持分布式训练
- **PolarGate [120]**：ambipolar embedding space（每个节点有 positive + negative 两个 embedding 对应逻辑 0 和 1），可微逻辑算子（OPAND, OPNOT），消息传递严格遵循布尔逻辑
- **NetTAG [110]**：将 AIG 扩展到 post-synthesis netlist（含多种标准单元），提取 gate-level 符号逻辑表达式用 LLM 编码，GNN 捕获全局结构
- **CircuitFusion [106]**：首个同时处理 HDL 文本、功能摘要文本、AST 图三种模态的 encoder，用 cross-attention 做模态融合 + 跨阶段对齐

#### 模块 B：Decoder 的领域适配技术

**这个模块存在的理由**：通用 LLM 不懂 Verilog 语法和电路语义，直接生成会产生大量语法错误和功能错误的 "幻觉代码"。需要通过各种适配技术让 LLM 学会电路领域知识。

**五种主要适配技术**（从简单到复杂）：

1. **Prompt Engineering**（零成本，效果有限）
   - MAGE [15]：用 GPT-3.5-Turbo 的 few-shot prompt 做 RTL 生成，在 VerilogEval 上达到 75% pass@1
   - 局限：依赖 prompt 质量，无法注入领域知识，复杂设计容易出错

2. **Supervised Fine-Tuning (SFT)**（需要标注数据，效果显著提升）
   - RTLCoder [14]：在 CodeGen 基础上用 Verilog 数据做 SFT，VerilogEval pass@1 提升至 80%+
   - OriGen：在 DeepSeek-Coder 基础上用大规模 RTL 语料做 SFT
   - VerilogCoder：任务感知的课程学习 + 多任务 SFT（代码生成 + 修复）

3. **LoRA / QLoRA**（参数高效，工业友好）
   - ChipNeMo [13]：在 Llama 上用 LoRA 做领域适配，参数量仅增加 0.1%，在 NVIDIA 内部 EDA 任务上显著优于通用 LLM
   - 优势：训练成本低，可以快速迭代

4. **Retrieval-Augmented Generation (RAG)**（知识注入，无需训练）
   - ChIRAAG：RAG-based RTL 生成，检索相似设计做上下文增强
   - RAG-EDA：为 EDA 任务构建领域知识库做检索增强

5. **Reinforcement Learning Alignment**（EDA 工具反馈，质量最高但成本也最高）
   - ChipSeek：用 DPO（Direct Preference Optimization）以 EDA 工具编译/仿真结果为 reward，对齐 LLM 输出和电路正确性
   - VeriRL：用 RLHF 框架以语法检查和功能仿真的 pass/fail 作为 reward 信号

#### 模块 C：多模态融合与跨阶段对齐

**这个模块存在的理由**：电路在不同设计阶段有不同表示（RTL 文本、网表图、版图图像），但这些表示描述的是**同一个电路**。如果能对齐这些表示，模型就能理解电路的完整信息。

**融合策略分类**（图 10）：

- **Hybrid Model**：用不同 encoder 分别处理各模态，再拼接。如 ProgSG 的 GNN（CDFG）+ LLM（C/C++ text），NetTAG 的 GNN（结构）+ LLM（逻辑表达式文本）。
- **Cross-Attention Fusion**：各模态独立编码后用 cross-attention 对齐，如 CircuitFusion。
- **跨阶段对比学习**：CircuitEncoder [109] 将同一电路的 RTL 表示和 netlist 表示在 latent space 中对齐（拉近），实现跨阶段知识迁移。

### 4.3 模块职责矩阵

| 模块 | 输入 | 输出 | 用到的模型/工具 | 是否需训练 |
|------|------|------|----------------|:---:|
| **Circuit Encoder（图编码）** | AIG/网表图/CDFG/版图图 | 通用电路 embedding | DeepGate, GAMORA, NetTAG 等专用 GNN/Transformer | 是（从头预训练） |
| **Self-supervised Pre-training** | 无标注电路数据 | 预训练权重 | 对比学习 / 掩码重建 / 功能监督任务 | 是（核心阶段） |
| **Lightweight Predictor** | 通用 embedding + 少量任务标签 | PPA/功能预测结果 | MLP / shallow GNN / linear probe | 是（轻量微调） |
| **LLM Decoder** | 自然语言/代码文本 token | 生成文本（RTL/断言/脚本） | Llama, DeepSeek-Coder, GPT-4 等 | 否（使用预训练权重） |
| **Domain Adaptation** | 电路领域数据 + LLM | 领域适配后的 LLM | SFT / LoRA / RAG / RLHF | 视策略而定 |
| **EDA Tool Feedback Loop** | 生成的 RTL/脚本 + EDA 工具 | 编译/仿真/综合结果 | iverilog, Yosys, Design Compiler 等 | 否（推理反馈） |
| **Multi-Agent Orchestration** | 子任务 + agent 角色定义 | 协作完成的硬件产物 | Generator / Judge / Debugger agents | 否（推理编排） |

---

## 5. 综述提出的分类维度与判据

这节要解决的问题是：这篇综述在归纳 160+ 篇工作时，用什么样的分类维度和判据来区分和组织这些工作？这些分类维度本身就是综述的核心学术贡献。

### 5.1 判据一：Type I vs Type II — 是否采用「预训练 + 微调」范式

这是最根本的判据，决定了是否属于本综述的覆盖范围：

- **Type I** 的特征：为特定任务收集标签 → 设计特征 → 设计模型 → 训练 → 单一任务预测。一套流程只解决一个问题。
- **Type II（CFM）** 的特征：Phase 1 在无标注数据上做自监督预训练，学到通用电路知识；Phase 2 用少量任务标注数据做轻量适配。**一个预训练模型可以服务多个下游任务**。

论文的筛选逻辑：只要满足 "预训练在 circuit-related data 上" + "意图支持多个 circuit/EDA tasks" 这两个条件，就纳入 CFM 范畴。这意味着即使某些 decoder 工作只做了 prompt engineering（没有训练），它仍然属于 CFM，因为它复用的 LLM 本身就是一个 foundation model。

### 5.2 判据二：Encoder-based vs Decoder-based — 预测还是生成

这是本综述最核心的二分法判据，区分依据是**模型的主要能力方向**：

**Encoder-based CFM 的判据**：
- 输入以图结构为主（AIG、网表图、CDFG、版图图）
- 输出是连续向量（embedding），经过轻量预测器转化为具体预测值
- 下游任务是**预测型**的：在 EDA 工具跑完之前就给出质量估计
- 需要**从头设计模型架构和预训练任务**，无法直接复用 CV/NLP 的 foundation model
- 数量少（21 篇），但每篇的技术深度和创新点都较高

**Decoder-based CFM 的判据**：
- 输入以文本为主（HDL 代码、自然语言规格）
- 输出是离散 token 序列（RTL 代码、断言、脚本）
- 下游任务是**生成型**的：自动创建电路设计的文本表示
- **直接复用已有的通用 LLM**，重点在领域适配而非架构创新
- 数量多（111+ 篇），但技术方法相对统一（不同适配策略的排列组合）

**为什么 Decoder 多这么多？** 论文给出了清晰解释（Section 1.3）：
> "This imbalance largely reflects the higher barrier to developing encoder-based CFMs, which typically require training from scratch on large-scale circuit datasets with carefully designed pre-training objectives, whereas many decoder-based works can directly leverage existing pre-trained LLMs and focus on task adaptation."

### 5.3 判据三：Encoder 的预训练策略 — 如何学到通用电路表示

论文将 encoder 的预训练策略归纳为四种，并以此作为分类维度（图 6）：

**1. 自监督对比学习（Contrastive Learning）**

核心技术思想：功能等价的电路 embedding 应该接近，功能不同的应该远离。

代表工作：
- FGNN [108]（DAC 2022）：首个将功能对比学习引入 netlist 编码，解决算术块识别问题
- SNS v2 [25]（MICRO 2023）：RTL 阶段的功能对比学习，用于 post-synthesis PPA 预测
- CircuitEncoder [109]（ASP-DAC 2025）：同时在 intra-stage（同阶段）和 cross-stage（RTL ↔ netlist）两个层面做对比学习
- CircuitFusion [106]（ICLR 2025）：对图/文本/功能摘要三种模态做对比对齐

**2. 自监督掩码重建（Mask-Reconstruction）**

核心技术思想：类似 BERT 的 masked language modeling，屏蔽电路的一部分，让模型重建。

代表工作：
- HARP [111]（ICCAD 2023）：masked pragma reconstruction for HLS design space exploration
- LLM-HD [112]（DAC 2024）：masked language modeling 处理 GDSII 版图数据
- NetTAG [110]（DAC 2025）：masked gate reconstruction + logic expression contrastive + netlist graph contrastive，三种自监督任务联合预训练
- MGVGA [113]（ICLR 2025）：masked gate reconstruction for QoR prediction 和逻辑等价性识别

**3. 监督预训练任务（Supervised Pre-training Tasks）**

核心技术思想：虽然不是下游任务的直接监督，但提供通用性强的电路属性作为预训练监督信号。

代表工作：
- DeepGate 系列 [116, 123, 107, 124]：以 signal probability、truth table distance、subgraph size/depth 等通用电路属性作为预训练监督
- GAMORA [54]：多任务学习（adder/XOR/MAJ 识别）作为预训练
- DeepSeq [125]：transition probability prediction + logic probability prediction + truth-table difference

**4. 多模态融合（Multimodal Fusion）**

核心技术思想：电路有多种表示形式，融合它们能学到更丰富的表示。

代表工作：
- ProgSG [121]：LLM（C/C++ 文本）+ GNN（CDFG 图）混合架构
- CircuitFusion [106]：cross-attention 融合 HDL 文本 + 功能摘要 + AST 图
- NetTAG [110]：LLM（gate 逻辑表达式）+ GNN（网表结构）
- TAG [118]：fastText（instance name 文本）+ GNN（版图层次图）

### 5.4 判据四：Decoder 的领域适配策略 — 如何让通用 LLM 学会电路

论文按适配技术的复杂度和成本排序：

| 技术 | 是否需要训练 | 需要标注数据 | 电路知识注入深度 | 代表工作 |
|------|:---:|:---:|------|------|
| Prompt Engineering | 否 | 否 | 浅（依赖模型泛化） | MAGE, ChatEDA |
| SFT（全参数微调） | 是 | 是（spec-RTL pairs） | 中 | RTLCoder, OriGen, VerilogCoder |
| LoRA/QLoRA | 是 | 是 | 中（参数高效） | ChipNeMo |
| RAG | 否 | 需要知识库 | 中（检索补充） | ChIRAAG, RAG-EDA |
| RLHF/DPO | 是 | 需要 reward 信号 | 深（EDA 工具反馈） | ChipSeek, VeriRL |
| Multi-Agent | 否（编排层） | 否 | 随 agent 角色而定 | Spec2RTL-Agent, RTLSquad |

### 5.5 判据五：电路数据独特属性 — 为什么 CFM 不能直接套用 CV/NLP 方案

论文从数据视角系统概括了**六大独特属性**，这既是对已有工作的归纳，也是未来 CFM 设计的指导性原则：

1. **跨阶段功能等价性（Equivalence across design stages）**
   - 判据：同一个电路在 RTL → 网表 → 版图各个阶段必须保持功能等价
   - 影响：催生了 (a) 等价变换数据增强（logic optimization 生成变体），(b) 跨阶段对比对齐（CircuitEncoder, CircuitFusion）
   - CFM 独特性：CV/NLP 中没有 "同一个物体在不同模态下必须语义等价" 这么强的约束

2. **多模态电路格式（Multimodal circuit format）**
   - 判据：电路天然有三种模态 — Text（HDL/规格）、Graph（网表/CDFG/版图连接）、Image（版图几何）
   - 影响：催生了多模态融合 encoder（ProgSG, CircuitFusion, NetTAG, TAG）
   - CFM 独特性：NLP 只有 text，CV 只有 image，电路天然多模态

3. **PPA + 功能双重目标（Multiple objectives）**
   - 判据：电路设计必须同时优化 Power/Performance/Area 和功能正确性
   - 影响：CFM 的预训练任务需要同时学习结构特征（影响 PPA）和语义特征（影响功能）
   - CFM 独特性：CV/NLP 模型通常只优化一个目标

4. **硬件并行执行（Parallel execution of hardware）**
   - 判据：电路本质是并行的（所有组合逻辑同时计算），不同于软件的串行执行
   - 影响：时序电路 encoder（DeepSeq）需要分离 structure/function/sequential 三个 embedding 空间
   - CFM 独特性：LLM 天然假设 token 是串行的，但电路是并行的

5. **组合爆炸（隐含属性，Section 3 多处提及）**
   - 判据：电路的空间复杂度和搜索空间巨大（100B+ 晶体管）
   - 影响：scalability 是所有 CFM 的核心挑战，催生了层级建模、图划分、sparse transformer 等技术

6. **数据稀缺性（Circuit data availability）**
   - 判据：公开电路数据远少于文本/图像，工业数据因商业 IP 不愿公开
   - 影响：(a) 自监督预训练变得至关重要（不依赖标注），(b) 合成数据（SynCircuit, SynC-LLM）成为新方向，(c) 数据增强（等价变换）被广泛使用
   - CFM 独特性：NLP/CV 有海量公开数据，电路领域的 "ImageNet 时刻" 尚未到来

---

## 6. 训练与实验设置

这节要解决的问题是：这篇综述覆盖的 160+ 篇论文在实验层面有什么共同特点？用什么 benchmark 和指标？

### 6.1 是否需要训练

综述论文本身不需要训练，但从它覆盖的 CFM 工作中可以总结出训练的完整图景：

| CFM 类型 | 预训练阶段 | 微调阶段 | 数据需求 |
|---------|-----------|---------|---------|
| **Encoder（从头训）** | 在无标注电路图上自监督预训练，如 DeepGate2 在 OpenABC-D 等 benchmark 的 AIG 上训 | 用少量任务标注数据做轻量微调（线性探测或浅层 MLP） | 预训练数据量：数千到数万电路图；微调标注：几十到几百个样本 |
| **Encoder（有监督预训练）** | 用通用电路属性标签（truth table, signal probability）监督训练 | 同上 | 预训练需要仿真/计算生成伪标签 |
| **Decoder（SFT/LoRA）** | 基于已预训练的通用 LLM，不做预训练 | 在 (spec, RTL) 对或 Verilog 语料上做 SFT/LoRA | 数百到数万对数据；如 RTLCoder 用 ~27K 对 |
| **Decoder（RLHF/DPO）** | 同 SFT | 用 EDA 工具编译/仿真结果做 reward 对齐 | 需要大量的 EDA 工具调用（计算昂贵） |
| **Decoder（Prompt-only）** | 不训练 | 不训练 | 零标注，但有 API 调用成本 |

### 6.2 实验设置

**主要 Benchmark：**

| Benchmark | 针对任务 | 规模 | 代表使用 |
|-----------|---------|------|---------|
| **VerilogEval [14]** | RTL 代码生成（功能正确性） | 156 题，来自 HDLBits | RTLCoder, ChipGPTV, VerilogCoder 等 |
| **RTLLM [12]** | RTL 代码生成（综合质量） | 30 个设计，评估综合后的面积/延迟 | MAGE, OriGen |
| **CVDP** | RTL 代码生成 | 多维度评估 | 多篇 decoder 工作 |
| **OpenABC-D [133]** | 综合后 PPA 预测 | 33 个真实开源设计 | DeepGate, SNS v2, CircuitFusion |
| **CircuitNet [294]** | 版图级预测（拥塞/DRC/IR drop） | 多种布局数据 | CircuitNet, TAG |
| **ITC'99, IWLS, EPFL** | 网表级功能/结构学习 | 标准 benchmark 套件 | 大部分 netlist encoder |
| **ICCAD 2012/2020** | 版图热点检测 | 含 GDSII 的版图数据 | LLM-HD |
| **ISPD 2011, DAC 2012** | 拥塞/线长预测 | 含布局信息 | Circuit GNN |

**主要评估指标：**

Decoder 生成任务：

- **pass@k**：在 k 个采样中至少有一个通过 testbench 的比例。最核心指标。

  $$
  \text{pass@k} = \mathbb{E}_{\text{Problems}}\left[1 - \frac{\binom{n-c}{k}}{\binom{n}{k}}\right]
  $$

  - $n$：每个问题生成的总样本数
  - $c$：通过 testbench 的样本数
  - $k$：评估时考虑的采样数

- **functional pass@k**：通过功能仿真（iverilog + testbench）的比例
- **syntax pass@k**：通过语法检查（无编译错误）的比例
- **SimEval**：多视角代码相似度（AST + CFG + netlist 三视图），比 BLEU/ROUGE 更适合评估 HDL 生成质量

Encoder 预测任务：

- **MAE（Mean Absolute Error，平均绝对误差）**：

$$
\text{MAE} = \frac{1}{n}\sum_{i=1}^{n}\left|y_i - \hat{y}_i\right|
$$

- **MAPE（Mean Absolute Percentage Error，平均绝对百分比误差）**：

$$
\text{MAPE} = \frac{100\%}{n}\sum_{i=1}^{n}\left|\frac{y_i - \hat{y}_i}{y_i}\right|
$$

- **RMSE（Root Mean Square Error，均方根误差）**：

$$
\text{RMSE} = \sqrt{\frac{1}{n}\sum_{i=1}^{n}(y_i - \hat{y}_i)^2}
$$

其中 $n$ 是样本数，$y_i$ 是第 $i$ 个样本的真值（如实测时序/功耗），$\hat{y}_i$ 是模型预测值。MAE 与量纲同阶、易解释；MAPE 是相对误差，$y_i$ 接近 0 时会爆炸；RMSE 对大偏差惩罚更重，适合关心最坏情况的场景。

- **F1 / AUC / Accuracy**：分类任务（功能推理、SAT 求解、热点检测）
- **R2（决定系数）**：回归任务拟合优度
- **Precision / Recall**：拥塞预测等异常检测类任务

### 6.3 关键实验发现（论文层面的统计结论）

论文没有自己的实验，而是通过系统综述归纳出以下发现：

**发现 1：Decoder 数量远超 Encoder（约 5:1）**

从图 3 可以看到，encoder-based CFM 各设计阶段总计约 21 篇（HLS: ~3, RTL: ~4, Netlist: ~11, Layout: ~3），decoder-based CFM 总计 111+ 篇。这是该领域最显著的结构性不平衡。

**发现 2：90%+ 工作在 2022 年或之后发表**

论文 Figure 2 的 evolutionary tree 和 Figure 3 的年份分布统计清楚地展示了这一点。最早的 encoder（Design2Vec, 2021）和 decoder（DAVE, 2020）只是零星尝试，真正的爆发始于 2023-2024 年。

**发现 3：RTL 代码生成是 Decoder 领域的绝对主力**

从图 3 (b) 可以看到，"RTL Code" 类别的 decoder 工作数量在所有年份（2023/2024/2025）都远超其他类别（Verification & Debug, Security, Flow & Layout, Architecture, Analog）。

**发现 4：Netlist stage 是 Encoder 领域最活跃的子领域**

从图 3 (a) 可以看到，netlist stage 的 encoder 数量 (11) 远多于 HLS (3)、RTL (4)、Layout (3)。这是因为 AIG 是一种干净的图结构，最符合 GNN 处理的自然范式。

**发现 5：缺乏统一的评估标准是最大的方法论问题**

多数 encoder-based CFM 和 decoder-based CFM（除 RTL 生成外）在不同数据集上用不同指标评估，无法公平比较。论文在第 6.1 节明确指出："This makes it difficult to compare models fairly or to track progress across tasks, modalities, and design stages."

---

## 7. 创新点

### 创新点 1：首次提出 "Circuit Foundation Model" 这一统一概念框架

这篇综述最大的学术贡献不是提出了一个新模型，而是提出了一个新的**分类学概念**。在这篇论文之前，AI4EDA 社区存在严重的概念混乱：有人叫 "large circuit model (LCM)"（[11]），有人叫 "LLM for EDA"（[73-79]），有人叫 "foundation model for chip design"。这些术语的范围各不相同，互相重叠但又不完全一致。

这篇论文做了一件基础性的概念澄清工作：
- 明确 CFM = "预训练 + 微调" 的 AI 模型，且数据和下游任务都在电路/EDA 领域
- 把 encoder-based（预测）和 decoder-based（生成）统一纳入 CFM 框架
- 把 Type I（传统监督学习）和 Type II（CFM）区分为不同范式，前者是后者的基础和对比参照

**和已有综述的关键区别**（Table 1）：此前几乎所有综述 [73-79] 只覆盖 decoder-based 方法（LLM for EDA），只有一篇 perspective paper [11] 同时讨论了 encoder 和 decoder。这篇综述是第一篇**系统性地涵盖两种范式并提供深度分析和对比**的综述。

### 创新点 2：从「电路数据独特属性」出发的分析框架（Section 3）

已有的 AI4EDA 综述大多按应用领域罗列工作（"LLM 在 RTL 生成中的应用" → "LLM 在验证中的应用" → ...）。这篇论文的不同之处在于，它先花整整一节（Section 3）讨论**电路数据本身的属性**——跨阶段等价性、多模态格式、PPA+功能双重目标、硬件并行性、数据稀缺、电路可复用性——然后再用这些属性解释为什么 CFM 要被设计成我们看到的样子。

例如：
- "DeepGate2 为什么用 truth table distance 做监督？" → 因为 "功能等价性" 是电路数据的核心属性
- "为什么需要多模态融合？" → 因为电路天然有三种模态
- "为什么自监督学习在 CFM 中特别重要？" → 因为 "数据稀缺"

这种「从数据属性到模型设计」的因果链是本综述最深刻的分析贡献。

### 创新点 3：四维度的预训练策略分类（Figure 6）

论文将 encoder 的预训练策略从 「怎么做」的角度分为对比学习、掩码重建、监督预训练、多模态融合四类，每一类都有清晰的技术原理图和代表工作 timeline。这种分类不是简单罗列，而是揭示了设计空间：

- 如果想学「功能等价性」→ 用对比学习（拉近等价电路，推远不等价电路）
- 如果想学「结构和完整性」→ 用掩码重建（mask gate 再预测）
- 如果想学「通用电路属性」→ 用监督预训练（truth table distance, signal probability）
- 如果想学「跨模态关联」→ 用多模态融合

### 创新点 4：Encoder-Decoder 桥接的展望（GenEDA, Section 6.3）

论文不仅总结了已有工作，还展示了作者团队的最新尝试（GenEDA [300]）——将 netlist encoder（NetTAG [110]）的图 embedding 注入 LLM decoder，实现 "reverse netlist functional reasoning"（从门级网表反推高层功能描述和 RTL 代码）。这在方法论上意义重大：

- 证明了 encoder 学习的电路表示确实包含 decoder 缺失的结构化知识
- 提出了两种对齐范式：embedding-based alignment（训练时注入）和 prediction-based alignment（以文本 prompt 形式注入）
- 为未来 "统一 CFM" 提供了可行的技术路线

### 创新点 5：合成数据缓解电路数据稀缺（SynCircuit + SynC-LLM）

论文在 Section 6.2 介绍了作者团队的两项合成数据工作：
- **SynCircuit [296]**：图中心范式，学习真实电路图的统计分布，采样生成新电路图再转回 RTL
- **SynC-LLM [297]**：层级范式，先生成高层电路骨架，再用 LLM 生成局部 RTL 块

这两项工作直接回应了 "电路数据稀缺" 这一根本瓶颈，论文同时坦诚指出了合成数据的局限：无法保证全局功能行为，功能可控性仍是开放问题。

---

## 8. EDA 缩写表

| 缩写 | 全称 | 一句话解释 |
|------|------|-----------|
| **AIG** | AND-Inverter Graph | 与-非图，逻辑综合的标准中间表示，只有 2 输入 AND 和取反边 |
| **AST** | Abstract Syntax Tree | 抽象语法树，编程语言/HDL 编译器的标准中间表示 |
| **ATE** | Automatic Test Equipment | 自动测试设备，用于晶圆级和封装后的芯片测试 |
| **BCD** | Binary-Coded Decimal | （本文未直接使用） |
| **BLEU** | Bilingual Evaluation Understudy | NLP 文本生成质量评估指标，在 HDL 生成中参考价值有限 |
| **CDFG** | Control-Data Flow Graph | 控制数据流图，HLS 阶段的标准中间表示 |
| **CFM** | Circuit Foundation Model | 电路基础模型，本文提出的统一概念 |
| **CMOS** | Complementary Metal-Oxide-Semiconductor | 互补金属氧化物半导体，当前数字芯片的主流工艺 |
| **CoT** | Chain-of-Thought | 思维链，prompt 技术，让 LLM 逐步推理 |
| **CPT** | Continued Pre-Training | 继续预训练，在通用 LLM 上用领域数据继续自回归训练 |
| **CTS** | Clock Tree Synthesis | 时钟树综合，为时钟信号插入缓冲器树，确保触发器同时触发 |
| **CVD** | Common Vulnerabilities and Exposures | （本文未直接使用） |
| **CVDP** | Chip Verification Design Platform | RTL 代码生成的一个多维度评估 benchmark |
| **DAC** | Design Automation Conference | 电子设计自动化顶级会议（CCF-A） |
| **DAG** | Directed Acyclic Graph | 有向无环图，组合电路本质上是一个 DAG |
| **DPO** | Direct Preference Optimization | 直接偏好优化，无需显式训练 reward model 的 RL 对齐方法 |
| **DRC** | Design Rule Check | 设计规则检查，验证版图能否被制造 |
| **DSE** | Design Space Exploration | 设计空间探索 |
| **ECO** | Engineering Change Order | 工程变更指令，芯片设计后期的功能性修改 |
| **EDA** | Electronic Design Automation | 电子设计自动化 |
| **FASText** | Fast Text Classification | Facebook 的轻量级文本分类/词嵌入工具 |
| **FF** | Flip-Flop | 触发器，基本的 1 位记忆单元 |
| **GDSII** | Graphic Design System II | 版图交换标准格式，旧称 GDSII Stream |
| **GNN** | Graph Neural Network | 图神经网络，encoder-based CFM 的核心架构 |
| **GRPO** | Group Relative Policy Optimization | DeepSeek 提出的改进 RL 对齐算法 |
| **HDL** | Hardware Description Language | 硬件描述语言（Verilog / VHDL） |
| **HLS** | High-Level Synthesis | 高级综合，将 C/C++/SystemC 翻译为 RTL |
| **HPWL** | Half-Perimeter Wire Length | 半周长线长估计，布局质量的快速近似指标 |
| **IC** | Integrated Circuit | 集成电路 |
| **ICCAD** | International Conference on Computer-Aided Design | 计算机辅助设计国际会议（CCF-B） |
| **IP** | Intellectual Property | 知识产权/硅知识产权，可复用的预设计电路模块 |
| **IR Drop** | Voltage (IR) Drop | 电压降，电源网络上的电压损耗，影响时序和可靠性 |
| **LCM** | Large Circuit Model | 大电路模型，[11] 中提出的概念，本质是多 encoder 对齐 |
| **LLM** | Large Language Model | 大语言模型（如 GPT-4, Llama, DeepSeek） |
| **LoRA** | Low-Rank Adaptation | 低秩适配，一种参数高效的 LLM 微调方法 |
| **LSTM** | Long Short-Term Memory | 长短期记忆网络 |
| **LVS** | Layout vs. Schematic | 版图与原理图对比，验证物理版图与设计网表一致 |
| **MAE** | Mean Absolute Error | 平均绝对误差 |
| **MAPE** | Mean Absolute Percentage Error | 平均绝对百分比误差 |
| **MAJ** | Majority Function | 多数表决函数，三输入中两个以上为 1 时输出 1 |
| **ML** | Machine Learning | 机器学习 |
| **MLP** | Multi-Layer Perceptron | 多层感知机 |
| **NMOS** | N-channel Metal-Oxide-Semiconductor | N 沟道金属氧化物半导体场效应管 |
| **NLP** | Natural Language Processing | 自然语言处理 |
| **PMOS** | P-channel Metal-Oxide-Semiconductor | P 沟道金属氧化物半导体场效应管 |
| **PPA** | Power, Performance, Area | 功耗、性能、面积——芯片设计的三大核心指标 |
| **PPO** | Proximal Policy Optimization | 近端策略优化，RLHF 常用的强化学习算法 |
| **QLoRA** | Quantized Low-Rank Adaptation | 量化低秩适配，LoRA + 模型量化，进一步降低显存需求 |
| **QoR** | Quality of Results | 综合结果质量，指逻辑综合后的 PPA 综合评分 |
| **RAG** | Retrieval-Augmented Generation | 检索增强生成，从知识库检索相关信息辅助 LLM 生成 |
| **RC** | Resistance-Capacitance | 电阻-电容，金属互连线的寄生参数 |
| **RL** | Reinforcement Learning | 强化学习 |
| **RLHF** | Reinforcement Learning from Human Feedback | 基于人类反馈的强化学习 |
| **RMSE** | Root Mean Square Error | 均方根误差 |
| **ROUGE** | Recall-Oriented Understudy for Gisting Evaluation | NLP 文本生成评估指标 |
| **RTL** | Register-Transfer Level | 寄存器传输级，描述数据在寄存器间流动的数字设计抽象层 |
| **SAT** | Boolean Satisfiability | 布尔可满足性问题，NP 完全问题，形式验证的核心 |
| **SDC** | Synopsys Design Constraints | 时序约束文件格式 |
| **SDF** | Standard Delay Format | 标准延时格式，记录每个门/线的延迟值 |
| **SFT** | Supervised Fine-Tuning | 监督微调 |
| **SoC** | System-on-Chip | 片上系统 |
| **SPEF** | Standard Parasitic Exchange Format | 标准寄生参数交换格式，记录走线寄生 RC 值 |
| **STA** | Static Timing Analysis | 静态时序分析 |
| **SVA** | SystemVerilog Assertions | SystemVerilog 断言，用于形式验证和动态验证 |
| **TNS** | Total Negative Slack | 总负余量 |
| **VHDL** | VHSIC Hardware Description Language | 另一种主流 HDL，欧洲和军工领域常用 |
| **VLSI** | Very Large Scale Integration | 超大规模集成电路 |
| **WNS** | Worst Negative Slack | 最差负余量 |
| **XOR** | Exclusive OR | 异或门 |

---

## 9. 与芯片流程的关系

### 9.1 在全流程中的位置

CFM 不改变芯片设计的物理流程（①-⑰），而是在流程的**各个节点上提供智能辅助**：

```
芯片设计流程                     CFM 的嵌入位置
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
① RTL 设计           ← Decoder: 自动生成 RTL (RTLCoder, MAGE)
                              Encoder: RTL 特征提取 (SNS v2)
② RTL 功能仿真        ← Decoder: testbench/断言生成
③ 逻辑综合            ← Encoder: AIG 编码 + QoR 预测 (DeepGate)
                              Decoder: 综合脚本生成 (ChatEDA)
④ 门级仿真            ← Encoder 的时序预测辅助分析
⑤ STA                ← Encoder: 路径延迟/时序 slack 预测
⑥ 形式验证            ← Encoder: SAT 辅助求解、功能推理
⑦ Floorplan          ← Encoder: 早期拥塞/面积预测
⑧ Placement          ← Encoder: 拥塞/线长/寄生预测 (TAG)
⑨ CTS                ← (CFM 空白区)
⑩ Routing            ← Encoder: routing congestion 预测
⑪ 后仿真             ← (间接，通过 PPA 预测指导)
⑫ DRC/LVS            ← Decoder: DRC 代码生成、热点检测
⑬ Signoff            ← Encoder: PPA 综合评估支撑签核决策
⑭ 流片               ← (间接)
⑮ 制造               ← Decoder: 缺陷检测 (FabGPT)
⑯ 封装测试            ← (CFM 未覆盖)
⑰ 芯片到手            ← —
```

**CFM 的核心价值**：在芯片设计流程中，CFM 扮演的角色是**早鸟预测器**和**自动生成器**。

- 作为早鸟预测器，CFM 在 EDA 工具跑完之前就给出 PPA/拥塞/IR drop 的估计，让设计者快速评估设计质量、做设计空间探索
- 作为自动生成器，CFM 从自然语言规格或高层描述直接生成 RTL/断言/脚本，减少人工编码的重复劳动

### 9.2 「CFM 能生成 RTL」和「能做成芯片」之间隔着什么

这一节拆解 CFM（尤其是 decoder-based RTL 生成）声称的 "成功" 距离真实流片还差哪些环节：

**1. 「pass@k 高」不等于「RTL 真的正确」**

VerilogEval 等 benchmark 的 pass@k 评估的是 **RTL 功能仿真的通过率**，这已经是 decoder-based CFM 能做的最好验证。但功能仿真通过只是万里长征第一步：

- 功能仿真只看 "testbench 覆盖到的输入组合" 下的逻辑正确性。但 testbench 覆盖率有限，真实芯片运行中会遇到无数 corner case
- 功能仿真不检查可综合性：有些看起来对的 Verilog 代码，综合工具会拒绝或产生意想不到的电路（如 latches 被意外推断）
- 功能仿真零延迟：不检查时序违例。一个 pass RTL simulation 的设计，可能在综合后因为关键路径过长而无法工作在目标频率

**2. 从 RTL 到 GDSII 的鸿沟**

即使 RTL 代码 "功能正确"，在变成真实芯片之前还需要经过：
- 逻辑综合（第③步）：可能产生功能等价但时序/面积/功耗很差的门级网表
- 门级仿真（第④步）+ STA（第⑤步）：发现 setup/hold 违例
- 形式验证（第⑥步）：证明 RTL 和网表等价（综合可能改错逻辑）
- 后端物理实现（⑦-⑩步）：可能发现 routing congestion、IR drop 等问题需要改 RTL
- 物理验证（⑫步）：DRC/LVS 通过是制造的前提

Decoder-based CFM 目前**完全不考虑这些物理约束**。生成的 RTL 可能在功能上通过仿真，但综合后的 PPA 可能无法接受。

**3. CFM 的 "验证循环" 远不完整**

ChipSeek 等用 EDA 工具反馈做 RLHF 对齐的工作，是朝正确方向迈出的一步。但目前的 EDA 反馈只包括：
- 语法检查（能否编译通过）
- 功能仿真（能否通过 testbench）

距离完整的 chip-level 验证还有：综合可行性、STA 签核、形式等价验证、物理验证。这些验证工具的调用成本极高（单个综合可能需要数小时到数天），难以用于 RL 的密集 reward 收集。

**结论**：CFM（尤其是 decoder-based RTL 生成）目前解决的只是 "写 RTL 代码" 这一步的自动化。它不能替代后续的设计流程，也不能保证生成的 RTL 能最终变成工作芯片。论文作者对此认识非常清醒——Section 6 的四条挑战本质就是在说：CFM 距离真正的 "端到端芯片设计自动化" 还有很长的路要走。

---

## 10. 讨论与局限

### 10.1 论文自述的局限

论文在 Section 6 中坦诚讨论了四大挑战，这些都是作者自己指出的局限：

1. **模型泛化性与可扩展性不足**：Encoder 难以同时支持结构预测和语义推理，Decoder 易产生幻觉（hallucination）和语法错误，当前模型难以处理工业级大规模电路（百万门级以上）。

2. **电路数据稀缺**：公开数据少、工业数据私有、标注昂贵。合成数据（SynCircuit, SynC-LLM）虽然是一种缓解，但 "the global functional behavior of the synthesized designs is only weakly controlled"（合成电路的功能行为只能弱控制）。

3. **Encoder-Decoder 鸿沟**：两类模型长期独立发展、能力未互补。虽然 GenEDA 展示了桥接的可能性，但目前仍是孤例。

4. **缺乏统一评估标准**：除 RTL 生成的 VerilogEval 外，encoder-based 和多数 decoder 任务的评估协议远未统一，无法公平比较、无法追踪进展。

论文还坦诚说明了自己覆盖范围的局限：
- 3 页以下的短论文（late-breaking results）未被覆盖
- 同一工作的多个版本避免了重复引用
- 由于这是一个快速发展的领域，发表后必然会有新的 CFM 工作出现

### 10.2 代码/复现层面的问题

作为综述论文，本文本身不涉及代码复现。但它指出的 CFM 领域的共性复现问题包括：

- **Encoder 的训练门槛高**：需要大规模电路图数据（数千到数万），自监督预训练设计复杂（GNN 架构 + 预训练目标 + 超参搜索），没有 "标准 recipe"
- **Decoder 依赖闭源 LLM**：很多 decoder 工作使用 GPT-4 / GPT-3.5 等闭源模型，无法完全复现（API 版本更替会改变结果）
- **工业设计的不可复现性**：涉及 industrial designs 的工作（如 ChipNeMo, TAG 的 AMS 电路）因数据专有而无法公开复现
- **Benchmark 碎片化**：每个团队用不同版本的 benchmark（如 VerilogEval v1 vs v2），增加了对比难度

### 10.3 本资料包的批判性分析

**1. 分类的完备性与边界模糊问题**

论文的 Encoder vs Decoder 二分法非常清晰，但也存在边界模糊的情况：

- **ChipNeMo**：既有 encoder（领域 adapt 的 BERT），又有 decoder（领域 adapt 的 Llama），论文将其归入 decoder 范畴
- **TAG**：使用文本+图多模态，既有 encoder 的 "表征学习" 成分，又用了 LLM 做文本编码，边界模糊
- **多模态融合的 encoder**（ProgSG, CircuitFusion）：它们用 LLM 做文本编码，这算 encoder 还是 decoder？

这暗示了一个更深层的问题：随着领域发展，Encoder 和 Decoder 的界限可能越来越模糊（论文自己也预言了 encoder-decoder 桥接是未来方向）。

**2. 「CFM」概念的界定争议**

论文对 CFM 的 operational definition 是："pre-trained on circuit-related data and intended to support multiple circuit/EDA tasks"。但某些工作可能只满足其中一个条件：
- 只做 prompt engineering（MAGE）的 decoder 工作：模型本身是通用 LLM，没有在 circuit data 上预训练。论文通过 "the LLM itself is a foundation model" 的逻辑将其纳入 CFM
- 某些 encoder 工作只在一个下游任务上验证（如 Design2Vec 只在功能验证覆盖预测上验证），"multiple tasks" 的含义可以被质疑

**3. 综述的 "代表性偏差"**

论文覆盖了 160+ 篇工作，但其中大量（111+ 篇）是 decoder 工作。Encoder 只有 21 篇。这可能不是论文的偏向，而是领域现状的如实反映。但这意味着：
- 综述对 encoder 方法的分析深度远高于 decoder（每篇 encoder 有详细的技术剖析，而 decoder 工作多数只能列表概括）
- 读者如果只看 Table 3/4/5-13 的 decoder 列表，会得到 "用 LLM 做 EDA 就是调一下 prompt 或 SFT" 的肤浅印象，但实际上 decoder 方向正在快速深化（RLHF、RAG、multi-agent）

**4. 评估框架的 "可操作性" 问题**

论文反复强调 "统一评估标准缺失" 是其核心挑战之一，但没有提出具体的评估框架建议。作为综述，指出问题已经足够，但作为该领域未来的路线图，这留了一个空白。

---

## 11. 复现信息

| 项目 | 内容 |
|------|------|
| 论文页 | [arXiv:2504.03711v2](https://arxiv.org/abs/2504.03711v2) |
| 代码 | 未开源（综述论文，无代码） |
| 数据集 | 无（综述论文，不涉及数据集发布） |
| 本地状态 | 已归档（txt 原文 + 标准化总结 + 详细总结 + 本文） |
| 复现等级 | N/A（综述论文，不需要复现） |
| 主要门槛 | N/A |

> 说明：本文是综述论文，本身不需要复现。但它引用的 160+ 篇工作中，部分已开源代码（如 DeepGate 系列 [GitHub](https://github.com/DeepGate)、CircuitFusion、RTLCoder、VerilogEval 等），可到各自原始论文获取代码和数据集。

---

## 12. 一分钟复述版

1. **背景**：这篇综述发表于 ACM TODAES 2026，由 HKUST 团队撰写，是截至 2026 年最全面的 Circuit Foundation Model 综述，覆盖 160+ 篇工作。

2. **核心概念**：论文提出 CFM = "预训练 + 微调" 的电路 AI 模型，与传统的 Type I（任务特定监督学习）形成对照。CFM 的核心优势是泛化性、数据效率、生成能力。

3. **二分法**：全部 CFM 分为 Encoder-based（预测型，21 篇）和 Decoder-based（生成型，111+ 篇）。前者用 GNN 编码电路图，做 PPA/功能预测；后者复用 LLM，做 RTL/断言/脚本生成。

4. **电路数据属性**：论文独特地从数据属性出发解释 CFM 设计——跨阶段等价性驱动对比学习，多模态格式驱动融合架构，数据稀缺驱动自监督预训练和合成数据。

5. **Encoder 预训练策略**：四类——对比学习（FGNN, SNS v2）、掩码重建（NetTAG, LLM-HD）、监督预训练（DeepGate 系列）、多模态融合（CircuitFusion, ProgSG）。Netlist 阶段（AIG 编码）是最活跃的子领域。

6. **Decoder 适配策略**：五类——prompt engineering（MAGE）、SFT（RTLCoder, OriGen）、LoRA（ChipNeMo）、RAG（ChIRAAG）、RLHF/DPO（ChipSeek）。RTL 代码生成是最大应用领域。

7. **数量不平衡**：Decoder 远超 Encoder（约 5:1），因为 encoder 需要从零构建 GNN 和预训练任务，门槛高得多。这种不平衡反映了领域发展初期的结构性特征。

8. **四大挑战**：泛化性/可扩展性不足、电路数据稀缺、Encoder-Decoder 各自为战缺少桥接、缺乏统一评估标准（除 RTL 生成外）。

9. **未来方向**：GenEDA（encoder-decoder 桥接）、合成数据（SynCircuit, SynC-LLM）、闭环优化 CFM（RL+搜索）、Agentic CFM（从被动模型到主动决策智能体）。

10. **实际定位**：CFM 目前解决的是 "设计辅助" 问题，不是 "替代工程师"。Decoder 生成的 RTL 能通过仿真，但距 "能做成芯片" 还隔着综合、STA、物理验证等多道关卡。论文作者对此非常坦诚——Section 6 的四条挑战本质上就是在承认：CFM 距离端到端芯片设计自动化还有长路。
