from typing import Dict, Any
from src.utils.frtu_client import frtu_client


def update_do_ini_for_module(
    device_id: str,
    slot_number: int,
    channels: Dict[str, Dict[str, Any]],
) -> None:
    if slot_number < 4:
        return

    module_index = slot_number - 3
    serial_channel = f"MODULE_{module_index}"

    dp_pairs = []
    visited = set()

    for ch in channels.values():
        ch_no = ch["channelNo"]
        ioa = ch["ioa"]
        ts = "1" if ch["timestampEnable"] else "0"
        enable = "1" if ch["status"] else "0"
        pulse = ch["PulseType"]
        sbo = ch["sboFlag"]
        single_double = "1" if ch["channelType"] == "Double Point Parameter" else "0"

        value = f"{ioa},{ts},{enable},{pulse},{sbo},{single_double}"

        frtu_client.update_do_module_ini(
            serial_channel=serial_channel,
            channel_key=ch_no,
            value=value,
        )

        if single_double == "1":
            assoc = ch.get("associateChannelNo")
            if assoc and ch_no not in visited:
                pair = sorted([ch_no, assoc], key=int)
                dp_pairs.append(f"{pair[0]},{pair[1]}")
                visited.update(pair)

    frtu_client.update_do_module_ini(
        serial_channel=serial_channel,
        channel_key="dp_conf",
        value="%".join(dp_pairs),
    )

def clear_do_ini_slot(
    device_id: str,
    slot_number: int,
) -> None:
    if slot_number < 4:
        return

    module_index = slot_number - 3
    serial_channel = f"MODULE_{module_index}"

    for ch_no in range(1, 11):
        frtu_client.update_do_module_ini(
            serial_channel=serial_channel,
            channel_key=str(ch_no),
            value="0,0,0,0,0,0",
        )

    frtu_client.update_do_module_ini(
        serial_channel=serial_channel,
        channel_key="dp_conf",
        value="",
    )
