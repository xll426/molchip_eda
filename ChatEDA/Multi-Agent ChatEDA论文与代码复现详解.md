# Multi-Agent ChatEDA / EDAid：论文、代码与复现边界详解

> 论文正式题名：**Divergent Thoughts toward One Goal: LLM-based Multi-Agent Collaboration System for Electronic Design Automation**  
> 系统名：**EDAid**  
> 作者：Haoyuan Wu, Haisheng Zheng, Zhuolun He, Bei Yu  
> 发表：NAACL 2025 Main Conference，Long Papers，pp. 1710–1721  
> 本地论文：[NAACL2025_Multi-Agent_ChatEDA.pdf](./NAACL2025_Multi-Agent_ChatEDA.pdf)  
> 论文官方地址：<https://aclanthology.org/2025.naacl-long.83.pdf>  
> 本地材料：[ChatEDA](./)  
> 静态核验 commit：`02bb522a98f759595fbfce6bee33f64ef02ce3a5`  
> 核验日期：2026-08-02  
> 本文只做论文、代码和数据静态核验，**没有重新运行模型、训练或 EDA flow**。

---

## 0. 最重要的结论

EDAid 是 ChatEDA 的多 Agent 扩展，但它不是常见的“manager / engineer / executor 多角色讨论”。论文真正定义的角色只有两类：

| 角色 | 论文符号 | 数量 | 职责 |
|---|---|---:|---|
| divergent-thoughts agent | `R0` | 3 | 用不同 few-shot 上下文生成 task planning 与 Python script 候选 |
| decision-making agent | `R1` | 1 | 对每个候选计算回答 `yes` 的 token probability，选概率最高者 |

其主链是：

```text
EDA task + API document
  → 检索相关 tool-use demos
  → 随机组织成不同 few-shot CoT prompt
  → 3 个 R0 Agent 生成 3 份规划/脚本
  → R1 分别判断每份脚本是否解决任务
  → 比较 yes-token probability
  → 选概率最高的脚本
  → 调用 EDA API
```

论文的关键创新是“divergent candidates + learned verifier selection”，不是运行 EDA 工具后根据 log 反馈修正。

当前仓库也没有公开上述多 Agent 实现。它与初版 ChatEDA 共用相同的：

- 50 条训练样例；
- 50 条 ChatEDA-Bench prompt；
- OpenROAD API 文档桩和包装原型。

缺失：

- ChipLlama-8B/70B 权重；
- hybrid instruction training code/完整数据；
- demo embedding、retrieval、group permutation 代码；
- R0 候选生成代码；
- R1 yes-token probability 评分代码；
- KV cache 复用实现；
- iEDA API 与 iEDA-bench；
- benchmark 输出与自动评测器。

因此 EDAid 的当前复现状态是：

| 层级 | 状态 | 说明 |
|---|---:|---|
| 论文机制解读 | R0 | 可完整梳理 |
| 共用数据/API 静态核对 | R1 | 已完成 |
| ChipLlama 推理 | R0 | 缺模型权重和推理代码 |
| 多 Agent 协作 | R0 | 核心实现未公开 |
| iEDA 跨平台实验 | R0 | benchmark/API 均不在仓库 |
| 论文 Table 1–4 重现 | R0 | 缺输出、模型、评分和环境 |

---

## 1. 论文身份与本地文件

本地 PDF：

- 路径：[NAACL2025_Multi-Agent_ChatEDA.pdf](./NAACL2025_Multi-Agent_ChatEDA.pdf)
- 页数：12；
- 文件大小：625,288 bytes；
- SHA256：`9c181e6530741e3ddb098b738d0265cd6b356f9f67308c3f59360d855f86a765`；
- 论文页码：1710–1721。

![论文首页与摘要](./figures/multi-paper-title-abstract.png)

*图源：本地论文 PDF 第 1 页裁剪，包含正式题名、作者和摘要；用于确认系统名、发表信息与主要主张。*

摘要主张：

- EDA flow 的 tool calling 链很长；
- 单 Agent 的中间一步错误会导致整条链失败；
- ChipLlama 是面向 EDA flow automation 微调的专家模型；
- EDAid 让多个 divergent thoughts 收敛到一个目标；
- 多 Agent 在论文 benchmark 上优于单 Agent。

---

## 2. 为什么要从 ChatEDA 升级到 EDAid

初版 ChatEDA 的失败模式是单轨生成：

