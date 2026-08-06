# LLM for EDA 综述 论文深度讲解

> **A Survey of Research in Large Language Models for Electronic Design Automation**
> Jingyu Pan, Guanglei Zhou, Chen-Chia Chang, Isaac Jacobson (Duke University), Jiang Hu (Texas A&M University), Yiran Chen (Duke University)
> Submitted to ACM TODAES · arXiv: 2501.09655v1 (January 16, 2025) · 21 pages
> 原文：[2501.09655v1.txt](./2501.09655v1.txt)
> 代码：未开源（综述论文，无独立代码仓库）

---

## 1. 一句话定位

**这是一篇全面综述，首次按 EDA 全流程（系统级设计 → RTL 设计 → 逻辑综合与物理设计 → 模拟电路设计）系统梳理了 LLM 在电子设计自动化中的 100+ 篇研究工作，提出了以 EDA 设计阶段为纵轴、以 LLM 方法论（模型选择与尺寸、定制化技术、多模态特征表示）为横轴的统一分类框架；关键发现包括：GPT-4 配合 autonomous agent 框架在 VerilogEval-Human v2 上可达 94.2% pass rate（VerilogCoder），RTLCoder 以 Mistral-7B 微调超越 GPT-3.5，LCDA 在 CiM DNN 加速器协同设计中实现 25x 加速，而 naive SFT 方法的性能与模型大小正相关。**

这句话里的 6 个承重点，后面逐一拆解：

1. **全流程覆盖是最大贡献** — 此前综述多聚焦单一任务（如 RTL 代码生成），本文首次将系统级设计、RTL 设计、逻辑综合/物理设计、模拟设计四大阶段统一纳入分析框架，而非偏废一端。论文覆盖了从 natural language specification 到 tapeout 的完整链条。

2. **分类框架 = 设计阶段 x 方法论维度** — 不是简单罗列论文，而是建立了一个二维分类矩阵：纵轴是 EDA 设计阶段（4 个大阶段），横轴是 LLM 方法论维度（模型选择、定制化技术、特征表示）。Section 3 按阶段组织，Section 4 按方法论组织，两套视角互补。

3. **提示工程与微调的量化对比** — 论文在 Figure 2 中给出了 VerilogEval 基准上提示工程方法 vs 微调方法的 quantitative 对比：GPT-4 的 prompt engineering 依然 highly competitive，但 RTLCoder 和 BetterV 等 SFT 方法在特定条件下可以超越；naive SFT 的性能随模型尺寸增长而提升。

4. **Autonomous agent 框架的突破性表现** — VerilogCoder 以 GPT4-turbo 为 backbone，配合 task-planning + AST-based waveform tracing，将 pass rate 从 standalone 的 60.3% 提升至 94.2%（+33.9 个百分点），展示了"工具反馈驱动迭代"范式的巨大潜力。

5. **多模态特征表示是未来方向** — 论文指出当前 LLM4EDA 主要使用文本表示，但 EDA 天然涉及图（网表）、图像（版图/floorplan）、波形等多种模态。Graph-based circuit features + Image-based layout features + Novel text representations 三者的融合是破局关键。

6. **数据与评估是核心瓶颈** — VerilogEval 仅 8,502 个样本，远不足以支撑大规模训练；缺乏跨阶段、跨任务的标准化评估框架；工业设计数据因 IP 保护而无法公开，制约了领域适配训练的规模。

---

## 2. EDA 阶段映射（①-⑰）

参照 [芯片流程.md](../芯片流程.md) 的 17 阶段标准编号：

| 阶段 | 覆盖 | 说明 |
|------|:---:|------|
| **① RTL 设计** | ✅ **核心** | 综述的最大焦点。涵盖 spec-based RTL generation、code completion、debugging、testbench generation，讨论了 prompt engineering（ChipGPT、RTLLM、AutoChip）、SFT（RTLCoder、VeriGen、BetterV）、autonomous agent（VerilogCoder、RTLFixer）三条技术路线。 |
| ② RTL 功能仿真 | ✅ | 涉及 testbench 自动生成（如 VerilogCoder 内置波形追踪工具做功能验证）、Coverage Directed Test Generation（VerilogReader）；LLM 根据仿真反馈迭代修复 RTL。 |
| ③ 逻辑综合 | ✅ **重点** | 讨论 LLM 辅助 synthesis recipe exploration、Tcl 脚本生成（ChatEDA、ChipNeMo）；综合策略选择由 LLM 根据设计特征推荐最优 flow。 |
| ④ 门级仿真 | ⚠️ 间接涉及 | 未直接讨论门级仿真，但 LLM 辅助的 PPA 评估和时序分析建议间接涵盖门级仿真结果的解读。 |
| ⑤ STA（静态时序分析） | ⚠️ 间接涉及 | 论文在 physical design 部分讨论了 LLM 辅助 timing estimation 和时序收敛的前景，指出 LLM 必须捕捉物理布局与寄生效应之间的复杂关系。 |
| ⑥ 形式验证 | ⚠️ 少量涉及 | 在 RTL 验证上下文中提及，但未深入等价性检查等具体形式验证任务。 |
| ⑦ 布局规划 (Floorplan) | ✅ | 讨论了 floorplan evaluation，LLM 分析布局规划质量；ChatEDA 和 ChipNeMo 可生成 floorplan 相关 Tcl 脚本。 |
| ⑧ 标准单元摆放 (Placement) | ✅ | 纳入 physical design 的 automated script generation 范畴；LLM 辅助 placement 决策与约束生成。 |
| ⑨ 时钟树综合 (CTS) | ⚠️ 少量涉及 | 在 physical design 的宽泛讨论中提及，但无专门工作聚焦 CTS 的 LLM 应用。 |
| ⑩ 布线 (Routing) | ✅ | 同样在 physical design 脚本生成范畴内讨论；DRC-Coder 涉及 layout 层面的设计规则编码。 |
| ⑪ 后仿真 | ⚠️ 间接涉及 | 论文提及 post-layout simulation（主要在模拟设计上下文中），但数字后仿真的 SPEF/串扰分析未展开。 |
| ⑫ 物理验证 (DRC + LVS) | ✅ | DRC-Coder 专门探讨利用多模态 LLM（文本+版图图像）自动生成 DRC 检查代码，是物理验证阶段的代表性工作。 |
| ⑬ 签核 (Signoff) | ⚠️ 少量涉及 | 论文提及 PPA 收敛、功耗/可靠性等 signoff 相关指标，但未深入具体签核工具链流程。 |
| ⑭ 流片 | ❌ | 仅在 Chip-Chat 的 tapeout 案例中间接提及，未作为独立阶段讨论。 |
| ⑮ 制造 | ❌ | 仅在讨论与 Foundry 工艺节点模型结合时作为远期愿景提及。 |
| ⑯ 封装 + 测试 | ❌ | 未涉及。 |
| ⑰ 芯片到手 | ❌ | 未涉及。 |

