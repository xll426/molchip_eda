# CircuitNet 2.0 论文深度讲解

> **CircuitNet 2.0: An Advanced Dataset for Promoting Machine Learning Innovations in Realistic Chip Design Environment**
> Xun Jiang, Zhuomin Chai, Yuxiang Zhao, Yibo Lin, Runsheng Wang, Ru Huang
> Peking University · Wuhan University
> ICLR 2024
> 原文：[ICLR2024_CircuitNet2.0.pdf](./ICLR2024_CircuitNet2.0.pdf)
> 代码：https://github.com/circuitnet/CircuitNet
> 数据集：https://circuitnet.github.io/

---

## 1. 一句话定位

**CircuitNet 2.0 是 CircuitNet 1.0 的全面升级版——它把数据集从 28nm planar CMOS CPU-only 扩展到 14nm FinFET 多架构（CPU+GPU+AI Chip），样本量超过 10,000 个完整商业 EDA flow 产出，任务从 routability/IR-drop 扩展到 routability+DRV+IR-drop+timing 四类预测，并首次系统性地研究了跨设计泛化（cross-design generalization）、类别不平衡（class imbalance）和跨工艺迁移（cross-technology transfer）三个 realistic EDA 场景下的 ML 挑战。与 1.0 的「建立一个可用的公开数据集」不同，2.0 的核心问题是：在一个 non-i.i.d. 的真实设计空间中，ML 模型到底能泛化多远？**

这句话里的四个技术承重点：

1. **数据规模与真实性的跃升** -- 从 1.0 的 28nm CPU-only 到 2.0 的 14nm FinFET CPU+GPU+AI Chip，10,000+ 完整 EDA flow 样本。每个样本都经过商业综合→floorplan→placement→CTS→routing→分析的全流程。
2. **任务扩展** -- 从 1.0 的 congestion/DRC/IR-drop 扩展到 routability（congestion+DRV）、IR-drop、timing（net delay + pin slack）四类任务。
3. **跨设计泛化研究** -- 1.0 的同设计 train/test split 不能反映真实 EDA 场景。2.0 定义了 cross-design split（CPU train → GPU test），结果揭示 domain shift 是真实瓶颈（F1 下降 20-45%）。
4. **跨工艺迁移** -- 在 N28（1.0 数据）上训练，在 N14（2.0 数据）上测试，研究工艺迁移的可行性。

---

## 2. EDA 阶段映射（①-⑰）

参照 [芯片流程.md](../芯片流程.md) 的 17 阶段标准编号：

| 阶段 | 覆盖 | 说明 |
|------|:---:|------|
| ① RTL 设计 | ✅ 上游输入 | CPU/GPU/AI Chip 的 RTL 是数据生成起点，但不随公开数据发布 |
| ② RTL 功能仿真 | ❌ | 数据集不提供 RTL 仿真波形 |
| ③ 逻辑综合 | ✅ 数据起点 | 商业综合工具产出网表，抽取后续特征 |
| ④ 门级仿真 | ❌ | 不提供门级仿真结果 |
| ⑤ STA（静态时序分析） | ✅ 预测目标 | timing 任务的 net delay / pin slack / WNS / TNS 标签取自签核级 STA 报告 |
| ⑥ 形式验证 | ❌ | 不涉及等价性检查或属性证明 |
| ⑦ 布局规划（Floorplan） | ✅ | 提供 macro region 等 floorplan 特征 |
| ⑧ 标准单元摆放（Placement） | ✅ | cell density、pin density、RUDY 等是核心输入 |
| ⑨ 时钟树综合（CTS） | ✅ | 提供 CTS 后的时钟网络特征 |
| ⑩ 布线（Routing） | ✅ | 提取最终 congestion、DRV 标注 |
| ⑪ 后仿真 | ❌ | 不提供带寄生的后仿真波形，也不公开原始 SPEF |
| ⑫ 物理验证（DRC + LVS） | ✅ 预测目标 | DRV hotspot 预测对应布线后的设计规则违规风险 |
| ⑬ 签核（Signoff） | ✅ 预测目标 | IR-drop 分布是签核级电源完整性结果 |
| ⑭ 流片 | ❌ | 不涉及 |
| ⑮ 制造 | ❌ | 不涉及 |
| ⑯ 封装 + 测试 | ❌ | 不涉及 |
| ⑰ 芯片到手 | ❌ | 不涉及 |

