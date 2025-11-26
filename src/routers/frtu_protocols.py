from typing import Any, Dict, Optional
from uuid import UUID
from fastapi import APIRouter, HTTPException, Query

from src.views.frtu_protocols import Protocol, create_protocol, delete_protocol, get_protocol, list_protocols, search_protocols, update_protocol

router = APIRouter(
    prefix="/api/protocol",
    tags=['frtu_protocols']
)

@router.post("/", response_model=dict)
def api_create_protocol(data: Protocol):
    proto = create_protocol(data)
    response = {
        "http_code": 200,
        "code": "OK",
        "message": "Protocol created successfully",
        "data": proto.dict()  # exclude id from data, or include if needed
    }
    return response

@router.get("/{protocol_id}", response_model=dict)
def api_get_protocol(protocol_id: UUID):
    proto = get_protocol(protocol_id)
    if proto:
        return {
            "http_code": 200,
            "code": "OK",
            "message": "Protocol found",
            "data": proto.dict()
        }
    raise HTTPException(status_code=404, detail="Protocol not found")


@router.get("/", response_model=dict)
def api_list_protocols(
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1),
    name: Optional[str] = Query(None, description="Search by channel_type (partial/full)")
):
    # Determine full matching set and page according to search
    matching_protocols = search_protocols(name)
    total_records = len(matching_protocols)
    start = (page - 1) * limit
    end = start + limit
    paged_protocols = matching_protocols[start:end]

    return {
        "http_code": 200,
        "code": "OK",
        "message": "Protocols fetched successfully",
        "data": [proto.dict() for proto in paged_protocols],
        "pagination": {
            "page": page,
            "limit": limit,
            "total_records": total_records,
            "records_on_page": len(paged_protocols),
        }
    }

@router.put("/{protocol_id}", response_model=dict)
def api_update_protocol(protocol_id: UUID, update_fields: Dict[str, Any]):
    updated = update_protocol(protocol_id, update_fields)
    if updated:
        return {
            "http_code": 200,
            "code": "OK",
            "message": "Protocol partially updated",
            "data": updated.dict()
        }
    raise HTTPException(status_code=404, detail="Protocol not found")



@router.delete("/{protocol_id}", response_model=dict)
def api_delete_protocol(protocol_id: UUID, is_deleted: bool = Query(..., description="Set true to confirm delete")):
    deleted = delete_protocol(protocol_id, is_deleted)
    if deleted:
        return {
            "http_code": 200,
            "code": "OK",
            "message": "Protocol deleted successfully",
            "data": None
        }
    if not is_deleted:
        return {
            "http_code": 400,
            "code": "DELETE_NOT_CONFIRMED",
            "message": "Delete not confirmed. Pass is_deleted=true to proceed.",
            "data": None
        }
    raise HTTPException(status_code=404, detail="Protocol not found")