**覆盖率：7/17（直接覆盖），另有 6 个阶段间接涉及。** 这篇综述的覆盖面集中于数字前端（RTL 设计）和物理设计脚本层，对后端制造、封装等阶段未涉及。模拟设计作为一个独立维度（非 17 阶段中的某一段）被完整讨论。

> 这篇综述的边界在于：它讨论的是 LLM 的"应用"而非 LLM 的"训练"。对于 EDA 流程，它更多讨论 LLM 如何辅助设计师做决策、生成代码/脚本、回答问题，而非 LLM 自身如何替代某个 EDA 工具。因此，"覆盖率 7/17"并不意味论文无价值——它的贡献在于建立了一个思考 LLM 如何渗透进 EDA 全流程的分析框架。

---

## 3. 综述的分类体系（taxonomy）

这节要解决的问题是：这篇综述用什么样的分类框架来组织 100+ 篇 LLM4EDA 论文？

论文建立了一个**二维分类体系**：

- **纵轴（Section 3）**：按 EDA 设计阶段分类——系统级设计、RTL 设计、逻辑综合与物理设计、模拟电路设计。
- **横轴（Section 4）**：按 LLM 方法论维度分类——模型选择与尺寸、定制化技术、多模态特征表示。

```text
                    LLM 方法论维度（横轴）
                    ┌──────────────┬──────────────┬──────────────┐
                    │ 模型选择与尺寸│  定制化技术   │ 多模态特征   │
                    │ (Sec 4.1)    │  (Sec 4.2)   │ (Sec 4.3)    │
    ┌───────────────┼──────────────┼──────────────┼──────────────┤
    │ 系统级设计     │ LCDA         │ —            │ —            │
    │ (Sec 3.1)     │ GPT4AIGChip  │              │              │
    │               │ Chip-Chat    │              │              │
    │               │ SpecLLM      │              │              │
    ├───────────────┼──────────────┼──────────────┼──────────────┤
    │ RTL 设计       │ CodeGen-16B  │ Prompt Eng.  │ —            │
    │ (Sec 3.2)     │ Mistral-7B   │ (Table 1)    │              │
    │               │ GPT-4-turbo  │ SFT (Table2) │              │
    │               │ DeepSeek-Coder│ Agent框架    │              │
    ├───────────────┼──────────────┼──────────────┼──────────────┤
    │ 逻辑综合/      │ Llama-20B    │ RAG (文档QA) │ Graph Encoder│
    │ 物理设计       │ LLaMA2-7B/   │ SFT (脚本生成)│ Image Encoder│
    │ (Sec 3.3)     │ 13B/70B      │              │ (DRC-Coder)  │
    ├───────────────┼──────────────┼──────────────┼──────────────┤
    │ 模拟电路设计   │ GPT-4        │ Bayesian Opt │ DocEDA       │
    │ (Sec 3.4)     │ (AnalogCoder)│ + LLM        │ (视觉+文本)  │
    │               │              │ (ADO-LLM)    │              │
    └───────────────┴──────────────┴──────────────┴──────────────┘
```

### 3.1 系统级设计（System-level Design）

这一分类涵盖 LLM 在芯片设计最早期的应用——从自然语言需求到架构规格的阶段。核心工作包括：

| 工作 | 模型 | 方法 | 关键贡献 |
|------|------|------|---------|
| LCDA [65] | Pretrained LLM | SW-HW co-design | CiM DNN 加速器协同设计，相比 SOTA 达到 **25x speedup**，避免传统优化器的 cold-start 问题 |
| GPT4AIGChip [19] | GPT 系列 | Demo-augmented prompt | 用自然语言指令替代专用硬件语言，自动化 demo-augmented prompt-generation pipeline |
| Chip-Chat [5] | ChatGPT-4 | 对话式协同设计 | 从初始规格到 tapeout 的端到端微处理器设计，人类仅做验证性审查 |
| SpecLLM [30] | LLM | 规格生成与审查 | 将架构规格分为三个抽象层次，LLM 在这三个层次上做规格撰写、代码→规格转换、规格审查 |

LCDA 的 25x speedup 是该子类中最显著的量化指标，其加速来源于预训练 LLM 能够基于历史设计特征智能决策设计属性，避免了传统协同设计优化器因随机猜测初始设计规格而面临的 cold-start 问题。

### 3.2 RTL 设计（RTL Design）

这是综述中篇幅最大、论文最密集的分类。论文将 RTL 设计中的 LLM 应用进一步细分为三个子趋势：

**子趋势 1：提示工程（Prompt Engineering）**。代表工作包括 ChipGPT（四阶段 zero-code logic design framework，使用 GPT-3.5 的 in-context learning）、RTLLM（self-planning 提示技术显著增强 GPT-3.5 在复杂硬件设计任务上的表现）、AutoChip（利用编译/仿真错误反馈迭代精炼 Verilog，多轮 feedback loop）、RTLCoder 的前身探索等。

