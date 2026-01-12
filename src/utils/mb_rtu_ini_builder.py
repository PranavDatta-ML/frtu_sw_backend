def build_mb_ini_payload(payload):
    return {
        "slot_number": payload.slotInfo.slotNumber,
        "protocol": payload.categoryInfo.communicationProtocol,
        "channels": payload.categoryInfo.channels
    }

