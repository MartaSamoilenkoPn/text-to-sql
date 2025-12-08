import sqlite3
import pandas as pd
import json
import numpy as np
import sys
import re

try:
    from sentence_transformers import SentenceTransformer
    from sklearn.metrics.pairwise import cosine_similarity
except ImportError:
    print("Error: Missing libraries.")
    sys.exit(1)

from langchain_community.utilities import SQLDatabase
from langchain_ollama import ChatOllama
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough

DB_URI = "sqlite:///sample.db"
LLM_MODEL = "llama3:8b"
EMBEDDING_MODEL_NAME = "all-MiniLM-L6-v2"
SIMILARITY_THRESHOLD = 0.35


def get_relevant_template(user_question, embed_model, conn):
    """
    Finds the most similar generic template in the database.
    """
    user_embedding = embed_model.encode(user_question)

    query = "SELECT question_template, sql_template, embedding FROM sql_templates"
    try:
        df = pd.read_sql_query(query, conn)
    except Exception:
        return None, 0

    if df.empty:
        return None, 0

    stored_embeddings = df['embedding'].apply(json.loads).tolist()
    stored_embeddings = np.array(stored_embeddings)

    user_embedding = user_embedding.reshape(1, -1)
    similarities = cosine_similarity(user_embedding, stored_embeddings)[0]

    best_idx = np.argmax(similarities)
    best_score = similarities[best_idx]

    if best_score > SIMILARITY_THRESHOLD:
        found_template_q = df.iloc[best_idx]['question_template']
        found_template_sql = df.iloc[best_idx]['sql_template']
        print(f"   [Template Match] '{found_template_q}' (Score: {best_score:.4f})")
        return found_template_sql, best_score

    return None, best_score


def create_chat_chain(db_uri, model_name):
    print("Setting up components...")
    db = SQLDatabase.from_uri(db_uri)
    llm = ChatOllama(model=model_name, temperature=0)

    # --- UPDATED STRICTER PROMPT ---
    prompt_system = """You are a SQLite query generator.

    Database Schema:
    {schema}

    INSTRUCTIONS:
    1. Use this pattern as a guide: {template_hint}
    2. Replace {{placeholders}} in the pattern with values from the question.
    3. Output ONLY the raw SQL query. 
    4. Do NOT output markdown (no ```sql). 
    5. Do NOT explain your answer. Start immediately with SELECT.

    Question: {question}
    SQLQuery:"""

    prompt = PromptTemplate.from_template(prompt_system)

    def get_schema(_):
        return db.get_table_info()

    chain = (
            RunnablePassthrough.assign(schema=get_schema)
            | prompt
            | llm
            | StrOutputParser()
    )

    print(f"Loading embedding model ({EMBEDDING_MODEL_NAME})...")
    embed_model = SentenceTransformer(EMBEDDING_MODEL_NAME)

    print("✓ Setup complete. Ready to chat.\n")
    return chain, db_uri, embed_model


def extract_sql_from_response(llm_response):
    """
    More robust extraction logic that looks for the SQL structure
    even if the LLM adds conversational text.
    """
    clean_text = llm_response.strip()

    print(clean_text)

    code_block_pattern = r"```(?:sql)?\s*(.*?)```"
    match = re.search(code_block_pattern, clean_text, re.DOTALL | re.IGNORECASE)
    if match:
        clean_text = match.group(1).strip()

    sql_pattern = r"(SELECT\s+.*?;)"
    match_sql = re.search(sql_pattern, clean_text, re.DOTALL | re.IGNORECASE)

    if match_sql:
        return match_sql.group(1)

    if "SQLQuery:" in clean_text:
        clean_text = clean_text.split("SQLQuery:")[1].strip()

    return clean_text


def main_chat_loop(chain, db_uri, embed_model):
    db_path = db_uri.replace("sqlite:///", "")
    conn = sqlite3.connect(db_path)

    print("--- Text-to-SQL (Template RAG Mode) ---")

    while True:
        try:
            user_question = input("\nAsk: ")
            if user_question.lower() in ['exit', 'quit']:
                break

            template_sql, score = get_relevant_template(user_question, embed_model, conn)

            if not template_sql:
                template_sql = "No template found. Generate valid SQLite based on schema."
                print(f"   [System] No template match (Max Score: {score:.4f}).")

            response = chain.invoke({
                "question": user_question,
                "IMPORTANT" : "TAKE THE QUESTION AS A PRIORITY, NOT THE TEMPLATE",
                "template_hint": template_sql
            })

            generated_sql = extract_sql_from_response(response)

            if not generated_sql.upper().startswith("SELECT"):
                print(f"[Warning] LLM Response didn't look like SQL: {response}")
                continue

            print(f"Extracted SQL: {generated_sql}")

            df = pd.read_sql_query(generated_sql, conn)
            print("\nResult:")
            print(df)

        except pd.errors.DatabaseError as e:
            print(f"\n[SQL Error] {e}")
        except Exception as e:
            print(f"\n[Error] {e}")

    conn.close()


if __name__ == "__main__":
    chain, uri, model = create_chat_chain(DB_URI, LLM_MODEL)
    main_chat_loop(chain, uri, model)