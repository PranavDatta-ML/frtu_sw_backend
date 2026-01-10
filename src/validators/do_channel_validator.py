from fastapi import HTTPException

from src.schemas.frtu_do_module_info import DOChannel

SP = "Single Point Parameter"
DP = "Double Point Parameter"

MAX_DO_CHANNELS = 10


def enforce_do_rules(channels: dict) -> None:
    used_names = {}
    dp_pairs = {}

    for ch in channels.values():
        ch_no = ch.get("channelNo")
        ch_type = ch.get("channelType")
        assoc = ch.get("associateChannelNo")

        name = (ch.get("name") or "").strip().lower()
        if not name:
            raise HTTPException(
                400,
                f"Channel name is required for channel {ch_no}"
            )

        if name in used_names and used_names[name] != ch_no:
            raise HTTPException(
                400,
                f"Duplicate DO channel name '{ch.get('name')}'"
            )
        used_names[name] = ch_no

        # ---------- SP ----------
        if ch_type == "Single Point Parameter":
            if assoc not in (None, "",):
                raise HTTPException(
                    400,
                    f"Single Point DO channel {ch_no} cannot have associateChannelNo"
                )
            continue

        # ---------- DP ----------
        if ch_type != "Double Point Parameter":
            raise HTTPException(
                400,
                f"Invalid DO channelType '{ch_type}' for channel {ch_no}"
            )

        if not assoc:
            continue

        assoc = str(assoc)

        if assoc == ch_no:
            raise HTTPException(400, "Channel cannot associate with itself")

        peer = channels.get(f"channel_{assoc}")
        if not peer:
            continue

        if peer.get("channelType") != "Double Point Parameter":
            raise HTTPException(
                400,
                "Double Point DO channels can associate only with Double Point channels"
            )

        # ---------- STRICT SAME-PAIR CHECK ----------
        if ch_no in dp_pairs and dp_pairs[ch_no] != assoc:
            raise HTTPException(
                400,
                f"Channel {ch_no} already paired with {dp_pairs[ch_no]}"
            )

        if assoc in dp_pairs and dp_pairs[assoc] != ch_no:
            raise HTTPException(
                400,
                f"Channel {assoc} already paired with {dp_pairs[assoc]}"
            )

        # ---------- PARAMETER CONSISTENCY ----------
        if ch.get("pulseType") != peer.get("pulseType"):
            raise HTTPException(400, "DP channels must have same pulseType")

        if ch.get("sboFlag") != peer.get("sboFlag"):
            raise HTTPException(400, "DP channels must have same sboFlag")

        if ch.get("status") != peer.get("status"):
            raise HTTPException(400, "DP channels must have same status")

        if ch.get("ioActivationMode") != peer.get("ioActivationMode"):
            raise HTTPException(400, "DP channels must have same ioActivationMode")

        if ch.get("normalState") == peer.get("normalState"):
            raise HTTPException(
                400,
                "Associated Double Point DO channels must have opposite normalState"
            )

        dp_pairs[ch_no] = assoc
        dp_pairs[assoc] = ch_no


def normalize_do_dp_associations(channels: dict) -> None:
    for ch in channels.values():
        if ch.get("channelType") != DP:
            continue

        assoc = ch.get("associateChannelNo")
        if not assoc:
            continue

        assoc = str(assoc)
        peer = channels.get(f"channel_{assoc}")

        if not peer:
            continue

        if peer.get("channelType") != DP:
            raise HTTPException(
                400,
                f"Channel {assoc} is not a Double Point channel"
            )

        peer["associateChannelNo"] = ch["channelNo"]
        

def validate_do_channels(channels: dict):
    used_names = set()
    dp_pairs = {}

    for ch in channels.values():
        name = ch["name"]
        if name in used_names:
            raise HTTPException(400, f"Duplicate channel name: {name}")
        used_names.add(name)

        if ch["commandType"] == "1":  # DOUBLE
            assoc = ch.get("associateChannelNo")
            if not assoc:
                raise HTTPException(
                    400,
                    f"associateChannelNo required for double command channel {ch['channelNo']}"
                )
            dp_pairs[ch["channelNo"]] = assoc

    for a, b in dp_pairs.items():
        if dp_pairs.get(b) != a:
            raise HTTPException(
                400,
                f"Double channels {a} and {b} must associate with each other"
            )

def normalize_do_channel(ch) -> dict:
    if isinstance(ch, dict):
        ch_no = str(int(ch["channelNoPrimary"]))
        return {
            **ch,
            "associateChannelNo": ch.get("associateChannelNo"),
            "channelNo": ch_no,
        }

    ch_no = str(int(ch.channelNoPrimary))
    data = ch.model_dump(exclude={"associateChannelNo"})
    data["associateChannelNo"] = ch.associateChannelNo
    data["channelNo"] = ch_no
    return data


