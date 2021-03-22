"""Utility methods for cam file handling.

Parsing directory structure from Reolink, extracting time stamps, file types
and creating web-site relevant data.
"""
from collections import defaultdict
from datetime import datetime
from itertools import chain
from os import makedirs, path, sep, symlink, walk
from re import compile
from typing import Sequence, Tuple, Optional, Dict, List

from cam_site_builder import CamData, PictureData

FOLDER_DEPTH_YEAR = 1
FOLDER_DEPTH_MONTH = 2
FOLDER_DEPTH = 3


def split(filename: str, year: str, month: str, day: str) -> Optional[Tuple[str, str, str]]:
    """Splits a filename as created by Reolink into its parts.

    >>> split("Camera BE_01_20210315004528.jpg", "2021", "03", "15")
    ('Camera BE_01', '20210315004528', 'jpg')

    :param filename: the complete filename
    :param year: year of the file
    :param month: month of the file
    :param day: day of the file
    :return: a tuple of the camera name, the timestamp, and the type suffix
    """
    pattern = "(.*)_({0}{1}{2}[0-9]{{6}}).(jpg|mp4)".format(year, month, day)
    regex = compile(pattern)
    match = regex.match(filename)

    if match is not None and len(match.groups()) == 3:
        return match.groups()[0], match.groups()[1], match.groups()[2]
    return None


def _as_datetime(time_code: str) -> datetime:
    """Parses a Reolink file time code into a datetime.

    >>> _as_datetime("20210313162209")
    datetime.datetime(2021, 3, 13, 16, 22, 9)

    :param time_code: the time code
    :return: the converted datetime
    """
    return datetime.strptime(time_code, '%Y%m%d%H%M%S')


def extract_by_type(files: Sequence[str], year: str, month: str, day: str) -> CamData:
    """Converts a file list into camera data.

    The output is converted to chunks with the same time code, provided with a
    list of type suffices.

    >>> test_files = ["Cam_20210313090000.jpg", "Cam_20210313090000.mp4",\
                      "Cam_20210313090523.jpg",\
                      "Cam_20210313090524.mp4"]
    >>> result = extract_by_type(test_files, "2021", "03", "13")
    >>> result.name
    'Cam'
    >>> result.contents[0]
    PictureData(time=datetime.datetime(2021, 3, 13, 9, 0), types=['jpg', 'mp4'])
    >>> result.contents[1]
    PictureData(time=datetime.datetime(2021, 3, 13, 9, 5, 23), types=['jpg'])
    >>> result.contents[2]
    PictureData(time=datetime.datetime(2021, 3, 13, 9, 5, 24), types=['mp4'])

    Input files that are on a different date are ignored.

    >>> test_files = ["Cam_20210313090000.jpg", "Cam_20210314090000.mp4"]
    >>> extract_by_type(test_files, "2021", "03", "13")
    CamData(name='Cam', contents=[PictureData(time=datetime.datetime(2021, 3, 13, 9, 0), types=['jpg'])])

    :param files: the list of files
    :param day: the date for which pictures are collected
    :param month: the month for which pictures are collected
    :param year: the year for which pictures are collected
    :return: a compiled `CamData` object with a list of all files
    """
    valid = [x for x in [split(filename, year, month, day) for filename in files] if x is not None]

    prefix = set([element[0] for element in valid])

    if len(prefix) != 1:
        raise ValueError("Illegal files found, more than one Prefix: {}".format(prefix))

    # Reduce to timestamp and suffix
    as_tuple = [(_as_datetime(element[1]), element[2]) for element in valid]

    as_dict = defaultdict(list)
    for entry in as_tuple:
        as_dict[entry[0]].append(entry[1])

    return CamData(next(iter(prefix)), [PictureData(time, types) for time, types in sorted(as_dict.items())])


def collect_images(camera_path: str) -> CamData:
    """Collects all picture in a given path.

    The files are collected in subdirectories `camera_path/year/month/day` and
    assembled together into a `CamData` object.

    It is assumed that all files have the same camera name as prefix, otherwise
    an `Exception` will be raised.

    :param camera_path: the root path for pictures
    :return: the constructed object holding all pictures
    """
    print("Iterating {}".format(camera_path))

    separator_count = camera_path.count(sep)

    result_name = None
    result_list = []

    year = None
    month = None

    for directory in walk(camera_path):
        print("Found: {}".format(directory))
        if directory[0].count(sep) == separator_count + FOLDER_DEPTH_YEAR:
            year = path.basename(path.normpath(directory[0]))
        if directory[0].count(sep) == separator_count + FOLDER_DEPTH_MONTH:
            month = path.basename(path.normpath(directory[0]))
        if directory[0].count(sep) == separator_count + FOLDER_DEPTH:
            print("Iterating files in {}".format(directory[0]))
            day = path.basename(path.normpath(directory[0]))
            cam_data = extract_by_type(directory[2], year, month, day)
            if result_name is None:
                result_name = cam_data.name
            elif result_name != cam_data.name:
                raise Exception("Invalid files found with prefixes {} and {}".format(result_name, cam_data.name))
            result_list.extend(cam_data.contents)
    return CamData(result_name, result_list)


