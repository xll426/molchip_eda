# ChatEDA：论文、开源代码与复现边界详解

> 论文：**ChatEDA: A Large Language Model Powered Autonomous Agent for EDA**  
> 作者：Haoyuan Wu, Zhuolun He, Xinyun Zhang, Xufeng Yao, Su Zheng, Haisheng Zheng, Bei Yu  
> 发表：IEEE TCAD 2024；本地 PDF 为 arXiv v4（2024-09-21）  
> 本地论文：[2308.10204_ChatEDA.pdf](./2308.10204_ChatEDA.pdf)  
> 本地代码：[ChatEDA](./)；同内容历史目录：[ChatEDAv1](../ChatEDAv1/)  
> 上游仓库：<https://github.com/wuhy68/ChatEDA>  
> 静态核验 commit：`02bb522a98f759595fbfce6bee33f64ef02ce3a5`  
> 核验日期：2026-08-02  
> 本文只使用论文、源码、数据和既有记录；**没有重新调用 LLM、训练模型或执行 OpenROAD**。

---

```text
┌─────────────────────────────────────────────────────────────────────────┐
│ P1 任务定义                                                              │
├─────────────────────────────────────────────────────────────────────────┤
│ Input:  自然语言后端 EDA 需求（设计、平台、目标阶段、参数/优化目标）        │
│ Output: 任务分解 + Python EDA 脚本 + 调用 OpenROAD/ORFS 执行后的 PPA    │
│         结果/报告                                                         │
│ Supervision: 训练数据由 GPT-3.5/4 self-instruct 生成并经人工修订；评测由 │
│              人工按 A/B/C 等级打分，无自动功能 oracle                     │
│ Why-hard: EDA 流程长且阶段依赖严格；API 参数 grounding 复杂；完整训练数据 │
│           与模型权重未公开；wrapper 实现存在多处缺陷；人工评分可复现性差   │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 0. 先给结论

ChatEDA 的研究目标不是生成 RTL，而是让大语言模型充当 EDA 流程的控制器：

```text
自然语言需求
  → AutoMage 理解需求并分解任务
  → 依据 Python EDA API 生成脚本
  → Python 包装器调用 OpenROAD/OpenROAD-flow-scripts
  → 完成 RTL-to-GDSII 阶段或读取 PPA 指标
