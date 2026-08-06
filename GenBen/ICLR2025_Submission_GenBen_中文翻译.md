# GenBen：面向LLM辅助设计的生成式基准测试

> **论文标题**: GenBen: A Generative Benchmark for LLM-Aided Design
>
> **会议**: ICLR 2025 投稿（双盲审稿中）
>
> **原文链接**: https://anonymous.4open.science/r/GENBEN-2812

---

## 摘要（ABSTRACT）

本文介绍了 GenBen，一个旨在评估大语言模型（LLMs）在硬件设计领域能力的生成式基准测试。随着 LLM 辅助设计（LAD）的快速发展，评估这些模型在自动化硬件设计过程中的有效性变得至关重要。现有的基准测试主要侧重于硬件代码生成，往往忽略了诸如结果质量（QoR）指标、设计多样性、多模态性以及测试集污染等关键方面。GenBen 是首个面向 LAD 的开源生成式基准测试，涵盖了从高层架构到底层电路优化的多种任务，并包含了多样化的、经过流片验证的硬件设计。我们还设计了一种难度分级机制，以提供对 LLM 辅助设计改进的细粒度洞察。通过使用 GenBen 对多个最先进的 LLM 进行广泛评估，我们揭示了它们在硬件设计自动化方面的优势与不足。我们的发现基于 10,920 次实验和 2,160 小时的评估，突显了这项工作对推动 LAD 研究社区发展的巨大潜力。此外，GenBen 采用端到端的测试基础设施，以确保不同 LLM 之间的一致性和可复现的结果。该基准测试可在以下链接获取：https://anonymous.4open.science/r/GENBEN-2812。

---

## 1. 引言（INTRODUCTION）

现代电路设计是一项复杂的、多学科的工作，需要诸多领域的专业知识，包括架构设计、性能建模、设计空间探索、寄存器传输级（RTL）实现、设计验证、物理布局等（Rabaey et al., 2002; Hennessy & Patterson, 2017; Bergeron, 2012）。随着硬件复杂性的增加，与设计和验证过程相关的开销也随之增加，进而延长了设计迭代周期（Calhoun et al., 2008）。传统方法严重依赖人工编写 Verilog 实现，而 Chisel（Thomas et al., 1989; Bachrach et al., 2012）和高层次综合（HLS）（Coussy & Morawiec, 2010; Gajski et al., 2012）通过引入额外的抽象层来自动化 RTL 代码生成，从而对传统方法进行了改进。然而，即使有了这些进步，验证开销仍然需要大量人力投入。因此，对于先进敏捷硬件设计方法的需求日益增长，以加速硬件开发迭代。

随着基于 Transformer 的大语言模型（LLMs）的兴起（Zhao et al., 2023; Winata et al., 2021; Chakrabarty et al., 2023），为硬件设计自动化开辟了新的途径。像 GPT-4（OpenAI, 2023）、Claude（Team, 2023）和 LLaMA（Touvron et al., 2023a;c; Dubey et al., 2024）这样的模型不仅在自然语言处理方面，而且在编程方面都展示了令人鼓舞的结果。在这个 LLM 辅助设计（LAD）的新范式下（ICCAD-Committee, 2023; ACM-SIGDA, 2024; Huang et al., 2024），诸如 WizardCoder（Luo et al., 2023）和 Code-LLaMA（Roziere et al., 2023）这样的模型已经展示出了显著的能力。

在这些先进模型的基础上，微调（Wei et al., 2021）和检索增强生成（RAG）（Lewis et al., 2020; Gao et al., 2023）等技术推动了领域特定模型和操作架构的发展，如 GPT4AIGChip（Fu et al., 2023）、AutoChip（Thakur et al., 2023c）、ChatChisel（Liu et al., 2024b）和 ChatCPU（Wang et al., 2024）。这些努力展示了使用 LLM 进行自动化硬件设计的能力。这一范式转变为硬件设计自动化带来了一波新的创新浪潮。

为了准确评估硬件代码生成的有效性，已引入了若干基准测试，例如 RTLLM（Lu et al., 2024）、Verigen（Thakur et al., 2023a）和 VerilogEval（Liu et al., 2023）。由于这些基准测试在 GitHub 上是开源的，并且通常由静态测试组成，它们可能会在无意中被纳入训练数据集，从而导致误导性的测试结果。此外，在验证覆盖率、评估指标和数据多样性方面也迫切需要改进。例如，这些基准测试中的测试相对简单且单一模态，主要关注语法和功能通过率。这种关注忽视了关键指标，如可综合性、调试能力以及性能、功耗和面积（PPA）（Marakkalage et al., 2024）统计数据，而这些对于全面评估至关重要。

为了解决这些局限性，我们引入了 GenBen，一个用于系统评估生成式 AI 在硬件设计中能力的创新基准测试。GenBen 通过以下关键创新增强功能与现有工作区分开来：

- **增强的验证覆盖率**: 我们严格采用标准的端到端验证流程，以最大化开发测试平台的功能覆盖率，将生成的测试激励映射到 RTL 设计的每个功能点。

- **多样化且难度分级的数据集**: GenBen 展示了一个多来源、多模态、难度分级的评估框架，包含 300 个测试，这些测试来源于经过流片验证的设计、教科书、StackOverflow 和其他来源。每个测试被归类为三个不同的难度等级之一（L1 到 L3），允许对 LLM 在硬件设计中的能力进行细粒度和有针对性的增强。

- **防范数据污染的生成式基准**: GenBen 是一个生成式基准测试，结合了静态和动态扰动来将每个测试与其源数据集区分开来。此外，我们利用基于脚本的生成方法来阻碍 GitHub 爬虫自动提取 RTL 代码，从而有效最小化测试集数据泄露的风险。

- **增强的评估指标**: GenBen 整合了多样化的指标来全面评估生成的设计，包括基本的语法/功能正确性，以及结果质量（QoR）指标（Yu et al., 2018），如可综合性、功耗、面积利用率、时序性能等。

- **端到端开源工作流**: GenBen 集成了 Icarus Verilog（Williams, 2023）、OpenLane EDA 流程（Ghazy & Shalan, 2020）和 Open-PDK（Edwards, 2023）等工具，以简化可复现性。

本文的其余部分组织如下：第 2 节介绍 GenBen 的动机并回顾相关工作。第 3 节介绍 GenBen 的架构和工作流程。第 4 节使用 GenBen 评估多种 LLM，第 5 节总结本文。

---

## 2. 相关工作（RELATED WORKS）

为了进一步阐明 GenBen 在推动硬件设计自动化方面的必要性和影响，必须审视 LLM 辅助设计（LAD）的现状以及用于评估此类系统的基准测试。以下各节深入探讨了 LLM 在硬件设计中的集成，并批判性地分析了评估 LAD 的基准测试，从而为我们的贡献奠定基础背景。

