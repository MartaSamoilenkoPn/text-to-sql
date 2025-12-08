import sqlite3
import os
import random
from faker import Faker

fake = Faker()

def create_sample_database(db_path: str = "sample.db"):
    if os.path.exists(db_path):
        os.remove(db_path)

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute("""DROP TABLE IF EXISTS users;""")
    cursor.execute("""
                   CREATE TABLE users
                   (
                       id         INTEGER PRIMARY KEY AUTOINCREMENT,
                       name       TEXT        NOT NULL,
                       email      TEXT UNIQUE NOT NULL,
                       age        INTEGER,
                       city       TEXT,
                       created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                   )
                   """)

    cursor.execute("""DROP TABLE IF EXISTS products;""")
    cursor.execute("""
                   CREATE TABLE products
                   (
                       id       INTEGER PRIMARY KEY AUTOINCREMENT,
                       name     TEXT NOT NULL,
                       category TEXT,
                       price    REAL NOT NULL,
                       stock    INTEGER DEFAULT 0
                   )
                   """)

    cursor.execute("""DROP TABLE IF EXISTS orders;""")
    cursor.execute("""
                   CREATE TABLE orders
                   (
                       id           INTEGER PRIMARY KEY AUTOINCREMENT,
                       user_id      INTEGER NOT NULL,
                       product_name TEXT    NOT NULL,
                       quantity     INTEGER NOT NULL,
                       price        REAL    NOT NULL,
                       order_date   TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                       FOREIGN KEY (user_id) REFERENCES users (id)
                   )
                   """)

    products_data = [
        ("Laptop", "Electronics", 999.99, 50),
        ("Mouse", "Electronics", 29.99, 200),
        ("Keyboard", "Electronics", 79.99, 150),
        ("Monitor", "Electronics", 299.99, 75),
        ("Headphones", "Electronics", 199.99, 100),
        ("Desk Chair", "Furniture", 199.99, 30),
        ("Standing Desk", "Furniture", 450.00, 15),
        ("Notebook", "Stationery", 4.99, 500),
        ("Pen Set", "Stationery", 12.99, 300),
        ("Stapler", "Stationery", 7.99, 100),
    ]
    cursor.executemany(
        "INSERT INTO products (name, category, price, stock) VALUES (?, ?, ?, ?)",
        products_data
    )

    print("Generating users...")
    users_data = []
    cities = ["New York", "Los Angeles", "Chicago", "Houston", "Phoenix", "Philadelphia", "San Antonio", "San Diego",
              "Dallas", "San Jose"]

    for _ in range(50):
        users_data.append((
            fake.name(),
            fake.unique.email(),
            random.randint(18, 70),
            random.choice(cities)
        ))

    cursor.executemany(
        "INSERT INTO users (name, email, age, city) VALUES (?, ?, ?, ?)",
        users_data
    )

    print("Generating orders...")
    user_ids = [row[0] for row in cursor.execute("SELECT id FROM users").fetchall()]

    orders_data = []
    for _ in range(200):
        u_id = random.choice(user_ids)
        prod = random.choice(products_data)
        prod_name = prod[0]
        base_price = prod[2]

        qty = random.randint(1, 5)
        total_price = round(base_price * qty, 2)

        orders_data.append((u_id, prod_name, qty, total_price))

    cursor.executemany(
        "INSERT INTO orders (user_id, product_name, quantity, price) VALUES (?, ?, ?, ?)",
        orders_data
    )

    conn.commit()
    conn.close()

    print(f"\n✓ Database created: {db_path}")
    print(f"  - Users: {len(users_data)}")
    print(f"  - Products: {len(products_data)}")
    print(f"  - Orders: {len(orders_data)}")


if __name__ == "__main__":
    create_sample_database()