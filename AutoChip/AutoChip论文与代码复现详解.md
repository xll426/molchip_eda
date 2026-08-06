# AutoChip：论文、代码闭环与本地复现详解

> 论文：*Automatically Improving LLM-based Verilog Generation using EDA Tool Feedback*  
> 作者：Jason Blocklove、Shailja Thakur、Benjamin Tan、Hammond Pearce、Siddharth Garg、Ramesh Karri  
> 本地论文：[2411.11856_AutoChip.pdf](./2411.11856_AutoChip.pdf)  
> 论文地址：https://arxiv.org/abs/2411.11856  
> 论文 PDF：https://arxiv.org/pdf/2411.11856  
> 代码地址：https://github.com/shailja-thakur/AutoChip  
> 论文实验归档：https://zenodo.org/records/13864552  
> 本地核对日期：2026-08-02  
> 本地代码提交：`3abe0b606d8819dfe548661b0245b55a1ebab40b`

---

```text
┌─────────────────────────────────────────────────────────────────────────┐
│ P1 任务定义                                                              │
├─────────────────────────────────────────────────────────────────────────┤
│ Input:  自然语言规格 + 顶层模块头/I/O + 匹配的 testbench + 模块名 +      │
│         LLM 配置（模型 family/ID、候选数 k、最大深度 d）                  │
│ Output: 每轮 k 个候选 Verilog、Icarus 编译产物、仿真失配统计、候选 rank、│
│         贪心路径上的全局最优模块                                          │
│ Supervision: 不微调模型，不人工解释 bug；仅把 iverilog 编译错误/警告和    │
│              vvp 仿真失配比例作为反馈返回给 LLM                           │
│ Why-hard: EDA 输出是底层信号，模型需把错误映射回 RTL 根因；testbench 质量 │
│           决定反馈上限；greedy 单分支可能早期丢弃更优分支；警告惩罚会误伤   │
│           无害 warning；商业模型版本和价格漂移                             │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 0. 先给结论

AutoChip 不是一个新训练的 Verilog 大模型，而是一个“LLM 生成 + Icarus Verilog 编译/仿真 + 自动反馈修复”的推理时闭环框架。

它最值得组会分享的点不只是“让编译器报错后再问一次 LLM”，而是把以下四件事组合成了一个可实验、可计数、可比较的系统：

1. 每轮生成 `k` 个候选；
2. 用编译错误、编译警告和测试样本失配率统一排序；
3. 只沿本轮最优候选继续展开，形成 greedy tree search；
4. 可以在最后一轮切换到更强模型，以降低整体 API 成本。

本地代码和 Icarus Verilog 环境可工作。本次没有调用商业 LLM API，但已经直接调用仓库原始 `LLMResponse.calculate_rank()`，完成了解析、编译、仿真、失配数解析、评分与反馈消息构造的受控复现：

| 候选 | 编译 | 失配 | 样本数 | 仓库计算的 rank |
|---|---:|---:|---:|---:|
| 7420 正确实现 | 通过 | 0 | 239 | 1.0 |
| 故意错误实现 | 通过 | 189 | 239 | 0.2092050209 |

因此，当前复现等级可记为 **B：核心 EDA 评分闭环已实跑，论文的大规模商业模型结果未重跑**。

必须注意：论文算法和当前仓库并非逐字一致。仓库默认只实现了 succinct 上下文裁剪；配置深度会实际生成 `max_iterations + 1` 层；单轮和跨轮的同分长度判定方向相反；批量实验脚本还有入口文件、参数和日志正则不一致等问题。下面均给出代码证据。

---

## 1. 论文版本和发表状态

本地 PDF 首页标注：

- arXiv:2411.11856v3；
- 版本日期为 2025-03-04；
- 26 页；
- PDF 内仍保留 `Manuscript submitted to ACM` 和占位 DOI；
- 仓库 README 声明该工作已被 ACM TODAES 的 “Large Language Models for Electronic System Design Automation” 特刊接收。

因此，分享时更稳妥的表达是：

> 本地保存的是 arXiv v3 稿件；作者仓库声明论文已被 ACM TODAES 特刊接收，但本地 PDF 不是带正式 DOI、卷期页码的出版社最终版。

论文是 2023 年早期 AutoChip 工作的扩展版。新版把单路径迭代扩展成多候选 greedy tree search，并系统比较：

- feedback 与 zero-shot；
- 候选数 `k`；
- 深度 `d`；
- full-context 与 succinct；
- 单模型与 mixed-model；
- token 数和美元成本。

---

## 2. 它解决什么问题

### 2.1 单次生成不符合真实硬件开发流程

传统 VerilogEval 式评测通常是：

```text
设计描述 -> LLM -> Verilog -> 测试 -> pass / fail
```

真实 RTL 开发则更接近：

```text
写 RTL -> 编译 -> 看错误/警告 -> 仿真 -> 看失配 -> 修改 RTL -> 再验证
```

AutoChip 的研究问题是：

> 不由人类解释 bug，只把 EDA 工具和测试台的输出返回给模型，模型能否自动修正自己的 RTL？

### 2.2 输入和输出

输入必须至少包含：

- 自然语言规格；
- 顶层模块头和 I/O；
- 与该顶层匹配的 testbench；
- 模块名；
- LLM 类型、模型 ID、候选数和最大深度。

输出包括：

- 每轮每个候选的完整 Verilog；
- `.vvp` 编译产物；
- 对话、token 和估算成本日志；
- 每个候选的 rank；
- 整棵贪心搜索路径上的全局最优模块。

它不负责：

- 训练或微调模型；
- 自动生成可靠 testbench；
- 综合、布局布线或 PPA 优化；
- 形式验证；
- 没有测试台时的开放式功能判断；
- 多文件大型 SoC 的完整工程管理。

---

## 3. 论文方法总图

![AutoChip greedy tree search](./figures/paper-fig1-greedy-tree-search.png)

图源：论文 Figure 1，本地 PDF 第 2 页截图。

设每轮候选数为 `k`，最大深度为 `d`。

完整流程是：

```text
system prompt + design prompt
            |
            v
       LLM 生成 k 个候选
            |
            v
   对每个候选抽取 module...endmodule
            |
            v
        iverilog 编译
       /      |       \
  无模块   编译失败   编译成功
  rank=-2  rank=-1       |
                  有警告 / 无警告
                  -0.5      |
                            v
                           vvp
                            |
                 解析最后一行失配统计
                            |
       rank=(samples-mismatches)/samples
                            |
                      本轮选择最高分
                            |
              成功(rank=1)？--是-->停止
                            |
                            否
                            v
              候选 RTL + 工具反馈进入下一轮
