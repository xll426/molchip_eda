# RTLCoder（LAD 2024）论文、代码与本地复现详解

> 论文：*RTLCoder: Outperforming GPT-3.5 in Design RTL Generation with Our Open-Source Dataset and Lightweight Solution*  
> 会议：IEEE International Workshop on LLM-Aided Design（LAD 2024）  
> 原文：[2312.08617_RTLCoder.pdf](./2312.08617_RTLCoder.pdf)  
> 本文件是面向入门、复现和选题判断的论文—代码核对版，不替代上游 `README.md`。  
> 本地仓库：`/mnt/d/AI4eda/RTL-Coder`  
> 上游仓库：<https://github.com/hkust-zhiyao/RTL-Coder>  
> 本地基线 commit：`b2847073be62d5f1d6d9b17bb247f0cfeb1ce642`  
> 核验日期：2026-07-20

```text
┌─────────────────────────────────────────────────────────────────────────┐
│ P1 任务定义                                                              │
├─────────────────────────────────────────────────────────────────────────┤
│ Input:  自然语言硬件规格（含模块名、端口、位宽、行为、时序要求）+ 可选    │
│         module header                                                     │
│ Output: 完整 Verilog/SystemVerilog RTL 模块（通常只输出 module...endmodule│
│         内的实现）                                                        │
│ Supervision: 训练用约 27k 合成 instruction-response 对做 MLE SFT；        │
│              quality-scoring 训练用同一问题的多候选 RTL 及外部质量分数；    │
│              推理后的语法/功能由 Icarus/Verilator/testbench 判定        │
│ Why-hard: 合成数据有噪声且未必功能正确；模型只生成 token 不保证可综合；   │
│           testbench 覆盖有限；量化权重不适合继续训练；公开 benchmark 存在   │
│           污染风险                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 1. 一句话说明

RTLCoder 是一个把**自然语言硬件规格转换为 Verilog RTL** 的 7B 级代码生成模型项目。它的重点不是发明新的 Transformer，而是构造 RTL 指令数据、按候选代码质量打分训练，并开放数据、训练脚本和量化权重。

## 2. 它位于芯片 EDA 的哪一步

```text
产品/架构需求
    ↓
微架构与模块规格
    ↓
[RTLCoder：自然语言规格 → Verilog RTL]
    ↓
Lint / 编译 / 功能仿真 / 形式验证
    ↓
逻辑综合 → 门级网表
    ↓
布局布线 → GDSII → 签核/流片
```

准确定位：**数字 IC 前端的 RTL 设计辅助**。

它不负责：

- 模拟电路设计；
- 逻辑综合、布局、布线、时序收敛；
- DRC/LVS/signoff；
- 自动证明生成代码一定满足规格。

仓库用 VerilogEval、RTLLM 和仿真器评测输出，但“使用仿真评测”不等于项目本身覆盖完整验证流程。

### 2.1 模型结构：通俗版

RTLCoder-v1.1 不是“把 Yosys 或仿真器做进神经网络”，而是在 Mistral 系代码语言模型上继续训练。模型看到的是 token，不直接看到 AST、波形、网表或版图。

本地 GGUF 文件的元数据给出：32 个 Transformer block、隐藏宽度 4096、32 个 query head、8 个 KV head、FFN 宽度 14336。它的每一层大致做两件事：

1. **自注意力**：当前 token 根据前面的规格、模块头和已生成代码选择应关注的位置。8 个 KV head 被 32 个 query head 共享，属于 grouped-query attention，可减少 KV cache。
2. **前馈网络**：每个 token 的 4096 维状态先扩展到 14336 维做非线性变换，再压回 4096 维，学习 Verilog 语法、常见电路模式和规格—代码对应关系。

32 层后，LM head 把隐藏向量投影为下一个 token 的概率。不断重复“预测下一个 token”，才得到完整 `module ... endmodule`。模型没有独立的综合层、仿真层或正确性判别头；这些必须在生成后由 Icarus、Verilator、Yosys 或 formal 工具完成。

### 2.2 4-bit 权重意味着什么

本地 `Q4_0` GGUF 把大部分矩阵压到约 4 bit，使 7B 模型约 4.1 GB、可在 CPU 上运行。量化改变数值精度但不改变 32 层结构；它适合推理，不等于 4-bit 训练，也不能直接拿这个 GGUF 继续论文的全参数 SFT。

## 3. 输入、推理过程和输出

### 3.1 推理输入

输入是普通文本 prompt，最好明确写出：

1. 模块名；
2. 所有输入/输出端口及位宽；
3. 时钟沿和复位极性；
4. 组合/时序行为；
5. 延迟、握手和边界条件；
6. 已知模块头。

最小示例：

```text
Please act as a professional verilog designer and provide a half adder.
Only output the complete Verilog module.
module half_adder(
    input a,
    input b,
    output sum,
    output carry
);
```

### 3.2 推理过程

```text
自然语言规格 + 可选模块头
    ↓ tokenizer