### 2.1 LLM 辅助设计

将基于 Transformer 架构的 LLM 集成到硬件设计中正在改变该领域，利用它们在自然语言处理方面已被证明的能力来高效管理复杂的设计任务（Vaswani, 2017; Achiam et al., 2023; Touvron et al., 2023b）。这些模型通过理解和生成类似人类的文本，在各个任务中表现出色，这使得它们能够将其效用扩展到硬件设计（Zheng et al., 2024; Nijkamp et al., 2022; Lozhkov et al., 2024; Lu et al., 2023）。在硬件设计领域，大量的努力集中在使用 LLM 来改进硬件描述语言（HDLs）的生成过程和功能。

一些值得注意的项目包括：ChatEDA，它开发了一个基于 LLM 的 EDA 接口，使用自然语言输入生成特定任务的代码（Wu et al., 2024）。GPT4AIGChip 项目通过将专门为 AI 加速器设计的各种硬件功能模块化，展示了 LLM 驱动设计自动化的潜力（Fu et al., 2023）。AutoChip 将 LLM 与 Verilog 编译器相结合，以迭代方式生成 Verilog 模块（Thakur et al., 2023c），而 Chip-chat 集成了对话式 LLM 技术来设计一个新的 8 位微处理器架构（Blocklove et al., 2023）。此外，ChatCPU 探索了一个全面的 LLM 辅助设计（LAD）芯片设计，并引入了一种新的验证方法（Wang et al., 2024），而 ChatChisel 使用一种专门的 HDL 来创建复杂的处理器（Liu et al., 2024b）。LLM 在这些方法中的集成，利用了基于数据的优化技术，如监督微调（SFT）（Hu et al., 2021; Liu et al., b; Houlsby et al., 2019; Zhang et al.; Wei et al., 2021），以及检索增强生成（RAG）（Lewis et al., 2020; Gao et al., 2023）和提示工程（Cao et al.; Bulat & Tzimiropoulos; Chen et al.; Deng et al.）。开发全面的基准测试以减轻预训练的影响并全面评估模型在该领域的性能是非常重要的。

**表 1: 现有工作与我们的工作的比较**

| 名称 | 会议 | 测试数量 | 扰动 | 最差覆盖率 | 多模态 | 难度分级 | 指标 |
|------|------|---------|------|-----------|--------|---------|------|
| VeriGen (Thakur et al., 2023b) | DATE 23 | 16 个模块 | ✗ | – | ✗ | ✗ | 编程 |
| RTLLM (Lu et al., 2024) | ASPDAC 23 | 30 个设计 | 部分 | 52.40% | ✗ | ✗ | 编程, PPA |
| RTLLM2.0 (Liu et al., 2024a) | ICCAD24 | 50 个设计 | 部分 | 52.40% | ✗ | ✗ | 编程, PPA |
| VerilogEval (Liu et al., 2023) | ICCAD 23 | HDLBit | 部分 | 44.64% | ✗ | ✗ | 编程 |
| MLLM Bench (Chang et al., 2024) | ICCAD 24 | 多模态 | ✗ | – | ✓ | ✗ | 编程 |
| **GenBen** | **本文** | **所有标准** | ✓ | **95.17%** | ✓ | ✓ | **知识, 编程, 调试, QoR** |

### 2.2 评估 LAD 的基准测试

在此背景下，建立基准测试来评估 LLM 在这些调整下的能力至关重要（Zhong & Wang, 2023; Liu et al., a）。然而，现有的基准测试是静态且开源的，使其容易在无意中被纳入预训练数据集，并且在测试平台覆盖率、基准数据多样性和评估指标的可扩展性方面仍有改进空间。

例如，尽管 Verigen（Thakur et al., 2023a）在对 CodeGen（Nijkamp et al., 2022）进行微调后评估了 17 个设计，但这些评估主要针对简单和小规模的电路设计，而且这些基准测试不是开源的。RTLLM（Lu et al., 2024）和 RTLLM2.0（Liu et al., 2024a）提供了 30-50 个测试平台用于测试 LLM。这些测试平台使用 VCS 进行评估以确定验证覆盖率，最差覆盖率得分约为 52.40%，如表 1 所示。此外，这些测试平台的题型相对简单和统一，并且所提到的一些评估工具不是开源的。VerilogEval（Liu et al., 2023）引入了来自 HDLBits 的 156 个问题的综合数据集，用于 LLM 生成 Verilog 代码的自动化功能正确性测试。然而，这些基准测试相对容易，表现最好的模型具有很高的验证通过率，这不允许在模型不断演进的情况下进行进一步的压力测试。此外，VerilogEval 的最差验证覆盖率相对较低，为 44.63%。

为了研究测试覆盖率的局限性，我们进一步分析了 VerilogEval 基准测试，如图 1 所示。RTL-Repo（Allam & Shalan, 2024）在评估 RTL Repo 项目时，可以通过精确匹配（EM）和编辑相似度（ES）来评估 LLM 的准确性，然而这些指标并不能保证 LLM 生成的设计是可验证的或最优可综合的。PyHDL-Eval（Batten et al., 2024）和 VHDLEval（Vijayaraghavan et al., 2024）是领域特定的基准测试，其数据多样性和评估指标可以进一步丰富。HDLEval（Zakharov & Renau）启动了一个多功能基准测试，使用快速工程技术来克服不同 HDL 之间的语法差异，并采用形式验证方法来评估跨多个 HDL 生成的代码。然而，在增强测试平台覆盖率和题型丰富性方面仍有空间。ChipGPTV（Chang et al., 2024）提出使用视觉表示来阐明设计意图，并引入了一个分层基准测试来评估 MLLM 在 Verilog 生成中的性能，但在扩展代码生成和硬件设计知识测试指标的多样性方面仍有进一步的空间。现有工作与我们的工作的详细比较见表 1。

### 2.3 问题陈述（PROBLEM FORMULATION）

1. **验证覆盖率差距**：现有基准测试揭示了设计复杂性和验证覆盖率方面的差距。开发的测试平台往往不能充分表示所包含 RTL 设计的基本功能点，这种情况随着设计复杂性的增加而恶化。因此，生成的硬件的有限验证覆盖率可能会破坏评估结果的真实性。

2. **数据多样性不足**：当前基准测试问题在数据来源和模态方面表现出不足的多样性和丰富性。许多源自教育材料的基准测试过于简单，缺乏流片验证。此外，这些基于文本的单模态基准测试往往无法反映真实世界的设计规范，后者经常包含视觉原理图和时序图。

3. **基准测试集污染**：由于这些基准测试在 GitHub 上是静态开源的，相关的 RTL 设计和规范可以被爬虫自动捕获，作为 RTL 语言数据集的一部分。像 GPT-4、Claude 和 Llama 3 这样的不断演进的 LLM 可能在预训练期间无意中纳入这些数据，导致数据泄露和测试集污染。

