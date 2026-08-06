# ROME：层次化 RTL 生成、工具反馈、代码与复现证据详解

> 论文：**Rome was Not Built in a Single Step: Hierarchical Prompting for LLM-based Chip Design**  
> 方法名：ROME，Recurrent Optimization via Machine Editing  
> 会议：MLCAD 2024；本地 PDF 标注 V1.1、Artifacts Available、arXiv v3  
> 本地论文：[2407.18276_ROME.pdf](./2407.18276_ROME.pdf)  
> 官方代码：<https://github.com/ajn313/ROME-LLM>  
> 本地代码：commit `a39593820833c14568d74e678d534cde6af196e0`，2026-06-05  
> 静态审计：[runs/static_audit_20260802.json](./runs/static_audit_20260802.json)  
> 核验日期：2026-08-02

---

```text
┌─────────────────────────────────────────────────────────────────┐
│ P1 任务定义                                                        │
├─────────────────────────────────────────────────────────────────┤
│ Input      │ 自然语言顶层设计目标 + 子模块层次/接口 + 每模块 unit testbench│
│            │ （HDHP：人工给层次；PGHP：仅顶层描述，由模型自发生成层次）   │
├─────────────────────────────────────────────────────────────────┤
│ Output     │ 一组层次化 Verilog 子模块及顶层，能在 Icarus/VVP 下编译并     │
│            │ 通过各自 testbench                                             │
├─────────────────────────────────────────────────────────────────┤
│ Supervision│ Icarus 编译/仿真返回码与 stderr 错误信息 + stdout pass marker │
├─────────────────────────────────────────────────────────────────┤
│ Why-hard   │ 复杂 RTL 一次性生成容易超长/丢失目标/接口错乱；需要把架构分解、│
│            │ 子模块局部错误修复与顶层集成串成可执行反馈链                 │
└─────────────────────────────────────────────────────────────────┘
```

## 0. 先给结论

ROME 解决的是复杂 RTL 不能稳定“一次写完”的问题。它不训练一个新模型，而是把硬件设计拆成层次化子模块，对每个子模块执行：

```text
层次计划
  → 逐模块生成
  → Icarus 编译/仿真
  → 错误反馈给 LLM 修复
  → 当前模块通过后进入下一层
  → 最终顶层集成与验证
```

论文区分两种 hierarchy 来源：

- **HDHP**：Human-Driven Hierarchical Prompting，人先给出层次与模块接口；
- **PGHP**：Purely Generative Hierarchical Prompting，LLM 自己从顶层需求提出层次。

核心结果不是“某模型绝对分数最高”，而是论文 Table 1 中 8 个模型在 6 个复杂 benchmark 上，层次提示相对非层次提示都获得改善；层次提示还减少反复生成长代码的时间与 token 成本。

但当前仓库与论文 artifact 有明显时间漂移：

| 维度 | 论文 | 当前 notebook |
|---|---|---|
| 模型 | 2024 年 8 个模型，含 GPT-3.5/GPT-4 和 6 个开放模型 | 默认 `gpt-5.2`，另有 Claude/Gemini wrapper |
| benchmark | 6 个层次 benchmark | 13 个 testbench 家族、92 个 `.v` testbench |
| 论文批量评价 | 每组合 n=10、pass@1/pass@5、时间 | 没有论文表格复算器 |
| relay prompt | 最近一层给完整代码，更早层压成实例/接口 | 当前把所有先前模块完整代码放进 prompt |
| 保存输出 | 论文有结果 | 当前仓库无生成 RTL、日志或结果表 |

本次没有调用任何 LLM，也没有重新跑仿真。原因不是“没看代码”，而是用户要求优先使用已有运行记录；当前目录又没有论文期输出，且当前默认模型已经不是论文模型。随便重跑 `gpt-5.2` 只能形成新实验，不能复现 Table 1。

综合复现等级：**R1**。论文方法、结果、当前 notebook 和 92 个 testbench 已静态核对；论文 n=10 生成、VCS/综合或 processor case study 均未本地重现。

---

## 1. 论文身份与研究位置

论文作者 Andre Nakkab、Sai Qian Zhang、Ramesh Karri 和 Siddharth Garg，发表于 MLCAD 2024，共 11 页。

本地 PDF 核验：

| 字段 | 值 |
|---|---|
| 文件 | `2407.18276_ROME.pdf` |
| 页数 | 11 |
| SHA-256 | `010f12fbfe81bdfa977152d1ab8cf8d1bac84a33eec8c6be6d632d6f9c304d4b` |
| 文档标识 | V1.1、Artifacts Available、arXiv v3 |

它在 RTL 生成谱系中的位置是：

```text
flat prompt / 单模块补全
        │
        ▼
层次计划 + 单元测试
        │
        ▼
逐层生成 + 工具反馈修复
        │
        ▼
复杂多模块顶层集成
```