**覆盖率：9/17（①③⑤⑦⑧⑨⑩⑫⑬；数据从 ③ 延伸到 ⑬ 的物理设计与签核预测，①、⑭-⑰ 仅是流程边界）。**

> ⚠️ CircuitNet 2.0 的数据由商业 EDA 工具和 14nm FinFET 商业 PDK 生成，遵守 NDA 限制。公开数据是提取后的特征和标签，不包含原始 RTL/网表/PDK/标准单元库。你无法从 RTL 重新生成这些数据。

---

## 3. 输入 / 输出

### 3.1 数据模态：从 RTL 到 Signoff 的全流程特征

CircuitNet 2.0 的数据覆盖物理设计全流程的多阶段特征。与 1.0 的最大不同是新增了 timing 相关特征和标签：

**Placement 阶段特征（图像模态）**：芯片版图划分为 256x256 或 512x512 的规则网格（tile/grid），每个格点编码该区域的物理特征。

```text
macro_region [H, W]:        宏单元区域掩码（1=macro, 0=standard cell area）
cell_density [H, W]:        标准单元密度（该格点内 cell 总面积/格点面积）
pin_density [H, W]:         引脚密度（该格点内 pin 总数）
RUDY [H, W]:                Rectangular Uniform wire DensitY 粗略布线需求
pin_RUDY [H, W]:            基于引脚位置的 RUDY 变体
```

**Routing 阶段特征（图像模态）**：

```text
early_global_routing_congestion [H, W]:  早期全局布线拥塞估计
early_global_routing_overflow [H, W]:    溢出计数
global_routing_congestion [H, W]:        最终全局布线拥塞
```

**Timing 特征（新增于 2.0）**：

```text
net_delay [N_nets]:          每条 net 的延迟
pin_slack [N_pins]:          每个 pin 的时序 slack（最差负余量）
cell_delay [N_cells]:        每个 cell 的固有延迟
timing_graph edges:          cell→net→cell 的时序传播路径
```

**输出标签（同尺寸 grid map 或 per-instance 标量）**：

```text
Routability:
  routing_congestion [H, W]:     最终布线拥塞 heatmap
  DRV_hotspot [H, W]:            设计规则违规 hotspot map (二值)

IR-drop (Signoff):
  IR_drop [H, W]:                电压降分布

Timing (Signoff, 新增):
  WNS (Worst Negative Slack):   全局最差负余量
  TNS (Total Negative Slack):   总负余量
  net_delay [N_nets]:           每条 net 的最终延迟
```

**图模态特征（GNN 适用）**：

```text
以 cell/pin/net 为三类节点的异构图:

Cell 节点特征 (N_cells):
  - cell_type: one-hot (AND/OR/FF/MUX/BUF/INV/...)
  - cell_area: 标准单元面积
  - cell_location: (x, y) 坐标
  - pin_count: 该 cell 的引脚数

Pin 节点特征 (N_pins):
  - pin_location: 相对于 cell 的偏移
  - pin_direction: input/output/bidirectional

Net 节点特征 (N_nets):
  - net_degree: 该 net 连接的 pin 数 (fanout)
  - net_bounding_box: 该 net 的最小包围矩形
  - net_layer: 布线金属层

边类型:
  - cell → pin (contains)
  - pin → net (connects)
  - net → pin (connects, 反向)
```

### 3.2 设计统计数据

论文 Table 1 列出 8 个设计的规模，总样本数 **10,791**（论文 Section 3.1 原文）：

| 设计 | 类型 | #Cells | #Nets | #Macros | #Pins | #IOs | #Samples |
|------|------|-------:|------:|--------:|------:|-----:|---------:|
| zero-riscy | CPU | 35,969 | 36,225 | 3 | 138,569 | 563 | 3,456 |
| RISCY | CPU | 46,184 | 47,233 | 3 | 180,069 | 563 | 3,456 |
| RISCY-FPU | CPU | 65,464 | 66,903 | 3 | 252,390 | 563 | 3,456 |
| Vortex-small | GPU | 113,961 | 124,058 | 43 | 433,449 | 1,234 | 96 |
| NVDLA-small | AI Chip | 270,072 | 285,465 | 108 | 1,039,571 | 538 | 89 |
| OpenC910-1 | CPU | 754,981 | 766,436 | 32 | 3,062,504 | 1,341 | 96 |
| Vortex-large | GPU | 1,018,221 | 1,107,255 | 376 | 3,731,139 | 1,242 | 74 |
| NVDLA-large | AI Chip | 1,478,865 | 1,637,556 | 80 | 5,705,108 | 1,734 | 68 |

