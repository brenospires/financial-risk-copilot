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
├── .env.example
├── .gitignore
├── help/
│   ├── 01_MVP_timeline.md
│   ├── 02_installing_ollama.md
│   └── 03_FRED_API.md
│
├── data/
│
├── agents/
│   ├── nodes_helper.py
│   ├── planner_node.py
│   ├── researcher_node.py
│   └── writer_node.py
│
├── config/
│   └── settings.py
│
├── docs/
│   └── supported_actions.md
│
├── graph/
│   ├── nodes.py
│   └── state.py
│
└── src/
    ├── llm.py
    ├── database/
    │   ├── fred_repository.py
    │   └── sec_repository.py
    ├── tests/
    │   ├── test_financial_statement_metrics.py
    │   ├── test_fred_pipeline.py
    │   └── test_sec_pipeline.py
    └── tools/
        ├── financial_analysis.py
        ├── financial_statement_metrics.py
        ├── fred_tool.py
        ├── macro_risk_score.py
        ├── metrics_utils.py
        ├── risk_score.py
        └── sec_tool.py

## Project Goal

This project is not intended to provide investment advice. Its purpose is to explore agentic AI patterns, tool orchestration, retrieval workflows, and financial data analysis using LangGraph.

## License

MIT