与 RTLLM self-planning 的区别是，ROME 不只“先想计划再写一份 RTL”，而是真正让子模块逐一进入编译/仿真反馈环。

与 AutoChip 的区别是，ROME 把层次顺序和已有子模块上下文当作一等对象，而不是对单个完整 DUT 反复修复。

---

## 2. 为什么 flat prompting 容易失败

论文指出复杂硬件一次性生成面临：

- 输出代码过长；
- LLM 在长 completion 中丢失原始目标；
- 容易生成无关模块或 testbench；
- 接口、层次与状态逻辑同时出现时更容易 hallucinate；
- output token limit 可能截断；
- 修复一处时破坏另一处；
- 对 rare syntax 可能陷入重复错误模式。

硬件工程师通常不会把 AES、UART 或 systolic array 当作一个无结构 always block 来写，而会先建立 S-box、round、buffer、controller、PE 等层次。

ROME 的假设是：

```text
LLM 对“小而明确的局部模块”更可靠
+ 每层有可执行 unit test
+ 下一层可复用已验证模块
= 更容易得到最终复杂设计
```

---

## 3. 官方方法图

![ROME 自动层次提示与工具反馈流程](./supplements/flowchart.png)

> 图 1：仓库 `supplements/flowchart.png`，对应论文 Figure 1 的自动层次提示 pipeline。图中 1–8 分别表示层次 prompt、LLM 生成、testbench/simulation、错误格式化回灌、无错误后记录当前层、进入下一子模块，最终输出层次模块。

图中存在两个循环：

```text
内循环：
当前子模块 → 编译/仿真 → 错误反馈 → 修复当前子模块

外循环：
当前子模块通过 → 记录 HDL hierarchy step → 生成下一子模块
```

这就是“Recurrent Optimization via Machine Editing”的实际含义：机器执行结果不断编辑当前生成物，同时成功的模块成为下一层的上下文。

---

## 4. 两种 hierarchy 来源

### 4.1 HDHP：人给层次

用户提供：

- 顶层目标；
- 有顺序的子模块清单；
- 每个模块的名字；
- I/O 接口；
- 每个子模块 unit testbench；
- 顶层 testbench。

LLM 负责实现各模块，但人已经完成了架构分解。

论文 benchmark 默认采用 HDHP，因为只有固定 hierarchy 才能预先写好每个子模块的 unit test。

### 4.2 PGHP：LLM 给层次

用户只描述顶层目标，LLM先生成必要子模块列表，再按列表实现。

优势是自动化程度高；风险是：

- 漏掉关键子模块；
- 加入多余模块；
- 接口命名跨模块不一致；
- hierarchy 每次随机变化，预写 unit test 困难；
- 一个早期错误计划会污染整个后续链。

论文发现除 GPT-4 外，大多数模型在 PGHP 的 hierarchy planning 上不稳定。

### 4.3 两者不能混称“全自动”

HDHP 的代码生成和修复可以无人工介入，但架构设计与测试接口仍是人工输入。

PGHP 才把架构决定交给模型；只有连接口修复也不需要人工，才能称论文意义上的 purely LLM-designed。

---

## 5. 论文三阶段、八步流程

### 5.1 Phase 1：Hierarchy Extraction

```text
HDHP：直接读取人提供的 submodule list
PGHP：让 LLM 从自然语言顶层需求生成 submodule list
```

输出应包含依赖顺序，叶子模块在前，集成模块在后。

### 5.2 Phase 2：Submodule Implementation

对每个子模块：

1. 根据全局目标、已有模块与当前接口生成 prompt；
2. LLM 输出当前 Verilog；
3. Icarus 编译 candidate + 当前 testbench；
4. 若编译/仿真失败，提取错误；
5. 把错误反馈给 LLM；
6. 通过后保存模块并进入下一项。

PGHP 如果没有 unit tests，论文说可接受首次生成的子模块，然后依靠顶层 testbench 最终把关。这一分支显然弱于 HDHP，因为中间错误可能直到顶层才暴露。

### 5.3 Phase 3：Top-Level Integration

最后让 LLM 使用所有已生成子模块实现顶层，并用顶层 testbench 进入同样的反馈环。

论文定义整个 run 成功的条件是：

```text
top module passes its testbench
```

它不是 formal equivalence，也没有 PPA 门槛。

---

## 6. Prompt 结构

### 6.1 System prompt

论文 system prompt 约束模型：

- 只生成指定的完整 Verilog module；
- 不生成 testbench 或补充模块；
- 遇到 compiler/simulation error 时修正完整模块；
- 输出 complete and correct form。

目标是减少无关文本和多模块 hallucination。

### 6.2 Global prompt

描述最终目标，例如“将设计一个 64-to-1 multiplexer，并使用 hierarchical submodules”。

### 6.3 当前子模块 prompt

只给：

- current module human-readable name；
- current filename/module name；
- I/O interface；
- 先前模块信息；
- `// Insert code here` 补全位置。

论文认为接口由人固定有利于 testbench 自动化。

