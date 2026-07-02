"""Lightweight Streamlit chat interface for the financial-risk copilot."""

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parents[1]))

import streamlit as st
from config.settings import LLM_MODEL, OLLAMA_CONTEXT_WINDOW_TOKENS
from llm.llm import get_ollama_context_length
from workflow.routes import get_route
from workflow.state import AgentState


PROJECT_ROOT = Path(__file__).resolve().parents[1]
FAVICON_PATH = PROJECT_ROOT / "img" / "favicon.png"
LOGO_PATH = PROJECT_ROOT / "img" / "logo.png"
STYLE_PATH = Path(__file__).resolve().parent / "style.css"
MAX_RENDERED_MESSAGES = 12
LONG_MESSAGE_CHARS = 6000


def build_initial_state(model_context_tokens: int | None = None) -> AgentState:
    token_limit = model_context_tokens or OLLAMA_CONTEXT_WINDOW_TOKENS
    
    return AgentState(
        status="ready_for_response",
        intent="chat",
        tickers=[],
        company_names=[],
        start_date=None,
        end_date=None,
        missing_inputs=[],
        follow_up_questions=[],
        agents_passed=[],
        intents_passed=[],
        llm_usage_by_agent={},
        prompt_tokens=0,
        output_tokens=0,
        total_tokens=0,
        context_window_tokens=token_limit,
        context_memory_pct=0.0,
        planner_prompt_tokens=0,
        planner_output_tokens=0,
        planner_total_tokens=0,
        planner_token_limit=token_limit,
        messenger_prompt_tokens=0,
        messenger_output_tokens=0,
        messenger_total_tokens=0,
        messenger_token_limit=token_limit,
        answer=None,
    )


def default_messages() -> list[dict[str, str]]:
    return [
        {
            "role": "assistant",
            "content": (
                "Hi! I'm Aegis, your financial intelligence copilot."
                "I can analyze company risk, compare companies, provide business overviews, "
                "explain financial metrics and formulas, and answer follow-up questions about "
                "your analyses. I'm also happy to chat and help you understand financial concepts."
            ),
        }
    ]


def load_styles() -> None:
    if STYLE_PATH.exists():
        st.markdown(
            f"<style>{STYLE_PATH.read_text()}</style>",
            unsafe_allow_html=True,
        )


def fetch_model_context_length() -> int:
    """Fetch model context length from Ollama API with fallback."""
    try:
        context_length = get_ollama_context_length(LLM_MODEL)
        if context_length:
            return context_length
    except Exception as e:
        print(f"Warning: Could not fetch Ollama context length: {e}")
    
    # Fallback to environment variable
    return OLLAMA_CONTEXT_WINDOW_TOKENS


def render_sidebar() -> None:
    with st.sidebar:
        if LOGO_PATH.exists():
            st.image(str(LOGO_PATH), width="stretch")

        st.caption("Local LLM")
        st.code(LLM_MODEL, language=None)
        st.caption("Render count")
        if "render_count_container" not in st.session_state:
            st.session_state.render_count_container = st.empty()

        if st.button("Clear chat", use_container_width=True):
            st.session_state.messages = default_messages()
            st.session_state.state = build_initial_state(st.session_state.model_context_tokens)
            st.rerun()
  
        st.caption("Agents passed")
        if "agents_passed_container" not in st.session_state:
            st.session_state.agents_passed_container = st.empty()

        st.caption("Intents passed")
        if "intents_passed_container" not in st.session_state:
            st.session_state.intents_passed_container = st.empty()

        st.caption("Agent token usage")
        if "planner_tokens_container" not in st.session_state:
            st.session_state.planner_tokens_container = st.empty()
        
        if "messenger_tokens_container" not in st.session_state:
            st.session_state.messenger_tokens_container = st.empty()

        if "debug_json_container" not in st.session_state:
            st.session_state.debug_json_container = st.empty()
        st.session_state.show_full_debug_state = st.checkbox(
            "Show full state",
            value=st.session_state.get("show_full_debug_state", False),
        )

        update_sidebar_diagnostics(expanded=False)


def update_sidebar_diagnostics(expanded: bool) -> None:
    agents_passed = st.session_state.state.get("agents_passed") or []
    intents_passed = st.session_state.state.get("intents_passed") or []
    
    planner_prompt_tokens = st.session_state.state.get("planner_prompt_tokens", 0)
    planner_output_tokens = st.session_state.state.get("planner_output_tokens", 0)
    planner_total_tokens = planner_prompt_tokens + planner_output_tokens
    model_token_limit = st.session_state.state.get("context_window_tokens") or OLLAMA_CONTEXT_WINDOW_TOKENS
    planner_usage_pct = (planner_total_tokens / model_token_limit * 100) if model_token_limit > 0 else 0.0
    
    messenger_prompt_tokens = st.session_state.state.get("messenger_prompt_tokens", 0)
    messenger_output_tokens = st.session_state.state.get("messenger_output_tokens", 0)
    messenger_total_tokens = messenger_prompt_tokens + messenger_output_tokens
    messenger_usage_pct = (messenger_total_tokens / model_token_limit * 100) if model_token_limit > 0 else 0.0

    st.session_state.render_count_container.write(st.session_state.render_count)
    st.session_state.agents_passed_container.write(
        " -> ".join(agents_passed) if agents_passed else "None"
    )
    
    st.session_state.intents_passed_container.write(
        " -> ".join(intents_passed) if intents_passed else "None"
    )
    
    # Planner token usage
    st.session_state.planner_tokens_container.progress(
        min(planner_usage_pct / 100, 1.0),
        text=(
            f"Planner: {planner_total_tokens:,} / {model_token_limit:,} "
            f"(P: {planner_prompt_tokens:,} | O: {planner_output_tokens:,})"
        ),
    )
    
    # Messenger token usage
    st.session_state.messenger_tokens_container.progress(
        min(messenger_usage_pct / 100, 1.0),
        text=(
            f"Messenger: {messenger_total_tokens:,} / {model_token_limit:,} "
            f"(P: {messenger_prompt_tokens:,} | O: {messenger_output_tokens:,})"
        ),
    )

    debug_state = st.session_state.state if st.session_state.get("show_full_debug_state") else compact_debug_state()
    st.session_state.debug_json_container.json(
        debug_state,
        expanded=expanded,
    )