4. **评估指标有限**：现有基准测试主要关注语法和功能通过率，忽略了关键的 QoR 指标，如 PPA 统计数据和可综合性。这种疏忽可能导致对生成的设计的不完整评估。

---

## 3. 设计与理念（DESIGN & PHILOSOPHY）

在本节中，我们详细介绍 GenBen 的设计，包括工作流程、数据集收集、任务构建、数据扰动、质量增强和问题生成。

### 3.1 GenBen 的设计策略

针对第 2.3 节中的挑战，GenBen 设计融合了以下策略：

- **改进的数据集多样性**：从 GitHub、流片验证的项目和 StackOverflow 等来源策划，包含客观（知识）和主观（编程、调试、设计优化）测试，分为三个难度等级（表 2）。

- **覆盖率增强的测试平台**：由我们的专家在线覆盖率、翻转覆盖率和功能覆盖率方面增强测试平台质量，以确保细粒度的验证。

- **扰动生成式基准**：在测试生成和评估过程中采用扰动策略，以防御记忆化。

- **多维评估**：设计五个维度和 12 个子项，具有 QoR 感知机制（表 5），实现灵活、可定制的基准测试。

### 3.2 GenBen 框架与工作流

GenBen 框架具有以下关键组件：预处理测试集、任务生成器、动态扰动器、响应收集器、评估套件、报告分析器和评分模块。评估开始时，用户提供模型的 API 和模态信息，如图 2.B 所示。然后 GenBen 使用脚本从测试数据集 D 生成测试，记为 T，每次评估测试保持一致。随后，动态扰动组件对 T 应用表面级扰动，得到变换后的集合 T'。这些扰动为动态评估引入了轻微的变化。GenBen 使用统一的提示模板从模型收集 T 和 T' 的响应。这些响应随后被送入评估套件，该套件执行检查和执行以验证输出。GenBen 使用 Icarus Verilog（Iverilog）模拟生成的答案和相应的测试平台，以获得语法和功能正确性的报告。

通过功能测试的设计将使用开源 SkyWater 130nm 工艺设计套件（PDK）（sky, 2020）和 OpenLane 流程进行进一步的物理实现。在 OpenLane 中，Yosys（Wolf et al., 2013）组件提取可综合性、面积和功耗数据，而 OpenSTA（Cherry, 2023）处理时序相关的数据提取。然后，报告分析器从评估结果中提取与指标相关的信息。这些信息传递给评分模块，该模块根据预定义的指标评估模型的性能并生成最终结果。

**表 2: 难度分级**

| 类别 | 描述 |
|------|------|
| L1（简单） | 适合初步评估，侧重于基本概念和直接的测试 |
| L2（中等） | 涉及更复杂的测试，需要强大的问题解决能力 |
| L3（困难） | 应对真实世界的设计挑战，需要高级推理和实现能力 |

### 3.3 基准数据集构建

我们的数据集构建过程如图 2.A 所示。我们从网络上收集了与硬件相关的内容，然后由 10 名领域专家团队精心策划。这些专家对数据进行了正确性、完整性和多样性的筛选，特别关注从流片验证的项目中采样。对于选定的代码测试，我们增强了其测试平台，以确保稳健的评估（第 3.3.1 节）；对于调试测试，我们按照第 3.3.2 节进行了优化。

收集和精炼的内容随后被筛选并分类为三种类型的测试：知识、设计和调试。为了减轻公开可用的预训练数据对评估的干扰，我们引入了静态扰动。使用多智能体系统结合人类反馈（如图 2.C 所示），我们对测试应用扰动，在 token 序列级别将其转化为新内容。

**表 3: GenBen 中的测试类别**

| 测试 | 数量 | 描述 |
|------|------|------|
| 知识掌握 | 75 | 侧重于评估 LLM 对基本硬件概念和原理的掌握 |
| 知识迁移 | 69 | 将概念应用于新的复杂场景以进行泛化 |
| 设计 | 99 | 根据代码行数、类型和设计时间区分难度 |
| 调试 | 57 | 区分纠正语法/功能/组合错误的难度 |
| 多模态 | 60 | 融合文本和视觉输入 |

更新后的测试随后根据难度进行分级（表 2），并映射到不同类别的测试：客观测试（评估基本知识理解和迁移）、设计测试、调试测试和多模态测试。这种映射确保了对 LLM 的知识和能力的全面端到端评估。最终，GenBen 测试的数量和各难度级别的分布如表 3 所示。

#### 3.3.1 测试平台覆盖率增强

在准备 GenBen 数据集之后，我们继续为每个 RTL 设计构建测试平台，以增强生成设计的验证覆盖率。我们严格采用标准的端到端验证流程，确保生成的测试激励与功能覆盖率检查表之间的点对点映射。通过采用约束随机化和覆盖率驱动的测试平台生成方法，我们显著提高了每个生成 RTL 设计的验证覆盖率，从而最大化了对 LAD 能力基准测试的有效性。

#### 3.3.2 调试测试设计

此外，调试过程是集成电路设计流程中的关键步骤，不应在基准测试中被忽略：现实世界的硬件设计通常涉及识别和纠正错误。因此，我们在 GenBen 中引入了调试测试。我们将它们分为三种类型：语法错误、功能错误以及两者的混合。通过向正确的设计中注入错误，我们创建了需要 LLM 定位和修复错误代码的调试数据集。

### 3.4 数据扰动

基于对现有 DS-1000 工作（Lai et al., 2023）的洞察，我们引入了扰动策略来减轻 AI 模型中潜在的记忆偏差。我们实现了两种类型的扰动：表面扰动和语义扰动，如表 4 所示。

**表 4: 扰动类别**

| 扰动 | 描述 |
|------|------|
| 表面 | 释义：不改变参考答案 |
| 语义 | 泛化：会改变参考答案 |

表面级扰动改变问题的措辞而不改变其核心含义。例如，提示"设计一个 128x32 RAM 模块"可能被重新表述为"构建一个具有 128 个地址和 32 位数据宽度的存储器模块"。如图 2.C 所示，表面扰动需要进行等价性检查，以确保任务的含义保持不变。

语义扰动通过改变问题的底层含义来增加任务的难度。例如，将提示从"设计一个 16 位加法器"改为"设计一个可以处理 16 位输入二进制补码算术的加法器"需要模型展现更强的推理能力。需要将更新后的任务与其相应的解决方案对齐以保持一致性，如图 2.C 所示。

我们在两个阶段实施扰动：在 GenBen 构建期间（如图 2.A 所示），以及在整个 GenBen 工作流程中（如图 2.B 所示）。

