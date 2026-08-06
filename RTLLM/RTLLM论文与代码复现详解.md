# RTLLM：论文、版本、代码与复现证据详解

> 论文：**RTLLM: An Open-Source Benchmark for Design RTL Generation with Large Language Model**  
> 论文版本：arXiv `2308.05345` v3，ASP-DAC 2024，6 页  
> 本地论文：[2308.05345_RTLLM.pdf](./2308.05345_RTLLM.pdf)  
> 官方仓库：<https://github.com/hkust-zhiyao/RTLLM>  
> 本地代码版本：commit `41b26896e33b536940116a975626455eed3de65e`，2024-11-08  
> 静态审计：[runs/static_audit_20260802.json](./runs/static_audit_20260802.json)  
> 核验日期：2026-08-02

---

## P8 全景：RTLLM 三目标评价阶梯

```text
        Quality：面积 / 功耗 / 时序
              ▲ 功能正确才比较 PPA
   Functionality：通过 testbench
              ▲ 语法正确才能仿真
         Syntax：综合器接受
```

三级全部通过，RTLLM 的质量评价才有设计意义。

---
## 0. 先给结论

RTLLM 不是一个需要训练或下载权重的“模型”，而是一套从**自然语言设计规格到 RTL，再到语法、功能和 PPA 评价**的 benchmark。

这篇论文最值得讲清楚的不是“GPT-4 得了多少分”，而是它第一次较完整地把设计级 RTL 生成拆成三个逐级目标：

1. **syntax goal**：RTL 能否被综合工具接受；
2. **functionality goal**：RTL 能否通过题目配套 testbench；
3. **quality goal**：正确 RTL 的面积、功耗和时序是否有竞争力。

论文还提出了一个非常简单的两阶段提示方法 **self-planning**：第一问只让模型写计划和语法注意事项，第二问再把原始规格与计划一起交给模型生成 RTL。它不是执行器闭环，也没有把 VCS 错误回灌给模型。

当前本地证据的准确结论是：

- 两篇论文 PDF、仓库、Git 版本历史、50 题 v2.0 数据和官方保留的 290 份旧版生成 RTL 已完成静态核对；
- 没有重新调用 GPT-3.5/GPT-4，也没有重新训练模型；
- 没有运行商业 VCS、Design Compiler 或物理实现流程；
- 当前 `auto_run.py` 不能直接遍历 v2.0 的分层目录，且评分与进程管理存在实质问题；
- 因此本篇的本地复现等级为 **R1：代码、数据、版本和执行入口已核对**，不能写成“论文表格已本地复现”。

一个必须反复强调的版本事实是：

| 口径 | 题数 | 说明 |
|---|---:|---|
| RTLLM 论文 Table II | 30 | 包含 `risc_cpu` |
| Git `origin/v1.0` 当前可见树 | 29 | 缺少论文中的 `risc_cpu` |
| Git `origin/v1.1` 当前可见树 | 29 | 相对 v1.0 有修订和题名变化 |
| 当前仓库 v2.0 | 50 | 四大类、分层目录 |
| GPT-3.5 官方保留输出 | 29 × 5 = 145 | 只覆盖旧版题集 |
| GPT-4 官方保留输出 | 29 × 5 = 145 | 只覆盖旧版题集 |

所以，“论文 30 题”“README 29 题”和“当前 50 题”都可能各自在自己的版本语境中成立，不能混成一个数字。

---

## 1. 论文身份与原文证据

论文作者为 Yao Lu、Shang Liu、Qijun Zhang 和 Zhiyao Xie，发表在 ASP-DAC 2024。仓库 README 明确说明论文实验基于 **RTLLM v1.0**。

![RTLLM 论文首页与相关工作对比表](./figures/rtllm-paper-title-table1.png)

> 图 1：截自论文第 1 页，包含论文标题、摘要及 Table I。它支持两个判断：RTLLM 的定位是 benchmark；论文把自己的贡献与早期 Verilog 数据/生成工作从题目数、复杂度以及是否评价 PPA 等维度区分开。

本地 PDF 核验信息：

| 字段 | 值 |
|---|---|
| 文件 | `2308.05345_RTLLM.pdf` |
| 页数 | 6 |
| 字节数 | 374,181 |
| SHA-256 | `fe62987f4fa18d44f109eb6d599b9167055c9178406288ca9772a4dfc55e5a37` |

这些信息用于防止后续把不同 arXiv 版本、会议版或截图来源混在一起。

---

## 2. RTLLM 到底评价什么

输入不是半成品 RTL，也不是波形，而是一份自然语言 `design_description.txt`。目标模型根据描述输出完整设计模块。

用符号表示：

```text
自然语言规格 L
    │
    ▼
LLM / 生成方法 F
    │
    ▼
候选 RTL V = F(L)
    ├── 综合检查：syntax
    ├── testbench：functionality
    └── 综合/实现：PPA quality
```

如果生成方法还使用提示工程 `P`，论文写成把 `L` 转成 `L_P`；如果允许人工修复，则可进一步写成 `H(F(L_P))`。但论文自己的五次生成实验明确没有对错误输出做额外人工修复或追加查询。

![RTLLM 三阶段工作流](./figures/rtllm-paper-fig1-workflow.png)

> 图 2：截自论文第 2 页 Figure 1。阶段 1 生成 RTL，阶段 2 用 testbench 做功能验证，阶段 3把生成 RTL 与人工 reference 综合后的 PPA 进行比较。

### 2.1 为什么是“逐级目标”

三个目标存在前置关系：

```text
语法不正确
  └─ 无法稳定进入仿真和综合

语法正确但功能错误
  └─ 可以得到网表和 PPA 数字，但数字没有设计意义

语法正确且功能正确
  └─ 才有资格比较面积、功耗和时序
```

