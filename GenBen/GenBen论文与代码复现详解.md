# GenBen：生成式硬件设计基准——论文、代码与本地复现详解

> 论文：**GenBen: A Generative Benchmark for LLM-Aided Design**  
> 本地论文：[ICLR2025_Submission_GenBen.pdf](./ICLR2025_Submission_GenBen.pdf)（23 页匿名投稿版）  
> 论文页：<https://openreview.net/forum?id=gtVo4xcpFI>；PDF：<https://openreview.net/pdf?id=gtVo4xcpFI>  
> 代码：<https://github.com/ChatDesignVerification/GenBen>  
> 本地代码版本：commit `a103f9a892e3`；仓库根目录未发现明确 LICENSE，二次分发前需要再核对授权  
> 核对日期：2026-08-02

---

```text
┌─────────────────────────────────────────────────────────────────────────┐
│ P1 任务定义                                                              │
├─────────────────────────────────────────────────────────────────────────┤
│ Input:  自然语言/图像形式的硬件题（含模块规格、调试代码、选择题）+        │
│         可选静态/动态扰动 + LLM API 配置                                  │
│ Output: 每题 5 次模型响应、抽取的答案/RTL、选择题正确率、pass@5、语法/   │
│         功能/可综合率、PPA 与 QoR 报告                                    │
│ Supervision: 选择题有 golden 答案；生成/调试题用 Icarus + Yosys +        │
│              OpenLane/OpenSTA 自动判分；无人类逐题标注                    │
│ Why-hard: 多模态输入解析；真实设计复杂度高于 HDLBits；功能正确与可综合/   │
│           PPA 需跨工具链；Sky130/OpenLane 路径硬编码；商业模型版本漂移    │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 1. 先给结论：它值得分享在哪里

GenBen 不是一个待训练的 RTL 大模型，而是一套评估 **LLM 能否完成真实硬件设计任务** 的综合 benchmark。它最值得分享的地方不是“又多了一组 Verilog 生成题”，而是把评估范围从代码是否通过仿真扩展成下面五条能力轴：

1. **Knowledge Mastery**：硬件基础概念是否掌握；
2. **Knowledge Transfer**：能否把知识迁移到需要推导的新情境；
3. **Debug Ability**：能否修复语法、功能或混合错误；
4. **Code Correctness**：生成 RTL 的语法和功能是否正确；
5. **Quality of Result（QoR）**：代码能否综合，以及面积、功耗、时序表现如何。

它同时包含文本与图像输入、L1/L2/L3 难度分级、静态与动态扰动，并试图用开源工具串起：

```text
题目/图像
  -> 动态扰动
  -> LLM 连续采样 5 次
  -> 答案抽取与任务分流
  -> 选择题/调试答案比对
  -> Icarus Verilog 仿真
  -> Yosys 可综合性检查
  -> OpenLane + Sky130 物理实现
  -> OpenSTA 时序、面积、功耗报告
  -> 统一 CSV 分数表
```

但要准确表述复现状态：**本地已确认部分公开数据可读，并用仓库自己的 `check_correctness` 跑通一个 GP_17 多路选择器仿真；尚未复现论文的全量 324 题、pass@5、多模态模型调用和 PPA 实验。** 当前代码存在若干作者机器路径和流程边界，不能写成“开箱即用全复现”。

---

## 2. 论文身份与公开状态

本地 PDF 首页写的是：

- `Under review as a conference paper at ICLR 2025`；
- 匿名作者、双盲评审；
- 标题中原文拼写为 `GENARATIVE`，但论文页和项目通常写作 `Generative`；
- 摘要报告总计 **10,920 次实验、2,160 小时评估**。

因此组会中宜称为“ICLR 2025 匿名投稿版 / OpenReview 版本”，不要仅凭 PDF 写成“ICLR 2025 已录用论文”。后续如需确认最终接收状态，应以 OpenReview 决议为准。

---

## 3. 论文试图解决的四个缺口

论文第 2.3 节将现有硬件 LLM benchmark 的问题归纳为四类：

| 缺口 | 具体含义 | GenBen 的对应设计 |
|---|---|---|
| 验证覆盖不足 | 简单 testbench 可能没有触发关键功能点 | 专家增强 testbench，强调 line/toggle/function coverage |
| 数据多样性不足 | 教学题多、真实设计少，且多为纯文本 | GitHub、流片/硅验证项目、教材、Stack Overflow；增加图像输入 |
| 测试集污染 | 静态公开题可能进入预训练语料 | 构建期静态扰动 + 评测时动态表层扰动 |
| 指标单一 | 只看语法/功能，忽略实现质量 | 增加可综合性、面积、功耗、hold/setup 时序指标 |

这四点构成 GenBen 的论文逻辑主线：它不是单独提出一个生成算法，而是提出一套 **更难污染、更接近硬件实现闭环的评测协议**。

---

## 4. 论文总流程

![GenBen 论文 Figure 2：数据构建、静态/动态扰动、工作流和提示模板](./figures/paper-fig2-pipeline.png)

论文 Figure 2 可以分成五块理解：

### 4.1 A：Dataset Construction

```text
书籍 / 论文 / 开源设计 / 问答网站
  -> 硬件问题与设计收集
  -> testbench 增强、设计生成、代码调试题构造
  -> 静态扰动
  -> L1/L2/L3 难度分级
  -> 知识 / 迁移 / 设计 / 调试 / 多模态题
