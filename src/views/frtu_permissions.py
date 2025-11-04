from datetime import datetime, UTC
from fastapi import Request, Header, Depends
from src.core.status_codes import HttpStatusCode
from src.core.settings import Settings
from src.models.frtu_permissions import FRTUPermissions
from src.models.frtu_resources import FRTUResources
from src.models.frtu_role_permissions import FRTURolePermissions
from src.models.frtu_users import FRTUUsers
from src.utils.jwt_tokens import decode_access_token
import uuid
from src import log


# async def create_permission(request: Request, authorization: str = Header(...)):
#     try:
#         if not authorization or not authorization.startswith("Bearer "):
#             return HttpStatusCode.UNAUTHORIZED.response(
#                 message="Invalid Authorization header"
#             )

#         token = authorization.split(" ")[1]
#         token_payload = decode_access_token(token)
#         creator_user_id = token_payload.get("sub")

#         if not creator_user_id:
#             return HttpStatusCode.UNAUTHORIZED.response(
#                 message="Invalid token: user_id missing"
#             )

#         try:
#             creator_user_id = uuid.UUID(creator_user_id)
#         except (ValueError, AttributeError):
#             return HttpStatusCode.BAD_REQUEST.response(
#                 message="Invalid user_id format in token"
#             )

#         users = await FRTUUsers.select(
#             id=creator_user_id,
#             columns=[FRTUUsers.id, FRTUUsers.name, FRTUUsers.email]
#         )
#         if not users:
#             return HttpStatusCode.NOT_FOUND.response(
#                 message="Creator user not found"
#             )
#         payload = await request.json()
#         attribute_input = payload.get("attribute")
#         if not attribute_input:
#             return HttpStatusCode.BAD_REQUEST.response(
#                 message="'attribute' is required"
#             )

#         if isinstance(attribute_input, dict):
#             attribute = [attribute_input]
#         elif isinstance(attribute_input, list):
#             attribute = attribute_input
#         else:
#             return HttpStatusCode.BAD_REQUEST.response(
#                 message="'attribute' must be an object or array of objects"
#             )

#         all_resources = await FRTUResources.select(
#             columns=[FRTUResources.name, FRTUResources.description]
#         )
#         if not all_resources:
#             return HttpStatusCode.INTERNAL_SERVER_ERROR.response(
#                 message="No resources found in system. Please seed resources first."
#             )

#         valid_resource_names = [r["name"] for r in all_resources]
#         valid_actions = ["view", "create", "edit", "delete", "configure"]

#         validated_attribute = []
#         for item in attribute:
#             if not isinstance(item, dict):
#                 return HttpStatusCode.BAD_REQUEST.response(
#                     message="Each attribute item must be an object with 'resource' and 'action'"
#                 )

#             resource = item.get("resource")
#             actions = item.get("action")

#             if not resource:
#                 return HttpStatusCode.BAD_REQUEST.response(
#                     message="Each attribute must have 'resource' field"
#                 )
#             if not actions or not isinstance(actions, list):
#                 return HttpStatusCode.BAD_REQUEST.response(
#                     message=f"'action' for resource '{resource}' must be a non-empty array"
#                 )

#             if resource not in valid_resource_names:
#                 return HttpStatusCode.BAD_REQUEST.response(
#                     message=f"Invalid resource '{resource}'. Valid resources are: {', '.join(valid_resource_names)}"
#                 )

#             for action in actions:
#                 if action not in valid_actions:
#                     return HttpStatusCode.BAD_REQUEST.response(
#                         message=f"Invalid action '{action}' for resource '{resource}'. Valid actions: {', '.join(valid_actions)}"
#                     )

#             validated_attribute.append({
#                 "resource": resource,
#                 "action": list(set(actions))  # ensure unique
#             })

#         existing_perms = await FRTUPermissions.select(user_id=creator_user_id)

#         now = datetime.utcnow()
#         creator = users[0]

#         # if existing_perms:
#         #     existing_perm = existing_perms[0]
#         #     existing_attr = existing_perm.get("attribute", [])

