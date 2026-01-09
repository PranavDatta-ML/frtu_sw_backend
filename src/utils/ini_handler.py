from typing import Any, Dict, List

from src.utils.frtu_client import frtu_client

# def regenerate_module_ini(
#     ini_path: str, 
#     serial_channel: str,
#     channels: Dict[str, Any],
#     dp_pairs: List[str],
#     deviceid: str = None,
#     devicetype: str = "DI"
# ) -> bool:
#     success_count = 0
    
#     for key, cfg in channels.items():
#         if not cfg.get("is_enabled", False):
#             continue
            
#         ch_no = str(cfg["channel_no"])
#         ioa_val = cfg.get("ioa", "0")
#         ts_val = "1" if cfg.get("timestamp_enable", False) else "0"
#         enable_val = "1"
        
#         if frtu_client.update_ini_file(
#             module_type=devicetype,
#             serial_channel=serial_channel,
#             channel_key=ch_no,
#             ioa=ioa_val,
#             ts=ts_val,
#             is_configure=enable_val,
#             serialport=None,
#             deviceid=deviceid,
#             devicetype=devicetype
#         ):
#             success_count += 1
    
#     if dp_pairs:
#         dp_conf_value = "%".join(dp_pairs)
#         if frtu_client.update_ini_file(
#             module_type=devicetype,
#             serial_channel=serial_channel,
#             channel_key="dp_conf",
#             ioa=dp_conf_value,
#             ts="0",
#             is_configure="1",
#             serialport=None,
#             deviceid=deviceid,
#             devicetype=devicetype
#         ):
#             success_count += 1
    
#     return success_count > 0

def regenerate_module_ini(
    ini_path: str, 
    serial_channel: str,
    channels: Dict[str, Any],
    dp_pairs: List[str],
    deviceid: str = None,
    devicetype: str = "DI"
) -> bool:
    success_count = 0

    for cfg in channels.values():
        try:
            ch_no_int = int(str(cfg["channel_no"]))
            if not (1 <= ch_no_int <= 16):
                continue
        except (KeyError, ValueError):
            continue
            
        ch_no = str(ch_no_int)
        ioa_val = str(cfg.get("ioa", "0"))
        ts_val = "1" if cfg.get("timestamp_enable", False) else "0"
        
        # FIXED is_enabled mapping: 0=Disable, 1=w/scada, 2=w/o scada
        is_enabled_raw = cfg.get("is_enabled")
        if isinstance(is_enabled_raw, bool):
            enable_val = "1" if is_enabled_raw else "0"
        elif isinstance(is_enabled_raw, int):
            enable_val = str(is_enabled_raw)  # 0, 1, or 2
        else:
            enable_val = "0"
            
        sp_dp = "1" if cfg.get("channel_type") == "Double Point Parameter" else "0"
        
        # ALL STRINGS, 4 values always: ioa,ts,enable,sp_dp
        complete_ioa = f"{ioa_val},{ts_val},{enable_val},{sp_dp}"

        if frtu_client.update_ini_file(
            module_type=devicetype,
            serial_channel=serial_channel,
            channel_key=ch_no,
            ioa=complete_ioa,
            ts="0",
            is_configure="0",
            serialport=None,
            deviceid=deviceid,
            devicetype=devicetype,
        ):
            success_count += 1

    # FIXED dp_conf: clean format
    if dp_pairs:
        dp_conf_value = "%".join(dp_pairs)
        if frtu_client.update_ini_file(
            module_type=devicetype,
            serial_channel=serial_channel,
            channel_key="dp_conf",
            ioa=dp_conf_value,
            ts="0",
            is_configure="1",
            serialport=None,
            deviceid=deviceid,
            devicetype=devicetype,
        ):
            success_count += 1

    return success_count > 0



