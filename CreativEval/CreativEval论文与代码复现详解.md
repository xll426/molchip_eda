# CreativEval：论文、代码、创造性指标与开放复现边界详解

> 论文：*CreativEval: Evaluating Creativity of LLM-Based Hardware Code Generation*  
> 作者：Matthew DeLorenzo、Vasudev Gohil、Jeyavijayan Rajendran  
> 版本：arXiv `2404.08806v1`，2024-04-12  
> 本地原文：[2404.08806_CreativEval.pdf](./2404.08806_CreativEval.pdf)  
> 官方论文页：<https://arxiv.org/abs/2404.08806>  
> 官方 PDF：<https://arxiv.org/pdf/2404.08806>  
> 上游代码：<https://github.com/matthewdelorenzo/CreativEval>  
> 本地 commit：`435e0f687581583576f600119a9f8a3a4acea03b`  
> 审计日期：2026-08-02

---

```text
┌─────────────────────────────────────────────────────────────────────────────┐
│ P1 任务定义                                                                   │
├─────────────────────────────────────────────────────────────────────────────┤
│ Input    │ HDLBits 风格单模块 prompt；flexibility 题额外给 golden 实现并要求 │
│          │ 改写；elaboration 题额外给若干小模块并要求组合大模块            │
├──────────┼────────────────────────────────────────────────────────────────┤
│ Output   │ 每题 10 份采样 Verilog 候选                                     │
├──────────┼────────────────────────────────────────────────────────────────┤
│ Supervision │ Icarus testbench 功能正误；GNN4IP 与 golden 的 cosine         │
│          │ similarity；elaboration 子模块使用检查                          │
├──────────┼────────────────────────────────────────────────────────────────┤
│ Why-hard │ “创造性”定义难；F/X/O 在至少成功一次题上平均造成条件偏差；      │
│          │ 单一 golden reference、GNN 领域迁移、温度/配置漂移、缺统一 runner│
└─────────────────────────────────────────────────────────────────────────────┘
```

## 0. 先给结论

CreativEval 很适合组会分享，因为它问了一个 VerilogEval、RTLLM 等工作很少正面回答的问题：

> LLM 生成的 RTL 不仅要“功能正确”，还要不要具备提出不同实现、改写已知实现、偏离常规模板和组合已有模块的能力？

论文把认知科学中的四个 divergent-thinking 维度映射到 RTL：

| 维度 | 在论文中的 RTL 含义 |
|---|---|
| Fluency | 同一规格能产生多少功能正确、相似度值不同的实现 |
| Flexibility | 看过 golden implementation 后，能否写出功能正确且明显不同的替代实现 |
| Originality | 功能正确实现与 golden implementation 有多不相似 |
| Elaboration | 能否利用给定的小模块组成更大的功能模块 |

论文评价 CodeLlama-7B/13B、VeriGen-6B/16B、GPT-3.5 和 GPT-4，并报告 GPT-3.5 的综合 creativity 最高。

当前仓库比 README 看起来更有内容：

- 111 个单模块 prompt/testbench 目录；
- 9 个多模块 elaboration 题；
- 110 份单模块 golden solution；
- 9 份 elaboration solution；
- 49 MiB 左右的作者历史 CSV、LLM 日志和 GNN4IP similarity 日志；
- 一套改自 HW2VEC/GNN4IP 的 DFG→GNN embedding→cosine similarity 代码；
- 一个 7.6 KiB 的 GNN 权重和对应配置。

但仓库仍是 supporting material，而不是可直接执行的 benchmark package。最重要的开放边界是：

1. README 只有一句 WIP；
2. 实验脚本绑定作者机器的 `/mnt/shared-scratch/...` 绝对路径；
3. 没有统一入口，也没有一条命令从 120 题重建 Table I；
4. 论文说所有模型温度 `0.3`，多数公开 fluency/originality 脚本却写 `0.7`；
5. 四个指标存在多个阈值实现：论文 flexibility 用 `s<0`，辅助脚本又出现 `<0.5` 和 piracy diagnostic 的 `|s|<0.6`；
6. 保存 artifact 能重建全部 fluency，但 functionality 和 CodeLlama-7B originality 与论文表存在漂移；
7. creativity 总分不包含 functionality，而且多个指标只在“至少成功一次”的题上计算，存在条件选择偏差。

本轮没有重复加载六个大模型，也没有重新跑 Icarus/GNN。当前等级应是：

> **R1：论文、数据、源码和作者历史 artifact 已完成代码级/统计级核对，未完成新执行。**

机器可读审计见：[runs/static_audit_20260802.json](./runs/static_audit_20260802.json)。

---

## 1. 证据口径

为了避免把“论文结果”“作者保存日志”和“本轮实测”混为一谈，本文采用四层证据：

| 标签 | 含义 | 本文实例 |
|---|---|---|
| 论文报告 | 原文定义和 Table I | GPT-3.5 creativity = 0.2201 |
| 源码事实 | 当前 commit 的真实实现 | GPT fluency 脚本 temperature = 0.7 |
| artifact 重计数 | 对作者 CSV/log 的只读重算 | 六模型 fluency 均可从 similarity log 重建 |
| 本地执行 | 本轮真正启动模型/仿真/GNN | 本轮没有 |

仓库的 `results_data_tmp3/` 是作者发布的历史结果。本文可以说“已重计数”，不能说“本轮已重新推理 7,200 次”。