---

## 7. Relay prompting

text-completion 模型不会自动记住多轮上下文，而且 context window 较短。论文提出 relay prompt：

```text
最早模块：只保留 module instantiation / interface
中间旧模块：只保留 module instantiation / interface
最近一个模块：保留完整 RTL
当前模块：请求完整生成
```

它不是普通摘要，而是保留层次连接所需的最小接口信息，并让最近一层的完整实现作为具体模板。

论文以 decoder 为例：生成 5-to-32 decoder 时，2-to-4 decoder 压成短接口，3-to-8 decoder 保留完整代码。

收益：

- 控制 prompt 长度；
- 保留层次顺序；
- 让短上下文开放模型也能“接力”；
- 避免每层重复全部早期代码。

当前 notebook 并没有严格实现这项压缩，后文单独说明。

---

## 8. 六个论文 benchmark

| 顶层 benchmark | 主要层次 |
|---|---|
| 64-to-1 Multiplexer | 2:1 → 4:1 → 8:1 → 16:1 → 32:1 → 64:1 |
| 5-to-32 Decoder | 2-to-4 → 3-to-8 → 5-to-32 |
| 32-bit Barrel Shifter | 1/2/4/8/16-bit shift stages → top |
| 4×4 Systolic Array | processing elements、阵列/控制/缓冲 |
| 8-bit UART | baud、TX、RX、top |
| AES Block Cipher | S-box、shift/mix/add-key、round、key、cipher top |

这些任务覆盖由规则递归扩展的简单层次和具有异构子模块的复杂系统。

论文附录 Table 5 列出 top modules 与对应 submodules，是 HDHP 的“人工 hierarchy ground truth”。

---

## 9. 论文模型与配置

### 9.1 八个模型

| 模型 | 参数 | 开放性 | 定位 |
|---|---:|---|---|
| Llama 2 | 13B | Open | 通用模型 |
| Code Llama | 13B | Open | 代码模型 |
| VeriGen | 16B | Open | Verilog 微调模型 |
| CL-Verilog | 13B | Open | 作者微调 Code Llama-Verilog |
| RTL-Coder | 7B | Open | Verilog/RTL 专用模型 |
| Llama 3 | 8B | Open | 新一代通用模型 |
| GPT-3.5 Turbo | 论文估约 20B | Closed | 商业 chat model |
| GPT-4 | 论文估约 1.8T | Closed | 商业 chat model |

参数量带 `*` 的闭源模型数字是估计，不是厂商公开架构事实。

### 9.2 运行设置

| 参数 | 论文设置 |
|---|---|
| open model hardware | 单张 NVIDIA A100 80GB |
| GPT | OpenAI API |
| temperature | 0.5 |
| top-p | 0.9 |
| 每 model-method-module | 10 个 run |
| 每模块 feedback iteration | 最多 10 |
| 评价 | pass@1、pass@5、平均 wall-clock time |

NH 非层次基线仍使用相同工具反馈环，只是 prompt 不提供 hierarchy。这使对比主要隔离 hierarchy，而不是“有没有反馈工具”。

---

## 10. pass@k 语义

每个组合生成 `n=10` 次，其中 `c` 次最终通过 testbench：

```text
pass@k = 1 - C(n-c, k) / C(n, k)
```

当 `k=1` 时，本质是成功样本比例 `c/n`。

当 `k=5` 时，表示从十份候选中不放回抽五份，至少一份成功的概率估计。

例如 `pass@1=0.4` 对应 10 次中 4 次成功，论文表中 `pass@5≈0.976`。

这和“feedback iteration”是两个不同层次：

```text
一次 run 内：最多若干次修复尝试
十次 run 间：统计 pass@1 / pass@5
```

---

## 11. Table 1：层次提示的主结果

下面把论文 Table 1 的 pass@1 写成 `NH → H`，每项都基于 10 次 run：

| 模型 | Mux | Decoder | Barrel | Systolic | UART | AES |
|---|---|---|---|---|---|---|
| Llama 2 | 0.0→0.4 | 0.0→0.5 | 0.0→0.0 | 0.0→0.0 | 0.0→0.2 | 0.0→0.0 |
| Code Llama | 0.0→0.7 | 0.0→0.8 | 0.0→0.2 | 0.0→0.2 | 0.0→0.4 | 0.0→0.2 |
| VeriGen | 0.0→0.8 | 0.1→0.7 | 0.0→0.3 | 0.0→0.5 | 0.0→0.4 | 0.0→0.3 |
| CL-Verilog | 0.3→0.8 | 0.1→0.9 | 0.0→0.4 | 0.0→0.5 | 0.0→0.6 | 0.0→0.3 |
| RTL-Coder | 0.0→0.4 | 0.2→0.7 | 0.0→0.0 | 0.0→0.1 | 0.0→0.2 | 0.0→0.0 |
| Llama 3 | 0.1→0.8 | 0.0→0.7 | 0.0→0.1 | 0.0→0.0 | 0.0→0.4 | 0.0→0.0 |
| GPT-3.5 | 0.0→0.7 | 0.0→0.8 | 0.0→0.1 | 0.0→0.0 | 0.0→0.7 | 0.0→0.1 |
| GPT-4 | 0.2→0.9 | 0.4→1.0 | 0.3→0.7 | 0.0→0.5 | 0.0→0.8 | 0.0→0.5 |