```

论文方法本身清晰，主要贡献有三点：

1. 把自然语言、任务分解、脚本生成和 EDA 工具执行连成一个 Agent 流程；
2. 用约 1,500 条 EDA 工具指令微调 Llama2，得到 AutoMage；
3. 用更丰富的 EDA 数据、约 110K 开放代码指令、解释式微调和 CoT，得到 AutoMage2。

但当前开源仓库不是完整的 ChatEDA 系统。实际公开的是：

- 50 条训练样例；
- 50 条 ChatEDA-Bench 自然语言需求；
- 一个只打印 `done` 的 API 文档桩；
- 一个 662 行的 OpenROAD-flow-scripts 包装原型；
- 两篇论文 PDF 和 README。

仓库没有公开：

- AutoMage / AutoMage2 权重；
- 训练代码和完整训练集；
- controller 推理入口及 prompt 编排；
- 论文使用的候选输出、人工评分标签和自动评测器；
- 固定版本的 OpenROAD-flow-scripts、PDK、设计输入和环境文件。

因此，正确的复现判断是：

| 层级 | 当前本地状态 | 结论 |
|---|---:|---|
| 论文方法理解 | R0 | 可完整梳理 |
| 公开数据/API 静态核对 | R1 | 已完成 |
| AutoMage/AutoMage2 推理 | R0 | 缺权重与推理代码 |
| OpenROAD 全流程执行 | R0 | 缺固定 ORFS/PDK/设计环境，且包装器存在实质缺陷 |
| 论文 Figure 5 结果复现 | R0 | 缺模型输出、执行记录与人工评分标签 |

这里的 `R0/R1` 沿用总索引定义：R0 是论文或资料级核对，R1 是代码/数据静态核对；不能把 R1 写成“端到端已跑通”。

---

## 1. 论文与本地文件身份

### 1.1 论文文件

本地 PDF：

- 路径：[2308.10204_ChatEDA.pdf](./2308.10204_ChatEDA.pdf)
- 页数：14 页；
- 文件大小：1,516,905 bytes；
- SHA256：`3aab84fcb174113505ada3e2db86c97ac0a5e55bd953c4ce2bcb4517c1b0bd28`；
- 版本标识：PDF 页边标有 `arXiv:2308.10204v4 [cs.AR] 21 Sep 2024`。

![论文首页与 Figure 1](./figures/chateda-paper-title-fig1-overview.png)

*图源：本地论文 PDF 第 1 页裁剪，包含标题、摘要与 Figure 1；用于确认 controller/executor 边界和三阶段系统总览。*

Figure 1 已经给出最重要的系统边界：

- AutoMage 是 controller；
- EDA tools 是 executor；
- controller 接收用户需求和 API specifications；
- 流程包含 task decomposition、script generation、task execution；
- 输入是 RTL，执行端目标可以到 GDSII。

### 1.2 仓库身份

当前本地仓库：

```text
remote : https://github.com/wuhy68/ChatEDA.git
commit : 02bb522a98f759595fbfce6bee33f64ef02ce3a5
date   : 2025-05-21
subject: Update README.md
```

另有目录 [ChatEDAv1](../ChatEDAv1/)，其 remote 是：

```text
https://github.com/wuhy68/ChatEDAv1.git
```

静态比较结果是：两个目录处于同一 commit；排除 `.git`、论文 PDF、`模型梳理.md` 和本次生成的审计材料后，README、LICENSE、`api_doc/` 与 `data/` 内容一致。

这意味着：

> `ChatEDA` 与 `ChatEDAv1` 不是当前本地保存的两个不同实现版本，不能把二者当成可比较的 v1/v2 代码库。

更值得注意的是，`ChatEDA/README.md` 中的数据和 API 链接仍然指向 `ChatEDAv1`。当前 `ChatEDA` 仓库更像论文与公开材料的汇总入口，而不是新实现。

---

## 2. ChatEDA 解决的具体问题

传统后端流程通常需要工程师：

1. 理解设计、工艺和约束；
2. 按顺序调用综合、floorplan、placement、CTS、routing 等步骤；
3. 编写 Tcl、Makefile 或 Python；
4. 调整利用率、密度、时钟周期、宏间距等参数；
5. 读取 PPA 和时序报告；
6. 根据目标重新搜索参数。

论文要把“自然语言需求”变成“可执行的 EDA 脚本”。它主要面向三类任务：

| 类型 | 论文比例 | 典型需求 |
|---|---:|---|
| Simple Flow Calls | 30% | 从 setup 跑到某个指定阶段 |
| Complex Flow Calls | 30% | 遍历多个参数组合、满足特定条件 |
| Parameter Tuner Calls | 40% | 调用调参功能优化 area/power/performance |

ChatEDA 关注的是工具使用、调用顺序、参数放置和脚本正确性，而不是电路功能生成。

---

## 3. 论文完整方法流程

## 3.1 总流程

论文主链可以拆成七个对象：

| 对象 | 作用 | 当前仓库是否有 |
|---|---|---:|
| 用户 requirement | 描述设计、平台、阶段、参数、优化目标 | benchmark 中有 50 条 |
| API specification | 告诉模型有哪些函数、参数与阶段依赖 | 有文档桩 |
| AutoMage controller | 任务分解与脚本生成 | 无权重、无推理代码 |
| task list | 按顺序组织调用 | 只在训练样例输出和论文案例中出现 |
| Python script | 实际调用 `chateda` API | 有样例，没有独立生成结果归档 |
| Python EDA wrapper | 把 API 映射到 EDA 命令 | 有原型实现 |
| OpenROAD executor | 执行物理设计脚本 | 不在仓库中 |

### 3.2 任务分解

模型先把用户需求解析为有序任务：

```text
setup
→ synthesis
→ floorplan
→ placement
→ CTS
→ global route
→ detail route
→ density fill
→ final report / metric
```

阶段顺序不是语言风格问题，而是物理设计依赖关系。后一步需要前一步产生的网表、数据库、约束或报告。

论文 Figure 2 给出了一个完整例子：

![论文 Figure 2：需求、任务分解与脚本生成](./figures/chateda-paper-fig2-task-script-flow.png)

*图源：本地论文 PDF 第 4 页 Figure 2 裁剪；用于核对 requirement、stage 依赖、参数归属与生成脚本之间的逐项映射。*

用户要求包含：

- 设计 `aes`；
- 平台 `asap7`；
- synthesis 的 clock period 为 5；
- floorplan 的 core utilization 为 70%；
- placement density 为 0.8；
- CTS 修复 40% 的 violating paths；
- routing 后读取 power。

模型输出必须同时正确处理：

1. 阶段依赖；
2. 参数属于哪个 API；
3. 参数名；
4. 指标应该在哪个 stage 读取；
5. Python 语法和对象初始化。

### 3.3 脚本生成

论文不是让模型直接写 OpenROAD Tcl，而是给模型一个更窄、更稳定的 Python API：

```python
eda = chateda()
eda.setup(design_name="aes", platform="asap7")
eda.run_synthesis(clock_period=5)
eda.floorplan(core_utilization=70)
eda.placement(density=0.8)
eda.cts(tns_end_percent=40)
eda.global_route()
eda.detail_route()
power = eda.get_metric("route", ["power"])
```

这是一个重要设计取舍：

- LLM 只面对有限 API；
- wrapper 内部处理 Tcl、路径和环境变量；
- API 文档承担 tool schema 的作用；
- 生成脚本可以交给 Python 解释器执行。

但论文示例表达的是期望接口，不能自动证明公开实现能正确执行；后文会逐项核对。

### 3.4 任务执行

论文 Section III-C 说明：

1. ChatEDA 用 Python interpreter 执行生成脚本；
2. wrapper 设置环境变量；
3. wrapper 启动 subprocess；
4. OpenROAD 作为 executor；
5. wrapper 通过 Tcl 脚本或命令实现各阶段功能。

这不是“LLM 在每个 EDA log 后继续反思”的闭环。论文的核心实验主要评估一次生成的任务规划与脚本是否正确，脚本生成后才进入执行。

因此不要把后续多 Agent、日志反馈或搜索式修复机制倒灌进初版 ChatEDA。

---

## 4. AutoMage 如何训练

## 4.1 基座模型选择

论文选择 Llama2，而没有直接以 CodeLlama 为主，理由是：

- CodeLlama 代码能力强；
- 但论文认为持续代码预训练会削弱部分通用和 EDA 知识；
- ChatEDA 同时需要自然语言理解、EDA 领域知识和代码生成。

这是论文观点，不是当前仓库可复验的结论；仓库没有模型或对照实验代码。

## 4.2 Self-Instruct 数据生成

AutoMage 的原始训练数据由 GPT-3.5/4 辅助构造：

```text
少量 in-context EDA 示例
  → self-instruction prompt
  → GPT-3.5/4 生成 requirement / analysis / script
  → instruction pool
  → 人工修订
