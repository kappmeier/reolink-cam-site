"""Main file to create a static cam site page.

Usage:
  create_cam_site
"""
from os import path
from typing import Sequence

from cam_file import load_cam_data, IMAGES_DIRECTORY
from cam_site_builder import CamSiteBuilder


def create_cam_site(project_name: str, web_root: str, cameras: Sequence[str]):
    """

    :return:
    """
    image_root = path.join(web_root, IMAGES_DIRECTORY)
    cam_data = load_cam_data(image_root, cameras)

    print("Creating website for {} cameras".format(len(cam_data)))

    # Relativize outputs
    cam_data = {path.relpath(key, image_root): value for key, value in cam_data.items()}

    builder = CamSiteBuilder(project_name, web_root, cam_data)

    builder.create_main_site()
