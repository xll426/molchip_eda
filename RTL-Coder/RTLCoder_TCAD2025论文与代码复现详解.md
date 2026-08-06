# RTLCoder（TCAD 2025）论文、代码与本地复现详解

> 论文：*RTLCoder: Fully Open-Source and Efficient LLM-Assisted RTL Code Generation Technique*  
> 期刊：IEEE TCAD, Vol. 44, No. 4, April 2025  
> 原文：[TCAD2025_RTLCoder.pdf](./TCAD2025_RTLCoder.pdf)  
> 官方仓库：<https://github.com/hkust-zhiyao/RTL-Coder>  
> 对应较短会议版：[RTLCoder_LAD2024论文与代码复现详解.md](./RTLCoder_LAD2024论文与代码复现详解.md)  
> 本地 commit：`b2847073be62d5f1d6d9b17bb247f0cfeb1ce642`；核验日期：2026-08-02。

## 1. 这篇 TCAD 扩展版新增了什么

TCAD 版仍然是“27k 合成 RTL instruction 数据 + 质量感知训练 + 7B 本地模型”，但比 LAD 版更完整地给出：

1. 三阶段数据生成和数据分布分析；
2. 多候选 quality-scoring loss 的公式；
3. gradient splitting 如何把候选训练的激活内存从随 `K` 增长改成分组处理；
4. VerilogEval/RTLLM 更细的 syntax、function、sampling/beam/greedy 实验；
5. 模型量化、部署和通用代码能力影响；
6. 训练标签只用 syntax score 的局限及 functionality checker 展望。

所以两篇不是两个独立模型仓库。代码、数据和权重相同，TCAD 版是应优先引用的方法完整版。

## 2. 完整任务边界

```text
硬件关键词与电路类别
   → teacher 生成自然语言 specification
   → teacher 生成 reference Verilog
   → Resyn-27k
   → Mistral-7B / DeepSeek-Coder-6.7B 普通 SFT
   → 每题再生成 K 个候选
   → Pyverilog syntax checker 给候选质量分
   → MLE + pairwise ranking loss
   → RTLCoder
   → VerilogEval / RTLLM testbench 评测
```

模型只做 spec-to-RTL token generation。编译、功能仿真、综合和 PPA 都在模型外；论文训练时的 scorer 主要是语法检查，不是完整功能 oracle。

## 3. 数据生成：代码如何对应论文

![TCAD 论文 Figure 1：自动数据生成三阶段](./figures/tcad-paper-dataset-flow.png)

### 3.1 Stage 1：domain keywords

论文先准备约 350 个领域关键词，覆盖组合逻辑、时序逻辑、FSM、算术单元、存储和接口等类别。关键词池用于约束 teacher 不只生成同一种简单门电路。

代码 `data_generation/instruction_gen.py`：

- 读取 seed instructions / keyword prompt；
- 通过 `askGPT35()` 请求 teacher；
- `post_process_gpt3_response*()` 解析返回；
- 用 ROUGE-L 和已有 instruction 比较；
- 最大相似度超过 0.7 的候选被过滤。

这只能降低自然语言表面重复，不能证明 RTL 结构、功能或 IP 来源不重复。

### 3.2 Stage 2：instruction generation

teacher 按关键词生成设计规格。好的 instruction 应包含模块行为、输入输出、时序/复位和边界条件；仓库数据并非所有条目都达到这一标准，因此训练前仍需审计。

### 3.3 Stage 3：reference code generation

teacher 为 instruction 生成 Verilog，形成 `Instruction`—`Response`。最终公开 `dataset/Resyn27k.json` 约 27k 行 JSONL。

训练代码 `train/mle.py` 实际读取：

```python
source = Instruction + "\n"
target = Response[-1] + eos_token
```

label 中把 source token 置为 ignore index，只对回答代码计算 cross-entropy。

## 4. 普通 MLE 为什么不够

同一规格可能有多种正确 RTL；teacher reference 也可能不完美。只最大化单份 reference 的概率，会把 reference 当成唯一正确答案，并忽略模型自己产生的其他候选质量。

TCAD 版为每个 instruction 组织：

```text
x_i                       规格
y_i = {y_i,1 ... y_i,K}   reference + 多份模型候选
z_i = {z_i,1 ... z_i,K}   外部 checker 分数
```

模型对候选的长度归一化 log probability 为：

```text
p_i,k = sum_t log P(y_i,k,t | x_i, y_i,k,<t) / |y_i,k|
s_i,k = softmax_k(p_i,k)
```

比较损失要求质量更高的候选具有更大的 `s`：

```text
L_compare = Σ_{z_i,k < z_i,τ} max(s_i,k - s_i,τ + λ, 0)
L_total   = L_MLE + L_compare
```

仓库实现位于 `train/mle_scoring.py::CompareTrainer`：它从 token logits 计算序列分数，形成候选两两差分，并按外部 `Score` 的相对顺序构造 margin loss。

![TCAD 论文 Table III 与 Figure 11：主结果和 MLE/质量感知训练对照](./figures/tcad-paper-main-results.png)

## 5. Gradient Splitting：代码和公式怎样对应

![TCAD 论文 Algorithm 1：多候选训练的 gradient splitting](./figures/tcad-paper-gradient-splitting.png)

如果同一 instruction 有 `K` 个长代码候选，全部同时前向会保存 `K` 份激活。论文把链式法则拆为：

