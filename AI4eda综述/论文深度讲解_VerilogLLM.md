# LLM for Verilog Code Generation 综述 论文深度讲解

> **Large Language Model for Verilog Code Generation: Literature Review and the Road Ahead**
> Guang Yang, Wei Zheng*, Dong Liang, Peng Hu, Yukui Yang, Shaohang Peng, Zhenghan Li, Jiahui Feng, Xiao Wei, Kexin Sun, Deyuan Ma, Haotian Cheng, Yiheng Shen, Xiang Chen, Xing Hu*, Terry Yue Zhuo, David Lo
> **机构**：Zhejiang University & Northwestern Polytechnical University (NWPU), Nantong University, Monash University, Singapore Management University (SMU)
> **期刊**：ACM Computing Surveys (ACM Comput. Surv.), Vol. 1, No. 1, December 2025
> **arXiv**：2512.00020v2 [cs.AR]（2024年12月24日），35 页
> **类型**：系统文献综述（SLR, Systematic Literature Review）
> **原文**：[2512.00020v2.txt](./2512.00020v2.txt)

---

## 1. 一句话定位

**首个专门聚焦于 LLM 辅助 Verilog 代码生成的系统文献综述，采用 Quasi-Gold Standard (QGS) 策略从 6 大数据库筛选出 102 篇论文（70 篇同行评审 + 32 篇高质量预印本），覆盖 2020-2025 年，系统回答了「用了哪些 LLM」「数据集和指标如何构建」「生成与优化技术如何分类」「对齐方法有哪些」四个核心研究问题（RQ1-RQ4），并提出从「夯实基础 → 扩展能力 → 优化部署」的三阶段研究路线图。**

这句话里的关键承重点，后面逐一拆解：

1. **系统性（SLR + QGS）** — 首次在 Verilog 代码生成领域采用系统文献综述方法。手工搜索 8 个顶会/顶刊（AAAI、ACL、ICML、ICLR、NeurIPS、DAC、TCAD）作为 QGS 种子，对 6 大数据库（IEEE Xplore、ACM DL、arXiv 等）进行自动检索，经三阶段过滤（5172 → 687 → 124）加前后向雪球（186 → 15），最终收录 102 篇，且每篇经 QAC 质量评分（0-15 分，阈值 12 分）。这一方法学上的严谨性远超一般「叙述性综述」。

2. **四维分类体系** — RQ1 将 LLM 分为 Base LLM（直接使用）与 Instruction-Tuned LLM（34 个 Verilog 专用模型，19 个开源权重）；RQ2 梳理了 27 个 benchmark 和 34 个 instruct-tuning dataset 的构建与质量保障策略；RQ3 将技术分为 Training-free（EDA 工具反馈、提示工程、推理优化）与 Training-based（预训练、SFT、RL）两条主线；RQ4 首次将安全、PPA 效率、版权、幻觉四个对齐维度进行系统化分析。

3. **三阶段路线图** — 不是简单的「未来展望」列表，而是有逻辑递进关系的工程路径：Stage 1 夯实基础（硬件感知模型、千级规模 benchmark）→ Stage 2 扩展能力（系统级分层生成、多模态输入）→ Stage 3 优化部署（EDA 反馈闭环 RL、Human-AI 协同 IDE 工具）。每个阶段有明确的技术目标和验收标准。

---

## 2. EDA 阶段映射（①-⑰）

这节回答：综述覆盖了芯片设计全流程的哪些阶段，哪些在讨论范围内，哪些完全不涉及。

| 阶段 | 覆盖 | 说明 |
|------|:---:|------|
| **① RTL 设计** | ✅ **核心** | 综述的全部 102 篇论文都聚焦于自然语言规格 → Verilog RTL 代码的生成任务 |
| **② RTL 功能仿真** | ✅ **强相关** | 大量工作通过 testbench 执行 functional-pass@k 评估；部分工作生成 testbench、SVA 断言、波形图作为辅助输出 |
| **③ 逻辑综合** | 🔶 **部分涉及** | VeriOpt、AutoSilicon、LLM-VeriPPA 等将 Synopsys Design Compiler / Yosys 综合反馈纳入闭环，评估 PPA 和可综合性；大多数工作未涉及 |
| ④ 门级仿真 | ❌ | 综述讨论范围的论文基本不涉及门级仿真和 SDF 反标 |
| ⑤ STA（静态时序分析） | ❌ | 时序约束讨论停留在「设计意图」层面，不涉及 PrimeTime/Tempus 实际 STA 流程 |
| ⑥ 形式验证 | 🔶 **部分涉及** | 约 10+ 篇论文使用 Yosys `-equiv` 进行 RTL ↔ 网表等价性检查；作为功能正确性验证手段，非签核级形式验证 |
| ⑦ 布局规划 (Floorplan) | ❌ | 综述范围内的论文不涉及后端物理设计 |
| ⑧ 标准单元摆放 (Placement) | ❌ | 同上 |
| ⑨ 时钟树综合 (CTS) | ❌ | 同上 |
| ⑩ 布线 (Routing) | ❌ | 同上 |
| ⑪ 后仿真 | ❌ | 不涉及 SPEF 寄生参数提取后的仿真 |
| ⑫ 物理验证 (DRC + LVS) | ❌ | 不涉及 |
| ⑬ 签核 (Signoff) | ❌ | 不涉及 |
| ⑭ 流片 | ❌ | 不涉及 |
| ⑮ 制造 | ❌ | 不涉及 |
| ⑯ 封装 + 测试 | ❌ | 不涉及 |
| ⑰ 芯片到手 | ❌ | 不涉及 |

**覆盖率：2/17（核心覆盖），3/17（含部分涉及）。**

这篇综述停留在 **EDA 前端设计 + 验证** 的交界处。它的讨论边界非常清晰：给定自然语言规格，生成 Verilog RTL 代码，并通过仿真验证功能正确性。它不涉及逻辑综合之后的任何物理设计阶段。

