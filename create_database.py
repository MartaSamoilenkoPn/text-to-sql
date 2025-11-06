import sqlite3
import os


def create_sample_database(db_path: str = "sample.db"):
    if os.path.exists(db_path):
        os.remove(db_path)
        print(f"Removed existing database: {db_path}")

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            age INTEGER,
            city TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    cursor.execute("""
        CREATE TABLE orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            product_name TEXT NOT NULL,
            quantity INTEGER NOT NULL,
            price REAL NOT NULL,
            order_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)

    cursor.execute("""
        CREATE TABLE products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            category TEXT,
            price REAL NOT NULL,
            stock INTEGER DEFAULT 0
        )
    """)
    
    # Insert sample users
    users_data = [
        ("Alice Johnson", "alice@example.com", 28, "New York"),
        ("Bob Smith", "bob@example.com", 35, "Los Angeles"),
        ("Charlie Brown", "charlie@example.com", 17, "Chicago"),
        ("Diana Prince", "diana@example.com", 42, "San Francisco"),
        ("Eve Wilson", "eve@example.com", 19, "Seattle"),
        ("Frank Miller", "frank@example.com", 55, "Boston"),
        ("Grace Lee", "grace@example.com", 31, "Austin"),
        ("Henry Davis", "henry@example.com", 16, "Denver"),
    ]
    
    cursor.executemany(
        "INSERT INTO users (name, email, age, city) VALUES (?, ?, ?, ?)",
        users_data
    )
    
    # Insert sample products
    products_data = [
        ("Laptop", "Electronics", 999.99, 50),
        ("Mouse", "Electronics", 29.99, 200),
        ("Keyboard", "Electronics", 79.99, 150),
        ("Monitor", "Electronics", 299.99, 75),
        ("Desk Chair", "Furniture", 199.99, 30),
        ("Notebook", "Stationery", 4.99, 500),
        ("Pen Set", "Stationery", 12.99, 300),
    ]
    
    cursor.executemany(
        "INSERT INTO products (name, category, price, stock) VALUES (?, ?, ?, ?)",
        products_data
    )
    
    # Insert sample orders
    orders_data = [
        (1, "Laptop", 1, 999.99),
        (1, "Mouse", 2, 29.99),
        (2, "Monitor", 1, 299.99),
        (2, "Keyboard", 1, 79.99),
        (3, "Notebook", 5, 4.99),
        (4, "Desk Chair", 1, 199.99),
        (4, "Laptop", 1, 999.99),
        (5, "Pen Set", 3, 12.99),
        (6, "Monitor", 2, 299.99),
        (7, "Mouse", 1, 29.99),
        (7, "Keyboard", 1, 79.99),
    ]
    
    cursor.executemany(
        "INSERT INTO orders (user_id, product_name, quantity, price) VALUES (?, ?, ?, ?)",
        orders_data
    )
    
    conn.commit()
    conn.close()
    
    print(f"\n✓ Sample database created: {db_path}")
    print(f"  - Users table: {len(users_data)} records")
    print(f"  - Products table: {len(products_data)} records")
    print(f"  - Orders table: {len(orders_data)} records")
    
    return db_path


if __name__ == "__main__":
    create_sample_database()
