# CVDP：综合 Verilog 设计问题基准——论文、代码与本地复现详解

> 论文：**Comprehensive Verilog Design Problems: A Next-Generation Benchmark Dataset for Evaluating Large Language Models and Agents on RTL Design and Verification**  
> 本地论文：[2506.14074_CVDP.pdf](./2506.14074_CVDP.pdf)  
> arXiv：<https://arxiv.org/abs/2506.14074>；PDF：<https://arxiv.org/pdf/2506.14074>  
> 代码：<https://github.com/NVlabs/cvdp_benchmark>  
> 完整数据：<https://huggingface.co/datasets/nvidia/cvdp-benchmark-dataset>  
> 本地代码版本：commit `8e894cf74414`；Apache-2.0 + NOTICE  
> 核对日期：2026-08-02

---

```text
┌──────────────────────────────────────────────────────────────┐
│ P1 任务定义                                                   │
├──────────────────────────────────────────────────────────────┤
│ Input：Verilog 设计问题描述（自然语言规格、部分 RTL、test plan、 │
│ 已有模块/文档），分 Non-Agentic 平面 prompt 或 Agentic mini   │
│ repository 两种形态。                                         │
├──────────────────────────────────────────────────────────────┤
│ Output：生成的 RTL / testbench / checker / assertion / 调试修复 │
│ 或 comprehension 回答；最终由 hidden executable harness 判定。 │
├──────────────────────────────────────────────────────────────┤
│ Supervision：人类工程师编写的 reference solution/patch 与 hidden │
│ harness（Cocotb/pytest/Icarus/Yosys/Verilator/Xcelium）。    │
├──────────────────────────────────────────────────────────────┤
│ Why-hard：SystemVerilog 语义复杂；验证需跨周期行为理解；agent  │
│ 需多轮工具使用；checker/assertion 类别极不平衡；LLM judge 主 │
│ 观；部分任务依赖商业 EDA license。                            │
└──────────────────────────────────────────────────────────────┘
```

## 1. 结论先行：CVDP 不是“漏洞检测 benchmark"

CVDP 的全称是 **Comprehensive Verilog Design Problems**。它不是只检查 RTL 漏洞，也不是单纯的 specification-to-RTL 数据集，而是一套覆盖设计与验证全流程的综合 benchmark：

```text
RTL 补全 / 规格转 RTL / 修改 / 模块复用 / lint-QoR 改进
+ testbench stimulus / checker / assertion 生成
+ RTL 调试与修复
+ RTL/规格、testbench/test plan 对应关系
+ RTL 与 testbench 技术问答
```

它同时提供两种交互形态：

- **Non-Agentic**：一次性给 model prompt + oracle context，模型一次回答；
- **Agentic**：给 agent 一个 mini repository，可读写文件、调用仿真/综合工具并迭代修改。

论文版本包含 **783 个问题、13 类任务**，其中 617 个 Non-Agentic、166 个 Agentic。论文的核心结论是：即使是当时最强模型，code-generation 总体 `pass@1` 也不超过约 34%；验证类任务，尤其 testbench checker 生成，比普通 RTL 生成明显更难。

本地当前状态：**论文、完整框架和 v1.1.0 的 6 组公开 example JSONL 已归档；已用官方 `local_export` 实际跑通一个 non-agentic LFSR 题的 prompt 构造。完整 783 题数据尚未放入本地，Docker harness、模型推理与论文结果未复现。**

---

## 2. 论文身份与版本边界

本地 PDF 是 `arXiv:2506.14074v1`，日期 2025-06-17，首页写 `Preprint. Under review.`。因此宜称为“2025 arXiv 预印本”，不要无依据写成某会议已录用论文。

论文描述的是首版 783 题数据；当前本地仓库文档已经演进到 **CVDP v1.1.0**，包含：

- 新的 open-source simulation image；
- local inference export/import；
- agent contract、patch 跟踪和 heavy-repository 支持；
- agentic/non-agentic 互相转换；
- 更新后的 score-based reporting。

所以必须区分：