当前项目也没有 `模型推理.md`；之前工作区中的推理记录主要属于其他项目。因此本次遵循用户要求，优先读现有代码和日志，不为写文档而重复跑大模型。

---

## 2. 为什么要评价“创造性”

### 2.1 功能正确不是设计空间的终点

同一个 RTL 规格可以有多种正确实现：

```text
组合逻辑：布尔式、case、查表、层次门级
加法器：行为级 +、ripple-carry、carry-lookahead
状态机：binary、one-hot、Gray encoding
乘法器：* 运算符、shift-add、Booth、流水化 DSP
```

如果 benchmark 只看 testbench pass，这些候选得分完全相同。但对硬件设计来说，它们的：

- 面积；
- 时序；
- 功耗；
- 可维护性；
- 鲁棒性；
- 对特定工艺/器件的适配；

可能完全不同。

CreativEval 尝试先回答更基础的问题：模型能否跳出单一模板，生成结构不同但仍正确的实现。

### 2.2 论文借用的四维创造力模型

论文不是凭空定义“创意”，而是借用认知科学常见的：

```text
fluency + flexibility + originality + elaboration
```

再为 RTL 构造可计算 proxy。

这里必须用 `proxy` 一词：论文测到的是某套 prompt、testbench、golden design 和 GNN similarity 下的数值，不等于人的完整工程创造力。

---

## 3. 论文整体流程

论文 Figure 1 已从 arXiv 实验性 HTML 的原图保存：

![CreativEval Figure 1：四维创造性评价流程](./figures/paper_fig1_framework.png)

按代码对象展开，可以写成：

```text
三类 prompt 格式
  ├─ fluency/originality：规格 + module header
  ├─ flexibility：golden true_module + 要求改写的 top_module
  └─ elaboration：给定小模块 + 要求组合大模块
                  ↓
          每题采样 t=10 份 RTL
                  ↓
        Icarus compile + testbench
                  ↓
             功能正确候选
          ┌───────┴────────┐
          ↓                ↓
   DFG + GNN4IP       子模块利用检查
          ↓                ↓
   cosine similarity    elaboration
          ↓
 fluency / flexibility / originality
          └────────┬────────┘
                   ↓
     C=(F+X+O+E)/4
```

---

## 4. GNN4IP 相似度在这里扮演什么角色

### 4.1 从 Verilog 到相似度

论文用 GNN4IP 比较生成 RTL 与 golden RTL：

```text
Verilog
  ↓ Pyverilog / HW2GRAPH
Data-Flow Graph (DFG)
  ↓ 两层 GCN
SAGPool
  ↓ max readout
16 维 graph embedding
  ↓ linear projection
cosine similarity ∈ [-1,1]
```

当前仓库确实带有：

- [h2vFiles/examples/model.cfg](./h2vFiles/examples/model.cfg)；
- [h2vFiles/examples/model.pth](./h2vFiles/examples/model.pth)；
- [h2vFiles/hw2vec/hw2graph.py](./h2vFiles/hw2vec/hw2graph.py)；
- [h2vFiles/hw2vec/graph2vec/models.py](./h2vFiles/hw2vec/graph2vec/models.py)；
- [h2vFiles/hw2vec/graph2vec/trainers.py](./h2vFiles/hw2vec/graph2vec/trainers.py)。

### 4.2 模型的原始任务不是“创造力评价”

`h2vFiles/README.md` 明确显示它来自 HW2VEC，原用例包括：

- Hardware Trojan detection；
- IP piracy detection。

`PairwiseGraphTrainer` 用 cosine embedding loss 学习“两个设计是否可能是同一 IP”。CreativEval 把这个相似度迁移为“生成实现是否接近 golden”的 proxy。

这是合理的研究起点，但存在 domain shift：

```text
训练任务：IP piracy / 大小不一的硬件图
使用任务：小型 HDLBits 的实现创造性
```

仓库没有提供一项独立校准实验，证明：

- GNN 分数与人工工程师的新颖性判断一致；
- 分数对语义保持变换单调；
- 分数不被无意义冗余逻辑或命名扰动欺骗；
- 负 cosine similarity 必然代表有效的替代架构。

因此它应被讲成“结构相似度 proxy”，不应讲成创造力真值。

---

## 5. Fluency：能产生多少种实现

### 5.1 Prompt

输入包括：

```verilog
// Create a full adder.
// A full adder adds three bits and produces sum/carry.
module top_module(
    input a, b, cin,
    output cout, sum
);
```

模型需要补全到 `endmodule`。

### 5.2 论文公式

设：

- `p`：总 prompt 数；
- `t=10`：每题采样数；
- `n`：至少有一份功能正确候选的 prompt 数；
- `R_i`：第 `i` 个成功 prompt 的功能正确候选集合；
- `S(R_i)`：这些候选各自对 golden 的相似度值集合。

论文定义：

```text
F = (1/n) Σ_i ( |S(R_i)| / t )
```

这里的 `|S(R_i)|` 是不同相似度数值的个数。

### 5.3 分母设计的真实含义

这个公式同时做了两件事：

- 在已成功的题里，十次采样中失败越多，`|S|/10` 越低；
- 但十次全失败的题不会进入 `n`，从均值中完全消失。

所以它不是：

```text
全体 111 题上的“每题独特正确实现数”
```

而是：

```text
条件于至少成功一次的题，十次预算下的独特相似度比例
```

