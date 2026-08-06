# VGen / VeriGen：论文、训练数据、模型、评价代码与复现证据详解

> 当前目录论文：**Benchmarking Large Language Models for Automated Verilog RTL Code Generation**  
> arXiv：`2212.11140` v1，2022-12-13；后发表于 DATE 2023  
> 本地论文：[2212.11140_VeriGen.pdf](./2212.11140_VeriGen.pdf)  
> 官方代码：<https://github.com/shailja-thakur/VGen>  
> 本地代码：commit `81710f872caf5c52440a455718d2c555c2d02d10`，2024-10-17  
> 静态审计：[runs/static_audit_20260802.json](./runs/static_audit_20260802.json)  
> 扩展稿独立详解：[VeriGen扩展论文_2308.00708_论文与代码复现详解.md](./VeriGen扩展论文_2308.00708_论文与代码复现详解.md)  
> 核验日期：2026-08-03

---

```text
┌─────────────────────────────────────────────────────────────────┐
│ P1 任务定义                                                        │
├─────────────────────────────────────────────────────────────────┤
│ Input      │ Verilog 问题描述（L/M/H 三档详细度）+ 模块头 + 端口声明    │
├─────────────────────────────────────────────────────────────────┤
│ Output     │ 自回归补全生成的完整 Verilog module，能通过 Icarus 编译与   │
│            │ testbench 功能验证                                             │
├─────────────────────────────────────────────────────────────────┤
│ Supervision│ Icarus 编译 stderr/return code + testbench 输出 "all tests passed"│
├─────────────────────────────────────────────────────────────────┤
│ Why-hard   │ 预训练通用模型几乎不会写可编译 Verilog；需要专用语料微调，并在   │
│            │ 温度、样本数、模型大小和 prompt 详细度之间做昂贵搜索           │
└─────────────────────────────────────────────────────────────────┘
```

## 0. 先纠正论文身份

当前文件名叫 `2212.11140_VeriGen.pdf`，目录与后续文献也常把这条工作线简称 VGen/VeriGen；但该 PDF 的真实标题是：

> **Benchmarking Large Language Models for Automated Verilog RTL Code Generation**

它不是后来标题为 **VeriGen: A Large Language Model for Verilog Code Generation** 的 arXiv `2308.00708`。

两篇高度相关，但不应只因模型/仓库名字相近就当成同一个 PDF。后者的正确地址是：

- 摘要页：<https://arxiv.org/abs/2308.00708>
- PDF：<https://arxiv.org/pdf/2308.00708>

`2308.00708v1.pdf` 现已归档，并已建立[扩展论文独立详解](./VeriGen扩展论文_2308.00708_论文与代码复现详解.md)。本篇继续只解读 `2212.11140` DATE 前版；扩展稿新增的 GPT-3.5/GPT-4/PaLM2、HDLBits Set II、教材消融、推理时间和失败案例不混入本篇结果表。

---

## 1. 一页结论

这篇论文是 Verilog LLM 研究的早期系统 baseline，核心不是 Agent，而是把四件事第一次较完整地放到一起：

1. 从 GitHub 与 Verilog 教材构造专用训练语料；
2. 微调 355M–16B 的五种预训练模型；
3. 建立 17 题、三种难度、三种 prompt 详细度的评测集；
4. 用 Icarus Verilog 区分“能编译”和“通过功能 testbench”。

论文主结果：

| 口径 | 论文报告 |
|---|---:|
| 预训练模型整体功能正确 | 1.09% |
| 微调模型整体功能正确 | 27.0% |
| CodeGen-16B-FT 功能正确 | 41.9% |
| code-davinci-002 功能正确 | 35.4% |
| CodeGen-16B-FT 相对后者 | +6.5 个百分点 |
| best-scenario 预训练编译率 | 11.9% |
| best-scenario 微调编译率 | 64.6% |
| GitHub+教材相对只用 GitHub | +1.4 个百分点 |

当前仓库不是端到端论文 artifact：

- 有 17 题、51 个 prompt、17 个 testbench、17 个逻辑 reference；
- 有两个推理 notebook，且提交文件内嵌了一次 6B half-adder 历史输出；
- 有 BigQuery/PDF 抽取代码；
- 有 `evaluation_scripts.zip`；
- 没有完整 300/400 MB corpus；
- 没有本仓库内训练脚本；
- 没有模型权重文件；
- 没有论文 raw completions 或 Table III/IV result CSV。

代码审计还发现当前 evaluator 不能直接重算论文：同一题的 L/M/H 三个 prompt 共用同一输出目录，首个创建后后两个被跳过；`get_results.py` 最终只汇总 `advanced5`；`run_eval.sh` 使用 n=1/10/20 而论文是 1/10/25。

本次没有重新加载 11GB 级模型或运行推理。综合等级：**R1**。

---

## 2. 论文身份与证据

作者为 Shailja Thakur、Baleegh Ahmad、Zhenxing Fan、Hammond Pearce、Benjamin Tan、Ramesh Karri、Brendan Dolan-Gavitt 和 Siddharth Garg。

本地 PDF：

| 字段 | 值 |
|---|---|
| 文件 | `2212.11140_VeriGen.pdf` |
| 页数 | 7 |
| SHA-256 | `b99d4af117a1d5b5995c05d23d62e7d9fb1d1022ceffd03990ae5a3683f491e9` |
| arXiv 版本 | v1，2022-12-13 |

