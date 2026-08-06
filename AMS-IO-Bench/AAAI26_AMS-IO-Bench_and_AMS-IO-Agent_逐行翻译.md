# AMS-IO-Bench and AMS-IO-Agent: Benchmarking and Structured Reasoning for Analog and Mixed-Signal Integrated Circuit Input/Output Design

> **论文标题：** AMS-IO-Bench 与 AMS-IO-Agent：面向模拟混合信号集成电路输入/输出设计的基准测试与结构化推理
>
> **会议：** The Fortieth AAAI Conference on Artificial Intelligence (AAAI-26)
>
> **作者：** Zhishuai Zhang\*¹†, Xintian Li\*², Shilong Liu³, Aodong Zhang¹, Lu Jie², Nan Sun¹
>
> **单位：**
> 1. 清华大学电子工程系
> 2. 清华大学集成电路学院
> 3. 普林斯顿大学 Princeton AI Lab
>
> **联系方式：** arcadia16zzs@gmail.com
>
> \* 共同第一作者 | † 通讯作者
>
> **代码：** https://github.com/Arcadia-1/AMS-IO-Agent
> **数据集：** https://github.com/Arcadia-1/AMS-IO-Bench

---

## 摘要 (Abstract)

> 在本文中，我们提出了 AMS-IO-Agent，一个面向领域的、基于大语言模型（LLM）的智能体，用于模拟混合信号（AMS）集成电路（IC）中结构感知的输入/输出（I/O）子系统生成。本文的核心贡献是一个框架，它将自然语言设计意图与工业级 AMS IC 设计交付物连接起来。

In this paper, we propose AMS-IO-Agent, a domain-specialized LLM-based agent for structure-aware input/output (I/O) subsystem generation in analog and mixed-signal (AMS) integrated circuits (ICs). The central contribution of this work is a framework that connects natural language design intent with industrial-level AMS IC design deliverables.

> AMS-IO-Agent 集成了两个关键能力：(1) 一个结构化领域知识库，捕获可复用的约束和设计惯例；(2) 设计意图结构化，使用 JSON 和 Python 作为中间格式，将模糊的用户意图转换为可验证的逻辑步骤。

AMS-IO-Agent integrates two key capabilities: (1) a structured domain knowledge base that captures reusable constraints and design conventions; (2) design intent structuring, which converts ambiguous user intent into verifiable logic steps using JSON and Python as intermediate formats.

> 我们还进一步提出了 AMS-IO-Bench，一个面向引线键合封装 AMS I/O 环自动化的基准测试。在该基准测试上，AMS-IO-Agent 实现了超过 70% 的 DRC+LVS 通过率，并将设计周转时间从数小时缩短到数分钟，优于基线 LLM。

We further introduce AMS-IO-Bench, a benchmark for wirebond-packaged AMS I/O ring automation. On this benchmark, AMS-IO-Agent achieves over 70% DRC+LVS pass rate and reduces design turnaround time from hours to minutes, outperforming the baseline LLM.

> 此外，一个由智能体生成的 I/O 环已在 28 nm CMOS 流片中制造并验证，证明了该方法在实际 AMS IC 设计流程中的实用有效性。据我们所知，这是首次报道的人机协作 AMS IC 设计，其中基于 LLM 的智能体完成了一个非平凡的子任务，其输出直接用于硅芯片。

Furthermore, an agent-generated I/O ring was fabricated and validated in a 28 nm CMOS tape-out, demonstrating the practical effectiveness of the approach in real AMS IC design flows. To our knowledge, this is the first reported human-agent collaborative AMS IC design in which an LLM-based agent completes a nontrivial subtask with outputs directly used in silicon.

---

## 1. 引言 (Introduction)

> 输入/输出（I/O）子系统是模拟混合信号（AMS）集成电路（IC）的基础组成部分，提供信号接口、电源传输和静电放电（ESD）保护。虽然数字 I/O 单元通常可以使用脚本放置并通过标准数字流程布线，但 AMS I/O 的实现由于复杂的、项目特定的需求，仍然主要依赖手工完成。

Input/output (I/O) subsystems are a fundamental component of analog and mixed-signal (AMS) integrated circuits (ICs), providing signal interfacing, power delivery, and electrostatic discharge (ESD) protection. While digital I/O cells can typically be placed using scripts and routed via standard digital flows, the implementation of AMS I/O remains largely manual due to intricate, project-specific requirements.

> 这些需求包括多样的信号类型、多个电源域、电源完整性约束、敏感的模拟信号布线要求，以及由制造和封装规则施加的布局限制。简单的脚本方法缺乏处理这种复杂性的推理能力，因此大部分设计工作留给了人类工程师。

These include diverse signal types, multiple power domains, power integrity constraints, sensitive analog signal routing requirements, and layout restrictions imposed by fabrication and packaging rules. Simple scripting approaches lack the reasoning capability to handle such complexity, leaving much of the design effort to human engineers.

> 因此，AMS I/O 设计是劳动密集型的，大部分努力几乎不可复用。在引线键合封装芯片中（图 1），一名新手工程师可能需要花一到两天时间来学习、手工组装和验证 I/O 放置与连接。迭代性的引脚变更往往导致临近流片时的破坏性返工风险。这些挑战凸显了对智能自动化的需求，而大语言模型（LLM）的最新进展为此提供了有希望的基础。

As a result, AMS I/O design is labor-intensive, with most effort rarely reusable. In wirebond-packaged chips (Fig. 1), a novice engineer may spend one or two days on studying, manually assembling, and verifying I/O placement and connections. Iterative pin changes often lead to disruptive rework risks, which intensify as tape-out approaches. These challenges highlight the need for intelligent automation, for which recent advances in large language models (LLMs) offer a promising foundation.

> 虽然 LLM 在多个硬件设计任务中展现了有希望的能力（Chen et al. 2024; Fang et al. 2025），但它们在 AMS I/O 设计中的应用仍未被充分探索，原因在于三个关键挑战：(1) 缺乏可获取的领域知识，这些知识通常局限于团队特定的实践和分散的内部文档中；(2) 缺乏标准化的任务接口，因为交互仍然依赖 GUI 或预训练 LLM 不熟悉的领域特定语言；(3) 缺乏公开的基准测试，阻碍了系统性评估。

While LLMs have shown promising capabilities across several hardware design tasks (Chen et al. 2024; Fang et al. 2025), their application to AMS I/O design remains underexplored due to three key challenges: (1) the lack of accessible domain knowledge, which is typically confined to team-specific practices and scattered internal documents, (2) the absence of standardized task interfaces, as interaction still relies on GUI or domain-specific languages unfamiliar to pretrained LLMs, and (3) the unavailability of public benchmarks, which hinders systematic evaluation.

> 为了弥合这一差距，我们提出了 AMS-IO-Agent，一个面向领域的、基于 LLM 的智能体，用于结构感知的 AMS I/O 生成。它集成了两个核心能力：(1) 一个领域知识库，由碎片化的工程实践构建而成，捕获可复用的约束和布局惯例，这些知识来源于一个由 10 余名工程师组成的专业 AMS IC 设计团队开发的真实培训材料，并通过 50 余次成功流片案例验证；

To bridge this gap, we propose AMS-IO-Agent, a domain-specialized LLM-based agent for structure-aware AMS I/O generation. It integrates two core capabilities: (1) a domain knowledge base built from fragmented engineering practices, capturing reusable constraints and layout conventions, curated from real training materials developed by a professional AMS IC design team of more than 10 engineers and validated through over 50 successful tape-out cases;

