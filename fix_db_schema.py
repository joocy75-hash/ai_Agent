import sqlite3
import os

DB_PATH = "backend/trading.db"


def migrate_db():
    if not os.path.exists(DB_PATH):
        print(f"Database not found at {DB_PATH}")
        return

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Check existing columns in users table
    cursor.execute("PRAGMA table_info(users)")
    columns = [info[1] for info in cursor.fetchall()]
    print(f"Current columns: {columns}")

    # Add totp_secret if missing
    if "totp_secret" not in columns:
        print("Adding totp_secret column...")
        try:
            cursor.execute("ALTER TABLE users ADD COLUMN totp_secret TEXT")
            print("totp_secret added.")
        except Exception as e:
            print(f"Error adding totp_secret: {e}")

    # Add is_2fa_enabled if missing
    if "is_2fa_enabled" not in columns:
        print("Adding is_2fa_enabled column...")
        try:
            cursor.execute(
                "ALTER TABLE users ADD COLUMN is_2fa_enabled BOOLEAN DEFAULT 0 NOT NULL"
            )
            print("is_2fa_enabled added.")
        except Exception as e:
            print(f"Error adding is_2fa_enabled: {e}")

    # Add suspended_at if missing
    if "suspended_at" not in columns:
        print("Adding suspended_at column...")
        try:
            cursor.execute("ALTER TABLE users ADD COLUMN suspended_at DATETIME")
            print("suspended_at added.")
        except Exception as e:
            print(f"Error adding suspended_at: {e}")

    conn.commit()
    conn.close()
    print("Migration completed.")


if __name__ == "__main__":
    migrate_db()
