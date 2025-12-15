-- create default schema
CREATE SCHEMA IF NOT EXISTS frtu_conf_db;

CREATE TYPE frtu_conf_db.frtu_action_type_enum AS ENUM (
	'READ',
	'WRITE');

CREATE TYPE frtu_conf_db.frtu_device_type_enum AS ENUM (
	'FRTU',
	'RTU');

CREATE TABLE frtu_conf_db.frtu_platform_admins (
	id uuid DEFAULT gen_random_uuid() NOT NULL,
	"name" varchar NOT NULL,
	mobile_no varchar NOT NULL,
	email varchar NULL,
	"attribute" json NULL,
	creation_time timestamp NULL,
	last_update_time timestamp NULL,
	CONSTRAINT frtu_platform_admins_pkey PRIMARY KEY (id),
	CONSTRAINT platform_admin_unique_email UNIQUE (email),
	CONSTRAINT platform_admin_unique_mobile_no UNIQUE (mobile_no)
);

CREATE TABLE frtu_conf_db.frtu_tenants (
	id uuid DEFAULT gen_random_uuid() NOT NULL,
	admin_id uuid NOT NULL,
	"name" varchar NOT NULL,
	"attribute" json NULL,
	creation_time timestamp NULL,
	last_update_time timestamp NULL,
	CONSTRAINT frtu_tenants_pk PRIMARY KEY (id),
	CONSTRAINT frtu_tenants_frtu_platform_admins_fk FOREIGN KEY (admin_id) REFERENCES frtu_conf_db.frtu_platform_admins(id)
);

CREATE TABLE frtu_conf_db.frtu_projects (
	id uuid DEFAULT gen_random_uuid() NOT NULL,
	tenant_id uuid NOT NULL,
	"name" varchar NOT NULL,
	"attribute" json NULL,
	creation_time timestamp NULL,
	last_update_time timestamp NULL,
	CONSTRAINT frtu_projects_pk PRIMARY KEY (id),
	CONSTRAINT frtu_projects_frtu_tenants_fk FOREIGN KEY (tenant_id) REFERENCES frtu_conf_db.frtu_tenants(id)
);

CREATE TABLE frtu_conf_db.frtu_sites (
	id uuid DEFAULT gen_random_uuid() NOT NULL,
	project_id uuid NOT NULL,
	"name" varchar NOT NULL,
	"attribute" json NULL,
	creation_time timestamp NULL,
	last_update_time timestamp NULL,
	CONSTRAINT frtu_sites_pk PRIMARY KEY (id),
	CONSTRAINT frtu_sites_frtu_projects_fk FOREIGN KEY (project_id) REFERENCES frtu_conf_db.frtu_projects(id)
);

CREATE TABLE frtu_conf_db.frtu_devices (
	id uuid DEFAULT gen_random_uuid() NOT NULL,
	site_id uuid NOT NULL,
	"name" varchar NOT NULL,
	"type" frtu_conf_db.frtu_device_type_enum NOT NULL,
	"attribute" json NULL,
	creation_time timestamp NULL,
	last_update_time timestamp NULL,
	CONSTRAINT frtu_device_pk PRIMARY KEY (id),
	CONSTRAINT frtu_devices_frtu_sites_fk FOREIGN KEY (site_id) REFERENCES frtu_conf_db.frtu_sites(id)
);

CREATE OR REPLACE FUNCTION frtu_conf_db.frtu_trg_fun_create_slots()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
DECLARE
	v_utc_now TIMESTAMP;
BEGIN
	  v_utc_now := NOW() AT TIME ZONE 'UTC';
      FOR i IN 1..11 LOOP
		    INSERT INTO frtu_slots (device_id, name, creation_time, last_update_time)
			VALUES (
            NEW.id,
--            NEW.name || '_' || LPAD(i::text, 2, '0'),  -- ETLDev0310_01 ... ETLDev0310_11
			LPAD(i::text, 2, '0'),
            v_utc_now,
            v_utc_now
        );
      END LOOP;
	  RETURN NEW;
END;
$function$
;

create trigger trg_ai_device after
insert
    on
    frtu_conf_db.frtu_devices for each row execute function frtu_trg_fun_create_slots();

CREATE TABLE frtu_conf_db.frtu_slots (
	id uuid DEFAULT gen_random_uuid() NOT NULL,
	device_id uuid NOT NULL,
	"name" varchar NOT NULL,
	"attribute" json NULL,
	creation_time timestamp NULL,
	last_update_time timestamp NULL,
	CONSTRAINT frtu_slot_pk PRIMARY KEY (id),
	CONSTRAINT frtu_slots_frtu_devices_fk FOREIGN KEY (device_id) REFERENCES frtu_conf_db.frtu_devices(id)
);

CREATE TABLE frtu_conf_db.frtu_module_type (
	id uuid DEFAULT gen_random_uuid() NOT NULL,
	"name" varchar NOT NULL,
	description text NULL,
	"attribute" json NULL,
	creation_time timestamp NULL,
	last_update_time timestamp NULL,
	CONSTRAINT frtu_modules_type_pk PRIMARY KEY (id)
);

