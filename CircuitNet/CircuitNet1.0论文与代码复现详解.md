# CircuitNet 1.0 论文、代码与预训练推理详解

> 论文：*CircuitNet: An Open-Source Dataset for Machine Learning Applications in Electronic Design Automation (EDA)*  
> 原文：[2208.01040_CircuitNet.pdf](./2208.01040_CircuitNet.pdf)  
> 上游：<https://github.com/circuitnet/CircuitNet>；本地 commit `41ade1d7e913`；BSD-3-Clause。  
> 论文、代码与本地推理核验：2026-08-02。  
> 注意：本地仓库已同时承载 N28 1.0、N14 2.0 和 N45/3.0 入口；本文以 1.0 论文任务和当前可运行 baseline 为主。

```text
┌──────────────────────────────────────────────────────────────┐
│ P1 任务定义                                                   │
├──────────────────────────────────────────────────────────────┤
│ Input：芯片物理设计中间产物（LEF/DEF/网表/placement/routing/   │
│ 功耗报告等），经栅格化或建图得到的多通道二维特征图 / DGL 图。  │
├──────────────────────────────────────────────────────────────┤
│ Output：与版图网格对齐的拥塞热图、DRC hotspot 风险图、IR-drop  │
│ 图，或每条 net/arc 的 delay 预测值。                         │
├──────────────────────────────────────────────────────────────┤
│ Supervision：真实物理设计流程产出的全局布线 overflow、DRC 报告、 │
│ 电源网压降仿真、STA 网延迟等标签。                           │
├──────────────────────────────────────────────────────────────┤
│ Why-hard：跨工艺节点/跨设计的 domain shift 大；真实 EDA 数据获取 │
│ 与预处理门槛高；多种物理效应耦合；预测结果必须与版图网格严格对齐； │
│ 模型只是代理，不能替代 signoff 工具。                         │
└──────────────────────────────────────────────────────────────┘
```

## 定位

CircuitNet 首先是一个**芯片物理设计机器学习数据集与 baseline 集合**，不是单一模型。它覆盖布局布线阶段的拥塞、DRC hotspot、IR drop、时序/网延迟等预测任务。

```text
综合网表 + LEF/DEF + placement/routing/电源信息
    ↓ 特征抽取、栅格化或建图
CNN/GNN baseline
    ↓
拥塞图 / DRC 风险图 / IR-drop 图 / net-delay 数值
```

EDA 位置：综合之后、详细布局布线和 signoff 之前/之中，用快速代理预测帮助早期优化。预测结果不是 signoff 结论。

## 是否需要训练

- 复现论文模型：需要训练，或下载任务对应的预训练权重直接测试。
- 只研究数据处理/特征：不需要训练。
- 不需要 LLM、付费 API；主要依赖 PyTorch，网延迟任务另用 DGL。

当前数据代际：N28、N14，以及 README 于 2026-05 标出的 N45/CircuitNet 3.0。不同版本的 PDK、字段和修复说明不能混用。

## 数据来源、格式与例子

![CircuitNet 1.0 论文第 2 页：设计规模、综合变化和物理设计参数](./figures/circuitnet1-paper-dataset-table.png)

数据来自真实物理设计流程的脱敏 LEF/DEF、网表、placement/routing 和工具报告，再抽取为栅格或图特征。大数据不在 git 仓库内，需要从项目页/Hugging Face 等入口按版本下载。

典型任务格式：

- 栅格任务：多个 `.npy` feature map + 同网格 label map，形状通常为 `[H, W]` 或 `[C, H, W]`；
- 网延迟：node、net edge、pin position 等表/数组，转换成 DGL graph；
- raw design：LEF、DEF、netlist 和 graph information；
- split：`files/train_N14.csv`、`test_N14.csv` 等按设计列出样本。

本地真实例子 `build_graph_demo/instance_placement_gcell/*.npy` 是 NumPy 0-D object array，解包后为：

```python
{
  "clk_rst_gen_i/PLL_i": [13, 164, 94, 245],
  "core_region_i/instr_mem/sp_ram_wrap_i/sp_ram_bank_i": [13, 13, 121, 76]
}
```

即 instance 名映射到 placement/gcell 边界坐标。栅格训练数据的实际通道名称应按对应版本下载说明和 `datasets/` loader 核对，不能只凭文件名猜测。

## 输入与输出例子

以拥塞预测为例：

```text
输入：宏/标准单元密度、RUDY/布线需求、pin density 等多通道二维图
模型：CNN/U-Net 类网络
输出：与版图网格对齐的 congestion heatmap
评测：NRMS、SSIM、hotspot/overflow 相关指标
```

以 net delay 为例：