> (2) 设计意图结构化，将模糊的设计意图转换为可验证的逻辑步骤作为中间格式，如图 2 所示。这些组件共同使智能体能够通过将生成建立在先验示例和领域约束之上，从而适应不同项目。

(2) design intent structuring, which converts ambiguous design intent into verifiable logic steps as an intermediate format, as shown in Fig. 2. Together, these components allow the agent to adapt across projects by grounding generation in prior examples and domain constraints.

> 为了支持一致的评估，我们还引入了 AMS-IO-Bench，一个面向引线键合封装 AMS I/O 环的基准测试。它涵盖了 I/O 环组装和验证等关键任务，用于评估生成设计的正确性、适应性和效率。据我们所知，这是首个针对真实世界 AMS IC I/O 环设计自动化提出基于 LLM 的智能体和综合评估基准的工作，也是首个能够作为关键模块直接集成到流片工作流中、与人类工程师协作的 AMS IC 设计 LLM 智能体。

To support consistent evaluation, we also introduce AMS-IO-Bench, a benchmark for wirebond-packaged AMS I/O rings. It covers key tasks such as I/O ring assembly and validation, and is used to assess the correctness, adaptability, and efficiency of generated designs. To the best of our knowledge, this is the first work to propose an LLM-based agent and comprehensive evaluation benchmark specifically targeting real-world AMS IC I/O ring design automation, and the first LLM-based agent for AMS IC design capable of direct integration into tape-out workflows as a key module collaborating with human engineers.

> 在 AMS-IO-Bench 上的实验表明，AMS-IO-Agent 实现了超过 70% 的 DRC+LVS 通过率，大幅超越基线 LLM，并将设计周转时间从数天缩短到每个案例仅需数分钟。值得注意的是，我们在真实的工业流片项目中验证了我们的系统：由 AMS-IO-Agent 生成的 I/O 环被无缝集成到商业 AMS IC 流程中，并在硅芯片上成功制造。这不仅证明了我们方法的实用性和鲁棒性，也证明了其在真实世界芯片设计流程中部署的成熟度。

Experiments on AMS-IO-Bench show that AMS-IO-Agent achieves over 70% DRC+LVS pass rates, surpassing the baseline LLM by a large margin and reducing design turnaround time from days to just minutes per case. Notably, we validated our system in real industrial tape-out projects: I/O rings generated by AMS-IO-Agent were seamlessly integrated into commercial AMS IC flows and successfully fabricated on silicon. This demonstrates not only the practicality and robustness of our approach, but also its readiness for deployment in real-world chip design pipelines.

> **综上所述，本文做出了以下贡献：**

In summary, our work makes the following contributions:

> - 我们提出了一个自动化 AMS IC I/O 生成流水线，将任务形式化为结构化步骤：意图解释、约束求解和 EDA 脚本生成，实现了实用的自动化。
> - 我们引入了一种新颖的智能体架构，结合了领域特定知识库和结构化意图推理，支持在不同 AMS I/O 设计上下文中的泛化。
> - 我们开发了一个面向引线键合封装 AMS I/O 环自动化的基准测试，并表明智能体方法始终能交付实用设计，减少手工工作量和设计周转时间。
> - 我们进一步在实际 28-nm CMOS 流片中验证了该智能体，首次报道了基于 LLM 的智能体直接贡献于非平凡 AMS IC 设计任务的演示。

- We propose an automatic pipeline for AMS IC I/O generation, formalizing the task into structured steps: intent interpretation, constraint resolution, and generation of EDA scripts, enabling practical automation.
- We introduce a novel agent architecture that combines domain-specific knowledge base and structured intent reasoning, supporting generalization across diverse AMS I/O design contexts.
- We develop a benchmark for wirebond-packaged AMS I/O ring automation, and show that the agent approach consistently delivers practical designs, reducing manual workload and design turnaround time.
- We further validate the agent in a real 28-nm CMOS tape-out, achieving the first reported demonstration of an LLM-based agent directly contributing to a nontrivial AMS IC design task.

---

## 2. 相关工作 (Related Work)

### 2.1 面向 IC 设计自动化的 LLM 方法 (LLM-based Approaches for IC Design Automation)

> LLM 已被应用于多种 EDA 任务，从基于知识的问答（Shi et al. 2024; Skelic et al. 2025）和寄存器传输级（RTL）代码生成（Chang et al. 2023; Blocklove et al. 2023; Thakur et al. 2023; Liu et al. 2023; Xu et al. 2024; Liu et al. 2024b; Tsai, Liu, and Ren 2024; Thakur et al. 2024; Fu et al. 2025），到网表综合（Lai et al. 2024）、电路优化（Yin et al. 2024; Ghose et al. 2025）以及 EDA 脚本生成（Chen et al. 2025）。为了超越单次代码合成，最近的研究采用了智能体架构，将 LLM 集成到迭代设计循环中（Wu et al. 2024; Ho and Ren 2024; Liu et al. 2025, 2024a; Ghose et al. 2025）。通过调用工具、观察结果并优化输出，这些智能体在多步骤工作流中展现了前景。

LLMs have been applied to a variety of EDA tasks, from knowledge-based question answering (Shi et al. 2024; Skelic et al. 2025) and register-transfer level (RTL) code generation (Chang et al. 2023; Blocklove et al. 2023; Thakur et al. 2023; Liu et al. 2023; Xu et al. 2024; Liu et al. 2024b; Tsai, Liu, and Ren 2024; Thakur et al. 2024; Fu et al. 2025) through netlist synthesis (Lai et al. 2024), circuit optimization (Yin et al. 2024; Ghose et al. 2025), to EDA script generation (Chen et al. 2025). To extend beyond one-shot code synthesis, recent studies adopt agent architectures that integrate LLMs into iterative design loops (Wu et al. 2024; Ho and Ren 2024; Liu et al. 2025, 2024a; Ghose et al. 2025). By invoking tools, observing results, and refining their outputs, these agents show promise for multi-step workflows.

> 然而，这些进展并未减轻 AMS IC 设计中重复性、约束繁重的日常任务，因为它们缺乏对真实设计流程的系统性适应和流片验证。因此，约束丰富、项目特定的任务仍然主要依赖手工完成，LLM 自动化这些任务的潜力仍未开发。

Nevertheless, these advances have not alleviated the repetitive, constraint-heavy routines in AMS IC design, as they lack systematic adaptation to real design flows and tape-out validation. As a result, constraint-rich, project-specific tasks remain largely manual, and the potential of LLMs to automate them is still untapped.

### 2.2 AMS IC 智能体的基准测试 (Benchmark for AMS IC Agents)

> 领域特定数据集的稀缺性以及精确定义 AMS IC 设计任务的内在困难，使得定量评估尤为具有挑战性。对于仅涉及几个到十几个操作序列的相对简单的任务，数据集可以扩展到超过一千个实例（Liu et al. 2025）。相比之下，对于复杂的 AMS IC 任务，如网表或测试平台生成，现有数据集仅包含几十个高度复杂的示例（表 1）。这凸显了对紧密反映实际 AMS 设计需求的基准测试的需求，这与实践芯片工程师从有限数量的精心筛选示例中学习的方式一致。

