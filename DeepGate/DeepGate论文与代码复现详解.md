# DeepGate 论文、代码与复现条件详解

> 论文：**DeepGate: Learning Neural Representations of Logic Gates**  
> 会议：ACM/IEEE Design Automation Conference（DAC），2022  
> arXiv：2111.14616  
> 原论文：[2111.14616_DeepGate.pdf](./2111.14616_DeepGate.pdf)  
> 官方论文页：<https://arxiv.org/abs/2111.14616>  
> 官方 PDF：<https://arxiv.org/pdf/2111.14616>  
> 官方代码：<https://github.com/cure-lab/DeepGate>  
> 本地代码 commit：`19060b788c84e7cd17af8b8b3fbb771e61422b17`  
> 本次核验日期：2026-08-02  
> 静态核验记录：[runs/static_audit_20260802.json](./runs/static_audit_20260802.json)

---

## P1. DeepGate Task 定义

```text
┌─────────────────────────────────────────────────────────────────┐
│  Task: DeepGate per-gate probability prediction                  │
├─────────────────────────────────────────────────────────────────┤
│  Input      AIG graph (PI / AND / NOT) + gate-type one-hot       │
│  Output     Per-gate signal probability  +  per-gate embedding   │
│  Supervision  Signal probability from random logic simulation    │
│  Why hard   Controlling values differ; reconvergence makes      │
│             fanin signals correlated; directionality matters.    │
└─────────────────────────────────────────────────────────────────┘
```

## 0. 先给结论

DeepGate 的研究问题很重要：

> 能不能先为逻辑门学习一个通用向量表示，再把这个表示迁移到不同 EDA 任务，而不是每个任务都重新设计特征和模型？

论文给出的答案是：

1. 把不同来源的组合逻辑电路统一转换为 AIG；
2. 用随机逻辑仿真得到每个节点的 signal probability；
3. 沿电路拓扑执行正向、反向循环消息传播；
4. 用 attention 模拟逻辑门输入的重要性差异；
5. 对 reconvergence 添加带距离编码的 skip connection；
6. 用概率回归训练 gate embedding。

⚠️ 论文结果中，完整 DeepGate 的平均概率预测误差为 `0.0204`，优于最好的 DAG-RecGNN 基线 `0.0302`。

但是，✅ **当前本地仓库不能被表述为“论文结果已经复现”**。

原因不是模型主体完全缺失，而是论文复现闭环缺少几个关键环节：

- 没有论文使用的 10,824 个子电路数据；
- 没有任何 DeepGate v1 checkpoint；
- 没有 `.npz` 处理数据或 `.bench` 原始电路；
- 文档提到的随机电路预处理脚本没有发布在本地仓库；
- `setup.sh` 期待的 ABC/AIGER 目录没有随仓库一起提供；
- 当前 `test.py` 的论文概率评测主体被整段注释；
- 当前激活的测试路径实际进入 SAT 求解，而不是复现论文表格；
- TPI 入口有无条件 `continue`，控制点插入主体不可达；
- 论文与代码在 hidden state 初始化、位置编码、regressor 共享方式上存在实质差异。

因此，本项目目前最准确的状态是：

| 项目层级 | 当前状态 |
|---|---|
| 原论文 | 已归档并逐节核对 |
| 论文方法 | 已完整梳理 |
| 核心 GNN 源码 | 已开源，可静态对应 |
| Python 语法 | 静态编译检查通过 |
| 论文训练数据 | 本地缺失 |
| 官方 checkpoint | 本地缺失 |
| 论文数值复现 | 未完成，不能声称完成 |
| DeepGate v1 推理 | 未重复执行；本地也没有可匹配权重 |
| DeepGate2 烟雾测试 | 以前已成功，但只能作为后续版本代码证据 |
| 综合复现等级 | ⚠️ **C-：方法可读，数值闭环不完整** |

本次没有重新训练或运行 DeepGate v1。

这是有意为之：当前缺的是论文数据和匹配 checkpoint，不是再做一次随机初始化“推理”。随机输出无法证明论文结果，也不能替代已有运行记录。

---

## 1. 证据边界：哪些是论文结论，哪些是代码事实

为了避免把不同证据混在一起，本文使用四种标记。

| 标记 | 含义 | 可支持什么结论 |
|---|---|---|
| `[论文]` | 来自原论文正文、公式或表格 | 作者方法和作者报告结果 |
| `[代码]` | 来自当前 commit 的源码 | 当前公开实现真实行为 |
| `[本地资产]` | 来自本地文件统计 | 数据、权重、日志是否真的存在 |
| `[已有运行]` | 来自以前保存的运行记录 | 对应代码路径曾经成功执行 |

这四者不能互相代替。

例如：

- `[论文] 0.0204` 不是本地实测值；
- `[代码] 模型能构建` 不等于 `[本地资产] 有 checkpoint`；
- `[已有运行] DeepGate2 smoke success` 不等于 DeepGate v1 论文复现；
- Python 文件语法正确不等于数据准备、训练和评测闭环正确。

### 1.1 本次实际做了什么

- 核对原论文标题、作者、页数、方法、公式和实验表；
- 阅读训练、数据、模型、聚合器、评测和 TPI 代码；
- 核对所有实验 shell 参数；
- 统计本地数据、checkpoint 和电路文件；
- 检查 Python 源码能否通过语法编译；
- 从论文 HTML 版本提取三张原始结构图；
- 对照 DeepGate2 已保存的 smoke record；
- 记录论文—代码差异和复现阻塞点。

### 1.2 本次没有做什么

- 没有下载缺失训练数据；
- 没有重新生成 10,824 个子电路；
- 没有训练 60 epochs；
- 没有伪造 checkpoint；
- 没有把随机初始化前向当成论文推理；
- 没有用 DeepGate2 的结果冒充 DeepGate v1；
- 没有复算论文 `0.0204`。

---

## 2. 论文身份与本地归档核对

### 2.1 论文基本信息

| 字段 | 内容 |
|---|---|
| 标题 | DeepGate: Learning Neural Representations of Logic Gates |
| 作者 | Min Li, Sadaf Khan, Zhengyuan Shi, Naixing Wang, Yu Huang, Qiang Xu |
| 会议 | DAC 2022 |
| arXiv ID | 2111.14616 |
| 本地 PDF | `2111.14616_DeepGate.pdf` |
| 页数 | 7 |
| 文件大小 | 499,402 bytes |
| SHA-256 | `3919b4998f7b8f52b77aeadf82be54c7fbd4cf454c1f40c16950b590926f2992` |

本地 PDF 与项目标题匹配，没有出现“文件名是 DeepGate、正文却是另一篇论文”的身份问题。

### 2.2 代码快照