准确解读：

- 每项 H 不低于 NH；
- 多个开放模型在 NH 完全失败、H 后出现有效成功率；
- GPT-4 的 H 在 6 题上都至少 0.5 pass@1；
- AES 对所有模型仍最难；
- “所有模型改善”指表中模型-题组合的总体趋势，部分组合是 `0→0`，并非每个格子都有严格正增益。

### 11.1 pass@5 的非线性

`pass@1=0.1` 时，`pass@5=0.5`；`pass@1=0.5` 时，`pass@5≈0.996`；因此 Table 1 的 pass@5 很快接近 1。

组会上不能把 pass@5=1.0 说成“每次都成功”，它可能只是十次里成功样本足够多，使五选一失败概率为零或近零。

---

## 12. 生成时间与延迟

论文 Figure 4 报告层次提示相对 flat 的平均延迟下降：

| benchmark | 平均延迟下降 |
|---|---:|
| 5-to-32 Decoder | 44.31% |
| 64-to-1 Multiplexer | 45.59% |
| 4×4 Systolic Array | 69.98% |
| UART | 70.39% |
| AES | 73.73% |
| 32-bit Barrel Shifter | 85.41% |

原因不只是单次输出更短。flat 失败时会在工具反馈环里反复生成整个长模块，错误处理成为主要耗时；hierarchy 让多数错误局部化到短模块。

但这里的 wall-clock 包含：

- 本地模型推理或远程 API；
- 编译仿真；
- 网络延迟；
- 多轮 repair；
- 模型差异。

它不是纯算法复杂度，也不能直接迁移到当前 API 价格/延迟。

---

## 13. PGHP hierarchy planning 结果

论文让六个模型对三个较简单任务各生成 20 个 hierarchy，并与 HDHP golden plan 比较：

| 模型 | Mux | Decoder | Barrel Shifter |
|---|---:|---:|---:|
| Code Llama | 0.15 | 0.05 | 0.05 |
| VeriGen | 0.15 | 0.10 | 0.00 |
| CL-Verilog | 0.25 | 0.10 | 0.10 |
| RTL-Coder | 0.05 | 0.15 | 0.00 |
| GPT-3.5 | 0.20 | 0.15 | 0.00 |
| GPT-4 | 0.85 | 1.00 | 0.35 |

这说明 PGHP 的主要瓶颈不一定是 Verilog syntax，而可能是架构规划：小模型容易缺关键模块或添加多余模块。

论文对 hierarchy accuracy 的“golden plan”匹配也有局限：不同但功能等价的合理架构可能被判错，尤其 barrel shifter 本来就有多种结构。

---

## 14. GPT-4 PGHP 结果

| benchmark | pass@1 | pass@5 |
|---|---:|---:|
| Multiplexer | 0.5 | 0.996 |
| Decoder | 1.0 | 1.0 |
| Barrel Shifter | 0.3 | 0.917 |
| Systolic Array | 0.1 | 0.5 |
| UART | 0.3 | 0.916 |
| AES | 0.0 | 0.0 |

PGHP 使 GPT-4 在 flat 完全失败的 systolic array 和 UART 上出现成功实现，但 AES 仍为零。

这表明“让模型自己分层”不是普适解：复杂、专业、接口密集的 hierarchy 仍可能需要人类架构输入或更强约束。

---

## 15. 常见失败模式

### 15.1 Completion 过长后失去目标

模型完成当前模块后继续生成 testbench、随机模块或解释。论文通过 system prompt 和 `endmodule` 截断抑制。

### 15.2 Perseveration-like loop

论文展示 GPT-3.5 被要求移除 barrel shifter 中不必要的 always block 后，口头确认已修改，却继续输出同样结构。

工具反馈如果只是重复相同错误文本，模型可能进入稳定错误循环。

### 15.3 Interface naming drift

PGHP processor case 中，模型即使列出了多数必要模块，也可能在 wire/signal 命名上不一致，导致顶层难以连接。

### 15.4 Missing control block

模型可能遗漏 control unit 等关键但不显眼的模块，必须明确请求。

### 15.5 Unit test 不足

子模块 testbench 通过不保证组合后的时序/协议正确；top-level testbench 仍是最终门槛。

---

## 16. Processor case studies 的准确边界

### 16.1 有人工介入的案例

论文先用 GPT-3.5 和 Code Llama-Verilog 生成 16-bit single-cycle MIPS，又用 GPT-4 生成 32-bit RISC-V。

这些尝试中：

