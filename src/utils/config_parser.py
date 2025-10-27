# import os

# BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# DEVIDS_CONF_PATH = os.path.join(BASE_DIR, "config", "devids.conf")
# VERSION_CONF_PATH = os.path.join(BASE_DIR, "config", "version.conf")

# def parse_devids_conf():
#     if not os.path.exists(DEVIDS_CONF_PATH):
#         raise FileNotFoundError(f"devids.conf not found at {DEVIDS_CONF_PATH}")

#     modules = []
#     with open(DEVIDS_CONF_PATH, "r") as f:
#         for line in f:
#             line = line.strip()
#             if line.startswith("#") or not line:
#                 continue
#             parts = line.split()
#             if len(parts) >= 5:
#                 modules.append({
#                     "slot_no": int(parts[0]),
#                     "dev_path": parts[1],
#                     "module_id": parts[2],
#                     "gpino": parts[3],
#                     "type_flag": int(parts[4])  
#                 })
#     return modules


# def update_devids_conf(slot_number, module_type):
#     if not os.path.exists(DEVIDS_CONF_PATH):
#         raise FileNotFoundError(f"devids.conf not found at {DEVIDS_CONF_PATH}")
    
#     lines = []
#     with open(DEVIDS_CONF_PATH, "r") as f:
#         lines = f.readlines()
    
#     devids_slot_no = slot_number - 3
#     type_flag = 1 if module_type == "DI" else 2
    
#     slot_found = False
#     new_lines = []
    
#     for line in lines:
#         stripped = line.strip()
        
#         if stripped.startswith("#") or not stripped:
#             new_lines.append(line)
#             continue
        
#         parts = stripped.split()
#         if len(parts) >= 5:
#             current_slot = int(parts[0])
            
#             if current_slot == devids_slot_no:
#                 new_lines.append(f"{parts[0]} {parts[1]} {parts[2]} {parts[3]} {type_flag}\n")
#                 slot_found = True
#             else:
#                 new_lines.append(line)
#         else:
#             new_lines.append(line)
    
#     if not slot_found:
#         dev_path = "/dev/ttySC1"
#         module_id = f"0x{devids_slot_no:02X}"
#         gpino = f"P{devids_slot_no}_1"
#         new_lines.append(f"{devids_slot_no} {dev_path} {module_id} {gpino} {type_flag}\n")
    
#     with open(DEVIDS_CONF_PATH, "w") as f:
#         f.writelines(new_lines)


# def parse_version_conf():
#     if not os.path.exists(VERSION_CONF_PATH):
#         return {}

#     version_data = {}
#     with open(VERSION_CONF_PATH, "r") as f:
#         for line in f:
#             line = line.strip()
#             if line.startswith("#") or not line:
#                 continue
#             parts = line.split()
#             if len(parts) >= 4:
#                 slot_no = int(parts[0])
#                 serial_number = parts[1] if parts[1] != "0" else None
#                 hardware_version = parts[2] if parts[2] != "0" else None
#                 software_version = parts[3] if parts[3] != "0" else None
                
#                 if serial_number:
#                     version_data[slot_no] = {
#                         "serial_number": serial_number,
#                         "hardware_version": hardware_version,
#                         "software_version": software_version
#                     }
#     return version_data


# def update_version_conf(slot_number, serial_number=None, hardware_version=None, software_version=None):
#     if not os.path.exists(VERSION_CONF_PATH):
#         with open(VERSION_CONF_PATH, "w") as f:
#             f.write("#DI_module_count=0\n")
#             f.write("#DO_module_count=0\n")
    
#     lines = []
#     slot_updated = False
    
#     with open(VERSION_CONF_PATH, "r") as f:
#         lines = f.readlines()
    
#     devids_slot_no = slot_number - 3
    
#     new_lines = []
#     for line in lines:
#         stripped = line.strip()
        
#         if stripped.startswith("#") or not stripped:
#             new_lines.append(line)
#             continue
        
#         parts = stripped.split()
#         if len(parts) >= 4:
#             current_slot = int(parts[0])
            
#             if current_slot == devids_slot_no:
#                 current_serial = parts[1]
#                 current_hw = parts[2]
#                 current_sw = parts[3]
                
#                 new_serial = serial_number if serial_number is not None else current_serial
#                 new_hw = hardware_version if hardware_version is not None else current_hw
#                 new_sw = software_version if software_version is not None else current_sw
                
#                 new_lines.append(f"{devids_slot_no} {new_serial} {new_hw} {new_sw}\n")
#                 slot_updated = True
#             else:
#                 new_lines.append(line)
#         else:
#             new_lines.append(line)
    
#     if not slot_updated and slot_number > 3:
#         new_serial = serial_number if serial_number else "0"
#         new_hw = hardware_version if hardware_version else "0"
#         new_sw = software_version if software_version else "0"
#         new_lines.append(f"{devids_slot_no} {new_serial} {new_hw} {new_sw}\n")
    
#     with open(VERSION_CONF_PATH, "w") as f:
#         f.writelines(new_lines)

from src.utils.frtu_client import frtu_client

def parse_devids_conf():
    """Fetch devids.conf from FRTU device"""
    return frtu_client.parse_devids_conf()

def update_devids_conf(slot_number, module_type):
    """Update devids.conf on FRTU device"""
    return frtu_client.update_devids_conf(slot_number, module_type)

def parse_version_conf():
    """Fetch version.conf from FRTU device"""
    return frtu_client.parse_version_conf()

def update_version_conf(slot_number, serial_number=None, hardware_version=None, software_version=None):
    """Update version.conf on FRTU device"""
    return frtu_client.update_version_conf(slot_number, serial_number, hardware_version, software_version)

