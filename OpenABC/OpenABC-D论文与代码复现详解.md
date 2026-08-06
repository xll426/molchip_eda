# OpenABC-D 论文、代码、数据生成与复现条件详解

> 论文：**OpenABC-D: A Large-Scale Dataset For Machine Learning Guided Integrated Circuit Synthesis**  
> 作者：Animesh Basak Chowdhury、Benjamin Tan、Ramesh Karri、Siddharth Garg  
> arXiv：2110.11292，2021-10-21  
> 原论文：[2110.11292_OpenABC-D.pdf](./2110.11292_OpenABC-D.pdf)  
> 官方论文页：<https://arxiv.org/abs/2110.11292>  
> 官方 PDF：<https://arxiv.org/pdf/2110.11292>  
> 官方代码：<https://github.com/NYU-MLDA/OpenABC>  
> 完整数据集：<https://ultraviolet.library.nyu.edu/records/mw6q2-a8p15>  
> ML-ready 数据：<https://zenodo.org/record/6399454>  
> 本地代码 commit：`ecd7dde67740556eaf842ccab4dc941c348ad8f6`  
> 本次核验日期：2026-08-02  
> 静态核验记录：[runs/static_audit_20260802.json](./runs/static_audit_20260802.json)

---

```text
┌──────────────────────────────────────────────────────────────┐
│ P1 任务定义                                                   │
├──────────────────────────────────────────────────────────────┤
│ Input：技术无关 AIG 图（node type、incoming inverter count、   │
│ edge index）与 20 维 synthesis recipe 向量（七种操作 ID 序列）。 │
├──────────────────────────────────────────────────────────────┤
│ Output：最终 AIG 节点数 / 技术映射后 area / delay 的归一化 QoR │
│（回归），或 IP 类别（分类）。                                  │
├──────────────────────────────────────────────────────────────┤
│ Supervision：ABC 综合与技术映射后得到的真实节点数、area、delay； │
│ 分类任务使用 IP 名称作为标签。                                │
├──────────────────────────────────────────────────────────────┤
│ Why-hard：recipe 效果高度依赖电路结构；870k 中间 AIG 轨迹生成 │
│ 成本极高；必须防止同一 design/recipe 的多个 step 泄漏到测试集； │
│ 当前公开代码入口存在 bug、路径契约不一致与 unseen-IP 标准化泄漏。│
└──────────────────────────────────────────────────────────────┘
```

## 0. 先给结论

OpenABC-D 最重要的贡献不是提出一个复杂的新 GNN，而是把下面这件事第一次较系统地做成公开数据资产：

> 对一组功能和规模不同的开源硬件 IP，使用大量随机逻辑综合 recipe，保留每一步 AIG，并附上图结构、最终节点数、面积和时延标签。

论文数据主干是：

```text
29 个开源 IP
× 1500 条随机 synthesis recipe
× 每条 20 个变换步骤
= 870,000 个中间/最终 AIG
```

在此基础上，作者定义三个 QoR 回归任务，并给出三组 GCN + recipe-CNN baseline：

- Variant 1：预测未见过的 recipe；
- Variant 2：预测未见过的大 IP；
- Variant 3：预测未见过的 IP–recipe 组合；
- 另有一个 IP 分类任务，用于观察 GCN 学到的 AIG embedding。

这篇论文很值得组会分享，原因有三点：

1. 它把“逻辑综合 recipe 搜索”明确转换成可监督学习的数据问题；
2. 它保留中间 AIG，而不只保留最后一个 PPA 数字；
3. 它给出了跨 recipe、跨 IP、跨组合三种泛化口径，正好能讨论 EDA 数据泄漏与 OOD。

但是，**当前本地仓库不能表述成“OpenABC-D baseline 已跑通”或“论文结果已复现”**。

本地目前有：

- 原论文 PDF；
- 当前代码快照；
- 47 个原始 `.bench`；
- 完整的 1500 条 reference recipe；
- 29 组 RTL synthesis settings；
- 后续扩展的 RTL 与 leaf-level Verilog；
- 数据生成和 baseline 源码。

本地目前没有：

- 1.4 TB 完整数据；
- 约 19 GB ML-ready 数据；
- GraphML；
- PyG `.pt.zip` 样本；
- train/test split CSV；
- `synthesisStatistics.pickle`；
- `synthID2Vec.pickle`；
- 训练 checkpoint；
- OpenABC-D 运行日志或既有模型推理记录。

而且，当前公开源码存在多个会直接影响复现的实现问题：

- 四个训练入口都定义 `--epochs`，却读取不存在的 `args.epoch`；
- README 写 `--batch-size`，代码只接受 `--batch_size`；
- README 示例漏掉必需的 `--target`；
- GraphML→PyG 生产器保存 `.pt.zip`，自己的 Dataset 却查找裸 `.pt`；
- PyG 生产器最后用 `sys.argv[1]` 推导 cleanup 路径，正常调用时得到的是字符串 `--des`；
- embedding 脚本构造了源码中不存在的 `SynthNet_embed`；
- QoR 的 per-design 标准化使用每个设计全部 1500 个真实标签，Variant 2 会读取未见测试 IP 的完整标签分布；
- edge type 被存入数据，但三个 QoR 模型和分类模型均未使用；
- AIG 边在 parser 中按“消费者→fanin”保存，PyG 继续沿该方向做消息传播；
- 训练、评测对 `datadir` 根目录的解释不同；
- 论文、README、requirements 对 PyTorch 和 Nangate 工艺版本的描述不一致。

因此当前最准确的复现判定是：

| 层级 | 当前状态 |
|---|---|
| 原论文 | 已归档，18 页，身份核对完成 |
| 论文方法 | 已逐节梳理 |
| 1500 条 recipe | 本地齐全，ID 0～1499 无缺失 |
| 原始 BENCH | 本地 47 个；论文原始范围是其中 29 个 |
| 数据生成代码 | 已逐文件静态核对 |
| Net1 / Net2 / Net3 | 结构已与论文 Table 3 对应 |
| IP 分类模型 | 结构与训练入口已核对 |
| 完整数据 / ML-ready 数据 | 本地缺失 |
| checkpoint | 本地缺失 |
| 论文数值复现 | 未完成，不能声称完成 |
| 新模型运行 | 本次未执行 |
| 综合等级 | **R1 / C-：方法和代码可审计，数值闭环未建立** |

本次没有重新跑随机初始化模型。

原因很直接：当前缺的是匹配数据、split、标签和 checkpoint；随机前向既不能验证论文 MSE，也不能替代真正复现。

---

## 1. 证据边界

本文使用四类证据，避免把论文数字、代码事实和本地运行混在一起。

| 标记 | 来源 | 能说明什么 |
|---|---|---|
| `[论文]` | 原论文正文、表格、附录 | 作者定义的方法与作者报告结果 |
| `[代码]` | 当前 commit 的源码 | 当前公开实现实际会做什么 |
| `[本地资产]` | 本地文件、数量、哈希 | 文件是否真实存在 |
| `[已有运行]` | 已保存的模型推理或实验记录 | 某条运行路径曾在本地执行成功 |

OpenABC-D 当前没有可用的 `[已有运行]` 证据。

因此：

- 论文的 `0.579 ± 0.02` 只能写成 `[论文] Net3 Variant 1 MSE`；
- 代码里存在 `SynthNet` 只能说明模型定义公开；
- 1500 个 script 齐全不能推出 43,500 次综合已在本机执行；
- 47 个原始 BENCH 不能推出当前仓库自带 870,000 个 AIG；
- 代码静态可读不能推出数据生成闭环可直接执行；
- 没有 checkpoint 时不能把随机初始化输出叫作论文推理。

### 1.1 本次实际完成的核对

- 核对论文标题、作者、日期、页数和 PDF 哈希；
- 提取并检查论文的数据生成图、29 IP 表和模型结构图；
- 阅读 1500 条 reference recipe 的归档结构与首尾样例；
- 阅读四个 automation 脚本；
- 阅读五个 data utility；
- 阅读 Net1、Net2、Net3 的 model/train/evaluate/dataset/utils；
- 阅读 IP 分类模型；
- 阅读 embedding 与 t-SNE 分析入口；
- 统计本地 BENCH、RTL、leaf-level Verilog、数据、权重和日志；
- 对照论文 Table 2、Table 3、Table 5、Table 6；
- 记录会阻断或污染复现的代码问题；
- 形成机器可读审计记录。

### 1.2 本次没有做的事情

- 没有下载 1.4 TB 数据；
- 没有下载约 19 GB ML-ready 包；
- 没有执行 29 × 1500 次 ABC；
- 没有重新生成 870,000 个 AIG；
- 没有训练 80 epoch；
- 没有用随机初始化做伪“推理”；
- 没有改动作者模型源码来制造“跑通”结论；
- 没有复算论文 Table 6。

---

## 2. 论文身份与本地归档

### 2.1 论文信息

| 字段 | 内容 |
|---|---|
| 标题 | OpenABC-D: A Large-Scale Dataset For Machine Learning Guided Integrated Circuit Synthesis |
| 作者 | Animesh Basak Chowdhury、Benjamin Tan、Ramesh Karri、Siddharth Garg |
| arXiv ID | 2110.11292 |
| arXiv 日期 | 2021-10-21 |
| 本地 PDF | `2110.11292_OpenABC-D.pdf` |
| 页数 | 18 |
| 文件大小 | 7,404,178 bytes |
| SHA-256 | `814a3332ef2e87b08f0d485fd6754f643ce5795187996607b749e1a8ce1d7086` |

