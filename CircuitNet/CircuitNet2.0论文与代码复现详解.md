# CircuitNet 2.0 论文、代码与复现边界详解

> 论文：*CircuitNet 2.0: An Advanced Dataset for Promoting Machine Learning Innovations in Realistic Chip Design Environment*  
> 会议：ICLR 2024  
> 原文：[ICLR2024_CircuitNet2.0.pdf](./ICLR2024_CircuitNet2.0.pdf)  
> 官方仓库：<https://github.com/circuitnet/CircuitNet>  
> OpenReview：<https://openreview.net/forum?id=nMFSUjxMIl>  
> 本地 commit：`41ade1d7e913`；BSD-3-Clause；核验日期：2026-08-02。

```text
┌──────────────────────────────────────────────────────────────┐
│ P1 任务定义                                                   │
├──────────────────────────────────────────────────────────────┤
│ Input：14 nm FinFET CPU/GPU/AI Chip 经商业 EDA flow 生成的    │
│ 网表、placement、routing、timing、power 等多模态特征。        │
├──────────────────────────────────────────────────────────────┤
│ Output：routability/DRV、IR-drop、timing 等预测标签，以及跨设计 │
│ /跨工艺泛化评测。                                             │
├──────────────────────────────────────────────────────────────┤
│ Supervision：完整商业 EDA flow 与分析工具产出的 congestion、   │
│ DRV hotspot、IR-drop、STA net delay 等标签。                │
├──────────────────────────────────────────────────────────────┤
│ Why-hard：realistic design space 复杂；CPU/GPU/AI Chip 跨架构 │
│ domain shift 大；类别极不平衡；商业 PDK/库/工具不可公开重跑；  │
│ 必须在数据层面研究泛化而非只在固定 split 上刷指标。           │
└──────────────────────────────────────────────────────────────┘
```

## 1. 一句话定位

CircuitNet 2.0 不是一个新神经网络，而是把 CircuitNet 从 28 nm CPU 数据扩展到更真实的 14 nm FinFET、多架构、多任务和多模态数据环境，重点研究跨设计泛化、类别不平衡和跨工艺迁移。

```text
CPU / GPU / AI Chip RTL
  → 商业综合、floorplan、placement、CTS、routing、分析
  → N14 网表、placement、routing、timing、power 等多模态特征
  → routability / DRV / IR-drop / timing labels
  → CNN/GNN baseline
  → 跨设计与跨工艺泛化评测
```

它是数据与评测基础设施论文；不能把某个 GPDL/MAVIREC/TimingGCN baseline 叫作“CircuitNet 2.0 模型”。

## 2. 与 CircuitNet 1.0 的实质变化

![论文 Figure 2：CircuitNet 1.0 与 2.0 的工艺、设计和任务差异](./figures/circuitnet2-paper-overview.png)

| 维度 | CircuitNet 1.0 | CircuitNet 2.0 |
|---|---|---|
| 工艺 | 28 nm planar CMOS | 14 nm FinFET |
| 设计类型 | 以 CPU 为主 | CPU、GPU、AI Chip |
| 规模 | 原始公开代际 | 超过 10,000 个完整 flow samples |
| 任务 | routability、IR-drop 等 | routability/DRV、IR-drop、timing 等更完整任务 |
| 研究重点 | 建立首个公开数据入口 | realistic design space、cross-design、imbalance、transfer |

论文的“realistic”指数据由完整商业 EDA flow 和先进工艺生成，不表示公开包包含商业 PDK、库和工具，也不表示用户能从 RTL 原样重跑全部 N14 flow。

## 3. 数据由什么组成

![论文 Figure 3 / Table 2：代表设计可视化，以及各任务的 feature/label](./figures/circuitnet2-paper-designs-features.png)

数据模态可按设计阶段理解：

### 3.1 RTL / netlist / graph

- cell、net、pin 及连接；
- pin location、cell type、net属性；
- timing graph 或 net delay 相关特征。

这类数据适合 GNN。`build_graph_demo/graph_information` 真实保存 node/net/pin attribute；`build_graph.py` 将其转为可训练图。

### 3.2 Placement / routing maps

- macro region；
- cell density；
- RUDY / pin RUDY；
- early/global routing overflow/utilization；
- DRC/DRV hotspot。

这些连续坐标经过 tile/grid rasterization，成为 `[C,H,W]` 图像，适合 FCN/U-Net 类模型。

### 3.3 Power / IR-drop

- total/internal/switching power；
- toggle-scaled power；
- 离散时间窗口的 dynamic power；
- IR-drop hotspot map。

