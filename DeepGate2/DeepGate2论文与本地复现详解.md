# DeepGate2 论文与本地复现详解

> 论文：**DeepGate2: Functionality-Aware Circuit Representation Learning**  
> 会议：ICCAD 2023；DOI `10.1109/ICCAD57390.2023.10323798`  
> 原论文：[2305.16373_DeepGate2.pdf](./2305.16373_DeepGate2.pdf)  
> 官方代码：<https://github.com/cure-lab/DeepGate2>  
> 本地 commit：`808567ece4d3`  
> 原文、代码和本地 record 核对日期：2026-08-02

## 0. 先给结论

DeepGate2 在 AIG 上训练一个双路 GNN，输出结构/功能 embedding，并用 truth-table distance 监督避免 v1 的 probability 混淆问题。论文在等价门识别上达到 F1=0.9434，推理速度比 v1 快约 16×；本地只完成了 13 节点最小链路验证，不声称复现论文指标。

```text
┌─────────────────────────────────────────────────────────────┐
│ 任务定义                                                      │
├─────────────────────────────────────────────────────────────┤
│ 输入    AIG = {PI, AND, NOT} 的有向无环图 + gate type/level  │
│ 监督    logic-1 probability + pairwise truth-table distance  │
│ 输出    每个 gate 的 hs（结构）与 hf（功能）embedding         │
├─────────────────────────────────────────────────────────────┤
│ 难点    reconvergence 让 fanin 不独立；AND 的 controlling    │
│         value 会“一票否决”；信号只能沿 PI→PO 单向传播。      │
└─────────────────────────────────────────────────────────────┘
```

## 1. 一句话定位

DeepGate2 给 AIG 中每个逻辑门学习两个 64-dim 向量：

- `hs`：结构 embedding，描述门在电路图中怎样连接；
- `hf`：功能 embedding，描述门对主输入实现了怎样的布尔函数。

它不生成 Verilog，也不输出布局、布线、PPA 或 GDS；它解决的是“怎样得到可迁移的门级电路表示”。

## 2. 为什么 DeepGate v1 不够

DeepGate v1 用 logic-1 probability 作为功能监督：概率只统计“有多少个 1”，不记录“哪些输入组合产生 1”。

```text
f(a,b) = a XOR b   → truth table 中 2/4 个 1
g(a,b) = a XNOR b  → truth table 中也有 2/4 个 1
```

两者 probability 都是 0.5，但功能完全相反 [来源：论文 §II / Table III]。DeepGate2 的核心改进是直接利用成对真值表差异：同一组 random pattern 下输出不同，就在 Hamming distance 中计一次差异。

## 3. 输入数据构造

论文把电路统一为 And-Inverter Graph，只保留 PI、AND、NOT；寄存器、clock/reset、模拟行为和版图信息不在该表示里 [来源：论文 §III-A]。

```text
INPUT(a)
INPUT(b)
n1 = AND(a, b)
n2 = NOT(n1)
OUTPUT(n2)
```

本地 `prepare_dataset.py` 生成 [来源：`src/prepare_dataset.py`]：

```text
graphs.npz
  x[N,3]              # 节点编号、gate type、forward level
  edge_index[2,E]     # fanin → gate

labels.npz
  prob[N]             # logic-1 probability
  tt_pair_index[2,P]  # 被比较的 gate pair
  tt_dis[P]           # pairwise truth-table distance
  min_tt_dis[P]       # 考虑取反关系后的较小距离
```

若电路有 `m` 个主输入，完整真值表需要 `2^m` 个组合，输入数稍大就不可承受。论文对每个电路生成 15,000 个随机 pattern，记录门响应作为不完整真值表；数据来自 ITC'99、IWLS'05、EPFL 与 OpenCore [来源：论文 §III-B]。

| 项 | 论文值 |
|---|---:|
| AIG 数 | 10,824 |
| 单电路规模 | 36–3,214 gates |
| 随机仿真 pattern | 15,000 / circuit |
| gate pair 数 | 894,151 |
| 训练/测试 | 80% / 20% |

⚠️ 正式复现必须按完整 circuit 切分，不能把同一电路的节点对随机分到训练/测试，否则会发生严重结构泄漏。

任意比较全图所有节点会产生平方级 pair。论文只比较共享相关 PI、logic probability 接近的候选，并重点采样 truth-table difference 很小或很大的 pair。这样控制数据量，也导致监督分布不是所有节点对的均匀分布 [来源：论文 §III-C]。

