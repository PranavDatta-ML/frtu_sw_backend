from fastapi import HTTPException

SP = "Single Point Parameter"
DP = "Double Point Parameter"

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

def normalize_dp_associations(channels: dict) -> None:
    for ch in channels.values():
        if ch.get("channelType") != DP:
            continue

        assoc = _get_assoc(ch)
        if not assoc:
            continue

        peer = channels.get(f"channel_{assoc}")
        if not peer:
            raise HTTPException(400, f"Associated channel {assoc} not found")

        if peer.get("channelType") != DP:
            raise HTTPException(400, f"Channel {assoc} is not a Double Point channel")

        ch_no = _get_ch_no(ch)
        peer["associateChannelNo"] = ch_no


def validate_slot_for_di(slot_number: int):
    if slot_number < 4:
        raise HTTPException(400, "DI module is allowed only from slot 4 onwards")


def validate_di_channels(channels: dict) -> None:
    paired = {}

    for ch in channels.values():
        ch_no = _get_ch_no(ch)
        ch_type = ch.get("channelType")
        assoc_no = _get_assoc(ch)

        if ch_type == SP:
            if assoc_no:
                raise HTTPException(400, f"Single Point channel {ch_no} cannot have associateChannelNo")
            continue

        if ch_type != DP:
            raise HTTPException(400, f"Invalid channelType for channel {ch_no}")

        if not assoc_no:
            continue

        assoc = channels.get(f"channel_{assoc_no}")
        if not assoc:
            continue

        if assoc.get("channelType") != DP:
            raise HTTPException(400, "Double Point channels can associate only with Double Point channels")

        if not ch.get("status") or not assoc.get("status"):
            raise HTTPException(400, "Both Double Point channels must be enabled")

        if ch.get("timestampEnable") != assoc.get("timestampEnable"):
            raise HTTPException(400, "Both Double Point channels must have same timestampEnable")

        if ch.get("normalState") == assoc.get("normalState"):
            raise HTTPException(400, "Associated Double Point channels must have opposite normalState")

        existing = paired.get(ch_no)
        if existing and existing != assoc_no:
            raise HTTPException(400, f"Channel {ch_no} already paired with channel {existing}")

        paired[ch_no] = assoc_no
        paired[assoc_no] = ch_no

def validate_di_channels_strict(channels: dict) -> None:
    used_names = {}
    dp_pairs = {}

    for ch in channels.values():
        ch_no = _get_ch_no(ch)
        name = (ch.get("name") or "").strip()
        ch_type = ch.get("channelType")
        assoc = _get_assoc(ch)

        if name:
            if name in used_names and used_names[name] != ch_no:
                raise HTTPException(400, f"Channel name '{name}' already used by channel {used_names[name]}")
            used_names[name] = ch_no

        if ch_type == DP and assoc:
            if assoc == ch_no:
                raise HTTPException(400, "Channel cannot associate with itself")

            if ch_no in dp_pairs and dp_pairs[ch_no] != assoc:
                raise HTTPException(400, f"DP channel {ch_no} already associated with {dp_pairs[ch_no]}")

            if assoc in dp_pairs and dp_pairs[assoc] != ch_no:
                raise HTTPException(400, f"DP channel {assoc} already associated with {dp_pairs[assoc]}")

            dp_pairs[ch_no] = assoc
            dp_pairs[assoc] = ch_no

        