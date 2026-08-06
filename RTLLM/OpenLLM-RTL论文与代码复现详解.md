# OpenLLM-RTL：论文、三套开源资产、代码与复现边界详解

> 论文：**OpenLLM-RTL: Open Dataset and Benchmark for LLM-Aided Design RTL Generation (Invited)**  
> 会议：ICCAD 2024 invited paper；本地文件为 arXiv `2503.15112` v1，2025-03-19，9 页  
> 本地论文：[2503.15112_OpenLLM-RTL.pdf](./2503.15112_OpenLLM-RTL.pdf)  
> RTLLM-2.0 仓库：<https://github.com/hkust-zhiyao/RTLLM>  
> AssertEval 仓库：<https://github.com/hkust-zhiyao/AssertLLM>  
> RTLCoder-Data 仓库：<https://github.com/hkust-zhiyao/RTL-Coder>  
> 当前目录静态审计：[runs/static_audit_20260802.json](./runs/static_audit_20260802.json)  
> 核验日期：2026-08-02

---

## 0. 一句话定位

OpenLLM-RTL 不是某一个新模型，也不是只对应当前 `RTLLM/` 目录的一套端到端代码。

它是一篇把作者团队三条工作线合在一起的 invited paper：

```text
OpenLLM-RTL
├── RTLLM-2.0
│   └── 50 题：自然语言规格 → RTL 生成 benchmark
├── AssertEval
│   └── 18 个真实设计：完整规格 → SVA assertion 生成 benchmark
└── RTLCoder-Data
    ├── 80K raw instruction-code 数据
    └── 7K assertion/formal 筛选后的 verified 数据
```

三者分别覆盖：

| 生命周期位置 | 资产 | 主要用途 |
|---|---|---|
| 训练前/训练中 | RTLCoder-Data | 微调 RTL 生成模型 |
| RTL 生成评价 | RTLLM-2.0 | 测语法、功能和设计质量 |
| RTL 验证评价 | AssertEval | 测模型能否从完整规格生成有效 assertion |

当前 `/mnt/d/AI4eda/RTLLM` 只完整对应第一项 **RTLLM-2.0**。AssertEval 是另一个仓库，本地当前未发现完整目录；RTLCoder-Data 位于 `/mnt/d/AI4eda/RTL-Coder`，并已有两篇 RTLCoder 的独立详解。

所以本篇采用“论文全景 + 当前代码边界 + 跨目录导航”，不把缺失的 AssertEval 代码虚构成 RTLLM 子目录，也不重复复制 RTLCoder 两篇文档的全部内容。

---

## 1. 先给复现结论

### 1.1 已完成

- OpenLLM-RTL 原论文已归档并逐页核对；
- RTLLM-2.0 的 50 题、四类目录、description/testbench/reference/Makefile 已核对；
- RTLLM 仓库的版本历史、旧模型输出和 `auto_run.py` 已代码级审阅；
- AssertEval 的任务形式、18 个设计、输入/输出、FPV 流程和三个指标已按论文还原；
- RTLCoder-Data 的 80K raw、7K verified、数据生成/验证流程、训练配置、消融和 Table 5 已按论文还原；
- 已把 RTLCoder-Data 对应到本地 `RTL-Coder` 代码与已有详解。

### 1.2 未完成

- 未重新训练 Mistral-7B 或 DeepSeek-Coder-6.7B；
- 未重新调用商业 LLM 生成 80K 数据或 assertion；
- 未运行 JasperGold FPV；
- 未运行 VCS 或 Design Compiler；
- 未重算 Table 5；
- 当前目录不含 AssertEval 完整 artifact，也不含 OpenLLM-RTL 三部分的统一执行器。

### 1.3 等级

| 组件 | 当前本地等级 | 原因 |
|---|---|---|
| RTLLM-2.0 数据/代码 | R1 | 50 题和执行入口已静态核对，未跑商业工具 |
| AssertEval | R0 | 仅论文核对，本地未归档完整代码/数据 |
| RTLCoder-Data | R1/R2 参考已有 RTLCoder 记录 | 数据/代码和代表性本地推理已有独立文档，但本篇训练表未重算 |
| OpenLLM-RTL 整篇 | R0/R1 混合 | 三个组件开放和本地证据程度不同 |

最准确的总述是：

> **论文方法与三套资产关系已完整还原；当前 RTLLM 目录不等于 OpenLLM-RTL 全部代码，论文训练、formal verification 和主结果表未本地复现。**

---

## 2. 论文身份与整体框架

![OpenLLM-RTL 首页和整体框架](./figures/openllm-paper-title-fig1.png)

> 图 1：截自论文第 1–2 页标题、摘要和 Figure 1。Figure 1 把 LLM-assisted RTL generation 与 verification 放在同一框架中，RTLCoder-Data 是训练数据，RTLLM-2.0 和 AssertEval 分别是生成与验证 benchmark。

本地 PDF 信息：

| 字段 | 值 |
|---|---|
| 文件 | `2503.15112_OpenLLM-RTL.pdf` |
| 页数 | 9 |
| 字节数 | 1,356,675 |
| SHA-256 | `15367e6dfa1a685d72b76fc741473f8220053e509da7005c3ae1220329c088f5` |

论文摘要的三项主张分别是：

1. RTLLM-2.0 从原始 30 题扩到 50 个手工设计；
2. AssertEval 提供 18 个设计，评价 assertion generation；
3. RTLCoder-Data 提供 80K instruction-code raw data，并用 assertion/formal 方法得到 7K verified data。

这篇论文的主线不是提出一个新网络结构，而是回答：

```text
如何开放可训练的数据？
如何评价 RTL 生成？
如何评价 RTL 验证中的 assertion 生成？
如何用验证工具反过来提高训练数据质量？
```

---

