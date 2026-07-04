import logging
from typing import Optional, Dict, Any
from travelpilot.config import USE_FIRESTORE, FIREBASE_PROJECT_ID

logger = logging.getLogger(__name__)

class SessionRepository:
    def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        raise NotImplementedError()

    def save_session(self, session_id: str, data: Dict[str, Any]) -> None:
        raise NotImplementedError()

    def delete_session(self, session_id: str) -> None:
        raise NotImplementedError()

class InMemoryRepository(SessionRepository):
    def __init__(self):
        self._storage: Dict[str, Dict[str, Any]] = {}
        logger.info("Initialized InMemoryRepository")

    def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        return self._storage.get(session_id)

    def save_session(self, session_id: str, data: Dict[str, Any]) -> None:
        self._storage[session_id] = data

    def delete_session(self, session_id: str) -> None:
        if session_id in self._storage:
            del self._storage[session_id]

# Dynamic import and initialization of Firestore to prevent startup failure if dependencies are missing or USE_FIRESTORE is false
class FirestoreSessionRepository(SessionRepository):
    def __init__(self):
        try:
            from google.cloud import firestore
            import os
            import json
            from google.oauth2 import service_account

            creds_json = os.getenv("GOOGLE_CREDENTIALS_JSON", "")
            if creds_json:
                logger.info("Initializing Firestore with credentials from GOOGLE_CREDENTIALS_JSON")
                creds_info = json.loads(creds_json)
                credentials = service_account.Credentials.from_service_account_info(creds_info)
                self.db = firestore.Client(credentials=credentials, project=creds_info.get("project_id"))
            elif FIREBASE_PROJECT_ID:
                self.db = firestore.Client(project=FIREBASE_PROJECT_ID)
            else:
                self.db = firestore.Client()
            self.collection = self.db.collection("tp_sessions")
            logger.info("Initialized FirestoreSessionRepository")
        except Exception as e:
            logger.error(f"Failed to initialize Firestore Client: {e}. Falling back to InMemory storage.")
            raise e

    def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        try:
            doc = self.collection.document(session_id).get()
            if doc.exists:
                return doc.to_dict()
        except Exception as e:
            logger.error(f"Error reading session {session_id} from Firestore: {e}")
        return None

    def save_session(self, session_id: str, data: Dict[str, Any]) -> None:
        try:
            self.collection.document(session_id).set(data)
        except Exception as e:
            logger.error(f"Error saving session {session_id} to Firestore: {e}")
            raise e

    def delete_session(self, session_id: str) -> None:
        try:
            self.collection.document(session_id).delete()
        except Exception as e:
            logger.error(f"Error deleting session {session_id} from Firestore: {e}")

# Global Repository Factory
_repo_instance: Optional[SessionRepository] = None

def get_repository() -> SessionRepository:
    global _repo_instance
    if _repo_instance is not None:
        return _repo_instance

    if USE_FIRESTORE:
        try:
            _repo_instance = FirestoreSessionRepository()
            return _repo_instance
        except Exception:
            logger.warning("Firestore initialization failed, using InMemoryRepository fallback.")
    
    _repo_instance = InMemoryRepository()
    return _repo_instance