```

论文称数据由 10 名领域专家筛选，特别关注 silicon-proven 项目，并对代码题的 testbench 做覆盖增强。

### 4.2 B：GenBen Workflow

```text
GenBen 数据库
  -> 脚本化生成测试
  -> 动态扰动
  -> 收集模型响应
  -> Lint / Simulation / EDA
  -> 报告分析
  -> 计分
```

关键思想是原始测试集 `T` 与扰动测试集 `T'` 都送入模型，比较模型在表述变化后的稳定性。

### 4.3 C：Static Perturbation

论文描述的是一个多模型与人工反馈结合的构建过程：

1. LLM 做表层改写；
2. 另一个 LLM 做等价性检查；
3. LLM group 做语义扰动；
4. 对齐检查确保题目与参考答案一致；
5. 失败样本回退、通过样本进入 benchmark。

表层扰动只改写描述；语义扰动会改变问题含义，因此也必须同步修改参考解。

### 4.4 D：Dynamic Perturbation

运行时用脚本做选项混淆、同义词改写、参数变化等轻量变化。目的不是无限生成新电路，而是降低模型直接背诵固定题面的收益。

### 4.5 E：Prompt Templates

提示由“硬件专家角色”加任务模板组成，并针对设计、调试和知识题分别要求不同输出格式。代码中进一步把任务 ID 中的 `U/T/D/G/M` 当作分流信号。

---

## 5. 数据集：论文口径与仓库实际文件必须分开

![GenBen 论文 Table 3：任务类别与数量](./figures/paper-table3-dataset.png)

### 5.1 论文口径

论文 Table 3 给出的主类别是：

| 类别 | 数量 | 评测重点 |
|---|---:|---|
| Knowledge Master | 75 | 基础概念和原理 |
| Knowledge Transfer | 69 | 推理、迁移和泛化 |
| Design | 99 | RTL 代码生成，难度与代码行数/类型/设计时间相关 |
| Debug | 57 | 语法、功能或混合错误修复 |
| Multimodal | 60 | 文本与图像联合输入，属于交叉模态统计 |

前四类相加为 **300**。多模态 60 不是额外独立任务类型，而是落在知识、设计、调试等类别中的输入模态切片。

### 5.2 本地仓库实际打包行数

`save_data/` 中当前可见 JSONL 为：

| 文件 | 行数 | 含义 |
|---|---:|---|
| `..._all.jsonl` | 324 | 文本 264 + 多模态 60 |
| `..._text.jsonl` | 264 | 纯文本任务 |
| `..._mm.jsonl` | 60 | 多模态任务 |
| `..._choice.jsonl` | 144 | 知识掌握/迁移题 |
| `..._debug.jsonl` | 57 | 调试题 |
| `..._design.jsonl` | 123 | 代码生成题 |
| `results_ppa_ref.jsonl` | 106 | 部分代码题的参考 PPA |

这里不能把各文件行数相加成独立样本总数，因为 `choice/debug/design` 都是 `all` 的子集，`text/mm` 又是按模态切分的同一批题。

论文正文的 300 与仓库 `all=324` 存在版本/统计口径差异。复现实验时应记录实际 commit 和输入文件哈希，以 `all.jsonl` 的 324 行为当前代码事实，不应用论文表格反推本地文件。

### 5.3 每条代码题的关键字段

