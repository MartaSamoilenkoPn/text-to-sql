import gradio as gr
import sqlite3
import pandas as pd
from langchain_community.utilities import SQLDatabase
from langchain_ollama import ChatOllama
from langchain_classic.chains import create_sql_query_chain

import langchain
langchain.debug = True

# --- Configuration ---
DB_URI = "sqlite:///sample.db"
LLM_MODEL = "qwen3:4b-instruct"

# --- Initialization ---
def create_chat_components(db_uri, model_name):
    print("Setting up components...")
    db = SQLDatabase.from_uri(db_uri)
    llm = ChatOllama(model=model_name, temperature=0)
    query_chain = create_sql_query_chain(llm, db)
    return query_chain

chain = create_chat_components(DB_URI, LLM_MODEL)

# --- Core Logic ---
def process_query(user_question):
    """
    Takes a text question, generates SQL, runs it, and returns the SQL + Table.
    """
    if not user_question:
        return "Please enter a question.", None

    # Connect to DB just for this query
    db_path = DB_URI.replace("sqlite:///", "")
    conn = sqlite3.connect(db_path)
    
    try:
        # 1. Invoke LLM with retry logic
        llm_response = ""
        for _ in range(5):
            llm_response = chain.invoke({"question": user_question})
            if llm_response:
                break
        
        # 2. Extract SQL
        # We try to split by 'SQLQuery:', but we also clean up markdown formatting just in case
        if "SQLQuery:" in llm_response:
            generated_sql = llm_response.split("SQLQuery:")[1]
        else:
            # Fallback: assume the whole response might be SQL if the prompt failed strictly
            generated_sql = llm_response

        # Cleanup: Remove Markdown backticks if the LLM adds them
        generated_sql = generated_sql.replace("```sql", "").replace("```", "").strip()
        
        # Remove any trailing semicolon if pandas doesn't like it (optional, usually pandas handles it)
        # generated_sql = generated_sql.rstrip(';') 

        # 3. Execute SQL
        df = pd.read_sql_query(generated_sql, conn)
        
        conn.close()
        
        # Return the SQL string and the Dataframe
        return generated_sql, df

    except pd.errors.DatabaseError as e:
        conn.close()
        return f"SQL Error:\n{e}\n\nGenerated SQL was:\n{generated_sql}", None
    except Exception as e:
        conn.close()
        return f"Error processing request: {str(e)}", None

# --- Gradio UI ---
with gr.Blocks(title="Text-to-SQL Chat") as demo:
    gr.Markdown("# 🍌 Text-to-SQL Assistant")
    gr.Markdown(f"Querying database: `{DB_URI}` using `{LLM_MODEL}`")
    
    with gr.Row():
        with gr.Column(scale=1):
            inp = gr.Textbox(placeholder="How many users do we have?", label="Ask a question")
            btn = gr.Button("Run Query", variant="primary")
        
        with gr.Column(scale=1):
            sql_output = gr.Code(language="sql", label="Generated SQL")
    
    # Dataframe to display results
    result_output = gr.Dataframe(label="Query Results", interactive=False)

    # Event listener
    btn.click(fn=process_query, inputs=inp, outputs=[sql_output, result_output])
    
    # Allow pressing "Enter" to submit
    inp.submit(fn=process_query, inputs=inp, outputs=[sql_output, result_output])

if __name__ == "__main__":
    demo.launch()