> **关键边界**：综述讨论的「成功」标准是「生成的 Verilog 通过 testbench 仿真」。从「仿真通过」到「能做成芯片」之间隔着：逻辑综合（代码能否映射到标准单元库）、STA（时序是否闭合）、形式验证（网表和 RTL 是否逻辑等价）、物理设计（能否布线）、DRC/LVS（能否制造）。综述在 limitations 中明确指出了这个 gap——这是实事求是的，因为综述本身不提出新方法，只是对现有文献的系统化整理。

---

## 3. 综述的分类体系（taxonomy）

这节是整篇综述的骨架。综述的组织结构本身就是一个四维分类体系，对应 Figure 1（Survey Structure）中的四大模块。

### 3.1 分类维度总览

综述将该领域的工作沿着四个正交维度进行系统分类：

```
                    ┌─────────────────────────────────────┐
                    │     LLM for Verilog Code Generation    │
                    │         102 篇文献 (2020-2025)         │
                    └─────────────────────────────────────┘
                                     │
          ┌──────────────┬───────────┼────────────┬──────────────┐
          ▼              ▼           ▼            ▼              ▼
     ┌─────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐
     │  RQ1    │  │   RQ2    │  │   RQ3    │  │   RQ4    │
     │ LLM 模型 │  │数据集/指标│  │ 生成技术  │  │ 对齐方法  │
     └─────────┘  └──────────┘  └──────────┘  └──────────┘
          │              │            │              │
    ┌─────┴─────┐  ┌────┴────┐  ┌──┴──────┐  ┌────┴────────┐
    │Base LLM   │  │Benchmark│  │Training-│  │Security      │
    │- 开源 204次│  │- 开放 18个│  │free      │  │Efficiency    │
    │- 闭源 179次│  │- 封闭 9个│  │- EDA反馈  │  │Copyright     │
    │IT LLM     │  │Instruct- │  │- 提示工程 │  │Hallucinations│
    │- 开源 19个 │  │Tuning    │  │- 推理优化 │  └─────────────┘
    │- 闭源 15个 │  │- 开放 22个│  │Training-  │
    └───────────┘  │- 封闭 12个│  │based      │
                   │Metrics   │  │- 预训练   │
                   │- 相似度   │  │- SFT      │
                   │- 执行    │  │- RL       │
                   │- LLM裁判 │  └───────────┘
                   └──────────┘
```

### 3.2 RQ1 分类详解：LLM 模型

综述将使用的模型分为两大类：

**Base LLM（直接使用/作为 baseline）**：共 383 次使用
- 开源（204 次，53.3%）：Llama 系列 64 次（CodeLlama、Llama3.x）、DeepSeek 系列 54 次（DeepSeek-Coder、DeepSeek-R1）、Qwen 系列 28 次（CodeQwen、Qwen2.5-Coder）、CodeGen 12 次、StarCoder 11 次、其他 35 次
- 闭源（179 次，46.7%）：GPT 系列 149 次（占闭源的 83.2%）、Claude 系列 19 次、Gemini 5 次、其他 6 次

**Instruction-Tuned (IT) LLM（Verilog 专用微调模型）**：共 34 个
- 开源权重（19 个，55.9%）：DAVE、ChipGPT、CodeV、CodeV-R1、GEMMV、Hardware Phi-1.5B、HAVEN、MG-Verilog、Mistral-Verilog、OriGen、ReasoningV、RTLCoder、VeriCoder、VeriGen、VeriLogos、VeriPrefer、VeriReason、VeriSeek、VeriThoughts
- 闭源权重（15 个，44.1%）：AutoVCoder、BetterV、CodeGen-Verilog、CraftRTL、DeepRTL、DeepRTL2、FreeV、ITERTL、MEV-LLM、OpenRTLSet、PyraNet、RTL++、RTLRepoCoder、ScaleRTL、Veritas

**关键趋势**：82.4% 的 IT LLM（28/34）基于代码专用基础模型构建，三大集群为 DeepSeek-Coder（11 个占 32.4%）、Qwen coder 系列（9 个占 26.5%）和 CodeLlama 衍生（8 个占 23.5%）。2025 年出现明显的「R1 风格」推理模型迁移趋势（CodeV-R1、ReasoningV、VeriReason、VeriThoughts）。

### 3.3 RQ2 分类详解：数据集与评估

**Benchmark 数据集（27 个）**：按构建方式分为四类
- 模板合成（Template Synthesis）：DAVE 等，结构化模板参数化生成
- 挖掘软件仓库（Mining Repos）：VerilogEval-v1/v2（来自 HDLBits）、AutoChip 等
- 专家策划（Expert Curation）：RTLLM-v1/v2、RealBench、ArchXBench 等
- 混合方法（Hybrid）：AutoSilicon、GenBen、VeriThoughts 等

关键数据：18 个开放 benchmark 中，16 个提供 testbench（88.9%），说明可执行验证已成为评估标准。

**Instruct-Tuning 数据集（34 个）**：按数据来源分三类
- 挖掘软件仓库：VeriGen_train（109k）、VerilogDB 等
- LLM 合成：RTLCoder（27k+）、CraftRTL（80k）、ScaleRTL 等
- 混合方法：VerilogEval_train（8.5k）、AutoVCoder-Data（100k）等

**评估指标三类**：
- 相似度指标：BLEU、CodeBLEU、SimEval（PyVerilog AST + Verilator CFG + Yosys 网表三层多视图相似度）
- 执行指标：syntax-pass@k、functional-pass@k、形式等价检查
- LLM 裁判指标：GPT Score、VCD-RNK、MetRex

### 3.4 RQ3 分类详解：生成与优化技术

