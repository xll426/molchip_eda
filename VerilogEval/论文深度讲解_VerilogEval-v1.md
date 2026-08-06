# VerilogEval (v1) 论文深度讲解

> **VerilogEval: Evaluating Large Language Models for Verilog Code Generation**
> Mingjie Liu, Nathaniel Pinckney, Brucek Khailany, and Haoxing Ren
> NVIDIA Corporation
> ICCAD 2023 · arXiv:2309.07544v2 (2023-12-10)
> 原文：[2309.07544_VerilogEval.pdf](./2309.07544_VerilogEval.pdf)
> 代码：https://github.com/NVlabs/verilog-eval (release/1.0.0)
> 姊妹篇：[VerilogEval v2 (Revisiting)](./论文深度讲解_VerilogEval-v2.md)

---

## 1. 一句话定位

**VerilogEval 是首个可自动执行的大规模 LLM Verilog 代码生成评测基准：把 156 道人工 HDLBits 题 + 143 道 GPT-3.5 机器生成的题做成统一协议（自然语言描述 $\to$ Verilog 补全 $\to$ Icarus 功能仿真 $\to$ pass@k），并证明用 8,502 条合成 description-code 对做 SFT 能有效提升硬件代码生成能力，GPT-4 在 human 集合上 pass@1 = 43.5%。**

这句话里的 5 个承重点，后面逐一拆解：

1. **156+143 道评测题** — 从 HDLBits 教学网站精选，人工将电路图/波形/状态转移图/Karnaugh 图转写为纯文本描述，同时用 GPT-3.5 从 golden RTL 逆生成 machine 描述形成对照集合。
2. **Icarus 功能仿真判定** — 不用 BLEU 等文本相似度指标，而是把候选 Verilog 与 golden reference 同时接入 testbench，在 Icarus Verilog 下编译仿真，比较瞬态输出是否一致。
3. **pass@k 无偏估计** — 每题生成 $n=20$ 个候选，计算 $k$ 个随机样本中至少一个通过功能仿真的概率；pass@1 衡量单样本成功率，pass@10 衡量"多试几次能不能过"。
4. **8,502 条合成 SFT 数据** — 从 GitHub Verilog 代码中筛选自包含模块，经 MinHash 去重后用 GPT-3.5 为每个模块生成 description-code 对，用于微调 CodeGen 模型。
5. **GPT-4 领先但不高** — 在 human 集合上 pass@1 = 43.5%（machine 上 60.0%），说明即便最强商业模型离"可靠地写对 Verilog"还有显著差距；CodeGen-16B-Verilog-SFT 性能与 GPT-3.5 相当。

---

## 2. EDA 阶段映射（①-⑰）

参照 [芯片流程.md](../芯片流程.md) 的 17 阶段标准编号：

| 阶段 | 覆盖 | 说明 |
|------|:---:|------|
| **① RTL 设计** | ✅ **核心** | 模型的全部任务：根据自然语言描述 + 固定 `module` 头补全 RTL 模块体，等价于芯片流程中"工程师写 Verilog" |
| **② RTL 功能仿真** | ✅ | 用 Icarus Verilog 跑 testbench 的瞬态仿真，比较候选输出与 golden reference 是否一致——"逻辑对不对"的验证 |
| ③ 逻辑综合 | ❌ | 不生成门级网表，不对 RTL 做可综合性检查 |
| ④ 门级仿真 | ❌ | 没有综合，不存在门级网表，不跑带时序反标的仿真 |
| ⑤ STA（静态时序分析） | ❌ | 不关心时序收敛，不计算 setup/hold slack |
| ⑥ 形式验证 | ❌ | 仅靠仿真激励覆盖，不做形式等价性检查 |
| ⑦ 布局规划 (Floorplan) | ❌ | 全部在 RTL 层操作，不涉及物理设计 |
| ⑧ 标准单元摆放 (Placement) | ❌ | `--` |
| ⑨ 时钟树综合 (CTS) | ❌ | `--` |
| ⑩ 布线 (Routing) | ❌ | `--` |
| ⑪ 后仿真 | ❌ | `--` |
| ⑫ 物理验证 (DRC + LVS) | ❌ | `--` |
| ⑬ 签核 (Signoff) | ❌ | `--` |
| ⑭ 流片 | ❌ | `--` |
| ⑮ 制造 | ❌ | `--` |
| ⑯ 封装 + 测试 | ❌ | `--` |
| ⑰ 芯片到手 | ❌ | `--` |