```

论文称其为 tree search，但它不是保留多个分支的 beam search，也不是 MCTS：

- 每层确实展开 `k` 个候选；
- 只选择本层最好候选继续；
- 其他 `k-1` 个候选不再展开；
- 所以更准确地说是“每层多采样、单分支贪心展开”。

---

## 4. 评分函数

### 4.1 论文定义

论文第 5 页给出的等级是：

| 条件 | rank |
|---|---:|
| 响应里找不到完整 Verilog module | -2 |
| Icarus 编译失败 | -1 |
| 编译成功但有 warning | -0.5 |
| 能仿真 | 正确样本比例，范围 0 到 1 |
| 所有样本正确 | 1，立即成功 |

若 testbench 报告总样本数为 `N`，失配数为 `M`：

```text
rank = (N - M) / N
```

这种评分比纯 pass/fail 多出一个“离正确还有多远”的近似信号。

### 4.2 代码实现位置

核心类位于：

- `autochip_scripts/languagemodels.py`
  - `LLMResponse.parse_verilog()`
  - `LLMResponse.calculate_rank()`
- `autochip_scripts/verilog_handling.py`
  - `find_verilog_modules()`
  - `compile_iverilog()`
  - `simulate_iverilog()`
  - `verilog_loop()`

实际编译命令为：

```bash
iverilog -Wall -Winfloop -Wno-timescale -g2012 -s tb \
  -o <response_outdir>/<module>.vvp \
  <response_outdir>/<module>.sv <testbench>