```
训练无关方法（Training-free）
├── EDA 工具反馈
│   ├── 单 Agent 系统（RTLFixer, VeriPPA, EvoVerilog, VGV）
│   └── 多 Agent 系统（MAGE 4 agents, VerilogCoder 3 agents, RTLSquad, VFlow, AutoSilicon）
├── 提示工程
│   ├── 层次化提示（ChatModel, HiVeGen, AoT）
│   └── RAG 增强（VeriRAG, HDLCoRe）
└── 推理优化
    ├── 语法感知解码（DecoRTL 温度缩放）
    └── 自一致性重排序（VRank, VCD-RNK）

训练方法（Training-based）
├── 预训练
│   ├── 从头训练（Hardware Phi-1.5B）
│   └── 继续预训练（FreeV + LoRA）
├── 监督微调（SFT）
│   ├── 数据中心（DAVE, VeriGen, RTLCoder）
│   ├── 策略中心（MEV-LLM 复杂度感知, AutoVCoder 课程学习）
│   ├── 多任务（BetterV 生成-判别双任务, ITERTL 排名损失）
│   └── 知识增强（RTL++ 注入 CFG/DFG, CodeV-R1 推理蒸馏）
└── 强化学习
    ├── 结构奖励（VeriSeek PPO + AST 相似度, VeriReason GRPO）
    ├── 工具反馈（VeriLogos 形式等价, CodeV-R1 DAPO）
    └── 多目标优化（MCTS-guided PPA 优化）
```

### 3.5 RQ4 分类详解：对齐方法

四个对齐维度，每个维度下都有当前方法和挑战分析：

| 对齐维度 | 核心问题 | 代表方法 | 当前成熟度 |
|---------|---------|---------|:---:|
| 安全 (Security) | 漏洞/硬件木马/数据投毒 | SecFSM (CWE 知识图谱), SALAD (机器反学习) | 早期 |
| 效率 (Efficiency) | PPA 优化/物理感知 | VeriOpt (in-context learning), HiVeGen (层次分解) | 中期 |
| 版权 (Copyright) | IP 保护/侵权预防 | RTLMarker (水印), FreeV (数据集过滤) | 早期 |
| 幻觉 (Hallucination) | 语法对但功能错 | HAVEN (三步流水线), DecoRTL (解码约束) | 中期 |

---

## 4. 方法与架构

这节回答：综述作为一个研究活动，其「方法」是什么——即它是如何产生这篇综述本身的，而非综述中讨论的被调查论文的方法。

### 4.1 综述方法论整体 Pipeline

```
手工搜索 8 个顶会/顶刊                         自动化搜索 6 大数据库
(AAAI, ACL, ICML, ICLR,           +          (IEEE Xplore, ACM DL, arXiv,
 NeurIPS, DAC, TCAD)                           ScienceDirect, SpringerLink, WoS)
        │                                               │
        ├─────────── 识别 16 篇种子论文 ─────────────────┤
        │            (Quasi-Gold Standard)                │
        ▼                                               ▼
  ┌─────────────────────────────────────────────────────────┐
  │  Stage 1: 初始筛选                                       │
  │  排除：短论文(<5页) + 重复 → 5172 篇                       │
  ├─────────────────────────────────────────────────────────┤
  │  Stage 2: 基于内容的筛选                                   │
  │  手工审查 venue/title/abstract → 687 篇                    │
  ├─────────────────────────────────────────────────────────┤
  │  Stage 3: 全文评估                                       │
  │  排除：只修不生成 / 缺实现 / 非LLM → 124 篇                  │
  ├─────────────────────────────────────────────────────────┤
  │  质量评估 (QAC, 0-15分, 阈值 ≥12)                            │
  │  QAC1: 顶会/顶刊?  QAC2: 学术贡献?  QAC3: 方法清晰?         │
  │  QAC4: 实验完整?    QAC5: 结论有据?                          │
  │  → 55 篇同行评审 + 30 篇预印本 = 85 篇                       │
  ├─────────────────────────────────────────────────────────┤
  │  前后向雪球 (Snowballing)                                 │
  │  追踪 85 篇的引文和被引 → 186 篇候选 → 15 篇补充             │
  │  → 最终：70 篇同行评审 + 32 篇预印本 = 102 篇                │
  └─────────────────────────────────────────────────────────┘
        │
        ▼
  ┌─────────────────────────────────────────────────────────┐
  │  数据提取与四维分析                                        │
  │  RQ1: LLM 使用统计 (383 次使用, 34 个 IT LLM)             │
  │  RQ2: 27 benchmark + 34 instruct-tuning dataset         │
  │  RQ3: Training-free vs Training-based 完整分类            │
  │  RQ4: Security/Efficiency/Copyright/Hallucinations     │
  └─────────────────────────────────────────────────────────┘
        │
        ▼
  结论：4 大局限 + 三阶段路线图 + 10 项关键发现
```

### 4.2 核心模块详解

**模块 1：QGS 种子论文识别**。手工从 8 个 AI/EDA 顶会（AAAI、ACL、ICML、ICLR、NeurIPS、DAC、TCAD）中系统检索将 LLM 应用于 Verilog 生成的论文，共获得 16 篇（14 篇会议 + 2 篇期刊）。这 16 篇是后续自动搜索策略的校准基准——用于验证搜索词的覆盖度与精确度。

**模块 2：自动搜索策略**。设计双向关键词组合（AND 逻辑）：
- Verilog 侧（12 个词）：Verilog, HDL, Hardware Description Language, RTL, Register Transfer Level, Digital Design, Hardware Design, Electronic Design Automation, EDA, Verilog Generation, FPGA, ASIC
- LLM 侧（13 个词）：LLM, Large Language Model, Language Model, GPT, ChatGPT, Transformer, fine-tuning, prompt engineering, In-context learning, Natural Language Processing, NLP, Machine Learning, AI

