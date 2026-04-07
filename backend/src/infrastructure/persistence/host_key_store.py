"""PostgreSQL implementation of SSH host key fingerprint storage."""

import logging

from src.domain.ports.host_key_store import HostKeyStore
from src.infrastructure.database.engine import session_scope
from src.infrastructure.database.models import AppSettingModel

logger = logging.getLogger(__name__)

_KEY_PREFIX = "SSH_HOST_KEY_"


class PostgresHostKeyStore(HostKeyStore):

    def get_fingerprint(self, hostname: str) -> str | None:
        key = f"{_KEY_PREFIX}{hostname}"
        with session_scope() as session:
            row = session.query(AppSettingModel).filter_by(key=key).first()
            return row.value if row and row.value else None

    def save_fingerprint(self, hostname: str, fingerprint: str) -> None:
        key = f"{_KEY_PREFIX}{hostname}"
        with session_scope() as session:
            row = session.query(AppSettingModel).filter_by(key=key).first()
            if row:
                row.value = fingerprint
            else:
                session.add(AppSettingModel(key=key, value=fingerprint))
        logger.info("SSH host key fingerprint saved for %s", hostname)
