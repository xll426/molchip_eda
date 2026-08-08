# molchip_eda — AI4EDA 论文深度解读与开源索引

> 📚 **110 篇论文深度讲解** · 102 个论文目录 · 全部分类 + 开源标注 + 点击直达
> 🏷️ 初版 v0.3 — 后续持续更新完善
> 📖 完整导航：[00-总索引.md](00-总索引.md) · 校验：`python3 _校验.py`（110/110 通过 ✅）

---

## 30 秒速览

本仓库为 AI4EDA（AI for Electronic Design Automation）领域 **110 篇论文** 提供统一格式的深度技术解读。

- **一篇论文 = 一份 `论文深度讲解.md`**，按 12 节骨架组织
- **每份解读包含**：一句话定位 → EDA 17 阶段映射 → 输入/输出样例 → 方法架构 ASCII 图 → 公式推导 → 实验数据 → 创新点 → 缩写表 → 芯片流程关系 → 讨论局限 → 复现信息 → 一分钟复述
- **想快速判断一篇论文是否与你相关**：读第 1 节「一句话定位」（30 秒）+ 第 2 节「EDA 阶段映射」（确认它落在芯片流程哪一段）

---

## 📊 论文分类总览

### 🏆 🔥 重点推荐（高价值论文 Top 30）

按 会议级别 × 开源 × 影响力 综合排序。点击论文名直接跳转深度讲解。