**模块 3：三阶段过滤**。不是一次性过滤，而是递进的：Stage 1 纯机械化（去除短文章和重复）→ Stage 2 人工审 venue/标题/摘要 → Stage 3 全文精读。这种分阶段设计减少了遗漏的风险：短文章可能被 Stage 1 误杀（但 < 5 页的论文确实难以包含足够的方法细节和实验），无 LLM 的论文不会浪费 Stage 3 的审稿精力。

**模块 4：质量评估（QAC）**。五维 Likert 量表（0-3 分），总分 15 分，阈值 12 分（80%）。对于预印本（QAC1 自动 0 分），需要在其他四个维度普遍拿到 3 分才能达标。这保证了即使是最新的 arXiv 成果也经过了严格质量审查。

**模块 5：前后向雪球**。前向雪球（查哪些后来论文引用了种子论文）+ 后向雪球（查种子论文引用了哪些更早的论文）。这一步骤从已录取的 85 篇出发，发现了 15 篇被初始搜索遗漏的相关论文。最终 102 篇的构成：85（QAC 筛选）+ 15（雪球）+ 2（QAC 筛选和雪球重叠? 原文未完全区分）。

### 4.3 方法论特点

| 维度 | 做法 | 与其他综述的差异 |
|------|------|----------------|
| 搜索策略 | 手工+自动+雪球 | QGS 策略保证搜索词经实验验证（16 篇种子） |
| 质量控制 | 五维 QAC，12/15 阈值 | 多数综述只用 inclusion/exclusion criteria，不加分数量化 |
| 预印本处理 | 纳入但需 QAC 高分 | 很多综述直接排除 arXiv 论文 |
| 分析框架 | 四 RQ 按维度正交分解 | 组织清晰、可复现 |

---

## 5. 综述提出的分类维度与判据

这节回答：综述的「贡献」是什么——它不是一篇提出新方法的论文，而是提出了一套为后续研究提供导航的分类维度和判据。

### 5.1 判据 1：LLM 分类体系（RQ1）

综述将用于 Verilog 生成的 LLM 组织为两个正交维度：

- **维度 1：Base LLM vs IT LLM**。Base LLM 是通用模型直接使用（383 次总使用，是绝对主流），IT LLM 是经过 Verilog 专用指令微调的模型（34 个，其中 19 个开源）。判据：是否进行 Verilog 专用微调。

- **维度 2：开源 vs 闭源**。开源模型 204 次使用（53.3%），闭源 179 次（46.7%）。判据：模型权重是否公开可获取。

这个分类的价值在于：它直接对应实践者的选择路径——做 baseline 对比选 GPT-4/Claude（闭源最强），做微调研究选 DeepSeek-Coder/Qwen2.5-Coder（开源可定制）。

### 5.2 判据 2：数据集分类维度（RQ2）

综述为数据集设计了两个分类面：

**Benchmark 数据集四类构建方式**：
1. 模板合成 — 参数化生成，质量可控，但缺乏真实场景的多样性
2. 挖掘软件仓库 — 从 HDLBits/GitHub/OpenCores 提取，覆盖广但质量参差
3. 专家策划 — 领域专家手工设计，质量最高但成本大
4. 混合方法 — 开源挖掘 + 专家精炼 + LLM 合成

判据：数据来源和人工参与程度。实践中通常混合使用——例如 VerilogEval 从 HDLBits 挖掘题目（类 2），再请专家撰写规范（类 3）。

**Instruct-Tuning 数据集三类来源**：
1. 挖掘软件仓库 — 真实性保证，但需要大量预处理
2. LLM 合成 — 可扩展性好，但可能缺乏真实 RTL 的多样性
3. 混合方法 — 社区代码 + LLM 增强描述

判据：数据生成过程中 LLM 参与的程度。纯挖掘（类 1）保证真实性但量有限，纯合成（类 2）量大但有质量风险，混合（类 3）是当前主流。

### 5.3 判据 3：技术路线分类维度（RQ3）

综述将 102 篇论文的技术路线分为两条大分支，每条分支下有明确的子分类判据：

**Training-free 分支判据**：是否修改模型参数？
- EDA 工具反馈：用编译/仿真/综合结果指导修复（判据：反馈信号的确定性程度）
- 提示工程：改 prompt 不改模型（判据：提示中嵌入的结构化信息量）
- 推理优化：改采样/解码策略不改模型（判据：是否改变了 token 概率分布）

**Training-based 分支判据**：训练的目标和奖励来源是什么？
- 预训练：从零训练 vs 继续预训练（判据：是否使用已有 checkpoint 初始化）
- SFT：数据中心（改数据）vs 策略中心（改训练流程）vs 多任务（改损失函数）vs 知识增强（注入结构信息）
- RL：结构奖励（AST 相似度）vs 工具反馈（testbench/等价检查）vs 多目标（PPA 综合奖励）

### 5.4 判据 4：对齐维度分类（RQ4）

综述首次将 Verilog 生成中的对齐问题系统化为四个正交维度，每个维度有明确的判据：

| 维度 | 判据 | 评估手段 |
|------|------|---------|
| 安全 | 无漏洞/无木马 | CWE 知识图谱覆盖、SALAD 反学习效果 |
| 效率 | PPA 达标 | 综合后功耗(mW)/频率(MHz)/面积(um²) |
| 版权 | IP 不侵权/可溯源 | 水印鲁棒性（综合后存活率）、侵权检测精度 |
| 幻觉 | 编译通过但功能错误 | 仿真 mismatch 率、形式等价检查结果 |

### 5.5 综述中的一个关键评估概念：Pass@k

虽然这是被综述论文中使用的指标而非综述本身的发明，但综述对该指标的讨论值得单独列出。Pass@k 是当前 Verilog 生成评估中最核心的指标，源自 Codex 论文（Chen et al. 2021）：