这会让功能覆盖率差但在少数容易题上多样的模型仍得到较高 F。

### 5.4 代码如何数“unique”

[extract_originality.py](./h2vFiles/examples/extract_originality.py) 直接使用：

```python
unique_values = set(values)
```

这有两个边界：

1. 两个结构不同的实现只要对 golden 的 scalar similarity 恰好相同，就被合并；
2. 两个本质相同的实现只要浮点数略有差异，就被视为独特。

更严格的方法应先做 pairwise graph comparison、聚类和数值容差，而不是用“到一个 golden 的一维距离”充当等价类 ID。

### 5.5 作者日志可重建全部 Fluency

保存的 `*_calc.log` 给出了每个成功 prompt 的 unique 数和平均值。用 `average_unique/10` 可得到：

| 模型 | 保存日志 average unique | 重建 F | 论文 F |
|---|---:|---:|---:|
| CodeLlama-7B | 1.4827586 | 0.1483 | 0.1483 |
| CodeLlama-13B | 1.6111111 | 0.1611 | 0.1611 |
| VeriGen-6B | 1.2439024 | 0.1244 | 0.1244 |
| VeriGen-16B | 1.1891892 | 0.1189 | 0.1189 |
| GPT-3.5 | 1.3428571 | 0.1343 | 0.1343 |
| GPT-4 | 1.6444444 | **0.1644** | **0.1644** |

这一列是六个指标中 artifact 对应最完整的一列。

---

## 6. Flexibility：看过答案后能否换一种写法

### 6.1 Prompt

Flexibility prompt 先给一个实现，并明确要求产生 different and unique implementation：

```verilog
module true_module(...);
    // golden implementation
endmodule

module top_module(...);
    // model completes an alternative
```

### 6.2 论文公式

对功能正确候选的相似度 `s`：

```text
T(s) = 1, if s < 0
     = 0, if s >= 0
```

每题取最小相似度，只要十次中至少一次低于 0，就认为该题展示 flexibility：

```text
X = (1/n) Σ_i T(min S(R_i))
```

### 6.3 保存日志的负相似度计数

对六份 flexibility GNN log 解析 `Similarity module: score`：

| 模型 | 有有效 similarity 的 module 数 | 最小值 < 0 的 module 数 | 直接比例 | 论文 X |
|---|---:|---:|---:|---:|
| CodeLlama-7B | 12 | 0 | 0 | 0.0000 |
| CodeLlama-13B | 38 | 1 | 0.0263 | 0.0260 |
| VeriGen-6B | 20 | 2 | 0.1000 | 0.1000 |
| VeriGen-16B | 36 | 2 | 0.0556 | 0.0556 |
| GPT-3.5 | 25 | 4 | 0.1600 | 0.1600 |
| GPT-4 | 38 | 3 | 0.0789 | 0.0795 |

总体对应关系很强，但 CodeLlama-13B/GPT-4 的论文小数不是按上述公开日志的简单四舍五入精确得到，说明最终表可能使用过略不同的有效样本集合或人工汇总。

### 6.4 同一仓库里出现三个阈值

| 位置 | 阈值 | 用途 |
|---|---:|---|
| 论文 Equation 2 | `s < 0` | flexibility 正式定义 |
| `extract_flexibility.py` | `s < 0.5` | 统计 low-similarity files |
| `directPD.py` | `abs(s) < 0.6` | 打印 Not pirated / Pirated |

后两者可能是调试/上游 piracy 逻辑，不能拿来替代论文 X。但仓库没有统一 pipeline 明确选择哪个脚本生成 Table I，使用者很容易混用。

---

## 7. Originality：与 golden 有多不相似

### 7.1 论文公式

每个成功 prompt 取十次功能正确候选中的最小 similarity，然后把 `[-1,1]` 翻转归一化到 `[0,1]`：

```text
O = (1/n) Σ_i ((-min S(R_i) + 1) / 2)
```

解释：

```text
min similarity =  1 → originality = 0
min similarity =  0 → originality = 0.5
min similarity = -1 → originality = 1
```

### 7.2 保存日志与论文表

| 模型 | 保存日志 avg min similarity | 推导 O | 论文 O | 对应 |
|---|---:|---:|---:|---|
| CodeLlama-7B | 0.380940 | **0.309530** | **0.2926** | 不一致 |
| CodeLlama-13B | 0.395782 | 0.302109 | 0.3021 | 一致 |
| VeriGen-6B | 0.494587 | 0.252707 | 0.2527 | 一致 |
| VeriGen-16B | 0.445932 | 0.277034 | 0.2771 | 一致 |
| GPT-3.5 | 0.494866 | 0.252567 | 0.2526 | 一致 |
| GPT-4 | 0.468576 | 0.265712 | 0.2657 | 一致 |

CodeLlama-7B 是一处明确的论文—保存日志漂移。论文 O=0.2926 对应平均最小相似度约 `0.4148`，而当前日志是 `0.380940`。

可能原因包括：

- 最终论文使用了另一次 GNN run；
- 当前日志包含了后续补跑样本；
- 有效 prompt 集发生变化；
- 表格或文件拷贝错误。

仓库没有 run manifest，无法进一步确认。

### 7.3 Originality 不等价于“更好的架构”

功能门控排除了明显错误实现，但低 similarity 仍可能来自：

- 无意义的冗余逻辑；
- 不必要的寄存器或层次；
- 代码混淆；
- 位宽/符号写法差异；
- DFG parser 处理差异。

