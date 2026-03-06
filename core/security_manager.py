# -*- coding: utf-8 -*-
"""Password hashing and access-control helpers."""

import hashlib
import logging
from core.config_manager import ConfigManager

logger = logging.getLogger("JaliMaker.Security")

DEFAULT_PASSWORD = "indus1234"


class SecurityManager:
    """Handles password storage and verification via config."""

    def __init__(self, config: ConfigManager):
        self._config = config

    # ── Public API ────────────────────────────────────────────────────────────

    @property
    def dev_mode(self) -> bool:
        return self._config.get_bool("SECURITY", "dev_mode", False)

    def has_password(self) -> bool:
        return bool(self._config.get("SECURITY", "password_hash", ""))

    def verify(self, password: str) -> bool:
        stored = self._config.get("SECURITY", "password_hash", "")
        if not stored:
            return False
        result = stored == self._hash(password)
        logger.info(f"Password verification: {'SUCCESS' if result else 'FAILED'}")
        return result

    def set_password(self, new_password: str) -> None:
        self._config.set("SECURITY", "password_hash", self._hash(new_password))
        self._config.save()
        logger.info("Password updated")

    def initialise_default_password(self) -> None:
        """Set the default password if none exists."""
        if not self.has_password():
            self.set_password(DEFAULT_PASSWORD)
            logger.warning(f"Default password set: {DEFAULT_PASSWORD}")

    # ── Internals ─────────────────────────────────────────────────────────────

    @staticmethod
    def _hash(password: str) -> str:
        return hashlib.sha256(password.encode("utf-8")).hexdigest()
