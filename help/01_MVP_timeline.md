## Execution Order

1. Create the GitHub repository
   - Name: `financial-risk-copilot`
   - License: MIT
   - Add README

2. Set up the local environment
   - Create Python virtual environment
   - Install LangGraph, LangChain, Ollama, pandas, requests, SQLAlchemy, etc

3. Run a local LLM
   - Install Ollama
   - Pull a free model, e.g. `llama3.1:8b` or `qwen2.5:7b`

4. Build the data ingestion layer
   - Fetch company data from SEC EDGAR
   - Fetch macro data from FRED
   - Save raw results locally

5. Create the database
   - PostgreSQL
   - Tables for companies, filings, financial facts, macro data, and agent runs

6. Build simple tools
   - `get_company_facts(ticker)`
   - `get_macro_indicators()`
   - `calculate_ratios(company_data)`
   - `summarize_risks(filing_text)`

7. Create the first LangGraph workflow
   - Input node
   - Data retrieval node
   - Analysis node
   - Report generation node

8. Add routing logic
   - If the question asks about macro, call macro tool
   - If it asks about financials, call SEC tool
   - If it asks for full analysis, call both

9. Add memory/logging
   - Store user question
   - Store tools used
   - Store final answer

10. Build a simple interface
   - Start with CLI
   - Later add Streamlit

11. Add evaluation
   - Test with 5 companies
   - Check if answers cite retrieved data
   - Check if reports are consistent

12. Improve the project
   - Add pgvector/RAG over filing text
   - Add risk-factor comparison between filings
   - Add charts
   - Add Docker

### TO DO:

[x] GitHub repository
[x] README
[x] Environment
[x] Ollama

SEC Ingestion
   [x] SEC Client
   [x] Financial Fact Extraction
   [x] Filing Retrieval
   [x] Persistence

FRED ingestion
   [x] FRED Client
   [x] Indicator Retrieval
   [x] Persistence

Financial ratios
   [x] Core ratios
   [ ] Risk score

LangGraph state
   [ ] State definition

Agent nodes
   [ ] Planner
   [ ] Researcher
   [ ] Writer

Graph workflow
   [ ] Graph definition
   [ ] End-to-end execution

Streamlit UI
   [ ] Chat interface