仓库为 Apache License 2.0，但许可证文件名是英式拼写 `LICENCE`；README 尾部链接写成 `LICENSE`，在大小写敏感文件系统上该链接会断。

---

## 3. 论文全流程

![VGen 训练—生成—testbench 评价总览](./fig/system_overview.png)

> 图 1：仓库 `fig/system_overview.png`，对应论文 Figure 1 的系统概览。左侧从 GitHub/教材构造 Verilog corpus 并微调预训练模型；下方 prompt 驱动生成 code completions；右侧 testbench 把生成物分成 accepted/rejected。

用更严格的工程流程表示：

```text
GitHub .v + 教材 PDF
        │
        ├─ 过滤、去重、分窗
        ▼
Verilog training corpus
        │
        ▼
预训练 LLM fine-tuning
        │
        ▼
Verilog-specialized model
        │
17 tasks × L/M/H prompts × temperature × n
        │
        ▼
candidate completions
        ├─ Icarus compile → syntax/compile rate
        └─ vvp + testbench → functional rate
```

论文没有使用 compiler/testbench 反向传播。训练仍是 next-token cross-entropy；工具只用于训练后的评价。

---

## 4. 模型本质：decoder-only code completion

以 CodeGen 为例：

```text
Verilog prefix / comments / module header
  → tokenizer
  → decoder-only causal Transformer
  → next-token distribution
  → autoregressive completion
```

它不是 chat agent，也没有：

- 独立功能正确分类头；
- testbench feedback loop；
- AST/VCD 调试器；
- PPA reward；
- 多 Agent 分工；
- formal verification。

因此输入格式更接近：

```verilog
// This is a half adder...
module half_adder(...);
```

而不是现代 instruction/chat 模型的多轮对话。

---

## 5. 训练语料一：GitHub corpus

### 5.1 来源

论文使用 Google BigQuery 的 GitHub snapshot，当时覆盖超过 280 万 repositories。

查询目标是 Verilog 相关仓库和 `.v` 文件。

### 5.2 过滤

论文说明：

1. 搜索 `.v` 与 Verilog 关键词；
2. 保留至少含一对 `module`/`endmodule` 的文件；
3. 用 MinHash 与 Jaccard similarity 去重/近重复；
4. 丢弃字符数 ≥20K 的大文件。

最后得到约：

```text
50K Verilog files
300 MB
```

### 5.3 当前 BigQuery notebook 实际代码

`verilog-fetch-big-query.ipynb` 中核心 SQL 查询：

```sql
FROM bigquery-public-data.github_repos.files AS f
JOIN bigquery-public-data.github_repos.contents AS c
ON f.id = c.id
WHERE NOT c.binary
  AND f.path LIKE '%.v'
  AND c.content LIKE '%endmodule%'
```

notebook 还探索 StackOverflow Verilog 内容和 GitHub language statistics。

但当前仓库没有：

- 论文最终 SQL snapshot；
- 50K 文件清单；
- MinHash/Jaccard 完整实现；
- 每条源文件 commit/hash；
- 过滤前后统计表；
- 300 MB 语料本体。

所以 notebook 能证明数据获取思路，不足以重建论文精确 corpus。

---

## 6. 训练语料二：70 本教材

论文从在线 e-library 下载 70 本 Verilog 教材 PDF，做 OCR/文本抽取和清洗。

流程：

```text
PDF
  → PyMuPDF/OCR 提取
  → 删除 index/preface/acknowledgment 等无关文本
  → 正则检查 Verilog 高层语法
  → overlapping sliding windows
  → 训练样本
```

与 GitHub 合并后总语料约：

```text
400 MB
```

### 6.1 当前 `pdf_extractor.py`

代码使用旧 `PyPDF2.PdfFileReader`、`extractText`、NLTK、textract。

存在的代码边界：

- `getPages` 在 fallback 中引用未作为参数传入的 `filename`；
- `preprocess(..., toLower=False)` 无论参数如何都转小写；
- `spellCheck=True` 使用未导入的 `Speller`；
- `clean_text` 计算了多个中间变量，但最终 `keywords` 条件 `word in punctuations and word in w_num` 把字符串当容器，语义可疑；
- 当前依赖版本未锁定。

### 6.2 当前 `pdf_extraction_instance.py`

该文件更像未封装的 notebook 片段：

- 使用 `fitz`、`re`、`pd`，但文件自己只 import `glob`；
- `files={}` 为空，直接运行不会处理教材；
- 页码范围需要外部填充；
- 用相邻页一半文本构造重叠窗口；
- 末尾直接创建 DataFrame。

它展示了滑窗思路，不是可独立复跑的 70 本教材生产脚本。

### 6.3 法律与可追溯性

论文没有提供 70 本教材清单和授权状态，也没有按 GitHub 文件保留 license/provenance manifest。

2026 年重新构建这类 corpus 必须补：

- repository/license/commit；
- 教材版权与可用范围；
- source URL/hash；
- 去重簇；
- train/test contamination；
- 删除请求与再发布政策。

---

## 7. 五个微调模型与一个商业基线

### 7.1 论文模型

