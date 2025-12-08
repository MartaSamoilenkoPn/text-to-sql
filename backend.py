import sqlite3
import pandas as pd
import json
import numpy as np
import re

from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
from langchain_community.utilities import SQLDatabase
from langchain_ollama import ChatOllama
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough

# ---------------------------
# CONFIG
# ---------------------------
DB_URI = "sqlite:///sample.db"
LLM_MODEL = "qwen3:4b-instruct"
EMBEDDING_MODEL_NAME = "all-MiniLM-L6-v2"
SIMILARITY_THRESHOLD = 0.35

def get_relevant_template(user_question, embed_model, conn):
    """
    Finds most similar question template and returns:
    (NL_template, SQL_template, similarity_score)
    """
    user_embedding = embed_model.encode(user_question)

    query = "SELECT question_template, sql_template, embedding FROM sql_templates"
    try:
        df = pd.read_sql_query(query, conn)
    except Exception:
        return None, None, 0

    if df.empty:
        return None, None, 0

    stored_embeddings = df['embedding'].apply(json.loads).tolist()
    stored_embeddings = np.array(stored_embeddings)

    user_embedding = user_embedding.reshape(1, -1)
    similarities = cosine_similarity(user_embedding, stored_embeddings)[0]

    best_idx = np.argmax(similarities)
    best_score = similarities[best_idx]

    if best_score > SIMILARITY_THRESHOLD:
        q_tmpl = df.iloc[best_idx]['question_template']
        sql_tmpl = df.iloc[best_idx]['sql_template']
        return q_tmpl, sql_tmpl, best_score

    return None, None, best_score

def create_chat_chain(db_uri, model_name):
    db = SQLDatabase.from_uri(db_uri)
    llm = ChatOllama(model=model_name, temperature=0)

    prompt_text = """
You are a SQLite query generator.

Database Schema:
{schema}

Instructions:
1. Use this template hint as guidance: {template_hint}
2. Output ONLY raw SQL, starting with SELECT
3. No markdown, no explanations.

Question: {question}
SQLQuery:
"""
    prompt = PromptTemplate.from_template(prompt_text)

    def get_schema(_):
        return db.get_table_info()

    chain = (
        RunnablePassthrough.assign(schema=get_schema)
        | prompt
        | llm
        | StrOutputParser()
    )

    embed_model = SentenceTransformer(EMBEDDING_MODEL_NAME)
    return chain, embed_model

def extract_sql_from_response(llm_response):
    clean_text = llm_response.strip()
    
    # Try finding markdown code block
    code_block_pattern = r"```(?:sql)?\s*(.*?)```"
    match = re.search(code_block_pattern, clean_text, re.DOTALL | re.IGNORECASE)
    if match:
        clean_text = match.group(1).strip()

    # Try finding raw SQL pattern
    sql_pattern = r"(SELECT\s+.*?;)"
    match_sql = re.search(sql_pattern, clean_text, re.DOTALL | re.IGNORECASE)
    if match_sql:
        return match_sql.group(1)

    if "SQLQuery:" in clean_text:
        clean_text = clean_text.split("SQLQuery:")[1].strip()

    return clean_text


def process_query(user_question, chain, embed_model, db_path_override=None, template_conn=None):
    """
    Args:
        template_conn: Connection to the RAG database (where sql_templates table lives).
                       If None, defaults to the target execution DB (for simple apps).
    """
    if not user_question:
        return "No match", "No match", "No score", "Please enter a query.", None
    
    target_db = db_path_override if db_path_override else DB_URI
    real_db_path = target_db.replace("sqlite:///", "")
    
    # Connection for EXECUTION (The target data)
    target_conn = sqlite3.connect(real_db_path)
    
    # Connection for TEMPLATES (The RAG knowledge base)
    # If no separate template DB is provided, assume templates are in the target DB
    rag_conn = template_conn if template_conn else target_conn

    # ---- Template Matching (Use rag_conn) ----
    # We pass rag_conn, NOT target_conn here
    q_tmpl, sql_tmpl, score = get_relevant_template(user_question, embed_model, rag_conn)
    score_text = f"{score:.4f}"

    if not sql_tmpl:
        template_for_llm = "No template found. Generate valid SQLite based on schema."
        q_tmpl_show = "No match"
        sql_tmpl_show = "No match"
    else:
        template_for_llm = sql_tmpl
        q_tmpl_show = q_tmpl
        sql_tmpl_show = sql_tmpl

    # ---- LLM ----
    response = chain.invoke({
        "question": user_question,
        "template_hint": template_for_llm
    })

    generated_sql = extract_sql_from_response(response)

    # ---- SQL Execution (Use target_conn) ----
    try:
        df = pd.read_sql_query(generated_sql, target_conn)
        target_conn.close()
        return q_tmpl_show, sql_tmpl_show, score_text, generated_sql, df

    except Exception as e:
        target_conn.close()
        error_msg = f"SQL Error: {e}\n\nGenerated SQL:\n{generated_sql}"
        return q_tmpl_show, sql_tmpl_show, score_text, error_msg, None
    

if __name__ == "__main__":
    # Initialize models once when module is imported
    print("Loading models...")
    chain, embed_model = create_chat_chain(DB_URI, LLM_MODEL)
    print("Models loaded.")