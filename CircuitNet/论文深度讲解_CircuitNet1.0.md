# CircuitNet 1.0 论文深度讲解

> **CircuitNet: An Open-Source Dataset for Machine Learning Applications in Electronic Design Automation (EDA)**
> Zhuomin Chai, Yuxiang Zhao, Yibo Lin, Wei Liu, Runsheng Wang, Ru Huang
> 北京大学集成电路学院；武汉大学物理科学与技术学院
> Science China Information Sciences, 2022 · arXiv: 2208.01040 v4（2022-09-01）
> 原文：[2208.01040_CircuitNet.pdf](./2208.01040_CircuitNet.pdf)
> 代码：https://circuitnet.github.io

---

## 1. 一句话定位

**CircuitNet 1.0 是首个面向 EDA 机器学习应用的大规模公开数据集，在 28 nm planar CMOS 工艺下对 6 个 RISC-V 设计跑 12,960 次完整商业后端设计流程（逻辑综合 + 物理设计），从中提取图结构特征（门级网表）和图像式特征（二维栅格化特征图），支持拥塞预测（NRMSE=0.040, SSIM=0.80）、DRC 违规预测（ROC-AUC=0.95, PR-AUC=0.63）和 IR-drop 预测（ROC-AUC=0.94, PR-AUC=0.83）三个跨阶段预测任务，为 EDA 领域的机器学习研究提供了可复现的公共评测基准。**

这句话里的三个核心承重点，后面逐一拆解：

1. **数据集而非模型** -- CircuitNet 1.0 的核心贡献是数据和基准，不是提出新神经网络。它把过去依赖私有数据才能做的后端物理设计跨阶段预测（routability、DRC、IR drop）变成了一个可公开评估的问题。论文验证性地跑了 FCN 和 U-Net baseline，但数据集本身才是 main dish。
2. **多模态特征体系** -- 同时提供图结构特征（门级网表，适合 GNN）和图像式特征（栅格化的密度/拥塞/功耗二维图，适合 CNN），覆盖了 EDA 中两种主流的机器学习建模范式。这种双模态设计使得研究者可以从图神经网络和卷积神经网络两个方向切入同一个预测问题。
3. **真实商业流程数据** -- 所有样本由 Synopsys Design Compiler（逻辑综合）和 Cadence Innovus（物理设计）在 28 nm 标准单元库下生成，每个设计引入了 2160 种参数组合（利用率、频率、macro 摆放、power mesh 配置等），反映了真实后端设计空间中的多样性。

---

## 2. EDA 阶段映射（①-⑰）

参照 [芯片流程.md](../芯片流程.md) 的 17 阶段标准编号：

| 阶段 | 覆盖 | 说明 |
|------|:---:|------|
| ① RTL 设计 | ✅ | RISC-V 设计的 Verilog RTL 源码来自开源项目 PULPino，是数据生成的起点 |
| ② RTL 功能仿真 | ❌ | 不涉及——数据生成流程直接从 RTL 进入逻辑综合 |
| **③ 逻辑综合** | ✅ **核心** | 用 Synopsys Design Compiler 把 RTL 映射到 28 nm 门级网表。通过改变频率约束（50/200/500 MHz）产生合成多样性 |
| ④ 门级仿真 | ❌ | 不涉及——综合后的网表直接交给物理设计，不做中间门级仿真 |
| ⑤ STA | ❌ | 1.0 版本不含时序预测任务，因此不提取 STA 数据 |
| ⑥ 形式验证 | ❌ | — |
| **⑦ 布局规划 (Floorplan)** | ✅ **核心** | 决定 macro 位置和芯片利用率（70%/75%/80%/85%/90%）。Macro Region 特征在此阶段提取。这一阶段引入 macro placement 和利用率变化，是设计空间多样性的主要来源之一 |
| **⑧ 标准单元摆放 (Placement)** | ✅ **核心** | 将标准单元摆放到位。Cell Density、RUDY（布线需求估计）、Pin Configuration 等特征在此阶段提取——这些是拥塞和 DRC 预测的输入特征。RUDY 通过在 placement 阶段估计每个 tile 的布线需求，绕过耗时的全局布线来预判拥塞热点 |
| ⑨ 时钟树综合 (CTS) | ✅ | Power mesh 设置在此阶段前的 powerplan 中已完成。IR drop 预测用到的静态/动态功耗特征在前几阶段和后阶段都可提取 |
| **⑩ 布线 (Routing)** | ✅ **核心** | 全局布线和详细布线分别产生 Congestion（全局布线 overflow）和 DRC Violations（详细布线违规）标签。**这些标签在布线完成后才能获得，预测任务的目标是用 placement 阶段的特征来预测布线后的结果——这就是"跨阶段预测"的含义** |
| ⑪ 后仿真 | ❌ | — |
| **⑫ 物理验证 (DRC)** | ✅ **核心** | DRC Violation Prediction 任务直接从这里取标签——详细布线产生的 DRC 违规报告被栅格化为 hotspot map |
| **⑬ 签核 (Signoff) -- IR Drop** | ✅ **核心** | IR-drop 标签来自电源分析工具（如 Voltus/RedHawk）对最终版图的压降仿真。静态功耗和 20 个时间片的动态功耗作为输入特征，IR-drop hotspot map 作为预测标签 |
| ⑭-⑰ 流片→制造→封装测试→芯片 | ❌ | — |

**覆盖率：6/17。** CircuitNet 1.0 覆盖了从逻辑综合（③）到签核（⑬）中与 routability/DRC/IR-drop 相关的阶段。它的核心定位是「物理设计阶段的跨阶段预测代理人」——用早期阶段（placement 之后）可获得的特征去预测晚期阶段（routing 和 signoff 之后）才能得到的质量指标。

