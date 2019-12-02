#!/bin/bash

date=$(date '+%Y-%m-%d')
season=$1

python3 /home/pacs/mre00/users/markus/_del/download_team_data.py -s $season -g RS schedules
python3 /home/pacs/mre00/users/markus/_del/download_team_data.py -s $season -g RS roster_stats
python3 /home/pacs/mre00/users/markus/_del/download_team_data.py -s $season -g RS team_stats
python3 /home/pacs/mre00/users/markus/_del/get_all_players.py
python3 /home/pacs/mre00/users/markus/_del/order_schedules.py -s $season
python3 /home/pacs/mre00/users/markus/_del/download_game_data.py -s $season -g RS game_info
python3 /home/pacs/mre00/users/markus/_del/download_game_data.py -s $season -g RS game_events
python3 /home/pacs/mre00/users/markus/_del/download_game_data.py -s $season -g RS game_roster
python3 /home/pacs/mre00/users/markus/_del/download_game_data.py -s $season -g RS game_team_stats
python3 /home/pacs/mre00/users/markus/_del/download_game_data.py -s $season -g RS game_player_stats
python3 /home/pacs/mre00/users/markus/_del/download_game_data.py -s $season -g RS game_goalies
python3 /home/pacs/mre00/users/markus/_del/download_game_data.py -s $season -g RS shifts
python3 /home/pacs/mre00/users/markus/_del/download_game_data.py -s $season -g RS shots

python3 /home/pacs/mre00/users/markus/_del/download_career_data.py

python3 /home/pacs/mre00/users/markus/_del/get_del_games.py -s 2019 --initial -f "Sep 13, 2019" -t "$date"
python3 /home/pacs/mre00/users/markus/_del/get_shots.py -s 2019 --initial
python3 /home/pacs/mre00/users/markus/_del/get_del_team_game_stats.py -s 2019 --initial
python3 /home/pacs/mre00/users/markus/_del/get_del_player_game_stats.py -s 2019 --initial
python3 /home/pacs/mre00/users/markus/_del/get_del_goalie_stats.py -s 2019 --initial
python3 /home/pacs/mre00/users/markus/_del/aggregate_del_player_game_stats.py -s 2019
python3 /home/pacs/mre00/users/markus/_del/get_streaks.py -s 2019
python3 /home/pacs/mre00/users/markus/_del/update_coaches.py
python3 /home/pacs/mre00/users/markus/_del/update_h2h_records.py

python3 /home/pacs/mre00/users/markus/_del/add_career_stats_to_rosters.py

cp -v /home/pacs/mre00/users/markus/_del/_data/del_players.json /home/doms/leaffan.net/subs/www/del/data/del_players.json
cp -v /home/pacs/mre00/users/markus/_del/_data/2019/del_goalie_game_stats.json /home/doms/leaffan.net/subs/www/del/data/2019
cp -v /home/pacs/mre00/users/markus/_del/_data/2019/del_player_game_stats_aggregated.* /home/doms/leaffan.net/subs/www/del/data/2019
cp -v /home/pacs/mre00/users/markus/_del/_data/2019/del_team_game_stats.json /home/doms/leaffan.net/subs/www/del/data/2019
cp -v /home/pacs/mre00/users/markus/_del/_data/2019/del_streaks.json /home/doms/leaffan.net/subs/www/del/data/2019
cp -TRv /home/pacs/mre00/users/markus/_del/_data/2019/per_player/ /home/doms/leaffan.net/subs/www/del/data/2019/per_player/

cp -v /home/pacs/mre00/users/markus/_del/_dlds/career_stats/career_stats.json /home/doms/leaffan.net/subs/www/del/data/career_stats
cp -TRv /home/pacs/mre00/users/markus/_del/_dlds/career_stats/per_player/ /home/doms/leaffan.net/subs/www/del/data/career_stats/per_player/
cp -TRv /home/pacs/mre00/users/markus/_del/_data/career_stats/per_team/ /home/doms/leaffan.net/subs/www/del/data/career_stats/per_team/

cp -v /home/pacs/mre00/users/markus/_del/_data/del_players.json /home/doms/leaffan.net/subs/www/del_extended/data/del_players.json
cp -v /home/pacs/mre00/users/markus/_del/_data/2019/coaches.json /home/doms/leaffan.net/subs/www/del_extended/data/2019
cp -v /home/pacs/mre00/users/markus/_del/_data/2019/full_schedule.json /home/doms/leaffan.net/subs/www/del_extended/data/2019
cp -v /home/pacs/mre00/users/markus/_del/_data/2019/del_goalie_game_stats.json /home/doms/leaffan.net/subs/www/del_extended/data/2019
cp -v /home/pacs/mre00/users/markus/_del/_data/2019/del_goalie_game_stats_aggregated.json /home/doms/leaffan.net/subs/www/del_extended/data/2019
cp -v /home/pacs/mre00/users/markus/_del/_data/2019/del_player_game_stats_aggregated.* /home/doms/leaffan.net/subs/www/del_extended/data/2019
cp -v /home/pacs/mre00/users/markus/_del/_data/2019/del_team_game_stats.json /home/doms/leaffan.net/subs/www/del_extended/data/2019
cp -v /home/pacs/mre00/users/markus/_del/_data/2019/del_streaks.json /home/doms/leaffan.net/subs/www/del_extended/data/2019
cp -TRv /home/pacs/mre00/users/markus/_del/_data/2019/per_player/ /home/doms/leaffan.net/subs/www/del_extended/data/2019/per_player/

cp -v /home/pacs/mre00/users/markus/_del/_dlds/career_stats/career_stats.json /home/doms/leaffan.net/subs/www/del_extended/data/career_stats
cp -TRv /home/pacs/mre00/users/markus/_del/_dlds/career_stats/per_player/ /home/doms/leaffan.net/subs/www/del_extended/data/career_stats/per_player/
cp -TRv /home/pacs/mre00/users/markus/_del/_data/career_stats/per_team/ /home/doms/leaffan.net/subs/www/del_extended/data/career_stats/per_team/


