import logging
from typing import Optional
from fastapi import Request, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from travelpilot.config import FIREBASE_PROJECT_ID

logger = logging.getLogger(__name__)

# Firebase admin initialization (conditional)
firebase_initialized = False
try:
    if FIREBASE_PROJECT_ID:
        import firebase_admin
        if not firebase_admin._apps:
            # Initialize with default credentials
            firebase_admin.initialize_app()
        firebase_initialized = True
        logger.info("Firebase Admin initialized successfully")
except Exception as e:
    logger.warning(f"Firebase Admin could not be initialized: {e}. Token verification will be bypassed or fail.")

security_scheme = HTTPBearer(auto_error=False)

class UserContext:
    def __init__(self, user_id: str, is_guest: bool = True):
        self.user_id = user_id
        self.is_guest = is_guest

async def get_current_user(
    request: Request,
    creds: Optional[HTTPAuthorizationCredentials] = Depends(security_scheme)
) -> UserContext:
    # If no token is provided, default to guest
    if not creds:
        return UserContext(user_id="guest", is_guest=True)

    token = creds.credentials
    if not firebase_initialized:
        logger.warning("Firebase not initialized; allowing guest access despite token provided.")
        return UserContext(user_id="guest", is_guest=True)

    try:
        from firebase_admin import auth
        decoded_token = auth.verify_id_token(token)
        uid = decoded_token.get("uid")
        if not uid:
            raise HTTPException(status_code=401, detail="Invalid token details")
        return UserContext(user_id=uid, is_guest=False)
    except Exception as e:
        logger.error(f"Token verification failed: {e}")
        raise HTTPException(status_code=401, detail="Authentication failed: invalid token")

def verify_session_owner(session_owner_id: str, current_user: UserContext) -> None:
    if session_owner_id != current_user.user_id:
        raise HTTPException(status_code=403, detail="Forbidden: session ownership mismatch")