#         #     merged_attr = {a["resource"]: set(a["action"]) for a in existing_attr}
#         #     for new_item in validated_attribute:
#         #         res = new_item["resource"]
#         #         acts = set(new_item["action"])
#         #         if res in merged_attr:
#         #             merged_attr[res].update(acts)
#         #         else:
#         #             merged_attr[res] = acts

#         #     final_attr = [{"resource": k, "action": sorted(list(v))} for k, v in merged_attr.items()]

#         #     await FRTUPermissions.update(
#         #         conditions={"id": existing_perm["id"]},
#         #         attribute=final_attr,
#         #         last_update_time=now
#         #     )

#         #     return HttpStatusCode.OK.response(
#         #         message="Permission updated successfully (merged existing data)",
#         #         data={
#         #             "id": str(existing_perm["id"]),
#         #             "user_id": str(creator_user_id),
#         #             "attribute": final_attr,
#         #             "updated_by": {
#         #                 "user_id": str(creator["id"]),
#         #                 "name": creator["name"],
#         #                 "email": creator["email"]
#         #             },
#         #             "last_update_time": now.isoformat()
#         #         }
#         #     )

#         permission_id = uuid.uuid4()
#         permission_obj = await FRTUPermissions.insert(
#             id=permission_id,
#             user_id=creator_user_id,
#             attribute=validated_attribute,
#             creation_time=now,
#             last_update_time=now
#         )

#         return HttpStatusCode.CREATED.response(
#             message="Permission created successfully",
#             data={
#                 "id": str(permission_obj.id),
#                 "user_id": str(permission_obj.user_id),
#                 "attribute": permission_obj.attribute,
#                 "resources_count": len(validated_attribute),
#                 "created_by": {
#                     "user_id": str(creator["id"]),
#                     "name": creator["name"],
#                     "email": creator["email"]
#                 },
#                 "creation_time": permission_obj.creation_time.isoformat() if permission_obj.creation_time else None,
#                 "last_update_time": permission_obj.last_update_time.isoformat() if permission_obj.last_update_time else None
#             }
#         )

#     except Exception as e:
#         import traceback
#         log.error(f"Failed to create/update permission: {traceback.format_exc()}")
#         return HttpStatusCode.BAD_REQUEST.response(
#             message=f"Failed to create/update permission: {str(e)}"
#         )

