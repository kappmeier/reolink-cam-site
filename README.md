 # Reolink Cam Site

 Builds an overview webpage based on photos and videos created by [Reolink] security cameras.

 The application crawls through a directory tree hosting uploaded photos and videos, collects files
 that belong together, and creates a website with thumbnails linked with the video files. All video
 files remain in their existing location and are accessed via symlinks.

## Requirements

- A [Linux] server hosting the image and video data. Data is uploaded from Reolink cameras, for
  example using FTP transfer.
- Python 3 running this software, ideally scheduled automatically e.g. via [cron] job.
- Webserver able to deliver static webpage, e.g. [nginx].
- One ore more [Reolink] security cameras configured to upload photos and videos.
- Optional: to set up an FTP server: [docker].

## Useage

### Preparation

First step to create a static cam site page. The script traverses the cameras directories in a
given root directory and creates links and thumbnails in the web root. The latter directory is used
as input for the [creation](#creation) script.

#### Usage
```
python3 prepare_cam_site.py \
        --root "/data/camera-storage" \
        --web-root ./out \
        --cameras camera-front camera-back \
        --date 2022-02-16
```

#### Parameters

- `root`: Root directory of cam data. The root directory containing sub directories for each
  camera. The camera directories contain data in the [Reolink] software format.
- `web-root`: The output directory. Will be used as output and expected to be the web root of the
  final cam site. This will contain the `images` and `thumbnails` directories after execution. The
  directory is supposed to be the input for the creation script.
- `cameras`: The cameras in the cam site. They are expected to be directories in the `ROOT`
  directory. They contain the content produced by [Reolink] software (in `year/month/day` sub
  directories). They are read and used to process the images and thumbnails.
- `date`: Load images for a certain date. The date is specified in ISO format `YYYY-MM-DD`.

### Creation

A static cam site page is created by `create_cam_site.py`. The script expects a prepared directory
with images and thumbnails as produced by the [preparation](#preparation) script.

#### Usage

```console
python3 create_cam_site.py \
        --name "My CamSite" \
        --dir ./out \
        --cameras camera-front camera-back \
        --date 2022-02-16
```

#### Parameters

- `name`: The cam site name. Used as the title of the cam site in the created website.
- `dir`: The Output directory. Will contain the created cam site. Also used as input directory for
  `images` and `thumbnails`. This is the same output directory as used for the preparation script.
- `cameras`: A list of cameras in the cam site. The cameras are directories inside the `images` and
  `thumbnails` directories. They are the same as used as input for the [preparation](#preparation).
- `date`: Optional date to load images for. The date is specified in ISO format `YYYY-MM-DD`.

## License

Copyright © 2022 Jan-Philipp Kappmeier

This project is [licensed](LICENSE) under the terms of the [Apache License 2.0].

[Reolink]: https://reolink.com/de/
[Linux]: https://www.linux.org/
[cron]: https://pubs.opengroup.org/onlinepubs/9699919799/utilities/crontab.html
[nginx]: https://www.nginx.com/
[docker]: https://www.docker.com/
[Apache License 2.0]: http://www.apache.org/licenses/LICENSE-2.0