```

实际仿真命令为：

```bash
vvp -n <response_outdir>/<module>.vvp
```

代码只在仿真标准输出的最后一行寻找：

```text
Mismatches: <M> in <N> samples
```

正则为：

```python
r"Mismatches: (\d+) in (\d+) samples"
```

所以自定义 testbench 若没有严格输出这一行，`calculate_rank()` 会抛出 `ValueError`，即使仿真本身已经正确结束。

### 4.3 工具反馈示例

![Simulation feedback](./figures/paper-fig6-simulation-feedback.png)

图源：论文 Figure 6，本地 PDF 第 8 页截图。

功能失败时，代码把完整 `sim_out` 放进下一轮用户消息：

```text
The testbench simulated, but had errors. Please fix the module.
The output of iverilog is as follows:
<完整仿真 stdout>
```

编译失败时返回 `stderr`；编译有 warning 时也返回 `stderr`；通过时消息是：

```text
The testbench completed successfully
```

---

## 5. Prompt 和上下文怎样进入下一轮

### 5.1 初始 system prompt

仓库在 `verilog_handling.verilog_loop()` 内硬编码 system prompt，要求模型：

- 作为 Verilog 自动补全引擎；
- 返回端到端完整模块；
- 不创建额外模块；
- 收到错误时修复整个模块；
- 只把完整 Verilog 放在代码围栏内。

论文给出的配置、输出目录和 system prompt 示例见下图。

![Configuration, output and context examples](./figures/paper-fig3-fig5-output-and-context.png)

图源：论文 Figures 3–5，本地 PDF 第 7 页截图。

### 5.2 初始 design prompt

入口 `generate_verilog.py` 从 `config_values['prompt']` 读取文本文件，并将全文作为第一条 user message。

VerilogEval 文件已经把自然语言描述写在注释里，并提供不完整的顶层 module header。例如 7420 任务描述两个 4 输入 NAND 门，并给出全部端口。

testbench 不会直接拼进 prompt。模型只能看到：

- system prompt；
- design prompt；
- 后续工具反馈。

它不能看到参考模块源码；参考模块只藏在 testbench 中参与仿真。

### 5.3 succinct 上下文在代码里如何实现

首轮后消息顺序是：

```text
0 system
1 design user
2 chosen assistant RTL
3 feedback user
```

第二轮生成之后，如果还没成功，代码执行两次：

```python
conv.remove_message(2)
```

因为第一次删除后列表左移，所以实际删掉旧的 assistant RTL 和旧 feedback，只留下 system、初始 design，再追加当前轮最佳 RTL 与当前 feedback。

下一轮上下文因此是：

```text
system + original design + latest chosen RTL + latest tool feedback
```

这就是论文所称 succinct feedback。

### 5.4 full-context 在当前代码中的状态

论文比较了 full-context 与 succinct：

- full-context：保留全部历史 RTL 和反馈；
- succinct：只保留最近一轮 RTL 和反馈。

当前 `verilog_loop()` 没有 `full_context` 参数，也没有关闭上述删除逻辑的配置项。因此：

> 论文报告过 full-context 实验，但当前提交的主循环固定执行 succinct 裁剪；若要复现实验表中的 full-context，需要修改代码或取得作者当时的实验版本。

---

## 6. 多候选贪心搜索的真实代码流程

### 6.1 每层生成

`generate_verilog_responses()` 根据 `model_type` 创建适配器，并调用：

```python
model.generate(conversation=conv, num_candidates=num_candidates)
```

每个返回文本被包装为：

```python
LLMResponse(iteration, response_num, response_text)
```

候选目录是：

```text
<outdir>/iter<iteration>/response<index>/
```

其中保存：

- `<module>.sv`；
- `<module>.vvp`；
- `log.txt`。

### 6.2 Verilog 抽取

`find_verilog_modules()` 用正则寻找：

```text
module <name> ... ; ... endmodule
```

所有匹配模块会拼接到 `parsed_text`。这允许响应有 Markdown 解释，但也有边界：

- 复杂 parameter/端口括号可能被正则误截断；
- 宏生成的 module 不会被理解；
- 文本中若有多个完整 module，会全部写进候选文件；
- 系统 prompt 虽要求代码围栏，但解析器实际上不依赖围栏。

### 6.3 本轮最优如何选

代码为：

```python
max(responses, key=lambda resp: (resp.rank, -resp.parsed_length))
```

含义是：

1. rank 越大越好；
2. 同 rank 时，`-parsed_length` 越大越好；
3. 即本轮同分时偏好更短的解析代码。

### 6.4 全局最优如何保存

主循环同时维护 `global_max_response`。rank 更高时更新；rank 相同则代码判断：

```python
max_rank_response.parsed_length > global_max_response.parsed_length
```

这意味着跨轮同分时偏好更长代码。

于是存在一个明确不一致：

| 场景 | 同分偏好 |
|---|---|
| 同一轮的多个候选 | 更短 |
| 当前轮最佳与历史全局最佳 | 更长 |

论文只说返回最高 rank，没有定义同分长度策略。复现实验若大量候选同分，这一实现细节可能改变最终保存的 RTL，但不会改变是否 pass 的统计。

### 6.5 谁决定停止

只有两个正常停止条件：

```python
if max_rank_response.rank == 1:
    success = True

if iterations >= max_iterations:
    timeout = True
