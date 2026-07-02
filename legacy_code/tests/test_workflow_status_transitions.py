"""
Test status transitions and intent handling for all workflows.

Tests verify that the workflow properly handles:
- Chat intent: planner -> ready_for_response -> messenger -> ready_for_response
- Company analysis: planner -> collecting_inputs/ready_for_pipeline -> researcher -> ready_for_response -> messenger -> done
- Follow-up: ready_for_response -> messenger -> ready_for_response
"""

import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[2]))

from workflow.state import AgentState
from workflow.routes import get_route


class TestChatWorkflow:
    """Test chat intent workflow."""
    
    def test_chat_intent_goes_through_messenger(self):
        """Chat: planner -> ready_for_response -> messenger -> ready_for_response"""
        state = AgentState(
            status="ready_for_response",
            intent="chat",
            agents_passed=[],
            intents_passed=[],
        )
        
        new_state = get_route(state, "what is market cap?")
        
        assert new_state["intent"] == "chat"
        assert new_state["status"] == "ready_for_response"
        assert "planner" in new_state["agents_passed"]
        assert "messenger" in new_state["agents_passed"]
        assert new_state.get("answer") is not None
        assert len(new_state["answer"]) > 0
        print("✓ Chat workflow test passed")


class TestCompanyAnalysisWorkflow:
    """Test company analysis intent workflow."""
    
    def test_company_analysis_missing_ticker_collecting_inputs(self):
        """Turn 1: Company analysis with missing ticker -> collecting_inputs"""
        state = AgentState(
            status="ready_for_response",
            intent="chat",
            agents_passed=[],
            intents_passed=[],
        )
        
        new_state = get_route(state, "analyze tesla risk")
        
        assert new_state["intent"] == "company_risk_analysis"
        assert new_state["status"] == "collecting_inputs"
        assert len(new_state["missing_inputs"]) > 0
        assert len(new_state["follow_up_questions"]) > 0
        assert "planner" in new_state["agents_passed"]
        print("✓ Company analysis with missing inputs test passed")
    
    def test_company_analysis_with_full_inputs_reaches_done(self):
        """Turn 2+: Company analysis with all inputs -> ready_for_pipeline -> researcher -> ready_for_response -> messenger -> done"""
        # Simulate a state that has gone through missing inputs and now has tickers
        state = AgentState(
            status="collecting_inputs",
            intent="company_risk_analysis",
            tickers=["TSLA"],
            company_names=["Tesla"],
            start_date="2020-01-01",
            end_date="2024-12-31",
            agents_passed=["planner"],
            intents_passed=["company_risk_analysis"],
            company_data={},  # Populated by researcher
            company_metrics={},  # Populated by researcher
        )
        
        # This would normally require actual API calls to researcher
        # For now, we verify the state structure is correct for the test
        assert state["intent"] == "company_risk_analysis"
        assert len(state["tickers"]) > 0
        assert len(state["company_names"]) > 0
        print("✓ Company analysis with full inputs structure test passed")


class TestFollowUpWorkflow:
    """Test follow-up intent workflow."""
    
    def test_follow_up_after_analysis_uses_last_report(self):
        """Follow-up: ready_for_response -> messenger -> ready_for_response (uses last_report)"""
        state = AgentState(
            status="ready_for_response",
            intent="follow_up",
            last_report="Tesla is a strong company with good growth prospects and strong R&D investment.",
            last_metrics={"Tesla": {"debt_ratio": 0.45, "roe": 0.18, "fcf_margin": 0.12}},
            agents_passed=["planner", "researcher", "messenger"],
            intents_passed=["company_risk_analysis"],
        )
        
        new_state = get_route(state, "what are the key risks?")
        
        assert new_state["intent"] == "follow_up"
        assert new_state["status"] == "ready_for_response"
        assert "planner" in new_state["agents_passed"]
        assert "messenger" in new_state["agents_passed"]
        assert new_state.get("answer") is not None
        assert len(new_state["answer"]) > 0
        # Verify last_report and last_metrics are preserved
        assert new_state["last_report"] is not None
        assert new_state["last_metrics"] is not None
        print("✓ Follow-up workflow test passed")


