# VeriGen Model 论文深度讲解

> **VeriGen: A Large Language Model for Verilog Code Generation**
> Shailja Thakur, Baleegh Ahmad, Hammond Pearce, Benjamin Tan, Brendan Dolan-Gavitt, Ramesh Karri, Siddharth Garg
> New York University, University of Calgary
> ACM TODAES（ACM Transactions on Design Automation of Electronic Systems），扩展自 DATE 2023
> arXiv: 2308.00708 v1（2023-07-28），共 29 页
> 原文：[2308.00708v1.pdf](./2308.00708v1.pdf)
> 代码：https://github.com/shailja-thakur/VGen
> 模型权重：https://huggingface.co/shailja

---

## 1. 一句话定位

**VeriGen（2308.00708）在 DATE 2023 Benchmark 版的基础上，把评测从 17 题自建 Set I 扩展到 163-181 道 HDLBits 在线 Set II，把对比模型从 code-davinci-002 一个商业基线扩展到 GPT-3.5-turbo、GPT-4、PaLM2，把语料消融从一句"GitHub+books 比 GitHub-only 高 1.4pp"展开为 books-only vs GitHub-only vs combined 三路对照 + guided system prompt 实验 + 推理时间剖面——系统证明领域微调后的 16B 模型在部分切片上可接近甚至超过当时的 GPT-4，但在复杂状态机、多时钟域、大尺度设计中仍是脆弱的。**

这句话里新增的技术承重点（相对 Benchmark 版）：

1. **"Set II HDLBits 在线评测"** -- 从自建 17 题的本地 Icarus/testbench 评测扩展到 HDLBits 在线 judge（Quartus 综合 + ModelSim 仿真），题量扩大约 10 倍，且使用工业级综合器和仿真器而非开源 Icarus。代价是 testbench 不公开、judge 版本不可冻结、题数存在 181/164/163 三种口径的内部矛盾。

2. **"GPT-3.5/GPT-4/PaLM2"** -- 2023 年上半年 OpenAI 和 Google 发布了新一代闭源大模型，论文迅速将其纳入对比。结论不是"VeriGen 全面击败 GPT-4"，而是"CodeGen-16B-FT 在 medium-description 切片略高（0.436 vs GPT-4 的 0.39），但 GPT-4 跨题平均分最高（约 0.53 vs CodeGen-16B-FT 约 0.40）"。

3. **"三路语料对照"** -- 新设 books-only FT\*、GitHub-only FT、combined FT++ 三个版本，证明单独的教材语料远不足以让模型学会 Verilog（books-only Basic Low 仅 0.083），但 combined 在 low-description 切片上比 GitHub-only 提升约 10%。

4. **"guided system prompt"** -- 发现给 GPT-3.5 一个明确的 Verilog autocomplete 角色描述（而非泛化的 programming assistant），在 Low description 上提升 41%，High description 上提升 34.3%。这说明 chat 模型的 system instruction 是实验配置的一部分，不能只用 user prompt 比较。

5. **"推理时间剖面"** -- CodeGen-16B-FT 推理延迟约 2.02 秒，GPT-4 约 10.00 秒（含网络通信）。领域微调小模型在响应速度上有数量级优势。

---

## 2. EDA 阶段映射（①-⑰）

参照 [芯片流程](../芯片流程.md) 的 17 阶段标准编号：

| 阶段 | 覆盖 | 说明 |
|------|:---:|------|
| **① RTL 设计** | ✅ **核心** | 从 L/M/H prompt + module header 生成 Verilog。新增 Set II 的 HDLBits prompt 风格（在线题目描述，通常不含 module header） |
| **② RTL 功能仿真** | ✅ **核心** | **双轨评测**：Set I 仍用 Icarus v11.0 + 自建 testbench；Set II 使用 **HDLBits 在线 judge**（Quartus 综合 + ModelSim 仿真，返回 Success / Compile Error / Simulation Error / Incorrect 四种状态） |
| ③ 逻辑综合 | ⚠️ **部分** | Set II 的在线 judge 内部跑 Quartus 综合——候选代码必须通过综合才能进入 ModelSim 仿真。**但综合结果不反馈给模型**（无 PPA optimization loop），只是 judge 的中间步骤。这比纯 Icarus 编译多了一道"可综合性"关卡 |
| ④ 门级仿真 | ⚠️ **部分** | Set II 在线 judge 的 ModelSim 仿真可能包含门级网表的时序仿真（取决于 HDLBits 题目配置），但论文没有控制或说明这层 |
| ⑤ STA（Static Timing Analysis，静态时序分析） | ❌ | 不计算任何路径延迟。HDLBits judge 做综合但不跑 STA |
| ⑥ 形式验证 | ❌ | 不做 SAT/SMT 等价性证明 |
| ⑦ 布局规划 (Floorplan) | ❌ | —— |
| ⑧ 标准单元摆放 (Placement) | ❌ | —— |
| ⑨ 时钟树综合 (CTS) | ❌ | —— |
| ⑩ 布线 (Routing) | ❌ | —— |
| ⑪ 后仿真 | ❌ | 无 SPEF（Standard Parasitic Exchange Format，标准寄生参数交换格式）信息 |
| ⑫ 物理验证 DRC + LVS | ❌ | —— |
| ⑬ 签核 (Signoff) | ❌ | —— |
| ⑭-⑰ 流片 → 制造 → 封装测试 → 芯片 | ❌ | —— |

**覆盖率：2/17（严格）或约 3/17（如果把 Set II 的 Quartus 综合算上）。** 模型版比 Benchmark 版多了一点物理反馈（HDLBits 的 Quartus 综合会在生成代码不可综合时报 Compile Error），但这个反馈仅用于评测，不用于训练或迭代修复。

> ⚠️ Set II 的"在线 judge"不是本地可冻结的工具链。每次提交到 HDLBits 的代码由远程 Quartus + ModelSim 实例评测，testbench 不公开、综合器版本/配置不可控、网络延迟不可控。这使得 Set II 的**可复现性**依赖于 HDLBits 服务端的稳定性和题目版本的不可变性——两个在 2026 年都不可靠的假设。

