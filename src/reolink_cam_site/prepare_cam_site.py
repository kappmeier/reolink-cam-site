"""Main file to create a static cam site page.

The script traverses the camera directories in a given root directory and
creates links and thumbnails in the web root. The latter directory is used as
input for the create_cam_site.py script.

Usage:
  prepare_cam_site.py --root "/data/camera-storage" --web-root ./out --cameras camera-front camera-back

Copyright © 2022 Jan-Philipp Kappmeier

Licensed under the Apache License, Version 2.0 (the "License"); you may not use this file except
in compliance with the License. You may obtain a copy of the License at

       http://www.apache.org/licenses/LICENSE-2.0
"""
from datetime import date
from os import path
from typing import List, Optional

from tap import Tap

from reolink_cam_site.cam_file import load_cam_data, create_symlinks, IMAGES_DIRECTORY
from reolink_cam_site.thumbnails import create_thumbnails


class PrepareCamArguments(Tap):
    root: str  # Root directory of cam data
    """The root directory containing sub directories for each camera. The
    camera directories contain data in ReoLink software format.
    """
    web_root: str  # Output directory
    """The directory that will be used as output and expected to be the web
    root of the final cam site. This will contain the `images` and
    `thumbnails` directories after execution. The directory is supposed to be
    the input for the creation script.
    """
    cameras: List[str]  # Cameras in the cam site.
    """The cameras are expected to be directories in the root directory. They
    contain the content produced by ReoLink software (in year/month/day sub
    folders). They are read and used to process the images and thumbnails.
    """
    date: Optional[date]  # Load images for a certain date.
    """The date is specified in ISO format `YYYY-MM-DD`.
    """

    def __init__(self, *args):
        super().__init__(args, underscores_to_dashes=True)

    def configure(self):
        """Define complex parameters."""
        self.add_argument('--date', required=False, type=date.fromisoformat)


def _get_arguments() -> PrepareCamArguments:
    parser = PrepareCamArguments()
    parsed_args = parser.parse_args()
    return parsed_args


def prepare_cam_site(configuration: PrepareCamArguments):
    """Links image data into

    :param configuration: the parameters required to run the preparation
    """
    cam_datasets = load_cam_data(configuration.root, configuration.cameras, configuration.date)

    print("Preparing website for {} cameras".format(len(cam_datasets)))

    print("Loaded {} images".format({key: len(value.contents) for key, value in cam_datasets.items()}))

    for root, cam_data in cam_datasets.items():
        updated_files = create_symlinks(root, cam_data, configuration.web_root)

        # The updated files should contain no duplicates any more and are located in the web root
        root_directory = path.join(configuration.web_root, IMAGES_DIRECTORY, path.basename(root))
        create_thumbnails(root_directory, updated_files, configuration.web_root)


def main():
    """Executes the prepare_cam_site script with command line arguments.
    """
    args = _get_arguments()
    prepare_cam_site(args)


if __name__ == '__main__':
    main()
