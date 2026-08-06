# Revisiting VerilogEval：论文、v2 代码与评价口径详解

> 论文：Nathaniel Pinckney, Christopher Batten, Mingjie Liu, Haoxing Ren, Brucek Khailany, **Revisiting VerilogEval: A Year of Improvements in Large-Language Models for Hardware Code Generation**。  
> 本地论文：[2408.11053_Revisiting_VerilogEval.pdf](2408.11053_Revisiting_VerilogEval.pdf)；arXiv：<https://arxiv.org/abs/2408.11053>。本地文件是 arXiv v2，日期 2025-02-03，共 21 页。  
> 仓库 README 使用过较早标题 **Revisiting VerilogEval: Newer LLMs, In-Context Learning, and Specification-to-RTL Tasks**；两者对应同一 arXiv 号，整理时以本地 v2 PDF 标题为准。  
> 开源代码：<https://github.com/NVlabs/verilog-eval>；本地 commit `c498220d0a52248f8e3fdffe279075215bde2da6`，提交日期 2025-02-07。  
> 只读审计：[runs/static_audit_20260802.json](runs/static_audit_20260802.json)。  
> 核对日期：2026-08-02。本文没有重新执行模型推理、API 查询、训练、Icarus 编译或仿真；可运行性只按代码、数据、已有项目记录和开源缺口分级。

---

## 1. 先给结论

Revisiting VerilogEval 不是简单给原论文补一张“新模型排行榜”，而是同时做了四项 benchmark 基础设施升级：

1. 从只有 code completion 扩展到 specification-to-RTL；
2. 增加 0–3 shot 论文实验和 0–4 shot 仓库支持；
3. 把单一 pass/fail 拆成编译期与运行期错误类别；
4. 把 v1 的 monolithic JSONL evaluator 改成 Makefile 驱动的逐题文件和工作目录。

它还用 14 个新旧模型/规格模型比较说明：

- GPT-4o 与开放的 Llama3.1 405B 明显推进当时前沿；
- RTL-Coder 6.7B 以较小规模达到约 34%；
- specification-to-RTL 往往比 code completion 更适合 instruction-tuned 模型；
- ICL 不是单调增益，同一个例子可能改善一题、毁掉另一题；
- 只看总 pass rate 会掩盖错误类型迁移。

代码核对后的本地结论：

| 对象 | 代码/数据状态 | 本地证据等级 | 说明 |
|---|---|---:|---|
| 两种 156 题数据 | 完整 | R1 静态核清 | prompt/ref/test 文件齐全 |
| Makefile + Icarus evaluator | 完整度较高 | 条件 R2 | 需 Icarus v12、Python 依赖与已有/新生成 response |
| API generation | 有实现 | R1 | 需 OpenAI/NVIDIA 凭据；预导入两个 provider 包 |
| 手工/本地模型接入 | 有文件协议 | R1 | 生成 full/system prompt，用户放入 `_response.txt` |
| 论文原始模型 responses/logs | 未发布 | R0 | 当前目录没有 build、summary、sample 或日志 |
| 论文表格重算 | 本次未做 | R0 | 遵循用户要求，不重复模型推理 |

最值得组会分享的不是“GPT-4o 63%”本身，而是：**benchmark 的 prompt、后处理、测试题修订、采样方式和错误分类会共同决定结果；版本不固定时，所谓 pass@1 很容易失去可比性。**

---

## 2. 论文首页与主要结论

![论文标题与摘要](figures/v2-paper-title-abstract.png)

摘要给出的代表性结果是：

- GPT-4o 在 specification-to-RTL 约 63%；
- 开放的 Llama3.1 405B 约 58%；
- 专用 RTL-Coder 6.7B 约 34%。

这些数字对应论文使用的特定 prompt/shot/采样协议，不能脱离条件引用。以 GPT-4o 为例，Table 2 中 spec-to-RTL 的高温结果为：

```text
0-shot: 61.4%
1-shot: 62.6%
```

摘要的 63% 是对 1-shot 62.6% 的取整表达。

---

## 3. v1 与 v2 的根本区别

| 维度 | VerilogEval v1 | VerilogEval v2 |
|---|---|---|
| 任务 | code completion | code completion + spec-to-RTL |
| 描述集合 | Human 156 + Machine 143 | 只支持 Human 156 |
| 数据格式 | 两个大 JSONL + descriptions JSONL | 每题 prompt/ref/test/ifc 文件 |
| ICL | 不支持 | 0–4 shot 文件化支持；论文主要评 0–3 |
| 评价指标 | pass@1/5/10，n=20 | 论文称 pass@1；n=1 与 n=20 两种协议 |
| 错误输出 | passed/failed/timeout | 多类编译/运行错误码 |
| 调度 | Python 进程池 | `configure` + Makefile，可 `make -j` |
| 生成 | 用户外部准备 JSONL completions | `sv-generate` 可调用 API 或手工 response |
| 结果结构 | `*_results.jsonl` | 每题工作目录 + `summary.txt/csv` |