**子趋势 2：领域适配训练（DAPT + SFT）**。代表工作包括 RTLCoder（Mistral-7B + 自动化 GPT 生成 Verilog 数据集 + scoring 机制，超越 GPT-3.5）、VeriGen（CodeGen-16B 在 GitHub+教科书 Verilog 语料上微调，匹配 GPT-3.5-turbo 性能）、BetterV（TinyLlama 判别器 + Bayesian 条件概率分解 guided generation，在 VerilogEval-machine 上达到 SOTA）、ChipNeMo（LLaMA2-7B/13B/70B 的领域适配，覆盖 tokenizer 定制、DAPT、SFT、检索模型）。

**子趋势 3：Autonomous Agent 框架**。代表工作包括 RTLFixer（RAG + ReAct prompting，数据库分类编译错误类型并标注专家指导）、VerilogCoder（task-planning + AST-based waveform tracing，GPT4-turbo 版在 VerilogEval-Human v2 上达 **94.2% pass rate**）、MEIC（双 agent 架构，分别负责调试和评分，self-planning 分解复杂调试任务）。

### 3.3 逻辑综合与物理设计（Logic Synthesis and Physical Design）

这一分类覆盖数字后端的两大主题：

- **脚本生成**：ChatEDA（LLM 驱动的 EDA 自主 agent，通过对话接口完成 task planning → script generation → execution）、ChipNeMo（在工业芯片设计流程中应用 LLM 做脚本生成 + bug summarization + analysis）。
- **文档问答**：Openroad-assistant（retrieval-aware fine-tuning 增强 LLM 问答框架）、RAG-EDA（定制化 retriever + enhanced reranker 处理 EDA 术语和工作流）。

### 3.4 模拟电路设计（Analog Circuit Applications）

这是综述的特色分类——大多数 LLM4EDA 综述聚焦数字设计，本文延伸到了模拟领域。按模拟设计流程细分：

- **规格与拓扑选择**：DocEDA（LLM + 计算机视觉自动提取技术文档中的 layout/参数/拓扑，构建 RAG 数据库用于拓扑推荐）
- **原理图设计与仿真**：AnalogCoder（feedback-enhanced 拓扑生成，LLM 读取功能检查和仿真结果迭代优化）、ADO-LLM（LLM + Bayesian Optimization，将 LLM 的领域知识注入搜索过程）、LaMAGIC（SFT on circuit formulations，学习电路-仿真结果关系，实现 one-shot 高成功率生成）
- **版图设计与后仿真**：LLANA（LLM + Bayesian Optimization 生成 layout constraints）、LayoutCopilot（多 agent LLM 系统 + 人类交互反馈优化模拟 layout 性能）

---

## 4. 方法与架构

### 4.1 LLM4EDA 研究的整体方法论 Pipeline

```text
                          ┌─────────────────────────────┐
                          │    EDA 任务输入               │
                          │  · 自然语言规格               │
                          │  · HDL 代码片段               │
                          │  · EDA 工具日志/报告          │
                          │  · 网表/版图（图/图像模态）   │
                          └─────────────┬───────────────┘
                                        │
                                        ▼
                          ┌─────────────────────────────┐
                          │    方法选择                   │
                          │  ┌───────────────────────┐  │
                          │  │ Prompt Engineering    │  │
                          │  │ (ChatGPT/GPT-4直接调用)│  │
                          │  ├───────────────────────┤  │
                          │  │ SFT / DAPT            │  │
                          │  │ (CodeGen/Llama/Mistral)│  │
                          │  ├───────────────────────┤  │
                          │  │ RAG                   │  │
                          │  │ (Retrieval + LLM)     │  │
                          │  ├───────────────────────┤  │
                          │  │ Autonomous Agent      │  │
                          │  │ (LLM + Tool Feedback) │  │
                          │  └───────────────────────┘  │
                          └─────────────┬───────────────┘
                                        │
                                        ▼
                          ┌─────────────────────────────┐
                          │    特征表示层                 │
                          │  · Text encoder (HDL/文档)   │
                          │  · Graph encoder (GNN)       │
                          │  · Image encoder (ViT/CLIP)  │
                          │  · Multi-modal fusion        │
                          └─────────────┬───────────────┘
                                        │
                                        ▼
                          ┌─────────────────────────────┐
                          │    LLM Backbone              │
                          │  GPT-4/GPT-3.5 | Llama3     │
                          │  CodeGen | Mistral | Claude  │
                          │  DeepSeek-Coder | CodeGemma  │
                          └─────────────┬───────────────┘
                                        │
                                        ▼
                          ┌─────────────────────────────┐
                          │    输出                       │
                          │  · Verilog/VHDL 代码          │
                          │  · Tcl 脚本                   │
                          │  · 设计文档/规格              │
                          │  · PPA 分析/预测              │
                          └─────────────┬───────────────┘
                                        │
                                        ▼
                          ┌─────────────────────────────┐
                          │    反馈循环（Agent 方法特有） │
                          │  · 编译结果 → 语法修错       │
                          │  · 仿真结果 → 功能修正       │
                          │  · PPA 报告 → 设计优化       │
                          └─────────────────────────────┘
```

### 4.2 LLM 架构类型与选择逻辑

论文在 Section 4.1 中系统梳理了 EDA 中使用的四种 Transformer 架构变体：

**Encoder-only 模型**（如 BERT）：使用全可见注意力机制，擅长对输入数据做深度理解和 context-rich representation。在 EDA 中的适用场景包括 HDL 代码分析与分类、芯片布局质量评估等理解型任务。论文指出 encoder-only 模型在最近的 EDA 研究中比 encoder-decoder 模型表现更好。

**Decoder-only 模型**（如 GPT 系列、LLaMA 系列、Mistral）：使用 causal attention mask（从左到右），擅长基于编码表示生成输出。这是 LLM4EDA 中**最主流的架构选择**——论文讨论的几乎所有生成任务（RTL 生成、Tcl 脚本生成、文档问答）都使用 decoder-only 模型。

