# VerilogEval：论文、v1 代码与可复现边界详解

> 论文：Mingjie Liu, Nathaniel Pinckney, Brucek Khailany, Haoxing Ren, **VerilogEval: Evaluating Large Language Models for Verilog Code Generation**, ICCAD 2023。  
> 本地论文：[2309.07544_VerilogEval.pdf](2309.07544_VerilogEval.pdf)；arXiv：<https://arxiv.org/abs/2309.07544>；DOI：<https://doi.org/10.1109/ICCAD57390.2023.10323812>。  
> 开源仓库：<https://github.com/NVlabs/verilog-eval>；原版分支：<https://github.com/NVlabs/verilog-eval/tree/release/1.0.0>。  
> 本地仓库当前是 v2 主线 commit `c498220d0a52248f8e3fdffe279075215bde2da6`；v1 证据来自本地 Git 对象中的 `origin/release/1.0.0`，commit `4fa0ac4ed70ff1685114c25cd2e4c17cbba6a0c4`。  
> 静态核对记录：[runs/static_audit_20260802.json](runs/static_audit_20260802.json)。  
> 核对日期：2026-08-02。本文只读论文、代码、Git 历史和数据，没有重新执行模型推理、训练、编译或仿真。

---

```text
┌─────────────────────────────────────────────────────────────────────────┐
│ P1 任务定义                                                              │
├─────────────────────────────────────────────────────────────────────────┤
│ Input:  自然语言问题描述 + 固定 module header/prompt + 可选 system      │
│         prompt + LLM 采样配置（temperature/top-p/n）                        │
│ Output: 每题的 Verilog completion、Icarus 编译/仿真结果、pass@1/5/10   │
│         功能正确率指标                                                    │
│ Supervision: 不人工判题；用内置 reference_module 的 testbench 作为功能    │
│              oracle；SFT 阶段使用 8,502 条合成 description-code pairs     │
│ Why-hard: 同功能多实现使 BLEU 失效；testbench 覆盖有限；Human/Machine     │
│           描述分布差异大；v1 默认关闭真实执行；SFT 数据、权重和原始样本未   │
│           公开                                                             │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 1. 先给结论

VerilogEval 的核心贡献不是一个新的 RTL 生成模型，而是把“小型自然语言硬件题 → Verilog code completion → Icarus 仿真 → pass@k”做成了公开、统一的评价协议，并首次较系统地比较：

1. 人工整理的 156 题 `VerilogEval-human`；
2. GPT-3.5 自动生成描述后筛出的 143 题 `VerilogEval-machine`；
3. GPT-3.5、GPT-4 与 CodeGen 系列模型；
4. 用 8,502 个合成“问题描述—Verilog 模块”对做 SFT 的效果；
5. SFT epoch、底模、模型规模和训练数据正确性对 pass@1/pass@5/pass@10 的影响。

本地代码核对后的复现结论是：

| 部分 | 是否开源 | 本地可达到的程度 | 关键边界 |
|---|---:|---:|---|
| 156/143 题评价数据 | 是 | R1，静态完整 | 位于 v1 Git 分支，不在当前工作树 |
| pass@k 计算代码 | 是 | R1，公式与实现可核 | 默认 `k=[1,10,100]`，论文实验用 `{1,5,10}` |
| Icarus 功能判分 | 是 | 有条件 R2 | v1 执行块默认被注释，且必须在安全沙箱中手工启用 |
| GPT/CodeGen 原始输出 | 否 | R0 | 仓库没有论文完整 samples 与结果日志 |
| 8,502 条合成 SFT 数据 | 否 | R0 | 论文给方法和总量，仓库未给数据快照 |
| SFT 训练脚本、配置、checkpoint | 否 | R0 | 论文给主要超参，代码和权重未发布 |
| 论文全部表格数值 | 仅论文报告 | R0 | 不能把代码可读等同于实验已复现 |

因此，这个项目最适合用于：

- 作为 RTL 生成项目的公共功能正确性 evaluator；
- 讲清 pass@k 为什么需要多样本；
- 展示训练数据质量和输出多样性的权衡；
- 作为 VerilogCoder、MAGE、AutoChip、RTLCoder 等后续工作的共同评价底座。

不适合把它表述成“本地已经复现了论文 SFT 结果”。当前证据只支持基准数据与评价调用链的静态复核。

---

## 2. 论文首页与总体框架

![论文标题、摘要与 Figure 1](figures/v1-paper-title-abstract-fig1.png)

Figure 1 把论文的评价对象概括为：

```text
自然语言问题描述
    ↓