本地 PDF 正文标题、作者和 arXiv ID 相互匹配。

### 2.2 代码快照

| 字段 | 内容 |
|---|---|
| remote | `https://github.com/NYU-MLDA/OpenABC.git` |
| commit | `ecd7dde67740556eaf842ccab4dc941c348ad8f6` |
| 最近 commit 时间 | 2025-07-23 |
| 最近 commit 内容 | 更新数据下载链接 |
| tracked files | 2,543 |
| tracked Python | 33 个，4,546 行 |
| 当前目录大小 | 约 276 MB |
| LICENSE | BSD 3-Clause |

根目录 `LICENSE` 明确是 BSD 3-Clause。

原来的短版 `模型梳理.md` 把许可证写成 MIT，这是错误的，后文已同步修正。

### 2.3 当前仓库不是 2021 artifact 的静态原样副本

论文发表于 2021，当前 checkout 最近更新于 2025。

当前仓库额外包含：

- 47 个 `_orig.bench`；
- 253 个 `bench_rtl/src` 下的 RTL Verilog；
- 2,020 个跨多种技术的 leaf-level Verilog；
- Nangate45、ASAP7、GF12、GF180、GF55、Intel16/22、Sky130、TSMC65LP 等目录。

这些内容对后续研究有价值，但不能反向写成“2021 论文已经使用 47 个 IP 或多工艺 leaf cell 数据”。

论文主体必须仍按：

```text
29 IP × 1500 recipe × 20 step = 870,000 AIG
```

---

## 3. OpenABC-D 在 EDA 流程中的位置

OpenABC-D 位于 RTL 与技术无关逻辑优化、技术映射之间。

```text
RTL Verilog / VHDL
        ↓
Yosys 前端综合
        ↓
ABC structural hashing
        ↓
初始 AIG
        ↓
20 步 logic synthesis recipe
        ↓
每一步保存 AIG BENCH
        ↓
最终 AIG
        ↓
Nangate45 technology mapping
        ↓
节点数 / depth / area / delay
```

机器学习部分不直接处理原始 RTL token。

它处理的是：

- 初始或中间 AIG 图；
- 20 维 synthesis recipe；
- 最终 QoR 标签。

### 3.1 它不是 placement/routing 数据集

OpenABC-D 的 area/delay 来自逻辑综合后技术映射估计。

它不包含完整物理设计中的：

- placement density；
- congestion map；
- detailed routing；
- IR drop；
- signoff STA；
- 实际布线寄生参数。

因此不能把它的 delay 标签等同于 post-route signoff delay。

### 3.2 它与 CircuitNet 的区别

| 维度 | OpenABC-D | CircuitNet 系列 |
|---|---|---|
| 主要阶段 | 逻辑综合 / AIG | 物理设计 / layout |
| 核心输入 | AIG + recipe | layout feature maps / netlist / physical data |
| 核心标签 | node、depth、mapped area/delay | congestion、DRC、IR drop 等 |
| 优化变量 | synthesis transformation sequence | placement/routing/physical parameters |
| 主要图结构 | logic DAG | netlist / grid / physical graph |

组会中可以把它作为 CircuitNet 之前的“前端逻辑优化数据层”。

---

## 4. 为什么 synthesis recipe 值得学习

逻辑综合不是只执行一次固定 rewrite。

ABC 中同一批基本变换用不同顺序组合，会得到不同结构：

```text
rewrite → balance → refactor
```

与：

```text
refactor → rewrite -z → resub
```

即使每一步保持布尔等价，最终：

- AND 节点数可能不同；
- depth 可能不同；
- logic sharing 可能不同；
- technology mapping 后 area/delay 可能不同。

### 4.1 论文使用的七种操作

| ID | ABC 操作 | 作用 |
|---:|---|---|
| 0 | `refactor` | 用最大 fanout-free cone 的等价函数重构局部逻辑 |
| 1 | `refactor -z` | 允许 zero-cost 变换的 refactor |
| 2 | `rewrite` | 用 cut/template 重写局部 AIG |
| 3 | `rewrite -z` | 允许 zero-cost 变换的 rewrite |
| 4 | `resub` | 用已有节点函数重表达目标节点，增强逻辑共享 |
| 5 | `resub -z` | zero-cost resubstitution |
| 6 | `balance` | 利用结合律/交换律平衡逻辑树，主要减小 depth |

每条 recipe 长度固定为 20。

论文按均匀分布从七个动作中随机采样。

### 4.2 为什么不存在统一最优 recipe

论文比较不同 IP 的 top 1%、5%、10% recipe overlap。

结论是 top recipe 的相似度低于 30%。

这意味着：

- recipe 的效果依赖电路结构；
- 单个固定 script 很难对所有 IP 最优；
- 只在 AES 上调出的 recipe 不应直接当成 JPEG、RISC-V 或总线控制器的最优 recipe；
- 学习模型必须同时看到“电路”和“recipe”。

仅对 recipe 做序列回归，不看 AIG，不足以区分同一 recipe 在不同 IP 上的效果。

仅对 AIG 做图回归，不看 recipe，也无法解释不同序列造成的 QoR 变化。

---

## 5. 论文数据生成总流程

![OpenABC-D 数据生成与学习任务总览](./figures/DatagenerationPipeline.png)

这张图可以拆成四个层级。

### 5.1 层级 A：定性定义任务

作者首先确定数据可以支持的任务：

- synthesis recipe QoR prediction；
- area prediction；
- optimal recipe selection；
- functional classification；
- AIG representation learning。

### 5.2 层级 B：规模化生成数据

```text
开源 RTL IP
   ↓ OpenROAD / Yosys / ABC
初始 AIG BENCH
   ↓ 1500 条 recipe
中间 AIG + 最终 AIG
   ↓ AIG2GraphML
GraphML
   ↓ PyTorch-Geometric preprocessing
PyG 样本
```

### 5.3 层级 C：构造监督信号

每个样本同时关联：

- 图结构；
- 节点和边特征；
- recipe ID 与动作序列；
- 当前 step ID；
- 图级统计；
- 最终 AIG 节点数；
- technology mapping 后 area/delay。

### 5.4 层级 D：模型评测

```text
定义 split
   ↓
构造 GCN + recipe encoder
   ↓
训练 QoR regression
   ↓
用 MSE 和逐 IP scatter/ranking 分析
```

### 5.5 图中数字与正文数字的口径

仓库图中写有 `850,000 Data points` 和 `592,785 compute hours`。

论文正文和摘要的主要口径是：

- 870,000 个 AIG；
- 200,000+ compute hours。

`29 × 1500 × 20` 的算术结果明确是 870,000。

论文附录 Table 5 的数据生成 compute-hours 分项合计：

```text
84,000 + 76,800 + 33,600 + 2,688 + 52,800 = 249,888
```

因此文档采用：

- 样本数：870,000；
- 数据生成计算量：论文称 200,000+，Table 5 分项合计 249,888；
- 不把仓库图中的 850,000 或 592,785 当成正文主结果。

---

## 6. 29 个论文 IP

![论文 Table 1：29 个开源 RTL IP](./figures/OpenSourceBenchmarks.png)

论文的 29 个 IP 覆盖通信、控制、密码、DSP 与处理器。

| 类别 | 设计 |
|---|---|
| 通信 / 总线 | spi、i2c、ss_pcm、usb_phy、sasc、wb_dma、simple_spi、pci、wb_conmax、ethernet |
| 控制器 | ac97_ctrl、mem_ctrl、bp_be、vga_lcd |
| 密码 | des3_area、aes、sha256、aes_xcrypt、aes_secworks |
| DSP | fir、iir、jpeg、idft、dft |
| 处理器 | tv80、tiny_rocket、fpu、picosoc、dynamic_node |

### 6.1 结构跨度

Table 1 中的规模跨度很大：

- `ss_pcm` 只有 462 个节点；
- `dft` 有 245,046 个节点；
- `idft` 有 241,552 个节点；
- `fpu` 的初始 AIG depth 达 819；
- `ethernet` 有 10,731 个 PI 和 10,422 个 PO；
- `dft/idft` 的 PI/PO 都在 3.7 万量级。

这比只用 ISCAS 小电路更接近跨规模泛化问题。

### 6.2 论文名称与代码名称漂移

论文写 `tiny_rocket`，代码多处写 `tinyRocket`。

论文写 `bp_be`，当前 synthesis settings 目录叫 `bp_be_top`。

这类命名差异会影响：

- split CSV 的 `fileName`；
- BENCH 文件路径；
- `desName` 标签；
- statistics pickle 的字典键；
- checkpoint 对应的数据身份。

复现时不能只按肉眼认为“是同一个设计”，必须明确写一个规范化映射表。

---

## 7. 一个 OpenABC-D 样本包含什么

论文 Table 2 给出样本命名：

```text
designIP_synthesisID_stepID.pt
```

例如：

```text
aes_syn149_step15.pt
```

含义是：

- 设计：AES；
- recipe ID：149；
- 当前保存状态：第 15 个优化步骤后。

### 7.1 图结构字段