---

## 3. 输入 / 输出

> Set I 的 prompt、采样、生成和评测已在 [Benchmark 版深度讲解](./论文深度讲解_VeriGen-Benchmark.md) 第 3 节完整覆盖，此处仅展示**模型版新增**的 Set II 和 GPT system prompt 示例。

### 3.1 Set II：HDLBits 在线评测的输入

Set II 使用 HDLBits 网站（https://hdlbits.01xz.net/）的题目描述作为 prompt，不再有 L/M/H 三档或标准化的 module header。典型 prompt 形态——"Ring or Vibrate" 题目（Combinational Logic）：

```text
Design a circuit that controls a cell phone's ringer and vibration motor.
When the phone receives an incoming call (input ring), the circuit must
start sounding the ringer (output ringer = 1) or vibrating the motor
(output motor = 1), but not both, based on the mode set by the user
(input vibrate_mode). If vibrate_mode = 0, just ring. If vibrate_mode = 1,
vibrate for 1 second, then ring for 1 second, then vibrate for 1 second,
and so on. When the user answers (input answer = 1), stop both.
```

与之对比，Set I 的 ABRO FSM prompt（同样也是 FSM 设计）：

```verilog
// Problem 17: ABRO FSM
// Design a finite state machine with one input and one output.
// The FSM reacts to the sequence of inputs a and b.
// When both a and b are true in any order, issue output r and reset.
module abro_fsm(
    input clk, rst, a, b,
    output reg r
);
```

关键区别：
- Set II prompt 是**自然语言 + 真实工程场景描述**，不包含 module header、端口声明或代码注释，更接近"老板给你的口头需求"
- Set I prompt 是**半结构化的代码补全前缀**，包含 module header 和功能注释，更接近"IDE 的代码补全提示"
- Set II 要求模型**从零构造 module header、端口列表、内部信号**，而 Set I 至少给出了 module name 和端口声明
- Set II 的 testbench 由 HDLBits 在线 judge 控制，不公开，无法本地重跑

#### Set II 采样协议（与 Set I 不同）

| 参数 | Set II 设置 | Set I 设置 |
|------|-----------|-----------|
| temperature | 0.2（固定） | {0.1, 0.3, 0.5, 0.7, 1.0} |
| completions n | 5（固定） | {1, 10, 25} |
| max_tokens | 900（chat models） | 300（autocomplete） |
| 参评模型 | CodeGen-16B-FT, GPT-3.5-turbo, PaLM2 | 5 FT + 1 商业基线 |
| GPT-4 | 未纳入 Set II（访问/成本限制） | 不适用 |

### 3.2 Problem Set II 概览（类别与题量）

| 难度 | 类别 | 题数 | 描述 |
|------|------|:---:|------|
| Getting Started | Getting Started | 2 | Step one, Output Zero |
| Verilog Language | Basics | 8 | Simple wires, Inverter, AND, NOR, XNOR, 7458 chip |
| Verilog Language | Vectors | 9 | Vectors, Bitwise operators, Concatenation, Replication |
| Verilog Language | Module Hierarchy | 9 | Modules, Connect by position/name, Adders |
| Verilog Language | Procedures | 8 | Always blocks, If/Case statements, Priority encoder |
| Verilog Language | More Features | 7 | Conditional ternary, Reduction, Generate for-loop |
| Circuits (Comb) | Basic | 17 | Wire, GND, NOR, Gates, Truth tables |
| Circuits (Comb) | Multiplexers | 5 | 2-to-1, 9-to-1, 256-to-1 mux |
| Circuits (Comb) | Arithmetic | 7 | Half/Full adder, 100-bit adder, BCD adder |
| Circuits (Comb) | K-Map to Circuit | 8 | 3/4-variable K-map, Minimum SOP/POS |
| Circuits (Seq) | Latches and Flip-Flops | 18 | DFF, D Latch, Edge detection |
| Circuits (Seq) | Counters | 8 | Binary counter, Decade counter, 12-hour clock |
| Circuits (Seq) | Shift Registers | 9 | Shift register, LFSR, LUT |
| Circuits (Seq) | Cellular Automata | 3 | Rule 90, Rule 110, Conway's Game of Life |
| Circuits (Seq) | FSM | 33 | Moore/Mealy FSM, Lemmings, Serial receiver |
| Circuits (Seq) | Larger Circuits | 7 | Counter 1000, FSM 1101 recognizer |
| Verify Bugs | Read Simulations | 5 | Mux2, NAND, Mux4, Add/subtract, Case statement |

**题数问题**：论文正文 Section 4.1 说"总共 181 题"（17 Set I + 164 Set II），Table 3 caption 称 "Set II has 164 problems"，但实际 Table 3 分类求和为 163 题。三种口径无法统一。

### 3.3 GPT-3.5 System Prompt 实验

模型版新增了一个 system prompt 消融实验，对比 GPT-3.5-turbo 在两种 system prompt 下的表现：

**Unguided system prompt（v0）：**
```
You are a programming assistant. Complete the code as per the user's description.
```

**Guided system prompt（v1）：**
```
You are an autocomplete engine for Verilog code. Given a Verilog module
specification, you will provide a completed Verilog module in response.
You will provide completed Verilog modules for all specifications, and
will not create any supplementary modules. Format your response as Verilog
code containing the end to end corrected module inside code blocks.
```

论文报告的结果：Low description 上 guided 比 unguided 高约 41%；High description 上高约 34.3%——更具体的 Verilog 指令更好。

### 3.4 Set II 的输出和评测

HDLBits 在线 judge 返回四种状态：
1. **Success**：通过 Quartus 综合 + ModelSim 仿真，所有 hidden testbench 用例通过
2. **Compile Error**：Quartus 综合失败（代码不可综合或语法错误）
3. **Simulation Error**：综合通过但 ModelSim 仿真无法运行（通常是模块接口不匹配）
4. **Incorrect**：综合和仿真都能跑，但输出不匹配 hidden testbench 预期