async def create_permission(request: Request, authorization: str = Header(...)):
    try:
        if not authorization or not authorization.startswith("Bearer "):
            return HttpStatusCode.UNAUTHORIZED.response(
                message="Invalid Authorization header"
            )

        token = authorization.split(" ")[1]
        token_payload = decode_access_token(token)
        creator_user_id = token_payload.get("sub")

        if not creator_user_id:
            return HttpStatusCode.UNAUTHORIZED.response(
                message="Invalid token: user_id missing"
            )

        try:
            creator_user_id = uuid.UUID(creator_user_id)
        except (ValueError, AttributeError):
            return HttpStatusCode.BAD_REQUEST.response(
                message="Invalid user_id format in token"
            )

        users = await FRTUUsers.select(
            id=creator_user_id,
            columns=[FRTUUsers.id, FRTUUsers.name, FRTUUsers.email]
        )
        if not users:
            return HttpStatusCode.NOT_FOUND.response(
                message="Creator user not found"
            )
        
        payload = await request.json()
        permission_name = payload.get("name")  
        permission_desc = payload.get("description")  
        attribute_input = payload.get("attribute")
        
        if not attribute_input:
            return HttpStatusCode.BAD_REQUEST.response(
                message="'attribute' is required"
            )

        if isinstance(attribute_input, dict):
            attribute = [attribute_input]
        elif isinstance(attribute_input, list):
            attribute = attribute_input
        else:
            return HttpStatusCode.BAD_REQUEST.response(
                message="'attribute' must be an object or array of objects"
            )

        all_resources = await FRTUResources.select(
            columns=[FRTUResources.name, FRTUResources.description]
        )
        if not all_resources:
            return HttpStatusCode.INTERNAL_SERVER_ERROR.response(
                message="No resources found in system. Please seed resources first."
            )

        valid_resource_names = [r["name"] for r in all_resources]
        valid_actions = ["view", "create", "edit", "delete", "configure"]

        validated_attribute = []
        for item in attribute:
            if not isinstance(item, dict):
                return HttpStatusCode.BAD_REQUEST.response(
                    message="Each attribute item must be an object with 'resource' and 'action'"
                )

            resource = item.get("resource")
            actions = item.get("action")

            if not resource:
                return HttpStatusCode.BAD_REQUEST.response(
                    message="Each attribute must have 'resource' field"
                )
            if not actions or not isinstance(actions, list):
                return HttpStatusCode.BAD_REQUEST.response(
                    message=f"'action' for resource '{resource}' must be a non-empty array"
                )

            if resource not in valid_resource_names:
                return HttpStatusCode.BAD_REQUEST.response(
                    message=f"Invalid resource '{resource}'. Valid resources are: {', '.join(valid_resource_names)}"
                )

            for action in actions:
                if action not in valid_actions:
                    return HttpStatusCode.BAD_REQUEST.response(
                        message=f"Invalid action '{action}' for resource '{resource}'. Valid actions: {', '.join(valid_actions)}"
                    )

            validated_attribute.append({
                "resource": resource,
                "action": list(set(actions))
            })
        now = datetime.utcnow()
        creator = users[0]

        final_attribute = {
            "resources": validated_attribute
        }
        
        if permission_name:
            final_attribute["name"] = permission_name
        if permission_desc:
            final_attribute["description"] = permission_desc

        permission_id = uuid.uuid4()
        permission_obj = await FRTUPermissions.insert(
            id=permission_id,
            user_id=creator_user_id,
            attribute=final_attribute,  
            creation_time=now,
            last_update_time=now
        )

        return HttpStatusCode.CREATED.response(
            message="Permission created successfully",
            data={
                "id": str(permission_obj.id),
                "user_id": str(permission_obj.user_id),
                "name": permission_name,
                "description": permission_desc,
                "attribute": final_attribute,
                "resources_count": len(validated_attribute),
                "created_by": {
                    "user_id": str(creator["id"]),
                    "name": creator["name"],
                    "email": creator["email"]
                },
                "creation_time": permission_obj.creation_time.isoformat() if permission_obj.creation_time else None,
                "last_update_time": permission_obj.last_update_time.isoformat() if permission_obj.last_update_time else None
            }
        )

    except Exception as e:
        import traceback
        log.error(f"Failed to create permission: {traceback.format_exc()}")
        return HttpStatusCode.BAD_REQUEST.response(
            message=f"Failed to create permission: {str(e)}"
        )
    

# async def get_all_permissions(request: Request):
#     try:
#         permissions = await FRTUPermissions.select(
#             columns=[
#                 FRTUPermissions.id,
#                 FRTUPermissions.user_id,
#                 FRTUPermissions.attribute,
#                 FRTUPermissions.creation_time,
#                 FRTUPermissions.last_update_time
#             ]
#         )
        
#         if not permissions:
#             return HttpStatusCode.OK.response(
#                 message="No permissions found",
#                 data={
#                     "permissions": [],
#                     "total_count": 0
#                 }
#             )
        
#         permissions_data = []
        
#         for perm in permissions:
#             creator = None
#             if perm.get("user_id"):
#                 try:
#                     users = await FRTUUsers.select(
#                         id=perm["user_id"],
#                         columns=[FRTUUsers.id, FRTUUsers.name, FRTUUsers.email]
#                     )
#                     if users and len(users) > 0:
#                         creator_user = users[0]
#                         creator = {
#                             "user_id": str(creator_user["id"]),
#                             "name": creator_user["name"],
#                             "email": creator_user["email"]
#                         }
#                 except Exception as e:
#                     log.error(f"Failed to fetch creator info: {str(e)}")
#                     creator = None
            
#             attribute = perm.get("attribute") if perm.get("attribute") is not None else []
            