- 模型漏掉关键元素；
- wire/signal 命名需要人工统一；
- control unit 等模块需人工明确请求；
- 修正后在 Vivado 综合并仿真指令。

所以它们不是“零人工反馈 processor”。

### 16.2 论文的零人工设计案例

作者随后再次用 GPT-4 PGHP 生成一个 MIPS core：

- 初始 prompt 要求定义 16-bit single-cycle MIPS 所需子模块；
- 设计决定由 LLM 做；
- 错误处理由工具反馈自动完成；
- 用时 23 分 37.85 秒；
- 论文称其覆盖一个 full MIPS ISA version；
- 附录给出 elaborated schematic 与指令 waveform。

“无人工设计干预”仍不代表整个研究系统没人设计：

- ROME pipeline、system prompt、parser、testbench 是人工构建；
- benchmark success 由特定 testbench 定义；
- 论文没有公开等价于工业 CPU verification 的完备证明。

最准确的说法是：在作者构建的自动 pipeline 与验证环境内，该次 MIPS 的 hierarchy/RTL 修复没有人类逐步介入。

---

## 17. Token 与价格

论文 Table 4：

| 模块 | H 输入 token | H 输出 token | H cost | NH 输入 token | NH 输出 token | NH cost | 节省 |
|---|---:|---:|---:|---:|---:|---:|---:|
| Multiplexer | 92 | 2,376 | $0.00484 | 91 | 3,283 | $0.00666 | 27.23% |
| 32-bit Barrel | 262 | 1,977 | $0.00422 | 191 | 4,268 | $0.00873 | 51.69% |
| 16-bit MIPS | 434 | 14,226 | $0.02868 | 1,243 | 31,033 | $0.06314 | 54.58% |
| 32-bit RISC-V | 795 | 17,310 | $0.03542 | 1,593 | 42,338 | $0.08593 | 58.8% |

价格基于论文时期 GPT-3.5 tokenizer/pricing，只用于比较同一时期两种 prompt 方法。不能当作当前 2026 API 报价。

---

## 18. 当前仓库地图

```text
ROME-LLM/
├── README.md
├── ROME_Demo_ADHP.ipynb
├── supplements/
│   ├── flowchart.png
│   └── rome_llm_flowchart.pdf
├── testbenches/
│   ├── aes-128/
│   ├── barrel-shifter/
│   ├── conv_1d/
│   ├── conv_2d/
│   ├── conv_3d/
│   ├── decoder/
│   ├── harris_corner/
│   ├── mips16-single-cycle/
│   ├── mux/
│   ├── rca-32/
│   ├── systolic-array/
│   ├── uart/
│   └── unsharp_mask/
├── 2407.18276_ROME.pdf
└── runs/static_audit_20260802.json
```

当前有 13 个 testbench 家族、92 个 `*tb.v` 文件。

仓库没有：

- 论文八模型统一推理脚本；
- CL-Verilog 训练代码/权重；
- 论文 10 次 raw outputs；
- pass@k 汇总器；
- Table 1/2/3/4 机器可读结果；
- processor 生成 RTL 与运行日志；
- 环境锁文件；
- 根目录 LICENSE 文件。

论文附录说 code where applicable 使用 MIT，但当前 commit 根目录确实未见明确 LICENSE，README 也写“under construction”。

---

## 19. 当前 notebook 的实际 provider 层

当前默认：

```python
model_choice = "gpt-5.2"
```

wrapper 包括：

- `ChatGPT`；
- `Claude`；
- `Gemini`。

依赖安装 cell 会安装 API SDK，并通过 apt 安装 Icarus、Verilator、GTKWave。

这说明 notebook 已在论文后继续维护，但也意味着现在直接运行不再是论文 GPT-4 默认环境。

### 19.1 ChatGPT 角色丢失

`Conversation` 保存了原始 `role`，但 `ChatGPT.generate` 构造 API messages 时把每条都改为：

```python
{"role": "user", "content": ...}
```

于是：

- system prompt 不再是 system；
- assistant 历史不再是 assistant；
- 对话交替结构丢失。

这是当前代码事实，不是论文声称的方法。

### 19.2 Claude/Gemini 与 OpenAI 语义不等价

Claude 直接保留 `Conversation` 中的 roles，但 base prompt 被当作 user；Gemini 只传 content 字符串列表，不保留明确 roles。

所以“支持三个 provider”不等于三者拿到同样 prompt protocol。

---

## 20. 代码解析链

`find_verilog_modules` 用两个 regex 匹配普通或 parameterized module；`write_code_blocks_to_file` 把所有匹配写入当前文件。

问题：

1. 传入的 `module_name` 没用于筛选；
2. 如果响应含多个 module，会全部写入；
3. regex 对嵌套括号、属性、宏、interface、复杂 parameter 可能失败；
4. 若没有 match，直接 `exit(3)`；
5. parse failure 不会变成一条 feedback 让 LLM 修格式。