论文报告的 Set II 类别结果（部分可确认数值）：

| 类别 | CodeGen-16B-FT | GPT-3.5-turbo | PaLM2 |
|------|:---:|:---:|:---:|
| Multiplexers | **0.653** | 0.540 | 0.483 |
| Read Simulations & Find Bugs | BugMux2 优势明显 | **0.60**（类别最高） | 0.42 |
| Getting Started (Step_one/Zero) | 接近 1.0 | **1.0** | 明显落后 |

### 3.5 推理时间数据

论文 Section 6.1 / Figure 14 报告的各模型单次推理时间（含网络通信）：

| 模型 | 推理时间 (s) | 说明 |
|------|:---:|------|
| CodeGen-2B-FT | 0.92 | 本地推理 |
| CodeGen-6B-FT | 1.14 | 本地推理 |
| CodeGen-16B-FT | 2.02 | 本地推理 |
| J1-Large-7B-FT | 2.12 | 含远程 API 通信 |
| PaLM2 | 5.76 | API 模型，含网络 |
| GPT-3.5-turbo | 6.32 | API 模型，含网络 |
| GPT-4 | 10.00 | API 模型，含网络 |

> ⚠️ 这些数字不能作为跨平台吞吐对比。缺少 GPU 型号、batch size、输入/输出 token 数、dtype/量化、warm-up 次数、API 网络位置等控制变量。Table 5 中 CodeGen-16B-FT 的推理时间报告为 1.994 秒，Section 6.1 中报告为 2.02 秒——两个数值来自不同测量批次。

---

## 4. 方法与架构

### 4.1 扩展版的总流程（相对 Benchmark 版的增量）

```text
┌──────────────────────────────────────────────────────────────────────────────┐
│  Benchmark 版（DATE 2023）已有的部分（详见 Benchmark 版深度讲解）               │
│                                                                               │
│  GitHub BigQuery + 70 本教材 PDF → ~400MB 语料 → 5 模型微调 → Set I 评测      │
└──────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      │ 继承（数据、模型、Set I 实验线）
                                      ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│  模型版（TODAES 扩展）新增的部分                                                │
└──────────────────────────────────────────────────────────────────────────────┘

  ┌─────────────────────────────────────────────────────┐
  │  新增 1：Set II HDLBits 大规模在线评测               │
  │                                                      │
  │  163-181 道 HDLBits 题目（取决于计数口径）            │
  │      │                                               │
  │      ├─ CodeGen-16B-FT：n=5, T=0.2                   │
  │      ├─ GPT-3.5-turbo：  n=5, T=0.2                  │
  │      └─ PaLM2：          n=5, T=0.2                  │
  │      │                                               │
  │      ▼                                               │
  │  HDLBits 在线提交                                    │
  │      │                                               │
  │      ├─ Quartus 综合（可综合性检验——新！）            │
  │      └─ ModelSim 仿真（功能正确性检验）               │
  │      │                                               │
  │      ▼                                               │
  │  四类结果：Success / Compile Error /                  │
  │            Simulation Error / Incorrect              │
  └─────────────────────────────────────────────────────┘

  ┌─────────────────────────────────────────────────────┐
  │  新增 2：闭源大模型对比                               │
  │                                                      │
  │  Set I:                                              │
  │  ├─ GPT-3.5-turbo（guided + unguided system prompt） │
  │  ├─ GPT-4（web interface, T=0.2, n=1）               │
  │  ├─ PaLM2                                           │
  │  └─ Claude（RQ5 提到，但无等量主结果表）             │
  │                                                      │
  │  Set II:                                             │
  │  ├─ GPT-3.5-turbo                                   │
  │  └─ PaLM2（GPT-4 未纳入，访问/成本限制）             │
  └─────────────────────────────────────────────────────┘

  ┌─────────────────────────────────────────────────────┐
  │  新增 3：多源语料系统消融（Section 6）                │
  │                                                      │
  │  CodeGen-2B-FT*  ← 仅用教材 books corpus             │
  │  CodeGen-2B-FT   ← 仅用 GitHub Verilog corpus        │
  │  CodeGen-2B-FT++ ← books + GitHub（combined）        │
  │      │                                               │
  │      ▼                                               │
  │  Set I 评测对比                                       │
  │  - books-only:   Basic Low 仅 0.083                  │
  │  - GitHub-only:  基准                                │
  │  - combined:     Low description 提升约 10%          │
  └─────────────────────────────────────────────────────┘

  ┌─────────────────────────────────────────────────────┐
  │  新增 4：推理时间分析 + 失败案例深化                  │
  │                                                      │
  │  - Section 6.1 / Figure 14：推理时间剖面              │
  │  - Conway's Game of Life：三个模型全败               │
  │  - 8-bit MUX bug-fixing：CodeGen-16B-FT 胜出         │
  │  - Priority encoder/1-to-12 counter/ABRO FSM 案例图  │
  └─────────────────────────────────────────────────────┘
```

### 4.2 扩展版与研究问题的映射

Benchmark 版的 4 个 RQ 扩展为 7 个：

| RQ | 问题 | 新增于模型版？ | 主要证据 |
|----|------|:---:|------|
| RQ1 | 通用预训练模型能否直接生成 Verilog？ | 继承 | Table 4、Table 5 |
| RQ2 | Verilog domain fine-tuning 是否有效？ | 继承 | PT vs FT |
| RQ3 | 参数量是否影响正确率？ | 继承 | 各模型规模 scaling |
| RQ4 | Prompt 详细度和难度如何影响输出？ | 继承 | L/M/H 对比 |
| **RQ5** | 领域微调小模型 vs GPT-4/GPT-3.5/Claude/PaLM2？ | ✅ **新增** | Figure 8 |
| **RQ6** | 大模型在哪种难度更强/更弱？ | ✅ **新增** | Figure 8、Set II |
| **RQ7** | 教材等多源语料是否有益？ | ✅ **新增** | Figure 12、Figure 13 |

RQ5 和 RQ7 是模型版的核心增量。

---