原版方法与 v1 代码详见 [VerilogEval论文与代码复现详解.md](VerilogEval论文与代码复现详解.md)。

---

## 4. v2 四项贡献的代码落点

| 论文贡献 | 当前仓库代码/数据 |
|---|---|
| Specification-to-RTL | [dataset_spec-to-rtl](dataset_spec-to-rtl/)，[sv-generate](scripts/sv-generate) 的 `spec-to-rtl` prompt 与提取分支 |
| In-context learning | `scripts/verilog-example-prefix_<task>_<n>-shot.txt` |
| Failure classification | [scripts/sv-iv-analyze](scripts/sv-iv-analyze)，[count_failures.py](count_failures.py) |
| Makefile infrastructure | [configure.ac](configure.ac)，[Makefile.in](Makefile.in)，[scripts/echo-progress](scripts/echo-progress) |

论文流程图与代码结构基本对应：

![VerilogEval v2 完整流程](figures/v2-paper-fig2-flow.png)

---

## 5. 当前仓库静态清单

本地逐文件核对结果：

| 数据目录 | problems | prompt | ifc | ref | test |
|---|---:|---:|---:|---:|---:|
| `dataset_code-complete-iccad2023` | 156 | 156 | 156 | 156 | 156 |
| `dataset_spec-to-rtl` | 156 | 156 | 0 | 156 | 156 |

两边 `problems.txt` 的 156 个 ID 完全一致，范围为：

```text
Prob001_zero
...
Prob156_review2015_fancytimer
```

额外文件包括：

- 两个目录都有 `Prob062_bugs_mux2.sv`，用于保留/检查该题历史问题；
- spec-to-RTL 还有 `problems-temp.txt`；
- 当前仓库没有预生成模型 samples、build 目录、`summary.txt/csv` 或实验日志。

所以“代码和题集完整”不等于“论文实验产物完整”。

---

## 6. 同一题的两种 prompt

以 `Prob009_popcount3` 为例。

Code completion 文件 [Prob009_popcount3_prompt.txt](dataset_code-complete-iccad2023/Prob009_popcount3_prompt.txt) 同时给自然语言和模块接口：

```verilog
A "population count" circuit counts the number of '1's ...

module TopModule (
  input [2:0] in,
  output [1:0] out
);
```

另有独立接口文件 [Prob009_popcount3_ifc.txt](dataset_code-complete-iccad2023/Prob009_popcount3_ifc.txt)，用于在模型只返回 body 时重新拼接完整模块。

Spec-to-RTL 文件 [Prob009_popcount3_prompt.txt](dataset_spec-to-rtl/Prob009_popcount3_prompt.txt) 改成抽象规格：

```text
implement a module named TopModule
- input in (3 bits)
- output out (2 bits)
implement a population count circuit
```

模型必须自己写：

- `module TopModule`；
- 端口声明；
- 类型与位宽；
- 模块主体；
- `endmodule`。

因此两任务题意相近，但模型自由度不同。

---

## 7. “两边题目相同”不等于文件逐字相同

[README](README.md) 说两种任务中的 problems identical，正确理解应是“同一组 156 个概念任务”，不是所有 golden/test 文件 byte-identical。

静态比较发现：

- 9 个 `_ref.sv` 不同；
- 7 个 `_test.sv` 不同。

9 个 reference 差异：

```text
Prob034_dff8
Prob092_gatesv100
Prob094_gatesv
Prob099_m2014_q6c
Prob113_2012_q1g
Prob116_m2014_q3
Prob135_m2014_q6b
Prob148_2013_q2afsm
Prob149_ece241_2013_q4
```

其中 7 个后者同时有 testbench 差异；`Prob034` 和 `Prob099` 当前只是 reference 精确内容不同。

---

## 8. 为什么 ref/test 会不同

差异多数用于适配 spec-to-RTL 更自然的 0-based、统一宽度接口。

例如：

- `Prob113` / `Prob116`：code completion 使用 `input [4:1] x`，spec-to-RTL 改为 `[3:0] x`；
- `Prob148`：`r[3:1]` / `g[3:1]` 改为 `[2:0]`，内部索引随之平移；
- `Prob149`：`s[3:1]`、`fr3/fr2/fr1` 改为 `s[2:0]`、`fr2/fr1/fr0`；
- `Prob092`：输出端口宽度与边界补零方式被重新定义；
- `Prob034`：code-completion reference 初值是 `8'hx`，spec-to-RTL reference 初值是 `8'h0`。

这意味着跨论文汇总时必须同时记录 task 类型。即便模型、采样参数相同，两个任务也不只是 prompt 文字变化，少数题的 oracle/interface 确实不同。

---

## 9. 论文所说的 14 题修订如何落到 Git 历史

