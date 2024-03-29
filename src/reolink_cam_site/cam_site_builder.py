"""Creates the actual cam site.

Copyright © 2022 Jan-Philipp Kappmeier

Licensed under the Apache License, Version 2.0 (the "License"); you may not use this file except
in compliance with the License. You may obtain a copy of the License at

       http://www.apache.org/licenses/LICENSE-2.0
"""
from calendar import monthrange
from datetime import datetime, date, timedelta
from locale import setlocale, LC_TIME
from os import path, listdir
from shutil import copy
from sys import modules
from typing import Callable, Collection, Dict, Optional, Sequence

from dominate import document
from dominate.tags import a, div, h1, h2, h3, img, link, p, table, tr, td, tbody, th, thead

from reolink_cam_site.cam_file import build_path, build_file_name, IMAGES_DIRECTORY
from reolink_cam_site.cam_site_data import PictureData, CamData
from reolink_cam_site.thumbnails import THUMBNAIL_DIRECTORY

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

    def __init__(self, for_time: datetime, cameras: Collection[str], style: str,
                 time_format: Callable[[datetime], str]) -> None:
        """

        :param for_time:
        :param cameras:
        :param style: the style. 'full' for 100% wide, 'float' for floating images next to each other
        :param time_format: formats the time to the header
        """
        self.for_time = for_time
        self.cameras = cameras
        self.time_format = time_format
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
        table_div = div(cls="cam-wrapper")

        with parent_div:
            h2(self.time_format(self.for_time))
        parent_div.add(table_div)

        for camera in self.cameras:
            camera_div = div()
            self._picture_divs[camera] = camera_div
            table_div.add(camera_div)
        return parent_div

    def _init_for_float(self) -> div:
        parent_div = div(_style="overflow:hidden")

        with parent_div:
            h2(self.time_format(self.for_time))
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
                _style="width:100%",
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
            new_block = ImageBlock(key, self.cameras, style='float',
                                   time_format=lambda time: datetime.strftime(time, '%H:%M'))
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
        with self.doc.head:
            link(rel='stylesheet', href='style.css')
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
        with self.doc.add(div(cls="site")) as site:
            site.add(h1("Archiv {}".format(str(self.for_date))))
            for time, tag in sorted(self.times.items()):
                site.add(tag.parent_div)

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

    if len(result) == 0 and candidate is not None:
        result.append(candidate_picture)

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
        self.cam_data_sets = cam_data_sets
        self.rounded_cam_data_sets = self._rounded_cam_data(cam_data_sets, round_to_minutes)
        self.project_name = project_name
        self.output_directory = output_directory
        self.archive_pages = set()
        """The directory which holds created thumbnails."""

    @staticmethod
    def _rounded_cam_data(cam_data_sets: Dict[str, CamData], to_minutes: int) -> Dict[str, CamData]:
        return {key: CamData(value.name, sorted(round_to(value.contents, to_minutes))) for key, value in
                cam_data_sets.items()}

    def load_archive_pages(self) -> None:
        """Loads existing archive pages.

        Finds all archive pages (named YYYY-MM-DD.html) in the root directory
        and adds it to the known archive pages.

        Consecutive calls to build the main page will include these pages.
        """
        print("Searching existing archive directories in {}".format(self.output_directory))

        def is_date_file(file_name: str) -> bool:
            try:
                datetime.strptime(file_name, '%Y-%m-%d.html')
                return True
            except ValueError:
                return False

        self.archive_pages |= {datetime.strptime(candidate_file, '%Y-%m-%d.html').date()
                               for candidate_file in listdir(self.output_directory) if is_date_file(candidate_file)}

    def _create_live_block(self) -> ImageBlock:
        """Creates an image block for the title page.

        The image block contains the latest picture for each camera.

        :return: an `ImageBlock` instance with the latest images
        """
        new_block = ImageBlock(datetime.now(), self.cam_data_sets.keys(), style='full',
                               time_format=lambda time: datetime.strftime(time, '%Y-%m-%d %H:%M'))
        for camera_root, cam_data in self.cam_data_sets.items():
            current_picture = max(cam_data.contents)
            parent_block = new_block.picture_div(camera_root)
            _add_image(parent_block, camera_root, cam_data.name, current_picture, use_thumbnail=False)
        return new_block

    def create_full_site(self) -> None:
        """Creates the full cam site.

        Builds the landing page and archive pages for all available images.
        """
        package_directory = modules['reolink_cam_site'].__path__[0]
        copy(path.join(package_directory, 'style.css'),
             path.join(self.output_directory, 'style.css'))
        doc = document(self.project_name)

        with doc.head:
            link(rel='stylesheet', href='style.css')

        with doc.add(div(cls="site")) as site:
            site.add(h1("Aktuell"))

            new_block = self._create_live_block()
            site.add(new_block.parent_div)

            site.add(h1("Archiv"))
            list_block = div()
            site.add(list_block)

        self.create_archive_pages()
        self.create_archive(list_block)

        with open(path.join(self.output_directory, 'index.html'), 'w') as f:
            f.write(doc.render())

    def create_archive_pages(self) -> None:
        """Builds all archive pages for the available images.

        Iterates all image files, aggregates per date and builds an archive
        site for each date.

        An entry for all dates with data is added to the list of archive pages.
        """
        # Create iterators
        indices = {}
        for camera_root, _ in self.rounded_cam_data_sets.items():
            indices[camera_root] = 0

        active_date = get_active_date(indices, self.rounded_cam_data_sets)
        date_site_builder = self._next_archive_builder(active_date)
        while active_date:
            next_date = self._handle_date(indices, active_date, date_site_builder)
            if next_date != active_date:
                date_site_builder.write()
                active_date = next_date
                date_site_builder = self._next_archive_builder(active_date)

    def _next_archive_builder(self, next_date: date) -> Optional[DateSiteBuilder]:
        """Prepares builder for the archive page for a date.

        Creates a `DateSiteBuilder` instance for the given date. When the input
        is `None`, no builder is returned.

        As a side effect, the date is added to the list of archive pages.

        :param next_date: the date for which the archive is built
        :return: the builder for the archive page
        """
        if next_date:
            self.archive_pages.add(next_date)
            return DateSiteBuilder(self.project_name, next_date, self.rounded_cam_data_sets.keys(),
                                   self.output_directory)
        else:
            return None

    def _handle_date(self, indices: Dict[str, int], active_date: date, archive_page_builder: DateSiteBuilder) \
            -> Optional[date]:
        """Iterates over camera contents and adds images to a builder.

        Takes images for the passed active date and adds it to the archive page
        builder. The indices are used as a counter to decide when a date is
        completely handled.

        :param indices: the dates not yet completely handled
        :param active_date: the date that is currently handled
        :param archive_page_builder: the builder for the archive page for the active date
        :return: the next active date, can be the same or another date
        """
        # Grab next pictures, if on current date
        pictures_to_add = {}
        to_be_deleted = []
        for key, value in indices.items():
            if self.rounded_cam_data_sets[key].contents[value].time.date() == active_date:
                pictures_to_add[key] = self.rounded_cam_data_sets[key].contents[value]
                indices[key] += 1
                if indices[key] == len(self.rounded_cam_data_sets[key].contents):
                    to_be_deleted.append(key)
        for key in to_be_deleted:
            del indices[key]
        for cam, picture in pictures_to_add.items():
            archive_page_builder.add(self.rounded_cam_data_sets[cam].name, cam, picture)

        # Update indices
        return get_active_date(indices, self.rounded_cam_data_sets)

    def create_archive(self, list_block: div) -> None:
        dates = sorted(self.archive_pages)
        calendar_builder = CalendarTableBuilder(dates)
        calendar_builder.build(list_block)