| # | 论文 | 会议 | 代码 | 方向 | 一句话亮点 |
|---:|---|---|:---:|---|------|
| 1 | [VeriTrace](VeriTrace/论文深度讲解.md) | arXiv 2026 | ⏳ | RTL 生成 | 首个 VerilogEval-V2 **100% Pass@1**，多 Agent 时序探索调试 |
| 2 | [CircuitFusion](CircuitFusion/论文深度讲解.md) | **ICLR 2025** | ✅ | 电路表示 | 首个多模态电路编码器（HDL+图+功能摘要），zero-shot PPA 预测 |
| 3 | [DeepGate4](DeepGate4/论文深度讲解.md) | **ICLR 2025** | ✅ | 电路表示 | 亚线性内存图 Transformer，1.6M 门电路训练，92.9% SAT 加速 |
| 4 | [TopoRTL](TopoRTL/论文深度讲解.md) | **ICLR 2026** | ✅ | 电路表示 | 拓扑信息对 RTL 电路表示至关重要 |
| 5 | [R2G](R2G/论文深度讲解.md) | **CVPR 2026** | ✅ | Benchmark | RTL→GDSII 多视图电路图 benchmark，覆盖率 8/17 |
| 6 | [QiMeng](QiMeng/论文深度讲解.md) | arXiv 2025 | ⏳ | 全流程系统 | 中科院三层全自动处理器设计，LPCM 多模态大模型，CPU-v2 对标 A53 |
| 7 | [ChipNeMo](ChipNeMo/论文深度讲解.md) | **DAC 2024** | ❌ | 领域 LLM | NVIDIA 芯片设计域适配 LLM，覆盖率 9/17（最高） |
| 8 | [RTLFixer](RTLFixer/论文深度讲解.md) | **DAC 2024** | ✅ | RTL 修复 | ReAct+RAG 自动化语法修复，**98.5%** 修复率，NVIDIA |
| 9 | [MAGE](MAGE/论文深度讲解.md) | **ICCAD 2024** | ✅ | RTL 生成 | 多 Agent 协作 RTL 生成，不训练模型，仿真反馈迭代修复 |
| 9 | [BetterV](BetterV/论文深度讲解.md) | **ICML 2024** | ⏳ | RTL 生成 | 判别式引导受控 Verilog 生成，Bayes+Langevin 动力学 |
| 10 | [CraftRTL](CraftRTL/论文深度讲解.md) | **ICLR 2025** | ✅ | RTL 生成 | NVIDIA 正确即构造（KMap/FSM）+ 目标代码修复 |
| 11 | [CircuitNet3.0](CircuitNet3.0/论文深度讲解.md) | **ICLR 2025** | ⏳ | 数据集 | 多模态早期 PPA 预测，RTLDistil 蒸馏+MOSS 编码，覆盖率 9/17 |
| 12 | [CodeV-R1](CodeV-R1/论文深度讲解.md) | **NeurIPS 2025** | ✅ | RTL 生成 | NLCDE 数据合成 + distill-then-RL 管线 |
| 13 | [SynthLoop-Eval](SynthLoop-Eval/论文深度讲解.md) | **GLSVLSI 2026** | ⏳ | Benchmark | HQI 综合闭环评测，32 模型评估 |
| 14 | [ChipSeek](ChipSeek/论文深度讲解.md) | arXiv 2025 | ✅ | RTL 生成 | SFT+CDPO 强化学习，用 EDA 工具反馈更新模型权重 |
| 15 | [VerilogCoder](VerilogCoder/论文深度讲解.md) | **ICCAD 2024** | ✅ | RTL 生成 | NVIDIA 多 Agent Verilog 生成+自修正，AST 感知任务规划 |
| 16 | [DeepGate3](DeepGate3/论文深度讲解.md) | **ICCAD 2024** | ✅ | 电路表示 | Transformer+GNN 双链路电路学习，解决大规模 scalability |
| 17 | [GenEDA](GenEDA/论文深度讲解.md) | **ICCAD 2025** | ✅ | 电路表示 | 首个跨模态电路-LLM 对齐框架，门级网表→RTL 反向翻译 |
| 18 | [DecoRTL](DecoRTL/论文深度讲解.md) | **ICCAD 2025** | ✅ | RTL 生成 | 推理时 contrastive re-rank+自适应温度解码 |
| 19 | [FVEval](FVEval/论文深度讲解.md) | **DAC 2025** | ✅ | 形式验证 | 形式验证 LLM 评测基准，Cadence JasperGold 评估（UCB/NVIDIA） |
| 20 | [RocketPPA](RocketPPA/论文深度讲解.md) | **MLSys 2026** | ❌ | PPA 预测 | LLM+MoE 代码级 PPA 预测，**20×** 快于 MetRex |
| 21 | [RTL-BenchLS](RTL-BenchLS/论文深度讲解.md) | arXiv 2026 | ✅ | Benchmark | 10,000+ 形式验证 Verilog 设计，3 种自监督任务 |
| 22 | [CLOSER-Bench](CLOSER-Bench/论文深度讲解.md) | arXiv 2026 | ⏳ | 跨阶段 | **10/17**（覆盖率最高），跨阶段 design closure |
| 23 | [FluxBench](FluxBench/论文深度讲解.md) | arXiv 2026 | ✅ | 跨阶段 | RTL-to-GDS Agent 评测，覆盖率 9/17 |
| 24 | [ScaleRTL](ScaleRTL/论文深度讲解.md) | **MLCAD 2025** | ⏳ | RTL 生成 | NVIDIA reasoning LLM for RTL，3.5B-token CoT |
| 25 | [VFlow](VFlow/论文深度讲解.md) | arXiv 2025 | ⏳ | RTL 生成 | MCTS 工作流优化 Verilog 生成，84.3% Machine pass@1 |
| 26 | [MGVGA](MGVGA/论文深度讲解.md) | **ICLR 2025** | ✅ | 电路表示 | 门级掩码建模（MGM）+ Verilog-AIG 对齐（VGA） |
| 27 | [PCB-Bench](PCB-Bench/论文深度讲解.md) | **ICLR 2026** | ✅ | 跨领域 | PCB 布局布线 LLM 评测基准，3,700+ 题目 |
| 28 | [CorrectHDL](CorrectHDL/论文深度讲解.md) | arXiv 2025 | ✅ | RTL 生成 | 以 HLS 为参考的 Agentic HDL 生成 |
| 29 | [SpecLoop](SpecLoop/论文深度讲解.md) | arXiv 2026 | ⏳ | RTL 逆向 | RTL→Spec 逆向生成 + 形式验证反馈闭环（NTU+MediaTek） |
| 30 | [FuncGNN](FuncGNN/论文深度讲解.md) | **ACM TRETS 2026** | ✅ | 电路表示 | GNN 学习逻辑电路功能语义 |
| 31 | [AnalogGenie](AnalogGenie/论文深度讲解.md) | arXiv 2025 | ✅ | 跨领域 | 模拟电路基础模型，3,350 拓扑生成 |

> 📝 【开源标注说明】✅ = GitHub 仓库已确认 · ⏳ = 论文声明将开源/等待发布 · ❌ = 闭源/未公开
> 🔗 点击论文名直接打开深度讲解

---

### 📂 按研究方向分类（全部 110 篇）

