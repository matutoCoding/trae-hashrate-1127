from datetime import datetime, date, timedelta
import random
import string


def parse_datetime(dt_str):
    if not dt_str:
        return None
    try:
        return datetime.strptime(dt_str, "%Y-%m-%d %H:%M:%S")
    except ValueError:
        try:
            return datetime.strptime(dt_str, "%Y-%m-%d %H:%M")
        except ValueError:
            return datetime.strptime(dt_str, "%Y-%m-%d")


def format_datetime(dt):
    if isinstance(dt, datetime):
        return dt.strftime("%Y-%m-%d %H:%M:%S")
    elif isinstance(dt, date):
        return dt.strftime("%Y-%m-%d")
    return str(dt)


def parse_date(date_str):
    if not date_str:
        return None
    return datetime.strptime(date_str, "%Y-%m-%d").date()


def format_date(d):
    if isinstance(d, (date, datetime)):
        return d.strftime("%Y-%m-%d")
    return str(d)


def generate_order_no():
    now = datetime.now()
    prefix = "R" + now.strftime("%Y%m%d%H%M%S")
    suffix = "".join(random.choices(string.digits, k=4))
    return prefix + suffix


def generate_batch_no():
    now = datetime.now()
    prefix = "B" + now.strftime("%Y%m%d")
    suffix = "".join(random.choices(string.digits, k=3))
    return prefix + suffix


def generate_item_code(batch_no=""):
    now = datetime.now()
    prefix = "E" + now.strftime("%Y%m%d")
    if batch_no:
        prefix = batch_no + "-"
    suffix = "".join(random.choices(string.digits + string.ascii_uppercase, k=6))
    return prefix + suffix


def generate_check_no():
    now = datetime.now()
    prefix = "CK" + now.strftime("%Y%m%d%H%M%S")
    suffix = "".join(random.choices(string.digits, k=3))
    return prefix + suffix


def hours_between(dt_start, dt_end):
    if dt_start >= dt_end:
        return 0.0
    delta = dt_end - dt_start
    return round(delta.total_seconds() / 3600.0, 2)


def get_status_color(status):
    colors = {
        "available": "#4CAF50",
        "rented": "#2196F3",
        "expired": "#F44336",
        "warning": "#FF9800",
        "normal": "#4CAF50",
        "active": "#2196F3",
        "closed": "#9E9E9E",
    }
    return colors.get(status, "#000000")


def status_text(status):
    texts = {
        "available": "可租",
        "rented": "已租",
        "expired": "已过期",
        "warning": "临期预警",
        "normal": "正常",
        "active": "租赁中",
        "closed": "已归还",
    }
    return texts.get(status, status)
