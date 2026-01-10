from typing import Dict, Any
from src.utils.frtu_client import frtu_client


def update_di_ini_for_module(
    device_id: str,
    slot_number: int,
    channels: Dict[str, Dict[str, Any]],
) -> None:
    if slot_number < 4:
        return

    module_index = slot_number - 3
    serial_channel = f"MODULE_{module_index}"

    # write all 16 channels
    for ch_no in range(1, 17):
        key = f"channel_{ch_no}"
        ch = channels.get(key, {})

        ioa = str(ch.get("ioa") or "0")
        ts = "1" if ch.get("timestampEnable") else "0"
        enable = "1" if ch.get("status") else "0"
        sp_dp = "1" if ch.get("channelType") == "Double Point Parameter" else "0"

        value = f"{ioa},{ts},{enable},{sp_dp}"

        frtu_client.update_di_module_ini(
            # module_type="DI",
            serial_channel=serial_channel,
            channel_key=str(ch_no),
            ioa=value,
            # deviceid=device_id,
            # devicetype="DI",
        )

    # DP pairing
    dp_pairs = []
    visited = set()

    for ch in channels.values():
        if ch.get("channelType") != "Double Point Parameter":
            continue
        if not ch.get("status"):
            continue

        ch_no = str(ch.get("channel_no"))
        assoc = ch.get("associate_channel_no")
        if not assoc:
            continue

        assoc_no = str(assoc)
        if ch_no in visited or assoc_no in visited:
            continue

        peer = channels.get(f"channel_{assoc_no}")
        if not peer:
            continue
        if not peer.get("status"):
            continue
        if peer.get("associate_channel_no") != ch_no:
            continue
        if peer.get("timestampEnable") != ch.get("timestampEnable"):
            continue

        ordered = sorted([ch_no, assoc_no], key=int)
        dp_pairs.append(f"{ordered[0]},{ordered[1]}")
        visited.update(ordered)

    frtu_client.update_di_module_ini(
        module_type="DI",
        serial_channel=serial_channel,
        channel_key="dp_conf",
        ioa="%".join(dp_pairs) if dp_pairs else "",
        deviceid=device_id,
        devicetype="DI",
    )


def clear_di_ini_slot(device_id: str, slot_number: int) -> None:
    if slot_number < 4:
        return

    module_index = slot_number - 3
    serial_channel = f"MODULE_{module_index}"

    for ch_no in range(1, 17):
        frtu_client.update_di_module_ini(
            module_type="DI",
            serial_channel=serial_channel,
            channel_key=str(ch_no),
            ioa="0,0,0,0",
            deviceid=device_id,
            devicetype="DI",
        )

    frtu_client.update_di_module_ini(
        module_type="DI",
        serial_channel=serial_channel,
        channel_key="dp_conf",
        ioa="0,0,0,0",
        deviceid=device_id,
        devicetype="DI",
    )