#             perm_data = {
#                 "id": str(perm["id"]),
#                 "user_id": str(perm["user_id"]) if perm.get("user_id") else None,
#                 "attribute": attribute,
#                 "resources_count": len(attribute) if isinstance(attribute, list) else 0,
#                 "is_system_permission": perm.get("user_id") is None,
#                 "created_by": creator if creator else {"user_id": None, "name": "System", "email": None},
#                 "creation_time": perm["creation_time"].isoformat() if perm.get("creation_time") else None,
#                 "last_update_time": perm["last_update_time"].isoformat() if perm.get("last_update_time") else None
#             }
            
#             permissions_data.append(perm_data)
        
#         return HttpStatusCode.OK.response(
#             message="Permissions retrieved successfully",
#             data={
#                 "permissions": permissions_data,
#                 "total_count": len(permissions_data)
#             }
#         )
    
#     except Exception as e:
#         import traceback
#         log.error(f"Failed to retrieve permissions: {traceback.format_exc()}")
#         return HttpStatusCode.BAD_REQUEST.response(
#             message=f"Failed to retrieve permissions: {str(e)}"
#         )

async def get_all_permissions(request: Request, authorization: str = Header(...), settings: Settings = Depends(Settings.get_settings)):
    try:
        if not authorization or not authorization.startswith("Bearer "):
            return HttpStatusCode.UNAUTHORIZED.response(message="Invalid Authorization header")

        token = authorization.split(" ")[1]
        try:
            token_payload = decode_access_token(token)
        except Exception as e:
            return HttpStatusCode.UNAUTHORIZED.response(message=f"Invalid or expired token: {str(e)}")

        user_id_param = request.query_params.get("user_id")
        filters = {}
        if user_id_param:
            try:
                filters["user_id"] = uuid.UUID(user_id_param)
            except Exception:
                return HttpStatusCode.BAD_REQUEST.response(message="Invalid user_id format in query params")

        permissions = await FRTUPermissions.select(
            columns=[
                FRTUPermissions.id,
                FRTUPermissions.user_id,
                FRTUPermissions.attribute,
                FRTUPermissions.creation_time,
                FRTUPermissions.last_update_time
            ],
            **filters
        )
        if not permissions:
            return HttpStatusCode.NOT_FOUND.response(message="No permissions found")

        all_resources = await FRTUResources.select(
            columns=[FRTUResources.name, FRTUResources.description]
        )
        resource_lookup = {r["name"]: r.get("description") for r in all_resources}

        data_list = []

        for perm in permissions:
            user_data = None
            if perm.get("user_id"):
                user_rows = await FRTUUsers.select(
                    columns=[
                        FRTUUsers.id,
                        FRTUUsers.name,
                        FRTUUsers.email,
                        FRTUUsers.mobile_no
                    ],
                    id=perm["user_id"]
                )
                if user_rows:
                    u = user_rows[0]
                    user_data = {
                        "user_id": str(u["id"]),
                        "name": u["name"],
                        "email": u["email"],
                        "mobile_no": u["mobile_no"]
                    }

            attr = perm.get("attribute", [])
            resource_actions = []
            for item in attr:
                resource = item.get("resource")
                actions = item.get("action", [])
                resource_actions.append({
                    "resource": resource,
                    "actions": actions
                })

            data_list.append({
                "id": str(perm["id"]),
                "user_id": str(perm["user_id"]),
                "resources_count": len(resource_actions),
                "attribute": resource_actions,
                "created_by": user_data,
                "creation_time": perm["creation_time"].isoformat() if perm.get("creation_time") else None,
                "last_update_time": perm["last_update_time"].isoformat() if perm.get("last_update_time") else None
            })

        return HttpStatusCode.OK.response(
            message="Permissions retrieved successfully",
            data={
                "permissions": data_list,
                "total_count": len(data_list)
            }
        )

    except Exception as e:
        import traceback
        log.error(f"Failed to retrieve permissions: {traceback.format_exc()}")
        return HttpStatusCode.BAD_REQUEST.response(
            message=f"Failed to retrieve permissions: {str(e)}"
        ) 


