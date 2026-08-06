# RealBench：真实 IP 级 Verilog 生成基准——论文、代码与本地复现详解

> 论文：**RealBench: Benchmarking Verilog Generation Models with Real-World IP Designs**  
> 本地论文：[2507.16200_RealBench.pdf](./2507.16200_RealBench.pdf)  
> arXiv：<https://arxiv.org/abs/2507.16200>；PDF：<https://arxiv.org/pdf/2507.16200>  
> 代码：<https://github.com/IPRC-DIP/RealBench>；数据页：<https://huggingface.co/datasets/Pengwei-Jin/RealBench>  
> 本地代码版本：commit `9bc9a6ac058b`；MIT License  
> 核对日期：2026-08-02

---

```text
┌─────────────────────────────────────────────────────────────────────────┐
│ P1 任务定义                                                              │
├─────────────────────────────────────────────────────────────────────────┤
│ Input:  真实开源 IP 的详细设计规格（文本+表格+图片）+ 模块级或系统级任务  │
│         描述 + 可选 golden submodule 依赖                                 │
│ Output: 单模块 RTL 或完整系统 RTL、Verilator 编译/功能 testbench 结果、   │
│         可选的 Yosys + JasperGold 形式等价证明                            │
│ Supervision: 功能验证使用 100% reference line coverage testbench；形式 │
│              验证使用 Yosys 综合 + JasperGold SEC；无人工逐题评分          │
│ Why-hard: 规格长、层级深、子模块依赖多；真实 IP 子模块接口易错；formal  │
│           工具需商业许可证；系统级任务当前所有模型功能/形式通过率为 0；     │
│           依赖 Verilator/Yosys/JasperGold 完整工具链                     │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 1. 结论先行：为什么它很值得组会分享

RealBench 的核心问题不是“LLM 会不会写一个小模块”，而是：

> 当输入变成真实 IP 设计文档，电路出现多层子模块依赖，验证从几个 directed tests 升级到 100% reference line coverage 与形式等价时，现有 Verilog LLM 还剩多少真实能力？

答案非常尖锐：论文中表现最好的 `o1-preview` 在 60 个模块级任务上的 `formal@1` 只有 **13.3%**，四个系统级任务的 `func@1/func@5/formal@1/formal@5` 全部是 **0**。

它最值得分享的三点是：

1. **任务更接近真实 IP**：AES 加/解密、SD 卡控制器、Hummingbirdv2 E203 CPU，不是平坦教学题；
2. **规格更接近工程文档**：接口表、寄存器、框图、数据流、状态机、子模块、corner case、约束并存；
3. **验证更严格**：功能 testbench 之外，Yosys 把 reference/candidate 综合成网表，再用 JasperGold 做形式等价。

本地当前状态也必须说清楚：**规格解密、60 个模块题 + 4 个系统题生成、60 个 agent 任务目录构建均已实际跑通；本机没有 Verilator/Yosys，且 JasperGold 是商业工具，因此论文表格尚未本地复现。**

---

## 2. 论文定位与任务定义

论文是 2025 年 7 月的 arXiv v1。它把 Verilog 生成任务形式化为：

```text
详细设计规格（文本 + 表格 + 图片）
  -> LLM / Agent
  -> 单模块 RTL 或完整系统 RTL
  -> 语法检查
  -> 100% reference line coverage testbench
  -> 形式等价检查