```text
输入：cell/net 图 + pin position + timing/物理特征
模型：DGL GNN
输出：每条 net/arc 的 delay 预测
```

## 模型结构：CircuitNet 不是一个网络，而是三类 baseline

### GPDL：拥塞热图

本次实跑的是 GPDL。它是一个很小的 U-Net 风格 encoder-decoder CNN，共 119,169 个参数：

```text
[B,3,256,256]
→ 两次 3×3 Conv(3→32) + InstanceNorm + LeakyReLU
→ MaxPool：256→128
→ 两次 Conv(32→64)
→ MaxPool：128→64
→ Conv(64→32) + Tanh                    # 瓶颈
→ 两次 Conv(32→32)
→ 转置卷积：64→128，通道 32→16
→ 两次 Conv(16→16)
→ 与 encoder 的 128×128、32 通道 skip feature 拼接
→ 转置卷积：128→256，48→4
→ 3×3 Conv(4→1) + Sigmoid
→ [B,1,256,256] 拥塞图
```

三个输入通道不是 RGB，而是：macro region、RUDY 布线需求、RUDY pin 需求。skip connection 把较浅层的空间细节直接送到 decoder，避免下采样后丢失热点边界。

### RouteNet：DRC hotspot

RouteNet 的 encoder-decoder 骨架与 GPDL 相近，但输入是 9 通道：macro、cell density、长/短 RUDY、pin RUDY、early/global routing 的水平/垂直 overflow 等。归一化层主要用 BatchNorm，输出 1 通道 Sigmoid 风险图。它预测“哪里可能有 DRC 风险”，不执行几何规则 deck，所以不能代替真实 DRC。

### MAVI：IR drop

MAVI 把静态功耗图和 20 个时间片功耗图组织成 3D 张量。encoder 用 3D convolution 同时看时间/空间，逐级下采样空间；decoder 对时间维聚合后用 2D U-Net 恢复 256×256。最后 4 个输出系数与输入前 4 个功耗分量逐点相乘并求和，得到 IR-drop map。这个物理乘法结构让输出与功耗特征直接关联，但仍是代理模型，不是电源网签核求解器。

## 本机预训练推理（2026-07-21）

### 下载的官方 checkpoint

| 文件 | 大小 | SHA-256 |
|---|---:|---|
| `weights/congestion.pth` | 494 kB | `6dfca5fd448b8d7f236d8c043ffee40913b1bb2082a42838ed624d987973a774` |
| `weights/DRC.pth` | 512 kB | `aa76f9d67f4fa3128c5de08413711ccad6c3c7cdc99fb0e71c8f46ec441eb2cd` |
| `weights/IR_drop.pth` | 68.3 MB | `31d65dc133f21e0f523b04f46a2889fe34ebbc98b256f40318c57676cbad3fd7` |

三个文件均来自上游 README 指向的官方 Google Drive。本次选择 congestion checkpoint 做真实特征前向。

### 真实输入流程

下载官方 N14 `Vortex-small` routability 包，从同一个物理实现样本取出：

```text
macro_region.npz [422,422]
RUDY.npz         [422,422]
RUDY_pin.npz     [422,422]
       ↓ cubic resize + 各通道 min-max
model input      [1,3,256,256]
       ↓ GPDL + congestion.pth
prediction       [1,1,256,256]
```

真实 label 是 global-routing 水平与垂直 overflow 相加、resize、归一化得到的 `[256,256]` 图。CPU 4 threads 前向约 0.824 s；checkpoint 严格加载无 missing/unexpected key。

复现命令：

```bash
python local_pretrained_inference.py \
  --sample-root data_samples/extracted/Vortex-small \
  --sample-name Vortex-small_freq_500_mp_1_fpu_60_fpa_1.0_p_4_fi_ap.npz \
  --checkpoint weights/congestion.pth \
  --output-dir runs/pretrained_congestion_vortex_small
```

记录：`runs/pretrained_congestion_vortex_small/record.json`，输入、label、输出 `.npy` 均保留。

### 指标应怎样解释

该次 MAE 约 0.0801、RMSE 约 0.0860，但**不能拿来宣称复现论文精度**：公开 checkpoint 来自原始发布，输入样本来自 N14，工艺/数据代际可能不匹配。这次实验的结论是“官方权重能严格加载，真实物理特征预处理和前向已跑通”，不是跨节点精度结论。正式评测必须下载与 checkpoint 同代的数据和官方 test split。

## 项目创新

1. 同时开放面向多种物理设计预测任务的数据、特征和 baseline。
2. 强调真实设计流程、跨设计划分和 EDA 专用评价，而非只在人工小图上训练。
3. 后续版本扩展工艺节点、时序/图特征和 raw LEF/DEF，支持自定义特征提取。
4. 使拥塞、DRC、IR drop 等过去依赖私有数据的研究更可复现。