自回归 7B causal language model
    ↓ 逐 token 生成
抽取 module ... endmodule
    ↓
Icarus/Verilator 编译和 testbench 仿真（必须额外执行）
```

模型本身只做 token 生成。语法编译、功能仿真和结果判定是模型外部的确定性步骤。

### 3.3 推理输出

输出是 Verilog/SystemVerilog 文本。例如本机实际生成：

```verilog
module half_adder(
    input a,
    input b,
    output sum,
    output carry
);
    assign sum = a ^ b;
    assign carry = a & b;
endmodule
```

本机的 `local_cpu_inference.py` 已完成一次固定 seed 的端到端验证：

- 模型：`RTLCoder-v1.1-gguf-4bit/ggml-model-q4_0.gguf`；
- SHA-256：`860753548c58bc298db10e0173e73b73f89724ce848b6be1491cd01eb7131a54`；
- GPU offload：0 层，即不使用显存；
- 编译：通过；
- 仿真：`PASS 4/4 vectors`；
- 记录：`runs/local_cpu_half_adder/record.json`。

## 4. 使用它是否需要训练

### 4.1 只使用已有模型：不需要训练

最推荐的入门路线是直接使用作者提供的免费权重：

- `ishorn5/RTLCoder-v1.1`：Mistral 系全精度/半精度版本；
- `ishorn5/RTLCoder-Deepseek-v1.1`：DeepSeek-Coder 6.7B 系版本；
- `ishorn5/RTLCoder-v1.1-gptq-4bit`：GPU 4-bit；
- `ishorn5/RTLCoder-v1.1-gguf-4bit`：可纯 CPU 推理。

本地已经采用 GGUF 4-bit 版本，不需要付费 API。

### 4.2 复现论文训练或适配私有任务：需要训练

上游提供三条训练路线：

| 路线 | 脚本 | 数据要求 | 目的 |
|---|---|---|---|
| 普通 SFT/MLE | `train/mle.py` | 每条规格对应至少一份 RTL | 学会 spec→RTL |
| 质量打分训练 | `train/mle_scoring.py` | 每条规格有多份候选 RTL 和分数 | 偏向高质量候选 |
| 梯度拆分打分训练 | `train/mle_scoring_grad_split.py` | 同上 | 降低多候选训练显存峰值 |

官方命令按 4 个进程、FP16、DeepSpeed stage 2 编写，属于多 GPU 全参数微调方案。当前单机环境不应直接照搬启动。若只是做领域适配，更现实的路线是另外接入 LoRA/QLoRA；上游这三份脚本没有直接提供完整 PEFT 配置，需要单独改造并重新做消融。

## 5. 训练数据从哪里来

![LAD 论文 Figure：关键词、instruction、reference code 与训练数据生成流程](./figures/dac-paper-dataset-training-flow.png)

### 5.1 已提供的 Resyn-27k

路径：`dataset/Resyn27k.json`，约 27k 条。

来源流程：

```text
约 350 个硬件关键词/十余类电路
    ↓ prompt 模板
GPT-3.5 生成自然语言规格和参考 RTL
    ↓ 清洗/候选质量处理
