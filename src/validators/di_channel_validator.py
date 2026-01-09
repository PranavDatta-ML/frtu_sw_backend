from fastapi import HTTPException
from typing import Dict, Any

SP = "Single Point Parameter"
DP = "Double Point Parameter"

def normalize_dp_associations(channels: dict) -> None:
    for ch in channels.values():
        if ch["channelType"] != DP:
            continue

        assoc = ch.get("associate_channel_no")
        if not assoc:
            continue

        peer = channels.get(f"channel_{assoc}")
        if not peer:
            raise HTTPException(
                400,
                f"Associated channel {assoc} not found"
            )

        if peer.get("channelType") != DP:
            raise HTTPException(
                400,
                f"Channel {assoc} is not a Double Point channel"
            )

        peer["associate_channel_no"] = ch["channel_no"]


def validate_di_channels_strict(channels: dict) -> None:
    used_names = {}
    dp_pairs = {}

    for ch in channels.values():
        ch_no = ch["channel_no"]
        name = ch.get("name")
        ch_type = ch.get("channelType")
        assoc = ch.get("associate_channel_no")

        if name:
            if name in used_names and used_names[name] != ch_no:
                raise HTTPException(
                    400,
                    f"Channel name '{name}' already used by channel {used_names[name]}"
                )
            used_names[name] = ch_no

        if ch_type == DP:
            if assoc:
                if assoc == ch_no:
                    raise HTTPException(400, "Channel cannot associate with itself")

                if ch_no in dp_pairs and dp_pairs[ch_no] != assoc:
                    raise HTTPException(
                        400,
                        f"DP channel {ch_no} already associated with {dp_pairs[ch_no]}"
                    )

                if assoc in dp_pairs and dp_pairs[assoc] != ch_no:
                    raise HTTPException(
                        400,
                        f"DP channel {assoc} already associated with {dp_pairs[assoc]}"
                    )

                dp_pairs[ch_no] = assoc
                dp_pairs[assoc] = ch_no

def validate_di_channels(channels):
    paired = {}

    for ch in channels.values():
        ch_no = str(ch.get("channel_no"))
        ch_type = ch.get("channelType")
        assoc_no = ch.get("associate_channel_no")

        # if ch_type == SP:
        #     if assoc_no is not None:
        #         raise HTTPException(
        #             400,
        #             f"Single Point channel {ch_no} cannot have associateChannelNo",
        #         )
        #     continue
        if ch_type == SP:
            if assoc_no and str(assoc_no).strip():
                raise HTTPException(
                    400,
                    f"Single Point channel {ch_no} cannot have associateChannelNo",
                )
            continue

        if ch_type != DP:
            raise HTTPException(
                400,
                f"Invalid channelType for channel {ch_no}",
            )

        if assoc_no is None:
            continue

        assoc_no = str(assoc_no)
        assoc = channels.get(f"channel_{assoc_no}")

        if not assoc:
            continue

        if assoc.get("channelType") != DP:
            raise HTTPException(
                400,
                "Double Point channels can associate only with Double Point channels",
            )

        if not ch.get("status") or not assoc.get("status"):
            raise HTTPException(
                400,
                "Both Double Point channels must be enabled",
            )

        if ch.get("normalState") == assoc.get("normalState"):
            raise HTTPException(
                400,
                "Associated Double Point channels must have opposite normalState",
            )

        existing = paired.get(ch_no)
        if existing and existing != assoc_no:
            raise HTTPException(
                400,
                f"Channel {ch_no} already paired with channel {existing}",
            )

        paired[ch_no] = assoc_no
        paired[assoc_no] = ch_no


        