动态 power 是空间 × 时间张量，不能和普通 RGB 图一样随意归一化或丢弃时间维。

### 3.4 Timing

论文把 pin/cell/net 连接与物理位置组织成 timing graph，预测 delay。代码对应 `net_delay_prediction/`，模型 `TimingGCN` 由 MLP、NetConv 等模块组成。

## 4. 代码目录怎样落到论文任务

| 论文层 | 当前仓库 | 作用 |
|---|---|---|
| 数据下载/版本 | `README.md`、项目网站 | N28/N14/N45 下载入口和修订通知 |
| feature extraction | `feature_extraction/` | 从 LEF/DEF 和 EDA report 解析、栅格化 |
| routability 数据 | `routability_ir_drop_prediction/datasets/congestion_dataset.py` | 读取 macro/RUDY/pin 等通道及 congestion label |
| DRV/DRC 数据 | `datasets/drc_dataset.py` | 多 routing feature 输入与 hotspot label |
| IR-drop 数据 | `datasets/irdrop_dataset.py` | 组织 static/dynamic power 与 IR-drop |
| 模型选择 | `models/build_model.py` | GPDL、RouteNet、MAVI |
| train/test | `train.py`、`test.py` | loss、optimizer、checkpoint、预测 |
| timing graph | `net_delay_prediction/build_graph.py` | 原始 node/net/pin attribute 转 DGL graph |
| timing model | `net_delay_prediction/model.py` | `TimingGCN` 前向预测 net delay |
| design split | `files/train_N14.csv`、`test_N14.csv` | 按发布配置指定样本 |

注意：GitHub 仓库跨多个数据代际演进。当前 main 上的脚本/权重不一定就是 ICLR 2024 camera-ready 时的逐字版本；复现论文必须记录 commit，不能只写“用了最新代码”。

## 5. 三类 baseline 方法

### 5.1 Congestion / routability

输入 macro region、RUDY、pin RUDY 等多通道网格，FCN/GPDL 预测拥塞图。主要指标：

```text
NRMSE：预测数值误差，越低越好
SSIM：空间结构相似度，越高越好
```

单独优化 NRMSE 可能把热点抹平；只看 SSIM 又可能忽略绝对容量误差，应并报并可增加 hotspot precision/recall。

### 5.2 DRV / DRC hotspot

RouteNet 输入更多 early/global routing 通道，输出 Sigmoid risk map。模型只是风险预测器，最终几何违规必须由真实 rule deck/DRC 工具判定。

### 5.3 IR-drop

MAVIREC/MAVI 类模型融合 static 与 dynamic power，输出 IR-drop 或 hotspot。ROC/AUC 用于不平衡 hotspot 检测，但必须同时检查低 FPR 下 TPR。

## 6. 论文实验一：跨设计泛化

![论文 Table 4 / 5：CPU、GPU、AI Chip 交叉训练测试与 oversampling](./figures/circuitnet2-paper-cross-design-results.png)

论文把 CPU、GPU、AI Chip 分别作为 train group，再测试另两类。例如：

| Train | Test | NRMSE | SSIM |
|---|---|---:|---:|
| CPU | GPU | 0.0805 | 0.6816 |
| CPU | AI Chip | 0.0730 | 0.6735 |
| GPU | CPU | 0.0470 | 0.7939 |
| AI Chip | CPU | 0.0362 | 0.8520 |

这个表的价值不是谁的数字最好，而是显示 domain shift：同一个 CNN 在不同架构间显著掉点。随机 tile split 会把同一 design 的布局纹理泄漏到 test，无法得到这种结论。

## 7. 论文实验二：数据不平衡和 oversampling

GPU/AI Chip 样本量相对不足时，论文对少数 design group oversample。以 GPU train 为例，对 CPU/AI Chip 测试：

- 无 oversampling：CPU 0.0470/0.7939，AI Chip 0.1379/0.6903；
- 有 oversampling：CPU 0.0411/0.8439，AI Chip 0.0471/0.7989。

oversampling 显著改善表中少数 domain，但可能复制同源布局模式。正式研究应比较 weighted sampler、domain-balanced loss、augmentation 和按 source design 去重。

## 8. 论文实验三：跨工艺/跨设计 transfer

论文用 congestion FCN 展示两种 transfer：

1. CircuitNet N28 checkpoint → CircuitNet 2.0 N14；
2. CircuitNet 2.0 → N28/ISPD15 的不同设计。

预训练模型比从头训练更快收敛，但曲线只支持“优化收敛加快”，不自动证明最终 accuracy 或部署鲁棒性全面更高。迁移时还必须处理：

