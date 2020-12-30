#!/bin/bash

season="${1:-2020}"

# copying data sets to standard site location
cp -v /home/pacs/mre00/users/markus/_del/_data/del_players.json /home/doms/leaffan.net/subs/www/del/data/del_players.json
cp -v /home/pacs/mre00/users/markus/_del/_data/$season/del_league_stats.json /home/doms/leaffan.net/subs/www/del/data/$season
cp -v /home/pacs/mre00/users/markus/_del/_data/$season/del_goalie_game_stats.json /home/doms/leaffan.net/subs/www/del/data/$season
cp -v /home/pacs/mre00/users/markus/_del/_data/$season/del_player_game_stats_aggregated.* /home/doms/leaffan.net/subs/www/del/data/$season
cp -v /home/pacs/mre00/users/markus/_del/_data/$season/del_player_game_stats.csv /home/doms/leaffan.net/subs/www/del/data/$season
cp -v /home/pacs/mre00/users/markus/_del/_data/$season/del_team_game_stats.json /home/doms/leaffan.net/subs/www/del/data/$season
cp -v /home/pacs/mre00/users/markus/_del/_data/$season/del_streaks_loose.json /home/doms/leaffan.net/subs/www/del/data/$season
cp -v /home/pacs/mre00/users/markus/_del/_data/$season/del_streaks_strict.json /home/doms/leaffan.net/subs/www/del/data/$season
cp -v /home/pacs/mre00/users/markus/_del/_data/$season/del_shots.csv /home/doms/leaffan.net/subs/www/del/data/$season
cp -TRv /home/pacs/mre00/users/markus/_del/_data/$season/per_player/ /home/doms/leaffan.net/subs/www/del/data/$season/per_player/

# copying career stats to standard site location
cp -v /home/pacs/mre00/users/markus/_del/_data/career_stats/updated_career_stats.json /home/doms/leaffan.net/subs/www/del/data/career_stats/career_stats.json
cp -TRv /home/pacs/mre00/users/markus/_del/_data/career_stats/per_player/ /home/doms/leaffan.net/subs/www/del/data/career_stats/per_player/
cp -TRv /home/pacs/mre00/users/markus/_del/_data/career_stats/per_team/ /home/doms/leaffan.net/subs/www/del/data/career_stats/per_team/

# copying data sets to extended site location
cp -v /home/pacs/mre00/users/markus/_del/_data/del_players.json /home/doms/leaffan.net/subs/www/del_extended/data/del_players.json
cp -v /home/pacs/mre00/users/markus/_del/_data/$season/coaches.json /home/doms/leaffan.net/subs/www/del_extended/data/$season
cp -v /home/pacs/mre00/users/markus/_del/_data/$season/h2h.json /home/doms/leaffan.net/subs/www/del_extended/data/$season
cp -v /home/pacs/mre00/users/markus/_del/_data/$season/full_schedule.json /home/doms/leaffan.net/subs/www/del_extended/data/$season
cp -v /home/pacs/mre00/users/markus/_del/_data/$season/del_league_stats.json /home/doms/leaffan.net/subs/www/del_extended/data/$season
cp -v /home/pacs/mre00/users/markus/_del/_data/$season/del_goalie_game_stats.json /home/doms/leaffan.net/subs/www/del_extended/data/$season
cp -v /home/pacs/mre00/users/markus/_del/_data/$season/del_goalie_game_stats_aggregated.json /home/doms/leaffan.net/subs/www/del_extended/data/$season
cp -v /home/pacs/mre00/users/markus/_del/_data/$season/del_player_game_stats_aggregated.* /home/doms/leaffan.net/subs/www/del_extended/data/$season
cp -v /home/pacs/mre00/users/markus/_del/_data/$season/del_player_game_stats.csv /home/doms/leaffan.net/subs/www/del_extended/data/$season
cp -v /home/pacs/mre00/users/markus/_del/_data/$season/del_team_game_stats.json /home/doms/leaffan.net/subs/www/del_extended/data/$season
cp -v /home/pacs/mre00/users/markus/_del/_data/$season/del_streaks_loose.json /home/doms/leaffan.net/subs/www/del_extended/data/$season
cp -v /home/pacs/mre00/users/markus/_del/_data/$season/del_streaks_strict.json /home/doms/leaffan.net/subs/www/del_extended/data/$season
cp -TRv /home/pacs/mre00/users/markus/_del/_data/$season/per_player/ /home/doms/leaffan.net/subs/www/del_extended/data/$season/per_player/

# copying career stats to extended site location
cp -v /home/pacs/mre00/users/markus/_del/_data/career_stats/updated_career_stats.json /home/doms/leaffan.net/subs/www/del_extended/data/career_stats/career_stats.json
cp -TRv /home/pacs/mre00/users/markus/_del/_data/career_stats/per_player/ /home/doms/leaffan.net/subs/www/del_extended/data/career_stats/per_player/
cp -TRv /home/pacs/mre00/users/markus/_del/_data/career_stats/per_team/ /home/doms/leaffan.net/subs/www/del_extended/data/career_stats/per_team/