$$
\text{Pass}@k = \mathbb{E}_{\text{Problems}} \left[ 1 - \frac{\binom{n-c}{k}}{\binom{n}{k}} \right]
$$

其中：
- $n$：每个问题的总采样数
- $c$：$n$ 个样本中通过 testbench 的正确样本数
- $k$：允许尝试的提交次数
- $\binom{n}{k}$：组合数，表示从 $n$ 个样本中选 $k$ 个的方式数

**工程直觉**：Pass@k 衡量的是「允许你提交 $k$ 个候选，只要有一个对就算对」的概率。公式中的 $\frac{\binom{n-c}{k}}{\binom{n}{k}}$ 是「$k$ 个全错」的概率，$1$ 减去它就是「至少有一个对」的概率。这个公式是一个无偏估计量（unbiased estimator），避免了直接用「$n$ 个里面 $c$ 个对，$k$ 次尝试都有 $c/n$ 概率对」的朴素估计的偏差。

综述特别指出：Pass@k 的无偏估计要求 $n \geq 20$ 才稳定，因为组合数在样本量小时方差大。

**为什么 Pass@k 比 BLEU 好**：在 Verilog 代码中，两个功能完全等价的实现可以有不同的语法结构（例如 always@(*) vs assign，阻塞赋值 vs 非阻塞赋值的不同组织方式）。BLEU 会惩罚这些「语法不同但功能等价」的实现，而 Pass@k 只看最终功能是否正确。

---

## 6. 训练与实验设置

这节回答：作为一个综述研究，「训练与实验」指的是综述中统计和比较被调查论文时采用的「元分析」设置，而不是综述本身的训练（综述不需要训练）。

### 6.1 综述本身是否需要训练

不需要。这是一篇文献综述（SLR），其研究方法是信息检索、文献筛选、质量评估和数据提取。不涉及任何模型训练。

### 6.2 论文学术背景：被调查论文中的主要实验范式

虽然综述本身不训练模型，但它总结了被调查论文的实验设置，以下是关键统计：

- **评估基准**：VerilogEval-v1 是最广泛使用的 benchmark（156 个人工题目 + 148 个机器生成题目），RTLLM-v1/v2 是第二常用的（30/50 个题目，三层难度分级）
- **核心指标**：functional-pass@k 已成为事实上的标准正确性指标，18 个开放 benchmark 中 16 个提供 testbench
- **基线模型**：GPT-4 和 GPT-3.5 是最常用的闭源 baseline，CodeLlama 和 DeepSeek-Coder 是最常用的开源 baseline
- **n 的选择**：Pass@k 无偏估计要求 $n \geq 20$，但并非所有论文都遵守这一准则，综述指出评估标准化仍是突出问题

### 6.3 被调查论文的训练范式分类

综述系统化地总结了训练范式，这些本身就是综述的核心贡献之一：

**SFT 的共同配置**：
- 损失函数：标准 cross-entropy loss

$$
\mathcal{L}_{SFT} = -\sum_{(x,y) \in \mathcal{D}} \sum_{i=1}^{|y|} \log P(y_i | x, y_{<i}; \theta)
$$

- $\mathcal{D}$：指令-代码对数据集
- $x$：自然语言规格
- $y$：目标 Verilog 代码序列
- $\theta$：模型参数

- 参数高效方案：LoRA 是对资源受限学术环境最友好的选项

$$
W = W_0 + \Delta W = W_0 + BA
$$

其中 $B \in \mathbb{R}^{d \times r}$，$A \in \mathbb{R}^{r \times k}$，远小于全参数更新的计算量。

- QLoRA 更激进：4-bit 量化 + LoRA，可在消费级 GPU 上微调 7B+ 模型

**RL 的共同配置**：
- 策略优化目标：

$$
J(\theta) = \mathbb{E}_{x \sim p_{data}, y \sim \pi_{\theta}(\cdot | x)} [R(y, y^*)]
$$

- $x$：自然语言规格
- $y$：生成的 Verilog 代码
- $y^*$：参考实现
- $R(y, y^*)$：代码质量奖励

- DPO（Direct Preference Optimization）的损失函数（论文未给出编号，此为形式化表示）：

$$
\mathcal{L}_{DPO} = -\mathbb{E}[\log \sigma(\beta \log \frac{\pi_{\theta}(y^+ | x)}{\pi_{ref}(y^+ | x)} - \beta \log \frac{\pi_{\theta}(y^- | x)}{\pi_{ref}(y^- | x)})]
$$

- $y^+$：通过更多 testbench 的「好」代码
- $y^-$：通过较少 testbench 的「差」代码
- $\pi_{\theta}$：当前策略
- $\pi_{ref}$：参考策略
- $\beta$：温度参数，控制 KL 散度正则化的强度

### 6.4 综述统计出的关键增长数据

| 年份 | 论文数 | Base LLM 总使用次数 |
|------|:------:|:-------------------:|
| 2020 | 1 | — |
| 2021 | 0 | — |
| 2022 | 0 | — |
| 2023 | 6 | 12 |
| 2024 | 29 | 97 |
| 2025 (至 10 月) | 66 | 274（增长 2183%） |

这张表清楚地展示了该领域的指数级增长轨迹。2020 年仅有一篇先驱性工作（DAVE），2021-2022 年是休眠期，2023 年起爆发式增长。

---

## 7. 创新点

这篇文章的创新不在于「提出一个新模型/算法」，而在于它是首个对该领域进行系统化整理的文献综述，其创新性体现在方法论和知识组织两个层面。

### 创新点 1：首次针对 LLM-based Verilog 代码生成的系统文献综述

