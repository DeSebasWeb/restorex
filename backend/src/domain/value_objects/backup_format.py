"""Value object representing backup output formats."""

from enum import Enum


class BackupFormat(Enum):
    CUSTOM = "custom"   # pg_dump -Fc → .backup (compressed, restorable)
    PLAIN = "plain"     # pg_dump -Fp → .sql (human-readable)

    @property
    def pg_dump_flag(self) -> str:
        return "-Fc" if self == BackupFormat.CUSTOM else "-Fp"

    @property
    def file_extension(self) -> str:
        return ".backup" if self == BackupFormat.CUSTOM else ".sql"