| 字段 | 内容 |
|---|---|
| connectivity | AIG adjacency / edge index |
| node type | PI、PO、Internal/AND |
| incoming inverter count | 0、1、2 |
| edge type | buffer=0、inverter=1 |

### 7.2 recipe 字段

| 字段 | 内容 |
|---|---|
| synthesis ID | 0～1499 |
| recipe vector | 长度 20，每项 0～6 |
| step ID | 当前中间 AIG 对应第几步 |

### 7.3 individual graph labels

- PI 数；
- PO 数；
- internal AND 数；
- inverted edge 数；
- edge 数；
- longest path / depth；
- IP 名称。

### 7.4 final labels

- 最终 AIG 节点数；
- mapped area；
- mapped delay。

### 7.5 论文任务实际主要使用哪个 AIG

论文的 QoR 问题是：

> 给定 IP 和完整 recipe，预测最终 QoR。

公开训练 CSV 的每个 `fileName` 理论上可以指任意保存状态，但 baseline 的语义需要固定：

- 若输入初始 AIG + 完整 recipe，任务是有意义的前置预测；
- 若输入最终 AIG + 完整 recipe，再预测最终节点数，会有明显 label shortcut；
- 若输入中间 AIG，必须明确 step 与剩余 recipe 的关系。

论文 Figure 5 和任务描述倾向于“IP 的 AIG + 完整 recipe”。

当前本地没有作者 split CSV，无法从文件名实证确认公开 ML-ready 包最终选择的是 `step0`、`step20` 还是混合状态。

这应作为数据身份的一部分记录，不能靠模型代码猜测。

---

## 8. 从 RTL 到 AIG 的论文流程

### 8.1 前端工具链

论文报告的版本：

| 工具 | 论文版本/用途 |
|---|---|
| OpenROAD | v1.0，整体开源 EDA 流程 |
| Yosys | v0.9，RTL synthesis front-end |
| ABC | structural hashing、logic optimization、technology mapping |
| NetworkX | v2.6，图处理 |
| PyTorch | v1.9，模型训练 |
| PyTorch-Geometric | v1.7.0，图数据与 GNN |

### 8.2 technology mapping 条件

论文明确使用：

- Nangate 45 nm；
- `5K_heavy` wireload model。

这决定 area/delay 标签的含义。

README 的目录说明却写 `Nangate 15nm` / `Nangate15nm.lib`。

代码 `automate_synthesisScriptGen.py` 写的是：

```python
readLibLine = "read " + ... + "nangate45.lib"
```

所以正确口径应以论文和实际 generator 的 `nangate45.lib` 为准。

### 8.3 intermediate AIG 保存

每条 20 步 recipe 会保存：

```text
step0：strash 后、应用 recipe 之前
step1：第 1 个变换之后
...
step20：第 20 个变换之后
```

严格说每条 recipe 存在 `step0..step20` 共 21 个状态。

论文的 870,000 计算只按 20 个中间/最终优化结果计数，没有把共同的初始状态重复算入。

代码的 GraphML automation 也只循环 `1..20`，没有转换 step0。

---

## 9. 本地 1500 条 recipe 的实际格式

`bench_openabcd/referenceScripts.zip` 包含：

```text
referenceScripts/abc0.script
...
referenceScripts/abc1499.script
```

审计结果：

- 正好 1500 个 script 文件；
- ID 从 0 到 1499；
- 没有缺失 ID；
- ZIP 还包含一个目录项，所以 `unzip -Z1 | wc -l` 是 1501，不代表有 1501 条 recipe。

### 9.1 一个 reference script 的结构

```text
strash
write_bench -l .../aes_orig.bench
<20 条从七个动作中采样的变换>
write_bench -l .../aes_syn<ID>.bench
dch
map -B 0.9
topo
stime -c
buffer -c
upsize -c
dnsize -c
```

### 9.2 generator 如何把 reference script 定制到不同 IP

`automate_synthesisScriptGen.py` 并不重新随机采样 recipe。

它做的是：

1. 读取已有 `abc<ID>.script`；
2. 为每个 design 写入 `read nangate45.lib`；
3. 把 `read_bench` 路径换成该 design 的原始 BENCH；
4. 写 `strash`；
5. 保存 step0；
6. 对 `fileLines[2:-8]` 的每个动作，执行后保存一个 intermediate BENCH；
7. 最后写 `map -B 0.9`、`topo`、`stime -c`。

因此公开的 1500 reference scripts 才是真正 recipe source。

### 9.3 固定行切片的脆弱性

代码通过：

```python
fileLines[2:-8]
```

提取 20 个动作。

`synthID2SeqMapping.py` 又通过：

```python
fileLines[3:-9]
```

从定制后的 script 提取动作。

这两个切片依赖模板前后行数完全不变。

只要增加：

- 一行注释；
- 一个 `read`；
- 一条统计命令；
- 一个空行；

recipe vector 就可能错位或出现未知 token。

稳健实现应按七个允许的完整命令解析，而不是按绝对行号切片。

---

## 10. AIG 的图表示

### 10.1 节点

公开 parser 使用三类节点：

| 数字 | 节点类型 |
|---:|---|
| 0 | PI |
| 1 | PO |
| 2 | Internal AND |

NOT 不单独作为图节点。

### 10.2 反相如何表达

BENCH 中的 `NOT(x)` 被 parser 记录为 alias。

当后续 AND 或 PO 使用这个 alias 时：

- edge type = 1；
- 目标节点的 `num_inverted_predecessors` 加 1。

普通连线：

- edge type = 0。

所以每个 AND 节点的输入反相数为 0、1 或 2。

### 10.3 论文列出 edge feature，baseline 却没有使用

论文 Table 2 把 `edge type` 明确列为样本字段。

`andAIG2Graphml.py` 也写入 `edge_type`。

`PyGDataAIG.py` 也把它转成 tensor。

但是，Net1/Net2/Net3 和 ClassNet 的 forward 都只读取：

```python
batched_data.node_type
batched_data.num_inverted_predecessors
batched_data.edge_index
```

没有读取：

```python
batched_data.edge_type
```

因此应准确表述为：

> OpenABC-D 数据格式保存了 edge type，但论文发布的这些 baseline 实现没有把 edge attribute 输入消息函数。

不能写成“模型显式使用 inverter edge embedding”。

### 10.4 parser 的边方向

`processANDAssignments` 调用：

```python
AIG_DAG.add_edge(idxCounter, srcIdx, edge_type=eType)
```

其中：

- `idxCounter` 是当前 AND/消费节点；
- `srcIdx` 是 fanin/source 节点。

因此保存方向是：

```text
consumer gate → fanin source
```

而常见信号流方向是：

```text
fanin source → consumer gate
```

`PyGDataAIG.py` 直接使用 `list(G.edges)`，没有反转或双向化。

PyG MessagePassing 默认按 `source_to_target` 聚合，这意味着 baseline 实际更接近从 fanout/消费者方向向 fanin 聚合信息。

这不一定绝对错误：

- QoR 可能从反向结构上下文中获益；
- 两层 GCN 加 self-loop 仍能学到结构统计；

但它是一个需要明确记录的实现语义，论文没有说明。

### 10.5 parser 的其他边界

1. BENCH 以 `r+` 打开，虽然只读，导致只读数据也需要写权限；
2. NOT alias 解析依赖被引用的原始节点已经出现在 mapping 中；
3. 遇到未知行直接 `exit(1)`；
4. dead verification helper 引用未定义的 `gateType`；
5. 使用字符串包含判断，如 `line.__contains__("AND")`，而不是完整语法解析；
6. 常量 `vdd` 被当作 PI，而不是常量节点。

这些都说明该 parser 是面向作者生成 BENCH 格式的专用工具，不是通用 BENCH front-end。

---

## 11. GraphML 到 PyG 的转换

`datagen/utilities/PyGDataAIG.py` 做两件事：

1. NetworkX GraphML → `torch_geometric.data.Data`；
2. 通过 Dataset wrapper 批量处理 1500 个 GraphML ZIP。

### 11.1 生成的 Data 属性

代码添加：

- `node_type`；
- `num_inverted_predecessors`；
- `edge_type`；
- `edge_index`；
- `longest_path`；
- `and_nodes`；
- `pi`；
- `po`；
- `not_edges`；
- `desName`；
- `synVec`；
- `synID`；
- `stepID`。

### 11.2 生产文件的实际命名

`preprocessGraphData` 保存：

```text
<design>_syn<synID>_step<stepID>.pt
```

紧接着把它压成：

```text
<design>_syn<synID>_step<stepID>.pt.zip
```

然后删除裸 `.pt`。

### 11.3 Dataset 自己期待的却是另一套命名

同一文件中的 `processed_file_names` 构造：

```text
<design>_<index>.pt
```

`get(idx)` 也加载：

```text
processed/<design>_<index>.pt
```

所以这个类的生产与消费契约互相不一致：

| 阶段 | 期待/生成 |
|---|---|
| process 实际生成 | `aes_syn149_step15.pt.zip` |
| processed check 期待 | `aes_<index>.pt` |
| get 期待 | `aes_<index>.pt` |

这会导致：

- PyG 认为 processed 文件不完整；
- Dataset 可能重复触发 process；
- `get` 找不到实际生成物；
- 即使 ZIP 在，也不能被该类按当前路径读取。