## 3. 三个组件怎样形成闭环

```text
设计领域关键词、开源 RTL、商业 LLM
                │
                ▼
       RTLCoder-Data raw 80K
                │
        syntax + assertion/FPV
                │
                ▼
       verified 7K high-quality subset
                │
                ▼
     微调 Mistral / DeepSeek-Coder
                │
        ┌───────┴────────┐
        ▼                ▼
  VerilogEval       RTLLM v1.1
  功能 pass@k       syntax + func

另一条评价线：
完整规格文档 + waveform
                │
                ▼
        LLM 生成 assertions
                │
                ▼
    AssertEval + JasperGold FPV
                │
       syntax / FPV / COI
```

这里有两个不同的 assertion 用途：

| assertion 用途 | 输入 | 被验证对象 | 目的 |
|---|---|---|---|
| AssertEval benchmark | 完整真实设计规格 | golden RTL | 评价 LLM 生成 assertion 的能力 |
| 7K 数据筛选 | 单条训练 instruction | 对应生成 code | 判断 instruction-code 是否大概率功能一致 |

二者共享“自然语言规格 → assertion → formal verification”思想，但任务规模与输出口径不同。

---

## 4. 组件一：RTLLM-2.0

### 4.1 从 30 扩到 50

原始 RTLLM 论文声称 30 个设计；RTLLM-2.0 扩成 50，并用粗体标出新题。

![OpenLLM-RTL 的 RTLLM-2.0 题表](./figures/openllm-paper-table2-rtllm2.png)

> 图 2：截自论文第 3 页 Table 2。它列出 50 个设计及简短功能描述，并按 Arithmetic、Memory、Control 和 Miscellaneous 四类组织；粗体表示相对原 RTLLM 新增。

当前仓库的实际计数为：

| 类别 | 当前目录题数 |
|---|---:|
| Arithmetic | 19 |
| Memory | 5 |
| Control | 6 |
| Miscellaneous | 20 |
| 合计 | 50 |

### 4.2 每题三个论文核心文件

论文为每题定义：

| 文件 | 内容 |
|---|---|
| `design_description.txt` | 功能、module 名、I/O 名称和位宽，作为 LLM prompt |
| `testbench.v` | 多个功能测试用例 |
| correct design | 人工编写且声明已通过 testbench 的 reference RTL |

当前仓库还提供每题 Makefile，总计：

```text
50 descriptions
50 testbenches
50 reference RTLs
50 Makefiles
```

### 4.3 评价目标没有改变

RTLLM-2.0 延续原 RTLLM：

1. syntax；
2. functionality；
3. design quality / PPA。

OpenLLM-RTL 没有在这部分提出新的模型或 Agent；主要贡献是扩大题集并细化分类。

### 4.4 论文表与目录拼写不完全一致

Table 2 使用：

```text
multi_pipie_4bit
multi_pipie_8bit
```

仓库目录使用：

```text
multi_pipe_4bit
multi_pipe_8bit
```

此外还有 `freq_divfrac`/`freq_divbyfrac`、`substractor`/`subtractor` 等跨脚本/规格/reference 的差异。详见 [RTLLM 独立详解](./RTLLM论文与代码复现详解.md)。

### 4.5 当前代码不能直接完成论文所称 off-the-shelf 评价

仓库 `auto_run.py`：

- 按旧版扁平目录找 `<design>/makefile`；
- 当前 v2.0 实际是 `<category>/<subcategory>/<design>/makefile`；
- 输出路径硬编码到作者机器；
- 历史 GPT 输出只覆盖 29 题；
- pass@k 平均多加一个零；
- VCS timeout 不会终止子进程；
- 用 `Pass/pass` 任意子串判功能成功。

因此数据集本体已扩成 50，不等于统一 evaluator 已同步成为 v2.0 可直接运行版本。

---

## 5. 组件二：AssertEval 的任务定义

### 5.1 为什么需要 assertion benchmark

RTL verification 不只需要 testbench。SystemVerilog Assertions 可以表达设计必须满足的时序/逻辑属性，并交给 formal property verification 检查。

论文指出已有方法包括：

- 从仿真 trace 动态挖 assertion；
- 用设计模板静态生成；
- 把人工提取或编写的规格句子翻译成 assertion；
- 直接处理完整、非结构化、多模态规格文档。

但不同工作缺少统一、开放的 assertion generation benchmark，于是作者提出 AssertEval。

### 5.2 输入不是短 prompt

AssertEval 给模型的是完整 specification document，其中可能含：

- 自然语言架构描述；
- signal definition；
- 配置与控制关系；
- 时序要求；
- waveform diagram；
- 多页非结构化文档。

模型要针对 architecture-level signals 生成 assertions。

这比“把一句英文翻成一条 SVA”更接近真实验证需求，也显著增加了信息抽取难度。

### 5.3 输出是什么

输出是可与 golden RTL 组合的 SystemVerilog assertions/properties。

概念流程：

```text
完整 specification
  └─ 提取设计功能、信号关系、时序约束
       └─ 对架构级信号生成 SVA
            └─ 与 golden RTL 一起进入 FPV
```

---

## 6. AssertEval 的 18 个设计

![AssertEval 流程与 18 个设计表](./figures/openllm-paper-fig2-asserteval.png)

> 图 3：截自论文第 4 页 Figure 2 和 Table 3。Figure 2 展示完整规格到 assertion、再在 golden RTL 上做 FPV 的评价流；Table 3 列出 18 个开源设计、规格页数和待验证架构信号数。

18 个设计覆盖：

| 应用 | 代表设计 |
|---|---|
| 密码/安全 | AES、sha3、tiny_aes、pairing、tiny_pairing |
| 处理器/SoC | amber、lxp32、minsoc、sockit |
| 算术/应用 | ecg、mac |
| 通信 | ethernet、i2c、uart |
| 内存/控制 | hpdmc、sdc、sdr_ctrl |
| 其他 | 论文表中的全部 18 项共同覆盖多种规模 |