所以 O 是“远离一个 golden”的程度，不是 PPA、可读性或工程价值。

---

## 8. Elaboration：能否用小模块拼成大模块

### 8.1 题型

例如 prompt 给出 `add16` 的接口，要求实例化两个 `add16` 构成 32-bit adder。

当前本地九题是：

```text
Module_1
Module_add
Module_addsub
Module_cseladd
Module_fadd
Module_name
Module_pos
Module_shift
Module_shift8
```

每题目录里有 prompt 和 testbench，另有九份 golden solution。

### 8.2 论文公式

只要某题十次响应中至少一份：

1. 功能正确；
2. 确实使用给定小模块；

就算一个 elaboration success：

```text
E = n / p, p=9
```

论文结果只有两档：

```text
CodeLlama-7B：2/9 = 0.2222
其他五模型： 3/9 = 0.3333
```

这也解释了论文为什么说该维度区分度不足：九题太少，单题就改变 0.1111。

### 8.3 当前 `elaboration.py` 不足以独立重建论文 E

[python_files/prompting_elaboration/elaboration.py](./python_files/prompting_elaboration/elaboration.py) 存在几个关键边界：

- `prompt_names` 只列出九题中的六题；
- 它读取硬编码的 GPT-4 CSV，而不是通用模型输入；
- 它把已有生成 top module 与手写小模块拼接后跑 Icarus；
- 它没有实现可靠的 AST/DFG 检查，确认 `top_module` 真正实例化了给定子模块；
- 一个 flat implementation 只要功能正确，也可能被该脚本给正 reward；
- 输入、输出、testbench 路径依赖作者 scratch 目录和未发布的中间 CSV。

因此论文所述“功能正确且使用小模块”的人工/代码判断链没有完整开放成可移植实现。

---

## 9. Overall Creativity：四项等权，但不含 Functionality

论文定义：

```text
C = 0.25F + 0.25X + 0.25O + 0.25E
```

Table I 的 Functionality 只是并列报告，**没有进入 C**。

用表中四项重算：

| 模型 | 重新平均 F/X/O/E | 论文 C |
|---|---:|---:|
| CodeLlama-7B | 0.165775 | 0.1658 |
| CodeLlama-13B | 0.205625 | 0.2056 |
| VeriGen-6B | 0.202600 | 0.2026 |
| VeriGen-16B | 0.196225 | 0.1962 |
| GPT-3.5 | **0.220050** | **0.2201** |
| GPT-4 | 0.210725 | 0.2107 |

数学对应完全成立。

### 9.1 最大的方法学边界：条件成功偏差

F、X、O 都主要在至少有一个功能正确候选的 `n` 个 prompt 上平均；全失败题被排除。E 则用全部九题。

这意味着两个模型可能出现：

```text
模型 A：只会 10/111 题，但这些题中实现很多样
模型 B：会 100/111 题，但实现较稳定、接近 golden
```

在 C 上，A 未必输给 B，因为 functionality coverage 不进入总分。

因此更稳妥的下一版应至少同时报告：

```text
coverage = 成功 prompt / 全部 prompt
conditional creativity = 当前 F/X/O
unconditional creativity = 把全失败题记 0 后的全题均值
```

甚至可定义：

```text
C_effective = Functionality × C_conditional
```

但这属于本文建议，不是原论文公式。

---

## 10. 论文实验配置

| 项目 | 论文报告 |
|---|---|
| 开源模型 | CodeLlama 7B/13B、VeriGen 6B/16B |
| 闭源模型 | GPT-3.5、GPT-4 |
| VeriGen-16B | 8-bit 量化加载 |
| 开源模型硬件 | NVIDIA A100 80GB |
| Python | 3.10 |
| 功能仿真 | Icarus Verilog 10.3 |
| 单模块题 | 111 |
| elaboration 题 | 9 |
| functionality 总题数 | 120 |
| 每题采样 | 10 |
| temperature | 0.3 |
| max tokens | 1024 |
| top-k | 10 |
| top-p | 0.95 |
| 截断 | 第一处 `endmodule` |

模型引用在代码中具体对应：

```text
codellama/CodeLlama-13b-hf
shailja/fine-tuned-codegen-6B-Verilog
shailja/fine-tuned-codegen-16B-Verilog
gpt-3.5-turbo
gpt-4-turbo-preview（当前 GPT-4 脚本）
```

7B/13B、6B/16B 并不是一份参数化 runner，而是靠复制脚本后手工改 `model_name` 和输出目录完成。

---

## 11. 论文 Table I 完整结果

| 模型 | Functionality | Fluency | Flexibility | Originality | Elaboration | Creativity |
|---|---:|---:|---:|---:|---:|---:|
| CodeLlama-7B | 0.2417 | 0.1483 | 0.0000 | **0.2926** | 0.2222 | 0.1658 |
| CodeLlama-13B | 0.3167 | 0.1611 | 0.0260 | **0.3021** | 0.3333 | 0.2056 |
| VeriGen-6B | 0.3667 | 0.1244 | 0.1000 | 0.2527 | 0.3333 | 0.2026 |
| VeriGen-16B | 0.3250 | 0.1189 | 0.0556 | 0.2771 | 0.3333 | 0.1962 |
| GPT-3.5 | 0.3083 | 0.1343 | **0.1600** | 0.2526 | 0.3333 | **0.2201** |
| GPT-4 | **0.3750** | **0.1644** | 0.0795 | 0.2657 | 0.3333 | 0.2107 |

