"""Main file to create a static cam site page.

The script expects a prepared directory with images and thumbnails as produced by the
create_cam_site.py script.

Usage:
  create_cam_site.py --name "My CamSite" --dir ./out --cameras camera-front camera-back
"""
from os import path
from typing import Sequence, List

from tap import Tap

from cam_file import load_cam_data, IMAGES_DIRECTORY
from cam_site_builder import CamSiteBuilder


class CreateCamArgumentParser(Tap):
    name: str  # Cam site name
    """The title of the cam site as used in the created website.
    """
    dir: str  # Output directory
    """The directory that will contain the created cam site. Also used as input
    directory for `images` and `thumbnails`. This is the same output directory
    used for the preparation script.
    """
    cameras: List[str]  # Cameras in the cam site.
    """The cameras are directory names in the `images` and `thumbnails`
    directories. They are the same as used as input for the preparation script.
    """


def _get_arguments() -> CreateCamArgumentParser:
    parser = CreateCamArgumentParser()
    parsed_args = parser.parse_args()
    return parsed_args


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


if __name__ == '__main__':
    args = _get_arguments()
    create_cam_site(args.name, args.dir, args.cameras)