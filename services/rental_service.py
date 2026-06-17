from datetime import datetime
from database.db_manager import DatabaseManager
from models.rental import RentalOrder, Customer
from models.equipment import EquipmentItem
from services.billing_service import BillingService
from services.equipment_service import EquipmentService
from utils.helpers import generate_order_no, parse_datetime


class RentalOrderItem:
    @staticmethod
    def add_items(order_id, item_ids):
        db = DatabaseManager()
        for item_id in item_ids:
            db.execute("""
                INSERT INTO rental_order_items (order_id, item_id) VALUES (?, ?)
            """, (order_id, item_id))

    @staticmethod
    def get_items(order_id):
        db = DatabaseManager()
        rows = db.query("""
            SELECT oi.*, i.item_code, i.status, i.batch_id, b.batch_no, b.expire_date,
                   t.type_name, t.type_code
            FROM rental_order_items oi
            JOIN equipment_items i ON oi.item_id = i.id
            JOIN equipment_batches b ON i.batch_id = b.id
            JOIN equipment_types t ON i.type_id = t.id
            WHERE oi.order_id = ?
            ORDER BY oi.id
        """, (order_id,))
        return [dict(r) for r in rows]

    @staticmethod
    def get_item_count(order_id):
        db = DatabaseManager()
        row = db.query_one("SELECT COUNT(*) as cnt FROM rental_order_items WHERE order_id = ?", (order_id,))
        return row["cnt"] if row else 0


class RentalService:

    @staticmethod
    def get_all_orders():
        orders = RentalOrder.get_all_with_info()
        for o in orders:
            o["item_count"] = RentalOrderItem.get_item_count(o["id"])
        return orders

    @staticmethod
    def get_active_orders():
        orders = RentalOrder.get_active_with_info()
        for o in orders:
            o["item_count"] = RentalOrderItem.get_item_count(o["id"])
        return orders

    @staticmethod
    def get_all_customers():
        return Customer.get_all()

    @staticmethod
    def create_customer(name, phone="", id_card=""):
        return Customer.create(name, phone, id_card)

    @staticmethod
    def create_rental(customer_id, type_id, rent_start_str, rent_end_str, quantity=1, deposit=0.0):
        available_count = EquipmentService.get_available_count_by_type(type_id)
        if available_count < quantity:
            return None, f"库存不足，可用数量：{available_count}台，需要：{quantity}台"
        fifo_items = EquipmentService.get_fifo_items(type_id, count=quantity)
        if len(fifo_items) < quantity:
            return None, f"可租出设备不足，实际只有{len(fifo_items)}台可用"
        order_no = generate_order_no()
        first_item = fifo_items[0]
        order_id = RentalOrder.create(
            order_no=order_no,
            customer_id=customer_id,
            item_id=first_item["id"],
            type_id=type_id,
            rent_start=rent_start_str,
            rent_end=rent_end_str,
            deposit=deposit
        )
        item_ids = [item["id"] for item in fifo_items]
        RentalOrderItem.add_items(order_id, item_ids)
        for item_id in item_ids:
            EquipmentService.mark_item_rented(item_id)
        bill_result = BillingService.calculate_rental_cost(rent_start_str, rent_end_str)
        base_amount = round(bill_result["base_amount"] * quantity, 2)
        order = RentalOrder.get_by_id(order_id)
        order.update_amounts(
            base_amount=base_amount,
            overtime_amount=0.0,
            total_amount=base_amount
        )
        segments_multiplied = []
        for seg in bill_result["segments"]:
            new_seg = dict(seg)
            new_seg["segment_amount"] = round(seg["segment_amount"] * quantity, 2)
            new_seg["hours"] = seg["hours"]
            segments_multiplied.append(new_seg)
        BillingService.save_bill_details(order_id, segments_multiplied)
        return order_id, order_no

    @staticmethod
    def return_equipment(order_id, actual_return_str=None):
        if not actual_return_str:
            actual_return_str = str(datetime.now())
        order = RentalOrder.get_by_id(order_id)
        if not order or order.status == "closed":
            return None, "订单不存在或已归还"
        items = RentalOrderItem.get_items(order_id)
        quantity = len(items) if items else 1
        bill_result = BillingService.calculate_full_bill(
            order.rent_start,
            order.rent_end,
            actual_return_str
        )
        base_amount = round(bill_result["base_amount"] * quantity, 2)
        overtime_amount = round(bill_result["overtime_amount"] * quantity, 2)
        total = round(base_amount + overtime_amount, 2)
        order.update_amounts(
            base_amount=base_amount,
            overtime_amount=overtime_amount,
            total_amount=total
        )
        segments_multiplied = []
        for seg in bill_result["segments"]:
            new_seg = dict(seg)
            new_seg["segment_amount"] = round(seg["segment_amount"] * quantity, 2)
            segments_multiplied.append(new_seg)
        BillingService.save_bill_details(order_id, segments_multiplied)
        order.close(actual_return_str)
        for item in items:
            EquipmentService.mark_item_returned(item["item_id"])
        result = {
            "base_amount": base_amount,
            "overtime_amount": overtime_amount,
            "total": total,
            "total_hours": bill_result.get("total_hours", 0),
            "overtime_hours": bill_result.get("overtime_hours", 0),
            "quantity": quantity
        }
        return result, None

    @staticmethod
    def get_order_bill(order_id):
        order = RentalOrder.get_by_id(order_id)
        if not order:
            return None
        items = RentalOrderItem.get_items(order_id)
        quantity = len(items) if items else 1
        segments = BillingService.get_order_bill_details(order_id)
        if order.status == "closed" and order.actual_return:
            bill_result = BillingService.calculate_full_bill(
                order.rent_start,
                order.rent_end,
                order.actual_return
            )
        else:
            bill_result = BillingService.calculate_rental_cost(
                order.rent_start,
                order.rent_end
            )
        return {
            "order": order,
            "items": items,
            "quantity": quantity,
            "segments": segments if segments else bill_result["segments"],
            "base_amount": order.base_amount,
            "overtime_amount": order.overtime_amount,
            "total_amount": order.total_amount,
            "total_hours": bill_result.get("total_hours", 0),
            "overtime_hours": bill_result.get("overtime_hours", 0)
        }

    @staticmethod
    def get_order_items(order_id):
        return RentalOrderItem.get_items(order_id)

    @staticmethod
    def pay_order(order_id, amount):
        order = RentalOrder.get_by_id(order_id)
        if not order:
            return False, "订单不存在"
        if amount <= 0:
            return False, "支付金额必须大于0"
        unpaid = order.total_amount - order.paid_amount
        if unpaid <= 0:
            return False, "该订单已结清，无需再支付"
        if amount > unpaid:
            amount = unpaid
        order.pay(amount)
        return True, f"支付成功 ¥{amount:.2f}"

    @staticmethod
    def check_overdue_orders():
        active = RentalService.get_active_orders()
        now = datetime.now()
        overdue = []
        for o in active:
            rent_end = parse_datetime(o["rent_end"])
            if rent_end and rent_end < now:
                hours_overdue = round((now - rent_end).total_seconds() / 3600, 1)
                o["hours_overdue"] = hours_overdue
                overdue.append(o)
        return overdue
