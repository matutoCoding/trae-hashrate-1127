from datetime import date, datetime, timedelta
from database.db_manager import DatabaseManager


class EquipmentType:
    def __init__(self, id=None, type_code="", type_name="", description="", warn_days=30):
        self.id = id
        self.type_code = type_code
        self.type_name = type_name
        self.description = description
        self.warn_days = warn_days

    @staticmethod
    def get_all():
        db = DatabaseManager()
        rows = db.query("SELECT * FROM equipment_types ORDER BY type_code")
        return [EquipmentType(**dict(r)) for r in rows]

    @staticmethod
    def get_by_id(type_id):
        db = DatabaseManager()
        row = db.query_one("SELECT * FROM equipment_types WHERE id = ?", (type_id,))
        return EquipmentType(**dict(row)) if row else None

    @staticmethod
    def create(type_code, type_name, description="", warn_days=30):
        db = DatabaseManager()
        cursor = db.execute("""
            INSERT INTO equipment_types (type_code, type_name, description, warn_days)
            VALUES (?, ?, ?, ?)
        """, (type_code, type_name, description, warn_days))
        return cursor.lastrowid

    def save(self):
        db = DatabaseManager()
        db.execute("""
            UPDATE equipment_types SET type_code=?, type_name=?, description=?, warn_days=?
            WHERE id=?
        """, (self.type_code, self.type_name, self.description, self.warn_days, self.id))

    @staticmethod
    def delete(type_id):
        db = DatabaseManager()
        db.execute("""
            DELETE FROM equipment_items WHERE type_id = ?
        """, (type_id,))
        db.execute("""
            DELETE FROM equipment_batches WHERE type_id = ?
        """, (type_id,))
        db.execute("DELETE FROM equipment_types WHERE id = ?", (type_id,))

    @staticmethod
    def check_delete_allowed(type_id):
        db = DatabaseManager()
        batches = db.query_one("SELECT COUNT(*) as cnt FROM equipment_batches WHERE type_id = ?", (type_id,))
        items = db.query_one("SELECT COUNT(*) as cnt FROM equipment_items WHERE type_id = ?", (type_id,))
        orders = db.query_one("SELECT COUNT(*) as cnt FROM rental_orders WHERE type_id = ?", (type_id,))
        errors = []
        batch_count = batches["cnt"] if batches else 0
        item_count = items["cnt"] if items else 0
        order_count = orders["cnt"] if orders else 0
        if batch_count > 0:
            errors.append(f"{batch_count} 个设备批次")
        if item_count > 0:
            errors.append(f"{item_count} 台设备")
        if order_count > 0:
            errors.append(f"{order_count} 个租赁订单")
        if errors:
            return False, "该设备类型已被以下数据占用，无法删除：\n- " + "\n- ".join(errors) + "\n\n请先清空相关数据后再删除。"
        return True, ""


