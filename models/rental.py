from datetime import datetime
from database.db_manager import DatabaseManager


class Customer:
    def __init__(self, id=None, customer_name="", phone="", id_card="", create_time=""):
        self.id = id
        self.customer_name = customer_name
        self.phone = phone
        self.id_card = id_card
        self.create_time = create_time

    @staticmethod
    def get_all():
        db = DatabaseManager()
        rows = db.query("SELECT * FROM customers ORDER BY create_time DESC")
        return [Customer(**dict(r)) for r in rows]

    @staticmethod
    def get_by_id(customer_id):
        db = DatabaseManager()
        row = db.query_one("SELECT * FROM customers WHERE id = ?", (customer_id,))
        return Customer(**dict(row)) if row else None

    @staticmethod
    def create(customer_name, phone="", id_card=""):
        db = DatabaseManager()
        cursor = db.execute("""
            INSERT INTO customers (customer_name, phone, id_card, create_time)
            VALUES (?, ?, ?, ?)
        """, (customer_name, phone, id_card, str(datetime.now())))
        return cursor.lastrowid

    def save(self):
        db = DatabaseManager()
        db.execute("""
            UPDATE customers SET customer_name=?, phone=?, id_card=? WHERE id=?
        """, (self.customer_name, self.phone, self.id_card, self.id))


class RentalOrder:
    def __init__(self, id=None, order_no="", customer_id=None, item_id=0, type_id=0,
                 rent_start="", rent_end=None, actual_return=None, deposit=0.0,
                 base_amount=0.0, overtime_amount=0.0, total_amount=0.0,
                 paid_amount=0.0, status="active", create_time=""):
        self.id = id
        self.order_no = order_no
        self.customer_id = customer_id
        self.item_id = item_id
        self.type_id = type_id
        self.rent_start = rent_start
        self.rent_end = rent_end
        self.actual_return = actual_return
        self.deposit = deposit
        self.base_amount = base_amount
        self.overtime_amount = overtime_amount
        self.total_amount = total_amount
        self.paid_amount = paid_amount
        self.status = status
        self.create_time = create_time

    @staticmethod
    def get_all_with_info():
        db = DatabaseManager()
        rows = db.query("""
            SELECT o.*, c.customer_name, c.phone, i.item_code, 
                   t.type_name, b.batch_no, b.expire_date
            FROM rental_orders o
            LEFT JOIN customers c ON o.customer_id = c.id
            JOIN equipment_items i ON o.item_id = i.id
            JOIN equipment_types t ON o.type_id = t.id
            JOIN equipment_batches b ON i.batch_id = b.id
            ORDER BY o.create_time DESC
        """)
        return [dict(r) for r in rows]

    @staticmethod
    def get_active_with_info():
        db = DatabaseManager()
        rows = db.query("""
            SELECT o.*, c.customer_name, c.phone, i.item_code, 
                   t.type_name, b.batch_no, b.expire_date
            FROM rental_orders o
            LEFT JOIN customers c ON o.customer_id = c.id
            JOIN equipment_items i ON o.item_id = i.id
            JOIN equipment_types t ON o.type_id = t.id
            JOIN equipment_batches b ON i.batch_id = b.id
            WHERE o.status = 'active'
            ORDER BY o.create_time DESC
        """)
        return [dict(r) for r in rows]

    @staticmethod
    def get_by_id(order_id):
        db = DatabaseManager()
        row = db.query_one("SELECT * FROM rental_orders WHERE id = ?", (order_id,))
        return RentalOrder(**dict(row)) if row else None

    @staticmethod
    def get_by_order_no(order_no):
        db = DatabaseManager()
        row = db.query_one("SELECT * FROM rental_orders WHERE order_no = ?", (order_no,))
        return RentalOrder(**dict(row)) if row else None

    @staticmethod
    def create(order_no, customer_id, item_id, type_id, rent_start, rent_end, deposit=0.0):
        db = DatabaseManager()
        cursor = db.execute("""
            INSERT INTO rental_orders (order_no, customer_id, item_id, type_id, rent_start, rent_end, deposit, create_time)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (order_no, customer_id, item_id, type_id, rent_start, rent_end, deposit, str(datetime.now())))
        return cursor.lastrowid

    def update_amounts(self, base_amount, overtime_amount, total_amount):
        db = DatabaseManager()
        db.execute("""
            UPDATE rental_orders SET base_amount=?, overtime_amount=?, total_amount=?
            WHERE id=?
        """, (base_amount, overtime_amount, total_amount, self.id))
        self.base_amount = base_amount
        self.overtime_amount = overtime_amount
        self.total_amount = total_amount

    def close(self, actual_return_time):
        db = DatabaseManager()
        db.execute("""
            UPDATE rental_orders SET actual_return=?, status='closed' WHERE id=?
        """, (actual_return_time, self.id))

    def pay(self, amount):
        db = DatabaseManager()
        new_paid = self.paid_amount + amount
        db.execute("UPDATE rental_orders SET paid_amount=? WHERE id=?", (new_paid, self.id))
        self.paid_amount = new_paid


class BillDetail:
    def __init__(self, id=None, order_id=0, segment_start="", segment_end="",
                 hours=0.0, rate=0.0, rate_name="", segment_amount=0.0):
        self.id = id
        self.order_id = order_id
        self.segment_start = segment_start
        self.segment_end = segment_end
        self.hours = hours
        self.rate = rate
        self.rate_name = rate_name
        self.segment_amount = segment_amount

    @staticmethod
    def get_by_order(order_id):
        db = DatabaseManager()
        rows = db.query("SELECT * FROM bill_details WHERE order_id = ? ORDER BY id", (order_id,))
        return [BillDetail(**dict(r)) for r in rows]

    @staticmethod
    def create(order_id, segment_start, segment_end, hours, rate, rate_name, segment_amount):
        db = DatabaseManager()
        cursor = db.execute("""
            INSERT INTO bill_details (order_id, segment_start, segment_end, hours, rate, rate_name, segment_amount)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (order_id, segment_start, segment_end, hours, rate, rate_name, segment_amount))
        return cursor.lastrowid

    @staticmethod
    def clear_by_order(order_id):
        db = DatabaseManager()
        db.execute("DELETE FROM bill_details WHERE order_id = ?", (order_id,))