训练侧的另一个 `NetlistGraphDataset` 能读取 `.pt.zip`，但依赖外部 split CSV 精确列出 ZIP 文件名。

### 11.4 cleanup 路径错误

`main()` 最后写：

```python
rawFolder = os.path.join(sys.argv[1], 'raw')
shutil.rmtree(rawFolder)
```

正常命令是：

```bash
python PyGDataAIG.py --des ... --name ... --gs ... --synvec ...
```

此时 `sys.argv[1]` 是字符串 `--des`，不是 `cmdArgs.des`。

于是它尝试删除：

```text
--des/raw
```

正确来源应是：

```python
cmdArgs.des
```

这属于 end-to-end 入口级错误。

### 11.5 外部命令没有检查返回码

解压与压缩通过 `os.system` 执行：

```text
unzip ...
zip ...
```

没有：

- shell quoting；
- return-code check；
- 输入 ZIP 完整性验证；
- 输出成员数量验证；
- 原子写入。

在大规模并行生成中，一次损坏 ZIP 很容易静默传播到后续 split。

---

## 12. 标签生成流程

### 12.1 area / delay

`collectAreaAndDelay.py` 对每个设计的 1500 个 log：

1. 读取最后一行；
2. 用正则提取字母、数字和点；
3. 用倒数第 9 个 token 作为 area；
4. 用倒数第 4 个 token 作为 delay。

核心逻辑等价于：

```python
information = re.findall(..., synthFileLines[-1])
area = information[-9]
delay = information[-4]
```

它没有检查 token 名称。

ABC 版本或 `stime` 输出格式稍有变化，就可能：

- 取错列；
- 取到别的数字；
- 索引越界；
- 仍然写出看似合法的 CSV。

稳健实现应匹配明确字段名并做数值范围验证。

### 12.2 最终 AIG 统计

`collectGraphStatistics.py` 对每个 recipe ZIP 固定查找：

```text
<design>_syn<ID>_step20.bench.graphml
```

然后统计：

- BUFF edge；
- NOT edge；
- AND node；
- PI；
- PO；
- longest path。

它只看 step20，符合最终 QoR 标签需求。

但是没有验证：

- 是否正好 1500 个 ZIP；
- recipe ID 是否无缺失；
- ZIP 是否包含唯一目标成员；
- GraphML 是否是 DAG；
- 数据是否与 area/delay CSV 同一批次。

### 12.3 pickle 标签合并

`pickleStatsForML.py` 将每个设计合并成：

```python
[ANDgates, NOTgates, longest_path, area, delay]
```

它分别按 `sid` 排序两张 CSV。

但没有 assert：

- 两边 `sid` 集合相同；
- 长度均为 1500；
- 没有重复 `sid`；
- area/delay 无 NaN；
- 设计名在两个目录都出现。

因此最小修复不只是“排序”，而是显式按 `sid` merge，并使用 `validate='one_to_one'`。

---

## 13. 论文 baseline 总体模型

![论文 Figure 5(a)：QoR baseline](./figures/paper_fig5a_baseline.png)

![论文 Figure 5(b)：AIG embedding 网络](./figures/paper_fig5b_aig_embedding.png)

模型有两条分支。

### 13.1 图分支

```text
node type embedding 3d
        +
incoming inverter count 1d
        ↓
4d node feature
        ↓
GCN layer 1 + BatchNorm + ReLU
        ↓
GCN layer 2 + BatchNorm
        ↓
global mean pool || global max pool
        ↓
AIG embedding
```

### 13.2 recipe 分支

```text
20 个 operation ID
        ↓
每个 ID → 3d embedding
        ↓
拼接成 60d sequence encoding
        ↓
多组并行 Conv1d
        ↓
recipe subsequence features
```

### 13.3 融合与输出

```text
AIG embedding || recipe conv outputs
                    ↓
             fully connected layers
                    ↓
              scalar normalized QoR
```

模型不是直接生成 recipe。

它解决的是：

```text
f(AIG, recipe) → predicted QoR
```

要选 recipe，还需对候选 recipe 批量评分或与搜索算法结合。

---

## 14. 图分支的代码细节

### 14.1 NodeEncoder

三个 QoR 模型和分类模型都把 `node_type` 映射成 3 维 embedding：

```text
PI / PO / Internal → R^3
```

再把原始 inverter count 作为 1 个连续标量直接拼接：

```text
3d learned type embedding || 1d raw count = 4d
```

这里 `num_inverted_predecessors` 虽然是类别值 0/1/2，代码没有单独 embedding。

### 14.2 Net1 的自定义 GCN

Net1 自己实现 `MessagePassing`：

1. 给图加入 self-loop；
2. 线性投影节点特征；
3. 按 degree 做对称归一化；
4. 对邻居消息求和。

抽象式：

```text
h'_i = Σ_{j∈N(i)∪{i}} 1/sqrt(d_i d_j) · W h_j
```

代码 degree 使用 `row` 端计算，并额外 `+1`：

```python
deg = degree(row, x.size(0), dtype=x.dtype) + 1
```

但 `add_self_loops` 已经加过自环。

因此这里的 `+1` 是否重复计入 self-loop，取决于作者对 row degree 的解释；它不是 PyG 标准 `GCNConv` 的逐字复用。

### 14.3 Net2

Net2 使用 PyG `GCNConv`，每层 64 维。

图级输出：

```text
mean pool 64d || max pool 64d = 128d
```

### 14.4 Net3

Net3 再次使用自定义 GCN，图层也是 64/64。

它与 Net2 的主要实验设计差异是：

- recipe 卷积 kernel 更大；
- FC 中加入 dropout 0.2；
- 仍使用 128d 图级 embedding。

所以 Table 6 中 Net3 变好，不能只归因于“更大 recipe kernel”，也同时混入了 dropout 与自定义 GCN 实现差异。

---

## 15. recipe encoder 的代码细节

### 15.1 operation embedding

七个 operation ID 的 embedding table 大小：

```text
7 × 3
```

长度 20 的 recipe 展平为：

```text
20 × 3 = 60
```

### 15.2 为什么使用 Conv1d

作者希望卷积捕捉局部子序列模式，例如：

```text
rewrite → rewrite -z → balance
```

可能比孤立动作更能解释 QoR。

不同 kernel 相当于不同长度的 recipe pattern detector。

### 15.3 图中“FC layer”与代码的关系

论文 Figure 5 画出 synthesis flow 后先过 FC layer 得到 60d encoding。

公开代码实际使用的是 embedding lookup：

```python
self.synth_emb = torch.nn.Embedding(7, 3)
```

然后逐位置拼接。

这在功能上可视为离散 ID 的可学习线性编码，但不是一个对 20 维连续向量执行的普通全连接层。

### 15.4 Conv 输出维度

无 padding、stride=3 时：

```text
L_out = floor((60 - kernel_size) / 3) + 1
```

Net1：

| kernel | 输出长度 |
|---:|---:|
| 6 | 19 |
| 9 | 18 |
| 12 | 17 |

图 embedding 为 256d，所以融合维度：

```text
256 + 19 + 18 + 17 = 310
```

与论文 Table 3 的 `310-128-128-1` 一致。

Net2：

| kernel | 输出长度 |
|---:|---:|
| 12 | 17 |
| 15 | 16 |
| 18 | 15 |
| 21 | 14 |

融合维度：

```text
128 + 17 + 16 + 15 + 14 = 190
```

与 `190-512-512-512-1` 一致。

Net3：

| kernel | 输出长度 |
|---:|---:|
| 21 | 14 |
| 24 | 13 |
| 27 | 12 |
| 30 | 11 |

融合维度：

```text
128 + 14 + 13 + 12 + 11 = 178
```

与 `178-512-512-512-1` 一致。

---

## 16. Net1、Net2、Net3 逐模型对应

### 16.1 论文 Table 3

| 模型 | GCN | 图 pooling | recipe kernels | stride | FC | dropout |
|---|---|---|---|---:|---|---:|
| Net1 | 128 / 128 | Max + Mean | 6, 9, 12 | 3 | 310-128-128-1 | 0 |
| Net2 | 64 / 64 | Max + Mean | 12, 15, 18, 21 | 3 | 190-512-512-512-1 | 0 |
| Net3 | 64 / 64 | Max + Mean | 21, 24, 27, 30 | 3 | 178-512-512-512-1 | 0.2 |

### 16.2 本地代码目录

| 论文名 | 代码目录 |
|---|---|
| Net1 | `models/qor/SynthNetV1/` |
| Net2 | `models/qor/SynthNetV2/` |
| Net3 | `models/qor/SynthNetV3/` |

每个目录都有：

- `model.py`；
- `train.py`；
- `evaluate.py`；
- `netlistDataset.py`；
- `utils.py`。

Net1 还多一个 `embedding.py`。

### 16.3 对应结论

三组源码的核心维度、kernel、stride、FC 深度和 dropout 与 Table 3 基本一致。

这是当前仓库最可靠的“论文—代码对应”部分。

但要注意：

- Table 3 对应的是模型定义；
- 它不证明公开训练入口可直接运行；
- 它不证明本地数据 split 与论文一致；
- 它不证明作者 checkpoint 已公开。

---

## 17. 三个 QoR 任务

### 17.1 Variant 1：未见 recipe

问题：

> 对已知 IP，给一个训练期间未见的 recipe，能否预测最终节点数？