The scarcity of domain-specific datasets and the inherent difficulty of precisely defining AMS IC design tasks make quantitative evaluation particularly challenging. For relatively straightforward tasks involving only a few to a few dozen operation sequences, datasets can scale to over one thousand instances (Liu et al. 2025). In contrast, for complex AMS IC tasks such as netlist or testbench generation, existing datasets contain only a few dozen highly intricate examples (Table 1). This highlights the need for benchmarks that closely reflect practical AMS design requirements, consistent with how practicing chip engineers learn from a limited number of carefully curated examples.

> **表 1：近期基于 LLM 的智能体研究中复杂 IC 设计任务的数据规模**

| 任务 (Task) | 数据规模 (Data Size) |
|---|---|
| Netlist Generation (Ho and Ren 2024) | 17 |
| Netlist Generation (Chen et al. 2025) | 24 |
| **AMS-IO-Bench (Ours)** | **30** |

### 2.3 I/O 环组装的自动化 (Automation in I/O Ring Assembly)

> 现有的 I/O 或焊盘环构建自动化方法要求设计者通过详细的配置表或元数据文件进行大量底层规范说明（Moseley, Barzic, and contributors 2025; Chen et al. 2021; Morita, Takiguti, and Noije 2015; Chen et al. 2010），使得这些工作流几乎与手工焊盘环组装一样劳动密集。这些方法主要针对数字 SoC 定制，对 AMS 特定需求（如电源域分离和定制模拟焊盘单元）提供有限支持；满足这些约束通常需要直接修改底层脚本或工具代码。

Existing automation methods for I/O or padring construction require designers to perform extensive low-level specification through detailed configuration tables or metadata files (Moseley, Barzic, and contributors 2025; Chen et al. 2021; Morita, Takiguti, and Noije 2015; Chen et al. 2010), making these workflows nearly as labor-intensive as manual padring assembly. These approaches are largely tailored for digital SoCs and offer limited support for AMS-specific needs such as power domain separation and custom analog pad cells; accommodating such constraints often requires direct modification of low-level scripts or tool code.

> 这些方法中没有一种包含语义解释或设计意图理解，而是依赖显式指定的参数。它们的输出也仅限于几何文件（如 GDS），设计者无法直接编辑。因此，这些方法运行在不同的抽象层级上，不能为 AMS I/O 环组装提供直接可比的基线。

None of these methods incorporates semantic interpretation or design-intent understanding, relying instead on explicitly specified parameters. Their outputs are also limited to geometric files such as GDS that cannot be directly edited by designers. Consequently, these methods operate at a different abstraction level and do not offer a directly comparable baseline for AMS I/O ring assembly.

---

## 3. 方法 (Method)

### 3.1 任务定义 (Task Definition)

> AMS I/O 生成被定义为将人类提供的引脚规划规范转换为 EDA 工具中可生产的原理图和布局，作为一个约束驱动的工程任务，侧重于满足设计意图并确保符合所有设计规则，而非性能或面积优化。

AMS I/O generation is defined as transforming human-provided pin planning specifications into production-ready schematics and layouts in EDA tools, as a constraint-driven engineering task focused on fulfilling design intent and ensuring compliance with all required design rules rather than performance or area optimization.

> 输入包括引脚规划规范，通常以表格或文本描述表示，定义 I/O 环的尺寸、引脚名称和排序，以及可能的附加自然语言需求，如电源域分离或自定义器件使用。

The input consists of pin planning specifications, typically expressed as tables or textual descriptions, defining I/O ring dimensions, pin names and ordering, and possibly additional requirements in natural language such as power domain separation or custom device usage.

> 输出是一套完整的可生产的原理图和布局，可直接集成到 AMS IC 设计流程中，如图 3 所示。生成的结果必须符合预期的几何形状和引脚排列，保持通过布局与原理图对比（LVS）验证的严格电气对应性，并满足通过设计规则检查（DRC）验证的所有物理设计规则和可制造性要求。

The output is a complete set of production-ready schematics and layouts that can be directly integrated into the AMS IC design flow, as illustrated in Fig. 3. The generated results must conform to the intended geometry and pin arrangement, maintain strict electrical correspondence verified by Layout Versus Schematic (LVS) checks, and satisfy all physical design rules and manufacturability requirements verified by Design Rule Check (DRC).

### 3.2 智能体概述 (Agent Overview)

> 如图 3 所示，AMS-IO-Agent 是一个基于 LLM 的智能体，通过结构化意图图和意图图适配器的结构化流水线，将自然语言设计意图与可执行 EDA 脚本相连接。该智能体由三个关键组件组成：

As illustrated in Fig. 3, AMS-IO-Agent is an LLM-based agent that bridges natural language design intent and executable EDA scripts through a structured pipeline of structured intent graph and intent graph adaptor. The agent consists of three key components:

> - **设计意图结构化 (Design Intent Structuring)：** 将自然语言或半结构化规范（如带有文本约束的引脚列表）转换为机器可读的图，显式表示器件配置、空间关系和电气连接。
> - **意图图适配器 (Intent Graph Adaptor)：** 解析意图图以求解约束、执行几何计算并导出实现参数，将结构化意图转换为可执行过程。
> - **领域特定知识库 (Domain-Specific Knowledge Base)：** 提供设计规则、器件规范和布局惯例，用于约束检查以及与 AMS I/O 实践的设计一致性。

- **Design Intent Structuring:** Converts natural language or semi-structured specifications, such as pin lists with textual constraints, into a machine-readable graph that explicitly represents device configurations, spatial relationships, and electrical connections.
- **Intent Graph Adaptor:** Parses the intent graph to resolve constraints, perform geometric calculations, and derive implementation parameters, transforming structured intent into executable procedures.
- **Domain-Specific Knowledge Base:** Provides design rules, device specifications, and layout conventions for constraint checking and design consistency with AMS I/O practices.

> 这种分层架构将高层意图推理与底层实现分离，使 LLM 专注于理解设计意图，而确定性模块确保约束求解和可复现的脚本生成。

This layered architecture separates high-level intent reasoning from low-level implementation, allowing the LLM to focus on understanding design intent while deterministic modules ensure constraint resolution and reproducible script generation.

### 3.3 设计意图结构化 (Design Intent Structuring)

> AMS I/O 设计通常起始于非正式规范，如自然语言描述、引脚列表或半结构化电子表格，这些包含必要的设计信息，但缺乏自动化处理所需的结构。为了解决这一问题，AMS-IO-Agent 将这些输入转换为标准化的意图图。

AMS I/O design often begins with informal specifications such as natural language descriptions, pin lists, or semi-structured spreadsheets, which contain essential design information but lack the structure required for automated processing. To address this gap, AMS-IO-Agent converts these inputs into a standardized intent graph.

> 意图图是一种基于 JSON 的表示，将 I/O 环建模为一系列互联节点的序列，每个节点代表一个焊盘或角单元，具有名称、器件类型、空间位置、方向和引脚连接等属性（图 4）。位置编码遵循 I/O 环布局，保留其物理组织结构。

The intent graph is a JSON-based representation that models the I/O ring as a sequence of interconnected nodes, each representing a pad or corner cell with attributes such as name, device type, spatial position, direction, and pin connections (Figure 4). Position encoding follows the I/O ring layout, preserving its physical organization.

> 意图图的构建结合了显式补全和隐式推理。显式补全应用于规范中提供了名称的引脚。在实践中，设计者通常使用约定缩写，如 DCLK（数字时钟）、VCM（共模电压）和 VREFN（参考电压 N 侧）。通过领域特定知识库利用这些模式，智能体可以推断额外的属性，包括信号类型、器件类型、默认方向和引脚连接。这些连接通常不需要用户显式指定，但在需要时支持显式用户覆盖。隐式推理用于完全没有提及的元素，如角单元，它们根据标准设计惯例自动插入，无需任何用户输入。

