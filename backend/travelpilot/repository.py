import logging
from typing import Optional, Dict, Any
from travelpilot.config import USE_FIRESTORE, FIREBASE_PROJECT_ID

logger = logging.getLogger(__name__)


class SessionRepository:
    async def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        raise NotImplementedError()

    async def save_session(self, session_id: str, data: Dict[str, Any]) -> None:
        raise NotImplementedError()

    async def delete_session(self, session_id: str) -> None:
        raise NotImplementedError()

    async def get_question_cache(self, group_id: str) -> Optional[Dict[str, Any]]:
        raise NotImplementedError()

    async def save_question_cache(self, group_id: str, data: Dict[str, Any]) -> None:
        raise NotImplementedError()

    async def delete_question_cache(self, group_id: str) -> None:
        raise NotImplementedError()


class InMemoryRepository(SessionRepository):
    def __init__(self):
        self._storage: Dict[str, Dict[str, Any]] = {}
        self._question_cache: Dict[str, Dict[str, Any]] = {}
        logger.info("Initialized InMemoryRepository")

    async def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        return self._storage.get(session_id)

    async def save_session(self, session_id: str, data: Dict[str, Any]) -> None:
        self._storage[session_id] = data

    async def delete_session(self, session_id: str) -> None:
        if session_id in self._storage:
            del self._storage[session_id]

    async def get_question_cache(self, group_id: str) -> Optional[Dict[str, Any]]:
        return self._question_cache.get(group_id)

    async def save_question_cache(self, group_id: str, data: Dict[str, Any]) -> None:
        self._question_cache[group_id] = data

    async def delete_question_cache(self, group_id: str) -> None:
        if group_id in self._question_cache:
            del self._question_cache[group_id]


# Dynamic import and initialization of Firestore to prevent startup failure if dependencies are missing or USE_FIRESTORE is false
class FirestoreSessionRepository(SessionRepository):
    def __init__(self):
        self.fallback = InMemoryRepository()
        self.use_fallback = False
        try:
            from google.cloud import firestore
            import os
            import json
            from google.oauth2 import service_account

            creds_json = os.getenv("GOOGLE_CREDENTIALS_JSON", "")
            if creds_json:
                logger.info(
                    "Initializing Firestore with credentials from GOOGLE_CREDENTIALS_JSON"
                )
                creds_info = json.loads(creds_json)
                credentials = service_account.Credentials.from_service_account_info(
                    creds_info
                )
                self.db = firestore.AsyncClient(
                    credentials=credentials, project=creds_info.get("project_id")
                )
            elif FIREBASE_PROJECT_ID:
                self.db = firestore.AsyncClient(project=FIREBASE_PROJECT_ID)
            else:
                self.db = firestore.AsyncClient()
            self.collection = self.db.collection("tp_sessions")
            self.qcache_collection = self.db.collection("tp_question_cache")
            logger.info("Initialized FirestoreSessionRepository")
        except Exception as e:
            logger.error(
                f"Failed to initialize Firestore Client: {e}. Falling back to InMemory storage."
            )
            self.use_fallback = True

    async def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        if self.use_fallback:
            return await self.fallback.get_session(session_id)
        try:
            doc = await self.collection.document(session_id).get()
            if doc.exists:
                return doc.to_dict()
        except Exception as e:
            logger.error(
                f"Error reading session {session_id} from Firestore: {e}. Falling back to InMemory storage."
            )
            self.use_fallback = True
            return await self.fallback.get_session(session_id)
        return None

    async def save_session(self, session_id: str, data: Dict[str, Any]) -> None:
        if self.use_fallback:
            await self.fallback.save_session(session_id, data)
            return
        try:
            await self.collection.document(session_id).set(data)
        except Exception as e:
            logger.error(
                f"Error saving session {session_id} to Firestore: {e}. Falling back to InMemory storage."
            )
            self.use_fallback = True
            await self.fallback.save_session(session_id, data)

    async def delete_session(self, session_id: str) -> None:
        if self.use_fallback:
            await self.fallback.delete_session(session_id)
            return
        try:
            await self.collection.document(session_id).delete()
        except Exception as e:
            logger.error(
                f"Error deleting session {session_id} from Firestore: {e}. Falling back to InMemory storage."
            )
            self.use_fallback = True
            await self.fallback.delete_session(session_id)

    async def get_question_cache(self, group_id: str) -> Optional[Dict[str, Any]]:
        if self.use_fallback:
            return await self.fallback.get_question_cache(group_id)
        try:
            doc = await self.qcache_collection.document(group_id).get()
            if doc.exists:
                return doc.to_dict()
        except Exception as e:
            logger.error(
                f"Error reading question cache {group_id} from Firestore: {e}. Falling back to InMemory."
            )
            self.use_fallback = True
            return await self.fallback.get_question_cache(group_id)
        return None

    async def save_question_cache(self, group_id: str, data: Dict[str, Any]) -> None:
        if self.use_fallback:
            await self.fallback.save_question_cache(group_id, data)
            return
        try:
            await self.qcache_collection.document(group_id).set(data)
        except Exception as e:
            logger.error(
                f"Error saving question cache {group_id} to Firestore: {e}. Falling back to InMemory."
            )
            self.use_fallback = True
            await self.fallback.save_question_cache(group_id, data)

    async def delete_question_cache(self, group_id: str) -> None:
        if self.use_fallback:
            await self.fallback.delete_question_cache(group_id)
            return
        try:
            await self.qcache_collection.document(group_id).delete()
        except Exception as e:
            logger.error(
                f"Error deleting question cache {group_id} from Firestore: {e}. Falling back to InMemory."
            )
            self.use_fallback = True
            await self.fallback.delete_question_cache(group_id)


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
            logger.warning(
                "Firestore initialization failed, using InMemoryRepository fallback."
            )

    _repo_instance = InMemoryRepository()
    return _repo_instance