| 字段 | 内容 |
|---|---|
| remote | `https://github.com/cure-lab/DeepGate.git` |
| commit | `19060b788c84e7cd17af8b8b3fbb771e61422b17` |
| 最近 commit 时间 | 2023-07-12 |
| tracked files | 149 |
| 审计 Python 文件 | 47 |
| Python 总行数 | 6,625 |
| 实验 shell 文件 | 18 |
| 根目录 LICENSE | 未找到 |

注意：

> GitHub 公开可读不等于具有明确的软件再利用授权。

仓库内部的 `PyMiniSolvers` 有它自己的 LICENSE，但不能据此推导整个 DeepGate 仓库采用同一许可证。公司或商业项目使用前应单独确认。

---

## 3. DeepGate 在 EDA 流程中的位置

DeepGate 不是 RTL 生成模型，也不是 placement/routing 模型。

它位于逻辑综合后的门级图阶段：

```text
RTL / gate-level netlist / benchmark circuit
                 ↓
      logic synthesis / mapping
                 ↓
        AIG：PI + AND + NOT
                 ↓
        random logic simulation
                 ↓
      per-gate signal probability
                 ↓
      DeepGate representation learning
                 ↓
       per-gate embedding + probability
                 ↓
logic optimization / testability / SAT / equivalence / other downstream EDA
```

它的目标不是直接给出最终 PPA，而是学习一种可复用的 gate-level representation。

### 3.1 为什么不直接把 AIG 喂给普通 GCN

普通 GCN 主要把图看成一般邻接关系。

组合逻辑电路却有更强的结构约束：

- 信号从 PI 按拓扑顺序传播到输出；
- AND/NOT 有确定的逻辑语义；
- fanin 的控制值与非控制值作用不同；
- fanout/reconvergence 会造成信号相关性；
- 从输出向输入的反向信息对 implication/backtracking 有帮助。

论文的主要观点是：

> 电路不是普通社交图，模型应显式利用逻辑传播顺序和 reconvergence 结构。

---

## 4. 论文整体流程

![论文 Figure 2：DeepGate 总体流程](./figures/paper_fig2_overview.png)

论文 Figure 2 可拆成两个阶段。

### 4.1 阶段 A：Circuit Data Preparation

```text
不同来源电路
   ↓
统一映射为 AIG
   ↓
ABC logic optimization
   ↓
过大电路切成 30～3k gate 的子电路
   ↓
最多 100k 随机输入 pattern 的逻辑仿真
   ↓
每个 gate 的 signal probability y_v
```

### 4.2 阶段 B：Probability Prediction with DeepGate

```text
AIG graph + gate type one-hot + probability labels
                       ↓
             初始化 gate hidden state
                       ↓
       forward topological propagation
                       ↓
       reverse topological propagation
                       ↓
                 重复 T 次
                       ↓
               per-gate embedding
                       ↓
                    MLP
                       ↓
          predicted signal probability ŷ_v
```

### 4.3 学到的 embedding 是什么

理想情况下，每个 gate 的最终 hidden state 同时编码：

- gate 类型；
- fanin/fanout 结构；
- 逻辑层级；
- 从 PI 到本节点的逻辑传播特征；
- 从输出方向反传的上下文；
- reconvergence 相关性；
- 与 signal probability 有关的功能信息。

但需要特别注意：

> signal probability 只是布尔功能的低维投影，不是完整真值表。

例如 XOR 与其他平衡函数都可能具有 `P(output=1)=0.5`，但函数完全不同。

这正是 DeepGate2 后续工作的出发点。

---

## 5. 为什么统一成 AIG

![论文 Figure 1：电路映射为 DAG/AIG 表示](./figures/paper_fig1_dag.png)

论文把不同逻辑网络统一成 AIG，节点只保留三类：

| 节点类型 | 含义 | one-hot 维度示意 |
|---|---|---|
| PI | primary input | `[1,0,0]` |
| AND | 2-input AND | `[0,1,0]` |
| NOT | inverter | `[0,0,1]` |

### 5.1 AIG 带来的好处

1. 减少 gate type 数量；
2. 避免不同 standard-cell library 的门类型漂移；
3. 使不同 benchmark 进入统一图空间；
4. 让训练数据更容易合并；
5. 让模型更容易学习逻辑规律；
6. 降低少数门类型样本不足的问题。

### 5.2 论文实验对 AIG 转换的支持

论文 Table IV：

| 数据集 | 不转换 | 转为 AIG | 使用 merged AIG 预训练模型 |
|---|---:|---:|---:|
| EPFL | 0.0442 | 0.0292 | 0.0142 |
| IWLS | 0.0447 | 0.0342 | 0.0209 |

这里的 `Pre-trained` 不是指仓库中有一个可以直接下载的通用权重。

它指论文实验中：

> 在四类 benchmark 合并 AIG 数据上训练的模型，直接应用到 EPFL/IWLS。

当前本地仓库没有这个 checkpoint。

---

## 6. 监督信号：signal probability

对 gate `v`，论文用随机输入分布下输出为 1 的概率作为标签：

```text
y_v = P(v = 1)
```

实际通过逻辑仿真估计：

```text
随机生成 PI pattern
        ↓
按 level 计算所有 gate
        ↓
统计每个 gate 输出 1 的次数
        ↓
次数 / pattern 总数
```

### 6.1 为什么选择这个监督

- 不需要人工标注；
- 比 SAT/形式证明标签更容易大规模产生；
- 与逻辑功能有关；
- 对 reconvergence 敏感；
- 对 power、testability 等任务有直接意义。

### 6.2 它不能表达什么

signal probability 不能唯一确定布尔函数。

```text
不同 truth table
        ↓
可能拥有相同的 1 的比例
        ↓
得到相同 signal probability
```

因此，DeepGate v1 所谓 functionality-aware 是“通过概率获得部分功能监督”，不是完整语义等价表示。

---

## 7. DeepGate GNN 的数学过程

设电路图为：

```text
G = (V, E)
```

对每个节点 `v`：

- `x_v`：固定 gate type one-hot；
- `h_v^t`：第 `t` 轮 hidden state；
- `P(v)`：fanin/predecessor 集合；
- `m_v^t`：聚合后的消息。

### 7.1 Attention 聚合

论文 Equation (5)：

```text
m_v^t = Σ_{u∈P(v)} α_uv^t h_u^t
```

其中：

```text
α_uv^t = softmax_{u∈P(v)}(
    w1^T h_v^(t-1) + w2^T h_u^t
)
```

解释：

- target 旧状态是 query；
- predecessor 当前状态是 key/value；
- softmax 在当前 gate 的所有 fanin 上归一化；
- 模型可以给控制输入更高权重。

例如 AND gate：

- 输入 0 是 controlling value；
- 输入 1 是 non-controlling value；
- 某些输入对输出概率的影响更强；
- 简单平均会丢失这种差异；
- attention 提供学习不同权重的能力。