| 内容 | 来源 | 能否直接等同于论文实验 |
|---|---|---|
| 783 题、论文 Tables 1–5 | 2025 v1 论文 | 是论文事实 |
| 当前 `example_dataset/*v1.1.0*` | 新版仓库 | 否，只是当前工具样例 |
| 当前 local inference / heavy agentic | 新版代码 | 否，是后续基础设施能力 |
| 本地 `local_export` 结果 | 当前机器实测 | 否，只证明 prompt 生成链可运行 |

---

## 3. 为什么需要 CVDP

论文认为 VerilogEval、RTLLM 等已有 benchmark 有三个共同限制：

1. 主要是小型、自包含、手工 prompt 的 RTL 生成题；
2. 随模型进步，通过率已经较高，缺少区分未来系统的 headroom；
3. 没有充分覆盖 verification、debug、assertion、module reuse、tool-using agent 等真实工作。

CVDP 对应的设计是：

- 约 35 名具有 4 年以上经验的硬件工程师从头写题；
- 硬件设计/管理领域博士或专家复审；
- reference solution 与缺失 context 做 sanity check；
- LLM 做辅助质量过滤，但不是让 LLM 直接替代人类出题；
- 1,313 个初始问题经过过滤后保留 783 个。

它的 benchmark 对象不只是“base LLM”，也包括能在 Docker 中读写 repository、调用 EDA 工具的 agent。

---

## 4. 13 个任务类别完整拆解

![CVDP 论文 Table 1 与 Figure 1：类别数量和总评测流](./figures/paper-table1-categories-figure1-flow.png)

### 4.1 Code Generation：9 类

| ID | 类别 | Non-Agentic | Agentic | 任务输出 |
|---|---|---:|---:|---|
| cid02 | RTL Code Completion | 94 | 0 | 补全被挖空/不完整 RTL |
| cid03 | Natural Language Spec to Code | 78 | 37 | 从规格生成 RTL |
| cid04 | RTL Code Modification | 56 | 26 | 按要求修改已有 RTL |
| cid05 | Spec to RTL with Module Reuse | 0 | 26 | 复用多个已有模块并写 glue logic |
| cid07 | Code Improvement：Linting/QoR | 41 | 0 | 改善 lint、面积/性能等 |
| cid12 | Testbench Stimulus Generation | 68 | 18 | 从 test plan 写 stimulus |
| cid13 | Testbench Checker Generation | 53 | 18 | 写 checker / scoreboard |
| cid14 | Assertion Generation | 68 | 30 | 写 SVA/断言 |
| cid16 | Debugging / Bug Fixing | 36 | 11 | 定位并修复 RTL/验证错误 |

合计：

```text
Code-generation Non-Agentic = 494
Code-generation Agentic     = 166
```

### 4.2 Code Comprehension：4 类，仅 Non-Agentic

| ID | 类别 | 数量 | 评分方法 |
|---|---|---:|---|
| cid06 | RTL ↔ Specification correspondence | 34 | BLEU / reference correspondence |
| cid08 | Testbench ↔ Test Plan correspondence | 29 | BLEU / reference correspondence |
| cid09 | RTL Question & Answer | 34 | LLM subjective judge |
| cid10 | Testbench Question & Answer | 26 | LLM subjective judge |

合计 123；因此全部 Non-Agentic 为 `494 + 123 = 617`，再加 166 个 Agentic，得到 783。

### 4.3 题目主题分布

作者要求类别内部还要覆盖：

- FSM/control：仲裁、计数器、Mealy/Moore；
- arithmetic/datapath：加法器、乘法器、移位器；
- interconnect：crossbar、router、FIFO；
- memory：cache、CAM；
- architecture：CPU、accelerator。

Non-Agentic 只有 easy/medium；hard 题只放入 Agentic，因为作者认为单轮交互不足以完成复杂任务。

---

## 5. Non-Agentic 与 Agentic 到底差在哪

### 5.1 Non-Agentic：平面 prompt，但仍是多文件输出

典型 v1.1 JSONL：

```json
{
  "id": "cvdp_copilot_lfsr_0001",
  "categories": ["cid003", "easy"],
  "input": {
    "prompt": "LFSR 规格...",
    "context": {"docs/...": "...", "rtl/...": "..."}
  },
  "output": {
    "response": "",
    "context": {"rtl/lfsr_8bit.sv": ""}
  },
  "harness": {"files": {"docker-compose.yml": "...", "src/test_runner.py": "..."}}
}
```