论文把规格控制在少于 60 页、架构级信号少于 60 个，以适配当时 LLM 的上下文与生成能力。

Table 3 中示例规模包括：

| 设计 | 规格页数 | 架构信号数 |
|---|---:|---:|
| AES | 15 | 11 |
| amber | 26 | 14 |
| ethernet | 42 | 54 |
| lxp32 | 59 | 22 |
| sdc | 26 | 53 |
| uart | 10 | 11 |

页数与信号数都是任务规模代理，但不等于 assertion 难度的完整度量。

---

## 7. AssertEval 的三个指标

### 7.1 Syntax

生成 assertion 能否被工具解析/编译。

它只证明形式语言结构合法，不能证明 assertion 表达了正确需求。

### 7.2 FPV result

把 assertion 放到作者提供的 golden RTL 上，用 formal property verification 检查。

论文的判定直觉是：

```text
assertion 在 golden RTL 上被证明成立
  → assertion 与正确实现相容

assertion 在 golden RTL 上失败
  → assertion 很可能错误，或假设/环境不完整
```

但 formal pass 仍不自动说明 assertion 足够强。例如恒真、过弱或没有触达关键逻辑的 property 也可能通过。

### 7.3 COI coverage

Cone of Influence coverage 衡量被 properties 结构性关联到的设计逻辑比例。

它补充回答：

```text
这些通过的 assertion 到底覆盖了多少设计逻辑？
```

因此三个指标应联合阅读：

| Syntax | FPV | COI | 解读 |
|---|---|---|---|
| fail | — | — | assertion 语言结构无效 |
| pass | fail | 任意 | 与 golden RTL 冲突或验证环境有问题 |
| pass | pass | 很低 | 可能是弱/局部 property |
| pass | pass | 较高 | 更可能是有用且广泛触达的 property 集 |

### 7.4 工具依赖

论文为每个设计提供 Cadence JasperGold FPV script，并称可一键执行。

这仍依赖：

- JasperGold 安装；
- 商业 license；
- 对应版本的 SystemVerilog/formal 支持；
- 正确的 clock/reset/assumption/environment 配置。

“脚本开源”不等于“formal 工具链完全开放”。

---

## 8. 当前工作区中的 AssertEval 边界

当前 `/mnt/d/AI4eda` 未发现完整 `AssertLLM`/`AssertEval` 项目目录。

因此本篇对 AssertEval 已完成的是：

- 论文流程还原；
- 18 个设计与指标核对；
- 与 RTLCoder-Data 7K 验证流程的关系说明；
- 官方仓库地址归档。

尚不能做：

- 逐文件核对 18 份 specification、golden RTL 和 FPV script；
- 检查 assertion 输出格式；
- 运行 JasperGold；
- 重算 syntax/FPV/COI 结果；
- 判断仓库版本与论文 snapshot 是否一致。

若用户手动下载，正确地址是：

```text
https://github.com/hkust-zhiyao/AssertLLM
```

下载后应单独建 `AssertLLM/AssertEval论文与代码复现详解.md`，不要把它塞进 RTLLM 代码树。

---

## 9. 组件三：RTLCoder-Data 基础生成流程

RTLCoder-Data 每条样本是：

```text
instruction：自然语言描述希望实现的电路
code：与该描述对应的 Verilog RTL
```

论文以团队此前 RTLCoder 27K 流程为基础，扩展到 80K raw，并增加 Stage 3 的 assertion/formal 功能验证以得到 7K verified。

![RTLCoder-Data 数据生成与验证流程](./figures/openllm-paper-fig3-data-verification.png)

> 图 4：截自论文第 6 页 Figure 3。流程从领域关键词、源代码与 instruction 生成/变异开始，经检查与 reference code 生成得到 raw data；新增 Stage 3 用 assertion 和 formal verification 做功能筛选。

### 9.1 基本生成链

按论文可还原为：

```text
1. 收集电路领域关键词
2. 建立开源 RTL source code pool
3. 基于关键词生成 instruction
4. 基于已有 instruction 做 mutation/扩展
5. 做 instruction content/diversity 检查
6. 用 GPT 为 instruction 生成 reference RTL code
7. 可选：syntax + assertion/formal 功能检查
```

原流程的价值是把人工写题变成自动化数据增强；代价是 instruction 与 code 的真正语义一致性很难只靠文本和语法检查保证。

### 9.2 两类 instruction 来源

论文图中体现两条主线：

- keyword-based instruction generation；
- source-code-based instruction generation。

前者从领域概念构造新任务，后者从真实代码提取/反推功能描述；再用 mutation 增加多样性。

### 9.3 reference code 不是人工 golden

流程第 6 步仍由商业 GPT 为 instruction 生成 code。

因此即使叫 reference code，也不应自动理解为人工证明正确的 golden RTL。80K 被论文明确称为 raw data，正是因为功能正确性无法保证。

---

## 10. 80K raw dataset

### 10.1 相对 27K 的变化

论文从原 RTLCoder 的 27K 扩到 80K，主要通过：

- 扩大 source code pool；
- 继续做 instruction mutation；
- 放宽耗时的全局多样性检查；
- 保留基本 instruction content 检查。

### 10.2 为什么移除 all-pairs diversity check

原先每条新 instruction 与所有已有 instruction 比较，数据变大后代价很高。

80K 流程移除了这类耗时的全量比较。论文随后用 CR/CR:POS 评估最终数据多样性，主张放宽在线检查没有破坏整体多样性。

### 10.3 为什么仍叫 raw

生成依赖商业 LLM，syntax 正确也不能保证 code 与 instruction 功能一致。

