from enum import Enum


class FrtuDeviceType(str, Enum):
    TYPE_A = 'FRTU'
    TYPE_B = 'RTU'
