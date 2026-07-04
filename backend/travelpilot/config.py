import os
from typing import List

# Gemini API configuration
GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")

# Firestore configuration
USE_FIRESTORE: bool = os.getenv("USE_FIRESTORE", "false").lower() == "true"
FIREBASE_PROJECT_ID: str = os.getenv("FIREBASE_PROJECT_ID", "h2s-promptwars-travel")

# Logging & Monitoring
ENABLE_CLOUD_LOGGING: bool = os.getenv("ENABLE_CLOUD_LOGGING", "false").lower() == "true"

# CORS Setup
ALLOWED_ORIGINS_RAW: str = os.getenv("ALLOWED_ORIGINS", "*")
ALLOWED_ORIGINS: List[str] = [origin.strip() for origin in ALLOWED_ORIGINS_RAW.split(",") if origin.strip()]

# Server Config
PORT: int = int(os.getenv("PORT", "8000"))
HOST: str = os.getenv("HOST", "0.0.0.0")