#### 3.4.1 静态扰动

静态扰动在测试构建阶段应用，利用图 2.C 所示的多智能体过程。该过程涉及对候选测试添加表面和语义扰动，然后由人类专家审查以最终确定测试设计。此阶段的关键方面包括：1) 将概念、定义和计算问题抽象为客观问题；2) 向正确的代码中注入错误以创建调试测试；3) 调整和派生新的编码测试。这些扰动在数据源级别应用，并且一旦测试集最终确定就保持不变。

#### 3.4.2 动态扰动

为了进一步减少预训练数据的干扰，我们在评估过程中使用表面级扰动引入动态扰动。此阶段涉及生成测试的略微变化版本，如第 3.2 节所述。这为研究人员分析 LLM 的鲁棒性和适应性提供了额外的洞察和参考。

### 3.5 多模态特征支持

GenBen 框架提供单模态和多模态任务评估，满足了硬件设计中日益增长的综合评估方法需求。这一特性尤为重要，因为现实世界的设计过程通常需要整合各种形式的数据，如文本规范、图表和架构原理图。理解和综合来自多种模态的信息对于有效的硬件设计至关重要。

在 GenBen 中，多模态数据类型包括基本电路图、设计架构原理图、波形图和表格。这些数据类型被用于各种测试类别：知识问题评估对基本概念及其应用的理解；代码生成测试需要解释视觉原理图并将其转化为 HDL 代码；调试测试涉及在通过文本和视觉数据组合呈现的设计中识别和纠正错误。

### 3.6 评估指标设计

我们开发了一个全面的评估指标体系，如表 5 所述，包括基本正确性指标和 QoR 指标。QoR 指标包括可综合性、功耗、面积和时序性能，用于评估生成设计对硅实现的可行性。为了量化 LLM 的设计优化能力，我们以参考设计为基准对这些 QoR 结果进行归一化。

**表 5: GenBen 的指标**

| 指标 | 描述 |
|------|------|
| 知识掌握 | 无需推理的基本概念 |
| 知识迁移 | 需要思维链或推理的泛化技能 |
| 调试能力 | 问题解决和坚持不懈的技能 |
| 代码正确性 | 语法与功能：编程技能 |
| 结果质量 | 可综合性、功耗、面积和时序 |

这种综合方法，包括知识掌握与迁移、设计生成、调试、多模态内容以及从后综合导出的设计优化，使 GenBen 能够系统地评估 LLM 在整个硬件设计过程中的性能。特别是，从功耗、面积和时序分析导出的改进感知指标，为模型生成高质量、可制造硬件设计的能力提供了清晰直观的表示。

---

## 4. 实验结果（EXPERIMENTAL RESULTS）

### 4.1 实验设置

**模型选择**：我们的研究评估了九个模型，包括六个多模态模型和三个语言模型。选定的模型有 GPT-4-turbo、GPT-4o、GPT-3.5-turbo、Claude3.5、Llama3、QWEN-vl-max、QWEN-vl-plus、GLM-4V-plus 和 GLM-4。

**提示模板**：我们开发了一个标准化的提示结构，由两个关键组件组成：(1) 角色扮演提示和 (2) 问题描述提示，如图 2.E 所示。

**测试迭代**：我们在整个实验中采用了 pass@5 评估策略。

**通过率**：最后，我们使用通过率（PR）来量化整体能力。对于一个问题 θᵢ 及其 LLM 生成的答案 θᵢ*，我们在 GenBen 数据库中有一组对应的正确答案 {(xᵢ⁰, yᵢ⁰), (xᵢ¹, yᵢ¹), ..., (xᵢᵐ, yᵢᵐ)}。对于正确的解 θᵢ*，当应用于测试用例的输入数据 xᵢʲ 时，它应产生正确的输出 yᵢʲ。即 a(θᵢ*, xᵢʲ) = yᵢʲ，测试用例 (xᵢʲ, yᵢʲ) 可被视为通过。

PR 定义为：

$$PR = \frac{\sum_{i=0}^{n} \bigwedge_{j=0}^{m} [a_{\theta_i^*}(x_i^j) = y_i^j]}{n} \times 100\%$$

**评估标准**：
- **知识和调试测试**：通过与参考答案比较的通过/失败标准。
- **代码生成**：语法——失败的尝试得分为 0%。成功的尝试若有警告，每个警告扣除 5% 的分数，最低得分为 60%。功能——计算范围为 0% 到 100%。此外，为了评估 QoR 优化能力，我们与参考设计进行归一化比较。

### 4.2 结果分析

**稳定的基准性能**：图 4-12 所示的结果突出表明，最佳模型的总体 PR 略高于 40% 但低于 50%，与预期一致。

**有效的难度分级**：难度级别和 PR 之间存在相关性。以 GPT-4o 为例（如图 4 所示，详细数值见附录 A 表 10），这些级别之间的 PR 存在一致的 5-10% 差异。

**测试之间的相关性**：数据表明知识掌握和编码能力之间存在相关性。在知识掌握方面表现良好的模型，如 GPT-4o 和 Claude 3.5，在调试和功能正确性方面也表现出高分。这表明对基本概念的扎实理解对实际编码技能有积极影响。

**可综合性与语法差异**：可综合性与语法正确性之间存在高度不一致（91.76%），如图 13 和 14 所示。这种差异源于仿真和综合工具之间需求的固在差异，加之预训练数据集中存在不符合 IEEE 标准的代码。这个问题突显了未来模型改进的一个领域。

**调试能力**：与代码生成相比，模型通常表现出更强的调试能力，这可能归因于调试测试中提供的额外上下文。

**顶级模型的 QoR 分析**：GPT-4o 和 Claude 3.5 的 QoR 结果如图 15 所示。GPT-4o 在面积和时序指标方面表现稳定，但在低功耗设计方面需要改进。另一方面，Claude 3.5 在功耗和面积方面展示了积极优化，但以时序违例为代价。这些洞察显示了不同模型的不同权衡。

**动态扰动的消融实验**：图 16 以 Llama3 为例说明了来自 GPT-3.5 和 GPT-4 的动态扰动的影响。结果表明，性能在不同测试集之间波动，总体性能下降约 9%。

---

## 5. 结论（CONCLUSION）

在本文中，我们介绍了 GenBen，一个全面的基准测试，旨在评估 LLM 在硬件设计领域的能力。与主要关注代码生成的现有基准测试不同，GenBen 通过涵盖调试、优化和芯片硬化流程，提供了更全面的评估。通过引入扰动和分层任务分类，GenBen 提供了多样化的端到端开源评估模态。我们的目标是将 GenBen 建立为 LAD 进步的催化剂，为一个可靠的基准测试，针对满足真实世界硅制造要求的生成式硬件设计量身定制。

---

## 参考文献（REFERENCES）

