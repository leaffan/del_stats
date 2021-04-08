#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import json
import yaml
import argparse

from collections import defaultdict

from utils import get_game_info, get_game_type_from_season_type
from reconstruct_skater_situation import build_interval_tree
from reconstruct_skater_situation import GoalieShift

GAME_SRC = 'del_games.json'
SHOT_SRC = 'del_shots.json'
PLR_SRC = 'del_players.json'
LEAGUE_SRC = 'del_league_stats.json'
PLAYER_GAME_STATS_SRC = 'del_player_game_stats.json'

# loading external configuration
CONFIG = yaml.safe_load(open(os.path.join(os.path.dirname(os.path.realpath(__file__)), 'config.yml')))

GOALIE_GAME_STATS_TGT = 'del_goalie_game_stats.json'

SKR_SITUATIONS = ['5v5', '4v4', '3v3', '5v4', '5v3', '4v3', '4v5', '3v5', '3v4']
SHOT_ZONES = ['blue_line', 'left', 'right', 'slot', 'neutral_zone']


def retrieve_goalies_in_game(game):

    interval_tree, _ = build_interval_tree(game)

    goalie_seconds = defaultdict(int)

    for interval in interval_tree:
        if type(interval[-1]) is GoalieShift:
            gs = interval[-1]
            goalie_seconds[(gs.team, gs.player_id)] += (
                abs(interval[0] - interval[1]))

    # retrieving on-going goalie shifts at time of the game-winning goal
    # later used to determine the goalie of record
    intervals_at_gw_goal_time = interval_tree[-game['gw_goal_time']]

    return dict(goalie_seconds), intervals_at_gw_goal_time


def calculate_goals_saved_above_average(goalie_dict, league_data):
    """
    Calculates goals saved above average using previously retrieved league-wide
    save percentage data.
    """
    # calculating goals saved above average
    ga_avg = goalie_dict['shots_against'] * (1 - league_data['save_pctg'])
    goalie_dict['ga_avg'] = round(ga_avg, 3)
    goalie_dict['gsaa'] = round(ga_avg - goalie_dict['goals_against'], 3)
    # calculating 5v5 goals saved above average
    ga_avg_5v5 = goalie_dict['sa_5v5'] * (1 - league_data['save_pctg_5v5'])
    goalie_dict['ga_avg_5v5'] = round(ga_avg_5v5, 3)
    goalie_dict['gsaa_5v5'] = round(ga_avg_5v5 - goalie_dict['ga_5v5'], 3)


def calculate_save_pctg(goalie_dict, type=''):
    if type:
        sa_key = "sa_%s" % type
        ga_key = "ga_%s" % type
        sv_key = ("save_pctg_%s" % type).lower()
    else:
        sa_key = 'shots_against'
        ga_key = 'goals_against'
        sv_key = 'save_pctg'

    if type in ('EV', 'SH', 'PP'):
        shots_against, goals_against = collect_shots_goals_per_situations(
            goalie_dict, type)
    else:
        shots_against = goalie_dict[sa_key]
        goals_against = goalie_dict[ga_key]

    if type and "sa_%s" % type not in goalie_dict:
        goalie_dict["sa_%s" % type.lower()] = shots_against
        goalie_dict["ga_%s" % type.lower()] = goals_against

    if shots_against:
        goalie_dict[sv_key] = round(
            100 - goals_against / shots_against * 100., 3)
    else:
        goalie_dict[sv_key] = None


def collect_shots_goals_per_situations(goalie_dict, situation='EV'):

    shots_against = 0
    goals_against = 0

    if situation == 'EV':
        skr_situations = ['5v5', '4v4', '3v3']
    elif situation == 'SH':
        skr_situations = ['4v5', '3v5', '3v4']
    elif situation == 'PP':
        skr_situations = ['5v4', '5v3', '4v3']

    for skr_situation in skr_situations:
        shots_against += goalie_dict["sa_%s" % skr_situation]
        goals_against += goalie_dict["ga_%s" % skr_situation]

    return shots_against, goals_against