**Encoder-decoder 模型**（如 T5）：结合 encoder 的理解能力和 decoder 的生成能力。论文提及 CodeGen 系列采用了这一架构的变体 PrefixLM。

**PrefixLM**（如 CodeGen 系列）：对输入 token 使用全可见注意力，对未来生成 token 使用 causal mask。这一设计使得模型能充分理解完整的用户输入（包括规格、示例、上下文），同时保持自回归生成的效率。CodeGen 系列专门为代码生成任务训练了这种架构。

### 4.3 定制化技术的五条路径

论文在 Section 4.2 中总结了五项核心定制化技术：

**路径 1：Fine-tuning with EDA tools**（代表：ChatEDA、VeriGen）。通过在 EDA 领域数据上微调 LLM，使模型理解并生成 EDA 特定的语言（Verilog、Tcl）和流程。ChatEDA 使用 QLoRA 微调 Llama-20B，VeriGen 在 Verilog 语料上全参数微调 CodeGen-16B。

**路径 2：Domain-adaptive pretraining + SFT**（代表：ChipNeMo）。在通用预训练的基础上，使用 EDA 领域数据做持续预训练，再进行监督微调。ChipNeMo 还引入了定制 tokenizer（新增约 9K tokens）和领域适配检索模型，在 7B/13B/70B 三种尺度上验证了效果。

**路径 3：Prompt engineering + In-context learning**（代表：RTLLM、ChipGPT、GPT4AIGChip）。不修改模型参数，通过精心设计的 prompt 结构引导 LLM 行为。RTLLM 的 self-planning 技术将复杂设计任务分解为子任务逐步执行；ChipGPT 的四阶段框架（prompt manager + output manager）实现了 zero-code 逻辑设计。

**路径 4：Autonomous agent framework**（代表：RTLFixer、VerilogCoder、DRC-Coder）。让 LLM 作为 agent 与外部工具交互——读取编译器/仿真器输出、查询知识库、执行波形追踪——在多轮迭代中自主提升输出质量。VerilogCoder 的 pass rate 从 standalone 的 60.3% 跃升至 94.2%，是这条路径价值的直接证据。

**路径 5：Retrieval-Augmented Generation**（代表：Openroad-assistant、RAG-EDA）。在 EDA 文档问答场景中，通过专门优化的检索器和重排序器（针对 EDA 术语和复杂工作流），配合 retrieval-aware fine-tuning，使 LLM 能够从海量技术文档中精准提取所需信息。

### 4.4 多模态特征表示的设计空间

论文在 Section 4.3 中描绘了三种互补的特征表示方向：

- **文本表示**：当前主流，包括代码片段、文档、规格的自然语言文本。未来方向包括用 Gist tokens 压缩长上下文、开发 EDA 专用 text encoder 封装工具日志知识。
- **图表示**：使用 GNN 作为 encoder，将网表/电路拓扑的层次化连接结构编码为 LLM 可理解的表示。论文引用 GraphLLM 和 G-Retriever 作为技术基础。
- **图像表示**：将版图、floorplan、设计规则图等视觉信息通过视觉编码器（ViT/CLIP 风格）输入 LLM。DRC-Coder 是该方向的首个实践——多模态 LLM 解读设计规则描述和版图可视化。

三种模态的融合是论文展望的核心方向——文本提供语义理解、图提供结构关系、图像提供空间直觉，三者协同有望突破纯文本 LLM 在物理设计阶段的瓶颈。

---

## 5. 综述提出的分类维度与判据

这节要解决的问题是：这篇综述用哪些维度来"分类"和"评判" LLM4EDA 的研究工作？这些维度本身构成了综述的核心学术贡献——它们为后续研究提供了一个可以复用和扩展的分析框架。

### 维度 1：EDA 设计阶段定位

论文将每项工作首先按其在芯片设计流程中的位置分类。判据是：该工作解决的是哪个设计阶段的问题？四个一级分类为系统级设计、RTL 设计、逻辑综合与物理设计、模拟电路设计。这个维度的价值在于帮助研究者快速判断一项 LLM4EDA 工作在完整 EDA 流程中的卡位，并识别研究密度的不均衡——例如 RTL 设计阶段工作密集，而 CTS、形式验证、后仿真阶段几乎空白。

### 维度 2：LLM 模型选择与尺寸

论文对每项工作的 backbone LLM 进行分类和比较。判据包括：

- **模型架构类型**：encoder-only、decoder-only、encoder-decoder、PrefixLM
- **模型开放程度**：闭源（GPT-4/GPT-3.5/Claude3）vs 开源（LLaMA/Mistral/CodeGen/DeepSeek-Coder）
- **模型参数量级**：小（7B 级，如 Mistral-7B、CodeLlama-7B）、中（13B~16B 级，如 CodeGen-16B）、大（70B+，如 LLaMA2-70B）、超大规模（GPT-4，参数量未公开）

论文的关键判据发现：naive SFT 方法的性能与模型尺寸正相关（Figure 2 的趋势线）、闭源模型在 autonomous agent 任务中显著优于开源模型（GPT4-turbo 94.2% vs Llama3 67.3% in VerilogCoder）、预训练语料中 Verilog 的比例对下游 RTL 生成性能有决定性影响。

### 维度 3：定制化技术路线

论文将 LLM4EDA 的定制化技术归纳为五条路径（已在 Section 4.3 详述），并给出了清晰的判据来选择不同路径：

| 判据 | 推荐路径 |
|------|---------|
| 无训练资源，需要快速验证 | Prompt Engineering（路径 3） |
| 有领域标注数据，追求极致效果 | SFT + DAPT（路径 1、2） |
| 需要多轮迭代优化，利用 EDA 工具链 | Autonomous Agent（路径 4） |
| 需要从海量文档中检索信息 | RAG（路径 5） |
| 目标场景涉及版图/网表等非文本模态 | 多模态融合 + 路径组合 |

