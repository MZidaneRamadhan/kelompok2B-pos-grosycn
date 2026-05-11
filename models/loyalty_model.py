import uuid
from datetime import datetime
from database import get_connection

def _row_to_dict(row):
    return dict(row) if row else None

def create_member(name: str, email: str, phone: str) -> str:
    member_id = f"MBR-{str(uuid.uuid4())[:6].upper()}"
    join_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    with get_connection() as conn:
        conn.execute('''
            INSERT INTO member (id, member_name, email, phone, tier, total_point, spent, visits, join_date, is_active)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (member_id, name, email, phone, "Bronze", 0, 0.0, 0, join_date, 1))
    return member_id

def get_member(member_id: str) -> dict:
    with get_connection() as conn:
        row = conn.execute("SELECT * FROM member WHERE id = ?", (member_id,)).fetchone()
        if not row: return None
        # Ubah nama kolom agar cocok dengan format UI loyalty.py
        d = dict(row)
        d["name"] = d["member_name"]
        d["points"] = d["total_point"]
        return d

def get_all_members() -> list[dict]:
    with get_connection() as conn:
        rows = conn.execute("SELECT * FROM member").fetchall()
        result = []
        for r in rows:
            d = dict(r)
            # Ubah nama kolom agar cocok dengan format UI loyalty.py
            d["name"] = d["member_name"]
            d["points"] = d["total_point"]
            result.append(d)
        return result

def update_member(member_id: str, name: str, email: str, phone: str) -> bool:
    with get_connection() as conn:
        result = conn.execute('''
            UPDATE member 
            SET member_name = ?, email = ?, phone = ? 
            WHERE id = ?
        ''', (name, email, phone, member_id))
        return result.rowcount > 0

def update_loyalty_stats(member_id: str, points_added: int, spent_added: float, new_tier: str) -> bool:
    with get_connection() as conn:
        result = conn.execute('''
            UPDATE member 
            SET total_point = total_point + ?, 
                spent = spent + ?, 
                visits = visits + 1, 
                tier = ? 
            WHERE id = ?
        ''', (points_added, spent_added, new_tier, member_id))
        return result.rowcount > 0

def deduct_points(member_id: str, points_used: int) -> bool:
    with get_connection() as conn:
        member = get_member(member_id)
        if not member or member['points'] < points_used:
            return False
            
        result = conn.execute('''
            UPDATE member 
            SET total_point = total_point - ? 
            WHERE id = ?
        ''', (points_used, member_id))
        return result.rowcount > 0

def delete_member(member_id: str) -> bool:
    with get_connection() as conn:
        result = conn.execute("UPDATE member SET is_active = 0 WHERE id = ?", (member_id,))
        return result.rowcount > 0