论文说明 14 个问题的描述或 testbench 被修订，用于解决一致性或清晰度问题。本地 Git 历史可恢复当前版本涉及的 14 个 task ID：

```text
Prob034_dff8
Prob045_edgedetect2
Prob068_countbcd
Prob074_ece241_2014_q4
Prob079_fsm3onehot
Prob082_lfsr32
Prob086_lfsr5
Prob099_m2014_q6c
Prob104_mt2015_muxdff
Prob124_rule110
Prob134_2014_q3c
Prob143_fsm_onehot
Prob145_circuit8
Prob150_review2015_fsmonehot
```

对应提交：

```text
71f2df4  2024-09-17  修订 13 个任务的 prompt/testbench
3d683ab  2025-01-31  修订 Prob034 reference 与 ICL prompt
```

严格说，当前第 14 个 `Prob034` 改的是 reference 初值，不是 prompt/testbench；论文用“descriptions or test benches”作了较宽泛概括。报告 current-main 结果时应固定 commit，不能只写“VerilogEval v2”。

---

## 10. `configure` 决定实验矩阵

[configure.ac](configure.ac) 支持：

```text
--with-model
--with-examples
--with-rules
--with-task
--with-samples
--with-temperature
--with-top-p
--with-dataset
--with-problems
--with-pregen
```

默认值是：

| 参数 | configure 默认 |
|---|---|
| model | `gpt4-turbo` |
| examples | 0 |
| rules | no |
| task | `spec-to-rtl` |
| samples | 20 |
| temperature | 0.85 |
| top_p | 0.95 |

论文高温协议写的是 temperature 0.8，而 configure 和 README 使用 0.85；`sv-generate` argparse 默认又是 0.8。要复现论文，必须显式传 `--with-temperature=0.8`，不能依赖默认值。

---

## 11. Makefile 逐题调用链

[Makefile.in](Makefile.in) 对每题和每个样本展开规则：

```text
<Prob>_prompt.txt
    ↓ sv-generate --model --task --examples --temperature --top-p
<Prob>/<Prob>_sampleYY.sv
<Prob>/<Prob>_sampleYY-sv-generate.log
    ↓ iverilog -g2012 -s tb sample.sv test.sv ref.sv
<Prob>/<Prob>_sampleYY executable
    ↓ timeout 30
<Prob>/<Prob>_sampleYY-sv-iv-test.log
    ↓ sv-iv-analyze
summary.txt + summary.csv
```

关键命令关系：

```make
iverilog ... -s tb -o <sample> <sample>.sv <problem>_test.sv <problem>_ref.sv
timeout 30 ./<sample>
```

`make -j4` 可以跨题/样本并行；文件级依赖也支持中断后继续。

---

## 12. `sv-generate` 支持哪些模型

当前 [scripts/sv-generate](scripts/sv-generate) 把模型分成三类。

### OpenAI API

```text
gpt-3.5-turbo
gpt-4
gpt-4-turbo
gpt-4o
```

### NVIDIA NIM

包括 Llama2/3/3.1、CodeLlama、Gemma/CodeGemma、Mistral/Mixtral/Mistral Large。

### Manual

```text
manual-rtl-coder
manual-deepseek-coder-6.7b
manual-deepseek-coder-33b
```

Manual 模式不会在脚本内加载本地权重，而是：

1. 写 `<sample>_fullprompt.txt`；
2. 写 `<sample>_systemprompt.txt`；
3. 等用户/外部推理程序写 `<sample>_response.txt`；
4. 再解析 response 为 `.sv`。

所以它是“本地模型接入协议”，不是内置 inference backend。

---

## 13. API 依赖与一个实际入口限制

脚本在命令行解析前就导入：

```python
from langchain_nvidia_ai_endpoints import ChatNVIDIA
from langchain_openai import ChatOpenAI
```

这意味着即便只想：

```bash
scripts/sv-generate --list-models ...
```

也必须先同时安装两个 provider 包，否则在进入 `--list-models` 分支前就导入失败。

README 要求：

```text
langchain
langchain-openai
langchain-nvidia-ai-endpoints
```

API 模式还需相应凭据。仓库没有固定这些包的版本 lock，因此 2026 年按最新 LangChain 安装不一定兼容 2024 年接口。

---

## 14. Code completion prompt 是怎样构造的

脚本为题目增加固定 instruction，把自然语言描述逐行改成 `//` 注释，直到遇到精确子串：

```python
if "module TopModule" in line:
    prefix = False
```

然后保留 module header，发送给模型。

这个实现有两个边界：

- 依赖模块名与大小写精确为 `TopModule`；
- 如果自定义题使用别的模块名，描述与代码边界识别会失败。

模型按 system message 被要求只补 body，并以 `endmodule` 结束，不重复 module/port 定义。

---

## 15. Code completion response 后处理