```

与 VerilogEval、RTLLM 等 benchmark 的最大差别，是 **输入、输出和 oracle 同时变复杂**：

- 输入从短描述变成长设计文档；
- 输出从几十行孤立模块变成几百行、带子模块依赖的 RTL；
- oracle 从仿真样例扩展到形式等价。

---

## 3. 与已有 benchmark 的量级差异

![RealBench 论文 Table I：设计、规格与验证质量对比](./figures/paper-table1-benchmark-comparison.png)

论文 Table I 报告：

| Benchmark | 设计数 | 平均代码行 | 平均 cell | 平均子模块 | 平均文档行 | 多模态 | line coverage | formal |
|---|---:|---:|---:|---:|---:|---|---:|---|
| VerilogEval-human | 156 | 15.8 | 31.4 | 0 | 5.7 | 否 | 99.7% | 否 |
| RTLLMv2 | 50 | 46.1 | 33.7 | 0.2 | 20.8 | 否 | 96.0% | 否 |
| ChipGPTV | 33 | 51.2 | 18.0 | 0.6 | 12.5 | 是 | 96.9% | 否 |
| RealBench-module | 60 | 241.2 | 0.52K | 1.6 | 197.3 | 是 | 100% | 是 |
| RealBench-system | 4 | 3537.3 | 1.1M | 14.5 | 2.9K | 是 | 100% | 是 |

论文据此总结，RealBench 相比此前 benchmark 平均有约：

- `4.3×` 代码行；
- `10.8×` circuit cells；
- `2.7×` 子模块实例；
- `8.8×` 文档长度。

这里的 60 与 4 是两种任务视角，不是 64 个互不相关 IP：60 个模块来自四个 IP，四个 system task 是把其中的层级规格整体交给模型。

---

## 4. 四个真实 IP 与层级结构

### 4.1 IP 组成

RealBench 以四个真实开源 IP 为基础：

| IP | 本地目录 | 模块数 | 典型难点 |
|---|---|---:|---|
| AES encoder | `aes/` | 与 decoder 共 6 个去重模块 | S-box、轮密钥、轮变换、子模块连接 |
| AES decoder | `aes/` | 与 encoder 共用部分模块 | 逆 S-box、逆轮变换、控制时序 |
| SD card controller | `sdc/` | 14 | Wishbone、FIFO、CRC、跨时钟域、多 FSM |
| Hummingbirdv2 E203 CPU | `e203_hbirdv2/` | 40 | 取指、译码、ALU、CSR、LSU、总线、层级宏定义 |

代码中的 `benchmark_info.py` 明确记录每个目标模块需要哪些 golden 子模块。例如：

```text
aes_cipher_top
  -> aes_key_expand_128
  -> aes_sbox

e203_core
  -> e203_ifu
  -> e203_exu
  -> e203_lsu
  -> e203_biu
```

这份依赖图既参与 problem 构建，也决定模块级验证时应带哪些已知正确的 dependency RTL。

### 4.2 为什么子模块是主要失败源

平坦题只需实现一个输入输出映射；层级题还必须同时做到：

1. 正确理解子模块接口；
2. 实例名、端口名、方向、位宽匹配；
3. 时序、reset、valid/ready 等协议一致；
4. 宏定义与参数传播正确；
5. 系统级任务还要自己实现所有下层模块。

论文 Table IV 报告，不带子模块任务的 `formal@1` 平均比带子模块任务高 13.0 个百分点；DS-V3-671B 的差距最大，达到 20.9 个百分点。

---

## 5. 设计规格不是普通 prompt

![RealBench 论文 Figures 1–4：真实代码/规格与严格验证对比](./figures/paper-fig1-fig4-design-spec-verification.png)

论文作者不是直接使用开源项目原有文档，而是人工重写规格，目标是让另一位工程师只看规格就能重新实现模块。每份模块规格通常包含：

1. Introduction / 模块总功能；
2. Block Diagram；
3. I/O Interface 表；
4. clock 与 reset 行为；
5. registers；
6. detailed operation principle；
7. data flow / state transition；
8. submodule 信息；
9. corner cases；
10. constraints。

本地已解密的 `aes/aes_cipher_top/aes_cipher_top.md` 就按这个结构展开，并引用真实规格图：

![RealBench AES cipher 数据流图（仓库规格素材）](./aes/aes_cipher_top/figures/aes_cipher_topdataflow.png)

这与一句“实现 AES”有本质区别：模型必须在长上下文中保持接口、状态、轮数、矩阵排列和多个子模块的一致性。

### 5.1 规格与 testbench 的协同设计

论文不是先写规格、再独立写 testbench，而是人工分析 reference RTL 的关键功能点：

```text
reference RTL 功能点
  -> testbench stimulus / checker
  -> 检查 line coverage
  -> 把必须满足的功能细节反写进 specification