以 `GP_17` 为例：

```json
{
  "task_id": "GP_17",
  "task_recommend": "自然语言模块规格",
  "verilog": "参考模块 ref_mux_2x1",
  "test": "实例化 top 的 testbench"
}
```

生成模型必须给出顶层模块 `top`。评测器会把 `test + reference Verilog + candidate` 拼成临时 `.sv` 文件，再以 `tb` 为仿真顶层运行。

---

## 6. 五维指标到底怎样落到代码

![GenBen 论文 Table 5：五维指标定义](./figures/paper-table5-metrics.png)

### 6.1 Knowledge Mastery / Transfer

`genben.py` 根据任务 ID 中的 `U` 或 `T` 生成选择题提示，要求模型只输出 `A.XXXX` 一类最终答案。完成五轮采样后，`choice_pass_5(...)` 将模型答案与 `choice` golden 文件比较，再按 all/mm/text 与 L1/L2/L3 汇总。

### 6.2 Debug Ability

任务 ID 中含 `D` 时走调试分支。`get_verilog(...)` 把模型输出拆到 debug JSONL，`debug_pass(...)` 做 pass@5 统计。这里的“debug”并不等价于完整交互式编译反馈循环；当前主脚本主要评估五个独立响应中是否存在正确修复。

### 6.3 Syntax Correctness

`verilog_eval/execution.py::check_correctness` 执行：

```bash
iverilog -Wall -Winfloop -Wno-timescale -g2012 -s tb -o test.vvp <task>.sv
vvp -n test.vvp
```

代码根据 stderr 中是否出现 `syntax error`、`warning`、`error` 进行分类。随后 `evaluation.py` 统计 `Syntax_pass@k`。

需要注意：当前实现只要没有出现字符串 `failed: syntax error.` 就将该题的 syntax 标记为可通过；它不是严格的 lint 质量分数实现，论文中“每个 warning 扣 5%，最低 60%”的细粒度规则并没有完整体现在这段 pass@k 代码里。

### 6.4 Function Correctness

testbench 必须输出：

```text
Mismatches: <错误数> in <总样本数> samples
```

评测器通过正则解析这行；`错误数 == 0` 才返回 `passed=True`。`evaluation.py` 使用标准无放回 pass@k 估计：

\[
\mathrm{pass@k}=1-\frac{\binom{n-c}{k}}{\binom{n}{k}}
\]

其中 `n` 是一题的生成样本数，`c` 是通过样本数。主脚本固定循环五次，所以论文实验强调 pass@5。

### 6.5 Synthesizability

`yosys_check_correctness(...)` 对候选代码运行 Yosys：

```text
read -sv
  -> hierarchy -top top
  -> proc / fsm / opt / memory / techmap
  -> dfflibmap
  -> abc
```

它通过输出中是否出现 `syntax error` 或 `ERROR` 判定综合成功。但当前命令把 liberty 文件写死为作者机器下的：

```text
/home/ord1nary/.volare/.../sky130_fd_sc_hd__ff_n40C_1v56.lib
```

换机器必须修改，不能直接把仓库原样运行失败归因于模型。

### 6.6 PPA 与时序

通过功能测试的候选进入 `test_ppa.py::make_run(...)`：

```text
candidate.v
  -> OpenLane Config.interactive(PDK=sky130A, clock=10ns)
  -> Yosys.Synthesis
  -> OpenROAD.STAPrePNR
  -> yosys-synthesis.log 提取 Area
  -> power.rpt 提取 Total Power
  -> summary.rpt 提取 hold/setup TNS/WNS
  -> 与 results_ppa_ref.jsonl 对齐
```

这里的复现门槛明显高于 Icarus 仿真：需要兼容版本的 OpenLane/OpenROAD/OpenSTA、Sky130 PDK、标准单元库和一致的环境配置。

---

## 7. 从命令到结果文件的真实代码调用链

### 7.1 数据准备

| 阶段 | 代码 | 输入 | 输出 |
|---|---|---|---|
| 解包原始题 | README 要求手工 `unzip data.zip` | `data.zip` | `data/`；当前本地根目录未见该压缩包 |
| 模态/类型整理 | `get_data.py` | `data/` 中题目、图片、RTL、testbench | 六组 `descriptions_*.jsonl` |
| 请求扰动 | `DS_get_ask.py` | 原题与模型 API | 加扰动后的问题响应 |
| 生成新数据 | `get_new_ds.py` | 扰动响应 | 新的 JSONL 测试集 |