## 复现建议

先选择一个任务和一个数据版本，不要一次下载所有数据：

1. 下载 1—2 个 design 的 feature/label；
2. 逐通道检查 shape、单位、坐标方向和缺失值；
3. 使用官方 design-level train/test CSV；
4. 跑官方 test + pretrained；
5. 再训练小 baseline；
6. 保存数据版本、PDK、工具 commit、split 和归一化参数。

严禁把同一 design 的不同 tile 随机分到 train/test，这会产生严重泄漏。

## 是否拥挤、是否值得进入

传统“对固定 CircuitNet split 跑 U-Net、MAE 小幅下降”已经很卷。仍然值得进入的方向是：跨 PDK/跨设计 domain shift、不确定性与失效检测、物理约束模型、早期阶段可用特征、增量训练、与 OpenROAD 闭环验证，以及对预测误差是否真正改善 PPA/DRC 的因果评估。

对入门者，CircuitNet 比直接研究商业 signoff 更适合；对创新论文，必须超越单数据集离线指标。

## 关键文件

### 代码调用链

| 阶段 | 代码位置 | 实际作用 |
|---|---|---|
| 原始报告/LEF 读取 | `feature_extraction/process_data.py`、`src/read.py` | 读取 macro、placement、routing、DRC、power 等报告并栅格化 |
| 压缩包解压 | `routability_ir_drop_prediction/preprocess_scripts/` | 把发布包还原为按 feature/label 组织的 `.npy/.npz` |
| 训练集生成 | `generate_training_set.py` | 按任务组合通道、resize/归一化并输出训练样本 |
| Dataset | `datasets/congestion_dataset.py` 等 | 根据 CSV split 加载 feature 和 label，执行 augmentation |
| 建模 | `models/build_model.py` | `congestion_gpdl`→GPDL、`drc_routenet`→RouteNet、`irdrop_mavi`→MAVI |
| 训练 | `routability_ir_drop_prediction/train.py` | AdamW、task loss、checkpoint |
| 官方测试 | `routability_ir_drop_prediction/test.py` | 加载模型、逐样本预测并计算/保存结果 |
| 网延迟图任务 | `net_delay_prediction/build_graph.py`、`model.py`、`train.py` | graph information→DGL graph→TimingGCN→net delay |
| 本地受控推理 | `local_pretrained_inference.py` | 只加载 GPDL 依赖，严格加载官方 checkpoint，对真实 N14 三通道样本做 CPU 前向 |

本地脚本绕开了 `models/__init__.py` 对 MAVI/MMCV 的无关导入，避免只跑拥塞模型也被商业/旧版依赖阻塞；这是兼容性入口，不改变 GPDL 参数或 checkpoint。

- `README.md`：版本、下载和入口
- `routability_ir_drop_prediction/`：拥塞/DRC/IR drop baseline
- `net_delay_prediction/`：DGL 图任务
- `feature_extraction/`：LEF/DEF 特征抽取
- `build_graph_demo/`：raw graph information 示例
- `LICENSE`：BSD-3-Clause
- `local_pretrained_inference.py`：本地真实特征 + checkpoint 推理
- `weights/`：三个官方 checkpoint
- `runs/pretrained_congestion_vortex_small/`：本次实测证据

## P7 组件一句话总结

| 组件 | 一句话角色 |
|---|---|
| GPDL | 轻量 U-Net 风格 CNN，将密度/RUDY 等三通道栅格特征映射为拥塞热图。 |
| RouteNet | 与 GPDL 骨架相近的 encoder-decoder，把 9 通道布线相关特征转为 DRC hotspot 风险图。 |
| MAVI | 用 3D 卷积编码时间-空间功耗特征，再经 2D U-Net 解码并物理约束求和得到 IR-drop 图。 |
| TimingGCN | 基于 DGL 的图神经网络，把 cell/net 图与 pin position/timing 特征映射为 net delay。 |
| local_pretrained_inference.py | 本地最小化依赖的 GPDL 真实特征 + 官方 checkpoint 推理入口。 |

## 讨论问题

1. 如何在 CircuitNet 的不同任务间共享从 LEF/DEF 抽取的底层特征，同时避免拥塞、IR-drop、DRC 三个任务的数据泄漏？
2. GPDL 的 skip connection 主要保留空间细节，若把 encoder 换成 Vision Transformer 或引入版图几何先验，是否能在保持轻量的同时提升跨设计泛化？
3. CircuitNet 的预测是代理模型而非 signoff 工具，应如何设计因果评估来验证“预测误差降低确实能改善最终 PPA/DRC”？
