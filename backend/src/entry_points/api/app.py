"""Entry Point: Flask REST API for the React frontend."""

import logging
import shlex
import sys
import threading
from pathlib import Path

from flask import Flask, jsonify, request
from flask_cors import CORS

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent.parent))

from src.container import init_container
from src.entry_points.scheduler import init_scheduler, shutdown_scheduler
from src.infrastructure.config import Settings
from src.infrastructure.database import init_db
from src.infrastructure.persistence.postgres_settings_repository import PostgresSettingsRepository

# Force unbuffered output for Docker
sys.stdout.reconfigure(line_buffering=True)

# Logging — set up handlers on the root logger
Settings.LOG_DIR.mkdir(parents=True, exist_ok=True)
_fmt = logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")
_fh = logging.FileHandler(Settings.LOG_DIR / "app.log", encoding="utf-8")
_fh.setFormatter(_fmt)
_sh = logging.StreamHandler(sys.stdout)
_sh.setFormatter(_fmt)

_root = logging.getLogger()
_root.setLevel(logging.INFO)
_root.addHandler(_fh)
_root.addHandler(_sh)

# Also explicitly configure the 'src' logger tree (all our modules)
_src_logger = logging.getLogger("src")
_src_logger.setLevel(logging.INFO)
_src_logger.propagate = True

logger = logging.getLogger(__name__)

# Flask app
app = Flask(__name__)
app.secret_key = Settings.FLASK_SECRET_KEY
CORS(app)

# Reduce werkzeug noise
logging.getLogger("werkzeug").setLevel(logging.WARNING)

_backup_lock = threading.Lock()
_backup_running = False

# Initialize database and container
try:
    init_db(Settings.LOCAL_DB_URL)
    Settings.reload()
except Exception as e:
    logger.error("Database initialization failed: %s", e)
    logger.error("The app will start but most features will not work until the database is available.")

_container = init_container()
_settings_repo = PostgresSettingsRepository()


def _rebuild():
    """Reload settings and rebuild the DI container."""
    global _container
    Settings.reload()
    _container = init_container()
    # Restart scheduler with new settings
    if Settings.is_configured():
        init_scheduler(
            backup_fn=_container.backup_service.run_full_backup,
            hour=Settings.SCHEDULER_HOUR,
            minute=Settings.SCHEDULER_MINUTE,
        )
    logger.info("Container rebuilt with new settings.")


# ── Health ──────────────────────────────────────────────────────

@app.route("/api/health")
def health():
    return jsonify({
        "status": "ok",
        "service": "restorex-api",
        "configured": Settings.is_configured(),
    })


# ── Settings ────────────────────────────────────────────────────