这也是阅读 Table IV 时最容易忽视的一点：**错误功能 RTL 的面积很小，并不代表它质量更好。**

---

## 3. 三个评价目标的严格定义

### 3.1 Syntax goal

论文把 syntax goal 定义为候选 RTL 能被逻辑综合工具正确综合为网表，没有语法错误。

这里的“syntax”比单纯 parser 接受略强，因为综合还可能拒绝不可综合构造；但它仍然不保证功能正确。

论文实验使用 Synopsys Design Compiler，仓库的功能 Makefile 则先使用 Synopsys VCS 编译。两者都不是当前仓库自带的工具。

### 3.2 Functionality goal

通过题目自带 `testbench.v` 中的采样测试用例。

论文自己明确承认：穷举全部输入会让 testbench 过大，因此只采样合理数量的测试。于是：

```text
通过当前 testbench
≠ 对所有输入和时序情况的数学完备证明
```

这不是 RTLLM 独有的问题，而是 simulation-based RTL benchmark 的共同边界。

### 3.3 Quality goal

对语法和功能都正确的 RTL，进一步比较：

- area；
- power；
- timing，论文报告 WNS；
- 人工 reference 与 LLM 候选之间的质量差异。

论文称在综合和布局后测量 PPA，但公开仓库没有随附可重放的 Design Compiler、布局、工艺库和完整报告链。

---

## 4. 一道题的文件契约

论文为每个设计定义三类核心文件：

| 文件 | 论文符号 | 作用 |
|---|---|---|
| `design_description.txt` | `L` | 自然语言功能、模块名、I/O 名称与位宽 |
| `testbench.v` | `T` | 多组输入与期望输出，用于功能验证 |
| 人工 reference RTL | `V_H` | 正确功能基线，也作为 PPA 比较对象 |

当前 v2.0 目录实际还给每题放置了 Makefile。

典型关系是：

```text
design_description.txt
  指定 module 名、端口名、方向、位宽、行为、时序/复位约束
        │
        ├──────────────► LLM 生成 candidate.v
        │
        └──────────────► testbench.v 按同一模块接口实例化 DUT

verified_*.v
  作为人工参考实现与质量基线
```

自动评价能否可靠工作的关键，不只是 RTL 内容正确，还要求三份文件遵守同一个接口契约。

---

## 5. 论文的 30 题是什么

论文 Table II 声称共 30 个设计，其中：

- 11 个 arithmetic designs；
- 19 个 logic designs；
- 既有小型组合逻辑，也有状态机、FIFO、处理单元和 `risc_cpu`；
- Table II 同时列出人工 reference 的行数与综合面积，用于说明规模跨度。

![RTLLM 论文 30 题列表](./figures/rtllm-paper-table2-designs.png)

> 图 3：截自论文第 3 页 Table II。论文口径是 30 题，最后包含 `risc_cpu`；这张表是核对 Git v1.0 只见 29 题时的原始依据。

### 5.1 为什么不能拿当前 50 题直接重算 Table III

Table III 的分母是论文 v1.0 的 30 题；当前工作树是 v2.0 的 50 题。新增题、修订后的描述、testbench 和目录结构都会改变难度与计分。

因此正确做法是：

```text
复核论文表格 → 恢复并锁定论文对应的 v1.0 artifact 与 30 题清单
评价当前模型 → 明确报告 RTLLM v1.1 或 v2.0，不冒充论文 Table III
```

---

## 6. Git 版本历史核对

### 6.1 v1.0：Git 树是 29，不是论文表中的 30

对 `origin/v1.0` 的 `design_description.txt` 计数为 29。其任务名为：

```text
Johnson_Counter, RAM, accu, adder_16bit, adder_32bit,
adder_64bit, adder_8bit, alu, asyn_fifo, calendar,
counter_12, div_16bit, edge_detect, freq_div, fsm,
multi_16bit, multi_booth, multi_pipe_4bit, multi_pipe_8bit,
mux, parallel2serial, pe, pulse_detect, radix2_div,
right_shifter, serial2parallel, signal_generator,
traffic_light, width_8to16
```

与论文 Table II 对比，论文中的 `risc_cpu` 没出现在当前可见的 v1.0 Git 树中。

这不意味着论文一定“算错”，只意味着今天从 Git 分支恢复到的公开 artifact 与论文表不是完全同一份 30 题快照。

### 6.2 v1.1：仍为 29，但内容修订

README 说明 v1.1 更新了：

- 更清楚的设计描述；
- 更完整的 testbench；
- 更实用的 `auto_run.py`。

从文件名集合看，v1.0 到 v1.1 至少有以下变化：

| v1.0 名称 | v1.1 名称/变化 | 解读 |
|---|---|---|
| `Johnson_Counter` | `JC_counter` | 名称统一 |
| `adder_64bit` | `adder_pipe_64bit` | 更明确是流水加法器 |
| `multi_booth` | `multi_booth_8bit` | 位宽写入名称 |
| `mux` | 被移除 | 任务集合变化 |
| 无 | `synchronizer` | 新增任务 |

所以即使都是“29 题”，v1.0 和 v1.1 也不能只按题数视为同一版本。

### 6.3 v2.0：扩成 50 题并改为分层目录

当前工作树按四大类组织：

| 一级类别 | 题数 | 二级类别 |
|---|---:|---|
| Arithmetic | 19 | Adder、Substractor、Multiplier、Divider、Comparator、Accumulator、Other |
| Memory | 5 | FIFO、LIFO、Shifter |
| Control | 6 | Finite State Machine、Counter |
| Miscellaneous | 20 | Signal generation、RISC-V、Frequency divider、Others |
| 合计 | 50 | — |

每题位于：

```text
<一级类别>/<二级类别>/<设计名>/
```

这与旧脚本假定的：

```text
<设计名>/
```

不是同一种布局。

### P4 版本题数常见误解对照