### 7.2 GRU 更新

论文 Equation (6)：

```text
h_v^t = GRU([m_v^t, x_v], h_v^(t-1))
```

这里有一个重要设计：

> gate type `x_v` 在每一轮都重新拼接进 GRU 输入。

它避免循环传播很多轮后，节点类型信息被邻居消息冲淡。

### 7.3 正向传播

```text
level 0: PI
level 1: fanin 都已更新的 gate
level 2: 更深 gate
...
primary output
```

同一个 level 的节点可以 batch 计算。

### 7.4 反向传播

每一轮正向传播后，再按反拓扑顺序传播：

```text
output side
    ↓
internal gates
    ↓
PI side
```

反向传播不是梯度反向传播。

它是模型 forward 内部的一次图消息传播，用于加入 fanout、output context 和 implication/backtracking 信息。

### 7.5 重复 T 轮

论文采用：

```text
T = 10
```

每一轮包含：

```text
forward topological pass
            +
reverse topological pass
```

论文还测试 `T=1...50`，观察到 prediction error 随 T 增加而下降，并在约 `T=10` 附近收敛。

### 7.6 Regressor 与 L1 loss

经过 `T` 轮后：

```text
ŷ_v = MLP(h_v^T)
```

训练目标：

```text
L = (1/N) Σ_v |y_v - ŷ_v|
```

论文的评测指标也是所有节点绝对误差的平均值。

---

## 8. Reconvergence 与 skip connection

![论文 Figure 3：reconvergence 的 skip connection](./figures/paper_fig3_reconvergence.png)

### 8.1 什么是 reconvergence

一个信号从 fanout node 分成多条路径，之后又汇合：

```text
        fanout
       /      \
   path A    path B
       \      /
     reconvergence
```

两条路径不是统计独立的，因为它们来自同一上游信号。

如果直接假定输入独立，概率计算会产生误差。

### 8.2 论文的处理

数据准备阶段记录：

- reconvergence node；
- 对应 source fanout node；
- 两者的 logic-level distance `D`。

然后添加直接边：

```text
source fanout node ─────────→ reconvergence node
                   skip edge
```

### 8.3 论文的位置编码

论文 Equation (7) 将距离 `D` 编码到 `R^(2L)`：

```text
γ(D) = (
  sin(2^0 πD), cos(2^0 πD),
  ...,
  sin(2^(L-1) πD), cos(2^(L-1) πD)
)
```

论文实验设置：

```text
L = 8
2L = 16 dimensions
```

编码向量作为 skip edge attribute，帮助 attention 区分普通边与 reconvergence 边，并感知距离。

---

## 9. 论文数据集

论文 Table I：

| Benchmark | 子电路数 | 节点数范围 | level 范围 |
|---|---:|---:|---:|
| EPFL | 828 | 52–341 | 4–17 |
| ITC'99 | 7,560 | 36–1,947 | 3–23 |
| IWLS'05 | 1,281 | 41–2,268 | 5–24 |
| OpenCores | 1,155 | 51–3,214 | 4–18 |
| Total | 10,824 | 36–3,214 | 3–24 |

论文说明：

- 输入来自四套 benchmark；
- 统一转换为 AIG；
- 从大设计中提取子电路；
- 每个节点用最多 100k 随机 pattern 仿真；
- 最终按 `90/10` 划分训练和测试。

### 9.1 精确复现需要额外固定的内容

论文没有在仓库中提供可直接验证的：

- 10,824 个子电路清单；
- 每个子电路来源设计；
- 具体 ABC commit；
- ABC optimization 命令完整快照；
- 子电路切分 seed；
- 训练/测试 split manifest；
- 每个节点实际使用的 pattern 数；
- 仿真标签文件 hash。

没有这些内容，即使重新生成相似数据，也只能称为“方法复现”，不能保证是论文的精确数值复现。

---

## 10. 论文训练配置

| 参数 | 论文设置 | 当前代码位置 |
|---|---:|---|
| hidden dimension | 64 | `src/config.py --dim_hidden` |
| message-passing rounds | 10 | `--num_rounds 10` |
| skip encoding L | 8 | 代码用 `dim_edge_feature=16` 近似对应维数 |
| epochs | 60 | `--num_epochs 60` |
| optimizer | Adam | `src/main.py` |
| learning rate | `1e-4` | `--lr` |
| loss | L1 | `--reg_loss l1` |
| train/test | 90/10 | `--trainval_split 0.9` |
| node type | PI/AND/NOT | shell 中 `--gate_types INPUT,AND,NOT` |
| node input dimension | 3 | `--dim_node_feature 3` |
| precomputed COP feature | 不使用 | `--no_node_cop` |
| aggregator | attention | `--aggr_function aggnconv` |
| update | GRU | 默认 `--update_function gru` |
| forward + reverse | 使用 | 默认 reverse=true |
| reconvergence SC | 完整模型使用 | `--reconv_skip_connection` |
| edge distance attr | 使用 | `--use_logic_diff` |

主实验脚本：

```bash
cd src
python3 main.py prob \
  --exp_id recgnn_deepgate \
  --data_dir ../data/benchmarks/merged/ \
  --num_rounds 10 \
  --dataset benchmarks \
  --gpus 0 \
  --gate_types INPUT,AND,NOT \
  --dim_node_feature 3 \
  --no_node_cop \
  --aggr_function aggnconv \
  --wx_update \
  --reconv_skip_connection \
  --use_logic_diff
```

这个 shell 与论文主配置的对应度较高，但只有在 `../data/benchmarks/merged/` 已经存在正确数据时才有意义。

当前目录中不存在这个数据。

---

## 11. 论文实验结果

### 11.1 Table II：模型与聚合器对比

| 模型 | Aggregator | Avg. Prediction Error |
|---|---|---:|
| GCN | Conv. Sum | 0.1386 |
| GCN | Attention | 0.1840 |
| GCN | DeepSet | 0.2541 |
| GCN | GatedSum | 0.1995 |
| DAG-ConvGNN | Conv. Sum | 0.2215 |
| DAG-ConvGNN | Attention | 0.2398 |
| DAG-ConvGNN | DeepSet | 0.2431 |
| DAG-ConvGNN | GatedSum | 0.2333 |
| DAG-RecGNN, T=10 | Conv. Sum | 0.0328 |
| DAG-RecGNN, T=10 | DeepSet | 0.0302 |
| DAG-RecGNN, T=10 | GatedSum | 0.0329 |
| DeepGate, T=10 | Attention, no SC | 0.0234 |
| DeepGate, T=10 | Attention + SC | ⚠️ **0.0204** |

关键观察：

1. 普通 GCN 和单向 DAG-ConvGNN 明显较差；
2. 循环正反向传播是最大一级提升；
3. attention 把 `0.0302` 降到 `0.0234`；
4. reconvergence skip connection 再降到 `0.0204`；
5. 相对 `0.0234`，SC 约降低 12.82% 误差；
6. 相对最好基线 `0.0302`，完整模型约降低 32.45% 误差。