| 模型 | 参数 | 层 | heads | head/embed 维 | context | 预训练数据 |
|---|---:|---:|---:|---:|---:|---|
| MegatronLM | 355M | 24 | 16 | 64 | 1024 | NL |
| J1-Large | 7B | 32 | 32 | 128 | 4096 | NL |
| CodeGen | 2B | 32 | 32 | 80 | 2048 | NL + code |
| CodeGen | 6B | 33 | 16 | 256 | 2048 | NL + code |
| CodeGen | 16B | 34 | 24 | 256 | 2048 | NL + code |
| code-davinci-002 | 未公开 | N/A | N/A | N/A | 8000 | NL + code |

论文微调前五个；code-davinci-002 是商业 baseline，不是作者微调模型。

### 7.2 为什么参数量影响结果

更大模型通常拥有：

- 更强代码先验；
- 更长/更稳的依赖建模；
- 更好的 syntax pattern 记忆；
- 更多 capacity 吸收 Verilog corpus。

但 16B 的优势不能只归因参数量，因为基座训练数据、tokenizer、模型架构和训练系统也不同。

---

## 8. 训练设置

### 8.1 CodeGen

论文对 CodeGen 2B/6B/16B 各微调 1 epoch。

按规模分别使用：

| 模型 | 硬件 | 时间 |
|---|---|---:|
| CodeGen-2B | 2×RTX8000 | 2 天 |
| CodeGen-6B | 4×RTX8000 | 4 天 |
| CodeGen-16B | 3×A100 | 6 天 |

16B 仅 FP16 参数约 30 GB，连同 optimizer states 和 activations，论文估约需 250 GB 聚合 GPU memory。

训练基于 DeepSpeed，用 model/data parallel 和 optimizer sharding。

### 8.2 MegatronLM

```text
9 epochs
1 × RTX8000
15 hours
default configuration
```

### 8.3 J1-Large

通过商业 AI21 Studio 微调，完整训练基础设施并不开放。

### 8.4 超参数复现边界

论文写 CodeGen 使用默认 training hyperparameters，但“默认”会随代码版本变化。严格复现需要：

- 训练仓库 commit；
- DeepSpeed config；
- optimizer/lr/scheduler；
- global batch；
- sequence packing；
- precision；
- seed；
- data order；
- checkpoint revision。

当前 VGen 仓库只把训练详情链接到另一个 `CodeGen-Fine-Tuning` 仓库，本目录没有训练脚本。

---

## 9. 17 道评测题

当前仓库按论文结构保留：

### Basic：4

```text
1. simple wire
2. 2-input AND gate
3. 3-bit priority encoder
4. 2-to-1 mux
```

### Intermediate：8

```text
5. half adder
6. counter 1 to 12
7. 5-bit LFSR
8. simple 2-state Moore FSM
9. shift-left rotate
10. RAM
11. permutation
12. truth table
```

### Advanced：5

```text
13. signed addition with overflow
14. counter with pause
15. FSM recognizing 101
16. 64-bit arithmetic shifter
17. ABRO FSM
```

覆盖组合、时序、FSM、RAM、算术、移位和置换。

题目来自课堂练习经验与 HDLBits 灵感，不是从训练 GitHub corpus 中随机 holdout 得到。

---

## 10. 三种 prompt 详细度

每题有 L/M/H 三份 prompt。

### 10.1 L：Low detail

- 功能概述 comment；
- module header；
- 端口声明；
- 部分内部信号；
- 少量或没有实现提示。

### 10.2 M：Medium detail

在 L 上加入与信号名对应的功能 comments。

### 10.3 H：High detail

进一步加入近似 pseudo-code 的细节，例如状态转移、条件与输出关系。

这三档研究的问题是：模型是在做高层设计，还是把详细伪代码翻译成 Verilog。

### 10.4 当前资产数量

```text
17 task directories
51 prompt*.v = 17 × 3
17 testbench files
16 answer_*.v + advanced3/advfsm.v = 17 logical references
```

---

## 11. 当前 prompt 的关键异常

### 11.1 Advanced3 的 L/M 完全相同

`advanced3/prompt1_advfsm.v` 与 `prompt2_advfsm.v` 字节完全一致。

所以当前 artifact 中这题没有真正不同的 Low/Medium 输入。

### 11.2 Advanced3 的 H 泄漏完整答案

`advanced3/prompt3_advfsm.v` 在规格 comments 后包含：

- 完整 `assign z`；
- 状态寄存器 always block；
- next-state case；
- `endmodule`。

它已经是一个完整可执行 solution，不再是 completion prompt。

当前 51 个 prompt 中，只有这一份含 `endmodule`。

若按当前 evaluator 把它交给模型，评测会发生严重答案泄漏。

### 11.3 与论文 Figure 5 不同

论文展示 Problem 15 的 H prompt 到状态转移 comments 为止，没有把完整实现当 prompt。

当前 evaluation set 是 2023 年才加入/更新，而论文 PDF 是 2022 年。不能假设当前文件 byte-identical 于论文输入。

---

## 12. 采样协议

论文 sweep：

| 参数 | 值 |
|---|---|
| temperature | 0.1、0.3、0.5、0.7、1.0 |
| completions/prompt `n` | 1、10、25 |
| max tokens | 300 |
| J1 max tokens | 256 |
| top-p | 1.0 |

如果每个模型完整跑全部组合，除 J1 外理论生成量：

```text
17 tasks × 3 prompts × 5 temperatures × (1+10+25)
= 9,180 completions per model
```

J1 不支持 n=25，所以对应量更少。

Table III/IV 只展示 `n=10`，并对每个 model/scenario 选择表现最好的 temperature。

