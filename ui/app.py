"""Streamlit chat interface for the financial-risk copilot."""

import html
import sys
from pathlib import Path

import streamlit as st

sys.path.append(str(Path(__file__).resolve().parents[1]))

from agents.planner import build_state_with_llm


PROJECT_ROOT = Path(__file__).resolve().parents[1]
LOGO_PATH = PROJECT_ROOT / "img" / "logo.png"

CHAT_CSS = """
<style>
.chat-row {
    display: flex;
    width: 100%;
    margin-bottom: 10px;
}
.chat-row.user {
    justify-content: flex-end;
}
.chat-row.assistant {
    justify-content: flex-start;
}
.chat-bubble {
    max-width: 80%;
    border-radius: 20px;
    padding: 16px 20px;
    line-height: 1.6;
    font-size: 0.98rem;
    box-shadow: 0 2px 8px rgba(7, 29, 73, 0.08);
    word-break: break-word;
}
.chat-bubble.user {
    background: #18C6A5;
    color: #071D49;
}
.chat-bubble.assistant {
    background: #071D49;
    color: #FFFFFF;
}
</style>
"""


def default_messages() -> list[dict[str, str]]:
    """Return the initial chat history."""

    return [
        {
            "role": "assistant",
            "content": (
                "Hi — I’m your financial-risk copilot. Ask me about a "
                "company’s liquidity, leverage, profitability, cash-flow "
                "quality, or broader credit risk."
            ),
        }
    ]


def initialize_session_state() -> None:
    """Initialize Streamlit session values used by the chat UI."""

    if "messages" not in st.session_state:
        st.session_state.messages = default_messages()
    if "planner_state" not in st.session_state:
        st.session_state.planner_state = None


def render_sidebar() -> str:
    """Render the left navigation and return the selected page."""

    with st.sidebar:
        if LOGO_PATH.exists():
            st.image(str(LOGO_PATH), use_container_width=True)

        st.title("Financial Risk Copilot")
        page = st.radio(
            "Menu",
            [
                "Chat with AI",
                "Settings",
            ],
            label_visibility="collapsed",
        )

        st.divider()
        st.caption("Local LLM")
        st.code("qwen3:8b", language=None)

        if st.button("Clear chat", use_container_width=True):
            st.session_state.messages = default_messages()
            st.session_state.planner_state = None
            st.rerun()

        with st.expander("Planner debug", expanded=False):
            planner_state = st.session_state.get("planner_state")

            if planner_state is None:
                st.write("Planner state will appear after the first query.")
            else:
                st.json(
                    {
                        "status": planner_state.get("status"),
                        "intent": planner_state.get("intent"),
                        "tickers": planner_state.get("tickers"),
                        "company_names": planner_state.get("company_names"),
                        "start_date": planner_state.get("start_date"),
                        "end_date": planner_state.get("end_date"),
                        "missing_inputs": planner_state.get("missing_inputs"),
                        "follow_up_questions": planner_state.get("follow_up_questions"),
                        "errors": planner_state.get("errors"),
                        "plan": planner_state.get("plan"),
                    }
                )

    return page


def render_chat_history() -> None:
    """Render all chat messages in chronological order."""

    chat_history = st.container(height=620, border=False, autoscroll=True)
    with chat_history:
        st.markdown(CHAT_CSS, unsafe_allow_html=True)

        for message in st.session_state.messages:
            safe_content = html.escape(message["content"]).replace("\n", "<br />")
            bubble_html = (
                f"<div class='chat-row {message['role']}'>"
                f"<div class='chat-bubble {message['role']}'>"
                f"{safe_content}"
                "</div>"
                "</div>"
            )
            st.markdown(bubble_html, unsafe_allow_html=True)


def build_status_response(planner_state: dict[str, object]) -> str:
    """Return the chat response for the current planner state."""

    status = planner_state.get("status")
    follow_up_questions = planner_state.get("follow_up_questions") or []

    if status == "collecting_inputs":
        if follow_up_questions:
            return str(follow_up_questions[0])

        return "I need one more detail before I can start. Which ticker should I use?"

    if status == "ready_for_pipeline":
        return build_ready_response(planner_state)

    if status == "planner_error":
        return (
            "I could not update the planner state from that message. Please rephrase the request "
            "as a company risk analysis, company comparison, or company overview."
        )

    if follow_up_questions:
        return str(follow_up_questions[0])

    return (
        "I can only help with company financial-risk analysis, company comparisons, and company overviews. "
        "Please ask about a specific company's liquidity, leverage, profitability, cash flow, or solvency."
    )


def build_ready_response(planner_state: dict[str, object]) -> str:
    intent = planner_state.get("intent")
    tickers = planner_state.get("tickers") or []
    start_date = planner_state.get("start_date")
    end_date = planner_state.get("end_date")

    if intent == "company_comparison":
        action = "compare"
    elif intent == "company_overview":
        action = "prepare an overview for"
    else:
        action = "analyze risk for"

    ticker_text = ", ".join(str(ticker) for ticker in tickers)

    return (
        f"I have enough information to {action} {ticker_text} "
        f"from {start_date} to {end_date}. The request is ready for the data pipeline."
    )


def render_chat_page() -> None:
    """Render the main chat interface."""

    st.title("Chat with Aegis")
    st.caption(
        "Ask financial-risk questions. The first draft is wired to the local "
        "Ollama model configured in `llm/llm.py`."
    )

    render_chat_history()

    user_prompt = st.chat_input("Ask about a company’s financial risk")
    if not user_prompt:
        return

    history = list(st.session_state.messages)
    st.session_state.messages.append(
        {
            "role": "user",
            "content": user_prompt,
        }
    )

    with st.chat_message("user"):
        st.markdown(user_prompt)

    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            planner_state = build_state_with_llm(
                user_prompt,
                current_state=st.session_state.get("planner_state"),
                history=history,
            )
            st.session_state.planner_state = planner_state
            response = build_status_response(planner_state)

            st.markdown(response)

    st.session_state.messages.append(
        {
            "role": "assistant",
            "content": response,
        }
    )

    st.session_state.planner_state = planner_state


def render_settings_page() -> None:
    """Render a small settings placeholder for future system controls."""

    st.title("Settings")
    st.caption("First draft of the system settings area.")

    st.subheader("Model")
    st.write("Current model source: `llm/llm.py`")
    st.code("qwen3:8b", language=None)

    st.subheader("Future controls")
    st.checkbox("Show retrieval trace", value=True, disabled=True)
    st.checkbox("Show calculated metrics", value=True, disabled=True)
    st.checkbox("Require cited data sources", value=True, disabled=True)


def main() -> None:
    """Run the Streamlit app."""

    st.set_page_config(
        page_title="Financial Risk Copilot",
        page_icon="📊",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    initialize_session_state()
    page = render_sidebar()

    if page == "Settings":
        render_settings_page()
    else:
        render_chat_page()


if __name__ == "__main__":
    main()
