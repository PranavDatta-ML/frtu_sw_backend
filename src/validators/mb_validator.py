from typing import Iterable
from fastapi import HTTPException

def validate_modbus_slot(slot_number: str | None):
    if slot_number and slot_number != "3":
        raise HTTPException(400, "Modbus module is allowed only in slot 3")

def validate_protocol(protocol: str):
    if protocol not in ("Modbus RTU", "Modbus TCP"):
        raise HTTPException(400, "Invalid Modbus protocol")

def validate_max_channels(max_channels: str, channels_len: int):
    if int(max_channels) < channels_len:
        raise HTTPException(
            400,
            f"Configured channels ({channels_len}) exceed maxChannels ({max_channels})"
        )


def _validate_unique(names: Iterable[str], level: str):
    seen = set()
    for name in names:
        if name in seen:
            raise HTTPException(
                400,
                f"Duplicate {level} name detected: {name}"
            )
        seen.add(name)


def validate_channels_slaves_params(channels):
    channel_names = []

    for ch in channels:
        ch_cfg = ch.channelConfig
        channel_names.append(ch_cfg.channelName)

        max_slaves = int(ch_cfg.maxSlaves)
        slaves = ch_cfg.modbusSlaves

        if len(slaves) > max_slaves:
            raise HTTPException(
                400,
                f"Slaves ({len(slaves)}) exceed maxSlaves ({max_slaves}) "
                f"for channel {ch_cfg.channelName}"
            )

        slave_names = []

        for sl in slaves:
            sl_cfg = sl.slaveConfig
            slave_names.append(sl_cfg.name)

            max_params = int(sl_cfg.maxParameters)
            params = sl_cfg.modbusParameters

            if len(params) > max_params:
                raise HTTPException(
                    400,
                    f"Parameters ({len(params)}) exceed maxParameters ({max_params}) "
                    f"for slave {sl_cfg.name}"
                )

            param_names = [
                p.parameterConfig.parameterName for p in params
            ]
            _validate_unique(param_names, "parameter")

        _validate_unique(slave_names, "slave")

    _validate_unique(channel_names, "channel")