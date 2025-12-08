import os
import json
import sqlite3
import argparse

import pandas as pd
from tqdm import tqdm
from datasets import load_dataset
from sentence_transformers import SentenceTransformer

from backend import process_query, create_chat_chain, LLM_MODEL, EMBEDDING_MODEL_NAME

SPIDER_DB_ROOT = "./benchmark/spider_data/database"
TEMPLATE_DB_PATH = "spider_templates.db"


def parse_arguments():
    parser = argparse.ArgumentParser(description="Benchmark Text-to-SQL App on Spider Dataset")
    parser.add_argument("--run_name", type=str, default="default", help="Name of the run (used for output filename)")
    return parser.parse_args()


def build_knowledge_base(train_data, embed_model):
    """
    Creates a temporary SQLite DB containing only the templates/embeddings
    derived from the Spider TRAINING set.
    """
    print("--- Phase 1: Building RAG Knowledge Base ---")
    if os.path.exists(TEMPLATE_DB_PATH):
        os.remove(TEMPLATE_DB_PATH)
    
    conn = sqlite3.connect(TEMPLATE_DB_PATH)
    conn.execute("CREATE TABLE sql_templates (question_template TEXT, sql_template TEXT, embedding TEXT)")
    
    print("Embedding training data...")
    questions = [item['question'] for item in train_data]
    embeddings = embed_model.encode(questions, show_progress_bar=True)
    
    data_to_insert = []
    for i, item in enumerate(train_data):
        emb_json = json.dumps(embeddings[i].tolist())
        data_to_insert.append((item['question'], item['query'], emb_json))
        
    conn.executemany("INSERT INTO sql_templates VALUES (?, ?, ?)", data_to_insert)
    conn.commit()
    conn.close()
    print("Knowledge Base Built.\n")


def run_benchmark(validation_data, embed_model, output_file):
    print(f"--- Phase 2: Running Evaluation (Saving to {output_file}) ---")
    
    # 1. Load already processed tasks to support resuming
    processed_keys = set()
    if os.path.exists(output_file):
        print(f"Found existing file '{output_file}'. Reading processed tasks...")
        with open(output_file, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line: 
                    continue

                try:
                    record = json.loads(line)
                    # We use (question, db_id) as a unique key to identify the task
                    key = (record["question"], record["category"])
                    processed_keys.add(key)
                except json.JSONDecodeError:
                    continue
        print(f"Resuming... Skipping {len(processed_keys)} already processed tasks.\n")

    # Keep the template DB open for the duration of the test
    template_conn = sqlite3.connect(TEMPLATE_DB_PATH)
    
    correct_count = 0
    total = 0
    
    # We loop through the validation set
    for item in tqdm(validation_data):
        question = item['question']
        gold_sql = item['query']
        db_id = item['db_id']

        if (question, db_id) in processed_keys:
            continue
        
        target_db_path = os.path.join(SPIDER_DB_ROOT, db_id, f"{db_id}.sqlite")
        
        if not os.path.exists(target_db_path):
            continue
            
        # 1. Create a chain specific to this database schema
        dynamic_chain, _ = create_chat_chain(f"sqlite:///{target_db_path}", LLM_MODEL)
        
        # 2. Run app logic
        _, _, _, generated_sql, df_gen = process_query(
            user_question=question,
            chain=dynamic_chain,
            embed_model=embed_model,
            db_path_override=f"sqlite:///{target_db_path}",
            template_conn=template_conn 
        )
        
        # 3. Validation (Execution Accuracy)
        score = 0
        try:
            check_conn = sqlite3.connect(target_db_path)
            df_gold = pd.read_sql_query(gold_sql, check_conn)
            check_conn.close()
            
            if df_gen is not None:
                gen_set = set(tuple(row) for row in df_gen.values)
                gold_set = set(tuple(row) for row in df_gold.values)

                if gen_set == gold_set:
                    score = 1
                    correct_count += 1

        except Exception:
            pass
            
        # 4. Save Result
        result_entry = {
            "question": question,
            "category": db_id,
            "gt_sql": gold_sql,
            "predicted_sql": generated_sql,
            "score": score
        }
        
        with open(output_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(result_entry) + "\n")

        total += 1

    template_conn.close()
    
    if total > 0:
        accuracy = correct_count / total
        print(f"\nNew Tasks Processed: {total}")
        print(f"Accuracy (on new tasks): {correct_count}/{total} ({accuracy:.2%})")
    else:
        print("\nNo new tasks to process.")
    
    print(f"All results available in {output_file}")


if __name__ == "__main__":
    args = parse_arguments()
    
    output_filename = f"./benchmark/benchmark_results_{args.run_name}.jsonl"

    print("Loading Embedding Model...")
    embed_model = SentenceTransformer(EMBEDDING_MODEL_NAME)
    
    dataset = load_dataset("spider")
    
    # Run
    build_knowledge_base(dataset['train'], embed_model)
    
    run_benchmark(dataset['validation'], embed_model, output_filename)