```text
一个 prompt
→ 一个规划
→ 一份脚本
→ 中间任何一个 API 或参数错误
→ 整条 EDA 流失败
```

EDA 后端流程特别容易发生这种错误，因为：

- stage 必须按依赖顺序执行；
- 同名概念可能属于不同 stage；
- 参数很多且数值范围不同；
- 工具平台之间 API 不同；
- routing 之前的错误可能直到后面才暴露；
- LLM 生成有随机性。

EDAid 的思路不是让同一个 Agent 自我反思多次，而是显式创建不同 few-shot 上下文，让多个 Agent 产生不同方案，再由一个 decision Agent 选择。

---

## 3. 方法全景

![论文 Figure 4：EDAid 多 Agent 总览](./figures/multi-paper-fig4-edaid-overview.png)

*图源：本地论文 PDF 第 4 页 Figure 4 裁剪；用于支撑 divergent demo retrieval、R0 候选生成、R1 decision 和 EDA execution 的完整链路。*

Figure 4 可以拆成两个子系统。

### 3.1 Divergent Thoughts

输入：

- 新 EDA task；
- EDA API document；
- EDA tool usage demo database。

过程：

1. 将新任务 embedding；
2. 在 demo database 中检索相关示例；
3. 把相关示例组织成多个 demo group；
4. 随机选择或排列 demo group；
5. 为不同 R0 Agent 构造不同 few-shot CoT prompt；
6. 每个 Agent 输出 task planning steps 和 EDA Python script。

### 3.2 Decision Making

对每个候选，R1 接收：

```text
EDA task
+ candidate planning steps
+ candidate EDA script
+ yes/no 判定 prompt
```

R1 需要判断候选能否完成任务，并以 `yes` 或 `no` 结束。

系统不只看最终生成的单词，而是读取模型输出 logits，得到 `yes` token probability，再选择概率最大的候选。

### 3.3 EDA Execution

被选中的脚本最终通过 API 连接 EDA tools，目标是完成 RTL-to-GDSII 或用户指定的阶段。

但候选选择阶段本身没有运行 OpenROAD/iEDA，也没有读取真实日志。

这点非常重要：

> EDAid 的“decision-making”是 LLM verifier，不是 EDA execution verifier。

---

## 4. ChipLlama-powered 单 Agent

在进入多 Agent 之前，论文先定义一个 ChipLlama-powered Agent。

![论文 Figure 1：ChipLlama 单 Agent](./figures/multi-paper-fig1-single-agent.png)

*图源：本地论文 PDF 第 2 页 Figure 1 裁剪；用于区分单个 R0 Agent 与后续完整 EDAid。*

输入包括：

- API document；
- EDA task；
- CoT prompt；
- few-shot demonstrations。

输出分两部分：

```text
task planning
→ EDA script
```

论文把这个单 Agent 也称为 role `R0`。做 ablation 时：

- single-agent system = 一个 R0；
- multi-agent system = 完整 EDAid。

因此“EDAid 提升”必须与相同 ChipLlama 的单 Agent 对比，不能只和 GPT-4 比。

---

## 5. ChipLlama 的 Hybrid Instruction Tuning

ChipLlama 基于 Llama3，而初版 AutoMage 基于 Llama2。

论文提供两个规模：

- ChipLlama-8B；
- ChipLlama-70B。

训练语料不只包含 EDA 数据，而是三类混合：

```text
MathInstruct → 逻辑推理
CodeInstruct → 代码生成
EDAInstruct → EDA API 与 flow 知识
```

![论文 Figure 2–3：混合指令微调与 few-shot CoT](./figures/multi-paper-fig2-fig3-training-prompt.png)

*图源：本地论文 PDF 第 3 页 Figure 2 和 Figure 3 裁剪；用于核对三类训练数据及 `(Q,C,A)` few-shot prompt。*

### 5.1 数据量

论文 Appendix Table 5：

| 数据集 | 数量 | 目的 |
|---|---:|---|
| MathInstruct | 80K | 数学/CoT 推理 |
| CodeInstruct | 100K | 编码能力 |
| EDAInstruct | 8K | EDA flow/API 领域知识 |
| 合计 | 188K | hybrid instruction corpus |

![论文 Table 5 与 Agent 数量说明](./figures/multi-paper-table5-training-agent-count.png)