> **关键边界澄清**：CircuitNet 1.0 的所有预测模型都是 **signoff 之前的代理模型**，不是 signoff 工具。GPDL 预测拥塞热图，不能替代 Cadence Innovus 的全局布线器；RouteNet 预测 DRC 风险，不能替代 Mentor Calibre 的 DRC deck；MAVI 预测 IR-drop 图，不能替代 Voltus/RedHawk 的电源网签核求解。模型的价值在于「快速筛出可能出问题的区域，减少完整的 signoff 迭代次数」，而不是「取代 signoff」。

---

## 3. 输入 / 输出

### 3.1 数据生成流水线

CircuitNet 1.0 的数据不是"拍一次照片"，而是对每个设计跑完整的后端 flow：

```text
RISC-V RTL (PULPino)
    │
    ▼
③ 逻辑综合 (Synopsys Design Compiler, 28nm)
    │  频率: 50 / 200 / 500 MHz
    │  输出: 门级网表 (.v)
    ▼
⑦ Floorplan (Cadence Innovus)
    │  Macro Setting: 3 or 8 macros
    │  Utilization: 70% / 75% / 80% / 85% / 90%
    │  输出: macro 位置, 芯片面积
    ▼
⑧ Placement (Cadence Innovus)
    │  输出: 标准单元坐标, cell density, RUDY, pin RUDY
    ▼
Powerplan + CTS
    │  Power Mesh: 13 / 14 / 15 种配置
    ▼
⑩ Routing (Cadence Innovus)
    │  Global Routing → 拥塞 overflow map
    │  Detailed Routing → DRC violation map
    ▼
⑬ Analysis
    │  IR Drop 分析 → IR-drop hotspot map
    ▼
特征提取 → 栅格化 / 建图 → 训练样本
```

每个设计有 3（频率）× 5（利用率）× 3（macro setting）× 3（power mesh，通过 13/14/15 实现）× 2（a/b 变体）× 2（filler insertion before/after routing）= 2160 种参数组合。6 个设计 × 2160 = 12,960 次 flow run，排除失败后得到 10,242 个有效 layout。

### 3.2 输入特征（以拥塞预测为例）

**图像式特征**——把版图划分为等距网格（tile），每个 tile 统计物理属性，构成多通道二维特征图：

```text
输入样本形状: [C=3, H=256, W=256]

通道 0: Macro Region [256,256]
  ┌────────────────────────────┐
  │ · · · · · · · · · · · · · │  · = 0 (无 macro)
  │ · · · · · · · · · · · · · │
  │ · · ■ ■ ■ · · · · · · · · │  ■ = 1 (macro 覆盖区域)
  │ · · ■ ■ ■ · · · · · · · · │
  │ · · ■ ■ ■ · · · · · · · · │  三个 macro 放在芯片底部偏左
  │ · · · · · · · · · · · · · │
  └────────────────────────────┘

通道 1: RUDY (Rectangular Uniform wire DensitY) [256,256]
  ┌────────────────────────────┐
  │ 0.1 0.1 0.2 0.3 0.2 0.1 ·│  每个 tile 的布线需求估计值
  │ 0.2 0.3 0.5 0.6 0.4 0.2 ·│  (由网表中 net 的 bounding box
  │ 0.3 0.5 0.8 0.9 0.6 0.3 ·│   计算得到的密度分布)
  │ 0.2 0.4 0.6 0.5 0.3 0.2 ·│
  └────────────────────────────┘

通道 2: Pin RUDY [256,256]
  ┌────────────────────────────┐
  │ 0.05 0.10 0.15 0.20 0.12 ·│  每个 tile 的 pin 密度估计
  │ 0.10 0.20 0.30 0.35 0.25 ·│  (与 RUDY 类似但仅考虑 pin
  └────────────────────────────┘
```

**图结构特征**——从网表构建图：

```text
图 G = (V_cells ∪ V_nets, E)

V_cells: 标准单元 + macro + IO
  - 每个 cell 有属性: {type, width, height, position(x,y)}
  - RISCY-a 设计: 44,836 个 cell 节点

V_nets: 线网（net）
  - 每个 net 连接多个 cell 的 pin
  - RISCY-a 设计: 80,287 个 net 节点

E: 超边（hyperedge）
  - cell → net: 单元驱动/接收该线网
  - 本质是超图 H(V, E)，其中 |E| 可达 |V| 量级
```

### 3.3 输出标签

| 任务 | 标签格式 | 含义 | 来源 |
|------|---------|------|------|
| Congestion | `[256, 256]` overflow map | 每个 grid cell 的布线溢出量 | 全局布线报告 |
| DRC Violation | `[256, 256]` hotspot map | 每个 grid cell 的 DRC 违规次数 | 详细布线 DRC 报告 |
| IR Drop | `[256, 256]` IR-drop map | 每个 grid cell 的最大压降值 | 电源分析工具 |

所有标签都是 **物理设计流程跑完后才能获得的真实数据**。预测任务的价值在于用流程早期（placement 阶段之后）就能提取的特征来预判这些晚期结果，从而避免浪费时间在注定会出问题的 layout 上继续跑后续阶段。

---

## 4. 方法与架构

### 4.1 为什么 CircuitNet 是 Representation Learning 论文

CircuitNet 1.0 虽然不是一篇提出新 GNN 架构的论文，但它的核心问题本质上是一个 **表示学习问题**：如何从 placement 后的版图状态中提取出足够好的特征表示，使得模型能预测 routing 和 signoff 后的物理质量？这需要：

