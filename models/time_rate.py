from database.db_manager import DatabaseManager


class TimeRate:
    def __init__(self, id=None, name="", start_hour=0, end_hour=24, rate_per_hour=0.0, is_peak=0):
        self.id = id
        self.name = name
        self.start_hour = start_hour
        self.end_hour = end_hour
        self.rate_per_hour = rate_per_hour
        self.is_peak = is_peak

    @staticmethod
    def get_all():
        db = DatabaseManager()
        rows = db.query("SELECT * FROM time_rates ORDER BY start_hour")
        return [TimeRate(**dict(r)) for r in rows]

    @staticmethod
    def get_by_id(rate_id):
        db = DatabaseManager()
        row = db.query_one("SELECT * FROM time_rates WHERE id = ?", (rate_id,))
        return TimeRate(**dict(row)) if row else None

    @staticmethod
    def create(name, start_hour, end_hour, rate_per_hour, is_peak=0):
        db = DatabaseManager()
        cursor = db.execute("""
            INSERT INTO time_rates (name, start_hour, end_hour, rate_per_hour, is_peak)
            VALUES (?, ?, ?, ?, ?)
        """, (name, start_hour, end_hour, rate_per_hour, is_peak))
        return cursor.lastrowid

    def save(self):
        db = DatabaseManager()
        db.execute("""
            UPDATE time_rates SET name=?, start_hour=?, end_hour=?, rate_per_hour=?, is_peak=?
            WHERE id=?
        """, (self.name, self.start_hour, self.end_hour, self.rate_per_hour, self.is_peak, self.id))

    @staticmethod
    def delete(rate_id):
        db = DatabaseManager()
        db.execute("DELETE FROM time_rates WHERE id = ?", (rate_id,))

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "start_hour": self.start_hour,
            "end_hour": self.end_hour,
            "rate_per_hour": self.rate_per_hour,
            "is_peak": self.is_peak
        }
