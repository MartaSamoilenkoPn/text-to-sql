import gradio as gr

import backend

DB_URI = backend.DB_URI
LLM_MODEL = backend.LLM_MODEL
CHAIN, EMBED_MODEL = backend.create_chat_chain(DB_URI, LLM_MODEL)


def ui_process_query(user_input):
    """Wrapper to call backend logic"""
    return backend.process_query(user_input, CHAIN, EMBED_MODEL)


with gr.Blocks(title="Template-RAG Text-to-SQL") as demo:
    gr.Markdown("# 🐍 Template-RAG Text-to-SQL Demo")
    gr.Markdown(f"Using db: `{DB_URI}` — model: `{LLM_MODEL}`")

    with gr.Row():
        with gr.Column(scale=1):
            inp = gr.Textbox(
                placeholder="How many users registered last week?",
                label="Ask a question"
            )
            btn = gr.Button("Run Query", variant="primary")

        with gr.Column(scale=1):
            nl_tmpl = gr.Textbox(label="Matched NL Template")
            sql_tmpl = gr.Textbox(label="Matched SQL Template")
            score = gr.Textbox(label="Similarity Score")
            sql_out = gr.Code(language="sql", label="Generated SQL")

    result_table = gr.Dataframe(label="Query Result")

    # Connect buttons to the backend function
    btn.click(
        fn=ui_process_query,
        inputs=inp,
        outputs=[nl_tmpl, sql_tmpl, score, sql_out, result_table]
    )

    inp.submit(
        fn=ui_process_query,
        inputs=inp,
        outputs=[nl_tmpl, sql_tmpl, score, sql_out, result_table]
    )

if __name__ == "__main__":
    demo.launch()
