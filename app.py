import sqlite3, requests, csv, io, json, os, sys, logging, webbrowser, uuid
from threading import Timer
from datetime import datetime
from flask import Flask, render_template, request, jsonify, make_response

def get_resource_path(relative_path):
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.abspath("."), relative_path)

app = Flask(__name__, template_folder=get_resource_path("templates"))
GEOTAB_BASE_URL = "https://keyless.geotab.com/api"

exe_dir = os.path.dirname(sys.executable if hasattr(sys, 'frozen') else os.path.abspath(__file__))
log_file_path = os.path.join(exe_dir, "fleet_manager.log")
db_path = os.path.join(exe_dir, "vehicles.db")

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[logging.FileHandler(log_file_path), logging.StreamHandler()]
)

def init_db():
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    # Crear tablas si no existen
    c.execute('''CREATE TABLE IF NOT EXISTS vehicles
                 (serial_number TEXT, description TEXT, tenant_db TEXT, faulty INTEGER DEFAULT 0, PRIMARY KEY(serial_number, tenant_db))''')
    c.execute('''CREATE TABLE IF NOT EXISTS virtual_keys
                 (vk_id TEXT PRIMARY KEY, serial_number TEXT, tenant_db TEXT, user_ref TEXT, expires_at INTEGER)''')
    c.execute('''CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS logs
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, timestamp TEXT, user TEXT, action TEXT, serial TEXT, parameters TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS vk_templates
                 (id TEXT PRIMARY KEY, tenant_db TEXT NOT NULL, name TEXT NOT NULL,
                  user_ref TEXT, vk_config TEXT NOT NULL, nfc_tags TEXT NOT NULL, duration_months INTEGER DEFAULT 12,
                  version INTEGER DEFAULT 1, previous_version_id TEXT, is_active INTEGER DEFAULT 1,
                  created_at TEXT NOT NULL, created_by TEXT, UNIQUE(tenant_db, name, version))''')
    
    # MIGRACIÓN: Verificar si falta la columna tenant_db en la tabla vehicles (para dbs antiguas)
    c.execute("PRAGMA table_info(vehicles)")
    columns = [info[1] for info in c.fetchall()]
    if 'tenant_db' not in columns:
        logging.info("Migrando base de datos: Añadiendo columna tenant_db...")
        try:
            c.execute("ALTER TABLE vehicles ADD COLUMN tenant_db TEXT DEFAULT 'default'")
        except Exception as e:
            logging.error(f"Error en migración: {e}")

    # MIGRACIÓN: Añadir columna expires_at a virtual_keys
    c.execute("PRAGMA table_info(virtual_keys)")
    vk_columns = [info[1] for info in c.fetchall()]
    if 'expires_at' not in vk_columns:
        logging.info("Migrando base de datos: Añadiendo columna expires_at...")
        try:
            c.execute("ALTER TABLE virtual_keys ADD COLUMN expires_at INTEGER")
        except Exception as e:
            logging.error(f"Error en migración expires_at: {e}")

    # MIGRACIÓN: Añadir columna faulty a vehicles
    c.execute("PRAGMA table_info(vehicles)")
    v_columns = [info[1] for info in c.fetchall()]
    if 'faulty' not in v_columns:
        logging.info("Migrando base de datos: Añadiendo columna faulty...")
        try:
            c.execute("ALTER TABLE vehicles ADD COLUMN faulty INTEGER DEFAULT 0")
        except Exception as e:
            logging.error(f"Error en migración faulty: {e}")

    # MIGRACIÓN: Añadir columna user_ref a vk_templates
    c.execute("PRAGMA table_info(vk_templates)")
    tpl_columns = [info[1] for info in c.fetchall()]
    if tpl_columns and 'user_ref' not in tpl_columns:
        logging.info("Migrando base de datos: Añadiendo columna user_ref a vk_templates...")
        try:
            c.execute("ALTER TABLE vk_templates ADD COLUMN user_ref TEXT")
        except Exception as e:
            logging.error(f"Error en migración user_ref: {e}")

    conn.commit()
    conn.close()
    logging.info("Base de datos lista.")