#### 1. RTL 生成、修复与 Agent（29 篇）

| 论文 | 会议 | 代码 | 覆盖率 | 链接 |
|---|---:|---|:---:|------|
| VeriTrace | arXiv 2026 | ⏳ | 2/17 | [📄](VeriTrace/论文深度讲解.md) |
| **QiMeng** | arXiv 2025 | ⏳ | 12-15/17 | [📄](QiMeng/论文深度讲解.md) |
| MAGE | ICCAD 2024 | ✅ | 2/17 | [📄](MAGE/论文深度讲解.md) |
| ChipSeek | arXiv 2025 | ✅ | ~3.5/17 | [📄](ChipSeek/论文深度讲解.md) |
| VerilogCoder | ICCAD 2024 | ✅ | 2/17 | [📄](VerilogCoder/论文深度讲解.md) |
| CodeV-R1 | NeurIPS 2025 | ✅ | 2/17 | [📄](CodeV-R1/论文深度讲解.md) |
| ScaleRTL | MLCAD 2025 | ⏳ | 2/17 | [📄](ScaleRTL/论文深度讲解.md) |
| BetterV | ICML 2024 | ⏳ | 4/17 | [📄](BetterV/论文深度讲解.md) |
| DecoRTL | ICCAD 2025 | ✅ | 2/17 | [📄](DecoRTL/论文深度讲解.md) |
| CraftRTL | ICLR 2025 | ✅ | 2/17 | [📄](CraftRTL/论文深度讲解.md) |
| VFlow | arXiv 2025 | ⏳ | 2/17 | [📄](VFlow/论文深度讲解.md) |
| RTLFixer | DAC 2024 | ✅ | 2/17 | [📄](RTLFixer/论文深度讲解.md) |
| CorrectHDL | arXiv 2025 | ✅ | 2.5/17 | [📄](CorrectHDL/论文深度讲解.md) |
| CASS-RTL | arXiv 2026 | ✅ | 2/17 | [📄](CASS-RTL/论文深度讲解.md) |
| ChipMATE | arXiv 2025 | ✅ | 2/17 | [📄](ChipMATE/论文深度讲解.md) |
| AutoChip | arXiv 2024 | ✅ | 2/17 | [📄](AutoChip/论文深度讲解.md) |
| AutoVCoder | arXiv 2024 | ✅ | 2/17 | [📄](AutoVCoder/论文深度讲解.md) |
| RTLCoder (arXiv) | arXiv 2023 | ✅ | 1/17 | [📄](RTL-Coder/论文深度讲解_RTLCoder-arXiv.md) |
| RTLCoder (TCAD) | TCAD 2025 | ✅ | 1/17 | [📄](RTL-Coder/论文深度讲解_RTLCoder-TCAD2025.md) |
| OriGen | arXiv 2024 | ✅ | 2/17 | [📄](OriGen/论文深度讲解.md) |
| ROME-LLM | arXiv 2024 | ✅ | 2/17 | [📄](ROME-LLM/论文深度讲解.md) |
| ChipGPT-V | arXiv 2024 | ✅ | 2/17 | [📄](chipgptv/论文深度讲解.md) |
| VClare | arXiv 2026 | ⏳ | 2/17 | [📄](VClare/论文深度讲解.md) |
| RTLCurator | arXiv 2026 | ⏳ | 2/17 | [📄](RTLCurator/论文深度讲解.md) |
| VeriGen (模型) | arXiv 2023 | ✅ | 2/17 | [📄](VGen/论文深度讲解_VeriGen-Model.md) |
| VeriGen (Benchmark) | arXiv 2022 | ✅ | 2/17 | [📄](VGen/论文深度讲解_VeriGen-Benchmark.md) |
| VeriReason | arXiv 2025 | ⏳ | 5/17 | [📄](VeriReason/论文深度讲解.md) |
| ChipNeMo | DAC 2024 | ❌ | 9/17 | [📄](ChipNeMo/论文深度讲解.md) |
| ChatHLS | ACL 2026 | ✅ | 5/17 | [📄](ChatHLS/论文深度讲解.md) |

#### 2. Benchmark 与评测（20 篇）