这与 system prompt 的“只输出当前模块”一起工作时通常够用，但不具备编译器级 parser 的鲁棒性。

---

## 21. `verilog_loop` 的实际调用链

```text
构造 initial conversation
  ├─ base system-like prompt
  ├─ 完整 testbench 文本
  └─ 当前 hierarchy prompt

while not success/timeout:
  ├─ provider.generate(conversation)
  ├─ regex 提取 module
  ├─ 保存 <outdir>/<module>.v
  ├─ 拼接 prior modules + current 到 __combined.v
  ├─ iverilog combined + testbench
  ├─ 若 stderr 非空或 returncode 非零 → error
  ├─ 否则 vvp
  ├─ stdout 含 "passed!" → success
  └─ 否则重建 repair-only conversation
```

它确实包含可执行工具反馈，而不是只把 LLM 的自我评价作为正确性。

---

## 22. Repair context 的当前实现偏差

初次生成输入：

- base prompt；
- testbench 全文；
- design/hierarchy prompt；
- 之前模块完整代码。

失败后 `_new_conv_repair_only` 只输入：

- 上一次当前模块 RTL；
- 最近 compiler/simulation 输出。

它丢掉：

- 原始 design prompt；
- testbench 原文；
- 当前 module I/O 以外的设计意图；
- prior hierarchy modules 上下文。

若错误日志只写“expected 3 got 2”，模型未必知道完整时序要求。论文描述更像在对话中回灌错误，而当前优化版为了控制 prompt size 做了更激进的上下文截断。

这是一个真实 trade-off：

```text
更小 prompt / 更低成本
vs
修复时保留规格与层次语义
```

更稳妥的最小上下文应至少保留 current interface、短规格摘要、testbench 判分协议和依赖 module signatures。

---

## 23. 日志行为

`Conversation(log_file=log)` 构造时如果文件存在会清空。每次失败又用同一 `log` 新建 Conversation，因此 `log.txt` 会被截断，不能作为全程对话历史。

代码另写：

```text
log_iter_0.txt
log_iter_1.txt
...
```

这些文件保存当次 bounded conversation 与 status，能保留各 iteration，但仓库目前没有提交任何现成运行日志。

因此不能根据“代码会写日志”宣称“已有论文运行记录”。

---

## 24. 编译与仿真判分问题

### 24.1 Warning 被当作 failure

逻辑是：

```text
returncode != 0 → compile error
stderr != ""   → warning，也作为失败进入 repair
```

Icarus 即使成功也可能把 warning 写到 stderr。严格清除 warning 有工程价值，但它与“语法/功能失败”不是同一指标。

### 24.2 不检查 vvp return code

仿真只看 stdout 是否含：

```text
passed!
```

没有检查 vvp return code，也没有锚定唯一终止行。含该子串的其他文本可能误判。

### 24.3 没有 timeout

API、Icarus 和 vvp 都没有 timeout。组合逻辑振荡、永不 `$finish` 的 testbench 或 provider 卡住都可能让 notebook无限等待。

### 24.4 最大迭代 off-by-one

`iterations` 从 0 开始，生成完成后才判断：

```python
if iterations >= max_iterations:
    timeout = True
iterations += 1
```

所以 `max_iterations=10` 实际生成 iteration 0–10，共 11 次。

论文写 ten iterations per module；若要严格复算，必须确认论文代码是否也有这一 off-by-one。

---

## 25. `hier_gen` 的当前层次实现

输入格式：

```python
[filename, human_name, interface_string]
```

例如 mux：

```text
mux2_1 → mux4_1 → mux8_1 → mux16_1 → mux32_1 → mux64_1
```

每层：

- 把所有 `prev_verilog_files` 的完整内容拼到 prompt；
- 明确要求只输出当前模块；
- compile 时也把全部 prior modules 与当前模块拼成 combined file；
- 通过后把当前 `.v` 加入依赖列表。

### 25.1 与论文 relay prompt 不同

论文 relay：最近一层 full code，更早层只留 instantiation/interface。

当前 notebook：所有 earlier modules 都读全文加入 prompt。

小层次更直观，但 AES、processor 等深层设计会让上下文持续增长，削弱论文强调的 relay efficiency。

### 25.2 顶层作为列表最后一项

当前 notebook 没有一个独立 `integrate_top()`；而是把 top module 放在 `submodules` 列表最后，通过同一 `hier_gen` 生成。

语义上仍能实现 Phase 3，但代码结构没有单独标记 top-level metric。

---

## 26. 当前 benchmark 扩展

论文只报告 6 个 benchmark。当前目录有 13 个家族：

| 家族 | testbench 数 |
|---|---:|
| AES-128 | 19 |
| Barrel shifter | 6 |
| Conv 1D | 3 |
| Conv 2D | 4 |
| Conv 3D | 5 |
| Decoder | 3 |
| Harris corner | 8 |
| MIPS16 single-cycle | 17 |
| Mux | 6 |
| RCA-32 | 3 |
| Systolic array | 7 |
| UART | 4 |
| Unsharp mask | 7 |
| 合计 | 92 |