def compact_debug_state() -> dict:
    state = st.session_state.state
    model_token_limit = state.get("context_window_tokens") or OLLAMA_CONTEXT_WINDOW_TOKENS

    return {
        "status": state.get("status"),
        "intent": state.get("intent"),
        "agents_passed": state.get("agents_passed", []),
        "intents_passed": state.get("intents_passed", []),
        "planner_tokens": {
            "prompt": state.get("planner_prompt_tokens", 0),
            "output": state.get("planner_output_tokens", 0),
            "total": state.get("planner_total_tokens", 0),
            "limit": model_token_limit,
        },
        "messenger_tokens": {
            "prompt": state.get("messenger_prompt_tokens", 0),
            "output": state.get("messenger_output_tokens", 0),
            "total": state.get("messenger_total_tokens", 0),
            "limit": model_token_limit,
        },
    }

def render_chat_history() -> None:
    messages = st.session_state.messages[-MAX_RENDERED_MESSAGES:]

    if len(st.session_state.messages) > len(messages):
        hidden_count = len(st.session_state.messages) - len(messages)
        st.caption(f"Showing the last {len(messages)} messages. {hidden_count} older messages hidden.")

    newest_visible_index = len(messages) - 1
    for index, message in enumerate(messages):
        with st.chat_message(message["role"]):
            content = message["content"]
            is_older_long_assistant_message = (
                message["role"] == "assistant"
                and index < newest_visible_index
                and len(content) > LONG_MESSAGE_CHARS
            )

            if is_older_long_assistant_message:
                with st.expander("Show earlier long response", expanded=False):
                    st.markdown(content)
            else:
                st.markdown(content)


def build_response_message(state: AgentState) -> str:
    answer = state.get("answer") or ""
    intent = state.get("intent")
    status = state.get("status")

    # If answer already generated by messenger, use it (for follow_up, chat, company analysis)
    if answer:
        return answer
    
    # If no answer, build context-appropriate messages
    if status == "collecting_inputs":
        follow_up_questions = state.get("follow_up_questions") or []
        if len(follow_up_questions) > 0:
            questions_text = "\n".join(f"- {q}" for q in follow_up_questions)
            answer = (
                "I need more information to proceed. Please answer the following questions:\n"
                f"{questions_text}"
            )
        else:
            answer = "I need more information to proceed."
    
    elif status == "ready_for_pipeline":
        answer = "Gathering data for your request..."
    
    elif status == "ready_for_response":
        answer = "The request is ready for analysis, but no report response was generated yet."
    
    elif status == "unsupported":
        answer = (
            "Action not supported. I can help with company financial-risk analysis, company comparisons, "
            "and company overviews."
        )
    
    else:
        answer = "I couldn't generate a response for your request. Please try rephrasing your question."

    state["answer"] = answer
    return answer


def process_user_query(user_query: str) -> None:
    st.session_state.messages.append({"role": "user", "content": user_query})

    with st.chat_message("user"):
        st.markdown(user_query)

    with st.chat_message("assistant"):
        with st.spinner("Working through the request..."):
            new_state = get_route(st.session_state.state, user_query)
            st.session_state.state.update(new_state)
            response = build_response_message(st.session_state.state)

        st.markdown(response)
        update_sidebar_diagnostics(expanded=False)

    st.session_state.messages.append({"role": "assistant", "content": response})

def init_session_state() -> None:
    st.session_state.render_count = st.session_state.get("render_count", 0) + 1

    if "model_context_tokens" not in st.session_state:
        st.session_state.model_context_tokens = fetch_model_context_length()
    
    if "messages" not in st.session_state:
        st.session_state.messages = default_messages()

    if "state" not in st.session_state:
        st.session_state.state = build_initial_state(st.session_state.model_context_tokens)

def main() -> None:
    st.set_page_config(
        page_title="Financial Risk Copilot",
        page_icon=str(FAVICON_PATH),
        layout="wide",
        initial_sidebar_state="expanded",
    )

    init_session_state()

    load_styles()

    st.title("Chat with Aegis")
    render_chat_history()

    render_sidebar()

    user_query = st.chat_input("Ask about a company's financial risk")
    if not user_query:
        return

    process_user_query(user_query)

if __name__ == "__main__":
    main()