| 论文 | 会议 | 代码 | 覆盖率 | 链接 |
|---|---:|---|:---:|------|
| VerilogEval v1 | arXiv 2023 | ✅ | 2/17 | [📄](VerilogEval/论文深度讲解_VerilogEval-v1.md) |
| VerilogEval v2 | arXiv 2024 | ✅ | 2/17 | [📄](VerilogEval/论文深度讲解_VerilogEval-v2.md) |
| RTLLM | ICCAD 2023 | ✅ | 3/17 | [📄](RTLLM/论文深度讲解_RTLLM.md) |
| OpenLLM-RTL | arXiv 2025 | ✅ | 3/17 | [📄](RTLLM/论文深度讲解_OpenLLM-RTL.md) |
| ChipBench | arXiv 2026 | ✅ | 2/17 | [📄](ChipBench/论文深度讲解.md) |
| RealBench | arXiv 2025 | ✅ | 5/17 | [📄](RealBench/论文深度讲解.md) |
| ArchXBench | arXiv 2025 | ✅ | 2/17 | [📄](ArchXBench/论文深度讲解.md) |
| ChipVerilog | arXiv 2026 | ✅ | 3/17 | [📄](ChipVerilog/论文深度讲解.md) |
| RTL-BenchLS | arXiv 2026 | ✅ | 3/17 | [📄](RTL-BenchLS/论文深度讲解.md) |
| SynthLoop-Eval | GLSVLSI 2026 | ⏳ | 3/17 | [📄](SynthLoop-Eval/论文深度讲解.md) |
| GenBen | ICLR 2025 | ⏳ | 4/17 | [📄](GenBen/论文深度讲解.md) |
| CreativEval | arXiv 2024 | ✅ | 2/17 | [📄](CreativEval/论文深度讲解.md) |
| ResBench | HEART 2025 | ✅ | 2.5/17 | [📄](ResBench/论文深度讲解.md) |
| R2G | CVPR 2026 | ✅ | 8/17 | [📄](R2G/论文深度讲解.md) |
| OpenRTLSet | ICLAD 2025 | ✅ | 2/17 | [📄](OpenRTLSet/论文深度讲解.md) |
| ICRTL | arXiv 2026 | ✅ | 2/17 | [📄](ICRTL/论文深度讲解.md) |
| HLS-Eval | arXiv 2025 | ✅ | 3/17 | [📄](HLS-Eval/论文深度讲解.md) |
| FVEval | DAC 2025 | ✅ | 2/17 | [📄](FVEval/论文深度讲解.md) |
| cvdp_benchmark | arXiv 2025 | ✅ | 3/17 | [📄](cvdp_benchmark/论文深度讲解.md) |
| PCB-Bench | ICLR 2026 | ✅ | 跨域 | [📄](PCB-Bench/论文深度讲解.md) |

#### 3. 电路表示学习与数据集（16 篇）

| 论文 | 会议 | 代码 | 覆盖率 | 链接 |
|---|---:|---|:---:|------|
| DeepGate | arXiv 2021 | ✅ | 1/17 | [📄](DeepGate/论文深度讲解.md) |
| DeepGate2 | DAC 2023 | ✅ | 2/17 | [📄](DeepGate2/论文深度讲解.md) |
| DeepGate3 | ICCAD 2024 | ✅ | 3/17 | [📄](DeepGate3/论文深度讲解.md) |
| **DeepGate4** | **ICLR 2025** | ✅ | 3/17 | [📄](DeepGate4/论文深度讲解.md) |
| MGVGA | ICLR 2025 | ✅ | 2/17 | [📄](MGVGA/论文深度讲解.md) |
| TopoRTL | ICLR 2026 | ✅ | 1/17 | [📄](TopoRTL/论文深度讲解.md) |
| **CircuitFusion** | **ICLR 2025** | ✅ | 3/17 | [📄](CircuitFusion/论文深度讲解.md) |
| CircuitNet 1.0 | DAC 2022 | ⏳ | 6/17 | [📄](CircuitNet/论文深度讲解_CircuitNet1.0.md) |
| CircuitNet 2.0 | ICLR 2024 | ⏳ | 9/17 | [📄](CircuitNet/论文深度讲解_CircuitNet2.0.md) |
| CircuitNet 3.0 | ICLR 2025 | ⏳ | 9/17 | [📄](CircuitNet3.0/论文深度讲解.md) |
| OpenABC-D | ICCAD 2022 | ✅ | 2/17 | [📄](OpenABC-D/论文深度讲解.md) |
| ACE | ICCAD 2024 | ✅ | 3/17 | [📄](ACE/论文深度讲解.md) |
| StructRTL | arXiv 2025 | ✅ | 2/17 | [📄](StructRTL/论文深度讲解.md) |
| FuncGNN | ACM TRETS 2026 | ✅ | 2/17 | [📄](FuncGNN/论文深度讲解.md) |
| SynC-LLM | EMNLP 2025 | ✅ | 2/17 | [📄](SynC-LLM/论文深度讲解.md) |
| GenEDA | ICCAD 2025 | ✅ | 3/17 | [📄](GenEDA/论文深度讲解.md) |