Instruction–Response 训练对
```

重要限制：

- 数据由 GPT-3.5 合成，不保证每条 RTL 功能正确；
- 很多样本没有独立 testbench；
- 本地抽查即可看到部分样本存在端口、时序语义或可综合性问题；
- 训练前应先用 parser、Icarus/Verilator、Yosys 和自动 testbench 做二次过滤；
- 数据来源与模型输出的再分发/商用权利需要单独核验。

使用仓库已有数据不需要调用任何 API。

### 5.2 自己扩充数据

`data_generation/instruction_gen.py` 是旧版 OpenAI API 数据生成脚本。没有必要购买 API：可以把 teacher 替换为本地开源权重模型，或让本地 vLLM/Ollama 暴露 OpenAI-compatible endpoint。

但“把 GPT-3.5 换成本地模型”只解决费用问题，不解决标签正确性。新增样本至少应经过：

1. JSON schema 校验；
2. Verilog parser/编译；
3. 针对规格生成或人工编写 testbench；
4. 仿真通过；
5. 可选 Yosys 综合；
6. 去重以及与测试集的污染检查。

## 6. 训练数据格式和例子

文件扩展名虽然是 `.json`，训练代码实际按**每行一个 JSON 对象（JSONL）**读取，不是一个外层 JSON 数组。

### 6.1 普通 SFT 格式

必需字段：

- `Instruction`：自然语言规格；
- `Response`：RTL 字符串数组；`mle.py` 实际取最后一个 `Response[-1]`。

最小示例：

```json
{"Instruction":"Design a 1-bit half adder with inputs a, b and outputs sum, carry.","Response":["module half_adder(input a,input b,output sum,output carry); assign sum=a^b; assign carry=a&b; endmodule"]}
```

训练时拼接方式约为：

```text
source = Instruction + "\n"
target = Response[-1] + eos_token
```

loss 会屏蔽 Instruction 对应 token，只监督 Response。

### 6.2 质量打分训练格式

`train/scoring_data_sample.json` 展示了四个字段：

- `Instruction`：任务规格；
- `Input`：可选的已有模块头/上下文；
- `Response`：同一问题的多份候选 RTL；
- `Score`：与候选一一对应的浮点质量分数。

最小化示例：

```json
{"Instruction":"Generate a 2-input AND gate.","Input":"module and2(input a,input b,output y);","Response":["assign y=a&b; endmodule","assign y=a|b; endmodule"],"Score":[1.0,0.0]}
```

仓库样例的真实分数形态类似：

```json
"Score": [0.4037882049, 0.3554884189, 0.0022547914, 1]
```

`mle_scoring.py` 会把每条 instruction 的所有候选展开，计算 token loss，并增加使模型排序倾向与 `Score` 排序一致的比较损失。

## 7. 项目的主要创新点

![LAD 论文 Table II：VerilogEval 与 RTLLM 主结果](./figures/dac-paper-main-results.png)

### 7.1 论文结果应怎样解读

| 模型 | EvalMachine Pass@1 | EvalHuman Pass@1 | RTLLM Function Pass@5 |
|---|---:|---:|---:|
| Mistral-7B base | 36.9% | 4.49% | 20.7% |
| RTLCoder-Mistral-Direct | 58.9% | 34.4% | 41.4% |
| RTLCoder-Mistral | 62.5% | 36.7% | 48.3% |
| DeepSeek-Coder-6.7B base | 54.1% | 30.2% | 34.5% |
| RTLCoder-DeepSeek-Direct | 59.8% | 39.1% | 44.8% |
| RTLCoder-DeepSeek | 61.2% | 41.6% | 48.3% |

`Direct` 表示只对合成 instruction/reference 做普通 MLE；不带 `Direct` 的完整版本再加入多候选质量排序训练。论文表明数据本身带来大部分提升，quality-scoring 在此基础上继续提升。论文宣称超过 GPT-4 的范围仅是 EvalMachine Pass@1：62.5% vs 60.0%；不能泛化成“所有 RTL 任务全面超过 GPT-4”。

1. **面向 RTL 的合成指令数据管线**：从硬件关键词扩展到大约 27k 个规格—代码对，缓解公开 RTL 指令数据不足。
2. **质量分数进入训练目标**：不仅学习“参考代码长什么样”，还让模型在多候选之间偏向高分 RTL。
3. **梯度拆分降低训练内存**：对多候选比较训练进行拆分，使有限 GPU 环境更可行。
4. **完整交付链较开放**：仓库包含数据生成、训练、benchmark inference，并链接多种权重和 4-bit 量化版本。
5. **轻量部署**：7B 量化模型可纯 CPU 运行，适合离线、隐私敏感场景。

要注意：创新核心是**数据与训练策略**，不是新的 EDA 算法，也不是完整的自动验证 Agent。

## 8. 免费/开源替代方案

| 环节 | 原项目可能使用 | 无付费 API 路线 |
|---|---|---|
| 直接 RTL 推理 | 作者 HF 权重 | 本地 RTLCoder GGUF 4-bit（已验证） |
| 全精度/半精度推理 | HF Transformers | 本地下载 RTLCoder-v1.1/Deepseek-v1.1 |
| 扩充训练规格 | GPT-3.5 API | 本地开源 instruct/code 模型 + vLLM/Ollama |
| 编译/仿真 | Icarus | Icarus 或 Verilator |
| 综合检查 | 未作为主训练环 | Yosys |
| 更强正确性约束 | 人工/benchmark TB | cocotb、SymbiYosys、形式属性与差分仿真 |

“开源权重”与“OSI 开源软件许可证”不是一回事。当前 pinned commit 的仓库根目录未找到明确 `LICENSE` 文件；实际用于公司项目或再分发前，必须分别核对代码、数据、基础模型和微调权重许可证。

## 9. 复现路线建议

### 路线 A：入门与推理验证（当前已完成）

```bash
conda run -n mage python local_cpu_inference.py \
  --model weights/RTLCoder-v1.1-gguf-4bit/ggml-model-q4_0.gguf \
  --threads 4 --context-length 1024 --batch-size 64