**覆盖率：2/17。** 这篇论文只覆盖芯片流程最前端的"设计 $\to$ 仿真"闭环，且仿真深度仅到"功能正确性判断"，不涉及可综合性、PPA 评估和时序分析。

> 最容易误读的边界：论文声称的"功能正确"仅由 testbench 覆盖的有限激励周期内的输出一致性定义，并不等价于形式等价的"数学正确"。一段代码可能通过仿真但不可综合（如含 `$display`、隐式 latch），也可能综合后行为不同（如 X/Z 传播策略差异）。

---

## 3. 输入 / 输出

### 3.1 输入

评测任务由三部分拼接成 prompt 送给 LLM：

```
[可选 System Prompt]
You only complete chats with syntax correct Verilog code. End the
Verilog module code completion with 'endmodule'. Do not include
module, input and output definitions.

[固定 Question Prompt]
Implement the Verilog module based on the following description. Assume
that signals are positive clock/clk edge triggered unless otherwise stated.

[自然语言 Problem Description + 模块头]
Given an 8-bit input vector [7:0], reverse its bit ordering.
module top_module (
    input [7:0] in,
    output [7:0] out
);
```

论文提供两类描述来源的输入：

| 集合 | 数量 | 描述来源 | 特点 |
|---|---:|---|---|
| **VerilogEval-human** | 156 题 | 人工把 HDLBits 页面整理为纯文本：状态转移图用边列表、Karnaugh 图转表格、电路图转自然语言、波形图按时钟边沿逐周期描述 | 接近真实题目，含天然歧义 |
| **VerilogEval-machine** | 143 题 | GPT-3.5 根据 golden RTL 自动生成描述，再经"LLM 能否根据该描述写出正确代码"筛选（零样本 108 题通过，4-shot 又筛出 35 题） | 更详细、更接近代码语义，天然低歧义 |

采样配置：temperature = 0.8，top-p = 0.95，上下文长度 2048，每题生成 $n=20$ 个候选。

Machine 描述的筛选过程值得注意：它不是简单的"生成即可用"。156 题首轮零样本生成描述后，对每题采样最多 100 个代码解答；108 题得到至少一个通过解答。剩余题目用已验证描述作为 4-shot 示例，每描述采 8 个解答，又筛出 35 题。因此 machine 集合有强烈的**选择偏差**：能留下来的描述必须"可被当时的 GPT-3.5 解出"，这导致 machine 上的分数系统性偏高。

### 3.2 中间产物

评测器运行的中间文件：

- 拼接后的 `.sv` 文件：`testbench + problem["prompt"] + completion`，组成完整的 SystemVerilog 待测设计
- Icarus 编译产物 `test.vvp`：由 `iverilog -Wall -Winfloop -Wno-timescale -g2012 -s tb` 生成
- 仿真输出 `stdout`：关键行 `Mismatches: N in M samples`，$N=0$ 即通过

### 3.3 输出

模型输出仅为 **Verilog 模块体补全**（不重复端口声明），例如对上述 bit-reversal 题的正确输出：

```verilog
    assign {out[0],out[1],out[2],out[3],out[4],out[5],out[6],out[7]} = in;
endmodule
```

评测器最终输出：每题 pass/fail 状态 + 跨题聚合的 **pass@1 / pass@5 / pass@10** 指标。

---

## 4. Benchmark 构建方法

### 4.1 整体 Pipeline

```text
          HDLBits 网站（156 题）               GitHub Verilog 语料
                │                                      │
    ┌───────────┴────────────┐                Pyverilog AST 提取
    │                        │                + 关键字/长度过滤
    ▼                        ▼                + MinHash 去重 (Jaccard=0.8)
 人工整理                 GPT-3.5 生成              │
 状态图→边列表            描述+筛选              自包含模块
 K-map→表格               零样本: 108 题            │
 波形→逐周期表            4-shot: +35 题      GPT-3.5 按模板生成描述
 电路图→自然语言          最终: 143 题        4 个 Human few-shot 示例
    │                         │                     │
    ▼                         ▼                     ▼
VerilogEval-human         VerilogEval-machine   8,502 条 SFT 数据
  (156 题)                   (143 题)          (description + code)
    │                         │
    └──────────┬──────────────┘
               ▼
     JSONL 格式：task_id + prompt + canonical_solution + test
               │
               ▼
          LLM 采样（n=20, T=0.8, top_p=0.95）
               │
               ▼
   test + prompt + completion → Icarus 编译 → vvp 仿真
               │
               ▼
     解析 "Mismatches: N in M samples"
               │
               ▼
     pass@1 / pass@5 / pass@10（无偏估计）
```

