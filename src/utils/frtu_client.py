from typing import Optional, Dict, Any, List
import logging
import requests # type: ignore

logger = logging.getLogger(__name__)

class FRTUClient:
    def __init__(self, frtu_ip: str = "10.150.2.235", frtu_port: int = 8000, timeout: int = 10):
        self.base_url = f"http://{frtu_ip}:{frtu_port}"
        self.timeout = timeout
        self.frtu_ip = frtu_ip
        self.frtu_port = frtu_port
    
    def health_check(self) -> bool:
        try:
            response = requests.get(f"{self.base_url}/health", timeout=5)
            return response.status_code == 200
        except:
            return False
    
    def parse_devids_conf(self) -> List[Dict[str, Any]]:
        try:
            response = requests.get(f"{self.base_url}/api/config/devids", timeout=self.timeout)
            response.raise_for_status()
            result = response.json()
            
            if result.get("status") == "success":
                return result.get("data", [])
            else:
                raise Exception(result.get("message", "Failed to fetch devids.conf"))
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to fetch devids.conf from FRTU: {str(e)}")
            raise FileNotFoundError(f"devids.conf not found at FRTU device {self.frtu_ip}")
    
    def update_devids_conf(self, slot_number: int, module_type: str) -> bool:
        try:
            payload = {
                "slot_number": slot_number,
                "module_type": module_type
            }
            response = requests.post(
                f"{self.base_url}/api/config/devids/update", 
                json=payload, 
                timeout=self.timeout
            )
            response.raise_for_status()
            result = response.json()
            
            if result.get("status") == "success":
                return True
            else:
                raise Exception(result.get("message", "Update failed"))
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to update devids.conf on FRTU: {str(e)}")
            raise Exception(f"Failed to update devids.conf: {str(e)}")
    
    def remove_devids_slot(self, slot_number: int) -> bool:
        response = requests.post(
            f"{self.base_url}/api/config/devids/remove",
            json={"slot_number": slot_number},
            timeout=self.timeout,
        )
        response.raise_for_status()
        return True

    def parse_version_conf(self) -> Dict[int, Dict[str, str]]:
        try:
            response = requests.get(f"{self.base_url}/api/config/version", timeout=self.timeout)
            response.raise_for_status()
            result = response.json()
            
            if result.get("status") == "success":
                return result.get("data", {})
            else:
                return {}
        except:
            return {}
    
    def update_version_conf(self, slot_number: int, serial_number: str = None, 
                           hardware_version: str = None, software_version: str = None) -> bool:
        try:
            payload = {
                "slot_number": slot_number,
                "serial_number": serial_number,
                "hardware_version": hardware_version,
                "software_version": software_version
            }
            response = requests.post(
                f"{self.base_url}/api/config/version/update", 
                json=payload, 
                timeout=self.timeout
            )
            response.raise_for_status()
            result = response.json()
            
            if result.get("status") == "success":
                return True
            else:
                raise Exception(result.get("message", "Update failed"))
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to update version.conf on FRTU: {str(e)}")
            raise Exception(f"Failed to update version.conf: {str(e)}")
    
    def update_ini_file(self, module_type: str, serial_channel: str, channel_key: str,
                       ioa: str, ts: str = "0", is_configure: str = "1",
                       serialport: str = None, deviceid: str = None, 
                       devicetype: str = None) -> bool:
        try:
            payload = {
                "module_type": module_type,
                "serial_channel": serial_channel,
                "channel_key": channel_key,
                "ioa": ioa,
                "ts": ts,
                "is_configure": is_configure,
                "serialport": serialport,
                "deviceid": deviceid,
                "devicetype": devicetype
            }
            response = requests.post(
                f"{self.base_url}/api/config/ini/update", 
                json=payload, 
                timeout=self.timeout
            )
            if response.status_code >= 400:
                try:
                    body = response.json()
                except Exception:
                    body = response.text
                raise Exception(f"INI update failed ({response.status_code}): {body}")
            # response.raise_for_status()
            result = response.json()
            
            if result.get("status") == "success":
                return True
            else:
                raise Exception(result.get("message", "Update failed"))
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to update {module_type} INI file on FRTU: {str(e)}")
            raise Exception(f"Failed to update {module_type} INI file: {str(e)}")
    

    # def update_di_module_ini(
    #     self,
    #     serial_channel: str,
    #     channel_key: str,
    #     ioa: str,
    #     ):
    #     payload = {
    #         "serial_channel": serial_channel,
    #         "channel_key": channel_key,
    #         "ioa": ioa,
    #     }

    #     response = requests.post(
    #         f"{self.base_url}/api/config/ini/update-di",
    #         json=payload,
    #         timeout=5,
    #     )

    #     response.raise_for_status()
    #     return response.json()
        
    def update_do_module_ini(
        self,
        serial_channel: str,
        channel_key: str,
        value: str,
        ):
        payload = {
            "serial_channel": serial_channel,
            "channel_key": channel_key,
            "value": value,
        }

        response = requests.post(
            f"{self.base_url}/api/config/ini/update-do",
            json=payload,
            timeout=self.timeout,
        )
        response.raise_for_status()
        return True
    
    def update_mb_config(self, payload: dict) -> bool:
        try:
            response = requests.post(
                f"{self.base_url}/api/config/modbus/update",
                # json=payload,
                json={"slot_number": 3, "modbus_data": payload},
                timeout=self.timeout
            )
            response.raise_for_status()
            result = response.json()
            return result.get("status") == "success"
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to update mb_config.ini: {str(e)}")
            raise Exception(f"FRTU mb_config update failed: {str(e)}")
    
    # def update_mb_config(frtu_ip: str, payload: dict):
    #     url = f"http://{frtu_ip}:8000/api/config/modbus/update"

    #     response = requests.post(url, json=payload, timeout=10)
    #     response.raise_for_status()

    #     return response.json()

# Initialize global FRTU client
frtu_client = FRTUClient(frtu_ip="10.150.2.235", frtu_port=8000)
# frtu_client = FRTUClient(frtu_ip="127.0.0.1", frtu_port=8000)