*图源：本地论文 PDF 第 11 页裁剪，包含 Table 5 与 Appendix B；用于核对 80K/100K/8K 数据量和 3 个 R0 + 1 个 R1 的设置。*

这与初版 AutoMage2 的“约 1.5K EDA + 110K code”不同。

当前仓库仍只有 50 条 `chateda_v1.5` 样例，不能代表论文中的 8K EDAInstruct，更不包含 MathInstruct80K 和 CodeInstruct100K 的整理版本。

### 5.2 训练配置

论文实现细节：

| 项目 | 设置 |
|---|---|
| base | Llama3-8B / Llama3-70B |
| tuning | QLoRA |
| schedule | constant learning rate |
| warmup ratio | 0.03 |
| optimizer | paged AdamW |
| learning rate | `1e-4` |
| weight decay | 0 |
| batch size | 128 |
| sequence length | 4096 |
| epochs | 1 |
| hardware | 16 × A100 80GB |

与初版论文的训练参数几乎一致，但模型基座与数据配方改变。

仓库没有 LoRA 配置、训练脚本、seed、checkpoint 和 loss 记录，不能重训对齐。

---

## 6. Few-shot CoT Prompt

论文把一个 demo 表示为：

```text
(Q, C, A)
```

其中：

- `Q`：EDA task；
- `C`：task planning steps；
- `A`：EDA script。

模型学习的联合目标可理解为：

```text
p(A | Q, T) ≈ p(A | Q, T, C) · p(C | Q, T)
```

即：

1. 先在 task `Q` 和 prompt `T` 下生成规划 `C`；
2. 再基于 `Q/T/C` 生成脚本 `A`。

与只生成脚本相比，显式规划的作用是：

- 先检查 stage 顺序；
- 先决定参数归属；
- 再编码；
- 让 decision Agent 同时看到“为什么这样写”和“最终代码”。

### 6.1 Zero-shot 与 Few-shot

论文同时比较：

- zero-shot：只给 task + API + CoT 指令；
- few-shot：再给若干 `(Q,C,A)` demos。

实验表明不同模型都从 few-shot 获益，尤其在 iEDA 跨工具 benchmark 上。

---

## 7. Divergent Thoughts 如何产生差异

多 Agent 不只是把同一个 prompt 复制三次。

论文设计差异来源：

1. 对新任务做语义检索；
2. 取得 top-K relevant demos；
3. 形成多个 demo groups；
4. 随机选择/排列这些 groups；
5. 构建不同 few-shot prompt；
6. 由三个 R0 生成不同候选。

这样既保持示例相关性，又人为制造上下文差异。

它与普通 self-consistency 的关系是：

| 方法 | 差异来源 | 最终选择 |
|---|---|---|
| temperature sampling | 同 prompt 的随机采样 | 多数票/打分 |
| CoT self-consistency | 多条推理路径 | 答案一致性 |
| EDAid | 不同相关 demo 组合 + LLM 生成 | R1 yes probability |

论文没有公开：

- embedding 模型；
- top-K 数值；
- 每组 demo 数量；
- 随机种子；
- prompt 的最终字符串；
- 候选解码超参数。

这些都是严格复现 divergent thoughts 所必需的。

---

## 8. Agent 数量

Appendix B 明确说明实验使用：

```text
3 个 divergent-thought agents
+ 1 个 decision-making agent
```

论文观察：

- R0 数量少于 3 时，增加 Agent 能提升稳定性和准确率；
- 到 3 个后性能趋于饱和；
- 更多 Agent 不一定带来显著提升；
- 真实 EDA flow 成本高，需要权衡模型推理与工具执行成本。

但仓库没有给出对应 Agent-count 曲线或逐点结果，只在附录文字中说明。

---

## 9. Decision Agent 的选择机制

## 9.1 输入模板

R1 对每个候选单独构造判断问题，大意为：

```text
你是一个 AI assistant。
给定 EDA task、planning steps 和 EDA script，
判断脚本是否能完成任务，回答 yes 或 no。
```

### 9.2 分数

对于候选 `j`，系统读取模型在回答位置对 `yes` token 的概率：

```text
score_j = P_R1(yes | task, plan_j, script_j)
```

最终：

```text
j* = argmax_j score_j
```

### 9.3 为什么只用开源模型

论文说明多 Agent 实验只使用开源模型，因为 selection 需要输出 logits。