| 版本口径 | 题数 | 说明 | 标记 |
|---|---|---|---|
| 论文 Table II | 30 | 含 `risc_cpu`，Git v1.0 不可见 | ⚠️ |
| Git `origin/v1.0` | 29 | README 声明实验基础，缺 `risc_cpu` | ✅ |
| 当前仓库 v2.0 | 50 | 新增/修订题，目录结构已变 | ⚠️ |
> 三个数字在各自版本语境中都能成立，混用会误以为“论文少一题”或“当前能直接复现论文表”。

### 6.4 README 自身混有不同版本口径

README 顶部明确写 v2.0 有 50 题，但 `Documents` 章节仍写“a total of 29 designs”。这段文字显然沿用了旧版说明。

因此引用 README 时必须指明具体段落，不能把同一页面里的两个数字当作相互验证。

---

## 7. 当前 v2.0 的 50 题全景

### 7.1 Arithmetic：19 题

```text
Adder:
  adder_8bit, adder_16bit, adder_32bit,
  adder_pipe_64bit, adder_bcd

Substractor:
  sub_64bit

Multiplier:
  multi_8bit, multi_16bit, multi_booth_8bit,
  multi_pipe_4bit, multi_pipe_8bit

Divider:
  div_16bit, radix2_div

Comparator:
  comparator_3bit, comparator_4bit

Accumulator:
  accu

Other:
  fixed_point_adder, fixed_point_substractor, float_multi
```

### 7.2 Memory：5 题

```text
asyn_fifo
LIFObuffer
right_shifter
LFSR
barrel_shifter
```

### 7.3 Control：6 题

```text
fsm
sequence_detector
counter_12
JC_counter
ring_counter
up_down_counter
```

### 7.4 Miscellaneous：20 题

```text
Signal generation:
  signal_generator, square_wave

RISC-V related blocks:
  clkgenerator, instr_reg, ROM, RAM, alu, pe

Frequency divider:
  freq_div, freq_divbyeven, freq_divbyodd, freq_divbyfrac

Others:
  calendar, traffic_light, width_8to16, synchronizer,
  edge_detect, pulse_detect, parallel2serial, serial2parallel
```

注意这里的 RISC-V 类只是若干相关子模块，并不等于论文 Table II 中完整的 `risc_cpu` 已重新出现。

---

## 8. Self-planning：真实方法流程

### 8.1 它是两次查询，不是工具反馈循环

论文的方法可精确还原成：

```text
第一次查询
  输入：原始设计规格 L
        + 请先用自然语言给出实现计划/推理步骤
        + 给出避免 Verilog 语法错误的建议
  输出：计划 P_plan + 语法注意事项 P_syntax

第二次查询
  输入：原始设计规格 L
        + 第一次的计划 P_plan
        + 第一次的语法注意事项 P_syntax
  输出：最终 RTL V
```

![RTLLM self-planning 示例](./figures/rtllm-paper-self-planning.png)

> 图 4：截自论文第 4 页 Code 1–4 附近。它展示第一次查询要求模型给 reasoning steps 和 syntax advice，再由第二次查询生成 RTL；还展示无 self-planning 时的语法/功能错误案例。

### 8.2 它不包含什么

论文 self-planning 不包含：

- 运行 VCS 后读取编译日志；
- 把 mismatch 波形反馈给 LLM；
- 多轮 debug 直到通过；
- 外部检索库；
- 人工修正中间 plan；
- 对失败 RTL 追加第三次查询。

论文还特别说明，五次候选是在五个并行 session 中用完全相同的描述生成；错误输出没有额外人工修复或另一轮 LLM 查询。

所以它应归类为：

```text
planning-enhanced prompting
```

而不是：

```text
simulation-feedback agent
```

### 8.3 为什么可能有效

它把两个容易同时遗漏的认知负担前置：

1. 先梳理状态、数据通路、循环或时序关系；
2. 先提醒变量声明、阻塞/非阻塞赋值、状态位宽等语法习惯；
3. 再生成最终代码。

论文用 `multi_16bit` 和 `adder_32bit` 举例，说明直接生成分别出现语法和 carry 功能错误，而 self-planning 版本生成正确候选。

但这两个例子只能说明机制的可能作用，整体有效性仍应看 Table III 的全题统计。

---

## 9. 实验协议

### 9.1 被评价的方法

论文实际列出六种配置：

| 配置 | 类型 |
|---|---|
| GPT-3.5 | 商业通用 LLM |
| GPT-4 | 商业通用 LLM |
| Thakur et al. | 16B、CodeGen 基础并用 Verilog 微调的学术模型 |
| StarCoder | 15B 通用代码模型，未专门做 Verilog 微调 |
| GPT-3.5 + self-planning | 两查询提示工程 |
| GPT-4 + self-planning | 两查询提示工程 |

论文摘要把重点放在 GPT-3.5 + self-planning，但 Table III 也报告 GPT-4 + self-planning。

### 9.2 每题五次生成

每个设计、每种方法生成 5 份候选：

```text
30 designs × 5 candidates per design
```

随机性因此被显式纳入统计，但论文的 functionality 列不是普通 pass@1。

### 9.3 商业工具

论文实验工具为：

| 阶段 | 工具/设置 |
|---|---|
| 功能仿真 | Synopsys VCS |
| 逻辑综合 | Synopsys Design Compiler |
| 综合优化 | `compile_ultra` |
| 时序设置 | 频率设得很高，使所有设计出现负 slack，便于 WNS 比较 |

“高频率使所有设计出现负 slack”是人为建立统一比较压力，不表示这些 WNS 就是某个真实产品频率下的 signoff 结果。

---

## 10. Table III 指标怎样读

### 10.1 Syntax 百分比

表中每个任务的 Syntax 是 0–5，表示五个候选中语法正确的数量。

