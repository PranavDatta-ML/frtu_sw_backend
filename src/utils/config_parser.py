
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

