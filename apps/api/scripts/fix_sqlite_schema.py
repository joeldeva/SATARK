import sqlite3
import os

db_path = "satark_dev.db"
if not os.path.exists(db_path):
    print(f"Database file not found: {db_path}")
    exit(1)

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Get column names of 'responses' table
cursor.execute("PRAGMA table_info(responses)")
columns = [row[1] for row in cursor.fetchall()]
print("Existing columns in responses table:", columns)

added = []
if "content_hash" not in columns:
    cursor.execute("ALTER TABLE responses ADD COLUMN content_hash VARCHAR")
    added.append("content_hash")
if "prev_hash" not in columns:
    cursor.execute("ALTER TABLE responses ADD COLUMN prev_hash VARCHAR")
    added.append("prev_hash")
if "chain_index" not in columns:
    cursor.execute("ALTER TABLE responses ADD COLUMN chain_index INTEGER")
    added.append("chain_index")

conn.commit()
conn.close()

if added:
    print(f"Successfully added columns to responses table: {added}")
else:
    print("All columns already present in responses table.")