```

循环从 `iterations = 0` 开始，并在循环末尾才加一。因此 `max_iterations=3` 实际执行编号为 0、1、2、3 的四层，也就是论文公式中的 `d+1` 组生成。

这与论文使用的最大响应数公式一致：

```text
k * (d + 1)
```

但 README 把 `iterations` 描述为“退出前的迭代次数”，容易让使用者误认为只运行 3 次。

### 6.6 最终返回谁

函数返回 `global_max_response`，不是最后一轮候选，也不一定是最后一轮本轮最优。

这保证后续修复若退化，最终仍保留历史最高 rank 版本。

![Successful greedy path](./figures/paper-fig7-successful-search-path.png)

图源：论文 Figure 7，本地 PDF 第 10 页截图。绿色节点是每层继续展开的唯一分支。

---

## 7. Mixed-model 流程

Mixed-model 不是将多个模型的回答投票融合，而是按迭代编号切换生成模型。

示例意图是：

```text
depth 0 ... d-1：GPT-4o-Mini / GPT-3.5 / Claude Haiku
depth d：GPT-4o
```

`validate_mixed_model_config()` 会把负索引转换成：

```python
start_iteration += max_iterations + 1
```

因此 `start_iteration=-1` 表示最后一层。

`get_iteration_model()` 按 `start_iteration` 降序查找，选择当前 iteration 已经达到的最近一个模型配置。

论文核心动机是：

- 小模型先低成本解决简单题；
- 难题带着部分正确 RTL 和工具反馈进入最后一轮；
- GPT-4o 只为未提前成功的问题付费。

![Mixed-model token Pareto](./figures/paper-fig13-mixed-model-token-pareto.png)

图源：论文 Figure 13，本地 PDF 第 19 页截图。

![Mixed-model cost Pareto](./figures/paper-fig14-mixed-model-cost-pareto.png)

图源：论文 Figure 14，本地 PDF 第 21 页截图。

需要注意配置键名：

- 当前仓库代码和 README 使用 `mixed-models`；
- 论文 Figure 2 截图中显示的是 `mixed-model`；
- 按当前代码运行必须使用复数形式，否则 mixed-model 配置不会启用。

---

## 8. 模型适配层

`languagemodels.py` 和 `generate_verilog_responses()` 暴露以下 family：

| family | 调用方式 | 需要的资源 |
|---|---|---|
| ChatGPT | OpenAI chat completions | `OPENAI_API_KEY` |
| Claude | Anthropic messages API | `ANTHROPIC_API_KEY` |
| Gemini | Google Generative AI | `GEMINI_API_KEY` |
| Mistral | Mistral API | `MISTRAL_API_KEY` |
| CodeLlama | Transformers 本地模型 | GPU/模型权重 |
| RTLCoder | Transformers 本地模型 | GPU/模型权重 |
| Human | 打开文本编辑器人工输入 | `EDITOR` 或 nano |

论文正式评估的是：

- Claude 3 Haiku；
- GPT-3.5-Turbo；
- GPT-4o-Mini；
- GPT-4o。

仓库其他适配器不能因为“类存在”就认定已验证：

- CodeLlama 代码使用 `CodeLlamaTokenizer`、`LlamaForCausalLM`，当前文件未导入这些名字；
- Mistral 代码使用 `ChatMessage`，当前文件未见对应导入；
- Gemini 通过循环发起 `num_candidates` 次请求，并非一次 API 调用原生返回多个候选；
- HumanInput 的返回值是字符串，不是候选字符串列表，和上层枚举预期不一致；
- 本次只实测了不需要模型 API 的 `LLMResponse` EDA 路径。

所以当前最可信的可用范围是论文实际使用的 OpenAI/Anthropic 适配层加 Icarus 闭环；其余适配器需要逐个修复和冒烟测试。

---

## 9. 数据集与本地文件

论文使用 VerilogEval v1，并明确说明实验完成后 VerilogEval v2 才发布。

本地 `verilogeval_prompts_tbs/` 包含：

| 子集 | 本地目录数 | 含义 |
|---|---:|---|
| `ve_testbenches_machine/` | 143 | VerilogEval-Machine 有效题 |
| `ve_testbenches_human/` | 156 | VerilogEval-Human 题目录 |
| `validation_set/` | 10 | 本地开发/验证子集 |

此外有四个 JSONL：

- `VerilogDescription_Human.jsonl`；
- `VerilogDescription_Machine.jsonl`；
- `VerilogEval_Human.jsonl`；
- `VerilogEval_Machine.jsonl`。

每个已经展开的任务目录通常包含：

```text
<problem>.sv                # 设计 prompt + module header
<problem>_tb.sv             # 自检 testbench + reference_module
canonical_solution.txt      # 正确实现主体
```

论文解释 Machine prompt 是从正确电路自动生成的描述，通常更直接；Human prompt 含更抽象的自然描述、K-map、FSM、波形等题型，因此整体更难。

---

## 10. 论文实验设置

### 10.1 六个研究问题

论文围绕六个 RQ：

1. EDA feedback 是否优于 zero-shot；
2. 候选数和搜索深度如何影响正确率；
3. feedback 对成本的影响；
4. full-context 和 succinct 是否有差异；
5. 哪些硬件问题类别更容易；
6. mixed-model 能否兼顾质量和成本。

### 10.2 主要变量

- 候选数 `k`：代表每层采样数；
- 深度 `d`：最大反馈修复层数；
- 最大潜在调用候选数：`k*(d+1)`；
- 成功标准：至少一个生成模块通过 testbench 的全部样本；
- 比较指标：成功率、平均输入/输出 token、按当时单价估算的美元成本。

论文配置和模型单价见下图。

![Paper configuration and model costs](./figures/paper-fig2-table1-config-and-models.png)

图源：论文 Figure 2 和 Table 1，本地 PDF 第 6 页截图。美元单价是论文发表时的历史价格，不能直接当成当前 API 价格。

### 10.3 主要结果表

![Main results](./figures/paper-table3-table4-main-results.png)

图源：论文 Tables 3–4，本地 PDF 第 12 页截图。

几个适合组会直接讲的结果：

- GPT-4o、succinct、`k=5,d=10`：Machine 87.4%，Human 84.0%；
- GPT-4o zero-shot、`k=55`：Machine 83.2%，Human 78.2%；
- 所以在相同最大候选数 55 下，反馈搜索比独立 zero-shot 多样本更好；
- 对 Haiku、GPT-3.5 和 GPT-4o-Mini，feedback 并非稳定优于 zero-shot；
- 增大 `k` 和 `d` 通常都有帮助，但论文观察 `k` 的影响往往更大；
- full-context 和 succinct 的成功率相近，succinct token 更少，所以后续实验主要用 succinct。

论文摘要给出的最好情形总结是：

- 相对最好 zero-shot，成功设计数提高 5.8%；
- 成本降低 34.2%；
- 小模型最后接一轮 GPT-4o，可达到与 GPT-4o feedback 相当的成功水平；
- mixed-model 相比全程 GPT-4o feedback 成本低 41.9%；
- 相比 zero-shot 成本总体低 89.6%。

这些都是论文报告值，不是本机本次运行结果。

### 10.4 mixed-model 的代表性结果

论文第 20 页举例：

- VerilogEval-Human mixed-model 最高约 75%，成本约 0.025 美元；
- 单独 GPT-4o 达到相近约 75% 时成本约 0.043 美元；
- 后者成本高约 72%。

这说明 mixed-model 的收益来自条件调用：小模型已经解决的题不会进入昂贵的最终轮。

### 10.5 题型分析

论文结论不是“反馈对某个特定类别必然特别有效”，而是：

- 基础语法和简单逻辑总体容易；
- 时序逻辑更难；
- K-map、FSM 图和波形理解等抽象输入更难；
- Machine prompt 通常比 Human prompt 更易；
- 强模型更有能力把工具输出对应回 RTL 根因；
- 小模型常能读到错误，却不能稳定完成正确修复。

---

## 11. 本地受控复现

### 11.1 复现目标

本次不调用 OpenAI、Anthropic 等付费 API，也不把 canonical solution 冒充模型生成结果。

验证的是仓库中与论文方法直接对应的确定性部分：

1. LLM 文本中的 module 抽取；
2. 候选 `.sv` 写出；
3. Icarus Verilog 编译；
4. vvp 仿真；
5. testbench 最后一行失配解析；
6. rank 计算；
7. 成功/失败反馈消息构造。

### 11.2 环境

| 组件 | 本地值 |
|---|---|
| Python | 3.12 |
| Icarus Verilog | 12.0 stable |
| vvp | 12.0 stable |
| 任务 | `validation_set/7420` |
| 顶层 | `top_module` |
| 测试样本 | 239 |

第三方 Python 包只临时安装在 `/tmp/autochip_pydeps`，没有写入系统 Python，也没有修改仓库源码。

### 11.3 两个候选

正确候选使用仓库自带 `canonical_solution.txt` 的模块主体，仅用于验证 EDA 评分上限。

错误候选故意写成：

```verilog
assign p1y = p1a;
assign p2y = p2a;
```

而正确功能应是两组 4 输入 NAND。

### 11.4 实际输出

```text
Testbench ran successfully
Mismatches: 0
Samples: 239
correct {'compiled': True, 'rank': 1.0, 'parsed_length': 251}