The construction of the intent graph combines explicit completion and implicit inference. Explicit completion is applied to pins whose names are provided in the specification. In practice, designers often use conventional abbreviations such as DCLK (digital clock), VCM (common-mode voltage) and VREFN (N-side of reference voltage). By leveraging these patterns through the domain-specific knowledge base, the agent can infer additional attributes, including signal type, device type, default direction, and pin connections. These connections typically do not need to be specified explicitly by the user, although explicit user overrides are supported when required. Implicit inference is used for elements that are not mentioned at all, such as corner cells, which are automatically inserted based on standard design conventions without any user input.

> 这种表示与网表有根本性的不同，并作为中间件处理的基础。网表仅描述电路连接性，而意图图还捕获空间关系、语义上下文和领域知识。它可以被人类和语言模型直接理解，并可以被代码高效解析和处理。这种双重可访问性使其成为非正式设计输入与自动化实现之间的有效接口。

This representation is fundamentally different from a netlist and serves as the basis for middleware processing. While a netlist only describes circuit connectivity, the intent graph also captures spatial relationships, semantic context, and domain knowledge. It can be directly understood by both humans and language models, and it can be efficiently parsed and processed by code. This dual accessibility makes it an effective interface between informal design inputs and automated implementation.

### 3.4 意图图适配器 (Intent Graph Adaptor)

> 意图图适配器作为中间件层，连接基于 LLM 的智能体与商业 EDA 工具。它支持结构化意图图完成 EDA 代码生成，并解决了 AMS I/O 设计中直接代码生成的局限性。

The Intent Graph Adaptor serves as a middleware layer that bridges the LLM-based agent and commercial EDA tools. It supports the structured intent graph in completing EDA code generation and addresses the limitations of direct code generation for AMS I/O design.

> 直接使用 LLM 生成领域特定语言（DSL）脚本（如 SKILL）无法产生正确且一致的输出，因为缺乏足够的训练数据。同样，使用这些 DSL 来执行解析意图图的逻辑操作也是不切实际的，因为这些语言并非为复杂数据操作而设计。为克服这些问题，适配器采用基于 Python 的中间件进行确定性处理，包括结构化数据解析、约束求解、几何计算和 DSL 脚本生成。

Directly generating domain-specific language (DSL) scripts such as SKILL with an LLM is ineffective for producing correct and consistent outputs due to the lack of sufficient training data. Likewise, using these DSLs themselves to perform logical operations for parsing the intent graph is impractical because such languages are not designed for complex data manipulation. To overcome these issues, the adaptor employs Python-based middleware for deterministic processing, including structured data parsing, constraint resolution, geometric calculations, and DSL script generation.

> 虽然原则上中间件工具可以每次由 LLM 生成，但这种方法效率低下且鲁棒性差。相反，将它们实现为可复用的工具库，使智能体能够调用确定性脚本进行结构化数据解析、约束求解、几何计算和 DSL 脚本生成。在收到意图图后，它提取 I/O 实例及其属性，并根据 I/O 设计规则计算精确的单元坐标。

Although the middleware tools could, in principle, be generated by the LLM for every run, this approach suffers from low efficiency and poor robustness. Instead, implementing them as a reusable tool library allows the agent to invoke deterministic scripts for structured data parsing, constraint resolution, geometric calculations, and DSL script generation. Upon receiving the intent graph, it extracts I/O instances with their attributes and computes precise cell coordinates based on I/O design rules.

> 为了与商业 EDA 工具集成，适配器生成 SKILL 脚本以在 Cadence Virtuoso 中创建原理图和布局，并生成 csh 脚本以调用 Siemens Calibre 验证工具。这些组件共同构成了 LLM 生成的意图图与可流片的 AMS I/O 设计流程之间可复现且可验证的桥梁。

For integration with commercial EDA tools, the adaptor generates SKILL scripts to create schematics and layouts in Cadence Virtuoso and csh scripts to invoke Siemens Calibre verification tools. Together, these components form a reproducible and verifiable bridge between the LLM-generated intent graph and tape-out-ready AMS I/O design flows.

### 3.5 领域特定知识库 (Domain-Specific Knowledge Base)

> 领域特定知识库解决了 AMS I/O 设计中的一个关键挑战：设计专业知识高度碎片化，通常埋藏在非正式的自然语言文档中，如培训笔记、参考指南和内部设计手册。这些材料涵盖器件选择实践、布局惯例、电源域规则、ESD 保护需求、命名规范、常见设计技术和从实际项目中积累的实践"诀窍"。

The domain-specific knowledge base addresses a key challenge in AMS I/O design: design expertise is highly fragmented and often buried in informal natural-language documents such as training notes, reference guides, and internal design manuals. These materials encompass device selection practices, layout conventions, power domain rules, ESD protection requirements, naming conventions, common design techniques, and practical "know-how" accumulated from real projects.

> 为了整合这些专业知识，AMS-IO-Agent 采用了一个知识库，该知识库由一支拥有 10 余名经验丰富工程师的专业 AMS IC 设计团队的培训材料和文档化实践构建而成，并通过 50 余次成功流片案例验证。该知识库反映了用于培训入门级工程师的相同材料，具有本科背景的工程师通常可在一到三天内掌握，确保了其实用性和可获取性。

To consolidate this expertise, AMS-IO-Agent employs a knowledge base built from the training materials and documented practices of a professional AMS IC design team of more than 10 experienced engineers, validated through over 50 successful tape-out cases. This knowledge base reflects the same materials used to train entry-level engineers, which can typically be mastered by engineers with an undergraduate background within one to three days, ensuring both its practicality and accessibility.

> AMS-IO-Agent 没有将这一知识转化为刚性的规则代码，而是将其组织为一个约 6k token 的轻量级仓库。该仓库既可作为人类设计者的参考，也可作为 LLM 的上下文知识源。由于其紧凑的规模，LLM 可以直接使用它，无需检索机制或模型微调。

Instead of converting this knowledge into rigid rule code, AMS-IO-Agent organizes it into a lightweight repository of approximately 6k tokens. This repository serves both as a reference for human designers and as an in-context knowledge source for the LLM. Because of its compact size, the LLM can directly consume it without retrieval mechanisms or model fine-tuning.

> 通过将经过验证的实际设计工作流专业知识集成到单一可获取的知识库中，该系统使人类和机器用户都能利用相同的权威工程知识，将人类可读的文档与意图解释和约束求解过程中的自动化、上下文驱动的推理相结合。

By integrating verified expertise from actual design workflows into a single accessible knowledge base, the system enables both human and machine users to leverage the same authoritative engineering knowledge, combining human-readable documentation with automated, context-driven reasoning during intent interpretation and constraint resolution.

---

## 4. 基准测试 (Benchmark)

> 目前 AMS I/O 生成尚无标准评估框架或公开可用的数据集。为解决这一问题，我们开发了 AMS-IO-Bench，首个专门面向引线键合封装 AMS IC 芯片 I/O 环生成的基准测试套件。虽然存在其他封装方法（如带焊料凸点的倒装芯片），但引线键合仍然是原型验证芯片最常用的方法。由于引线键合需要沿芯片边界的周边 I/O 环，它为评估 I/O 规划提供了清晰且定义明确的上下文，使其成为我们基准测试最实用的选择。