@app.route("/api/settings", methods=["GET"])
def api_get_settings():
    try:
        masked = _settings_repo.get_all_masked(Settings.get_env_defaults())
        # Normalize types: DB stores everything as strings, frontend expects correct types
        _bool_keys = {"GENERATE_SQL"}
        _int_keys = {"SSH_PORT", "PG_PORT", "RETENTION_DAYS", "SCHEDULER_HOUR", "SCHEDULER_MINUTE", "PARALLEL_WORKERS"}
        for k in _bool_keys:
            if k in masked and isinstance(masked[k], str):
                masked[k] = masked[k].lower() in ("true", "1", "yes")
        for k in _int_keys:
            if k in masked:
                try:
                    masked[k] = int(masked[k])
                except (ValueError, TypeError):
                    pass
        return jsonify({
            "settings": masked,
            "configured": Settings.is_configured(),
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/settings", methods=["POST"])
def api_save_settings():
    try:
        updates = request.json
        if not updates:
            return jsonify({"error": "No settings provided"}), 400

        _settings_repo.save(updates)
        _rebuild()

        return jsonify({
            "message": "Settings saved and applied",
            "configured": Settings.is_configured(),
        })
    except Exception as e:
        logger.exception("Failed to save settings")
        return jsonify({"error": str(e)}), 500


@app.route("/api/settings/test-connection", methods=["POST"])
def api_test_connection():
    try:
        if request.is_json and request.json:
            _settings_repo.save(request.json)
            _rebuild()

        ssh = _container.ssh_adapter
        ssh.connect()

        stdout, stderr, code = ssh.execute(
            f"PGPASSWORD={shlex.quote(Settings.PG_PASSWORD)} psql "
            f"-h {shlex.quote(Settings.PG_HOST)} -p {shlex.quote(str(Settings.PG_PORT))} "
            f"-U {shlex.quote(Settings.PG_USER)} -d postgres -t -A "
            f"-c 'SELECT version();'"
        )

        ssh.disconnect()

        if code != 0:
            return jsonify({
                "success": False, "ssh": True, "postgres": False,
                "error": f"PostgreSQL error: {stderr}",
            })

        return jsonify({
            "success": True, "ssh": True, "postgres": True,
            "pg_version": stdout.strip(),
            "message": "Connection successful!",
        })
    except Exception as e:
        return jsonify({
            "success": False, "ssh": False, "postgres": False,
            "error": str(e),
        })


# ── Status ──────────────────────────────────────────────────────

@app.route("/api/status")
def api_status():
    try:
        statuses = _container.report_service.get_all_database_statuses()
        with _backup_lock:
            running = _backup_running
        return jsonify({
            "databases": [s.to_dict() for s in statuses],
            "total_dbs": len(statuses),
            "backup_running": running,
            "retention_days": Settings.RETENTION_DAYS,
            "configured": Settings.is_configured(),
        })
    except Exception as e:
        logger.exception("Error in /api/status")
        return jsonify({"error": str(e)}), 500


# ── History ─────────────────────────────────────────────────────

@app.route("/api/history")
def api_history():
    try:
        history = _container.backup_repository.get_history(limit=50)
        return jsonify({"history": history})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ── Backup ──────────────────────────────────────────────────────

@app.route("/api/backup/run", methods=["POST"])
def api_run_backup():
    global _backup_running

    if not Settings.is_configured():
        return jsonify({"error": "Server not configured. Go to Settings first."}), 400

    with _backup_lock:
        if _backup_running:
            return jsonify({"error": "A backup is already running"}), 409
        _backup_running = True

    force = request.json.get("force", False) if request.is_json else False

    def _run():
        global _backup_running
        tracker = _container.progress_tracker
        try:
            tracker.start(total_dbs=0)
            summary = _container.backup_service.run_full_backup(force=force)

            # Send notifications for backup result
            try:
                _container.notification_service.notify_backup_result(summary.to_dict())
            except Exception as notify_err:
                logger.warning("Notification delivery failed: %s", notify_err)
        except Exception as e:
            logger.exception("Backup thread failed: %s", e)

            # Notify about fatal errors (SSH failure, connection lost, etc.)
            try:
                _container.notification_service.notify_backup_result({
                    "backed_up": 0,
                    "failed": 1,
                    "skipped": 0,
                    "total_dbs": 0,
                    "started_at": "",
                    "finished_at": "",
                    "results": [],
                    "errors": [{"db_name": "SYSTEM", "error": str(e)}],
                })
            except Exception:
                pass  # Don't let notification failure mask the original error
        finally:
            tracker.finish()
            with _backup_lock:
                _backup_running = False

    threading.Thread(target=_run, daemon=True).start()
    return jsonify({"message": "Backup started", "force": force})


@app.route("/api/backup/status")
def api_backup_running():
    from src.infrastructure.persistence.progress_tracker import ProgressTracker
    progress = ProgressTracker.get_progress()
    with _backup_lock:
        running = _backup_running
    return jsonify({
        "running": running,
        "progress": progress,
    })


# ── Scan ────────────────────────────────────────────────────────

@app.route("/api/scan", methods=["POST"])
def api_scan():
    if not Settings.is_configured():
        return jsonify({"error": "Server not configured. Go to Settings first."}), 400
    try:
        databases = _container.backup_service.scan_databases()
        return jsonify({"message": f"Scanned {len(databases)} databases", "count": len(databases)})
    except Exception as e:
        logger.exception("Scan failed")
        return jsonify({"error": str(e)}), 500


# ── Report ──────────────────────────────────────────────────────

@app.route("/api/report")
def api_report():
    try:
        report = _container.report_service.generate_report()
        return jsonify(report)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ── Notifications ──────────────────────────────────────────────

@app.route("/api/notifications", methods=["GET"])
def api_get_notifications():
    try:
        channels = _container.notification_repository.get_all_channels_masked()
        return jsonify({"channels": channels})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/notifications/<channel_name>", methods=["POST"])
def api_save_notification(channel_name: str):
    try:
        data = request.json
        if not data:
            return jsonify({"error": "No data provided"}), 400
        _container.notification_repository.save_channel(channel_name, data)
        return jsonify({"message": f"{channel_name} configuration saved"})
    except Exception as e:
        logger.exception("Failed to save notification config")
        return jsonify({"error": str(e)}), 500


@app.route("/api/notifications/<channel_name>/test", methods=["POST"])
def api_test_notification(channel_name: str):
    try:
        success, message = _container.notification_service.test_channel(channel_name)
        return jsonify({"success": success, "message": message})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


# ── Logs ────────────────────────────────────────────────────────

@app.route("/api/logs")
def api_logs():
    try:
        logs = _container.report_service.get_logs(lines=100)
        return jsonify({"logs": logs})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ── Bootstrap (runs on import — needed for both gunicorn and __main__) ──

Settings.DATA_DIR.mkdir(parents=True, exist_ok=True)
Settings.LOG_DIR.mkdir(parents=True, exist_ok=True)

if Settings.is_configured():
    init_scheduler(
        backup_fn=_container.backup_service.run_full_backup,
        hour=Settings.SCHEDULER_HOUR,
        minute=Settings.SCHEDULER_MINUTE,
    )


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=Settings.FLASK_PORT, debug=False)