```

![论文 Figure 3：Self-Instruct 与 QLoRA](./figures/chateda-paper-fig3-self-instruction.png)

*图源：本地论文 PDF 第 5 页 Figure 3 及 self-instruction prompt 裁剪；用于支撑约 1,500 条 EDA 指令的数据构造流程。*

论文给出的数据量约为 1,500 条 EDA instruction instances。数据强调：

- 多样的用户表达；
- 必须使用给定 API；
- 阶段不能跳过；
- Python 中使用命名参数；
- 脚本应能直接执行；
- 输出包括需求分析和脚本。

论文还说明数据经过人工检查和修正，约花费两个人日。

## 4.3 QLoRA

论文使用 QLoRA 做参数高效微调，核心是：

- 基座权重以 4-bit NF4 存储；
- 计算使用 BF16；
- 使用 double quantization 进一步减少量化常数开销；
- 只更新低秩 LoRA 参数。

论文篇幅较多地介绍量化公式，但当前仓库没有：

- LoRA rank/alpha/target modules；
- bitsandbytes 配置；
- tokenizer 配置；
- train command；
- checkpoint。

所以这里只能复述论文方法，不能从代码确认训练细节。

## 4.4 解码

AutoMage 的生成使用 beam search，论文写明 beam width 为 4。

这与后续 AutoMage2 的 zero-shot CoT 共同作用于输出质量，但仓库没有 generation config，无法确认诸如 temperature、max tokens、repetition penalty 等细节。

---

## 5. AutoMage2 相对 AutoMage 的升级

论文把 AutoMage2 作为更强 controller，主要改动如下。

### 5.1 扩充并去重 EDA 数据

论文流程是：

1. 生成更多 EDA tool-use instances；
2. 使用 instructor embedding 编码；
3. 计算 cosine similarity；
4. 相似度高于 0.95 的样本去重；
5. 去重后仍保留约 1,500 条 EDA 指令。

这里的“约 1,500 条”不是说只使用当前仓库的 50 条样例。

### 5.2 混合代码指令

为了增强代码和逻辑推理，论文再加入约 110K 条开放代码 instruction。

因此 AutoMage2 训练语料可概括为：

```text
约 1.5K EDA tool instructions
+ 约 110K open code instructions
```

当前公开 JSON 的 50 条只占论文 EDA 指令规模约 1/30，更不包括 110K 代码数据。

### 5.3 解释式微调

AutoMage2 模仿 Orca 风格，让教师模型输出：

- think step-by-step；
- justify your steps；
- 最终 Python script。

这样训练目标不只是从 requirement 映射到代码，还包括任务规划解释。

### 5.4 Zero-shot CoT

推理 prompt 要求：

1. 先描述任务；
2. 再按 API 分析完成步骤；
3. 最后生成 Python script。

![论文中的训练 prompt、CoT prompt 与 benchmark 设置](./figures/chateda-paper-prompts-training-benchmark.png)

*图源：本地论文 PDF 第 8 页裁剪；左侧是 explanation/zero-shot CoT prompt，右侧是训练配置、开源说明和 ChatEDA-Bench 类别。*

需要注意：公开训练样例中的长自然语言分析确实符合这种格式，但仓库没有真正加载模型和组装 prompt 的程序。

---

## 6. 论文训练配置

论文给出 AutoMage2 的主要配置：

| 项目 | 论文设置 |
|---|---|
| 学习率调度 | constant |
| warm-up ratio | 0.03 |
| optimizer | paged AdamW 8-bit |
| learning rate | `1e-4` |
| weight decay | 0 |
| global batch size | 128 |
| sequence length | 4096 |
| epoch | 1 |
| GPU | 16 × A100 80GB |

论文没有在当前仓库中提供可对应这些参数的 config。也没有显存日志、loss curve、checkpoint size 或 seed。

因此即使手动准备数据，仍不能做到严格训练复现。

---

## 7. ChatEDA-Bench

## 7.1 数据规模

论文与仓库都给出 50 个任务。

本地静态统计：

```text
文件：data/test/ChatEDA-Bench.txt
Requirement 标记：50
唯一 Requirement：50
字符数：15,007
```

### 7.2 类别分布

按论文比例换算：

| 类别 | 比例 | 题数 |
|---|---:|---:|
| simple flow | 30% | 15 |
| complex flow | 30% | 15 |
| parameter tuner | 40% | 20 |
| 合计 | 100% | 50 |

仓库文本没有为每题附显式类别标签；分类依据来自论文而不是数据文件 schema。

### 7.3 benchmark 实际包含什么

它只有自然语言需求，没有：

- 标准任务分解；
- reference Python script；
- 可用设计 RTL；
- PDK 与 ORFS 环境；
- 预期 PPA 数值；
- 自动判分规则；
- 人工 A/B/C 标签。

因此它是 prompt set，不是开箱即用的 executable benchmark package。

### 7.4 benchmark 中的挑战

任务不只要求按顺序调用 API，还包含：

- 多参数笛卡尔积；
- continuous/discrete search space；
- 根据 WNS 非负判断有效 clock period；
- 在 route/final 等指定阶段取指标；
- 发现给定脚本的参数位置错误；
- 修正遗漏阶段；
- 处理用户给出的不合法平台名或参数 step。

这使 benchmark 同时考察接口 grounding 与逻辑推理。

---

## 8. 论文评测方法

论文评测分两层：

1. 把生成的 Python script 交给 EDA interface 测试可执行性；
2. 多位匿名人工评审判断输出是否满足用户需求。

最终使用三档等级：

| 等级 | 含义 |
|---|---|
| Grade A | task decomposition 连贯，脚本准确 |
| Grade B | 规划大体合理，但脚本存在缺陷 |
| Grade C | 任务分解和代码生成失败 |

该方法比只做字符串匹配更贴近工具调用，但存在几个复现问题：

- 没有公开每题生成结果；
- 没有公开多位评审的原始标签；
- 没有公开分歧处理规则；
- 没有公开执行日志；
- 没有说明每个设计、平台和 PDK 是否真的齐备；
- 论文也承认缺少基础或半自动的 benchmark 评分工具。

所以 Figure 5 的数字不能由当前仓库一键重算。

---

## 9. 论文结果

![论文 Figure 5：主要结果](./figures/chateda-paper-fig5-main-results.png)

*图源：本地论文 PDF 第 9 页 Figure 5 裁剪；用于核对五个模型的 Grade A/B/C 百分比。*

论文 Figure 5 的 A/B/C 百分比如下：

| 模型 | Grade A | Grade B | Grade C |
|---|---:|---:|---:|
| GPT-3.5 | 28% | 18% | 54% |
| Claude 2 | 46% | 26% | 28% |
| GPT-4 | 62% | 16% | 22% |
| AutoMage | 74% | 12% | 14% |
| AutoMage2 | **82%** | 8% | 10% |

论文结论是 AutoMage2 明显优于通用 LLM。

但应准确解释这些结果：

- 指标是 50 个任务上的人工等级占比；
- 82% 等于 41/50 获得 Grade A；
- 不是 PPA 优于 GPT-4 82%；
- 不是所有任务都真正完成 tapeout；
- 不是多次采样后的 pass@k；
- 不是自动测试覆盖率。

---

## 10. 论文案例与代码现实

论文展示 AutoMage2 正确完成参数网格搜索，而 GPT-4 把每个 stage 拆成互不连贯的函数，遗漏必要上下文。

![论文参数网格搜索案例](./figures/chateda-paper-case-grid-search.png)

*图源：本地论文 PDF 第 10 页左栏裁剪；展示 AutoMage2 对 floorplan/placement/CTS 网格搜索的任务分解与脚本。*

这个案例强调：

- EDA 参数不是独立函数调用；
- 每次组合需要从合适阶段重新执行；
- metric 应在用户指定阶段获取；
- 综合、floorplan、placement、CTS 和 routing 的参数必须落在正确函数上。

但论文案例也暴露一个更深的复现点：模型生成的脚本以“API 应当正确实现”为前提；当前公开 `openroad_api_impl.py` 的 metric 和 tune 实现并没有满足这个前提。

---

## 11. 当前仓库结构

核心文件只有：

```text
ChatEDA/
├── README.md
├── LICENSE
├── 2308.10204_ChatEDA.pdf
├── NAACL2025_Multi-Agent_ChatEDA.pdf
├── api_doc/
│   ├── openroad_api.py
│   ├── openroad_api_impl.py
│   └── parse_mk_config.py
└── data/
    ├── train/ChatEDA-train-example.json
    └── test/ChatEDA-Bench.txt
