from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4
from fastapi import HTTPException
from pydantic import BaseModel


class Protocol(BaseModel):
    id: UUID = None
    channel_type: str
    baud_rate: str
    parity: str
    stop_bits: str
    data_bits: str
    module_counts: str
    channel_description: Optional[str] = ''
    flow_control: Optional[str] = ''
    master_mode: Optional[str] = ''
    module_address_scheme: Optional[str] = ''
    physical_port: Optional[str] = ''
    enabled: bool = True
    status: Optional[str] = 'Active'

protocols_mock: List[Protocol] = []

def create_protocol(data: Protocol) -> Protocol:
    new_protocol = data.copy(update={"id": uuid4()})
    protocols_mock.append(new_protocol)
    return new_protocol

def get_protocol(protocol_id: UUID) -> Optional[Protocol]:
    for proto in protocols_mock:
        if proto.id == protocol_id:
            return proto
    return None

def list_protocols(page: int = 1, limit: int = 10) -> List[Protocol]:
    start = (page - 1) * limit
    end = start + limit
    return protocols_mock[start:end]

def search_protocols(
    name: Optional[str] = None
) -> List[Protocol]:
    if name:
        # Case-insensitive partial match on channel_type
        return [
            proto for proto in protocols_mock
            if name.lower() in proto.channel_type.lower()
        ]
    return protocols_mock

def get_total_records(name: Optional[str] = None) -> int:
    if name:
        return len(search_protocols(name))
    return len(protocols_mock)


def update_protocol(protocol_id: UUID, update_fields: Dict[str, Any]) -> Optional[Protocol]:
    for idx, proto in enumerate(protocols_mock):
        if proto.id == protocol_id:
            # Only update supplied fields, preserve everything else
            updated_protocol = proto.copy(update=update_fields)
            protocols_mock[idx] = updated_protocol
            return updated_protocol
    return None

def delete_protocol(protocol_id: UUID, is_deleted: bool) -> bool:
    if not is_deleted:
        return False
    for idx, proto in enumerate(protocols_mock):
        if proto.id == protocol_id:
            protocols_mock.pop(idx)
            return True
    return False


async def toggle_protocol_status(protocol_id: str, enabled: bool) -> Protocol:
    for index, protocol in enumerate(protocols_mock):
        if protocol.id == protocol_id:
            updated_protocol = protocol.copy(update={"enabled": enabled})
            protocols_mock[index] = updated_protocol
            return updated_protocol
    raise HTTPException(status_code=404, detail="Protocol not found")

async def get_protocols_by_channel(channel_id: str) -> List[Protocol]:
    return [protocol for protocol in protocols_mock if protocol.channel_id == channel_id]   

async def get_active_protocols() -> List[Protocol]:
    return [protocol for protocol in protocols_mock if protocol.enabled]

async def get_protocols_by_type(channel_type: str) -> List[Protocol]:
    return [protocol for protocol in protocols_mock if protocol.channel_type == channel_type]

async def count_protocols() -> int:
    return len(protocols_mock)

