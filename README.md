<p align="center">
  <img src="https://img.shields.io/badge/-%F0%9F%9B%A1%EF%B8%8F%20Restorex-10b981?style=for-the-badge&labelColor=0a0b14" alt="Restorex" height="40" />
</p>

<h3 align="center">Automated Database Backup Engine</h3>

<p align="center">
  Smart change detection · Real-time dashboard · Docker-ready
</p>

<p align="center">
  <a href="#-quick-start">Quick Start</a> ·
  <a href="#-features">Features</a> ·
  <a href="#-architecture">Architecture</a> ·
  <a href="#-api">API</a> ·
  <a href="#-roadmap">Roadmap</a>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/React_19-61DAFB?style=flat&logo=react&logoColor=black" />
  <img src="https://img.shields.io/badge/Flask_3-000000?style=flat&logo=flask&logoColor=white" />
  <img src="https://img.shields.io/badge/PostgreSQL-4169E1?style=flat&logo=postgresql&logoColor=white" />
  <img src="https://img.shields.io/badge/Docker-2496ED?style=flat&logo=docker&logoColor=white" />
  <img src="https://img.shields.io/badge/TypeScript-3178C6?style=flat&logo=typescript&logoColor=white" />
  <img src="https://img.shields.io/badge/Tailwind_CSS-06B6D4?style=flat&logo=tailwindcss&logoColor=white" />
  <img src="https://img.shields.io/badge/License-MIT-10b981?style=flat" />
</p>

---

## The Problem

You manage production databases. You know you should back them up daily. But you forget, or the script breaks silently, or you waste time backing up databases that haven't changed. Restorex fixes all of that.

## The Solution

Restorex connects to your server via SSH, detects which databases actually changed, backs up only those, and shows you everything in a professional dashboard. Set it up once, and it runs automatically.

---

## Quick Start

```bash
git clone https://github.com/DeSebasWeb/restorex.git
cd backup-manager
cp backend/.env.example backend/.env    # Edit with your local DB URL
docker compose up --build -d
```

Open **http://localhost:3000** → Go to **Settings** → Enter your server credentials → **Test Connection** → **Scan DBs** → **Smart Backup**

> **Requirements:** Docker Desktop + PostgreSQL running locally (for app metadata)

---

## Features

### Smart Change Detection
Queries `pg_stat_user_tables` to detect INSERTs, UPDATEs, and DELETEs since the last backup. Databases with no changes are skipped automatically. New databases are always backed up on first run.

### Real-time Dashboard
Professional React UI with live progress bars, download percentages, backup coverage ring, database overview table, and recent run history. Dark and light mode included.

### Dual Format Output
Every backup generates two files:
- **`.backup`** — PostgreSQL custom format. Compressed, fast to restore, supports parallel restore
- **`.sql.gz`** — Gzipped plain SQL. Human-readable, portable. Optional (configurable in Settings)

### Automatic Scheduling
Built-in APScheduler runs backups daily at your configured time. Manual backup available anytime via dashboard or CLI.

### Executive Reports
Generate reports with KPIs: success rate, storage used, databases without protection. Print-ready for management presentations.

### Secure by Design
- SSH tunnels with host key verification (saved to `known_hosts`)
- All shell arguments escaped with `shlex.quote()`
- Remote file cleanup via SFTP (not shell `rm`)
- Path validation — only deletes inside `/tmp/pg_backups/`
- Database names validated with `DbName` value object (regex, max 63 chars)
- Credentials stored in local PostgreSQL, masked in UI

### Full Configuration from UI
No need to edit `.env` files. Configure SSH, PostgreSQL, backup directory, retention days, schedule time, and SQL generation — all from the Settings page. Test connection with one click.

---

## Architecture

Built with **hexagonal architecture** (ports & adapters). The domain layer has zero external dependencies.

```
backend/src/
├── domain/                    # Business core — 0 dependencies
│   ├── entities/              # BackupRecord, DatabaseInfo
│   ├── ports/                 # Interfaces (RemoteExecutor, FileTransfer,
│   │                          #   DatabaseInspector, Filesystem, BackupRepository)
│   ├── value_objects/         # BackupFormat, DbChangeStats, DbName
│   └── exceptions.py
│
├── application/               # Use cases — depends only on domain
│   ├── services/              # BackupService, ReportService
│   └── dto/                   # BackupResultDTO, BackupSummaryDTO, DatabaseStatusDTO
│
├── infrastructure/            # Output adapters — implements ports
│   ├── adapters/              # SSHAdapter, PostgresAdapter, FilesystemAdapter
│   ├── database/              # SQLAlchemy models, engine, auto-migrations
│   ├── persistence/           # PostgresBackupRepository, SettingsRepository,
│   │                          #   ProgressTracker
│   └── config.py              # Settings (DB > .env > defaults)
│
├── entry_points/              # Input adapters
│   ├── api/app.py             # Flask REST API
│   ├── cli.py                 # Terminal execution
│   └── scheduler.py           # APScheduler (daily backup)
│
└── container.py               # Dependency injection

frontend/src/
├── components/                # Sidebar, TopBar, StatCard, ProgressRing,
│                              #   BackupProgressBar, StatusDot, Toast
├── pages/                     # Dashboard, Databases, History, Reports, Logs, Settings
├── hooks/                     # useBackupStatus, useTheme
├── services/api.ts            # Typed HTTP client with timeout + error handling
├── types/index.ts             # TypeScript interfaces
└── utils/format.ts            # Shared formatters
```