Simulation error
Mismatches: 189
Samples: 239
incorrect {'compiled': True, 'rank': 0.20920502092050208,
           'parsed_length': 202}
```

错误候选的计算可手工核对：

```text
(239 - 189) / 239 = 50 / 239 = 0.20920502092050208
```

与代码输出完全一致。

### 11.5 复现产物

- [运行记录](./runs/rank_smoke_7420/record.json)
- [正确候选写出文件](./runs/rank_smoke_7420/correct/top_module.sv)
- [错误候选写出文件](./runs/rank_smoke_7420/incorrect/top_module.sv)
- [最后一次仿真波形](./runs/rank_smoke_7420/last_simulation_wave.vcd)

两个 `.vvp` 也保存在对应目录。

### 11.6 本次没有复现什么

没有复现：

- GPT-4o/Claude 的真实候选生成；
- 多轮语言模型自修复；
- 143 + 156 题的完整参数扫描；
- 论文成功率表；
- 论文 token 和美元成本；
- Zenodo 原始全量运行日志再统计。

因此不能写成“AutoChip 论文结果已完全复现”。

---

## 12. 代码审计发现的复现问题

### 12.1 直接导入的循环依赖

`languagemodels.py` 导入 `verilog_handling`，而 `verilog_handling.py` 又导入 `languagemodels`。

直接执行：

```python
from languagemodels import LLMResponse
```

在当前 Python 环境会因为 `compile_iverilog(..., response: lm.LLMResponse)` 的运行时类型注解求值而报：

```text
AttributeError: partially initialized module 'languagemodels'
has no attribute 'LLMResponse'
```

仓库正式入口先导入 `verilog_handling`，该顺序能完成加载。本地 smoke 也沿这个工作顺序导入。

建议修复：

- 使用 `from __future__ import annotations`；或
- 将类型注解写成字符串；或
- 把 `LLMResponse` 移到独立模块，打破环。

### 12.2 仿真工作目录不是候选目录

`subprocess.run(simulator_cmd, ...)` 没有设置 `cwd=response_outdir`。

因此 testbench 中：

```verilog
$dumpfile("wave.vcd");
```

会把波形写到启动 Python 的当前目录，而不是 `iterN/responseK/`。并行批量运行还可能互相覆盖同名波形。

### 12.3 shell 命令未安全引用路径

编译命令用 f-string 拼接并设置 `shell=True`。路径若含空格或 shell 元字符会失败，外部不可信路径还可能形成命令注入面。

更稳妥的是传参数列表并使用 `shell=False`。

### 12.4 编译警告直接阻止仿真

只要 `comp_err != ""`，候选就被记为 `rank=-0.5`，不会继续仿真。

但 Icarus 的 stderr 不一定全是会影响功能的 warning；这可能使功能正确但有无害警告的候选，排名低于任意能仿真的错误候选。

这是论文明确采用的策略，不是单纯 bug，但分享时应说明评价偏好。

### 12.5 仿真返回码和 stderr 没有参与判断

`simulate_iverilog()` 返回 `(returncode, stderr, stdout)`，但 `calculate_rank()` 主要从 stdout 最后一行提取 Mismatch；没有先检查 `sim_return`。

若仿真异常但碰巧仍输出匹配格式，或正常测试台输出格式不同，行为会不可靠。

### 12.6 空样本可能除零

若 testbench 输出：

```text
Mismatches: 0 in 0 samples
```

代码会执行 `(samples-mismatches)/samples`，没有零样本保护。

### 12.7 本轮和跨轮同分规则相反

前文已核准：

- 单轮：短者优先；
- 全局：长者优先。

建议统一并显式记录 tie-break。

### 12.8 当前主循环只有 succinct

论文 Table 3 的 full-context 不能直接由当前配置重现。

### 12.9 批量脚本与当前入口不一致

`run_all_tests.sh` 存在多处陈旧接口：

- 变量指向 `auto_create_verilog.py`，当前目录只有 `generate_verilog.py`；
- `-m Claude` 实际会被当前参数解析器当作 model ID，而 family 应使用 `-f`；
- `--prompt="$(cat ...)"` 传入的是 prompt 内容，但当前入口把该值当文件路径再 `open()`；
- 脚本定义了 `autogen_script`，实际调用时又没有使用该变量；
- 默认数据路径指向本地不存在的 `rerun_haiku_machine`。

所以不能直接运行它复现论文参数扫描。

### 12.10 参数扫描解析器有日志拼写不一致

`parse_parameter_sweep.py` 查找：

```text
Rank of best repsonse:
```

而 `generate_verilog.py` 写的是：

```text
Rank of best response:
```

`repsonse` 拼写错误会导致 rank 正则匹配不到，最终 CSV 缺数据。

### 12.11 README 的 LICENSE 链接与文件名不一致

README 链接到根目录 `LICENSE`，当前根目录没有该文件；实际 Apache-2.0 文本位于：

```text
autochip_scripts/LICENCE
```

代码许可意图清楚，但仓库链接和文件布局不规范。

### 12.12 成本常量是历史快照

代码把 GPT-4、GPT-4o-Mini、GPT-3.5 和 Claude 的每百万 token 单价硬编码在 `verilog_handling.py`。

API 型号和价格都会变化，因此：

- 复现论文历史成本可保留论文当时常量；
- 估算当前成本必须重新核价；
- 最好把单价、日期和币种写入每次实验 manifest。

---

## 13. 如何正确运行单题

### 13.1 安装依赖

```bash
cd /mnt/d/AI4eda/AutoChip
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