论文 split：

```text
每个 IP 前 1000 个 recipe → train
每个 IP 后 500 个 recipe → test
```

训练样本数：

```text
29 × 1000 = 29,000
```

这个任务测试 recipe 泛化，但 IP 都见过。

### 17.2 Variant 2：未见 IP

问题：

> 只用较小 IP 训练，能否预测未见大 IP 的 recipe QoR？

论文使用：

- 16 个较小 IP 训练；
- 8 个较大 IP 推理。

这是三种 split 中最困难、也最接近真实 OOD 的一个。

### 17.3 Variant 3：未见 IP–recipe 组合

论文随机选择 70% 的 IP–recipe pair 训练。

测试 pair 在训练中未出现，但：

- 该 IP 可能在其他 recipe 下出现过；
- 该 recipe 可能在其他 IP 上出现过。

所以它是组合泛化，不是完全未见实体泛化。

### 17.4 三种任务不能混写

| Variant | IP 是否见过 | recipe 是否见过 | pair 是否见过 |
|---|---:|---:|---:|
| 1 | 是 | 否 | 否 |
| 2 | 否 | 是/可用 | 否 |
| 3 | 是 | 是 | 否 |

Variant 3 的数值最好，不代表它比 Variant 1/2 更强，只代表任务信息条件更宽松。

---

## 18. 论文 QoR 结果

论文 Table 6 报告 normalized target 上的 test MSE：

| 任务 | Net1 | Net2 | Net3 |
|---|---:|---:|---:|
| Variant 1 | 0.648 ± 0.05 | 0.815 ± 0.02 | **0.579 ± 0.02** |
| Variant 2 | 10.59 ± 2.78 | **1.236 ± 0.15** | 1.47 ± 0.14 |
| Variant 3 | 0.588 ± 0.04 | 0.538 ± 0.01 | **0.536 ± 0.03** |

这些都是 `[论文]` 数字，不是本地重算。

### 18.1 如何解释

- Variant 1：Net3 最好；
- Variant 2：Net2 最好，Net1 明显失效；
- Variant 3：Net2 与 Net3 接近；
- 更大的 recipe kernel 并非对所有 OOD 情况都最好；
- 未见 IP 远难于未见 pair。

### 18.2 论文指出的具体 OOD 设计

Variant 2 中：

- `aes_xcrypt`；
- `wb_conmax`；

跨模型都较差，作者认为测试 AIG embedding 与训练分布不同。

而：

- `bp_be`；
- `tinyRocket`；
- `picosoc`；

预测更接近真实 QoR。

### 18.3 MSE 不能直接解释为节点数误差

目标先做 per-design 标准化：

```text
y_norm = (y - μ_design) / σ_design
```

因此 MSE 是标准化空间中的误差。

不能直接说：

```text
MSE 0.579 = 平均少错 0.579 个节点
```

正确解释是：

> 平方误差以该设计标签标准差为尺度归一化。

---

## 19. IP 分类与 embedding 实验

作者还训练两层 GCN，根据 AIG 结构识别 IP 类别。

论文配置：

- batch size 64；
- Adam；
- learning rate `1e-3`；
- weight decay `1e-2`；
- categorical cross-entropy；
- 35 epochs；
- 报告 accuracy 98.05%。

### 19.1 分类模型结构

公开 `ClassNetV1/model.py`：

```text
4d node input
  ↓
GCN 128 + BN + ReLU
  ↓
GCN 128 + BN
  ↓
global mean pool
  ↓
FC 128 + ReLU
  ↓
num_classes logits
```

它只用 mean pool，不用 QoR 模型的 mean+max。

### 19.2 当前训练脚本不能直接复现 98.05%

原因包括：

1. 同样读取不存在的 `args.epoch`；
2. 默认 `lp=1`，帮助文本却说 classification 应为 2；
3. `random_split` 不设 seed；
4. 每个 epoch 都存 checkpoint；
5. 虽计算 `best_val_epoch`，测试时仍使用最后一个 in-memory model；
6. accuracy 先对每个 batch 求比例，再对 batch 等权平均；最后一个小 batch 权重被放大；
7. 代码 optimizer 没有传论文所说的 `weight_decay=1e-2`。

所以源码结构与论文任务对应，但训练协议并不完整一致。

### 19.3 embedding 导出入口不完整

`models/qor/SynthNetV1/embedding.py` 构造：

```python
SynthNet_embed(...)
```

但 `model.py` 没有定义 `SynthNet_embed`。

它还假设模型 forward 返回：

```text
prediction, graphEmbed, synFlowEmbed
```

当前 `SynthNet.forward` 只返回 prediction。

此外：

- 没有 `model.to(device)`；
- batch 没有 `.to(device)`；
- 直接对 tensor 调 `.numpy()`；
- `device='cuda'` 参数没有真正使用。

因此 Figure 6 所需的公开 embedding 提取闭环在当前代码中缺失。

---

## 20. 训练代码的实际执行流程

以 `SynthNetV1/train.py` 为例。

### 20.1 参数解析

代码接受：

```text
--batch_size
--lr
--lp
--epochs
--dataset
--rundir
--datadir
--target
```

其中 `--rundir`、`--datadir`、`--target` 是 required。

### 20.2 第一个直接错误

代码写：

```python
parser.add_argument('--epochs', ...)
...
num_epochs = args.epoch
```

Argparse 生成的是：

```python
args.epochs
```

因此原入口在加载数据之前就会抛：

```text
AttributeError: 'Namespace' object has no attribute 'epoch'
```

同样的问题出现在：

- `SynthNetV1/train.py`；
- `SynthNetV2/train.py`；
- `SynthNetV3/train.py`；
- `ClassNetV1/train.py`。

### 20.3 数据集根目录

训练代码构造：

```python
root = os.path.join(ROOT_DIR, "lp" + str(learningProblem))
```

于是 PyG 实际从下面找 processed 文件：

```text
<datadir>/lp1/processed/
```

而 README 画的结构是：

```text
OPENABC-D/
├── lp1/*.csv
└── processed/*.pt.zip
```

按 PyG Dataset 规则，`root=lp1` 时，`processed_dir` 是 `lp1/processed`，不是顶层 `processed`。

所以 README 结构与训练代码也不完全一致。

### 20.4 train/validation

外部 split CSV 先定义 train/test。

训练脚本再把 train 随机切成：

```text
80% train
20% validation
```

没有：

- generator seed；
- design-aware stratification；
- recipe-aware grouping；
- split manifest hash。

因此重复运行的 validation set 不同。

### 20.5 训练

```text
MSELoss
Adam lr=0.001
ReduceLROnPlateau
80 epochs（论文/默认）
batch 64（论文/默认）
```

保存 validation MSE 最低的 state dict。

### 20.6 训练后评测

训练代码重新加载 best validation checkpoint，计算：

- train MSE；
- validation MSE；
- test MSE；
- per-design scatter；
- top-k ranking overlap。

QoR 训练脚本这部分选择 best checkpoint 的逻辑基本合理；分类脚本没有做到同样的 reload。

---

## 21. README 命令为什么不能直接运行

README 给出的训练示例：

```bash
python train.py --datadir ... --rundir ... --dataset set1 \
  --lp 1 --lr 0.001 --epochs 60 --batch-size 32
```

至少有四个问题。

### 21.1 参数名错误

README：

```text
--batch-size
```

代码：

```text
--batch_size
```

Argparse 不会自动把这两者视为同一个参数。

### 21.2 缺少 required target

代码要求：

```text
--target nodes|area|delay
```

README 示例没有提供。

### 21.3 epoch 与 batch 不同

README 示例：

- 60 epochs；
- batch 32。

论文和代码默认：

- 80 epochs；
- batch 64。

### 21.4 即使修正命令，args.epoch 仍然报错

把 `--batch-size` 改为 `--batch_size` 并补 `--target nodes` 后，训练仍会在：

```python
num_epochs = args.epoch
```

处失败。

因此不能把 README 命令列为“官方可直接复现命令”。

---

## 22. train 与 evaluate 的路径契约不一致

训练：

```python
NetlistGraphDataset(root=<datadir>/lp1, filePath=train_data_set1.csv)
```

评测：

```python
NetlistGraphDataset(root=<datadir>, filePath=train_data_set1.csv)
```

同一个 `--datadir` 在两个脚本中代表不同目录层级。

若 CSV 位于：

```text
OPENABC-D/lp1/train_data_set1.csv
```

训练可以按 `datadir=OPENABC-D` 找到。

评测却会尝试：

```text
OPENABC-D/train_data_set1.csv
```

若把 `datadir` 改成 `OPENABC-D/lp1` 让评测找到 CSV，那么它又从：

```text
OPENABC-D/lp1/synthesisStatistics.pickle
```

读取标签，而 README 把 pickle 放在顶层。

正确复现必须先统一一个 schema，再同时修改 train/evaluate/dataset，而不是只改命令。

---

## 23. target 标准化与 Variant 2 泄漏

`computeMeanAndVarianceOfTargets` 对 `synthesisStatistics.pickle` 中每个设计的全部 recipe 标签计算：

```text
μ_design = mean(y_design[0:1500])
σ_design = std(y_design[0:1500])
```

然后 train 与 test 都用：

```text
(y - μ_design) / σ_design
```

### 23.1 Variant 1