def add_log(user, action, serial, params):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    conn = sqlite3.connect(db_path)
    conn.execute("INSERT INTO logs (timestamp, user, action, serial, parameters) VALUES (?, ?, ?, ?, ?)",
                 (ts, user, action, serial, json.dumps(params)))
    conn.commit()
    conn.close()

@app.route('/')
def index(): return render_template('index.html')

@app.route('/settings', methods=['GET', 'POST'])
def manage_settings():
    conn = sqlite3.connect(db_path)
    if request.method == 'POST':
        for k, v in request.json.items():
            conn.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", (k, v))
        conn.commit()
        return jsonify({"status": "saved"})
    cur = conn.cursor()
    cur.execute("SELECT * FROM settings")
    settings = {r[0]: r[1] for r in cur.fetchall()}
    conn.close()
    return jsonify(settings)

@app.route('/auth', methods=['POST'])
def authenticate():
    res = requests.post(f"{GEOTAB_BASE_URL}/auth", json=request.json)
    if res.status_code == 200:
        resp = make_response(jsonify({"status": "success"}))
        resp.set_cookie('access_token', res.json().get("accessToken"), httponly=True)
        resp.set_cookie('tenant', request.json['database'])
        logging.info(f"Login OK: {request.json['username']} -> {request.json['database']}")
        add_log(request.json['username'], "LOGIN", request.json['database'], {"status": "success"})
        return resp
    add_log(request.json.get('username', 'unknown'), "LOGIN_FAILED", request.json.get('database', 'unknown'), {"status": res.status_code})
    return jsonify({"error": "Auth failed"}), 401

@app.route('/vehicles', methods=['GET', 'POST'])
def manage_vehicles():
    tenant = request.args.get('tenant')
    if not tenant: return jsonify([])
    conn = sqlite3.connect(db_path)
    if request.method == 'POST':
        v = request.json
        conn.execute("INSERT OR REPLACE INTO vehicles (serial_number, description, tenant_db) VALUES (?, ?, ?)",
                     (v['serial'].strip(), v['desc'].strip(), tenant))
        conn.commit()
        add_log(request.cookies.get('user_email'), "ADD_DEVICE", v['serial'].strip(), {"desc": v['desc'].strip()})
    
    cur = conn.cursor()
    cur.execute("SELECT serial_number, description, faulty FROM vehicles WHERE tenant_db = ?", (tenant,))
    v_rows = cur.fetchall()
    vehicles = []
    for vr in v_rows:
        cur.execute("SELECT vk_id, user_ref, expires_at FROM virtual_keys WHERE serial_number = ? AND tenant_db = ?", (vr[0], tenant))
        keys = [{"id": kr[0], "ref": kr[1], "expires": kr[2]} for kr in cur.fetchall()]
        vehicles.append({"serial": vr[0], "desc": vr[1], "keys": keys, "faulty": bool(vr[2])})
    conn.close()
    return jsonify(vehicles)

@app.route('/sync-key/<serial>', methods=['GET'])
def sync_key(serial):
    token, tenant = request.cookies.get('access_token'), request.cookies.get('tenant')
    if not token: return jsonify({"error": "No session"}), 401
    res = requests.get(f"{GEOTAB_BASE_URL}/tenants/{tenant}/devices/{serial}/virtual-keys?virtualKeysFilter=Stored",
                        headers={"Authorization": f"Bearer {token}"})
    if res.status_code == 200:
        conn = sqlite3.connect(db_path)
        conn.execute("DELETE FROM virtual_keys WHERE serial_number = ? AND tenant_db = ?", (serial, tenant))
        keys_synced = 0
        for vk in res.json().get('virtualKeys', []):
            expires_at = vk.get('endingTimestamp')
            conn.execute("INSERT INTO virtual_keys (vk_id, serial_number, tenant_db, user_ref, expires_at) VALUES (?, ?, ?, ?, ?)",
                         (vk['virtualKeyId'], serial, tenant, vk.get('userReference'), expires_at))
            keys_synced += 1
        # Clear faulty status on successful sync
        conn.execute("UPDATE vehicles SET faulty = 0 WHERE serial_number = ? AND tenant_db = ?", (serial, tenant))
        conn.commit()
        conn.close()
        add_log(request.cookies.get('user_email'), "SYNC", serial, {"keys_found": keys_synced})
        return jsonify(res.json())
    else:
        # Mark device as faulty
        conn = sqlite3.connect(db_path)
        conn.execute("UPDATE vehicles SET faulty = 1 WHERE serial_number = ? AND tenant_db = ?", (serial, tenant))
        conn.commit()
        conn.close()
        add_log(request.cookies.get('user_email'), "SYNC_ERROR", serial, {"status": res.status_code, "error": res.text[:200]})
        return jsonify({"error": "Sync failed", "details": res.text}), res.status_code