## 4. 模型结构

![论文 Figure 4：网表到结构/功能 embedding，再到三类监督任务](./figures/paper-fig4-learning-framework.png)

论文图中的三个 readout 在代码里分别落到 `readout_prob`、`readout_rc` 和训练器中的 pairwise functional distance loss；模型 `forward()` 本身返回 `hs, hf, prob, is_rc`，功能相似度 loss 在 gate pair 上计算，不是第三个逐节点输出头 [来源：论文 §IV / 代码 `src/models/mlpgate.py`、`src/trains/mlpgnn_trainer.py`]。

### 4.1 前向流程

```text
┌──────────────────────────────────────────────────────────────┐
│  PI Encoding（近似正交初始化）                              │
│        ↓                                                     │
│  level-wise GRU / TFMLP（AND 与 NOT 各用不同单元）          │
│        ↓                                                     │
│  hs_i  +  hf_i   （每个 gate 64+64）                        │
│        ↓                                                     │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐ │
│  │ readout_prob│  │ readout_rc  │  │ pairwise cosine loss│ │
│  │  预测 prob  │  │ 预测 recon  │  │ 拟合 truth-table dis│ │
│  └─────────────┘  └─────────────┘  └─────────────────────┘ │
└──────────────────────────────────────────────────────────────┘
```

### 4.2 两条 embedding 流

每个节点同时维护：

```text
hs_i ∈ R^64  # structural embedding
hf_i ∈ R^64  # functional embedding
```

AND 与 NOT 使用不同的消息聚合和 GRU 更新器，因为两类门的逻辑作用不同 [来源：论文 §IV-A]。

### 4.3 PI Encoding

如果所有 PI 一开始都用同一向量，GNN 很难区分“来自 a 的路径”和“来自 b 的路径”。DeepGate2 给不同 PI 分配近似正交的初始结构编码，使不同输入在 embedding 空间保持身份；功能 embedding 则从统一的可学习映射开始，再通过 fanin 消息逐层分化。PIE 的目标不是背下 PI 名字，而是阻止图同构聚合过早抹去输入身份和 reconvergence 信息 [来源：论文 §IV-B]。

### 4.4 level-wise 单轮传播

“one-round GNN”不是只看一跳，而是按 AIG 拓扑 level 从 PI 向 PO 扫：level l 使用已更新的 level l-1 状态，一轮即可覆盖整个前向 cone，不再像 v1 那样反复进行 10 次 forward + 10 次 backward propagation [来源：论文 §IV-C]。

### 4.5 TFMLP 聚合

默认聚合器对同一目标 gate 的 fanin 做 Q/K/V attention：

```text
fanin hidden states
  → Q/K/V 线性映射
  → 对 fanin 做 softmax 权重
  → 加权 value 求和
  → AND/NOT 对应 GRU
  → 更新 hs 或 hf
```

结构分支仅读 `hs`；AND 的功能分支结合结构与功能，NOT 的功能分支主要更新 `hf`。这种门类型归纳偏置比对所有节点使用同一通用 GNN 更贴近 AIG 语义 [来源：论文 §IV-D / 代码 `src/models/tfmlp.py`]。

### 4.6 为什么 attention 适合电路？

对 AND 门，只要一个 fanin 是 controlling value 0，输出必为 0。如果做简单平均，这个“否决票”会被其它 fanin 稀释；attention 可以把它压到主导权重。

```text
AND(a,b,c)
  a=0, b=1, c=1
  平均：(0+1+1)/3 = 0.67  → 不像 AND
  attention：自动放大 a=0 的权重 → 输出逼近 0
```

这就像“合议制里有一票否决权”：多数同意也不代表通过。AND 的 controlling value 不能被平均掉，这就是 attention 在门级聚合中的物理意义 [来源：论文 §IV-D]。

## 5. 三个训练任务与 loss

### 5.1 三个任务

- **logic probability**：从 `hf_i` 预测 gate 输出 1 的概率，`L_prob = L1(P_i, P_hat_i)`。
- **reconvergence**：从一对 `hs` 预测信号分叉后是否重汇，`L_rc = BCE(R_ij, R_hat_ij)`。
- **pairwise functional distance**：用 cosine distance 衡量 gate pair 的 embedding 距离，拟合归一化 Hamming distance。

```text
D_H(i,j) = 1 - cosine(hf_i, hf_j)
L_func   = L1(normalize(D_H), normalize(D_T))
```

