from config.settings import OLLAMA_CONTEXT_WINDOW_TOKENS
from workflow.state import AgentState


def update_token_usage(state: AgentState, response: object, agent_name: str) -> None:
    """Update cumulative and current-call token usage for an agent."""
    metadata = getattr(response, "response_metadata", {}) or {}

    prompt_tokens = metadata.get("prompt_eval_count", 0)
    output_tokens = metadata.get("eval_count", 0)
    total_tokens = prompt_tokens + output_tokens
    context_window_tokens = state.get("context_window_tokens") or OLLAMA_CONTEXT_WINDOW_TOKENS

    # Update cumulative tokens
    state["prompt_tokens"] = state.get("prompt_tokens", 0) + prompt_tokens
    state["output_tokens"] = state.get("output_tokens", 0) + output_tokens
    state["total_tokens"] = state.get("total_tokens", 0) + total_tokens
    state["context_window_tokens"] = context_window_tokens
    state["context_memory_pct"] = _context_memory_pct(
        state["total_tokens"],
        context_window_tokens,
    )
    
    # Update per-agent cumulative usage (for diagnostics)
    state["llm_usage_by_agent"] = state.get("llm_usage_by_agent", {})
    state["llm_usage_by_agent"][agent_name] = {
        "prompt_tokens": prompt_tokens,
        "output_tokens": output_tokens,
        "total_tokens": total_tokens,
        "total_context_pct": _context_memory_pct(
            total_tokens,
            context_window_tokens,
        ),
    }
    
    # Update current-call tokens for the agent
    _update_agent_current_call_tokens(state, agent_name, prompt_tokens, output_tokens, total_tokens)


def _update_agent_current_call_tokens(
    state: AgentState,
    agent_name: str,
    prompt_tokens: int,
    output_tokens: int,
    total_tokens: int,
) -> None:
    """Track current call tokens separately for each agent."""
    token_limit = state.get("context_window_tokens") or OLLAMA_CONTEXT_WINDOW_TOKENS

    if agent_name == "planner":
        state["planner_prompt_tokens"] = state.get("planner_prompt_tokens", 0) + prompt_tokens
        state["planner_output_tokens"] = state.get("planner_output_tokens", 0) + output_tokens
        state["planner_total_tokens"] = state.get("planner_total_tokens", 0) + total_tokens
        state["planner_token_limit"] = token_limit
    elif agent_name == "messenger":
        state["messenger_prompt_tokens"] = state.get("messenger_prompt_tokens", 0) + prompt_tokens
        state["messenger_output_tokens"] = state.get("messenger_output_tokens", 0) + output_tokens
        state["messenger_total_tokens"] = state.get("messenger_total_tokens", 0) + total_tokens
        state["messenger_token_limit"] = token_limit


def _context_memory_pct(total_tokens: int, context_window_tokens: int) -> float:
    if context_window_tokens <= 0:
        return 0.0

    return round((total_tokens / context_window_tokens) * 100, 2)
