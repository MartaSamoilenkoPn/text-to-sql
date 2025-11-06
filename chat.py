import sqlite3
import pandas as pd
import re
from langchain_community.utilities import SQLDatabase
from langchain_ollama import ChatOllama
from langchain_classic.chains import create_sql_query_chain

import langchain
langchain.debug = True

DB_URI = "sqlite:///sample.db"
LLM_MODEL = "llama3:8b"

def create_chat_components(db_uri, model_name):
    print("Setting up components...")
    db = SQLDatabase.from_uri(db_uri)
    llm = ChatOllama(model=model_name, temperature=0)
    query_chain = create_sql_query_chain(llm, db)
    print("✓ Setup complete. Ready to chat.\n")
    return query_chain, db_uri


def main_chat_loop(query_chain, db_uri):
    db_path = db_uri.replace("sqlite:///", "")
    conn = sqlite3.connect(db_path)

    print("--- Text-to-SQL Chat ---")
    print("Type 'exit' to quit.")

    while True:
        try:
            user_question = input("\nAsk your database a question: ")

            if user_question.lower().strip() == 'exit':
                print("Goodbye!")
                break

            k = 0
            while k < 5:
                llm_response = query_chain.invoke({"question": user_question})
                if llm_response:
                    break
                k += 1

            print(f"LLM Response:\n{llm_response}")

            sql_match = llm_response.split("SQLQuery:")[1]

            if not sql_match:
                print("\n[Error] Could not find a valid SQL query in the LLM's response.")
                continue

            generated_sql = sql_match
            print(f"Extracted SQL:\n{generated_sql}")

            df = pd.read_sql_query(generated_sql, conn)

            print("\nQuery Result:")
            print(df)

        except pd.errors.DatabaseError as e:
            print(f"\n[Error] The generated SQL was invalid: {e}")
        except Exception as e:
            print(f"\n[Error] An unexpected error occurred: {e}")

    conn.close()


if __name__ == "__main__":
    chain, uri = create_chat_components(DB_URI, LLM_MODEL)
    main_chat_loop(chain, uri)