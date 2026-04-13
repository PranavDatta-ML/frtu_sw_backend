import os
from fpdf import FPDF

BASE = r'D:\KMP FRTU Configurator\frtu_config_backend_v1'

# ── Section data ─────────────────────────────────────────────────────────────

SECTIONS = [
    ("FRTU Config Backend V1 - Complete Backend Documentation", "h1"),

    ("1. Project Overview", "h2"),
    ("FRTU Config Backend V1 is the backend service for the KMP FRTU (Field Terminal Remote Unit) Configurator. It provides a REST API to manage and configure FRTU devices in the field.", "p"),
    ("What the system does:", "p"),
    ("Managing a multi-tenant hierarchy: Tenants > Projects > Sites > Devices > Slots > Modules", "li"),
    ("Configuring device modules: DI, DO, Modbus RTU, Modbus TCP", "li"),
    ("Auto-discovering modules on physical FRTU devices", "li"),
    ("User authentication with JWT and OTP via email", "li"),
    ("Role-based access control (RBAC) across the hierarchy", "li"),
    ("Pushing configuration changes directly to FRTU hardware devices", "li"),

    ("2. Tech Stack", "h2"),
    ([["Component","Technology","Version"],
      ["Framework","FastAPI","0.110.0"],
      ["Server","Uvicorn","0.30.0"],
      ["ORM","SQLAlchemy async","2.0.30"],
      ["Database","PostgreSQL asyncpg","-"],
      ["Caching","Redis","7.1.0"],
      ["Task Queue","Celery + RabbitMQ","5.4.0"],
      ["Auth","PyJWT HS256","2.10.1"],
      ["Validation","Pydantic v2","2.9.0"],
      ["Email","AWS SES SMTP","-"],
      ["Password","bcrypt","5.0.0"],
      ["Container","Docker + Docker Compose","-"]], "table"),

    ("3. Setup and Installation", "h2"),
    ("Prerequisites: Python 3.10+, PostgreSQL (port 55432 locally), Redis (port 6379), RabbitMQ (port 5672)", "p"),
    ("Step 1 - Create virtual environment and install dependencies:", "p"),
    ("python -m venv venv\nvenv\\Scripts\\activate\npip install -r requirements.txt", "code"),
    ("Step 2 - Configure environment (copy .sample.env to .env and fill in values):", "p"),
    ("cp .sample.env .env", "code"),
    ("Step 3 - Start required services:", "p"),
    ("redis-server\nrabbitmq-server", "code"),
    ("Step 4 - Run the application:", "p"),
    ("uvicorn manage:app --host 0.0.0.0 --port 5001 --reload --log-level debug", "code"),
    ("Step 5 - Open Swagger UI at: http://127.0.0.1:5001/docs", "p"),

    ("4. Environment Configuration (.env)", "h2"),
    ([["Variable","Default","Description"],
      ["DEBUG","1","1=Development, 0=Production"],
      ["LOG_LEVEL","INFO","DEBUG / INFO / WARNING / ERROR"],
      ["DATABASE_URI","postgresql+asyncpg://...@127.0.0.1:55432/frtu_conf_db","PostgreSQL async connection"],
      ["REDIS_HOST","127.0.0.1","Redis server host"],
      ["REDIS_PORT","6379","Redis server port"],
      ["REDIS_DB","0","Redis database index"],
      ["JWT_SECRET","default key","JWT signing secret key"],
      ["JWT_ALGORITHM","HS256","JWT algorithm"],
      ["CELERY_BROKER_URL","amqp://guest:guest@127.0.0.1:5672","RabbitMQ broker URL"],
      ["CELERY_RESULT_BACKEND","db+postgresql://...","Celery result backend"],
      ["CELERY_RESULT_EXPIRES","86400","Task result TTL (24h)"],
      ["SES_HOST","email-smtp.ap-south-1.amazonaws.com","AWS SES SMTP host"],
      ["SES_PORT","587","AWS SES SMTP port"],
      ["SES_FROM_EMAIL","message-noreply@kimbal.io","Sender email address"]], "table"),

    ("5. Available URLs After Startup", "h2"),
    ([["URL","Description"],
      ["http://127.0.0.1:5001/docs","Swagger UI (interactive API docs)"],
      ["http://127.0.0.1:5001/redoc","ReDoc API documentation"],
      ["http://127.0.0.1:5001/openapi.json","Raw OpenAPI schema"],
      ["http://127.0.0.1:5001/health","Health check endpoint"],
      ["http://127.0.0.1:5001/version","API version"]], "table"),

    ("6. Application Startup Flow", "h2"),
    ("1. uvicorn manage:app starts the ASGI server", "li"),
    ("2. src/app.py: FastAPI initialized, CORS middleware added, all 30 routers registered", "li"),
    ("3. Startup Hook 1 fires: logs 'Starting Application...'", "li"),
    ("4. Startup Hook 2 fires: test_redis_connection() runs", "li"),
    ("5. Redis OK: logs 'Redis Connected Successfully: healthy'", "li"),
    ("6. Redis FAIL: raises Exception and app CRASHES (won't start)", "li"),
    ("NOTE: Redis must be running before starting the app.", "p"),

    ("7. Architecture Overview", "h2"),
    ("Request Flow:", "p"),
    ("Client (Frontend / Swagger) -> CORS Middleware -> JWT Auth Middleware -> FastAPI Router", "p"),
    ("From the Router:", "p"),
    ("Auth Routes -> DB + Redis (OTP storage)", "li"),
    ("RBAC Routes -> DB (permission checks)", "li"),
    ("Hierarchy Routes (Tenant>Project>Site>Device>Slot>Module) -> DB", "li"),
    ("Device Config Routes (DI, DO, Modbus) -> DB + FRTU Device API", "li"),
    ("Task Routes -> Celery -> RabbitMQ -> Physical FRTU Device (http://10.150.3.245:8000)", "li"),

    ("8. Database", "h2"),
    ("Driver: asyncpg (async PostgreSQL). ORM: SQLAlchemy 2.0 async. Default port: 55432 (local) / 5432 (Aurora RDS production). Database: frtu_conf_db", "p"),
    ([["Table","Description"],
      ["frtu_users","Application user accounts"],
      ["frtu_roles","Role definitions"],
      ["frtu_permissions","Permission definitions"],
      ["frtu_role_permissions","Role to permission mappings"],
      ["frtu_user_assignments","User to role assignments"],
      ["frtu_platform_admins","Platform level admin records"],
      ["frtu_tenants","Tenants (top of hierarchy)"],
      ["frtu_projects","Projects under tenants"],
      ["frtu_sites","Sites under projects"],
      ["frtu_devices","Devices under sites"],
      ["frtu_slots","Physical slots in a device"],
      ["frtu_modules","Modules in slots"],
      ["frtu_module_master","Master catalog of module types"],
      ["frtu_base_config","Device base configuration"],
      ["frtu_entities","RBAC entity definitions"],
      ["frtu_resources","RBAC resource definitions"],
      ["rbac","RBAC mapping table"],
      ["tasks","Celery task records"]], "table"),

    ("9. Authentication and Security", "h2"),
    ("Login Flow:", "h3"),
    ("POST /auth/login with email + password", "li"),
    ("Verify bcrypt password hash from frtu_users table", "li"),
    ("Fetch user role via frtu_user_assignments", "li"),
    ("Fetch role permissions via frtu_role_permissions", "li"),
    ("Generate JWT Access Token (30 min expiry, HS256 algorithm)", "li"),
    ("Return token + user info + permissions", "li"),
    ("OTP Login Flow:", "h3"),
    ("POST /auth/login/otp: generates OTP, stores in Redis (TTL 600s), sends via AWS SES email", "li"),
    ("POST /auth/verify/otp: reads from Redis, compares, deletes on match, returns JWT", "li"),
    ("Password Reset Flow:", "h3"),
    ("POST /auth/reset-password/request: generates token, stores in Redis, emails reset link", "li"),
    ("POST /auth/reset-password/confirm: verifies token, updates password hash, deletes token", "li"),
    ("JWT Token fields: sub (user UUID), role_id, exp (30 min expiry), aud: www.etlab.co, iss: www.etlab.co", "p"),

    ("10. RBAC - Role Based Access Control", "h2"),
    ("Hierarchy: User > UserAssignment > Role > RolePermissions > Permission (resource + action)", "p"),
    ("How permission checks work:", "h3"),
    ("Request arrives with Authorization: Bearer token", "li"),
    ("Middleware decodes JWT and extracts role_id", "li"),
    ("frtu_role_permissions queried for that role_id", "li"),
    ("Matched against required resource and action", "li"),
    ("Returns 403 Forbidden if no matching permission", "li"),
    ([["Exception","HTTP Code","Message"],
      ["RBACError","403","Generic permission denied"],
      ["SelfEditError","403","Cannot modify your own roles or permissions"],
      ["ChildScopeError","403","Can only modify child-created resources"]], "table"),

    ("11. Middleware", "h2"),
    ("JWT Auth Middleware: Intercepts every request, validates Authorization Bearer token, decodes JWT with secret/algorithm/audience/issuer verification, sets request.state.user, returns 401 for invalid/expired tokens.", "p"),
    ("Create Permission Middleware: Used as FastAPI dependency on write/edit endpoints. Validates user has 'edit' action on PERMISSION resource. Returns 401 (bad token) or 403 (insufficient permission).", "p"),
    ("Read Permission Middleware: Used on read endpoints. Validates user has 'view' action on the resource.", "p"),

    ("12. Redis and Caching", "h2"),
    ([["Purpose","Key Pattern","TTL"],
      ["Health check","health_check","60 seconds"],
      ["OTP storage","otp:{email}","600 seconds (10 min)"],
      ["Password reset token","reset:{token}","Until used"]], "table"),

    ("13. Email Service - AWS SES", "h2"),
    ("Provider: AWS SES. Region: ap-south-1. Host: email-smtp.ap-south-1.amazonaws.com. Port: 587 STARTTLS. From: message-noreply@kimbal.io", "p"),
    ("Templates: otp_email_template.html (Login OTP), reset_password_email_template.html (Password reset)", "p"),

    ("14. Celery Task Queue", "h2"),
    ("Broker: RabbitMQ amqp://guest:guest@127.0.0.1:5672", "li"),
    ("Result Backend: PostgreSQL db+postgresql://...", "li"),
    ("Serializer: pickle. Result TTL: 86400 seconds (24 hours)", "li"),
    ("Run worker: celery -A src.celery worker --loglevel=info -Q http", "code"),

    ("15. External FRTU Device API", "h2"),
    ("FRTUClient (src/utils/frtu_client.py) communicates with physical FRTU hardware. Base URL: http://10.150.3.245:8000", "p"),
    ([["Method","Endpoint","Description"],
      ["GET","/health","Device health check"],
      ["GET","/api/config/devids","Read device IDs config"],
      ["POST","/api/config/devids/update","Update device IDs config"],
      ["POST","/api/config/devids/remove","Remove slot config"],
      ["GET","/api/config/version","Read device version"],
      ["POST","/api/config/version/update","Update device version"],
      ["POST","/api/config/ini/update","Update INI config file"],
      ["POST","/api/config/ini/update-do","Update DO module INI"],
      ["POST","/api/config/ini/delete-di-module","Delete DI module config"],
      ["POST","/api/config/ini/delete-do-module","Delete DO module config"],
      ["POST","/api/config/modbus/update","Update Modbus RTU config"],
      ["POST","/api/config/modbus/clear","Clear Modbus RTU config"],
      ["POST","/api/config/modbus/delete-param","Delete Modbus RTU parameter"],
      ["POST","/api/config/modbus/delete-slave","Delete Modbus RTU slave"],
      ["POST","/api/config/modbus/delete-channel","Delete Modbus channel"],
      ["POST","/api/config/modbus-tcp/update","Update Modbus TCP config"],
      ["POST","/api/config/modbus-tcp/delete-param","Delete Modbus TCP parameter"],
      ["POST","/api/config/modbus-tcp/delete-slave","Delete Modbus TCP slave"]], "table"),

    ("16. All API Endpoints (141 Total)", "h2"),

    ("Health and Version", "h3"),
    ([["Method","Path","Description"],
      ["GET","/health","App and Redis health check"],
      ["GET","/version","API version info"]], "table"),

    ("Authentication", "h3"),
    ([["Method","Path","Description"],
      ["POST","/auth/login","Login with email + password, returns JWT"],
      ["POST","/auth/login/otp","Send OTP to email for login"],
      ["POST","/auth/verify/otp","Verify OTP and return JWT"],
      ["POST","/auth/reset-password/request","Request password reset email"],
      ["POST","/auth/reset-password/confirm","Confirm password reset with token"]], "table"),

    ("Users", "h3"),
    ([["Method","Path","Description"],
      ["POST","/api/users/","Create a new user"],
      ["POST","/api/users/users","Add user (alternate endpoint)"],
      ["GET","/api/users/","List all users with pagination and search"],
      ["GET","/api/users/permissions","Get current user permissions"],
      ["GET","/api/users/{user_id}","Get user by ID"],
      ["PUT","/api/users/{user_id}","Update user"],
      ["DELETE","/api/users/{user_id}","Delete user"]], "table"),

    ("Roles", "h3"),
    ([["Method","Path","Description"],
      ["POST","/api/roles","Create role"],
      ["GET","/api/roles","List roles with pagination and search"],
      ["GET","/api/roles/{role_id}","Get role by ID"],
      ["PUT","/api/roles/{role_id}","Update role"],
      ["DELETE","/api/roles/{role_id}","Delete role"]], "table"),

    ("Permissions", "h3"),
    ([["Method","Path","Description"],
      ["POST","/api/","Create permission"],
      ["GET","/api/permissions","Get permission catalog"],
      ["GET","/api/","List all permissions"],
      ["GET","/api/{permission_id}","Get permission by ID"],
      ["PUT","/api/{permission_id}","Update permission"],
      ["DELETE","/api/{permission_id}","Delete permission"]], "table"),

    ("Role-Permissions", "h3"),
    ([["Method","Path","Description"],
      ["POST","/api/role-permissions/","Assign permission to a role"],
      ["GET","/api/role-permissions/{role_id}","List all permissions of a role"],
      ["GET","/api/role-permissions/{role_id}/{permission_id}","Get specific mapping"],
      ["PUT","/api/role-permissions/{role_id}/{permission_id}","Update mapping"],
      ["DELETE","/api/role-permissions/{role_id}/{permission_id}","Remove permission from role"]], "table"),

    ("User Assignments", "h3"),
    ([["Method","Path","Description"],
      ["POST","/api/user-assignments/","Assign role to user"],
      ["GET","/api/user-assignments/user/{user_id}","List all assignments for a user"],
      ["GET","/api/user-assignments/{assignment_id}","Get specific assignment"],
      ["PUT","/api/user-assignments/{assignment_id}","Update assignment"],
      ["DELETE","/api/user-assignments/{assignment_id}","Delete assignment"]], "table"),

    ("Platform Admins", "h3"),
    ([["Method","Path","Description"],
      ["POST","/api/platform-admin/","Create platform admin"],
      ["GET","/api/platform-admin/","List all platform admins"],
      ["GET","/api/platform-admin/{id}","Get platform admin by ID"],
      ["PUT","/api/platform-admin/{id}","Update platform admin"],
      ["DELETE","/api/platform-admin/{id}","Delete platform admin"],
      ["GET","/api/platform-admin/{id}/hierarchy","Get full role + permission hierarchy"]], "table"),

    ("Tenants", "h3"),
    ([["Method","Path","Description"],
      ["POST","/api/tenants","Create tenant"],
      ["GET","/api/tenants/","List tenants with pagination and search"],
      ["GET","/api/tenants/{tenant_id}","Get tenant by ID"],
      ["PUT","/api/tenants/{tenant_id}","Update tenant"],
      ["DELETE","/api/tenants/{tenant_id}","Delete tenant"]], "table"),

    ("Projects", "h3"),
    ([["Method","Path","Description"],
      ["POST","/project/create","Create project"],
      ["POST","/project/read","List projects with filters"],
      ["POST","/project/read/id={project_id}","Get project by ID"],
      ["POST","/project/update","Update project by name"],
      ["POST","/project/update/{project_id}","Update project by ID"],
      ["POST","/project/delete-by-name","Delete project by name"],
      ["POST","/project/delete","Delete project by ID"]], "table"),

    ("Sites", "h3"),
    ([["Method","Path","Description"],
      ["POST","/site/create","Create site"],
      ["POST","/site/read","List sites with filters"],
      ["POST","/site/read/{id}","Get site by ID"],
      ["POST","/site/update","Update site"],
      ["POST","/site/update-by-name","Update site by name"],
      ["POST","/site/update-by-id","Update site by ID"],
      ["POST","/site/delete-by-name","Delete site by name"],
      ["POST","/site/delete","Delete site by ID"]], "table"),

    ("Devices", "h3"),
    ([["Method","Path","Description"],
      ["POST","/device/create","Create device"],
      ["POST","/device/read","List devices with filters"],
      ["POST","/device/read/{id}","Get device by ID"],
      ["POST","/device/update-by-name","Update device by name"],
      ["POST","/device/update","Update device by ID"],
      ["POST","/device/delete","Delete device"],
      ["POST","/device/configure_base_config","Add or update device base configuration"],
      ["GET","/device/get_configred_base_config","Get device base configuration"]], "table"),

    ("Slots", "h3"),
    ([["Method","Path","Description"],
      ["GET","/slots","List device slots"]], "table"),

    ("Module Discovery and Management", "h3"),
    ([["Method","Path","Description"],
      ["POST","/auto_discover_modules","Trigger auto-discovery on device"],
      ["GET","/auto_discover_modules_msg","Get auto-discovery status message"],
      ["GET","/auto_discover_modules","List auto-discovered modules"],
      ["GET","/get_card_type","Get available card types"],
      ["GET","/get_slot_module_detail","Get module detail for a slot"],
      ["GET","/get_available_slots","Get available empty slots"],
      ["GET","/get_slot_module_options","Get slot module category options"],
      ["POST","/update_module_detail","Update module detail for a slot"],
      ["GET","/get_module_list","Get full module list"],
      ["POST","/add_module","Add module (auto flow)"],
      ["POST","/add_module_manually","Add module (manual flow)"],
      ["GET","/get_modules","Get all modules on a device"],
      ["POST","/configure_module_manually","Manually configure a module"],
      ["GET","/configured_module_detail","Get configured module detail"]], "table"),

    ("DI Digital Input Module", "h3"),
    ([["Method","Path","Description"],
      ["POST","/add_di_general_info","Add DI module general info"],
      ["POST","/edit_di_general_info","Edit DI module general info"],
      ["GET","/get_di_general_info","Get DI module general info"],
      ["POST","/add_di_channel","Add DI channel"],
      ["GET","/get_di_channel","Get DI channel list"],
      ["GET","/get_di_channel_info","Get DI channel detail"],
      ["POST","/configure_module_ioa","Configure module IOA"],
      ["POST","/add_di_module_info","Add DI module info"],
      ["POST","/edit_di_module_info","Edit / move DI module"],
      ["GET","/get_di_module_info_by_slot_id","Get DI module info by slot ID"],
      ["GET","/get_di_module_info","Get DI module info by sub-module ID"],
      ["DELETE","/delete_di_channel","Delete DI channel"],
      ["DELETE","/delete_di_module_info","Delete DI module"]], "table"),

    ("DO Digital Output Module", "h3"),
    ([["Method","Path","Description"],
      ["POST","/add_do_module_info","Add DO module info"],
      ["POST","/edit_do_module_info","Edit / move DO module"],
      ["GET","/get_do_module_info","Get DO module info"],
      ["DELETE","/delete_do_channel","Delete DO channel"],
      ["DELETE","/delete_do_module_info","Delete DO module"]], "table"),

    ("Modbus RTU Module", "h3"),
    ([["Method","Path","Description"],
      ["POST","/add_modbus_rtu_info","Add or update Modbus RTU module"],
      ["GET","/get_modbus_rtu_info","Get Modbus RTU module info"],
      ["DELETE","/delete_modbus_rtu_parameter","Delete Modbus RTU parameter"],
      ["DELETE","/delete_modbus_rtu_slave","Delete Modbus RTU slave"],
      ["DELETE","/delete_modbus_channel","Delete Modbus channel"]], "table"),

    ("Modbus TCP Module", "h3"),
    ([["Method","Path","Description"],
      ["POST","/add_modbus_tcp_info","Add or update Modbus TCP module"],
      ["GET","/get_modbus_tcp_info","Get Modbus TCP module info"],
      ["DELETE","/delete_modbus_tcp_parameter","Delete Modbus TCP parameter"],
      ["DELETE","/delete_modbus_tcp_slave","Delete Modbus TCP slave"]], "table"),

    ("Modbus Unified RTU and TCP", "h3"),
    ([["Method","Path","Description"],
      ["POST","/add_modbus_info","Add Modbus info (auto-detects RTU or TCP)"],
      ["GET","/get_modbus_info","Get Modbus info (RTU or TCP)"],
      ["DELETE","/delete_modbus_parameter","Delete Modbus parameter (unified)"],
      ["DELETE","/delete_modbus_slave","Delete Modbus slave (unified)"]], "table"),

    ("Protocols", "h3"),
    ([["Method","Path","Description"],
      ["POST","/api/protocol/","Create protocol"],
      ["GET","/api/protocol/","List protocols with pagination and search"],
      ["GET","/api/protocol/{protocol_id}","Get protocol by ID"],
      ["PUT","/api/protocol/{protocol_id}","Update protocol"],
      ["DELETE","/api/protocol/{protocol_id}","Delete protocol"]], "table"),

    ("RBAC", "h3"),
    ([["Method","Path","Description"],
      ["POST","/rbac/roles/","Create role (RBAC context)"],
      ["POST","/rbac/permissions/","Create permission (RBAC context)"],
      ["POST","/rbac/role-permissions/","Assign permission to role"],
      ["POST","/rbac/user-roles/","Assign role to user"],
      ["GET","/rbac/rbac/me","Get current user RBAC info"],
      ["GET","/rbac/rbac/my-users","Get users created by current user"],
      ["GET","/rbac/rbac/my-roles","Get roles visible to current user"]], "table"),

    ("Admin Hierarchy Deletion", "h3"),
    ([["Method","Path","Description"],
      ["DELETE","/api/admin/{admin_id}/hierarchy","Delete complete admin hierarchy"]], "table"),

    ("Tasks", "h3"),
    ([["Method","Path","Description"],
      ["POST","/api/v1/task/push","Push a new task to the queue"],
      ["GET","/api/v1/task/list","List all queued and processed tasks"],
      ["GET","/api/v1/task/get/{task_id}","Get task status and result by ID"]], "table"),

    ("17. Data Hierarchy", "h2"),
    ("Platform Admin -> Tenant -> Project -> Site -> Device -> Slot -> Module", "p"),
    ("Tenant: e.g. Company A", "li"),
    ("Project: e.g. City Grid Project", "li"),
    ("Site: e.g. Substation North", "li"),
    ("Device: physical FRTU unit", "li"),
    ("Slot: physical slot on device (e.g. Slot 1 to 16)", "li"),
    ("Module types: DI (Digital Input with channels), DO (Digital Output with channels), Modbus RTU (with Slaves and Parameters), Modbus TCP (with Slaves and Parameters)", "li"),

    ("18. Known Issues", "h2"),
    ("Pydantic v2 Warning: orm_mode renamed to from_attributes. Non-blocking but schemas need updating.", "li"),
    ("Duplicate Startup Hooks: manage.py defines app_startup twice. Only second definition runs.", "li"),
    ("CORS Hardcoded: src/app.py CORS origins hardcoded to localhost:5500 and localhost:3000 only.", "li"),
    ("Redis Required: If Redis is unavailable the app crashes on startup and refuses to start.", "li"),
    ("FRTU Device IP Hardcoded: FRTUClient base URL http://10.150.3.245:8000 is hardcoded in code.", "li"),

    ("Last Updated: 2026-04-06", "p"),
]

