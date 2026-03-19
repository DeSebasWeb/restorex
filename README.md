# Backup Manager

Sistema automatizado de backups de bases de datos con deteccion inteligente de cambios, dashboard en tiempo real y arquitectura hexagonal.

![Dashboard](https://img.shields.io/badge/Dashboard-React%20%2B%20TypeScript-blue) ![API](https://img.shields.io/badge/API-Flask%20%2B%20SQLAlchemy-green) ![Docker](https://img.shields.io/badge/Deploy-Docker%20Compose-2496ED) ![License](https://img.shields.io/badge/License-MIT-yellow)

## Que hace

- Respalda automaticamente bases de datos PostgreSQL via SSH
- Detecta que bases de datos cambiaron y solo respalda esas (Smart Backup)
- Dashboard web profesional con progreso en tiempo real
- Genera reportes ejecutivos para presentar a gerencia
- Scheduler configurable (backup diario automatico)
- Modo claro y oscuro

## Arquitectura

```
backend/                          # Python - Arquitectura Hexagonal
├── src/
│   ├── domain/                   # Nucleo de negocio (0 dependencias)
│   │   ├── entities/             # BackupRecord, DatabaseInfo
│   │   ├── ports/                # Interfaces: RemoteExecutor, DatabaseInspector,
│   │   │                         #   FileTransfer, Filesystem, BackupRepository
│   │   ├── value_objects/        # BackupFormat, DbChangeStats, DbName (validated)
│   │   └── exceptions.py
│   │
│   ├── application/              # Casos de uso (solo depende de domain)
│   │   ├── services/             # BackupService, ReportService
│   │   └── dto/                  # BackupResultDTO, BackupSummaryDTO, DatabaseStatusDTO
│   │
│   ├── infrastructure/           # Adaptadores de salida
│   │   ├── adapters/             # SSHAdapter, PostgresAdapter, FilesystemAdapter
│   │   ├── database/             # SQLAlchemy models, engine, Alembic migrations
│   │   ├── persistence/          # PostgresBackupRepository, SettingsRepository, ProgressTracker
│   │   └── config.py             # Settings (DB > .env > defaults)
│   │
│   ├── entry_points/             # Adaptadores de entrada
│   │   ├── api/app.py            # Flask REST API
│   │   ├── cli.py                # Ejecucion por terminal
│   │   └── scheduler.py          # APScheduler (backup diario)
│   │
│   └── container.py              # Inyeccion de dependencias

frontend/                         # React + Vite + TypeScript + Tailwind
├── src/
│   ├── components/               # Sidebar, TopBar, StatCard, ProgressRing,
│   │                             #   StatusDot, Toast, BackupProgressBar
│   ├── pages/                    # Dashboard, Databases, History, Reports, Logs, Settings
│   ├── hooks/                    # useBackupStatus, useTheme
│   ├── services/api.ts           # Cliente HTTP tipado
│   ├── types/index.ts            # Interfaces TypeScript
│   └── utils/format.ts           # Utilidades compartidas
```

## Stack

| Capa | Tecnologia |
|---|---|
| Frontend | React 19, Vite 8, TypeScript, Tailwind CSS 4 |
| API | Flask 3, Flask-CORS |
| ORM | SQLAlchemy 2, Alembic |
| SSH/SFTP | Paramiko |
| Scheduler | APScheduler |
| DB Metadata | PostgreSQL (local) |
| Deploy | Docker Compose, nginx |

## Requisitos

- Docker Desktop
- PostgreSQL corriendo en tu maquina (para metadata de la app)
- Acceso SSH al servidor remoto donde estan las bases de datos
- OpenVPN o acceso de red al servidor

## Instalacion

```bash
# 1. Clonar
git clone https://github.com/DeSebasWeb/backup-manager.git
cd backup-manager

# 2. Configurar
cp backend/.env.example backend/.env
# Editar backend/.env con tu LOCAL_DB_URL (PostgreSQL local)

# 3. Crear directorio de backups
mkdir -p D:/Backups/PostgreSQL

# 4. Levantar
docker compose up --build -d

# 5. Abrir
# http://localhost:3000
```

## Configuracion

Todo se configura desde el dashboard en **Settings**:

| Campo | Descripcion |
|---|---|
| SSH Host | IP del servidor remoto (via VPN) |
| SSH User/Password | Credenciales SSH |
| PG Host | Host de PostgreSQL (usualmente `localhost` desde el server) |
| PG User/Password | Credenciales de PostgreSQL |
| Backup Dir | Directorio local para backups (`/backups/databases` en Docker) |
| Retention | Dias de retencion (default: 7) |
| Schedule | Hora del backup diario automatico (default: 23:00) |

## Flujo de backup

```
1. Conectar al servidor via SSH
2. Listar las N bases de datos (excluye template0, template1, postgres)
3. Por cada DB:
   a. Consultar pg_stat_user_tables para detectar cambios (I/U/D)
   b. Si nunca se ha respaldado → backup obligatorio
   c. Si ya tiene backup → solo si hay cambios
   d. pg_dump -Fc → .backup (comprimido, restauracion rapida)
   e. pg_dump -Fp → .sql (texto plano, legible)
   f. Descargar ambos via SFTP
   g. Limpiar archivos temporales del servidor
4. Rotar backups locales > N dias
5. Guardar historial en PostgreSQL local
```

## Seguridad

- Nombres de DB validados con `DbName` (regex `[a-zA-Z0-9_]`, max 63 chars)
- Todos los argumentos de shell escapados con `shlex.quote()`
- Limpieza de archivos remotos via `SFTP.remove()` (no shell `rm`)
- Path validation: solo permite borrar dentro de `/tmp/pg_backups/`
- Credenciales almacenadas en PostgreSQL local, enmascaradas en la UI
- CORS habilitado, nginx como reverse proxy

## API Endpoints

| Metodo | Ruta | Descripcion |
|---|---|---|
| GET | `/api/health` | Health check |
| GET | `/api/status` | Estado de todas las DBs |
| GET | `/api/history` | Historial de backups |
| POST | `/api/backup/run` | Iniciar backup (smart o force) |
| GET | `/api/backup/status` | Estado del backup + progreso |
| POST | `/api/scan` | Escanear DBs del servidor |
| GET | `/api/report` | Reporte ejecutivo |
| GET | `/api/logs` | Logs de la aplicacion |
| GET | `/api/settings` | Leer configuracion |
| POST | `/api/settings` | Guardar configuracion |
| POST | `/api/settings/test-connection` | Probar conexion SSH + PG |

## Screenshots

### Dashboard (Dark Mode)
- 26 bases de datos monitoreadas
- Deteccion de cambios en tiempo real (I/U/D)
- Anillo de cobertura de backup
- Historial de ejecuciones recientes

### Settings
- Configuracion de SSH y PostgreSQL desde la UI
- Test de conexion integrado
- Scheduler configurable

### Reports
- Reporte ejecutivo con KPIs
- Tasa de exito, almacenamiento usado
- Lista de DBs sin proteccion
- Boton de impresion

## Desarrollo local (sin Docker)

```bash
# Backend
cd backend
python -m venv venv
source venv/bin/activate  # o venv\Scripts\activate en Windows
pip install -r requirements.txt
cp .env.example .env
python src/entry_points/api/app.py

# Frontend
cd frontend
npm install
npm run dev
```

## Proximos pasos

- [ ] Soporte para MySQL, MongoDB, SQL Server
- [ ] Notificaciones (Slack, email, Telegram)
- [ ] Backup incremental
- [ ] Encriptacion de backups en reposo
- [ ] Autenticacion en el dashboard
- [ ] Restore desde la UI

---

Desarrollado con arquitectura hexagonal, buenas practicas de seguridad y mucho cafe.