### Tech Stack

| Layer | Technology |
|---|---|
| **Frontend** | React 19, Vite 8, TypeScript, Tailwind CSS 4 |
| **API** | Flask 3, Flask-CORS |
| **ORM** | SQLAlchemy 2, auto-migrations |
| **SSH/SFTP** | Paramiko (keepalive, host key verification) |
| **Scheduler** | APScheduler |
| **Metadata DB** | PostgreSQL (local) |
| **Deploy** | Docker Compose, nginx |

---

## How It Works

```
                         Your PC (Docker)
                    ┌──────────────────────────┐
                    │  React Dashboard (:3000)  │
                    │         ↕ API             │
                    │  Flask Backend (:5000)    │
                    │         ↕ SSH             │
                    └──────────┬───────────────┘
                               │ VPN + SSH
                    ┌──────────▼───────────────┐
                    │  Remote Linux Server      │
                    │  ├── pg_dump (runs here)  │
                    │  └── SFTP transfer ↑      │
                    └──────────────────────────┘
                               │
                    ┌──────────▼───────────────┐
                    │  D:/Backups/PostgreSQL    │
                    │  ├── db_name_1/           │
                    │  │   ├── 2026-03-20.backup│
                    │  │   └── 2026-03-20.sql.gz│
                    │  ├── db_name_2/           │
                    │  └── ... (auto-rotated)   │
                    └──────────────────────────┘
```

**Backup flow:**

1. Connect to server via SSH (with keepalive every 30s)
2. List databases (excludes `template0`, `template1`, `postgres`)
3. For each database:
   - Query `pg_stat_user_tables` for change stats (I/U/D)
   - If never backed up → backup (always)
   - If already backed up → only if changes detected
   - Generate `.backup` via `pg_dump -Fc`
   - Generate `.sql.gz` via `pg_dump -Fp | gzip` (optional)
   - Download via SFTP with real-time progress
   - Clean up remote temp files
4. Rotate local backups older than retention period
5. Save run history to local PostgreSQL

---

## API

All endpoints return JSON. The frontend communicates exclusively through this API.

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/health` | Health check + configuration status |
| `GET` | `/api/status` | All databases with stats, sizes, backup status |
| `GET` | `/api/history` | Backup run history (last 50 runs) |
| `POST` | `/api/backup/run` | Start backup (`{ "force": false }`) |
| `GET` | `/api/backup/status` | Running state + live progress (DB, step, download %) |
| `POST` | `/api/scan` | Discover databases on remote server |
| `GET` | `/api/report` | Executive report with KPIs |
| `GET` | `/api/logs` | Application logs (last 100 lines) |
| `GET` | `/api/settings` | Current configuration (passwords masked) |
| `POST` | `/api/settings` | Save configuration + rebuild DI container |
| `POST` | `/api/settings/test-connection` | Test SSH + PostgreSQL connectivity |

---

## Configuration

Everything is configurable from the dashboard (**Settings** page):

| Setting | Description | Default |
|---|---|---|
| SSH Host | Remote server IP (via VPN) | — |
| SSH Port | SSH port | `22` |
| SSH User / Password | SSH credentials | — |
| PG Host | PostgreSQL host (from server perspective) | `localhost` |
| PG Port | PostgreSQL port | `5432` |
| PG User / Password | Database credentials | — |
| Backup Directory | Local backup path (inside Docker) | `/backups/databases` |
| Remote Temp Dir | Temp directory on remote server | `/tmp/pg_backups` |
| Retention Days | Auto-delete backups older than N days | `7` |
| Schedule Hour/Minute | Daily automatic backup time | `23:00` |
| Generate SQL | Create `.sql.gz` in addition to `.backup` | `true` |

---

## Local Development

```bash
# Backend
cd backend
python -m venv venv
source venv/bin/activate       # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env           # Edit LOCAL_DB_URL
python src/entry_points/api/app.py

# Frontend (separate terminal)
cd frontend
npm install
npm run dev
```

---

## Roadmap

- [ ] Multi-engine support (MySQL, MongoDB, SQL Server)
- [ ] Notifications (Slack, Email, Telegram)
- [ ] Cloud backup destinations (S3, Google Cloud Storage)
- [ ] Multi-server monitoring from single dashboard
- [ ] MCP server for AI agent integration
- [ ] Backup encryption at rest
- [ ] Authentication & team access
- [ ] Restore from UI
- [ ] Incremental backups

---

## Contributing

Pull requests are welcome. For major changes, please open an issue first to discuss what you would like to change.

## License

[MIT](LICENSE)

---

<p align="center">
  <sub>Built with hexagonal architecture, secure SSH tunnels, and lots of coffee.</sub>
</p>
