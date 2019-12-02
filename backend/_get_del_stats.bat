@echo off

set SEASON=%1
set GAME_TYPE=%2

if [%SEASON%] EQU [] (
    set SEASON=2019
)

if [%GAME_TYPE%] EQU [] (
    set GAME_TYPE=ALL
)

call _download_del_stats.bat %SEASON% %GAME_TYPE%
call _process_del_stats.bat %SEASON%
call _copy_del_stats.bat %SEASON%