1. **图表示学习**：从门级网表的拓扑结构中学习 cell/net 的嵌入表示。一个 cell 的"物理行为"（比如它周围会不会拥塞）不仅取决于它自己的属性（大小、类型），还取决于它和哪些 cell 通过 net 相连、它的 fan-in/fan-out 拓扑位置、它在 clock tree 中处于什么层级。
2. **图像表示学习**：从栅格化的版图特征中学习空间上下文。拥塞是局部和全局布线资源竞争的结果——一个 tile 的拥塞程度不仅由该 tile 内的 cell/RUDY 决定，还受周围 tiles 的布线资源占用影响。

### 4.2 整体 Pipeline

```text
┌─────────────────────────────────────────────────────────────┐
│         CircuitNet 1.0 跨阶段预测 Pipeline                    │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  综合后网表 (.v) + 版图 (LEF/DEF) + 工具报告                  │
│         │                                                   │
│         ├─── 栅格化路径 (Image-based) ────┐                  │
│         │   ① 版图划分为 N×N grid        │                  │
│         │   ② 每 grid 统计:               │                  │
│         │     macro_region(RUDYpin_RUDY   │                 │
│         │   ③ resize → [C,H,W] 张量       │                  │
│         │                                 ▼                  │
│         │                          CNN Encoder-Decoder      │
│         │                          (FCN / U-Net)            │
│         │                                 │                  │
│         │                                 ▼                  │
│         │                          预测热图 [H,W]            │
│         │                                                   │
│         └─── 建图路径 (Graph-based) ──────┐                  │
│             ① 网表解析: cells→nodes,      │                  │
│                nets→hyperedges             │                  │
│             ② 节点特征: cell type, area,   │                  │
│                position, pin location      │                  │
│             ③ 边特征: net bounding box,    │                  │
│                fan-out degree              │                  │
│                                 ▼          │                  │
│                          GNN (消息传递)     │                  │
│                                 │          │                  │
│                                 ▼          │                  │
│                          节点级/边级预测     │                  │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### 4.3 Baseline 模型详解

CircuitNet 1.0 为三个任务各提供了一个 baseline 模型，用来验证数据集的有效性。这些 baseline 均来自当时已有的发表方法，不是 CircuitNet 自己提出的新架构。

#### 4.3.1 GPDL -- 拥塞预测 (Congestion Prediction)

GPDL 的名称来自 DATE 2021 论文 "Global Placement with Deep Learning-Enabled Explicit Routability Optimization"，在 CircuitNet 中作为拥塞预测的 baseline。

**模型类型**：轻量 U-Net 风格 encoder-decoder CNN，约 119,169 个参数。

```text
Encoder:
  [B, 3, 256, 256]
    → 3×3 Conv(3→32) + InstanceNorm + LeakyReLU   # 重复 2 次
    → [B, 32, 256, 256]
    → MaxPool 2×2
    → [B, 32, 128, 128]
    → 3×3 Conv(32→64) + InstanceNorm + LeakyReLU   # 重复 2 次
    → [B, 64, 128, 128]
    → MaxPool 2×2
    → [B, 64, 64, 64]

Bottleneck:
    → 3×3 Conv(64→32) + Tanh
    → [B, 32, 64, 64]
    → 3×3 Conv(32→32) + Tanh                   # 重复 2 次
    → [B, 32, 64, 64]

Decoder:
    → ConvTranspose2d(32→16, stride=2)
    → [B, 16, 128, 128]
    → 拼接 Encoder 的 [B, 32, 128, 128] skip feature
    → [B, 48, 128, 128]
    → 3×3 Conv(48→16)
    → 3×3 Conv(16→16)
    → ConvTranspose2d(16→4, stride=2)
    → [B, 4, 256, 256]
    → 3×3 Conv(4→1) + Sigmoid
    → [B, 1, 256, 256]
```

**为什么用 InstanceNorm 而非 BatchNorm**：拥塞预测是逐样本的密度估计问题，不同 design 的 cell 密度和布线需求分布差异很大。InstanceNorm 在 H×W 维度上做归一化，每个样本独立，避免了 BatchNorm 跨样本统计量被不同 design 的分布差异污染。

**Skip Connection 的作用**：MaxPool 后空间分辨率从 256→128→64，热图中宽度 1~2 个 tile 的拥塞热点在瓶颈处分辨率不足。skip connection 把 encoder 浅层的 [B, 32, 128, 128] 空间细节直接送给 decoder，保留高分辨率下的局部密度特征。

#### 4.3.2 RouteNet -- DRC 违规预测 (DRC Violation Prediction)

**模型类型**：与 GPDL 骨架相近的 encoder-decoder CNN，输入通道拓展到 9 通道。

```text
输入 9 通道:
  1. Macro Region          -- macro 占据区域
  2. Cell Density           -- 标准单元密度分布
  3. RUDY (long)           -- 长距离布线需求估计
  4. RUDY (short)          -- 短距离布线需求估计
  5. Pin RUDY              -- pin 密度估计
  6. Early Global Routing H-overflow  -- 早期全局布线水平溢出
  7. Early Global Routing V-overflow  -- 早期全局布线垂直溢出
  8. Global Routing H-overflow        -- 全局布线水平溢出
  9. Global Routing V-overflow        -- 全局布线垂直溢出