### 11.2 Table III：超大电路泛化

| Design | Nodes | Levels | DeepSet | DeepGate | Reduction |
|---|---:|---:|---:|---:|---:|
| Arbiter | 23.7K | 173 | 0.0277 | 0.0073 | 73.56% |
| Squarer | 36.0K | 373 | 0.0495 | 0.0346 | 30.16% |
| Multiplier | 47.3K | 521 | 0.0220 | 0.0159 | 27.94% |
| 80386 Processor | 13.2K | 122 | 0.0534 | 0.0387 | 27.56% |
| Viper Processor | 40.5K | 133 | 0.0520 | 0.0389 | 25.18% |

这些设计的节点数比训练子电路大很多。

论文用它说明：

- 模型可以在小子电路训练；
- 再迁移到数万 gate 的大图；
- reconvergence 多的 Arbiter 获益最明显。

但当前仓库没有五个大电路处理结果、checkpoint 或对应原始输出，因此本地不能复算该表。

### 11.3 Table IV：AIG 统一表示

前文已经列出 Table IV。

它支持两个结论：

1. 同一数据转成 AIG 后更容易学习；
2. 合并多 benchmark 的预训练模型比单数据集从零训练更好。

---

## 12. 当前代码目录与职责

```text
DeepGate/
├── 2111.14616_DeepGate.pdf
├── README.md
├── DATASETS.md
├── requirements.txt
├── setup.sh
├── data/
│   └── benchmarks/
│       └── prepare_benchmarks_circuits.py
├── experiments/prob/
│   ├── recgnn_deepgate.sh
│   ├── recgnn_deepgate_cr.sh
│   ├── recgnn_*.sh
│   ├── dagconvgnn_*.sh
│   ├── convgnn_*.sh
│   ├── test.sh
│   └── test_large.sh
├── src/
│   ├── config.py
│   ├── main.py
│   ├── test.py
│   ├── demo.py
│   ├── datasets/
│   ├── models/
│   ├── trains/
│   ├── detectors/
│   └── utils/
├── tpi/
├── figures/
├── runs/
└── 模型梳理.md
```

### 12.1 关键文件速查

| 文件 | 真实职责 |
|---|---|
| `src/config.py` | 参数解析、gate mapping、目录和配置一致性检查 |
| `src/main.py` | 数据划分、DataLoader、训练、验证、checkpoint |
| `src/datasets/circuit_dataset.py` | 读取 graphs/labels NPZ，转换 PyG 图并缓存 |
| `src/datasets/load_data.py` | 构造 node feature、edge、level、skip connection |
| `src/models/recgnn.py` | DeepGate 主体：正向/反向循环传播 |
| `src/models/gat_conv.py` | attention aggregator |
| `src/utils/data_utils.py` | one-hot、reconvergence edge、距离编码 |
| `src/utils/dag_utils.py` | topological order 与按 level 取子图 |
| `src/trains/base_trainer.py` | L1 loss、train/val loop |
| `data/benchmarks/prepare_benchmarks_circuits.py` | `.bench` 解析、COP、reconvergence、仿真、NPZ |
| `src/test.py` | 当前激活的是 SAT 求解；论文概率评测被注释 |
| `src/detectors/base_detector.py` | 加载 checkpoint、模型前向、结果 clamp |
| `tpi/tpi_top.py` | TPI 入口，但主要插入逻辑当前不可达 |

---

## 13. 代码数据格式

### 13.1 原始 `.bench`

典型组合电路：

```text
INPUT(a)
INPUT(b)
n1 = AND(a, b)
n2 = NOT(n1)
OUTPUT(n2)
```

### 13.2 graphs NPZ

代码期待：

```text
benchmarks_circuits_graphs.npz
└── circuits[name]
    ├── x
    └── edge_index
```

`x` 的原始列在预处理代码中实际包括：

| 列 | 含义 |
|---:|---|
| 0 | node index/name |
| 1 | gate type index |
| 2 | logic level |
| 3 | C1 controllability/probability-style feature |
| 4 | C0 |
| 5 | observability |
| 6 | fanout |
| 7 | reconvergence flag |
| 8 | reconvergence source node index |
| 9+ | 可选 implication/mask 数据 |

### 13.3 labels NPZ

```text
benchmarks_circuits_labels.npz
└── labels[name]
    └── y: [num_nodes, 1]
```

`y` 是逻辑仿真估计的 signal probability。

### 13.4 PyG graph

`circuit_parse_pyg()` 产生：

| 字段 | 含义 |
|---|---|
| `x` | 实际送入模型的 gate one-hot/可选特征 |
| `edge_index` | `[2,E]` 有向边 |
| `y` | 训练目标 |
| `forward_level` | 每节点正向拓扑层 |
| `forward_index` | 正向节点索引 |
| `backward_level` | 反向拓扑层 |
| `backward_index` | 反向节点索引 |
| `edge_attr` | 可选 reconvergence 距离编码 |
| `rec` | reconvergence flag |
| `c1` | 原始 C1 |
| `gt` | 仿真概率 |
| `gate` | gate type index |

---

## 14. 代码实际执行流程

### 14.1 参数解析

入口：

```text
src/main.py
  → get_parse_args()
```

`config.py` 做这些事情：

1. 解析 `task`、dataset、arch；
2. 建立 gate type 到整数的映射；
3. 推导 `num_gate_types`；
4. 检查 `dim_node_feature`；
5. 决定是否反向传播；
6. 决定是否使用 edge attributes；
7. 建立 `exp/<task>/<exp_id>`；
8. 处理 `--resume` 和 `--load_model`。

### 14.2 数据加载

```text
CircuitDataset(root, args)
        ↓
检查 processed data.pt
        ↓ 不存在
读取 graphs NPZ + labels NPZ
        ↓
逐电路调用 circuit_parse_pyg
        ↓
collate 所有 PyG Data
        ↓
保存 processed data.pt
```

### 14.3 划分训练集与验证集

```text
perm = torch.randperm(len(dataset))
training_cutoff = int(0.9 * len(dataset))
train = dataset[:cutoff]
val   = dataset[cutoff:]
```

问题是仓库没有发布论文 split manifest。

即使 seed 固定为 `208`，只要：

- circuits 字典顺序不同；
- 数据生成顺序不同；
- PyTorch 版本不同；
- 子电路集合不同；

就无法保证得到论文同一划分。

### 14.4 模型构建

```text
create_model(args)
    ├── recgnn      → RecGNN
    ├── convgnn     → ConvGNN
    └── dagconvgnn  → DAGConvGNN
```

论文完整模型对应 `RecGNN`。

### 14.5 训练