最后一行的百分比，是所有任务、所有候选的聚合语法正确比例：

```text
syntax rate = 语法正确候选总数 / (30 × 5)
```

它不是“30 题中解决了多少题”。

### 10.2 Func 数量

每题只要五个候选中至少一个：

1. 先语法正确；
2. 再通过 testbench；

该题的 Func 就记作成功。

所以末行 `19/30` 的语义接近在五次采样下的 task-level success，即常被后续工作称为 pass@5 的口径，但论文表格直接报告的是成功题数。

### 10.3 无语法正确候选时

如果某题五个候选全部语法失败，Func 不能进入有效功能验证，表中用 `-` 表示。

### 10.4 通过 testbench 的边界

通过表示通过当前采样用例，不是 formal equivalence，也不是穷举证明。

---

## 11. Table III 原始结果

![RTLLM 语法与功能结果](./figures/rtllm-paper-table3-results.png)

> 图 5：截自论文第 5 页 Table III。每格 Syntax 是五次生成中语法正确的数量；Func 是该题是否至少有一个语法正确候选通过 testbench。

论文报告：

| 方法 | Syntax | Func |
|---|---:|---:|
| GPT-3.5 | 55% | 10/30 |
| GPT-4 | 81% | 15/30 |
| Thakur et al. | 40% | 5/30 |
| StarCoder | 27% | 5/30 |
| GPT-3.5 + self-planning | 73% | 14/30 |
| GPT-4 + self-planning | 90% | 19/30 |

### 11.1 Self-planning 的增益

论文数据中：

| 基础模型 | Syntax 变化 | Func 变化 |
|---|---:|---:|
| GPT-3.5 → GPT-3.5 + SP | 55% → 73%，+18 个百分点 | 10 → 14，+4 题 |
| GPT-4 → GPT-4 + SP | 81% → 90%，+9 个百分点 | 15 → 19，+4 题 |

这支持“先规划再写 RTL”在该实验中有效。

但不能从中推出：

- 所有模型都必然同幅度受益；
- 对更长、多模块、协议密集的任务仍有相同增益；
- 两次调用的成本/延迟与一次调用等价；
- 2026 年的新模型仍保持相同排名。

### 11.2 论文给出的整体排序

论文按正确性概括为：

```text
GPT-4 + SP
  > GPT-4
  > GPT-3.5 + SP
  > GPT-3.5
  > Thakur et al.
  >= StarCoder
```

该排序只属于论文的模型版本、prompt、30 题 v1.0 和五次采样协议。

---

## 12. Table IV：PPA 结果怎样读

![RTLLM PPA 结果表](./figures/rtllm-paper-table4-ppa.png)

> 图 6：截自论文第 6 页 Table IV。比较人工 reference、GPT-3.5、GPT-4、Thakur et al. 与 GPT-3.5 + self-planning 的面积、功耗和时序；StarCoder 因篇幅未列。

### 12.1 表中的候选筛选

论文先对语法正确候选得到网表与 PPA。功能错误结果用红色标识；只有语法、功能都正确的候选才有资格被标为某项 best quality。

正确的解读顺序应是：

```text
先看候选是否正确
  └─ 再比较该候选的 area / power / timing
```

### 12.2 Best Quality Num

论文最后一行统计各来源在三个单独目标上获得最佳值的题数：

| 来源 | Area 最佳数 | Power 最佳数 | Timing 最佳数 |
|---|---:|---:|---:|
| 人工 reference | 3 | 7 | 5 |
| GPT-3.5 | 2 | 2 | 5 |
| GPT-4 | 8 | 5 | 6 |
| Thakur et al. | 2 | 1 | 2 |
| GPT-3.5 + self-planning | 5 | 7 | 5 |

论文据此说 GPT-4 最好、GPT-3.5 + SP 次之，并指出部分生成 RTL 在单项 PPA 上超过人工 reference。

### 12.3 论文自己承认的统计局限

area、power、timing 有强 trade-off。把三个目标分别数“第一名”，再按数量直观比较，不等于做了严格多目标 Pareto 评价。

论文原文因此把这种汇总称为 straightforward but less rigorous comparison。

后续如果复现实验，更合理的补充包括：

- Pareto front；
- 相对人工 reference 的归一化 PPA；
- 固定时序约束下的面积/功耗；
- 固定面积预算下的频率；
- 多随机种子综合结果；
- 对错误候选完全屏蔽 PPA 排名。

---

## 13. 当前仓库代码地图

```text
RTLLM/
├── README.md
├── File_list.md
├── auto_run.py
├── Arithmetic/
├── Memory/
├── Control/
├── Miscellaneous/
├── _chatgpt35/
│   ├── t1/ ... t5/
├── _chatgpt4/
│   ├── t1/ ... t5/
├── _pic/
├── 2308.05345_RTLLM.pdf
├── 2503.15112_OpenLLM-RTL.pdf
├── figures/
└── runs/
```

### 13.1 50 题目录

当前每题都有：

| artifact | 数量 |
|---|---:|
| `design_description.txt` | 50 |
| `testbench.v` | 50 |
| `makefile` | 50 |
| `verified_*.v` | 50 |

这说明 benchmark 数据主体齐全，但不自动说明每组文件可以原样互换运行。

### 13.2 历史生成输出

仓库保留：

| 目录 | trial 数 | 每 trial 文件数 | 总数 |
|---|---:|---:|---:|
| `_chatgpt35` | 5 | 29 | 145 |
| `_chatgpt4` | 5 | 29 | 145 |

它们是论文/旧版附近留下的生成 artifact，可以用于代码质量审阅或在恢复旧版 testbench 后复核。

它们不是本机重新调用 API 的结果，也不覆盖 v2.0 新增的 21 题。

---

## 14. Makefile 的真实工具链

README 示例与当前题目 Makefile 的核心路径是：