## 5. 关键公式

> Set I 已有公式（因果 LM 损失、Temperature 采样、论文自定义 Pass@(scenario\*n)）详见 [Benchmark 版深度讲解](./论文深度讲解_VeriGen-Benchmark.md) 第 5 节。本节仅覆盖**模型版新增**的公式分析。

### 5.1 标准 causal LM loss（模型版在语料消融中的新语境）

$$
\mathcal{L}(\theta) = -\sum_{t} \log P_{\theta}(x_t \mid x_{<t})
$$

模型版在 Section 6 语料消融中赋予了这个公式新的语境：

- **books-only（FT\*）**：训练样本的 $x_{<t}$ 前缀来自教材自然语言解释，$x_t$ 是 Verilog 代码 token。这是"自然语言 -> 代码"的翻译 mapping
- **GitHub-only（FT）**：训练样本是连续的 Verilog 代码，$x_{<t}$ 和 $x_t$ 都是代码 token。这是"代码前缀 -> 代码后缀"的补全 mapping
- **combined（FT++）**：混合两种 mapping

books-only 的失败说明：**仅靠"翻译 mapping"不足以让模型学会从 prompt 生成 RTL，因为 prompt（评测输入）的风格更接近"代码补全前缀"而非"教材的详细解释"。** 这是 RTL LLM 训练数据设计中一个重要的观察：训练数据和评测数据的分布匹配可能比数据质量本身更重要。

### 5.2 GPT-3.5 System Prompt 的条件概率

$$
P(r \mid p_{sys}, p_{user}) \neq P(r \mid p_{user} \text{ only})
$$

- $p_{sys}$：system prompt（chat model 的顶层指令，不在 user prompt 中）
- $p_{user}$：user prompt（包含题目描述、规格、module header）
- $r$：生成的 response

这个不等式看似平凡，但在 RTL 评测中是一个容易被忽视的陷阱。ChatGPT 的 system prompt 是 **hidden state**——它的存在不被标准 benchmark 协议捕获。论文的 guided vs unguided 实验量化了这个 hidden factor 的影响：约 34-41% 的通过率差异。这意味着：(1) ChatGPT Web 界面的 RTL 能力不能直接和 API 测试对比；(2) 不同研究者在不同时间测试同一 GPT 模型可能得到不同结果；(3) 后来 AutoChip 的 system prompt 设计很可能借鉴了 VeriGen 的 guided prompt。

### 5.3 Combined corpus 的理想化收益模型

论文没有显式写出这个公式，但可以从消融实验中反推：

$$
\text{quality}(FT++) = \underbrace{\alpha \cdot \text{quality}(FT)}_{\text{GitHub code 贡献}} + \underbrace{\beta \cdot \text{quality}(FT^*)}_{\text{books 贡献}} + \underbrace{\gamma \cdot \text{cross}(FT, FT^*)}_{\text{互补效应}}
$$

- $\alpha$：GitHub 语料在 combined 中的有效占比（接近 1，因为 GitHub 语料占约 75% 体积）
- $\beta$：教材语料在 combined 中的有效占比（远小于 1，因为教材文本中只有 Verilog code blocks 对代码生成有直接帮助）
- $\gamma$：互补效应系数

论文的消融结果显示：$\beta$ 可能远小于 $\alpha$（books-only 远弱于 GitHub-only），但 $\gamma > 0$（combined 在 Low description 上比 GitHub-only 提升约 10%）。这个互补效应的存在是模型版对 Benchmark 版"仅差 1.4pp"论断的重要修正。

### 5.4 模型的推理成本-收益模型

结合论文的推理时间数据和能力数据：

$$
\text{efficiency}(M) = \frac{\text{functional rate}(M)}{\text{inference time}(M) + \text{cost}(M)}
$$

虽然论文没有直接做这个计算，但从数据可以推断：
- CodeGen-16B-FT：约 0.40 functional rate / 约 2s / \$0.00（本地推理）—— **效率最高**
- GPT-4：约 0.53 functional rate / 约 10s / 按 token 计费—— **能力最高但效率低**
- GPT-3.5-turbo：约 0.41 functional rate / 约 6s / 按 token 计费—— **性价比好但弱于本地模型**

对需要大量推理（如采样 100 个候选）的场景，本地部署的 CodeGen-16B-FT 有不可替代的成本优势。

### 5.5 Bug Fixing 的成功条件

论文的 8-bit MUX bug-fixing 案例揭示了 RTL bug fixing 的数学条件：

$$
P(\text{fix success}) \propto P(\text{locate bug} \mid \text{buggy code}) \cdot P(\text{generate fix} \mid \text{bug location})
$$

- $P(\text{fix success})$：一次修复尝试成功的概率
- $P(\text{locate bug} \mid \text{buggy code})$：给定含 bug 的代码，正确定位到 bug 所在行的概率
- $P(\text{generate fix} \mid \text{bug location})$：已知 bug 位置后写出正确修复的概率
- $\propto$：正比于——两步串联，任一步失败整次修复即失败

CodeGen-16B-FT 成功修复了 8-bit MUX 的 bug，而 GPT-3.5 和 PaLM2 失败了。区别不在第二步（生成修复），而在第一步（定位 bug）：CodeGen-16B-FT 见过大量 GitHub 上的 MUX 实现变体，对"MUX 的不同位宽输入之间的 bitwise 操作"有领域知识，能准确定位到缺失的位宽处理。这说明：**领域微调对 bug fixing 的价值不是"知道怎么修"，而是"知道哪里可能有问题"。**

---

## 6. 训练与实验设置

### 6.1 是否需要训练

**需要训练。** 模型版与 Benchmark 版共享同一套微调流程和模型。微调目标仍是标准的 next-token causal LM cross-entropy，无 compiler-in-the-loop 或 RL 反馈。

若使用作者已发布的 Hugging Face checkpoint，则不需要再训练。

### 6.2 预训练基线模型（模型版扩展了闭源模型）

继承 Benchmark 版的 5 个微调模型（MegatronLM-355M、J1-Large-7B、CodeGen-2B/6B/16B），模型版新增对比以下商业闭源大模型：

