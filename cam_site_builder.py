"""Creates the actual cam site.
"""
from datetime import datetime, date, timedelta
from os import path
from typing import Dict, Optional, Sequence, Collection

from dominate import document
from dominate.tags import a, div, h1, img, h2, p

from cam_file import build_path, build_file_name, IMAGES_DIRECTORY
from cam_site_data import PictureData, CamData
from thumbnails import THUMBNAIL_DIRECTORY

ROUND = 10


def round_minutes(timestamp: datetime, delta_minutes: int):
    """Rounds a timestamp to multiples of minutes.

    Ignores time shares less than seconds. These do not occur in the context of
    the cam site as all timestamps are only in second acurracy.

    >>> round_minutes(datetime(2021, 3, 13, 15, 10, 55), 10)
    datetime.datetime(2021, 3, 13, 15, 10)

    Rounding uses exact rounding and the threshold time is exactly in the
    middle of the `delta_minutes`:

    >>> round_minutes(datetime(2021, 3, 13, 15, 14, 59), 10)
    datetime.datetime(2021, 3, 13, 15, 10)
    >>> round_minutes(datetime(2021, 3, 13, 15, 15, 0), 10)
    datetime.datetime(2021, 3, 13, 15, 20)

    :param timestamp: a datetime object to be rounded
    :param delta_minutes: number of minutes
    """
    multiple_seconds = timedelta(minutes=delta_minutes).total_seconds()
    value_seconds = (timestamp - timestamp.min).seconds
    rounded_seconds = (value_seconds + multiple_seconds / 2) // multiple_seconds * multiple_seconds
    return timestamp + timedelta(0, rounded_seconds - value_seconds)


def date_site_name(for_date: date) -> str:
    """Returns the

    :param for_date:
    :return:
    """
    return for_date.strftime('%Y-%m-%d.html')


class ImageBlock:
    """Contains all HTML elements of image block for one point in time.

    Provides a `parent_block` which is a `div` element that can be included
    into a document. The div itself will contain sub elements such as a
    heading and space for pictures each camera. Each camera gets a reserved
    `div` element that can be accessed and filled elsewhere.
    """

    def __init__(self, for_time: datetime, cameras: Collection[str], style: str) -> None:
        """

        :param for_time:
        :param cameras:
        :param style: the style. 'full' for 100% wide, 'float' for floating images next to each other
        """
        self.for_time = for_time
        self.cameras = cameras
        self._picture_divs = {}
        if style == 'float':
            self.parent_div = self._init_for_float()
        elif style == 'full':
            self.parent_div = self._init_for_full()
        else:
            raise ValueError("Unsupported style: ''{}".format(style))

    def picture_div(self, camera: str) -> div:
        return self._picture_divs[camera]

    def _init_for_full(self):
        parent_div = div()
        table_div = div(style="display:table;width=100%")

        with parent_div:
            h2(str(self.for_time))
        parent_div.add(table_div)

        width = int(100 / len(self.cameras))
        for camera in self.cameras:
            camera_div = div(_style="display:table-cell;width:{}%;height:512px".format(width))
            self._picture_divs[camera] = camera_div
            table_div.add(camera_div)
        return parent_div

    def _init_for_float(self) -> div:
        parent_div = div(_style="overflow:hidden")

        with parent_div:
            h2(str(self.for_time))
        for camera in self.cameras:
            camera_div = div(_style="float:left")
            self._picture_divs[camera] = camera_div
            parent_div.add(camera_div)
        return parent_div


def _add_image(parent_block: div, camera_root: str, name: str, picture: PictureData, use_thumbnail: bool = True):
    """

    :param camera_root:
    :param name:
    :param picture:
    :return:
    """
    with parent_block:
        image_src = path.join(build_path(path.join(IMAGES_DIRECTORY, camera_root), picture),
                              build_file_name(name, picture) + ".jpg")
        if use_thumbnail:
            thumbnail = path.join(build_path(path.join(THUMBNAIL_DIRECTORY, camera_root), picture),
                                  build_file_name(name, picture) + ".jpg")
        else:
            thumbnail = image_src

        a(
            img(
                _style="width:100%; height:100%",
                src=thumbnail
            ),
            href=image_src
        )

        if len(picture.types) == 2:
            film_src = path.join(build_path(path.join(IMAGES_DIRECTORY, camera_root), picture),
                                 build_file_name(name, picture) + ".mp4")
            p(
                a(
                    "Captured video",
                    href=film_src
                )
            )