async def get_user_permissions(request: Request,authorization: str = Header(...),settings: Settings = Depends(Settings.get_settings)):
    try:
        if not authorization or not authorization.startswith("Bearer "):
            return HttpStatusCode.UNAUTHORIZED.response(
                message="Invalid Authorization header"
            )

        token = authorization.split(" ")[1]
        try:
            token_payload = decode_access_token(token)
        except Exception as e:
            return HttpStatusCode.UNAUTHORIZED.response(
                message=f"Invalid or expired token: {str(e)}"
            )

        requester_id_str = token_payload.get("sub")
        role = token_payload.get("role", "User")

        if not requester_id_str:
            return HttpStatusCode.UNAUTHORIZED.response(
                message="Invalid token: user_id missing"
            )

        requester_id = uuid.UUID(requester_id_str)
        requester_user = await FRTUUsers.select(id=requester_id)
        if not requester_user:
            return HttpStatusCode.NOT_FOUND.response(message="Requester user not found")

        requester_user = requester_user[0]

        username = request.query_params.get("username")

        target_users = []
        if role == "Tenant Admin":
            tenant_id = requester_user.get("attribute", {}).get("tenant_id")
            if not tenant_id:
                return HttpStatusCode.BAD_REQUEST.response(
                    message="Tenant Admin does not have tenant_id in attribute"
                )

            all_users = await FRTUUsers.select()
            for u in all_users:
                if u.get("attribute", {}).get("tenant_id") == tenant_id:
                    target_users.append(u)

        elif username:
            target_users = await FRTUUsers.select(name=username)
            if not target_users:
                return HttpStatusCode.NOT_FOUND.response(
                    message=f"User '{username}' not found"
                )
            if str(target_users[0]["id"]) != str(requester_id) and role != "Tenant Admin":
                return HttpStatusCode.FORBIDDEN.response(
                    message="Access denied. You can only view your own permissions."
                )
        else:
            target_users = [requester_user]

        all_resources = await FRTUResources.select(
            columns=[FRTUResources.name, FRTUResources.description]
        )
        resource_lookup = {r["name"]: r.get("description") for r in all_resources}

        response_list = []

        for user in target_users:
            permissions = await FRTUPermissions.select(
                columns=[
                    FRTUPermissions.id,
                    FRTUPermissions.user_id,
                    FRTUPermissions.attribute,
                    FRTUPermissions.creation_time,
                    FRTUPermissions.last_update_time,
                ],
                user_id=user["id"],
            )

            perm_data = []
            for p in permissions:
                attr = p.get("attribute", [])
                for item in attr:
                    resource = item.get("resource")
                    actions = item.get("action", [])
                    perm_data.append(
                        {
                            "resource": resource,
                            "description": resource_lookup.get(resource, ""),
                            "actions": actions,
                        }
                    )

            response_list.append(
                {
                    "user": {
                        "id": str(user["id"]),
                        "name": user["name"],
                        "email": user["email"],
                        "mobile_no": user["mobile_no"],
                        "role": user.get("attribute", {}).get("role"),
                    },
                    "permissions": perm_data,
                    "total_resources": len(perm_data),
                }
            )

        return HttpStatusCode.OK.response(
            message="User permissions retrieved successfully",
            data=response_list,
        )

    except Exception as e:
        import traceback

        log.error(f"Failed to get user permissions: {traceback.format_exc()}")
        return HttpStatusCode.BAD_REQUEST.response(
            message=f"Failed to get user permissions: {str(e)}"
        )