对应论文 Figure 1：在一个 Docker 沙箱容器中运行 Icarus Verilog，实现可复现的自动评测。

### 4.2 题目来源与筛选

论文从 HDLBits 教学网站精选 156 道自包含（self-contained）Verilog 题目，覆盖：

- 基础：wire、常量、逻辑门、向量、位选择、归约运算
- 组合逻辑：多路选择器、加法器、Karnaugh map、真值表
- 时序逻辑：D 触发器、计数器、移位寄存器、LFSR
- 高阶：有限状态机（FSM）与较复杂时序控制

筛选原则：题意相对明确、可表示为纯文本、顶层模块不实例化其他用户模块。论文明确承认模块实例化是 Verilog 系统设计的重要能力，但不在此基准范围内。

### 4.3 Human 描述的文本化策略

HDLBits 原始题目大量依赖非文本模态。论文采用不同的文本化策略：

| 原始形式 | 文本化方法 |
|---|---|
| 电路原理图 | 用自然语言描述各逻辑门的连接关系 |
| 状态转移图 | 边列表格式：`StateA (0) --1--> StateB`（见图 4 经 ChatGPT 指导确认） |
| 布尔逻辑表 / Karnaugh 图 | 转写为表格形式的文字描述 |
| 时序波形图 | 按时钟边沿逐周期列举所有信号值，加时间列 |
| 时钟/复位极性 | 明确说明 posedge/negedge、active high/low、synchronous/asynchronous |

### 4.4 合成 SFT 数据构造

此部分虽非 benchmark 必需组件，但论文将其作为独立贡献。从公开 GitHub Verilog 语料中：

1. 用 Pyverilog 提取 AST，筛选自包含模块（含 `module`/`endmodule`、位于代码首尾）
2. 过滤规则：模块 $\leq$ 200 行、$\leq$ 1024 tokens、至少含一个 `always`/`assign`/`always_ff`/`always_comb`/`always_latch` 关键字、无模块实例化
3. MinHash 近似去重（Jaccard 阈值 0.8）
4. 用 GPT-3.5 + 4 个 VerilogEval-human 示例（shift18、rule110、lemmings1、fsm3onehot）为每个模块生成自然语言描述
5. 最终得到 **8,502 条 description-code 对**（11MB，相比之下 GitHub Verilog 原始语料约 700MB）

---

## 5. 关键公式

### 5.1 pass@k 无偏估计

这是论文最核心的公式，来自 HumanEval [Chen et al., 2021]：

$$
\text{pass@k} := \mathbb{E}_{\text{Problems}} \left[ 1 - \frac{\binom{n-c}{k}}{\binom{n}{k}} \right]
$$

- $\text{pass@k}$：$k$ 个随机采样中至少一个通过功能仿真的期望概率
- $n$：每题的候选生成总数（论文中 $n = 20$）
- $c$：$n$ 个候选中通过功能仿真的个数（$c \leq n$）
- $\binom{n-c}{k}$：从 $n-c$ 个失败候选里无放回取 $k$ 个的组合数
- $\binom{n}{k}$：从 $n$ 个总候选里无放回取 $k$ 个的组合数

**工程直觉**：$\frac{\binom{n-c}{k}}{\binom{n}{k}}$ 是"随机抽 $k$ 个全部失败"的概率，$1 -$ 它就是"至少一个成功"。对所有题求期望再平均，即为无偏估计量。代码中为了避免大组合数计算，使用乘积形式：

```python
1.0 - np.prod(1.0 - k / np.arange(n - c + 1, n + 1))
```

**为什么这么设计**：BLEU 等基于 n-gram 共现的文本相似度指标不适用于 Verilog 代码评测。同一电路可以有很多文本差异巨大的正确实现（如 `assign y = sel ? b : a` 与 `assign y = (sel & b) | (~sel & a)` 等价），高 BLEU 不保证功能正确，低 BLEU 也不代表电路错误。论文 Figure 6 用 CodeGen-16B-Verilog 的实验证明：正确解与错误解的 BLEU 概率密度分布几乎不可分。

### 5.2 功能正确性判定