本地已有整理后的 `save_data/*.jsonl`，所以评测器冒烟测试不依赖缺失的 `data.zip`；但想复现“从原始来源重新生成 benchmark”仍需要完整原始数据。

### 7.2 模型调用

入口：

```bash
python genben.py --mode all --model <provider-model-name>
```

主程序实际流程：

1. `--mode` 选择 `all/text/mm` JSONL；
2. 从环境变量读取 `OPENAI_API_url` 和 `OPENAI_API_KEY`；
3. `main(mode)` 用 `aiohttp` 异步发送请求；
4. 根据 ID 类型构造选择题、调试题或生成题 prompt；
5. 多模态题从 `data/Multimodal` 读取图像并 Base64 编码；
6. 外层 `for i in range(5)` 连续采样五轮；
7. `merge_done_files(...)` 合并五份响应；
8. `get_verilog(...)` 抽取代码并分流成 code/debug/choice JSONL。

因此 `--model` 只是传给 OpenAI-compatible API 的字符串，并不自动下载或加载本地权重。若接本地 vLLM/Ollama/兼容服务，需要自己保证 URL、鉴权、消息格式、视觉输入格式和模型名一致。

### 7.3 正确性与 QoR 评测

| 顺序 | 调用点 | 实际作用 | 典型输出 |
|---:|---|---|---|
| 1 | `choice_pass_5` | 知识题答案比对 | `choice_pass.txt` |
| 2 | `debug_pass` | 调试题 pass@5 | `debug_pass.txt` |
| 3 | CLI `evaluate_functional_correctness` | Icarus 功能/语法 + Yosys 综合 | `eval_*_code.jsonl_results.jsonl`、`*_yosys_results.jsonl` |
| 4 | `make_run` | 通过功能测试的设计跑 OpenLane/STA | `ppa_result/<id>-*` |
| 5 | `collect_result` | 汇总 syntax/function/synthesis | `<model>_test_results_<time>.csv` |
| 6 | PPA 解析 | 与参考面积/功耗/时序并排 | `<model>_ppa_results_<time>.csv` |

论文 Algorithm 2 与当前代码的对应关系如下图。上半部分是论文模型结果，下半部分是从 `T/T'` 到 Iverilog、Sky130/OpenLane、Yosys/OpenSTA 的总评测伪代码。

![GenBen 论文 Tables 6–7 与 Algorithm 2](./figures/paper-table6-table7-algorithm2.png)

---

## 8. 论文结果怎样读，不能怎样读

### 8.1 论文报告的主要结果

论文 Table 6 的 GenBen-all 多模态模型结果中：

| 模型 | 知识掌握 | 知识迁移 | 调试 | 功能正确 | 语法正确 | 可综合 |
|---|---:|---:|---:|---:|---:|---:|
| GPT-4o | 69.0% | 65.0% | 52.2% | 34.8% | 100.0% | 96.9% |
| Claude 3.5 | 59.0% | 55.0% | 55.4% | 35.4% | 98.6% | 90.0% |
| GPT-4-turbo | 57.0% | 56.0% | 40.0% | 21.2% | 100.0% | 93.7% |

几个重要观察：

- 高语法/综合率不意味着高功能正确率；
- Claude 3.5 的功能正确率略高于 GPT-4o，而 GPT-4o 的知识维度更强；
- 最好的功能正确率仍只有约 35%，说明“能生成合法 RTL”和“满足真实规格”之间差距很大；
- 论文还报告难度等级与通过率相关，L1 到 L3 通常逐步下降。

这些数字是论文作者在其模型版本、API、五次采样和工具环境下的报告，**不是本地复现结果**。

### 8.2 PPA 表的正确解释

![GenBen 论文 Tables 8–9：部分 Claude 3.5 / GPT-4 设计的 PPA](./figures/paper-table8-table9-ppa.png)

论文把模型生成设计与参考设计并排列出功能分数、面积、功耗及 hold/setup 时序。应注意：

- 只有能进入实现流程的设计才有 PPA 意义；
- 面积更小或功耗更低不能弥补功能错误；
- 不同工具/PDK/库版本会改变绝对数值；
- 对模型做公平比较必须固定提示、采样数、温度、工具链和失败处理规则。

---