```

没有常见完整模型工程中的：

```text
train.py
inference.py
model/
configs/
requirements.txt
environment.yml
Dockerfile
checkpoints/
eval.py
outputs/
```

所以 `README.md` 的“提供数据、benchmark、API 文档与实现”是准确的；如果据此进一步说“提供完整 ChatEDA 代码”，就超出了仓库事实。

---

## 12. README 能证明什么

README 只有约 35 行，明确说明：

- 训练样例用于 AutoMage 和 ChipLlama；
- ChatEDA-Bench 有 50 个任务；
- 提供 API document 和 OpenRoad implementation；
- 引用 ChatEDA 与 Multi-Agent ChatEDA 两篇论文。

README 没有给出：

- 安装命令；
- Python 版本；
- OpenROAD-flow-scripts 版本；
- PDK 下载；
- 训练与推理命令；
- benchmark 运行命令；
- 预期输出。

这进一步说明仓库定位是 artifact excerpt，而不是 replication package。

---

## 13. `openroad_api.py`：API 文档桩

文件：[api_doc/openroad_api.py](./api_doc/openroad_api.py)

这个文件定义：

- `chateda.setup`；
- `run_synthesis`；
- `floorplan`；
- `placement`；
- `cts`；
- `global_route`；
- `detail_route`；
- `density_fill`；
- `final_report`；
- `get_metric`；
- 顶层 `tune`。

它的主要价值是让 LLM 阅读 docstring。

所有阶段函数都只执行类似：

```python
print("run_synthesis done")
```

`get_metric` 固定返回 0，`tune` 也只打印 `tune done`。

因此：

> `openroad_api.py` 可以作为 prompt 中的工具说明，不能作为 EDA 执行实现。

---

## 14. API 参数和阶段映射

| 阶段 | 函数 | 可调参数 | 预期输出 |
|---|---|---|---|
| setup | `setup` | design, platform, flow_home, verilog, sdc | 环境与输入路径 |
| synthesis | `run_synthesis` | clock period, ABC area/speed | gate netlist + SDC |
| floorplan | `floorplan` | utilization, aspect ratio, margins, macro halo/channel | floorplan ODB |
| placement | `placement` | density | placed ODB |
| CTS | `cts` | tns_end_percent | CTS ODB |
| global route | `global_route` | 无公开调参 | global routing 状态 |
| detail route | `detail_route` | 无公开调参 | routed ODB |
| fill | `density_fill` | 无 | fill ODB |
| report | `final_report` | 无 | final metrics/report |
| metric | `get_metric` | stage + metric list | 标量 |
| DSE | `tune` | function + search space | 最优配置 |

这张表是论文任务 grounding 的基础，也是检查模型输出最直接的规则集。

---

## 15. `openroad_api_impl.py` 的实际调用链

文件：[api_doc/openroad_api_impl.py](./api_doc/openroad_api_impl.py)

### 15.1 构造函数

构造 `chateda` 时运行：

```python
self.ord = subprocess.Popen(
    "openroad", stdin=subprocess.PIPE, stdout=subprocess.PIPE
)
```

但后续阶段不是通过这个进程交互，而是通过：

```python
self.ord_cmd = "openroad -exit -no_init"
```

在 `_run_ord_cmd` 中启动新的 subprocess。

所以常驻 `self.ord` 主要用于 `help()`，一般流程中可能成为未关闭资源；它不是论文所暗示的持续 EDA session。

### 15.2 `_run_ord_cmd`

实际命令形态：

```text
/usr/bin/time ... openroad -exit -no_init <script.tcl>
    -metrics <LOG_DIR>/<metric.json>