def is_shutout(goalie_dict, goalies_in_game):
    """
    Checks whether current goalie game can be considered a shutout.
    """
    # only goalies that played and didn't concede any goals can have a shutout
    if (goalie_dict['games_played'] and not goalie_dict['goals_against']):
        # if more than two goalies (for both teams) were in the game, we
        # have to check whether goalies shared a game with no goals against
        if len(goalies_in_game) > 2:
            # counting goalies per team
            goalies_per_team_cnt = 0
            for team, _ in goalies_in_game:
                if team == goalie_dict['team']:
                    goalies_per_team_cnt += 1
            # if current team had more than one goalie in the game, this can't
            # be a personal shutout
            if goalies_per_team_cnt > 1:
                return False

        # games lost in overtime or the shootout are no shutouts regardless
        if goalie_dict['sl'] or goalie_dict['ol']:
            return False

        # only games solely played with no goals against throughout regulation,
        # overtime, and shootout are shutouts
        return True

    return False


def get_shootout_stats(goalie_dict, game):
    """
    Retrieves shootout stats for specified game goaltender statistics item.
    """
    game_type = get_game_type_from_season_type(game)
    game_events_src_path = os.path.join(
        CONFIG['base_data_dir'], 'game_events', str(game['season']), str(game_type), "%d.json" % game['game_id'])
    game_events = json.loads(open(game_events_src_path).read())

    if 'shootout' in game_events:
        shootout = game_events['shootout']
    else:
        shootout = list()

    # retrieving shootout attempts directed towards current goalie
    per_goalie_shootout_attempts = list(filter(
        lambda d:
            d['type'] == 'shootout' and
            d['data']['goalkeeper']['playerId'] == goalie_dict['goalie_id'], shootout
    ))

    # retrieving game-winning goal in shootout
    so_winning_goal = list(filter(lambda d: d['type'] == 'goal', shootout))
    if so_winning_goal:
        so_winning_goal = so_winning_goal.pop(0)

    # setting initial values
    if per_goalie_shootout_attempts:
        goalie_dict['so_games_played'] = 1
        goalie_dict['so_attempts_a'] = 0
        goalie_dict['so_goals_a'] = 0
        # not yet sure how to definetely retrieve winning/losing status here
        # since winning goal data gives no indication about the goalie allowing it
        # goalie_dict['so_w'] = 0
        # goalie_dict['so_l'] = 0
    # cumulating shootout statistics
    for attempt in per_goalie_shootout_attempts:
        goalie_dict['so_attempts_a'] += 1
        if attempt['data']['scored']:
            goalie_dict['so_goals_a'] += 1
    # calculating shootout save percentage
    else:
        if 'so_attempts_a' in goalie_dict and goalie_dict['so_attempts_a']:
            goalie_dict['so_sv_pctg'] = round((1 - goalie_dict['so_goals_a'] / goalie_dict['so_attempts_a']) * 100, 2)

    return goalie_dict


