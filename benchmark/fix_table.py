import sqlite3

# Path to your specific database
DB_PATH = "./benchmark/spider_data/database/wta_1/wta_1.sqlite"

def fix_database():
    print(f"Connecting to {DB_PATH}...")
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Get a list of all actual tables in the database
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    existing_tables = {row[0] for row in cursor.fetchall()}
    print(f"Tables found in DB: {existing_tables}")

    # List of tables and their specific date columns to fix
    target_corrections = [
        ("players", "birth_date"),
        ("matches", "tourney_date"),
        ("qualifying_matches", "tourney_date"),
        ("rankings", "ranking_date")
    ]

    for table, col in target_corrections:
        if table not in existing_tables:
            print(f"Skipping table '{table}' (does not exist in this DB).")
            continue

        print(f"Fixing table '{table}', column '{col}'...")
        
        try:
            # 1. Check how many bad rows exist
            cursor.execute(f"SELECT count(*) FROM {table} WHERE typeof({col}) != 'text' OR {col} NOT LIKE '%-%'")
            bad_count = cursor.fetchone()[0]
            
            if bad_count == 0:
                print(f"  -> No bad rows found. Skipping.")
                continue
                
            print(f"  -> Found {bad_count} rows to fix.")

            # 2. Run the update
            # Takes 20230101 (integer) and turns it into '2023-01-01' (string)
            sql = f"""
            UPDATE {table}
            SET {col} = substr({col}, 1, 4) || '-' || substr({col}, 5, 2) || '-' || substr({col}, 7, 2)
            WHERE typeof({col}) != 'text' 
               OR {col} NOT LIKE '%-%';
            """
            cursor.execute(sql)
            print(f"  -> Successfully updated rows.")
            
        except Exception as e:
            print(f"  -> Error processing {table}: {e}")

    conn.commit()
    conn.close()
    print("\nDone! Database update complete and saved.")

if __name__ == "__main__":
    fix_database()
