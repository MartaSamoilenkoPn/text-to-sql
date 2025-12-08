import sqlite3
import yaml
import json
import os
import sys

try:
    from sentence_transformers import SentenceTransformer
except ImportError:
    print("Error: pip install sentence-transformers")
    sys.exit(1)

DB_PATH = "sample.db"
TEMPLATE_PATH = "select_info.yaml"
EMBEDDING_MODEL_NAME = "all-MiniLM-L6-v2"


def get_db_connection():
    return sqlite3.connect(DB_PATH)


def main():
    if not os.path.exists(TEMPLATE_PATH):
        print(f"Error: {TEMPLATE_PATH} not found.")
        return

    # 1. Load Templates from YAML
    with open(TEMPLATE_PATH, 'r') as f:
        data = yaml.safe_load(f)
        templates = data.get('templates', [])

    print(f"Loaded {len(templates)} templates from YAML.")

    # 2. Load Embedding Model
    print(f"Loading embedding model ({EMBEDDING_MODEL_NAME})...")
    model = SentenceTransformer(EMBEDDING_MODEL_NAME)

    # 3. Prepare Database
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("DROP TABLE IF EXISTS sql_templates")
    cursor.execute("""
                   CREATE TABLE sql_templates
                   (
                       id                INTEGER PRIMARY KEY AUTOINCREMENT,
                       question_template TEXT NOT NULL,
                       sql_template      TEXT NOT NULL,
                       embedding         TEXT
                   )
                   """)

    print("Embedding templates...")

    questions = [t['question'] for t in templates]
    embeddings = model.encode(questions)

    data_to_insert = []
    for i, t in enumerate(templates):
        emb_json = json.dumps(embeddings[i].tolist())
        data_to_insert.append((t['question'], t['sql'], emb_json))

    cursor.executemany(
        "INSERT INTO sql_templates (question_template, sql_template, embedding) VALUES (?, ?, ?)",
        data_to_insert
    )

    conn.commit()
    conn.close()
    print(f"✓ Successfully stored {len(data_to_insert)} templates with embeddings.")


if __name__ == "__main__":
    main()