这意味着结果是调参后的 best-of-temperature，不是统一固定温度。

---

## 13. 编译与功能评价

### 13.1 编译

论文使用 Icarus Verilog v11.0。

它检查：

- 词法/语法；
- module/interface；
- elaboration；
- 一部分不合法结构。

“compile”不等于综合，也不保证功能。

### 13.2 功能

每题有手写 testbench。

论文说明：

- Basic 和部分 Intermediate 接近 exhaustive；
- 复杂任务只类似 unit tests；
- RAM 若穷举代价过高；
- reset synchronous/asynchronous 等规格可能模糊；
- testbench 不检查未被 prompt 明确规定的全部 corner cases。

### 13.3 accepted/rejected

论文整体图把 completions 分成 accepted/rejected，但应继续细分：

```text
parse/compile fail
compile pass but test fail
compile pass and test pass
timeout/tool error
```

当前脚本没有完整保存这些结构化状态。

---

## 14. 论文的“Pass@(scenario*n)”不是常见 pass@k

论文把一个 scenario 定义为：

```text
difficulty × prompt detail
```

然后将该 scenario 下所有问题的 `n` 个 samples 合起来，报告编译或 testbench 通过的比例。

正文还明确说：

```text
for functional tests, this metric is the fraction of the k code samples that pass
```

所以它更像：

```text
sample-level accuracy = passing completions / all completions
```

而不是 HumanEval 常见的：

```text
pass@k = 每题从 n 个样本中抽 k 个至少一个成功的概率，再对题目平均
```

后续引用论文时应写“论文定义的 Pass@(scenario*n)/completion pass fraction”，避免与 VerilogEval pass@k 混用。

---

## 15. Table III：编译结果

论文在 `n=10` 与 best temperature 下报告：

| 模型 | 类型 | Basic | Intermediate | Advanced |
|---|---|---:|---:|---:|
| MegatronLM-345M | PT | 0.000 | 0.000 | 0.000 |
| MegatronLM-345M | FT | 0.730 | 0.391 | 0.165 |
| CodeGen-2B | PT | 0.080 | 0.065 | 0.176 |
| CodeGen-2B | FT | 0.902 | 0.612 | 0.592 |
| CodeGen-6B | PT | 0.052 | 0.152 | 0.187 |
| CodeGen-6B | FT | 0.987 | 0.689 | 0.599 |
| J1-Large-7B | PT | 0.182 | 0.176 | 0.108 |
| J1-Large-7B | FT | 0.882 | 0.635 | 0.588 |
| CodeGen-16B | PT | 0.132 | 0.203 | 0.240 |
| CodeGen-16B | FT | 0.942 | 0.728 | 0.596 |
| code-davinci-002 | PT | 0.847 | 0.452 | 0.569 |

### 15.1 编译率的结论

- 每个微调模型显著优于自己的 PT 版本；
- CodeGen-6B-FT 的 Basic compile 0.987 高于 16B-FT 的 0.942；
- 16B-FT 的 Intermediate/Advanced compile 略高；
- compile 排名与功能排名不完全相同。

论文 Discussion 的 best-scenario 汇总：

```text
PT compile: 11.9%
FT compile: 64.6%
```

这和摘要里的“25.9% overall”使用了不同聚合语境，引用时应带上统计口径，不把两个数字互换。

---

## 16. Table IV：功能结果

下表完整保留 L/M/H：

| 模型 | 类型 | Basic L/M/H | Intermediate L/M/H | Advanced L/M/H |
|---|---|---|---|---|
| Megatron-355M | PT | 0/0/0 | 0/0/0 | 0/0/0 |
| Megatron-355M | FT | .170/.591/.245 | .043/.018/.025 | 0/0/0 |
| CodeGen-2B | PT | 0/0/0 | 0/0/0 | .016/.020/0 |
| CodeGen-2B | FT | .835/.350/.630 | .130/.092/.163 | .132/.048/.068 |
| CodeGen-6B | PT | 0/0/0 | 0/0/.013 | 0/0/0 |
| CodeGen-6B | FT | 1.000/.500/.760 | .135/.150/.168 | .284/.164/.164 |
| J1-Large-7B | PT | .044/.058/.067 | 0/0/.021 | 0/0/0 |
| J1-Large-7B | FT | .388/.283/.342 | .125/.075/.200 | 0/0/0 |
| CodeGen-16B | PT | 0/.085/.055 | .035/.003/.045 | .012/0/.016 |
| CodeGen-16B | FT | .745/.720/.745 | .213/.270/.255 | .246/.290/.294 |
| code-davinci-002 | PT | .520/.685/.775 | .175/.200/.150 | .156/.184/.344 |

所有数值都是论文报告，不是本地运行。

### 16.1 详细 prompt 不总是单调更好

例如 CodeGen-6B-FT Basic：

```text
L=1.000, M=0.500, H=0.760
```

更详细不保证更高分，因为：

- comment/pseudo-code 可能引导错误结构；
- prompt 变长；
- 模型训练分布更接近某种描述风格；
- 每格选择的最佳 temperature 可能不同；
- testbench 对某些实现细节有隐含偏好。

论文总体说 terse prompt 会减少正确答案，但单个模型/难度格并不严格单调。

---

## 17. 四个研究问题的答案

### RQ1：Base LLM 做得怎样

