# Financial Risk Copilot

Financial Risk Copilot is a simple agentic AI project built with LangGraph for learning and experimentation.

The agent analyzes public companies using SEC filings and macroeconomic indicators, producing short risk reports with supporting evidence.

## Features

- Agent-based workflow with LangGraph
- SEC filing retrieval
- Financial ratio calculation
- Risk factor summarization
- Macroeconomic context analysis
- Automated risk report generation

## Tech Stack

- Python
- LangGraph
- Ollama
- Llama 3
- PostgreSQL + pgvector

## Data Sources

- SEC EDGAR
- FRED Economic Data

## Example

```text
Input:
"Analyze the financial risk of Apple."

Output:
- Financial health summary
- Key risk factors
- Macroeconomic context
- Overall risk assessment
```

## File System

financial-risk-copilot/
│
├── README.md
├── LICENSE
├── requirements.txt
├── .gitignore
├── help/
│   ├── 01_MVP_timeline.md
│   ├── 02_installing_ollama.md
│   └──
│
├── data/
│   │
│   ├── raw/
│   │   ├── filings/
│   │   └── macro/
│   │
│   └── processed/
│
├── notebooks/
│   ├── 01_sec_exploration.ipynb
│   ├── 02_fred_exploration.ipynb
│   └── 03_agent_testing.ipynb
│
├── src/
│   │
│   ├── main.py
│   ├── llm.py
│   ├── config.py
│   │
│   ├── database/
│   │   ├── connection.py
│   │   ├── models.py
│   │   └── seed.py
│   │
│   ├── tools/
│   │   ├── sec_tool.py
│   │   ├── fred_tool.py
│   │   ├── financial_ratios.py
│   │   └── risk_analysis.py
│   │
│   ├── agents/
│   │   ├── planner.py
│   │   ├── researcher.py
│   │   └── writer.py
│   │
│   ├── graphs/
│   │   ├── state.py
│   │   └── financial_risk_graph.py
│   │
│   └── prompts/
│       ├── planner_prompt.py
│       ├── researcher_prompt.py
│       └── writer_prompt.py
│
├── tests/
│   ├── test_sec_tool.py
│   ├── test_fred_tool.py
│   ├── test_ratios.py
│   └── test_graph.py
│
└── docs/
    ├── architecture.md
    ├── ollama_setup.md
    ├── langgraph_workflow.md
    └── future_improvements.md

## Project Goal

This project is not intended to provide investment advice. Its purpose is to explore agentic AI patterns, tool orchestration, retrieval workflows, and financial data analysis using LangGraph.

## License

MIT