`D_T(i,j)` 为真值表监督。功能 loss 迫使真值表越相似的 gate 在 embedding 空间越近。

### 5.2 两阶段训练

本地脚本对应 [来源：`run/stage1_train.sh`、`run/stage2_train.sh`]：

```text
Stage 1：Prob/RC/Func = 1/0/0  → 先学 logic probability
Stage 2：Prob/RC/Func = 3/1/2  → 从 Stage 1 恢复，加入 RC 与 function
```

论文文字把第一阶段描述为从容易任务建立表示，再在第二阶段学习细粒度功能。原文同一段同时出现“训练 60 epochs”和“所有模型 80 epochs”的表述，存在文字不一致；严格复现应固定代码 commit、脚本参数并记录实际训练日志。

### 5.3 指标解读

| 指标 | 数值 | 含义 |
|---|---|---|
| probability MAE | < 0.01 | 很好 |
| probability MAE | 0.02–0.03 | 论文报道水平 |
| probability MAE | > 0.05 | 需要检查监督或收敛 |
| 等价门 F1 | > 0.90 | 可替代/加速传统等价类筛选 |
| SAT calls 降幅 | ~50% | 模型作为启发式的典型收益 |

## 6. 论文模型实验

![论文 Table II–V 与 Figure 5：等价门识别、PIE/多阶段消融和 SAT sweeping 接法](./figures/paper-table2-ablation-sat.png)

### 6.1 训练配置

论文报告的核心设置 [来源：论文 §VI-A]：

| 项 | 值 |
|---|---:|
| `hs` / `hf` 维度 | 64 / 64 |
| probability / reconvergence MLP 隐层 | 32 |
| optimizer | Adam |
| learning rate | 1e-4 |
| weight decay | 1e-10 |
| batch size | 16 |
| GPU | 单张 NVIDIA V100 |

### 6.2 logic probability

在 10 个 3.18k–40.50k gate 的工业电路上 [来源：论文 Table II]：

| 模型 | 平均 PE | 平均推理时间 |
|---|---:|---:|
| DeepGate | 0.0356 | 59.04 s |
| DeepGate2 | 0.0310 | 3.59 s |

DeepGate2 的平均 prediction error 降低 13.08%，推理速度约 16.43×；速度提升主要来自单轮前向 level propagation，而不是硬件或 batch 配置变化。

### 6.3 等价 gate 识别

| 模型 | Recall | Precision | F1 |
|---|---:|---:|---:|
| DeepGate2 | 98.73% | 90.49% | 0.9434 |
| DeepGate | 91.46% | 54.00% | 0.6778 |
| FGNN | 59.11% | 36.60% | 0.4402 |

DeepGate 的 recall 尚可但 precision 很低，符合“logic probability 相同却功能不同”的理论问题 [来源：论文 Table III]。

### 6.4 消融

| 配置 | 等价 gate F1 |
|---|---:|
| 完整 DeepGate2 | 0.9434 |
| 去掉 PI Encoding | 0.7541 |
| 去掉 multi-stage training | 0.7137 |

去掉 multi-stage 后 `L_func` 从 0.0594 恶化到 0.1224；分阶段使功能 loss 降低 51.47% [来源：论文 Table IV]。

## 7. 两个下游任务

![论文 Table VI / VII：SAT sweeping 与 SAT solver 的调用数和运行时间](./figures/paper-table6-table7-sat-results.png)

### 7.1 SAT sweeping / 逻辑综合

ABC 的 `&fraig` 先用仿真形成候选等价类，再调用 SAT solver 证明两个 gate 是否等价。传统策略如果优先级不好，会产生大量返回 SAT 的无效证明调用。

DeepGate2 用 embedding cosine similarity 给候选等价类排序：功能越相似的 pair 越先交给 SAT solver。最终仍用 `&cec` 做形式等价检查，因此神经模型只提供 heuristic，不替代正确性证明 [来源：论文 §V-A]。

论文在 6 个工业电路上报告：

- SAT calls 平均减少 53.37%，最大 95.88%；
- 总时间平均减少 49.46%，最大 57.77%。

### 7.2 SAT solving

论文把 gate embedding 相似度映射到 CNF variable correlation。某变量赋值后，对高度相关且未赋值的变量做联合反向决策，以更快制造 conflict、收缩搜索空间 [来源：论文 §V-B]。

在 5 个工业 LEC instance 上，把模型推理时间也计入总时间后 [来源：论文 Table VII]：

