from enum import Enum


class FrtuDeviceType(str, Enum):
    FRTU = 'FRTU'
    RTU = 'RTU'


class FRTUDeviceCardType(str, Enum):
    POWER_SUPPLY = "Power Supply"
    MASTER_PROCESSOR = "Master Processor"
    COMMUNICATION_MODULE = "Communication Module"
    DI_16_DIGITAL_INPUT = "DI-16 Digital Input"
    DO_10_DIGITAL_OUTPUT = "DO-10 Digital Output"
    AI_10_ANALOG_INPUT = "AI-10 Analog Input"
    AO_8_ANALOG_OUTPUT = "AO-8 Analog Output"