@app.route('/create-key', methods=['POST'])
def create_key():
    token, tenant = request.cookies.get('access_token'), request.cookies.get('tenant')
    if not token: return jsonify({"error": "No session"}), 401
    payload = request.json
    serial = payload.pop('serialNumber')

    # Extract template metadata (not sent to Geotab API)
    template_id = payload.pop('_template_id', None)
    template_name = payload.pop('_template_name', None)
    template_version = payload.pop('_template_version', None)

    res = requests.post(f"{GEOTAB_BASE_URL}/tenants/{tenant}/devices/{serial}/virtual-keys",
                        json=payload, headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"})
    if res.status_code == 200:
        vk = res.json()
        conn = sqlite3.connect(db_path)
        expires_at = vk.get('endingTimestamp')
        conn.execute("INSERT INTO virtual_keys (vk_id, serial_number, tenant_db, user_ref, expires_at) VALUES (?, ?, ?, ?, ?)",
                     (vk['virtualKeyId'], serial, tenant, vk.get('userReference'), expires_at))
        # Clear faulty status on successful create
        conn.execute("UPDATE vehicles SET faulty = 0 WHERE serial_number = ? AND tenant_db = ?", (serial, tenant))
        conn.commit()
        conn.close()

        # Enhanced logging with template info
        log_params = {"userRef": payload.get('userReference')}
        if template_id:
            log_params["template_id"] = template_id
            log_params["template_name"] = template_name
            log_params["template_version"] = template_version
        add_log(request.cookies.get('user_email'), "CREATE_VK", serial, log_params)
    else:
        # Mark device as faulty on 404 (device not found) or other errors
        conn = sqlite3.connect(db_path)
        conn.execute("UPDATE vehicles SET faulty = 1 WHERE serial_number = ? AND tenant_db = ?", (serial, tenant))
        conn.commit()
        conn.close()
        add_log(request.cookies.get('user_email'), "CREATE_VK_ERROR", serial, {"status": res.status_code, "error": res.text[:200]})
    return jsonify(res.json()), res.status_code

@app.route('/delete-key/<serial>/<vk_id>', methods=['DELETE'])
def delete_key(serial, vk_id):
    """Delete a single virtual key from a device"""
    token, tenant = request.cookies.get('access_token'), request.cookies.get('tenant')
    if not token: return jsonify({"error": "No session"}), 401

    # Delete from Geotab API
    res = requests.delete(f"{GEOTAB_BASE_URL}/tenants/{tenant}/devices/{serial}/virtual-keys/{vk_id}",
                          headers={"Authorization": f"Bearer {token}"})

    if res.status_code in [200, 202, 204]:
        # Delete from local DB
        conn = sqlite3.connect(db_path)
        conn.execute("DELETE FROM virtual_keys WHERE vk_id = ? AND serial_number = ? AND tenant_db = ?",
                     (vk_id, serial, tenant))
        conn.commit()
        conn.close()
        add_log(request.cookies.get('user_email'), "DELETE_VK", serial, {"vk_id": vk_id})
        return jsonify({"status": "deleted"})

    add_log(request.cookies.get('user_email'), "DELETE_VK_ERROR", serial, {"vk_id": vk_id, "status": res.status_code})
    return jsonify({"error": "Failed to delete key", "details": res.text}), res.status_code

@app.route('/delete-all-keys/<serial>', methods=['DELETE'])
def delete_all_keys(serial):
    """Delete all virtual keys from a single device"""
    token, tenant = request.cookies.get('access_token'), request.cookies.get('tenant')
    if not token: return jsonify({"error": "No session"}), 401

    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute("SELECT vk_id FROM virtual_keys WHERE serial_number = ? AND tenant_db = ?", (serial, tenant))
    keys = cur.fetchall()

    deleted = 0
    errors = []
    for (vk_id,) in keys:
        res = requests.delete(f"{GEOTAB_BASE_URL}/tenants/{tenant}/devices/{serial}/virtual-keys/{vk_id}",
                              headers={"Authorization": f"Bearer {token}"})
        if res.status_code in [200, 202, 204]:
            conn.execute("DELETE FROM virtual_keys WHERE vk_id = ?", (vk_id,))
            deleted += 1
        else:
            errors.append({"vk_id": vk_id, "error": res.text})

    conn.commit()
    conn.close()

    if deleted > 0:
        add_log(request.cookies.get('user_email'), "DELETE_ALL_VK", serial, {"deleted": deleted, "errors": len(errors)})

    return jsonify({"status": "completed", "deleted": deleted, "errors": errors})

@app.route('/delete-keys-bulk', methods=['POST'])
def delete_keys_bulk():
    """Delete all virtual keys from multiple selected devices"""
    token, tenant = request.cookies.get('access_token'), request.cookies.get('tenant')
    if not token: return jsonify({"error": "No session"}), 401

    serials = request.json.get('serials', [])
    if not serials: return jsonify({"error": "No devices selected"}), 400

    results = {"total_deleted": 0, "devices_processed": 0, "errors": []}

    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    for serial in serials:
        cur.execute("SELECT vk_id FROM virtual_keys WHERE serial_number = ? AND tenant_db = ?", (serial, tenant))
        keys = cur.fetchall()

        for (vk_id,) in keys:
            res = requests.delete(f"{GEOTAB_BASE_URL}/tenants/{tenant}/devices/{serial}/virtual-keys/{vk_id}",
                                  headers={"Authorization": f"Bearer {token}"})
            if res.status_code in [200, 202, 204]:
                conn.execute("DELETE FROM virtual_keys WHERE vk_id = ?", (vk_id,))
                results["total_deleted"] += 1
            else:
                results["errors"].append({"serial": serial, "vk_id": vk_id, "error": res.text})

        results["devices_processed"] += 1

    conn.commit()
    conn.close()

    if results["total_deleted"] > 0:
        add_log(request.cookies.get('user_email'), "BULK_DELETE_VK", ",".join(serials),
                {"deleted": results["total_deleted"], "devices": len(serials)})

    return jsonify(results)

@app.route('/import-csv', methods=['POST'])
def import_csv():
    tenant = request.cookies.get('tenant') or request.args.get('tenant')
    if not tenant: return jsonify({"error": "Defina una Database primero"}), 400
    file = request.files['file']
    stream = io.StringIO(file.stream.read().decode("UTF8"))
    conn = sqlite3.connect(db_path)
    imported = 0
    for row in csv.reader(stream):
        if len(row) >= 2:
            v_tenant = row[2].strip() if len(row) >= 3 else tenant
            conn.execute("INSERT OR REPLACE INTO vehicles (serial_number, description, tenant_db) VALUES (?, ?, ?)",
                         (row[0].strip(), row[1].strip(), v_tenant))
            imported += 1
    conn.commit()
    conn.close()
    add_log(request.cookies.get('user_email'), "IMPORT_CSV", f"{imported} devices", {"count": imported})
    return jsonify({"status": "done", "imported": imported})

@app.route('/vehicles/<serial>', methods=['DELETE'])
def delete_vehicle_local(serial):
    tenant = request.cookies.get('tenant')
    conn = sqlite3.connect(db_path)
    conn.execute("DELETE FROM vehicles WHERE serial_number = ? AND tenant_db = ?", (serial, tenant))
    conn.execute("DELETE FROM virtual_keys WHERE serial_number = ? AND tenant_db = ?", (serial, tenant))
    conn.commit()
    conn.close()
    add_log(request.cookies.get('user_email'), "DELETE_DEVICE", serial, {})
    return jsonify({"status": "deleted"})

@app.route('/vehicles-bulk', methods=['DELETE'])
def delete_vehicles_bulk():
    """Delete multiple vehicles from local database"""
    tenant = request.cookies.get('tenant')
    serials = request.json.get('serials', [])
    if not serials: return jsonify({"error": "No devices selected"}), 400

    conn = sqlite3.connect(db_path)
    deleted = 0
    for serial in serials:
        conn.execute("DELETE FROM vehicles WHERE serial_number = ? AND tenant_db = ?", (serial, tenant))
        conn.execute("DELETE FROM virtual_keys WHERE serial_number = ? AND tenant_db = ?", (serial, tenant))
        deleted += 1
    conn.commit()
    conn.close()

    add_log(request.cookies.get('user_email'), "BULK_DELETE_DEVICES", ",".join(serials), {"count": deleted})
    return jsonify({"status": "deleted", "count": deleted})

@app.route('/export-csv', methods=['GET'])
def export_csv():
    """Export vehicles and keys to CSV"""
    tenant = request.cookies.get('tenant')
    if not tenant: return jsonify({"error": "No session"}), 401

    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute("SELECT serial_number, description FROM vehicles WHERE tenant_db = ?", (tenant,))
    vehicles = cur.fetchall()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['Serial', 'Description', 'Key Count', 'Keys (UserRef | ID | Expires)'])

    for v in vehicles:
        cur.execute("SELECT vk_id, user_ref, expires_at FROM virtual_keys WHERE serial_number = ? AND tenant_db = ?", (v[0], tenant))
        keys = cur.fetchall()
        key_info = "; ".join([f"{k[1] or 'N/A'} | {k[0][:10]}... | {datetime.fromtimestamp(k[2]/1000).strftime('%Y-%m-%d') if k[2] else 'N/A'}" for k in keys])
        writer.writerow([v[0], v[1], len(keys), key_info])

    conn.close()

    response = make_response(output.getvalue())
    response.headers['Content-Type'] = 'text/csv'
    response.headers['Content-Disposition'] = f'attachment; filename=vehicles_export_{tenant}_{datetime.now().strftime("%Y%m%d")}.csv'
    return response