class EquipmentBatch:
    def __init__(self, id=None, batch_no="", type_id=0, quantity=0, expire_date="", in_date="", remark=""):
        self.id = id
        self.batch_no = batch_no
        self.type_id = type_id
        self.quantity = quantity
        self.expire_date = expire_date
        self.in_date = in_date
        self.remark = remark

    @staticmethod
    def get_all_with_info():
        db = DatabaseManager()
        rows = db.query("""
            SELECT b.*, t.type_name, t.type_code, t.warn_days
            FROM equipment_batches b
            JOIN equipment_types t ON b.type_id = t.id
            ORDER BY b.in_date ASC, b.id ASC
        """)
        return [dict(r) for r in rows]

    @staticmethod
    def get_by_id(batch_id):
        db = DatabaseManager()
        row = db.query_one("SELECT * FROM equipment_batches WHERE id = ?", (batch_id,))
        return EquipmentBatch(**dict(row)) if row else None

    @staticmethod
    def get_fifo_for_type(type_id):
        db = DatabaseManager()
        today = date.today()
        rows = db.query("""
            SELECT b.*, 
                   (SELECT COUNT(*) FROM equipment_items i 
                    WHERE i.batch_id = b.id AND i.status = 'available') as available_count
            FROM equipment_batches b
            WHERE b.type_id = ?
            ORDER BY b.in_date ASC, b.expire_date ASC, b.id ASC
        """, (type_id,))
        return [dict(r) for r in rows]

    @staticmethod
    def create(batch_no, type_id, quantity, expire_date, in_date, remark=""):
        db = DatabaseManager()
        today = date.today()
        cursor = db.execute("""
            INSERT INTO equipment_batches (batch_no, type_id, quantity, expire_date, in_date, remark)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (batch_no, type_id, quantity, expire_date, in_date, remark))
        batch_id = cursor.lastrowid
        for i in range(quantity):
            item_code = f"{batch_no}-{str(i+1).zfill(3)}"
            expire_dt = datetime.strptime(expire_date, "%Y-%m-%d").date()
            status = "available" if expire_dt >= today else "expired"
            db.execute("""
                INSERT INTO equipment_items (item_code, batch_id, type_id, status)
                VALUES (?, ?, ?, ?)
            """, (item_code, batch_id, type_id, status))
        return batch_id

    @staticmethod
    def delete(batch_id):
        db = DatabaseManager()
        db.execute("DELETE FROM equipment_items WHERE batch_id = ?", (batch_id,))
        db.execute("DELETE FROM equipment_batches WHERE id = ?", (batch_id,))

    @staticmethod
    def check_delete_allowed(batch_id):
        db = DatabaseManager()
        items = db.query_one("SELECT COUNT(*) as cnt FROM equipment_items WHERE batch_id = ?", (batch_id,))
        orders = db.query_one("""
            SELECT COUNT(*) as cnt FROM rental_orders o
            JOIN equipment_items i ON o.item_id = i.id
            WHERE i.batch_id = ?
        """, (batch_id,))
        errors = []
        item_count = items["cnt"] if items else 0
        order_count = orders["cnt"] if orders else 0
        if item_count > 0:
            errors.append(f"{item_count} 台设备")
        if order_count > 0:
            errors.append(f"{order_count} 个租赁订单")
        if errors:
            return False, "该批次已被以下数据占用，无法删除：\n- " + "\n- ".join(errors) + "\n\n请先清空相关数据后再删除。"
        return True, ""

    def get_expire_status(self):
        db = DatabaseManager()
        today = date.today()
        expire_dt = datetime.strptime(self.expire_date, "%Y-%m-%d").date()
        days_left = (expire_dt - today).days
        type_info = db.query_one("SELECT warn_days FROM equipment_types WHERE id = ?", (self.type_id,))
        warn_days = type_info["warn_days"] if type_info else 30
        if days_left < 0:
            return "expired", days_left
        elif days_left <= warn_days:
            return "warning", days_left
        else:
            return "normal", days_left


class EquipmentItem:
    def __init__(self, id=None, item_code="", batch_id=0, type_id=0, status="available"):
        self.id = id
        self.item_code = item_code
        self.batch_id = batch_id
        self.type_id = type_id
        self.status = status

    @staticmethod
    def get_all_with_info():
        db = DatabaseManager()
        rows = db.query("""
            SELECT i.*, b.batch_no, b.expire_date, t.type_name, t.type_code
            FROM equipment_items i
            JOIN equipment_batches b ON i.batch_id = b.id
            JOIN equipment_types t ON i.type_id = t.id
            ORDER BY b.in_date ASC, i.id ASC
        """)
        return [dict(r) for r in rows]

    @staticmethod
    def get_available_by_type_fifo(type_id, limit=1):
        db = DatabaseManager()
        today = date.today()
        rows = db.query("""
            SELECT i.*, b.batch_no, b.expire_date, t.type_name
            FROM equipment_items i
            JOIN equipment_batches b ON i.batch_id = b.id
            JOIN equipment_types t ON i.type_id = t.id
            WHERE i.type_id = ? AND i.status = 'available' AND b.expire_date >= ?
            ORDER BY b.in_date ASC, b.expire_date ASC, i.id ASC
            LIMIT ?
        """, (type_id, str(today), limit))
        return [dict(r) for r in rows]

    @staticmethod
    def get_by_id(item_id):
        db = DatabaseManager()
        row = db.query_one("SELECT * FROM equipment_items WHERE id = ?", (item_id,))
        return EquipmentItem(**dict(row)) if row else None

    def update_status(self, new_status):
        db = DatabaseManager()
        db.execute("UPDATE equipment_items SET status = ? WHERE id = ?", (new_status, self.id))

    @staticmethod
    def get_by_code(item_code):
        db = DatabaseManager()
        row = db.query_one("SELECT * FROM equipment_items WHERE item_code = ?", (item_code,))
        return EquipmentItem(**dict(row)) if row else None
