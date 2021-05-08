"""Main file to create a static cam site page.

Usage:
  create_cam_site
"""
from os import path
from typing import Sequence

from cam_file import load_cam_data, create_symlinks, IMAGES_DIRECTORY
from thumbnails import create_thumbnails


def prepare_cam_site(root: str, cameras: Sequence[str], web_root: str):
    """Links image data into

    :param root:
    :param cameras:
    :param web_root:
    :return:
    """
    cam_datas = load_cam_data(root, cameras)

    print("Preparing website for {} cameras".format(len(cam_datas)))

    print("Loaded {} images".format({key: len(value.contents) for key, value in cam_datas.items()}))

    for root, cam_data in cam_datas.items():
        updated_files = create_symlinks(root, cam_data, web_root)

        # The updated files should contain no duplicates any more and are located in the web root
        root_directory = path.join(web_root, IMAGES_DIRECTORY, path.basename(root))
        create_thumbnails(root_directory, updated_files, web_root)