- 不同 PDK 的 cell/metal/routing capacity；
- tile 物理尺寸；
- feature normalization；
- 不同工具版本和约束；
- label 定义变化。

## 9. IR-drop 附录结果

论文 Table B.2：

| 数据集 | FPR（约束 ≤5%） | TPR | Accuracy | AUC |
|---|---:|---:|---:|---:|
| CircuitNet 2.0 | 4.7% | 39.6±1.9% | 95.2±0.1% | 0.8671±0.0032 |
| CircuitNet 1.0 | 4.4% | 29.7±1.2% | 95.4±0.1% | 0.8537±0.0023 |

Accuracy 很高但 TPR 只有 30%–40%，正是类别极不平衡下 accuracy 会误导的例子。组会应重点讲低 FPR 下的检出率，而不是 95% accuracy。

## 10. 本地已有证据

本地保存了一个官方 N14 `Vortex-small` routability 样本包，真实读取：

```text
macro_region [422,422]
RUDY         [422,422]
RUDY_pin     [422,422]
```

本地 `local_pretrained_inference.py` 将其 resize/min-max 后送入 GPDL，严格加载 `weights/congestion.pth` 并完成 CPU 前向，记录在：

- [runs/pretrained_congestion_vortex_small/record.json](./runs/pretrained_congestion_vortex_small/record.json)

但 checkpoint 来源于上游旧版发布，未证明与 N14 样本同代；因此 MAE/RMSE 只用于检查数值链路，不作为 CircuitNet 2.0 论文复现精度。真正复现需要 N14 对应 checkpoint、官方 split 和同版本 preprocess。

## 11. 可复现状态

| 层级 | 状态 | 说明 |
|---|---|---|
| PDF/代码/小样本 | 已完成 | 本地齐全 |
| N14 feature 读取 | 已完成 | Vortex-small 真实 `.npz` |
| CNN checkpoint 前向 | 已完成但跨代 | 严格加载、CPU 推理成功 |
| 论文 N14 congestion test | 未完成 | 缺同代 checkpoint/完整 split |
| cross-design 表格 | 未完成 | 需要 CPU/GPU/AI Chip 训练组和长训练 |
| IR-drop | 未完成 | 旧 MMCV/CUDA 依赖、数据和 68 MB checkpoint 待匹配 |
| timing GNN | 未完成 | 需完整 DGL graph 数据和 GPU 配置 |
| 从 RTL 重建 N14 flow | 不可公开完整复现 | 商业 PDK/库/EDA 环境未公开 |

## 12. 组会分享建议

按“数据代际—任务—代码—证据—边界”讲：

1. N28 CPU 为什么不够；
2. N14 + CPU/GPU/AI Chip + 多模态；
3. raster CNN 与 timing GNN 两条代码路线；
4. cross-design 表格说明 domain shift；
5. 95% accuracy 与 39.6% TPR 说明不平衡指标陷阱；
6. 本地真实 N14 feature + 旧 checkpoint 前向；
7. 为什么这不是论文同代精度复现；
8. 用 CircuitNet 3.0 收束版本演进。

CircuitNet 2.0 最值得继续研究的是跨工艺/跨设计泛化和不确定性，而不是在固定 split 上再换一个 U-Net 小幅刷 NRMSE。

## P7 组件一句话总结

| 组件 | 一句话角色 |
|---|---|
| README.md / 项目网站 | N28/N14/N45 数据下载入口与版本修订说明。 |
| feature_extraction/ | 从 LEF/DEF 和 EDA report 解析并栅格化多模态特征。 |
| congestion_dataset.py / drc_dataset.py / irdrop_dataset.py | 分别组织 routability/DRV/IR-drop 的 feature-label 训练样本。 |
| build_model.py | 根据任务名派发 GPDL、RouteNet、MAVI 三类 baseline 模型。 |
| net_delay_prediction/ | 把 node/net/pin attribute 转为 DGL graph 并用 TimingGCN 预测 net delay。 |
| files/train_N14.csv / test_N14.csv | 按设计指定样本，防止同一 design 的 tile 泄漏到测试集。 |

## 讨论问题

1. CircuitNet 2.0 强调跨设计泛化，但论文中的 oversampling 可能复制同源布局模式，如何设计更严格的 domain-balanced 采样策略？
2. 14 nm FinFET 数据由商业 EDA flow 生成，在无法公开 PDK/库/工具的情况下，社区应如何验证“realistic”结论的可复现性？
3. IR-drop 任务 accuracy 高达 95% 但 TPR 仅约 40%，若要在实际部署中避免漏检，应该优先优化哪些指标和损失函数？