`output.context` 的 key 决定模型应该生成哪些文件。当前 `ModelHelpers` 的策略是：

- 只输出一个文件时，允许 plain text / code block；
- 多个文件时，要求结构化 JSON；
- 根据 cid 注入不同 system guidance；
- 模型响应经 parser 写回 mini repo。

### 5.2 Agentic：修改 repository，以 patch 作为接口

典型 agentic JSONL：

```json
{
  "id": "cvdp_agentic_fixed_arbiter_0001",
  "categories": ["cid003", "easy"],
  "system_message": "可用文件与仿真工具说明",
  "prompt": "按 docs/specification.md 实现 arbiter",
  "context": {
    "docs/specification.md": "...",
    "rtl/fixed_priority_arbiter.sv": ""
  },
  "patch": {
    "rtl/fixed_priority_arbiter.sv": "unified diff"
  },
  "harness": {...}
}
```

agent 不是返回一句答案，而是在 Docker workspace 中：

```text
查看 docs / rtl / verif
  -> 创建或修改文件
  -> 运行 iverilog / vvp / yosys / verilator
  -> 根据错误继续修复
  -> runner 比较 before/after
  -> 生成 agent_changes.patch
  -> hidden harness 评分
```

### 5.3 oracle context 的含义

论文版的两种格式都给“完成任务所需的最小相关上下文”，不额外考查从大仓库检索文件的能力。Agentic 的优势主要是多轮工具使用和文件编辑，而不是 repository navigation。

当前 v1.1 又增加 heavy agentic dataset：让 agent 处理更大的 git workspace。这属于新版扩展，不应倒写进原论文方法。

---

## 6. 数据质量控制链

论文流程可归纳为：

```text
35 名工程师写 1,313 题
  -> 专家检查准确性 / 类别 / 范围
  -> reference solution 跑 hidden harness
  -> 不完整 context 必须失败
  -> LLM 检查缺上下文、类别错误、歧义、一致性
  -> 质量过滤
  -> 保留 783 题
```

论文也承认 benchmark 不可能绝对无 bug，后续会版本化更新。当前 README 进一步说明：

- 初始公开版因 harness/许可问题省略 20 个 datapoint；
- 为降低污染，没有公开完整数据的 `output` / `patch` reference solution；
- 本地 `example_dataset/*_with_solutions.jsonl` 只为验证工具链，不能替代完整数据集。

所以如果要下载完整数据，应从本文顶部 Hugging Face 地址获取，并保留文件版本与 revision；不要把 example 的 6 条样例误写成 783 题已在本地。

---

## 7. 从 JSONL 到评分的真实代码流程

### 7.1 总入口

```bash
python run_benchmark.py -f <dataset.jsonl> [模式参数]
```

`detect_dataset_format(...)` 通过第一条 ID 的第二段判断：

```text
cvdp_copilot_* -> Non-Agentic / CopilotWrapper
cvdp_agentic_* -> AgenticWrapper
```

`--force-agentic` / `--force-copilot` 可把同一数据转成另一工作流，但转换实验应与原生格式结果分开报告。

### 7.2 Non-Agentic 调用链

```text
run_benchmark.py
  -> CopilotBenchmark
  -> DatasetProcessor.process_json
  -> model factory 创建 API / custom / local model
  -> all_prepare
       -> create system prompt
       -> 调模型
       -> parse response
       -> 把生成内容写进 mini repo
  -> all_run
       -> Docker Compose 启动 harness
       -> 收集每个 pytest/cocotb test 的 return code 和 log
  -> Report.format_report
  -> raw_result.json / report.json / report.txt
```

### 7.3 Agentic 调用链

```text
AgenticProcessor.process_json
  -> 建 mini repository 与 hidden harness
  -> 建 docker-compose-agent.yml
  -> agent_run / th_agent
       -> mount 允许的 workspace roots
       -> 监控基础设施文件是否被修改
       -> 记录 return code / timeout / log
       -> 生成统一 agent_changes.patch
  -> 将 patch 应用到待评测 repo
  -> 独立 harness Docker 评分
  -> 报告 agent status / contract violations / ignored changes
```

### 7.4 golden self-check

不带 `--llm` 时，runner 可应用 with-solutions 数据中的 golden `output/patch`。官方 sanity 约束是：

