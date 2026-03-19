"""Entry Point: Command-line interface for manual backup execution."""

import argparse
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from src.infrastructure.config import Settings
from src.infrastructure.database import init_db
from src.container import init_container


def setup():
    Settings.LOG_DIR.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=[
            logging.FileHandler(Settings.LOG_DIR / "app.log", encoding="utf-8"),
            logging.StreamHandler(),
        ],
    )
    init_db(Settings.LOCAL_DB_URL)
    Settings.reload()
    return init_container()


def cmd_backup(args):
    container = setup()
    print("\n=== PostgreSQL Backup Manager ===\n")
    mode = "FORCED (all databases)" if args.force else "SMART (only changed databases)"
    print(f"Mode: {mode}")
    print(f"Server: {Settings.SSH_HOST}")
    print(f"Retention: {Settings.RETENTION_DAYS} days")
    print(f"Output: {Settings.BACKUP_LOCAL_DIR}\n")

    summary = container.backup_service.run_full_backup(force=args.force)

    print(f"\n=== Results ===")
    print(f"Total databases: {summary.total_dbs}")
    print(f"Backed up:       {summary.backed_up}")
    print(f"Skipped:         {summary.skipped}")
    print(f"Failed:          {summary.failed}")

    if summary.errors:
        print("\nErrors:")
        for err in summary.errors:
            print(f"  - {err['db_name']}: {err['error']}")

    print(f"\nStarted:  {summary.started_at}")
    print(f"Finished: {summary.finished_at}")


def cmd_scan(args):
    container = setup()
    print("\n=== Scanning databases ===\n")
    databases = container.backup_service.scan_databases()

    print(f"{'Database':<30} {'Size':<12} {'Tables':<8} {'Rows':<12}")
    print("-" * 62)
    for db in databases:
        print(
            f"{db['name']:<30} {db['size']:<12} "
            f"{db['tables']:<8} {db['live_rows']:<12}"
        )
    print(f"\nTotal: {len(databases)} databases")


def cmd_report(args):
    container = setup()
    report = container.report_service.generate_report()
    print("\n=== Backup Report ===\n")
    print(f"Server:            {report['server']}")
    print(f"Total databases:   {report['total_databases']}")
    print(f"Backup runs:       {report['total_backup_runs']}")
    print(f"Backups created:   {report['total_backups_created']}")
    print(f"Failures:          {report['total_failures']}")
    print(f"Success rate:      {report['success_rate']}%")
    print(f"Local storage:     {report['local_storage_used']}")
    print(f"Retention:         {report['retention_days']} days")


def main():
    parser = argparse.ArgumentParser(
        description="PostgreSQL Backup Manager - CLI",
        prog="pg-backup",
    )
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    bp = subparsers.add_parser("backup", help="Run backup for all databases")
    bp.add_argument("--force", action="store_true", help="Backup all DBs regardless of changes")
    bp.set_defaults(func=cmd_backup)

    sp = subparsers.add_parser("scan", help="Scan databases without backing up")
    sp.set_defaults(func=cmd_scan)

    rp = subparsers.add_parser("report", help="Show backup report summary")
    rp.set_defaults(func=cmd_report)

    args = parser.parse_args()
    if args.command is None:
        parser.print_help()
        return

    args.func(args)


if __name__ == "__main__":
    main()