```text
for epoch in 1...60:
    model.train()
    for batch:
        outputs = model(batch)
        loss = sum(L1(output, y) for output in outputs)
        zero_grad
        backward
        optional grad clip
        optimizer.step
    model.eval()
    validation
    save best / last checkpoint
```

### 14.6 模型输出

当前 `RecGNN.forward()` 返回：

```text
preds: list[per-node probability tensor]
```

模型内部确实产生：

```text
node_embedding = node_state.squeeze(0)
```

但公开函数没有把 embedding 返回。

因此，若要把 v1 作为通用 representation extractor，当前代码还需要一个明确的 embedding export 接口。

这不是重新训练问题，而是公开 API 完整性问题。

---

## 15. 论文方法与代码逐项对应

| 论文组件 | 代码位置 | 对应程度 |
|---|---|---|
| AIG gate type one-hot | `data_utils.construct_node_feature` | 高 |
| topological batching | `dag_utils.return_order_info` + `recgnn.py` | 高 |
| attention aggregation | `models/gat_conv.py` | 高，但 edge attr 行为有差异 |
| GRU update | `models/recgnn.py` | 高 |
| fixed gate type each round | `--wx_update` + concat `[l_msg,l_x]` | 高 |
| forward propagation | `RecGNN._gru_forward` | 高 |
| reverse propagation | 同上 | 高 |
| T rounds | `--num_rounds` | 高 |
| signal probability L1 | `BaseTrainer` | 高 |
| reconvergence skip edge | `data_utils.add_skip_connection` | 高 |
| distance positional encoding | `data_utils.add_edge_attr` | **公式不同** |
| random hidden initialization | `RecGNN.forward` | **行为不同** |
| gate-type-specific regressor sharing | `RecGNN.predictor` | **实现含义不同** |
| 10,824 subcircuits | 本地无数据 | 缺失 |
| up to 100k patterns | preprocessor 默认 15k | 不一致 |
| Tables II–IV evaluator | `test.py` | 主体被注释 |
| reusable embedding output | `node_embedding` 局部变量 | 未公开 |

---

## ⚠️ 16. 论文—代码差异：必须重点说明

### 16.1 hidden state 并不是论文描述的随机逐节点初始化

论文描述：

```text
h_v^0 initialized randomly
```

当前代码：

```python
one = torch.ones(1)
h_init = self.emd_int(one).view(1, 1, -1)
h_init = h_init.repeat(1, num_nodes, 1)
```

也就是：

- 先对常数 `1` 做一个可学习线性映射；
- 再把同一个向量复制给所有节点；
- 每个节点初始 hidden state 完全相同；
- 真正随机张量初始化代码被注释掉了。

模型仍可以依靠每轮拼接的 gate type 和邻接结构分化节点，但这与论文文字不是同一初始化方式。

### 16.2 位置编码公式不同

论文：

```text
sin(2^k πD), cos(2^k πD)
```

代码：

```python
sin(D / 10000 ** (...))
cos(D / 10000 ** (...))
```

后者更接近 Transformer positional encoding。

因此：

> 代码维度 `16` 与论文 `2L=16` 一致，不代表编码数值一致。

### 16.3 edge attribute 不只进入 attention coefficient

论文说距离编码作为 attention coefficient 的第三个输入。

代码中：

```python
edge_embedding = self.edge_encoder(edge_attr)
h_attn = h_attn + edge_embedding
a_j = attn_lin(cat([query, h_attn]))
return h_attn * a_j
```

因此 edge embedding 同时影响：

- attention score；
- 实际被加权聚合的 value。

这比论文文字描述的作用范围更大。

### 16.4 regressor sharing 解释不一致

论文说：

> MLP weights are shared for nodes with the same gate types.

这通常可以理解为同类节点共享一套 regressor，不同 gate type 可有不同 regressor。

当前代码只有：

```text
self.predictor = one MLP
```

所有 PI、AND、NOT 共用它。

虽然存在 `--mul_mlp` 参数，但 `config.py` 对它直接：

```text
raise NotImplementedError
```

因此不能把公开代码描述成“已经实现 per-gate-type multiple MLP”。

### 16.5 仿真 pattern 数不同

论文：

```text
up to 100k random input patterns
```

公开 benchmark 预处理脚本默认：

```text
--num-patterns 15000
```

而 simulator 实际使用：

```text
min(num_patterns, 10 * 2^(#PI))
```

所以实际 pattern 数还可能低于 15k。

除非显式传 `--num-patterns 100000`，否则不会接近论文上限。

### 16.6 公开预处理不等于论文完整数据准备

论文流程：

```text
heterogeneous circuits
→ AIG mapping
→ ABC optimization
→ 30～3k subcircuit extraction
→ simulation
```

公开 `prepare_benchmarks_circuits.py`：

```text
already prepared .bench
→ parse gate types
→ COP/reconvergence
→ simulation
→ NPZ
```

缺少自动执行的：

- RTL/gate netlist 到 AIG；
- ABC optimization；
- 与论文一致的子电路提取；
- 四类 benchmark 合并；
- 固定 10,824 条目；
- 固定 split。

`--sub-circuit-size` 参数虽然存在，但在该脚本的主路径中没有使用。

---

## 17. 当前仓库中的复现阻塞点

### 17.1 没有数据 payload

本地统计：

```text
.npz files: 0
.bench files: 0
```

只有预处理代码，没有输入或处理后数据。

### 17.2 没有 checkpoint

本地统计：

```text
.pt/.pth/.ckpt model files: 0
```

因此：

- `test.sh` 指向的 `model_best.pth` 不存在；
- `test_large.sh` 指向的 `model_best.pth` 不存在；
- 不能进行论文意义上的预训练推理；
- 不能提取论文训练得到的 gate embedding。

### 17.3 DATASETS.md 指向未发布脚本

文档要求：

```text
cd data/random_circuits
python prepare_random_circuits.py
```

但本地仓库没有：

```text
data/random_circuits/
prepare_random_circuits.py
```

所以随机电路数据路线不是开箱即用。

### 17.4 setup.sh 引用缺失 third-party 目录

`setup.sh` 期待：

```text
src/external/abc
src/external/aiger/aiger
src/external/aiger/cnf2aig
```

本地 `src/external/` 只有：

```text
PyMiniSolvers/
```

因此 CNF→AIG→ABC 的辅助路线不完整。

### 17.5 requirements 与 README 版本漂移

README：

```text
Python 3.7.4
PyTorch 1.8.1
PyG 2.0.1
```

requirements：

```text
torch 1.10.0
torch-geometric 2.0.4
torchvision 0.10.0
```

这至少说明作者运行环境没有被唯一锁定。

### 17.6 测试入口缺少依赖声明

`src/test.py` 顶部导入：

```text
cmd2
```

`src/detectors/base_detector.py` 顶部导入：

