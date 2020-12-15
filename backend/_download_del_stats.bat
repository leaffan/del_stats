@echo off

set SEASON=%1
set GAME_TYPE=%2

if [%SEASON%] EQU [] (
    set SEASON=2020
)

if [%GAME_TYPE%] EQU [] (
    set GAME_TYPE=ALL
)

python download_team_data.py -s %SEASON% -g %GAME_TYPE% schedules
python download_team_data.py -s %SEASON% -g %GAME_TYPE% roster_stats
python download_team_data.py -s %SEASON% -g %GAME_TYPE% team_stats

python get_all_players.py
python order_schedules.py -s %SEASON%

python download_game_data.py -s %SEASON% -g %GAME_TYPE% game_info
python download_game_data.py -s %SEASON% -g %GAME_TYPE% game_events
python download_game_data.py -s %SEASON% -g %GAME_TYPE% game_roster
python download_game_data.py -s %SEASON% -g %GAME_TYPE% game_team_stats
python download_game_data.py -s %SEASON% -g %GAME_TYPE% game_player_stats
python download_game_data.py -s %SEASON% -g %GAME_TYPE% game_goalies
python download_game_data.py -s %SEASON% -g %GAME_TYPE% shifts
python download_game_data.py -s %SEASON% -g %GAME_TYPE% shots
python download_game_data.py -s %SEASON% -g %GAME_TYPE% faceoffs

if [%SEASON%] EQU [2020] (
    python download_career_data.py
)

python check_and_commit_repo.py
