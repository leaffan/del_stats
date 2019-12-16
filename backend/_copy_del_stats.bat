@echo off

set SEASON=%1
set TGT_BASE_DIR=C:\dev\del_stats\frontend\data
set TGT_EXTENDED_DIR=C:\dev\del_stats\frontend\data\

set DEL_DATA_BASE_DIR=c:\del

if [%SEASON%] EQU [] (
    set SEASON=2019
)

echo %SEASON%

copy data\del_players.json %TGT_BASE_DIR%
copy data\%SEASON%\del_goalie_game_stats.json %TGT_BASE_DIR%\%SEASON%
copy data\%SEASON%\del_player_game_stats_aggregated.* %TGT_BASE_DIR%\%SEASON%
copy data\%SEASON%\del_player_game_stats.csv %TGT_BASE_DIR%\%SEASON%
copy data\%SEASON%\del_team_game_stats.json %TGT_BASE_DIR%\%SEASON%
copy data\%SEASON%\del_streaks_strict.json %TGT_BASE_DIR%\%SEASON%
copy data\%SEASON%\del_streaks_loose.json %TGT_BASE_DIR%\%SEASON%
copy data\%SEASON%\del_shots.csv %TGT_BASE_DIR%\%SEASON%
xcopy /i /y /d data\%SEASON%\per_player %TGT_BASE_DIR%\%SEASON%\per_player

copy %DEL_DATA_BASE_DIR%\career_stats\career_stats.json %TGT_BASE_DIR%\career_stats
xcopy /i /y /d %DEL_DATA_BASE_DIR%\career_stats\per_player %TGT_BASE_DIR%\career_stats\per_player
xcopy /i /y /d data\career_stats\per_team %TGT_BASE_DIR%\career_stats\per_team

:: Daten für Extended-Version
copy data\del_players.json %TGT_EXTENDED_DIR%
copy %DEL_DATA_BASE_DIR%\del_facts\facts.json %TGT_EXTENDED_DIR%\%SEASON%
copy data\%SEASON%\full_schedule.json %TGT_EXTENDED_DIR%\%SEASON%
copy data\%SEASON%\coaches.json %TGT_EXTENDED_DIR%\%SEASON%
copy data\%SEASON%\h2h.json %TGT_EXTENDED_DIR%\%SEASON%
copy data\%SEASON%\del_goalie_game_stats.json %TGT_EXTENDED_DIR%\%SEASON%
copy data\%SEASON%\del_goalie_game_stats_aggregated.json %TGT_EXTENDED_DIR%\%SEASON%
copy data\%SEASON%\del_player_game_stats_aggregated.* %TGT_EXTENDED_DIR%\%SEASON%
copy data\%SEASON%\del_player_game_stats.csv %TGT_EXTENDED_DIR%\%SEASON%
copy data\%SEASON%\del_team_game_stats.json %TGT_EXTENDED_DIR%\%SEASON%
copy data\%SEASON%\del_streaks_strict.json %TGT_EXTENDED_DIR%\%SEASON%
copy data\%SEASON%\del_streaks_loose.json %TGT_EXTENDED_DIR%\%SEASON%
xcopy /i /y /d data\%SEASON%\per_player %TGT_EXTENDED_DIR%\%SEASON%\per_player

copy %DEL_DATA_BASE_DIR%\career_stats\career_stats.json %TGT_EXTENDED_DIR%\career_stats
xcopy /i /y /d %DEL_DATA_BASE_DIR%\career_stats\per_player %TGT_EXTENDED_DIR%\career_stats\per_player
xcopy /i /y /d data\career_stats\per_team %TGT_EXTENDED_DIR%\career_stats\per_team
