import sqlite3
import os
from datetime import datetime, date, timedelta


class DatabaseManager:
    _instance = None
    DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "rental.db")

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance.conn = sqlite3.connect(cls.DB_PATH)
            cls._instance.conn.row_factory = sqlite3.Row
            cls._instance.conn.execute("PRAGMA foreign_keys = ON")
            cls._instance._init_tables()
            cls._instance._seed_demo_data()
        return cls._instance

    def _init_tables(self):
        cursor = self.conn.cursor()
        cursor.executescript("""
            CREATE TABLE IF NOT EXISTS time_rates (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                start_hour INTEGER NOT NULL,
                end_hour INTEGER NOT NULL,
                rate_per_hour REAL NOT NULL,
                is_peak INTEGER DEFAULT 0
            );

            CREATE TABLE IF NOT EXISTS equipment_types (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                type_code TEXT NOT NULL UNIQUE,
                type_name TEXT NOT NULL,
                description TEXT,
                warn_days INTEGER DEFAULT 30
            );

            CREATE TABLE IF NOT EXISTS equipment_batches (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                batch_no TEXT NOT NULL UNIQUE,
                type_id INTEGER NOT NULL,
                quantity INTEGER NOT NULL,
                expire_date TEXT NOT NULL,
                in_date TEXT NOT NULL,
                remark TEXT,
                FOREIGN KEY (type_id) REFERENCES equipment_types(id)
            );

            CREATE TABLE IF NOT EXISTS equipment_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                item_code TEXT NOT NULL UNIQUE,
                batch_id INTEGER NOT NULL,
                type_id INTEGER NOT NULL,
                status TEXT NOT NULL DEFAULT 'available',
                FOREIGN KEY (batch_id) REFERENCES equipment_batches(id),
                FOREIGN KEY (type_id) REFERENCES equipment_types(id)
            );

            CREATE TABLE IF NOT EXISTS customers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                customer_name TEXT NOT NULL,
                phone TEXT,
                id_card TEXT,
                create_time TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS rental_orders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                order_no TEXT NOT NULL UNIQUE,
                customer_id INTEGER,
                item_id INTEGER NOT NULL,
                type_id INTEGER NOT NULL,
                rent_start TEXT NOT NULL,
                rent_end TEXT,
                actual_return TEXT,
                deposit REAL DEFAULT 0,
                base_amount REAL DEFAULT 0,
                overtime_amount REAL DEFAULT 0,
                total_amount REAL DEFAULT 0,
                paid_amount REAL DEFAULT 0,
                status TEXT NOT NULL DEFAULT 'active',
                create_time TEXT NOT NULL,
                FOREIGN KEY (customer_id) REFERENCES customers(id),
                FOREIGN KEY (item_id) REFERENCES equipment_items(id),
                FOREIGN KEY (type_id) REFERENCES equipment_types(id)
            );

            CREATE TABLE IF NOT EXISTS bill_details (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                order_id INTEGER NOT NULL,
                segment_start TEXT NOT NULL,
                segment_end TEXT NOT NULL,
                hours REAL NOT NULL,
                rate REAL NOT NULL,
                rate_name TEXT,
                segment_amount REAL NOT NULL,
                FOREIGN KEY (order_id) REFERENCES rental_orders(id)
            );

            CREATE TABLE IF NOT EXISTS rental_order_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                order_id INTEGER NOT NULL,
                item_id INTEGER NOT NULL,
                daily_rate REAL DEFAULT 0,
                FOREIGN KEY (order_id) REFERENCES rental_orders(id),
                FOREIGN KEY (item_id) REFERENCES equipment_items(id)
            );

            CREATE TABLE IF NOT EXISTS stock_checks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                check_no TEXT NOT NULL UNIQUE,
                check_type TEXT NOT NULL,
                target_id INTEGER,
                check_date TEXT NOT NULL,
                operator TEXT,
                remark TEXT,
                total_system INTEGER DEFAULT 0,
                total_actual INTEGER DEFAULT 0,
                total_profit INTEGER DEFAULT 0,
                total_loss INTEGER DEFAULT 0,
                status TEXT NOT NULL DEFAULT 'draft',
                create_time TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS stock_check_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                check_id INTEGER NOT NULL,
                type_id INTEGER,
                batch_id INTEGER,
                system_qty INTEGER DEFAULT 0,
                actual_qty INTEGER DEFAULT 0,
                profit_qty INTEGER DEFAULT 0,
                loss_qty INTEGER DEFAULT 0,
                remark TEXT,
                FOREIGN KEY (check_id) REFERENCES stock_checks(id)
            );
        """)
        self.conn.commit()

    def _seed_demo_data(self):
        cursor = self.conn.cursor()
        cursor.execute("SELECT COUNT(*) as cnt FROM time_rates")
        if cursor.fetchone()["cnt"] == 0:
            cursor.executemany("""
                INSERT INTO time_rates (name, start_hour, end_hour, rate_per_hour, is_peak)
                VALUES (?, ?, ?, ?, ?)
            """, [
                ("夜间时段", 0, 6, 8.0, 0),
                ("早间时段", 6, 9, 12.0, 0),
                ("白天时段", 9, 18, 20.0, 1),
                ("晚间时段", 18, 24, 15.0, 0),
            ])
        cursor.execute("SELECT COUNT(*) as cnt FROM equipment_types")
        if cursor.fetchone()["cnt"] == 0:
            cursor.executemany("""
                INSERT INTO equipment_types (type_code, type_name, description, warn_days)
                VALUES (?, ?, ?, ?)
            """, [
                ("DRL-001", "电钻", "手持电动钻孔设备", 30),
                ("JCK-001", "脚手架", "建筑施工用脚手架", 60),
                ("WLD-001", "电焊机", "交流弧焊机", 30),
                ("CMP-001", "空压机", "空气压缩机", 45),
            ])
        cursor.execute("SELECT COUNT(*) as cnt FROM equipment_batches")
        if cursor.fetchone()["cnt"] == 0:
            today = date.today()
            batches = [
                ("B202501001", 1, 10, str(today + timedelta(days=365)), str(today - timedelta(days=10))),
                ("B202501002", 1, 5, str(today + timedelta(days=15)), str(today - timedelta(days=5))),
                ("B202501003", 2, 20, str(today + timedelta(days=730)), str(today - timedelta(days=20))),
                ("B202501004", 3, 8, str(today - timedelta(days=5)), str(today - timedelta(days=100))),
                ("B202501005", 4, 6, str(today + timedelta(days=90)), str(today - timedelta(days=30))),
                ("B202501006", 4, 3, str(today + timedelta(days=20)), str(today - timedelta(days=15))),
            ]
            for batch_no, type_id, qty, expire, in_date in batches:
                cursor.execute("""
                    INSERT INTO equipment_batches (batch_no, type_id, quantity, expire_date, in_date)
                    VALUES (?, ?, ?, ?, ?)
                """, (batch_no, type_id, qty, expire, in_date))
                batch_id = cursor.lastrowid
                for i in range(qty):
                    item_code = f"{batch_no}-{str(i+1).zfill(3)}"
                    expire_dt = datetime.strptime(expire, "%Y-%m-%d").date()
                    status = "available" if expire_dt >= today else "expired"
                    cursor.execute("""
                        INSERT INTO equipment_items (item_code, batch_id, type_id, status)
                        VALUES (?, ?, ?, ?)
                    """, (item_code, batch_id, type_id, status))
        cursor.execute("SELECT COUNT(*) as cnt FROM customers")
        if cursor.fetchone()["cnt"] == 0:
            cursor.executemany("""
                INSERT INTO customers (customer_name, phone, id_card, create_time)
                VALUES (?, ?, ?, ?)
            """, [
                ("张三", "13800138001", "110101199001010001", str(datetime.now())),
                ("李四", "13800138002", "110101199002020002", str(datetime.now())),
                ("王五", "13800138003", "110101199003030003", str(datetime.now())),
            ])
        self.conn.commit()

    def execute(self, sql, params=()):
        cursor = self.conn.cursor()
        cursor.execute(sql, params)
        self.conn.commit()
        return cursor

    def query(self, sql, params=()):
        cursor = self.conn.cursor()
        cursor.execute(sql, params)
        return cursor.fetchall()

    def query_one(self, sql, params=()):
        cursor = self.conn.cursor()
        cursor.execute(sql, params)
        return cursor.fetchone()

    def close(self):
        if self.conn:
            self.conn.close()