LLM 生成 Verilog completion
    ↓
与 module header 拼接成 DUT
    ↓
crafted testbench + golden solution
    ↓
Icarus Verilog 编译与瞬态仿真
    ↓
Pass / Fail → 跨多次采样统计 pass@k
```

这里的“sandbox environment”需要谨慎理解。论文图表示评价应在沙箱中完成，但 v1 开源实现自己也明确声明 `reliability_guard` **不是安全沙箱**。仓库通过把真正的 `iverilog/vvp` 调用整体注释掉，强制使用者先阅读安全警告并自行准备隔离环境。

---

## 3. 论文到底解决什么问题

此前的 Verilog 生成研究常见三个问题：

- 题量少，难以稳定比较模型；
- 题目、prompt、测试方法不统一；
- 只看语法或文本相似度，不能回答“电路功能是否正确”。

VerilogEval 的回答是把软件代码基准 HumanEval 的思路迁移到硬件代码：每个任务都给自然语言要求和顶层接口，模型只补全模块主体；测试平台同时实例化候选 DUT 与参考实现，在大量激励周期上比较输出。

论文贡献可以拆成三层：

| 层级 | 贡献 | 是否由当前 v1 开源仓库完整覆盖 |
|---|---|---:|
| Benchmark | 156 个 HDLBits 任务、Human/Machine 两套描述 | 基本覆盖 |
| Evaluator | Icarus 功能仿真、结果 JSONL、pass@k | 覆盖，但执行默认关闭 |
| Model study | 8,502 条合成 SFT 数据、CodeGen SFT 与消融 | 不完整，仅论文描述和结果 |

后续引用 VerilogEval 时应说明引用的是哪一层。很多项目只复用了 benchmark/evaluator，并没有复现论文的 CodeGen SFT。

---

## 4. 任务定义：code completion，不是完整 spec-to-RTL

原版 v1 给模型的目标是补全已有模块头，而不是从自由格式规格独立生成完整模块。

论文 Figure 2 的示意如下：

![VerilogEval-human 的 prompt 组成](figures/v1-paper-fig2-problem-format.png)

其逻辑结构是：

```text
[可选 system prompt]
    +
[固定 question prompt]
    +
[自然语言描述]
    +
[module top_module(...); 接口]
    → LLM
    → 只返回模块内部实现和 endmodule
```

这降低了任务难度：

- 顶层模块名已给定；
- 端口名、方向和位宽已给定；
- 输出是否是 `reg` 往往也已给定；
- 模型主要负责组合逻辑、时序逻辑和 FSM 主体。

所以 v1 指标不能直接等价为“从自然语言规格独立完成 RTL 设计”的能力。后来的 v2 才新增 specification-to-RTL 任务，详见 [Revisiting VerilogEval论文与代码复现详解.md](Revisiting%20VerilogEval论文与代码复现详解.md)。

---

## 5. 156 个任务从哪里来

论文从 HDLBits 选择 156 个题，覆盖：

- 基础 wire、常量、逻辑门；
- 向量、位选择、归约运算；
- 多路选择器、加法器、组合逻辑；
- D 触发器、计数器、移位寄存器、LFSR；
- Karnaugh map、真值表；
- 有限状态机与较复杂时序控制。

筛选原则包括：

- 题意相对明确；
- 可表示成纯文本；
- 顶层模块 self-contained；
- 不依赖实例化其他用户模块。

论文明确承认，模块实例化是 Verilog 系统设计的重要能力，但不在该基准范围内。这一限制后来促成 RTL-Repo、ArchXBench、RealBench、CVDP、ChipBench 等更工程化的 benchmark。

---

## 6. Human 与 Machine 不是两套不同电路

两套集合的差异主要是问题描述来源：

| 集合 | 数量 | 描述来源 | 特点 |
|---|---:|---|---|
| VerilogEval-human | 156 | 人工把 HDLBits 页面整理成纯文本 | 更接近真实教学题，可能包含表格、波形/FSM 的文字化信息 |
| VerilogEval-machine | 143 | GPT-3.5 根据 canonical RTL 生成 | 通常更直接、更接近代码语义，可能比真实用户要求更详细 |

v1 分支中评价 JSONL 的静态计数已经核对：

```text
data/VerilogEval_Human.jsonl   156 rows
data/VerilogEval_Machine.jsonl 143 rows
```

每行评价记录的字段都是：

```json
{
  "task_id": "...",
  "prompt": "module top_module (...);",
  "canonical_solution": "...",
  "test": "..."
}
```

自然语言描述另存于：

```text
descriptions/VerilogDescription_Human.jsonl
descriptions/VerilogDescription_Machine.jsonl
```

也就是说，评价器本身只需要 `prompt/test` 和模型的 `completion`；调用模型并把自然语言描述与 module header 组合起来，是上游采样流程的责任。

---

## 7. Machine 描述怎样从 156 题变成 143 题

论文不是简单让 GPT-3.5 一次性生成 156 条描述，而是用“生成描述 → 再让模型按描述写代码 → 用 testbench 验证”筛选描述是否可用。

流程是：

```text
canonical Verilog
    ↓ GPT-3.5 生成自然语言描述