还需要系统可执行文件：

```bash
iverilog -V
vvp -V
```

### 13.2 配置 API key

只设置实际要用的模型 key，例如：

```bash
export OPENAI_API_KEY='...'
```

不要把 key 写进 `config.json`、日志或 Markdown。

### 13.3 从脚本目录运行

当前导入和相对路径设计更适合在 `autochip_scripts/` 内执行：

```bash
cd /mnt/d/AI4eda/AutoChip/autochip_scripts
python generate_verilog.py -c config.json
```

示例配置应使用当前代码认可的键：

```json
{
  "general": {
    "prompt": "../verilogeval_prompts_tbs/validation_set/7420/7420.sv",
    "name": "top_module",
    "testbench": "../verilogeval_prompts_tbs/validation_set/7420/7420_tb.sv",
    "model_family": "ChatGPT",
    "model_id": "gpt-4o-mini",
    "num_candidates": 2,
    "iterations": 3,
    "outdir": "outputs/7420",
    "log": "log.txt",
    "mixed-models": false
  }
}
```

注意 `iterations=3` 会运行深度 0 到 3，最多产生 `2*(3+1)=8` 个候选。

### 13.4 mixed-model 示例

```json
{
  "general": {
    "prompt": "../verilogeval_prompts_tbs/validation_set/7420/7420.sv",
    "name": "top_module",
    "testbench": "../verilogeval_prompts_tbs/validation_set/7420/7420_tb.sv",
    "num_candidates": 5,
    "iterations": 10,
    "outdir": "outputs/7420_mixed",
    "log": "log.txt",
    "mixed-models": true
  },
  "mixed-models": {
    "cheap": {
      "start_iteration": 0,
      "model_family": "ChatGPT",
      "model_id": "gpt-4o-mini"
    },
    "strong_final": {
      "start_iteration": -1,
      "model_family": "ChatGPT",
      "model_id": "gpt-4o"
    }
  }
}
```

