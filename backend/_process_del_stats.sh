#!/bin/bash

date=$(date '+%Y-%m-%d')
season="${1:-2019}"

python3 /home/pacs/mre00/users/markus/_del/get_del_games.py -s "$season" --initial -f "Sep 1, $season" -t "$date"
python3 /home/pacs/mre00/users/markus/_del/get_shots.py -s "$season" --initial
python3 /home/pacs/mre00/users/markus/_del/get_del_team_game_stats.py -s "$season" --initial
python3 /home/pacs/mre00/users/markus/_del/get_del_player_game_stats.py -s "$season" --initial
python3 /home/pacs/mre00/users/markus/_del/get_league_wide_stats.py -s "$season" --initial
python3 /home/pacs/mre00/users/markus/_del/get_del_goalie_stats.py -s "$season" --initial
python3 /home/pacs/mre00/users/markus/_del/aggregate_del_player_game_stats.py -s "$season"
python3 /home/pacs/mre00/users/markus/_del/get_streaks.py -s "$season"
python3 /home/pacs/mre00/users/markus/_del/update_coaches.py
python3 /home/pacs/mre00/users/markus/_del/update_h2h_records.py

python3 /home/pacs/mre00/users/markus/_del/add_career_stats_to_rosters.py -s "$season"