**关键区别**：以前的综述要么覆盖全 EDA 流程（如 Fang et al. 覆盖 Layout/Netlist/HDL/Assertion 等约 250 篇，He et al. 覆盖 EDA 生成/验证/调试 211 篇），要么覆盖通用代码生成（如 Jiang et al. 235 篇面向 Python/Java）。这些综述对 Verilog 只是「提及」或「一个子节」，缺乏系统性分析。

本综述的独特价值：
- 专门的搜索策略：25 个关键词的组合（12 个 Verilog 侧 + 13 个 LLM 侧），针对 Verilog 生成定制
- 深入的领域分析：不仅列出论文，还分析了 Verilog 特有的挑战（并发性、时序约束、可综合性、硬件专门知识）
- 形式化的任务定义：$f_{\theta}: (D, I) \rightarrow V$，其中 $D$ 是自然语言规格、$I$ 是可选多模态输入、$V$ 是生成的 Verilog

### 创新点 2：Quasi-Gold Standard (QGS) 方法论保证了系统性和全面性

**关键区别**：一般的综述（尤其是这个快速发展的领域）往往依赖作者的领域知识来挑选论文，这样容易遗漏相关工作。QGS 策略通过「种子论文 → 验证搜索词 → 系统检索」的流程，既保证了搜索词的有效性（经 16 篇种子论文验证），又保证了覆盖面（6 大数据库的自动检索）。

具体机制：
- 8 个顶会/顶刊的手工检索作为 ground truth 校准搜索策略
- 10+ 个关键词的双向组合防止遗漏
- 三阶段过滤（5172 → 687 → 124 → 85 → 102）保证了严格的筛选
- 五维 QAC 评分保证了每个入选论文的质量

### 创新点 3：对齐维度的首次系统化分析

**关键区别**：此前的综述最多讨论「安全性」「可靠性」等单一维度，本综述首次将 Verilog 生成中的对齐问题分解为四个正交维度，每个维度都有：

- 明确的问题定义（例如「安全」不等于软件安全，包括硬件木马、侧信道、数据投毒）
- 现有方法的分类（例如版权分为「所有权保护」和「侵权预防」两个子目标）
- 局限分析（例如当前水印技术面临「鲁棒性 vs 透明性」的 trade-off）
- 未来方向的建议（例如功能等价但语法不同的 IP 复制需要新的检测手段）

### 创新点 4：三阶段路线图——从学术原型到工业部署的系统路径

**关键区别**：很多综述的「未来方向」是不分优先级的愿望列表。本综述的路线图有明确的阶段划分和依赖关系：

- Stage 1（夯实基础）必须先完成，因为「如果没有硬件感知模型和可靠的 benchmark，后面的一切都建立在沙子上」
- Stage 2（扩展能力）依赖 Stage 1 的模型和 benchmark，解决系统级复杂度和多模态输入
- Stage 3（优化部署）依赖 Stage 2 的分层生成能力，才能实现 PPA/安全闭环 RL 和 Human-AI 协同

这种分阶段设计使得路线图具有可操作性——研究者可以据此确定自己工作在路线图上的位置，并知道下一步需要克服什么障碍。

---

## 8. EDA 缩写表

| 缩写 | 全称 | 一句话解释 |
|------|------|-----------|
| AIG | AND-Inverter Graph | 与-非图，逻辑综合的标准中间表示，只有 2 输入 AND 和取反边 |
| ASIC | Application-Specific Integrated Circuit | 专用集成电路，针对特定应用定制的芯片 |
| AST | Abstract Syntax Tree | 抽象语法树，代码语法结构的树形表示，PyVerilog 用于提取 Verilog AST |
| CDFG | Control/Data Flow Graph | 控制/数据流图，表示代码的执行流程和数据依赖 |
| CFG | Control Flow Graph | 控制流图，表示程序执行路径的有向图 |
| DPI | Direct Programming Interface | Verilog/SystemVerilog 与 C 语言的直接编程接口 |
| DRC | Design Rule Check | 设计规则检查，验证版图是否符合工艺厂的制造规则 |
| EDA | Electronic Design Automation | 电子设计自动化，芯片设计的工业软件工具链 |
| FPGA | Field-Programmable Gate Array | 现场可编程门阵列，可反复编程的硬件平台 |
| FSM | Finite State Machine | 有限状态机，数字逻辑中描述状态转移的模型 |
| GDSII | Graphic Data System II | 芯片制造的最终版图文件格式 |
| HDL | Hardware Description Language | 硬件描述语言（Verilog、VHDL 等） |
| IP | Intellectual Property | 知识产权，在 EDA 中指可复用的设计模块 |
| LVS | Layout vs Schematic | 版图与原理图一致性检查 |
| MUX | Multiplexer | 多路选择器，根据选择信号输出多路输入之一 |
| PDK | Process Design Kit | 工艺设计套件，包含特定工艺的标准单元库和设计规则 |
| PPA | Power, Performance, Area | 功耗、性能、面积——芯片设计的三大优化目标 |
| RTL | Register Transfer Level | 寄存器传输级，用寄存器间数据传输描述电路行为的抽象层次 |
| SDF | Standard Delay Format | 标准延时格式，描述每个门的上升/下降延迟 |
| SDC | Synopsys Design Constraints | 设计约束文件，定义时钟频率、输入/输出延迟等时序约束 |
| SoC | System on Chip | 片上系统，集成处理器、存储器、外设等完整系统的单芯片 |
| SPEF | Standard Parasitic Exchange Format | 标准寄生参数交换格式，描述走线的寄生电阻/电容 |
| STA | Static Timing Analysis | 静态时序分析，不跑仿真纯数学计算所有路径延迟 |
| SVA | SystemVerilog Assertions | SystemVerilog 断言，用于形式验证和动态仿真中的属性检查 |
| VCD | Value Change Dump | 值变化记录，仿真波形的标准文件格式 |

ML/AI 相关缩写：

