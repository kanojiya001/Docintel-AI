"""
Supabase client for real-time broadcasting and storage operations.
Uses the service key so it can bypass RLS for server-side operations.
"""
from typing import Optional
from app.core.config import settings

_supabase_client = None


def get_supabase():
    """Return a singleton Supabase client (service role)."""
    global _supabase_client
    if _supabase_client is None and settings.SUPABASE_URL and settings.SUPABASE_SERVICE_KEY:
        try:
            from supabase import create_client, Client
            _supabase_client = create_client(
                settings.SUPABASE_URL,
                settings.SUPABASE_SERVICE_KEY,
            )
        except Exception as e:
            print(f"[Supabase] Could not initialise client: {e}")
    return _supabase_client


async def broadcast_event(table: str, event: str, payload: dict):
    """
    Broadcast a change event via Supabase Realtime channel so the
    frontend receives live updates without polling.

    table  – logical name, e.g. 'documents', 'queries', 'analytics'
    event  – INSERT | UPDATE | DELETE
    payload – serialisable dict with the changed row data
    """
    client = get_supabase()
    if client is None:
        return
    try:
        # Use the Realtime broadcast API (no RLS required)
        channel = client.channel(f"db-{table}")
        await channel.send_broadcast(
            event=event,
            payload=payload,
        )
    except Exception as e:
        # Non-fatal — real-time is best-effort
        print(f"[Supabase broadcast] {table}/{event}: {e}")