1. Skywater sky130 pdk, 2020. URL https://skywater-pdk.readthedocs.io/en/main/
2. Josh Achiam, et al. GPT-4 technical report. arXiv preprint arXiv:2303.08774, 2023.
3. ACM-SIGDA. Home, 2024. URL https://www.islad.org.
4. Ahmed Allam and Mohamed Shalan. RTL-repo: A benchmark for evaluating LLMs on large-scale RTL design projects. arXiv preprint arXiv:2405.17378, 2024.
5. Jonathan Bachrach, et al. Chisel: constructing hardware in a Scala embedded language. In Proceedings of DAC, pp. 1216–1225, 2012.
6. Christopher Batten, et al. PyHDL-eval: An LLM evaluation framework for hardware design using Python-embedded DSLs. In MLCAD, Sep 2024.
7. Janick Bergeron. Writing testbenches: functional verification of HDL models. Springer, 2012.
8. Jason Blocklove, et al. Chip-chat: Challenges and opportunities in conversational hardware design. In MLCAD, pp. 1–6. IEEE, 2023.
9. Adrian Bulat and Georgios Tzimiropoulos. LASP: Text-to-Text Optimization for Language-Aware Soft Prompting of Vision & Language Models.
10. Benton H Calhoun, et al. Digital circuit design challenges and opportunities in the era of nanoscale CMOS. Proceedings of the IEEE, 96(2):343–365, 2008.
11. Jialun Cao, et al. A study on Prompt Design, Advantages and Limitations of ChatGPT for Deep Learning Program Repair.
12. Tuhin Chakrabarty, et al. Creative natural language generation. In EMNLP Tutorial Abstracts, pp. 34–40, 2023.
13. Kaiyan Chang, et al. Natural language is not enough: Benchmarking multi-modal generative AI for Verilog generation. arXiv preprint arXiv:2407.08473, 2024.
14. Xiang Chen, et al. KnowPrompt: Knowledge-aware Prompt-tuning with Synergistic Optimization for Relation Extraction. In WWW 2022, pp. 2778–2788.
15. James Cherry. Parallax static timing analyzer, 2023. URL https://github.com/parallaxsw/OpenSTA.
16. Philippe Coussy and Adam Morawiec. High-level synthesis, volume 1. Springer, 2010.
17. Mingkai Deng, et al. RLPrompt: Optimizing Discrete Text Prompts with Reinforcement Learning.
18. Abhimanyu Dubey, et al. The Llama 3 herd of models. arXiv preprint arXiv:2407.21783, 2024.
19. R. Timothy Edwards. Open PDKs PDK installer for open-source tools, 2023. URL http://www.opencircuitdesign.com/open_pdks/index.html.
20. Yonggan Fu, et al. GPT4AIGChip: Towards next-generation AI accelerator design automation via large language models. In ICCAD, pp. 1–9. IEEE, 2023.
21. Daniel D Gajski, et al. High-Level Synthesis: Introduction to Chip and System Design. Springer, 2012.
22. Yunfan Gao, et al. Retrieval-augmented generation for large language models: A survey. arXiv preprint arXiv:2312.10997, 2023.
23. Ahmed Ghazy and Mohamed Shalan. OpenLane: The open-source digital ASIC implementation flow. In WOSET, 2020.
24. John L Hennessy and David A Patterson. Computer architecture: a quantitative approach. Morgan Kaufmann, 2017.
25. Neil Houlsby, et al. Parameter-efficient transfer learning for NLP. In ICML, pp. 2790–2799. PMLR, 2019.
26. Edward J Hu, et al. LoRA: Low-rank adaptation of large language models. arXiv preprint arXiv:2106.09685, 2021.
27. Yingbing Huang, et al. New solutions on LLM acceleration, optimization, and application, 2024.
28. ICCAD-Committee. LLM-Aided Design Panel, 2023. URL https://2023.iccad.com/llm-aided-design-panel.
29. Yuhang Lai, et al. DS-1000: a natural and reliable benchmark for data science code generation. In ICML'23. JMLR.org, 2023.
30. Patrick Lewis, et al. Retrieval-augmented generation for knowledge-intensive NLP tasks. NeurIPS, 33:9459–9474, 2020.
31. Mingjie Liu, et al. VerilogEval: Evaluating large language models for Verilog code generation. In ICCAD, pp. 1–8. IEEE, 2023.
32. Peng Liu, et al. Pre-train, Prompt and Recommendation: A Comprehensive Survey.
33. Shang Liu, et al. OpenLLM-RTL: Open dataset and benchmark for LLM-aided design RTL generation. 2024a.
34. Tianyang Liu, et al. ChatChisel: Enabling agile hardware design with large language models. In ISEDA, pp. 710–716. IEEE, 2024b.
35. Xiao Liu, et al. P-Tuning: Prompt Tuning Can Be Comparable to Fine-tuning. In ACL 2022, pp. 61–68.
36. Anton Lozhkov, et al. StarCoder 2 and the Stack v2: The next generation. arXiv preprint arXiv:2402.19173, 2024.
37. Pan Lu, et al. MathVista: Evaluating mathematical reasoning of foundation models in visual contexts. arXiv preprint arXiv:2310.02255, 2023.
38. Yao Lu, et al. RTLLM: An open-source benchmark for design RTL generation with large language model. In ASP-DAC, pp. 722–727. IEEE, 2024.
39. Ziyang Luo, et al. WizardCoder: Empowering code large language models with evol-instruct. arXiv preprint arXiv:2306.08568, 2023.
40. Dewmini Sudara Marakkalage, et al. Scalable sequential optimization under observability don't cares. In DATE, pp. 1–6. IEEE, 2024.
41. Erik Nijkamp, et al. CodeGen: An open large language model for code with multi-turn program synthesis. arXiv preprint arXiv:2203.13474, 2022.
42. OpenAI. GPT-4 technical report. Technical report, OpenAI, 2023.
43. Jan M Rabaey, et al. Digital integrated circuits, volume 2. Prentice Hall, 2002.
44. Baptiste Roziere, et al. Code Llama: Open foundation models for code. arXiv preprint arXiv:2308.12950, 2023.
45. Anthropic Team. Claude2. https://www.anthropic.com/index/claude-2, 2023.
46. Shailja Thakur, et al. Benchmarking large language models for automated Verilog RTL code generation. In DATE, pp. 1–6. IEEE, 2023a.
47. Shailja Thakur, et al. VeriGen: A large language model for Verilog code generation. arXiv preprint arXiv:2308.00708, 2023b.
48. Shailja Thakur, et al. AutoChip: Automating HDL generation using LLM feedback. arXiv preprint arXiv:2311.04887, 2023c.
49. Donald E Thomas, et al. Algorithmic and Register-Transfer Level Synthesis. Springer, 1989.
50. Hugo Touvron, et al. LLaMA: Open and efficient foundation language models. arXiv preprint arXiv:2302.13971, 2023a.
51. Hugo Touvron, et al. LLaMA: Open and efficient foundation language models. arXiv preprint arXiv:2302.13971, 2023b.
52. Hugo Touvron, et al. Llama 2: Open foundation and fine-tuned chat models. arXiv preprint arXiv:2307.09288, 2023c.
53. Ashish Vaswani. Attention is all you need. arXiv preprint arXiv:1706.03762, 2017.
54. Prashanth Vijayaraghavan, et al. VHDL-Eval: A framework for evaluating large language models in VHDL code generation. arXiv preprint arXiv:2406.04379, 2024.
55. Xi Wang, et al. ChatCPU: An agile CPU design & verification platform with LLM. In DAC'24, pp. 6, 2024.
56. Jason Wei, et al. Finetuned language models are zero-shot learners. arXiv preprint arXiv:2109.01652, 2021.
57. S. Williams. The Icarus Verilog compilation system, 2023. URL https://github.com/steveicarus/iverilog.
58. Genta Indra Winata, et al. Language models are few-shot multilingual learners. arXiv preprint arXiv:2109.07684, 2021.
59. Clifford Wolf, et al. Yosys - a free Verilog synthesis suite. In Austrochip, volume 97, 2013.
60. Haoyuan Wu, et al. ChatEDA: A large language model powered autonomous agent for EDA. IEEE TCAD, 2024.
61. Cunxi Yu, et al. Developing synthesis flows without human knowledge. In DAC, pp. 1–6, 2018.
62. Farzaneh Rabiei Kashanaki, Mark Zakharov and Jose Renau. HDLEval: Benchmarking LLMs for multiple HDLs.
63. Yuanhan Zhang, et al. Neural Prompt Search.
64. Wayne Xin Zhao, et al. A survey of large language models. arXiv preprint arXiv:2303.18223, 2023.
65. Tianyu Zheng, et al. OpenCodeInterpreter: Integrating code generation with execution and refinement. arXiv preprint arXiv:2402.14658, 2024.
66. Li Zhong and Zilong Wang. A study on robustness and reliability of large language model code generation, 2023.

