from typing import Dict, Any, Optional
from src.utils.frtu_client import frtu_client

DP = "Double Point Parameter"


def build_di_ini_payload(
    slot_number: int,
    channels: Dict[str, Dict[str, Any]],
    serial_number: Optional[str],
):
    return {
        "slot_number": slot_number,
        "serial_number": serial_number,
        "channels": channels,
    }


def _get_ch_no(ch: dict) -> str:
    v = ch.get("channelNo")
    if v is None:
        v = ch.get("channel_no")
    return str(v or "").strip()


def _get_assoc(ch: dict) -> str:
    v = ch.get("associateChannelNo")
    if v is None:
        v = ch.get("associate_channel_no")
    return str(v or "").strip()


def update_di_ini_for_module(
    device_id: str,   # DI module serial_number
    slot_number: int,
    channels: Dict[str, Dict[str, Any]],
) -> None:
    if slot_number < 4:
        return

    module_index = slot_number - 3
    serial_channel = f"MODULE_{module_index}"

    # 1..16 channel lines
    for ch_no in range(1, 17):
        key = f"channel_{ch_no}"
        ch = channels.get(key, {})

        ioa = str(ch.get("ioa") or "0")
        ts_flag = "1" if ch.get("timestampEnable") else "0"

        # channel_enable: 0=disabled, 1=enabled with SCADA, 2=enabled without SCADA
        status = bool(ch.get("status"))
        scada_type = str(ch.get("scadaPointType") or "0")
        if not status:
            enable = "0"
        else:
            enable = "1" if scada_type == "0" else "2"

        sp_dp = "1" if ch.get("channelType") == DP else "0"

        value = f"{ioa},{ts_flag},{enable},{sp_dp}"

        frtu_client.update_ini_file(
            module_type="DI",
            serial_channel=serial_channel,
            channel_key=str(ch_no),
            ioa=value,
            ts="0",
            is_configure="1",
            serialport=None,
            deviceid=device_id,
            devicetype="DI",
        )

    # DP pairing -> dp_conf
    dp_pairs = []
    visited = set()

    for ch in channels.values():
        if ch.get("channelType") != DP:
            continue
        if not ch.get("status"):
            continue

        ch_no = _get_ch_no(ch)
        assoc_no = _get_assoc(ch)
        if not ch_no or not assoc_no:
            continue

        if ch_no in visited or assoc_no in visited:
            continue

        peer = channels.get(f"channel_{assoc_no}")
        if not peer:
            continue
        if peer.get("channelType") != DP:
            continue
        if not peer.get("status"):
            continue

        peer_assoc = _get_assoc(peer)
        if peer_assoc != ch_no:
            continue

        if peer.get("timestampEnable") != ch.get("timestampEnable"):
            continue

        ns1 = (ch.get("normalState") or "").strip().upper()
        ns2 = (peer.get("normalState") or "").strip().upper()

        if ns1 == "ON" and ns2 == "OFF":
            ordered = (ch_no, assoc_no)
        elif ns1 == "OFF" and ns2 == "ON":
            ordered = (assoc_no, ch_no)
        else:
            ordered = tuple(sorted([ch_no, assoc_no], key=int))

        dp_pairs.append(f"{ordered[0]},{ordered[1]}")
        visited.update([ch_no, assoc_no])

    dp_conf_value = "%".join(dp_pairs) if dp_pairs else ""

    frtu_client.update_ini_file(
        module_type="DI",
        serial_channel=serial_channel,
        channel_key="dp_conf",
        ioa=dp_conf_value,
        ts="0",
        is_configure="1",
        serialport=None,
        deviceid=device_id,
        devicetype="DI",
    )


def clear_di_ini_slot(device_id: str, slot_number: int) -> None:
    if slot_number < 4:
        return

    module_index = slot_number - 3
    serial_channel = f"MODULE_{module_index}"

    for ch_no in range(1, 17):
        frtu_client.update_ini_file(
            module_type="DI",
            serial_channel=serial_channel,
            channel_key=str(ch_no),
            ioa="0,0,0,0",
            ts="0",
            is_configure="1",
            serialport=None,
            deviceid=device_id,
            devicetype="DI",
        )

    frtu_client.update_ini_file(
        module_type="DI",
        serial_channel=serial_channel,
        channel_key="dp_conf",
        ioa="",
        ts="0",
        is_configure="1",
        serialport=None,
        deviceid=device_id,
        devicetype="DI",
    )
