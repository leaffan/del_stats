@echo off

python download_team_data.py -s 2019 -g RS schedules
python download_team_data.py -s 2019 -g RS roster_stats
python download_team_data.py -s 2019 -g RS team_stats

python get_all_players.py
python order_schedules.py

python download_game_data.py -s 2019 -g RS game_info
python download_game_data.py -s 2019 -g RS game_events
python download_game_data.py -s 2019 -g RS game_roster
python download_game_data.py -s 2019 -g RS game_team_stats
python download_game_data.py -s 2019 -g RS game_player_stats
python download_game_data.py -s 2019 -g RS game_goalies
python download_game_data.py -s 2019 -g RS shifts
python download_game_data.py -s 2019 -g RS shots

python download_career_data.py