---

## 附录 A（APPENDIX）

### 附录目录

- A.1 LLM辅助设计的概念
- A.2 硬件设计中的结果质量
  - A.2.1 可综合性
  - A.2.2 功耗、性能和面积（PPA）
  - A.2.3 总负裕量（TNS）和最差负裕量（WNS）
  - A.2.4 建立时间和保持时间
- A.3 开源EDA工具在增强科学可复现性中的作用
  - A.3.1 开源EDA工具在GenBen中的实现
  - A.3.2 QoR评估中PDK的选择
- A.4 数据集来源
- A.5 生成式基准的概念和原理
  - A.5.1 测试生成算法
- A.6 实验结果
- A.7 教程：使用GenBen评估LLM性能
  - A.7.1 分步说明
  - A.7.2 详细使用说明请参阅README
- A.8 开源声明

---

### A.1 LLM辅助设计的概念

LLM辅助设计（LAD）被定义为使用大语言模型（LLMs）作为一种方法论，以改进质量、生产力、鲁棒性和成本效益来辅助设计电路、软件和计算系统。它侧重于讨论利用生成式AI和LLM技术所捕获的重大进步和创新，为面向各种应用的设计自动化提供新的方法和解决方案。这一概念由IEEE ICCAD 2023首次提出。

### A.2 硬件设计中的结果质量

在硬件设计中，结果质量（QoR）指标对于评估设计的有效性和效率至关重要。这些指标涵盖了决定生成硬件实用性和性能的各个方面。下面我们提供关键QoR指标的详细解释及其意义：

#### A.2.1 可综合性

可综合性指的是硬件设计从高层描述转换为可制造的門级网表的能力。这个过程被称为综合，是硬件设计流程的基础。一个不可综合的设计无法在硅上实现，使其在实际应用中不切实际。确保可综合性是验证设计能否从概念过渡到物理实现的第一步。重要的是要注意，通过仿真的设计并不能保证通过综合，通常是由于语法或结构问题，这些问题在仿真中是可接受的，但不满足综合工具的严格要求。

#### A.2.2 功耗、性能和面积（PPA）

功耗、性能和面积（PPA）是用于评估硬件设计效率的一套综合指标：

- **功耗**：测量硬件设计消耗的电功率量。较低的功耗对于电池供电设备和节能系统至关重要。
- **性能**：通常以最大工作频率或吞吐量来评估，性能指标表示硬件可以运行多快。更高的性能对于需要快速数据处理和高速计算的应用至关重要。
- **面积**：指硬件设计占据的硅面积。最小化面积对于降低制造成本和在给定芯片尺寸内集成更多功能非常重要。

平衡这三个方面——功耗、性能和面积——是硬件设计中的关键挑战，因为一个方面的改进往往会导致其他方面的权衡。

在我们的基准测试设计中，为了确保运行时间和EDA脚本标准化方面的一致性和效率，我们将主要性能指标统一为频率。因此，性能反馈主要通过总负裕量（TNS）和最差负裕量（WNS）提供。

#### A.2.3 总负裕量（TNS）和最差负裕量（WNS）

总负裕量（TNS）和最差负裕量（WNS）是用于评估硬件设计时序性能的关键时序指标：

- **总负裕量（TNS）**：设计中所有负时序裕量的总和。负裕量表示时序路径不满足其所需的时序约束。TNS 提供了整个设计中时序违例的聚合度量。
- **最差负裕量（WNS）**：表示设计中最严重的时序违例。它是最大的单个负裕量值，突出显示了表现最差的时序路径。

TNS 和 WNS 对于识别和解决时序问题至关重要，确保设计满足其性能要求而无违例。

#### A.2.4 建立时间和保持时间

建立时间和保持时间是确保时序电路可靠运行的关键参数：

- **建立时间**：时钟沿之前数据必须稳定的最小时间，以便被正确锁存。建立时间违例可能导致捕获错误数据，影响设计功能。
- **保持时间**：时钟沿之后数据必须保持稳定的最小时间，以便被正确锁存。保持时间违例可能导致数据损坏，导致不可预测的电路行为。

确保满足建立时间和保持时间对于硬件设计的稳定性和可靠性至关重要。

总之，这些 QoR 指标为评估硬件设计的实际可行性和性能提供了一个全面的框架。它们对于确保设计不仅满足功能要求，而且在现实世界应用中高效可靠地运行至关重要。此外，满足综合的语法和结构要求确保设计在理论上是合理的，并且在硅上是实际可实现的。

### A.3 开源EDA工具在增强科学可复现性中的作用