## 9. 本地实测：已跑通什么

### 9.1 受控冒烟测试

本地选择公开 JSONL 中的 `GP_17`（2:1 MUX），把随数据提供的参考实现顶层名从 `ref_mux_2x1` 改为候选接口要求的 `top`，直接调用仓库函数：

```python
check_correctness(problem, candidate, timeout=20, completion_id=0)
```

环境与结果：

```text
Icarus Verilog: 12.0 (stable)
task_id: GP_17
passed: true
result: passed
completion_id: 0
```

结构化记录见：[runs/smoke_gp17/record.json](./runs/smoke_gp17/record.json)。

这个测试证明了四件事：

1. 本地 JSONL 字段与评测函数能正确衔接；
2. 临时 SystemVerilog 拼接、`iverilog` 编译和 `vvp` 仿真可执行；
3. testbench 的 `Mismatches: 0 in 10 samples` 能被正则识别；
4. 仓库功能评测器至少对该样例是可运行的。

### 9.2 这个结果不证明什么

它不是以下项目的复现：

- 不是任一 LLM 的生成能力测试；候选使用的是 bundled golden；
- 不是 324 题全量评测；
- 不是 pass@5；
- 不是多模态输入；
- 没有运行 Yosys/Sky130；
- 没有运行 OpenLane/OpenSTA/PPA；
- 没有复现论文 10,920 次实验。

所以本项目当前复现等级应标成 **B：受控评测链冒烟通过**，不能标成 A 级论文结果复现。

---

## 10. 代码核对发现的复现风险与实现差异

### 10.1 两处作者本机绝对路径

1. `verilog_eval/execution.py` 写死 `/home/ord1nary/.volare/...sky130...lib`；
2. `test_ppa.py` 把 `openlane_ipynb` 插入路径写成 `/root/autodl-tmp/GENBEN_test/openlane_ipynb`。

这两处必须改成可配置路径，才能移植到其他机器。

### 10.2 `data.zip` 与当前公开内容边界

README 说“只提供部分问题”，并要求先解压 `data.zip`；当前本地目录没有看到 `data.zip/data`，但已有 324 行处理后 JSONL。于是：

- 可以做已有文本题的评测器审计；
- 多模态图片加载路径可能缺素材；
- 不能验证 `get_data.py` 从原始来源重构全部 JSONL 的过程。

### 10.3 PPA 循环跳过第一条记录

`genben.py` 读取生成代码文件时先执行一次 `f.readline()`，随后才遍历：

```python
with open(problem_file, 'r') as f:
    f.readline()
    for line in f:
        ...
```

JSONL 没有表头时，这会直接跳过第一个候选。复现前应修正，并用固定小样验证输出条目数。

### 10.4 功能通过后的 PPA 输入文件存在状态耦合

主程序运行 CLI `evaluate_functional_correctness` 后，原始 `save_file` 与生成的 `save_file_results.jsonl` 是两个文件；PPA 循环却再次读取原始 `save_file`，并检查 `problem.get("passed")`。如果原始文件没有被回写 `passed`，分支行为和作者预期可能不一致。需要实际端到端跑一批任务核实。

### 10.5 语法指标实现比论文规则更粗

论文写了 warning 扣分规则；`evaluation.py` 的语法 pass@k 主要把“出现 syntax error”与“未出现 syntax error”二分。严格复现论文表格前，应确认作者实验是否用了同一版代码或额外评分脚本。

### 10.6 清理函数会调用进程级命令

`clean_up_simulation()` 使用 `pkill iverilog` 和 `pkill vvp`。在共享服务器运行可能误伤其他用户的仿真任务，应改成只管理本次启动的子进程 PID。

### 10.7 安全边界

评测器会编译和执行模型生成的 SystemVerilog；代码中的 `reliability_guard` 注释也明确说明它不是完整安全沙箱。批量评测未知模型输出时应放进隔离容器并限制 CPU、内存、磁盘和运行时间。

---

## 11. 建议的可复现改造顺序

### 阶段 1：无模型、无 PDK 的 evaluator 自检

1. 从 design 数据中抽取 5–10 个简单题；
2. 用 bundled golden 重命名为 `top`；
3. 单进程运行 `check_correctness`；
4. 记录每题 Icarus 版本、耗时和结果；
5. 人工注入语法错误和功能错误，确认分类正确。

### 阶段 2：小规模本地/统一 API 模型评测