class DateSiteBuilder:
    """Builder for the site for a certain date.

    """

    def _get_with_default(self, key: datetime) -> ImageBlock:
        if key in self.times:
            return self.times[key]
        else:
            new_block = ImageBlock(key, self.cameras, style='float')
            self.times[key] = new_block
            return new_block

    def __init__(self, project_name: str, for_date: date, cameras: Collection[str], output_directory: str) -> None:
        """

        """
        self.project_name = project_name
        self.for_date: date = for_date
        self.cameras = cameras
        self.output_directory = output_directory
        self.doc = document(title="{} - {}".format(project_name, for_date))
        self.times = {}
        """Contains the blocks for one datetime entry."""

    def add(self, name: str, camera_root: str, picture: PictureData) -> None:
        """Adds a picture to the site.

        :param name:
        :param camera_root:
        :param picture:
        """
        rounded_time_stamp = round_minutes(picture.time, ROUND)

        parent_block = self._get_with_default(rounded_time_stamp).picture_div(camera_root)
        _add_image(parent_block, camera_root, name, picture)

    def write(self) -> str:
        """Writes out the document.

        :return:
        """
        print("Finalize output")
        for time, tag in sorted(self.times.items()):
            self.doc.add(tag.parent_div)

        output_file_name = path.join(self.output_directory, date_site_name(self.for_date))
        print("Writing {}".format(output_file_name))
        with open(output_file_name, 'w') as f:
            f.write(self.doc.render())
        return output_file_name


def get_active_date(indices: Dict[str, int], cam_data: Dict[str, CamData]) -> Optional[date]:
    dates = [cam_data[key].contents[indices[key]].time.date() for key, value in indices.items()]
    if dates:
        return min(dates)
    else:
        return None


def round_to(contents: Sequence[PictureData], minutes: int) -> Sequence[PictureData]:
    """Takes only pictures at multiples of a time.

    :param contents: the original contents
    :param minutes: the minutes interval to filter for
    :return: the items of the original sequence closest to the multiples of given minutes
    """
    result = []

    candidate = None
    candidate_diff = 0
    candidate_picture = None

    for image in contents:
        rounded = round_minutes(image.time, minutes)
        if candidate is None:
            candidate = rounded
            candidate_diff = abs((image.time - rounded).total_seconds())
            candidate_picture = image
        elif abs((rounded - candidate).total_seconds()) < 1:
            image_diff = abs((image.time - rounded).total_seconds())
            if image_diff < candidate_diff:
                # We found an improvement
                candidate = rounded
                candidate_picture = image
                candidate_diff = image_diff
        else:
            # We are nearer to a new point
            result.append(candidate_picture)
            candidate_picture = image
            candidate = rounded
            candidate_diff = abs((image.time - rounded).total_seconds())

    print("Rounded {} to {} points.".format(len(contents), len(result)))

    return result


class CamSiteBuilder:
    """Builds the cam website.

    Supports multiple cams which are displayed in parallel.
    """

    def __init__(self, project_name: str, output_directory: str, cam_data_sets: Dict[str, CamData],
                 round_to_minutes: int = ROUND) -> None:
        """

        """
        # Round
        self.cam_data_sets = self._rounded_cam_data(cam_data_sets, round_to_minutes)
        self.project_name = project_name
        self.output_directory = output_directory
        """The directory which holds created thumbnails."""

    @staticmethod
    def _rounded_cam_data(cam_data_sets: Dict[str, CamData], to_minutes: int) -> Dict[str, CamData]:
        return {key: CamData(value.name, sorted(round_to(value.contents, to_minutes))) for key, value in
                cam_data_sets.items()}

    def create_main_site(self) -> None:
        """Creates the landing page.
        """
        doc = document(self.project_name)
        doc.add(h1("Almost live view"))

        new_block = ImageBlock(datetime.now(), self.cam_data_sets.keys(), style='full')
        for camera_root, cam_data in self.cam_data_sets.items():
            current_picture = cam_data.contents[-1]
            parent_block = new_block.picture_div(camera_root)
            _add_image(parent_block, camera_root, cam_data.name, current_picture, use_thumbnail=False)
        doc.add(new_block.parent_div)

        doc.add(h1("Archive"))
        list_block = div()
        doc.add(list_block)

        # Create iterators
        indices = {}
        for camera_root, _ in self.cam_data_sets.items():
            indices[camera_root] = 0

        active_date = get_active_date(indices, self.cam_data_sets)
        current_date_site_builder = DateSiteBuilder(self.project_name, active_date, self.cam_data_sets.keys(),
                                                    self.output_directory)

        while indices:
            # Grab next pictures, if on current date
            pictures_to_add = {}
            to_be_deleted = []
            for key, value in indices.items():
                if self.cam_data_sets[key].contents[value].time.date() == active_date:
                    pictures_to_add[key] = self.cam_data_sets[key].contents[value]
                    indices[key] += 1
                    if indices[key] == len(self.cam_data_sets[key].contents):
                        to_be_deleted.append(key)
            for key in to_be_deleted:
                del indices[key]
            for cam, picture in pictures_to_add.items():
                current_date_site_builder.add(self.cam_data_sets[cam].name, cam, picture)

            # Update indices
            next_date = get_active_date(indices, self.cam_data_sets)
            if next_date != active_date:
                current_date_site_builder.write()
                self._add_date(list_block, active_date)
                active_date = next_date
                current_date_site_builder = DateSiteBuilder(self.project_name, active_date, self.cam_data_sets.keys(),
                                                            self.output_directory)

        with open(path.join(self.output_directory, 'index.html'), 'w') as f:
            f.write(doc.render())

    @staticmethod
    def _add_date(parent: div, to_add: date):
        link_text = to_add.strftime('%Y-%m-%d')
        link_url = date_site_name(to_add)
        with parent:
            p(
                a(
                    link_text,
                    href=link_url
                )
            )