```text
make vcs
  └─ VCS 编译 candidate + testbench

make sim
  └─ 执行 simv

make clean
  └─ 清理编译/仿真产物
```

这套官方入口使用 **Synopsys VCS**，不是 Icarus Verilog。

此前短版 `模型梳理.md` 把它写成 Icarus/综合工具，容易让人误以为仓库已有官方 Icarus 路径；本次已按代码纠正。

### 14.1 仓库没有什么

当前未看到：

- VCS 安装与 license 配置；
- Python 依赖锁定；
- 容器或 Conda 环境；
- Design Compiler 脚本；
- 论文所用工艺库；
- 完整时钟/约束文件；
- PPA 原始报告；
- 物理布局脚本；
- portable Icarus/Verilator evaluator。

因此“代码开源”主要指题目、testbench、reference、部分生成结果和一个批处理脚本，而不是论文三目标的完整环境镜像。

---

## 15. `auto_run.py` 调用链

脚本没有 `if __name__ == "__main__"`，导入时就开始执行。

它的真实流程是：

```text
模块导入
  ├─ 创建 tqdm(total=290)
  ├─ 固定 50 个 design_name
  ├─ 固定模型输出根目录 path
  └─ 从 t1 开始循环，只要 path/tN 存在
       └─ test_one_file(tN)
            └─ 对每个 design_name
                 ├─ 若 <design>/makefile 存在
                 ├─ 把 ${TEST_DESIGN} 替换成输出 RTL 路径
                 ├─ chdir(<design>)
                 ├─ os.system("make vcs")
                 ├─ 若 simv 存在，则 syntax_success += 1
                 ├─ 最多等待 8 秒运行 make sim
                 ├─ output.txt 含 Pass/pass，则 func_success += 1
                 ├─ 恢复 Makefile
                 └─ make clean
       ├─ cal_atk(..., k=1)
       └─ 统计至少一次 syntax/function 成功的题数
```

这段代码的意图很清楚：把不同 trial 的同名 RTL 依次替换进每题 Makefile，自动汇总。

但意图与当前可执行状态不是一回事。

---

## 16. `auto_run.py` 与 v2.0 不兼容

### 16.1 仍按扁平目录找题

脚本判断：

```python
os.path.exists(f"{design}/makefile")
```

并执行：

```python
os.chdir(design)
```

当前路径却是：

```text
Arithmetic/Adder/adder_8bit/makefile
```

从仓库根目录运行时，`adder_8bit/makefile` 不存在，50 题都会被跳过。

### 16.2 设计列表扩成 50，不等于适配完成

当前 `design_name` 的确有 50 个名字，但目录遍历、输出路径和进度总数没有一起按 v2.0 改造。

这是一类典型 bug：

```text
数据清单升级了
≠ 执行器的数据定位契约也升级了
```

### 16.3 模型输出根目录硬编码

脚本写死：

```text
/home/coguest/luyao/SmallDesigns/chatgpt35/
```

没有命令行参数，也不是当前仓库内 `_chatgpt35` 的相对路径。换机器必然先失败或零样本退出。

### 16.4 新题没有历史输出

即使修好目录遍历，`_chatgpt35/t1` 和 `_chatgpt4/t1` 等目录各只有 29 个旧版 RTL，v2.0 新增 21 题没有候选。

因此不能把 `design_name` 扩成 50 后的统计直接叫作 v2.0 结果。

---

## 17. `auto_run.py` 的评分和进程问题

### 17.1 pass@k 平均分母多加了 1

`cal_atk` 对每题计算无偏 pass@k 形式：

```text
1 - C(n-c, k) / C(n, k)
```

但在求均值前执行了：

```python
sum_list.append(0)
```

因此分母从 `design_count` 变成 `design_count + 1`，所有分数都会被系统性压低。

例如理论上 50 题均值为 `S/50`，脚本得到 `S/51`。

### 17.2 超时不终止子进程

`exec_shell` 用 Python Thread 包裹 `os.system`：

- 8 秒后如果线程仍活着，只返回 0；
- 没有 kill `make sim` 或 `simv`；
- Thread 设置为 `daemon=False`；
- 后续清理可能与仍在运行的仿真竞争。

这不是可靠的 wall-clock timeout。

### 17.3 用 `simv` 是否存在判断语法成功

脚本不检查 `make vcs` 的 return code，只检查当前目录是否存在 `simv`。

如果上次异常退出留下旧 `simv`，本次编译失败仍可能误记为语法成功。脚本虽然正常路径末尾会 `make clean`，但运行前没有先清理，崩溃路径也不保证恢复。

### 17.4 用字符串包含关系判断功能成功

脚本规则是：

```python
if "Pass" in output or "pass" in output:
```

因此以下输出也可能被误判：

```text
0 tests passed, design failed
not pass
bypass mode error
```

可靠判分应使用：

- 明确的退出码；
- 唯一、锚定的终止标志；
- mismatch 计数；
- 编译和仿真日志的结构化解析。

### 17.5 直接改写 Makefile

脚本把 `${TEST_DESIGN}` 替换后覆盖原 Makefile，正常完成时再恢复。

若 VCS、读取日志或 Python 中途异常，Makefile 可能保留机器相关绝对路径。更安全的方式是通过环境变量或 `make TEST_DESIGN=...` 传参，不改源文件。

### 17.6 `os.system` 返回码被丢弃

编译、仿真、清理都主要用 `os.system`，没有对 return code 做统一检查和记录，无法可靠区分：

- 工具不存在；
- license 失败；
- RTL 编译失败；
- testbench 编译失败；
- 仿真超时；
- 功能 mismatch；
- 清理失败。

### 17.7 进度总数陈旧

`tqdm(total=290)` 与常见组合都对不上：