```

脚本包含低内存保护，默认要求约“两倍模型文件大小 + 2 GiB”可用内存，并强制 `n_gpu_layers=0`。

### 路线 B：20—50 题小评测

1. 固定 VerilogEval release/commit；
2. 先跑 greedy 或固定 seed 的 pass@1；
3. 每题保存 prompt、raw output、提取后的 RTL、编译日志和仿真日志；
4. 限制并发为 1，模型常驻、题目串行，避免反复加载和内存峰值；
5. 报告 compile-pass 与 functional-pass，不只报语法率。

### 路线 C：训练研究

不要先做全量训练。先选 500—2,000 条具有 testbench 的小数据集，比较：

- 原始 SFT；
- 编译过滤 SFT；
- 功能仿真过滤 SFT；
- quality-ranking loss；
- LoRA 与 full fine-tuning。

只有功能正确率、未见任务泛化或 PPA 指标显著提升，才值得扩大训练。

## 10. 这个方向是否已经卷或饱和

### 判断

**“小型文本规格 → 单文件 RTL → 在 VerilogEval/RTLLM 上报 pass@k”已经非常拥挤，不适合再做低差异重复。** RTLCoder 之后已经出现 CodeV、CraftRTL、OriGen、AutoVCoder、VerilogCoder、MAGE、VeriCoder 等数据、微调和 Agent 路线；新工作若只是换一个 7B 底模、再合成一批数据，很难形成持久创新。

但整个方向没有饱和，仍值得进入的空白包括：

1. **真实复杂规格**：多模块、多文件、协议、参数化和长上下文，而不是几十行 toy RTL；
2. **功能正确性数据**：每条样本带可审计 testbench/formal property，而不是“编译通过即正确”；
3. **验证闭环**：区分语法、组合逻辑、时序、协议和 testbench 误解，进行可解释修复；
4. **PPA 与可实现性**：生成结果进入 Yosys/OpenROAD，比较面积、频率、功耗代理和约束违例；
5. **数据污染与泛化**：按 IP 家族、设计来源和时间切分，建立不可背题的隐藏集；
6. **低成本本地 Agent**：小模型负责生成，确定性工具负责检查，按失败类型路由，而非无限堆 token；
7. **企业私有 RTL 场景**：检索、权限、审计、可追溯和离线部署。

### 是否建议你现在投入

- **适合投入**：把 RTLCoder 当作低成本 baseline，研究“验证反馈、数据质量、复杂任务、PPA/形式约束”。
- **不适合投入**：重新证明“微调后比未微调模型更会写简单 Verilog”，或只在旧公开题上追一点 pass@k。
- **最建议的切口**：本地 RTLCoder one-shot 对比 MAGE/自研最小 repair-loop，在相同 token 和候选预算下衡量功能成功率，再把通过的 RTL 接入 Yosys/OpenROAD。

## 11. 已知风险

- 合成训练标签存在明显噪声，不能直接当 golden RTL；
- prompt 对结果影响大；
- DeepSeek 版本可能在完成后继续生成，需要可靠截断；
- benchmark 题目公开，存在训练污染风险；
- testbench 也可能有错误，本地半加器实验曾发现验证逻辑误报；
- 4-bit 量化适合推理，不适合直接继续全参数训练；
- 仓库依赖版本较旧，重建训练环境时要单独锁定 CUDA/PyTorch/Transformers。

## 12. 主要资料

### 12.1 代码执行链逐项对照

| 阶段 | 代码位置 | 真实行为 |
|---|---|---|
| 关键词/规格合成 | `data_generation/instruction_gen.py` | 调用 teacher，根据关键词和 prompt 模板生成 instruction，并用 ROUGE-L 去重 |
| SFT 数据读取 | `train/mle.py::SupervisedDataset` | 读取 JSONL 的 `Instruction` 和 `Response[-1]`，只监督 response token |
| 普通 SFT | `train/mle.py` | Hugging Face `Trainer` 全参数训练，DeepSpeed 配置由启动命令提供 |
| 质量候选读取 | `train/mle_scoring.py::ScoreDataset` | 同一 instruction 下展开多份 `Response` 和对应 `Score` |
| 排序损失 | `CompareTrainer.compare_loss()` | 比较模型对候选的长度归一化概率排序与外部分数排序 |
| 梯度拆分 | `train/mle_scoring_grad_split.py` | 候选分组前向，先求 loss 对 candidate score 的梯度，再重算并累加到模型参数 |
| Benchmark 生成 | `benchmark_inference/test_on_verilog-eval.py`、`test_on_rtllm.py` | 批量采样、后处理 DeepSeek/Mistral 输出并落盘 |
| 本地 CPU 复现 | `local_cpu_inference.py` | 加载作者 4-bit GGUF，固定 prompt 生成 half-adder，Icarus 编译/仿真并写 record |

代码中的质量分数样例不是动态调用 Icarus 得到；原论文训练用 Pyverilog syntax checker 给候选评分，功能 testbench 只用于 benchmark。后续若把分数升级为功能或 PPA，必须重建候选数据并重新训练，不能只修改评测脚本。

- 官方仓库：<https://github.com/hkust-zhiyao/RTL-Coder>
- 论文：<https://arxiv.org/abs/2312.08617>
- TCAD 版本：<https://zhiyaoxie.com/files/TCAD25_RTLCoder.pdf>
- 作者模型主页：<https://huggingface.co/ishorn5>
- 本地数据：`dataset/Resyn27k.json`
- 打分数据样例：`train/scoring_data_sample.json`
- 本地推理脚本：`local_cpu_inference.py`
- 本地运行记录：`runs/local_cpu_half_adder/record.json`

---

## P7 关键组件一句话总结

| 组件 | 一句话总结 |
|---|---|
| RTLCoder-v1.1 7B model | 基于 Mistral/DeepSeek-Coder 的 7B 因果语言模型，自回归生成 Verilog token。 |
| Resyn-27k dataset | 从约 350 个硬件关键词出发，用 GPT-3.5 合成的约 27k 条规格—RTL 训练对。 |
| instruction_gen.py | 旧版 OpenAI API 数据生成脚本，用关键词和模板产生新的 instruction-reference 对。 |
| MLE SFT (mle.py) | 普通监督微调，对每条 instruction 的 response token 计算 loss。 |
| quality-scoring trainer | 在多候选展开训练，增加比较损失使模型输出偏向高分 RTL。 |
| gradient-split scoring | 候选分组前向并拆分梯度，降低多候选比较训练显存峰值。 |
| local CPU inference | 加载作者 GGUF 4-bit 权重，在纯 CPU 上完成 RTL 生成、Icarus 编译与仿真验证。 |

---

## 讨论问题

1. 合成训练数据 Resyn-27k 没有独立 testbench，如何设计低成本过滤流程以保证训练标签质量？
2. quality-scoring 训练依赖外部质量分数，若改用功能仿真分数训练，是否会比 Pyverilog-based 分数更稳健？
3. 量化 GGUF 模型已实现本地 CPU 推理，但 4-bit 权重无法继续全参数微调；如何平衡部署便利与研究可扩展性？