```

这减少了“测试了但题目没说”和“题目说了但没测试”两类 benchmark 缺陷。

### 5.2 层级信息隔离

每个模块只提供当前层需要的信息，不允许无关的跨层细节泄漏。模块级任务允许使用已正确实现的 submodule；系统级任务则提供全层级规格，让模型从头生成全部实现。

---

## 6. 数据防污染机制：GPG 不是装饰

所有模块规格默认以 `.md.gpg` 保存，避免普通 GitHub crawler 直接把 benchmark 规格抓进训练集。仓库 Makefile 给出：

```bash
make decrypt
make clean_encrypt
```

口令写在 Makefile 中，目标是阻挡自动爬取而不是密码学保密。论文还要求训练方法统一去污染：

- 用 Rouge-L 衡量训练样本与 RealBench 的相似度；
- `β = 1.0`；
- 删除 Rouge-L 大于 `0.5` 的训练样本。

这不能完全排除模型曾见过原始开源 RTL，但至少把“规格文档直接进入后续训练集”的风险显式化。

---

## 7. 模块级与系统级：oracle 不同

### 7.1 Module-level

```text
当前模块规格 + 子模块接口/说明
  -> 生成当前模块
  -> 验证时挂接 golden dependency modules
  -> 当前模块 testbench
  -> 当前模块 formal equivalence
```

这种设置模拟工程师在已有模块库之上实现一个新模块，不把下层模块的错误归到当前任务。

### 7.2 System-level

```text
整个系统所有层级规格
  -> 从头生成 top + 全部 submodules
  -> system-level testbench
  -> system-level formal equivalence
```

验证只看系统外部行为，不强求内部结构与 reference 完全相同。但由于输出规模达到数千行、依赖十几个模块，论文中所有模型的系统功能和形式指标都是 0。

---

## 8. 三层验证闭环

### 8.1 Syntax

`run_verify.py::testbench_verification(...)` 把候选写到临时目录中的 `<module>_top.sv`，执行模块 `verification/Makefile`：

```text
verilator --cc --exe --binary --trace --assert
          --coverage-line --timing --top tb ...
  -> obj_dir/Vtb
  -> simulation
  -> verilator_coverage annotate
```

stderr 中出现 `%Error` 或 `%Warning` 时，旧版脚本把 syntax 和 function 都置 0。

### 8.2 Function

testbench 同时实例化：

```text
stimulus_gen
  -> ref_<module> 产生 golden output
  -> candidate <module> 产生 DUT output
  -> 比较每个输出
  -> 打印 Hint: Output ... mismatches / no mismatches
```

脚本解析 stdout 的 `Hint: Output` 行，只要存在 mismatch 就判功能失败。

### 8.3 Formal

`formal_verification(...)` 的代码链是：

```text
reference RTL --Yosys synth--> a.v
candidate RTL --Yosys synth--> b.v
  -> top.f / ref.f
  -> JasperGold SEC test.tcl
  -> 解析 jgproject/jg.log 的 proven / cex / determined 状态