这张表说明三件事。第一，**规模跨度接近 40×**：最大设计 NVDLA-large 的 1,478,865 个 cell 约为最小设计 zero-riscy（35,969）的 41 倍，而 CircuitNet 1.0 全部设计的 cell 数都在 70,000 以下——这是 2.0 相对 1.0 最实质的进步。

第二，**样本数与设计规模严重反比**，这正是论文定义的「data imbalance」挑战的数据来源：三个小型 RISC-V CPU 各贡献 3,456 个样本（合计 10,368，占总量的 96%），而 5 个大型设计合计仅 423 个样本。原因是生成成本——论文脚注写明 zero-riscy 生成一个样本约 2 小时，NVDLA-large 接近 **1 周**。

第三，**macro 数量与设计类型不成正比**：Vortex-large 有 376 个 macro（最多），NVDLA-large 只有 80 个，但后者 cell 数更多。这意味着 floorplan 的形态差异不能仅用规模解释，跨设计泛化面对的是结构差异而非单纯尺度缩放。

### 3.2.1 与 CircuitNet 1.0 的数据规模对比

| 指标 | CircuitNet 1.0 | CircuitNet 2.0 |
|------|:---:|:---:|
| 工艺 | 28nm planar | **14nm FinFET** |
| 设计类型 | CPU | **CPU + GPU + AI Chip** |
| 样本数 | 数百 | **10,000+** |
| 任务数 | 3 | **4 (+timing)** |
| 跨设计 split | ❌ | ✅ |
| 跨工艺 transfer | ❌ | ✅ |

### 3.3 数据集划分策略

| Split | 训练集 | 测试集 | 研究问题 |
|-------|--------|--------|---------|
| Same-design | 同设计 80% | 同设计 20% | 标准 ML benchmark |
| Cross-design | CPU 设计 | GPU 设计（或相反） | 跨架构 domain shift |
| Cross-technology | N28 设计 | N14 同类型设计 | 工艺迁移 |

---

## 4. 方法与架构

### 4.1 Baseline 模型

CircuitNet 2.0 是数据集论文，提供 baseline 验证数据可用性：

**图像模态（CNN/FCN）**：U-Net 变体对 [C,H,W] 特征图做 dense prediction。

```text
  Feature Maps [C, H, W]
      │
      ▼
  ┌─────────────────────────────┐
  │  U-Net / FCN Encoder-Decoder │
  │  Encoder: 下采样+特征提取     │
  │  Decoder: 上采样+skip conn   │
  │  Output: [1, H, W] prediction│
  └─────────────────────────────┘
```

**图模态（GNN）**：GCN/GAT 对异构图做 node-level 或 graph-level 预测。

### 4.2 跨设计泛化的核心发现

论文最重要的实验发现：same-design split 上的高性能在 cross-design split 上全面退化。

| 任务 | Same-design F1 | Cross-design F1 | 退化幅度 | 解释 |
|------|:---:|:---:|:---:|------|
| Congestion | 0.85+ | 0.55~0.65 | **-25~35%** | 不同设计的布线拥塞模式差异大 |
| DRV | 0.80+ | 0.40~0.55 | **-30~45%** | DRV 对工艺和设计规则高度敏感 |
| IR-drop | 0.90+ | 0.60~0.75 | **-20~30%** | 电源网络结构在不同设计间较稳定 |

**这张表说明什么**：DRV 是跨设计泛化最难的任务——F1 从 0.80+ 跌到 0.40~0.55，几乎砍半。这是因为 DRV 模式高度依赖具体的标准单元布局和金属层走线密度，一个 CPU 设计中学到的「哪些格点容易产生 DRV」的知识几乎无法迁移到 GPU 设计。IR-drop 相对最鲁棒，因为电源网络的拓扑结构在设计间有更多共性。

### 4.3 类别不平衡处理策略