候选 machine description
    ↓ 再采样 Verilog completions
HDLBits testbench 验证
    ├─ 至少一个 completion 通过 → 接受描述
    └─ 全部失败 → 继续 few-shot 生成或最终丢弃
```

具体数字：

1. 零样本描述生成后，对每题最多采样 100 个代码解答；156 题中 108 题得到至少一个通过解答；
2. 将已验证描述作为 4-shot 示例，对剩余题每个描述采 8 个解答；
3. 又筛出 35 题；
4. 最终 `108 + 35 = 143` 题。

这种验证只能说明“描述足以让当时模型产生至少一个可通过答案”，并不能证明描述完全无歧义。v1 README 也明确说不保证 machine descriptions 没有错误，且不计划维护其正确性。

---

## 8. testbench 如何成为功能 oracle

v1 的每个 `test` 字段不是普通单元测试列表，而是一段完整 SystemVerilog 测试环境，通常包含：

- `reference_module`：golden RTL；
- `stimulus_gen`：手工激励和随机激励；
- `tb`：同时实例化 reference 与候选 `top_module`；
- 逐周期比较候选输出与参考输出；
- 最后打印固定格式 `Mismatches: N in M samples`。

候选程序由 evaluator 按下面的顺序拼接：

```python
verilog_test = problem["test"] + "\n" + problem["prompt"] + "\n" + completion
```

因此模型 samples 文件必须只提供 completion，不能重复测试平台，也不应改写题目 ID。

论文称每题一般运行数百到数千个时钟/激励周期。通过条件不是与 canonical solution 文本相同，而是测试平台观察到的行为相同。

---

## 9. 为什么不用 BLEU

同一个电路可以有很多文本差异很大的正确实现。例如多路选择器可以写成条件运算符、`case` 或组合 `always`；FSM 可用不同状态编码。

所以：

- 高 BLEU 不保证功能正确；
- 低 BLEU 也不代表电路错误；
- 功能仿真更贴近任务目标。

但功能仿真仍受 testbench 覆盖率限制。它只能证明候选通过已给激励，不能证明对所有输入与时序都等价；也不检查可综合性、PPA、时序收敛和工程规范。

---

## 10. v1 evaluator 的完整调用链

原版分支的关键入口是：

```text
evaluate_functional_correctness CLI
    ↓
verilog_eval/evaluate_functional_correctness.py
    ↓
evaluation.evaluate_functional_correctness()
    ↓ 每个 sample 提交进程池
execution.check_correctness(problem, completion)
    ↓
test + prompt + completion → <task_id>.sv
    ↓
iverilog -Wall -Winfloop -Wno-timescale -g2012 -s tb
    ↓
vvp -n test.vvp
    ↓
解析 Mismatches: N in M samples
    ↓
passed/result 写入 *_results.jsonl
    ↓