- 旧版 29 题 × 5 次 = 145；
- 两个模型各 145，共 290；
- 但脚本一次只指向一个硬编码模型目录；
- v2.0 50 题 × 5 次 = 250。

这个数字更像把 GPT-3.5 和 GPT-4 两套旧输出总数相加后的遗留值。

---

## 18. 文件命名与接口契约问题

### 18.1 `multi_pipie` 与 `multi_pipe`

`File_list.md` 写：

```text
multi_pipie_4bit
multi_pipie_8bit
```

实际目录和 `auto_run.py` 写：

```text
multi_pipe_4bit
multi_pipe_8bit
```

OpenLLM-RTL 论文 Table 2 也沿用 `multi_pipie` 拼写。做程序匹配时不能直接把论文字符串当目录名。

### 18.2 `freq_divfrac` 与 `freq_divbyfrac`

`auto_run.py` 的列表为：

```text
freq_divfrac
```

当前目录和规格为：

```text
freq_divbyfrac
```

因此即使改成递归查找，按脚本名字仍找不到这题。

### 18.3 `calendar` 与 `calender`

任务名是 `calendar`。GPT-3.5 保留输出中存在 `calender.v` 拼写，而 GPT-4 对应文件使用 `calendar.v`。

若 evaluator 严格拼接文件名，GPT-3.5 的该样本会因路径问题而不是 RTL 功能问题丢失。

### 18.4 `substractor` 与 `subtractor`

目录/规格采用 `fixed_point_substractor`，部分 reference top module 使用正确英语拼写 `fixed_point_subtractor`。

testbench 若实例化前者，后者不能直接作为 DUT，除非改名或加 wrapper。

### 18.5 规格 module 与 reference top 不完全一致

静态提取 50 题后：

| 检查 | 数量 |
|---|---:|
| 规格指定 module 与 reference 首个 top module 完全一致 | 21 |
| 不完全一致 | 29 |

大量 reference 使用 `verified_<task>` 作为 top，而 testbench 按规格名实例化。

这不一定说明 reference 的逻辑错；它说明当前 reference 文件并非普遍可以“直接替换候选文件后运行”。仓库所说“reference 都通过了 testbench”很可能依赖当时的改名、宏、wrapper 或旧版 testbench，当前 artifact 没完整保存这一转换步骤。

---

## 19. 为什么这次没有重复跑推理

用户此前已明确：项目里的 `模型推理.md`、日志和输出是已经执行过的证据，不需要为了写文档重复调用模型。

RTLLM 目录当前没有新的本地模型推理记录，但有官方保留的 290 份生成 RTL。对本篇而言，更重要的工作是判断它们究竟对应哪个 benchmark 版本，以及现有 evaluator 能否正确运行。

本次没有执行以下动作：

| 动作 | 是否执行 | 原因 |
|---|---|---|
| GPT-3.5/GPT-4 API 生成 | 否 | 不是必要的代码审计动作；模型版本与论文时期也已变化 |
| 本地开源 LLM 推理 | 否 | 会产生另一种模型配置，不能复现论文表 |
| 模型训练 | 否 | RTLLM 本身是 benchmark，论文没有发布需训练的 RTLLM 模型 |
| VCS 仿真 | 否 | 商业工具环境不在公开 artifact 中 |
| Design Compiler 综合 | 否 | 工艺库、脚本与环境不完整 |
| Icarus 替代仿真 | 否 | 官方路径不是 Icarus；未先修复 evaluator/data contract 时替代运行只会混淆错误来源 |

这不是“没有做复现”，而是把复现边界收紧到当前证据真正支持的层级。

---

## 20. 当前能证明与不能证明的内容

### 20.1 已能证明

- 本地 PDF 与论文元数据可追溯；
- 论文报告的是 v1.0、30 题、每题五次生成；
- 当前 Git v1.0/v1.1 各只有 29 份 description；
- 当前 v2.0 有 50 套 description、testbench、Makefile 和 reference；
- v2.0 是四大类分层目录；
- GPT-3.5/GPT-4 各有 145 份旧版生成 artifact；
- self-planning 是两次查询，不是运行日志反馈；
- `auto_run.py` 与当前目录不兼容；
- `cal_atk` 平均分母有额外零项；
- Makefile 的官方仿真器是 VCS；
- 规格、目录、脚本和 reference 之间存在多处命名/接口错位。

### 20.2 不能证明

- 本机重新生成得到了论文同样的 55%/81% 等数值；
- 当前模型 API 与 2023 年论文模型行为相同；
- 290 份历史 RTL 在当前 v2.0 testbench 上保持论文分数；
- 当前 50 个 reference 都能原样通过当前 Makefile；
- Table IV 的 PPA 可在没有原工艺/脚本时重算；
- testbench 通过等价于形式完备功能正确；
- GPT-4 生成 RTL在真实工程中整体优于人工 RTL。

---

## 21. 论文—代码—数据对应表

| 论文概念 | 当前 artifact | 对应程度 | 说明 |
|---|---|---|---|
| 30 个 v1.0 设计 | Git v1.0 的 29 个目录 | 部分对应 | 缺 `risc_cpu` |
| 自然语言规格 `L` | `design_description.txt` | 高 | 当前 v2.0 有 50 份 |
| testbench `T` | `testbench.v` | 高 | 当前 v2.0 有 50 份，使用 VCS |
| 人工 reference `V_H` | `verified_*.v` | 中 | 有 50 份，但 29 题 top name 不完全匹配规格 |
| 五次 GPT-3.5 生成 | `_chatgpt35/t1..t5` | 中 | 29 题 × 5，不是 30/50 |
| 五次 GPT-4 生成 | `_chatgpt4/t1..t5` | 中 | 29 题 × 5，不是 30/50 |
| 自助批处理 | `auto_run.py` | 低到中 | 旧布局思路保留，但当前 v2.0 不能直接运行 |
| Syntax 评价 | VCS/综合 + 脚本 | 部分 | 脚本只看 `simv` 是否存在 |
| Functionality 评价 | VCS + testbench | 部分 | 用 `Pass/pass` 子串判定过宽 |
| pass@k | `cal_atk` | 有实现但有 bug | 平均时额外追加 0 |
| PPA 评价 | README 图片、论文表 | 低 | 原始 DC/工艺/布局脚本和报告未开放 |
| Self-planning | 论文 prompt 示例 | 低 | 仓库没有独立 prompt/inference 脚本 |