async def update_permission(request: Request,authorization: str = Header(...),settings: Settings = Depends(Settings.get_settings)):

    try:
        if not authorization or not authorization.startswith("Bearer "):
            return HttpStatusCode.UNAUTHORIZED.response(
                message="Invalid Authorization header"
            )

        token = authorization.split(" ")[1]
        try:
            token_payload = decode_access_token(token)
        except Exception as e:
            return HttpStatusCode.UNAUTHORIZED.response(
                message=f"Invalid or expired token: {str(e)}"
            )

        user_id_str = token_payload.get("sub")
        if not user_id_str:
            return HttpStatusCode.UNAUTHORIZED.response(
                message="Invalid token: user_id missing"
            )
        user_id = uuid.UUID(user_id_str)

        user = await FRTUUsers.select(id=user_id)
        if not user:
            return HttpStatusCode.NOT_FOUND.response(message="User not found")

        payload = await request.json()
        new_attribute = payload.get("attribute")
        if not new_attribute:
            return HttpStatusCode.BAD_REQUEST.response(
                message="'attribute' is required"
            )

        if isinstance(new_attribute, dict):
            new_attribute = [new_attribute]

        valid_resources = await FRTUResources.select(columns=[FRTUResources.name])
        valid_resource_names = [r["name"] for r in valid_resources]
        valid_actions = ["view", "create", "edit", "delete", "configure"]

        validated = []
        for item in new_attribute:
            if item.get("resource") not in valid_resource_names:
                return HttpStatusCode.BAD_REQUEST.response(
                    message=f"Invalid resource '{item.get('resource')}'. Valid: {', '.join(valid_resource_names)}"
                )
            if not isinstance(item.get("action"), list):
                return HttpStatusCode.BAD_REQUEST.response(
                    message=f"'action' must be list for resource '{item.get('resource')}'"
                )
            for act in item["action"]:
                if act not in valid_actions:
                    return HttpStatusCode.BAD_REQUEST.response(
                        message=f"Invalid action '{act}' in resource '{item.get('resource')}'"
                    )
            validated.append(item)

        existing = await FRTUPermissions.select(user_id=user_id)
        now = datetime.utcnow()

        if existing:
            existing_attr = existing[0].get("attribute", [])
            existing_resources = {item["resource"]: item["action"] for item in existing_attr}
            for item in validated:
                if item["resource"] in existing_resources:
                    existing_resources[item["resource"]] = list(
                        set(existing_resources[item["resource"]] + item["action"])
                    )
                else:
                    existing_resources[item["resource"]] = item["action"]

            merged_attr = [
                {"resource": res, "action": acts} for res, acts in existing_resources.items()
            ]

            await FRTUPermissions.update(
                conditions={"id": existing[0]["id"]},
                attribute=merged_attr,
                last_update_time=now,
            )

            return HttpStatusCode.OK.response(
                message="Permissions updated successfully",
                data={"attribute": merged_attr},
            )

        else:
            permission_id = uuid.uuid4()
            value = await FRTUPermissions.insert(
                id=permission_id,
                user_id=user_id,
                attribute=validated,
                creation_time=now,
                last_update_time=now,
            )
            return HttpStatusCode.CREATED.response(
                message="New permission record created",
                data=value.as_dict() if hasattr(value, "as_dict") else validated,
            )

    except Exception as e:
        import traceback
        log.error(f"Failed to update permission: {traceback.format_exc()}")
        return HttpStatusCode.BAD_REQUEST.response(
            message=f"Failed to update permission: {str(e)}"
        )


async def delete_permission(request: Request,authorization: str = Header(...),settings: Settings = Depends(Settings.get_settings)):

    try:
        if not authorization or not authorization.startswith("Bearer "):
            return HttpStatusCode.UNAUTHORIZED.response(
                message="Invalid Authorization header"
            )

        token = authorization.split(" ")[1]
        token_payload = decode_access_token(token)
        user_id_str = token_payload.get("sub")

        if not user_id_str:
            return HttpStatusCode.UNAUTHORIZED.response(
                message="Invalid token: user_id missing"
            )

        user_id = uuid.UUID(user_id_str)

        existing = await FRTUPermissions.select(user_id=user_id)
        if not existing:
            return HttpStatusCode.NOT_FOUND.response(
                message="No permission record found for this user"
            )

        permission = existing[0]
        resource = request.query_params.get("resource")

        if not resource:
            await FRTUPermissions.delete(conditions={"id": permission["id"]})
            return HttpStatusCode.OK.response(
                message="All permissions deleted for this user"
            )

        attr = permission.get("attribute", [])
        updated_attr = [a for a in attr if a.get("resource") != resource]

        if len(updated_attr) == len(attr):
            return HttpStatusCode.NOT_FOUND.response(
                message=f"Resource '{resource}' not found in permissions"
            )

        await FRTUPermissions.update(
            conditions={"id": permission["id"]},
            attribute=updated_attr,
            last_update_time=datetime.utcnow(),
        )

        return HttpStatusCode.OK.response(
            message=f"Permission for resource '{resource}' deleted successfully",
            data={"remaining_permissions": updated_attr},
        )

    except Exception as e:
        import traceback
        log.error(f"Failed to delete permission: {traceback.format_exc()}")
        return HttpStatusCode.BAD_REQUEST.response(
            message=f"Failed to delete permission: {str(e)}"
        )



