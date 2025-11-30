import sqlite3
import yaml
import chevron
import os
import threading
import json
import time

try:
    from sentence_transformers import SentenceTransformer
except ImportError:
    print("Error: Please install sentence-transformers (pip install sentence-transformers)")
    exit(1)

DB_PATH = "sample.db"
TEMPLATE_PATH = "templates/select_info.yaml"
EMBEDDING_MODEL_NAME = "all-MiniLM-L6-v2"


def get_db_connection():
    return sqlite3.connect(DB_PATH)


def fetch_unique_values(cursor, table, column):
    cursor.execute(f"SELECT DISTINCT {column} FROM {table}")
    return [row[0] for row in cursor.fetchall() if row[0] is not None]


def background_embedding_worker():
    """
    This runs in a separate thread. It loads the model,
    finds rows without embeddings, and updates them.
    """
    print("\n[Background] Starting embedding process...")

    print(f"[Background] Loading model: {EMBEDDING_MODEL_NAME}...")
    model = SentenceTransformer(EMBEDDING_MODEL_NAME)

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("SELECT id, question, sql_query FROM training_data WHERE question_embedding IS NULL")
    rows = cursor.fetchall()

    if not rows:
        print("[Background] No rows to process.")
        conn.close()
        return

    print(f"[Background] Processing {len(rows)} rows...")

    updates = []

    ids = [r[0] for r in rows]
    questions = [r[1] for r in rows]
    sqls = [r[2] for r in rows]

    # Encode
    q_embeddings = model.encode(questions)
    s_embeddings = model.encode(sqls)

    # 5. Prepare SQL updates
    for i, row_id in enumerate(ids):
        # We store embeddings as JSON strings so they are easy to read/retrieve
        q_vec = json.dumps(q_embeddings[i].tolist())
        s_vec = json.dumps(s_embeddings[i].tolist())
        updates.append((q_vec, s_vec, row_id))

    # 6. Update Database
    cursor.executemany(
        "UPDATE training_data SET question_embedding = ?, sql_embedding = ? WHERE id = ?",
        updates
    )

    conn.commit()
    conn.close()
    print("[Background] Embeddings saved successfully.")


def save_to_database(pairs):
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("DROP TABLE IF EXISTS training_data")
    # Updated Schema to include embedding columns
    cursor.execute("""
        CREATE TABLE training_data (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            question TEXT NOT NULL,
            sql_query TEXT NOT NULL,
            template_source TEXT,
            question_embedding TEXT,
            sql_embedding TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    data_to_insert = [
        (p['question'], p['sql'], p['template_id'])
        for p in pairs
    ]

    cursor.executemany(
        "INSERT INTO training_data (question, sql_query, template_source) VALUES (?, ?, ?)",
        data_to_insert
    )

    conn.commit()
    conn.close()
    print(f"✓ Successfully saved {len(data_to_insert)} raw rows to 'training_data'.")

    # Trigger the background process
    thread = threading.Thread(target=background_embedding_worker)
    thread.start()

    # In a real server app, you wouldn't join here.
    # But for a script, we must wait for the thread to finish before the script exits.
    print("Waiting for background process to finish...")
    thread.join()


def main():
    if not os.path.exists(TEMPLATE_PATH):
        print(f"Error: {TEMPLATE_PATH} not found.")
        return

    with open(TEMPLATE_PATH, 'r') as f:
        data = yaml.safe_load(f)
        templates = data.get('templates', [])

    conn = get_db_connection()
    cursor = conn.cursor()

    context_data = {
        'city': fetch_unique_values(cursor, 'users', 'city'),
        'category': fetch_unique_values(cursor, 'products', 'category'),
        'product_name': fetch_unique_values(cursor, 'products', 'name'),
    }

    conn.close()

    print(f"Loaded context data:")
    for k, v in context_data.items():
        print(f" - {k}: {len(v)} unique values found.")

    generated_pairs = []

    for temp in templates:
        question_template = temp['question']
        sql_template = temp['sql']

        active_key = None
        for key in context_data.keys():
            if f"{{{{{key}}}}}" in question_template:
                active_key = key
                break

        if active_key:
            values = context_data[active_key]
            for val in values:
                render_context = {active_key: val}
                gen_q = chevron.render(question_template, render_context)
                gen_sql = chevron.render(sql_template, render_context)

                generated_pairs.append({
                    'question': gen_q,
                    'sql': gen_sql,
                    'template_id': question_template
                })
        else:
            generated_pairs.append({
                'question': question_template,
                'sql': sql_template,
                'template_id': "static"
            })

    print(f"\nGenerated {len(generated_pairs)} training examples.")
    save_to_database(generated_pairs)


if __name__ == "__main__":
    main()