脚本扫描：

- Markdown backticks 数量；
- 是否错误地重新输出 `module TopModule`；
- 是否找到 `endmodule`；
- `endmodule` 是否出现在 module 之前；
- response 中是否有多个代码区段。

如果模型没有重复 module header，就从对应 `_ifc.txt` 自动补接口；然后只写第一个有效区段，并增加诊断注释：

```text
VERILOG-EVAL: abnormal backticks count
VERILOG-EVAL: errant inclusion of module definition
VERILOG-EVAL: endmodule not found
```

`manual-rtl-coder` 还有特定修补，用于处理 `endmodule` 后粘连继续生成的情况。论文也说明 RTL-Coder 的结果使用了与其原评测脚本一致的 response extraction；这说明后处理本身是 benchmark 协议的一部分。

---

## 16. Specification-to-RTL prompt 与 response 提取

Spec-to-RTL 采用问答格式：

```text
Question:
<完整文字规格>

<可选 coding rules>

Enclose your code with [BEGIN] and [DONE].

Answer:
```

优先提取 `[BEGIN] ... [DONE]`；若模型没有遵守，再退回 Markdown fence / 普通 module completion 风格提取。

一个代码小瑕疵是，spec-to-RTL 分支最后会无条件写入：

```text
// VERILOG-EVAL: response did not use <CODE></CODE> correctly
```

即使 `[BEGIN]/[DONE]` 已正确解析，也会出现这条仍引用旧 `<CODE>` 标签的注释。它通常不影响 Verilog 编译，但日志含义会误导人工检查。

---

## 17. API 重试和失败边界

非 manual 模式最多重试 10 次，每次失败等待 20 秒：

```text
LLM call
  ├─ success → resp/callback
  └─ exception → sleep 20s，最多 10 次
```

若 10 次全部失败，代码随后仍访问 `resp.content` 和 callback 变量，可能触发未绑定变量异常，而不是生成结构化失败记录。

因此长规模 sweep 应额外做：

- API failure sentinel；
- 失败 sample 的明确状态文件；
- 可恢复重试；
- provider/model 版本记录；
- 避免把空/异常 response 误判成普通语法错误。

当前仓库这部分更像研究脚本，不是健壮的生产评测服务。

---

## 18. ICL 文件怎样组织

两种任务都有 1/2/3/4-shot 文件。论文主要解释前三个累加示例：

| shot | 新增示例 | 主要能力 |
|---:|---|---|
| 1 | 组合 incrementer | 简单接口与组合赋值 |
| 2 | 带同步 reset 的 registered incrementer | 时序逻辑与 reset |
| 3 | 两个连续 1 检测 FSM | 状态、next-state、输出逻辑 |

对应文件：

- [code completion 1-shot](scripts/verilog-example-prefix_code-complete-iccad2023_1-shot.txt)
- [code completion 2-shot](scripts/verilog-example-prefix_code-complete-iccad2023_2-shot.txt)
- [code completion 3-shot](scripts/verilog-example-prefix_code-complete-iccad2023_3-shot.txt)
- [spec-to-RTL 1-shot](scripts/verilog-example-prefix_spec-to-rtl_1-shot.txt)
- [spec-to-RTL 2-shot](scripts/verilog-example-prefix_spec-to-rtl_2-shot.txt)
- [spec-to-RTL 3-shot](scripts/verilog-example-prefix_spec-to-rtl_3-shot.txt)

当前 4-shot 文件不是简单在 3-shot 后再追加同一套第四例，而是使用 XOR、registered incrementer、参数化 incrementer、FSM 的另一组组合。做 0–4 shot sweep 时不要假设 prompt 是严格嵌套的。

---

## 19. 可选 coding rules

`--rules` 只在 spec-to-RTL prompt 分支加入规则，包括：

- 端口和信号尽量用 `logic`；
- 组合 always 用 `always @(*)`；
- 数值常量 size 必须大于 0；
- 无输入依赖时不要用永不触发的 always；
- 同步 reset 不应出现在 sensitivity list。

这些规则直接针对论文观察到的 Icarus 错误类型。

需要记录 rules 开关，因为它会改变：

- 语法错误分布；
- `wire/reg` 错误；
- sensitivity 错误；
- reset 错误；
- 最终 pass rate。

只报告 shot 数、不报告 rules，也不完整。

---

## 20. v2 的两种“pass@1”协议

论文不再报告 pass@5/pass@10，而是对 pass@1 用两种采样设置：

| 协议 | temperature | top_p | 每题 n | 含义 |
|---|---:|---:|---:|---|
| 低温 | 0.0 | 0.01 | 1 | 接近 deterministic/greedy 的单次成功率 |
| 高温 | 0.8 | 0.95 | 20 | 每题 20 次中通过比例，再跨题平均 |

v1 的 pass@1 无偏估计在每题恰好等于 `c/n`，所以高温协议用 20 次通过比例并称 pass@1 是数学上成立的。