---

## 22. 如果要做严格复现，应怎样分阶段

### 22.1 阶段 A：先冻结版本

必须先选一个目标：

```text
A1. 复核论文：RTLLM v1.0、论文 30 题
A2. 与后续工作对齐：RTLLM v1.1、29 题
A3. 做当前基准：RTLLM v2.0、50 题
```

三者应分别出结果，不应合表。

### 22.2 阶段 B：建立 manifest

对每题显式记录：

```yaml
id: adder_8bit
version: v2.0
category: Arithmetic/Adder
description: .../design_description.txt
testbench: .../testbench.v
reference: .../verified_adder_8bit.v
expected_top: adder_8bit
reference_top: verified_adder_8bit
candidate_pattern: ...
```

这样能在运行前发现命名不一致，而不是把路径错误统计成模型错误。

### 22.3 阶段 C：先验证 reference

每题先让 reference 走与 candidate 完全相同的编译/仿真路径。

只有 reference 通过，题目才进入模型评价；否则标为 benchmark infrastructure failure。

### 22.4 阶段 D：结构化执行状态

建议每个 candidate 输出：

```json
{
  "compile_status": "pass|fail|timeout|tool_error",
  "simulation_status": "pass|mismatch|timeout|tool_error",
  "compile_returncode": 0,
  "simulation_returncode": 0,
  "mismatch_count": 0,
  "elapsed_seconds": 1.23,
  "stdout_log": "...",
  "stderr_log": "..."
}
```

不能只保存一个 `Pass` 布尔值。

### 22.5 阶段 E：再算 pass@k

对每题有 `n` 个样本、其中 `c` 个成功时：

```text
pass@k = 1 - C(n-c, k) / C(n, k)
```

然后直接对有效题均值，不追加虚构的零样本。

同时报告：

- 有效题数；
- reference 失败题数；
- 缺失候选题数；
- 编译失败、仿真 mismatch、timeout、tool error 的分布。

### 22.6 阶段 F：最后做 PPA

只对功能正确候选做 PPA，并固定：

- 工艺库；
- 工具版本；
- 时钟/IO/负载约束；
- 综合 effort；
- 物理实现阶段；
- corner；
- 多线程/随机性设置。

否则 PPA 数字不能跨实验比较。

---

## 23. 对当前脚本的最小修复清单

本篇按用户要求只做审阅和文档，没有改 evaluator。若后续要修，优先级如下：

1. 增加 `main()` 与 CLI，不在 import 时执行；
2. 使用 manifest/递归路径，不用 50 个裸目录名；
3. 把输出根目录、trial 数和工具命令参数化；
4. 使用 `subprocess.run(..., timeout=...)` 并终止进程组；
5. 运行前清理独立临时 build 目录；
6. 检查编译、仿真 return code；
7. 用明确 pass/fail 协议，不做任意子串匹配；
8. 不覆盖仓库 Makefile；
9. 修复 `freq_divfrac` 等名称；
10. 删除 `sum_list.append(0)`；
11. 每个样本保存结构化记录；
12. 在汇总中区分 missing、tool error、syntax error 和 function error；
13. 首先跑 reference self-check；
14. 明确 v1.0/v1.1/v2.0 的题集 manifest。

---

## 24. 复现等级矩阵

### P10 当前复现进度条
```text
R0  R1  R2  R3  R4  R5
[██░░░░░░░░░░░░░░]  R1 / R5
 ↑ 当前位置：静态审计完成，论文 LLM / VCS / PPA 流程未重跑
```

| 层级 | 当前状态 | 等级判断 |
|---|---|---|
| PDF 与论文方法 | 已核对 | 完成 |
| v1.0/v1.1/v2.0 版本题数 | 已用 Git 与文件树核对 | 完成 |
| 50 题规格/testbench/reference 静态结构 | 已核对 | 完成 |
| 官方 GPT 输出数量与覆盖版本 | 已核对 | 完成 |
| `auto_run.py` 调用链与缺陷 | 已代码级核对 | 完成 |
| 本地重新调用论文 LLM | 未执行 | 不可声称 |
| 旧版 290 份输出全量 VCS 复验 | 未执行 | 不可声称 |
| 50 个 reference 的当前路径自检 | 因接口/工具边界未执行 | 不可声称 |
| 论文 Table III 重算 | 未完成 | 不可声称 |
| 论文 Table IV PPA 重算 | 缺商业环境/工艺/脚本 | 不可声称 |

综合等级：**R1**。

如果未来恢复旧版 evaluator 并把官方 290 份输出全量重编译/重仿真，可上升到 R3 artifact verification；只有在相同模型、prompt、版本和工具下重新生成并重算主要表格，才接近 R4。

---

## 25. 与 VerilogEval 的差异

RTLLM 与 VerilogEval 都做自然语言到 RTL，但研究侧重点不同：

| 维度 | RTLLM | VerilogEval |
|---|---|---|
| 早期题数 | 30（公开 Git 快照 29） | 156 Human + 143 Machine 等版本口径 |
| 任务规模 | 更强调 design-level 和复杂模块 | 大量短规格功能题 |
| 评价 | syntax、function、PPA | 主要功能正确性与 pass@k |
| reference PPA | 有论文比较 | 不是主要目标 |
| 官方仿真器 | VCS | Icarus Verilog |
| 提示方法 | self-planning | 原版重点不在 Agent 反馈 |