归一化: BatchNorm (而非 InstanceNorm)
输出: [B, 1, 256, 256] Sigmoid 风险图 -- 每个像素是 DRC 违规概率
```

**为什么 DRC 用 BatchNorm 而拥塞用 InstanceNorm**：DRC 违规通常是稀疏的二分类问题（hotspot vs 非 hotspot），类别本身的分布特征在不同设计间相对稳定（违规密度低、空间聚类）。BatchNorm 用跨样本的 mini-batch 统计量能提供更稳定的归一化参考。

**为什么 DRC 需要 9 通道输入**：DRC 违规的根因比拥塞更复杂。拥挤可能导致 DRC（间距违规），但 DRC 还涉及 pin accessibility（引脚的物理可达性）、macro 周围的绕线死角（fence region 效应）、不同 metal layer 的 via 堆叠限制等。9 通道中的 early/global routing overflow 捕捉了布线过程的中间状态，提供了比单纯 placement 后特征更强的预测信号。

#### 4.3.3 MAVI -- IR Drop 预测 (IR Drop Prediction)

**模型类型**：3D CNN + 2D U-Net 混合架构，包含物理约束输出层。

```text
输入:
  静态功耗图: [1, H, W]           -- total power at each tile
  动态功耗时序: [T=20, H, W]      -- power sampled at 20 time windows

  → 组合为 4D 张量 [C_static + C_dynamic, T, H, W]

3D CNN Encoder:
  3D 卷积同时沿时间和空间轴编码
  逐级下采样空间维度 (H,W)
  保留时间维到瓶颈

时间聚合:
  对时间维做 pooling/conv → 压缩为 2D feature maps

2D U-Net Decoder:
  上采样恢复至 [256, 256]

物理约束输出层:
  输出 4 个系数图 [4, 256, 256]
  与输入前 4 个功耗分量逐元素相乘并求和
  → [1, 256, 256] IR-drop map
```

**物理约束输出层的设计逻辑**：纯 CNN 的输出是"黑盒"——网路可能学到一个从功耗图到 IR-drop 的映射，但没有任何物理保证。MAVI 的 4 系数乘法结构强制输出与输入功耗特征保持线性叠加关系——每个 tile 的 IR-drop 必须是其功耗分量的加权和。这符合 IR-drop 的物理本质：压降 = 电流 × 电阻，电阻由电源网络拓扑决定（是空间上缓变的），电流由各 tile 功耗决定（是空间上快变的局部量）。

### 4.4 图表示学习路径——从网表到 GNN 输入

虽然 CircuitNet 1.0 论文给的 baseline 都是 CNN（图像式特征），但数据中包含了完整的门级网表和 placement 信息，天然适合 GNN。以下是图表示学习路径的形式化描述。

**图的构建流程**：

```text
门级网表 (.v):
  module top (...);
    XOR2X1 u_and1 (.A(a), .B(b), .Y(n1));
    DFFRX1 u_ff1 (.D(n1), .CK(clk), .Q(q1));
    ...
  endmodule

Placement 报告:
  u_and1:  (x=123.45, y=67.89, orient=N)
  u_ff1:   (x=130.12, y=68.01, orient=N)
  ...

         ↓ 解析
