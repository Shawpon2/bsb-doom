import sqlite3
import time
import os
from pathlib import Path
from ..config import DB_PATH
from ..utils.machine import get_machine_id

class DatabaseManager:
    def __init__(self):
        db_path = Path(DB_PATH).expanduser()
        db_path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(str(db_path), check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self.cursor = self.conn.cursor()
        self._create_tables()
        # Enable WAL mode for better concurrency
        self.cursor.execute('PRAGMA journal_mode=WAL')

    def _create_tables(self):
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                machine_id TEXT PRIMARY KEY,
                first_seen INTEGER,
                last_seen INTEGER,
                ip_address TEXT,
                blocked INTEGER DEFAULT 0
            )
        ''')
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS tests (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                machine_id TEXT,
                target TEXT,
                start_time INTEGER,
                end_time INTEGER,
                status TEXT,
                load_at_failure INTEGER,
                duration INTEGER,
                rps_peak REAL,
                error_rate REAL,
                avg_latency REAL,
                p95_latency REAL,
                FOREIGN KEY(machine_id) REFERENCES users(machine_id)
            )
        ''')
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS active_sessions (
                machine_id TEXT PRIMARY KEY,
                target TEXT,
                start_time INTEGER,
                pid INTEGER
            )
        ''')
        self.conn.commit()

    def register_user(self):
        mid = get_machine_id()
        now = int(time.time())
        # IP not used, set placeholder
        self.cursor.execute('''
            INSERT INTO users (machine_id, first_seen, last_seen, ip_address)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(machine_id) DO UPDATE SET last_seen=excluded.last_seen
        ''', (mid, now, now, "0.0.0.0"))
        self.conn.commit()
        return mid

    def is_blocked(self, machine_id):
        self.cursor.execute('SELECT blocked FROM users WHERE machine_id = ?', (machine_id,))
        row = self.cursor.fetchone()
        return row and row['blocked'] == 1

    def add_test(self, machine_id, target, status, load_at_failure, duration,
                 rps_peak=0, error_rate=0.0, avg_latency=0.0, p95_latency=0.0):
        now = int(time.time())
        self.cursor.execute('''
            INSERT INTO tests (machine_id, target, start_time, end_time, status, load_at_failure,
                               duration, rps_peak, error_rate, avg_latency, p95_latency)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (machine_id, target, now-duration, now, status, load_at_failure,
              duration, rps_peak, error_rate, avg_latency, p95_latency))
        self.conn.commit()

    def start_session(self, machine_id, target, pid):
        now = int(time.time())
        self.cursor.execute('''
            INSERT OR REPLACE INTO active_sessions (machine_id, target, start_time, pid)
            VALUES (?, ?, ?, ?)
        ''', (machine_id, target, now, pid))
        self.conn.commit()

    def end_session(self, machine_id):
        self.cursor.execute('DELETE FROM active_sessions WHERE machine_id = ?', (machine_id,))
        self.conn.commit()

    def get_active_sessions(self):
        self.cursor.execute('SELECT machine_id, target, start_time, pid FROM active_sessions')
        return [dict(row) for row in self.cursor.fetchall()]

    # Admin methods
    def get_total_users(self):
        self.cursor.execute('SELECT COUNT(*) FROM users')
        return self.cursor.fetchone()[0]

    def get_active_users(self, since_seconds=86400):
        cutoff = int(time.time()) - since_seconds
        self.cursor.execute('SELECT machine_id, last_seen FROM users WHERE last_seen > ?', (cutoff,))
        return self.cursor.fetchall()

    def get_all_users(self):
        self.cursor.execute('SELECT machine_id, first_seen, last_seen, blocked FROM users')
        return self.cursor.fetchall()

    def get_test_history(self, limit=100):
        self.cursor.execute('''
            SELECT target, start_time, status, load_at_failure, duration,
                   rps_peak, error_rate, avg_latency, p95_latency
            FROM tests ORDER BY start_time DESC LIMIT ?
        ''', (limit,))
        return self.cursor.fetchall()

    def block_user(self, machine_id):
        self.cursor.execute('UPDATE users SET blocked = 1 WHERE machine_id = ?', (machine_id,))
        self.conn.commit()

    def unblock_user(self, machine_id):
        self.cursor.execute('UPDATE users SET blocked = 0 WHERE machine_id = ?', (machine_id,))
        self.conn.commit()

    def get_blocked_users(self):
        self.cursor.execute('SELECT machine_id, first_seen, last_seen FROM users WHERE blocked = 1')
        return self.cursor.fetchall()

    def close(self):
        self.conn.close()
