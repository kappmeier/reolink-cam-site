"""Some static data types for cam site handling.

Copyright © 2022 Jan-Philipp Kappmeier

Licensed under the Apache License, Version 2.0 (the "License"); you may not use this file except
in compliance with the License. You may obtain a copy of the License at

       http://www.apache.org/licenses/LICENSE-2.0
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