```text
golden patch     -> 100% problems pass
--no-patch (-d)  -> 0% problems pass
```

这比只检查 golden 能通过更严格：如果空实现也能通过，说明 harness 没有区分力。

---

## 8. EDA 与评分工具链

### 8.1 开源 code-generation harness

当前 v1.1 `docker/Dockerfile.sim` 固定/声明：

| 工具 | 版本/作用 |
|---|---|
| Cocotb | 2.0.1，Python 驱动 RTL 验证 |
| pytest | 8.3.2，组织测试和返回码 |
| Icarus Verilog | v13_0，仿真 |
| Yosys | 0.40，综合与 QoR/结构检查 |
| Verilator | 5.038，lint/仿真 |

每个 datapoint 自带 harness 描述，runner 把 `__OSS_SIM_IMAGE__` 等模板变量替换为 `.env` 中配置的镜像。

### 8.2 商业验证子集

论文说明 cid12–14 的部分 testbench/assertion 题需要 Cadence Xcelium；当前代码又通过 harness 中是否出现 `__VERIF_EDA_IMAGE__` 做更全面判断，因此不能只按 category 判断。

商业题需要：

- 自建含 Xcelium 的 verification image；
- license network；
- `VERIF_EDA_IMAGE` 配置；
- 与开源子集分开汇报。

把商业子集因 license 失败记成“模型失败”是不正确的。

### 8.3 Comprehension scoring

| 类别 | 论文方法 | 当前代码 |
|---|---|---|
| cid06 / cid08 | BLEU，与 reference 片段匹配 | 默认 score-based，保留 0–1 连续分数 |
| cid09 / cid10 | GPT o4-mini subjective judge | `SubjectiveScoreModel`，比较原问题、reference 和回答 |
| code generation | hidden executable harness | 所有 sub-tests 都通过才算 problem passed |

LLM judge 结果不能理解成形式正确性；它是一个依赖 judge model、prompt 和 API 版本的主观技术回答分数。

---

## 9. 论文实验设置与主结果

论文评估：

- Claude 3.7 Sonnet（有/无 Extended Thinking）；
- Claude 3.5 Haiku；
- GPT-4.1、o1、o4-mini；
- Llama 3.1 405B / 70B；
- 每题 `n=5`；
- 报告 expected `pass@1`，因此本质是五次样本的平均单次通过概率；
- Llama 设置 `T=0.2, top-p=0.7`，其他 API 模型使用端点默认采样参数。

### 9.1 Non-Agentic code generation

![CVDP 论文 Table 2：Non-Agentic 代码生成结果](./figures/paper-table2-nonagentic-results.png)

| 模型 | Overall | cid03 spec→RTL | cid13 checker | cid16 debug |
|---|---:|---:|---:|---:|
| Claude 3.7 Sonnet | 33.56% | 48% | 6% | 53% |
| Claude 3.7 Sonnet Thinking | 33.04% | 44% | 7% | 51% |
| GPT-4.1 | 28.91% | 44% | 10% | 45% |
| GPT o4-mini | 28.74% | 47% | 11% | 43% |
| Llama 3.1 405B | 22.79% | 31% | 5% | 32% |

最强总体不超过 34%。更关键的是 cid13 testbench checker 只有 3%–11%，远低于 spec→RTL 或 debug。

### 9.2 Agentic 题强制转成单轮模型评测

论文当时没有可直接使用的通用开源硬件 agent，所以将 Agentic datapoint 转成 Non-Agentic 格式给模型做单轮回答。这个结果衡量的是 **agentic-origin tasks under single-turn models**，不是 Docker agent 的真实多轮成绩。

![CVDP 论文 Tables 3–4：Agentic-origin 生成题与 comprehension 结果](./figures/paper-table3-table4-agentic-comprehension.png)

| 模型 | Agentic-origin Overall | cid05 module reuse | cid13 checker | cid16 debug |
|---|---:|---:|---:|---:|
| Claude 3.7 Sonnet | 29% | 24% | 0% | 53% |
| Claude 3.7 Thinking | 29% | 24% | 1% | 56% |
| GPT-4.1 | 21% | 21% | 13% | 45% |
| Llama 3.1 405B | 21% | 25% | 6% | 45% |