论文特别强调一个趋势：**提示工程在闭源大模型上极具竞争力**（GPT-4 + prompt engineering 的性能可以匹敌甚至超越开源模型的 SFT），而 **SFT 在开源小模型上可以显著提升**（RTLCoder 以 Mistral-7B 微调后超越 GPT-3.5），**最先进的方法往往需要 SFT + 高质量数据 + 生成后筛选或 agent 反馈的组合**。

### 维度 4：数据模态与特征表示

论文将 LLM4EDA 中的特征表示按模态分类为文本、图、图像三种，判据是输入数据的结构特征：

- **纯文本**是最成熟但最受限的表示——它能捕捉 Verilog 的语法和语义，但无法表达电路的拓扑依赖和空间布局关系。
- **图表示**可以天然编码网表的层次化连接结构，但需要 GNN encoder 作为桥接层才能输入 LLM。
- **图像表示**可以捕捉版图的 pin density、cell density 等空间特征，但需要视觉 encoder 配合。

论文的判据发现是：当前几乎所有工作（Table 1 和 Table 2 的全部条目）仅使用文本模态，多模态融合仍处于早期探索阶段（仅有 DRC-Coder 等个别工作尝试），这个 gap 本身就是一个重要研究方向。

### 维度 5：评估基准与数据集

论文在 Table 3 中梳理了 LLM4EDA 的学术基础设施，并按以下判据分类：

| 判据 | 关键数据 |
|------|---------|
| 最大的领域适配数据集 | ChipNeMo: 24.1B tokens（来自 NVBugs 等工业源） |
| 最常用的评估基准 | VerilogEval: 8,502 samples |
| 指令微调数据集规模 | ChatEDA: 1,500 instructions; RTLCoder: 10,000 designs |
| 教学材料数据集 | VeriGen: 400 MB（来自 Verilog 教科书） |

论文明确指出：VerilogEval 仅约 8K 样本，相对于 NLP 领域动辄百万级的数据集严重不足；缺乏统一的跨任务、跨阶段评估标准；现有基准多聚焦 syntax/function correctness，缺乏 PPA、安全性、可综合性等多维度评估。

---

## 6. 训练与实验设置

### 6.1 本文是否涉及训练

这篇综述论文自身不涉及新模型训练——它是对已有工作的系统整理和分析。但它详细描述了它所覆盖的各项工作的训练和实验设置，使读者能够横向比较不同方法论的计算成本与效果。

### 6.2 代表性工作的实验设置对比

**提示工程类（无需训练）**：

| 工作 | 模型 | 技术 | 关键参数 |
|------|------|------|---------|
| ChipGPT [10] | ChatGPT (GPT-3.5) | In-context learning | 四阶段框架，prompt manager + output manager |
| RTLLM [36] | GPT-3.5 | Self-planning | open-source benchmark，评估 syntax correctness + functionality + design quality |
| AutoChip [59] | GPT-3.5-turbo 等 | Iterative feedback | 多轮编译/仿真反馈，直至通过 |
| Chip-Chat [5] | ChatGPT-4 | Conversational co-design | 对话式交互，8-bit accumulator-based microprocessor 设计到 tapeout |

**SFT/微调类（需要训练）**：

| 工作 | Base Model | 数据规模 | 训练方法 | 关键效果 |
|------|-----------|---------|---------|---------|
| RTLCoder [35] | Mistral-7B | 10,000 designs（GPT-3.5 生成） | SFT with Verilog scoring | 超越 GPT-3.5 的 RTL 生成能力 |
| VeriGen [58] | CodeGen-16B | 400 MB Verilog 语料（GitHub + 教科书） | SFT | 匹配 GPT-3.5-turbo 性能 |
| ChipNeMo [33] | LLaMA2-7B/13B/70B | 24.1B tokens（NVBugs 等工业数据） | DAPT + SFT + 定制 tokenizer | 7B 模型在 EDA 任务上接近通用大模型 |
| ChatEDA [24] | Llama-20B | 1,500 instructions（GPT-4 生成） | Instruction tuning + QLoRA | EDA 自主 agent 的脚本生成 |
| BetterV [44] | CodeLlama-7B-Instruct + TinyLlama | Verilog 数据集 | SFT + Bayesian controlled generation | VerilogEval-machine SOTA |
| CodeGen-345M [14] | CodeGen-345M | 公开 Verilog 数据 | SFT | 轻量级 Verilog 代码补全 |

**Autonomous Agent 类（LLM 不训练，但 agent 框架有工程开销）**：

| 工作 | Backbone LLM | Agent 组件 | Pass Rate |
|------|-------------|-----------|-----------|
| VerilogCoder [26] | GPT4-turbo | Task planner + AST-based waveform tracing | **94.2%** (VerilogEval-Human v2) |
| VerilogCoder [26] | Llama3 | 同上 | 67.3% |
| RTLFixer [62] | LLM + RAG | 编译错误分类数据库 + ReAct prompt | 报告中显著优于单次生成 |

### 6.3 Figure 2 的关键实验发现

论文 Figure 2 是综述中最重要的一张实验对比图，它比较了多种方法在 VerilogEval-machine 和 VerilogEval-Human 上的 functional correctness pass rate。关键发现：

1. **Naive SFT 的性能与模型尺寸正相关**：CodeGen-16B 的三种预训练变体（nl / multi / verilog）中，在 Verilog 语料上预训练的版本显著优于在自然语言或多编程语言语料上预训练的版本。这说明预训练语料中 Verilog 的比例是决定下游 RTL 生成性能的**第一性因素**。

2. **RTLCoder 和 BetterV 通过超越 SFT 的技术达到 SOTA**：RTLCoder 采用 data-oriented 方法——对 RTL 设计候选评分并将评分反馈到微调过程；BetterV 采用 Bayesian 规则分解生成时的条件概率，使用生成式判别器修改 token 概率分布以偏向期望的 token。这两种技术都超越了单纯的 "more data + bigger model" 范式。

