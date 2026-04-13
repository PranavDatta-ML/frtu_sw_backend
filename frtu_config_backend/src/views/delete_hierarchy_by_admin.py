from uuid import UUID
from src.models.frtu_devices import FRTUDevices
from src.models.frtu_entities import FRTUEntities
from src.models.frtu_modules import FRTUModules
from src.models.frtu_platform_admins import FRTUPlatformAdmin
from src.models.frtu_projects import FRTUProjects
from src.models.frtu_role_permissions import FRTURolePermissions
from src.models.frtu_roles import FRTURoles
from src.models.frtu_sites import FRTUSites
from src.models.frtu_slots import FRTUSlots
from src.models.frtu_tenants import FRTUTenants
from src.models.frtu_user_assignment import FRTUUserAssignment

async def delete_hierarchy_by_admin_id(admin_id: UUID, confirm: bool = False) -> dict:
    if not confirm:
        return {
            "http_code": 400,
            "code": "CONFIRM_REQUIRED",
            "message": {
                "title": "Confirm Complete Hierarchy Deletion",
                "message": "This will delete Admin + ALL tenants, projects, sites, devices, slots, modules, roles & permissions. This action is IRREVERSIBLE.",
                "action_required": "set_confirm_true"
            },
            "confirm_required": True
        }

    deleted_count = {
        "admin": 0, "tenants": 0, "projects": 0, "sites": 0, 
        "devices": 0, "slots": 0, "modules": 0, "roles": 0, "permissions": 0
    }
    
    try:
        # 1. Get hierarchy IDs
        tenants = await FRTUTenants.select(admin_id=admin_id)
        tenant_ids = [t.id for t in tenants]
        deleted_count["tenants"] = len(tenant_ids)
        
        projects = await FRTUProjects.select(tenant_id=tenant_ids) if tenant_ids else []
        project_ids = [p.id for p in projects]
        deleted_count["projects"] = len(project_ids)
        
        sites = await FRTUSites.select(project_id=project_ids) if project_ids else []
        site_ids = [s.id for s in sites]
        deleted_count["sites"] = len(site_ids)
        
        devices = await FRTUDevices.select(site_id=site_ids) if site_ids else []
        device_ids = [d.id for d in devices]
        deleted_count["devices"] = len(device_ids)
        
        slots = await FRTUSlots.select(device_id=device_ids) if device_ids else []
        slot_ids = [s.id for s in slots]
        deleted_count["slots"] = len(slot_ids)
        
        modules_list = await FRTUModules.select(slot_id=slot_ids) if slot_ids else []
        deleted_count["modules"] = len(modules_list)

        # 2. DELETE BOTTOM-UP - LOOP SAFE DELETION
        for slot_id in slot_ids:
            await FRTUModules.delete(conditions={"slot_id": slot_id})
            
        for device_id in device_ids:
            await FRTUSlots.delete(conditions={"device_id": device_id})
            
        for site_id in site_ids:
            await FRTUDevices.delete(conditions={"site_id": site_id})
            
        for project_id in project_ids:
            await FRTUSites.delete(conditions={"project_id": project_id})
            
        for tenant_id in tenant_ids:
            await FRTUProjects.delete(conditions={"tenant_id": tenant_id})

        # 3. Delete entities & tenants
        for tenant_id in tenant_ids:
            await FRTUEntities.delete(conditions={"entity_id": tenant_id})
            
        await FRTUTenants.delete(conditions={"admin_id": admin_id})
        
        # 4. Delete assignments
        await FRTUUserAssignment.delete(conditions={"admin_id": admin_id})
        
        # 5. Delete roles & permissions
        # admin_roles = await FRTURoles.select(admin_id=admin_id)
        # role_ids = [r.id for r in admin_roles]
        # deleted_count["roles"] += len(role_ids)
        
        # for role_id in role_ids:
        #     await FRTURolePermissions.delete(conditions={"role_id": role_id})
            
        # await FRTURoles.delete(conditions={"admin_id": admin_id})
        
        # 6. Delete admin
        admin = await FRTUPlatformAdmin.select(id=admin_id)
        if admin:
            deleted_count["admin"] = 1
            await FRTUPlatformAdmin.delete(conditions={"id": admin_id})
        
        return {
            "http_code": 200,
            "code": "SUCCESS",
            "message": "Complete hierarchy deleted successfully",
            "data": {
                "deleted_count": deleted_count,
                "admin_id": str(admin_id)
            }
        }
        
    except Exception as e:
        return {
            "http_code": 500,
            "code": "INTERNAL_SERVER_ERROR",
            "message": str(e),
            "deleted_count": deleted_count
        }