#### 4. 逻辑综合与 PPA 预测（4 篇）

| 论文 | 会议 | 代码 | 覆盖率 | 链接 |
|---|---:|---|:---:|------|
| CircuitEvo | ICLR 2025 | ✅ | 2/17 | [📄](CircuitEvo/论文深度讲解.md) |
| RTL-Sequencer | arXiv 2026 | ❌ | 2/17 | [📄](RTL-Sequencer/论文深度讲解.md) |
| DREAMPlace | DAC 2019 | ✅ | 1/17 | [📄](DREAMPlace/论文深度讲解.md) |
| **RocketPPA** | **MLSys 2026** | ❌ | 3/17 | [📄](RocketPPA/论文深度讲解.md) |

#### 5. 验证、修复与形式化（16 篇）

| 论文 | 会议 | 代码 | 覆盖率 | 链接 |
|---|---:|---|:---:|------|
| GoGoTB | arXiv 2026 | ✅ | 1/17 | [📄](GoGoTB/论文深度讲解.md) |
| MechMem-RTL | arXiv 2026 | ⏳ | 2/17 | [📄](MechMem-RTL/论文深度讲解.md) |
| Rtl2lean | arXiv 2026 | ❌ | 1/17 | [📄](Rtl2lean/论文深度讲解.md) |
| OpenSource-Formal-RTL | arXiv 2026 | ✅ | 2/17 | [📄](OpenSource-Formal-RTL/论文深度讲解.md) |
| VeriRefine | arXiv 2026 | ✅ | 3/17 | [📄](VeriRefine/论文深度讲解.md) |
| ChipFuzzer | arXiv 2026 | ⏳ | 1/17 | [📄](ChipFuzzer/论文深度讲解.md) |
| VeriChat | arXiv 2026 | ⏳ | 3/17 | [📄](VeriChat/论文深度讲解.md) |
| PRO-V | arXiv 2025 | ✅ | 1/17 | [📄](PRO-V/论文深度讲解.md) |
| HierSVA | arXiv 2026 | ✅ | 1/17 | [📄](HierSVA/论文深度讲解.md) |
| TrojanWhisper | arXiv 2024 | ✅ | 1/17 | [📄](TrojanWhisper/论文深度讲解.md) |
| CktFormalizer | arXiv 2025 | ⏳ | 6/17 | [📄](CktFormalizer/论文深度讲解.md) |
| SpecAlign | arXiv 2025 | ✅ | 2/17 | [📄](SpecAlign/论文深度讲解.md) |
| VeriDafny | arXiv 2025 | ❌ | 2/17 | [📄](VeriDafny/论文深度讲解.md) |
| AssertLLM | arXiv 2024 | ✅ | 1/17 | [📄](AssertLLM/论文深度讲解.md) |
| **SpecLoop** | arXiv 2026 | ⏳ | 2/17 | [📄](SpecLoop/论文深度讲解.md) |
| VerilogLAVD | arXiv 2026 | ⏳ | 1/17 | [📄](VerilogLAVD/论文深度讲解.md) |

#### 6. 物理设计、跨阶段与成本（7 篇）

| 论文 | 会议 | 代码 | 覆盖率 | 链接 |
|---|---:|---|:---:|------|
| CLOSER-Bench | arXiv 2026 | ⏳ | 10/17 | [📄](CLOSER-Bench/论文深度讲解.md) |
| FluxBench | arXiv 2026 | ✅ | 9/17 | [📄](FluxBench/论文深度讲解.md) |
| PDAGENT-BENCH | arXiv 2026 | ⏳ | 7/17 | [📄](PDAGENT-BENCH/论文深度讲解.md) |
| ARES | arXiv 2026 | ⏳ | 3/17 | [📄](ARES/论文深度讲解.md) |
| VPR-Evolve | arXiv 2026 | ✅ | 3/17 | [📄](VPR-Evolve/论文深度讲解.md) |
| AlphaRoute | IEEE LAD 2026 | ✅ | 4/17 | [📄](AlphaRoute/论文深度讲解.md) |
| ARCADE | IEEE VTS 2026 | ✅ | 5/17 | [📄](ARCADE/论文深度讲解.md) |