论文的功能判定逻辑是将 `testbench + prompt + completion` 拼接后在 Icarus Verilog 下仿真，比较候选 DUT 与 golden reference 在相同激励下的输出：

- 组合电路：在输入信号每次变化时验证输出匹配
- 时序电路：在时钟沿（posedge/negedge）验证输出匹配
- 通过条件：testbench 输出 `Mismatches: 0 in M samples`

这个判定方式等价于：**候选在给定的 testbench 激励空间上的行为与 golden reference 完全一致**。

---

## 6. 评测协议与打分

### 6.1 评测协议

评测器（VerilogEval v1 evaluator）的核心调用链：

```text
evaluate_functional_correctness CLI
    ↓
evaluation.evaluate_functional_correctness()
    ↓ 进程池并行为每个 sample
execution.check_correctness(problem, completion)
    ↓
拼接 test + prompt + completion → <task_id>.sv
    ↓
iverilog -Wall -Winfloop -Wno-timescale -g2012 -s tb -o test.vvp
    ↓
vvp -n test.vvp
    ↓
解析 stdout: "Mismatches: N in M samples"
    ↓
N=0 → passed, 写入 *_results.jsonl
    ↓
estimate_pass_at_k() 对各题求均值 → pass@k
```

几个重要的实现细节：

1. **安全门控**：v1 `execution.py` 将真正的 `iverilog`/`vvp` 调用放在三引号注释字符串中，默认不执行。使用者必须阅读安全警告、准备隔离沙箱后手动启用。这是有意为之，不是 bug。
2. **错误处理优先级**：`stderr` 含 `syntax error` $\to$ syntax failure；其他非空 `stderr` $\to$ compile failure；`stdout` 匹配 `Mismatches: N in M samples`，$N=0$ 即 pass。
3. **限制**：除 syntax 特例外，**任何 `stderr` 都按编译失败处理**——某些不影响功能的 warning 也可能被归入失败；结果依赖 Icarus 版本和日志格式。

### 6.2 SFT 实验设置

论文将 8,502 条合成数据用于监督微调 CodeGen 系列模型：

| 参数 | 值 |
|---|---|
| 优化器 | Adam ($\beta_1 = 0.9$, $\beta_2 = 0.999$, $\epsilon = 10^{-8}$) |
| 学习率 | $2 \times 10^{-5}$ |
| 有效 batch size | 1M tokens |
| Weight decay | 0 |
| 上下文长度 | 2048 |
| SFT epoch (multi 模型) | 10 |
| SFT epoch (verilog 模型) | 5 |
| 硬件 | 1 个 DGX 节点，8$\times$A100，2TB RAM |

评测模型基线：

- **codegen-nl**：在 ThePile（825.18GB 英文语料）上预训练的自然语言模型
- **codegen-multi**：从 codegen-nl 初始化，在 BigQuery 多语言代码（C/C++/Go/Java/JS/Python）上继续训练
- **codegen-verilog**：从 codegen-multi 初始化，在约 300MB GitHub Verilog + 400MB 教科书数据上继续训练

### 6.3 关键实验结果

**GPT 模型 vs CodeGen-16B-Verilog-SFT（VerilogEval-human + machine）：**

| 模型 | Machine pass@1 | pass@5 | pass@10 | Human pass@1 | pass@5 | pass@10 |
|---|---:|---:|---:|---:|---:|---:|
| GPT-3.5 | 46.7 | 69.1 | 74.1 | 26.7 | 45.8 | 51.7 |
| **GPT-4** | **60.0** | 70.6 | 73.5 | **43.5** | **55.8** | **58.9** |
| CodeGen-16B-Verilog-SFT | 46.2 | 67.3 | 73.7 | 28.8 | 45.9 | 52.3 |

这张表说明：GPT-4 在两个集合上均大幅领先；machine 上的分数系统性高于 human（因为 machine 描述天然低歧义且经模型可解性筛选）；CodeGen-16B-Verilog-SFT 性能与 GPT-3.5 相当。

**底模对比（VerilogEval-machine, 16B）：**

| 模型 | pass@1 | pass@5 | pass@10 |
|---|---:|---:|---:|
| CodeGen-16B-NL-SFT | 33.9 | 51.9 | 58.1 |
| CodeGen-16B-Multi-SFT | 37.1 | 55.0 | 61.1 |

