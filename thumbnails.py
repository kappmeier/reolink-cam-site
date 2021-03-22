"""Dealing with camera thumbnails.

"""
from os import makedirs, path
from PIL import Image

from cam_file import build_path, build_file_name
from cam_site_builder import PictureData, CamData

THUMBNAIL_DIRECTORY = "thumbnails"
"""Directory for thumbnails under web root."""


def create_thumbnail(root: str, web_root: str, cam_name: str, picture: PictureData, skip_existing: bool):
    """Creates a thumbnail for a cam picture and returns the path.

    :param root: the root of the camera
    :param web_root: the root directory of the web output
    :param cam_name: the camera name, used to derive the image name
    :param picture: the picture data for which a thumbnail is created
    :param skip_existing: skip existing to speed up process
    :return: the relative path to the thumbnail in the web root
    """
    thumbnail_file = build_file_name(cam_name, picture)
    thumbnail_root = path.join(web_root, THUMBNAIL_DIRECTORY, path.basename(root))
    target_file = path.join(build_path(thumbnail_root, picture), thumbnail_file + ".jpg")

    if skip_existing and path.exists(target_file):
        return

    source_file = path.join(build_path(root, picture), thumbnail_file + ".jpg")

    image = Image.open(source_file)
    image.thumbnail((256, 256))
    try:
        image.save(target_file)
    except FileNotFoundError:
        makedirs(path.dirname(target_file))
        image.save(target_file)


def create_thumbnails(root: str, cam_data: CamData, web_root: str, skip_existing: bool = True):
    """Creates all thumbnails for pictures

    :param root: the root of the camera
    :param cam_data:
    :param web_root: the root directory of the web output
    :param skip_existing: skip existing to speed up process
    :return:
    """
    for pictures in cam_data.contents:
        create_thumbnail(root, web_root, cam_data.name, pictures, skip_existing)
