"""Run the local Flask lead workflow app."""

from __future__ import annotations

import os

from dotenv import load_dotenv

from app.main import create_app

load_dotenv()

if __name__ == "__main__":
    create_app().run(
        host=os.getenv("APP_HOST", "127.0.0.1"),
        port=int(os.getenv("APP_PORT") or os.getenv("PORT_RANGE_START", "47000")),
        debug=os.getenv("APP_ENV", "development") == "development",
    )