| 模型 | 规模 | 预训练数据 | Context | 备注 |
|------|------|-----------|---------|------|
| GPT-3.5-turbo | 未公开 | NL + Code | 4096 | OpenAI chat model，需 system prompt |
| GPT-4 | 未公开 | NL + Code | 8000 | web interface 访问，T=0.2, n=1 |
| PaLM2 | 未公开 | NL + Code | 8000 | Google 大模型 |
| Claude | 未公开 | NL + Code | N/A | RQ5 提到但无等量主结果表 |

### 6.3 训练基础设施（与 Benchmark 版相同）

| 模型 | 硬件 | 时间 | Epochs |
|------|------|------|--------|
| CodeGen-2B | 2x NVIDIA RTX 8000 | 2 天 | 1 |
| CodeGen-6B | 4x NVIDIA RTX 8000 | 4 天 | 1 |
| CodeGen-16B | 3x NVIDIA A100 | 6 天 | 1 |
| MegatronLM-355M | 1x NVIDIA RTX 8000 | 15 小时 | 9 |
| J1-Large-7B | AI21 Studio 商业微调 | -- | -- |

CodeGen-16B 在 FP16 精度下参数占 30 GB GPU 内存，微调需约 250 GB（含 optimizer states），使用 DeepSpeed 的 model/data parallelism 与 ZeRO optimizer state sharding。

### 6.4 实验设置（模型版新增）

**Set I 实验**：与 Benchmark 版相同，17 题 x L/M/H prompt x 5 temperatures x n=10，best temperature 报告。

**Set II 实验**（新增）：163-181 道 HDLBits 题目，固定 T=0.2, n=5，参评模型为 CodeGen-16B-FT、GPT-3.5-turbo、PaLM2（GPT-4 因成本和访问限制未纳入 Set II）。

**GPT-4 实验**（新增）：Set I 上，通过第三方 web-interface library 访问，T=0.2, n=1（仅 1 个候选），与 CodeGen-16B-FT 的 n=10 + best temperature 进行比较——协议严重不均衡。

**System prompt 消融**（新增）：GPT-3.5-turbo 在 guided vs unguided 两种 system prompt 下在 Set I 上比较。

**语料消融**（新增）：CodeGen-2B 在三种语料配置下微调——books-only (FT\*)、GitHub-only (FT)、combined (FT++)——在 Set I 上比较。

### 6.5 关键实验结果（模型版新增）

#### GPT-3.5/GPT-4/PaLM2 对比（Set I, n=1, best scenario）

| 模型 | 平均功能分 (approx.) | Medium complexity 最高 | Advanced (all prompt) | 推理时间 |
|------|:---:|:---:|:---:|:---:|
| CodeGen-16B-FT | ~0.40 | ~0.74 | 0.246-0.294 | ~2.02s |
| GPT-4 | **~0.53** | ~0.75 | **~0.6** | ~10.00s |
| GPT-3.5-turbo | ~0.41 | -- | -- | ~6.32s |
| PaLM2 | ~0.30 | -- | -- | ~5.76s |

关键解读：
1. **GPT-4 的 Advanced 能力远超其他所有模型**：约 0.6 vs CodeGen-16B-FT 的约 0.29，接近 2 倍的通过率
2. **CodeGen-16B-FT 在 medium-description 切片上接近 GPT-4**：0.436 vs GPT-4 的 0.39
3. **但 GPT-4 的比较协议严重不均衡**：GPT-4 用 n=1, T=0.2；CodeGen-16B-FT 用 n=10, best temperature

#### 三路语料消融（Set I, CodeGen-2B）

| 版本 | 语料 | Basic Low | Low description 提升 |
|------|------|:---:|:---:|
| FT\* | books-only | 0.083 | -- |
| FT | GitHub-only | 基准 | -- |
| FT++ | combined | 0.548 | 比 GitHub-only 提升约 10% |

解读：books-only 几乎无法工作（Basic Low 仅 0.083，Advanced 全部 0），原因是教材文本大量是自然语言解释，token 层面的分布和 Verilog 代码完全不同。combined 在 Low description 上优于 GitHub-only 约 10%，但在 Basic 上几乎不提升（0.548 vs 0.547）——教材的价值体现在"从匮乏的 prompt 中推断完整规格"的能力上。

> ⚠️ 消融实验存在 2B/16B 标注冲突：Section 6 开头和 Figure 10 明确以 **CodeGen-2B** 定义 FT\*/FT/FT++，但 Figure 12/13 及其 caption 写 **CodeGen-16B**。

#### System prompt 消融

| Description Level | Guided (v1) vs Unguided (v0) 提升 |
|------|:---:|
| Low (L) | 约 41% |
| Medium (M) | 显著 |
| High (H) | 约 34.3% |

#### 推理时间

| 模型 | 推理时间 | 类型 |
|------|:---:|------|
| CodeGen-2B-FT | 0.92s | 本地 |
| CodeGen-6B-FT | 1.14s | 本地 |
| CodeGen-16B-FT | 2.02s | 本地 |
| GPT-3.5-turbo | 6.32s | API |
| GPT-4 | 10.00s | API |

---

## 7. 创新点

### 创新点 1：首个将 RTL LLM 评测从"自建 testbench"扩展到"在线 judge"的工作

Benchmark 版的 17 题 Set I 存在规模小、天花板效应、testbench 自建而缺乏独立性等固有问题。模型版引入 HDLBits 作为 Set II，带来了三个突破：(1) 题量扩大约 10 倍，覆盖 17 个类别；(2) 评测独立性——HDLBits 的 testbench 和 judge 由第三方维护；(3) 可综合性检验——Quartus 综合在仿真之前运行，不可综合的代码在 Set II 中会被直接标记为 Compile Error。但代价是题数三种口径无法统一（181/164/163）、testbench 不透明、不可冻结。

### 创新点 2：系统比较领域微调模型与新一代闭源大模型

