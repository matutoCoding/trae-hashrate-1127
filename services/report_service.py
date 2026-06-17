from datetime import datetime
from database.db_manager import DatabaseManager
import csv
import os


class ReportService:

    @staticmethod
    def get_summary_by_date(start_date, end_date):
        db = DatabaseManager()
        rows = db.query("""
            SELECT 
                DATE(create_time) as order_date,
                COUNT(*) as order_count,
                SUM(base_amount) as base_total,
                SUM(overtime_amount) as overtime_total,
                SUM(total_amount) as total_amount,
                SUM(paid_amount) as paid_total,
                SUM(total_amount - paid_amount) as unpaid_total
            FROM rental_orders
            WHERE DATE(create_time) BETWEEN ? AND ?
            GROUP BY DATE(create_time)
            ORDER BY order_date
        """, (start_date, end_date))
        return [dict(r) for r in rows]

    @staticmethod
    def get_summary_by_type(start_date, end_date):
        db = DatabaseManager()
        rows = db.query("""
            SELECT 
                t.id as type_id,
                t.type_code,
                t.type_name,
                COUNT(o.id) as order_count,
                SUM(o.base_amount) as base_total,
                SUM(o.overtime_amount) as overtime_total,
                SUM(o.total_amount) as total_amount,
                SUM(o.paid_amount) as paid_total,
                SUM(o.total_amount - o.paid_amount) as unpaid_total
            FROM rental_orders o
            JOIN equipment_types t ON o.type_id = t.id
            WHERE DATE(o.create_time) BETWEEN ? AND ?
            GROUP BY t.id
            ORDER BY t.type_code
        """, (start_date, end_date))
        return [dict(r) for r in rows]

    @staticmethod
    def get_summary_by_customer(start_date, end_date):
        db = DatabaseManager()
        rows = db.query("""
            SELECT 
                c.id as customer_id,
                c.customer_name,
                c.phone,
                COUNT(o.id) as order_count,
                SUM(o.base_amount) as base_total,
                SUM(o.overtime_amount) as overtime_total,
                SUM(o.total_amount) as total_amount,
                SUM(o.paid_amount) as paid_total,
                SUM(o.total_amount - o.paid_amount) as unpaid_total
            FROM rental_orders o
            LEFT JOIN customers c ON o.customer_id = c.id
            WHERE DATE(o.create_time) BETWEEN ? AND ?
            GROUP BY c.id
            ORDER BY total_amount DESC
        """, (start_date, end_date))
        return [dict(r) for r in rows]

    @staticmethod
    def get_overall_summary(start_date, end_date):
        db = DatabaseManager()
        row = db.query_one("""
            SELECT 
                COUNT(*) as order_count,
                SUM(base_amount) as base_total,
                SUM(overtime_amount) as overtime_total,
                SUM(total_amount) as total_amount,
                SUM(paid_amount) as paid_total,
                SUM(total_amount - paid_amount) as unpaid_total
            FROM rental_orders
            WHERE DATE(create_time) BETWEEN ? AND ?
        """, (start_date, end_date))
        return dict(row) if row else {}

    @staticmethod
    def get_order_details_for_export(start_date, end_date):
        db = DatabaseManager()
        rows = db.query("""
            SELECT 
                o.order_no,
                c.customer_name,
                c.phone,
                t.type_name,
                t.type_code,
                o.rent_start,
                o.rent_end,
                o.actual_return,
                o.deposit,
                o.base_amount,
                o.overtime_amount,
                o.total_amount,
                o.paid_amount,
                (o.total_amount - o.paid_amount) as unpaid,
                o.status,
                o.create_time
            FROM rental_orders o
            LEFT JOIN customers c ON o.customer_id = c.id
            JOIN equipment_types t ON o.type_id = t.id
            WHERE DATE(o.create_time) BETWEEN ? AND ?
            ORDER BY o.create_time DESC
        """, (start_date, end_date))
        return [dict(r) for r in rows]

    @staticmethod
    def export_to_csv(start_date, end_date, export_type="orders", filepath=None):
        if filepath is None:
            filepath = os.path.join(os.path.expanduser("~"), f"rental_report_{start_date}_{end_date}.csv")

        if export_type == "orders":
            data = ReportService.get_order_details_for_export(start_date, end_date)
            headers = [
                "订单号", "客户姓名", "联系电话", "设备类型编码", "设备类型名称",
                "起租时间", "应还时间", "实际归还", "押金",
                "基础租金", "超期罚金", "总金额", "已付金额", "未付金额",
                "订单状态", "创建时间"
            ]
            rows = []
            for d in data:
                status_text = "已归还" if d["status"] == "closed" else "租赁中"
                rows.append([
                    d["order_no"], d["customer_name"] or "", d["phone"] or "",
                    d["type_code"], d["type_name"],
                    d["rent_start"], d["rent_end"], d["actual_return"] or "",
                    d["deposit"], d["base_amount"], d["overtime_amount"],
                    d["total_amount"], d["paid_amount"], d["unpaid"],
                    status_text, d["create_time"]
                ])
        elif export_type == "by_type":
            data = ReportService.get_summary_by_type(start_date, end_date)
            headers = ["设备类型编码", "设备类型名称", "订单数", "基础租金合计",
                       "超期罚金合计", "总金额", "已收金额", "未收金额"]
            rows = []
            for d in data:
                rows.append([
                    d["type_code"], d["type_name"], d["order_count"],
                    d["base_total"] or 0, d["overtime_total"] or 0,
                    d["total_amount"] or 0, d["paid_total"] or 0, d["unpaid_total"] or 0
                ])
        elif export_type == "by_customer":
            data = ReportService.get_summary_by_customer(start_date, end_date)
            headers = ["客户姓名", "联系电话", "订单数", "基础租金合计",
                       "超期罚金合计", "总金额", "已收金额", "未收金额"]
            rows = []
            for d in data:
                rows.append([
                    d["customer_name"] or "散客", d["phone"] or "", d["order_count"],
                    d["base_total"] or 0, d["overtime_total"] or 0,
                    d["total_amount"] or 0, d["paid_total"] or 0, d["unpaid_total"] or 0
                ])
        else:
            data = ReportService.get_summary_by_date(start_date, end_date)
            headers = ["日期", "订单数", "基础租金", "超期罚金", "总金额", "已收金额", "未收金额"]
            rows = []
            for d in data:
                rows.append([
                    d["order_date"], d["order_count"],
                    d["base_total"] or 0, d["overtime_total"] or 0,
                    d["total_amount"] or 0, d["paid_total"] or 0, d["unpaid_total"] or 0
                ])

        with open(filepath, "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.writer(f)
            writer.writerow(headers)
            writer.writerows(rows)

        return filepath, len(rows)

    @staticmethod
    def get_report_by_date_range(start_date, end_date, type_id=None, customer_id=None):
        db = DatabaseManager()
        sql = """
            SELECT 
                o.id, o.order_no, o.rent_start, o.rent_end, o.actual_return,
                o.deposit, o.base_amount, o.overtime_amount, o.total_amount,
                o.paid_amount, o.status, o.create_time,
                t.id as type_id, t.type_code, t.type_name,
                c.id as customer_id, c.customer_name, c.phone
            FROM rental_orders o
            LEFT JOIN customers c ON o.customer_id = c.id
            JOIN equipment_types t ON o.type_id = t.id
            WHERE DATE(o.create_time) BETWEEN ? AND ?
        """
        params = [start_date, end_date]
        if type_id:
            sql += " AND o.type_id = ?"
            params.append(type_id)
        if customer_id:
            sql += " AND o.customer_id = ?"
            params.append(customer_id)
        sql += " ORDER BY o.create_time DESC"

        rows = db.query(sql, tuple(params))
        records = []
        for r in rows:
            d = dict(r)
            d["customer_name"] = d.get("customer_name", "") or ""
            d["type_name"] = d.get("type_name", "") or ""
            d["actual_return"] = d.get("actual_return", "") or ""
            records.append(d)

        summary = {
            "order_count": len(records),
            "base_amount": sum(r["base_amount"] for r in records),
            "overtime_amount": sum(r["overtime_amount"] for r in records),
            "total_amount": sum(r["total_amount"] for r in records),
            "paid_amount": sum(r["paid_amount"] for r in records),
            "unpaid_amount": sum(r["total_amount"] - r["paid_amount"] for r in records),
        }
        return summary, records

    @staticmethod
    def export_to_csv_file(filepath, records):
        headers = [
            "订单号", "客户", "联系电话", "设备类型",
            "起租时间", "应还时间", "实际归还",
            "押金", "基础租金", "超期罚金", "总金额", "已收金额", "未收金额", "状态"
        ]
        rows = []
        for d in records:
            status_text = "已归还" if d.get("status") == "closed" else "租赁中"
            unpaid = d["total_amount"] - d["paid_amount"]
            rows.append([
                d["order_no"], d.get("customer_name", ""), d.get("phone", ""),
                d.get("type_name", ""),
                d.get("rent_start", ""), d.get("rent_end", ""), d.get("actual_return", ""),
                d.get("deposit", 0), d.get("base_amount", 0), d.get("overtime_amount", 0),
                d.get("total_amount", 0), d.get("paid_amount", 0), unpaid, status_text
            ])
        with open(filepath, "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.writer(f)
            writer.writerow(headers)
            writer.writerows(rows)
        return True, f"成功导出 {len(rows)} 条记录"