从自然语言模型到多语言代码模型的预训练迁移仅提升约 3 个百分点，说明 C++/Python 等软件语言到 Verilog 的知识迁移有限，Verilog 预训练语料的重要性远超通用代码能力迁移。

**SFT 数据质量消融（CodeGen-2B-Verilog, VerilogEval-machine）：**

| 模型 | pass@1 | pass@5 | pass@10 |
|---|---:|---:|---:|
| CodeGen-2B-Verilog (base) | 20.1 | 46.0 | 55.9 |
| + 正确 SFT | **35.9** | **59.0** | **65.7** |
| + 错配 SFT (sft-error) | 21.4 | 38.8 | 46.1 |

错配数据将描述随机打乱与错误代码配对，导致 pass@5/10 甚至低于底模。这说明"数据质量比数量更重要"——模型可能学到表面 Verilog 风格却破坏问题-实现对应关系。

**SFT epoch 趋势（Figure 8）：**

随着 SFT epoch 增加，pass@1 持续提升但 pass@5/10 下降或停滞。这表明模型过拟合到 SFT 数据后输出多样性退化：对简单题更自信（pass@1 提升），但丧失了探索不同解法的能力（pass@5/10 下降）。论文因此建议后对齐模型应同时报告 pass@1 和 pass@5/10。

**模型规模消融（Figure 9）：**

论文在 350M/2B/6B/16B 四个规模级别上评测了 multi 和 verilog 基线的 SFT 效果：

- **更大模型普遍更强**：16B 模型在所有 k 值上显著优于 2B/6B。codegen-16B-multi-SFT 在 VerilogEval-machine 上 pass@1 = 37.1%、pass@5 = 55.0%、pass@10 = 61.1%；codegen-2B-multi-SFT 对应为 19.6%/40.3%/50.6%。
- **SFT 收益在 multi 模型上更显著**：multi 模型原本未在 Verilog 语料上训练，SFT 起到"首次接触硬件语义"的作用，提升幅度大（pass@1 约翻倍）。verilog 模型已预训练过 Verilog 语料，SFT 主要做对齐（alignment），在 VerilogEval-machine 上提升明显（+15--20 个百分点），但在 VerilogEval-human 上提升有限甚至有轻微退化。
- **350M 模型结果被省略**：因为 pass rate 太低无法统计显著，论文没有报告该级别的具体数字。

**Human vs Machine 差异在不同模型上的表现：**

一个值得注意的模式是：SFT 在 machine 上的提升总是大于 human。例如 codegen-16B-verilog-SFT 在 machine 上 pass@1 从 base 的 35% 左右提升到 46.2%（+11 个百分点），但在 human 上仅从约 27% 提升到 28.8%（+2 个百分点）。论文将此归因于 SFT 数据与 machine 描述的分布更接近——两者都由 GPT-3.5 根据代码生成，而 human 描述包含 machine 数据中缺失的"状态转移图的边列表格式""波形逐周期表格"等异构文本模式。这里的核心洞察是：**SFT 数据的分布和评测数据的分布如果不一致，微调收益会高度不均匀**，SFT 的"泛化"只在数据分布覆盖的方向上有效。

**pass@k 的采样方差与 n 的选择（Figure 7）：**

论文用 codegen-16B-verilog 的输出数据分析了不同 $n$ 下 pass@k 估计的方差。关键发现：

- 当 $n < 10$ 时，pass@10 的估计极其不稳定（置信区间宽达 20+ 个百分点）
- $n = 20$ 对于 pass@1 和 pass@5 已足够（方差可接受），但对 pass@10 仍有显著方差
- 论文推荐 $n \geq 20$ 作为基本要求，更大的 $n$（如 100 或 200）能进一步减小估计方差但不改变均值
- 这个分析说明：**报告的 pass@k 数字本身含有不可忽略的估计噪声**，跨论文比较 2--3 个百分点的差异时需考虑采样方差

---

## 7. 创新点

### 创新点 1：首个大规模、可自动执行的 LLM Verilog 生成公开 benchmark

在此论文之前，Verilog 生成评测存在三个痛点：题量少（如 RTLLM 仅 30 题）、题目/prompt/测试方法不统一、依赖文本相似度（BLEU）判定正确性。VerilogEval 一次性解决了这三个问题：156+143 题的规模、统一的 prompt 和 testbench 协议、基于 Icarus 功能仿真的自动判定——把 HumanEval 的"功能正确性评测"范式迁移到硬件代码领域。