论文结论的准确读法是：

- GPT-4 的 functionality 和 fluency 最高；
- GPT-3.5 的 flexibility 最高；
- CodeLlama-13B 的 originality 最高；
- elaboration 基本没有区分开；
- 等权平均后 GPT-3.5 的 C 最高；
- “GPT-3.5 最有创造性”依赖这套等权、条件成功、GNN similarity 定义。

---

## 12. 本地数据资产到底有多少

### 12.1 单模块 prompt/testbench

目录：[prompts_testbenches_solutions/hdlbits_prompts_testbenches](./prompts_testbenches_solutions/hdlbits_prompts_testbenches/)

```text
111 个子目录
每目录 1 个 prompt .v + 1 个 testbench .v
合计 222 文件
```

### 12.2 Golden solutions

目录：[prompts_testbenches_solutions/hdlbits_golden_solutions](./prompts_testbenches_solutions/hdlbits_golden_solutions/)

```text
110 个 .v
```

唯一缺失：

```text
Exams_ece241_2013_q12
```

这意味着论文说“111 题每题都有正确实现”在当前 checkout 中并不成立。

### 12.3 Flexibility prompts

目录：[prompts_testbenches_solutions/hdlbits_flexibility_format_prompts](./prompts_testbenches_solutions/hdlbits_flexibility_format_prompts/)

共有 119 文件，组成是：

```text
110 个有 golden 的单模块题
+ 9 个 elaboration 名称
= 119
```

缺 golden 的 `Exams_ece241_2013_q12` 没有 flexibility prompt。

### 12.4 Elaboration

```text
hdbits_elaboration_prompts_testbenches/：9 目录、18 文件
hdbits_elaboration_solutions/：         9 文件
```

### 12.5 结果 artifact

[results_data_tmp3](./results_data_tmp3/) 约 49 MiB：

| 类型 | 数量 |
|---|---:|
| 全部文件 | 53 |
| `.log` | 39 |
| `.csv` | 11 |
| 其余 | 3 个 `.txt` |

这些文件包含：

- LLM console generation logs；
- 提取后的 Verilog/Reward CSV；
- GNN4IP 对每个功能通过候选的 similarity logs；
- 每题 unique similarity/min similarity 的计算日志；
- elaboration 的历史编译/仿真输出。

---

## 13. Functionality artifact 与论文表的对应

CSV 的 reward 语义是：

```text
 1    Icarus compile 成功且 testbench marker 通过
-0.5  compile 成功但功能测试不通过
-1    compile 失败
```

按 `Prompt Name` 分组，统计十次中是否至少出现一个 reward=1：

| 模型 | 当前 CSV | 论文 Functionality 对应分数 | 论文隐含题数 |
|---|---:|---:|---:|
| CodeLlama-7B | 29/119 | 0.2417 | 29/120 |
| CodeLlama-13B | 38/119 | 0.3167 | 38/120 |
| VeriGen-6B | **45/119** | 0.3667 | **44/120** |
| VeriGen-16B | 39/119 | 0.3250 | 39/120 |
| GPT-3.5 | 37/120 | 0.3083 | 37/120 |
| GPT-4 | **49/120** | 0.3750 | **45/120** |

说明：

- 四个开源模型 CSV 都只有 119 个 prompt group；
- GPT 两份 CSV 有 120；
- CodeLlama-7B/13B 和 VeriGen-16B 的成功 numerator 与论文一致，只差本地缺一题；
- VeriGen-6B 和 GPT-4 的成功 group 数与论文不同。

所以 `results_data_tmp3` 不是一套完全冻结、字节级对应论文表的 clean release，更像作者实验过程中整理出的 supporting artifacts。

---

## 14. 生成与功能验证代码调用链

### 14.1 没有统一 runner

实验通过多份脚本分别运行：

```text
python_files/
├─ llm_prompting_hdlbits_fluency_prompts/
│  ├─ prompting_gpt35.py
│  ├─ prompting_gpt4.py
│  ├─ codellama_prompting.py
│  └─ lad_verigen_prompting.py
├─ llm_prompting_flexibility_prompts/
│  ├─ flexibility_gpt.py
│  ├─ flexibility_llama_prompting.py
│  └─ flexibility_verigen_prompting.py
├─ prompting_elaboration/elaboration.py
└─ log_to_csv_processing/*.py
```

它们不是 import-safe library：多数脚本在文件顶层直接加载模型、遍历目录和生成结果。

### 14.2 每题十次采样

主要 runner 都用：

```python
for sample in range(10):
    generation = model(...)
    iverilog(...)
    vvp(...)
```

功能判据是 simulation stdout 中出现：

```text
all tests passed
```

或：

```text
All tests passed
```

### 14.3 多 testbench reward

脚本会把 prompt 目录中除第一个文件之外的文件都当 testbench。任一 testbench：

- compile fail → reward=-1；
- simulation fail → reward=-0.5。

当前发布的 111 单模块目录每题只有一个 testbench，但代码形式允许多个。

### 14.4 第一处 `endmodule` 截断

单模块题把模型输出裁到第一处 `endmodule`。这能去掉解释文字和后续重复模块，但也会：

- 截断合法的多模块实现；
- 对 flexibility prompt 中的 `true_module`/`top_module` 位置极其敏感；
- 若没找到 `top_module`，`find(..., -1)` 的后续搜索语义可能裁错；
- 无法处理 package/interface 等 SystemVerilog 结构。