```text
cv2
```

二者都未在 `requirements.txt` 固定。

而且这两个导入在论文概率评测核心逻辑中并非必要，却会让程序在进入 main 前就可能失败。

### 17.7 demo 与辅助测试不完整

- `src/demo.py` 是 0 行空文件；
- `src/deepsat_test.py` 导入不存在的 `models.deepsat`；
- 同文件还导入不存在的 `models.deepsat_copy`。

这不直接破坏 `main.py prob`，但说明仓库包含未完整发布的研究分支。

---

## 18. 数据缓存键问题

`CircuitDataset.processed_dir` 的格式串有 10 个 `{}`：

```text
{}_{}_{}_{}_{}_{}_{}_{}_{}_{}
```

但 `.format()` 传入 12 个配置字段。

Python 对多余参数不会报错，而是忽略最后两个。

被忽略的是：

```text
logic_implication
mask
```

后果：

```text
同一 root
+ 前 10 个参数相同
+ logic_implication/mask 不同
        ↓
落到同一个 processed_dir
        ↓
可能错误复用旧 data.pt
```

这不是语法错误，而是缓存隔离错误。

它会让实验表面上能跑，实际加载了与当前配置不兼容的数据。

---

## 19. 评测入口为什么不能复现论文表格

README 说运行 `experiments/prob/test.sh`。

该脚本最终调用：

```text
src/test.py prob ...
```

### 19.1 当前激活逻辑

当前 `test.py`：

1. 加载 dataset；
2. 构造 detector；
3. 打印“Solving the SAT problem”；
4. 调用 `solve_sat_iteratively()`；
5. 统计 SAT 成功率。

这不是论文 Equation (8) 的 probability prediction error。

### 19.2 论文评测逻辑被注释

文件后半段原本包含：

- 对每个 graph 调用 detector；
- 保存 prediction 和 GT；
- 计算平均绝对误差；
- 计算 reconvergent/non-reconvergent 误差；
- 计算 top 5% error。

但整段位于三引号字符串中，不会执行。

### 19.3 `test_split` 当前没有生效

代码读取：

```text
split = args.test_split
```

但实际 train/test slicing 也被注释。

所以即使移除 SAT 分支，也必须先恢复并核对 split 逻辑，才能谈论文 test set。

---

## 20. TPI 下游流程核对

论文正文把下游应用主要放在未来工作；仓库额外提供 `tpi/`。

### 20.1 设计目标

```text
DeepGate predicted probability
          ↓
寻找 probability 接近 0/1 的节点
          ↓
插入 control point
          ↓
Atalanta ATPG
          ↓
比较 test coverage / pattern count
```

### 20.2 仓库需要的输入

```text
tpi/sub_circuits/<circuit>.txt
tpi/predictions/<circuit>.txt
```

但主仓库没有脚本从 `RecGNN` 自动导出第二类 prediction 文件。

### 20.3 当前不可达代码

`tpi_top.py` 在输出原始 bench 后立即：

```python
continue
```

其后的内容包括：

- COP strategy；
- DeepGate strategy；
- control-point selection；
- inserted bench output；

全部不可执行。

README 自己也写了：

```text
cannot ensure validity yet
```

因此 TPI 只能列为实验性、不完整代码，不能写成已经复现的下游结果。

---

## 21. checkpoint 与恢复训练问题

### 21.1 checkpoint 格式

`save_model()` 保存：

```text
{
  epoch,
  state_dict,
  optimizer? 
}
```

### 21.2 best 与 last

训练时：

- val loss 改善：保存 `model_best.pth`；
- val loss 不改善：保存 `model_last.pth`；
- 每 `save_intervals` 还会保存阶段模型。

这意味着如果早期连续改善，`model_last.pth` 可能暂时不存在。

而 `--resume` 默认寻找：

```text
model_last.pth
```

所以恢复流程并不总是稳健。

### 21.3 `--load_model` 路径

参数会被拼到当前 `save_dir`：

```text
exp/<task>/<exp_id>/<load_model>
```

它适合 shell 中的：

```text
--load_model model_best.pth
```

但不适合直接传任意绝对 checkpoint 路径，除非修改路径处理逻辑。

### 21.4 checkpoint 还缺少数据身份

当前 checkpoint 没有显式保存：

- gate mapping；
- preprocessing flags；
- dataset hash；
- ABC version；
- train/test split；
- simulation pattern count；
- source commit；
- full config dict。

加载时只根据 tensor key/shape 尝试兼容。

这不足以证明某个权重与某个数据 revision 精确匹配。

---

## 22. 当前本地运行证据

### 22.1 DeepGate v1

当前没有发现：

- `runs/` 下的旧 v1 推理 record；
- 论文 checkpoint；
- 训练日志；
- prediction 数组；
- Table II/III/IV 重算结果。

所以本文没有写“DeepGate v1 已跑通”。

### 22.2 为什么没有补一次随机前向

随机前向最多能证明：

- 张量 shape 合法；
- 当前环境可 import；
- 某个 toy graph 能过 forward。

它不能证明：

- 学到了功能 embedding；
- 论文误差得到复现；
- checkpoint 可用；
- 数据处理一致；
- 下游任务有效。

在缺少数据和权重时，重复做这一步容易制造错误印象，因此没有执行。

### 22.3 DeepGate2 已有 smoke evidence

已存在：

[DeepGate2 smoke record](../DeepGate2/runs/smoke/record.json)

记录明确写的是：

```text
Random initialization, one real-label CPU update;
not pretrained inference.
```

关键结果：

| 项目 | 值 |
|---|---:|
| status | success |
| toy AIG nodes | 13 |
| edges | 16 |
| parameters | 171,334 |
| structural embedding | `[13,64]` |
| functional embedding | `[13,64]` |
| probability | `[13,1]` |
| gradient norm | 3.4683 |

这个记录可以支持：

> DeepGate 系列后续版本的最小数据→前向→真实标签 loss→backward 路径曾在本地成功。

不能支持：

> DeepGate v1 的论文 checkpoint 或 `0.0204` 已复现。

---

## 23. DeepGate v1 与 DeepGate2 的关系

详细 DeepGate2 文档：

[DeepGate2论文与本地复现详解.md](../DeepGate2/DeepGate2论文与本地复现详解.md)

### 23.1 核心差异

| 维度 | DeepGate v1 | DeepGate2 |
|---|---|---|
| 功能监督 | 单节点 signal probability | gate-pair truth-table distance |
| embedding | 一组混合表示 | structural + functional 两组 |
| PI 身份 | 相同初始 hidden 后靠传播分化 | 显式 PI encoding |
| 传播 | T=10 正向+反向循环 | 一次拓扑前向主线 |
| 速度 | 较慢 | 明显更快 |
| 等价性区分 | 同概率不同函数难区分 | 直接优化功能距离 |
| 公开 smoke | 本地没有 v1 record | 本地已有随机初始化训练步 record |