因此 RTLLM 的独特价值是把“能写对”延伸到“写对之后的设计质量”，但其 PPA artifact 开放度反而更弱。

---

## 26. 组会应怎样讲

### 26.1 推荐标题

**“RTLLM：从语法、功能到 PPA 的设计级 RTL 基准，以及 30/29/50 题版本真相”**

### 26.2 推荐 10 页结构

1. 为什么仅靠 syntax 或 BLEU 不能评价 RTL；
2. RTLLM 三目标工作流；
3. 一道题的 description/testbench/reference 契约；
4. 论文 30 题与复杂度范围；
5. self-planning 两查询流程；
6. Table III 指标语义；
7. self-planning 的结果增益；
8. Table IV 的 PPA 与多目标局限；
9. v1.0 30 vs Git 29 vs v2.0 50；
10. `auto_run.py` 和公开 artifact 的真实复现边界。

### 26.3 最值得讨论的三个问题

1. testbench 通过能在多大程度上代表功能正确？
2. PPA 是否应只报单项最佳数，还是用 Pareto/约束化评价？
3. benchmark 更新后，如何保证目录、规格、testbench、reference 和 evaluator 的版本契约同步？

---

## 27. 可以继续做的研究方向

### 27.1 版本化 benchmark manifest

把每个版本的题目、hash、top module、testbench、reference、期望终止标志写入机器可读 manifest，可以直接解决当前 30/29/50 混用与命名漂移。

### 27.2 Reference-first evaluator certification

每次 release 前自动执行：

```text
reference compile
  → reference simulation
  → negative-control mutation
  → timeout/failure-path test
  → scoring self-consistency
```

这比只声明“reference 已验证”更可审计。

### 27.3 Simulation + formal 双轨

对小模块补形式验证，对大模块保留仿真：

```text
small combinational/sequential block → equivalence / assertions
complex protocol/design block       → simulation + coverage
```

### 27.4 正确性约束下的 PPA 搜索

让模型或 Agent 在每次 RTL 变换后都先通过功能门，再比较 PPA；保存完整 Pareto front，而不是只留“最小面积”候选。

### 27.5 隐藏测试与污染控制

RTLLM 已公开多年，题目和 reference 可能进入预训练语料。后续研究应增加：

- 私有 holdout；
- 语义等价但表述变化的规格；
- 接口随机化；
- parameter 扰动；
- 多模块新题；
- 时间切分或仓库来源审计。

---

## 28. 文件导航

### 28.1 论文与说明

- [RTLLM 原论文](./2308.05345_RTLLM.pdf)
- [OpenLLM-RTL 原论文](./2503.15112_OpenLLM-RTL.pdf)
- [仓库 README](./README.md)
- [v2.0 题目分类](./File_list.md)
- [短版模型梳理](./模型梳理.md)

### 28.2 代码与记录

- [批处理脚本](./auto_run.py)
- [静态审计 JSON](./runs/static_audit_20260802.json)
- [OpenLLM-RTL 逐论文详解](./OpenLLM-RTL论文与代码复现详解.md)

### 28.3 论文截图

- `figures/rtllm-paper-title-table1.png`
- `figures/rtllm-paper-fig1-workflow.png`
- `figures/rtllm-paper-table2-designs.png`
- `figures/rtllm-paper-self-planning.png`
- `figures/rtllm-paper-table3-results.png`
- `figures/rtllm-paper-table4-ppa.png`

---

## P7 一句话组件摘要
| 组件 | 一句话结论 |
|---|---|
| 论文方法 | 提出 syntax / functionality / quality 三目标评价与 self-planning 两次查询 |
| v1.0 / v1.1 | Git 可见树为 29 题，与论文 30 题不完全一致，不能混用 |
| v2.0 数据 | 50 题、四大类、分层目录，数据主体齐全但接口契约需再核对 |
| 官方历史输出 | 290 份旧版生成 RTL，只覆盖 29 题，不覆盖 v2.0 新增题 |
| `auto_run.py` | 意图清晰，但与 v2.0 目录、硬编码路径和评分逻辑多处不兼容 |
| PPA 评价 | 论文报告完整，但商业工具、工艺库与脚本未随仓库开放 |
| self-planning | 两次提示工程，不是仿真反馈 Agent，增益仅限论文实验配置 |

---

## 29. 最终判断

RTLLM 的研究价值依然很清楚：它把 RTL 生成从“像不像代码”推进到“能不能综合、功能对不对、PPA 是否有用”，还用非常轻量的 self-planning 展示了提示结构对硬件代码生成的影响。

但代码核对也说明，benchmark 的论文概念比当前公开执行 artifact 更完整：

- 论文是 30 题，Git v1.0/v1.1 可见树是 29 题；
- 当前 v2.0 虽有 50 题，批处理脚本仍按旧扁平目录工作；
- 历史模型输出只覆盖 29 题；
- reference top module 与规格有较多不一致；
- PPA 所需商业工具、工艺与脚本没有完整开放；
- pass@k、timeout 和成功字符串判断还需要修正。

因此最准确的表述是：

> **本地已完成 RTLLM 论文、Git 版本、50 题数据、290 份历史生成物和评价脚本的静态审计；没有重新运行论文模型、VCS 或 PPA 流程，论文表格尚未本地复现。**


## 30. 讨论问题

1. 如果 syntax 正确但功能错误，我们是否应该在报告 PPA 时完全屏蔽该候选？
2. self-planning 的两次查询结构是否仍然是当前 LLM 的最优 prompting 策略，还是已有更强的 tool-use / feedback agent？
3. 在 benchmark 升级过程中，应建立怎样的 manifest / CI 规则，才能避免目录、reference 与 evaluator 的版本漂移？
