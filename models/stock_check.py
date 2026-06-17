from datetime import date, datetime
from database.db_manager import DatabaseManager
from utils.helpers import generate_check_no


class StockCheck:
    def __init__(self, id=None, check_no="", check_type="type", target_id=None,
                 check_date="", operator="", remark="", total_system=0,
                 total_actual=0, total_profit=0, total_loss=0, status="draft", create_time=""):
        self.id = id
        self.check_no = check_no
        self.check_type = check_type
        self.target_id = target_id
        self.check_date = check_date
        self.operator = operator
        self.remark = remark
        self.total_system = total_system
        self.total_actual = total_actual
        self.total_profit = total_profit
        self.total_loss = total_loss
        self.status = status
        self.create_time = create_time

    @staticmethod
    def generate_check_no():
        return generate_check_no()

    @staticmethod
    def get_all():
        db = DatabaseManager()
        rows = db.query("SELECT * FROM stock_checks ORDER BY create_time DESC")
        return [StockCheck(**dict(r)) for r in rows]

    @staticmethod
    def get_by_id(check_id):
        db = DatabaseManager()
        row = db.query_one("SELECT * FROM stock_checks WHERE id = ?", (check_id,))
        return StockCheck(**dict(row)) if row else None

    @staticmethod
    def create(check_type, target_id=None, operator="", remark="", check_date=None):
        db = DatabaseManager()
        check_no = StockCheck.generate_check_no()
        today = check_date if check_date else str(date.today())
        cursor = db.execute("""
            INSERT INTO stock_checks (check_no, check_type, target_id, check_date, operator, remark, create_time)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (check_no, check_type, target_id, today, operator, remark, str(datetime.now())))
        return cursor.lastrowid, check_no

    def save(self):
        db = DatabaseManager()
        db.execute("""
            UPDATE stock_checks SET check_date=?, operator=?, remark=?,
                   total_system=?, total_actual=?, total_profit=?, total_loss=?, status=?
            WHERE id=?
        """, (self.check_date, self.operator, self.remark, self.total_system,
              self.total_actual, self.total_profit, self.total_loss, self.status, self.id))

    def confirm(self):
        self.status = "confirmed"
        self.save()


class StockCheckItem:
    def __init__(self, id=None, check_id=0, type_id=None, batch_id=None,
                 system_qty=0, actual_qty=0, profit_qty=0, loss_qty=0, remark=""):
        self.id = id
        self.check_id = check_id
        self.type_id = type_id
        self.batch_id = batch_id
        self.system_qty = system_qty
        self.actual_qty = actual_qty
        self.profit_qty = profit_qty
        self.loss_qty = loss_qty
        self.remark = remark

    @staticmethod
    def get_by_check(check_id):
        db = DatabaseManager()
        rows = db.query("""
            SELECT ci.*, t.type_name, t.type_code, b.batch_no, b.expire_date
            FROM stock_check_items ci
            LEFT JOIN equipment_types t ON ci.type_id = t.id
            LEFT JOIN equipment_batches b ON ci.batch_id = b.id
            WHERE ci.check_id = ?
            ORDER BY ci.id
        """, (check_id,))
        return [dict(r) for r in rows]

    @staticmethod
    def create(check_id, type_id=None, batch_id=None, system_qty=0, actual_qty=0, remark=""):
        db = DatabaseManager()
        profit = max(0, actual_qty - system_qty)
        loss = max(0, system_qty - actual_qty)
        cursor = db.execute("""
            INSERT INTO stock_check_items (check_id, type_id, batch_id, system_qty, actual_qty, profit_qty, loss_qty, remark)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (check_id, type_id, batch_id, system_qty, actual_qty, profit, loss, remark))
        return cursor.lastrowid

    @staticmethod
    def update(item_id, actual_qty, remark=""):
        db = DatabaseManager()
        item = db.query_one("SELECT * FROM stock_check_items WHERE id = ?", (item_id,))
        if not item:
            return
        profit = max(0, actual_qty - item["system_qty"])
        loss = max(0, item["system_qty"] - actual_qty)
        db.execute("""
            UPDATE stock_check_items SET actual_qty=?, profit_qty=?, loss_qty=?, remark=?
            WHERE id=?
        """, (actual_qty, profit, loss, remark, item_id))

    @staticmethod
    def clear_by_check(check_id):
        db = DatabaseManager()
        db.execute("DELETE FROM stock_check_items WHERE check_id = ?", (check_id,))