Claude 在普通 RTL 生成上领先，但 module reuse 没有显著优势，说明“写一个模块”和“理解/复用多个既有模块”是不同能力。

### 9.3 comprehension

论文 Table 4 中 Claude 3.7 Thinking 平均 71%，但 GPT-4.1/o1/o4-mini 在 correspondence 类别 cid06/08 很低，而在 QA cid09/10 高达约 82%–89%。论文认为 QA 太像成熟 chatbot 场景，挑战可能不足；未来更值得做从 RTL 生成规格等任务。

以上数字均为论文报告，不是本地实测。

---

## 10. 为什么 verification 比 RTL generation 更难

论文观察 testbench stimulus、checker、assertion 的失败类型更多：

- missing timescale；
- syntax errors / unmatched blocks；
- truncated implementation；
- multiple drivers；
- flawed synchronization；
- incorrect checker；
- misplaced SVA / timing semantics；
- insufficient coverage。

原因不只是 SystemVerilog 语法：

1. testbench 更偏 procedural/imperative；
2. checker 必须理解 DUT 的跨周期正确行为；
3. stimulus 要覆盖边界与状态空间，而不是只产生合法波形；
4. assertion 涉及 clocking、sampling、implication 和 reset disable；
5. 输出“能编译”仍可能 verification intent 不完整。

---

## 11. 失败聚类方法

![CVDP 论文 Algorithm 1 与 Figure 2：失败反思、向量化和聚类](./figures/paper-algorithm1-figure2-failure-analysis.png)

论文的 failure analysis 不是简单人工数错误字符串，而是：

```text
每个 failed datapoint
  -> o1 反思失败原因
  -> SentenceTransformer embedding
  -> k=2..11 做 K-means
  -> 用 silhouette score 选最佳 k
  -> o1 对每个 cluster 总结失败实体
  -> category-level failure taxonomy
```

这里有两层模型依赖：失败原因由 o1 生成，cluster label 也由 o1 解释。所以聚类结果适合做定性趋势，不是完全独立于 LLM judge 的客观 ground truth。

![CVDP 论文 Table 5 与 Figure 3：类别失败簇及过滤前后变化](./figures/paper-table5-figure3-failure-clusters.png)

质量过滤后 cid13 的失败 cluster 数减少，Claude 3.7 由 6 个降为 2 个，作者据此认为题面歧义与一致性得到改善。不过失败簇减少也可能同时来自样本数/分布变化，不能单独当作质量的充分证明。

---

## 12. 本地代码与数据实测

### 12.1 本地实际拥有的内容

| 内容 | 状态 |
|---|---|
| 16 页论文 PDF | 已归档 |
| benchmark Python 框架 | 已 clone，commit 已记录 |
| v1.1.0 example datasets | 6 类 × with/without solution，共 10 个 JSONL 文件，每个 1 条 |
| 完整 783 题 | 本地未发现；需从 Hugging Face 下载 |
| open-source Docker image | Dockerfile 在，本地 daemon 无访问权限，未构建 |
| commercial EDA image/license | 未提供 |

### 12.2 local prompt export：通过

结构化记录：[runs/local_export_20260802/record.json](./runs/local_export_20260802/record.json)。

对无商业依赖的 Non-Agentic LFSR 样例运行：

```bash
python run_benchmark.py \
  -f example_dataset/cvdp_v1.1.0_example_nonagentic_code_generation_no_commercial.jsonl \
  --llm --model local_export \
  --prompts-responses-file runs/local_export_20260802/prompts.jsonl \
  --prefix runs/local_export_20260802/work
```

输出：

```text
id: cvdp_copilot_lfsr_0001
rows: 1
bytes: 10,375
fields: id, prompt, system, user
sha256: 32f8b14454bcf0917f64fafd73b3cbbf1246426432946c2b78cfbbab948a42a4
```

实际 prompt 由三部分构成：

1. 通用 `rtl/verif/docs` 文件结构说明；
2. cid003 的 “Specification to RTL Translation” guidance；
3. 4,452 字符 LFSR 用户规格，并要求 plain text 写入 `rtl/lfsr_8bit.sv`。

这证明 `JSONL -> category guidance -> system/user prompt -> local inference export` 链已跑通。