class CalendarTableBuilder:
    """Builds a sequence of calendars linked to archive pages.

    """

    def __init__(self, dates: Sequence[date]) -> None:
        self.dates = dates
        self.date_index = 0
        self._year = 0
        self._month = 0
        self._today = date.today()
        setlocale(LC_TIME, 'de_DE.UTF-8')

    def build(self, list_block: div):
        """Creates the calendar table and adds it to a parent block.

        :return:
        """
        self.date_index = 0
        last_year = 0
        year_block = None
        while self.date_index < len(self.dates):
            self._year = self.dates[self.date_index].year
            if self._year != last_year:
                last_year = self._year
                year_block = self._create_year_block(list_block)
            self._add_month(year_block)

    def _create_year_block(self, parent_block: div) -> div:
        year = self.dates[self.date_index].year
        parent_block.add(h2(year))
        year_block = div(cls="container-year")
        parent_block.add(year_block)
        return year_block

    def _add_month(self, parent_block: div) -> None:
        """Adds the content for a single month. The month consists of

        <div>
          <h2>Month name</h2>
          <table>Calendar content</table>
        </div>

        :param parent_block: a container that the month will be added to
        """
        start_date = self.dates[self.date_index]

        self._month = start_date.month

        self.week_day_index, self.days_in_month = monthrange(self._year, self._month)

        with parent_block.add(div()):
            h3(start_date.strftime("%B"))

            with table(cls="calendar"):
                with thead():
                    tr(
                        th("Mo", cls="workday"),
                        th("Di", cls="workday"),
                        th("Mi", cls="workday"),
                        th("Do", cls="workday"),
                        th("Fr", cls="workday"),
                        th("Sa", cls="workday"),
                        th("So", cls="weekend"),
                        cls="names"
                    )
                with tbody():
                    self._fill_table()

    def __advance_row(self, current_row: tr) -> tr:
        self.week_day_index += 1
        return tr() if self.week_day_index % 7 == 0 else current_row

    def __add_element(self, current_row: tr, content, current: bool) -> None:
        cls = "workday" if self.week_day_index % 7 < 6 else "weekend"
        if current:
            today_div = div(content, cls="today")
            content = today_div
        current_row += td(content, cls=cls)

    def __fill_initial_skip(self) -> tr:
        current_row = tr()
        for i in range(self.week_day_index):
            self.__add_element(current_row, "", False)
        return current_row

    def __fill_days_in_month(self, current_row: tr) -> tr:
        for i in range(1, self.days_in_month + 1):
            if i == self.dates[self.date_index].day:
                link_to_archive = a(i, href=date_site_name(self.dates[self.date_index]))
                self.__add_element(current_row, link_to_archive, self.__is_today(i))
                self.date_index += 1
                if self.date_index == len(self.dates) or self.dates[self.date_index].month != self._month:
                    return self.__advance_row(current_row)
            else:
                self.__add_element(current_row, i, self.__is_today(i))
            current_row = self.__advance_row(current_row)
        raise AssertionError("No entry for month {}".format(self._month))

    def __fill_terminal_skip(self, day: int, current_row: tr) -> None:
        while self.week_day_index % 7 != 0 or day < self.days_in_month:
            text = "" if day > self.days_in_month else day
            self.__add_element(current_row, text, self.__is_today(day))
            day += 1
            current_row = self.__advance_row(current_row)

    def __is_today(self, day: int) -> bool:
        return self._year == self._today.year and self._month == self._today.month and self._today.day == day

    def _fill_table(self) -> None:
        """Fills table for a single month.

        Expects an open dominate tag.
        """
        current_row = self.__fill_initial_skip()

        current_row = self.__fill_days_in_month(current_row)

        day = self.dates[self.date_index - 1].day + 1
        self.__fill_terminal_skip(day, current_row)

    @staticmethod
    def _add_date(parent: div, to_add: date) -> None:
        """Adds a link to an archive page for a date.

        >>> parent_entity = div()
        >>> CalendarTableBuilder._add_date(parent_entity, date(2021, 3, 21))
        >>> print(parent_entity)
        <div>
          <p>
            <a href="2021-03-21.html">2021-03-21</a>
          </p>
        </div>

        :param parent:
        :param to_add:
        """
        link_text = to_add.strftime('%Y-%m-%d')
        link_url = date_site_name(to_add)
        with parent:
            p(
                a(
                    link_text,
                    href=link_url
                )
            )