# ── PDF Builder ───────────────────────────────────────────────────────────────

class Doc(FPDF):
    def header(self):
        self.set_fill_color(26, 26, 46)
        self.rect(0, 0, 210, 11, 'F')
        self.set_text_color(255, 255, 255)
        self.set_font('Helvetica', 'B', 8)
        self.set_xy(10, 3)
        self.cell(0, 5, 'FRTU Config Backend V1 - Backend Documentation', align='L')
        self.set_text_color(0, 0, 0)
        self.ln(8)

    def footer(self):
        self.set_y(-12)
        self.set_fill_color(26, 26, 46)
        self.rect(0, 285, 210, 12, 'F')
        self.set_text_color(200, 200, 200)
        self.set_font('Helvetica', '', 7)
        self.set_xy(10, 287)
        self.cell(95, 5, 'FRTU Config Backend V1  |  2026-04-06', align='L')
        self.cell(95, 5, f'Page {self.page_no()}', align='R')
        self.set_text_color(0, 0, 0)


def draw_table(pdf, rows):
    if not rows:
        return
    n_cols = len(rows[0])
    col_w = 180 / n_cols
    # header
    pdf.set_fill_color(26, 26, 46)
    pdf.set_text_color(255, 255, 255)
    pdf.set_font('Helvetica', 'B', 8)
    for cell in rows[0]:
        pdf.cell(col_w, 6, str(cell)[:40], border=1, fill=True)
    pdf.ln()
    pdf.set_text_color(0, 0, 0)
    # body
    for r_idx, row in enumerate(rows[1:]):
        pdf.set_fill_color(245, 245, 245) if r_idx % 2 == 0 else pdf.set_fill_color(255, 255, 255)
        pdf.set_font('Helvetica', '', 7.5)
        for cell in row:
            pdf.cell(col_w, 5.5, str(cell)[:55], border=1, fill=True)
        pdf.ln()
    pdf.ln(2)