async def get_available_resources(request: Request):
    try:
        resources = await FRTUResources.select(
            columns=[
                FRTUResources.id,
                FRTUResources.name,
                FRTUResources.description,
                FRTUResources.attribute
            ]
        )
        
        if not resources:
            return HttpStatusCode.OK.response(
                message="No resources found",
                data={
                    "resources": [],
                    "total_count": 0,
                    "available_actions": []
                }
            )
        
        resources_data = []
        
        for res in resources:
            res_data = {
                "id": str(res["id"]),
                "name": res["name"],
                "description": res.get("description"),
                "display_name": res.get("attribute", {}).get("display_name") if res.get("attribute") else None,
                "icon": res.get("attribute", {}).get("icon") if res.get("attribute") else None,
                "category": res.get("attribute", {}).get("category") if res.get("attribute") else None,
                "order": res.get("attribute", {}).get("order") if res.get("attribute") else 999
            }
            resources_data.append(res_data)
        
        resources_data.sort(key=lambda x: x["order"])
        
        return HttpStatusCode.OK.response(
            message="Resources retrieved successfully",
            data={
                "resources": resources_data,
                "total_count": len(resources_data),
                "available_actions": ["view", "create", "edit", "delete", "configure"]
            }
        )
    
    except Exception as e:
        import traceback
        log.error(f"Failed to retrieve resources: {traceback.format_exc()}")
        return HttpStatusCode.BAD_REQUEST.response(
            message=f"Failed to retrieve resources: {str(e)}"
        )


async def check_user_permission(request: Request, authorization: str = Header(...)):
    try:
        # Verify authorization
        if not authorization or not authorization.startswith("Bearer "):
            return HttpStatusCode.UNAUTHORIZED.response(
                message="Invalid Authorization header"
            )
        
        token = authorization.split(" ")[1]
        token_payload = decode_access_token(token)
        user_id_str = token_payload.get("sub")
        
        if not user_id_str:
            return HttpStatusCode.UNAUTHORIZED.response(
                message="Invalid token"
            )
        
        user_id = uuid.UUID(user_id_str)
        
        # Get payload
        payload = await request.json()
        resource = payload.get("resource")
        action = payload.get("action")
        
        if not resource or not action:
            return HttpStatusCode.BAD_REQUEST.response(
                message="'resource' and 'action' are required"
            )
        
        # Get user's role assignments
        from src.models.frtu_user_assignment import FRTUUserAssignment
        from src.models.frtu_roles import FRTURoles
        
        assignments = await FRTUUserAssignment.select(
            user_id=user_id,
            columns=[FRTUUserAssignment.role_id]
        )
        
        if not assignments:
            return HttpStatusCode.OK.response(
                message="User has no role assignments",
                data={
                    "has_permission": False,
                    "resource": resource,
                    "action": action
                }
            )
        
        # Check each role's permissions
        has_permission = False
        
        for assignment in assignments:
            role_id = assignment["role_id"]
            
            # Get role permissions
            role_perms = await FRTURolePermissions.select(
                role_id=role_id,
                columns=[FRTURolePermissions.permission_id]
            )
            
            if role_perms:
                for rp in role_perms:
                    # Get permission details
                    perms = await FRTUPermissions.select(
                        id=rp["permission_id"],
                        columns=[FRTUPermissions.attribute]
                    )
                    
                    if perms:
                        perm = perms[0]
                        attribute = perm.get("attribute", [])
                        
                        # Check if permission includes the resource and action
                        for item in attribute:
                            if item.get("resource") == resource:
                                if action in item.get("action", []):
                                    has_permission = True
                                    break
                        
                        if has_permission:
                            break
            
            if has_permission:
                break
        
        return HttpStatusCode.OK.response(
            message="Permission check completed",
            data={
                "has_permission": has_permission,
                "resource": resource,
                "action": action
            }
        )
    
    except Exception as e:
        import traceback
        log.error(f"Failed to check permission: {traceback.format_exc()}")
        return HttpStatusCode.BAD_REQUEST.response(
            message=f"Failed to check permission: {str(e)}"
        )