### 12.3 没有跑通/没有尝试伪装成跑通的部分

- 没有调用任何模型；
- 没有生成 LFSR candidate RTL；
- 没有运行 Cocotb/Icarus hidden harness；
- 没有运行 agent Docker；
- 没有下载完整 783 题；
- 没有复现论文 Tables 2–5。

当前证据等级是 **C：代码与样例审计 + prompt 构造冒烟通过**。

---

## 13. 代码审计发现的实现边界

### 13.1 export 模式仍初始化 Docker network

`local_export` 的 model 明确 `requires_evaluation=False`，最终也会跳过 harness；但程序前置流程仍尝试创建 Docker network。本地因 daemon 无权限出现错误，prompt 仍成功导出。

更合理的实现是检测 export mode 后直接跳过：

```text
commercial EDA validation
Docker network creation
harness repository creation
subjective scorer initialization
```

### 13.2 subjective scoring 被无条件打开

`benchmark_main()` 当前代码写：

```python
use_sbj_scoring = True
```

所以即使 cid003 code-generation prompt export，也会尝试创建 `sbj_score` API model；本地无 API key 报错，但不影响导出。正式离线运行应只对 cid09/10 或显式启用时初始化 judge。

### 13.3 pass@k 说明与公式有概念混用

当前 `run_reporter.py` 对一题在 `n` 次样本中通过 `c` 次时使用：

\[
1-(1-c/n)^k
\]

它是按经验通过率、带放回抽取 k 次的成功概率，不是 HumanEval 常用的无放回 unbiased estimator：

\[
1-\frac{\binom{n-c}{k}}{\binom{n}{k}}
\]

同时部分帮助文字又把 k 描述为“至少 k 个样本通过”的 threshold，两者不是同一统计量。论文只报告 `pass@1, n=5`，此时两种公式都退化为 `c/n`，所以不影响论文主表；做 pass@5 等新版实验时必须先固定定义。

### 13.4 score-based 类别不能与二元 pass 直接相加

cid06/08/09/10 当前可把 BLEU/LLM 分数作为 fractional passed problem。总报表混合时应分别报告：

- executable code pass rate；
- correspondence similarity score；
- subjective QA score。

把三者平均成一个“总体准确率”会掩盖任务定义差异。

### 13.5 agent 能看到什么必须记录

`--force-agentic-include-golden` 与 `--force-agentic-include-harness` 会主动把 reference patch 或 harness 暴露给 agent，只适合开发/调试，不适合作为正式盲测结果。正式结果至少要记录：

```text
force mode
golden visibility
harness visibility
workspace roots
network mode
EDA tools
timeout / retry / disk limit
agent image digest
```

---

## 14. 推荐复现路线

### 阶段 1：补齐完整公开数据

从 Hugging Face 下载并归档：

- non-agentic code generation no-commercial；
- non-agentic code comprehension；
- agentic code generation no-commercial；
- 如有授权，再单列 commercial 与 heavy-agentic。

记录 dataset version、revision、每个 JSONL 的行数与 SHA256；确认公开文件是否含 reference solutions。

### 阶段 2：golden harness 自检

1. 构建 `nvidia/cvdp-sim:v1.0.0`；
2. 先跑 example `*_with_solutions`；
3. golden 必须 100%，`-d` no-patch 必须 0%；
4. 再抽完整数据的 10–20 题检查；
5. 把 infra failure 与 candidate failure 分开。

### 阶段 3：本地模型闭环

1. 对 no-commercial non-agentic 数据 `local_export`；
2. 固定本地模型 checkpoint、量化、模板、temperature、seed；
3. 生成与 ID 对齐的 `responses.jsonl`；
4. `local_import` 执行同一 hidden harness；
5. 至少 5 samples，保存原始 completion；
6. 报告 cid02/03/04/07/12/13/14/16 分项结果。

### 阶段 4：Agent

1. build agent image；
2. 禁止 golden/harness 暴露；
3. 先单题 fixed arbiter；
4. 验证 patch 生成、timeout、基础设施防篡改；
5. 再跑 module reuse、checker、assertion；
6. 同时报告 pass rate、平均工具调用、时间、token/成本和 agent status。

### 阶段 5：商业子集