---

## 14. 若要真正复现论文表格，建议的顺序

### 阶段 A：先修基础可复现性

1. 修循环导入；
2. 为 simulator 设置独立 cwd；
3. 修 `run_all_tests.sh` 入口和参数；
4. 修 `parse_parameter_sweep.py` 正则拼写；
5. 把 full-context 做成明确开关；
6. 记录模型精确版本、API seed/temperature、价格日期；
7. 为每个任务保存请求 ID、原始响应和失败原因。

### 阶段 B：验证 10 题 validation set

建议先跑：

- `k=1,d=0`：zero-shot 对照；
- `k=1,d=3`：单路径修复；
- `k=2,d=3`：小规模贪心树；
- 固定同一模型和温度；
- 每配置至少重复多次，因为 API 采样不是确定性的。

### 阶段 C：全量 143/156 题

需要控制：

- API 预算；
- 并发速率限制；
- testbench 超时；
- wave 文件冲突；
- 模型版本漂移；
- 某题提前成功导致实际调用数小于理论最大值。

### 阶段 D：论文对照

最终表必须同时报告：

| 字段 | 内容 |
|---|---|
| paper | 论文 Table/Figure 的原始数值 |
| local | 当前模型版本的本地实测数值 |
| delta | local - paper |
| calls | 实际请求次数，不是只写理论上限 |
| tokens | input/output 分开 |
| price snapshot | 价格与日期 |
| failures | API、解析、编译、仿真、格式错误分别统计 |

---

## 15. 与相邻工作的关系

### 15.1 对比 VerilogEval

VerilogEval 提供任务、prompt、testbench 和 pass@k 评测；AutoChip 在其上增加工具反馈闭环。

```text
VerilogEval：多次独立生成 -> 是否至少一个通过
AutoChip：每层多生成 -> 选最好 -> 带反馈修复 -> 再生成
```

### 15.2 对比 RTLCoder

RTLCoder 的主要贡献是数据和专用轻量模型训练；AutoChip 不训练模型，专注推理时修复。

二者可组合：仓库已有 RTLCoder adapter，理论上可把 RTLCoder 当生成器放进 AutoChip，但当前 adapter 仍需单独验证。

### 15.3 对比 MAGE

MAGE 更偏多 Agent 角色协同和多轮生成；AutoChip 的决策主体更简单，排序信号直接来自 testbench 失配比例，因而闭环更容易解释。

### 15.4 对比 VerilogCoder