3. **GPT-4 的 prompt engineering 依然 highly competitive**：即使不进行任何微调，GPT-4 配合精心设计的 prompt 在多个基准上的表现依然可以匹敌或接近经过专门微调的模型。

---

## 7. 创新点

### 创新点 1：首次建立 LLM4EDA 的全流程分类框架

在此之前，LLM4EDA 的综述要么聚焦单一任务（如 RTL 代码生成，Yang et al. 综述），要么聚焦单一方法论（如 Circuit Foundation Models 的预训练+微调范式，Fang et al. 综述）。本文首次将"EDA 全流程"作为分类框架的主轴——从系统级设计到模拟设计，覆盖了数字设计的全部主要阶段。这个框架的创新不在于"全面"，而在于它揭示了不同设计阶段对 LLM 的需求差异：系统级设计需要 LLM 做架构推理和高层次决策，RTL 设计需要精确的代码生成和功能验证，物理设计需要多模态理解和约束推理，模拟设计需要拓扑创新和仿真迭代。这种分阶段的精细化分析使得后续研究者能够准确定位自己的工作在整个 EDA 自动化版图中的卡位。

### 创新点 2：提示工程 vs 微调 vs Agent 的实证对比分析框架

论文不只是罗列技术路线，而是建立了实证对比的基准。Figure 2 将 prompt engineering（GPT-3.5/GPT-4 无需训练）、naive SFT（CodeGen-16B 在不同语料上的微调）、advanced SFT（RTLCoder 的 data-scoring、BetterV 的 controlled generation）放在同一坐标下比较，形成了清晰的 performance hierarchy。这个对比框架是一项方法论贡献——它帮助研究者判断"我应该在什么条件下选择哪种技术路线"，例如：有 GPT-4 API 就用 autonomous agent（94.2% pass rate），有领域数据就用 SFT + 质量评分（RTLCoder 超越 GPT-3.5），只有开源小模型就叠加多轮 agent 反馈（Llama3 从 41.7% 提升到 67.3%）。

### 创新点 3：将模拟电路设计纳入 LLM4EDA 讨论

几乎所有 LLM4EDA 综述都聚焦于数字电路——因为 Verilog/VHDL 是文本语言，天然适合 LLM 处理。本文的独特贡献是将模拟电路设计作为一个完整的独立维度纳入讨论，梳理了 LLM 在模拟设计各子阶段（拓扑选择、原理图设计、仿真分析、版图约束生成、后仿真优化）中的应用。这是一个被大多数综述忽视但极具潜力的方向——模拟设计长期以来依赖资深工程师的经验和直觉，LLM 如果能从历史设计先例中学习，可能大幅降低模拟设计的门槛。

### 创新点 4：多模态特征表示的统一展望

论文在 Section 4.3 中提出的"文本 + 图 + 图像"三模态特征表示框架，虽然目前大多数工作仅使用了文本模态，但这个框架为后续研究指明了方向。具体而言，论文指出 GNN 编码电路拓扑 + 视觉编码器处理版图 + 文本编码器处理规格和文档，三者通过 LLM 作为统一 backbone 进行融合——这个架构设想如果实现，将使 LLM 从"纯语言层面的代码生成器"进化为"能够理解电路物理本质的设计引擎"。

### 创新点 5：学术基础设施的全面盘点

Table 3 整合了 LLM4EDA 领域的六大关键数据集（ChipNeMo 24.1B tokens、ChatEDA 1,500 instructions、GPT4AIGChip 7,000 snippets、VeriGen 400 MB、VerilogEval 8,502 samples、RTLCoder 10,000 designs），为后续研究者提供了"入门数据清单"。论文还指出 VerilogEval 的规模瓶颈（仅约 8K 样本，远不足以支撑大规模预训练），明确提出了"扩大数据集 + 增大模型尺寸"的研究方向。

---

## 8. EDA 缩写表

| 缩写 | 全称 | 一句话解释 |
|------|------|-----------|
| EDA | Electronic Design Automation | 电子设计自动化，用软件工具辅助芯片设计全流程 |
| LLM | Large Language Model | 大语言模型，在 web-scale 文本上预训练的巨型神经网络 |
| RTL | Register Transfer Level | 寄存器传输级，用 Verilog/VHDL 描述数据在寄存器间的流动和逻辑操作 |
| HDL | Hardware Description Language | 硬件描述语言，如 Verilog、VHDL |
| PPA | Power, Performance, Area | 功耗、性能、面积，芯片设计的三个核心优化目标 |
| SFT | Supervised Fine-Tuning | 监督微调，在有标注数据上进一步训练预训练模型 |
| DAPT | Domain-Adaptive Pre-Training | 领域自适应预训练，在特定领域语料上对通用预训练模型做持续预训练 |
| RLHF | Reinforcement Learning from Human Feedback | 基于人类反馈的强化学习，用于对齐 LLM 输出与人类偏好 |
| RAG | Retrieval-Augmented Generation | 检索增强生成，先检索相关知识再让 LLM 基于检索结果生成 |
| GNN | Graph Neural Network | 图神经网络，处理图结构数据的深度学习模型 |
| DSE | Design Space Exploration | 设计空间探索，在庞大的设计参数空间中搜索最优配置 |
| AST | Abstract Syntax Tree | 抽象语法树，代码的结构化树形表示 |
| DRC | Design Rule Check | 设计规则检查，验证版图是否满足工艺厂的可制造性规则 |
| LVS | Layout vs Schematic | 版图与原理图比对，验证版图是否忠实实现了电路设计 |
| STA | Static Timing Analysis | 静态时序分析，不跑仿真纯数学计算所有路径延迟 |
| CTS | Clock Tree Synthesis | 时钟树综合，为时钟信号插入缓冲器树确保同步 |
| CiM | Compute-in-Memory | 存内计算，在存储器内部直接进行计算的新型计算范式 |
| DNN | Deep Neural Network | 深度神经网络 |
| NAS | Neural Architecture Search | 神经架构搜索，自动搜索最优神经网络结构 |
| SW-HW | Software-Hardware | 软硬件协同 |
| FPGA | Field-Programmable Gate Array | 现场可编程门阵列，可重新配置的硬件平台 |
| ASIC | Application-Specific Integrated Circuit | 专用集成电路，针对特定应用定制的芯片 |
| DSL | Domain-Specific Language | 领域特定语言 |
| QLoRA | Quantized Low-Rank Adaptation | 量化低秩适配，一种参数高效的微调方法 |
| MCTS | Monte Carlo Tree Search | 蒙特卡洛树搜索，用于决策过程的搜索算法 |
| GQA | Grouped-Query Attention | 分组查询注意力，Mistral 7B 使用的注意力优化机制 |
| Tcl | Tool Command Language | 工具命令语言，EDA 工具（如 Design Compiler、Innovus）的脚本语言 |
| SDC | Synopsys Design Constraints | 设计约束文件，定义时钟频率、输入输出延迟等时序约束 |
| SPEF | Standard Parasitic Exchange Format | 标准寄生参数交换格式，记录走线的寄生电阻和电容 |
| CWE | Common Weakness Enumeration | 通用弱点枚举，安全漏洞分类标准 |
| ECO | Engineering Change Order | 工程变更单，设计后期的局部修改 |
| IC | Integrated Circuit | 集成电路 |
| VLSI | Very Large Scale Integration | 超大规模集成 |