@app.route('/logs', methods=['GET', 'DELETE'])
def get_logs():
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    if request.method == 'DELETE':
        user = request.cookies.get('user_email')
        cur.execute("DELETE FROM logs")
        conn.commit()
        conn.close()
        # Log the reset action (this will be the first entry in the clean log)
        add_log(user, "RESET_LOGS", "ALL", {})
        return jsonify({"status": "logs cleared"})

    cur.execute("SELECT * FROM logs ORDER BY id DESC LIMIT 50")
    logs = [{"at": r[1], "user": r[2], "action": r[3], "serial": r[4]} for r in cur.fetchall()]
    conn.close()
    return jsonify(logs)

@app.route('/export-logs', methods=['GET'])
def export_logs():
    """Export all logs as a text file"""
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute("SELECT timestamp, user, action, serial, parameters FROM logs ORDER BY id DESC")
    logs = cur.fetchall()
    conn.close()

    output = io.StringIO()
    output.write("=" * 80 + "\n")
    output.write("GEOTAB KEYLESS MANAGER - LOG EXPORT\n")
    output.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    output.write("=" * 80 + "\n\n")

    for log in logs:
        output.write(f"[{log[0]}] {log[2]}\n")
        output.write(f"  User: {log[1] or 'N/A'}\n")
        output.write(f"  Serial: {log[3]}\n")
        if log[4]:
            output.write(f"  Params: {log[4]}\n")
        output.write("-" * 40 + "\n")

    response = make_response(output.getvalue())
    response.headers['Content-Type'] = 'text/plain; charset=utf-8'
    response.headers['Content-Disposition'] = f'attachment; filename=keyless_log_{datetime.now().strftime("%Y%m%d_%H%M%S")}.txt'
    return response