```text
dL/dw = Σ_k (dL/ds_i,k) · (ds_i,k/dw)
```

执行过程：

1. 将 `K` 个候选按 GPU 可承受 batch `J` 分组；
2. 分组前向，收集每个候选序列分数 `s_i,k`，释放大计算图；
3. 在小的 score 向量上计算 `L` 和 `dL/ds_i,k`；
4. 再次逐组前向；
5. 用保存的 `dL/ds_i,k` 对每组做 vector-Jacobian product；
6. 把各组对参数的梯度累加。

代码 `train/mle_scoring_grad_split.py` 的 `CompareTrainer` 分成 `get_sftscore()`、`compare_loss()` 和重算/累计逻辑。它以额外前向计算换激活内存，不减少总 FLOPs，也不会改变 loss 的数学目标。

## 6. 论文主结果

核心数字与 LAD 版一致：

| 模型 | EvalMachine Pass@1 | EvalHuman Pass@1 | RTLLM Function Pass@5 |
|---|---:|---:|---:|
| Mistral-7B base | 36.9% | 4.49% | 20.7% |
| RTLCoder-Mistral-Direct | 58.9% | 34.4% | 41.4% |
| RTLCoder-Mistral | 62.5% | 36.7% | 48.3% |
| DeepSeek-Coder-6.7B base | 54.1% | 30.2% | 34.5% |
| RTLCoder-DeepSeek-Direct | 59.8% | 39.1% | 44.8% |
| RTLCoder-DeepSeek | 61.2% | 41.6% | 48.3% |

论文 VerilogEval 每题 `n=20`，再用无偏 Pass@k 估计；RTLLM v1.1 为 29 个更大设计，分别报告 VCS syntax、Design Compiler synthesizability 和 VCS functionality。不同 checker 的“syntax”口径不能混合。

## 7. 解码消融与局限

![TCAD 论文 Table V / VI：解码方式消融、RTL 训练对通用编程任务的影响](./figures/tcad-paper-ablation.png)

TCAD 版比较 sampling、beam search 和 greedy，说明生成预算和 decoding 会显著改变结果。任何本地复现都必须固定：

- temperature / top-p；
- beams / samples；
- max new tokens；
- 输出截断规则；
- 每题候选数；
- pass@k 的 `n` 与 `k`。

论文也明确承认 syntax checker 不是可靠功能评分。更强 scorer 可用 testbench/formal，但自动生成 assertion/testbench 又会引入错误 oracle。后续研究的关键不是单纯扩大合成数据，而是建立可审计的功能标签。

## 8. 本地 4-bit CPU 复现

本地实际使用作者关联的 `RTLCoder-v1.1-gguf-4bit`：

```bash
conda run -n mage python local_cpu_inference.py \
  --model weights/RTLCoder-v1.1-gguf-4bit/ggml-model-q4_0.gguf \
  --threads 4 --context-length 1024 --batch-size 64
```

结果：

- 纯 CPU，`n_gpu_layers=0`；
- 生成完整 half-adder；
- Icarus 编译通过；
- testbench `PASS 4/4 vectors`；
- 证据：[runs/local_cpu_half_adder/record.json](./runs/local_cpu_half_adder/record.json)。

它证明“4-bit 权重—token generation—RTL 抽取—Icarus”链路可运行，不证明 TCAD 表格的全量 pass@k，也没有复现 full-parameter 多 GPU 训练。

## 9. 复现层级

| 层级 | 当前状态 | 证据/缺口 |
|---|---|---|
| 论文和代码可读 | 已完成 | PDF、仓库、训练脚本均在本地 |
| 量化模型单题推理 | 已完成 | 4/4 testbench record |
| 20–50 题小评测 | 未完成 | 需固定 VerilogEval commit 和模型常驻批量 runner |
| 27k 普通 SFT | 未完成 | 需要多 GPU、锁定旧依赖并审计训练数据 |
| quality-scoring 训练 | 未完成 | 需要候选及 Score 数据、显存和训练日志 |
| gradient-splitting 等价复现 | 未完成 | 需对比 loss/gradient 数值、峰值显存和时间 |
| 论文全量成绩 | 未完成 | 需要相同模型、benchmark、采样和商业 VCS/DC 环境 |

## 10. 代码入口

| 功能 | 文件 |
|---|---|
| 27k 数据 | `dataset/Resyn27k.json` |
| teacher 数据生成 | `data_generation/instruction_gen.py` |
| 普通 SFT | `train/mle.py` |
| quality-scoring | `train/mle_scoring.py` |
| gradient splitting | `train/mle_scoring_grad_split.py` |
| VerilogEval 推理 | `benchmark_inference/test_on_verilog-eval.py` |
| RTLLM 推理 | `benchmark_inference/test_on_rtllm.py` |
| CPU GGUF 单题 | `local_cpu_inference.py` |
| 本地证据 | `runs/local_cpu_half_adder/record.json` |

## 11. 组会结论

RTLCoder 最值得讲的不是“7B 超过 GPT-3.5”，而是三层因果：合成领域数据让 base model 学会 RTL；候选质量排序让训练不再盲信单一 reference；gradient splitting 让多候选 loss 在有限显存上可训练。它也是 OriGen、ChipSeek、MAGE 的重要前置基线：后续工作分别把标签升级为编译修复、EDA/PPA 奖励和推理时工具反馈。
