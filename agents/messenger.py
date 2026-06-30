
from workflow.state import AgentState
from llm.llm import get_llm


class MessengerAgent:
    def __init__(self, state: AgentState, llm=None):
        self.state = state
        self.llm = llm or get_llm()

    def generate_response(self) -> AgentState:
        """Generate a response based on the current state."""
        
        if self.state["status"] != "ready_for_response":
            raise ValueError("Cannot generate responses when the state is not ready for response.")

        if self.state["intent"] == "company_risk_analysis":
            self._company_risk_analysis()
        elif self.state["intent"] == "company_overview":
            self._company_overview_analysis()
        elif self.state["intent"] in {"chat", "follow_up"}:
            self.state["answer"] = self.state.get("answer") or ""

        self.state["status"] = "done"
        return self.state
    
    def _company_risk_analysis(self) -> None:
        """Generate company risk analysis response based on the current state."""
        
        report_metrics = self._remove_none_metrics(self.state["company_metrics"])

        prompt = f"""
# Role

You are Aegis, a senior financial analyst writing a concise corporate financial risk assessment.
Assess {self.state['company_names'][0]} ({self.state['tickers'][0]}) using the supplied financial statements and adjusted financial metrics.

# Inputs

Company Data:
{self.state['company_data']}

Adjusted Metrics:
{report_metrics}

Analysis date range:
{self.state['start_date']} to {self.state['end_date']}

# Evidence Rules

Use Adjusted Metrics as the primary evidence for risk conclusions.
Use Company Data only as supporting raw-statement evidence.
Do not invent missing values.
Do not mention unavailable metrics.
Do not use recent news, analyst opinions, management commentary, exact peer benchmarks, or outside company-specific facts.
You may use broad sector context only qualitatively.
Every material conclusion must cite supplied metrics or statement values.

If raw statement values and Adjusted Metrics differ, explain that ratios were calculated from trend-adjusted financial statement measures.
Be careful with negative values: negative net debt usually indicates a net cash position unless the supplied data shows otherwise.

# Required Output Structure

Write the report using exactly these sections:

1. Risk Overview
2. Liquidity Risk
3. Leverage and Solvency Risk
4. Profitability and Cash-Flow Risk
5. Risk Profile
6. Key Findings
7. Notes

# Section Instructions

## 1. Risk Overview
Briefly summarize the company's overall financial risk position.
State the main risk drivers in one short paragraph.
Do not assign the final Low, Moderate, or High classification in this section unless it naturally follows from the evidence.

## 2. Liquidity Risk
Assess short-term financial flexibility.
Use available liquidity metrics such as current ratio, quick ratio, cash ratio, working capital, or working capital to assets.
Explain whether the observed liquidity profile raises, reduces, or does not clearly indicate short-term risk.

## 3. Leverage and Solvency Risk
Assess debt burden and balance-sheet risk.
Use available leverage metrics such as debt to assets, debt to equity, liabilities to assets, equity ratio, net debt to EBITDA, or interest coverage.
Explain whether leverage and coverage point to low, moderate, or elevated solvency pressure.

## 4. Profitability and Cash-Flow Risk
Assess whether profitability and cash generation support financial resilience.
Use available profitability and cash-flow metrics such as margins, ROA, ROE, operating cash-flow margin, free-cash-flow margin, operating cash flow to net income, or free cash flow to debt.
Distinguish accounting profitability from cash-flow quality when possible.

## 5. Risk Profile
Classify the company's financial risk as Low, Moderate, or High.
Write one concise paragraph explaining the overall risk profile.
Combine liquidity, leverage, solvency, profitability, and cash-flow evidence.
If metrics conflict, explain which evidence is more important and why.

## 6. Key Findings
Provide 3 to 5 bullet points.
Each bullet must be grounded in supplied financial metrics or Company Data.
Focus on the most decision-relevant risk findings.
Avoid generic findings.

## 7. Notes
State that Adjusted Metrics are calculated from trend-adjusted financial statement measures.
State that the method is designed to capture recent financial momentum while reducing reporting noise.
State that future financial behavior may differ from historical observations.

# Writing Style

Use markdown headings.
Use a professional financial analyst tone.
Be concise and evidence-driven.
Do not provide investment advice.
Do not make buy, sell, or hold recommendations.
Do not end with a question.
        """

        response = self.llm.invoke(prompt)
        self.state["answer"] = str(response.content)

    def _company_overview_analysis(self) -> None:
        """Generate company overview response based on the current state."""
        
        report_metrics = self._remove_none_metrics(self.state["company_metrics"])

        prompt = f"""
# Role

You are Aegis, a senior financial analyst writing a concise company profile.
Write a professional overview for {self.state['company_names'][0]} ({self.state['tickers'][0]}).

# Inputs

Company Data:
{self.state["company_data"]}

Adjusted Financial Metrics:
{report_metrics}

Reporting date:
{self.state["end_date"]}

# Evidence Rules

Use general model knowledge only to describe the company's business and sector context.
Do not use general model knowledge to infer capital structure, liquidity, profitability, solvency, cash-flow quality, or financial risk.
Use Company Data as the latest raw financial statement snapshot.
Use Adjusted Financial Metrics as the primary source for ratio, margin, and financial-profile observations.
Do not invent financial values.
Do not mention unavailable metrics.
Do not provide investment advice.
Do not make buy, sell, or hold recommendations.
Do not classify the company as low, moderate, or high risk.

# Required Output Structure

Write the overview using exactly these sections:

1. Company Overview
2. Sector Overview
3. Financial Metrics
4. Profile
5. Key Findings
6. Notes

# Section Instructions

## 1. Company Overview
Briefly describe the company's business using general model knowledge.
Focus on what the company does, what it sells or provides, and its main business activities.
Do not infer capital structure, liquidity, profitability, solvency, or financial strength in this section.

Example style:
"Apple is a technology company that designs and sells smartphones, personal computers, wearables, accessories, and related software and services."

## 2. Sector Overview
Describe the main characteristics of the company's sector.
Mention operational caveats generally relevant to companies in that sector, such as capital intensity, margins, cyclicality, working-capital needs, research and development intensity, regulation, competitive pressure, interest-rate sensitivity, or macroeconomic sensitivity.
Keep this qualitative.
Do not cite exact industry averages.
Do not claim company-specific sector strengths unless supported by supplied financial data.

## 3. Financial Metrics
State the relevant findings from Company Data and Adjusted Financial Metrics.
Focus on the most informative observations.
Interpret metrics instead of simply listing them.
Discuss only metrics and statement values that are present.
Useful topics may include scale, liquidity, leverage, solvency, profitability, operating efficiency, cash generation, working capital, and balance-sheet structure.
Tie every financial conclusion to supplied data or metrics.

## 4. Profile
Write one concise paragraph describing the company's overall profile.
Combine the business description, sector context, and observed financial characteristics.
Do not assign a risk rating.

## 5. Key Findings
Provide 3 to 5 bullet points.
Each bullet must be grounded in the business description, sector overview, supplied financial data, or supplied financial metrics.
Avoid generic findings.

## 6. Notes
State that the overview is based on the latest available raw financial statement snapshot, adjusted financial metrics, and general business knowledge.
State that Adjusted Financial Metrics are calculated from trend-adjusted financial statement measures, not adjusted directly after ratio calculation.
State that this adjustment is designed to capture recent financial momentum while reducing reporting noise.
State that future behavior may differ from historical observations.

# Writing Style

Use markdown headings.
Use a professional financial analyst tone.
Be concise.
Avoid excessive formatting.
Avoid conversational phrases.
Do not end with a question.
        """

        response = self.llm.invoke(prompt)
        self.state["answer"] = str(response.content)


    @staticmethod
    def _remove_none_metrics(metrics: dict) -> dict:
        return {
            ticker: {
                name: value
                for name, value in ticker_metrics.items()
                if value is not None
            }
            for ticker, ticker_metrics in metrics.items()
        }
