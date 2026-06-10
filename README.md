# Market Surveillance Agent with LangGraph and Strands on AgentCore

This repository contains sample code for building a multi-agent AI system using [LangGraph](https://github.com/langchain-ai/langgraph) for workflow orchestration and [Strands Agents](https://github.com/strands-agents/sdk-python) for agent reasoning, deployed on [Amazon Bedrock AgentCore](https://aws.amazon.com/bedrock/agentcore/).

> **Associated blog post:** [Market Surveillance Agent with LangGraph and Strands on AgentCore](https://aws.amazon.com/blogs/machine-learning/market-surveillance-agent-with-langgraph-and-strands-on-agentcore/) <!-- Update with final URL -->

## Overview

The sample demonstrates a hybrid multi-agent architecture for market surveillance agent. LangGraph handles orchestration (state machines, routing, and checkpoint-based recovery) while Strands powers each specialist agent with tool use, streaming, and model-agnostic reasoning. AgentCore provides the managed runtime infrastructure.

### Architecture

```
┌──────────────────────────────────────────────────────────┐
│              Streamlit UI (app.py)                    │
│          Direct boto3 invocation to AgentCore        │
├──────────────────────────────────────────────────────────┤
│           AWS AgentCore Runtime                       │
│         Container running api.py                     │
├──────────────────────────────────────────────────────────┤
│         LangGraph Workflow (workflow.py)              │
│    StateGraph → Orchestrator → Routing →             │
│    Specialist Agents → Synthesizer                   │
│    Checkpointer: AgentCoreMemorySaver                │
├──────────────────────────────────────────────────────────┤
│          Strands Agents (agents/*.py)                │
│    Security Monitor | Broker Monitor | Risk Monitor  │
│    Intel Analyst | Orchestrator | Synthesizer        │
├──────────────────────────────────────────────────────────┤
│             Tools (tools/*.py)                        │
│    get_report_list | get_report_schema | run_report  │
│    (schema-validated, parameterised SQL; mock data)  │
└──────────────────────────────────────────────────────────┘
```

### Specialist agents

| Agent | Focus | Data sources |
|-------|-------|--------------:|
| Security Monitor | Single-day, single-security analysis | TradeActivity, PriceBars, OrderBook, VolumeProfile |
| Broker Monitor | Multi-day security trends and risk | PriceBars, DailySnapshot, RiskScores |
| Risk Monitor | Single-day broker activity | TradeActivity, BrokerActivity, RiskScores, OrderBook |
| Intel Analyst | External market intelligence via web research | None (uses http_request) |

## Prerequisites

- Python 3.11+
- AWS CLI v2 with configured credentials (`aws sts get-caller-identity` should succeed)
- Amazon Bedrock model access enabled for your chosen model in the target region
- Docker Desktop running (required for ARM64 image build)
- Bash shell

## Deployment

### 1. Clone and install

```bash
git clone https://github.com/aws-samples/sample-market-surveillance-langgraph-strands-agentcore.git
cd sample-market-surveillance-langgraph-strands-agentcore
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

### 2. Configure

```bash
cp .env.example .env
cp config/dynamic-config.yaml.example config/dynamic-config.yaml
```

Edit `.env` with your AWS region. The deployment scripts will auto-populate `config/dynamic-config.yaml`.

### 3. Deploy to AgentCore

```bash
# Full deployment: IAM role, ECR repo, Docker build, AgentCore runtime
make deploy

# First deployment takes ~5 minutes while AgentCore provisions the runtime
```

### 4. Run the Streamlit UI

```bash
make start-client
# Opens at http://localhost:8501
```

### Alternative: Step-by-Step Workshop Notebook

Prefer a guided walkthrough? The [`notebooks/workshop_build_and_deploy.ipynb`](notebooks/workshop_build_and_deploy.ipynb) notebook takes you through building the system from scratch — creating tools, wiring up a Strands agent, adding an orchestrator, connecting everything with a LangGraph state graph, and deploying to AgentCore.

```bash
jupyter notebook notebooks/workshop_build_and_deploy.ipynb
```

## Usage

### Sample queries

```text
# Single-agent (security monitor)
What trades happened on AAPL on March 15, 2024?

# Multi-agent (security + risk)
What was the trading activity for AAPL on March 15, 2024 and which brokers were most active?

# Multi-day (broker monitor)
Analyze MSFT's price movement and broker risk scores between March 10-15, 2024

# External intelligence (intel analyst)
Show me unusual trading patterns for TSLA on March 20, 2024 and check for related market news
```

### Local testing

```bash
# Option A: Streamlit against deployed AgentCore (requires make deploy)
streamlit run app.py

# Option B: Workflow directly (no AgentCore, fast iteration)
python -m src.agents.workflow --chat

# Option C: api.py locally (mimics the AgentCore container)
python api.py
```

## Mock data

This sample uses in-memory mock data for demonstration purposes:

- **Securities:** AAPL, MSFT, TSLA
- **Brokers:** ALPHA_CAPITAL, SUMMIT_TRADING, VERTEX_SECURITIES, PINNACLE_PARTNERS, MERIDIAN_BROKERS, CRESTVIEW_CAPITAL
- **Date range:** March 1–31, 2024
- **Market hours:** Mon–Fri, 09:30–16:00 EST

## Cleanup

```bash
make destroy
```

This removes the AgentCore runtime, ECR repository, and IAM role.

## Makefile reference

| Command | Description |
|---------|-------------|
| `make deploy` | Full deployment (IAM + ECR + Docker build + AgentCore runtime) |
| `make prerequisites` | Set up IAM role and ECR repository only |
| `make destroy` | Delete all AgentCore resources |
| `make start-client` | Start Streamlit UI |
| `make logs` | Tail AgentCore runtime logs from CloudWatch |
| `make status` | Check deployment status and runtime info |
| `make clean` | Clean up temporary files |

## Security

See [CONTRIBUTING](CONTRIBUTING.md#security-issue-notifications) for more information.

## License

This library is licensed under the MIT-0 License. See the [LICENSE](LICENSE) file.
