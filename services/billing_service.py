from datetime import datetime, timedelta
from models.time_rate import TimeRate
from models.rental import BillDetail, RentalOrder
from utils.helpers import parse_datetime, hours_between


class BillingService:
    OVERTIME_MULTIPLIER = 1.5

    @staticmethod
    def get_rates_sorted():
        rates = TimeRate.get_all()
        return sorted(rates, key=lambda r: r.start_hour)

    @staticmethod
    def _find_rate_for_hour(rates, hour):
        for rate in rates:
            if rate.start_hour <= hour < rate.end_hour:
                return rate
        return rates[-1] if rates else None

    @staticmethod
    def split_time_segments(start_dt, end_dt):
        rates = BillingService.get_rates_sorted()
        if not rates:
            return []
        segments = []
        current = start_dt
        while current < end_dt:
            current_hour = current.hour + current.minute / 60.0 + current.second / 3600.0
            current_rate = BillingService._find_rate_for_hour(rates, current.hour)
            if not current_rate:
                break
            next_segment_start = current.replace(minute=0, second=0, microsecond=0) + timedelta(hours=current_rate.end_hour - current.hour)
            if next_segment_start.hour == 0 and current_rate.end_hour == 24:
                next_segment_start = (current + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
            next_cutoff = min(next_segment_start, end_dt)
            hours = hours_between(current, next_cutoff)
            if hours > 0:
                segments.append({
                    "segment_start": current,
                    "segment_end": next_cutoff,
                    "hours": hours,
                    "rate": current_rate.rate_per_hour,
                    "rate_name": current_rate.name,
                    "rate_id": current_rate.id,
                    "segment_amount": round(hours * current_rate.rate_per_hour, 2),
                    "is_overtime": False
                })
            current = next_cutoff
        return segments

    @staticmethod
    def calculate_rental_cost(rent_start_str, rent_end_str):
        rent_start = parse_datetime(rent_start_str)
        rent_end = parse_datetime(rent_end_str)
        if not rent_start or not rent_end or rent_start >= rent_end:
            return {"segments": [], "base_amount": 0.0, "total": 0.0, "total_hours": 0.0}
        segments = BillingService.split_time_segments(rent_start, rent_end)
        total_hours = sum(s["hours"] for s in segments)
        base_amount = round(sum(s["segment_amount"] for s in segments), 2)
        return {
            "segments": segments,
            "base_amount": base_amount,
            "total": base_amount,
            "total_hours": total_hours
        }

    @staticmethod
    def calculate_full_bill(rent_start_str, rent_end_str, actual_return_str=None):
        result = BillingService.calculate_rental_cost(rent_start_str, rent_end_str)
        rent_end = parse_datetime(rent_end_str)
        actual_return = parse_datetime(actual_return_str) if actual_return_str else None
        overtime_amount = 0.0
        overtime_segments = []
        if actual_return and actual_return > rent_end:
            overtime_rates = BillingService.split_time_segments(rent_end, actual_return)
            for seg in overtime_rates:
                seg["is_overtime"] = True
                seg["segment_amount"] = round(seg["segment_amount"] * BillingService.OVERTIME_MULTIPLIER, 2)
                seg["rate"] = round(seg["rate"] * BillingService.OVERTIME_MULTIPLIER, 2)
                seg["rate_name"] = f"{seg['rate_name']}(超期x1.5)"
                overtime_segments.append(seg)
            overtime_amount = round(sum(s["segment_amount"] for s in overtime_segments), 2)
        all_segments = result["segments"] + overtime_segments
        total = round(result["base_amount"] + overtime_amount, 2)
        return {
            "segments": all_segments,
            "base_amount": result["base_amount"],
            "overtime_amount": overtime_amount,
            "total": total,
            "total_hours": round(result["total_hours"] + sum(s["hours"] for s in overtime_segments), 2),
            "overtime_hours": round(sum(s["hours"] for s in overtime_segments), 2)
        }

    @staticmethod
    def save_bill_details(order_id, segments):
        BillDetail.clear_by_order(order_id)
        for seg in segments:
            BillDetail.create(
                order_id=order_id,
                segment_start=str(seg["segment_start"]),
                segment_end=str(seg["segment_end"]),
                hours=seg["hours"],
                rate=seg["rate"],
                rate_name=seg["rate_name"],
                segment_amount=seg["segment_amount"]
            )

    @staticmethod
    def get_order_bill_details(order_id):
        details = BillDetail.get_by_order(order_id)
        segments = []
        for d in details:
            segments.append({
                "segment_start": d.segment_start,
                "segment_end": d.segment_end,
                "hours": d.hours,
                "rate": d.rate,
                "rate_name": d.rate_name,
                "segment_amount": d.segment_amount
            })
        return segments

    @staticmethod
    def validate_rates():
        rates = BillingService.get_rates_sorted()
        if not rates:
            return False, "没有设置费率"
        rates.sort(key=lambda r: r.start_hour)
        if rates[0].start_hour != 0:
            return False, "费率应从0点开始"
        if rates[-1].end_hour != 24:
            return False, "费率应覆盖到24点"
        for i in range(len(rates) - 1):
            if rates[i].end_hour != rates[i + 1].start_hour:
                return False, f"费率时段不连续: {rates[i].name}({rates[i].start_hour}-{rates[i].end_hour}) -> {rates[i+1].name}"
        return True, "费率配置正确"
