# OriGen 论文、代码与本地复现详解

> 论文：*OriGen: Enhancing RTL Code Generation with Code-to-Code Augmentation and Self-Reflection*  
> 原文：[2407.16237_OriGen.pdf](./2407.16237_OriGen.pdf)  
> 上游：<https://github.com/pku-liang/OriGen>；本地 commit `bba405fe54f2`。  
> 模型卡声明 GPL-3.0，GitHub 根目录未见标准 LICENSE，使用前需分别核对代码与权重授权。  
> 论文、代码与本地运行核验：2026-08-02。

```text
┌──────────────────────────────────────────────────────────────┐
│ P1 任务定义                                                   │
├──────────────────────────────────────────────────────────────┤
│ Input：自然语言模块规格（生成任务），或原始错误 RTL + 编译器   │
│ 错误信息（修复任务），可选已知模块头。                        │
├──────────────────────────────────────────────────────────────┤
│ Output：自回归生成的 Verilog RTL（生成任务），或修复后的      │
│ Verilog RTL（修复任务）。                                     │
├──────────────────────────────────────────────────────────────┤
│ Supervision：code-to-code 增强得到的 (description, RTL) 对，   │
│ 以及 (错误 RTL, 编译反馈, 修复 RTL) 监督对。                │
├──────────────────────────────────────────────────────────────┤
│ Why-hard：Verilog 语法/语义严格；描述到实现映射歧义大；功能   │
│ 正确需通过 testbench/formal；code-to-code 数据增强需防止   │
│ 训练/测试污染；修复任务中“编译通过”远不等于“功能正确”。     │
└──────────────────────────────────────────────────────────────┘
```

## 1. 它解决芯片流程的哪一步

OriGen 位于**数字前端 RTL 编写与修复**，不是端到端芯片设计系统。

```text
微架构/模块规格
   ↓
[OriGen：自然语言 → Verilog RTL]
   ↓
编译/仿真发现语法错误
   ↓
[OriGen_Fix：规格 + 错误 RTL + 编译器错误 → 修复 RTL]
   ↓
DV/testbench/formal → 综合 → 门级网表 → 布局布线 → GDS
```

- 它能生成或改写 `.v/.sv` 文本。
- 它不直接生成 UVM 验证环境、门级网表、DEF/GDS，也不做 STA/DRC/LVS。
- OriGen_Fix 使用编译反馈，但“修到能编译”仍不等于功能正确，必须继续跑 testbench/formal。

## 2. 输入和输出到底是什么

### 2.1 OriGen 生成模型

输入是一段带 `### Instruction` / `### Response` 模板的文本，最好包含模块名、端口、位宽、时钟/复位、组合或时序语义及边界条件。输出是自回归生成的 Verilog 文本。

本地实测输入要求 1-bit half adder，输出完整 `half_adder`，随后由 Icarus 独立编译和仿真。

### 2.2 OriGen_Fix 修复模型

输入由四部分组成：

1. 目标任务描述；
2. 原始错误 RTL；
3. Icarus/其他编译器错误；
4. 已知模块头（可选）。

输出是修复后的 RTL。真实 Agent 流应先执行编译器产生错误，再把错误送给模型，而不是人工编一个与代码无关的错误文本。

## 3. 模型结构：基础模型 + LoRA，不是两个完整 7B

两个作者权重都是 LoRA adapter，必须挂在同一个 `deepseek-ai/deepseek-coder-7b-instruct-v1.5` 基础模型上：

```text
token → 7B DeepSeek-Coder 主干（冻结）
      ↘ 每层 q/k/v/o、gate/up/down 的 LoRA 低秩增量
        → 下一 token 概率 → Verilog
```

本地量化基础模型元数据：

| 项 | 值 | 通俗解释 |
|---|---:|---|
| Transformer block | 30 | 规格与已生成代码连续处理 30 次 |
| hidden size | 4096 | 每个 token 在层内用 4096 维状态表示 |
| attention heads | 32 | 从接口、信号依赖、语法等不同角度关注上下文 |
| KV heads | 32 | 这里是标准多头注意力，不做 GQA 共享 |
| FFN size | 11008 | 每层的非线性特征扩展宽度 |
| vocabulary | 102400 | 最终预测的 token 词表规模 |
| context | 4096 | 训练配置的上下文上限 |

### 3.1 LoRA 在一层里做了什么

原线性层是 `y = Wx`。LoRA 冻结大矩阵 `W`，只训练两个小矩阵 `A` 和 `B`：

```text
y = Wx + (alpha / r) · B(Ax)
```

作者配置 `r=32`、`alpha=32`，所以缩放系数为 1。每个 adapter 有 420 个张量、74,956,800 个 LoRA 参数，覆盖 30 层的：

- attention：`q_proj/k_proj/v_proj/o_proj`；
- MLP：`gate_proj/up_proj/down_proj`。

420 的来源是 `30 层 × 7 个目标线性层 × (A,B 两个矩阵)`。这解释了为什么 adapter safetensors 约 300 MB，而完整 7B FP16 模型要十几 GB。

