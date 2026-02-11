# DeepMining: Agentic Knowledge Mining Framework

<div align="center">

![License](https://img.shields.io/badge/license-Apache%202.0-blue)
![Python](https://img.shields.io/badge/python-3.10+-orange)
![Framework](https://img.shields.io/badge/Framework-Qwen--Agent-green)

**赋能小模型具备深度研究能力的知识挖掘框架**
*Heavy Mining, Light Inference. From Unstructured Data to Deterministic SOPs.*

[核心理念](#-design-philosophy) • [架构全景](#-architecture) • [快速开始](#-quick-start) • [案例展示](#-case-studies) • [Roadmap](#-roadmap)

</div>

---

## 📖 简介 (Introduction)

**DeepMining** 是一个基于 **Hypothesis-Driven Deep Research（假设驱动深度研究）** 范式的自动化知识挖掘框架。

传统的知识挖掘往往依赖“自底向上”的聚类（Bottom-up Clustering），容易受噪声干扰且难以覆盖长尾场景。DeepMining 引入了类似人类专家的 **Agentic Workflow**，通过 **“Planner（规划）- Researcher（调研）- Analyst（分析）”** 的协作闭环，将海量的非结构化文档（Policy）和对话日志（Logs）转化为 **结构化、可执行的 Mermaid 图谱与原子技能（Atomic Skills）**。

本项目旨在解决智能客服（Customer Service Agent）场景中的核心痛点：
- **幻觉抑制**：通过离线挖掘构建确定性 SOP，而非依赖在线模型的随机生成。
- **长尾覆盖**：利用 MECE 原则主动构建假设树，捕捉稀疏场景下的业务逻辑。
- **降本增效**：将推理算力前置到挖掘阶段（Mining），实现运行时的低延迟与低 Token 消耗。

---

## 🧠 设计哲学 (Design Philosophy)

> **"Heavy Mining, Light Inference"**

DeepMining 的核心思想是将非结构化的文档转化为 **Agent 的操作系统（OS for Agent）**。我们认为，挖掘不仅是提取信息，更是**逻辑重构**。

1.  **Top-Down over Bottom-Up**: 先建立业务假设（Hypothesis Tree），再带着问题去寻找证据，而非在数据海中盲目打捞。
2.  **Graph as The Backbone**: 产出物必须是机器可读的 Mermaid 有向图谱，提供确定性的状态流转。
3.  **Conflict Resolution**: 自动识别“规范文档”与“实际执行”之间的冲突，并内化为技能逻辑。

---

## 🏗️ 架构全景 (Architecture)

DeepMining 的工作流模拟了人类专家进行深度业务调研的过程，分为三个核心阶段：

![Architecture Diagram](assets/deep_mining.png)

### Phase I: Hypothesis Generation (The Planner) 🕵️
* **角色**: 规划师
* **任务**: 基于场景名（如“生鲜坏果退款”），利用大模型的世界知识进行 **MECE 分解**。
* **产出**: **Intent-Hypothesis Tree**（包含潜在的用户意图、约束条件、边缘Case）。
* **核心能力**: 模拟用户画像 (Persona Simulation)、构建调研问题 (RQ Formulation)。

### Phase II: Evidence Acquisition (The Researcher) 🔍
* **角色**: 调研员
* **任务**: 针对 Planner 提出的 RQ，在异构数据源中寻找证据。
* **流程**: Query Translation -> Iterative Retrieval -> Self-Correction。
* **数据源**:
    *   **Normative Docs**: 业务规范、PPT、Wiki（验证“应该是通过什么”）。
    *   **Empirical Logs**: 历史对话日志、API调用记录（验证“实际发生了什么”）。

### Phase III: Knowledge Synthesis (The Analyst) 📊
* **角色**: 分析师
* **任务**: 将碎片化证据拼装成完整的知识库。
* **产出**:
    1.  **Core SOP**: 全局流程骨架（Mermaid Flowchart）。
    2.  **Atomic Skills**: 挂载在节点上的原子能力（Prompt + Knowledge + Tools）。
* **闭环**: 如果发现逻辑断层，自动触发 Feedback Loop 回到 Phase I 补充调研。

---

## ⚡ 快速开始 (Quick Start)

### 环境依赖
```bash
pip install -r requirements.txt
# 推荐使用 python 3.10+
```

### 配置 API
DeepMining 基于 Qwen-Agent 框架构建，支持兼容 OpenAI 格式的模型。
```bash
export DASHSCOPE_API_KEY="sk-..."
```

### 运行挖掘任务
```python
from csc_ai_deep_mining.core import DeepMiner

# 初始化挖掘器
miner = DeepMiner(
    scenario="Fresh Fruit Refund",  # 场景名称
    docs_path="./data/policies",    # 规范文档路径
    logs_path="./data/dialogues"    # 历史日志路径
)

# 1. 生成假设树 (Planner)
hypothesis_tree = miner.generate_hypothesis()

# 2. 执行深度调研 (Researcher)
evidence_bank = miner.research(hypothesis_tree)

# 3. 合成知识图谱 (Analyst)
sop_graph, skills = miner.synthesize(evidence_bank)

# 4. 导出结果
miner.export(format="mermaid", output_dir="./output")
```

---

## 📂 目录结构 (Directory Structure)

```text
deep-mining/
├── assets/               # 静态资源 (图片等)
├── csc_ai_deep_mining/   # 核心源码
│   ├── core/
│   │   ├── planner/      # 假设生成与MECE分解模块
│   │   ├── researcher/   # 检索、工具调用与证据清洗模块
│   │   └── analyst/      # 图谱构建、冲突消解与技能抽象模块
│   ├── llm/              # 大模型服务接口封装
│   ├── prompts/          # 各阶段 Agent 的 System Prompts
│   ├── rag/              # 检索增强生成模块 (RAG)
│   └── schema/           # 数据结构定义 (IntentTree, Evidence, SOP, Skill)
├── docs/                 # 项目文档
├── examples/             # 示例数据与运行脚本
├── grpc_api/             # gRPC 服务接口定义与实现
├── tests/                # 单元测试
└── ...                   # 配置文件 (pyproject.toml, etc.)
```

---

## 📊 效果对比 (Benchmark)

在某电商售后场景（Complex Refund）的实测数据：

| 指标 (Metric) | V1 (Clustering-based) | V2 (DeepMining) | 提升 (Improvement) |
| :--- | :--- | :--- | :--- |
| **知识完备度 (Coverage)** | 65% (遗漏长尾) | **92%** | +41% |
| **逻辑冲突率 (Conflict)** | High | **Low** | 显著降低 |
| **Runtime Token 消耗** | ~4k / turn | **~800 / turn** | **-80%** |
| **人工标注不可用率** | ~15% | **< 1%** | 接近上线标准 |

---

## 🗺️ Roadmap (Q1 规划)

- [x] **V2 核心架构重构**: 完成 Planner/Researcher/Analyst 三阶段跑通。
- [ ] **数据飞轮 (Data Flywheel)**: 实现从 Badcase 到知识库的自动溯源与热更新。
- [ ] **可视化工作台**: 基于 Mermaid 的交互式图谱编辑工具。
- [ ] **增量挖掘**: 支持针对特定分支（Sub-branch）的增量更新，而非全量重跑。

---

## 🤝 贡献 (Contributing)

欢迎提交 PR 或 Issue。我们特别关注以下领域的贡献：
* 更强的 Graph Induction 算法。
* 针对垂直领域（如金融、医疗）的预设假设模板。
* 对接更多向量数据库与检索引擎。

---

## 📄 License

Apache License 2.0