| 缩写 | 全称 | 一句话解释 |
|------|------|-----------|
| CoT | Chain-of-Thought | 思维链，让 LLM 逐步推理而非直接生成答案的提示策略 |
| CPT | Continued Pre-Training | 继续预训练，在通用预训练基础上用领域数据继续训练 |
| DPO | Direct Preference Optimization | 直接偏好优化，无需显式奖励模型的 RLHF 替代算法 |
| GRPO | Group Relative Policy Optimization | 群组相对策略优化，DeepSeek-R1 使用的 RL 算法 |
| IT | Instruction-Tuned | 指令微调，在(指令, 回答)对上微调模型以遵循指令 |
| LoRA | Low-Rank Adaptation | 低秩适配，参数高效微调方法，只更新低秩矩阵 |
| MCTS | Monte Carlo Tree Search | 蒙特卡洛树搜索，用于设计空间探索的搜索算法 |
| PPO | Proximal Policy Optimization | 近端策略优化，OpenAI 提出的 RL 算法 |
| QGS | Quasi-Gold Standard | 准金标准，系统文献综述中用手工筛选的论文作为搜索策略验证标准 |
| QLoRA | Quantized LoRA | 量化低秩适配，4-bit 量化 + LoRA，可在消费级 GPU 微调大模型 |
| RAG | Retrieval-Augmented Generation | 检索增强生成，从知识库检索相关文档辅助 LLM 生成 |
| RL | Reinforcement Learning | 强化学习，通过与环境交互获取奖励来优化策略 |
| RLHF | Reinforcement Learning from Human Feedback | 基于人类反馈的强化学习，用人类偏好训练奖励模型 |
| SFT | Supervised Fine-Tuning | 监督微调，在标注数据上用监督学习调整模型参数 |
| SLR | Systematic Literature Review | 系统文献综述，遵循严格方法论（规划→执行→分析）的综述形式 |

---

## 9. 与芯片流程的关系

### 9.1 在全流程中的位置

回到 17 阶段标准，这篇综述聚焦于**芯片设计的最前端**：

```
┌─────────────────────────────────────────────────────────────┐
│  综述覆盖范围（前端设计 + 验证）                                │
│                                                             │
│  [架构规格] → [① RTL 设计] ←→ [② 功能仿真]                     │
│                   ↑                    ↑                    │
│              综述核心              综述评估手段                │
│         102 篇论文的生成任务     functional-pass@k 评估       │
│                                                             │
├─────────────────────────────────────────────────────────────┤
│  综述未覆盖（中后端）                                          │
│                                                             │
│  [③ 逻辑综合] → [④ 门级仿真] → [⑤ STA] → [⑥ 形式验证]          │
│  → [⑦ Floorplan] → [⑧ Placement] → [⑨ CTS] → [⑩ Routing]   │
│  → [⑪ 后仿真] → [⑫ DRC+LVS] → [⑬ Signoff] → [⑭-⑰ 制造交付]  │
└─────────────────────────────────────────────────────────────┘
```

综述的定位：它是在分析「AI 如何帮助设计者写出 Verilog」这个具体问题上的所有现有研究。它不解决「Verilog 写出来之后怎么办」的问题——但它在 RQ3 和 RQ4 中讨论了那些试图将综合/仿真/形式验证反馈纳入 LLM 生成闭环的前沿工作（如 VeriOpt、AutoSilicon、CodeV-R1 等），这是连接前端生成和中后端实现的桥梁。

### 9.2 「仿真通过」和「能做成芯片」之间隔着什么

综述讨论的 102 篇论文中，绝大多数论文的「成功」标准是 testbench 仿真通过。从仿真通过到真正能流片，至少还需要：

1. **逻辑综合验证**（③）：Verilog 能否被 Design Compiler / Genus 综合成门级网表？testbench 通过但不可综合的代码在学术界并不少见——例如用了 `initial` 块、`$display`、不可综合的 `for` 循环等。

2. **时序闭合**（⑤ STA）：即使逻辑综合通过，门级网表的时序是否满足目标频率？RTL 仿真假设零延迟，但真实物理门有 ns 级延迟。

3. **形式等价**（⑥）：综合工具做了大量优化（资源共享、重定时、状态机重编码），综合后的网表和原始 RTL 在逻辑上是否等价？

4. **PPA 满足**：功耗、面积、性能是否符合设计约束？testbench 只验证功能，不管面积。

5. **物理设计**（⑦-⑩）：即使网表时序闭合，在芯片上实际布局布线后，走线延迟可能使得时序再次恶化。

综述在 limitations 部分（Section 8.1）明确指出了这个鸿沟：当前工作「在仿真层面演示的功能正确性」距离「工业芯片的签核标准」仍有很大距离。这是实事求是的，不是这篇综述的缺点，而是整个领域当前的状态。

---

## 10. 讨论与局限

### 10.1 论文自述的局限（Section 8.1 + Section 9）

综述作者在 Section 8.1 中系统承认了四大局限：

**局限 1：基础与知识鸿沟**。通用 LLM（即使是 GPT-4）缺乏对硬件并发性、时序约束、面积/功耗的「直觉」理解。自回归架构（逐 token 生成）对 Verilog 的并行语义建模天然困难——Verilog 中的 `always` 块是并行执行的，但 LLM 从左到右逐 token 生成，可能产生「仿真正确但综合失败」的代码。

**局限 2：数据与 benchmark 稀缺**。高质量 Verilog 数据远少于 Python/Java。现有 benchmark 规模普遍偏小（多数 < 100 个题目），且集中在基础模块（计数器、FSM、加法器），缺乏系统级复杂设计（流水线 CPU、总线接口、SoC）。

**局限 3：评估与对齐不足**。functional-pass@k 只看功能正确性，忽略 PPA、安全、版权等关键维度。安全工具覆盖的 CWE 种类有限，PPA 优化缺乏高效的闭环反馈，版权水印在综合优化后可能丢失。

