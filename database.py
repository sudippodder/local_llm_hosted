import os
import sqlite3
from datetime import datetime

# Get database path from environment variable, defaulting to local workspace
DB_PATH = os.getenv("SQLITE_DB_PATH", "chat_history.db")

def get_db_connection():
    """Establish and return a connection to the SQLite database.
    Ensures that parent directories exist and foreign key support is enabled.
    """
    # Create parent directories if they don't exist
    db_dir = os.path.dirname(DB_PATH)
    if db_dir:
        os.makedirs(db_dir, exist_ok=True)

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    # Enable foreign keys support in SQLite
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn

def init_db():
    """Initialize the SQLite database schema if tables do not exist."""
    conn = get_db_connection()
    try:
        with conn:
            # Create threads table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS threads (
                    id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)
            # Create messages table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    thread_id TEXT NOT NULL,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (thread_id) REFERENCES threads (id) ON DELETE CASCADE
                );
            """)
    finally:
        conn.close()

def create_thread(thread_id: str, title: str):
    """Create a new chat thread."""
    conn = get_db_connection()
    try:
        with conn:
            conn.execute(
                "INSERT INTO threads (id, title, created_at) VALUES (?, ?, ?)",
                (thread_id, title, datetime.now().isoformat())
            )
    finally:
        conn.close()

def get_all_threads():
    """Retrieve all threads, sorted by creation time descending (newest first)."""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT id, title, created_at FROM threads ORDER BY created_at DESC")
        return [dict(row) for row in cursor.fetchall()]
    finally:
        conn.close()

def rename_thread(thread_id: str, new_title: str):
    """Rename an existing thread's title."""
    conn = get_db_connection()
    try:
        with conn:
            conn.execute(
                "UPDATE threads SET title = ? WHERE id = ?",
                (new_title, thread_id)
            )
    finally:
        conn.close()

def delete_thread(thread_id: str):
    """Delete a thread. Cascade delete will remove associated messages."""
    conn = get_db_connection()
    try:
        with conn:
            conn.execute("DELETE FROM threads WHERE id = ?", (thread_id,))
    finally:
        conn.close()

def add_message(thread_id: str, role: str, content: str):
    """Add a chat message to a specific thread."""
    conn = get_db_connection()
    try:
        with conn:
            conn.execute(
                "INSERT INTO messages (thread_id, role, content, created_at) VALUES (?, ?, ?, ?)",
                (thread_id, role, content, datetime.now().isoformat())
            )
    finally:
        conn.close()

def get_messages(thread_id: str):
    """Retrieve all messages for a thread, sorted by time/id ascending."""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT role, content, created_at FROM messages WHERE thread_id = ? ORDER BY id ASC",
            (thread_id,)
        )
        return [dict(row) for row in cursor.fetchall()]
    finally:
        conn.close()