CREATE TABLE frtu_conf_db.frtu_modules (
	id uuid DEFAULT gen_random_uuid() NOT NULL,
	slot_id uuid NOT NULL,
	"name" varchar NOT NULL,
	module_type uuid NOT NULL,
	description text NULL,
	"attribute" json NULL,
	creation_time timestamp NULL,
	last_update_time timestamp NULL,
	channel json NULL,
	CONSTRAINT frtu_modules_pk PRIMARY KEY (id),
	CONSTRAINT frtu_modules_frtu_module_type_fk FOREIGN KEY (module_type) REFERENCES frtu_conf_db.frtu_module_type(id),
	CONSTRAINT frtu_modules_frtu_slots_fk FOREIGN KEY (slot_id) REFERENCES frtu_conf_db.frtu_slots(id)
);

CREATE TABLE frtu_conf_db.frtu_users (
	id uuid DEFAULT gen_random_uuid() NOT NULL,
	email varchar NOT NULL,
	mobile_no varchar NOT NULL,
	"name" varchar NOT NULL,
	password_hash varchar NOT NULL,
	salt varchar NOT NULL,
	is_active bool DEFAULT true NOT NULL,
	is_deleted bool DEFAULT false NOT NULL,
	"attribute" json NULL,
	creation_time timestamp NULL,
	last_update_time timestamp NULL,
	CONSTRAINT frtu_users_pk PRIMARY KEY (id),
	CONSTRAINT frtu_users_unique_email UNIQUE (email),
	CONSTRAINT frtu_users_unique_mobile_no UNIQUE (mobile_no)
);

CREATE TABLE frtu_conf_db.frtu_roles (
	id uuid DEFAULT gen_random_uuid() NOT NULL,
	user_id uuid NULL,
	"name" varchar NOT NULL,
	description text NULL,
	"attribute" json NULL,
	creation_time timestamp NULL,
	last_update_time timestamp NULL,
	CONSTRAINT frtu_roles_pk PRIMARY KEY (id)
);

CREATE TABLE frtu_conf_db.frtu_user_assignment (
	id uuid DEFAULT gen_random_uuid() NOT NULL,
	user_id uuid NOT NULL,
	role_id uuid NOT NULL,
	scope_type varchar NULL,
	scope_id uuid NOT NULL,
	"attribute" json NULL,
	creation_time timestamp NULL,
	last_update_time timestamp NULL,
	admin_id uuid NOT NULL,
	CONSTRAINT frtu_user_assignment_unique UNIQUE (id),
	CONSTRAINT frtu_user_assignment_frtu_roles_fk FOREIGN KEY (role_id) REFERENCES frtu_conf_db.frtu_roles(id),
	CONSTRAINT frtu_user_assignment_frtu_users_fk FOREIGN KEY (user_id) REFERENCES frtu_conf_db.frtu_users(id)
);

CREATE TABLE frtu_conf_db.frtu_entities (
	id uuid DEFAULT gen_random_uuid() NOT NULL,
	entity_id uuid NULL,
	"name" varchar NOT NULL,
	email_id varchar NULL,
	mobile_no varchar NULL,
	"attribute" json NULL,
	created_by uuid NULL,
	creation_time timestamptz DEFAULT CURRENT_TIMESTAMP NULL,
	last_update_time timestamptz DEFAULT CURRENT_TIMESTAMP NULL
);

CREATE TABLE frtu_conf_db.frtu_module_master (
	id uuid DEFAULT gen_random_uuid() NOT NULL,
	"name" varchar NOT NULL,
	"attribute" json NULL,
	creation_time timestamp NULL,
	last_update_time timestamp NULL,
	CONSTRAINT frtu_module_master_pk PRIMARY KEY (id)
);

CREATE TABLE frtu_conf_db.frtu_permissions (
	id uuid DEFAULT gen_random_uuid() NOT NULL,
	user_id uuid NULL,
	"attribute" json NULL,
	creation_time timestamp NULL,
	last_update_time timestamp NULL,
	CONSTRAINT frtu_permissions_unique UNIQUE (id),
	CONSTRAINT frtu_permissions_frtu_users_fk FOREIGN KEY (user_id) REFERENCES frtu_conf_db.frtu_users(id)
);

CREATE TABLE frtu_conf_db.frtu_resources (
	id uuid DEFAULT gen_random_uuid() NOT NULL,
	"name" varchar NOT NULL,
	description text NULL,
	"attribute" json NULL,
	creation_time timestamp NULL,
	last_update_time timestamp NULL,
	CONSTRAINT frtu_resources_pk PRIMARY KEY (id)
);

CREATE TABLE frtu_conf_db.frtu_role_permissions (
	role_id uuid NOT NULL,
	permission_id uuid NOT NULL,
	creation_time timestamp NULL,
	last_update_time timestamp NULL,
	CONSTRAINT frtu_role_permissions_pk PRIMARY KEY (role_id, permission_id),
	CONSTRAINT frtu_role_permissions_frtu_permissions_fk FOREIGN KEY (permission_id) REFERENCES frtu_conf_db.frtu_permissions(id),
	CONSTRAINT frtu_role_permissions_frtu_roles_fk FOREIGN KEY (role_id) REFERENCES frtu_conf_db.frtu_roles(id)
);