整体较差，尤其功能正确率只有 1.09%。code-davinci-002 明显强于多数开放 base model。

### RQ2：微调是否有用

有。编译和功能都大幅提升：功能总体 1.09%→27.0%。

### RQ3：更大模型是否更好

总体趋势是 16B/商业大模型更强，但不是每个格子都由最大模型赢。模型架构与预训练代码数据也是混杂因素。

### RQ4：prompt 描述有何影响

难度升高会降低通过率，描述细节能影响生成质量；但 L/M/H 并非对每个模型严格单调。

---

## 18. 最重要的总结果

论文结论：

```text
PT models functional: 1.09%
FT models functional: 27.0%
```

最佳模型：

```text
CodeGen-16B-FT: 41.9%
code-davinci-002: 35.4%
差值: 6.5 个百分点
```

准确说法是：

> 在论文 17 题、三 prompt 档、其定义的 completion-level 统计与 best-temperature 协议下，fine-tuned CodeGen-16B 总体功能通过率比 code-davinci-002 高 6.5 个百分点。

不应缩写成：

> VeriGen 全面超过 Codex。

因为：

- 不同 scenario 中 Codex 仍可能更高；
- 使用 best temperature；
- 题集仅 17 题；
- testbench 不是完整证明；
- 模型/API 版本属于 2022；
- 当前公开 evaluator 不能直接重算。

---

## 19. 温度、样本数和模型大小

### 19.1 Temperature

论文 Figure 6 发现 `t=0.1` 通常最好，温度升高后通过比例显著下降。

RTL benchmark 追求功能精确而不是文本多样性，低温更符合目标。

### 19.2 Completion count

增加候选数提高“至少找到一个正确解”的机会；论文认为 n=10 对各难度是较好折中。

正文对 Pass@(scenario*n) 的描述有些混乱：它同时讨论 sample fraction 与更多 candidates 带来的成功机会。严格复现应同时报告：

- sample-level pass rate；
- task-level pass@1/5/10；
- solved tasks；
- token/compute cost。

### 19.3 Model size

大模型整体更强，尤其在 advanced tasks，但 6B-FT 也在 Basic compile/function 某些格达到最佳。

---

## 20. 失败任务分析

即使 CodeGen-16B-FT 每题生成 540 个 completion：

- Problem 7 LFSR：0 份通过；
- Problem 12 truth table：0 份通过；
- Problem 9 shift/rotate：仅 1 份通过。

论文人工分析：

### LFSR

模型在最高位与 feedback value 的 concatenation 上犯错。

### Shift/rotate

漏掉 shift amount 取值或 bit position 错。

### Truth table

能枚举输入并写 assign，但布尔表达式组合错误。

这说明大量同分布采样不能补救系统性知识缺口。若 540 份都沿同一错误模式，继续增加 n 的收益接近零。

---

## 21. GitHub + 教材消融

CodeGen-16B：

```text
只用 GitHub
vs
GitHub + textbook PDF
```

后者 Pass@(scenario*10) 只高约 1.4 个百分点。

可能原因：

- PDF OCR 噪声；
- 教材新增高质量例子有限；
- GitHub 300 MB 已覆盖大量 syntax；
- 400 MB 中教材占比有限；
- 训练 1 epoch 未充分吸收；
- evaluation 与 GitHub code style 更接近。

不能简单得出“教材无用”；只能说当前抽取与训练配置下边际增益小。

---

## 22. 当前仓库地图

```text
VGen/
├── README.md
├── LICENCE
├── VGen_Demo.ipynb
├── VGen_Demo_notebook.ipynb
├── verilog-fetch-big-query.ipynb
├── pdf_extractor.py
├── pdf_extraction_instance.py
├── evaluation_scripts.zip
├── prompts-and-testbenches/
│   ├── basic1 ... basic4
│   ├── intermediate1 ... intermediate8
│   ├── advanced1 ... advanced5
│   ├── prompts-summary.txt
│   └── prompts-templates.txt
├── fig/system_overview.png
├── 2212.11140_VeriGen.pdf
└── runs/static_audit_20260802.json
```

仓库当前 119 个 tracked files；其中还提交了 19 个 Icarus `vvp` 可执行脚本 artifact。

这些 binary-like `vvp` 文件来自不同路径：有的 shebang 指向 `/usr/bin/vvp`，有的指向作者 macOS Homebrew `/usr/local/Cellar/icarus-verilog/11.0/bin/vvp`。它们是历史编译产物，不是跨平台 source，也不是本机新运行证据。

---

## 23. 两个推理 notebook

### 23.1 `VGen_Demo_notebook.ipynb`

加载：

```text
shailja/fine-tuned-codegen-6B-Verilog
```

提交 notebook 内嵌历史输出显示：

- 下载约 9.98 GB + 1.26 GB 模型分片；
- 输出 attention-mask/pad-token warning；
- 对 `//a half adder module` 生成合理 half-adder；
- 另有逐 token greedy 调试输出。

这证明作者当时 notebook 曾运行并保存结果，但不是 2026 本机重跑，也没有功能 testbench 记录。

### 23.2 `VGen_Demo.ipynb`

内嵌 2022-11-15 Google Colab Tesla T4 15,109 MiB 环境输出，并显示 `Using GPU`；没有提交生成结果。

### 23.3 当前生成参数问题

代码调用：

```python
model.generate(
    input_ids,
    max_length=128,
    temperature=0.5,
    top_p=0.9
)
```