测试 recipe 未见，但 IP 见过。

如果 μ/σ 用全部 1500 recipe，就包含后 500 个测试标签。

这已经是 test-label distribution leakage，不过影响主要是标准化尺度。

### 23.2 Variant 2 更严重

测试 IP 从未用于训练。

但代码要预测该 IP 的某个 recipe 前，先读取该 IP 全部 1500 个真实 QoR，计算 μ/σ。

现实场景中，要得到这些真实标签，本来就必须把 1500 个 recipe 全部综合一遍。

这与“避免大 IP 昂贵综合”的任务动机冲突。

并且模型输出是 normalized QoR；若要反标准化，也需要测试 IP 的 μ/σ。

因此 Variant 2 当前 normalization 是 oracle normalization。

### 23.3 更合理的处理

至少有三种选择：

1. 只用 training designs / training recipes 计算全局 scaler；
2. 预测相对初始 AIG 的比例，如 `final_nodes / initial_nodes`；
3. 用可从输入 AIG 直接计算的规模因子归一化。

无论哪种，都应：

- scaler 只 fit train；
- 保存 scaler；
- test 只 transform；
- 报 normalized 与 physical-space 指标。

---

## 24. 论文结果与当前代码不能直接等同的其他原因

### 24.1 split 生成脚本缺失

论文和 README 说提供按学习任务划分数据的脚本。

当前仓库没有找到生成：

- `train_data_set1.csv`；
- `test_data_set1.csv`；
- `train_data_set2.csv`；
- `test_data_set2.csv`；
- mixmatch split；

的源码。

这些 CSV 只可能随外部 ML-ready 数据提供。

没有它们，就不能确认：

- 具体 IP 列表；
- 具体 recipe ID；
- 输入 step；
- 文件命名；
- 是否存在重复或交叉污染。

### 24.2 checkpoint 缺失

本地 `.pt/.pth/.ckpt` 数量为 0。

仓库模型目录没有作者预训练权重。

所以 `evaluate.py --model ...` 不能直接使用。

### 24.3 随机性未固定

- `random_split` 无 seed；
- DataLoader shuffle 无固定 generator；
- PyTorch、NumPy、Python random 未统一设 seed；
- CUDA deterministic 设置缺失。

论文报告 `±` error bar，但当前入口没有显式 multiple-seed runner。

### 24.4 evaluator 输出顺序随机

评测 DataLoader 也设置 `shuffle=True`。

整体 MSE 在无状态 transform 下不受顺序影响，但：

- 导出的 batchData 顺序不稳定；
- debug 难以逐样本追踪；
- 同一 checkpoint 的日志和图难以逐字节比较。

### 24.5 MSE 与 top-k 的关联

模型训练优化 MSE。

真正 recipe selection 更关心：

- top-1 命中；
- top-k recall；
- regret；
- 实际选中 recipe 的 area/delay；
- Pareto frontier coverage。

代码后处理有 top-k overlap，但论文主表仍只给 MSE。

低 MSE 不必然保证最优 recipe 排名正确。

---

## 25. automation 流程中的闭环问题

### 25.1 synthesis script generator 不创建 syn 目录

生成的 ABC script 要写：

```text
bench/<design>/syn<ID>/<design>_syn<ID>_stepK.bench
```

但 `automate_synthesisScriptGen.py` 不创建 `syn<ID>`。

`automate_bulkSynthesis.py` 也没有在 `yosys-abc` 前写 `mkdir`。

所以除非外部人工预先建立 29 × 1500 个目录，ABC 写 intermediate BENCH 会失败。

### 25.2 bulk shell 没有 fail-fast

对每个 recipe 依次写：

```text
yosys-abc ... > log
zip syn<ID>/
rm -fr syn<ID>/
```

生成的 shell 没有：

- `set -euo pipefail`；
- ABC return-code check；
- 输出文件数量检查；
- ZIP 测试；
- 删除前确认。

如果 ABC 失败，后续仍可能压缩空目录并删除临时目录。

### 25.3 GraphML 阶段多了 swerv

综合、统计的 design list 共 29 个。

`automate_synbench2Graphml.py` 的 set5 却是：

```python
['dft', 'idft', 'fir', 'iir', 'sha256', 'swerv']
```

因此 GraphML 阶段变成 30 个设计。

若 `swerv` 没有相应 BENCH ZIP，批处理会失败；若有，它又不会被其他阶段一致收集。

### 25.4 并行等待写法

脚本每个 recipe 启 20 个后台 Python：

```text
python andAIG2Graphml.py ... &
```

然后写：

```bash
wait < <(jobs -p)
```

常见写法应是：

```bash
wait
```

或显式收集 PID。

当前写法把 process substitution 接到 wait 的 stdin，但 Bash `wait` 不从 stdin 读取 PID 列表。

它通常等价于无参数 `wait`，可读性和可移植性差。

### 25.5 大规模删除风险

automation 生成大量 `rm -fr`。

这些命令是写入 shell 文件，不是 Python 立即执行，但真正运行 shell 时会删除：

- 解压后的 BENCH 目录；
- 临时 GraphML 目录。

安全复现必须：

- 先验证 ZIP 完整；
- 使用显式绝对数据根；
- 禁止空变量；
- 对目标路径做前缀检查；
- 保存 manifest 后再清理。

本次审计没有执行这些删除命令。

---

## 26. requirements 与版本漂移

### 26.1 论文

```text
PyTorch 1.9
PyG 1.7.0
NetworkX 2.6
```

### 26.2 README

```text
PyTorch 1.8.1
PyG 1.7.0
NetworkX >= 2.5
Python >= 3.9
CUDA 10.1
```

### 26.3 requirements.txt

同一环境文件同时包含：

```text
pytorch=1.8.1=...
torch=1.7.1=pypi_0
torchvision=0.8.2
torchaudio=0.7.2
torch-geometric=1.7.0
```

Conda 的 `pytorch` 与 pip metadata 中的 `torch` 版本冲突。

### 26.4 PyG 2.x 兼容性

README 明确提醒：

- 已发布 `.pt` 是 PyG 1.x 格式；
- PyG 2.x 不向后兼容；
- 应使用 `<2.0` 或从 GraphML 重新生成。

因此不能在现代 PyG 上简单 `torch.load` 后报错，就归因于数据损坏。

精确复现应先重建 2021 legacy 环境，再另做 modern migration。

### 26.5 当前不建议直接用 requirements.txt 创建生产环境

该文件共 220 行，混合：

- conda 包；
- pip 包；
- Jupyter；
- NLP；
- Gym；
- AWS CLI；
- DGL；
- PyG；
- 多组深度学习包。

对 OpenABC baseline，应该从实际 imports 重新提炼最小锁定环境。

---

## 27. 本地资产审计

### 27.1 有什么

| 资产 | 数量/状态 |
|---|---:|
| 原论文 | 1 |
| 原始 BENCH | 47 |
| reference recipe | 1500，ID 完整 |
| RTL `.v` under bench_rtl/src | 253 |
| leaf-level Verilog | 2020 |
| synthesis settings dirs | 29 |
| 数据/模型 Python | 已开源 |
| paper/README figures | 已归档 |

### 27.2 没有什么

| 资产 | 本地数量 |
|---|---:|
| GraphML | 0 |
| PyG `.pt/.pt.zip` 数据 | 0 |
| checkpoint | 0 |
| synthesis statistics pickle | 0 |
| recipe vector pickle | 0 |
| train/test CSV | 0 |
| ABC run log | 0 |
| OpenABC-D 模型运行 record | 0 |

唯一 CSV 是后续 leaf-level Verilog 的 `verilog_status.csv`，不是论文 split 或标签。

### 27.3 为什么已有 47 个 BENCH 仍不能训练

模型还需要：

1. 每个设计、recipe 的图样本；
2. 20 维 recipe vector；
3. 最终节点数/area/delay；
4. split CSV；
5. 与 PyG 版本兼容的序列化格式。

只有原始 BENCH 无法提供监督标签和 1500 recipe 的最终结果。

---

## 28. 为什么本次没有“再跑一次推理”

用户此前已经明确指出：已有模型应优先查 `模型推理.md` 和保存记录，不应无意义重复运行。

OpenABC-D 当前没有匹配的：

- checkpoint；
- PyG dataset；
- split；
- scaler；
- OpenABC 运行 record。

此时能做的“推理”只有：

```text
随机初始化模型 + 人造图
```

它最多证明某个 forward shape 成立，不能证明：

- 论文模型训练成功；
- MSE 接近 Table 6；
- dataset loader 正确；
- recipe 与标签对齐；
- OOD split 无泄漏；
- 论文 checkpoint 可用。

因此本轮只做静态代码与论文核对。

这不是把“没跑”包装成“跑过”，而是明确区分：

- model construction smoke；
- data pipeline reproduction；
- checkpoint inference；
- paper metric reproduction。

---

## 29. 正确的最小复现顺序

### Gate 0：固定身份

记录：

- 论文 PDF 哈希；
- repo commit；
- 数据下载版本；
- 数据包 checksum；
- PyTorch/PyG 版本；
- Nangate library hash；
- ABC/Yosys/OpenROAD commit。

### Gate 1：只下载 ML-ready 包

若目标只是复现 Table 6，优先下载约 19 GB ML-ready 数据。