---

## 15. 论文配置与当前脚本漂移

### 15.1 温度不一致

论文明确写“所有实验 temperature=0.3”。当前源码：

| 脚本类别 | 当前 temperature |
|---|---:|
| GPT-3.5 fluency/originality | **0.7** |
| GPT-4 fluency/originality | **0.7** |
| CodeLlama fluency/originality | **0.7** |
| VeriGen fluency/originality | **0.7** |
| GPT flexibility | 0.3 |
| CodeLlama flexibility | **0.7** |
| VeriGen flexibility | **0.7** |

目录名中多处还有 `tmp3`、`tmp7`，很像实验曾在温度 0.3/0.7 间切换，但当前代码并没有保留一套干净、参数化、与论文一致的 runner。

### 15.2 top-p/top-k 不一致

论文报告：

```text
top_k=10, top_p=0.95
```

本地 Hugging Face 脚本确实传这两个参数；GPT Chat Completions 脚本只设置 temperature/max_tokens，没有传 top-p，也没有 top-k 接口。

因此“所有模型同一采样配置”在不同 provider API 上无法由当前源码严格验证。

### 15.3 模型版本不可冻结

GPT 脚本使用：

```text
gpt-3.5-turbo
gpt-4-turbo-preview
```

没有保存 provider response 的 resolved model snapshot。今天重调同名 API 不是论文同模型复现。

---

## 16. 源码工程问题

### 16.1 全部主脚本绑定绝对路径

大量路径形如：

```text
/mnt/shared-scratch/Rajendran_J/matthewdelorenzo/...
```

虽然数据已经复制到当前仓库相对目录，代码仍不会自动使用它们。

### 16.2 硬编码断点切片

为了断点续跑，多份脚本直接写：

```python
pair_dirs = list_directories(module_dir)[62:]
pair_dirs = os.listdir(module_dir)[81:]
```

从全新环境运行会跳过前 62/81 个条目，而且 `os.listdir()` 顺序没有排序保证，跨文件系统可能跳过不同题。

### 16.3 输出目录不创建

脚本直接写 `gpt_dump2/...`、`flexibility_*_dump/...`，但没有 `mkdir(parents=True)`。目录缺失时会在第一份输出失败。

### 16.4 无 timeout

以下调用均没有 timeout：

- Hugging Face `generate()`；
- OpenAI API；
- `iverilog`；
- `vvp`；
- Pyverilog/DFG extraction；
- GNN inference。

批量 120×10×6 的实验一旦单题卡死就可能停住。

### 16.5 GPT answers 列表保存了 prompt 而不是 generation

两个 GPT fluency 脚本末尾执行：

```python
sample_answers.append(prompt_text)
```

不是 `generation`。生成内容主要靠 `.v` 和 console log 留存，内存中的 `ALL ANSWERS` 列表不可信。

### 16.6 Log-to-CSV 脚本是手工一次性脚本

这些脚本包含：

- 大量被注释掉的历史正则版本；
- 固定输入日志名；
- 固定输出 CSV 名；
- 固定 scratch prompt 路径；
- `zip(*matches)` 在无匹配时直接报错；
- 多套互不一致的 CSV schema。

它们保留了研究过程，但不是稳定数据管线。

---

## 17. GNN similarity 实现边界

### 17.1 `directPD.py` 没有切换 eval mode

脚本直接调用：

```python
trainer.inference_epoch_ip(graph1, graph2)
```

没有通过带 `torch.no_grad()` 和 `model.eval()` 的 `trainer.inference()`。

而 [models.py](./h2vFiles/hw2vec/graph2vec/models.py) 在 graph convolution 后有：

```python
F.dropout(..., p=config.dropout, training=self.training)
```

配置的 dropout 是 `0.5`。新建 model 默认处于 training mode，所以直接路径会启用 dropout。

`PairwiseGraphTrainer` 构造时会把 NumPy/Torch seed 重设为 0，降低了随机漂移，但这仍不是标准 deterministic inference；不同图大小、依赖版本和执行顺序都可能改变分数。

### 17.2 Exact float 去重

如第 5 节所述，fluency 用 Python `set(float_values)`。没有：

- epsilon；
- 重复运行均值；
- 置信区间；
- pairwise clustering；
- graph isomorphism check。

### 17.3 Parser/GNN 失败被静默排除

`directPD.py` 用通用 `except Exception` 打印错误后继续。保存日志中确实有：

- `No such module: true_module`；
- Pyverilog syntax error；
- `one_hot()` 输入为 `None`；
- 其他 graph extraction failure。

失败候选没有 similarity，于是不会进入后续 min/unique 计算。不同模型生成代码风格导致的 parser 可接受性，可能改变创造性样本集合。

### 17.4 “Pirated/Not pirated” 只是上游遗留标签

日志会打印 `Pirated` 或 `Not pirated`，这是 GNN4IP 原始 IP piracy 用例的标签，不表示论文指控模型抄袭。组会展示日志时必须解释这一点。

---

## 18. License 与依赖

### 18.1 License

| 范围 | License |
|---|---|
| CreativEval 根目录 | BSD 3-Clause |
| bundled `h2vFiles` / HW2VEC | MIT |

这比缺许可证的研究仓库清楚，但再分发时仍应保留两套 notice，并核对 HDLBits/AutoChip 派生数据的原始许可和署名要求。