OriGen 和 OriGen_Fix 结构相同、数值不同：前者学规格→RTL，后者在生成 adapter 基础上继续学习错误→修复。

## 4. 数据从哪里来、怎样训练

![论文 Figure 1 / 2：code-to-code 数据增强，以及生成—编译—自反思修复](./figures/paper-fig1-fig2-augmentation-reflection.png)

公开数据入口：

- `origen_dataset_description`：RTL 与多层次描述；
- `origen_dataset_instruction`：把描述转换成生成指令；
- `origen_dataset_debug`：错误代码、编译反馈和修复代码。

论文的核心是 code-to-code augmentation：从已有 RTL 出发生成不同抽象层次描述，再把描述转成 instruction；修复阶段则制造/收集错误，调用编译器得到反馈，并构成监督对。

概念格式如下，实际训练必须以 Hugging Face revision 的真实列名为准：

```json
{"instruction":"Create an 8-bit full adder...","output":"module ... endmodule"}
{"description":"Implement an AND gate","original_code":"module ...","error":"syntax error...","fixed_code":"module ... endmodule"}
```

训练步骤：

1. 固定 DeepSeek-Coder 7B v1.5 与 tokenizer revision；
2. 按官方 prompt 模板拼 instruction/response；
3. 只对 response token 计算 causal-LM cross-entropy；
4. 冻结基础模型，只更新 rank-32 LoRA；
5. 第一阶段训练 OriGen；第二阶段从它继续训练 OriGen_Fix；
6. validation 监控 loss，但最终必须在未泄漏的 testbench/formal 集上判断功能正确率。

训练数据必须先做许可证追踪、按仓库/IP 家族去重、编译与 testbench 过滤。公开 VerilogEval 题不能同时进入训练和测试。

### 4.1 论文结果与消融

![论文 Table 1：OriGen 在 VerilogEval 与 RTLLM 上的主结果](./figures/paper-table1-main-results.png)

论文在不启用 self-reflection、保持单次生成的对比中报告：

| Benchmark | 指标 | OriGen | 论文中的关键对照 |
|---|---|---:|---:|
| VerilogEval-Human | Pass@1 | 54.4% | RTLCoder-DeepSeek 41.6% |
| VerilogEval-Machine | Pass@1 | 74.1% | RTLCoder-DeepSeek 61.2% |
| RTLLM | Pass@5 | 65.5% | RTLCoder-DeepSeek 48.3% |

论文的数据量曲线从 base model 的 31.7% 开始：10k 数据达到 43.2%，完整约 180k 数据达到 54.4%，说明早期数据增量收益最大，随后出现边际递减。

![论文 Table 2–4：VerilogFixEval、自反思和两类训练消融](./figures/paper-table2-fix-results.png)

VerilogFixEval 上 OriGen_Fix 的语法正确率为 89.1%、功能正确率为 33.5%。这两个指标必须分开：编译修复显著强于功能修复。消融还显示：

- code-to-code augmentation 把 Human Pass@1 从 41.6% 提高到 54.4%；
- Machine Pass@1 从 62.5% 提高到 74.1%；
- RTLLM Pass@5 从 41.4% 提高到 65.5%；
- error-correction finetune + compiler error message 达到 89.1% syntax / 33.5% function。

这些是论文模型与论文评测设置的结果；下面本地两个 4-vector 例子只是链路复现。

## 5. 本机权重与实测

### 5.1 已下载资产

| 资产 | 大小/参数 | SHA-256 |
|---|---:|---|
| DeepSeek-Coder 7B v1.5 Q3_K_M GGUF | 3,461,192,128 B | `304ada716aa9b8872530e97553d70caf5873dc48a79f74e7a0e03ba2a020feb4` |
| OriGen adapter safetensors | 74,956,800 参数 | `5927edd800b10e85f0a5d610b2b7cdfb9674c368878c6efa5dad0420c59cc61b` |
| OriGen F16 LoRA GGUF | 149,942,848 B | `d1a83fc980a436c488ac7e5f42c60bc922694687ee6134aad5a3552f5af62cab` |
| OriGen_Fix adapter safetensors | 74,956,800 参数 | `cdffeaa4d10dcb211d4f83e1288091a14874dd066b63faec8572c15c2b854b4a` |
| OriGen_Fix F16 LoRA GGUF | 149,942,848 B | `5d3630531137945696760a9e99b764ec0b6d947bb3146e71558ab8eaf8a911ac` |

基础 GGUF 来自标明对应官方 base model 的 community quantization；LoRA 是作者权重转换，不能把社区量化本身写成作者发布物。

### 5.2 生成实测：成功

```bash
/home/xlx/miniconda3/envs/mage/bin/python local_cpu_inference.py \
  --base-model weights/base/deepseek-coder-7b-instruct-v1.5-Q3_K_M.gguf \
  --lora weights/OriGen/OriGen-LoRA-f16.gguf \
  --mode generation --output-dir runs/origen_generation_half_adder
```

