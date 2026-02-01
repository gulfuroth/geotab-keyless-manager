# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Geotab NFC Keyless Manager - A Flask web application for managing Geotab virtual keys across vehicle fleets. Built for Telefónica Tech / Vecttor client.

## Commands

Install dependencies:
```bash
pip install flask requests
```

Run the application:
```bash
python app.py
```
The app auto-opens a browser to http://127.0.0.1:5000

Build standalone executable (Windows):
```bash
pyinstaller app.spec
```
Output goes to `dist/app.exe`

## Architecture

**Single-file Flask app** (`app.py`) with embedded SQLite database.

### Backend (app.py)

- **Flask routes** serve the SPA and proxy requests to Geotab Keyless API (`https://keyless.geotab.com/api`)
- **SQLite database** (`vehicles.db`) stores:
  - `vehicles`: serial_number, description, tenant_db (composite PK: serial + tenant)
  - `virtual_keys`: vk_id, serial_number, tenant_db, user_ref
  - `settings`: key-value pairs for persisting credentials
  - `logs`: audit trail of key operations
- **Authentication**: Tokens stored in cookies (`access_token`, `tenant`)
- **Multi-tenant support**: Each Geotab database is isolated via `tenant_db` column
- **PyInstaller compatible**: Uses `get_resource_path()` for bundled resources

### Frontend (templates/index.html)

- Single-page app using Tailwind CSS (CDN)
- No build step required
- Key features:
  - Connect to Geotab tenant with service account credentials
  - Add/remove vehicles (GO9 devices) by serial number
  - Create virtual keys in bulk with JSON template
  - Sync keys from Geotab API
  - Import vehicles from CSV

### API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/auth` | POST | Authenticate with Geotab |
| `/vehicles` | GET/POST | List or add vehicles |
| `/vehicles/<serial>` | DELETE | Remove vehicle locally |
| `/sync-key/<serial>` | GET | Sync keys from Geotab |
| `/create-key` | POST | Create virtual key via Geotab API |
| `/import-csv` | POST | Bulk import vehicles |
| `/settings` | GET/POST | Persist/retrieve settings |
| `/logs` | GET | Get audit logs |

### CSV Import Format

```
SERIAL_NUMBER,DESCRIPTION[,TENANT_DB]
GAW4MAN8YZNY,8060LYK
G93XV1KAKB6M,veh1,custom_tenant
```

## Key Files

- `app.py` - Complete application code
- `templates/index.html` - Web UI
- `vehicles.db` - SQLite database (auto-created on first run)
- `fleet_manager.log` - Application logs
- `app.spec` - PyInstaller configuration for building exe
