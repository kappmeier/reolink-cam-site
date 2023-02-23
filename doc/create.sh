#!/usr/bin/env bash

# Location of output, relative to working directory
NAME="Reolink Cam Site Test"
ROOT="sample_root/"
WEB_ROOT="web_root/"

# Definition of the cameras
CAMERAS=("front" "back" "entrance")
COLORS=("yellow" "pink" "LightSkyBlue")

# Time range and interval
DAYS=100
SKIP_SECONDS=600

# Format specifications
FILE_SUFFIX="_01_%Y%m%d%H%M%S.jpg"
PATH_SUFFIX="/%Y/%m/%d/"
TEXT_FORMAT="%Y-%m-%d\n%H:%M:%S"

START_DATE=$(date "+%Y-%m-%dT%H:%M:%S" --date="${DAYS} days ago")
ROUNDS=$((${DAYS}*24*60*60/${SKIP_SECONDS}))
for i in "${!CAMERAS[@]}"; do
    camera="${CAMERAS[i]}"
    color="${COLORS[i]}"

    current_date=$(date -d "${START_DATE}" "+%s")
    for ((i = 0; i < ROUNDS; ++i)); do
        path="${ROOT}$(date "+${camera}${PATH_SUFFIX}" -d "@${current_date}")"
        file_name="$(date "+${camera}${FILE_SUFFIX}" -d "@${current_date}")"
        echo "${path}${file_name}"

        mkdir -p "${path}"
        image_text=$(date "+${TEXT_FORMAT}" -d "@${current_date}")
        convert -background "${color}" -fill black -pointsize 196 -gravity Center -size 1920x1080 label:"${image_text}" "${path}${file_name}"

        current_date=$(("$current_date + ${SKIP_SECONDS}"))
    done
done

# Build the Reolink Cam Site
prepare-cam-site --root "${ROOT}" --web-root "${WEB_ROOT}" --cameras "${CAMERAS[@]}"
create-cam-site --name "${NAME}" --dir "${WEB_ROOT}" --cameras "${CAMERAS[@]}"