- GPU offload：0；CPU 4 threads；greedy；seed 7。
- 模型加载约 11.60 s；生成 66 tokens 约 14.26 s。
- Icarus 编译成功；testbench：`PASS 4/4 vectors`。
- 证据：`runs/origen_generation_half_adder/record.json`。

### 5.3 修复实测：成功

输入是缺少两个分号的 `and2` 及对应语法错误。OriGen_Fix 生成可编译模块：

- 模型加载约 12.39 s；生成 12 tokens 约 10.88 s；
- Icarus 编译成功；testbench：`PASS 4/4 vectors`；
- 证据：`runs/origen_fix_and2/record.json`。

llama.cpp 输出的 `CPU_REPACK fallback to CPU` 是部分 LoRA 张量退回普通 CPU buffer 的性能提示，不是权重缺失；两次结果均通过后续独立仿真。

## 6. 这不是端到端，也不是完整 DV

当前闭环只证明两个小例：文本→RTL，以及错误文本→修复 RTL。它没有证明：

- 多周期协议、复位、CDC 或 X 传播正确；
- testbench 覆盖了所有规格；
- RTL 可综合、时序/PPA 良好；
- 复杂多模块系统可工作。

实际工程下一步应接 lint、隐藏 testbench、SVA/formal、Yosys 综合；只有进入 ORFS/OpenROAD 后，才开始回答门级网表和物理实现问题。

## 7. 关键文件

### 7.1 代码执行链逐项对照

| 阶段 | 代码/资产 | 实际作用 |
|---|---|---|
| 论文全精度推理 | `evaluation/generate_lora.py` | `AutoModelForCausalLM` 加载 base，`PeftModel.from_pretrained()` 挂 LoRA，批量生成 JSONL |
| prompt | `evaluation/generate_lora.py` 与模型卡 | 将 `Instruction` 包装为 `### Instruction/### Response` 模板 |
| 生成后处理 | `post_process_generated_code()` | 去掉 Markdown fence 等外层文本；不负责功能验证 |
| 官方评测输入 | `results/reference_verilogeval.jsonl` | VerilogEval prompt/reference 组织形式 |
| 本地量化推理 | `local_cpu_inference.py` | llama.cpp 加载 Q3 base + F16 LoRA，支持 generation/fix 两种 prompt |
| RTL 抽取 | `local_cpu_inference.py` | 从模型输出截取 `module ... endmodule`，保存原始输出和提取代码 |
| 确定性验收 | `local_cpu_inference.py` | 调用 Icarus 编译、`vvp` 运行 4-vector testbench，并生成 `record.json` |

本地脚本不是上游原始训练实现，而是为了在 CPU/低内存环境验证作者 adapter 的新增复现入口；它保留 base/LoRA SHA、prompt、raw output、RTL、编译和仿真证据，因此比只展示生成文本更可审计。

- `local_cpu_inference.py`：本地 GGUF + LoRA 推理、抽取、Icarus 验证；
- `weights/`：基础量化权重、作者 adapters 与转换后 LoRA；
- `runs/origen_generation_half_adder/`：生成实测完整输入输出；
- `runs/origen_fix_and2/`：修复实测完整输入输出；
- `evaluation/`：官方 VerilogEval 生成/评测入口；
- 官方模型：<https://huggingface.co/henryen/OriGen>、<https://huggingface.co/henryen/OriGen_Fix>。

## P7 组件一句话总结

| 组件 | 一句话角色 |
|---|---|
| DeepSeek-Coder 7B v1.5 | 冻结的 7B 代码 LLM 主干，提供 Verilog 生成先验。 |
| OriGen / OriGen_Fix LoRA adapter | 在 base 上低秩微调的两组参数，分别负责规格→RTL 和 错误→修复。 |
| evaluation/generate_lora.py | 官方全精度 batch 生成入口，使用 PEFT 加载 base+LoRA。 |
| post_process_generated_code() | 去掉 Markdown fence 等外层噪声，提取 Verilog 代码块。 |
| local_cpu_inference.py | 本地 llama.cpp 量化推理 + Icarus 编译 + 4-vector testbench 验收入口。 |
| evaluation/reference_verilogeval.jsonl | VerilogEval 评测 prompt/reference 组织。 |
| origen_dataset_description / instruction / debug | Hugging Face 上的训练数据描述、生成指令和修复监督对。 |

## 讨论问题

1. OriGen 使用 code-to-code augmentation 生成多层次描述再转 instruction，这种做法在防止训练/测试污染和保持描述多样性之间如何权衡？
2. OriGen_Fix 在 VerilogFixEval 上语法正确率 89.1% 但功能正确率仅 33.5%，说明“修到能编译”远不等于“修对功能”；应如何设计更难的功能级修复 benchmark？
3. OriGen 基于 DeepSeek-Coder 7B + LoRA，如果要在更大 base model 或更先进代码模型上复现，哪些因素（tokenizer、prompt 模板、Verilog 风格）最可能导致性能漂移？