There is currently no standard evaluation framework or publicly available dataset for AMS I/O generation. To address this gap, we develop AMS-IO-Bench, the first benchmark suite dedicated to I/O ring generation for wirebond-packaged AMS IC chips. Although other packaging methods such as flip-chip with solder bumps exist, wirebond remains the most commonly used approach for prototype verification chips. Because wirebond requires peripheral I/O rings along the chip boundary, it provides a clear and well-defined context for evaluating I/O planning, making it the most practical choice for our benchmark.

> AMS-IO-Bench 源自过去 5 年收集的 10 个真实流片项目的 I/O 规划。从这些项目中，我们通过简化、增强和转换原始设计构建了 30 个案例的基准测试，确保每个案例保留生产流程的核心约束和设计模式。这种方法同时实现了真实性和可复现性。每个基准实例提供一个结构化的焊盘位置列表，指定信号分配、电源域和布线提示。

AMS-IO-Bench is derived from the I/O planning of 10 real tape-out projects collected over the past 5 years. From these projects, we construct a benchmark of 30 cases by simplifying, augmenting, and transforming the original designs, ensuring that each case preserves the core constraints and design patterns of production flows. This approach enables both realism and reproducibility. Each benchmark instance provides a structured pad location list specifying signal assignments, power domains, and routing hints.

> 基准测试按三个难度级别组织，如表 2 所示：

The benchmark is organized into three difficulty levels, as shown in Table 2.

> **表 2：AMS-IO-Bench 中的三个难度级别**

| 级别 (Level) | 数量 (Number) | 真实性 (Realism) | 特征 (Features) |
|---|---|---|---|
| **简单 (Simple)** | 10 | 简化 (Simplified) | 小尺寸，单信号域 |
| **中等 (Medium)** | 10 | 默认 (Default) | 标准尺寸，多电源域 |
| **困难 (Hard)** | 10 | 复杂 (Complex) | 大尺寸，交错排列，定制单元 |

> - **简单 (Simple)。** 简单案例使用单一信号域，因此无需隐式推理隔离和局部 ESD 电源。它们通过对典型 AMS IC 设计进行简化而得到。
> - **中等 (Medium)。** 中等难度案例反映典型 AMS IC 设计的默认复杂度。每个案例对应约 1mm × 1mm 的标准 MPW 芯片轮廓，具有单排 I/O 环。I/O 环被划分为多个电源域，包括数字和模拟，每个域由不同的器件类型、设计规则、填充单元和隔离单元管理。求解这些案例需要智能体对领域知识和上下文约束进行推理，与流片项目中遇到的真实世界挑战紧密匹配。
> - **困难 (Hard)。** 困难案例代表复杂流片中遇到的高级场景。包括双排或部分双排 I/O 环（交错焊盘）、具有扩大轮廓（默认尺寸的 1.5 到 2 倍或更大）的芯片、定制 I/O 单元（如具有降低 ESD 电容的模拟 I/O 单元），以及具有高度专门化电源域配置（如局部 ESD 供电）的设计。这些案例考验智能体对高度定制化设计需求的适应能力。

- **Simple.** Simple cases use a single signal domain, thereby removing the need for implicit reasoning about isolation and local ESD power supply. They are derived from typical AMS IC designs through simplification.
- **Medium.** Medium-difficulty cases reflect the default complexity of typical AMS IC designs. Each case corresponds to a standard MPW chip outline of approximately 1mm × 1mm with a single-row I/O ring. The I/O ring is partitioned into multiple power domains, including digital and analog, each governed by distinct device types, design rules, filler cells, and isolation cells. Solving these cases requires the agent to reason over domain knowledge and contextual constraints, closely matching the real-world challenges encountered in tape-out projects.
- **Hard.** Hard cases represent advanced scenarios observed in complex tape-outs. They include dual-row or partially dual-row I/O rings (staggered pads), chips with enlarged outlines (1.5× to 2× the default size or larger), custom I/O cells (e.g., analog I/O cells with reduced ESD capacitance), and designs with highly specialized power domain configurations such as localized ESD power delivery. These cases stress the adaptability of agents to highly customized design requirements.

> 通过聚焦于真实世界约束和垂直领域特异性，AMS-IO-Bench 建立了一个实用且可扩展的平台，用于在真实芯片开发条件下评估 AMS I/O 设计智能体。

By focusing on real-world constraints and vertical domain specificity, AMS-IO-Bench establishes a practical and scalable platform for evaluating AMS I/O design agents under realistic chip development conditions.

---

## 5. 实验 (Experiments)

### 5.1 实验设置 (Setup)

> 我们使用基于 Python 的自动化框架 smolagents 实现并评估了所提出的 AMS-IO-Agent。骨干语言模型通过 API 访问。智能体在工作站上运行，通过 SSH 和套接字连接与芯片设计服务器工作站通信。

We implement and evaluate the proposed AMS-IO-Agent using the Python-based automation framework smolagents. The backbone language model is accessed via API. The agent runs on a workstation and communicates with chip-design server workstations via SSH and socket connections.

> 智能体调用的工具用 Python 实现。为了与商业 EDA 工具链集成，智能体接收设计意图描述作为输入，生成用于原理图和布局创建的 SKILL 脚本，并在 Cadence Virtuoso 中执行它们。布局验证和物理规则检查通过 csh 脚本调用 Siemens Calibre 来执行。评估遵循前述的 AMS-IO-Benchmark 方法。

The tools invoked by the agent are implemented in Python. For integration with commercial EDA toolchains, the agent receives design intent descriptions as input, generates SKILL scripts for schematic and layout creation, and executes them in Cadence Virtuoso. Layout verification and physical rule checks are performed by invoking Siemens Calibre through csh scripts. The evaluation follows the AMS-IO-Benchmark methodology described earlier.

### 5.2 评估指标 (Evaluation Metrics)

> 我们使用覆盖从意图解释到布局验证的整个过程的五阶段流水线评估 AMS-IO-Agent。每个指标针对一个不同的阶段，实现系统性诊断和定量质量评估。

We evaluate AMS-IO-Agent using a five-stage pipeline covering the entire process from intent interpretation to layout verification. Each metric targets a distinct stage, enabling systematic diagnosis and quantitative quality assessment.

> - **指标 1：意图图通过率 (Intent Graph Pass Rate)** — 检查智能体是否正确地将自然语言规范转换为有效的意图图，包括正确的焊盘命名、器件类型分配和属性补全。失败表明对设计需求的理解有误。
> - **指标 2：形状得分 (Shape Score)** — 使用视觉语言模型（VLM）量化布局相似性，基于与参考的结构对齐执行二值评估（通过或失败）。它捕获超越基于规则评估的视觉和拓扑正确性。
> - **指标 3：DRC 通过率 (DRC Pass Rate)** — 报告通过所有晶圆厂指定设计规则（如间距、宽度、包围）的布局百分比，反映物理可制造性。
> - **指标 4：LVS 通过率 (LVS Pass Rate)** — 检查原理图与布局之间的电气等价性，确保正确的连接性，无开路、短路或不匹配。
> - **指标 5：DRC+LVS 通过率 (DRC+LVS Pass Rate)** — 代表可生产质量，作为整体有效性指标。

