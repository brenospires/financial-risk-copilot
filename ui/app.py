"""Lightweight Streamlit chat interface for the financial-risk copilot."""

import sys
from pathlib import Path

import streamlit as st

sys.path.append(str(Path(__file__).resolve().parents[1]))

from config.settings import LLM_MODEL
from workflow.routes import get_route
from workflow.state import AgentState


PROJECT_ROOT = Path(__file__).resolve().parents[1]
LOGO_PATH = PROJECT_ROOT / "img" / "logo.png"
STYLE_PATH = Path(__file__).resolve().parent / "style.css"


def build_initial_state() -> AgentState:
    return AgentState(
        status="collecting_inputs",
        intent="chat",
        tickers=[],
        company_names=[],
        start_date=None,
        end_date=None,
        missing_inputs=[],
        follow_up_questions=[],
        answer=None,
    )


def default_messages() -> list[dict[str, str]]:
    return [
        {
            "role": "assistant",
            "content": (
                "Hi! I'm Aegis, your financial-risk copilot. Ask me to analyze "
                "company risk, compare two companies, or provide a company overview."
            ),
        }
    ]


def load_styles() -> None:
    if STYLE_PATH.exists():
        st.markdown(
            f"<style>{STYLE_PATH.read_text()}</style>",
            unsafe_allow_html=True,
        )


def render_sidebar() -> None:
    with st.sidebar:
        if LOGO_PATH.exists():
            st.image(str(LOGO_PATH), use_container_width=True)

        st.title("Financial Risk Copilot")
        st.caption("Local LLM")
        st.code(LLM_MODEL, language=None)

        if st.button("Clear chat", use_container_width=True):
            st.session_state.messages = default_messages()
            st.session_state.state = build_initial_state()
            st.rerun()


def render_chat_history() -> None:
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])


def build_response_message(state: AgentState) -> str:
    answer = state.get("answer")
    if answer:
        return answer

    follow_up_questions = state.get("follow_up_questions") or []
    if state.get("status") == "collecting_inputs" and follow_up_questions:
        return str(follow_up_questions[0])

    if state.get("status") == "collecting_inputs":
        return "I need one more detail before I can start."

    if state.get("status") == "unsupported":
        return (
            "I can help with company financial-risk analysis, company comparisons, "
            "and company overviews."
        )

    if state.get("status") == "planner_error":
        return "I could not read that request clearly. Please rephrase it."

    return "The request was processed, but no response was generated."


def handle_user_query(user_query: str) -> AgentState:
    state = st.session_state.state
    state["user_query"] = user_query
    state["status"] = "collecting_inputs"

    state = get_route(state)
    st.session_state.state = state
    return state


def main() -> None:
    st.set_page_config(
        page_title="Financial Risk Copilot",
        page_icon="A",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    if "messages" not in st.session_state:
        st.session_state.messages = default_messages()

    if "state" not in st.session_state:
        st.session_state.state = build_initial_state()

    load_styles()
    render_sidebar()

    st.title("Chat with Aegis")
    render_chat_history()

    user_query = st.chat_input("Ask about a company's financial risk")
    if not user_query:
        return

    st.session_state.messages.append({"role": "user", "content": user_query})
    with st.chat_message("user"):
        st.markdown(user_query)

    with st.chat_message("assistant"):
        with st.spinner("Working through the request..."):
            state = handle_user_query(user_query)
            response = build_response_message(state)
        st.markdown(response)

    st.session_state.messages.append({"role": "assistant", "content": response})


if __name__ == "__main__":
    main()
