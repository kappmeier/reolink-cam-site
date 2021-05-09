"""Some static data types for cam site handling.

"""
from datetime import datetime
from typing import NamedTuple, Sequence, Optional


class PictureData(NamedTuple):
    """
    One snapshot.

    Including a datetime and a list of available types, typically `jpg` and `mp4`.
    """
    time: datetime
    """Timestamp of the snapshot."""
    types: Sequence[str]
    """The types of snapshot data available for the timestamp."""


class CamData(NamedTuple):
    """

    """
    name: Optional[str]
    """The camera name.

    `None` for invalid data.
    """
    contents: Sequence[PictureData]
    """List of sorted snapshots for the camera."""