开源电子设计自动化（EDA）工具是科学可复现性的关键推动者，为传统上依赖商业EDA工具（如 Design Compiler 和 Synopsys VCS）的基准测试提供了可访问的替代方案。

开源EDA工具的主要优势之一是促进研究人员和设计人员之间的轻松协作。它们消除了对复杂法律协议（如保密协议 NDA）的需求，允许直接分享设计、想法和材料。这种协作的便利性对于整合来自计算机科学等领域的专家尤为有益，在这些领域开源开发是普遍的做法。

此外，开源EDA工具对教育和研究目的非常宝贵。它们使教育者能够为学生提供设计自动化过程的实践洞察。学生和研究人员可以修改代码，测试他们的假设，并全面理解芯片设计过程。

#### A.3.1 开源EDA工具在GenBen中的实现

在我们的 GenBen 设计过程中，我们专门使用开源EDA工具。在任务构建阶段，我们依赖 Verilator 进行测试平台的覆盖率分析、增强和优化。对于模型测试期间的敏捷执行，我们使用 Icarus Verilog，因为它编译时间更快，尽管它缺乏全面的覆盖率分析。因此，我们在不同阶段使用不同的工具来平衡效率和彻底性。

此外，为了获取物理实现信息，我们使用 OpenLane，一个开源的 RTL-to-GDSII EDA 流程，如图 17 所示。OpenLane 使我们能够提取关于可综合性、面积、功耗和时序的关键数据，确保我们的基准测试既实用又可以使用广泛可用的工具复现。

#### A.3.2 QoR评估中PDK的选择

设计的结果质量（QoR）可能在不同工艺设计套件（PDK）之间显著变化。为了确保评估的一致性，我们选择了开源 SkyWater 130nm PDK 进行 QoR 测试。这一选择为评估硬件设计的实际可行性提供了一个标准化的参考点，允许在不同设计实现之间进行公平和可比较的结果。

### A.4 数据集来源

我们 GenBen 基准测试的数据集是从多种来源精心策划的，以确保全面覆盖硬件设计的各个方面。这些来源根据其贡献的任务的复杂性和深度分为三个级别——一级（L1）、二级（L2）和三级（L3）。

**一级（L1）来源**提供旨在评估硬件设计中基本知识和技能的基础任务。这些包括大学教科书等材料，提供理解核心概念的基本理论和实践问题。基本代码示例提供简单的编码任务以测试基础编程技能，而基本测验包括选择题和简答题以评估基本知识。此外，HDLBits 提供适合初学者的基本硬件描述语言（HDL）练习。

**二级（L2）来源**呈现中等难度级别的任务，需要更深入的理解和应用硬件设计原则。这些来源包括 GitHub 项目，提供需要实际实现技能的真实世界代码示例和项目。研究生项目贡献来自高级课程作业的任务，侧重于更复杂的设计和问题解决能力。问答论坛如 Stack Overflow 和 GitHub Q&A 包含开发人员常遇到的实用调试和问题解决任务，解决从业者面临的真实世界问题。

**三级（L3）来源**提供挑战硬件设计中最高专业水平的任务。这些包括经过流片验证的仓库，贡献来自已在硅上成功实现的项目的任务，确保高可靠性和复杂性。研究教科书提供源自硬件设计前沿研究的高级理论和实践问题。来自 ACM 和 IEEE 的同行评审出版物包括基于该领域最新进展的任务。学生竞赛提供来自硬件设计竞赛的具有挑战性的问题，而高级微架构研究提供涉及复杂架构设计和优化的任务。创新项目引入推动当前技术边界的问题，工业项目提供源自真实世界工业应用的任务，强调实际实现和优化。

这些来自不同来源的任务进一步分类，以涵盖各种技能和知识领域。专注于知识迁移的任务评估将学到的概念应用于新场景的能力，增强设计方法的适应性。涉及代码调试的任务需要识别和纠正代码中的错误，这对开发健壮的硬件系统至关重要。知识掌握任务评估对基本概念理解的深度，确保扎实的理论基础。代码生成任务需要基于给定规范创建新代码，测试创新和有效实现设计要求的能力。

这些任务被组织为 GenBen 基准测试的两个主要类别：基于文本的任务和多模态任务。基于文本的任务是纯文本的，侧重于理论和概念理解，包括问题解决和分析推理。多模态任务涉及多种形式的数据，如文本和图表，以模拟真实世界的设计挑战，并提供更全面的实践技能评估。

图 20 说明了数据源与最终数据集之间的关系。值得注意的是，相当一部分流片验证的设计来自 Google FOSS 和 OpenCores 等资源，如图 18 和 19 所示。

### A.5 生成式基准的概念和原理

生成式基准的概念涉及创建不直接以明文形式存储在 GitHub 等平台上的评估任务，而是隐式分布在各个数据集中。这种方法需要使用脚本动态提取任务，排列选项，并在每次生成时随机化问题顺序。这种方法有助于减轻模型预训练记忆造成的干扰，确保评估基于能力而非记忆化。

这种生成式方法背后的原理是确保每个生成的任务在每次评估中保持一致，从而保持评估的客观性和公平性。此外，引入一个仅进行表面级扰动的对照组，允许同时评估两组，提供对模型对此类变化敏感度的洞察。

此外，GenBen 支持研究人员替换或修改评估方法和任务，因为测试、评估框架和生成脚本是解耦的。这种灵活性允许基准测试适应不同的研究需求，并纳入新的评估策略。

#### A.5.1 测试生成算法

**算法 1：测试生成算法**

```
Require: 测试数据集 D
Ensure: 生成的测试集 T 和扰动测试集 T'
 1: 初始化测试集 T ← ∅
 2: 初始化扰动测试集 T' ← ∅
 3: 加载测试数据集 D
 4: for each 测试 d ∈ D do
 5:    使用脚本从 d 生成任务 t
 6:    将任务 t 添加到 T
 7: end for
 8: for each 任务 t ∈ T do
 9:    对 t 应用表面级扰动生成 t'
10:    将扰动任务 t' 添加到 T'
11: end for
12: return T 和 T'
```

**算法 2：总体评估流程**

```
Require: 测试集 T, 扰动测试集 T', 模型的 API A, 模态信息 M
Ensure: 评估结果和最终分数
 1: 初始化响应集 R ← ∅
 2: 初始化扰动响应集 R' ← ∅
 3: 初始化评估结果 E ← ∅
 4: 初始化最终分数 S ← ∅
 5: for each 任务 t ∈ T do
 6:    使用 API A 从模型收集响应 r
 7:    将响应 r 添加到 R
 8: end for
 9: for each 扰动任务 t' ∈ T' do
10:    使用 API A 从模型收集响应 r'
11:    将响应 r' 添加到 R'
12: end for
13: for each 响应 r ∈ R 和 r' ∈ R' do
14:    使用评估套件验证 r 和 r'
15:    使用 Icarus Verilog 仿真 r 和 r'
16:    生成语法和功能正确性报告
17:    if r 和 r' 通过功能测试 then
18:       使用 SkyWater 130nm PDK 和 OpenLane 进行物理实现
19:       使用 Yosys 提取可综合性、面积和功耗数据
20:       使用 OpenSTA 提取时序相关数据
21:    end if
22:    将评估结果添加到 E
23: end for
24: 使用报告分析器分析 E 中的评估结果
25: 基于预定义指标生成最终分数 S
26: return S
```