### 创新点 2：Human vs Machine 描述双集合

首次系统研究描述来源（人工整理 vs LLM 从 golden 代码逆生成）对模型性能的影响。machine 描述天然低歧义且经模型可解性筛选，导致分数系统性偏高——这本身是一个重要发现：**benchmark 的描述质量决定分数上限，仅靠"高分"判断模型好坏有误导风险**。这个发现直接催生了后续 v2 移除 machine 集合的决定。

### 创新点 3：LLM 自举合成 SFT 数据

用 GPT-3.5 从 GitHub Verilog 代码自包含模块反向生成 8,502 条 description-code 对，以 11MB 的 SFT 数据量（相比原始 GitHub Verilog 的约 700MB）显著提升 CodeGen 的 pass@k。这为硬件领域"高质量标注数据稀缺"提供了低成本扩数据范式：用商用 LLM 生成 description，用开源代码作为 code，不依赖人工标注。

### 创新点 4：系统消融揭示训练关键因素

论文完整比较了模型规模（350M/2B/6B/16B）、底模语料（nl/multi/verilog）、SFT epoch 和数据正确性对 pass@k 的影响。三个关键发现：(1) 更大模型普遍更强；(2) 多语言代码预训练对 Verilog 的迁移约 +3%，Verilog 领域语料才是关键；(3) pass@1 与 pass@5/10 在过拟合后出现背离，评测需同时报告两者。

---

## 8. EDA 缩写表

| 缩写 | 全称 | 一句话解释 |
|---|---|---|
| RTL | Register-Transfer Level（寄存器传输级） | 用 always/assign/reg 描述寄存器间数据流动的硬件行为代码层级 |
| EDA | Electronic Design Automation（电子设计自动化） | 用软件工具辅助芯片设计、验证、制造的一整套方法论 |
| HDL | Hardware Description Language（硬件描述语言） | 描述数字电路行为的编程语言，Verilog/SystemVerilog/VHDL 是主流 |
| FSM | Finite State Machine（有限状态机） | 由状态寄存器 + 转移逻辑组成的时序电路范式，HDLBits 常见题型 |
| LLM | Large Language Model（大语言模型） | 基于 Transformer 的自回归语言模型，如 GPT-4、CodeGen |
| SFT | Supervised Fine-Tuning（监督微调） | 用标注好的输入-输出对微调预训练模型，使其适应特定任务 |
| BLEU | Bilingual Evaluation Understudy（双语评估基准） | 基于 n-gram 共现的文本相似度指标，源自机器翻译，被本文明确弃用 |
| PPA | Power, Performance, Area（功耗/性能/面积） | 芯片设计的三个核心优化目标，本文完全不评估 |
| ICL | In-Context Learning（上下文学习） | 在 prompt 中放置少量示例让模型模仿，不更新权重（v2 引入） |
| MinHash | MinHash | 用于近似集合去重的哈希技术，Jaccard 阈值 0.8 表示两段代码 80% 相似即视为重复 |
| AST | Abstract Syntax Tree（抽象语法树） | 代码的树形结构化表示，Pyverilog 用于提取 Verilog AST |
| JSONL | JSON Lines | 每行一个 JSON 对象的文本格式，v1 评测数据存储格式 |

---

## 9. 与芯片流程的关系

### 9.1 在全流程中的位置

VerilogEval 覆盖 17 阶段中仅前 2 步：**① RTL 设计**（接自然语言 spec，出 Verilog 模块）和 **② RTL 功能仿真**（接 Verilog 模块，出 pass/fail 判定）。它不接手任何上游产出，也不交棒给下游综合/布局布线工具。

在真实芯片流程中，VerilogEval 模拟的是"工程师根据 spec 写 RTL + 用 testbench 验证逻辑"这个日常循环。它把这一步做成 LLM 可重复评测的协议，是 LLM 进入芯片设计流程的**入门验证场**。

### 9.2 "仿真通过"和"能做成芯片"之间隔着什么

这是本资料包特别强调的边界。VerilogEval 的"正确"仅指：

1. **testbench 覆盖的激励范围内**行为一致（数百到数千个时钟周期）
2. **Icarus 这个特定仿真器**下的行为一致
3. **功能层面**一致，不保证可综合性

距离"能做成芯片"还缺至少 5 层验证：