```

形式检查只对已通过功能 testbench 的候选运行。返回值中：

- `1 = proven`；
- `0 = cex / cex_threshold_reached`；
- 负数表示网表生成、工具启动等基础设施失败；
- 其他正值对应 determined/skipped/未知状态，聚合时不当作 `formal==1`。

论文 Figure 3 的关键观点是：100% reference line coverage 仍不等于等价性证明。

---

## 9. pass@1 / pass@5 怎样计算

论文对多数模型设置：

- temperature `0.2`；
- 每题采样 20 次；
- 根据 20 次样本估计 metric@1 与 metric@5；
- o1-preview 因成本高只采样 1 次，所以没有可靠的 @5。

代码使用：

\[
\mathrm{pass@k}=1-\frac{\binom{n-c}{k}}{\binom{n}{k}}
\]

三类 metric 分别为：

- `syntax@k`：至少一个采样能通过 Verilator 编译；
- `func@k`：至少一个采样通过 testbench；
- `formal@k`：至少一个采样形式等价 proven。

当 `num_samples < 5` 时，README 明确警告 metric@5 不可靠。

---

## 10. 论文主结果与正确解读

![RealBench 论文 Table III 与 Figure 6：模型结果和层级失败分布](./figures/paper-table3-main-results.png)

### 10.1 模块级结果

部分关键数字：

| 模型 | syntax@1 | func@1 | formal@1 | formal@5 |
|---|---:|---:|---:|---:|
| o1-preview | 28.3 | 13.3 | 13.3 | — |
| DeepSeek-V3-671B | 24.9 | 12.8 | 10.8 | 14.2 |
| DeepSeek-R1-671B | 13.4 | 8.0 | 7.8 | 15.4 |
| GPT-4o | 24.5 | 10.9 | 8.8 | 12.4 |
| GPT-4o-V | 29.3 | 13.5 | 11.7 | 13.3 |
| RTLCoder-DS-6.7B | 10.9 | 3.4 | 2.0 | 3.6 |
| CodeV-QW-7B | 3.6 | 0.3 | 0.0 | 0.0 |

这里最重要的不是谁第一，而是：

- 很多模型在简单 benchmark 上 60%–80% 的功能通过率，到真实 IP 任务只剩个位数或十几个百分点；
- reasoning model DeepSeek-R1 相比同规模 V3 在 RealBench `formal@1` 反而下降 3.0 个百分点；
- 论文观察到 R1 会在复杂长任务中产生虚构模块头等低级 hallucination；
- GPT-4o-V 对 GPT-4o 的提升很小，说明“支持图片”不等于能稳定理解多张复杂工程图。

### 10.2 系统级结果

系统级仅语法有非零结果，例如 DeepSeek-V3 `syntax@1=41.3%`、GPT-4o-V `38.8%`；但所有模型：

```text
func@1 = func@5 = formal@1 = formal@5 = 0
```

这表明输出“看起来像一个大系统、甚至能编译”与“真实满足系统规格”差距极大。

### 10.3 testbench 与 formal 的差距

论文用 GPT-4-Turbo 在 RTLLMv2 上重新检查，发现原本通过 testbench 的候选中，相对 **44.2%** 不能通过形式验证。RealBench 自身也存在 `func@1 > formal@1` 的差距。

因此组会中不能把“仿真通过”直接说成“完全正确”；更准确的是“在给定 stimulus/oracle 下未发现错误”。

---

## 11. Agent 闭环：论文版本与仓库新版要分开

### 11.1 论文中的 self-reflection agent

![RealBench 论文 Figure 5：self-reflection agent](./figures/paper-fig5-self-reflection.png)

```text
规格
  -> LLM 生成 RTL
  -> syntax checker
  -> testbench
  -> formal checker
  -> 把错误反馈给同一个模型
  -> 修复并再次验证