```

包装器会：

1. 从 `SCRIPTS_DIR` 拼 Tcl 路径；
2. 用 `shell=True` 运行；
3. stdout 同时打印和写 log；
4. 返回 subprocess return code。

这证明当前实现依赖 OpenROAD-flow-scripts 的脚本目录和文件命名，而不是只依赖 `openroad` 可执行文件。

---

## 16. `setup` 的真实行为

`setup` 主要完成：

1. 设置 `DESIGN_NAME` 和 `PLATFORM`；
2. 推导或接收 Verilog/SDC；
3. 设置 `FLOW_HOME`、`DESIGN_HOME`、`PLATFORM_HOME`；
4. 解析 design/platform 的 `config.mk`；
5. 设置 ORFS 默认环境变量；
6. 构造 logs/objects/reports/results 目录；
7. 处理 wrapped LEF/LIB 与 `dont_use`；
8. 调用 ORFS 的 `markDontUse.py`。

支持平台的 docstring 写为：

```text
asap7, nangate45, sky130, gf180
```

但是否能运行取决于传入 `flow_home` 是否包含对应 ORFS platform 和 design 配置。仓库本身并不包含这些目录。

### 16.1 清理目录的 glob 错误

代码写成：

```python
shutil.rmtree(os.path.join(OBJECTS_DIR, "2*"), ignore_errors=True)
```

`shutil.rmtree` 不展开 shell glob，因此它只尝试删除名字真的叫 `2*` 的目录，而不会删除 `2_1_floorplan` 等阶段产物。

结果可能是：

- 上一次运行的中间文件残留；
- 新结果和旧结果混用；
- benchmark 可执行性判断受到污染。

---

## 17. 各 EDA stage 的代码映射

### 17.1 Synthesis

调用 ORFS `synth.tcl`，期望：

- 生成 `1_1_yosys.v`；
- 复制为 `1_synth.v`；
- 复制 SDC 为 `1_synth.sdc`。

当设置 `clock_period` 时，代码：

- 设置 `ABC_CLOCK_PERIOD_IN_PS`；
- 直接打开 `DESIGN_DIR/constraint.sdc`；
- 替换包含 `set clk_period` 的行。

问题是：`setup` 允许用户传入自定义 `sdc` 并保存到 `SDC_FILE`，但这里仍修改固定的 `DESIGN_DIR/constraint.sdc`。

这会造成两个约束源不一致：

```text
修改的是 DESIGN_DIR/constraint.sdc
复制的是 SDC_FILE
```

此外 API 把 `clock_period` 标成 `int`，但 benchmark 明确出现 8.5、0.5 step 等小数。

### 17.2 Floorplan

顺序调用：

1. `floorplan.tcl`；
2. `io_placement_random.tcl`；
3. `tdms_place.tcl` 或复制手工 macro placement；
4. `macro_place.tcl`；
5. `tapcell.tcl`；
6. `pdn.tcl`。

最后复制 `2_6_floorplan_pdn.odb` 为 `2_floorplan.odb`。

参数设置存在条件嵌套：

```python
if core_utilization is not None:
    ...
    if core_aspect_ratio is not None:
        ...
    if core_margins is not None:
        ...
```

这意味着用户不能单独调整 `core_aspect_ratio` 或 `core_margins`；必须同时提供 `core_utilization` 才会生效。

论文训练样例和 benchmark 经常要求独立调参，所以这是会影响论文任务正确性的实现差异。

### 17.3 Placement

依次调用：

1. global placement, skip IO；
2. IO placement；
3. global placement；
4. resize；
5. detailed placement。

前四步大多检查 return code；第五步计算 status 后没有检查，直接复制预期文件。

如果 detail placement 失败，用户看到的可能是 `FileNotFoundError`，而不是原始 OpenROAD 错误。

### 17.4 CTS

设置 `TNS_END_PERCENT`，调用：

```text
cts.tcl
fillcell.tcl
```

代码不检查两个 stage 的返回值，随后直接复制 `4_2_cts_fillcell.odb`。

### 17.5 Routing

`global_route` 中确实获取：

```python
status = self._run_ord_cmd(...)
```

但函数末尾没有：

```python
return status
```

因此调用者收到 `None`。

文件底部调参示例又写：

```python
status = ceda.global_route()
if status != 0:
    report_penalty()
    return