**局限 4：部署就绪度低**。当前没有任何方案能无缝集成到工业 EDA 流程中。缺少交互式迭代、可解释性、人类反馈机制——硬件工程师不可能像软件工程师接受 GitHub Copilot 那样接受一个「黑盒生成 Verilog」的工具。

综述在 Section 9「Threats to Validity」中还承认了三个方法论局限：
- **论文遗漏风险**：尽管搜索了 6 大数据库 + 雪球，但 LLM 领域发展太快，新论文可能被遗漏
- **选择偏差**：5172 → 102 的筛选过程涉及主观判断（尽管有 QAC 标准化评分）
- **分类偏差**：将多样化的工作归入固定类别不可避免有主观成分

### 10.2 综述的隐含前提与可能的偏倚

**隐含前提 1：LLM 是解决 Verilog 生成问题的正确方向**。综述没有讨论「LLM 是否适合 Verilog 生成」这个问题本身。它默认 LLM 是有效的，然后在这个前提下分析如何让它更有效。实际上，Verilog 的并行语义和 LLM 的序列生成之间的根本矛盾并未解决——多数工作只是在「绕过」这个问题（通过 testbench 反馈、多 Agent 验证等），而非从根本上解决。

**隐含前提 2：benchmark 分数 = 进步**。综述的分析框架将一个领域的进步等价于 benchmark 分数的提升。但 functional-pass@k 的提升可能来自 benchmark 污染（训练数据中包含了测试题）、prompt 工程技巧（而非真正理解）、或 testbench 不够严格（通过了简单 test 但无法处理 corner case）。

**隐含前提 3：英文文献中心**。综述仅收入英文论文，排除了中文（如 CCF 中文期刊）和日文的硬件设计文献。考虑到中国在 EDA 和 AI 两个领域都有大量投入，这可能遗漏了一些相关工作。

### 10.3 本资料包的批判性分析

**综述的不可替代价值**：尽管有上述限制，这篇综述仍然是目前进入 Verilog LLM 领域的「最佳第一读」。它的 102 篇论文的完整分类、27 个 benchmark 的系统梳理、34 个 IT LLM 的全景图，为任何想进入这个领域的研究者提供了地图。四维 RQ 框架使得读者可以按需跳转到自己关心的维度。

**综述的「综述性」局限**：这篇综述的价值在于「整理已有工作」，而不是「提出新方向」。三阶段路线图虽然结构良好，但本质上是对已有方向的归纳（硬件感知模型、系统级生成、Human-AI 协同都是已有论文中提到过的），没有提出全新的范式转变（如「放弃 LLM 自回归生成，改用扩散模型做硬件设计」等激进方向）。

**与其他综述的互补关系**：这篇综述是 Verilog 生成领域的「深度纵切」，配合 Pan et al. (2501.09655) 的全 EDA 流程「广度横切」和 Fang et al. (2504.03711) 的 Circuit Foundation Model 范式综述，可以构成一个完整的 AI4EDA 知识体系。本综述最适合想要具体进入 Verilog 代码生成方向的研究者。

---

## 11. 复现信息

| 项目 | 内容 |
|------|------|
| 论文页 | arXiv: https://arxiv.org/abs/2512.00020（v2, 2025年12月24日） |
| 期刊 | ACM Computing Surveys, Vol. 1, No. 1, December 2025, 35 页 |
| DOI | https://doi.org/XXXXXXX.XXXXXXX（待分配） |
| 代码 | 综述类论文，无模型代码仓库 |
| 数据 | 综述中讨论的 27 个 benchmark 和 34 个 instruct-tuning dataset 均有公开 URL（见表 6-7）；综述的完整论文列表见参考文献 [1]-[141] |
| 本地状态 | 综述论文，无需复现实验 |
| 复现等级 | N/A（综述不需要复现） |
| 相关资源 | 综述引用的核心开源项目：RTLCoder (https://github.com/hkust-zhiyao/RTL-Coder)、OriGen (https://huggingface.co/henryen/OriGen)、VerilogEval (https://github.com/NVlabs/verilog-eval)、MAGE、VerilogCoder 等 |

---

## 12. 一分钟复述版

这篇综述是**第一个专门研究「LLM 怎么写 Verilog」的系统文献综述**，发表在 ACM Computing Surveys。它用一套严格的方法（QGS + 6 大数据库 + 三阶段过滤 + 五维 QAC 评分），从 5172 篇候选论文中筛选出 102 篇（70 篇同行评审 + 32 篇预印本），覆盖 2020-2025 年。

综述围绕四个研究问题展开：**RQ1** 统计了 LLM 使用情况——GPT 系列使用 149 次（占闭源 83%），Llama 64 次，DeepSeek 54 次，还有 34 个 Verilog 专用微调模型（19 个开源权重）；**RQ2** 梳理了 27 个 benchmark 和 34 个 instruct-tuning dataset 的构建方式与质量保障策略——functional-pass@k 已成为事实标准指标；**RQ3** 将生成技术分为 Training-free（EDA 工具反馈 + 提示工程 + 推理优化）和 Training-based（预训练 + SFT + RL）两条主线；**RQ4** 首次系统分析了安全、效率、版权、幻觉四个对齐维度的现状与挑战。

核心发现：领域从 2020 年的 1 篇爆发到 2025 年的 64 篇，开源 IT 模型和推理增强模型（CodeV-R1、VeriReason 等）是 2025 年最重要的技术趋势，RL + EDA 工具反馈通常优于纯 SFT。综述提出的三阶段路线图——夯实基础（硬件感知模型 + 大规模 benchmark）→ 扩展能力（系统级分层生成 + 多模态输入）→ 优化部署（EDA 闭环 RL + Human-AI 协同 IDE）——为从学术原型到工业落地的路径提供了清晰的导航。