这说明代码资产持续扩展，已经覆盖卷积和图像处理等层次设计。

但 notebook 当前展示 cell 主要覆盖 mux、decoder、barrel、systolic、UART 和 AES；其余 testbench 不等于已有完整 submodule plan/运行结果。

---

## 27. 论文—代码对应表

| 论文概念 | 当前代码 | 对应程度 | 备注 |
|---|---|---|---|
| hierarchy list | notebook `submodules` | 高 | 显式顺序、名字、接口 |
| HDHP | 手工填写 `submodules` | 高 | 当前主要实现 |
| PGHP hierarchy extraction | 无通用自动函数 | 低 | 当前 notebook 没有论文完整 PGHP 入口 |
| system prompt | `base_sys_prompt` | 中 | OpenAI wrapper 会丢失 system role |
| relay prompt | `hier_gen` prior code | 中低 | 当前保留全部 prior full code |
| tool feedback | `verilog_loop` | 高 | Icarus + vvp + error feedback |
| unit test | `testbenches/` | 高 | 当前 92 份 |
| top integration | 列表最后一个 module | 中高 | 无独立 phase API |
| output truncation at endmodule | regex module extractor | 中 | 不是 provider stop token |
| n=10 benchmark | 未见批量驱动 | 低 | 只能手工反复运行 cell |
| pass@k | 未见实现 | 无 | 论文数值不可从仓库直接重算 |
| 8 models | 当前 3 provider wrapper | 低 | 模型与论文不一致 |
| saved raw outputs | 无 | 无 | 无法做 artifact verification |
| processor case output | 无 | 无 | 论文图有，仓库当前未提交 RTL/log |

---

## 28. 当前能证明与不能证明

### 已能证明

- 论文确实提出 HDHP、PGHP 与 relay prompting；
- 论文 NH 基线仍有 tool feedback；
- 论文使用 8 模型、6 benchmark、n=10、temperature 0.5、top-p 0.9；
- 论文 Table 1 中 hierarchy 总体优于 flat；
- 当前 notebook 确实实现逐模块 Icarus/vvp 反馈；
- 当前仓库有 92 个 testbench；
- 当前 notebook 已漂移到新 provider/model；
- OpenAI message roles、repair context、日志、parser、timeout 和 iteration 存在上述边界。

### 不能证明

- 当前 notebook 可重算论文 Table 1；
- GPT-4 论文 snapshot 与当前 GPT 服务等价；
- 论文 10 次 raw output 均可追溯；
- 论文 processor RTL 在当前仓库可以重新综合；
- 92 个 testbench 都有配套 hierarchy plan；
- testbench pass 等价于完整功能正确；
- 当前默认 GPT-5.2 一定优于论文 GPT-4；
- 所有新 benchmark 都已运行。

---

## 29. 严格复现需要补什么

### 29.1 固定 paper snapshot

当前 clone 是 shallow/grafted，只见 2026 commit。应从 Zenodo/FigShare 恢复论文 artifact snapshot，并记录 hash。

### 29.2 固定模型

开放模型应保存 checkpoint revision；闭源模型至少记录 API model ID、日期和完整响应元数据。

### 29.3 恢复两类方法

统一 runner 应支持：

```text
NH + feedback
HDHP + feedback
PGHP + feedback
```

并确保除 hierarchy 输入外，生成次数、max repair、temperature、top-p、testbench 完全一致。

### 29.4 结构化运行记录

每次 run 保存：

- hierarchy plan；
- 每层 prompt/response；
- parser 输出；
- compile/sim return code；
- stdout/stderr；
- mismatch/pass marker；
- repair count；
- token usage；
- API latency；
- 总 wall-clock；
- 最终全部 RTL。

### 29.5 Reference-first 自检

每个 testbench 先用人工 reference 验证，加入错误控制 RTL，确认 pass/fail 不是字符串误判。

### 29.6 pass@k

按每个 model-method-module 的 10 个独立 run 计算，不能把一次 run 内 10 个 repair iteration 当成 10 个独立 sample。

---

## 30. 如果后续修代码，优先级

本次按用户要求只完善文档，没有改 notebook。后续最小修复顺序：

1. OpenAI wrapper 保留真实 roles；
2. repair context 保留短规格、接口和依赖 signatures；
3. `subprocess.run` 增加 timeout 并检查 return code；
4. success marker 使用锚定协议/mismatch count；
5. parse failure 回灌模型，不 `exit(3)`；
6. module parser 按目标 module name 选择；
7. 修正 max-iteration off-by-one；
8. 不在 repair Conversation 初始化时清空总日志；
9. 重建论文 relay compression；
10. 加 NH/HDHP/PGHP 统一 CLI；
11. 自动多 seed/n=10；
12. 输出 JSONL 与 pass@k 汇总；
13. 锁 provider/model/config；
14. 为 13 个当前 benchmark 写 manifest。