没有显式 `do_sample=True`。在现代 Transformers 默认 greedy 的情况下，temperature/top_p 可能被忽略或触发 warning。

逐 token loop 也总取概率最高 token，是明确 greedy；它没有 max length，只等 `endmodule` 出现，可能无限增长。

### 23.4 `model_name` 没有实际作用

notebook 先赋值 `model_name`，但 `from_pretrained` 使用另一条硬编码字符串。修改变量不会切换模型。

---

## 24. `evaluation_scripts.zip` 调用链

解压后主要脚本：

```text
run_eval.sh
  → run_evaluation.sh
      → remove_all.py
      → gen_examples_all.py
      → evaluate_examples.py
      → get_results.py
      → copy_results.py
      → remove_all.py
```

### 24.1 生成

`gen_examples_all.py`：

- 递归找 `prompt*.v`；
- 连接 OpenAI-compatible fauxpilot endpoint 或 Codex；
- temperature 五档；
- `n` 由 CLI；
- stop 为 `endmodule`/`endmodulemodule`；
- 把 prompt + completion 保存为 `.v`。

### 24.2 评价

`evaluate_examples.py`：

- 找 `examples-*` 目录；
- 用 `iverilog -o example candidate tb`；
- stderr 为空时视为编译成功；
- 执行 `vvp example`；
- stdout 最后 17 个字符严格等于 `all tests passed\n` 时视为功能成功。

### 24.3 汇总

`get_results.py` 读取 `results_compiled.txt` 和 `results_tb_passed.txt`，写 `results.csv`。

这条链的设计意图与论文一致，但当前代码有多项阻断。

---

## 25. 同题三 prompt 的输出目录冲突

输出目录名：

```text
examples-<model>-tmp_<temperature>
```

它位于题目目录下，却不包含：

- prompt filename；
- L/M/H detail level。

每题三份 prompt 按顺序循环：

```python
if not os.path.isdir(examples_dir):
    os.mkdir(examples_dir)
    generate(...)
```

第一份 prompt 创建目录后，同题后两份发现目录已存在，直接跳过。

因此一次 `gen_examples_all.py` 不能生成 L/M/H 三组结果，也无法重算论文对 prompt detail 的消融。

正确目录至少应是：

```text
examples/<task>/<prompt_id>/<model>/<temperature>/<sample_id>.v
```

---

## 26. Completion 自动补 `end` 的风险

`complete_example` 按行统计 substring：

```text
begin count
end count
```

若 begin 更多，就在文件末尾追加若干 `end`，再追加 `endmodule`。

问题：

- `endcase`、`endmodule`、变量/comment 中的 `end` 都可能被计数；
- 单行多个 begin/end 不准确；
- generate block、function/task、case 不同 closing token 不能用 `end` 统一补；
- 修改 candidate 后再评价，结果不再是模型原始 output；
- 自动补出的结构可能碰巧编译，但语义不是模型生成能力。

合理做法是保存 raw output，再把 repair 作为单独后处理指标。

---

## 27. `examples.json` 不是 JSON

代码写：

```text
prompt 原文
+ str(completion)
```

文件名叫 `examples.json`，内容却不是 `json.dump` 的合法 JSON。

后续无法可靠解析：

- model ID；
- usage；
- finish reason；
- sample index；
- prompt hash；
- temperature。

这使 paper run artifact 难以审计。

---

## 28. 编译与功能判定代码问题

### 28.1 Compile 只看 stderr 是否为空

```python
result = subprocess.run(...).stderr.decode()
if len(result) == 0:
    compile success
```

没有看 return code。

后果：

- 成功但有 warning → 被判 compile fail；
- 极端情况下失败但 stderr 重定向/为空 → 可能误判；
- 无法区分 tool missing、timeout、syntax、testbench 错误。

### 28.2 Functional marker 过于脆弱

要求：

```python
result[-17:] == "all tests passed\n"
```

多一个空格、CRLF、工具尾日志都会把正确结果判错。

### 28.3 没有 timeout

编译和仿真都可能无限等待。

### 28.4 固定输出 `example`

所有样本共享当前目录下 `example` executable；没有隔离 build dir，也没有先清理。并行不安全，异常退出可能留下 stale artifact。

---

## 29. 汇总脚本不能汇总全题

`get_results.py` 先定义了一个 15 题列表：

```python
prompts=[...15 tasks...]
```

该列表本来就漏 `intermediate7` 和 `intermediate8`；紧接着又执行：

```python
prompts=["advanced5"]
```

所以最终只汇总 ABRO 一题。

此外：

- 默认假设每个目录已有五温度 results；
- 缺文件会直接异常；
- 没有按 L/M/H 分组；
- 不计算论文 Table III/IV 场景；
- 不选择/记录 best temperature；
- 不产生置信区间。

---

## 30. Shell runner 与论文协议漂移

`run_eval.sh` 循环：

```text
n = 1, 10, 20
```

论文是：

```text
n = 1, 10, 25
```

脚本里的 `MODEL_TYPE=ft` 被传入，但 Python 只解析后打印，实际 endpoint/model 选择不使用 `model_kind`。

`run_evaluation.sh` 还存在：

- 检查 `results` 目录却创建 `evaluation`；
- help 把 `-n` 描述为“person alive”；
- 自动删除 `examples-*`；
- 依赖作者内部主机名 `arrakis.poly.edu`；
- 未锁 Python/OpenAI API 版本。