EDA 预测任务存在严重的天然类别不平衡，需要专门的训练策略：

```text
典型 DRV 预测的类别分布:
  Non-violation tiles: ~95-98%  (负样本，不产生 DRV)
  Violation tiles:     ~2-5%    (正样本，产生 DRV)

标准 BCE loss 的问题:
  模型只要全部预测为 "no violation"，就有 95%+ accuracy
  但 Recall = 0%，完全无法检测 hotspot

解决策略对比:
  1. Class-balanced sampling: 对 violence tile 过采样/对 normal tile 欠采样
     → 改变数据分布，训练变慢但稳定
  
  2. Focal Loss: L = -(1-p_t)^γ * log(p_t)
     → γ=2 时，易分样本 (p_t≈0.9) 的 loss 缩小 100 倍
     → 模型被迫关注难分的 violation tiles
  
  3. Class weight: 给正样本分配更高的 BCE loss 权重
     → weight = 1/class_frequency
     → 最简单、最鲁棒的方法

论文结论: Category weight 调整最稳定有效，
  Focal loss 在极端不平衡 (>98%) 场景下有时不稳定。
```

### 4.4 跨工艺迁移实验

论文在 N28（1.0 数据）上训练模型，在 N14（2.0 数据）同类型设计上测试，研究工艺迁移：

| 任务 | N28→N14 F1 退化 | 关键差异 |
|------|:---:|------|
| Congestion | -10~15% | 14nm 金属层更多，布线资源更丰富 |
| DRV | -15~20% | 14nm FinFET 设计规则更严格 |
| IR-drop | -5~10% | 电源网络分析在不同工艺间相对稳定 |

**跨工艺迁移 vs 跨设计泛化**：跨工艺的 F1 退化（10~20%）远小于跨设计的退化（20~45%），说明「相同设计在不同工艺下」比「不同设计在相同工艺下」的 domain shift 更小——设计本身的物理特征差异是比工艺更大的 domain factor。

### 4.5 模块职责矩阵

CircuitNet 2.0 是数据集论文，没有「模型模块」，它的职责矩阵是**任务 → 特征 → 标签 → 模态**的映射（论文 Table 2）：

| 预测任务 | 输入特征 | 特征模态 | 标签 | 标签模态 | 需训练 |
|---|---|---|---|---|:---:|
| Routability（congestion） | Macro Region、RUDY、Instance Placement | 图像 + 图 | Congestion | 图像 | ✅ |
| Routability（DRV） | Macro Region、Cell Density、RUDY、Pin Configuration、eCongestion、Congestion | 图像 | DRV | 图像 | ✅ |
| IR-drop | Overall Power、Temporal Power | 图像 + 3D 数组 | IR-drop | 图像 | ✅ |
| Timing | Netlist、Pin Position | 图 | Net delay | 图 | ✅ |

三点值得注意。**第一，congestion 身兼两职**——它是 congestion 预测任务的标签，同时又是 DRV 预测任务的输入特征。这反映真实流程的因果链：先有拥塞，拥塞才导致 DRV。用预测出的 congestion 去预测 DRV 会引入误差传播，论文的 DRV 任务用的是真实 congestion。

**第二，只有 IR-drop 任务用到 3D 数组**（Temporal Power，即随时间变化的功耗序列）。其余特征都是 2D 图像或图。这是因为 IR-drop 本质是动态现象——瞬时电流峰值决定压降，静态平均功耗不足以刻画。

**第三，Timing 任务是纯图模态**（netlist 拓扑 + pin 位置 → net delay），不走图像路线。时序沿网表路径传播，格点化会破坏连接关系，这是 GNN 而非 CNN 的天然场景。

---

## 5. 关键公式

### 5.1 逐格点预测评估

Congestion 预测是逐格点二分类：

$$
\text{F1} = 2 \cdot \frac{\text{Precision} \cdot \text{Recall}}{\text{Precision} + \text{Recall}}
$$

hotspot 阈值由 congestion map 分布决定（如 top 5% 定义为 hotspot）。

### 5.2 IR-drop 预测

$$
\hat{V}_{\text{drop}}(x, y) = f_{\theta}(\text{Features}[x, y])
$$

- $(x, y)$：版图格点坐标
- $\text{Features}[x, y]$：该格点多模态特征
- $f_{\theta}$：CNN/U-Net 模型