论文明确写不能保证所有样本正确，所以把 80K 称为 raw dataset。

这点很重要：

```text
80K 是数量资产
7K verified 是质量筛选资产
```

二者不是包含“绝对错误”和“绝对正确”的二元划分。

---

## 11. 7K verified dataset

### 11.1 功能验证的核心思路

对每条 `(instruction, code)`：

```text
instruction
  └─ 商业 LLM 生成 assertions
         │
code + assertions
         │
         ▼
JasperGold / formal verification
         │
         ├─ assertion 全通过 + syntax 通过 → 保留
         └─ 失败 → 丢弃
```

### 11.2 为什么是“likely correct”，不是 100% correct

assertion 由 LLM 从 instruction 生成，可能存在：

- 规格覆盖不全；
- property 太弱；
- property 自身错误；
- reset/clock/assumption 写错；
- vacuous pass；
- 对数据通路只检查局部条件。

论文自己写明该流程不是 100% correctness guarantee。

### 11.3 为什么它是保守筛选

若 LLM 生成了错误 assertion，即使 code 实际正确，也可能 formal fail 被丢弃。

因此：

```text
通过者：大概率更正确，但不保证完美
失败者：不一定 code 错，也可能 assertion 错
```

这是偏高 precision、可能牺牲 recall 的过滤器。

### 11.4 最终规模

syntax checker 与 assertion-based functionality checker 联合后，论文得到 7K verified samples。

“7K”不是从 80K 随机抽样，而是验证管线筛选得到的高质量子集口径。

---

## 12. 数据泄漏控制

论文把每条训练样本的 instruction+code 拼接文本，与 VerilogEval 和 RTLLM benchmark case 计算最大 Rouge-L。

观察结果：

- 大多数训练样本的 Rouge-L 约 0.25；
- 少量样本相似度较高；
- 训练时剔除 `Rouge-L > 0.5` 的样本。

这个策略控制的是表面序列重叠，不是完整语义泄漏。

它可能漏掉：

- 变量/模块改名后的相同电路；
- 描述重写但功能完全相同；
- reference RTL 结构等价但 token 差异大；
- 基础模型预训练阶段已见 benchmark；
- 题目来自同一上游开源仓库的近重复版本。

论文 limitations 也明确承认 Rouge-L 近似不完美，预训练泄漏难以控制。

---

## 13. 数据多样性指标

![RTLCoder-Data 多样性、长度与数据量消融](./figures/openllm-paper-table4-fig5-data-ablation.png)

> 图 5：截自论文第 7 页 Figure 4、Table 4 与 Figure 5。Figure 4 展示 benchmark 相似度和 token 长度；Table 4 比较 CR/CR:POS；Figure 5 展示训练数据量增加时 VerilogEval pass@k 的变化。

论文使用：

- Compression Ratio，CR；
- Part-of-Speech Compression Ratio，CR:POS。

这两项都是**越低代表冗余越少、多样性越高**。

| 数据集 | CR | CR:POS |
|---|---:|---:|
| RTLCoder-Data Raw 80K | 4.21 | 7.33 |
| RTLCoder-Data Verified 7K | 4.32 | 7.45 |
| MG-Verilog | 5.80 | 9.16 |
| Goh et al. | 5.27 | 10.1 |

论文据此认为两套 RTLCoder-Data 比对比数据有更好的词汇/句法多样性。

但 compression-based diversity 不评价：

- 电路功能覆盖；
- 设计复杂度；
- 时序协议多样性；
- code 正确率；
- benchmark 泄漏；
- 训练价值。

它只能作为数据冗余的一个侧面。

---

## 14. 训练配置

### 14.1 基座模型

| 模型 | 规模 | 用法 |
|---|---:|---|
| Mistral-7B-v0.1 | 7B | 直接训练与 scoring-based 训练 |
| DeepSeek-Coder-6.7B-Instruct | 6.7B | 多数据量、direct/scoring/verified 对比 |

### 14.2 优化设置

| 参数 | 论文值 |
|---|---|
| optimizer | Adam |
| beta1 | 0.9 |
| beta2 | 0.999 |
| learning rate | `1e-5` |
| weight decay | 0 / 不使用 |
| context length | 2048 |
| global batch size | 256 |
| DeepSpeed | stage 2 |

### 14.3 硬件

论文使用：

```text
4 × RTX 4090 24GB
每 GPU 可承载 2 × 2048 context
```

这说明 7B 级全参数/分布式微调在消费级 GPU 上可进行，但不代表任何复现都只需相同显存：实际还取决于精度、gradient checkpointing、optimizer state、DeepSpeed 配置和数据 packing。

### 14.4 为什么 max length 取 2048

论文的 token length 分析显示 instruction+code 样本通常在 2048 token 内，因此把它设为微调最大长度。

超长样本如何截断、instruction 与 code 的 loss mask 如何处理，仍应以具体训练脚本核对，不能只凭论文一行推断。

---

## 15. 评价协议

### 15.1 Benchmark

模型在：

- VerilogEval Machine；
- VerilogEval Human；
- RTLLM v1.1；

上评价。

注意：论文训练结果使用的是 **RTLLM v1.1**，不是本篇前面介绍的 50 题 RTLLM-2.0。这是另一个容易混淆的版本事实。

### 15.2 VerilogEval 指标

分别报告 Machine/Human 的：

- pass@1；
- pass@5；
- pass@10。

### 15.3 RTLLM 指标

每题五次 trial，只要任意一次通过，就把题记为成功，可解释为 pass@5。

Table 5 给出：

- Syntax-VCS；
- Func。

### 15.4 Temperature 选择

所有模型都在：

```text
temperature ∈ {0.2, 0.5, 0.8}
```

三种条件下评价，并为每个模型报告最佳结果。