但它与“20 次里只要一次通过就算成功”完全不同；后者更接近 pass@20。

---

## 21. 当前 analyzer 实际怎样算分

[scripts/sv-iv-analyze](scripts/sv-iv-analyze) 每题计算：

```python
pass_rate = int((npass/nsamples)*100)
```

然后对 156 个题的整数百分比做 macro average。

对论文设置：

- `n=20` 时每次通过是 5%，不会被整数截断；
- `n=1` 时是 0% 或 100%，也不会截断；
- 所以能复现论文 pass@1 口径。

但对任意 `n=3/6/7/...`，每题先 `int()` 会向下截断，再平均，产生系统性偏差。例如 1/3 会由 33.33% 变成 33%。因此当前 analyzer 不是通用 pass@k 实现，也不是任意 sample 数下的无损 pass-rate 汇总器。

---

## 22. 失败分类表与代码映射

![论文 Table 1：失败类别](figures/v2-paper-table1-failure-types.png)

当前代码输出：

| 码 | 代码条件 | 含义 |
|---|---|---|
| `.` | `Mismatches: 0 ...` | 通过 |
| `S` | 日志含 `syntax error` | 语法错误 |
| `C` | 其他包含 `error` 的编译错误 | 通用编译错误 |
| `c` | 无法绑定 `clk` | 缺失时钟端口 |
| `e` | assignment requires explicit cast | 显式类型转换问题 |
| `0` | numeric constant size 为 0 | 零宽常量 |
| `n` | always 无 sensitivity | 敏感列表问题 |
| `w` | declared here as wire | wire 当 reg 赋值 |
| `m` | Unknown module type | 缺少/错误 module |
| `p` | 其他 Unable to bind wire/reg | 端口/信号绑定失败 |
| `r` | 生成代码命中 reset 启发式 | 可能把同步 reset 写成异步 |
| `R` | 未归类运行失败/有 mismatch | 通用功能错误 |
| `T` | 日志含 TIMEOUT | 超时 |

代码还支持论文 Table 1 没有单独突出显示的 `0` 类。

---

## 23. 分类是按优先级的单标签，不是完整根因分析

`sv-iv-analyze` 从日志上到下匹配，命中某些类别立即 `break`。结果是每个 sample 只有一个标签。

例如一段代码可能同时存在：

- 缺 module；
- 错误端口；
- reset 语义错误；
- 功能不匹配。

但编译失败会阻止运行期检查，最终只能记录最先匹配的编译错误。论文 Figure 5 也提醒，堆叠柱应从下往上读：编译错误会遮蔽潜在运行错误。

因此“某类错误下降”可能有三种解释：

1. 真正被修复；
2. 被更早的另一类编译错误覆盖；
3. 通过编译后转化成运行 mismatch。

不能把错误柱状图当作独立多标签故障计数。

---

## 24. Reset 分类尤其是启发式

只有在日志没有明确分类时，analyzer 才扫描生成 Verilog 文本：

```text
posedge reset
negedge reset
posedge r)
```

命中就标记 `r`。

这无法理解题目规格，也没有 AST：

- 若题目本来要求异步 reset，可能误报；
- 若 reset 名称是 `rst_n`、`areset` 等，可能漏报；
- 注释或格式差异也可能影响匹配；
- 第三个模式只覆盖很特定的信号名。

所以 `r` 应解释成“疑似异步 reset 模式”，不是已证明的语义根因。

---

## 25. `count_failures.py` 的统计边界

[count_failures.py](count_failures.py) 用 pandas 汇总多个 `summary.csv`，但当前主线存在一个组合问题：

1. `sv-iv-analyze.write_csv()` 写 CSV 时没有 header；
2. `pd.read_csv()` 默认把第一行当 header；
3. 因而第一个 problem 的结果会从计数数据中消失；
4. 脚本注释说忽略前三列，实际 `df.iloc[:, 4:]` 忽略前四列；后者与当前 `problem,npass,nsamples,pass_rate` 四个元数据字段相符，注释本身不准确。

这不会改变 `summary.txt` 的总 pass rate，但会影响用该辅助脚本重画/重统计 failure counts。若要复核论文 Figure 5，应先显式给 `header=None` 和列结构，不能原样相信辅助输出。

---

## 26. 论文主结果：高温 n=20

Figure 3 给出 0-shot → 1-shot 的变化：

![Figure 3：code completion 与 specification-to-RTL](figures/v2-paper-fig3-primary-results.png)

完整 Table 2 同时包含低温和高温：

![Table 2：14 个模型完整结果](figures/v2-paper-table2-results.png)

下面只抽取高温 `T=0.8, n=20` 四个最常引用的数字：