def build_pdf(out_path):
    pdf = Doc()
    pdf.set_auto_page_break(auto=True, margin=18)
    pdf.set_margins(15, 16, 15)
    pdf.add_page()

    for item, kind in SECTIONS:
        if kind == 'h1':
            pdf.set_fill_color(26, 26, 46)
            pdf.set_text_color(255, 255, 255)
            pdf.set_font('Helvetica', 'B', 15)
            pdf.ln(2)
            pdf.multi_cell(0, 9, str(item), fill=True, align='C')
            pdf.set_text_color(0, 0, 0)
            pdf.ln(3)

        elif kind == 'h2':
            pdf.set_fill_color(22, 33, 62)
            pdf.set_text_color(255, 255, 255)
            pdf.set_font('Helvetica', 'B', 11)
            pdf.ln(4)
            pdf.cell(0, 7, str(item), new_x='LMARGIN', new_y='NEXT', fill=True)
            pdf.set_text_color(0, 0, 0)
            pdf.ln(1)

        elif kind == 'h3':
            pdf.set_text_color(15, 52, 96)
            pdf.set_font('Helvetica', 'B', 10)
            pdf.ln(3)
            pdf.cell(0, 6, str(item), new_x='LMARGIN', new_y='NEXT')
            pdf.set_draw_color(15, 52, 96)
            pdf.line(15, pdf.get_y(), 195, pdf.get_y())
            pdf.set_draw_color(0, 0, 0)
            pdf.set_text_color(0, 0, 0)
            pdf.ln(2)

        elif kind == 'p':
            pdf.set_font('Helvetica', '', 10)
            pdf.set_x(15)
            pdf.multi_cell(180, 5, str(item))
            pdf.ln(1)

        elif kind == 'li':
            pdf.set_font('Helvetica', '', 10)
            pdf.set_x(20)
            pdf.cell(5, 5, '-')
            pdf.set_x(25)
            pdf.multi_cell(165, 5, str(item))

        elif kind == 'code':
            pdf.set_fill_color(30, 30, 50)
            pdf.set_text_color(200, 220, 200)
            pdf.set_font('Courier', '', 8.5)
            pdf.ln(1)
            for line in str(item).split('\n'):
                pdf.set_x(15)
                pdf.cell(0, 4.5, line[:110], new_x='LMARGIN', new_y='NEXT', fill=True)
            pdf.set_text_color(0, 0, 0)
            pdf.ln(2)

        elif kind == 'table':
            draw_table(pdf, item)

    pdf.output(out_path)
    print(f'PDF saved: {out_path}')


if __name__ == '__main__':
    out = os.path.join(BASE, 'BACKEND_DOCUMENTATION.pdf')
    build_pdf(out)