### 23.2 DeepGate2 论文对 v1 的定量比较

DeepGate2 论文报告：

| 模型 | 平均 probability error | 平均推理时间 |
|---|---:|---:|
| DeepGate | 0.0356 | 59.04 s |
| DeepGate2 | 0.0310 | 3.59 s |

这里 DeepGate 的 `0.0356` 与 v1 论文 Table II 的 `0.0204` 不是同一实验表。

不能直接比较两个数字并断言复现漂移，因为：

- 数据划分可能不同；
- 任务设置可能不同；
- 代码版本可能不同；
- 运行批次和硬件不同。

### 23.3 研究演进逻辑

```text
DeepGate v1
  signal probability supervision
          ↓ 发现同概率不同函数问题
DeepGate2
  truth-table pair supervision
  structural / functional disentanglement
          ↓
更适合 logic equivalence、SAT 等功能敏感任务
```

---

## 24. 如果补齐数据，正确复现顺序是什么

当前不建议直接运行 60 epochs。

应先按以下 gate 顺序逐层验收。

### Gate 0：补齐身份与许可证

- 固定 Git commit；
- 记录论文 PDF hash；
- 确认仓库使用权限；
- 固定 Python/PyTorch/PyG 组合。

### Gate 1：补齐原始数据

至少需要：

- EPFL；
- ITC'99；
- IWLS'05；
- OpenCores；
- 明确每个原始文件的 hash。

### Gate 2：补齐 synthesis 工具链

需要：

- ABC；
- AIGER；
- 可能的 Yosys/CNFtoAIG；
- 固定版本；
- 固定命令脚本。

### Gate 3：重建论文数据准备

```text
source circuit
→ AIG
→ optimize
→ subcircuit extraction
→ reconvergence metadata
→ simulation labels
→ NPZ
```

验收：

- 总子电路数是否 10,824；
- 每 suite 数量是否匹配 Table I；
- node/level 范围是否匹配；
- gate type 是否只含 PI/AND/NOT；
- label 是否落在 `[0,1]`；
- 同名 graph 和 label 是否一一对应。

### Gate 4：固定 split

把 split 写为显式 manifest：

```text
train.txt
test.txt
```

不要只依赖运行时 `torch.randperm`。

### Gate 5：小数据过拟合

先取 10～20 个小 AIG：

- loss 能否下降；
- prediction 是否进入 `[0,1]`；
- forward/reverse level 是否正确；
- skip edge 是否只加到 reconvergence；
- cache 是否隔离不同 flags。

### Gate 6：恢复论文主配置

```text
hidden=64
rounds=10
attention
GRU
forward+reverse
reconvergence skip
edge distance encoding
60 epochs
Adam lr=1e-4
L1
```

### Gate 7：恢复论文 evaluator

输出至少包括：

- all-node MAE；
- reconvergent-node MAE；
- non-reconvergent-node MAE；
- per-circuit MAE；
- runtime；
- checkpoint/config/data hash。

### Gate 8：复算 Table II

必须逐一运行：

- GCN × 4 aggregators；
- DAG-ConvGNN × 4 aggregators；
- DAG-RecGNN × 3/4 aggregators；
- DeepGate no-SC；
- DeepGate with-SC。

不要只跑最佳模型然后声称“Table II reproduced”。

### Gate 9：大电路泛化

补齐论文五个 large designs，固定：

- design revision；
- AIG conversion；
- node count；
- level count；
- inference rounds；
- runtime measurement method。

---

## 25. 一个可审计的运行记录应该长什么样

建议每次运行保存：

```json
{
  "paper": "2111.14616",
  "repo_commit": "...",
  "dataset_hash": "...",
  "split_hash": "...",
  "abc_commit": "...",
  "torch_version": "...",
  "pyg_version": "...",
  "seed": 208,
  "model": {
    "hidden": 64,
    "rounds": 10,
    "aggregator": "attention",
    "reverse": true,
    "skip": true,
    "edge_encoding": "paper_eq7_or_code_transformer"
  },
  "checkpoint_sha256": "...",
  "all_node_mae": 0.0,
  "reconvergent_mae": 0.0,
  "non_reconvergent_mae": 0.0,
  "runtime_seconds": 0.0
}
```

尤其需要明确：

```text
edge_encoding = paper Equation 7
```

还是：

```text
edge_encoding = released code 10000-based implementation
```

二者不应混写。

---

## 26. 适合组会讲的核心问题

### 26.1 一句话定位

> DeepGate 是早期“电路基础表示”工作：用 AIG、逻辑概率监督和电路定制 GNN，为每个 gate 学习可迁移 embedding。

### 26.2 最值得讲的三个创新

1. **统一表示**：异构逻辑网络先转 AIG；
2. **电路归纳偏置**：正向/反向拓扑循环传播 + attention；
3. **reconvergence 显式处理**：source→merge skip edge + distance encoding。

### 26.3 最值得讲的一个根本限制

> signal probability 不能唯一表示布尔函数。

这能自然引出 DeepGate2。

### 26.4 最值得讲的一个复现教训

> “论文给代码”不等于“论文实验闭环已公开”。

DeepGate 核心模型代码存在，但精确数据、checkpoint、active evaluator 和 TPI 闭环不完整。

---

## 27. 建议的组会 PPT 结构

### Slide 1：问题背景

- EDA 模型通常任务专用；
- 同一电路图被重复编码；
- 能否学习通用 gate representation？

### Slide 2：为什么普通 GNN 不够

- 电路有方向和拓扑 level；
- gate 有逻辑类型；
- controlling value 不同；
- reconvergence 造成相关性。

### Slide 3：数据准备

直接使用论文 Figure 2 左半：

```text
multi-source circuit → AIG → optimization → simulation label
```

### Slide 4：模型主干

- gate type one-hot；
- attention aggregate fanin；
- GRU combine；
- forward + reverse；
- repeat T=10。

### Slide 5：Reconvergence

使用论文 Figure 3，解释：

- fanout；
- multiple paths；
- reconvergent node；
- direct skip；
- distance encoding。

### Slide 6：Table II

突出三步提升：

```text
best DAG-RecGNN 0.0302
→ attention 0.0234
→ +skip connection 0.0204
```

### Slide 7：大图泛化

展示 Table III，强调训练图最多约 3.2K node，却测试 13K～47K node。

### Slide 8：代码对应

```text
config.py
→ CircuitDataset
→ recgnn.py
→ gat_conv.py
→ BaseTrainer
```

### Slide 9：论文—代码差异

- random hidden vs repeated learned constant；
- Equation 7 vs 10000-based encoding；
- per-type sharing vs single predictor；
- 100k vs default 15k patterns。

### Slide 10：复现状态