普通闭源 chat API 通常只返回文本或有限 logprobs，不能保证取得论文需要的完整 yes-token probability。

### 9.4 不是“修复后再执行”

论文 Figure 7 把 R1 描述为能识别并修正脚本错误，但 Figure 4 的主算法是从候选中选择最高分脚本。

从论文开源可核验范围看，没有：

- 执行候选；
- 解析 EDA error log；
- 自动 patch；
- 重新运行直到成功。

所以更严谨的表述是：

> R1 通过模型判断筛选或给出正确方案；论文没有提供基于真实工具反馈的 iterative repair 实现。

---

## 10. KV Cache 优化

论文指出不同候选的 system prompt 和任务部分相同，因此可以缓存共同前缀的 KV cache，避免重复计算。

这个优化适用于：

- 同一模型；
- 相同 tokenized prefix；
- 本地推理引擎支持 prefix/KV cache 复用；
- 候选差异只出现在后缀。

但仓库没有推理代码，无法确认使用 vLLM、Transformers 或其他引擎，也不能测量论文系统的实际 latency/memory。

---

## 11. 两个 Benchmark

### 11.1 ChatEDA-Bench

- 基于 OpenROAD API；
- 50 个任务；
- 公开在 [data/test/ChatEDA-Bench.txt](./data/test/ChatEDA-Bench.txt)；
- simple 30%、complex 30%、parameter tuner 40%。

### 11.2 iEDA-bench

- 基于 iEDA；
- 50 个任务；
- 用来测试跨 EDA tool/platform 泛化；
- 当前仓库没有对应 prompt、API document、implementation 或 design assets。

因此论文关于 iEDA 的所有结果目前只能作为论文报告值引用。

### 11.3 评测指标

论文称指标是生成 EDA script 的 accuracy，并关联脚本是否成功自动化 EDA flow。

当前仓库缺少：

- 每题 reference；
- execution harness；
- design/PDK；
- 成功判定；
- 失败分类；
- 生成结果；
- summary file。

不能仅靠 50 个 prompt 重新计算 accuracy。

---

## 12. 主结果 Table 1

![论文 Table 1：ChatEDA-bench 与 iEDA-bench 主结果](./figures/multi-paper-table1-main-results.png)

*图源：本地论文 PDF 第 6 页 Table 1 裁剪；用于核对两套 benchmark 的主结果及表下注释。*

论文报告：

| 系统 | 模型 | ChatEDA-bench | iEDA-bench |
|---|---|---:|---:|
| ChatEDA | GPT-3.5 | 28% | 30% |
| ChatEDA | GPT-4 | 62% | 70% |
| ChatEDA | AutoMage-70B | 74% | - |
| ChatEDA | AutoMage2-70B | 82% | - |
| EDAid | ChipLlama-8B | 88% | 84% |
| EDAid | ChipLlama-70B | **100%** | **100%** |

表下注释很重要：

- GPT-3.5、GPT-4、AutoMage 在 ChatEDA-bench 的值直接引用初版论文；
- AutoMage 模型不可获得，所以没有在 iEDA-bench 评测；
- EDAid/ChipLlama 的值来自本论文。

### 12.1 对 100% 的正确理解

100% 表示论文的 50 个脚本任务都被判定正确，不等于：

- 所有 OpenROAD/iEDA 设计都收敛；
- PPA 都达到目标；
- 任意新 EDA API 都能泛化；
- 多次不同 seed 都是 100%；
- tapeout signoff 100%。

由于 benchmark 只有 50 题，单题就是 2 个百分点。

---

## 13. Ablation：Hybrid Instruction Tuning

论文 Table 2：

| Base | Hybrid tuning | ChatEDA | iEDA |
|---|---:|---:|---:|
| Llama3-8B | 否 | 78% | 50% |
| Llama3-8B | 是 | 78% | 76% |
| Llama3-70B | 否 | 88% | 74% |
| Llama3-70B | 是 | 94% | 96% |

![论文 Table 2–4：消融实验](./figures/multi-paper-table2-table4-ablations.png)

*图源：本地论文 PDF 第 7 页左栏裁剪；包含 hybrid tuning、zero/few-shot 与 single/multi-agent 三组消融。*

可见：

- 8B 在 ChatEDA 上没有提升，但 iEDA 从 50% 到 76%；
- 70B 在 ChatEDA 从 88% 到 94%；
- 70B 在 iEDA 从 74% 到 96%。

