import json
import pandas as pd
from collections import Counter

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

    # 3. Accuracy by Category (if you have multiple schemas/domains)
    if 'category' in df.columns:
        print("\n--- Accuracy by Category ---")
        cat_stats = df.groupby('category')['score'].agg(['count', 'mean']).reset_index()
        cat_stats['mean'] = cat_stats['mean'] * 100
        cat_stats.columns = ['Category', 'Total Questions', 'Accuracy (%)']
        print(cat_stats.to_string(index=False))
        print("-" * 30)

    # 4. Error Analysis (Inspecting the failures)
    failures = df[df['score'] == 0].copy()
    
    if len(failures) > 0:
        print(f"\n--- Analysis of {len(failures)} Failures ---")
        
        # Keyword Analysis: What SQL features are present in failed queries?
        # This helps check if the model struggles with JOINs, GROUP BYs, etc.
        keywords = ['JOIN', 'GROUP BY', 'ORDER BY', 'HAVING', 'WHERE', 'Distinct', 'LIMIT']
        failure_features = []
        
        for sql in failures['gt_sql']:
            features = [kw for kw in keywords if kw.lower() in sql.lower()]
            failure_features.extend(features)
            
        common_fail_patterns = Counter(failure_features).most_common()
        print("\nMost common SQL keywords in failed questions (Ground Truth):")
        for kw, count in common_fail_patterns:
            print(f"  - {kw}: {count} times")

        print("\n--- Detailed Failure Examples (First 5) ---")
        for i, row in failures.head(5).iterrows():
            print(f"\n[Question]: {row['question']}")
            print(f"[Gold SQL] : {row['gt_sql']}")
            print(f"[Pred SQL] : {row['predicted_sql']}")
            
        # Optional: Export failures to CSV for manual review
        failures.to_csv('failed_queries.csv', index=False)
        print(f"\nFull list of failed queries saved to 'failed_queries.csv'")
        
    else:
        print("\nGreat job! No failures detected.")

# --- Run the analysis ---
# Create a dummy file for demonstration if you run this directly
# You can replace this block by just pointing to your actual file
if __name__ == "__main__":
    # Assuming the data provided in the prompt is saved in 'results.jsonl'
    file_path = './benchmark/benchmark_results_qwen2.5-coder:7b_Qwen_Qwen3-Embedding-0.6B.jsonl' 

    analyze_sql_results(file_path)