这提高了每个模型的展示上限，但也意味着表格不是单一预注册 temperature 的直接对比。复现时必须保存每个温度的原始结果，不能只留最优数字。

---

## 16. 两种训练方案

### 16.1 Basic direct training

直接用 instruction-code pairs 做 supervised fine-tuning：

```text
instruction → reference RTL code
```

论文对 DeepSeek 分别使用 5K、27K、50K、80K raw 和 7K verified，以隔离数据量/质量影响。

### 16.2 Scoring-based training

沿用 RTLCoder 的 code-quality feedback 训练方案，把代码质量评分融入训练，而不只是对 reference token 做普通监督。

论文用相同 27K raw subset 比较：

```text
Direct 27K
vs
Scoring 27K
```

以区分“训练 scheme”而不是数据量带来的变化。

具体代码和评分机制应结合：

- [RTLCoder LAD/arXiv 版详解](../RTL-Coder/RTLCoder_LAD2024论文与代码复现详解.md)
- [RTLCoder TCAD 2025 扩展版详解](../RTL-Coder/RTLCoder_TCAD2025论文与代码复现详解.md)

---

## 17. Table 5 完整主结果

![OpenLLM-RTL 主结果表](./figures/openllm-paper-table5-main-results.png)

> 图 6：截自论文第 8 页 Table 5。列依次为 VerilogEval Machine/Human 的 pass@1、pass@5、pass@10，以及 RTLLM v1.1 的 Syntax-VCS 和 Func。

为避免只摘有利数字，下面完整转录表中数值：

| 模型 | Machine p@1 | p@5 | p@10 | Human p@1 | p@5 | p@10 | RTLLM Syntax | RTLLM Func |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| GPT-3.5 | 46.7 | 69.1 | 74.1 | 26.7 | 45.8 | 51.7 | 89.7 | 37.9 |
| GPT-4 | 60.0 | 70.6 | 73.5 | 43.5 | 55.8 | 58.9 | 100 | 65.5 |
| ChipNeMo 13B | 43.4 | N/A | N/A | 22.4 | N/A | N/A | N/A | N/A |
| VerilogEval 16B | 46.2 | 67.3 | 73.7 | 28.8 | 45.9 | 52.3 | N/A | N/A |
| BetterV 7B | 64.2 | 75.4 | 79.1 | 40.9 | 50.0 | 53.3 | N/A | N/A |
| CodeGen2 16B | 5.00 | 9.00 | 13.9 | 0.90 | 4.10 | 7.25 | 72.4 | 6.90 |
| StarCoder 15B | 46.8 | 54.5 | 59.6 | 18.1 | 26.1 | 30.4 | 93.1 | 27.6 |
| Thakur et al. 16B | 44.0 | 52.6 | 59.2 | 30.3 | 43.9 | 49.6 | 86.2 | 24.1 |
| Mistral-7B base | 36.9 | 48.8 | 57.4 | 4.49 | 12.6 | 18.6 | 72.4 | 20.7 |
| DeepSeek-Coder 6.7B base | 54.1 | 63.8 | 67.5 | 30.2 | 42.2 | 46.2 | 89.6 | 34.5 |
| Mistral-Scoring 27K | 62.5 | 72.2 | 76.6 | 36.7 | 45.5 | 49.2 | 96.6 | 48.3 |
| DeepSeek-Scoring 27K | 61.2 | 76.5 | 81.8 | 41.6 | 50.1 | 53.4 | 93.1 | 48.3 |
| Mistral-Direct 27K | 58.9 | 70.0 | 74.1 | 34.4 | 42.3 | 45.1 | 89.7 | 41.4 |
| DeepSeek-Direct 5K | 53.7 | 71.7 | 77.1 | 32.9 | 45.8 | 52.4 | 93.1 | 41.4 |
| DeepSeek-Direct 27K | 59.8 | 73.6 | 77.2 | 39.1 | 48.3 | 51.3 | 86.2 | 44.8 |
| DeepSeek-Direct 50K | 62.6 | 75.6 | 80.5 | 38.9 | 48.7 | 51.8 | 89.7 | 55.2 |
| DeepSeek-Direct 80K | 64.7 | 76.6 | 80.8 | 42.8 | 51.6 | 55.0 | 93.1 | 48.3 |
| DeepSeek-Direct 7K verified | 61.3 | 76.3 | 80.8 | 38.9 | 50.1 | 55.3 | 100 | 48.3 |

所有数值都是**论文报告**，不是本地重跑结果。

---

## 18. 论文的四个核心实验结论

### 18.1 80K 在 Eval-Machine pass@1 超过 GPT-4

```text
DeepSeek-Direct 80K: 64.7
GPT-4:               60.0
差值:                +4.7 个百分点
```

这只发生在 VerilogEval Machine pass@1 这一列。不能缩写成“7B 模型全面超过 GPT-4”，因为：

- Human pass@1：42.8 < 43.5；
- RTLLM Func：48.3 < 65.5；
- 其他 pass@k 列也不是全部领先。

### 18.2 数据量增大带来提升

DeepSeek direct raw data 的 Machine pass@1：

```text
5K  → 53.7
27K → 59.8
50K → 62.6
80K → 64.7
```

论文认为到 80K 仍未明显饱和。

但不同列并非严格单调，例如 RTLLM Func 50K 为 55.2，80K 反而为 48.3。更准确的说法是整体 VerilogEval 趋势随数据量上升，而不是所有 benchmark/metric 单调增加。

### 18.3 Scoring-based training 优于相同 27K direct

| 基座 | Direct 27K Machine p@1 | Scoring 27K | 变化 |
|---|---:|---:|---:|
| Mistral | 58.9 | 62.5 | +3.6 |
| DeepSeek | 59.8 | 61.2 | +1.4 |