┌──────────────────────────────────────┐
│  异构图 G = (V_cell ∪ V_net, E)       │
│                                      │
│  V_cell 节点:                         │
│    u_and1: {type="XOR2X1",            │
│             area=2.5,                 │
│             pos=(123.45, 67.89)}     │
│    u_ff1:  {type="DFFRX1",           │
│             area=4.8,                 │
│             pos=(130.12, 68.01)}     │
│                                      │
│  V_net 节点:                          │
│    n1: {fanout=2,                    │
│          bounding_box=(110,60,140,80)}│
│                                      │
│  E (超边):                            │
│    u_and1 → n1  (驱动)               │
│    n1 → u_ff1   (扇出)               │
└──────────────────────────────────────┘
```

---

## 5. 关键公式

CircuitNet 1.0 论文是短文体（2 页 News & Views），没有编号公式。以下公式是对其预测任务和评估体系的形式化，基于论文描述和物理设计概念。

### 5.1 栅格化特征提取

将连续版图坐标离散化为 $N \times N$ 网格（论文中 $N=256$）：

$$
F_{k}[i, j] = \sum_{c \in \text{cells}} \mathbb{1}\left[ \text{tile}(c) = (i, j) \right] \cdot \phi_k(c)
$$

- $F_k[i,j]$：第 $k$ 个特征通道在 grid cell $(i,j)$ 处的值
- $\text{tile}(c)$：cell $c$ 的中心坐标所在的 grid cell 索引
- $\phi_k(c)$：cell $c$ 对第 $k$ 个特征的贡献值
- $\mathbb{1}[\cdot]$：指示函数

**工程直觉**：这个公式做的事就是把几万个 cell 的位置和属性"投影"到一个 $256 \times 256$ 的网格上。$\phi_k(c)$ 对 macro region 就是 1（有/无 macro），对 cell density 就是 1（计数），对 RUDY 就是该 cell 的布线需求估计。

### 5.2 RUDY 布线需求估计

给定一个 net 的 bounding box $(x_{\min}, y_{\min}, x_{\max}, y_{\max})$：

$$
\text{RUDY}(i, j) = \sum_{n \in \text{nets}} \frac{w_n \cdot h_n}{(x_{\max}^{(n)} - x_{\min}^{(n)}) \cdot (y_{\max}^{(n)} - y_{\min}^{(n)})}
$$

- $n$：遍历所有 net
- $w_n, h_n$：net $n$ 在 grid cell $(i,j)$ 上的宽度和高度贡献
- $x_{\min}^{(n)}, y_{\min}^{(n)}, x_{\max}^{(n)}, y_{\max}^{(n)}$：net $n$ 的 bounding box 坐标

**工程直觉**：RUDY 的物理假设是——如果 net $n$ 的两个 pin 分别位于 $A$ 和 $B$，那么布线器大概会在 $A$ 到 $B$ 的矩形区域内（bounding box）走线，该区域的布线需求均匀分摊。这当然不是全局布线器的真实行为（真实布线会绕开拥塞区域），但作为 placement 阶段的快速估计，RUDY 的计算量极小（只遍历网表，不做实际布线）且与最终拥塞有统计相关性。

### 5.3 图像式预测的损失函数

拥塞预测使用像素级回归损失：

$$
\mathcal{L}_{\text{cong}} = \frac{1}{N^2} \sum_{i=1}^{N} \sum_{j=1}^{N} (Y[i,j] - \hat{Y}[i,j])^2
$$

- $Y[i,j]$：全局布线后的真实拥塞 overflow 值
- $\hat{Y}[i,j]$：模型预测的拥塞值
- $N$：网格分辨率（256）

DRC 违规预测使用像素级二分类交叉熵（类别极不平衡）：

$$
\mathcal{L}_{\text{DRC}} = -\frac{1}{N^2} \sum_{i,j} \left[ w_1 \cdot Y[i,j] \log \hat{Y}[i,j] + w_0 \cdot (1 - Y[i,j]) \log(1 - \hat{Y}[i,j]) \right]
$$

- $w_1$：正样本权重（远大于 $w_0$，因为 DRC hotspot 像素占比通常 < 1%）
- $Y[i,j] \in \{0, 1\}$：该 grid cell 是否有 DRC 违规
- $\hat{Y}[i,j] \in [0, 1]$：预测的违规概率

IR-drop 预测使用 L1 损失（对异常值更鲁棒）：

$$
\mathcal{L}_{\text{IR}} = \frac{1}{N^2} \sum_{i,j} |Y[i,j] - \hat{Y}[i,j]|
$$

- $Y[i,j]$：真实 IR-drop 值（每 grid cell 的最大压降，单位 mV）
- $\hat{Y}[i,j]$：预测的 IR-drop 值

### 5.4 评估指标

**NRMSE（归一化均方根误差）**——拥塞预测的主指标：

$$
\text{NRMSE} = \frac{\sqrt{\frac{1}{N^2} \sum_{i,j} (Y[i,j] - \hat{Y}[i,j])^2}}{\max(Y) - \min(Y)}
$$

- $\max(Y) - \min(Y)$：标签的动态范围，用于归一化

**SSIM（结构相似度）**——拥塞预测的结构指标：

$$
\text{SSIM}(Y, \hat{Y}) = \frac{(2\mu_Y \mu_{\hat{Y}} + C_1)(2\sigma_{Y\hat{Y}} + C_2)}{(\mu_Y^2 + \mu_{\hat{Y}}^2 + C_1)(\sigma_Y^2 + \sigma_{\hat{Y}}^2 + C_2)}
$$

- $\mu_Y, \mu_{\hat{Y}}$：真实值和预测值的均值
- $\sigma_Y^2, \sigma_{\hat{Y}}^2$：方差
- $\sigma_{Y\hat{Y}}$：协方差
- $C_1, C_2$：稳定常数，防止分母为零

**为什么需要两个指标互补**：NRMSE 测量像素级数值误差，但可能把预测完全抹平的低 NRMSE 热图评为"好"——每个像素都接近均值，NRMSE 确实低，但热点全丢了。SSIM 测量空间结构的保持程度，惩罚把热点抹平的平滑预测，但不关心绝对数值。两者并报才能判断模型是否同时做到了"数值对"和"热点在正确的位置"。

**ROC-AUC 和 PR-AUC**——DRC/IR-drop 的 hotspot 检测指标：

DRC 和 IR-drop 是严重的类别不平衡问题（正例 hotspot 占比 < 1%），accuracy 会严重误导——模型只要全预测 0（无违规），accuracy > 99%，但没有检出任何问题。

$$
\text{TPR} = \frac{\text{TP}}{\text{TP} + \text{FN}}, \quad \text{FPR} = \frac{\text{FP}}{\text{FP} + \text{TN}}
$$

- $\text{TP}$（True Positive）：正确识别出的 hotspot 数
- $\text{FN}$（False Negative）：漏检的 hotspot 数
- $\text{FP}$（False Positive）：误报的非 hotspot 数
- $\text{TN}$（True Negative）：正确识别出的非 hotspot 数

ROC 曲线绘制 TPR vs FPR 在不同阈值下的轨迹，AUC（Area Under Curve）越接近 1 说明模型在不同操作点下整体表现越好。PR 曲线绘制 Precision vs Recall，在正例极少（high class imbalance）时比 ROC 更敏感——ROC-AUC 可能高达 0.95 但 PR-AUC 只有 0.63，这是因为 ROC 中的 TN（正确识别的非 hotspot，数量庞大）会稀释 FPR 的变化。

---

## 6. 训练与实验设置

### 6.1 是否需要训练

**是，需要训练。** CircuitNet 1.0 提供的 baseline 模型（FCN / U-Net）都需要在数据集上训练。也可以直接下载官方预训练 checkpoint 做推理。

- **训练类型**：监督学习（像素级回归 / 二分类）
- **框架**：PyTorch
- **数据要求**：下载 N28 数据包（约 10,242 个 layout 的特征和标签）
- **数据划分**：按 design 划分 train/test（不能按 tile 随机划分——同一 design 的不同 tile 有强相关性，随机划分会导致严重泄漏）

### 6.2 实验设置

**Benchmark**：CircuitNet 1.0 自己的 N28 数据集，含 6 个 RISC-V 设计的 10,242 个 layout。

**Baseline 方法**：
- Congestion：FCN-based 方法（源自 DATE 2021 Liu et al.）
- DRC Violation：FCN-based 方法（源自 ICCAD 2018 Xie et al. "RouteNet"）
- IR Drop：U-Net-based 方法（源自 DATE 2021 Chhabria et al. "MAVIREC"）

**数据划分**：论文采用 design-level split——把 6 个设计分成训练集和测试集（例如 5 个训练、1 个测试），不允许同一设计的 layout 同时出现在训练和测试中。这种划分模拟了真实场景：你在一批已知设计上训练模型，然后部署到全新设计上预测。

### 6.3 关键实验结果

| 任务 | 方法 | NRMSE | SSIM | ROC-AUC | PR-AUC |
|------|------|------:|------:|------:|------:|
| Congestion | FCN-based | **0.040** | **0.80** | — | — |
| DRC Violation | FCN-based (RouteNet) | — | — | **0.95** | **0.63** |
| IR Drop | U-Net-based (MAVIREC) | — | — | **0.94** | **0.83** |

**这张表说明了什么**：

1. **拥塞预测**（NRMSE=0.040, SSIM=0.80）：FCN 能从 placement 阶段的 macro region + RUDY + pin RUDY 三通道特征中较好地预测全局布线后的拥塞分布。NRMSE=0.040 意味着预测误差约为标签动态范围的 4%——对于需要提前识别拥塞热点并调整 floorplan/placement 的场景来说，这个精度足够提供有意义的引导。
2. **DRC 违规预测**（ROC-AUC=0.95, PR-AUC=0.63）：ROC-AUC 很高（模型区分 hotspot 和非 hotspot 的能力强），但 PR-AUC=0.63 暴露出在极低的 prevalence（正例占比 < 1%）下，精确率随召回率迅速下降。PR-AUC=0.63 意味着当模型试图查出 50% 的违规时，其预测结果中只有一部分是真正的违规，其余是误报。
3. **IR-drop 预测**（ROC-AUC=0.94, PR-AUC=0.83）：效果在三个任务中最好——压降热点与功耗分布的物理耦合较强，U-Net 能较好地捕捉这种空间模式。

---

## 7. 创新点

### 创新点 1：首个面向 EDA 机器学习的大规模公开数据集

**已有方法的困境**：在 CircuitNet 之前，几乎所有 ML for EDA（尤其是 physical design 相关的预测任务）的研究都依赖内部私有数据。每篇论文在自己的（未公开的）数据上报告结果，无法跨论文比较、无法复现、无法做公平的消融分析。这导致该领域的进展速度远慢于 CV/NLP——benchmark 是推进研究的基础设施，而 EDA 缺乏这种基础设施。

**CircuitNet 的做法**：
- 用商业 EDA 工具（Synopsys Design Compiler + Cadence Innovus）和真实开源 RTL 设计（PULPino RISC-V）跑完整后端 flow
- 从 flow 的中间产物中提取 ML-ready 特征（栅格化 feature map 和网表图结构）
- 在符合 NDA 要求的前提下公开特征和标签（原始 LEF/DEF 和 PDK 库文件受 NDA 保护，不能公开，但抽取后的数值特征不包含受保护信息）
- 提供 baseline 模型代码和预训练权重，降低新研究者的入门门槛

**为什么这很重要**：一个领域从"各自在私有数据上跑实验"到"有公共 benchmark"的转变，通常标志着该领域从实验科学进入工程科学的阶段。ImageNet 对 CV、GLUE/SuperGLUE 对 NLP 都是这种转折点。CircuitNet 试图扮演 EDA 领域的这个角色。

### 创新点 2：多模态特征覆盖——同时支持图像和图的建模范式

EDA 预测任务天然是多模态的。芯片版图有空间属性（density/RUDY 等图像式特征适合 CNN），同时也有拓扑属性（netlist 连接关系适合 GNN）。CircuitNet 1.0 在数据层面同时提供两种表示，使得研究者可以：
- 用 CNN 捕获空间局部模式（拥塞热点通常表现为高密度区域周围的高 RUDY 值）
- 用 GNN 捕获全局拓扑依赖（某个 cell 的 fan-out 过大可能在整个 netlist 传播时序压力）
- 设计融合模型（CNN branch + GNN branch → 拼接 → 联合预测）

### 创新点 3：Design-level split 的评测规范

CircuitNet 强调按 design 划分 train/test，违反了 ML 中常见的"随机 shuffle 然后 80/20 split"的习惯。但这是故意为之：同一个 chip design 的不同参数变体（比如不同利用率下的同一 RISCY 布局）之间，layout 纹理、cell 分布、netlist 结构都是高度相关的。按 tile 随机分会导致 test set 中的 tile 和 train set 中的 tile 来自几乎相同的版图拓扑——模型只需要学会"记住"该设计的布局模式，就能在 test 上得高分，但完全没有泛化到新设计。

Design-level split 强制模型面对 unseen design——这是真正的跨设计泛化评测，符合工业场景（在新芯片上使用预训练模型的需求）。

---

## 8. EDA 缩写表

| 缩写 | 全称 | 一句话解释 |
|------|------|-----------|
| **EDA** | Electronic Design Automation（电子设计自动化） | 芯片设计全流程的工具链总称 |
| **VLSI** | Very Large Scale Integration（超大规模集成电路） | 单芯片集成百万门以上的集成电路 |
| **CAD** | Computer-Aided Design（计算机辅助设计） | 本文中与 EDA 基本同义，指芯片设计的自动化工具 |
| **RTL** | Register Transfer Level（寄存器传输级） | 用 Verilog/VHDL 描述每个时钟沿寄存器之间的数据流动 |
| **LEF** | Library Exchange Format（库交换格式） | 标准单元的物理抽象视图（尺寸、pin 位置、金属层阻挡） |
| **DEF** | Design Exchange Format（设计交换格式） | 芯片版图的几何描述（cell 位置、net 走线、区域定义） |
| **PDK** | Process Design Kit（工艺设计套件） | 特定工艺节点下制造芯片所需的全部文件（库、规则、模型） |
| **NDA** | Non-Disclosure Agreement（保密协议） | 限制商业 PDK 和 EDA 工具相关数据公开的法律协议 |
| **FCN** | Fully Convolutional Network（全卷积网络） | 不含全连接层的 CNN，适合 dense prediction 任务 |
| **CNN** | Convolutional Neural Network（卷积神经网络） | 以卷积运算为核心的神经网络，适合图像/网格数据 |
| **GNN** | Graph Neural Network（图神经网络） | 在图结构数据上做消息传递的神经网络 |
| **U-Net** | — | encoder-decoder CNN 架构，带 skip connection，广泛用于图像分割 |
| **NRMSE** | Normalized Root Mean Square Error（归一化均方根误差） | 回归误差指标，用标签范围归一化以跨任务比较 |
| **SSIM** | Structural Similarity Index Measure（结构相似度） | 图像质量指标，衡量两张图在亮度、对比度、结构上的相似性 |
| **ROC-AUC** | Receiver Operating Characteristic Area Under Curve（受试者工作特征曲线下面积） | 二分类器在不同阈值下的 TPR vs FPR 综合指标 |
| **PR-AUC** | Precision-Recall Area Under Curve（精确率-召回率曲线下面积） | 类别不平衡时比 ROC-AUC 更敏感的分类器评估指标 |
| **RUDY** | Rectangular Uniform wire DensitY（矩形均匀线网密度） | 在 placement 阶段快速估计每个 tile 的布线需求的启发式方法 |
| **DRC** | Design Rule Check（设计规则检查） | 检查版图几何是否满足制造工艺的物理约束（间距、包围等） |
| **DRV** | Design Rule Violation（设计规则违规） | DRC 检查发现的不满足制造规则的几何结构 |
| **IR Drop** | 电流×电阻压降 | 电源网络上电流流过电阻产生的电压降落，严重时导致门电路失效 |
| **PPA** | Power, Performance and Area（功耗、性能、面积） | 芯片设计的三个核心质量维度 |
| **STA** | Static Timing Analysis（静态时序分析） | 不跑仿真，纯数学枚举所有路径延迟与时钟周期比较 |
| **SDF** | Standard Delay Format（标准延时格式） | 门电路延迟参数的工业标准格式 |
| **SPEF** | Standard Parasitic Exchange Format（标准寄生参数交换格式） | 版图走线的寄生 RC 参数格式 |
| **CTS** | Clock Tree Synthesis（时钟树综合） | 给时钟网络插入缓冲器树，使所有触发器同时收到时钟沿 |
| **GDSII** | Graphic Data System II（版图数据格式） | 芯片版图的最终工业交付格式，发给代工厂制造 |

---

## 9. 与芯片流程的关系

### 9.1 在全流程中的位置

```text
① RTL 设计 (PULPino RISC-V)
       │
       ▼
