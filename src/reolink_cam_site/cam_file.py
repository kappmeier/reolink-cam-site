"""Utility methods for cam file handling.

Parsing directory structure from Reolink, extracting time stamps, file types
and creating web-site relevant data.

Copyright © 2022 Jan-Philipp Kappmeier

Licensed under the Apache License, Version 2.0 (the "License"); you may not use this file except
in compliance with the License. You may obtain a copy of the License at

       http://www.apache.org/licenses/LICENSE-2.0
"""
from collections import defaultdict
from datetime import datetime, date
from itertools import chain
from os import makedirs, path, sep, symlink, walk
from re import compile
from typing import Dict, Iterator, List, Optional, Sequence, Tuple, Union

from reolink_cam_site.cam_site_data import CamData, PictureData

IMAGES_DIRECTORY = "images"
"""The image directory in the web root."""

_FOLDER_DEPTH_YEAR = 1
_FOLDER_DEPTH_MONTH = 2
_FOLDER_DEPTH = 3


def split(filename: str, for_date: date) -> Optional[Tuple[str, str, str]]:
    """Splits a filename as created by Reolink into its parts.

    >>> split("Camera BE_01_20210315004528.jpg", date(2021, 3, 15))
    ('Camera BE_01', '20210315004528', 'jpg')

    :param filename: the complete filename
    :param for_date: year, month, and day of the file
    :return: a tuple of the camera name, the timestamp, and the type suffix
    """
    pattern = "(.*)_({0:02d}{1:02d}{2:02d}[0-9]{{6}}).(jpg|mp4)".format(for_date.year, for_date.month, for_date.day)
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


def extract_by_type(files: Sequence[str], for_date: date) -> CamData:
    """Converts a file list into camera data.

    The output is converted to chunks with the same time code, provided with a
    list of type suffices.

    >>> test_files = ["Cam_20210313090000.jpg", "Cam_20210313090000.mp4", \
                      "Cam_20210313090523.jpg", \
                      "Cam_20210313090524.mp4"]
    >>> result = extract_by_type(test_files, date(2021, 3, 13))
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
    >>> extract_by_type(test_files, date(2021, 3, 13))
    CamData(name='Cam', contents=[PictureData(time=datetime.datetime(2021, 3, 13, 9, 0), types=['jpg'])])

    In case of empty or unrelated directories a special dummy cam data object is returned:

    >>> extract_by_type([], date(2021, 3, 13))
    CamData(name=None, contents=[])
    >>> extract_by_type(["some_other_data.txt"], date(2021, 3, 13))
    CamData(name=None, contents=[])

    :param files: the list of files
    :param for_date: the year, month, and day for which pictures are collected
    :return: a compiled `CamData` object with a list of all files
    """
    valid = [x for x in [split(filename, for_date) for filename in files] if x is not None]

    prefix = set([element[0] for element in valid])

    if len(prefix) > 1:
        raise ValueError("Illegal files found, more than one Prefix: {}".format(prefix))
    elif len(prefix) == 0:
        return CamData(None, [])

    # Reduce to timestamp and suffix
    as_tuple = [(_as_datetime(element[1]), element[2]) for element in valid]

    as_dict = defaultdict(list)
    for entry in as_tuple:
        as_dict[entry[0]].append(entry[1])

    return CamData(next(iter(prefix)), sorted([PictureData(time, types) for time, types in sorted(as_dict.items())]))


def _iterate_image_directories(camera_path: str) -> Iterator[Tuple[Sequence[str], date]]:
    """Iterates images in subdirectories per date.

    All subdirectories of the form `camera_path/year/month/day` are iterated.
    The yielded result contains all files in a directory together with its
    date.

    :param camera_path: the root path for pictures
    :return: the constructed object holding all pictures
    """
    print("Iterating {}".format(camera_path))

    separator_count = camera_path.count(sep)

    year = None
    month = None

    for directory in walk(camera_path):
        print("Found directory {} with {} files".format(directory[0], len(directory[2])))
        if directory[0].count(sep) == separator_count + _FOLDER_DEPTH_YEAR:
            year = int(path.basename(path.normpath(directory[0])))
        if directory[0].count(sep) == separator_count + _FOLDER_DEPTH_MONTH:
            month = int(path.basename(path.normpath(directory[0])))
        if directory[0].count(sep) == separator_count + _FOLDER_DEPTH:
            print("Iterating files in {}".format(directory[0]))
            day = int(path.basename(path.normpath(directory[0])))
            yield directory[2], date(year, month, day)