```

Python 中 `None != 0` 为真，所以该示例总会在 global routing 后上报惩罚并返回，永远到不了 detail route 和 final report。

这是当前包装器中最直接的控制流 bug 之一。

### 17.6 Fill 与 Final Report

`density_fill` 根据 `DENSITY_FILL` 环境变量决定执行 Tcl 或复制 route ODB。

`final_report` 调用 `final_report.tcl` 并复制 SDC。

两者都没有检查 `_run_ord_cmd` 返回码。

---

## 18. `get_metric` 为什么当前不可用

`get_metric(stage, metrics)` 目标是将：

```text
area, power, tns, wns, performance
```

映射到 ORFS metrics JSON 的完整 key。

当前实现有多处问题。

### 18.1 没有修改列表

代码：

```python
for metric in metrics:
    if metric == "area":
        metric = stage + "__design__core__area"
```

这里仅修改循环局部变量，`metrics` 列表仍是 `['area']`。

后面执行：

```python
data[metric]
```

实际会访问 `data['area']`，而不是映射后的 ORFS key。

### 18.2 stage file 映射不完整

代码只为：

- `floorplan` → `2_1_floorplan`；
- `final` → `6_report`；

设置了 `stage_file`。

`place`、`cts`、`route` 会保持空字符串，最终打开：

```text
LOG_DIR/.json
```

### 18.3 参数类型与示例冲突

docstring 要求 `metrics: list`，但底部示例调用：

```python
get_metric("final", "area")
```

传入字符串会让循环依次处理字符 `a/r/e/a`。

### 18.4 指标聚合含义不清

函数把多个 metric 直接求算术平均：

```text
(area + power + performance) / 3
```

这些量纲不同、尺度不同，直接平均没有物理意义。

因此论文中“获取 PPA”或“作为 DSE objective”的动作，不能由当前实现可靠完成。

---

## 19. `tune` 与 `tuned` 的接口错位

API 文档和训练样例都使用：

```python
tune(func, param)
```

真实实现导出的却是：

```python
def tuned(func, param):
```

如果生成脚本照论文 API 调 `tune`，直接导入实现文件后会找不到同名函数。

### 19.1 Ray Tune 搜索空间

实现统一用：

```python
tune.quniform(min, max, step)
```

但公开训练样例和 benchmark 中出现：

```json
{"core_aspect_ratio": {"minmax": [0.8, 1.2], "step": 0}}
```

`step=0` 不能作为有效量化步长。论文语言中的“continuously”需要另一类 sampling distribution，不能机械映射到 `quniform(..., 0)`。

### 19.2 固定目标与固定预算

实现固定：

- OptunaSearch；
- objectives：`area`、`power`；
- mode：两个都 minimize；
- 20 samples；
- 单 trial 600 秒；
- 最大并发 1。

但 benchmark 会要求：

- performance；
- TNS/WNS；
- PPA 多目标；
- 满足 WNS 条件后最小 clock period。

当前 `tuned` 不是论文需求中通用的 DSE 接口。

### 19.3 返回值

API 描述让用户期待获得 best parameters，但实现只打印 area/power 的最佳 config，没有返回统一结果。

---

## 20. `parse_mk_config.py`

文件：[api_doc/parse_mk_config.py](./api_doc/parse_mk_config.py)

核心 `parse(path)` 思路合理：

1. 创建临时 Makefile；
2. include 目标 `config.mk`；
3. 运行 `make` 后打印环境；
4. 取出原进程环境中不存在的变量。

但也有边界：

- 没有检查 `make` return code；
- 只返回“原环境中不存在”的变量，已有环境变量会覆盖配置；
- 解析过程会执行 Makefile 中的函数和 shell 行为；
- `__main__` 调用不存在的 `parse_config_mk`，而不是 `parse`。

最后一项意味着直接运行该文件的示例会 `NameError`。

---

## 21. shell 与执行安全

包装器把路径和参数拼成字符串，并以 `shell=True` 执行。

潜在风险包括：

- 用户提供的 `flow_home`、文件名或环境值未统一 quoting；
- 生成脚本可以直接调用 Python；
- wrapper 会写 constraint、results、logs；
- Makefile parser 会 include 并执行配置；
- 没有 sandbox、命令白名单、超时回收和工作区隔离的完整实现。

论文目标是 autonomous agent，但开源 artifact 没有提供安全执行层。

实际复现时至少需要：

1. 容器隔离；
2. 只挂载允许的 design/PDK 路径；
3. 禁网或细粒度网络策略；
4. API schema 白名单；
5. 每 stage timeout；
6. 禁止模型自由导入模块和调用 shell；
7. 每个 trial 独立工作目录；
8. 保留原始命令、stdout、stderr、return code 和文件哈希。

---

## 22. 训练样例静态分析

文件：[data/train/ChatEDA-train-example.json](./data/train/ChatEDA-train-example.json)

本地统计：

| 项目 | 数量/值 |
|---|---:|
| JSON rows | 50 |
| unique instruction | 50 |
| unique output | 50 |
| empty input | 50 |
| dataset label | `chateda_v1.5` |
| keys | `instruction/input/output/dataset` |

每条输出通常包含：

```text
自然语言分析
→ 阶段分解
→ Python fenced code
```

### 22.1 数据优点

- API grounding 明确；
- 涵盖 simple flow 与 DSE；
- 输出有解释，适合 explanation tuning；
- 强调阶段顺序；
- 包含错误脚本诊断任务。

### 22.2 数据中的可执行性问题

静态检查可看到一些会影响训练目标的问题：

- 多处把 `step=0` 表示 continuous search；
- 示例调用 `tune`，实现只有 `tuned`；
- 示例相信 `get_metric` 支持所有 stage，而实现不支持；
- 有些示例只写 `import chateda`，但仓库没有名为 `chateda.py` 的安装包入口；
- benchmark 中可能出现实现未支持的平台或拼写；
- 样例中的“能执行”没有相应 execution log 佐证。

如果直接拿这些 50 条做 SFT，模型会学习论文期望 API，而不是当前实现的真实行为。

---

## 23. 论文与代码逐项对应

| 论文要素 | 代码/数据位置 | 对应程度 |
|---|---|---|
| API specifications | `api_doc/openroad_api.py` | 有，文档桩 |
| OpenROAD wrapper | `api_doc/openroad_api_impl.py` | 有，原型且有缺陷 |
| Make config parsing | `api_doc/parse_mk_config.py` | 有 |
| 训练数据格式 | `data/train/*.json` | 有 50 条样例 |
| 约 1,500 EDA 数据 | 无 | 未公开完整集 |
| 约 110K code instructions | 无 | 未公开 |
| embedding 去重 | 无 | 未公开代码 |
| QLoRA 训练 | 无 | 未公开代码/config |
| AutoMage | 无 | 未公开权重 |
| AutoMage2 | 无 | 未公开权重 |
| beam search width 4 | 无 | 只有论文描述 |
| zero-shot CoT prompt | 论文截图/训练样例风格 | 无推理模板文件 |
| ChatEDA-Bench prompts | `data/test/*.txt` | 50 条完整公开 |
| benchmark reference | 无 | 未公开 |
| EDA execution logs | 无 | 未公开 |
| 人工 A/B/C 标签 | 无 | 未公开 |

---

## 24. 哪些部分“能复现”

### 24.1 当前能确认

- 论文架构与三阶段流程；
- API 名称、参数和预期顺序；
- 公开 50 条训练样例的数据结构；
- 公开 50 条 benchmark prompt；
- OpenROAD wrapper 试图调用哪些 ORFS Tcl；
- 论文训练配置与报告结果；
- 代码与论文之间的接口差异。

### 24.2 当前不能确认

- AutoMage/AutoMage2 的真实输出；
- 训练数据完整清洗过程；
- 模型是否能稳定生成可执行脚本；
- 50 题中每题的 Grade A/B/C；
- 当前 wrapper 是否对应论文运行时版本；
- Figure 5 是否能在相同模型版本下重现；
- EDA flow 对 PPA 的真实影响。

### 24.3 不应宣称

不能仅凭 `openroad_api_impl.py` 存在就写：

```text
ChatEDA 已在本地跑通 RTL-to-GDSII。
```

也不能仅凭 50 条训练样例就写：

```text
AutoMage2 训练集已完整开源。
```

---

## 25. 如果后续要做最低成本复现

这里给出复现设计，不在本次执行。

### 路线 A：只复现“API 规划”

1. 把 `openroad_api.py` 作为 tool schema；
2. 用本地开源 instruct/code model生成脚本；
3. 建 AST 检查器，不执行 EDA；
4. 检查 API 名称、参数、阶段顺序和指标 stage；
5. 人工抽查 50 题。

这是最接近当前开源材料、成本最低的复现。

### 路线 B：修好 wrapper 后做单设计 smoke test

前置工作：

- 固定 ORFS commit；
- 固定 OpenROAD build；
- 固定一个免费 PDK；
- 准备一个 ORFS 自带小设计；
- 修复 `global_route`、`get_metric`、`tune/tuned` 和 SDC；
- 每个 stage 验证 return code 和输出文件。

然后只跑：

```text
setup → synth → floorplan → placement → CTS → global route
```

先不要直接把 LLM 接到真实 shell。

### 路线 C：复现论文表格

除路线 A/B 外还需要：

- AutoMage/AutoMage2 checkpoint 或重训 recipe；
- 完整训练数据；
- generation config；
- 每题 reference 或人工评分协议；
- 所有基线的固定版本；
- 多评审一致性统计。

当前仓库不满足这些条件。

---

## 26. 建议的确定性脚本验证器

与其立即执行模型生成脚本，更适合先把输出解析为结构化 action：

```json
{
  "design": "aes",
  "platform": "asap7",
  "actions": [
    {"name": "setup", "args": {}},
    {"name": "run_synthesis", "args": {"clock_period": 5}},
    {"name": "floorplan", "args": {"core_utilization": 70}},
    {"name": "placement", "args": {"density": 0.8}},
    {"name": "cts", "args": {"tns_end_percent": 40}},
    {"name": "global_route", "args": {}},
    {"name": "detail_route", "args": {}},
    {"name": "get_metric", "args": {"stage": "route", "metrics": ["power"]}}
  ]
}
```

验证器可以确定性检查：

- 函数是否在白名单；
- 参数是否属于该函数；
- stage 依赖是否满足；
- 数值范围和 step 是否合法；
- metric stage 是否已经执行；
- DSE 是否在每个 trial 重置状态。

这会把“语言生成正确性”和“EDA 执行正确性”拆开，便于定位问题。

---

## 27. 对论文评价的正确口径

ChatEDA 的价值在于较早地把 LLM tool-use 引入 RTL-to-GDSII 流程，并系统化了：

- EDA 专家模型；
- API 文档 grounding；
- 任务分解；
- 脚本生成；
- 工具执行；
- 面向 EDA 的 benchmark。

但证据边界也很明确：

- benchmark 规模只有 50；
- 评分主要依赖人工；
- 完整训练与模型资产未开源；
- 当前 API implementation 不是可靠的可执行发布；
- 论文结果评价的是脚本规划/生成，不等同于 PPA 优化效果；
- 论文公开局限包括 API/平台泛化、推理延迟、缺少自动评分工具。

所以更准确的评价是：

> ChatEDA 是一个有影响力的“LLM 作为 EDA 流程 controller”方法原型；论文方法值得分享，但当前开源仓库只足以做接口、数据和包装器级研究，不能支持完整论文复现。

---

## 28. 与后续 Multi-Agent ChatEDA 的边界

初版 ChatEDA：

```text
一个 AutoMage controller
→ 一条 task decomposition
→ 一份 Python script
→ EDA executor
```

后续 EDAid：

```text
多个 divergent-thought agents
→ 多份 planning/script 候选
→ decision-making agent 比较候选
→ 选一份脚本
→ EDA executor
```

初版没有后续论文的：

- ChipLlama；
- 3 个 divergent agents；
- 1 个 decision agent；
- retrieval/permutation few-shot；
- yes-token probability 排序；
- iEDA-bench。

两篇论文必须分开写，详细差异见 [Multi-Agent ChatEDA论文与代码复现详解.md](./Multi-Agent%20ChatEDA论文与代码复现详解.md)。

---

## 29. 组会可直接讲的主线

推荐按下面逻辑组织，不需要先讲量化公式：

1. **问题**：后端 EDA 流程长、接口复杂、参数多；
2. **核心想法**：把 LLM 放在 controller 位置，EDA 工具仍是 executor；
3. **方法**：requirement → decomposition → Python script → OpenROAD；
4. **模型**：Llama2 + EDA self-instruct + QLoRA，AutoMage2 再混入代码数据和 CoT；
5. **评测**：50 个 ChatEDA-Bench prompt，人工 A/B/C；
6. **结果**：AutoMage2 Grade A 82%，GPT-4 62%；
7. **代码现实**：公开的是数据/API/包装原型，不是完整 controller；
8. **复现风险**：wrapper 的 metric、route status、tune 接口都有问题；
9. **启示**：未来重点应是结构化 action、可验证执行、版本固定、安全和自动评分。

### 一句话总结

> ChatEDA 证明了“领域微调 LLM + 窄 EDA API”能提高长链 EDA 脚本规划，但当前开源程度不足以复现 AutoMage2 和论文 82% 结果，且公开 wrapper 需要先修复才能作为可靠执行端。

---

## 30. 可追溯证据清单

### 论文证据

- 系统总览：PDF Figure 1；
- task decomposition 与 script generation：Figure 2；
- self-instruction 与 QLoRA：Figure 3；
- AutoMage2、prompt、训练配置和 benchmark：Section V–VI；
- 主要结果：Figure 5；
- 论文 limitations：结尾 Limitation。

### 代码证据

- API 文档桩：[api_doc/openroad_api.py](./api_doc/openroad_api.py)
- ORFS wrapper：[api_doc/openroad_api_impl.py](./api_doc/openroad_api_impl.py)
- Make 配置解析：[api_doc/parse_mk_config.py](./api_doc/parse_mk_config.py)
- 训练样例：[data/train/ChatEDA-train-example.json](./data/train/ChatEDA-train-example.json)
- benchmark：[data/test/ChatEDA-Bench.txt](./data/test/ChatEDA-Bench.txt)
- 静态审计：[runs/static_audit_20260802.json](./runs/static_audit_20260802.json)

### 本次没有产生的证据

- 无新模型推理；
- 无 API 调用；
- 无训练；
- 无 OpenROAD 编译/运行；
- 无 PDK 下载；
- 无论文表格重算。

这样保留了“论文报告”“代码事实”“本地执行”三类证据的清晰边界。

---

## P7 关键组件一句话总结

| 组件 | 一句话总结 |
|---|---|
| AutoMage/AutoMage2 controller | 经 QLoRA 微调 Llama2 的领域模型，负责把需求分解为有序 EDA 任务并生成 Python 脚本。 |
| Python EDA API wrapper | 把高层 `chateda` API 映射到 OpenROAD-flow-scripts Tcl 命令的包装层。 |
| API doc stub | 只打印 done/返回 0 的文档桩，用于 prompt 中的工具说明。 |
| OpenROAD/ORFS executor | 实际执行综合、floorplan、placement、CTS、routing 等阶段的底层 EDA 工具链。 |
| ChatEDA-Bench | 50 条自然语言后端需求的 prompt set，覆盖简单/复杂流程和参数调优。 |
| Self-instruct data pipeline | 用少量 EDA 示例通过 GPT-3.5/4 生成约 1.5K EDA tool-use instruction 并经人工修订。 |

---

## 讨论问题

1. ChatEDA-Bench 只有 50 条需求且评分依赖人工，如何设计更大规模、可自动复现的 EDA tool-use benchmark？
2. 公开 wrapper 与训练样例中的 API 接口存在多处不一致，直接 SFT 会让模型学习期望 API 而非真实实现，如何对齐？
3. 人工 A/B/C 评分反映“脚本规划质量”，但未必反映真实 PPA 收益；如何建立规划评分与执行后 PPA 的对应关系？