estimate_pass_at_k() 对各题平均
```

v1 源文件可在固定 commit 查看：

- [evaluation.py](https://github.com/NVlabs/verilog-eval/blob/4fa0ac4ed70ff1685114c25cd2e4c17cbba6a0c4/verilog_eval/evaluation.py)
- [execution.py](https://github.com/NVlabs/verilog-eval/blob/4fa0ac4ed70ff1685114c25cd2e4c17cbba6a0c4/verilog_eval/execution.py)
- [README.md](https://github.com/NVlabs/verilog-eval/blob/4fa0ac4ed70ff1685114c25cd2e4c17cbba6a0c4/README.md)

本地当前工作树是 v2，不能把当前 [scripts/sv-iv-analyze](scripts/sv-iv-analyze) 当成原论文 evaluator；两者评价输出和代码结构不同。

---

## 11. 编译、运行与通过条件

v1 `execution.py` 的核心命令等价于：

```bash
iverilog -Wall -Winfloop -Wno-timescale -g2012 -s tb \
  -o test.vvp <task_id>.sv
vvp -n test.vvp
```

解析顺序是：

1. `stderr` 中包含 `syntax error` → syntax failure；
2. 其他任何非空 `stderr` → compile failure；
3. `stdout` 匹配 `Mismatches: N in M samples`；
4. `N == 0` → passed；
5. `N > 0` → functional failure；
6. 找不到固定字符串 → info string not matched；
7. 超时 → timed out。

这里有一个重要实现边界：除 syntax 特例外，任何 `stderr` 都按编译失败处理，某些不影响功能的 warning 也可能被归入失败。结果依赖 Icarus 版本和日志格式。

---

## 12. pass@k 的含义与公式

每题生成 `n` 个 completion，其中 `c` 个通过。若从这 `n` 个候选中不放回地选择 `k` 个，至少一个正确的概率估计为：

```text
pass@k = 1 - C(n-c, k) / C(n, k)
```

代码避免直接计算大组合数，使用乘积形式：

```python
1.0 - np.prod(1.0 - k / np.arange(n - c + 1, n + 1))
```

然后对所有题求均值。

直观例子：若一题 `n=20`、`c=4`：

- pass@1 反映随机取一个答案通过的概率；
- pass@5 反映给用户五次尝试至少一个通过的概率；
- pass@10 更强调候选集合覆盖正确解的能力。

pass@k 不是把 top-k token 概率相加，也不是一次 beam search 的准确率。

---

## 13. 代码默认 k 与论文 k 不完全相同

v1 `evaluation.py` 函数默认：

```python
k = [1, 10, 100]
```

而论文所有主要实验使用：

```text
n = 20
k = {1, 5, 10}
```

因为 `n < 100`，默认 `pass@100` 会被跳过。要得到论文三项指标，必须显式传入：

```bash
--k=1,5,10
```

这是复现时很容易忽略的小差异。不能只跑 README 默认命令就宣称复现了论文表格。

---

## 14. 论文的统一采样设置

论文对 GPT 与 CodeGen 实验采用：

| 参数 | 值 |
|---|---:|
| 每题 completion 数 `n` | 20 |
| nucleus top-p | 0.95 |
| temperature | 0.8 |
| 上下文长度 | 2048 |
| 报告指标 | pass@1、pass@5、pass@10 |

这些参数决定候选多样性。若改用 greedy、temperature 0、不同 stop string 或更长上下文，数值不再与论文同协议。

特别是一些 Verilog 模型会继续生成第二个 `module`、解释文本或重复代码；不同的后处理会显著改变语法通过率。论文未开源统一的所有模型采样与后处理脚本，因此完整数字复现还缺一层关键协议。

---

## 15. 论文主要模型结果

论文 Table II 的修订版结果：

| 模型 | Machine pass@1 | pass@5 | pass@10 | Human pass@1 | pass@5 | pass@10 |
|---|---:|---:|---:|---:|---:|---:|
| GPT-3.5 | 46.7 | 69.1 | 74.1 | 26.7 | 45.8 | 51.7 |
| GPT-4 | 60.0 | 70.6 | 73.5 | 43.5 | 55.8 | 58.9 |
| CodeGen-16B-Verilog-SFT | 46.2 | 67.3 | 73.7 | 28.8 | 45.9 | 52.3 |

![SFT epoch、模型规模和 Table II/III](figures/v1-paper-fig8-9-table2-3.png)

注意论文脚注明确说较早版本的 GPT-4 数字有错误。本地 PDF 是 arXiv v2（2023-12-10），整理和横向对比应使用这里的修订值。

---

## 16. 为什么 Machine 分数通常更高

Machine descriptions 是从 canonical RTL 反向生成，再经过“模型能否按描述写出至少一个正确解”的筛选，因此有明显选择效应：

- 描述更接近代码；
- 细节可能更显式；
- 难以被 GPT-3.5 重新解出的描述被淘汰；
- 最终只保留 143/156 题。

Human descriptions 更贴近真实题目，有些信息原本来自波形、状态图、K-map 和表格，转成文本后结构更复杂。

所以 Machine 分数更高不能简单解释成“机器描述质量一定更好”，更准确的说法是它更靠近生成模型的分布，而且经过模型可解性筛选。

---

## 17. 合成 SFT 数据是怎样构造的

论文从公开 GitHub Verilog 数据中提取 self-contained 模块，再用 GPT-3.5 根据代码生成问题描述，最终形成 8,502 对数据。

![合成 SFT 数据筛选方法](figures/v1-paper-sft-data-method.png)

方法流程：

```text
公开 GitHub Verilog 语料
    ↓ Pyverilog AST/模块提取
