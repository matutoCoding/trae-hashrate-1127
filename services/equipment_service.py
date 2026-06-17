from datetime import date, datetime
from database.db_manager import DatabaseManager
from models.equipment import EquipmentType, EquipmentBatch, EquipmentItem
from models.rental import RentalOrder
from utils.helpers import parse_date, format_date, generate_batch_no


class EquipmentService:

    @staticmethod
    def get_all_types():
        return EquipmentType.get_all()

    @staticmethod
    def get_all_batches_with_status():
        batches = EquipmentBatch.get_all_with_info()
        today = date.today()
        result = []
        for b in batches:
            expire_dt = parse_date(b["expire_date"])
            days_left = (expire_dt - today).days if expire_dt else 0
            warn_days = b.get("warn_days", 30)
            if days_left < 0:
                status = "expired"
                status_text = "已过期"
            elif days_left <= warn_days:
                status = "warning"
                status_text = f"临期({days_left}天)"
            else:
                status = "normal"
                status_text = "正常"
            db = DatabaseManager()
            available = db.query_one("""
                SELECT COUNT(*) as cnt FROM equipment_items 
                WHERE batch_id = ? AND status = 'available'
            """, (b["id"],))
            rented = db.query_one("""
                SELECT COUNT(*) as cnt FROM equipment_items 
                WHERE batch_id = ? AND status = 'rented'
            """, (b["id"],))
            expired_count = db.query_one("""
                SELECT COUNT(*) as cnt FROM equipment_items 
                WHERE batch_id = ? AND status = 'expired'
            """, (b["id"],))
            b["status"] = status
            b["status_text"] = status_text
            b["days_left"] = days_left
            b["available_count"] = available["cnt"] if available else 0
            b["rented_count"] = rented["cnt"] if rented else 0
            b["expired_count"] = expired_count["cnt"] if expired_count else 0
            result.append(b)
        return result

    @staticmethod
    def get_all_items_with_status():
        items = EquipmentItem.get_all_with_info()
        today = date.today()
        result = []
        for it in items:
            expire_dt = parse_date(it["expire_date"])
            days_left = (expire_dt - today).days if expire_dt else 0
            status = it["status"]
            if status == "available" and days_left < 0:
                EquipmentItem.get_by_id(it["id"]).update_status("expired")
                status = "expired"
            status_map = {
                "available": "可租",
                "rented": "已租",
                "expired": "已过期",
                "lost": "盘亏"
            }
            it["status_text"] = status_map.get(status, status)
            it["days_left"] = days_left
            result.append(it)
        return result

    @staticmethod
    def get_warning_batches():
        batches = EquipmentService.get_all_batches_with_status()
        return [b for b in batches if b["status"] in ("warning", "expired")]

    @staticmethod
    def get_expired_items_count():
        items = EquipmentService.get_all_items_with_status()
        return len([i for i in items if i["status"] == "expired"])

    @staticmethod
    def get_available_count_by_type(type_id):
        today = date.today()
        db = DatabaseManager()
        row = db.query_one("""
            SELECT COUNT(*) as cnt FROM equipment_items i
            JOIN equipment_batches b ON i.batch_id = b.id
            WHERE i.type_id = ? AND i.status = 'available' AND b.expire_date >= ?
        """, (type_id, str(today)))
        return row["cnt"] if row else 0

    @staticmethod
    def get_next_fifo_item(type_id):
        items = EquipmentItem.get_available_by_type_fifo(type_id, limit=1)
        return items[0] if items else None

    @staticmethod
    def get_fifo_items(type_id, count=1):
        return EquipmentItem.get_available_by_type_fifo(type_id, limit=count)

    @staticmethod
    def mark_item_rented(item_id):
        item = EquipmentItem.get_by_id(item_id)
        if item and item.status == "available":
            item.update_status("rented")
            return True
        return False

    @staticmethod
    def mark_item_returned(item_id):
        db = DatabaseManager()
        today = date.today()
        item = EquipmentItem.get_by_id(item_id)
        if not item:
            return False
        batch = db.query_one("SELECT expire_date FROM equipment_batches WHERE id = ?", (item.batch_id,))
        expire_dt = parse_date(batch["expire_date"]) if batch else None
        if expire_dt and expire_dt < today:
            item.update_status("expired")
        else:
            item.update_status("available")
        return True

    @staticmethod
    def create_type(type_code, type_name, description="", warn_days=30):
        return EquipmentType.create(type_code, type_name, description, warn_days)

    @staticmethod
    def create_batch(type_id, quantity, expire_date, in_date=None, remark="", batch_no=None):
        if not batch_no:
            batch_no = generate_batch_no()
        if not in_date:
            in_date = format_date(date.today())
        return EquipmentBatch.create(batch_no, type_id, quantity, expire_date, in_date, remark)

    @staticmethod
    def check_and_lock_expired():
        today = date.today()
        db = DatabaseManager()
        expired = db.query("""
            SELECT i.id FROM equipment_items i
            JOIN equipment_batches b ON i.batch_id = b.id
            WHERE i.status = 'available' AND b.expire_date < ?
        """, (str(today),))
        for row in expired:
            EquipmentItem.get_by_id(row["id"]).update_status("expired")
        return len(expired)

    @staticmethod
    def get_type_stats():
        db = DatabaseManager()
        rows = db.query("""
            SELECT t.id, t.type_code, t.type_name,
                   COUNT(DISTINCT i.id) as total,
                   SUM(CASE WHEN i.status = 'available' THEN 1 ELSE 0 END) as available,
                   SUM(CASE WHEN i.status = 'rented' THEN 1 ELSE 0 END) as rented,
                   SUM(CASE WHEN i.status = 'expired' THEN 1 ELSE 0 END) as expired
            FROM equipment_types t
            LEFT JOIN equipment_items i ON t.id = i.type_id
            GROUP BY t.id
            ORDER BY t.type_code
        """)
        return [dict(r) for r in rows]