2023 年上半年 GPT-3.5/GPT-4 的发布改变了 LLM 格局。模型版迅速将这代模型纳入 RTL 评测框架。关键发现不是"VeriGen 打败 GPT-4"（它没有），而是：(1) 领域微调模型在 medium-description 切片上接近 GPT-4（0.436 vs 0.39）；(2) GPT-4 的 Advanced 能力远超其他所有模型（~0.6 vs ~0.29）；(3) 领域微调的小模型在成本和延迟上有不可替代的优势。

### 创新点 3：三路语料消融实验揭示"代码 vs 教材"的真实分工

Benchmark 版只说"GitHub+books 比 GitHub-only 高 1.4pp"，信息量极低。模型版将消融展开为 books-only / GitHub-only / combined 三路对照。工程启示：**训练 RTL LLM 时，教材语料的价值体现在"从匮乏的 prompt 中推断完整规格"的能力上。** 如果 prompt 已经足够详细（M/H 档），教材的边际收益很小。

### 创新点 4：首次研究 system prompt 对 RTL 生成质量的影响

Guided vs Unguided system prompt 实验揭示了 chat 模型评测中 system prompt 作为 hidden variable 的问题——不同评测框架的 system prompt 不同，同一模型在同一题目上的分数可能因此变化 30-40%。这个发现直接影响了后来 AutoChip 的 system prompt 设计。

### 创新点 5：Conway's Game of Life 等复杂失败案例分析

三个模型（GPT-3.5、PaLM2、CodeGen-16B-FT）在 Game of Life 上**全部失败**：GPT-3.5 同时修改 next_state 和 current_state，wire 放进 always 块；CodeGen-16B-FT 规则判定不符合 Conway 规则；共同问题包括 neighbor counting 没处理环面边界、可能把 cell 自身算作 neighbor。这说明 2023 年水平的 LLM 在真实的"算法 -> 硬件"映射上存在系统性短板——不是某个 token 写错了，而是整个计算模型的理解不够。

### 创新点 6：在 VerilogEval/RTLLM 出现之前建立了 RTL LLM 的评测标准

模型版论文提出了后来被整个领域广泛采纳的评测范式：编译 + 功能双层评测（被 RTLCoder、MAGE、AutoChip 继承）、按难度分级（被 VerilogEval 的 difficulty rating 继承）、在线 judge 作为独立评测源（被 RTLLM benchmark 继承）、多源语料消融（被 OriGen、OpenLLM-RTL 的数据消融实验继承）。

---

## 8. EDA 缩写表

> Benchmark 版已覆盖的缩写（RTL、LLM、EDA、HDL、FSM、RAM、LFSR、MUX、DUT、TB、PT、FT、SDF、SPEF、STA、BLEU、OCR、GPU、API、PPA、RoPE、ZeRO、MinHash）不再重复。以下是**模型版新增**的缩写。

| 缩写 | 全称 | 一句话解释 |
|------|------|-----------|
| **HDLBits** | -- | 在线 Verilog 练习与评测网站（https://hdlbits.01xz.net/），内置 Quartus 综合 + ModelSim 仿真 judge |
| **Quartus** | Intel Quartus Prime | Intel（原 Altera）的 FPGA 综合与布局布线工具。Set II 用它做综合检查 |
| **ModelSim** | Mentor Graphics / Intel ModelSim | 工业级 Verilog/SystemVerilog/VHDL 仿真器。Set II 在线 judge 用它做功能仿真 |
| **TODAES** | ACM Transactions on Design Automation of Electronic Systems | ACM 的数字设计自动化期刊。本文发表于 TODAES 特刊 |
| **NL** | Natural Language | 自然语言。论文模型表中表示仅用自然语言预训练的模型 |
| **GPT** | Generative Pre-trained Transformer | OpenAI 的大语言模型系列。本文对比 GPT-3.5-turbo 和 GPT-4 |
| **PaLM2** | Pathways Language Model 2 | Google 的大语言模型 |
| **DeepSpeed** | -- | Microsoft 的深度学习训练优化库。CodeGen-16B 微调依赖其 model/data parallelism |
| **System Prompt** | -- | Chat 模型的顶层指令，决定模型的角色和行为，会显著影响 RTL 生成质量（34-41% 差异） |
| **Jaccard** | Jaccard Similarity | 两个集合的交集除以并集。论文用 MinHash 近似 Jaccard 做近重复文件去重 |
| **PyMuPDF** | -- | Python 的 PDF 处理库（fitz 绑定），支持文本提取和 OCR |
| **VCD** | Value Change Dump | 值变化转储，仿真器输出的标准波形文件格式 |

---

## 9. 与芯片流程的关系

> Benchmark 版已覆盖的阶段关系和反例（initial 赋初值、组合环、latch 推断、敏感列表不全、阻塞赋值、CDC 无同步器）不再重复。本节聚焦模型版**因 Set II 引入 Quartus 综合而新增的阶段关系**。

### 9.1 Set II 的 Quartus 综合比 Icarus 编译多了什么

Icarus Verilog（Set I 用的编译器）是一个**仿真器前端**——它编译代码的目标是生成可执行的仿真程序，不是生成门级网表。Quartus（Set II 在线 judge 用的综合器）是一个**综合器**——它编译代码的目标是生成可在 FPGA/ASIC 上实现的网表。这多了几层检查：

```verilog
// Icarus 能编译，Quartus 综合会报错的典型代码：

// 1. initial 块（Icarus 可以，Quartus 报错）
reg [7:0] state;
initial state = 8'h00;    // Icarus 编译通过
                           // Quartus 综合报错：initial block not synthesizable

// 2. 延迟语句（Icarus 可以，Quartus 忽略/报错）
assign #5 out = a & b;     // Icarus 仿真：5 个时间单位后赋值
                           // Quartus 综合报错：delay not synthesizable

// 3. fork/join（Icarus 可以，Quartus 不全部支持）
initial begin
    fork                   // Icarus 仿真：并行执行
        a = 1;             // Quartus 综合：大多不被支持
        b = 0;
    join
end
```