明确展示：

```text
paper ✔
core code ✔
dataset ✘
checkpoint ✘
active paper evaluator ✘
exact reproduction ✘
```

### Slide 11：DeepGate2

```text
probability supervision
→ truth-table distance supervision
```

### Slide 12：可做方向

- 多任务逻辑预训练；
- sequential circuit；
- scalable million-gate graph；
- 与 SAT/CEC/LLM 组合；
- 可验证 embedding。

---

## 28. 可以继续研究什么

### 28.1 多任务监督

不要只预测 probability，可以联合：

- signal probability；
- truth-table distance；
- observability/controllability；
- reconvergence type；
- logic depth；
- equivalence pair；
- critical path；
- switching activity。

### 28.2 从组合逻辑扩展到时序逻辑

DeepGate 的 AIG 主线面向组合逻辑。

时序扩展需要显式处理：

- register state；
- clock domain；
- reset；
- cycle unrolling；
- temporal equivalence；
- sequential probability。

### 28.3 可扩展性

论文证明了数万 gate 泛化，但现代 SoC 可达百万级 gate。

需要考虑：

- graph partition；
- hierarchical pooling；
- cone-based retrieval；
- distributed level batching；
- incremental embedding update；
- subgraph caching。

### 28.4 与形式工具结合

合理定位是：

```text
neural embedding → heuristic / ranking / candidate generation
formal tool       → correctness guarantee
```

而不是让 GNN 直接替代 SAT/CEC 的正确性证明。

### 28.5 与 LLM 结合

可以把 gate embedding 用于：

- RTL bug localization；
- synthesis suggestion retrieval；
- netlist-to-RTL explanation；
- LLM 生成候选的结构一致性过滤；
- 功能相似子电路检索；
- EDA agent 的图状态表示。

但需要建立清晰接口：

```text
RTL text token
↕ source mapping
gate/subgraph embedding
↕ tool feedback
formal/synthesis result
```

---

## 29. 不值得重复做的方向

以下工作研究价值有限：

- 只换一层普通 GNN，然后在同一随机电路上刷很小误差；
- 把随机初始化 embedding 可视化后声称学到了逻辑；
- 不固定数据 split，却比较小数点后三位；
- 用 signal probability 冒充完整逻辑功能；
- 不做 SAT/CEC 验证就声称 embedding 判断等价；
- 没有 checkpoint hash 的“预训练推理”；
- 没有 active evaluator 的“论文复现”。

---

## 30. 最终复现判定

### 30.1 已完成

- 原论文已放入项目文件夹；
- 论文身份已核对；
- 三张论文原图已归档；
- 方法和公式已梳理；
- Table I～IV 已整理；
- 核心代码路径已逐项对应；
- 实验 shell 已核对；
- 本地数据/权重缺失已统计；
- 论文—代码差异已定位；
- DeepGate2 已有 smoke 证据已正确引用；
- 静态审计记录已保存。

### 30.2 未完成

- 论文原始训练集重建；
- 官方 checkpoint 获取；
- v1 模型论文权重推理；
- Table II 完整 ablation；
- Table III 大电路评测；
- Table IV AIG transform 对照；
- TPI/ATPG 下游闭环。

### 30.3 最准确的一句话

> ✅ DeepGate 的核心研究方法和核心 GNN 实现已经开源并可做代码级核对，但论文数据、权重、评测入口和下游闭环没有完整发布；当前能够确认“方法与源码已梳理”，不能确认“论文数值已复现”。

---

## 31. 文件导航

### 论文与说明

- [原论文 PDF](./2111.14616_DeepGate.pdf)
- [项目 README](./README.md)
- [数据说明](./DATASETS.md)
- [短版模型梳理](./模型梳理.md)

### 论文截图

- [Figure 1：Circuit Representation as DAG](./figures/paper_fig1_dag.png)
- [Figure 2：Overview of DeepGate](./figures/paper_fig2_overview.png)
- [Figure 3：Reconvergence Skip Connection](./figures/paper_fig3_reconvergence.png)

### 代码入口

- [训练入口](./src/main.py)
- [配置](./src/config.py)
- [DeepGate RecGNN](./src/models/recgnn.py)
- [Attention aggregator](./src/models/gat_conv.py)
- [数据集加载](./src/datasets/circuit_dataset.py)
- [图数据构造](./src/datasets/load_data.py)
- [reconvergence 编码](./src/utils/data_utils.py)
- [训练循环](./src/trains/base_trainer.py)
- [当前测试入口](./src/test.py)
- [benchmark 预处理](./data/benchmarks/prepare_benchmarks_circuits.py)
- [TPI 入口](./tpi/tpi_top.py)

### 审计与跨版本证据

- [本次静态审计 JSON](./runs/static_audit_20260802.json)
- [DeepGate2 详细文档](../DeepGate2/DeepGate2论文与本地复现详解.md)
- [DeepGate2 已有 smoke record](../DeepGate2/runs/smoke/record.json)

---

## P10. 本地可复现等级阶梯

```text
R0 论文身份与公式已核对       [██████████] 100%  ✅
R1 核心源码可静态阅读         [████████░░]  80%  ✅
R2 Python 语法/构建通过       [████████░░]  80%  ✅
R3 训练数据本地可用           [░░░░░░░░░░]   0%  ⚠️
R4 论文权重可加载推理         [░░░░░░░░░░]   0%  ⚠️
```

## P7. 组件一句话总结

| 组件 | 一句话说明 |
|---|---|
| AIG conversion | 把异构逻辑门网表统一转成 PI/AND/NOT 三种节点，消除库漂移。 |
| Signal probability supervision | 用随机输入仿真得到每节点输出为 1 的概率作为监督标签。 |
| Forward propagation | 按拓扑顺序从 PI 向 PO 聚合 fanin 消息，模拟正常逻辑传播。 |
| Backward propagation | 按反拓扑顺序从 PO 向 PI 传播上下文，引入 fanout/implication 信息。 |
| Attention aggregation | 用 target-query 与 fanin-key 计算 softmax 权重，区分控制输入与非控制输入。 |
| GRU update | 把聚合消息与 gate type 拼接，循环更新节点 hidden state。 |
| Reconvergence skip | 对 fanout→reconvergence 的跨路径相关加直接边并编码距离。 |
| L1 loss | 以预测概率与仿真概率的平均绝对误差作为训练目标。 |

## 讨论问题

1. signal probability 作为监督信号能否唯一区分布尔函数？DeepGate2 的监督方式解决了哪些 v1 未解决的问题？
2. 代码中的 hidden state 初始化、位置编码和 regressor 共享与论文文字存在差异；这些差异在多大程度上会影响论文数值复现？
3. 在缺少官方 checkpoint 和 10,824 子电路数据的情况下，我们应该如何设计一个可被审计的“最小可行复现”实验？

