# ═══════════════════════════════════════════════
#  config.py  —  Supabase конфигурация и API
# ═══════════════════════════════════════════════

import requests

SUPABASE_URL = "https://yzpvbhuspgxdnvnbnwsh.supabase.co"
SUPABASE_KEY = (
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9"
    ".eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Inl6cHZiaHVzcGd4ZG52bmJud3NoIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzEzNTA1OTAsImV4cCI6MjA4NjkyNjU5MH0"
    ".YU0iwISJ9YmKxzTT3M65qrW2zMXwwPHYFJ3vwu34p0k"
)

HEADERS = {
    "apikey":        SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type":  "application/json",
    "Prefer":        "return=representation",
}


def _sb_get(table, params=None):
    """GET редове от Supabase таблица."""
    r = requests.get(
        f"{SUPABASE_URL}/rest/v1/{table}",
        headers=HEADERS, params=params, timeout=10
    )
    r.raise_for_status()
    return r.json()


def _sb_post(table, data):
    """INSERT ред и върни създадения обект."""
    r = requests.post(
        f"{SUPABASE_URL}/rest/v1/{table}",
        headers=HEADERS, json=data, timeout=10
    )
    r.raise_for_status()
    result = r.json()
    return result[0] if isinstance(result, list) and result else result


def _sb_patch(table, match_params, data):
    """UPDATE редове по match_params."""
    r = requests.patch(
        f"{SUPABASE_URL}/rest/v1/{table}",
        headers=HEADERS, params=match_params, json=data, timeout=10
    )
    r.raise_for_status()

# Groq API ключ за AI Съветника — БЕЗПЛАТЕН!
# Вземи ключ от: https://console.groq.com/ → API Keys → Create API Key
# Ключът започва с 'gsk_...'
GROQ_API_KEY = ""  # Постави тук своя ключ