- **Metric 1: Intent Graph Pass Rate** checks whether the agent correctly converts natural language specifications into valid Intent Graphs, including proper pad naming, device type assignment, and attribute completion. Failures indicate misunderstanding of design requirements.
- **Metric 2: Shape Score** quantifies layout similarity using a Vision-Language Model (VLM), which performs a binary evaluation (pass or fail) based on structural alignment with the reference. It captures visual and topological correctness beyond rule-based evaluation.
- **Metric 3: DRC Pass Rate** reports the percentage of layouts passing all foundry-specified design rules (e.g., spacing, width, enclosure), reflecting physical manufacturability.
- **Metric 4: LVS Pass Rate** checks electrical equivalence between schematic and layout, ensuring correct connectivity without opens, shorts, or mismatches.
- **Metric 5: DRC+LVS Pass Rate** represents production-ready quality and serves as the overall effectiveness metric.

> 这些指标共同提供了一个综合评估框架，涵盖高层意图解释和底层物理验证。

Together, these metrics provide a comprehensive evaluation framework spanning high-level intent interpretation and low-level physical validation.

### 5.3 主要结果 (Main Results)

> 我们在 AMS-IO-Bench 上评估 AMS-IO-Agent，结果总结在表 3 中。在不同骨干模型上，AMS-IO-Agent 实现了 100% 的意图图翻译和形状有效性，同时保持较高的 DRC 和 LVS 通过率。即使对于完整的 DRC+LVS 签核，智能体最高达到 76.7%（30 个案例中的 23 个），展示了在最少人工努力下向可生产级布局生成的实质性进展。

We evaluate AMS-IO-Agent on AMS-IO-Bench, with results summarized in Table 3. Across different backbone models, AMS-IO-Agent achieves 100% intent graph translation and shape validity, while maintaining high DRC and LVS pass rates. Even for full DRC+LVS signoff, the agent reaches up to 76.7% (23 out of 30 cases), demonstrating substantial progress toward production-ready layout generation with minimal human effort.

> **表 3：AMS-IO-Agent 实现完美的意图翻译和形状有效性、高 DRC/LVS 通过率，并将设计时间从数小时缩短到数分钟，优于基线 LLM，同时比专家手工设计高效得多。**

| 方法 (Method) | IG (%) | Shape (%) | DRC (%) | LVS (%) | DRC+LVS (%) | 时间 (min) | Token (k) |
|---|---|---|---|---|---|---|---|
| 人类 (Human) | 100 | 100 | 100 | 100 | 100 | ≈ 480 | – |
| LLM (GPT-4o) | 0 | 0 | 0 | 0 | 0 | 0.2 | 1k |
| AMS-IO-Agent (GPT-4o) | 100 | 100 | 76.67 | 66.67 | 63.33 | 4.1 | 160k |
| AMS-IO-Agent (Claude-3.7) | 100 | 100 | 93.33 | 76.67 | 76.67 | 4.2 | 96k |
| AMS-IO-Agent (DeepSeek-V3) | 100 | 100 | 93.33 | 76.67 | 76.67 | 5.1 | 105k |

> 与通常每个任务需要约 480 分钟的手工设计相比，智能体将周转时间缩短到仅几分钟，并显著优于基线 LLM，token 使用量保持在 200k 以下，使其适用于工业部署。这些结果表明，AMS-IO-Agent 在功能设计正确性方面比基线方法实现了显著的效率提升和大幅改进。

Compared to manual design, which typically requires around 480 minutes per task, the agent reduces turnaround time to only a few minutes and significantly outperforms baseline LLMs, with token usage remaining below 200k, making it practical for industrial deployment. These results show that AMS-IO-Agent delivers a major efficiency boost while substantially improving functional design correctness over baseline methods.

### 5.4 错误处理 (Error Handling)

> 考虑到流片的高成本（每 mm² 超过 $10k）和长制造时间（约三个月），人类工程师在智能体流水线中保持参与，主要作为审查者。在执行过程中或通过 DRC 和 LVS 检测到的不可行案例，可以通过提示优化或微小的 EDA 编辑在几分钟内解决，这说明了生成可编辑的中间交付物而非固定几何输出的优势。

Given the high cost (greater than $10k per mm²) and long fabrication time (about three months) of tape-out, human engineers remain in the agent pipeline and primarily serve as reviewers. Infeasible cases detected during execution or through DRC and LVS can be resolved within minutes via prompt refinement or minor EDA edits, illustrating the advantage of generating editable intermediate deliverables rather than fixed geometric outputs.

### 5.5 消融实验 (Ablation)

> 我们进一步进行了消融研究，以评估 AMS-IO-Agent 每个组件的贡献，如表 4 所示。人类时间通过与 16 名博士级设计者的访谈估算。没有知识库（KB）、意图图（IG）或适配器，智能体完全无法生成有效输出，凸显了组合所有三个组件的必要性。仅使用知识库可以实现一些基本形状组装，但 DRC 通过率低且无 LVS 签核，表明仅靠设计规则不足，缺乏结构化推理。同样，使用意图图而不使用适配器允许智能体生成语法有效的意图表示，但无法将其转化为签核质量的实现。只有完整配置（集成 KB、IG 和适配器）实现了意图图和形状 100%，DRC 93.33%，DRC+LVS 76.67%，同时将运行时间降至 5.1 分钟，token 使用量适中（105k）。这些结果确认了三个组件是互补的，并且对于实用的 AMS I/O 设计自动化共同至关重要。

We further conduct an ablation study to assess the contribution of each component of AMS-IO-Agent, as shown in Table 4. Human time was estimated from interviews with 16 PhD level designers. Without the knowledge base (KB), intent graph (IG), or adaptor, the agent completely fails to generate valid outputs, highlighting the necessity of combining all three components. Using only the knowledge base enables some basic shape assembly but results in low DRC and no LVS signoff, indicating that design rules alone are insufficient without structured reasoning. Similarly, employing the intent graph without the adaptor allows the agent to generate syntactically valid intent representations but fails to translate them into signoff-quality implementations. Only the full configuration, integrating KB, IG, and the adaptor, achieves 100% in intent graph, shape, 93.33% in DRC, and 76.67% in DRC+LVS, while reducing runtime to 5.1 minutes with modest token usage (105k). These results confirm that the three components are complementary and jointly essential for practical AMS I/O design automation.

> **表 4：使用 DeepSeek-V3 的消融结果表明，知识库和结构化意图适配器都是必不可少的：移除任一组件都会消除签核正确性。**

| KB | IG | Adaptor | IG (%) | Shape (%) | DRC (%) | LVS (%) | DRC+LVS (%) | Time (min) | Token (k) |
|---|---|---|---|---|---|---|---|---|---|
| × | × | × | – | 0 | 0 | 0 | 0 | 0.2 | 1 |
| ✓ | × | ×† | – | 0 | 0 | 0 | 0 | 16.2 | 1,098 |
| ✓ | × | ✓†† | – | 100 | 20.00 | 0 | 0 | 27.4 | 2,036 |
| ✓ | ✓ | × | 100 | 0 | 0 | 0 | 0 | 2.3††† | 18 |
| **✓** | **✓** | **✓** | **100** | **100** | **93.33** | **76.67** | **76.67** | **5.1** | **105** |

> † LLM 直接生成 SKILL 代码，无结构化意图推理。
> †† LLM 生成用于 SKILL 生成的 Python 代码，无结构化意图推理。
> ††† 运行时间缩短是因为无法调用 LVS/DRC 工具。

† LLM directly generates SKILL code without structured intent reasoning.
†† LLM generates Python code for SKILL generation without structured intent reasoning.
††† Reduced runtime because LVS/DRC tools cannot be invoked.

### 5.6 不同难度的表现

> 表 5 展示了不同难度级别的结果。所有模型在简单案例上都取得成功，但在中等和困难案例上表现下降，验证了基准测试的难度分级反映了真实的设计复杂度。

