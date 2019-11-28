#!/bin/bash

season="${1:-2019}"
game_type="${2:-ALL}"

python3 /home/pacs/mre00/users/markus/_del/download_team_data.py -s "$season" -g "$game_type" schedules
python3 /home/pacs/mre00/users/markus/_del/download_team_data.py -s "$season" -g "$game_type" roster_stats
python3 /home/pacs/mre00/users/markus/_del/download_team_data.py -s "$season" -g "$game_type" team_stats
python3 /home/pacs/mre00/users/markus/_del/get_all_players.py
python3 /home/pacs/mre00/users/markus/_del/order_schedules.py -s "$season"
python3 /home/pacs/mre00/users/markus/_del/download_game_data.py -s "$season" -g "$game_type" game_info
python3 /home/pacs/mre00/users/markus/_del/download_game_data.py -s "$season" -g "$game_type" game_events
python3 /home/pacs/mre00/users/markus/_del/download_game_data.py -s "$season" -g "$game_type" game_roster
python3 /home/pacs/mre00/users/markus/_del/download_game_data.py -s "$season" -g "$game_type" game_team_stats
python3 /home/pacs/mre00/users/markus/_del/download_game_data.py -s "$season" -g "$game_type" game_player_stats
python3 /home/pacs/mre00/users/markus/_del/download_game_data.py -s "$season" -g "$game_type" game_goalies
python3 /home/pacs/mre00/users/markus/_del/download_game_data.py -s "$season" -g "$game_type" shifts
python3 /home/pacs/mre00/users/markus/_del/download_game_data.py -s "$season" -g "$game_type" shots
python3 /home/pacs/mre00/users/markus/_del/download_career_data.py