---

## 31. 组会分享建议

### 推荐标题

**“ROME：层次化提示为什么能让 RTL 工具反馈从单模块修补扩展到复杂系统”**

### 推荐 12 页

1. flat RTL 生成在复杂模块上的失败；
2. 论文 Figure 1 的内外双循环；
3. HDHP 与 PGHP；
4. 三阶段八步 pipeline；
5. relay prompt 为什么节省上下文；
6. 六个层次 benchmark；
7. NH 基线为什么仍有 feedback；
8. Table 1 pass@1 的 NH→H；
9. PGHP hierarchy planning 是主要瓶颈；
10. processor case 的人工介入边界；
11. 当前 notebook 的真实代码调用链；
12. 当前版本漂移与可复现性结论。

### 两个最容易讲错的点

1. **ROME 不是 PPA optimization**：名字中的 optimization 是机器编辑迭代，不是面积/功耗/时序搜索；论文 success 是 testbench pass。
2. **所有 processor 都零人工**是错的：早期 MIPS/RISC-V 案例有人工接口和缺失模块干预，只有后续 GPT-4 MIPS 被论文标作无人工设计干预。

---

## 32. 与其他本地项目的关系

| 项目 | 计划层次 | 工具反馈 | 多模块 | PPA |
|---|---|---|---|---|
| RTLLM self-planning | 自然语言计划 | 无执行反馈 | 通常单设计模块 | 评价 PPA |
| AutoChip | 无显式 hierarchy | Icarus compile/sim | 主要完整 DUT | 无 |
| VerilogCoder | Planner + task graph | sim/debug + AST/VCD | 支持分任务 | 主要功能 |
| ROME | HDHP/PGHP hierarchy | 每层 Icarus/vvp | 核心贡献 | 无 |
| ChipSeek | 不同层次 | 综合/PPA reward | 优化流程 | 有 |

ROME 最独特的是把**模块层次顺序**与**每层可执行反馈**结合，而不是单纯多轮生成。

---

## 33. 文件导航

- [ROME 原论文](./2407.18276_ROME.pdf)
- [官方 README](./README.md)
- [当前 Colab notebook](./ROME_Demo_ADHP.ipynb)
- [官方流程图 PNG](./supplements/flowchart.png)
- [官方流程图 PDF](./supplements/rome_llm_flowchart.pdf)
- [92 个 testbench 根目录](./testbenches/)
- [静态审计 JSON](./runs/static_audit_20260802.json)
- [短版模型梳理](./模型梳理.md)

---

## 34. 最终判断

ROME 是很适合组会分享的一篇：它把“硬件本来就是层次化设计”转化成可执行 LLM pipeline，并且用公平的 NH+feedback 对比说明收益不只是来自工具闭环，而来自 hierarchy 本身。

论文最有价值的三点是：

1. HDHP/PGHP 分开了“人给架构”和“模型自己设计架构”；
2. relay prompting 处理开放模型短上下文；
3. unit-test feedback 把错误局部化到当前层。

当前代码又提供了很好的反面教材：一个 paper artifact 随时间加入新模型和新 benchmark 后，如果没有固定 snapshot、结果记录和批量 evaluator，就不能直接拿最新 notebook 当论文复现。

最终应写：

> **本地已完成 ROME 论文、当前 notebook、13 个 testbench 家族与 92 个 testbench 的静态核对；HDHP 工具反馈调用链已代码级还原，但未调用 LLM 或运行仿真，论文 8 模型×6 题×NH/H×10 次结果和 processor case 尚未本地复现。**

---

## 35. P7 组件一句话角色

| 组件 | 一句话角色 |
|---|---|
| `submodules` 列表 | 定义 HDHP 层次顺序、模块名与接口的人工架构蓝图。 |
| `base_sys_prompt` | 约束 LLM 只输出当前模块完整 Verilog、不生成 testbench 的系统提示。 |
| `verilog_loop()` | 对当前子模块反复调用 LLM → regex 提取 → Icarus 编译 → vvp 仿真 → 错误回灌的修复闭环。 |
| `hier_gen()` | 按层次顺序逐层生成并集成先前已通过模块的主驱动函数。 |
| `testbenches/` 目录 | 提供 13 个家族共 92 个 `.v` testbench，作为各模块和顶层的判定依据。 |

---

## 36. 讨论问题

1. 在 PGHP 中，LLM 自己提出的层次计划与人工给定的 HDHP 差距显著，那么“自动生成合理硬件架构”是否比“生成正确 RTL 代码”更难，应如何单独评价？
2. relay prompting 只保留最近一层完整代码而压缩更早模块，这种上下文截断在什么情况下会丢失关键的层次语义？
3. 当前 notebook 默认使用 `gpt-5.2` 并丢失 OpenAI system role，这说明论文 artifact 随时间漂移，做可复现研究时应如何锁定模型快照和 prompt 协议？