```

论文还评估 VerilogCoder 多 agent：planner 制定计划，多个角色分步生成，再用语法、仿真和 AST waveform tracing 调试。公平设置为 GPT-4o base、4 小时上限，只保留前 6 份 RTL。

论文发现：简单 reflection 在模块级随迭代提高，但系统级仍为 0；VerilogCoder 在 RealBench 上不稳定，代码随迭代变复杂时 syntax 甚至下降。

![RealBench 论文 Figure 7 与 Table IV：agent 迭代和失败因素](./figures/paper-fig7-table4-analysis.png)

### 11.2 仓库新增的 Claude Code runner

`realbench_release/` 是一套更工程化的后续 runner：

```text
stage 0  mk_bench：从解密规格构造 60 个任务目录
stage 1  Docker 内运行 Claude Code + claude-trace
stage 2  collect：收集 <module>.v 到 aes/sdc/e203 JSONL
stage 3  独立 Docker：挂只读 benchmark oracle，运行 Verilator，生成 Markdown report
```

它不等同于论文原始模型结果，文档中提到的 `claude-sonnet-4-6` 等也不是论文 Table III 的模型。使用它应作为“新的 agent 实验”，不能写成“复现论文 Claude 结果”。

### 11.3 隔离设计核对

新版 `mk_bench` 的实际代码：

- 不复制 `verification/` 中的目标 `.sv` reference/testbench/stimulus；
- 会复制 `Makefile` 和 `.v` dependency modules；
- 复制解密后的目标规格到 `doc/`；
- 生成 `task.md` 要求 agent 写目标 RTL 和自己的 testbench。

这符合论文模块级任务允许使用 golden submodule 的定义。代码注释中“任务目录不应有任何 `.v`”过于绝对：实测 60 个 scaffold 共复制 354 个 `.v` dependency 文件；它们是允许的下层模块，而目标 golden 在 `.sv` 中被跳过。`start_container.sh` 的兜底守卫会因任何 `.v` 而拒绝部分合法任务目录，和 `mk_bench` 的行为存在冲突，正式跑前应修正为只检查目标模块答案泄漏。

---

## 12. 本地实际完成的复现步骤

结构化记录：[runs/data_preparation_20260802.json](./runs/data_preparation_20260802.json)。

### 12.1 规格解密：通过

仓库 72 份 `.md.gpg` 已解密为 `.md`，加密原件保留。本环境默认 home 只读，因此使用临时 `GNUPGHOME` 和 GPG loopback pinentry；这是环境适配，不改变明文内容。

### 12.2 problem generation：通过

运行：

```bash
python generate_problem.py --task_level module
python generate_problem.py --task_level system
```

得到：

| 输出 | 条数 | 本地文本字符数 |
|---|---:|---:|
| `problems/aes/problems.jsonl` | 6 | 36,035 |
| `problems/sdc/problems.jsonl` | 14 | 228,199 |
| `problems/e203_hbirdv2/problems.jsonl` | 40 | 1,858,403 |
| `problems/system/problems.jsonl` | 4 | 1,009,329 |

E203 module problem 特别长，是因为 `generate_problem.py` 会把 `e203_defines.md` 和 `config.md` 附加到每个 E203 规格；system problem 又会拼接整个依赖树所有规格。

### 12.3 agent task scaffold：通过

`realbench_release/evaluation.py mk_bench` 在临时目录成功生成 60 个 task dir。每个 task 包含：

```text
task.md
doc/<module>.md
Makefile
允许的 dependency .v（若需要）
```

没有复制目标 `.sv` golden oracle。

### 12.4 尚未运行

| 阶段 | 状态 | 原因 |
|---|---|---|
| Verilator syntax/function | 未跑 | 当前 host 无 `verilator`；论文固定版本为 5.030 |
| Yosys synthesis | 未跑 | 当前 host 无 `yosys`；论文环境写 0.55 |
| JasperGold formal | 未跑 | 商业工具未安装，开源仓库不能替代其许可证 |
| Claude Code agent | 未跑 | 需要用户授权的模型 API 与 Docker daemon 权限 |
| 论文 20 samples/model | 未跑 | 需模型版本、预算与完整验证工具链 |

所以当前复现等级是 **C+：数据、规格与任务生成链已复现，模型和验证结果未复现**。

---

## 13. 代码审计发现的其他边界

### 13.1 旧版验证临时目录写死

`run_verify.py` 使用：

```python
tempfile.TemporaryDirectory(dir=f"/run/user/{os.getuid()}")
```

某些容器或批处理节点没有该目录，会在调用 Verilator 前失败。新版 `realbench_release/evaluation.py` 已改为系统默认临时目录，移植性更好。

### 13.2 stderr 判错过严

旧版只要 Verilator stderr 非空就提前失败，再从其中抽 `%Error/%Warning`。某些非错误诊断也可能写入 stderr。更稳妥的判定应同时检查 return code、分类后的 error/warning 和仿真输出。

### 13.3 形式验证不可完全开源复现

前处理 Yosys 是开源的，但最终 equivalence checker 是 Cadence JasperGold。没有商业许可证只能复现 testbench 层，或者另建 Yosys EQY/SymbiYosys 等开源对照实验；后者是“替代实验”，不能宣称与论文 formal 指标完全一致。

### 13.4 100% line coverage 的含义

它只说明 reference RTL 每行被触发，不保证：

- 每个输入组合都测试；
- 每个状态转移及跨周期关系都充分覆盖；
- candidate 的额外错误逻辑一定被触发；
- testbench oracle 自身没有 bug。

这也是论文继续增加形式等价的原因。

### 13.5 bundled model samples 可用于复查，但不是本地日志

仓库 `samples/` 含多个模型的 JSONL，总计 11,584 条记录；多数模型是 60 模块 × 20 samples + 4 system × 20 samples，o1-preview 每题只有 1 条。它们是作者发布的模型输出，可以重新送入验证器，但不能当作当前机器已经跑出的结果。

---

## 14. 推荐复现路线

### 路线 A：先复现公开 testbench 指标

1. 建 `conda_env.yml` 指定的 Python 3.10 / Verilator 5.030 / Yosys 0.55 环境；
2. 选 bundled sample 中的 AES 六个模块；
3. 单进程验证，核对 syntax/function 分类；
4. 扩到 SD，再扩到 E203；
5. 用 20 samples 重新聚合 pass@1/pass@5；
6. 保存每题 stdout/stderr、工具版本和耗时。

### 路线 B：形式指标

1. 用 reference/reference 做正例，必须 `proven`；
2. 人工注入一处可综合功能 bug，必须返回 cex；
3. 固定 Yosys 和 JasperGold 版本；
4. 再批量检查功能通过候选；
5. 论文结果与本地结果逐模型对齐。

### 路线 C：新 agent 实验

1. 先跑 `mk_bench`；
2. 修复 `.v` dependency 守卫冲突；
3. 单任务 `aes_sbox` 验证 API、trace 与隐藏 oracle 隔离；
4. 固定模型名、API date、budget、effort、timeout；
5. 扩到 60 个模块；
6. 结果单列为“Claude Code agent on RealBench”，不要混入论文 Table III。

---

## 15. 组会讲法建议

### 一句话

> RealBench 证明了小型 RTL benchmark 上的高通过率不能直接外推到真实 IP：当规格长、层级深、子模块多且增加形式验证时，最强模型的模块级 formal@1 也只有 13.3%，系统级功能通过率为 0。

### 建议顺序

1. Table I：为什么已有 benchmark 太简单；
2. Figures 1–2：真实 RTL 与真实规格长什么样；
3. Figure 3：为什么 100% line coverage 后还要 formal；
4. Table III：模型在简单题和 RealBench 上的断崖；
5. Figure 6 / Table IV：子模块、FSM、长输入输出为什么难；
6. Figure 7：agent 反思有帮助，但复杂多 agent 不会自动解决真实 IP；
7. 本地代码：展示 60+4 problem 构建已跑通，以及验证工具链边界。

### 最值得讨论的问题

- 商业 formal oracle 会不会限制 benchmark 的可重复性？
- reference line coverage 与 candidate 行为覆盖怎样统一？
- system task 是否应该分阶段评分，而不是全有或全无？
- golden dependency 提供多少才既真实又不泄漏？
- 多模态模型究竟理解了图，还是主要依赖长文本？

---

## 16. 最终判断

| 维度 | 结论 |
|---|---|
| 论文分享价值 | 很高：真实 IP、层级生成、严格验证，结论有冲击力 |
| 代码/数据完整度 | 高：规格、RTL、testbench、样本、脚本齐；formal 工具许可证不开放 |
| 本地已复现 | 规格解密、60+4 problem 生成、60 个 agent task scaffold |
| 本地未复现 | Verilator/Yosys/JasperGold、模型采样、论文聚合指标 |
| 当前证据等级 | C+ |
| 与 GenBen 的关系 | GenBen 强在跨任务与 QoR；RealBench 强在真实 IP 层级、规格质量和 formal oracle |
| 后续优先级 | 很高，可作为下一次组会的 benchmark 主线论文 |

RealBench 最重要的启示是：**RTL 生成研究的瓶颈已经不只是模型能否写出语法正确的代码，而是能否在长规格、层级依赖和严格 oracle 下保持端到端一致性。**

---

## P7 关键组件一句话总结

| 组件 | 一句话总结 |
|---|---|
| RealBench-module / -system | 60 个模块级 + 4 个系统级任务，来自 AES、SD 卡控制器、Hummingbirdv2 E203 三个真实 IP。 |
| detailed design spec | 人工重写的长文档，含接口表、寄存器、框图、数据流、状态机、子模块和 corner case。 |
| dependency scaffolding | 模块级任务允许使用 golden submodule，系统级任务要求从头生成全部层级。 |
| Verilator testbench | 用 100% reference line coverage 的定向/随机激励比较 candidate 与 reference 输出。 |
| Yosys synthesis | 将 reference 与 candidate 分别综合为网表，为 JasperGold 形式等价检查做准备。 |
| JasperGold formal equivalence | 商业 SEC 工具判定 candidate 网表是否与 reference 网表行为等价。 |
| self-reflection agent | 将 syntax/testbench/formal 错误反馈给模型迭代修复，但系统级仍无法突破 0。 |

---

## 讨论问题

1. 100% reference line coverage 仍不等于形式等价，RealBench 为何仍同时保留两者？它们各自的优缺点是什么？
2. 系统级任务目前所有模型 func/formal 通过率为 0，应如何拆分评分或设计渐进式子任务来推动研究？
3. JasperGold 是商业工具，限制 benchmark 的可重复性；能否用 Yosys EQY/SymbiYosys 建立开源替代 oracle，同时保持与论文指标的可比性？