### A.6 实验结果

我们将任务分为三组：GenBen-all、GenBen-mm 和 GenBen-text，分别对应所有任务、多模态任务和基于文本的任务。此外，后两类进一步细分为 L1 至 L3 级别。

**表 6：测试的多模态模型在 GenBen-all 上的结果**

| 数据集 | 模型 | 知识掌握 | 知识迁移 | 调试 | 功能正确性 | 语法正确性 | 可综合性 |
|--------|------|---------|---------|------|----------|----------|---------|
| GENBEN-all | gpt-4-turbo | 57.00% | 56.00% | 40.00% | 21.20% | 100.00% | 93.70% |
| GENBEN-all | gpt-4o | 69.00% | 65.00% | 52.20% | 34.80% | 100.00% | 96.90% |
| GENBEN-all | claude3.5 | 59.00% | 55.00% | 55.40% | 35.40% | 98.60% | 90.00% |
| GENBEN-all | qwen-vl-plus | 45.00% | 39.00% | 32.00% | 16.30% | 78.40% | 66.40% |
| GENBEN-all | qwen-vl-max | 59.00% | 49.00% | 36.50% | 26.50% | 88.60% | 78.90% |
| GENBEN-all | GLM-4V-plus | 51.00% | 55.00% | 39.60% | 12.50% | 71.70% | 51.10% |

**表 7：所有测试模型在 GenBen-Text 上的结果**

| 数据集 | 模型 | 知识掌握 | 知识迁移 | 调试 | 功能正确性 | 语法正确性 | 可综合性 |
|--------|------|---------|---------|------|----------|----------|---------|
| GENBEN-text | gpt-4-turbo | 65.00% | 62.00% | 35.60% | 21.30% | 100.00% | 89.80% |
| GENBEN-text | gpt-4o | 75.00% | 70.00% | 40.00% | 32.00% | 97.50% | 96.00% |
| GENBEN-text | gpt-3.5-turbo | 63.00% | 60.00% | 37.80% | 26.70% | 98.10% | 93.30% |
| GENBEN-text | claude3.5 | 62.00% | 58.00% | 46.00% | 22.10% | 98.10% | 89.10% |
| GENBEN-text | qwen-vl-max | 60.00% | 50.00% | 43.40% | 20.20% | 84.80% | 76.90% |
| GENBEN-text | qwen-vl-plus | 52.00% | 47.00% | 43.00% | 20.20% | 84.90% | 76.90% |
| GENBEN-text | GLM-4V-plus | 57.00% | 51.00% | 42.20% | 7.50% | 65.60% | 45.30% |
| GENBEN-text | llama3 | 68.00% | 60.00% | 40.00% | 6.90% | 85.90% | 57.30% |
| GENBEN-text | GLM-4 | 57.00% | 48.00% | 39.20% | 7.50% | 65.60% | 45.30% |

**表 8：Claude 3.5 在部分生成设计上的 PPA 信息**

（表格数据展示 Claude 3.5 在 Text 和 Multimodal 模态下的功能正确性、面积、功耗、Hold WNS、Setup TNS 的生成值与参考值对比）

**表 9：GPT-4 在部分生成设计上的 PPA 信息**

（表格数据展示 GPT-4 在 Text 和 Multimodal 模态下的功能正确性、面积、功耗、Hold WNS、Setup TNS 的生成值与参考值对比）

**表 10：测试模型的详细结果**

（包含各模型在 GenBen-all、GenBen-allmodal-L1/L2/L3、GenBen-mm、GenBen-mm-L1/L2/L3、GenBen-text、GenBen-text-L1/L2/L3 等子集上的知识掌握、知识迁移、调试、功能正确性、语法正确性、可综合性的详细分数）

结果如表 10 所示。这提供了测试模型的统计分析，涵盖知识掌握、知识迁移、调试、功能正确性、语法正确性和可综合性。对于进一步的 QoR 分析，表现最好的模型 GPT-4o 和 Claude 3.5 的数据包含在正文中。

表中的数据展示了任务分类的有效性、可综合性指标的必要性以及知识点与编码能力之间的相关性，与基准测试的设计预期一致。

### A.7 教程：使用 GenBen 评估 LLM 性能

您可以通过以下链接访问完整的 GenBen 代码：GenBen Repository。本指南将指导您通过命令行评估大语言模型（LLMs）在硬件设计中的性能并获取详细结果。

#### A.7.1 分步说明

**1. 克隆 GenBen 仓库**

首先，将 GenBen 仓库克隆到本地机器：
```bash
git clone https://anonymous.4open.science/r/GENBEN-2812
cd GENBEN-2812
```

**2. 运行评估脚本**

使用命令行，您可以通过以下命令评估 LLM 的性能：
```bash
python genben.py --mode all --model gpt4
```
此命令使用指定的参数运行评估。

**3. 理解命令参数**

- `--mode`：此参数控制输入 LLM 的任务类型。有三个可用选项：
  - `all`：启用所有任务类型的输入。
  - `mm`：允许多模态任务。
  - `text`：仅限制为基于文本的任务输入。

- `--model`：此参数指定 LLM 的模型。根据您使用的 LLM 的具体 API 调整此参数。

**示例**：
```bash
python genben.py --mode text --model gpt4
```
此命令仅使用基于文本的任务评估 gpt4 模型。

#### A.7.2 详细使用说明请参阅 README

有关更详细的使用说明，请参阅 GenBen 项目中包含的 README 文件。README 文件包含全面的信息。

### A.8 开源声明

为了促进透明度、协作和创新，GenBen 基准测试将根据 MIT 开源许可证发布。这确保研究人员、教育工作者和从业者可以自由访问、使用、修改和分发该基准测试而不受任何限制。

在同行评审过程完成后，完整的数据集连同所有相关脚本和文档将公开发布。我们希望支持全球研究社区在推进硬件设计和 AI 驱动 EDA 领域的发展。

---

> **翻译说明**：本文为 ICLR 2025 投稿论文《GenBen: A Generative Benchmark for LLM-Aided Design》的逐行中文翻译。翻译力求准确传达原文含义，专业术语保持与业界惯例一致。部分图和表的原始数据已保留在翻译中。