Table 5 shows results across difficulty levels. All models succeed on simple cases, but their performance declines on medium and hard cases, validating that the benchmark's difficulty scaling reflects real design complexity.

> **表 5：不同模型在 AMS-IO-Bench 各难度级别的 DRC+LVS 通过率**

| 模型 (Model) | 简单 (Simple) | 中等 (Medium) | 困难 (Hard) |
|---|---|---|---|
| GPT-4o | 10/10 | 7/10 | 2/10 |
| Claude-3.7 | 10/10 | 9/10 | 4/10 |
| DeepSeek-V3 | 10/10 | 10/10 | 3/10 |

### 5.7 案例研究 (Case Study)

> 为了展示 AMS-IO-Agent 的真实世界适用性，我们对一个采用 28-nm CMOS 技术的原型流片项目进行了案例研究，该项目涉及一个 1 mm × 1 mm 的引线键合封装混合信号 IC，具有 48 个 I/O 焊盘（每边 12 个）和多个电源及信号域。如图 5 所示，内部 AMS 核心由两名人类设计者实现，而周围的 I/O 环由我们的智能体生成。这种明确的分工凸显了智能体与既定设计工作流的无缝集成。

To demonstrate the real-world applicability of AMS-IO-Agent, we conducted a case study on a prototype tape-out project implemented in 28-nm CMOS technology, involving a 1 mm × 1 mm wirebond-packaged mixed-signal IC with 48 I/O pads (12 per side) and multiple power and signal domains. As illustrated in Figure 5, the inner AMS core was implemented by two human designers, while the surrounding I/O ring was generated by our agent. This clear division of labor highlights the agent's seamless integration into established design workflows.

> 在设计过程中，引入了一次重大的引脚顺序变更，需要滑动和重新排列许多焊盘。虽然这种变更通常需要大量手工重绘，但智能体在几分钟内重新生成了完全更新且经过验证的布局。生成的 I/O 环与专家设计的质量相匹配，并迅速被设计团队采纳。

During the design process, a major pin-order change was introduced that required sliding and reordering many pads. While such a change would normally necessitate extensive manual redrawing, the agent regenerated a fully updated and verified layout within minutes. The resulting I/O ring matched expert-designed quality and was readily adopted by the design team.

> 最终设计（手工制作的 AMS 核心与智能体生成的 I/O 环相结合）通过了 LVS 和 DRC 并成功制造。硅测量确认了正确的功能。本案例研究表明，AMS-IO-Agent 可以在真实流片工作流中作为可生产级的模块使用，实现真正的人机协作设计，同时在后期迭代中显著减少手工返工工作量。

The final design, combining a manually crafted AMS core with the agent-generated I/O ring, passed LVS and DRC and was successfully fabricated. Silicon measurements confirmed correct functionality. This case study demonstrates that AMS-IO-Agent can serve as a production-ready module within real tape-out workflows, enabling true human-agent collaborative design while significantly reducing manual rework effort during late-stage iterations.

---

## 6. 结论 (Conclusion)

> 在本文中，我们提出了 AMS-IO-Agent，一个面向领域的、基于 LLM 的智能体，用于结构感知的 AMS I/O 生成，以及 AMS-IO-Bench 用于系统性评估。通过将精心策划的领域知识库与结构化意图表示相结合，我们的方法将非正式的引脚规划规范转换为可生产的 EDA 工作流。

In this work, we introduced AMS-IO-Agent, a domain-specialized LLM-based agent for structure-aware AMS I/O generation, together with AMS-IO-Bench for systematic evaluation. By combining a curated domain knowledge base with structured intent representation, our approach translates informal pin-planning specifications into production-ready EDA workflows.

> 在 AMS-IO-Bench 上的实验表明，AMS-IO-Agent 实现了 100% 的意图图正确性、100% 的布局形状有效性以及超过 70% 的 DRC+LVS 签核通过率，将设计周转时间从数天缩短到仅几分钟。此外，原型流片确认了智能体能够与人类工程师无缝协作，适应后期引脚顺序变更，并交付适合真实世界芯片设计流程的签核质量 I/O 环。

Experiments on AMS-IO-Bench show that AMS-IO-Agent achieves 100% intent graph correctness, 100% layout shape validity, and over 70% DRC+LVS signoff pass rate, reducing design turnaround time from days to mere minutes. Moreover, a prototype tape-out confirms the agent's capability to seamlessly collaborate with human engineers, adapt to late-stage pin-order changes, and deliver signoff-quality I/O rings suitable for real-world chip design flows.

> 这些结果确立了部署基于 LLM 的智能体用于 AMS IC I/O 自动化的可行性，并为人机协同设计提供了具体基础。该方法广泛适用于表现出规则结构和语义有意义信号命名的 AMS 布局任务，并可通过替换知识库和执行适配器来适应其他工艺节点或封装风格。未来的工作将把这种方法扩展到更复杂的 AMS 设计任务，并实现与下游验证和布线工具的更深层次集成。

These results establish the feasibility of deploying LLM-based agents for AMS IC I/O automation and provide a concrete foundation for human-agent co-design. The methodology applies broadly to AMS layout tasks that exhibit regular structures and semantically meaningful signal naming, and can be adapted to other technology nodes or packaging styles by substituting the knowledge base and execution adaptor. Future work will extend this approach to more complex AMS design tasks and enable deeper integration with downstream verification and routing tools.

### 局限性与社会影响 (Limitation and Social Impact)

> 我们的方法专注于引线键合封装的 AMS I/O 环，并依赖针对特定设计惯例定制的领域知识库，这可能会限制对其他封装类型或晶圆厂规则的泛化。虽然 AMS-IO-Agent 减少了手工工作量，但它不能完全取代专家审查，特别是对于高度定制或非常规设计。

Our approach focuses on wirebond-packaged AMS I/O rings and relies on a domain knowledge base tailored to specific design conventions, which may limit generalization to other packaging types or foundry rules. While AMS-IO-Agent reduces manual workload, it cannot fully replace expert review, especially for highly customized or unconventional designs.

> 从社会角度来看，我们的方法可以提高生产力并降低 AMS IC 设计的门槛，但也可能改变对某些工程技能的需求。负责任的使用和人类监督对于确保真实世界芯片开发中的安全性和可靠性仍然至关重要。

From a social perspective, our method can boost productivity and lower barriers for AMS IC design, but may also shift the demand for certain engineering skills. Responsible use and human oversight remain essential to ensure safety and reliability in real-world chip development.

---

## 致谢 (Acknowledgments)

> 本研究得到国家自然科学基金（NSFC）博士生青年学者基础研究项目（Grant 624B2081）的资助。

This work was supported by National Science Foundation of China (NSFC) Young Scholar Basic Research Program for doctoral students (Grant 624B2081).

---

## 参考文献 (References)

1. Blocklove, J.; Garg, S.; Karri, R.; and Pearce, H. 2023. Chip-Chat: Challenges and Opportunities in Conversational Hardware Design. In *2023 ACM/IEEE 5th Workshop on Machine Learning for CAD (MLCAD)*, 1–6. IEEE.

2. Chang, K.; Wang, Y.; Ren, H.; Wang, M.; Liang, S.; Han, Y.; Li, H.; and Li, X. 2023. ChipGPT: How far are we from natural language hardware design. arXiv:2305.14019.