不要先下载 1.4 TB 全量包。

下载地址：

<https://zenodo.org/record/6399454>

检查：

- split CSV 是否齐全；
- `.pt.zip` 成员命名；
- `synthesisStatistics.pickle`；
- `synthID2Vec.pickle`；
- 设计数与样本数；
- step ID。

### Gate 2：重建 legacy 环境

目标环境优先：

```text
Python 3.9
PyTorch 1.8/1.9 中与数据实际兼容的一版
PyG 1.7.0
torch-scatter 2.0.6
torch-sparse 0.6.9
NetworkX 2.5/2.6
```

先不要为了“最新版”直接升级数据对象。

### Gate 3：修复入口级错误

最小必要修复：

- `args.epoch` → `args.epochs`；
- README/CLI 统一 `--batch_size`；
- 补 `--target nodes`；
- train/evaluate 使用同一 data root；
- 明确 `.pt.zip` 的读取位置；
- 保存 fix patch 与 diff。

### Gate 4：检查 split 身份

打印并保存：

- 每个 split 的设计集合；
- recipe ID 集合；
- step ID 分布；
- train/test 文件交集；
- design–recipe pair 交集；
- 每个 CSV 的 SHA-256。

### Gate 5：修复 scaler

先复刻作者原 normalization，复算作者口径。

再增加无泄漏口径：

- train-only global scaler；
- input-size normalization；
- physical-space MAE/MAPE；
- ranking regret。

两种结果必须分开报告。

### Gate 6：单 batch forward

只在真实 ML-ready 样本上验证：

- node feature shape；
- edge direction；
- recipe shape 20；
- batch pooling；
- output shape `[B,1]`；
- target 对应 recipe ID。

### Gate 7：小样本过拟合

选一个小 IP、少量 recipe：

- 16～64 个样本；
- 让训练 loss 明显下降；
- 检查 checkpoint save/load 一致；
- 检查 normalized target 可反变换。

### Gate 8：Variant 1

按作者 1000/500 recipe split 跑 Net1/2/3。

至少记录：

- seed；
- best epoch；
- train/validation/test MSE；
- 每个 IP MSE；
- top-k regret；
- wall time；
- GPU；
- checkpoint hash。

### Gate 9：Variant 2

重点做两版：

1. 作者 normalization；
2. train-only 无泄漏 normalization。

只有第二版能更接近真实“未见大 IP”应用。

### Gate 10：Variant 3

明确 pair-level split，并验证：

```text
train_pair ∩ test_pair = ∅
```

同时确认每个 test IP 与 recipe 是否各自在 train 出现过。

### Gate 11：完整数据生成

只有要研究 intermediate trajectory 或扩展新 IP 时，才考虑 1.4 TB 全量数据或重新生成。

完整数据地址：

<https://ultraviolet.library.nyu.edu/records/mw6q2-a8p15>

README 提醒：

- 14 个约 107 GB 分卷；
- 压缩总量约 1.4 TB；
- 下载与解压至少 3 TB 磁盘。

在当前盘空间未核实前，不应直接下载。

---

## 30. 如果修复代码，优先级是什么

### P0：决定能否启动

1. `args.epochs`；
2. dataset root；
3. `.pt.zip` 生产/消费一致；
4. embedding class/return contract；
5. PyG 版本。

### P1：决定结果是否可信

1. scaler 只 fit train；
2. split seed 与 manifest；
3. edge direction 明确；
4. train/test 无交集检查；
5. best checkpoint 评测；
6. physical-space 与 ranking metrics。

### P2：决定流程是否稳健

1. ABC log 按字段解析；
2. recipe 按语法解析；
3. ZIP 完整性与成员计数；
4. shell fail-fast；
5. 删除前验证；
6. 每阶段 manifest 与 checksum。

### P3：现代化

1. PyG 2.x regeneration；
2. typed config；
3. Lightning/纯 PyTorch 统一 trainer；
4. DVC/manifest 管理数据；
5. CI 中增加小 BENCH 流程。

---

## 31. 论文—代码逐项对应表

| 论文概念 | 代码位置 | 对应情况 |
|---|---|---|
| 29 个 IP | automation 中五组 design list | 基本对应；GraphML 阶段多 `swerv` |
| 1500 recipe | `referenceScripts.zip` | 本地完整 |
| 七种动作 | `synthID2SeqMapping.py` | 完整对应 |
| 每条 20 步 | reference script + generator | 对应 |
| 保存 step0..20 | `automate_synthesisScriptGen.py` | generator 对应 |
| BENCH→GraphML | `andAIG2Graphml.py` | 对应，但边方向需说明 |
| node type | parser + NodeEncoder | 对应 |
| incoming inverter count | parser + NodeEncoder | 对应 |
| edge type | parser/PyG | 数据保存；模型未使用 |
| recipe 3d embedding | `SynthFlowEncoder` | 对应 |
| 1D recipe conv | `SynthConv` | 对应 |
| 2-layer GCN | 各 `model.py` | 对应 |
| mean+max pooling | QoR `GNN.forward` | 对应 |
| Net1 Table 3 | SynthNetV1 | 维度对应 |
| Net2 Table 3 | SynthNetV2 | 维度对应 |
| Net3 Table 3 | SynthNetV3 | 维度/dropout 对应 |
| batch 64 / lr .001 / 80 epoch | train defaults | epoch 读取 bug 阻断 |
| MSE | `criterion` / sklearn MSE | 对应 |
| Variant 1/2/3 | datasetDict set1/2/3 | 文件名入口存在，split generator 缺失 |
| IP classification | ClassNetV1 | 结构对应，weight decay 和 best model 不一致 |
| t-SNE embedding | embedding.py + analysis | 当前入口不完整 |

---

## 32. 论文 compute 成本

### 32.1 数据生成

论文 Table 5：

| 机器 | threads | wall time | compute hours |
|---|---:|---:|---:|
| 4× AMD EPYC 7551 32-Core，504 GB | 100 | 35 days | 84,000 |
| Dual Xeon E5-2650 v3，502 GB | 80 | 40 days | 76,800 |
| Xeon E5-2640，252 GB | 40 | 35 days | 33,600 |
| Threadripper 2920X，32 GB | 16 | 7 days | 2,688 |
| 8× i7-6700，96 GB | 40 | 55 days | 52,800 |

合计 249,888 compute-hours。

### 32.2 模型训练

论文列出：

| 平台 | GPU | QoR | 分类 |
|---|---|---:|---:|
| Lambda-quad | GTX 1080 Ti 11 GB，batch 4 | 48 h | 18 h |
| Greene HPC | RTX 8000 48 GB，batch 64 | 约 36 h | 约 12 h |

### 32.3 这意味着什么

OpenABC-D 的复现成本主要在数据生成，不在 baseline 网络本身。

因此合理复现层级是：

1. 先用 ML-ready 数据复现 baseline；
2. 再用少量 IP 验证数据生成；
3. 最后才考虑全量重新生成。

直接从零重跑 249,888 compute-hours 不是常规组会复现的合理第一步。

---

## 33. 值得组会重点讲的代码事实

### 33.1 贡献与 baseline 要分开

论文的长久价值主要是：

- 标准数据；
- trajectory；
- split 任务；
- 开放工具链。

GCN baseline 本身很简单，而且当前代码还有复现问题。

### 33.2 保存 edge type 不等于模型使用 edge type

这是一个很典型的 dataset-paper-code 三层差异。

可以把它作为组会审计案例：

```text
论文 Table 2：有 edge feature
数据转换：有 edge_type
baseline forward：完全不读 edge_type
```

### 33.3 未见 IP 的标准化可能泄漏完整测试标签分布

这是最值得深入讨论的实验设计问题。

如果模型目标是减少新大 IP 的综合成本，就不应先用该 IP 的 1500 个真实 QoR 算 μ/σ。

### 33.4 当前公开代码不是“一条命令复现”

它更像：

- 研究过程中的脚本集合；
- 外部大数据包配套代码；
- 需要理解目录约定后修补的 artifact。

这不削弱数据集的学术贡献，但影响复现等级。

---

## 34. 推荐的组会讲述逻辑

### Slide 1：为什么逻辑综合是序列决策

- 七种局部变换；
- 顺序决定 QoR；
- 不同 IP 没有统一最优 recipe。

### Slide 2：OpenABC-D 的核心数字

```text
29 × 1500 × 20 = 870,000
```

- 中间 AIG；
- 节点/边特征；
- area/delay；
- 200,000+ compute-hours。

### Slide 3：数据生成图

展示：

[DatagenerationPipeline.png](./figures/DatagenerationPipeline.png)

说明 RTL→AIG→GraphML→PyG。

### Slide 4：29 IP 多样性

展示：

[OpenSourceBenchmarks.png](./figures/OpenSourceBenchmarks.png)

强调从 462 到 245k 节点、fpu depth 819。

### Slide 5：样本 schema

```text
design_synID_stepID.pt
```

拆图、recipe、individual labels、final labels。

### Slide 6：模型

展示 Figure 5(a)/(b)。

讲两条分支：

- GCN 学 AIG；
- Conv1d 学 recipe 子序列。

### Slide 7：三个 split

用表比较：

- unseen recipe；
- unseen IP；
- unseen pair。

### Slide 8：Table 6

强调 Variant 2 最难，Net1 MSE 10.59。