---

## 9. 与芯片流程的关系

### 9.1 在全流程中的位置

这篇综述不解决任何一个具体的 EDA 子问题——它的定位是"地图"而非"引擎"。从 17 阶段视角看：

- **接手的输入**：已有 LLM4EDA 研究文献（2022-2024 年，100+ 篇论文）
- **完成的工作**：建立分类框架、归纳方法论、对比实证结果、识别瓶颈与未来方向
- **交付的价值**：为 EDA 从业者提供"LLM 能在流程的哪些环节帮我？"的系统性回答；为 AI 研究者提供"EDA 中什么任务最难、最有价值？"的路线图；为后续综述提供可复用的分析模板

具体而言，论文在第 2 节（Background on LLM）和第 3 节（Trends）之间建立了清晰的"承接关系"——先讲 LLM 技术的发展脉络（GPT 系列、开源模型、RLHF、多模态），再讲这些技术如何在 EDA 各阶段落地——这使得不同背景的读者都能找到切入点。

### 9.2 "综述的洞察"和"流片的现实"之间隔着什么

这一节的目的是厘清：论文覆盖了 7/17 个阶段，但它所描述的"LLM 辅助设计"与"真实的工业流片"之间的距离。

1. **规模差距**：论文覆盖的代表性工作在 VerilogEval-Human 基准上评估，但 VerilogEval 的题目规模通常是单模块、几十到几百行 Verilog。工业级 SoC 设计涉及数百个模块、数万行 RTL 代码、复杂的 inter-module 依赖和多时钟域。LLM 目前无法处理这种规模。

2. **物理信息缺失**：论文讨论的 LLM 辅助主要停留在"文本层面"——生成 RTL 代码、生成 Tcl 脚本、回答文档问题。但真实芯片设计的核心挑战（时序收敛、功耗优化、IR drop、串扰）都发生在物理层面。LLM 要真正影响 PPA，必须在多模态融合（图+图像+文本）上取得突破。

3. **确定性与概率性**：EDA 工具（综合器、STA 引擎、DRC 检查器）是确定性的——给定相同的输入，总是产生相同的输出。LLM 是概率性的——相同 prompt 不同采样产生不同结果，甚至可能产生幻觉（生成语法正确但功能错误的代码）。在 signoff 阶段，一个错误的时序报告可能导致数千万美元的流片失败。确定性可验证与概率性生成之间的张力是 LLM4EDA 必须解决的根本矛盾。

4. **人类的角色**：论文反复强调 LLM 目前是"辅助"而非"替代"。Chip-Chat 中人类设计师的角色是"validate LLM's choices"，而不是让 LLM 自主做出所有决策。在可预见的未来，人类在验证、signoff、风险决策中的不可替代性仍然成立。

---

## 10. 讨论与局限

### 10.1 论文自述的局限

论文在 Section 5.2（Application Bottlenecks）中坦率地指出了 LLM4EDA 面临的六大瓶颈：

1. **数据隐私与 IP 保护**：高质量芯片设计数据是高度专有的商业机密，企业不愿分享用于训练 LLM。联邦学习、差分隐私、同态加密等技术尚未在 EDA 场景中得到验证。

2. **领域专业知识与数据稀缺**：LLM 在通用语料上训练，缺乏 HDL/Tcl/EDA 工具日志等专业知识的深度覆盖。现有公开 Verilog 数据集（VerilogEval 仅约 8K 样本）远不足以支撑大规模领域适配预训练。

3. **与现有 EDA 工具链的集成困难**：工业 EDA 流程经过数十年发展，LLM 需要兼容 legacy 系统、脚本格式和 IP 管理，而这不是简单的 API 调用问题。

4. **计算资源与实时性**：EDA 任务常需实时或近实时的分析与反馈，LLM 推理（尤其是 iterative prompting）的计算开销和延迟在工程实践中可能不可接受。

5. **准确性与可靠性**：EDA 中错误的代价极高，工程师习惯于信任确定性工具。LLM 输出的不确定性和潜在的幻觉是工业采纳的主要心理障碍。

6. **行业标准与合规**：半导体行业受严格的可靠性标准约束，LLM 生成的组件必须满足这些标准且输出可被验证和审计。

### 10.2 综述覆盖面的局限

作为综述，本文自身也存在覆盖面选择带来的局限：

