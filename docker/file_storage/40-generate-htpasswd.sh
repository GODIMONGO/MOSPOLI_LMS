#!/bin/sh
set -eu

FILE_STORAGE_USER="${FILE_STORAGE_USER:-storage_admin}"
FILE_STORAGE_PASSWORD="${FILE_STORAGE_PASSWORD:-change_this_password}"

htpasswd -bc /etc/nginx/.htpasswd "${FILE_STORAGE_USER}" "${FILE_STORAGE_PASSWORD}"
