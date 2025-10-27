# import os

# BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# DI_INI_PATH = os.path.join(BASE_DIR, "config", "rtu_config_iec104_di.ini")
# DO_INI_PATH = os.path.join(BASE_DIR, "config", "rtu_config_iec104_do.ini")


# def update_ini_file(ini_path, serial_channel, channel_key, ioa, ts, is_configure, serialport=None, deviceid=None, devicetype=None):
#     if not os.path.exists(ini_path):
#         raise FileNotFoundError(f"INI file not found at {ini_path}")
    
#     with open(ini_path, 'r') as f:
#         lines = f.readlines()
    
#     section_found = False
#     section_start = -1
#     section_end = -1
#     channel_line_updated = False
    
#     for i, line in enumerate(lines):
#         stripped = line.strip()
        
#         if stripped == f"[{serial_channel}]":
#             section_found = True
#             section_start = i
#             continue
        
#         if section_found and stripped.startswith("[") and stripped.endswith("]"):
#             section_end = i
#             break
        
#         if section_found:
#             # if stripped.startswith("serialport") and serialport:
#             #     lines[i] = f"serialport = {serialport}\n"
#             if stripped.startswith("deviceid") and deviceid:
#                 lines[i] = f"deviceid = {deviceid}\n"
#             elif stripped.startswith("devicetype") and devicetype:
#                 lines[i] = f"devicetype = {devicetype}\n"
#             elif stripped.startswith("status"):
#                 lines[i] = f"status = ENABLED\n"
#             elif stripped.startswith(channel_key):
#                 lines[i] = f"{channel_key} = {ioa},{ts},{is_configure}\n"
#                 channel_line_updated = True
    
#     if section_found and not channel_line_updated:
#         insert_pos = section_end if section_end != -1 else len(lines)
#         for i in range(section_start + 1, insert_pos):
#             if lines[i].strip().startswith("di_sp_conf") or lines[i].strip().startswith("do_sp_conf"):
#                 lines.insert(i, f"{channel_key} = {ioa},{ts},{is_configure}\n")
#                 break
    
#     if not section_found:
#         lines.append(f"\n[{serial_channel}]\n")
#         # if serialport:
#         #     lines.append(f"serialport = {serialport}\n")
#         if deviceid:
#             lines.append(f"deviceid = {deviceid}\n")
#         if devicetype:
#             lines.append(f"devicetype = {devicetype}\n")
#         lines.append(f"status = ENABLED\n")
#         lines.append(f"{channel_key} = {ioa},{ts},{is_configure}\n")
    
#     with open(ini_path, 'w') as f:
#         f.writelines(lines)

from src.utils.frtu_client import frtu_client

def update_ini_file(ini_path, serial_channel, channel_key, ioa, ts, is_configure, 
                   serialport=None, deviceid=None, devicetype=None):
    """Update INI file on FRTU device"""
    module_type = "DI" if "di" in ini_path.lower() else "DO"
    
    return frtu_client.update_ini_file(
        module_type=module_type,
        serial_channel=serial_channel,
        channel_key=channel_key,
        ioa=ioa,
        ts=ts,
        is_configure=is_configure,
        serialport=serialport,
        deviceid=deviceid,
        devicetype=devicetype
    )