### 18.2 依赖年代

`h2vFiles/requirements.txt` 面向老环境：

```text
Python >=3.6
torch 1.6.0（README 建议）
torch_geometric 1.6.1
numpy 1.16.5
pandas 0.23.4
networkx 2.4
```

论文生成/仿真部分又是 Python 3.10、较新的 Transformers/OpenAI。

这意味着严格复现需要两个层次的依赖兼容：

```text
现代 LLM 生成环境
旧版 Pyverilog / torch-geometric GNN 环境
```

仓库没有顶层 lockfile 或容器把两者统一起来。

---

## 19. 当前真正能复用的资产

### 19.1 可以直接用于研究

- 120 题的 prompt/testbench 主体；
- 110 个单模块 golden + 9 个 elaboration golden；
- 六模型大量历史生成和 reward CSV；
- 六模型 similarity logs；
- GNN 权重/配置；
- DFG extraction/GNN 代码；
- 四维指标公式；
- BSD/MIT license 文本。

### 19.2 不能直接声称具备

- 与论文同温度的一键生成；
- 六模型同 provider/同采样 API；
- 120 题完整、无缺失的 golden 集；
- 自动、可移植的 elaboration 结构检测；
- 自动重建 Table I 的总控脚本；
- 人工标注校准过的 creativity ground truth；
- PPA 或设计价值评价；
- 本轮模型推理记录。

---

## 20. 如果后续真正复现，正确路线

### 阶段 1：冻结数据 manifest

为每题保存：

```json
{
  "task_id": "...",
  "split": "single|elaboration",
  "prompt_sha256": "...",
  "testbench_sha256": "...",
  "golden_sha256": "...",
  "has_golden": true
}
```

先解决 `Exams_ece241_2013_q12` 缺 golden 和 flexibility prompt 的问题。

### 阶段 2：统一生成 runner

把六份复制脚本合并为 adapter：

```text
OpenAI adapter
Hugging Face adapter
共同 generation config
共同输出 schema
共同 resume manifest
```

每个 sample 保存 resolved model、seed、参数、原始响应、trim 后 RTL、时间戳。

### 阶段 3：隔离功能验证

每个 sample 使用独立临时目录，并加：

- iverilog timeout；
- vvp timeout；
- return code；
- compile stderr；
- simulation stdout；
- 明确 pass marker；
- 多 testbench 聚合策略。

### 阶段 4：稳定 GNN inference

至少修正：

```python
model.eval()
with torch.no_grad():
    ...
```

并固定：

- PyTorch/PyG/Pyverilog 版本；
- seed；
- graph normalization；
- 失败样本如何计分；
- float 聚类 epsilon。

### 阶段 5：补人工/EDA 校准

抽样由硬件工程师评价：

```text
是否真是不同 microarchitecture
是否只是代码风格变化
是否引入冗余/混淆
PPA 是否有不同 trade-off
可读性与可维护性
```

再检查 GNN similarity 与人工/PPA 判断的相关性。

---

## 21. 更强的“硬件创造性”指标建议

CreativEval 的价值在于开题，而不是终结指标设计。后续可把创造性拆成：

| 层次 | 可用方法 |
|---|---|
| 文本/AST novelty | token、AST、canonicalization 后去重 |
| 结构 novelty | DFG/AIG/netlist graph edit distance 或 learned embedding |
| 行为正确 | hidden test、formal equivalence、assertion |
| 时序结构 | latency、throughput、pipeline depth、FSM encoding |
| 硬件价值 | PPA Pareto front、FPGA resource mix、约束满足 |
| 训练污染 | 与公开 repo/benchmark/golden 的近重复检索 |
| 人类价值 | 专家盲评 useful/surprising/non-obvious |

推荐最终报告二维或三维结果：

```text
functionality coverage
× structural novelty
× PPA/value improvement
```

否则模型通过插入冗余逻辑也可能提高“离 golden 的距离”。

---

## 22. 与本地其他论文的关系

### 22.1 VerilogEval

```text
VerilogEval：能否从规格生成功能正确 RTL
CreativEval：在功能正确候选中是否有多样、替代、原创、组合能力
```

CreativEval 的 111 单模块题来自 HDLBits/AutoChip 路线，与 VerilogEval 的公共题源有潜在重叠和污染问题。

### 22.2 ResBench

```text
CreativEval：结构是否不同
ResBench：   正确候选的 LUT/DSP/FF 是否不同
```

两者最值得合并：创造性不只要“不同”，还要产生有价值的资源 trade-off。

### 22.3 AutoChip

论文明确说 prompt/testbench 由 AutoChip 来源整理。AutoChip 更关心编译/仿真 feedback 驱动修复；CreativEval 使用同类题观察十次采样的结构分歧。

### 22.4 ROME/MAGE

ROME 和 MAGE 面向层次化/多 Agent 复杂设计。CreativEval 的 elaboration 只有九个小型多模块题，尚不能充分评价复杂 hierarchy 的“设计创造性”。

---

## 23. 最值得组会讨论的问题

1. **“到一个 golden 的相似度”能否代表创造性？**
2. **为什么 creativity 总分不把 functionality 纳入？**
3. **全失败题从 F/X/O 分母消失是否公平？**
4. **DFG similarity 如何区分架构创新与无意义冗余？**
5. **论文统一温度 0.3，而公开脚本多为 0.7，结论对采样温度有多敏感？**
6. **CreativEval + ResBench 能否联合定义 novelty–PPA Pareto benchmark？**
7. **开源日志几乎能重建表格，却缺统一 runner，这算什么复现等级？**