当前压缩包更像研究脚本快照，不是可移植 reproducibility package。

---

## 31. 论文—代码对应表

| 论文要素 | 当前 artifact | 对应程度 | 结论 |
|---|---|---|---|
| 17 题 | 17 个目录 | 高 | 题目齐 |
| L/M/H prompts | 51 份 prompt | 中 | advanced3 重复/答案泄漏 |
| testbenches | 17 份 | 高 | 当前都有 `all tests passed` 协议 |
| references | 16 `answer_*` + `advfsm.v` | 高 | 命名不统一 |
| GitHub data collection | BigQuery notebook | 低到中 | 最终 corpus/去重链缺失 |
| textbook extraction | 两个 Python 脚本 | 低 | 依赖/变量不完整 |
| 300/400 MB corpus | 无 | 无 | 不能重训 |
| 五模型训练 | 外链仓库 | 低 | 本目录无训练代码/config/log |
| model weights | Hugging Face 远程 | 低到中 | 本仓库不含权重 |
| 6B inference | committed notebook output | 中 | 有历史 half-adder 生成，不是本地重跑 |
| 论文采样矩阵 | zipped generator | 低 | L/M/H 目录冲突，n 漂移 |
| Icarus evaluator | zipped scripts | 中 | 核心链在，但判分脆弱 |
| Table III/IV raw results | 无 | 无 | 不能 artifact 重算 |

---

## 32. 为什么这次不重复跑模型

当前目录没有 `模型推理.md` 或本地 run JSON，但 committed notebook 已保留作者历史 6B half-adder 输出。

重新运行的障碍/边界：

- 6B FP32 分片历史下载约 11.24 GB；
- 当前机器无可用 GPU；
- 论文最佳是 16B-FT，不是 demo 6B；
- 完整评价至少数千 completions；
- evaluator 需先修复；
- Hugging Face revision 与 2022 可能已变化；
- 单个 half-adder 新输出无法验证论文 Table IV。

因此本次没有把“再生成一个简单 half-adder”当成有价值复现。已有 notebook 输出已作为**作者提交 artifact**记录，不能写成本机 2026 推理。

---

## 33. 当前能证明与不能证明

### 已能证明

- 论文的训练 corpus、五模型微调、17 题与评价协议；
- 当前 repo 有 17×3 prompts 和 17 testbench；
- 6B demo notebook 曾保存 half-adder output；
- BigQuery/PDF 数据入口存在；
- evaluator 压缩包有生成、编译、仿真、汇总框架；
- 当前 prompts 与论文 snapshot 不完全一致；
- 当前 evaluator 不能直接重算 L/M/H 与全题结果。

### 不能证明

- 本机已加载 2B/6B/16B；
- 论文 50K/300MB 或 400MB corpus 已下载；
- 五个模型已本机重训；
- 9,180 completion/model 已生成；
- Table III/IV 可由当前仓库一键重算；
- CodeGen-16B-FT 的 41.9% 已本地复现；
- 17 个 testbench 对所有未指定行为完备；
- 当前 high-detail prompt 是论文原版。

---

## 34. 严格复现路线

### 阶段 A：论文归档已完成，snapshot 仍需追溯

1. 保留当前 `2212.11140`；
2. 已归档 `2308.00708v1.pdf` 并建立独立详解；
3. 已区分 DATE paper 与 VeriGen later paper；
4. 找到论文时期 repo tag/commit；
5. 固定 Hugging Face revisions。

### 阶段 B：修 benchmark artifact

1. advanced3 H prompt 移除完整答案；
2. 恢复真正的 L/M/H；
3. reference-first 编译/仿真；
4. manifest 记录每题 prompt/reference/testbench hash；
5. 写 negative control 验证判分。

### 阶段 C：修 evaluator

1. 输出路径加 prompt ID；
2. raw output 与 repaired output 分开；
3. JSON 正规序列化；
4. 检查 return code；
5. timeout；
6. 独立临时 build dir；
7. robust terminal marker/mismatch count；
8. 全 17 题汇总；
9. n=1/10/25；
10. 保存五温度全量分数。

### 阶段 D：模型与训练

先只做作者 checkpoint artifact evaluation；再决定是否重建 corpus 和微调。

重训需要完整 provenance、去重和 decontamination，否则即使分数一致也不能证明同一数据。

---

## 35. 对当前 evaluator 的最小修复清单

本篇只审阅，没有修改代码。后续优先：

1. `examples_dir_name` 加 prompt 文件 stem；
2. 删除 `get_results.py` 的 `prompts=["advanced5"]`；
3. 任务列表自动从 manifest 读取 17 题；
4. n 改为论文 1/10/25；
5. `model_kind` 真正影响 checkpoint；
6. `subprocess.run(..., timeout=...)`；
7. 用 return code，而不是 stderr 为空；
8. 输出协议用明确 JSON/exit code；
9. build dir 每样本隔离；
10. raw completion 不自动补 `end`；
11. 若保留 repair，单列 repair rate；
12. `examples.json` 用 `json.dump`；
13. 汇总按 task/detail/temp/model/sample；
14. 同时报 sample accuracy 与标准 task-level pass@k；
15. 修 advanced3 prompt leakage。

---

## 36. 组会分享建议

### 推荐标题

**“从 GitHub Verilog 微调到可执行功能评价：VGen/VeriGen 的早期路线与当前 artifact 真相”**