**因此 Set II 的 Compile Error 率高于 Set I 的 compile fail 率**，因为 Set II 多了一道"可综合性"关卡。但论文没有单独对比同模型的 Set I compile rate vs Set II Compile Error rate（两个评测集题目不同，无法直接比较）。

### 9.2 Set II 没有覆盖的阶段问题

即使通过了 Quartus 综合 + ModelSim 仿真，代码仍然可能被后续阶段拦截：
- **STA 阶段**：Quartus 综合能做 FPGA 上的时序分析（TimeQuest），但 HDLBits judge 不 report 时序结果
- **形式验证阶段**：综合后的网表和 RTL 的等价性未被验证
- **PPA**：面积、功耗、性能完全没有被考虑

---

## 10. 讨论与局限

> Benchmark 版已覆盖的局限（语料版权不可追溯、17 题规模小、Pass@(scenario\*n) 非标准 pass@k、evaluator 缺陷、数据污染风险、单文件模块）不再重复。本节聚焦**模型版特有的问题和增量局限**。

### 10.1 论文自述的局限

1. **GPT-4 访问/成本限制**：只能通过 web interface 以 n=1 测试，无法做多候选采样或 temperature sweep。
2. **Set II 的评估不具有本地可复现性**：依赖 HDLBits 在线 judge，testbench 不公开。
3. **CodeGen-16B-FT 在复杂问题上仍然脆弱**：Game of Life 全败、LFSR/truth table/shift-rotate 几乎全败。
4. **领域微调模型需要进一步优化**：未来方向包括 targeted training data、additional iterations、hybrid approaches、domain-specific knowledge 注入。

### 10.2 代码/复现层面的问题

1. **当前仓库没有任何 Set II 相关资产**：没有 163/164/181 道 HDLBits 题目的 prompt 快照、没有每题的 5 份 completion、没有 HDLBits submitter 脚本、没有在线 judge 的返回日志。Set II 的结果在 2026 年**无法从代码重建、无法审计、无法复现**。
2. **Benchmark 版的 evaluator 缺陷依然存在**：advanced3 答案泄漏、L/M/H 目录冲突、get_results.py 只汇总 advanced5、n=20 不是 25。
3. **当前仓库无完整训练脚本/权重**：只有 demo notebook 和 evaluator zip。复现等级：**R1**。

### 10.3 本资料包的批判性分析

1. **Set II 题数的三种口径无法调和**：Section 4.1 说 181、Table 3 caption 说 164、Table 3 分类求和为 163。这种不确定性对 benchmark 的严肃性有致命影响：不知道 GPT-3.5-turbo 的 Pass@(scenario\*n) 值是基于 163、164 还是 181 道题计算的。

2. **GPT-4 的比较协议严重不均衡**：GPT-4 用 n=1, T=0.2（单次 pass@1 下界），CodeGen-16B-FT 用 n=10 + best temperature selection（调参后的上界）。Figure 8 的比较更像是一个**探索性对比**而非**严格对照实验**。

3. **教材消融的 2B/16B 标注冲突**：Section 6 以 CodeGen-2B 定义消融变体，但 Figure 12/13 写 CodeGen-16B。如果是 2B，结论不一定能推广到 16B；如果是 16B，books-only 的极差表现对一个大模型来说出人意料。

4. **Claude 被提及但无数据支撑**：RQ5 提到 Claude，但没有形成与其他模型等量、可核验的主结果表。可能是结果不理想、或通过 Web 界面测试数据采集不规范、或截稿时 API 未普及。

5. **推理时间的不可比性**：混合了本地模型和云端 API（含网络延迟），且控制变量大量缺失。只能用于定性趋势判断——"领域微调的小模型比商业大模型 API 响应快"。

6. **论文内部不一致清单**：(1) Set II 题数：181/164/163；(2) Table 5 caption 写 "Problem Set II" 但实际内容是 Set I 结果；(3) System prompt 段落：先说 minimal 超过 detailed by 53%，随后又说 detailed 一致优于 minimal——内部矛盾；(4) 消融模型：Section 6 写 2B，Figure 12/13 写 16B；(5) 推理时间两处口径不一致（1.994 vs 2.02）；(6) CodeGen-2B-PT 推理时间为 0.000s——更像记录异常而非真实零延迟。

---

## 11. 复现信息

| 项目 | 内容 |
|------|------|
| 论文页 | https://arxiv.org/abs/2308.00708 |
| 代码 | https://github.com/shailja-thakur/VGen，本地 commit `81710f872caf`（与 Benchmark 版共享仓库） |
| 数据集 | Set I：17 题 + 51 prompts + 17 testbenches（本地有）；Set II：HDLBits 在线题目（本地无 prompt/提交脚本/结果日志） |
| 模型权重 | https://huggingface.co/shailja（与 Benchmark 版共享），2B 约 11.23 GB FP32 |
| 本地状态 | 已审计（论文与 artifact 静态核验），Set I 资产存在但 evaluator 代码有多个 bug；Set II 资产完全缺失 |
| 复现等级 | **R1**（静态核验，不是重新推理或重训） |
| 主要门槛 | 1）Set II 资产完全缺失（无 prompt/completion/judge 日志）；2）GPT-3.5/GPT-4/PaLM2 原始 completions 不存在；3）论文 Table/Figure 原始 CSV 不存在；4）16B 训练需 3x A100 + 250GB + 6 天；5）闭源模型 API 已变化（code-davinci-002 已下线，GPT-3.5/GPT-4 版本已更新） |

---

## 12. 一分钟复述版

**VeriGen（2308.00708）是 DATE 2023 Benchmark 版的扩展。** 它把 VGen 的方法论（GitHub + 教材语料微调 CodeGen 等模型）推向更全面的评估：

1. **Set II（HDLBits 在线 judge）**：把评测从 17 题扩展到 163-181 题，首次在 RTL LLM 评测中引入工业级综合器（Quartus）和仿真器（ModelSim），多了可综合性验证。但题数 181/164/163 三种口径无法统一，且当前仓库没有任何 Set II 资产。

