from datetime import date, datetime
from database.db_manager import DatabaseManager
from models.stock_check import StockCheck, StockCheckItem
from models.equipment import EquipmentType, EquipmentBatch, EquipmentItem
from services.equipment_service import EquipmentService


class StockCheckService:

    @staticmethod
    def get_all_checks():
        return StockCheck.get_all()

    @staticmethod
    def get_check_detail(check_id):
        check = StockCheck.get_by_id(check_id)
        if not check:
            return None
        items = StockCheckItem.get_by_check(check_id)
        return {"check": check, "items": items}

    @staticmethod
    def create_type_check(type_id=None, operator="", remark="", check_date=None):
        check_id, check_no = StockCheck.create("type", type_id, operator, remark, check_date)
        if type_id:
            batches = EquipmentBatch.get_fifo_for_type(type_id)
            for b in batches:
                system_qty = b.get("available_count", 0)
                StockCheckItem.create(check_id, type_id=type_id, batch_id=b["id"],
                                      system_qty=system_qty, actual_qty=system_qty)
        else:
            types = EquipmentType.get_all()
            for t in types:
                stats = EquipmentService.get_type_stats()
                for s in stats:
                    if s["id"] == t.id:
                        StockCheckItem.create(check_id, type_id=t.id, batch_id=None,
                                              system_qty=s.get("total", 0),
                                              actual_qty=s.get("total", 0))
                        break
        StockCheckService._recalc_totals(check_id)
        return check_id, check_no

    @staticmethod
    def create_batch_check(batch_id=None, operator="", remark="", check_date=None):
        check_id, check_no = StockCheck.create("batch", batch_id, operator, remark, check_date)
        db = DatabaseManager()
        if batch_id:
            batch = EquipmentBatch.get_by_id(batch_id)
            if batch:
                available = db.query_one("""
                    SELECT COUNT(*) as cnt FROM equipment_items 
                    WHERE batch_id = ? AND status = 'available'
                """, (batch_id,))
                system_qty = available["cnt"] if available else 0
                StockCheckItem.create(check_id, type_id=batch.type_id, batch_id=batch_id,
                                      system_qty=system_qty, actual_qty=system_qty)
        else:
            batches = EquipmentBatch.get_all_with_info()
            for b in batches:
                StockCheckItem.create(check_id, type_id=b.get("type_id"), batch_id=b["id"],
                                      system_qty=b.get("available_count", 0),
                                      actual_qty=b.get("available_count", 0))
        StockCheckService._recalc_totals(check_id)
        return check_id, check_no

    @staticmethod
    def update_item_actual(item_id, actual_qty, remark=""):
        StockCheckItem.update(item_id, actual_qty, remark)
        item = DatabaseManager().query_one("SELECT check_id FROM stock_check_items WHERE id = ?", (item_id,))
        if item:
            StockCheckService._recalc_totals(item["check_id"])

    @staticmethod
    def _recalc_totals(check_id):
        db = DatabaseManager()
        result = db.query_one("""
            SELECT SUM(system_qty) as sys, SUM(actual_qty) as act,
                   SUM(profit_qty) as profit, SUM(loss_qty) as loss
            FROM stock_check_items WHERE check_id = ?
        """, (check_id,))
        if result:
            check = StockCheck.get_by_id(check_id)
            if check:
                check.total_system = result["sys"] or 0
                check.total_actual = result["act"] or 0
                check.total_profit = result["profit"] or 0
                check.total_loss = result["loss"] or 0
                check.save()

    @staticmethod
    def confirm_check(check_id):
        check = StockCheck.get_by_id(check_id)
        if not check or check.status == "confirmed":
            return False, "盘点单不存在或已确认"
        items = StockCheckItem.get_by_check(check_id)
        for item in items:
            StockCheckService._apply_check_item(item)
        check.confirm()
        return True, "盘点确认成功"

    @staticmethod
    def _apply_check_item(item):
        profit_qty = item.get("profit_qty", 0) if isinstance(item, dict) else item.profit_qty
        loss_qty = item.get("loss_qty", 0) if isinstance(item, dict) else item.loss_qty
        type_id = item.get("type_id") if isinstance(item, dict) else item.type_id
        batch_id = item.get("batch_id") if isinstance(item, dict) else item.batch_id
        if profit_qty == 0 and loss_qty == 0:
            return
        db = DatabaseManager()
        if loss_qty > 0:
            sql = """
                SELECT id FROM equipment_items 
                WHERE status = 'available' 
                {type_condition} {batch_condition}
                ORDER BY in_date ASC, expire_date ASC
                LIMIT ?
            """.format(
                type_condition="AND type_id = ?" if type_id else "",
                batch_condition="AND batch_id = ?" if batch_id else ""
            )
            params = []
            if type_id:
                params.append(type_id)
            if batch_id:
                params.append(batch_id)
            params.append(loss_qty)
            rows = db.query(sql, tuple(params))
            for row in rows:
                db.execute("DELETE FROM equipment_items WHERE id = ?", (row["id"],))
        if profit_qty > 0:
            if not batch_id or not type_id:
                return
            batch = EquipmentBatch.get_by_id(batch_id)
            if not batch:
                return
            from utils.helpers import generate_item_code
            expire_date = batch.expire_date if hasattr(batch, 'expire_date') else batch.get('expire_date')
            for i in range(profit_qty):
                item_code = generate_item_code(batch.batch_no if hasattr(batch, 'batch_no') else batch.get('batch_no'))
                db.execute("""
                    INSERT INTO equipment_items (item_code, type_id, batch_id, status, in_date, expire_date)
                    VALUES (?, ?, ?, 'available', DATE('now'), ?)
                """, (item_code, type_id, batch_id, expire_date))

    @staticmethod
    def delete_check(check_id):
        check = StockCheck.get_by_id(check_id)
        if not check:
            return False
        if check.status == "confirmed":
            return False
        db = DatabaseManager()
        db.execute("DELETE FROM stock_check_items WHERE check_id = ?", (check_id,))
        db.execute("DELETE FROM stock_checks WHERE id = ?", (check_id,))
        return True