| instance | baseline | 模型 + solver | 降幅 |
|---|---:|---:|---:|
| I1 | 88.01 s | 32.02 s | 63.62% |
| I2 | 29.36 s | 8.86 s | 69.82% |
| I3 | 61.24 s | 36.13 s | 41.00% |
| I4 | 158.04 s | 142.13 s | 10.07% |
| I5 | 89.89 s | 75.73 s | 15.75% |
| 平均 | — | — | 40.05% |

这个结果说明 embedding 的价值不是“看起来聚类好”，而是能作为传统 solver 的启发式。不同 instance 的收益差异很大，也说明它不是恒定加速器。

## 8. 本地真实运行

### 8.1 为什么不是预训练推理

本地没有找到与当前代码 config 精确匹配的官方 checkpoint，所以没有把随机初始化输出包装成论文效果。当前实测链路是：

```text
真实 .bench 解析
→ 真值表/概率标签构造
→ 真实 DeepGate2 前向
→ 用真实 probability label 算 loss
→ CPU Adam 更新一步
```

### 8.2 运行对象与结果

[`runs/smoke/record.json`](./runs/smoke/record.json) 记录：

| 项 | 本地值 |
|---|---:|
| circuit | `tiny_aig` |
| nodes / edges | 13 / 16 |
| truth-table pair | 1 |
| 模型 | MLPGate + TFMLP，单轮传播 |
| 参数量 | 171,334 |
| structural embedding | `[13,64]` |
| functional embedding | `[13,64]` |
| probability output | `[13,1]` |
| RC output | `[2,1]` |
| 更新前 probability L1 | 0.39677 |
| gradient norm | 3.46828 |

✅ 这证明数据到模型再到反向更新的链路可运行。  
⚠️ 它不证明训练收敛、等价门 F1 或 SAT 加速。

### 8.3 为兼容当前环境做的修正

- parser 把 `INPUT` 归一为 `PI`，预处理 gate map 同步改为 `PI`；
- 逻辑仿真函数兼容新的 gate-map 参数；
- 修正不存在的 `utils.rename_node` 调用；
- 默认 TFMLP 不需要 `torch_scatter`，把旧聚合器改为可选导入。

这些改动属于运行兼容修复，不是论文算法改进。正式复现实验必须保留补丁、环境和 commit。

## 9. 与 CircuitNet 3.0、LLM 的区别

| 项目 | 学习对象 | 粒度 | 输出 |
|---|---|---|---|
| DeepGate2 | AIG 图 | gate-level | 结构/功能 embedding |
| CircuitNet 3.0 | RTL、网表、版图多模态 | design / net / image | timing、power 等预测 |
| RTLCoder/ChipSeek/MAGE | 自然语言与 RTL token | sequence-level | Verilog 文本 |

DeepGate2 可与 LLM 组合：做功能相似检索、repair 候选特征、综合策略 state、formal/SAT 候选优先级。但当前论文没有证明它能直接处理时序 RTL、多模块协议或物理 PPA。

## 10. 局限与后续研究

1. 只处理组合 AIG，时序状态被消除或需另建表示。
2. 15,000 随机 pattern 是近似，稀有 corner case 可能采不到。
3. pair 构造和 truth-table distance 仍有平方级风险，需要采样策略。
4. 80/20 划分必须确认是 circuit-level；若是 pair-level，结果可能受泄漏影响。
5. 下游工业电路未公开，完整复现受限。
6. 仓库根目录当前未见明确 LICENSE，代码再发布或商用前需向作者确认。
7. 更有价值的是 sequential circuit、跨工艺/跨综合器泛化、uncertainty 和与 LLM/tool agent 的联合闭环。

## 11. 模型直觉：reconvergence 的“支流”比喻

如果信号从某节点分叉到两条路径，再汇到同一个 gate，这两个 fanin 就不是独立随机变量——它们共享上游水源。不能只看局部 fanin，必须记得它们有共同祖先。

```text
      上游大河 n
        ├─ 支流 A ─┐
        └─ 支流 B ─┘
               ↓
            汇合门 m
```

PI Encoding + level-wise 传播就像给每条支流贴上“来自哪条河”的标签，并在汇合时把共同来源的统计信息 skip 过多层直接带回来。否则模型会把两条支流当成无关的独立水源，低估 reconvergence 造成的 fanin 相关性。

## 12. 组会分享建议与代码执行链