def load_cam_data(root: str, cameras: Sequence[str]) -> Dict[str, CamData]:
    """Loads all pictures for multiple cameras in a root directory.

    Each camera data is expected to reside in its own directory with structure
    `root/camera_root/year/month/day/pictures.{jpg,mp4}`.

    :return: dictionary of paths to compiled `CamData` objects
    """

    def load_camera_with_logging(camera: str) -> CamData:
        images = collect_images(path.join(root, camera))
        print("Found {} images".format(len(images[1])))
        print(images)
        return images

    cam_data = {path.join(root, camera): load_camera_with_logging(camera) for camera in cameras}
    return cam_data


def _add_if_proximate(candidate: PictureData, image: PictureData, result: List[List[PictureData]]) -> int:
    """Function with side effect adding an element to a list.

    >>> picture_list = []
    >>> picture1 = PictureData(datetime(2021, 3, 13, 0, 0, 10), ["jpg"])
    >>> related = PictureData(datetime(2021, 3, 13, 0, 0, 11), ["mp4"])
    >>> _add_if_proximate(picture1, related, picture_list)
    0
    >>> picture_list
    [[PictureData(time=datetime.datetime(2021, 3, 13, 0, 0, 10), types=['jpg']), \
PictureData(time=datetime.datetime(2021, 3, 13, 0, 0, 11), types=['mp4'])]]

    :return: 1 if the two pictures were skipped, 0 if taken
    """
    difference = (image.time - candidate.time).total_seconds()
    if difference < 10:
        result.append([candidate, image])
        return 0
    else:
        print("Skipping pair with {} seconds difference".format(difference))
        return 1


def _combine_proximate(contents: Sequence[PictureData]) -> Sequence[Sequence[PictureData]]:
    """Combines pictures belonging together.

    Consecutive entries are tried to be combined if they belong to the same
    picture. This is the case if the timestamps differ only by a few seconds.

    The output contains lists. If the input entry already consisted of two
    files belonging to each other, they are included as a singleton element
    list in the output. Items that are combined in the process form a
    two-element list in the output.

    The sweep line algorithm expects that the inputs are sorted by timestamp.

    :param contents: list of picture data
    :return: list of entries belonging together
    """
    result = []
    print("Combine {} pictures".format(contents))
    candidate = None

    skip_count = 0

    for image in contents:
        if len(image.types) == 2:
            result.append([image])
            candidate = None
        else:
            if candidate is None:
                candidate = image
            else:
                skip_count += _add_if_proximate(candidate, image, result)
                candidate = None

    if skip_count > 0:
        print("Skipped {} images".format(skip_count))

    return result


def _build_path(root: str, picture: PictureData) -> str:
    """Returns the path to a picture

    >>> _build_path("root/dir", PictureData(datetime(2021, 3, 9, 16, 44, 20), []))
    'root/dir/2021/03/09'

    :param root: the output root directory
    :param picture: the picture file for which the path is constructed
    :return: the path to the file relative to the root dir
    """
    return path.join(root, picture.time.strftime('%Y'), picture.time.strftime('%m'), picture.time.strftime('%d'))


def _build_file_name(cam_name: str, picture: PictureData) -> str:
    """Builds the file name without suffix.

    >>> _build_file_name("Camera", PictureData(datetime(2021, 3, 9, 16, 44, 20), []))
    'Camera_20210309164420'

    :param cam_name: the name of the camera
    :param picture: the picture file for which the path is constructed
    :return: the filename for the corresponding file (without type suffix)
    """
    return cam_name + "_" + picture.time.strftime('%Y%m%d%H%M%S')


def create_symlink(root: str, web_root: str, cam_name: str, pictures: Sequence[PictureData]) -> PictureData:
    """

    Combines the possibly different file names.

    :param root:
    :param web_root: the root directory of the web output
    :param cam_name:
    :param pictures:
    :return:
    """
    symlink_defining_picture = pictures[0]

    symlinks_root = path.join("images", path.basename(root))
    symlinks_file_relative = _build_path(symlinks_root, symlink_defining_picture)
    symlinks_file_name = _build_file_name(cam_name, symlink_defining_picture)

    for picture in pictures:
        for file_type in picture.types:
            symlink_file = path.join(web_root, symlinks_file_relative, symlinks_file_name + "." + file_type)

            original_image_path = _build_path(root, picture)
            original_image_file_name = _build_file_name(cam_name, picture)
            original_image_symlink = path.join(original_image_path, original_image_file_name + "." + file_type)

            try:
                symlink(original_image_symlink, symlink_file)
            except FileNotFoundError:
                makedirs(path.dirname(symlink_file))
                symlink(original_image_symlink, symlink_file)
            except FileExistsError:
                # We ignore existing links
                pass

    combined_types = list(chain.from_iterable([picture.types for picture in pictures]))
    return PictureData(symlink_defining_picture.time, combined_types)


def create_symlinks(root: str, cam_data: CamData, web_root: str) -> CamData:
    """Creates symlinks for camera pictures

    Different timings are adjusted, i.e. input pictures consisting of jpg and
    mp4 file whose filename differs, will receive the same file name.

    :param root:
    :param cam_data:
    :param web_root:
    :return: updated camera data due to merging
    """
    # Get approximate files
    merged_images = _combine_proximate(cam_data.contents)

    updated_pictures = []
    for pictures in merged_images:
        print("Creating symlink for {}".format(pictures))
        updated_pictures.append(create_symlink(root, web_root, cam_data.name, pictures))
    return CamData(cam_data.name, updated_pictures)