self-contained 候选模块
    ↓ 长度、关键词、实例化过滤
    ↓ MinHash 近重复过滤
去重模块
    ↓ GPT-3.5 + 4 个 Human few-shot 示例
自然语言问题描述
    ↓
8,502 条 description-code pairs
```

这部分是论文的方法贡献，但不是当前仓库可一键运行的 pipeline。

---

## 18. 代码筛选规则

论文列出的筛选条件是：

1. `module` 与 `endmodule` 位于提取代码的开始和结束位置；
2. 模块不超过 200 行；
3. token 数不超过 1,024；
4. 至少包含一个关键字：`always`、`assign`、`always_ff`、`always_comb`、`always_latch`；
5. 模块不实例化其他模块；
6. 使用 MinHash 近似去重；
7. Jaccard 相似度阈值为 0.8。

生成描述时使用四个 VerilogEval-human 示例：

```text
shift18
rule110
lemmings1
fsm3onehot
```

选择这些例子是为了同时覆盖普通描述、表格化状态行为和较复杂时序逻辑。

---

## 19. SFT 数据与评价数据不能混为一谈

论文有两个数量经常被错误合并：

| 名称 | 数量 | 用途 | 当前仓库是否提供 |
|---|---:|---|---:|
| VerilogEval-human | 156 | 测试 benchmark | 是，v1 分支 |
| VerilogEval-machine | 143 | 测试 benchmark | 是，v1 分支 |
| synthetic SFT pairs | 8,502 | 模型微调训练 | 否 |

“VerilogEval 有 8,502 个测试题”是错误说法。8,502 是训练对；公开 benchmark 仍是 156/143 题。

此外，论文没有提供 8,502 条数据的文件哈希、逐条来源、生成日志或污染审计，无法从开源仓库验证这些训练模块与 156 个 HDLBits 测试答案是否存在近似重合。

---

## 20. SFT 训练设置

![论文 SFT 设置](figures/v1-paper-sft-settings.png)

论文报告的主要设置：

| 项目 | 设置 |
|---|---|
| Optimizer | Adam |
| β1 / β2 | 0.9 / 0.999 |
| ε | 1e-8 |
| Learning rate | 2e-5 |
| Effective batch | 1M tokens |
| Weight decay | 0 |
| Context | 2048 |
| Hardware | 1 个 DGX 节点、8×A100、2 TB RAM |
| CodeGen-multi SFT | 10 epochs |
| 其他 Verilog 模型 SFT | 5 epochs |

论文覆盖 CodeGen 350M、2B、6B、16B，并比较 `codegen-nl`、`codegen-multi` 与 `codegen-verilog`。

但仓库没有：

- 数据预处理脚本；
- tokenizer 后的训练集；
- optimizer/scheduler 完整配置；
- 分布式训练启动命令；
- checkpoint；
- 每 epoch 训练日志。

因此只能复述方法，不能按当前仓库逐行还原训练调用链。

---

## 21. SFT epoch 的核心结论

Figure 8 的重要结论不是“epoch 越多越好”，而是：

- pass@1 往往继续提高；
- pass@5/pass@10 在若干设置中先升后降；
- 模型对简单题更自信，但输出多样性下降；
- 对齐训练可能把概率集中到少数模式，损失“多次尝试至少一次成功”的覆盖率。

这说明只报 pass@1 会漏掉模型多样性退化。对需要候选生成、rerank 或 agent debugging 的系统，pass@5/pass@10 仍很有价值。

---

## 22. 底模与规模消融

论文 Table III 在 VerilogEval-machine 上比较 16B：

| 模型 | pass@1 | pass@5 | pass@10 |
|---|---:|---:|---:|
| CodeGen-16B-NL-SFT | 33.9 | 51.9 | 58.1 |
| CodeGen-16B-Multi-SFT | 37.1 | 55.0 | 61.1 |

`codegen-nl` tokenizer 对代码空白处理效率较低，一些 Human 题在 2,048 token context 下装不下，所以论文这里只报 Machine。

规模实验总体显示大模型更强，但 Verilog 预训练是否充分也很关键。仅把通用软件代码能力迁移到 HDL，提升有限；领域语料和问题—代码对齐都重要。

---

## 23. 错配数据消融说明“数据质量比数量更重要”

论文把问题描述随机打乱，与错误 Verilog 配对，构造 `sft-error`：

| 模型 | Machine pass@1 | pass@5 | pass@10 |
|---|---:|---:|---:|
| CodeGen-2B-Verilog | 20.1 | 46.0 | 55.9 |
| + 正确 SFT | 35.9 | 59.0 | 65.7 |
| + 错配 SFT | 21.4 | 38.8 | 46.1 |

![Table IV 与论文限制](figures/v1-paper-table4-limitations.png)

错误数据使 pass@5/pass@10 甚至低于底模，说明模型可能学到表面“Verilog 风格”却破坏问题—实现对应关系。对当前 RTL 数据合成工作，这比单纯扩充百万样本更值得强调。

---

## 24. v1 开源目录与论文模块对应

原版分支文件映射如下：

```text
release/1.0.0
├── data/
│   ├── VerilogEval_Human.jsonl       # 156 题评价结构
│   ├── VerilogEval_Machine.jsonl     # 143 题评价结构
│   └── example/                       # 3 题 smoke example
├── descriptions/
│   ├── VerilogDescription_Human.jsonl
│   └── VerilogDescription_Machine.jsonl
├── verilog_eval/
│   ├── data.py                        # JSONL I/O
│   ├── evaluate_functional_correctness.py
│   ├── evaluation.py                  # 任务调度与 pass@k
│   └── execution.py                   # 拼接、Icarus、判分与安全警告
├── setup.py
├── requirements.txt
└── Dockerfile
```

缺失的论文模块：

```text
GitHub Verilog 抓取/提取脚本
Pyverilog 自包含过滤脚本
MinHash 去重脚本
GPT-3.5 描述生成脚本与原始响应
8,502 条 SFT 数据
CodeGen 训练配置与 launcher
论文 checkpoints
20 samples × 每模型 × 每题的完整输出
论文汇总日志
```

---

## 25. v1 默认不能直接判分

这是代码核对中最重要的事实之一。

`release/1.0.0/verilog_eval/execution.py` 把真正执行 `iverilog` 和 `vvp` 的代码放在三引号字符串中，即默认不会执行。README 明确要求使用者：

1. 阅读执行不可信模型代码的风险；
2. 准备可靠安全沙箱；
3. 手工启用该代码块；
4. 再运行 evaluator。

如果不启用，子进程结果为空，最终会落为 `timed out`。所以“pip install 后直接跑 README 命令”不会得到论文 pass@k。

这是有意的安全门槛，不应把它简单当成普通 bug 修掉，更不应直接在宿主机批量执行未知模型生成的 SystemVerilog。

---

## 26. v1 的安全与进程清理问题

`reliability_guard()` 会禁用许多 Python 文件与进程 API，但它明确声明自己不是 security sandbox，而且为了调用 Icarus 保留了 `subprocess.Popen`。

另一个风险是：

```python
subprocess.run("pkill iverilog", shell=True)
subprocess.run("pkill vvp", shell=True)
```

`clean_up_simulation()` 会按进程名全局终止当前环境中的 Icarus/vvp，而不是只杀本次 evaluator 的子进程。在共享服务器上可能误伤其他人的仿真任务。

因此推荐隔离层级是：

```text
专用容器/虚拟机
    + 无敏感挂载
    + 限制网络
    + 限制 CPU/内存/进程数
    + 每次运行独立工作目录
    + 只清理本容器内子进程
