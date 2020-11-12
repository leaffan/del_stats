#!/bin/bash

season="${1:-2020}"
game_type="${2:-ALL}"

/home/pacs/mre00/users/markus/_del/_download_del_stats.sh "$season" "$game_type"
/home/pacs/mre00/users/markus/_del/_process_del_stats.sh "$season"
/home/pacs/mre00/users/markus/_del/_copy_del_stats.sh "$season"