### 5.3 跨设计 Domain Gap

论文未给出编号公式，以下是对其行为的形式化：

$$
\text{DomainGap} = \text{Perf}_{\text{same-design}} - \text{Perf}_{\text{cross-design}}
$$

GPU→CPU 的 gap 通常小于 CPU→GPU，因 GPU 设计物理特征分布更广（包含更多极端值）。

---

## 6. 训练与实验设置

### 6.1 是否需要训练

**是，需要训练——但训练的是使用者的模型，不是数据集本身。** CircuitNet 2.0 提供的是「特征 + 标签」对，使用者按第 4.5 节的任务矩阵自行训练：图像模态任务（congestion / DRV / IR-drop）训练 U-Net 类 FCN 做 dense prediction，图模态任务（timing）训练 GNN 做 net-level 回归。

论文自己训练的 baseline 是「够用即止」的参考实现，目的是证明数据可学，而不是刷 SOTA。论文明确把两类 realistic 任务作为训练时必须面对的挑战：

1. **不平衡数据学习**：DRV 正样本占比仅 2~5%，直接用 BCE 会退化成全负预测（见第 4.3 节）。论文结论是 category weight 最稳定，focal loss 在 >98% 不平衡时反而不稳。
2. **迁移学习**：跨 PDK（N28→N14）与跨设计（CPU→GPU）两种迁移。跨设计的退化远大于跨工艺（见第 4.2、4.4 节）。

换言之，在这个数据集上「训练」不是简单跑通一个 U-Net，而是必须显式处理类别不平衡和 domain shift——这是它区别于 CircuitNet 1.0 的核心设计意图。

### 6.2 关键实验结果

**跨设计泛化**：

| 训练 | 测试 | Congestion F1 | DRV F1 | IR-drop F1 |
|------|------|:---:|:---:|:---:|
| CPU | CPU | 0.87 | 0.82 | 0.91 |
| CPU | GPU | 0.58 | 0.45 | 0.68 |
| GPU | GPU | 0.85 | 0.80 | 0.90 |
| GPU | CPU | 0.62 | 0.50 | 0.72 |

**跨工艺迁移**：N28 train → N14 test，F1 退化约 10~20%。

**类别不平衡**：focal loss / class-balanced loss 在 DRV 预测上 F1 提升 5~15 个百分点。

---

## 7. 创新点

### 创新点 1：从 28nm CPU-only 到 14nm 多架构 realistic 数据集

工艺从 28nm planar 到 14nm FinFET 意味着物理特征分布的根本变化。

### 创新点 2：首次系统性跨设计泛化研究

量化 domain gap，证明 same-design split 高估模型泛化能力。不同设计类型之间的 domain shift 远大于 CV/NLP 常见场景。

### 创新点 3：定义 realistic EDA ML 三大挑战

(a) cross-design generalization；(b) severe class imbalance；(c) cross-technology transfer。

### 创新点 4：多模态数据统一 — 同一份物理设计同时提供图像、图与时序三种模态

以前是：一个 EDA ML 数据集只服务一种模型范式。图像类数据集（如 CircuitNet 1.0 的主体）把版图格点化成 2D 特征图喂 CNN，图类数据集（如 OpenABC-D）把网表交给 GNN，两者的设计来源、工艺、流程配置各不相同，导致「CNN 方法和 GNN 方法谁更好」这个问题无法公平回答——差异可能来自数据而非模型。

它改成：**同一批 10,791 个样本，同时导出三种模态的特征**（论文 Table 2）——
- **图像（2D array）**：Macro Region、Cell Density、RUDY、Pin Configuration、eCongestion、Congestion、Overall Power
- **图（Graph）**：Instance Placement、Netlist、Pin Position
- **3D 数组**：Temporal Power（功耗随时间的序列）

因为这样才能让模态选择本身成为可研究的变量。具体带来两件以前做不到的事：

第一，**同任务跨模态对比成为可能**。congestion 预测既可以用 RUDY 图像走 CNN，也可以用 Instance Placement 图走 GNN，两条路线的输入源自同一次物理实现，性能差异可以归因于模型而非数据。

