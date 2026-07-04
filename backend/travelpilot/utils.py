import secrets
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

def generate_session_id() -> str:
    # 7 bytes = 14 hex characters. Combined with prefix: tp_<14 hex characters>
    return f"tp_{secrets.token_hex(7)}"

def format_timestamp(dt: datetime) -> str:
    return dt.isoformat()