论文称 scoring-based 在所有对应 benchmark 指标上优于 direct 27K，Table 5 支持这组配对比较。

### 18.4 7K verified 的数据效率

论文主张：

- 7K verified 全指标超过 27K raw direct；
- 7K verified 在 8 个指标中的 6 个超过 50K raw；
- 训练时间少于 50K raw 的 20%。

这支持“质量筛选可以抵消大量低质量数据”的方向。

但 7K verified 不是随机同分布子集，而是被 assertion/formal 管线选择过，可能同时改变：

- 正确率；
- 任务类型分布；
- 代码长度；
- formal 易验证程度；
- assertion 易生成程度。

因此若要把收益严格归因于“正确率”，还需要匹配分布的对照实验。

---

## 19. 结果中容易误读的地方

### 19.1 OpenLLM-RTL 没有训练一个叫 OpenLLM-RTL 的模型

表中模型名是 Mistral/DeepSeek 的 Direct 或 Scoring 版本。OpenLLM-RTL 是论文/资源框架名称。

### 19.2 50 题 RTLLM-2.0 没用于 Table 5

Table 5 明确写 RTLLM v1.1。不能把 50 题章节与 29 题评价列混为一体。

### 19.3 “verified” 不等于 formal 等价证明

7K 的 code 是对 LLM 生成的 assertion 做 property checking，不是与一个人工 golden RTL 做全功能 equivalence。

### 19.4 最佳 temperature 带来选择效应

每个模型从 0.2/0.5/0.8 中报最佳。若不同模型最佳温度不同，这是合理调参；但比较时应保留选择协议，不能把结果当单一固定解码设置。

### 19.5 Syntax 100 不等于 Func 100

7K verified 模型在 RTLLM v1.1 Syntax-VCS 为 100，Func 为 48.3。语法微调成熟并没有自动解决复杂功能生成。

### 19.6 Machine 与 Human 难度/分布不同

80K 模型 Machine p@1 64.7，但 Human p@1 42.8。训练数据对自动生成式规格的适配可能更强，不能只用 Machine 一列代表真实工程能力。

---

## 20. 论文 limitations

![OpenLLM-RTL 局限与开放问题](./figures/openllm-paper-limitations.png)

> 图 7：截自论文第 8 页 Section 6。作者从 benchmark 难度、描述细节、数据泄漏和 assertion 质量等方面列出开放问题。

### 20.1 Benchmark 复杂度选择

- 题目太难，所有模型都失败，无法区分；
- 题目太简单，所有模型都通过，也无法区分；
- benchmark 要随模型能力演进。

### 20.2 规格详细程度

如果 description 把实现步骤写得过细，任务接近自然语言到代码翻译；如果过于含糊，又不能公平判断模型是否理解需求。

需要在“足够可实现”和“保留设计空间”之间平衡。

### 20.3 训练数据泄漏

Rouge-L 只能近似文本相似；基础模型预训练数据无法完全控制。公开 RTL benchmark 尤其容易进入未来模型语料。

### 20.4 Assertion 质量

只看 assertion 语法和 formal pass 不足以衡量：

- assertion 是否完整；
- 是否覆盖关键行为；
- 是否过弱或 vacuous；
- 能否发现真实 bug；
- 是否需要环境 assumptions。

### 20.5 规格质量上限

如果 specification 本身缺少关键行为，无论 LLM 多强都无法生成完整 assertions。模型能力与输入规格质量必须分开评价。

---

## 21. 当前工作区资产映射

| 论文组件 | 官方仓库 | 当前本地位置 | 本地状态 |
|---|---|---|---|
| RTLLM-2.0 | `hkust-zhiyao/RTLLM` | `/mnt/d/AI4eda/RTLLM` | 50 题、旧输出和脚本在；已静态审计 |
| AssertEval | `hkust-zhiyao/AssertLLM` | 当前未发现完整目录 | 仅论文级还原；需手动下载/克隆 |
| RTLCoder-Data | `hkust-zhiyao/RTL-Coder` | `/mnt/d/AI4eda/RTL-Coder` | 代码、数据/模型相关资产与两篇详解已存在 |

### 21.1 为什么不复制 RTLCoder 文档

RTLCoder 在工作区已有：

- [LAD/arXiv 版论文与代码复现详解](../RTL-Coder/RTLCoder_LAD2024论文与代码复现详解.md)
- [TCAD 2025 扩展版论文与代码复现详解](../RTL-Coder/RTLCoder_TCAD2025论文与代码复现详解.md)
- [RTLCoder 原论文 PDF](../RTL-Coder/2312.08617_RTLCoder.pdf)
- [TCAD 扩展版 PDF](../RTL-Coder/TCAD2025_RTLCoder.pdf)

本篇只解释 OpenLLM-RTL 如何使用/扩展 RTLCoder-Data，并把具体代码入口交叉链接到已有逐论文文档，避免形成相互漂移的重复副本。

---

## 22. 论文—代码对应表

| 论文内容 | 当前可核对代码/数据 | 对应程度 | 结论 |
|---|---|---|---|
| RTLLM-2.0 50 题 | `RTLLM/{Arithmetic,Memory,Control,Miscellaneous}` | 高 | 50 套核心文件存在 |
| RTLLM description/testbench/reference | 每题目录 | 中到高 | 文件齐，但部分 module naming 不一致 |
| RTLLM 自动评价 | `RTLLM/auto_run.py`、Makefile | 低到中 | 旧布局、硬编码和评分问题阻止 v2.0 直接运行 |
| RTLLM PPA | 论文表、README 图片 | 低 | 缺完整 DC/工艺/报告链 |
| AssertEval 18 设计 | 应在独立 AssertLLM 仓库 | 当前本地不可核对 | 需要下载后逐文件审计 |
| JasperGold FPV scripts | 应在 AssertLLM 仓库 | 当前本地不可核对 | 商业工具仍是外部依赖 |
| 80K raw data | RTL-Coder 仓库/发布资产 | 已有本地关联目录 | 具体 schema/脚本见 RTLCoder 详解 |
| 7K verified data | RTL-Coder 仓库/发布资产 | 已有本地关联目录 | 论文说明 assertion/formal 筛选 |
| 80K 数据生成 | RTL-Coder 代码与外部 GPT | 部分 | 商业 LLM、源池和完整生成环境需另核 |
| assertion functionality checker | 论文 Figure 3、JasperGold | 开放不完整 | formal 与 assertion 生成依赖未在 RTLLM 目录中 |
| Mistral/DeepSeek 训练 | RTL-Coder 训练脚本 | 部分 | Table 5 未本地重训/重算 |

