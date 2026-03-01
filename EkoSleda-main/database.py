# ═══════════════════════════════════════════════
#  database.py  —  Всички функции за база данни
# ═══════════════════════════════════════════════

import hashlib
import requests
from datetime import datetime
from config import _sb_get, _sb_post, _sb_patch


def init_db():
    """Таблиците са в Supabase — няма нужда от локална инициализация."""
    pass


def hash_pw(pw: str) -> str:
    return hashlib.sha256(pw.encode()).hexdigest()


def register_user(username: str, password: str, name: str):
    """Регистрира нов потребител. Връща (uid, None) или (None, error_msg)."""
    try:
        result = _sb_post("users", {
            "username":   username.strip(),
            "password":   hash_pw(password),
            "name":       name.strip(),
            "created_at": datetime.now().strftime('%Y-%m-%d'),
        })
        return result.get("id"), None
    except requests.exceptions.HTTPError as e:
        if e.response is not None and e.response.status_code in (409, 422):
            return None, "Потребителското име вече съществува."
        return None, f"Грешка при регистрация: {e}"
    except Exception as e:
        return None, f"Грешка при регистрация: {e}"


def login_user(username: str, password: str):
    """Влизане. Връща (uid, name, None) или (None, None, error_msg)."""
    try:
        rows = _sb_get("users", params={
            "username": f"eq.{username.strip()}",
            "password": f"eq.{hash_pw(password)}",
            "select":   "id,name",
        })
        if rows:
            return rows[0]["id"], rows[0]["name"], None
        return None, None, "Грешно потребителско име или парола."
    except Exception as e:
        return None, None, f"Грешка при вход: {e}"


def load_entries(user_id: str) -> list:
    """Зарежда всички записи за потребителя, сортирани по дата."""
    try:
        rows = _sb_get("entries", params={
            "user_id": f"eq.{user_id}",
            "order":   "date.asc",
            "select":  "date,travel_co2,electricity_co2,total_co2,"
                       "start_location,end_location,transport_mode",
        })
        return [
            {
                'date':            datetime.strptime(r['date'], '%Y-%m-%d'),
                'travel_co2':      r['travel_co2']      or 0,
                'electricity_co2': r['electricity_co2'] or 0,
                'total_co2':       r['total_co2']       or 0,
                'start_location':  r['start_location']  or '',
                'end_location':    r['end_location']    or '',
                'transport_mode':  r['transport_mode']  or '',
                # Нови категории — стари записи нямат тези данни
                'flights_co2':     0,
                'shopping_co2':    0,
                'heating_co2':     0,
                'pure_elec_co2':   r['electricity_co2'] or 0,
            }
            for r in rows
        ]
    except Exception as e:
        print(f"Грешка при зареждане на записи: {e}")
        return []


def save_entry(user_id: str, entry: dict):
    """Записва нов CO₂ запис в Supabase."""
    try:
        _sb_post("entries", {
            "user_id":         user_id,
            "date":            entry['date'].strftime('%Y-%m-%d'),
            "travel_co2":      entry['travel_co2'],
            "electricity_co2": entry['electricity_co2'],
            "total_co2":       entry['total_co2'],
            "start_location":  entry['start_location'],
            "end_location":    entry['end_location'],
            "transport_mode":  entry['transport_mode'],
        })
    except Exception as e:
        print(f"Грешка при запис: {e}")


def get_profile(user_id: str):
    """Връща (username, name, created_at) или None."""
    try:
        rows = _sb_get("users", params={
            "id":     f"eq.{user_id}",
            "select": "username,name,created_at",
        })
        if rows:
            r = rows[0]
            return r['username'], r['name'], r['created_at']
        return None
    except Exception as e:
        print(f"Грешка при профил: {e}")
        return None


def update_name(user_id: str, new_name: str):
    """Обновява името на потребителя."""
    try:
        _sb_patch("users", {"id": f"eq.{user_id}"}, {"name": new_name.strip()})
    except Exception as e:
        print(f"Грешка при обновяване на име: {e}")