| 模型 | Code 0-shot | Code 1-shot | Spec 0-shot | Spec 1-shot |
|---|---:|---:|---:|---:|
| GPT-4o | 56.1 | 60.7 | 61.4 | 62.6 |
| GPT-4 Turbo | 49.8 | 59.5 | 61.1 | 56.7 |
| GPT-4 | 41.6 | 50.1 | 31.7 | 51.4 |
| Mistral Large | 33.1 | 42.7 | 35.9 | 46.0 |
| Llama3.1 405B | 57.0 | 57.9 | 57.1 | 58.3 |
| Llama3.1 70B | 36.3 | 33.0 | 39.0 | 48.5 |
| Llama3 70B | 39.1 | 36.5 | 43.9 | 40.5 |
| Llama2 70B | 1.7 | 13.3 | 5.3 | 19.2 |
| CodeLlama 70B | 29.0 | 27.4 | 25.3 | 27.0 |
| DeepSeek Coder 33B | 29.3 | 37.5 | 19.5 | 38.1 |
| Llama3.1 8B | 4.9 | 12.8 | 16.8 | 26.5 |
| CodeGemma 7B | 8.7 | 16.2 | 9.5 | 22.2 |
| DeepSeek Coder 6.7B | 21.0 | 30.3 | 22.6 | 25.6 |
| RTL-Coder 6.7B | 31.5 | 32.6 | 30.9 | 33.5 |

这些全部是论文报告值，不是当前本地重跑值。

---

## 27. 如何读这张模型表

### 27.1 模型规模不是唯一因素

RTL-Coder 6.7B 在多个条件下接近或超过更大的通用代码模型，说明领域训练有效；但 Llama3.1 405B 的通用能力仍把开放模型前沿推到接近 GPT-4o。

### 27.2 Spec-to-RTL 不是对所有模型都更强

Instruction-tuned 模型往往受益，但 GPT-4 Turbo 的 1-shot spec 反而从 61.1% 降至 56.7%；CodeLlama 在两任务中 ICL 效果也弱或负。

### 27.3 1-shot 不是单调提升

Llama3 70B、Llama3.1 70B 的 code completion、GPT-4 Turbo 的 spec 都有下降。

### 27.4 后处理是结果的一部分

论文特别说明 RTL-Coder 会在 `endmodule` 后继续重复代码，作者调整提取脚本后才给出表中结果。比较其他项目时必须对齐 extraction policy。

---

## 28. 0–3 shot 的非单调现象

论文选 GPT-4o、Llama3.1 70B、Llama3 70B、RTL-Coder 6.7B 做更深 sweep：

![Figure 4：0–3 shot ICL](figures/v2-paper-fig4-icl.png)

主要趋势：

- GPT-4o 在 1–2 shot 保持高水平，3-shot 略回落；
- Llama3.1 70B 的 spec-to-RTL 随 ICL 明显提升，但 code completion 较平或下降；
- Llama3 70B 的 spec-to-RTL 后续改善，而 code completion 随 shot 增加明显下降；
- RTL-Coder 两任务较稳定，增益小但不剧烈崩溃。

结论不是“加更多示例”，而是“示例内容、任务格式和模型对齐方式需要联合调参”。

---

## 29. 两个 case study：同一个示例为何一好一坏

论文分析：

- `Prob009_popcount3`：3-bit population count，组合逻辑；
- `Prob034_dff8`：8 个正沿 DFF，时序逻辑。

Llama3 70B code completion：

```text
Prob009: 0-shot 0/20 → 1-shot 13/20
Prob034: 0-shot 20/20 → 1-shot 1/20
```

1-shot incrementer 对组合表达有帮助，却让 DFF 题出现严重模式复制/接口或输出结构问题。继续加示例也可能产生重复代码、错端口、额外 `endmodule` 等错误。

Llama3.1 70B 的另一组现象：

```text
0-shot: Prob009 0/20, Prob034 20/20
1-shot: Prob009 15/20, Prob034 20/20
2-shot: Prob009 12/20, Prob034 0/20
3-shot: Prob009 15/20, Prob034 20/20
```

2-shot 会让 `Prob034` 全部失败，但 3-shot 又恢复，说明错误不是随上下文长度平滑变化。

Llama3.1 405B 对这两题在各 shot 下均为 20/20，说明大模型更能区分“示例模式”和“当前任务约束”。

---

## 30. specification-to-RTL 的自由度既是优势也是风险

优势：

- 模型不用在给定 `wire/reg` 接口后硬接 body；
- 可自行选择 `logic`、`reg`、`always_comb` 等形式；
- 更符合 chat/instruction 模型训练格式；
- code completion 常见的“重复 module header”冲突减少。

风险：

- 可能改错端口名；
- 可能遗漏 clock/reset；
- 可能改变位宽和符号；
- 可能忘记 `TopModule`；
- 接口错误会在编译阶段遮住功能质量。

