"""Lightweight Streamlit chat interface for the financial-risk copilot."""

import sys
from pathlib import Path

import streamlit as st

sys.path.append(str(Path(__file__).resolve().parents[1]))

from config.settings import LLM_MODEL
from workflow.routes import get_route
from workflow.state import AgentState


PROJECT_ROOT = Path(__file__).resolve().parents[1]
FAVICON_PATH = PROJECT_ROOT / "img" / "favicon.png"
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
  
        st.caption("Debug")

        if "debug_json_container" not in st.session_state:
            st.session_state.debug_json_container = st.empty()

        st.session_state.debug_json_container.json(
            st.session_state.state,
            expanded=False,
        )


def render_chat_history() -> None:
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])


def build_response_message(state: AgentState) -> str:
    answer = state.get("answer") or ""
    intent = state.get("intent")
    status = state.get("status")

    if status == "done" and answer:
        return answer

    if intent in ["chat", "follow_up"] and answer:
        return answer or "I have no response for that."

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

    elif status == "unsupported":
        answer = (
            state.get("answer")
            or "Action not supported. I can help with company financial-risk analysis, company comparisons, "
            "and company overviews."
        )

    elif status == "ready_for_response":
        answer = state.get("answer") or "I have no response for that."

    elif status == "ready_for_pipeline" and len(answer) == 0:
        answer = "The request is ready for analysis, but no report response was generated yet."

    else:
        answer = "I have no response for that."

    state["answer"] = answer
    return answer

def handle_user_query(user_query: str) -> AgentState:
    state = st.session_state.state
    state["user_query"] = user_query
    
    return get_route(state)
    
def process_user_query(user_query: str) -> None:
    st.session_state.messages.append({"role": "user", "content": user_query})

    with st.chat_message("user"):
        st.markdown(user_query)

    with st.chat_message("assistant"):
        with st.spinner("Working through the request..."):
            state = handle_user_query(user_query)
            st.session_state.state = state

            response = build_response_message(state)

        st.markdown(response)
        st.session_state.debug_json_container.json(state, expanded=True)


    st.session_state.messages.append(
        {"role": "assistant", "content": response}
    )

def init_session_state() -> None:
    if "messages" not in st.session_state:
        st.session_state.messages = default_messages()

    if "state" not in st.session_state:
        st.session_state.state = build_initial_state()

def main() -> None:
    st.set_page_config(
        page_title="Financial Risk Copilot",
        page_icon=str(FAVICON_PATH),
        layout="wide",
        initial_sidebar_state="expanded",
    )

    init_session_state()

    load_styles()
    render_sidebar()

    st.title("Chat with Aegis")
    render_chat_history()

    user_query = st.chat_input("Ask about a company's financial risk")
    if not user_query:
        return

    process_user_query(user_query)

if __name__ == "__main__":
    main()