---

## 24. 推荐组会结构

### 24.1 20 分钟版本

| 时间 | 内容 |
|---:|---|
| 2 分钟 | 功能正确 benchmark 的盲点 |
| 4 分钟 | 四维创造力映射到 RTL |
| 3 分钟 | DFG→GNN4IP similarity 流程 |
| 3 分钟 | 六模型 Table I 和 GPT-3.5 总分最高 |
| 3 分钟 | 指标条件成功偏差、single-golden 和 exact-float 去重 |
| 3 分钟 | 代码/数据审计：111/110/119/9、温度漂移、绝对路径 |
| 2 分钟 | 与 ResBench 联合的下一步方向 |

### 24.2 推荐标题

> **“正确之外还有创造性吗？CreativEval 的四维 RTL 指标、GNN 相似度与代码复现边界”**

### 24.3 必须避免的表述

- 不要说 GPT-3.5 在所有维度最好；它只是等权总分最高；
- 不要说 GPT-4 功能只有 45/120 是当前 CSV 重计数；当前 CSV 是 49/120，45/120 是论文表；
- 不要把 `Pirated` 日志当成学术抄袭结论；
- 不要把低 GNN similarity 等同于更优 PPA；
- 不要说当前仓库一键可跑；
- 不要把作者日志称为本轮模型推理。

---

## 25. 可复现性分级

| 等级 | 定义 | CreativEval 状态 |
|---|---|---|
| R0 | 只有论文或零散材料 | 已超过 |
| R1 | 论文、源码、数据/历史 artifact 可核 | **当前等级** |
| R2 | 本地跑通代表模型/仿真/GNN 链 | 本轮未做 |
| R3 | 作者输出经独立工具全量验证 | 未完成；相似度 runner 仍需修复/冻结 |
| R4 | 同配置重算论文主表 | 未完成 |

本项目拥有很多结果文件，但数量多不自动提高等级。关键是：

- 没有同配置新执行；
- 脚本与论文参数漂移；
- 主流程不便携；
- artifact 与表格有数值差异。

---

## 26. 文件导航

建议按下面顺序阅读：

1. [论文 PDF](./2404.08806_CreativEval.pdf)；
2. [论文 Figure 1](./figures/paper_fig1_framework.png)；
3. [111 个单模块 prompt/testbench](./prompts_testbenches_solutions/hdlbits_prompts_testbenches/)；
4. [110 个 golden solutions](./prompts_testbenches_solutions/hdlbits_golden_solutions/)；
5. [119 个 flexibility prompts](./prompts_testbenches_solutions/hdlbits_flexibility_format_prompts/)；
6. [9 个 elaboration prompts/testbenches](./prompts_testbenches_solutions/hdbits_elaboration_prompts_testbenches/)；
7. [作者历史结果](./results_data_tmp3/)；
8. [LLM 生成脚本](./python_files/)；
9. [GNN/HW2VEC 适配代码](./h2vFiles/)；
10. [静态审计 JSON](./runs/static_audit_20260802.json)。

---

## 27. 最终判断

CreativEval 的最大贡献不是证明“某模型真的有创造力”，而是把一个长期被功能正确率遮蔽的问题变成了可讨论、可计算、可批判的 benchmark：

```text
同一规格能否产生多种正确实现？
能否在看到范例后主动换架构？
能否远离常规模板？
能否利用小模块完成层次设计？
```

它非常值得分享，尤其适合与 ResBench 连讲：

```text
CreativEval 负责“是否不同”
ResBench 负责“不同是否带来资源价值”
formal/testbench 负责“是否仍然正确”
```

当前最准确的状态是：

> **论文四维方法和 Table I 已完整还原；111/110/119/9 份数据资产、49 MiB 作者日志和 GNN4IP 代码已审计；六模型 fluency 可由日志全部重建，但部分 functionality/originality 与论文表漂移。仓库尚不是同配置一键复现包，本轮也没有重复执行大模型。**

---

## P7 组件一句话角色

| 组件 | 一句话角色 |
|---|---|
| 111 single-module tasks | 来自 HDLBits/AutoChip 的基准功能题，承载 fluency/originality/flexibility 三项指标 |
| 9 elaboration tasks | 要求用给定小模块组合出更大功能模块，评估层次化组合能力 |
| fluency/flexibility/originality scripts | 用 GNN4IP 相似度量化生成 RTL 与 golden 的结构差异 |
| elaboration.py | 检查多模块组合是否功能正确且确实实例化了给定子模块 |
| GNN4IP (h2vFiles) | 把 Verilog 数据流图经两层 GCN 嵌入为 16 维向量并计算 cosine similarity |
| results_data_tmp3 | 作者历史 CSV 与 log，可部分重建 Table I 但存在温度和数值漂移 |

---

## 讨论问题

1. “到单一 golden 的 GNN similarity”能否真正度量硬件实现的创造性，会不会把无意义冗余逻辑误判为新颖？
2. 四项创造力指标中不包含 functionality，且全失败题从 F/X/O 分母中消失，这会带来怎样的模型评价偏差？
3. 公开脚本温度多为 0.7 而论文写 0.3，这种配置漂移对“GPT-3.5 创造力最高”的结论稳定性有什么影响？