所以 spec-to-RTL 高分不一定说明“逻辑推理突然更强”，其中一部分来自 prompt 与 instruction tuning 更匹配、接口声明更自由。

---

## 31. Failure Figure 应怎样解释

![Figure 5：Llama 系列错误分类](figures/v2-paper-fig5-failures.png)

图中每个设置最多：

```text
156 problems × 20 samples = 3,120 failures
```

橙色为编译期、蓝色为运行期。论文观察包括：

- specification-to-RTL 往往减少 syntax 和 wire/reg 类错误；
- ICL 可能减少某类编译错误，却没有减少总失败；
- Llama3.1 70B 在 spec-to-RTL 随 ICL 增加总体明显改善；
- Llama3 70B 的 code completion 增加 ICL 后编译失败可能上升。

由于分类是单标签、且编译错误遮蔽运行错误，最可靠的用途是“定位 prompt 改动后错误分布发生了什么”，而不是声称已完成精确根因诊断。

---

## 32. 结果文件与可追溯性

每个 sample 理论上保留：

```text
ProbXXX/
├── ProbXXX_sampleYY.sv
├── ProbXXX_sampleYY-sv-generate.log
└── ProbXXX_sampleYY-sv-iv-test.log
```

生成日志包含：

- problem/model；
- temperature/top_p/max tokens；
- system prompt；
- full prompt；
- raw response；
- token/cost 信息。

汇总输出：

```text
summary.txt
summary.csv
```

这比 v1 的单个 JSONL 更适合人工定位具体题目。但当前本地仓库没有论文作者当年的这些输出，因此不能追溯 Table 2 每个百分比对应哪些 sample。

---

## 33. 当前代码的其他可复现性细节

### 33.1 Icarus 版本

README 指定 v12，并明确不支持开发版 v13。不同版本的 warning/error 文本会影响字符串分类。

### 33.2 Python 版本

作者环境写 Python 3.11，但没有完整 lockfile。

### 33.3 超时

每次 simulation 30 秒；超时记 `T`。

### 33.4 shell 与工具依赖

`configure.ac` 使用 `sed`、`column`；Makefile 使用 GNU make 的非标准特性、Bash `PIPESTATUS`、`seq`、`timeout`、`tee`、`rsync` 等，更偏 Linux/GNU 环境。

### 33.5 pregen

Makefile 设计了保存生成样本以避免重复 API，但当前 `pregen_dir` 处理存在硬编码/配置残留，使用前应核对生成后的 Makefile，而不是只看 configure 提示。

---

## 34. 不重新跑模型时，如何复用已有输出

如果项目中已有模型推理结果，正确做法是只转换成 v2 的 manual response 协议，而不是重新加载模型：

```text
已有 raw response
    ↓ 与 problem/sample ID 对齐
<sample>_response.txt
    ↓ sv-generate manual 模式做同一后处理
<sample>.sv
    ↓ 只在需要补评价证据且获得授权时离线 Icarus
summary
```

本次没有发现 VerilogEval 目录自身的 `_response.txt`、sample、summary 或日志，因此没有冒充已有结果，也没有为了填表新跑 API。

其他项目（如 AutoChip、VerilogCoder、MAGE）确有自己的 VerilogEval 结果与记录，但它们允许的反馈资源和后处理不同，不能直接算作这篇论文 Table 2 的本地复现。

---

## 35. 复现等级与缺失资产

### R0：论文数字

当前缺：

- 14 个模型的固定服务/checkpoint 版本；
- 全部 raw responses；
- API provider 版本与完整日志；
- 作者 build 目录；
- Table 2 / Figure 3–5 的机器可读原始数据；
- 随机种子/服务端采样确定性信息。

### R1：本地已完成

- 两篇 PDF 与 SHA256；
- current main、release branches/tags commit；
- 156×两套数据文件计数；
- cross-task ref/test 差异；
- 14 题修订 Git 证据；
- generation、Makefile、Icarus、analyzer 静态调用链；
- metric 和辅助统计脚本审计。

### 条件 R2：可进行但本次未执行

若用户提供已生成 responses、Icarus v12 和依赖，可离线重放后处理与仿真；若要重现论文模型数字，还需 API/权重与严格协议。

---

## 36. 与 agent 方法比较时必须对齐资源

论文后半部分讨论 RTLFixer、VeriAssist、AIvril、PromptV、VerilogCoder、MAGE 等。它们常用：

- testbench；
- compiler/simulator 错误；
- mismatch；
- VCD waveform；
- 多轮修改；
- 多 agent 候选和 judge。

而 Table 2 的单模型评价是单轮 prompt → response → test。即使都叫 VerilogEval pass@1，资源条件不同：

```text
单轮模型能力 ≠ 可访问验证反馈的 agent 闭环能力
```

例如论文引用 VerilogCoder/MAGE 超过 94–95%，不能直接说它们的基础 LLM 比 GPT-4o 强 30 个百分点；更准确是它们用验证工具与迭代预算提高了任务闭环成功率。