只有具备 Xcelium image 和 license network 时运行，并与开源子集单独成表。无法运行时标为 infrastructure blocked，不记模型 0 分。

---

## 15. 组会分享建议

### 一句话定位

> CVDP 把 Verilog LLM benchmark 从单一的 spec-to-RTL 扩展成 13 类设计/验证任务，并首次把 Docker 化工具使用 agent 作为一等评测对象；结果显示真正困难的不是写普通 RTL，而是 checker、assertion、module reuse 和验证闭环。

### 推荐讲图顺序

1. Table 1：13 类任务、617/166 两种交互；
2. Figure 1：同一 JSONL 如何分到 model 或 agent，再进 hidden harness；
3. Table 2：最强 overall 约 34%，cid13 极低；
4. Table 3：Agentic-origin 题即使平面化仍更难；
5. Algorithm 1 / Figures 2–3：失败类型不仅是 syntax，而是 coverage、sync、SVA semantics；
6. 本地 `local_export`：展示完整 prompt 是怎样从数据与 category guidance 合成的。

### 与 GenBen / RealBench 的关系

| Benchmark | 核心问题 | 强项 | 主要边界 |
|---|---|---|---|
| GenBen | 模型是否具备跨层硬件知识、生成、调试与 QoR | 多模态、扰动、PPA | 路径/数据完整度与 PPA 环境 |
| RealBench | 模型能否实现真实层级 IP | 长规格、100% line coverage、formal | JasperGold 商业依赖 |
| CVDP | 模型/agent 能否覆盖多种设计与验证子任务 | 13 类、Docker agent、hidden harness | 完整数据需另下，部分商业工具，LLM judge |

它们不是互相替代：RealBench 深挖真实 IP 层级，CVDP 横向覆盖任务类型，GenBen横跨知识到实现 QoR。

---

## 16. 最终判断

| 维度 | 结论 |
|---|---|
| 分享价值 | 很高：验证任务与 agent 视角能补足普通 RTL 生成论文 |
| 论文严谨性 | 高：人类工程师出题、reference/harness sanity、分类别失败分析 |
| 代码成熟度 | 高但复杂：覆盖模型、agent、转换、报告、商业/开源 EDA |
| 本地数据完整度 | 低到中：只有 examples，完整 783 题待从 HF 下载 |
| 本地已跑 | 一个 cid003 no-commercial 样例的 local prompt export |
| 本地未跑 | 模型、Docker harness、agent、全量数据、论文结果 |
| 当前证据等级 | C |
| 后续优先级 | 很高，适合和 RealBench 组成“下一代 benchmark”专题 |

CVDP 最重要的启示是：**硬件大模型不能只按“生成的 RTL 能不能过几个 testbench”排名；验证代码生成、模块复用、工具使用和失败恢复本身就是必须独立测量的能力。**

## P7 组件一句话总结

| 组件 | 一句话角色 |
|---|---|
| run_benchmark.py | 总入口，根据 ID 前缀选择 Non-Agentic 或 Agentic 评测流程。 |
| CopilotBenchmark / AgenticProcessor | 分别处理平面 prompt 与 Docker 仓库式 agent 任务。 |
| DatasetProcessor | 解析 JSONL，合成 system/user prompt 并写回 mini repo。 |
| docker/Dockerfile.sim | 开源仿真 harness 环境，固定 Cocotb/Icarus/Yosys/Verilator 版本。 |
| run_reporter.py | 计算 pass@k 并格式化 report.json / report.txt。 |
| SubjectiveScoreModel | 对 cid09/10 comprehension 做 LLM judge 评分。 |
| local_export / local_import | 本地模型 prompt 导出与结果回灌执行的解耦接口。 |

## 讨论问题

1. CVDP 的 Non-Agentic 与 Agentic 任务在 hidden harness 和 reference 暴露策略上有何本质区别，如何防止把 agent 能看到 harness 的调试结果误报为正式成绩？
2. 论文发现 verification 类任务（checker、assertion）通过率远低于 RTL 生成，你认为当前 LLM 在时序语义、跨周期行为和 coverage 理解上的核心短板是什么？
3. CVDP 同时混用了 executable harness、BLEU 和 LLM subjective judge 三种评分，设计一个“总体 leaderboard”时应该如何避免不同量纲掩盖任务差异？