2. **闭源大模型比较**：对比 GPT-3.5-turbo、GPT-4、PaLM2。GPT-4 跨题平均分最高（~0.53），但 CodeGen-16B-FT 在 medium-description 切片略高（0.436 vs 0.39），且推理速度约 5 倍（2s vs 10s）。GPT-4 的 Advanced 能力远超其他所有模型（~0.6 vs ~0.29）。

3. **三路语料消融**：books-only 几乎无法工作（Basic Low 0.083），但 combined 在 Low description 上比 GitHub-only 提升约 10%——证明教材的价值在"从匮乏 prompt 推断规格"，而非"教模型写 Verilog 语法"。

4. **Guided system prompt**：给 GPT-3.5 明确的 Verilog autocomplete 角色可提升 34-41% 的通过率。这揭示了 chat 模型评测中 system prompt 作为 hidden variable 的问题。

5. **复杂失败案例**：Game of Life（三个模型全败）、8-bit MUX bug-fixing（CodeGen-16B-FT 胜出）——领域微调对 bug fixing 的价值更多在"定位错误模式"而非"生成修复"。

**它的增量贡献不是模型创新，而是把 2022 年的 RTL LLM 评测框架推进到 2023 年年中的新技术格局——更大规模的在线 benchmark、闭源大模型对比、更细粒度的语料消融和 system prompt 研究。**

---

## 13. 两者关系与区别

本节澄清 VGen/VeriGen 两条工作线的关系，避免读者混淆。

### 13.1 论文身份

| 维度 | Benchmark 版 (2212.11140) | Model 版 (2308.00708) |
|------|--------------------------|----------------------|
| **正式标题** | Benchmarking Large Language Models for Automated Verilog RTL Code Generation | VeriGen: A Large Language Model for Verilog Code Generation |
| **发表** | DATE 2023（7 页短论文） | ACM TODAES 扩展稿（29 页长论文） |
| **arXiv 日期** | 2022-12-13 | 2023-07-28 |
| **作者团队** | NYU + U. Calgary（完全相同） | NYU + U. Calgary + UNSW（Hammond Pearce 转至 UNSW） |
| **代码仓库** | https://github.com/shailja-thakur/VGen | **共享同一个仓库** |

两篇论文是**同一团队在同一个研究方向上不同阶段的产出**——Benchmark 版是 DATE 会议的 7 页短论文，Model 版是 TODAES 期刊邀请的 29 页扩展稿。扩展稿继承了 Benchmark 版的所有基础实验线（数据 pipeline、5 模型微调、17 题 Set I、采样协议、编译/功能双层评测），在此基础上新增了四项内容。

### 13.2 各自贡献

**Benchmark 版（2212.11140）的核心贡献**：
- 建立 Verilog 专用语料构建 pipeline（GitHub BigQuery + 70 本教材 PDF OCR）
- 微调 5 种预训练模型并系统评测
- 设计 17 题 Set I benchmark（三级难度 + 三档 prompt）
- 用 Icarus/testbench 可执行评测代替文本相似度
- 发现领域微调将功能正确率从 1.09% 拉到 27.0%，CodeGen-16B-FT 达 41.9%

**Model 版（2308.00708）的增量贡献**：
- 引入 HDLBits Set II（163-181 题在线 judge），扩大评测规模约 10 倍
- 比较 GPT-3.5-turbo、GPT-4、PaLM2 等新一代闭源大模型
- 三路语料消融（books-only vs GitHub-only vs combined）
- Guided system prompt 实验（量化了 system prompt 对 RTL 生成的 34-41% 影响）
- 推理时间剖面和复杂失败案例分析（Game of Life、8-bit MUX bug-fixing）

### 13.3 关键区别

1. **定位不同**：Benchmark 版是"LLM 能不能写 Verilog？"的首次系统回答；Model 版是"专用微调模型 vs 最新的通用大模型，谁更强？"的比较研究。

2. **数据/模型完全共享**：Model 版**没有重新训练模型**——它的微调模型和数据 pipeline 就是 Benchmark 版的那套。因此 Set I 的实验线在 Model 版中不是"独立新实验"，而是"对已有结果的引用和重新呈现"。

3. **评测体系扩展**：Benchmark 版只有 Set I（本地 Icarus/testbench）；Model 版新增 Set II（远程 HDLBits/Quartus/ModelSim judge）。

4. **对比基线扩展**：Benchmark 版的唯一商业基线是 code-davinci-002；Model 版新增 GPT-3.5-turbo、GPT-4、PaLM2 三个闭源基线。

5. **方法论深化**：Benchmark 版只说"GitHub+books 比 GitHub-only 高 1.4pp"；Model 版把这个消融展开为三路对照，并新增 guided system prompt 实验。

### 13.4 实践建议

- 如果要**理解 RTL LLM 评测的方法论基础**（数据 pipeline、benchmark 设计、可执行评测），先读 Benchmark 版的深度讲解。
- 如果要**了解 2023 年年中时间点上的"专用模型 vs 通用大模型"竞争格局**，读 Model 版的深度讲解。
- 如果只需要一个**关键技术数字**：CodeGen-16B-FT 在 Set I 上的整体功能正确率是 41.9%（来自 Benchmark 版），在 Set II 上对 Multiplexers 类别的 Pass@(scenario\*n) 是 0.653（来自 Model 版）。
- 两篇论文共享同一个 GitHub 仓库（https://github.com/shailja-thakur/VGen），模型权重都在 Hugging Face（https://huggingface.co/shailja），但当前仓库的 evaluator 代码存在多个 bug，无法直接重算论文结果。

---

> 参考：
> - [VeriGen Benchmark 版深度讲解（2212.11140）](./论文深度讲解_VeriGen-Benchmark.md)
> - [VeriGen 论文与代码复现详解](./VeriGen论文与代码复现详解.md)
> - [VeriGen 扩展论文复现详解](./VeriGen扩展论文_2308.00708_论文与代码复现详解.md)
> - [芯片流程（17 阶段标准参考）](../芯片流程.md)
