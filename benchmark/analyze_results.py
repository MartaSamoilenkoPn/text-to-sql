import json
import pandas as pd

def analyze_sql_results(file_path):
    # 1. Load the data
    data = []
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            for line in f:
                if line.strip():
                    try:
                        data.append(json.loads(line))
                    except Exception as e:
                        print(line)
                        print(f"Error decoding JSON: {e}")
                        raise e
    except FileNotFoundError:
        print(f"Error: File '{file_path}' not found.")
        return

    df = pd.DataFrame(data)
    
    # 2. Basic Metrics
    total_samples = len(df)
    correct_predictions = df['score'].sum()
    accuracy = (correct_predictions / total_samples) * 100

    print(f"--- General Statistics ---")
    print(f"Total Samples: {total_samples}")
    print(f"Correct:       {correct_predictions}")
    print(f"Accuracy:      {accuracy:.2f}%")
    print("-" * 30)

    # 3. Accuracy by Category
    if 'category' in df.columns:
        print("\n--- Accuracy by Category ---")
        cat_stats = df.groupby('category')['score'].agg(['count', 'mean']).reset_index()
        cat_stats['mean'] = cat_stats['mean'] * 100
        cat_stats.columns = ['Category', 'Total Questions', 'Accuracy (%)']
        print(cat_stats.to_string(index=False))
        print("-" * 30)


if __name__ == "__main__":
    file_path = './benchmark/benchmark_results_qwen2.5-coder:7b_Qwen_Qwen3-Embedding-0.6B.jsonl' 

    analyze_sql_results(file_path)