#### 7. EDA Agent 与流程编排（3 篇）

| 论文 | 会议 | 代码 | 覆盖率 | 链接 |
|---|---:|---|:---:|------|
| ChatEDA | arXiv 2023 | ✅ | 5/17 | [📄](ChatEDA/论文深度讲解_ChatEDA.md) |
| Multi-Agent ChatEDA | NAACL 2025 | ✅ | 5/17 | [📄](ChatEDA/论文深度讲解_Multi-Agent-ChatEDA.md) |
| CircuitWeave | arXiv 2026 | ❌ | 2/17 | [📄](CircuitWeave/论文深度讲解.md) |

#### 8. 跨领域 — 光子 / 模拟 / RF / PCB（11 篇）

| 论文 | 领域 | 会议 | 代码 | 链接 |
|---|---:|---|---|:---:|------|
| PICBench | 光子 | arXiv 2025 | ✅ | [📄](PICBench/论文深度讲解.md) |
| AMS-IO-Bench | 模拟 | AAAI 2026 | ⏳ | [📄](AMS-IO-Bench/论文深度讲解.md) |
| SINA | 模拟 | arXiv 2026 | ⏳ | [📄](SINA/论文深度讲解.md) |
| Weave | 模拟 | arXiv 2026 | ✅ | [📄](Weave/论文深度讲解.md) |
| RF-Agent | RFIC | arXiv 2026 | ✅ | [📄](RF-Agent/论文深度讲解.md) |
| OmniLayout | PCB | arXiv 2026 | ⏳ | [📄](OmniLayout/论文深度讲解.md) |
| AnalogSeeker | 模拟 | arXiv 2025 | ✅ | [📄](AnalogSeeker/论文深度讲解.md) |
| Masala-CHAI | 模拟 | arXiv 2024 | ✅ | [📄](Masala-CHAI/论文深度讲解.md) |
| **AnalogGenie** | 模拟 | arXiv 2025 | ✅ | [📄](AnalogGenie/论文深度讲解.md) |
| SchGen | PCB | arXiv 2025 | ⏳ | [📄](SchGen/论文深度讲解.md) |
| OptiCo | 光刻 | CVPR 2026 | ❌ | [📄](OptiCo/论文深度讲解.md) |

#### 9. 综述（4 篇）

| 论文 | 会议 | 覆盖率 | 链接 |
|---|---:|---|:---:|------|
| CFM（电路基础模型综述） | arXiv 2025 | 12/17 | [📄](AI4eda综述/论文深度讲解_CFM.md) |
| LLM4EDA 综述 | arXiv 2025 | 7/17 | [📄](AI4eda综述/论文深度讲解_LLM4EDA.md) |
| Verilog LLM 综述 | arXiv 2025 | 2/17 | [📄](AI4eda综述/论文深度讲解_VerilogLLM.md) |
| Agentic EDA 综述 | arXiv 2025 | 跨阶段 | [📄](AgenticEDA综述/论文深度讲解.md) |

---

### 📈 开源率统计

| 分类 | 总数 | 已开源 ✅ | 待发布 ⏳ | 闭源 ❌ |
|---|---:|---:|---:|---:|
| RTL 生成、修复与 Agent | 29 | 18 | 9 | 2 |
| Benchmark 与评测 | 20 | 17 | 3 | 0 |
| 电路表示学习与数据集 | 16 | 13 | 3 | 0 |
| 逻辑综合与 PPA 预测 | 4 | 2 | 0 | 2 |
| 验证、修复与形式化 | 16 | 8 | 6 | 2 |
| 物理设计与跨阶段 | 7 | 4 | 3 | 0 |
| EDA Agent 与流程编排 | 3 | 2 | 0 | 1 |
| 跨领域 | 11 | 6 | 4 | 1 |
| 综述 | 4 | 0 | 0 | 4 |
| **总计** | **110** | **70 (64%)** | **28 (25%)** | **12 (11%)** |

---

## 🗺️ 推荐阅读路线