### Slide 9：代码对应

Net1/2/3 的 kernel 和融合维度可精确由源码算出。

### Slide 10：复现边界

- 19 GB ML-ready 未在本地；
- 1.4 TB 全量未下载；
- checkpoint 缺失；
- CLI/路径/数据生产契约存在问题。

### Slide 11：最重要的审计发现

讲 per-design normalization 在 unseen IP 上的 oracle leakage。

### Slide 12：下一步研究

- leakage-free OOD；
- edge-aware / directed GNN；
- trajectory model；
- active recipe search；
- Pareto PPA；
- 与 DeepGate/DeepGate2 表示结合。

---

## 35. 后续研究方向

### 35.1 使用 intermediate trajectory

baseline 主要把完整 recipe 编码后预测最终 QoR。

但数据集最独特的部分其实是 20 步轨迹。

可以建模：

```text
(G_t, action_t) → G_{t+1} / ΔQoR
```

用于：

- model-based RL；
- action value estimation；
- early stopping；
- branch-and-bound；
- counterfactual recipe analysis。

### 35.2 directed / edge-aware GNN

当前 baseline 忽略 edge type，边方向还与信号流相反。

可以比较：

1. source→sink；
2. sink→source；
3. 双向两套 message；
4. inverter edge relation；
5. logic-level positional encoding；
6. fanout/reconvergence features。

### 35.3 DeepGate / DeepGate2 初始化

OpenABC baseline 的 node feature 很弱：

```text
node type + inverter count
```

可使用 DeepGate 系列预训练 gate embedding，再做 graph pooling 和 recipe fusion。

必须控制：

- 预训练电路与 OpenABC test IP 的重叠；
- 结构泄漏；
- 不同 AIG parser 的节点/边语义；
- checkpoint 数据身份。

### 35.4 多目标 Pareto

当前模型每次只选择 `nodes`、`area` 或 `delay` 一个 target。

真实综合是多目标：

```text
min area
min delay
possibly min power
```

可以预测联合分布或 Pareto rank，而不把三者简单加权成固定标量。

### 35.5 不确定性与 OOD

论文已观察 `aes_xcrypt/wb_conmax` 跨 IP 较差。

可以增加：

- ensemble；
- deep evidential regression；
- conformal interval；
- graph embedding density；
- OOD detector；
- abstention/re-synthesis 策略。

比单纯降低平均 MSE 更符合新 IP 应用。

### 35.6 active recipe selection

对新 IP 不必一次综合 1500 条。

可以：

1. 先选少量覆盖 recipe；
2. 综合得到真实标签；
3. 更新 surrogate；
4. 用 acquisition function 选择下一批；
5. 直到 regret 或预算达标。

这比假设测试 IP 的 μ/σ 已知更现实。

### 35.7 跨工艺泛化

论文 area/delay 固定 Nangate45。

当前仓库后来增加多工艺 leaf-level Verilog，可研究：

```text
f(AIG, recipe, technology) → area/delay
```

但后续数据不是原论文标签，需重新建立：

- library identity；
- operating corner；
- wireload/RC model；
- mapping constraints；
- label comparability。

---

## 36. 不建议直接重复的工作

### 36.1 不要把随机 forward 当复现

它不回答任何论文结果问题。

### 36.2 不要先下载 1.4 TB

若目标只是复现 Table 6，19 GB ML-ready 包已足够。

### 36.3 不要直接随机按 PyG 样本切分

同一个 design/recipe 的多个 step 高度相关。

随机 sample split 会造成严重 trajectory leakage。

### 36.4 不要用最终 AIG 预测最终节点数而不说明

这可能把 label 信息直接暴露在图结构中。

### 36.5 不要只报 normalized MSE

至少同时报：

- physical-space MAE；
- per-design MSE；
- top-k regret；
- Pareto hit；
- OOD confidence。

### 36.6 不要把当前 47 BENCH 写成论文规模

论文原始规模始终是 29 IP。

---

## 37. 当前复现判定

### 37.1 已完成

- 原论文归档；
- PDF 身份与哈希核对；
- 论文方法和实验表梳理；
- 四张图归档；
- 1500 recipe 完整性核对；
- automation/data/model/classification/analysis 代码阅读；
- Net1/2/3 维度逐项复算；
- 当前仓库后续扩展与论文范围分离；
- 阻断项与泄漏风险记录；
- JSON 静态审计。

### 37.2 未完成

- ML-ready 数据下载；
- 完整数据下载；
- legacy 环境重建；
- 真实数据 Dataset load；
- checkpoint inference；
- 训练；
- Table 6 重算；
- classification 98.05% 重算；
- 1.4 TB 生成闭环。

### 37.3 最准确的一句话

> OpenABC-D 的论文方法、1500 条 recipe、数据生成源码和四个 baseline 目录已经完成细致静态核对；当前本地没有 ML-ready 数据、标签 split 或 checkpoint，且公开入口存在 CLI、路径、PyG 文件契约和 unseen-IP 标准化泄漏问题，所以当前只能定为 R1/C-，不能声称模型或论文指标已复现。

---

## 38. 文件导航

### 38.1 论文与审计

- [原论文 PDF](./2110.11292_OpenABC-D.pdf)
- [机器可读静态审计](./runs/static_audit_20260802.json)
- [短版模型梳理](./模型梳理.md)
- [项目 README](./README.md)
- [BSD 3-Clause LICENSE](./LICENSE)

### 38.2 论文图

- [数据生成总览](./figures/DatagenerationPipeline.png)
- [29 个论文 benchmark](./figures/OpenSourceBenchmarks.png)
- [QoR baseline](./figures/paper_fig5a_baseline.png)
- [AIG embedding network](./figures/paper_fig5b_aig_embedding.png)

### 38.3 数据生成入口

- [`datagen/automation/automate_synthesisScriptGen.py`](./datagen/automation/automate_synthesisScriptGen.py)
- [`datagen/automation/automate_bulkSynthesis.py`](./datagen/automation/automate_bulkSynthesis.py)
- [`datagen/automation/automate_synbench2Graphml.py`](./datagen/automation/automate_synbench2Graphml.py)
- [`datagen/automation/automate_finalDataCollection.py`](./datagen/automation/automate_finalDataCollection.py)

### 38.4 数据工具

- [`datagen/utilities/andAIG2Graphml.py`](./datagen/utilities/andAIG2Graphml.py)
- [`datagen/utilities/PyGDataAIG.py`](./datagen/utilities/PyGDataAIG.py)
- [`datagen/utilities/collectAreaAndDelay.py`](./datagen/utilities/collectAreaAndDelay.py)
- [`datagen/utilities/collectGraphStatistics.py`](./datagen/utilities/collectGraphStatistics.py)
- [`datagen/utilities/pickleStatsForML.py`](./datagen/utilities/pickleStatsForML.py)
- [`datagen/utilities/synthID2SeqMapping.py`](./datagen/utilities/synthID2SeqMapping.py)

### 38.5 模型目录

- [`models/qor/SynthNetV1/`](./models/qor/SynthNetV1/)
- [`models/qor/SynthNetV2/`](./models/qor/SynthNetV2/)
- [`models/qor/SynthNetV3/`](./models/qor/SynthNetV3/)
- [`models/classification/ClassNetV1/`](./models/classification/ClassNetV1/)

### 38.6 数据地址

- 完整 1.4 TB 数据：<https://ultraviolet.library.nyu.edu/records/mw6q2-a8p15>
- 约 19 GB ML-ready 数据：<https://zenodo.org/record/6399454>

## P7 组件一句话总结

| 组件 | 一句话角色 |
|---|---|
| automate_synthesisScriptGen.py | 根据 reference recipe 为每个 IP 生成定制 ABC script。 |
| automate_bulkSynthesis.py | 批量调用 yosys-abc 执行 recipe 并保存中间 BENCH/log。 |
| andAIG2Graphml.py | 将 BENCH 解析为 NetworkX GraphML，记录 node/edge/inverter 语义。 |
| PyGDataAIG.py | 把 GraphML 转换为 PyG Data 并序列化为 `.pt.zip`。 |
| collectAreaAndDelay.py / collectGraphStatistics.py / pickleStatsForML.py | 从 ABC log 与 GraphML 提取 area/delay/AIG 统计并合并为 ML 标签。 |
| SynthNetV1/V2/V3 | 三组 GCN + recipe Conv1d 融合回归 baseline。 |
| ClassNetV1 | 两层 GCN 对 AIG 做 IP 分类。 |
| NetlistGraphDataset | PyG Dataset，按 split CSV 加载 `.pt.zip` 样本。 |

## 讨论问题

1. OpenABC-D 把“逻辑综合 recipe 搜索”建模为 f(AIG, recipe) → QoR 的回归问题，而不是直接生成 recipe；这种设定对真实 EDA 流程中的 recipe 优化有什么优势与局限？
2. 当前代码在 Variant 2 的 per-design 标准化中使用了测试 IP 全部 1500 个真实标签，这造成 oracle normalization leakage；应如何设计无泄漏的 scaler 才能更公平地评估“未见大 IP”？
3. 论文数据保存了 edge type，但 baseline 模型没有使用；如果引入 edge-aware 或方向正确的 GNN，能否显著提升跨 IP 泛化，尤其是 `aes_xcrypt`、`wb_conmax` 等 OOD 设计？