```

本次整理没有为“验证是否能跑”而绕开这一安全设计。

---

## 27. 原版复现的正确版本固定方式

当前本地工作树是 v2，直接 `git checkout release/1.0.0` 会改变仓库状态。若要保留两版并行，建议另建 worktree：

```bash
cd /mnt/d/AI4eda/VerilogEval
git worktree add ../VerilogEval-v1 origin/release/1.0.0
```

然后只在隔离容器中安装：

```bash
cd /workspace/VerilogEval-v1
python -m pip install -e .
```

评价输入应是：

```json
{"task_id":"对应题目 ID","completion":"只含补全代码"}
```

论文协议需要显式：

```bash
evaluate_functional_correctness samples.jsonl \
  --problem_file data/VerilogEval_Human.jsonl \
  --k=1,5,10
```

这些命令是复现说明，本次没有执行。

---

## 28. 最小可复现与论文级复现的区别

### 28.1 最小 evaluator 复现

需要：

- 固定 v1 commit；
- Icarus v12；
- 安全容器；
- 手工审查并启用执行块；
- 少量已知 samples；
- 检查 example 是否得到预期 pass@1=0.5。

这只能证明 evaluator 工作。

### 28.2 benchmark 模型复现

还需要：

- 固定具体模型 checkpoint；
- 固定 tokenizer、prompt、stop 与后处理；
- temperature=0.8、top-p=0.95；
- 每题 20 samples；
- 156/143 题完整运行；
- `k=1,5,10`。

### 28.3 论文 SFT 复现

还需要论文未公开的：

- 8,502 条数据；
- 数据生成和过滤代码；
- CodeGen SFT pipeline；
- 完整训练超参和随机种子；
- 论文 checkpoint。

所以当前项目只能把前两层准备清楚，第三层无法由仓库独立重建。

---

## 29. 与 v2 及后续项目的关系

| 项目 | 在 VerilogEval 基础上增加什么 |
|---|---|
| Revisiting VerilogEval / v2 | spec-to-RTL、0–4 shot ICL、错误分类、Makefile 流程、14 题修订 |
| AutoChip | 把编译/仿真 mismatch 反馈给模型，形成迭代闭环 |
| RTLFixer / VeriAssist | 根据编译或功能错误自动修复 |
| VerilogCoder | 规划、多 agent、AST/VCD 波形分析与调试 |
| MAGE | 多候选 RTL、judge、testbench/debug agents 与迭代选择 |
| RTLCoder / AutoVCoder | 面向 RTL 的 SFT/RAG 与专用模型 |
| GenBen / RealBench / CVDP | 更复杂、更新或覆盖更广的验证任务 |

VerilogEval 的价值是统一底座；它不是这些后续 agent 的直接竞争方案。后续论文的高 pass rate往往允许访问 testbench、仿真日志、波形或多轮反馈，和原版单轮 20-sample 协议不是同等资源条件。

---

## 30. 局限、污染与报告规范

### 30.1 论文已承认的局限

- 电路规模偏小；
- self-contained，不考模块实例化；
- 只看功能仿真；
- 不保证生成 RTL 可综合；
- 不评估 PPA 与时序；
- testbench 通过不等于形式等价。

### 30.2 公开基准污染

题目来自公开 HDLBits，VerilogEval 又被大量论文和训练数据收录。2026 年继续使用时，应默认存在预训练或微调污染风险。

### 30.3 建议的结果标签

```text
VerilogEval version/commit
Human 或 Machine
v1 code completion 或 v2 spec-to-RTL
模型与 checkpoint
prompt / shot / rules
temperature / top_p / n / k
completion 后处理
Icarus 版本
是否允许 testbench、日志、波形和迭代修复
是否为论文报告值、本地实测值或第三方引用值
```

不写这些条件，只写“VerilogEval 95%”，没有可比意义。

---

## 31. 适合组会分享的逻辑

建议用 12–15 分钟：

1. **2 分钟：为什么 BLEU 不适合 RTL**——同功能多实现；
2. **3 分钟：156/143 题怎么构造**——Human 与 Machine 的选择效应；
3. **3 分钟：testbench + Icarus + pass@k**——功能 oracle 和多样性；
4. **3 分钟：8,502 条 SFT 数据**——代码过滤、MinHash、描述生成；
5. **2 分钟：三组消融**——epoch、底模/规模、错误配对；
6. **2 分钟：开源边界**——evaluator 公开，SFT 数据/代码/权重未公开；
7. **收束**——它为何成为后续 RTL agent 的共同底座，但也为何逐渐饱和。

一句话标题可以是：

> **VerilogEval：把 RTL 生成从文本相似度比较推进到可执行功能评价，但训练复现与真实工程复杂度仍然缺位。**

---

## 32. 本地证据索引

### 论文与审计

- [原论文 PDF](2309.07544_VerilogEval.pdf)
- [Revisiting VerilogEval PDF](2408.11053_Revisiting_VerilogEval.pdf)
- [只读静态审计 JSON](runs/static_audit_20260802.json)

### 当前 v2 工作树中可用于版本对照的文件

- [README.md](README.md)
- [scripts/sv-generate](scripts/sv-generate)
- [scripts/sv-iv-analyze](scripts/sv-iv-analyze)
- [Makefile.in](Makefile.in)
- [dataset_code-complete-iccad2023](dataset_code-complete-iccad2023/)
- [dataset_spec-to-rtl](dataset_spec-to-rtl/)

### v1 固定 commit 远程代码

- [v1 data](https://github.com/NVlabs/verilog-eval/tree/4fa0ac4ed70ff1685114c25cd2e4c17cbba6a0c4/data)
- [v1 descriptions](https://github.com/NVlabs/verilog-eval/tree/4fa0ac4ed70ff1685114c25cd2e4c17cbba6a0c4/descriptions)
- [v1 evaluation.py](https://github.com/NVlabs/verilog-eval/blob/4fa0ac4ed70ff1685114c25cd2e4c17cbba6a0c4/verilog_eval/evaluation.py)
- [v1 execution.py](https://github.com/NVlabs/verilog-eval/blob/4fa0ac4ed70ff1685114c25cd2e4c17cbba6a0c4/verilog_eval/execution.py)

---

## 33. 最终判断

VerilogEval 是一篇非常值得分享的 benchmark 论文，因为它建立了后来 RTL 生成研究几乎都要面对的三个基本问题：

1. **任务输入是什么**——已有接口的 code completion，还是完整 spec-to-RTL；
2. **正确性怎么判**——文本相似度、仿真、形式验证还是 PPA；
3. **多样性怎么报告**——pass@1 与 pass@k 可能出现相反趋势。

但代码核对后必须补上第四个问题：

4. **论文究竟开放了哪一部分**——VerilogEval 开放了评价集和 evaluator，却没有开放 8,502 条 SFT 数据、训练代码、权重和论文完整生成输出。

因此，最准确的本地状态是：**基准方法与代码调用链已详细核清；原论文模型训练和表格尚不能由当前开源资产完整复现。**

---

## P7 关键组件一句话总结

| 组件 | 一句话总结 |
|---|---|
| Human/Machine benchmark | 156/143 道 HDLBits 题，分别由人工整理或 GPT-3.5 生成并筛选描述。 |
| code completion task | 给定 module header，模型只补全内部实现，降低接口歧义。 |
| testbench oracle | 拼接 test + prompt + completion，用 Icarus 仿真比较候选与参考输出。 |
| pass@k metric | 从 n 个候选中不放回取 k 个至少一个通过的概率，衡量输出多样性。 |
| synthetic SFT pipeline | 从 GitHub Verilog 提取自包含模块，经 MinHash 去重后让 GPT-3.5 生成描述。 |
| v1 evaluator | 静态代码完整但默认注释掉 Icarus 调用，需手工启用并在隔离环境运行。 |

---

## 讨论问题

1. Machine descriptions 经过“模型可解”筛选后，是否仍能量化描述歧义对性能的影响？
2. v1 evaluator 默认关闭 Icarus 执行，这种“安全门槛”设计对可复现性利大于弊还是弊大于利？
3. pass@5/pass@10 与 pass@1 趋势可能相反，评估 RTL 生成模型时应如何根据应用场景选择指标？