### 入门路线（3 篇，快速建立全局视角）

1. [AgenticEDA综述](AgenticEDA综述/论文深度讲解.md) — 了解什么是 Agentic EDA
2. [LLM4EDA 综述](AI4eda综述/论文深度讲解_LLM4EDA.md) — 了解 LLM 在 EDA 各阶段的应用全景
3. [芯片流程.md](芯片流程.md) — 理解 17 阶段 EDA 标准流程

### RTL 生成路线（5 篇）

1. [VerilogEval v1](VerilogEval/论文深度讲解_VerilogEval-v1.md) → [v2](VerilogEval/论文深度讲解_VerilogEval-v2.md) — 理解评测标准
2. [MAGE](MAGE/论文深度讲解.md) — 推理时多 Agent（不训练模型）
3. [ChipSeek](ChipSeek/论文深度讲解.md) — 训练时强化学习（更新模型权重）
4. [VeriTrace](VeriTrace/论文深度讲解.md) — 100% Pass@1 的 SOTA 方法

### 电路表示学习路线（4 篇）

1. [DeepGate](DeepGate/论文深度讲解.md) → [DeepGate2](DeepGate2/论文深度讲解.md) — 经典基础
2. [DeepGate4](DeepGate4/论文深度讲解.md) — 百万门级扩展方案
3. [CircuitFusion](CircuitFusion/论文深度讲解.md) — 多模态编码新范式

### 验证与形式化路线（3 篇）

1. [FVEval](FVEval/论文深度讲解.md) — 形式验证评测基线
2. [GoGoTB](GoGoTB/论文深度讲解.md) — Agentic 验证与覆盖率闭合
3. [AssertLLM](AssertLLM/论文深度讲解.md) — 断言生成评测

---

## 📂 仓库结构

```text
molchip_eda/
├── README.md                         ← 你在这里
├── 00-总索引.md                      ← 完整导航（110 篇分类总表 + 覆盖率反查 + 组会轮次）
├── 芯片流程.md                       ← 17 阶段标准编号定义（①-⑰）
├── _合并规范.md                      ← 12 节骨架写作规范
├── _校验.py                          ← 机器校验脚本
├── 论文原文归档清单_20260802.md
├── 新增参考文献_20260804.bib
│
├── <论文目录> ×102/                   ← 每个目录 = 论文深度讲解.md + PDF + TXT
│   例：VeriTrace/ MAGE/ DeepGate4/ CircuitFusion/ ChipNeMo/ ...
│
├── AI4eda综述/                       ← 3 篇综述 + 增量调研报告
└── OpenABC/                          ← 重复归档目录（→ OpenABC-D/）
```

每个论文目录的标准结构：

```text
论文目录/
├── 论文深度讲解.md          ← 唯一正文（12 节骨架）
├── xxxx.pdf                 ← 论文原文
├── xxxx.txt                 ← pdftotext 提取文本（事实校对来源）
└── （少数）复现详解.md       ← 本地复现记录
```

---

## 🔍 如何找到你需要的论文

**按阶段找**：打开 [00-总索引.md 第 4 节](00-总索引.md#4-按阶段覆盖率查找)，按 ①-⑰ 阶段反查

**按方向找**：本 README 上方分类表格，每个论文名都是可点击链接

**按关键词找**：GitHub 仓库内搜索（`grep` 或 GitHub Search），每篇解读包含英文论文标题和 EDA 缩写表

**按会议找**：聚焦 ICLR / DAC / ICCAD / NeurIPS 等顶会论文（见重点推荐 Top 30）

---

## 📝 贡献与更新计划

- [ ] 补充更多 2025-2026 年新论文
- [ ] 增加论文之间的对比分析
- [ ] 完善开源代码的实际运行验证
- [ ] 增加中文术语对照表
- [ ] 补充 PPT 组会 slides

欢迎提 Issue / PR 补充新论文或修正错误。

---

## 📄 License

本仓库中的深度解读文档为原创内容。各论文目录下的 PDF 文件版权归原作者/出版社所有，仅供学术研究使用。

---

> 📖 完整导航：[00-总索引.md](00-总索引.md)
> 🔬 增量调研：[AI4eda综述/20260804_最新论文与开源代码补充.md](AI4eda综述/20260804_最新论文与开源代码补充.md)
> 📐 校验：`python3 _校验.py`（110/110 ✅）