def update_password(user_id: str, new_pw: str):
    """Сменя паролата на потребителя."""
    try:
        _sb_patch("users", {"id": f"eq.{user_id}"}, {"password": hash_pw(new_pw)})
    except Exception as e:
        print(f"Грешка при промяна на парола: {e}")


def get_road_route(start_coords, end_coords, transport_mode: str):
    """
    Взема реален пътен маршрут от OSRM.
    Връща (distance_km, duration_min, [[lat,lng],...]) или None.
    """
    profile_map = {
        "car":     "driving",
        "bus":     "driving",
        "train":   "driving",
        "bicycle": "bike",
        "walking": "foot",
    }
    profile    = profile_map.get(transport_mode, "driving")
    coords_str = (f"{start_coords[1]},{start_coords[0]};"
                  f"{end_coords[1]},{end_coords[0]}")
    url = (f"http://router.project-osrm.org/route/v1/{profile}/{coords_str}"
           f"?overview=full&geometries=geojson&steps=false")
    try:
        resp = requests.get(url, timeout=10)
        data = resp.json()
        if data.get("code") != "Ok":
            return None
        route   = data["routes"][0]
        dist_km = route["distance"] / 1000.0
        dur_min = route["duration"] / 60.0
        geom    = [[c[1], c[0]] for c in route["geometry"]["coordinates"]]
        return dist_km, dur_min, geom
    except Exception:
        return None


# ─────────────────────────────────────────────
#  COMMUNITY TIPS  (таблица: community_tips)
# ─────────────────────────────────────────────

def load_community_tips(limit: int = 50) -> list:
    """
    Зарежда последните N съвети от всички потребители.
    Всеки ред: {id, user_name, tip, created_at}
    """
    try:
        rows = _sb_get("community_tips", params={
            "select": "id,user_name,tip,created_at",
            "order":  "created_at.desc",
            "limit":  str(limit),
        })
        return rows or []
    except Exception as e:
        print(f"Грешка при зареждане на съвети: {e}")
        return []


def post_community_tip(user_name: str, tip: str) -> tuple:
    """
    Публикува нов съвет. Връща (True, None) или (False, error_msg).
    """
    try:
        _sb_post("community_tips", {
            "user_name":  user_name,
            "tip":        tip.strip(),
            "created_at": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        })
        return True, None
    except Exception as e:
        return False, str(e)


def delete_community_tip(tip_id: str, user_name: str) -> bool:
    """Изтрива съвет само ако принадлежи на потребителя."""
    try:
        import requests as _req
        from config import SUPABASE_URL, HEADERS
        r = _req.delete(
            f"{SUPABASE_URL}/rest/v1/community_tips",
            headers=HEADERS,
            params={"id": f"eq.{tip_id}", "user_name": f"eq.{user_name}"},
            timeout=10,
        )
        r.raise_for_status()
        return True
    except Exception as e:
        print(f"Грешка при изтриване: {e}")
        return False


# ─────────────────────────────────────────────
#  LEADERBOARD  (агрегира данни от entries)
# ─────────────────────────────────────────────

def load_leaderboard_data() -> list:
    """
    Зарежда агрегирани данни от всички потребители за лидерборд.
    Връща [{user_name, total_co2, avg_co2, count}, ...]
    """
    try:
        # Вземи всички записи + join с users за потребителско име
        rows = _sb_get("entries", params={
            "select": "user_id,total_co2",
            "limit":  "5000",
        })
        if not rows:
            return []

        # Вземи потребителски имена
        user_rows = _sb_get("users", params={
            "select": "id,username",
        })
        uid_to_name = {u['id']: u['username'] for u in (user_rows or [])}

        # Агрегирай по потребител
        agg = {}
        for r in rows:
            uid = r['user_id']
            name = uid_to_name.get(uid, f"Потребител_{uid[:6]}")
            co2 = r['total_co2'] or 0
            if name not in agg:
                agg[name] = {'user_name': name, 'total_co2': 0, 'count': 0}
            agg[name]['total_co2'] += co2
            agg[name]['count'] += 1

        result = []
        for name, d in agg.items():
            d['avg_co2'] = d['total_co2'] / max(d['count'], 1)
            result.append(d)
        return result
    except Exception as e:
        print(f"Грешка при лидерборд: {e}")
        return []
