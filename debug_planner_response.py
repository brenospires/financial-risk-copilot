"""
Temporary debug script to capture exact planner prompts and responses
"""
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parents[0]))

from agents.planner import PlannerAgent
from workflow.state import AgentState

def test_followup_classification():
    """Test how planner classifies follow-up questions"""
    
    # Simulate a state after company analysis
    state_after_analysis = AgentState(
        status="done",
        intent="company_overview",
        tickers=["AMZN"],
        company_names=["Amazon"],
        last_report="Amazon is a strong company with...",
        last_metrics={"Amazon": {"metric1": 0.5}},
    )
    
    # Now test a follow-up question
    followup_query = "what metrics were used for profile classification?"
    
    print("\n" + "="*80)
    print("DEBUG: Testing Planner with Follow-Up")
    print("="*80)
    print(f"\nQuery: {followup_query}")
    print(f"\nState before planner:")
    print(f"  - status: {state_after_analysis['status']}")
    print(f"  - intent: {state_after_analysis['intent']}")
    print(f"  - has last_report: {bool(state_after_analysis.get('last_report'))}")
    
    # Build state_context like routes.py does
    state_context = {
        "user_query": followup_query,
        "tickers": state_after_analysis.get("tickers", []),
        "company_names": state_after_analysis.get("company_names", []),
        "start_date": state_after_analysis.get("start_date"),
        "end_date": state_after_analysis.get("end_date"),
        "last_report": state_after_analysis.get("last_report"),
        "last_metrics": state_after_analysis.get("last_metrics"),
    }
    
    print(f"\nState context passed to planner: {str(state_context)[:200]}...")
    
    try:
        planner = PlannerAgent()
        result = planner.get_status(followup_query, current_state=state_context)
        
        print(f"\n✅ Planner succeeded!")
        print(f"  - intent: {result.get('intent')}")
        print(f"  - status: {result.get('status')}")
        print(f"  - answer: {result.get('answer', '')[:100]}...")
        
    except ValueError as e:
        print(f"\n❌ Planner failed with error:")
        print(f"  {str(e)[:200]}")

if __name__ == "__main__":
    test_followup_classification()