- **可综合性**：仿真通过的代码可能包含不可综合语法（如 `$display`）、隐式 latch、多驱动冲突
- **时序收敛**：不检查 setup/hold slack，不评估最大工作频率
- **PPA 达标**：不评估功耗、面积、吞吐率是否满足 spec
- **形式等价**：仿真覆盖率不等于数学等价，testbench 可能遗漏 corner case
- **物理实现**：综合后的门级网表、布局布线后的寄生参数会改变行为

因此 VerilogEval 的定位是**"前端第一道门"**：通过它只说明模型学会了写小模块的逻辑，不代表能进真实流片流程。

---

## 10. 评测公平性与可信度分析

### 10.1 描述来源偏差

machine 描述从 golden RTL 逆生成，再经"模型能否根据描述写出正确代码"筛选，存在严重的**选择偏差**和**内循环效应**：

- 描述与代码天然更匹配（描述就是看着代码写的）
- 无法被 GPT-3.5 解出的描述被淘汰（留下的都是"可解"的）
- 同一个 LLM（GPT-3.5）既生成描述又用于解题，形成闭环

Human 描述才是真实 spec 的不完备性的反映：它包含从电路图/波形/状态图人工转写时的信息损失和歧义。因此 human 分数更低但更可信，machine 分数虚高但更适合作为"模型是否能理解低层编码指令"的上限测试。

### 10.2 数据污染风险

HDLBits 是一个公开的在线教学网站，题目在网上流传多年。2023 年后大量论文引用 VerilogEval，训练数据中极可能已包含这些题目和解答。因此 2026 年继续用 VerilogEval-human 作为"零污染"评测集已不可信——任何模型在这些题目上的高分都可能部分来自记忆而非推理。

### 10.3 采样协议敏感性与结果可复现性

论文采用 $T=0.8$, $n=20$ 的采样协议。pass@k 的无偏估计依赖足够大的 $n$：$n$ 太小时方差大（论文 Figure 7 展示 $n=5$ 时 pass@10 的估计极不稳定）。但即便 $n=20$，不同随机种子、不同 API 调用时间的模型输出也可能有差异。

此外，v1 evaluator 存在几个影响可复现性的细节：
- 默认不执行 Icarus（安全门控），需手动启用
- 全局 `pkill iverilog/vvp` 可能误杀共享环境中的其他仿真任务
- 任何 `stderr` 都算编译失败（包含无关 warning）
- 依赖 Icarus 版本（不同版本的 warning/error 文本可能不同）

### 10.4 pass@k 指标的适用范围

pass@k 来自软件编程评测（HumanEval），其核心假设是"多次尝试中有一次通过即算解决"。这对交互式编码助手（如 Copilot）的使用场景（用户可多次生成、选取）是合理的。但在硬件设计中，"生成 20 个候选、跑 20 次仿真、人工筛选"的工作量远超直接从零编写。因此 pass@1 才是更贴近硬件设计实际工作流的指标，pass@10 更多反映"模型输出中含正确答案的概率"而非"实际可用性"。

### 10.5 Icarus 仿真的局限

Icarus Verilog 是教学级仿真器，不实现 IEEE-1364 标准的全部特性。论文明确承认"评测受限于仿真器支持的特性"。此外，Icarus 对 X/Z 传播、隐式 latch 等"仿真能过但综合有问题"的代码可能表现出与商业仿真器不同的行为。

### 10.6 评测作为一种协议——对后续工作的影响

VerilogEval 确立的范式——"功能仿真判正确 + pass@k 指标 + 双描述集"——本质上是一套**评测协议**而非单纯的分数排行榜。理解这一点对正确引用 VerilogEval 至关重要：

1. **协议的稳定性比绝对值重要**：VerilogEval 的价值不在于"GPT-4 是 43.5%"，而在于它提供了统一协议让后续模型可在同一条件下比较。任何偏离协议（改 prompt、换仿真器、用不同 Icarus 版本、修改后处理逻辑）的比较都必须显式声明。
2. **题目集合的"天花板效应"**：156 道 HDLBits 教学题的上限是有限的。v1 发布时 GPT-4 的 machine pass@10 = 73.5%，已接近"20 次中至少 1 次通过"的饱和。到 2026 年，agent 方法（VerilogCoder、MAGE）的 pass@1 已超 94%，说明该题目池对顶尖方法的区分度已耗尽。
3. **从 benchmark 到 ecosystem**：VerilogEval 开创的不是一个 top-1 排行榜，而是一套方法论和工具链。后续工作——RTLLM、ChipBench、CVDP、RealBench——都是在 VerilogEval 的基础上根据各自的评测需求做出的"协议变体"，而非独立体系。这体现了 VerilogEval 作为"基准基准（meta-benchmark）"的历史价值。
4. **fair comparison checklist**：任何声称"在 VerilogEval 上达到 X%"的结果，应同时报告：VerilogEval 版本（v1/v2）、描述集合（human/machine）、任务类型（code completion/spec-to-RTL）、采样参数（$T$/top-p/$n$）、后处理方式、Icarus 版本、是否允许多轮/agent/反馈。不写这些条件，只写百分比，没有可比意义。

