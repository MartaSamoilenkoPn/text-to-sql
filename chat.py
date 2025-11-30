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
    print("Error: Missing libraries. Run: pip install sentence-transformers scikit-learn numpy")
    sys.exit(1)

from langchain_community.utilities import SQLDatabase
from langchain_ollama import ChatOllama
from langchain_classic.chains import create_sql_query_chain

DB_URI = "sqlite:///sample.db"
LLM_MODEL = "llama3:8b"
EMBEDDING_MODEL_NAME = "all-MiniLM-L6-v2"
SIMILARITY_THRESHOLD = 0.95


def create_chat_components(db_uri, model_name):
    print("Setting up components...")
    db = SQLDatabase.from_uri(db_uri)
    llm = ChatOllama(model=model_name, temperature=0)
    query_chain = create_sql_query_chain(llm, db)

    print(f"Loading embedding model ({EMBEDDING_MODEL_NAME})...")
    embed_model = SentenceTransformer(EMBEDDING_MODEL_NAME)

    print("✓ Setup complete. Ready to chat.\n")
    return query_chain, db_uri, embed_model


def get_cached_sql(user_question, embed_model, conn):
    user_embedding = embed_model.encode(user_question)

    query = "SELECT question, sql_query, question_embedding FROM training_data WHERE question_embedding IS NOT NULL"
    try:
        df = pd.read_sql_query(query, conn)
    except Exception:
        return None, 0

    if df.empty:
        return None, 0

    stored_embeddings = df['question_embedding'].apply(json.loads).tolist()
    stored_embeddings = np.array(stored_embeddings)

    user_embedding = user_embedding.reshape(1, -1)
    similarities = cosine_similarity(user_embedding, stored_embeddings)[0]

    best_idx = np.argmax(similarities)
    best_score = similarities[best_idx]

    if best_score > SIMILARITY_THRESHOLD:
        found_sql = df.iloc[best_idx]['sql_query']
        found_question = df.iloc[best_idx]['question']
        print(f"   [Cache Hit] Matched: '{found_question}' (Score: {best_score:.4f})")
        return found_sql, best_score

    return None, best_score


# --- NEW HELPER FUNCTION ---
def extract_sql_from_response(llm_response):
    """
    Robustly extracts SQL from chatty LLM responses.
    Priority:
    1. Content inside ```sql ... ``` code blocks.
    2. Content inside ``` ... ``` generic code blocks.
    3. Content after 'SQLQuery:'.
    4. Raw text (fallback).
    """
    code_block_pattern = r"```(?:sql)?\s*(.*?)```"
    match = re.search(code_block_pattern, llm_response, re.DOTALL | re.IGNORECASE)

    if match:
        sql = match.group(1).strip()
        if sql.lower().startswith("sql"):
            sql = sql[3:].strip()
        return sql

    if "SQLQuery:" in llm_response:
        return llm_response.split("SQLQuery:")[1].strip()

    return llm_response.strip()


def main_chat_loop(query_chain, db_uri, embed_model):
    db_path = db_uri.replace("sqlite:///", "")
    conn = sqlite3.connect(db_path)

    print("--- Text-to-SQL Chat (Hybrid Mode) ---")
    print("Type 'exit' to quit.")

    while True:
        try:
            user_question = input("\nAsk your database a question: ")

            if user_question.lower().strip() == 'exit':
                print("Goodbye!")
                break

            print("   [System] Checking cache...")
            cached_sql, score = get_cached_sql(user_question, embed_model, conn)

            generated_sql = ""

            if cached_sql:
                print("   [System] Using cached SQL.")
                generated_sql = cached_sql
            else:
                print(f"   [System] No close match found (Max score: {score:.4f}). Generating via LLM...")

                k = 0
                llm_response = ""
                while k < 5:
                    try:
                        llm_response = query_chain.invoke({"question": user_question})
                        if llm_response:
                            break
                    except Exception as e:
                        print(f"LLM Error: {e}")
                    k += 1

                generated_sql = extract_sql_from_response(llm_response)

            if not generated_sql:
                print("\n[Error] Could not determine a valid SQL query.")
                continue

            print(f"Extracted SQL:\n{generated_sql}")

            df = pd.read_sql_query(generated_sql, conn)

            print("\nQuery Result:")
            print(df)

        except pd.errors.DatabaseError as e:
            print(f"\n[Error] The SQL was invalid: {e}")
        except Exception as e:
            print(f"\n[Error] An unexpected error occurred: {e}")

    conn.close()


if __name__ == "__main__":
    chain, uri, model = create_chat_components(DB_URI, LLM_MODEL)
    main_chat_loop(chain, uri, model)