③ 逻辑综合 (Synopsys DC, 28nm)
       │  输出: 门级网表
       ▼
⑦ Floorplan → ⑧ Placement
       │          │
       │          ├── Cell Density, RUDY, Pin RUDY ──┐
       │          │  (这些是预测模型的输入特征)        │
       ▼          ▼                                    │
⑨ CTS → ⑩ Routing ──────────────────────┐              │
       │  Global Routing → Congestion     │              │
       │  Detailed Routing → DRC          │              │
       ▼                                  ▼              ▼
⑬ Signoff                          ┌──────────────────────┐
    IR Drop Analysis → IR-drop      │  跨阶段预测的训练信号  │
                                    │  用 placement 后的    │
                                    │  特征预测 routing 和  │
                                    │  signoff 后的质量指标 │
                                    └──────────────────────┘
```

CircuitNet 1.0 的预测模型扮演的角色是：在 placement 完成之后、routing 还没开始之前，快速预测该 layout 哪一带会出现拥塞和 DRC 违规、哪一带会产生 IR-drop 热点。这些预测结果可以反馈给 floorplan/placement 阶段的优化工具，以"如果我这样摆 macro、这样设利用率，最终会出什么问题"的方式实现 early feedback，避免跑完整个 flow 才发现不可行。

### 9.2 「agent 预测」和「signoff 核实」之间隔着什么

CircuitNet 1.0 的预测模型是 **proxy model（代理模型）**，不是 signoff 工具。以下几点是代理和真签核之间的鸿沟：

1. **预测分辨率有限**：$256 \times 256$ 的栅格化分辨率对应 28 nm 工艺下约 100 nm per pixel。真实的 DRC 规则要求亚纳米级精度检查（如金属间距 >= 0.032 um）。模型说"这个 100 nm 的 tile 里有风险"，但实际违规可能在该 tile 内的某个 5 nm 级别的局部几何上——模型无法给出精确坐标。

2. **没有物理规则保证**：GPDL/RouteNet 是纯数据驱动的函数逼近器——它们学的是"过去这种 layout 出过问题"的统计关联，而非物理定律。如果训练数据里没有某个特殊的 macro+cell 组合模式，模型的预测不可靠。

3. **IR-drop 的瞬态行为被简化**：MAVI 只取了 20 个时间片——真实芯片的 switching activity 是 GHz 级别的连续动态过程，20 个时间片的采样可能遗漏最差的电压跌落时刻。

4. **不能替代 ECO（Engineering Change Order）**：实际工程中，DRC 违规需要用工具自动修复或手动修正，IR-drop 超标需要加 decap cell（去耦电容）或改动 power mesh——模型只告诉你"哪里可能有问题"，不告诉你怎么修。

---

## 10. 讨论与局限

### 10.1 论文自述的局限

1. **单一工艺节点**：只有 28 nm planar CMOS 数据，不支持跨工艺迁移研究。
2. **设计类型单一**：六个设计全是 CPU（RISC-V 系列），没有 GPU、AI Chip、DSP 等异构设计，限制了跨架构泛化研究的空间。
3. **任务覆盖有限**：没有时序预测（timing/net delay）、没有功耗预测（power estimation），也没有 layout 优化（placement/routing 优化本身）。
4. **数据不可从 RTL 原样重跑**：商业 PDK 和 EDA 工具受 NDA 保护，不能公开原始 LEF/DEF/GDS，用户无法从头重跑完整 flow 来扩展或自定义数据。

### 10.2 代码/复现层面的问题

1. **数据依赖商业工具流程**：虽然公开的特征和标签可以自由使用，但如果想生成新设计的数据（比如自己的 RTL 设计），用户需要自己有商业 EDA 工具和 PDK 的 license。
2. **预训练权重跨代不兼容**：当前 GitHub 仓库同时承载 N28（1.0）、N14（2.0）和 N45（3.0）的数据和权重，不同代际的 checkpoint 和特征格式不完全兼容。
3. **特征通道依赖版本**：拥塞预测的三个输入通道（macro_region, RUDY, RUDY_pin）在不同数据代际可能有不同的归一化参数和网格分辨率，必须按对应版本的文档使用。

### 10.3 本资料包的批判性分析

1. **数据集的"规模"争议**：10,242 个 layout 听起来很多，但它们来自仅 6 个独特设计，每个设计通过参数变化产生了约 1700 个变体。这些变体之间的相关性较高（同一 netlist 结构，不同利用率/频率设置），实际独立信息量显著小于 10,000 个独立设计。对 GNN 来说，6 个 netlist 图结构不能提供足够的图结构多样性。

2. **Baseline 选择偏保守**：论文使用了当时已发表的方法作为 baseline（FCN/RouteNet/MAVIREC），没有和新方法做对比。这意味着"数据集有效"的结论只在这些特定方法上成立，不能保证其他 ML 方法在该数据集上也能学到有价值的模式。

3. **GNN 路径未被充分探索**：尽管数据包含完整的网表图结构，但 1.0 论文的所有 baseline 都是 CNN（图像式特征）。GNN 在这个数据集上的潜力（用图结构捕获拓扑依赖，用图像特征捕获空间模式）直到后续工作（如 Circuit GNN, LHNN）才被探索——这说明 1.0 的数据集设计为图方法留了接口，但论文本身没有吃透这部分价值。

4. **评估的"代理性"未被量化**：论文报告了预测精度（NRMSE/SSIM/AUC），但没有回答最关键的问题——这些预测精度的提升是否真正转化为设计流程的效率提升？如果模型预测"高拥塞区域"的准确率提高 5%，能否减少 floorplan 迭代次数？这种 causal evaluation 是数据集论文最需要但最难做的。

---

## 11. 复现信息

| 项目 | 内容 |
|------|------|
| 论文页 | https://arxiv.org/abs/2208.01040 |
| 代码 | https://github.com/circuitnet/CircuitNet · commit `41ade1d7e913`（已审计） |
| 许可证 | BSD-3-Clause |
| 数据集 | N28 数据包，需从项目网站/Hugging Face 下载，含 10,242 个 layout 的 feature/label |
| 本地状态 | 已归档 + 已验真。官方 checkpoint 严格加载并通过 CPU 前向。`local_pretrained_inference.py` 对 N14 Vortex-small 样本跑通 GPDL 推理 |
| 复现等级 | R1（代码 + 预训练权重已验证；完整训练需 N28 数据和 GPU 训练时间，未从头跑） |
| 主要门槛 | **(1) 数据下载**：N28 数据包约几十 GB，需从项目网站获取；(2) **GPU 训练**：三个 baseline 模型训练约需 1 张 GPU（如 V100）几小时；(3) **特征理解**：需逐通道检查 shape、单位、坐标方向和缺失值，不能只凭文件名猜测通道含义；(4) **Design-level split**：必须按设计划分，不能随机 tile split |

---

## 12. 一分钟复述版

CircuitNet 1.0（Science China Information Sciences, 2022, 北京大学+武汉大学）是首个面向 EDA 机器学习应用的大规模公开数据集。

核心三件事：

1. **数据**：在 28 nm 工艺下对 6 个 RISC-V 设计跑 12,960 次完整商业后端 flow（逻辑综合 + 物理设计），排除失败后保留 10,242 个 layout。每个设计引入 2160 种参数组合（利用率、频率、macro 摆放、power mesh），反映真实后端设计空间的多样性。

2. **特征**：同时提供图像式特征（栅格化 macro region/RUDY/cell density 等 2D feature map）和图结构特征（门级网表 + placement 坐标），支持 CNN 和 GNN 两种建模范式。这种双模态设计覆盖了 EDA 中「空间的」和「拓扑的」两类信息源。

3. **验证**：用三个任务验证数据集有效性——拥塞预测（NRMSE=0.040, SSIM=0.80）、DRC 违规预测（ROC-AUC=0.95, PR-AUC=0.63）、IR-drop 预测（ROC-AUC=0.94, PR-AUC=0.83）。所有 baseline 使用当时已发表方法，证明数据质量支持 ML 模型学到有意义的物理模式。

**边界**：覆盖 6/17 流程阶段（③⑦⑧⑨⑩⑫⑬），28 nm 单一工艺，CPU 单一架构，不含时序预测，所有预测都是 signoff 前的代理模型。最重要的规范是 design-level split——不能用 tile 随机划分，必须按设计区分 train/test，否则泛化结论无效。