---

## 37. 论文与代码之间的关键偏差表

| 项目 | 论文 | 当前代码/README | 影响 |
|---|---|---|---|
| 高温 temperature | 0.8 | configure/README 0.85，argparse 0.8 | 必须显式固定 |
| shot 范围 | 主要 0–3 | 支持 0–4 | 4-shot 不属于主要图表协议 |
| pass@1 | c/n 的跨题均值 | 每题整数百分比后平均 | n=1/20 等价，其他 n 有截断 |
| 失败类别 | Table 1 十余类 | 额外有 `0` 类 | 代码比表多一类 |
| reset issue | 语义描述 | 字符串启发式 | 可能误报/漏报 |
| 14 题修订 | 描述或 testbench | current Git 第 14 题为 reference 初值修复 | 应按 commit 解释 |
| 数据相同 | 同一 156 概念任务 | 9 ref、7 test 非精确相同 | 不应跨 task 混算 |
| failure 汇总 | Figure 5 | `count_failures.py` 与无 header CSV 不完全匹配 | 重画前需修复读法 |
| 原始结果 | 论文图表 | 仓库不含 samples/logs | 不能本地追溯 |

---

## 38. 适合组会分享的结构

建议 15–18 分钟：

1. **2 分钟：v1 为什么不够**——只有 code completion、单一 pass/fail、JSONL 难看；
2. **3 分钟：Figure 2**——两个数据集、生成、Icarus、错误分类、Makefile；
3. **3 分钟：两种 prompt**——给接口补 body 与完整 spec-to-RTL；
4. **3 分钟：Figure 3/Table 2**——GPT-4o、Llama3.1 405B、RTL-Coder；
5. **3 分钟：Figure 4 与两个 case**——ICL 非单调；
6. **2 分钟：Figure 5**——错误分层、编译错误遮蔽运行错误；
7. **2 分钟：代码审计**——14 题、9/7 文件差异、temperature 默认、metric 截断；
8. **收束**——benchmark 也是软件系统，版本和实现细节会改变科学结论。

一句话标题：

> **Revisiting VerilogEval：模型进步之外，更重要的是 prompt、后处理、测试和错误分类共同定义了 RTL benchmark。**

---

## 39. 本地证据与链接

### 论文与总审计

- [Revisiting VerilogEval PDF](2408.11053_Revisiting_VerilogEval.pdf)
- [原版 VerilogEval PDF](2309.07544_VerilogEval.pdf)
- [static_audit_20260802.json](runs/static_audit_20260802.json)

### 主代码

- [README.md](README.md)
- [configure.ac](configure.ac)
- [Makefile.in](Makefile.in)
- [scripts/sv-generate](scripts/sv-generate)
- [scripts/sv-iv-analyze](scripts/sv-iv-analyze)
- [count_failures.py](count_failures.py)
- [pass_rate_to_csv.py](pass_rate_to_csv.py)

### 两套数据

- [dataset_code-complete-iccad2023](dataset_code-complete-iccad2023/)
- [dataset_spec-to-rtl](dataset_spec-to-rtl/)

### 代表题

- [Prob009 code prompt](dataset_code-complete-iccad2023/Prob009_popcount3_prompt.txt)
- [Prob009 interface](dataset_code-complete-iccad2023/Prob009_popcount3_ifc.txt)
- [Prob009 spec prompt](dataset_spec-to-rtl/Prob009_popcount3_prompt.txt)
- [Prob009 testbench](dataset_spec-to-rtl/Prob009_popcount3_test.sv)
- [Prob034 code reference](dataset_code-complete-iccad2023/Prob034_dff8_ref.sv)
- [Prob034 spec reference](dataset_spec-to-rtl/Prob034_dff8_ref.sv)

---

## 40. 最终判断

这篇论文值得分享，因为它把“模型更强了吗”拆成更精确的工程问题：

1. 模型面对 code completion 还是 specification-to-RTL；
2. prompt 是否带 ICL 与 coding rules；
3. response 怎样提取；
4. 编译/仿真怎样运行；
5. pass@1 在 n=1 和 n=20 下怎样统计；
6. 失败是语法、接口、reset、timeout 还是功能 mismatch；
7. benchmark 题和 testbench 是否修订过。

本地代码阅读进一步补出论文正文没有完全展开的事实：两种任务的概念题 ID 相同，但部分 reference/testbench 不同；当前 analyzer 只对论文 n=1/20 协议无损；错误分类是日志字符串和 source pattern 的单标签启发式；辅助 failure 汇总脚本还需修正无 header CSV 的读取方式。

因此最准确的复现结论是：**v2 benchmark 数据和评测流程的代码逻辑已经核清，具备条件离线重放；论文模型 outputs 未开源，本地也没有对应运行记录，所以不把论文表格声明为已复现。**