1. 把 provider 抽象成独立适配器；
2. 固定模型版本、temperature、seed、最大 token 和五次采样；
3. 先跑 10 道纯文本 design 题；
4. 保存原始响应、抽取后 RTL、仿真日志和失败类别；
5. 再扩到 choice/debug，最后才接多模态。

### 阶段 3：综合与 PPA

1. 将 PDK root、liberty、OpenLane 路径全部改成命令行参数；
2. 固定 Sky130/OpenLane/OpenROAD/Yosys 版本；
3. 用参考 RTL 验证 5 个 `results_ppa_ref.jsonl` 数值是否能在容差内重现；
4. 修复跳首行和 `passed` 文件耦合；
5. 仅对功能通过设计计算 PPA，并保留失败原因。

### 阶段 4：论文尺度复现

完整记录：

```text
paper version + repo commit + dataset hashes
+ model exact version / API date
+ prompt + temperature + sample count
+ simulator/synth/P&R/PDK versions
+ per-task raw answers and logs
+ failure taxonomy
+ all/text/mm × L1/L2/L3 aggregate tables
```

只有完成这一阶段，才适合说“复现了论文结果”。

---

## 12. 组会分享时建议采用的逻辑

### 12.1 一句话定位

> GenBen 把硬件 LLM benchmark 从“RTL 能不能编译和仿真”扩展到“知识—迁移—调试—功能—可制造 QoR”的五维闭环，并用多模态、难度分级和扰动降低固定测试集污染。

### 12.2 三张核心图

1. Figure 2：讲数据构建、扰动、模型响应和 EDA 闭环；
2. Table 5：讲五维能力，而不是只讲 pass@k；
3. Tables 6–7 + Algorithm 2：讲“语法很高但功能很低”，以及结果是怎么跑出来的。

### 12.3 最值得讨论的问题

- 动态扰动是否真的保持硬件规格语义等价？
- testbench 高覆盖是否等于功能 oracle 正确？
- 功能不完全正确的设计是否应该比较 PPA？
- API 模型滚动升级后，benchmark 如何保留长期可比性？
- 当前开源代码的路径和指标差异会不会影响论文可复现性？

---

## 13. 最终判断

| 维度 | 判断 |
|---|---|
| 论文价值 | 高：综合 LAD benchmark，适合讲评测方法学 |
| 代码开放度 | 中：主评测脚本和部分数据开放，但根目录许可不清晰、原始素材不完整 |
| 本地可运行性 | 中：Icarus 功能评测器单例已跑通；全流程需 API、图像数据、PDK 与路径改造 |
| 论文结果复现 | 未完成 |
| 当前证据等级 | B：受控冒烟测试通过 |
| 后续优先级 | 高：很适合作为“RTL benchmark 不应只看语法/功能”的组会扩展 |

GenBen 最可靠的分享方式，是同时展示它提出的五维评测闭环和当前代码离全量复现仍有多远。这样既能体现论文的 benchmark 设计价值，也不会把“有开源仓库”误写成“全部论文实验已经可复现”。

---

## P7 关键组件一句话总结

| 组件 | 一句话总结 |
|---|---|
| five-axis benchmark | 从知识掌握、迁移、调试、代码正确性、QoR 五个维度评估 LLM 硬件能力。 |
| static/dynamic perturbation | 构建期和评测期分别改写题干或选项，降低测试集污染与记忆收益。 |
| task router | 按 task_id 中的 U/T/D/G/M 把题目分流为选择、迁移、调试、生成、多模态。 |
| verilog_eval/execution | 调用 iverilog/vvp 判定语法与功能，并调用 Yosys 检查可综合性。 |
| PPA runner | 对通过功能测试的候选用 OpenLane + Sky130 + OpenSTA 产出面积/功耗/时序。 |
| result collector | 汇总语法、功能、综合、PPA 与各维度通过率，生成统一 CSV 分数表。 |

---

## 讨论问题

1. 功能正确率约 35% 但语法/综合率接近 100%，说明瓶颈从“写出合法 RTL”转向“精确满足规格”，应如何改进 prompt 或后处理？
2. 动态扰动是否真能保持题目语义等价？若模型对扰动敏感，应归因于推理脆弱还是训练污染？
3. PPA 评估只对功能正确的设计有意义，但功能错误的设计占大多数，如何设计更公平的 QoR 指标？
