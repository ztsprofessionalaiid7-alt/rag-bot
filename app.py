from pathlib import Path

import streamlit as st

st.set_page_config(page_title="FastAPI Docs Assistant")

if not Path("chroma_db").exists():
    from ingest import build_index

    with st.spinner("First start: building the search index (1-2 min)..."):
        build_index()

from answer import answer

EXAMPLES = [
    "How do I make a query parameter optional?",
    "Which URL shows the interactive API docs?",
    "How do I raise an HTTP error with a custom status code?",
]

st.title("FastAPI Docs Assistant")
st.caption(
    "Answers only from 8 FastAPI tutorial pages, with sources. "
    "If the docs don't cover it, it says so."
)

with st.sidebar:
    st.header("Try an example")
    for ex in EXAMPLES:
        if st.button(ex):
            st.session_state["q"] = ex
    st.divider()
    st.markdown(
        "**Docs covered:** first steps, path params, query params, "
        "request body, error handling, response model, background tasks, CORS"
    )

question = st.text_input(
    "Ask a question",
    key="q",
    placeholder="How do I make a query parameter optional?",
)

if st.button("Ask", type="primary") and question.strip():
    with st.spinner("Searching docs..."):
        text, hits = answer(question.strip())
    if text == "NOT_IN_DOCS":
        st.warning("I can't find this in the loaded docs.")
    elif text == "LLM_ERROR":
        st.error("The AI service is busy right now. Please try again in a minute.")
    else:
        st.success(text)
    with st.expander("Sources (top matches)"):
        for h in hits:
            st.markdown(f"**{h['source']}** · distance {h['distance']:.3f}")
            st.text(h["text"][:300])