建议用 XOR/XNOR 开场，依次讲：AIG 与两套 embedding → pairwise truth-table distance → PI Encoding 与 level-wise one-round GNN → 三个 loss 和两阶段训练 → 0.9434 F1 / 16.43× 加速 → SAT 下游真实收益 → 本地 13 节点边界 → 与 CircuitNet 3.0 / RTL LLM 的表示层差异。

### 12.1 代码执行链逐项对照

| 阶段 | 代码位置 | 真实行为 |
|---|---|---|
| `.bench`/AIG 解析 | `src/prepare_dataset.py`、`src/get_emb_bench.py` | 建立 node type、edge、topological level、真值表/概率与候选 pair |
| PyG 数据封装 | `src/datasets/mlpgate_dataset.py` | 生成 `OrderedData`，保存 forward index/level、prob、TT pair、RC pair |
| PI encoding | `src/utils/utils.py::generate_hs_init()` | 给同一图的 PI 生成近似正交结构初始向量 |
| 双流初始化 | `src/models/mlpgate.py::forward()` | `hs` 从 PI encoding 开始，`hf` 从可学习的一维映射复制到节点 |
| level-wise GNN | `MLPGate._gru_forward()` | 按 `forward_level` 分层，AND/NOT 分别聚合并由不同 GRU 更新 |
| readout | `MLPGate.forward()` | `readout_prob(hf)` 预测 probability；结构 pair 拼接后预测 reconvergence |
| 训练 | `src/main.py` + `src/trains/mlpgnn_trainer.py` | DataLoader、stage loss 权重、反向传播、checkpoint |
| 单图 embedding | `src/get_emb_bench.py` | 加载 checkpoint，输出 `hf` 和 probability 文本 |
| SAT 下游 | `T2_SAT/` | 将 embedding 接入 SAT sweeping / solver heuristic；最终正确性仍由 SAT/CEC 证明 |

本地 `local_smoke_test.py` 走的是上述前六步的最小可执行子集，并额外做一次 backward；它没有进入论文 `T2_SAT` 工业实例，也没有加载论文 checkpoint。

## 13. 关键文件索引

- [原论文 PDF](./2305.16373_DeepGate2.pdf)
- [简版模型梳理](./模型梳理.md)
- [数据准备](./src/prepare_dataset.py)
- [MLPGate 主模型](./src/models/mlpgate.py)
- [TFMLP 聚合器](./src/models/tfmlp.py)
- [训练器](./src/trains/mlpgnn_trainer.py)
- [两阶段脚本](./run/)
- [本地烟雾测试 record](./runs/smoke/record.json)
- [SAT 下游](./T2_SAT/)

## 14. 一句话组件总结

| 组件 | 一句话 |
|---|---|
| AIG 表示 | 只保留 PI/AND/NOT 的最小布尔图，统一所有电路的输入格式。 |
| PI Encoding | 给不同主输入近似正交的初始结构向量，防止早期聚合抹掉身份。 |
| level-wise GRU | 按拓扑层从 PI 扫向 PO，一轮覆盖整个前向 cone。 |
| TFMLP 聚合 | 用 attention 为 fanin 加权，AND/NOT 各用不同更新单元。 |
| `hs` / `hf` | 结构 embedding 记“怎么连”，功能 embedding 记“实现什么布尔函数”。 |
| readout_prob | 从 `hf` 预测 gate 输出 1 的概率，提供粗粒度功能监督。 |
| readout_rc | 从 `hs` 判断两个节点是否 reconverge，捕捉 fanin 相关性。 |
| pairwise function loss | 用 cosine distance 拟合 Hamming distance，拉近功能相似 gate。 |
| 两阶段训练 | 先学 probability 粗调，再学 RC+function 细调。 |
| SAT 下游 | embedding 只排优先级，最终等价性仍由 SAT/CEC 证明。 |

## 15. 组会讨论题

1. 为什么 DeepGate2 用 **truth-table distance** 而不是直接用真值表全向量作为监督？这种成对距离在训练效率和表达能力之间做了怎样的取舍？
2. PI Encoding 给主输入近似正交的初始向量，但 AIG 是同构图：如果测试电路里出现训练时没见过的 PI 名字或拓扑，这种正交初始化会不会反而限制泛化？有什么缓解思路？
3. DeepGate2 的 SAT 加速本质上是“用神经网络给 SAT solver 排优先级”。在你看来，哪些 EDA 环节也适合这种“神经启发式 + 传统证明器”的范式，又有哪些环节必须端到端保证正确性？