@app.route('/logout', methods=['POST'])
def logout():
    """End current session"""
    user = request.cookies.get('user_email')
    tenant = request.cookies.get('tenant')
    add_log(user, "LOGOUT", tenant or "N/A", {})
    resp = make_response(jsonify({"status": "logged_out"}))
    resp.delete_cookie('access_token')
    resp.delete_cookie('tenant')
    resp.delete_cookie('user_email')
    return resp

# ==================== TEMPLATE ENDPOINTS ====================

@app.route('/templates', methods=['GET', 'POST'])
def manage_templates():
    tenant = request.args.get('tenant') or request.cookies.get('tenant')
    if not tenant:
        return jsonify({"error": "Tenant required"}), 400

    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    if request.method == 'POST':
        user = request.cookies.get('user_email')
        data = request.json
        template_id = f"tpl_{uuid.uuid4().hex[:12]}"
        created_at = datetime.now().isoformat()

        try:
            cur.execute("""INSERT INTO vk_templates
                          (id, tenant_db, name, user_ref, vk_config, nfc_tags, duration_months, version, is_active, created_at, created_by)
                          VALUES (?, ?, ?, ?, ?, ?, ?, 1, 1, ?, ?)""",
                       (template_id, tenant, data['name'], data.get('user_ref'),
                        json.dumps(data.get('vk_config', {})),
                        json.dumps(data.get('nfc_tags', [])),
                        data.get('duration_months', 12), created_at, user))
            conn.commit()
            add_log(user, "CREATE_TEMPLATE", data['name'], {"template_id": template_id})
            conn.close()
            return jsonify({"id": template_id, "version": 1})
        except sqlite3.IntegrityError:
            conn.close()
            return jsonify({"error": "Template name already exists"}), 409

    # GET: List templates - check if user_ref column exists
    cur.execute("PRAGMA table_info(vk_templates)")
    columns = [info[1] for info in cur.fetchall()]
    has_user_ref = 'user_ref' in columns

    include_archived = request.args.get('include_archived', 'false') == 'true'

    if has_user_ref:
        if include_archived:
            cur.execute("""SELECT id, name, user_ref, nfc_tags, duration_months, version, is_active, created_at
                          FROM vk_templates WHERE tenant_db = ? ORDER BY name, version DESC""", (tenant,))
        else:
            cur.execute("""SELECT id, name, user_ref, nfc_tags, duration_months, version, is_active, created_at
                          FROM vk_templates WHERE tenant_db = ? AND is_active = 1 ORDER BY name""", (tenant,))
        templates = [{"id": r[0], "name": r[1], "user_ref": r[2], "nfc_tags": json.loads(r[3]),
                      "duration_months": r[4], "version": r[5], "is_active": bool(r[6]),
                      "created_at": r[7]} for r in cur.fetchall()]
    else:
        if include_archived:
            cur.execute("""SELECT id, name, nfc_tags, duration_months, version, is_active, created_at
                          FROM vk_templates WHERE tenant_db = ? ORDER BY name, version DESC""", (tenant,))
        else:
            cur.execute("""SELECT id, name, nfc_tags, duration_months, version, is_active, created_at
                          FROM vk_templates WHERE tenant_db = ? AND is_active = 1 ORDER BY name""", (tenant,))
        templates = [{"id": r[0], "name": r[1], "user_ref": None, "nfc_tags": json.loads(r[2]),
                      "duration_months": r[3], "version": r[4], "is_active": bool(r[5]),
                      "created_at": r[6]} for r in cur.fetchall()]

    conn.close()
    return jsonify(templates)

