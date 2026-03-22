"""Value object representing backup output formats."""

from enum import Enum


class BackupFormat(Enum):
    CUSTOM = "custom"   # pg_dump -Fc → .backup (compressed, restorable)
    PLAIN = "plain"     # pg_dump -Fp | gzip → .sql.gz (compressed plain text)

    @property
    def pg_dump_flag(self) -> str:
        return "-Fc" if self == BackupFormat.CUSTOM else "-Fp"

    @property
    def file_extension(self) -> str:
        return ".backup" if self == BackupFormat.CUSTOM else ".sql.gz"

    @property
    def needs_pipe_gzip(self) -> bool:
        """PLAIN format pipes through gzip for compression."""
        return self == BackupFormat.PLAIN
