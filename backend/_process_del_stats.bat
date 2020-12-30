@echo off

set SEASON=%1

if [%SEASON%] EQU [] (
    set SEASON=2020
)

for /F "usebackq tokens=1,2 delims==" %%i in (`wmic os get LocalDateTime /VALUE 2^>NUL`) do if '.%%i.'=='.LocalDateTime.' set ldt=%%j
set ldt=%ldt:~0,4%-%ldt:~4,2%-%ldt:~6,2%

set CURRENT_DATE=%ldt%

python get_del_games.py --initial -s %SEASON% -f "Sep 1, %SEASON%" -t "%CURRENT_DATE%"
python get_shots.py --initial -s %SEASON%
python get_del_team_game_stats.py --initial -s %SEASON%
python get_del_player_game_stats.py --initial -s %SEASON%
python get_league_wide_stats.py --initial -s %SEASON%
python get_del_goalie_stats.py --initial -s %SEASON%
python aggregate_del_player_game_stats.py -s %SEASON%
python get_streaks.py -s %SEASON%

rem TODO: check base stats
if [%SEASON%] EQU [2020] (
    python update_coaches.py
    python update_h2h_records.py
    python update_career_stats.py
    python add_career_stats_to_rosters.py -s %SEASON%
)