### 推荐 12 页

1. 先纠正 2212.11140 与 2308.00708；
2. Figure 1 全流程；
3. 50K/300MB GitHub corpus；
4. 70 本教材与 400MB；
5. 五个模型与训练成本；
6. 17 题 Basic/Intermediate/Advanced；
7. L/M/H prompts；
8. temperature/n sweep；
9. compile 与 functional 的分层；
10. Table III/IV 与 41.9 vs 35.4；
11. 系统性失败任务；
12. 当前代码的目录碰撞、答案泄漏和汇总问题。

### 三条重点结论

1. Verilog domain fine-tuning 在当时显著提升 syntax 与功能；
2. 更多参数/更详细 prompt 并非每个任务单调有效；
3. benchmark 的代码实现会决定分数能否可信重算。

---

## 37. 历史价值与今天还能做什么

到 2026 年，单纯“抓 GitHub Verilog 微调 CodeGen”已不新颖，但这篇仍值得作为历史基线，因为它很早就坚持用 testbench 而不是 BLEU。

今天可继续的方向：

- license/provenance 完整语料；
- 语义/结构去重而不是只看文本；
- 时间切分避免 benchmark 污染；
- verified instruction-code data；
- 多模块/协议/processor 任务；
- simulation + formal 双轨；
- 工具反馈 repair；
- PPA-aware generation；
- 标准 task-level pass@k 与成本报告。

VGen 最适合当作“起点”，与 RTLCoder、AutoVCoder、OpenLLM-RTL 和 VerilogCoder 对比数据与反馈如何演进。

---

## 38. 文件导航

### 论文与说明

- [当前 2212.11140 论文](./2212.11140_VeriGen.pdf)
- [VeriGen 扩展论文 2308.00708v1](./2308.00708v1.pdf)
- [扩展论文独立详解](./VeriGen扩展论文_2308.00708_论文与代码复现详解.md)
- [扩展论文静态审计](./runs/static_audit_2308.00708_20260803.json)
- [README](./README.md)
- [短版模型梳理](./模型梳理.md)

### 数据构造

- [BigQuery notebook](./verilog-fetch-big-query.ipynb)
- [PDF extractor](./pdf_extractor.py)
- [PDF extraction instance](./pdf_extraction_instance.py)

### 推理与评价

- [6B demo notebook](./VGen_Demo_notebook.ipynb)
- [Colab demo notebook](./VGen_Demo.ipynb)
- [评价脚本压缩包](./evaluation_scripts.zip)
- [17 题 prompts/testbenches](./prompts-and-testbenches/)
- [静态审计](./runs/static_audit_20260802.json)

---

## 39. 最终判断

这篇论文在方法史上的意义很明确：它证明 Verilog 专用 fine-tuning 能让开放 CodeGen 在一个可执行的 17 题 benchmark 上超过当时 commercial Codex 的总体功能通过比例，并且系统研究了温度、候选数、模型大小和 prompt 详细度。

代码审计后的真实开放边界是：

- 题目、prompt、testbench 和 demo 比较完整；
- 训练 corpus、训练实现、论文输出和结果表不在本仓库；
- 当前 prompts 后于论文发布，且 advanced3 存在完整答案泄漏；
- 当前 evaluator 的目录、汇总、n 值和判分实现不足以直接复算论文；
- committed notebook 有作者历史 6B half-adder 输出，但不是本机运行，也没有 testbench 证据；
- 本篇 PDF 不是后续同名 VeriGen 论文；后续扩展稿现已另行归档和整理。

因此准确结论是：

> **本地已完成 2212.11140 DATE 前版及 2308.00708v1 扩展稿的分篇整理，并核对 17 题/51 prompt/17 testbench、两个推理 notebook、BigQuery/PDF 数据入口和 zipped evaluator；未重新加载模型、生成 RTL、运行 Icarus 或重训，论文结果表尚未本地重算。**

---

## 40. P7 组件一句话角色

| 组件 | 一句话角色 |
|---|---|
| `verilog-fetch-big-query.ipynb` | 从 GitHub BigQuery snapshot 中检索并下载 `.v` 文件以构建训练语料。 |
| `pdf_extractor.py` / `pdf_extraction_instance.py` | 从 70 本 Verilog 教材 PDF 中抽取文本并构造重叠滑窗训练样本。 |
| `VGen_Demo_notebook.ipynb` | 加载微调后的 CodeGen-6B 并演示 half-adder 自回归补全。 |
| `evaluation_scripts.zip` | 内含生成、编译、仿真和汇总的端到端 evaluator 脚本链。 |
| `prompts-and-testbenches/` | 存放 17 题 × L/M/H 三档 prompt、testbench 和参考实现的 benchmark 资产。 |

---

## 41. 讨论问题

1. 当前 evaluator 把 L/M/H 三档 prompt 的输出放到同一目录导致后两档被跳过，这种实现漏洞会如何系统性扭曲对“prompt 详细度影响”的结论？
2. 论文把 17 题分成 Basic/Intermediate/Advanced 并 sweeps 温度与样本数，这种小样本 benchmark 在今天应如何扩展才能保持对现代大模型的区分度？
3. 训练语料来自 GitHub 和教材 PDF，但仓库没有提供完整 300/400 MB corpus 的 license/provenance，后续研究应如何建立可追溯的 Verilog 数据集？