3. Chen, L.; Chen, Y.; Chu, Z.; Fang, W.; Ho, T.-Y.; Huang, R.; Huang, Y.; Khan, S.; Li, M.; Li, X.; Li, Y.; Liang, Y.; Liu, J.; Liu, Y.; Lin, Y.; Luo, G.; Pan, H.; Shi, Z.; Sun, G.; Tsaras, D.; Wang, R.; Wang, Z.; Wei, X.; Xie, Z.; Xu, Q.; Xue, C.; Yan, J.; Yang, J.; Yu, B.; Yuan, M.; Young, E. F. Y.; Zeng, X.; Zhang, H.; Zhang, Z.; Zhao, Y.; Zhen, H.-L.; Zheng, Z.; Zhu, B.; Zhu, K.; and Zou, S. 2024. Large circuit models: opportunities and challenges. *Science China Information Sciences*, 67(10).

4. Chen, S.-H.; et al. 2021. Pad Ring Generation for Integrated Circuits. U.S. Patent 11,055,457 B1. SiFive Inc.

5. Chen, W.; Liu, C.; Huang, W.; Lyu, J.; Yang, M.; Du, Y.; Du, L.; and Yang, J. 2025. AnalogTester: A Large Language Model-Based Framework for Automatic Testbench Generation in Analog Circuit Design. arXiv:2507.09965.

6. Chen, Y. P.; Srujana, S. T. L. N. V.; Patel, N.; Reddy, R. R. L.; Subramanian, S.; and Vallapaneni, V. R. 2010. Automated electrostatic discharge structure placement and routing in an integrated circuit. Filed Nov. 30, 2006; published Feb. 2, 2010.

7. Fang, W.; Wang, J.; Lu, Y.; Liu, S.; Wu, Y.; Ma, Y.; and Xie, Z. 2025. A Survey of Circuit Foundation Model: Foundation AI Models for VLSI Circuit Design and EDA. arXiv:2504.03711.

8. Fu, Y.; Zhang, Y.; Yu, Z.; Li, S.; Ye, Z.; Li, C.; Wan, C.; and Lin, Y. C. 2025. GPT4AIGChip: Towards Next-Generation AI Accelerator Design Automation via Large Language Models. arXiv:2309.10730.

9. Ghose, A.; Kahng, A. B.; Kundu, S.; and Wang, Z. 2025. ORFS-agent: Tool-Using Agents for Chip Design Optimization. arXiv:2506.08332.

10. Ho, C.-T.; and Ren, H. 2024. Large Language Model (LLM) for Standard Cell Layout Design Optimization. arXiv:2406.06549.

11. Lai, Y.; Lee, S.; Chen, G.; Poddar, S.; Hu, M.; Pan, D. Z.; and Luo, P. 2024. AnalogCoder: Analog Circuit Design via Training-Free Code Generation. arXiv:2405.14918.

12. Liu, B.; Zhang, H.; Gao, X.; Kong, Z.; Tang, X.; Lin, Y.; Wang, R.; and Huang, R. 2025. LayoutCopilot: An LLM-Powered Multiagent Collaborative Framework for Interactive Analog Layout Design. *IEEE Transactions on Computer-Aided Design of Integrated Circuits and Systems*, 44(8): 3126–3139.

13. Liu, M.; Ene, T.-D.; Kirby, R.; Cheng, C.; Pinckney, N.; Liang, R.; Alben, J.; Anand, H.; Banerjee, S.; Bayraktaroglu, I.; Bhaskaran, B.; Catanzaro, B.; Chaudhuri, A.; Clay, S.; Dally, B.; Dang, L.; Deshpande, P.; Dhodhi, S.; Halepete, S.; Hill, E.; Hu, J.; Jain, S.; Jindal, A.; Khailany, B.; Kokai, G.; Kunal, K.; Li, X.; Lind, C.; Liu, H.; Oberman, S.; Omar, S.; Pasandi, G.; Pratty, S.; Raiman, J.; Sarkar, A.; Shao, Z.; Sun, H.; Suthar, P. P.; Tej, V.; Turner, W.; Xu, K.; and Ren, H. 2024a. ChipNeMo: Domain-Adapted LLMs for Chip Design. arXiv:2311.00176.

14. Liu, M.; Pinckney, N.; Khailany, B.; and Ren, H. 2023. VerilogEval: Evaluating Large Language Models for Verilog Code Generation. arXiv:2309.07544.

15. Liu, S.; Fang, W.; Lu, Y.; Zhang, Q.; Zhang, H.; and Xie, Z. 2024b. RTLCoder: Outperforming GPT-3.5 in Design RTL Generation with Our Open-Source Dataset and Lightweight Solution. In *2024 IEEE LLM Aided Design Workshop (LAD)*, 1–5.

16. Morita, A. K.; Takiguti, R.; and Noije, W. A. M. V. 2015. Metadata based padring and pad multiplexing generation for microcontroller design. *Journal of Integrated Circuits and Systems*, 10(3): 139–146.

17. Moseley, N.; Barzic, R.; and contributors, Y. 2025. padring: A padring generator for ASICs. https://github.com/YosysHQ/padring/tree/master. ISC License.

18. Shi, L.; Kazda, M.; Sears, B.; Shropshire, N.; and Puri, R. 2024. Ask-EDA: A Design Assistant Empowered by LLM, Hybrid RAG and Abbreviation De-hallucination. arXiv:2406.06575.

19. Skelic, L.; Xu, Y.; Cox, M.; Lu, W.; Yu, T.; and Han, R. 2025. CIRCUIT: A Benchmark for Circuit Interpretation and Reasoning Capabilities of LLMs. arXiv:2502.07980.

20. Thakur, S.; Ahmad, B.; Pearce, H.; Tan, B.; Dolan-Gavitt, B.; Karri, R.; and Garg, S. 2023. VeriGen: A Large Language Model for Verilog Code Generation. arXiv:2308.00708.

21. Thakur, S.; Blocklove, J.; Pearce, H.; Tan, B.; Garg, S.; and Karri, R. 2024. AutoChip: Automating HDL Generation Using LLM Feedback. arXiv:2311.04887.

22. Tsai, Y.-D.; Liu, M.; and Ren, H. 2024. RTLFixer: Automatically Fixing RTL Syntax Errors with Large Language Models. arXiv:2311.16543.

23. Wu, H.; He, Z.; Zhang, X.; Yao, X.; Zheng, S.; Zheng, H.; and Yu, B. 2024. ChatEDA: A Large Language Model Powered Autonomous Agent for EDA. *IEEE Transactions on Computer-Aided Design of Integrated Circuits and Systems*, 43(10): 3184–3197.

24. Xu, K.; Qiu, R.; Zhao, Z.; Zhang, G. L.; Schlichtmann, U.; and Li, B. 2024. LLM-Aided Efficient Hardware Design Automation. arXiv:2410.18582.

25. Yin, Y.; Wang, Y.; Xu, B.; and Li, P. 2024. ADO-LLM: Analog Design Bayesian Optimization with In-Context Learning of Large Language Models. In *Proceedings of the 43rd IEEE/ACM International Conference on Computer-Aided Design, ICCAD '24*, 1–9. ACM.

---

> **翻译说明：**
> - 原文共 8 页，577 行（含参考文献），本文档按章节结构逐段翻译
> - 翻译原则：学术直译为主，保留专业术语原文（如 DRC、LVS、DRC+LVS、SKILL、LLM、EDA 等）
> - 每个段落先放中文翻译（引用块格式），再放对应的英文原文
> - 表格数据保持原样，表头翻译标注
> - 参考文献保留原文格式不翻译
