from datetime import datetime
from models.rental import RentalOrder, Customer
from models.equipment import EquipmentItem
from services.billing_service import BillingService
from services.equipment_service import EquipmentService
from utils.helpers import generate_order_no, parse_datetime


class RentalService:

    @staticmethod
    def get_all_orders():
        return RentalOrder.get_all_with_info()

    @staticmethod
    def get_active_orders():
        return RentalOrder.get_active_with_info()

    @staticmethod
    def get_all_customers():
        return Customer.get_all()

    @staticmethod
    def create_customer(name, phone="", id_card=""):
        return Customer.create(name, phone, id_card)

    @staticmethod
    def create_rental(customer_id, type_id, rent_start_str, rent_end_str, deposit=0.0):
        available_count = EquipmentService.get_available_count_by_type(type_id)
        if available_count <= 0:
            return None, "该类型设备无可用库存"
        fifo_item = EquipmentService.get_next_fifo_item(type_id)
        if not fifo_item:
            return None, "没有可租出的设备（可能已过期）"
        order_no = generate_order_no()
        order_id = RentalOrder.create(
            order_no=order_no,
            customer_id=customer_id,
            item_id=fifo_item["id"],
            type_id=type_id,
            rent_start=rent_start_str,
            rent_end=rent_end_str,
            deposit=deposit
        )
        EquipmentService.mark_item_rented(fifo_item["id"])
        bill_result = BillingService.calculate_rental_cost(rent_start_str, rent_end_str)
        order = RentalOrder.get_by_id(order_id)
        order.update_amounts(
            base_amount=bill_result["base_amount"],
            overtime_amount=0.0,
            total_amount=bill_result["base_amount"]
        )
        BillingService.save_bill_details(order_id, bill_result["segments"])
        return order_id, order_no

    @staticmethod
    def return_equipment(order_id, actual_return_str=None):
        if not actual_return_str:
            actual_return_str = str(datetime.now())
        order = RentalOrder.get_by_id(order_id)
        if not order or order.status == "closed":
            return None, "订单不存在或已归还"
        bill_result = BillingService.calculate_full_bill(
            order.rent_start,
            order.rent_end,
            actual_return_str
        )
        order.update_amounts(
            base_amount=bill_result["base_amount"],
            overtime_amount=bill_result["overtime_amount"],
            total_amount=bill_result["total"]
        )
        BillingService.save_bill_details(order_id, bill_result["segments"])
        order.close(actual_return_str)
        EquipmentService.mark_item_returned(order.item_id)
        return bill_result, None

    @staticmethod
    def get_order_bill(order_id):
        order = RentalOrder.get_by_id(order_id)
        if not order:
            return None
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
            "segments": segments if segments else bill_result["segments"],
            "base_amount": order.base_amount,
            "overtime_amount": order.overtime_amount,
            "total_amount": order.total_amount,
            "total_hours": bill_result.get("total_hours", 0),
            "overtime_hours": bill_result.get("overtime_hours", 0)
        }

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
        active = RentalOrder.get_active_with_info()
        now = datetime.now()
        overdue = []
        for o in active:
            rent_end = parse_datetime(o["rent_end"])
            if rent_end and rent_end < now:
                hours_overdue = round((now - rent_end).total_seconds() / 3600, 1)
                o["hours_overdue"] = hours_overdue
                overdue.append(o)
        return overdue