# async def create_permission(request: Request, authorization: str = Header(...), settings: Settings = Depends(Settings.get_settings)):
#     try:
#         if not authorization.startswith("Bearer "):
#             return HttpStatusCode.UNAUTHORIZED.response(message="Invalid Authorization header")

#         payload = await request.json()
#         user_id = await request.id
#         name = payload.get("name")
#         attribute = payload.get("attribute", {})

#         if not name:
#             return HttpStatusCode.BAD_REQUEST.response(message="Permission name is required")

#         existing = await FRTUPermissions.select(name=name)
#         if existing:
#             return HttpStatusCode.BAD_REQUEST.response(message=f"Permission '{name}' already exists")

#         now = datetime.now(UTC).replace(tzinfo=None)
#         perm = await FRTUPermissions.insert(
#             # name=name,
#             attribute=attribute,
#             creation_time=now,
#             last_update_time=now
#         )

#         return HttpStatusCode.CREATED.response(
#             message="Permission created successfully",
#             data={"id": str(perm.id),  "attribute": perm.attribute}
#         )
#     except Exception as e:
#         return HttpStatusCode.BAD_REQUEST.response(message=str(e))


# async def get_permissions(request: Request):
#     try:
#         permissions = await FRTUPermissions.select()
#         data = [{
#             "id": str(p["id"]),
#             "name": p["name"],
#             "attribute": p.get("attribute", {}),
#             "creation_time": p["creation_time"].isoformat() if p["creation_time"] else None
#         } for p in permissions]

#         return HttpStatusCode.OK.response(message="Permissions retrieved", data=data)
#     except Exception as e:
#         return HttpStatusCode.BAD_REQUEST.response(message=str(e))


# async def update_permission(request: Request, name: str, authorization: str = Header(...)):
#     try:
#         if not authorization.startswith("Bearer "):
#             return HttpStatusCode.UNAUTHORIZED.response(message="Invalid Authorization header")

#         payload = await request.json()
#         permissions = await FRTUPermissions.select(name=name)
#         if not permissions:
#             return HttpStatusCode.NOT_FOUND.response(message=f"Permission '{name}' not found")

#         perm = permissions[0]
#         update_data = {}

#         if "new_name" in payload:
#             update_data["name"] = payload["new_name"]

#         if "attribute" in payload:
#             merged_attr = {**(perm.get("attribute") or {}), **payload["attribute"]}
#             update_data["attribute"] = merged_attr

#         update_data["last_update_time"] = datetime.utcnow()

#         await FRTUPermissions.update(extra={}, conditions={"id": perm["id"]}, **update_data)

#         return HttpStatusCode.OK.response(message="Permission updated successfully")
#     except Exception as e:
#         return HttpStatusCode.BAD_REQUEST.response(message=str(e))


# async def delete_permission(request: Request, name: str, authorization: str = Header(...)):
#     try:
#         if not authorization.startswith("Bearer "):
#             return HttpStatusCode.UNAUTHORIZED.response(message="Invalid Authorization header")

#         permissions = await FRTUPermissions.select(name=name)
#         if not permissions:
#             return HttpStatusCode.NOT_FOUND.response(message=f"Permission '{name}' not found")

#         perm = permissions[0]
#         await FRTUPermissions.delete(conditions={"id": perm["id"]})
#         return HttpStatusCode.OK.response(message=f"Permission '{name}' deleted successfully")
#     except Exception as e:
#         return HttpStatusCode.BAD_REQUEST.response(message=str(e))


