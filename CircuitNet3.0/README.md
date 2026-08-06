# CircuitNet 3.0 论文深度解读

> **CircuitNet 3.0: A Multi-Modal Dataset with Task-Oriented Augmentation for AI-Driven Circuit Design**
>
> ICLR 2026 · 中科院计算所 · 港中文 · 北大 · 斯坦福
>
> 📦 [github.com/sklp-eda-lab/iclr-circuitnet_3.0](https://github.com/sklp-eda-lab/iclr-circuitnet_3.0/)

---

## 文档导航

| # | 文档 | 重点 |
|---|------|------|
| 01 | [论文全面解读](./01-论文全面解读.md) | 完整翻译 + 全部数据表 |
| 02 | [AST语法树改写算法详解](./02-AST语法树改写算法详解.md) | Algorithm 2/3 逐行走读 |
| 03 | [数据集对比深度分析](./03-数据集对比深度分析.md) | 与 7 个数据集的横向对比 |
| 04 | [模型架构与任务详解](./04-模型架构与任务详解.md) | 8 个模型的输入输出架构 |
| — | [原论文 PDF](./8829_CircuitNet_3_0_A_Multi_Mo.pdf) | ICLR 2026 原文 |

---

## 30 秒速览

做了 **15,863 个芯片设计**的开源数据集。每个设计有 RTL 代码→网表→版图 的完整链条（文本+图+图像三种数据）。通过 **AST 语法树改写**（6 类变异算子）+ 任务导向过滤，专门训练 AI 在芯片设计早期预测时序和功耗。

- 多模态 > 单模态：时序 PCC +8%，MAPE -18%
- 最佳时序模型 RTLDistil：AT PCC 0.935 / TNS PCC 0.968
- 最佳功耗模型 MOSS：Total Power PCC 0.948 / MAPE 仅 7.4%

---

## 核心概念一图看懂

### 芯片设计的三个阶段

![Figure 2: EDA 工作流中三个设计阶段及对应数据模态](figures/fig2-design-representations.png)

> **Figure 2**：RTL 代码（文本，LLM 编码）→ 网表（图结构，GNN 编码）→ 版图（图像，CNN 编码）。三种模态对应三个抽象层级。

> 📖 **网表和版图到底有什么区别？寄生参数是什么？** 见 [01-论文全面解读 §3.1.1](./01-论文全面解读.md)——用半加器例子从 RTL→网表→版图一步步讲清楚，包括寄生电阻/电容为什么必须在版图阶段才能提取。

### 传统瀑布模型 vs 左移模型

![Figure 1: 传统瀑布模型 vs 现代左移模型](figures/fig1-waterfall-shiftleft.png)

> **Figure 1**：(a) 传统瀑布——RTL→网表→版图顺序执行，做完才验证，有问题就 ECO 回溯；(b) 左移——每阶段提前预测，大幅缩短周期。CircuitNet 3.0 为左移提供数据基础。

---

## 数据增强机制

![Figure 5: 数据增强三路流程 + Table 3: AST变异算子](figures/fig5-data-augmentation.png)

> **Figure 5**：(a) AST-based Rewrite —— 在语法树上做 6 类微调变异；(b) Timing-Task-Oriented —— compile_ultra + Innovus 迭代 → 只保留长路径的难设计；(c) Power-Task-Oriented —— 同 RTL 多配置综合 + Voltus 筛选活跃逻辑。

![Table 3: 六类 AST 变异算子](figures/table3-ast-mutation-operators.png)

> **Table 3**：算术/逻辑/关系/时序/赋值/常量六类变异、变换方式及约束条件。详见 [AST语法树改写算法详解](./02-AST语法树改写算法详解.md)。

### Algorithm 2：AST 变异流程

![Algorithm 2: AST-Based RTL Mutation Process](figures/algo2-ast-mutation.png)

> 完整流程：ParseVerilogToAST → BuildNodePaths → 收集候选变异 → RandomSample N个 → ApplyMutation + CheckConsistency → ASTToVerilog → PassesSynthesis 综合验证。详见 [02 号文档](./02-AST语法树改写算法详解.md)。

---

## 数据集对比

![Table 1: 开源 EDA 数据集全面对比](figures/table1-dataset-comparison.png)

> **Table 1**：VerilogEval / RTLLM / CircuitNet 2.0 / RTLCoder / CircuitNet 3.0 在开源、数据增强、综合验证、阶段覆盖、数据模态、设计数量、目标任务等维度的对比。详见 [03 号文档](./03-数据集对比深度分析.md)。

### 增强前后数据分布变化

![Figure 6: WNS 和 Power 增强前后分布对比](figures/fig6-distribution.png)

> **Figure 6**：(a-b) WNS 从 [-2.5,0]ns 扩展到 [-6,0]ns；(c-d) Power 从 <60mW 集中分布变为 0~160mW 均匀覆盖。详见 [03 号文档](./03-数据集对比深度分析.md)。

---

## 模型与任务

### 多模态预测框架

![Figure 8: 多阶段多模态预测框架](figures/fig8-prediction-framework.png)

> **Figure 8**：XGBoost/GNN/LLM/CNN 四路模型分别处理表格/图/文本/图像模态，覆盖逻辑设计到物理设计全流程。详见 [04 号文档](./04-模型架构与任务详解.md)。

### 模型性能对比

![Table 4: 多模态模型性能对比](figures/table4-performance.png)

> **Table 4**：(a) 时序预测——RTLDistil（多模态蒸馏）全面超越 MasterRTL 和 RTL-Timer（纯 RTL）；(b) 功耗预测——MOSS（RTL+网表多模态）全面超越 DeepSeq2（纯网表）。详见 [04 号文档](./04-模型架构与任务详解.md)。

---

## 实验配置速查

![Table 21: 关键实验规格](figures/table21-key-specs.png)

> **Table 21**：45nm CMOS (GSCLIB), TT 工艺角, 1.05V, 85°C, 1GHz。Synopsys DC 2020.09 + Cadence Innovus 19.11 + PrimePower + Voltus。8× A100, PyTorch 2.0.1, AdamW lr=2e-4。

---

## 文件夹结构

```
CircuitNet3.0/
├── README.md                              ← 你在这里
├── 8829_CircuitNet_3_0_A_Multi_Mo.pdf     ← 原论文
├── 01-论文全面解读.md
├── 02-AST语法树改写算法详解.md
├── 03-数据集对比深度分析.md
├── 04-模型架构与任务详解.md
└── figures/                               ← 17 张论文原图（裁剪版）
    ├── fig1-waterfall-shiftleft.png        Figure 1
    ├── fig2-design-representations.png     Figure 2
    ├── fig3-timing-power.png              Figure 3
    ├── fig4-workflow.png                  Figure 4
    ├── fig5-data-augmentation.png         Figure 5
    ├── fig6-distribution.png              Figure 6
    ├── fig7-iterative-optimization.png     Figure 7
    ├── fig8-prediction-framework.png      Figure 8
    ├── fig9-distribution-boxplots.png      Figure 9
    ├── table1-dataset-comparison.png       Table 1
    ├── table3-ast-mutation-operators.png   Table 3
    ├── table4-performance.png             Table 4
    ├── table9-detailed-operators.png       Table 9
    ├── table10-distribution-statistics.png Table 10
    ├── table21-key-specs.png              Table 21
    ├── algo2-ast-mutation.png             Algorithm 2
    └── algo3-assignment-consistency.png   Algorithm 3
```