第二，**多模态融合有了实验基础**。timing 预测天然是图问题（延迟沿网表路径累积），但拥塞信息天然是空间问题（图像）——真实的时序退化恰恰由局部拥塞引起。只有当图与图像来自同一份 layout，才能把「拥塞图像特征」注入「网表图模型」去预测 net delay。IR-drop 的 Temporal Power 更进一步：静态功耗图无法解释瞬时压降，必须叠加时间维度。

需要说明的边界：论文提供多模态数据，但其 baseline 实验主体仍是单模态（以 timing 任务为例演示），跨模态融合被列为数据集支持的方向而非已完成的贡献。

---

## 8. EDA 缩写表

| 缩写 | 全称 | 一句话解释 |
|------|------|-----------|
| DRV | Design Rule Violation | 设计规则违规——布线后违反工艺规则的位置 |
| RUDY | Rectangular Uniform wire DensitY | 矩形均匀线密度——粗略布线需求估计 |
| FinFET | Fin Field-Effect Transistor | 鳍式场效应晶体管，14nm 以下主流结构 |
| PDK | Process Design Kit | 工艺设计套件，含标准单元库和设计规则 |
| NDA | Non-Disclosure Agreement | 保密协议，商业 PDK/工具受此约束 |
| Domain Shift | 领域偏移 | 训练/测试数据分布不同导致性能下降 |
| Class Imbalance | 类别不平衡 | hotspot <5% 导致模型偏向多数类 |

其他缩写见 [CircuitNet 1.0 深度讲解](./论文深度讲解_CircuitNet1.0.md)。

---

## 9. 与芯片流程的关系

### 9.1 与 CircuitNet 1.0 的演进

| 维度 | 1.0 | 2.0 | 演进意义 |
|------|-----|-----|---------|
| 工艺 | 28nm | 14nm FinFET | 更现代工艺，物理效应更复杂 |
| 设计 | CPU only | CPU+GPU+AI Chip | 可研究 domain shift |
| 任务 | 3 | 4 (+timing) | 覆盖更完整 PPA |
| 研究重点 | 数据可用性 | 泛化能力 | 从「能用」到「多好用」 |

---

## 10. 讨论与局限

### 10.1 论文自述局限

- 商业工具+PDK 数据不可重跑
- Cross-design 泛化 F1 下降 20-45%，是开放问题
- 14nm 非最新工艺（3nm/5nm 受更严 NDA）

### 10.2 批判性分析

- **「真实」的代价是无法复现数据**：10,000+ 样本需商业 EDA license + 14nm PDK + 数月计算。CircuitNet 2.0 是「公共评测基准」而非「可自行生成的数据集框架」。
- **Cross-design gap 根源未深挖**：展示了 domain gap 但未分析「gap 来自哪些物理特征分布差异」。
- **预测时间点仍在 routing 后**：与 1.0 一样是「routing 后预测 signoff」。真正的前移预测（RTL 阶段预测最终 PPA）见 [CircuitNet 3.0](../CircuitNet3.0/论文深度讲解.md)。

---

## 11. 复现信息

| 项目 | 内容 |
|------|------|
| 论文页 | https://openreview.net/forum?id=nMFSUjxMIl |
| 代码 | https://github.com/circuitnet/CircuitNet · BSD-3-Clause |
| 数据集 | https://circuitnet.github.io/ |
| 复现等级 | R2（数据可下载，baseline 可运行；数据不可自生成） |

---

## 12. 一分钟复述版

CircuitNet 2.0（PKU，ICLR 2024）是 CircuitNet 1.0 全面升级：28nm→14nm FinFET，CPU-only→CPU+GPU+AI Chip，样本 10,000+，任务 3→4（+timing）。核心贡献：首次系统性 cross-design generalization 研究，发现 same-design split 严重高估泛化能力（cross-design F1 降 20-45%），定义 realistic EDA ML 三大挑战（domain shift + class imbalance + technology transfer）。局限：商业数据不可重生成，预测仍在 routing 后而非 RTL 阶段。

---

> 参考：[CircuitNet 1.0 深度讲解](./论文深度讲解_CircuitNet1.0.md) · [CircuitNet2.0论文与代码复现详解.md](./CircuitNet2.0论文与代码复现详解.md) · [CircuitNet3.0 深度讲解](../CircuitNet3.0/论文深度讲解.md) · [芯片流程](../芯片流程.md)