@app.route('/templates/<template_id>', methods=['GET', 'PUT', 'DELETE'])
def manage_template(template_id):
    tenant = request.cookies.get('tenant')
    user = request.cookies.get('user_email')

    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    if request.method == 'GET':
        # Check if user_ref column exists
        cur.execute("PRAGMA table_info(vk_templates)")
        columns = [info[1] for info in cur.fetchall()]
        has_user_ref = 'user_ref' in columns

        if has_user_ref:
            cur.execute("""SELECT id, tenant_db, name, user_ref, vk_config, nfc_tags,
                           duration_months, version, previous_version_id, is_active, created_at, created_by
                           FROM vk_templates WHERE id = ? AND tenant_db = ?""", (template_id, tenant))
        else:
            cur.execute("""SELECT id, tenant_db, name, vk_config, nfc_tags,
                           duration_months, version, previous_version_id, is_active, created_at, created_by
                           FROM vk_templates WHERE id = ? AND tenant_db = ?""", (template_id, tenant))

        row = cur.fetchone()
        conn.close()
        if not row:
            return jsonify({"error": "Template not found"}), 404

        if has_user_ref:
            return jsonify({
                "id": row[0], "tenant_db": row[1], "name": row[2],
                "user_ref": row[3], "vk_config": json.loads(row[4]), "nfc_tags": json.loads(row[5]),
                "duration_months": row[6], "version": row[7],
                "previous_version_id": row[8], "is_active": bool(row[9]),
                "created_at": row[10], "created_by": row[11]
            })
        else:
            return jsonify({
                "id": row[0], "tenant_db": row[1], "name": row[2],
                "user_ref": None, "vk_config": json.loads(row[3]), "nfc_tags": json.loads(row[4]),
                "duration_months": row[5], "version": row[6],
                "previous_version_id": row[7], "is_active": bool(row[8]),
                "created_at": row[9], "created_by": row[10]
            })

    if request.method == 'PUT':
        # Get current version info
        cur.execute("SELECT name, version FROM vk_templates WHERE id = ? AND tenant_db = ?",
                    (template_id, tenant))
        current = cur.fetchone()
        if not current:
            conn.close()
            return jsonify({"error": "Template not found"}), 404

        data = request.json
        old_name, old_version = current
        new_version = old_version + 1
        new_id = f"tpl_{uuid.uuid4().hex[:12]}"
        created_at = datetime.now().isoformat()

        # Mark old version as inactive
        conn.execute("UPDATE vk_templates SET is_active = 0 WHERE id = ?", (template_id,))

        # Create new version
        conn.execute("""INSERT INTO vk_templates
                       (id, tenant_db, name, user_ref, vk_config, nfc_tags, duration_months,
                        version, previous_version_id, is_active, created_at, created_by)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 1, ?, ?)""",
                    (new_id, tenant, data.get('name', old_name), data.get('user_ref'),
                     json.dumps(data.get('vk_config', {})),
                     json.dumps(data.get('nfc_tags', [])),
                     data.get('duration_months', 12), new_version,
                     template_id, created_at, user))

        conn.commit()
        add_log(user, "UPDATE_TEMPLATE", data.get('name', old_name),
                {"old_id": template_id, "new_id": new_id, "version": new_version})
        conn.close()
        return jsonify({"id": new_id, "version": new_version, "previous_version_id": template_id})

    if request.method == 'DELETE':
        hard_delete = request.args.get('hard', 'false') == 'true'
        cur.execute("SELECT name FROM vk_templates WHERE id = ? AND tenant_db = ?", (template_id, tenant))
        row = cur.fetchone()
        if not row:
            conn.close()
            return jsonify({"error": "Template not found"}), 404

        if hard_delete:
            conn.execute("DELETE FROM vk_templates WHERE id = ? AND tenant_db = ?", (template_id, tenant))
            add_log(user, "DELETE_TEMPLATE_HARD", row[0], {"template_id": template_id})
        else:
            conn.execute("UPDATE vk_templates SET is_active = 0 WHERE id = ? AND tenant_db = ?", (template_id, tenant))
            add_log(user, "ARCHIVE_TEMPLATE", row[0], {"template_id": template_id})

        conn.commit()
        conn.close()
        return jsonify({"status": "deleted" if hard_delete else "archived"})

@app.route('/templates/<template_id>/history', methods=['GET'])
def get_template_history(template_id):
    tenant = request.cookies.get('tenant')
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    # Get the template name first
    cur.execute("SELECT name FROM vk_templates WHERE id = ? AND tenant_db = ?", (template_id, tenant))
    row = cur.fetchone()
    if not row:
        conn.close()
        return jsonify({"error": "Template not found"}), 404

    # Get all versions with same name
    cur.execute("""SELECT id, version, created_at, created_by, is_active
                  FROM vk_templates WHERE tenant_db = ? AND name = ?
                  ORDER BY version DESC""", (tenant, row[0]))
    history = [{"id": r[0], "version": r[1], "created_at": r[2],
                "created_by": r[3], "is_active": bool(r[4])} for r in cur.fetchall()]
    conn.close()
    return jsonify(history)

if __name__ == '__main__':
    init_db()
    Timer(1.5, lambda: webbrowser.open("http://127.0.0.1:5000")).start()
    app.run(debug=False, port=5000)