论文据此强调 hybrid data 对跨工具泛化更重要。

但“无 hybrid tuning”具体用了什么 EDA-only 数据、相同 token 数与否、模型 checkpoint 如何得到，仓库没有 config 可核对。

---

## 14. Ablation：Zero-shot 与 Few-shot

论文 Table 3：

| 模型 | ChatEDA zero | ChatEDA few | iEDA zero | iEDA few |
|---|---:|---:|---:|---:|
| GPT-3.5 | 28% | 56% | 30% | 50% |
| GPT-4 | 62% | 82% | 70% | 84% |
| ChipLlama-8B | 74% | 78% | 64% | 76% |
| ChipLlama-70B | 90% | 94% | 90% | 96% |

所有模型都提升，但提升幅度不同。

这支持“API demos 能提高 tool grounding”的结论；不能单独证明 CoT 推理本身贡献，因为 few-shot 同时改变了示例信息量和 prompt 长度。

---

## 15. Ablation：Single Agent 与 Multi Agent

论文 Table 4：

| 模型 | 系统 | ChatEDA | iEDA |
|---|---|---:|---:|
| ChipLlama-8B | single | 78% | 76% |
| ChipLlama-8B | multi | 88% | 84% |
| ChipLlama-70B | single | 94% | 96% |
| ChipLlama-70B | multi | 100% | 100% |

换算到 50 题：

| 模型 | ChatEDA 多答对 | iEDA 多答对 |
|---|---:|---:|
| 8B | 5 题 | 4 题 |
| 70B | 3 题 | 2 题 |

这个换算能直观看出多 Agent 的收益规模，也提醒我们需要报告随机性和 confidence interval；论文表格没有给多 seed 方差。

---

## 16. Case Study：参数放错 API

论文 Figure 6 使用任务：

```text
在 asap7 上为 router 设计测试不同 clock period 和 channel value。
```

正确逻辑：

```python
tool.floorplan(macro_place_channel=channel_value)
...
tool.global_route()
```

错误候选把参数放到：

```python
tool.global_route(channel_value)
```

而 `global_route` 没有 `macro_place_channel` 参数。

![论文 Figure 6：正确与错误 divergent thoughts](./figures/multi-paper-fig6-divergent-thoughts.png)

*图源：本地论文 PDF 第 8 页 Figure 6 裁剪；用于说明 `macro_place_channel` 被错误传给 `global_route` 的典型失败。*

这类错误非常适合用确定性 schema/AST validator 发现，不一定需要另一个 70B 模型。

论文选择 learned verifier 的优点是可以同时判断更复杂的语义目标；工程实现中更合理的是：

```text
静态规则过滤明显 API 错误
→ LLM verifier 比较剩余候选
→ sandbox 执行验证
```

---

## 17. Case Study：脚本诊断与纠正

论文 Figure 7 有两类错误：

1. 用户要求 final-stage performance，脚本却在 CTS 后取指标并停止；
2. 用户要求 CTS，脚本把 `tns_end_percent` 传给 `placement`。

R1 能生成包含必要阶段、参数位置正确的脚本。

![论文 Figure 7：错误识别与脚本纠正](./figures/multi-paper-fig7-error-correction.png)

*图源：本地论文 PDF 第 9 页 Figure 7 裁剪；用于说明 final-stage 遗漏与 `tns_end_percent` 参数错位的诊断案例。*

但当前开源 benchmark 只有这些任务文本，没有 Figure 7 对应的机器可读输入/输出和 decision score。

因此能核对案例逻辑，不能复现 R1 的概率排序。

---

## 18. EDAid 与真实工具反馈闭环的区别

EDAid 在论文图中最终连接 EDA tools，但它的候选选择过程是：

```text
读任务和候选文本
→ 语言模型判断 yes/no
→ 选最高 yes probability
```

真正的工具反馈闭环会是：

```text
执行候选
→ 获取 syntax error / return code / OpenROAD log / metric
→ 定位失败阶段
→ 修改脚本
→ 从 checkpoint 恢复或重跑
```

论文/仓库没有提供后一套机制。

所以组会中更准确的说法是：

> EDAid 是候选生成—判别闭环，而不是工具执行—日志修复闭环。

---

## 19. 当前仓库与 EDAid 的关系

README 同时列出 ChatEDA 和 EDAid 论文，并声称训练样例可用于 AutoMage 和 ChipLlama。