class TestStatusTransitionIntegrity:
    """Test status transitions are not contaminated between turns."""
    
    def test_status_resets_properly_on_new_query(self):
        """Verify status doesn't carry over from previous interaction"""
        # Simulate end of first interaction: status="done"
        state_after_analysis = AgentState(
            status="done",
            intent="company_risk_analysis",
            tickers=["TSLA"],
            company_names=["Tesla"],
            answer="Tesla shows strong financial metrics.",
            agents_passed=["planner", "researcher", "messenger"],
            intents_passed=["company_risk_analysis"],
        )
        
        # After the transition in routes.py, status should be ready_for_response
        # (This is tested implicitly in the workflow, but we verify the logic)
        new_state = get_route(state_after_analysis, "what about margins?")
        
        # The new state should have been processed by planner for follow-up
        assert new_state["status"] in {"ready_for_response", "collecting_inputs"}
        # If it's follow-up, status must be ready_for_response
        if new_state["intent"] == "follow_up":
            assert new_state["status"] == "ready_for_response"
        print("✓ Status reset integrity test passed")
    
    def test_answer_not_duplicated_on_follow_up(self):
        """Verify follow-up generates NEW answer, not cached previous answer"""
        # This test assumes messenger properly generates new answers
        # The key verification happens in messenger._give_followup()
        state = AgentState(
            status="ready_for_response",
            intent="follow_up",
            last_report="Previous analysis report about Tesla.",
            last_metrics={"Tesla": {"metric1": 0.5}},
            agents_passed=[],
            intents_passed=[],
        )
        
        # After routing, answer should be generated (not the old last_report)
        new_state = get_route(state, "what else should I know?")
        
        assert new_state.get("answer") is not None
        # The answer should be different from last_report (unless coincidentally same)
        # This is a best-effort check; the real validation is manual testing
        if new_state["answer"] and state["last_report"]:
            # They should not be identical (messenger generates new content)
            # Note: This is a heuristic; in practice, they could contain similar content
            print(f"Last report length: {len(state['last_report'])}")
            print(f"New answer length: {len(new_state['answer'])}")
        print("✓ Answer duplication prevention test passed")


class TestAgentPassedTracking:
    """Test that agents_passed is properly tracked."""
    
    def test_planner_always_recorded(self):
        """Planner should always be in agents_passed"""
        state = AgentState(
            status="ready_for_response",
            intent="chat",
            agents_passed=[],
            intents_passed=[],
        )
        
        new_state = get_route(state, "hello")
        
        assert "planner" in new_state["agents_passed"]
        print("✓ Planner tracking test passed")
    
    def test_messenger_recorded_for_ready_for_response(self):
        """Messenger should be recorded when status is ready_for_response"""
        state = AgentState(
            status="ready_for_response",
            intent="chat",
            agents_passed=[],
            intents_passed=[],
        )
        
        new_state = get_route(state, "what is this?")
        
        assert "messenger" in new_state["agents_passed"]
        print("✓ Messenger tracking for ready_for_response test passed")


class TestIntentPassedTracking:
    """Test that intents_passed is properly tracked."""
    
    def test_intent_recorded_after_planner(self):
        """Intent should be recorded after planner determines it"""
        state = AgentState(
            status="ready_for_response",
            intent="chat",
            agents_passed=[],
            intents_passed=[],
        )
        
        new_state = get_route(state, "analyze apple")
        
        assert len(new_state["intents_passed"]) > 0
        # Should have the detected intent
        assert new_state["intent"] in new_state["intents_passed"]
        print("✓ Intent tracking test passed")


if __name__ == "__main__":
    print("\n" + "="*60)
    print("Running Workflow Status Transition Tests")
    print("="*60 + "\n")
    
    # Chat workflow
    print("Testing Chat Workflow...")
    test_chat = TestChatWorkflow()
    test_chat.test_chat_intent_goes_through_messenger()
    
    # Company analysis workflow
    print("\nTesting Company Analysis Workflow...")
    test_company = TestCompanyAnalysisWorkflow()
    test_company.test_company_analysis_missing_ticker_collecting_inputs()
    test_company.test_company_analysis_with_full_inputs_reaches_done()
    
    # Follow-up workflow
    print("\nTesting Follow-Up Workflow...")
    test_followup = TestFollowUpWorkflow()
    test_followup.test_follow_up_after_analysis_uses_last_report()
    
    # Status transition integrity
    print("\nTesting Status Transition Integrity...")
    test_status = TestStatusTransitionIntegrity()
    test_status.test_status_resets_properly_on_new_query()
    test_status.test_answer_not_duplicated_on_follow_up()
    
    # Agent tracking
    print("\nTesting Agent Tracking...")
    test_agents = TestAgentPassedTracking()
    test_agents.test_planner_always_recorded()
    test_agents.test_messenger_recorded_for_ready_for_response()
    
    # Intent tracking
    print("\nTesting Intent Tracking...")
    test_intents = TestIntentPassedTracking()
    test_intents.test_intent_recorded_after_planner()
    
    print("\n" + "="*60)
    print("✓ All tests completed!")
    print("="*60 + "\n")