---

## 23. 本次为何不重新训练或推理

用户要求优先参考已经存在的运行记录，不重复消耗模型推理或训练。

对 OpenLLM-RTL 来说，直接重跑尤其不能简单等价于复现：

1. 80K raw 数据生成需要商业 LLM 与原始 source pool；
2. 7K verified 需要 assertion generator 与 JasperGold；
3. Table 5 需要 4×4090、多个数据规模、两个基座、两种训练 scheme；
4. 每个模型还要在三个 temperature 下多样本评价；
5. RTLLM v1.1、VerilogEval evaluator 和模型 checkpoint 必须锁版本；
6. 当前 RTLLM evaluator 本身还需先修复。

随便选一个本地模型跑一题，只能证明“某条替代路径能运行”，不会验证论文关于数据量、数据质量和训练 scheme 的因果结论。

因此本次选择了证据价值更高的静态工作：

- 对齐三套仓库；
- 还原数据生成/验证路径；
- 完整转录主结果；
- 标注版本与指标；
- 对当前代码可运行性做审计；
- 明确哪些动作需要新下载或商业环境。

---

## 24. 严格复现 Table 5 的实验矩阵

### 24.1 数据轴

```text
raw 5K
raw 27K
raw 50K
raw 80K
verified 7K
```

### 24.2 模型轴

```text
Mistral-7B-v0.1
DeepSeek-Coder-6.7B-Instruct
```

### 24.3 训练轴

```text
basic direct SFT
scoring-based training（27K 对照）
```

### 24.4 解码轴

```text
temperature 0.2
temperature 0.5
temperature 0.8
多样本：至少支持 pass@10
```

### 24.5 Benchmark 轴

```text
VerilogEval Machine
VerilogEval Human
RTLLM v1.1
```

### 24.6 必须保存的证据

每个训练 run：

- commit；
- dataset hash/过滤后样本数；
- base checkpoint hash；
- DeepSpeed config；
- optimizer/scheduler；
- batch、sequence length、epochs/steps；
- GPU 型号和数量；
- seed；
- loss/log/checkpoint；
- wall-clock/GPU-hour。

每个评价 run：

- prompt template；
- temperature、top-p、max tokens；
- 每题原始候选；
- 编译/仿真日志；
- evaluator commit；
- 缺失/timeout/tool-error 明细；
- 未取 best-temperature 前的全量分数。

---

## 25. 7K verified 的关键消融还可以怎样补强

论文已经证明 7K verified 在效率上很有吸引力。若继续研究，建议增加匹配对照：

| 对照 | 目的 |
|---|---|
| 随机 raw 7K | 区分筛选质量与样本数 |
| 与 verified 任务类型匹配的 raw 7K | 控制领域分布 |
| 与 verified 长度匹配的 raw 7K | 控制 token/训练量 |
| syntax-only filtered 7K | 隔离 formal 功能筛选收益 |
| assertion confidence/coverage 分层 | 分析哪些验证信号最有用 |
| formal-easy vs formal-hard | 检查筛选是否偏向简单电路 |
| 人工抽检 precision/recall | 估计通过者正确率与误拒率 |

尤其应区分：

```text
assertion 生成得容易
```

和：

```text
RTL 任务本身质量高、对模型训练有价值
```

这两个属性可能相关，但不等价。

---

## 26. AssertEval 还需要怎样评价 assertion 质量

在 Syntax、FPV、COI 之外，可以补充：

### 26.1 Mutation score

对 golden RTL 注入受控 bug，测 assertion 能否捕获。通过 golden 但抓不到任何 bug 的 property 价值有限。

### 26.2 Vacuity detection

检查 antecedent 是否永远不触发，避免 `A |-> B` 因 A 不成立而形式通过。

### 26.3 Requirement coverage

把规格拆成 requirement units，标记每条 requirement 是否有 assertion 覆盖。

### 26.4 Redundancy

多条 assertion 可能表达同一条件。只看数量和 COI 会奖励重复生成。

### 26.5 Assumption quality

过强 environment assumptions 可以让错误 property 被“证明”。应分别审计 assume 与 assert。

### 26.6 Debug usefulness

对失败 trace 的定位能力、counterexample 长度和可解释性也影响工程价值。

---

## 27. 组会分享建议

### 27.1 推荐标题

**“OpenLLM-RTL：80K 规模、7K 质量与两类 benchmark，数据—生成—验证怎样闭环”**

### 27.2 推荐 12 页结构

1. 论文不是一个模型，而是三套开放资产；
2. Figure 1 总框架；
3. RTLLM-2.0：30→50 与四类任务；
4. 当前 50 题目录和 evaluator 版本问题；
5. AssertEval：完整规格到 SVA；
6. Syntax、FPV、COI 三指标；
7. RTLCoder-Data 生成链；
8. 80K raw 为什么不保证正确；
9. assertion/formal 如何筛出 7K；
10. Table 5：数据量、scheme、质量三组消融；
11. 7K verified 的数据效率与因果边界；
12. 开源资产、商业工具与当前本地复现等级。