if __name__ == '__main__':

    # retrieving arguments specified on command line
    parser = argparse.ArgumentParser(
        description='Download DEL goalie game statistics.')
    parser.add_argument(
        '--initial', dest='initial', required=False,
        action='store_true', help='Re-create list of goalie games')
    parser.add_argument(
        '-s', '--season', dest='season', required=False, default=2020,
        type=int, choices=[2016, 2017, 2018, 2019, 2020],
        metavar='season to process games for',
        help="The season information will be processed for")

    args = parser.parse_args()
    initial = args.initial
    season = args.season

    tgt_dir = os.path.join(CONFIG['tgt_processing_dir'], str(season))

    if not os.path.isdir(tgt_dir):
        os.makedirs(tgt_dir)

    # setting up source and target paths
    src_path = os.path.join(tgt_dir, GAME_SRC)
    shot_src_path = os.path.join(tgt_dir, SHOT_SRC)
    plr_src_path = os.path.join(CONFIG['tgt_processing_dir'], PLR_SRC)
    league_src_path = os.path.join(tgt_dir, LEAGUE_SRC)
    plr_game_stats_src_path = os.path.join(CONFIG['tgt_processing_dir'], str(season), PLAYER_GAME_STATS_SRC)
    tgt_path = os.path.join(tgt_dir, GOALIE_GAME_STATS_TGT)

    # loading games and shots
    games = json.loads(open(src_path).read())
    shots = json.loads(open(shot_src_path).read())
    players = json.loads(open(plr_src_path).read())
    player_game_stats = json.loads(open(plr_game_stats_src_path).read())[-1]
    league_data = json.loads(open(league_src_path).read())

    # loading existing player game stats
    if not initial and os.path.isfile(tgt_path):
        goalies_per_game = json.loads(open(tgt_path).read())
    else:
        goalies_per_game = list()

    # retrieving set of games we already have retrieved player stats for
    registered_games = set([gpg['game_id'] for gpg in goalies_per_game])
    # retrieving player statuses from regular player game stats
    plr_status_dict = dict()
    for plr_game in player_game_stats:
        plr_status_dict[plr_game['player_id']] = plr_game['status']

    for game in games[:]:

        game_shots = list(filter(
            lambda d: d['game_id'] == game['game_id'] and
            d['target_type'] == 'on_goal', shots
        ))

        # skipping already processed games
        if game['game_id'] in registered_games:
            continue

        print("+ Retrieving goalie stats for game %s" % get_game_info(game))

        # retrieving goalies dressed from game item
        goalies_dressed = [
            (game['home_abbr'], game['home_g1'][0] if 'home_g1' in game else None),
            (game['home_abbr'], game['home_g2'][0] if 'home_g2' in game else None),
            (game['home_abbr'], game['home_g3'][0] if 'home_g3' in game else None),
            (game['road_abbr'], game['road_g1'][0] if 'road_g1' in game else None),
            (game['road_abbr'], game['road_g2'][0] if 'road_g2' in game else None),
            (game['road_abbr'], game['road_g3'][0] if 'road_g3' in game else None),
        ]
        goalies_in_game, gw_goal_intervals = retrieve_goalies_in_game(game)

        for goalie_team, goalie_id in goalies_dressed:

            if goalie_id is None:
                continue

            if str(goalie_id) not in players:
                print("=> Goalie with id %d not registered" % goalie_id)
                continue

            goalie_dict = defaultdict(int)

            # retrieving game, team and base goalie information
            goalie_dict['game_id'] = game['game_id']
            # TODO: reactivate when schedule game id is available again
            # goalie_dict['schedule_game_id'] = game['schedule_game_id']
            goalie_dict['game_date'] = game['date']
            goalie_dict['weekday'] = game['weekday']
            goalie_dict['season'] = game['season']
            goalie_dict['season_type'] = game['season_type']
            goalie_dict['round'] = game['round']
            goalie_dict['team'] = goalie_team
            if goalie_dict['team'] == game['home_abbr']:
                goalie_dict['opp_team'] = game['road_abbr']
                goalie_dict['score'] = game['home_score']
                goalie_dict['opp_score'] = game['road_score']
                goalie_dict['home_road'] = 'home'
            else:
                goalie_dict['opp_team'] = game['home_abbr']
                goalie_dict['score'] = game['road_score']
                goalie_dict['opp_score'] = game['home_score']
                goalie_dict['home_road'] = 'road'
            if game['shootout_game']:
                goalie_dict['game_type'] = 'SO'
            elif game['overtime_game']:
                goalie_dict['game_type'] = 'OT'
            else:
                goalie_dict['game_type'] = ''
            goalie_dict['team'] = goalie_team
            goalie_dict['goalie_id'] = goalie_id
            goalie_dict['first_name'] = players[str(goalie_id)]['first_name']
            goalie_dict['last_name'] = players[str(goalie_id)]['last_name']
            goalie_dict['country'] = players[str(goalie_id)]['iso_country']
            # retaining player status from corresponding lookup table
            if goalie_id in plr_status_dict:
                goalie_dict['status'] = plr_status_dict[goalie_id]
            else:
                goalie_dict['status'] = 'fff'

            print("\t+ Retrieving goalie stats for %s %s (%s)" % (
                goalie_dict['first_name'], goalie_dict['last_name'], goalie_team))

            goalie_dict['games_dressed'] += 1
            # checking whether goaltender actually played
            if (goalie_team, goalie_id) in goalies_in_game:
                goalie_dict['games_played'] += 1
            else:
                goalie_dict['games_played'] = 0
            # checking whether goaltender was starting goaltender
            if goalie_id in [game['home_g1'][0], game['road_g1'][0]]:
                goalie_dict['games_started'] += 1
            else:
                goalie_dict['games_started'] = 0
            # # TODO: determine whether to cut processing short right here
            # if not goalie_dict['games_played']:
            #     continue
            if (goalie_team, goalie_id) in goalies_in_game:
                goalie_dict['toi'] = goalies_in_game[(goalie_team, goalie_id)]
            else:
                goalie_dict['toi'] = 0

            goalie_dict['of_record'] = 0

            for interval in gw_goal_intervals:
                gs = interval[-1]
                if gs.team == goalie_team and gs.player_id == goalie_id:
                    goalie_dict['of_record'] += 1
                    break

            for outcome in ['w', 'rw', 'ow', 'sw', 'l', 'rl', 'ol', 'sl']:
                goalie_dict[outcome] = 0

            if goalie_dict['of_record']:
                if game['gw_goal'] == goalie_team:
                    goalie_dict['w'] += 1
                    if game['shootout_game']:
                        goalie_dict['sw'] += 1
                    elif game['overtime_game']:
                        goalie_dict['ow'] += 1
                    else:
                        goalie_dict['rw'] += 1
                else:
                    goalie_dict['l'] += 1
                    if game['shootout_game']:
                        goalie_dict['sl'] += 1
                    elif game['overtime_game']:
                        goalie_dict['ol'] += 1
                    else:
                        goalie_dict['rl'] += 1

            # initializing goalie data dictionary
            goalie_dict['shots_against'] = 0
            goalie_dict['goals_against'] = 0
            for skr_situation in SKR_SITUATIONS:
                goalie_dict["sa_%s" % skr_situation] = 0
            for skr_situation in SKR_SITUATIONS:
                goalie_dict["ga_%s" % skr_situation] = 0
            for shot_zone in SHOT_ZONES:
                goalie_dict["sa_%s" % shot_zone] = 0
            for shot_zone in SHOT_ZONES:
                goalie_dict["ga_%s" % shot_zone] = 0

            for shot in game_shots:
                # skipping shot if not from current game or not on goal
                if (
                    shot['game_id'] != game['game_id'] or
                    shot['target_type'] != 'on_goal'
                ):
                    continue
                # checking whether shot was on current goalie
                if (
                    shot['team_against'] == goalie_team and
                    shot['goalie'] == goalie_id
                ):
                    # counting shots and goals against
                    goalie_dict['shots_against'] += 1
                    goalie_dict["sa_%s" % shot['plr_situation_against']] += 1
                    goalie_dict["sa_%s" % shot['shot_zone'].lower()] += 1
                    if shot['scored']:
                        goalie_dict['goals_against'] += 1
                        goalie_dict["ga_%s" % shot['plr_situation_against']] += 1
                        goalie_dict["ga_%s" % shot['shot_zone'].lower()] += 1
            else:
                # calculating save percentages
                for shot_zone in SHOT_ZONES:
                    calculate_save_pctg(goalie_dict, shot_zone)
                for skr_situation in SKR_SITUATIONS:
                    calculate_save_pctg(goalie_dict, skr_situation)
                calculate_save_pctg(goalie_dict, 'EV')
                calculate_save_pctg(goalie_dict, 'SH')
                calculate_save_pctg(goalie_dict, 'PP')
                calculate_save_pctg(goalie_dict)
                # calculating goals against average
                if goalie_dict['goals_against']:
                    goalie_dict['gaa'] = round(goalie_dict['goals_against'] * 3600 / goalie_dict['toi'], 2)
                else:
                    goalie_dict['gaa'] = 0

            if is_shutout(goalie_dict, goalies_in_game):
                goalie_dict['so'] = 1
            else:
                goalie_dict['so'] = 0

            calculate_goals_saved_above_average(goalie_dict, league_data)

            goalie_dict['game_score'] = round(
                -0.75 * goalie_dict['goals_against'] +
                0.1 * (goalie_dict['shots_against'] - goalie_dict['goals_against']), 2)

            if game['shootout_game']:
                goalie_dict = get_shootout_stats(goalie_dict, game)

            goalies_per_game.append(goalie_dict)

    # dumping collected and calculated data to target file
    tgt_path = os.path.join(tgt_dir, GOALIE_GAME_STATS_TGT)
    open(tgt_path, 'w').write(json.dumps(goalies_per_game, indent=2))