- **对验证阶段的覆盖不足**：RTL 功能仿真（阶段 2）更多被当作 RTL 代码生成的"下游验证手段"讨论，而非独立的 LLM 应用领域。形式验证、门级仿真、STA 签核等阶段的 LLM 应用几乎没有涉及。
- **FPGA 设计生态的讨论有限**：论文承认 FPGA 设计中的 LLM 应用研究"remains limited"，虽然在 Section 3.3 末尾指出了前景，但在正文中的篇幅极少。
- **硬件安全方向的覆盖较浅**：虽然提及了 CWEs 和生成安全 RTL 的问题，但硬件木马检测、侧信道攻击防护等经典硬件安全议题未能在 LLM 视角下展开讨论。

### 10.3 本资料包的批判性分析

**方法的隐含前提**：论文的分类框架隐含假设是"LLM 可以渗透进 EDA 的每个阶段"，但它未系统讨论"哪些阶段天然适合 LLM，哪些不适合"。例如：RTL 代码生成（文本→文本）天然适合 LLM，而 STA（图上的数学计算）天然不适合。前者只需要语法和功能正确，后者要求对所有路径的精确数学证明——LLM 的概率性本质与 STA 的确定性需求之间存在根本性的范式冲突。

**评测的公平性问题**：Figure 2 将不同方法放在同一张图上对比，但这些方法的计算成本差异巨大。GPT-4 的 prompt engineering 可能需要数十轮迭代，而 RTLCoder 的推理是前向一次完成。论文未讨论"pass rate per GPU-hour"或"pass rate per dollar"这类效率指标，导致对比维度不完整。此外，VerilogEval 自身是否是公平的评测基准也存在争议——它偏向于特定风格和规模的 Verilog 题目。

**可扩展性天花板**：论文指出的"扩大数据集 + 增大模型尺寸"这一研究方向，在实践中可能面临收益递减。Naive SFT 的性能随模型尺寸的增长曲线（Figure 2）已经呈现趋势——CodeGen-16B 的三种预训练变体之间的性能差距远大于不同模型尺寸之间的差距，说明"数据质量"和"预训练语料的领域相关性"是比"模型大小"更具决定性作用的因素。单纯增大模型而不解决数据瓶颈，可能是一条 low-ROI 的路径。

---

## 11. 复现信息

| 项目 | 内容 |
|------|------|
| 论文页 | [arXiv:2501.09655v1](https://arxiv.org/abs/2501.09655v1) |
| 代码 | 未开源（综述论文，不涉及独立代码仓库） |
| 数据集 | 综述论文，所引用的各工作数据集分散在原始论文中。核心数据集包括：VerilogEval（8,502 samples）、RTLCoder（10,000 designs）、ChipNeMo（24.1B tokens，未公开）、ChatEDA（1,500 instructions） |
| 本地状态 | 综述论文无需复现 |
| 复现等级 | N/A（综述论文，但其所综述的代表性工作复现等级分布在 R1~R3） |
| 主要门槛 | 综述论文无直接复现门槛。若复现其代表性工作（如 RTLCoder、VerilogCoder），主要门槛为：高质量 Verilog 训练数据获取、GPU 算力（SFT 需要 A100 级别）、GPT-4 API 访问（agent 方法依赖闭源模型） |

---

## 12. 一分钟复述版

1. **这篇综述做了什么**：系统梳理了 2022-2024 年 LLM 在 EDA 全流程（系统级 → RTL → 逻辑综合/物理设计 → 模拟设计）中的 100+ 篇研究工作，建立了以设计阶段为纵轴、以 LLM 方法论为横轴的统一分类框架。

2. **五项定制化技术路线**：prompt engineering（ChatGPT 直接调用）、DAPT+SFT（领域微调）、RAG（检索增强）、autonomous agent（工具反馈驱动迭代）、多模态融合（文本+图+图像）。五条路线各有适用场景，当前最先进的方法是 SFT + 数据质量筛选 + agent 反馈的组合。

3. **RTL 设计是最大焦点，三条子路线**：提示工程（ChipGPT、RTLLM、AutoChip）、领域微调（RTLCoder 超越 GPT-3.5、BetterV 在 VerilogEval 上 SOTA）、autonomous agent（VerilogCoder 以 GPT4-turbo 达 94.2% pass rate，相比 standalone 提升 33.9 个百分点，但 Llama3 仅 67.3%，闭源模型在 agent 场景中显著领先）。

4. **系统级设计的量化亮点**：LCDA 在 CiM DNN 加速器协同设计中实现 25x speedup，通过预训练 LLM 的智能决策避免了传统优化器的 cold-start 问题。

5. **逻辑综合与物理设计**：LLM 主要用于 Tcl 脚本生成和文档问答，ChatEDA 和 ChipNeMo 是代表性工作。真正的物理层面突破（PPA 预测、时序收敛）依赖于多模态融合的成熟。

6. **模拟电路设计是独特贡献**：首次将模拟设计纳入 LLM4EDA 综述，梳理了从拓扑选择（DocEDA）、原理图生成（AnalogCoder、ADO-LLM、LaMAGIC）到版图约束（LLANA、LayoutCopilot）的完整链条。

7. **Figure 2 的核心结论**：naive SFT 性能与模型大小正相关；预训练语料中 Verilog 比例比模型大小更重要；GPT-4 的 prompt engineering 依然 highly competitive；RTLCoder 的 data-scoring 和 BetterV 的 controlled generation 超越了单纯的 SFT 范式。

8. **三大未解决问题**：数据瓶颈（VerilogEval 仅约 8K 样本，工业数据因 IP 保护无法公开）、评估标准不统一（缺乏跨任务、跨阶段、包含 PPA+安全性+可综合性的综合评估框架）、多模态融合处于早期（当前几乎所有工作仅使用文本模态，图+图像+文本的融合刚刚起步）。

9. **LLM4EDA 的"引力中心"**：当前社区过度集中于 RTL 代码生成的 functional correctness 指标（VerilogEval pass rate），对后端物理约束（时序、面积、功耗、可制造性）的关注严重不足。真正的价值创造不在于"LLM 生成的 Verilog 有多少语法正确"，而在于"LLM 能否帮助设计团队在更短时间内达到 PPA 收敛和 signoff"。