但文件结构仍是：

```text
README.md
api_doc/openroad_api.py
api_doc/openroad_api_impl.py
api_doc/parse_mk_config.py
data/train/ChatEDA-train-example.json
data/test/ChatEDA-Bench.txt
```

不存在：

```text
chipllama/
train_chipllama.py
edaid/
agents.py
retriever.py
decision.py
prompts/
ieda_api.py
iEDA-Bench.txt
evaluate.py
```

因此当前代码树不含 EDAid 核心实现。

---

## 20. 共用 OpenROAD wrapper 能提供什么

[api_doc/openroad_api_impl.py](./api_doc/openroad_api_impl.py) 可以证明作者构造了怎样的 Python-to-ORFS 映射原型，例如：

```text
floorplan → floorplan/io placement/macro/tapcell/pdn Tcl
placement → global place/IO/resize/detail place Tcl
CTS → cts/fillcell Tcl
route → global_route/detail_route Tcl
```

但它不能证明：

- R0 如何加载模型；
- demo 如何检索；
- prompt 如何分组；
- R1 如何取 logits；
- 最终候选如何执行；
- 跨 iEDA 如何切换 API；
- benchmark 成功如何判定。

此外包装器本身已有详细静态缺陷，见 [ChatEDA论文与代码复现详解.md](./ChatEDA论文与代码复现详解.md#17-各-eda-stage-的代码映射) 的第 15–21 节。

最关键的几项是：

- `global_route` 不返回 status；
- `get_metric` 映射失效；
- `tune` 文档名与 `tuned` 实现名不一致；
- `step=0` 与 Ray `quniform` 不兼容；
- stage 失败常被后续文件复制异常掩盖。

所以即便补齐多 Agent 代码，也不能直接把当前 wrapper 当作可靠 oracle。

---

## 21. 训练数据开放差距

本地 JSON 静态统计：

```text
rows                : 50
unique instructions : 50
unique outputs      : 50
dataset label       : chateda_v1.5
```

论文 ChipLlama 数据：

```text
MathInstruct : 80,000
CodeInstruct : 100,000
EDAInstruct  : 8,000
```

对比：

| 内容 | 论文 | 当前仓库 |
|---|---:|---:|
| EDA instructions | 8,000 | 50 examples |
| math instructions | 80,000 | 0 |
| code instructions | 100,000 | 0 |
| 总量 | 188,000 | 50 |
| 数据生成/清洗代码 | 应存在 | 无 |
| 训练 split | 未公开到仓库 | 无 |

50 条样例适合了解格式，不适合重训 ChipLlama。

---

## 22. benchmark 开放差距

| 资产 | ChatEDA-bench | iEDA-bench |
|---|---:|---:|
| 50 条 requirement | 有 | 无 |
| API document | OpenROAD 版有 | 无 |
| API implementation | OpenROAD 原型有 | 无 |
| reference scripts | 无 | 无 |
| task labels | 无 | 无 |
| model outputs | 无 | 无 |
| execution logs | 无 | 无 |
| automated scorer | 无 | 无 |

因此当前仓库最多支持对 ChatEDA-bench 做自建静态评估，无法对齐论文 iEDA 结果。

---

## 23. 论文结果可重复性风险

### 23.1 模型版本

论文写 Llama3，但未在仓库锁定具体 Hugging Face revision、tokenizer revision 或上下文模板。

### 23.2 生成参数

缺少：

- temperature；
- top-p/top-k；
- max new tokens；
- stop tokens；
- sampling seed；
- tensor parallel 配置。

### 23.3 Retrieval

缺少：

- embedding model；
- vector normalization；
- top-K；
- demo group size；
- permutation algorithm；
- random seed。

### 23.4 Decision

缺少：

- exact prompt；
- `yes` 是一个 token 还是多个 token；
- 大小写/空格 token 处理；
- score 是否归一化为 yes-vs-no；
- 同分策略；
- decision model 与 R0 是否共享权重。

### 23.5 执行和评测

缺少：

- ORFS/iEDA commit；
- PDK 与 design；
- timeout；
- success condition；
- 每题日志；
- 多 seed 方差。

这些缺口共同决定 Table 1–4 目前不能严格重现。

---

## 24. 为什么 `yes` probability 不一定等于正确性

R1 的 score 是模型置信度，不是形式化证明。

可能的失效包括：

- 模型对更长、更流畅的错误脚本过度自信；
- 所有候选都错，但仍必须选一个最高分；
- prompt wording 改变 yes prior；
- 参数范围错误不容易从自然语言判断；
- API implementation 与文档不一致；
- 语法正确但 EDA 工具运行失败；
- script 满足流程却不满足 PPA 条件。

更稳健的选择器应分层：

```text
AST/Schema Validator
→ Stage Dependency Checker
→ Restricted Dry Run
→ EDA Execution Result
→ LLM Semantic Judge
```

论文的 R1 可以放在其中一层，而不是唯一 oracle。

---

## 25. 成本与延迟

完整 EDAid 对每个任务至少涉及：

- 3 次 R0 generation；
- 3 次 R1 candidate scoring；
- 1 次最终脚本执行；
- retrieval 和 prompt construction。

如果 R0/R1 都是 70B，推理成本显著高于单 Agent。

论文 limitation 明确承认 multi-agent 带来额外 inference latency，因为 divergent thoughts 与 decision-making 都需要多次 LLM inference。

论文没有提供：

- tokens/task；
- latency/task；
- GPU hours；
- KV cache 节省比例；
- 8B 与 70B 成本对比；
- 单题 OpenROAD 执行时间。

所以只能确认性能提升，不能评估 cost–accuracy Pareto。

---

## 26. 与初版 ChatEDA 的逐项比较

| 维度 | ChatEDA / AutoMage2 | EDAid / ChipLlama |
|---|---|---|
| 年份 | TCAD 2024 | NAACL 2025 |
| base model | Llama2 | Llama3 8B/70B |
| EDA data | 约 1.5K | 8K |
| 通用数据 | 约 110K code | 80K math + 100K code |
| inference | 单 controller | 3 R0 + 1 R1 |
| few-shot | 论文 CoT prompt | retrieval + divergent demo groups |
| selection | 单输出 | yes-token probability |
| benchmark | ChatEDA-bench | ChatEDA-bench + iEDA-bench |
| ChatEDA result | 82% Grade A | 100% accuracy（70B） |
| 工具反馈 repair | 无完整闭环 | 仍无真实 log repair 实现 |
| 当前核心代码 | 未公开 | 未公开 |

最本质的代际升级：

```text
单一路径生成
→ 多路径生成 + 模型判别
```

---

## 27. 可以复现的最低版本

不训练 ChipLlama、不执行 EDA，也可以构建一个方法级 mini reproduction：

1. 读取 50 条 ChatEDA-Bench；
2. 从 50 条训练样例中做 embedding retrieval；
3. 为每题形成 3 个不同 demo groups；
4. 用现有本地开源模型生成 3 个结构化 action plans；
5. 用同一模型或另一个模型做 yes/no score；
6. 用 AST/schema 规则检查；
7. 人工记录是否满足需求。

这个实验只能复现 EDAid 的“divergent + decision”思想，不能声称复现论文 ChipLlama 或 100% 结果。

本次没有执行这一路线，因为用户要求优先阅读已有代码和论文，并避免重复模型推理。

---

## 28. 真正端到端复现所需资产

### 模型与训练

- Llama3 固定 revision；
- 188K 训练 corpus；
- QLoRA config；
- training script；
- checkpoint；
- tokenizer/chat template；
- seed 与训练日志。

### Agent 系统

- embedding/retrieval；
- demo database；
- divergent prompt builder；
- 3 个 R0 generator；
- R1 probability scorer；
- KV cache；
- candidate storage；
- failure handling。

### EDA 执行

- 修复后的 OpenROAD wrapper；
- iEDA wrapper；
- 固定工具 commit；
- PDK 和 design suite；
- 容器；
- timeout；
- results/log parser。

### 评测

- 两套 benchmark 的完整 100 题；
- reference/acceptance rules；
- per-task outputs；
- exact-match 与 execution score；
- 多 seed；
- latency/cost。

当前仓库只覆盖上述清单的一小部分。

---

## 29. 工程上值得延伸的方向

### 29.1 Deterministic checker 优先

Figure 6 的参数归属错误可以由函数签名直接发现。先用确定性检查器过滤，可减少 70B verifier 的调用。

### 29.2 真正 execution-grounded selection

对通过静态检查的候选做受限执行，使用：

- return code；
- stage completion；
- expected output files；
- metric availability；
- tool error category；

作为选择依据，比纯 yes probability 更可靠。

### 29.3 状态与 checkpoint

EDA stage 成本高，应保存：

```text
synthesis checkpoint
floorplan checkpoint
placement checkpoint
CTS checkpoint
```

候选只在首次分歧 stage 之后重跑，避免每个 Agent 从 setup 重跑。

### 29.4 API/version contract

模型所读 API 文档必须从真实 Python signature 自动生成，并绑定 wrapper commit。当前 `tune/tuned` 的错位就是反例。

### 29.5 不确定性校准

R1 的 yes probability 应做 calibration，并允许：

```text
所有候选低于阈值 → 拒绝执行 / 重新生成
```

论文的 argmax 会在全错时仍选一个。

---

## 30. 组会分享建议

### 30.1 推荐主线

1. ChatEDA 单 Agent 为什么会在长链 API 调用中失败；
2. ChipLlama 如何用 math/code/EDA hybrid data 补推理、编码和领域知识；
3. retrieval 如何构造不同 few-shot thoughts；
4. 三个 R0 如何产生候选；
5. R1 如何用 yes-token probability 选择；
6. Table 1 的 100% 和 Table 4 的多 Agent 增益；
7. Figure 6/7 的典型 API 错误；
8. 仓库实际没开源哪些部分；
9. 为什么下一步应做静态验证 + 真实 execution feedback。

### 30.2 最值得展示的图表

- Figure 4：完整 EDAid；
- Table 1：主结果；
- Table 2–4：数据/few-shot/multi-agent 消融；
- Figure 6：divergent candidate 的单参数错误；
- Figure 7：decision Agent 的诊断案例；
- Table 5：188K hybrid data。

### 30.3 一句话评价

> EDAid 用“相关示例驱动的多候选 + 模型概率判别”提高长链 EDA API 脚本正确率，但当前开源仓库没有 ChipLlama 和多 Agent 核心代码，论文的 100% 只能作为报告结果，尚不能本地复现。

---

## 31. 论文主张、源码事实、本地证据分离

| 陈述 | 证据类型 | 当前结论 |
|---|---|---|
| ChipLlama-70B 在两套 benchmark 100% | 论文 Table 1 | 论文报告值 |
| multi-agent 优于 single-agent | 论文 Table 4 | 论文报告值，无多 seed |
| 使用 3 个 R0 + 1 个 R1 | 论文 Appendix B | 方法设置 |
| R1 使用 yes-token probability | 论文 Figure 4/方法节 | 方法定义 |
| 仓库含 EDAid 实现 | 源码树 | 否 |
| 仓库含 8K EDAInstruct | 数据统计 | 否，仅 50 条样例 |
| 仓库含 iEDA-bench | 文件树 | 否 |
| OpenROAD wrapper 可直接支撑评测 | 源码静态检查 | 否，存在关键缺陷 |
| 本地已运行 ChipLlama/EDAid | 本地记录 | 否 |

这种分层可以避免把论文数字误写成本地运行结果。

---

## 32. 可追溯材料

### 本地论文与图

- 原论文：[NAACL2025_Multi-Agent_ChatEDA.pdf](./NAACL2025_Multi-Agent_ChatEDA.pdf)
- 初版论文：[2308.10204_ChatEDA.pdf](./2308.10204_ChatEDA.pdf)
- 论文截图：[figures](./figures/)

### 共用代码与数据

- README：[README.md](./README.md)
- API 文档：[api_doc/openroad_api.py](./api_doc/openroad_api.py)
- OpenROAD wrapper：[api_doc/openroad_api_impl.py](./api_doc/openroad_api_impl.py)
- config parser：[api_doc/parse_mk_config.py](./api_doc/parse_mk_config.py)
- 训练样例：[data/train/ChatEDA-train-example.json](./data/train/ChatEDA-train-example.json)
- ChatEDA-Bench：[data/test/ChatEDA-Bench.txt](./data/test/ChatEDA-Bench.txt)
- 静态审计：[runs/static_audit_20260802.json](./runs/static_audit_20260802.json)

### 初版详细解读

- [ChatEDA论文与代码复现详解.md](./ChatEDA论文与代码复现详解.md)

### 本次明确未执行

- 未运行 LLM inference；
- 未训练/微调；
- 未调用在线 API；
- 未运行 OpenROAD 或 iEDA；
- 未重算论文 Table 1–4；
- 未把论文结果冒充本地结果。