VerilogCoder 引入多 Agent、RAG、工具调用和波形分析；AutoChip 是更干净的单主循环基线。

如果研究问题是“EDA feedback 本身是否有效”，AutoChip 更适合作为消融基线；如果研究问题是“如何解决复杂错误和知识缺口”，VerilogCoder 的系统更丰富。

---

## 16. 组会建议讲法

### 16.1 一句话

> AutoChip 把 Verilog 生成从一次性回答改造成每层多采样、Icarus 打分、沿最优候选继续修复的贪心闭环，并证明强模型比小模型更能利用原始 EDA 错误信息。

### 16.2 三张核心图

建议按这个顺序：

1. Figure 1：讲 `k` 个候选、rank 和深度 `d`；
2. Tables 3–4：讲 feedback 与相同调用上限的 zero-shot；
3. Figure 14：讲“小模型先跑、GPT-4o 最后一轮”的成本收益。

### 16.3 最值得讨论的问题

- testbench 失配比例是否真能代表“离正确有多近”？
- warning 一律记为负分是否太激进？
- greedy 只保留一个分支，会不会早期选错方向？
- 把原始仿真日志直接交给小模型，信息是否过于低层？
- mixed-model 收益有多少来自提前停止，而不是强模型利用了小模型修复轨迹？
- 如果 testbench 有漏洞，闭环是否只会学会“过测试”而非实现真实规格？

### 16.4 不应夸大的地方

不要说：

- 已经自动生成可 tapeout 的完整芯片；
- 所有模型都能从 feedback 获益；
- 本地已经完整复现论文成功率；
- 这是保留完整搜索树的通用 tree search；
- 仓库所有声明支持的模型适配器都已跑通。

---

## 17. 最终评价

### 优点

- 研究问题清楚：EDA feedback 是否真的帮助 RTL 生成；
- rank 规则简单、可解释；
- 候选数、深度、上下文和模型组合都可消融；
- Icarus + VerilogEval 使功能验证部分开源；
- mixed-model 把模型能力和调用成本联系起来；
- 当前核心评分路径可以在本地直接跑通。

### 局限

- 必须预先拥有高质量 testbench；
- 只做功能仿真，不覆盖综合/PPA/形式验证；
- 贪心搜索会丢弃非当前最优分支；
- 小模型常不能从低层日志推断根因；
- 商业模型版本和价格随时间变化；
- 当前仓库与论文全量实验版本存在接口差异；
- 批量复现实验脚本需要修复；
- 多个额外模型 adapter 只停留在代码存在，不能视为已验证。

### 复现判定

| 项目 | 判定 |
|---|---|
| 论文 PDF | 已本地归档并逐页核对 |
| 代码 | 已本地归档并核对到函数级调用链 |
| 数据 | 143 Machine、156 Human、10 validation 目录存在 |
| Icarus 评分闭环 | 已实跑 |
| 正确/错误候选 rank | 已实跑并手算核对 |
| LLM API 多轮修复 | 本次未跑 |
| 论文主表 | 未完整复现 |
| 当前总等级 | B：核心确定性闭环可复现 |

AutoChip 很适合作为“RTL Agent 工具反馈闭环”的基础论文分享：它比单次 Verilog 生成更接近工程过程，又比复杂多 Agent 系统更容易看清每个反馈究竟怎样改变下一轮。真正复现时，最关键的不是先烧 API 预算，而是先修仓库的批量入口、上下文模式开关、日志统计和运行隔离。

---

## P7 关键组件一句话总结

| 组件 | 一句话总结 |
|---|---|
| greedy tree search | 每层采样 k 个候选，只沿 rank 最高的单分支继续展开，最多 d+1 层。 |
| rank function | 按 -2/-1/-0.5/(N-M)/N 五级评分，用 testbench 失配比例衡量离正确有多远。 |
| succinct feedback | 每轮只保留 system prompt、原始 design、最新 RTL 和最新工具反馈。 |
| mixed-model schedule | 前几轮用便宜小模型，最后一轮条件切换到强模型以降低成本。 |
| Icarus EDA loop | 抽取 module → iverilog 编译 → vvp 仿真 → 解析 Mismatches → 构造反馈。 |
| model adapter layer | 包装 OpenAI/Anthropic/Gemini/Mistral/本地模型的统一 generate 接口。 |

---

## 讨论问题

1. rank 函数把 warning 一律记为 -0.5 是否会过滤掉功能正确但带无害 warning 的优质候选？应如何改进？
2. greedy 单分支展开相比 beam search/MCTS 损失了多少探索收益，什么证据能说明 k 比 d 更重要？
3. mixed-model 的成本收益主要来自“小模型提前成功”还是“强模型利用前序修复轨迹”？如何设计消融实验区分二者？