### 27.3 一页最核心图

```text
数据规模：27K → 80K raw
                  │
                  ├─ 更多数据 → Machine p@1 上升
                  │
                  └─ assertion + formal 筛选 → 7K verified
                                             │
                                             └─ 更少训练时间、更高数据效率

评价侧：RTLLM-2.0 测 RTL 生成
        AssertEval 测 assertion 生成
```

### 27.4 最适合讨论的问题

1. 形式验证筛出来的是“功能更正确的数据”，还是“更容易写 assertion 的数据”？
2. 公开 benchmark 在基础模型预训练后还能否公平？
3. 使用商业 LLM 和 JasperGold 生成开放数据，能否称为 fully reproducible？
4. 80K 数据量增益是否会在更复杂、多模块、长上下文任务上继续？
5. assertion 通过 golden RTL 以后，怎样衡量其强度和 bug-finding 能力？

---

## 28. 对“开源”的准确理解

论文强调 fully open-sourced resources，但复现需要分层：

| 层级 | 是否开放/可得 | 说明 |
|---|---|---|
| 论文 | 是 | 本地已归档 |
| RTLLM-2.0 题目 | 是 | 当前目录有 50 题 |
| AssertEval 数据/脚本 | 官方另仓库 | 当前本地未下载 |
| RTLCoder-Data | 官方另仓库 | 本地有 RTL-Coder 目录 |
| 商业 LLM 数据生成服务 | 否/服务依赖 | 模型版本会变化 |
| JasperGold | 否 | 商业 license |
| VCS/Design Compiler | 否 | 商业 license/工艺环境 |
| 论文全部训练 checkpoint | 需逐项核对 | 不应仅凭代码仓库存在推断齐全 |
| 三组件统一一键 pipeline | 当前未见 | 三个仓库、多个商业工具 |

所以更准确的说法是：

> 数据集和 benchmark artifact 面向公开使用，但“从数据自动生成、formal 筛选、模型训练到三套 benchmark 重算”的完整生产环境并未被一个开放容器封装。

---

## 29. 下载与归档地址

### 29.1 论文

- OpenLLM-RTL PDF：<https://arxiv.org/pdf/2503.15112>
- RTLLM PDF：<https://arxiv.org/pdf/2308.05345>

### 29.2 代码/数据

- RTLLM-2.0：<https://github.com/hkust-zhiyao/RTLLM>
- AssertEval / AssertLLM：<https://github.com/hkust-zhiyao/AssertLLM>
- RTLCoder-Data：<https://github.com/hkust-zhiyao/RTL-Coder>

当前论文 PDF 已在模型目录内，不需要再次下载。若用户要手动补全 AssertEval，应优先下载上面的 AssertLLM 仓库；完成后再逐代码完善它自己的 MD。

---

## 30. 文件导航

### 本目录

- [OpenLLM-RTL 原论文](./2503.15112_OpenLLM-RTL.pdf)
- [RTLLM 原论文](./2308.05345_RTLLM.pdf)
- [RTLLM 独立详解](./RTLLM论文与代码复现详解.md)
- [RTLLM/OpenLLM-RTL 静态审计](./runs/static_audit_20260802.json)
- [RTLLM 仓库 README](./README.md)
- [RTLLM-2.0 分类表](./File_list.md)
- [当前批处理脚本](./auto_run.py)

### RTLCoder 交叉文档

- [RTLCoder LAD/arXiv 版详解](../RTL-Coder/RTLCoder_LAD2024论文与代码复现详解.md)
- [RTLCoder TCAD 2025 版详解](../RTL-Coder/RTLCoder_TCAD2025论文与代码复现详解.md)
- [RTLCoder 短版梳理](../RTL-Coder/模型梳理.md)

### 论文截图

- `figures/openllm-paper-title-fig1.png`
- `figures/openllm-paper-table2-rtllm2.png`
- `figures/openllm-paper-fig2-asserteval.png`
- `figures/openllm-paper-fig3-data-verification.png`
- `figures/openllm-paper-table4-fig5-data-ablation.png`
- `figures/openllm-paper-table5-main-results.png`
- `figures/openllm-paper-limitations.png`

---

## 31. 最终判断

OpenLLM-RTL 的最大价值是把 RTL 领域的三个稀缺资源放到同一张研究地图上：

- **更多生成训练数据**：80K raw；
- **更高质量训练数据**：7K assertion/formal verified；
- **更广生成评价**：RTLLM-2.0 50 题；
- **验证能力评价**：AssertEval 18 个真实设计。

论文实验较有说服力地展示了三个方向：数据量增加、scoring-based training 和 verified data 都能影响小型开源模型的 RTL 生成表现。尤其 7K verified 的数据效率，值得作为“EDA 工具参与训练数据治理”的代表案例。

但详细代码审阅后的边界同样重要：

- OpenLLM-RTL 不是单一模型或单仓库；
- Table 5 用 RTLLM v1.1，不是本文介绍的 50 题 v2.0；
- AssertEval 和 RTLCoder-Data 在独立仓库；
- 当前 RTLLM evaluator 尚未适配 v2.0 分层目录；
- 7K 的 verified 是高概率正确，不是 100% 形式完备证明；
- 数据生产和验证依赖商业 LLM、JasperGold、VCS/综合工具；
- 本地没有重训或重算论文主表。

因此组会中应使用这一结论：

> **OpenLLM-RTL 提供的是“开放数据与 benchmark 的组合框架”，不是开箱即用的统一端到端模型。当前本地已完成论文—仓库—代码的对应核对，RTLLM-2.0 可静态审阅，AssertEval 仍需下载，RTLCoder-Data 应结合现有 RTL-Coder 目录继续追踪；论文训练与 formal 结果尚未复现。**