### 10.7 对本资料包其他论文的启示

VerilogEval 作为资料包中多个 RTL 生成论文的共同评测底座，其设计选择直接影响了后续工作的报告口径：

- **[VerilogCoder](../VerilogCoder/论文深度讲解.md)**：报告 94% pass@1 时使用了 testbench/仿真日志/波形反馈的多轮 agent 循环，这与 v1 的单轮 20-sample 协议是不同资源条件下的结果。不能直接将 94% 与 v1 的 43.5% 对比并宣称"模型能力提升 50 个百分点"——提升的来源是 agent 架构 + 验证反馈，而非底层 LLM 能力的等幅跃迁。
- **[MAGE](../MAGE/论文深度讲解.md)**：类似地，95% pass@1 来自多候选 RTL + judge agent + debug agent 的迭代闭环，资源条件同样与 v1 不可比。
- **后续 benchmark（RTLLM、ChipBench、CVDP、RealBench）**：均直接或间接以 VerilogEval 为 baseline，但各自修改了题目池、任务形态或评测协议。跨 benchmark 比较时需逐一确认协议差异。

---

## 11. 复现信息

| 项目 | 内容 |
|---|---|
| 论文页 | https://arxiv.org/abs/2309.07544 |
| 代码 | https://github.com/NVlabs/verilog-eval (release/1.0.0, commit `4fa0ac4`) |
| 评测数据 | 156 (human) + 143 (machine) 题，v1 分支 `data/` + `descriptions/` |
| SFT 数据 | **未公开**（8,502 对仅论文描述） |
| SFT 训练脚本/权重 | **未公开** |
| 论文原始 samples/logs | **未公开** |
| 复现等级 | 评测数据和 evaluator 代码可静态核清 (R1)；Icarus 执行有条件复现 (R2)；SFT 实验不可复现 (R0) |
| 主要门槛 | Icarus v12 + Docker 容器 + 安全隔离环境；SFT 需自有数据、8$\times$A100 算力和完整训练 pipeline |

---

## 12. 一分钟复述版

1. VerilogEval 把 "自然语言硬件题 $\to$ Verilog 补全 $\to$ Icarus 仿真 $\to$ pass@k" 做成统一评测协议。
2. 156 道人工描述题（VerilogEval-human）+ 143 道 GPT-3.5 机器生成描述题（VerilogEval-machine），全部来自 HDLBits 教学网站。
3. 不用 BLEU/文本相似度，用 Icarus 功能仿真比较候选与 golden 的瞬态输出——仿真通过才是"功能正确"。
4. pass@k 公式：$\text{pass@k} = \mathbb{E}[1 - \binom{n-c}{k}/\binom{n}{k}]$，$n=20$，报告 $k=1,5,10$。
5. GPT-4 领先：human pass@1 = 43.5%、machine pass@1 = 60.0%；CodeGen-16B-Verilog-SFT 追平 GPT-3.5。
6. 从 GitHub Verilog 筛选自包含模块，用 GPT-3.5 逆生成 8,502 条 description-code 对做 SFT，11MB 数据显著提升 CodeGen 性能。
7. 三个关键消融：(a) 多语言代码预训练迁移仅 +3%；(b) pass@1 与 pass@5/10 趋势可背离（过拟合衰减多样性）；(c) 错误配对 SFT 数据伤害超过无数据。
8. machine 描述经模型可解性筛选，分数系统性偏高，不能等同于真实 spec 下的模型能力。
9. 已带动 VerilogEval v2 升级（spec-to-RTL + ICL + 失败分类），详见 [姊妹篇](./论文深度讲解_VerilogEval-v2.md)。
10. 局限：电路规模小（无实例化）、不保可综合/PPA/时序、HDLBits 公开数据已污染、SFT 数据/权重/训练代码未开源。