def _collect_images(image_groups: Iterator[Tuple[Sequence[str], date]]) -> CamData:
    """Converts groups of pictures into CamData object.

    The pictures are grouped by date and passed as an iterable. The date
    belonging to each group is used to derive the ReoLink path under which the
    images are located.

    >>> images_1 = ["Cam_20210508090000.jpg", "Cam_20210508090000.mp4"], date(2021, 5, 8)
    >>> images_2 = ["Cam_20210509090000.jpg", "Cam_20210509091010.jpg"], date(2021, 5, 9)
    >>> result = _collect_images([images_1, images_2])
    Collecting 2 images for 2021-05-08
    Collecting 2 images for 2021-05-09

    All file names that are passed must follow the REoLink pattern and the
    camera prefix must be the same for all iterated files, otherwise an
    exception is thrown.

    >>> result.name
    'Cam'

    The above example contains two files for 2021-05-08 for the same time of
    different type:

    >>> result.contents[0]
    PictureData(time=datetime.datetime(2021, 5, 8, 9, 0), types=['jpg', 'mp4'])

    The images for the second date (2021-05-09) are for different times:

    >>> result.contents[1]
    PictureData(time=datetime.datetime(2021, 5, 9, 9, 0), types=['jpg'])
    >>> result.contents[2]
    PictureData(time=datetime.datetime(2021, 5, 9, 9, 10, 10), types=['jpg'])

    :param image_groups: iterable collection of pictures for a date
    :return: the data combined into a CamData object
    """
    result_name = None
    result_list = []

    for files, for_date in image_groups:
        print("Collecting {} images for {}".format(len(files), for_date))
        cam_data = extract_by_type(files, for_date)
        if cam_data.name is None or len(cam_data.contents) == 0:
            print("No files in {}".format(files))
        elif result_name is None:
            result_name = cam_data.name
        elif result_name != cam_data.name:
            raise Exception("Invalid files found with prefixes {} and {}".format(result_name, cam_data.name))
        result_list.extend(cam_data.contents)
    return CamData(result_name, result_list)


def collect_images(camera_path: str, for_date: date = None) -> CamData:
    """Collects all picture in a given root path.

    The files are searched in subdirectories `camera_path/year/month/day` and
    collected into a `CamData` object.

    It is assumed that all files have the same camera name as prefix, otherwise
    an `Exception` will be raised.

    :param camera_path: the root path for pictures
    :param for_date: optional date for image collection
    :return: the constructed object holding all pictures
    """
    if for_date:
        picture_path = build_path(camera_path, for_date)
        _, _, filenames = next(walk(picture_path))
        images = filenames, for_date
        return _collect_images([images])
    else:
        return _collect_images(_iterate_image_directories(camera_path))


def load_cam_data(root: str, cameras: Sequence[str], for_date: date = None) -> Dict[str, CamData]:
    """Loads all pictures for multiple cameras in a root directory.

    Each camera data is expected to reside in its own directory with structure
    `root/camera_root/year/month/day/pictures.{jpg,mp4}`.

    If the date is present, only images for the specified date are loaded.
    Otherwise, the whole directory is traversed.

    :param root: root directory for the camera data
    :param cameras: cameras for image loading, subdirectories in the root
    :param for_date: optional date for image loading
    :return: dictionary of paths to compiled `CamData` objects
    """

    def load_camera_with_logging(camera: str) -> CamData:
        images = collect_images(path.join(root, camera), for_date)
        print("Found {} images for {}".format(len(images[1]), camera))
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
        print("Skipping pair with {} seconds difference".format(difference))
        return 1
    else:
        result.append([candidate, image])
        return 0


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

    if candidate is not None:
        skip_count += _add_if_proximate(candidate, image, result)

    if skip_count > 0:
        print("Skipped {} images".format(skip_count))

    return result


def build_path(root: str, picture: Union[PictureData, date]) -> str:
    """Returns the path to a picture

    >>> build_path("root/dir", PictureData(datetime(2021, 3, 9, 16, 44, 20), []))
    'root/dir/2021/03/09'

    :param root: the output root directory
    :param picture: the picture file for which the path is constructed
    :return: the path to the file relative to the root dir
    """

    def build_path_from_date(picture_time: date) -> str:
        return path.join(root, picture_time.strftime('%Y'), picture_time.strftime('%m'), picture_time.strftime('%d'))

    if isinstance(picture, PictureData):
        return build_path_from_date(picture.time)
    else:
        return build_path_from_date(picture)


def build_file_name(cam_name: str, picture: PictureData) -> str:
    """Builds the file name without suffix.

    >>> build_file_name("Camera", PictureData(datetime(2021, 3, 9, 16, 44, 20), []))
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

    symlinks_root = path.join(IMAGES_DIRECTORY, path.basename(root))
    symlinks_file_relative = build_path(symlinks_root, symlink_defining_picture)
    symlinks_file_name = build_file_name(cam_name, symlink_defining_picture)

    for picture in pictures:
        for file_type in picture.types:
            target_file = path.join(web_root, symlinks_file_relative, symlinks_file_name + "." + file_type)

            source_image_path = build_path(root, picture)
            source_image_file_name = build_file_name(cam_name, picture)
            source_image_symlink = path.join(source_image_path, source_image_file_name + "." + file_type)

            try:
                symlink(path.abspath(source_image_symlink), target_file)
            except FileNotFoundError:
                makedirs(path.dirname(target_file))
                symlink(path.abspath(source_image_symlink), target_file)
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
        updated_pictures.append(create_symlink(root, web_root, cam_data.name, pictures))
    return CamData(cam_data.name, updated_pictures)
