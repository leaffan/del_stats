#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import json
import yaml
import argparse

from collections import defaultdict
from datetime import datetime

from utils import get_game_info, get_game_type_from_season_type
from utils import name_corrections, coaches

# loading external configuration
CONFIG = yaml.safe_load(open(os.path.join(
    os.path.dirname(os.path.realpath(__file__)), 'config.yml')))

GAME_SRC = 'del_games.json'
SHOT_SRC = 'del_shots.json'
TEAM_GAME_STATS_TGT = 'del_team_game_stats.json'

SHOT_ZONE_CATEGORIES = [
    'slot_shots', 'slot_on_goal', 'slot_missed', 'slot_blocked', 'slot_goals',
    'slot_distance', 'slot_pctg', 'slot_on_goal_pctg',
    'left_shots', 'left_on_goal', 'left_missed', 'left_blocked', 'left_goals',
    'left_distance', 'left_pctg', 'left_on_goal_pctg',
    'right_shots', 'right_on_goal', 'right_missed', 'right_blocked',
    'right_goals', 'right_distance', 'right_pctg', 'right_on_goal_pctg',
    'blue_line_shots', 'blue_line_on_goal', 'blue_line_missed',
    'blue_line_blocked', 'blue_line_goals', 'blue_line_distance',
    'blue_line_pctg', 'blue_line_on_goal_pctg',
    'neutral_zone_shots', 'neutral_zone_on_goal', 'neutral_zone_missed',
    'neutral_zone_blocked', 'neutral_zone_goals', 'neutral_zone_distance',
    'neutral_zone_pctg', 'neutral_zone_on_goal_pctg',
    'behind_goal_shots', 'behind_goal_on_goal', 'behind_goal_missed',
    'behind_goal_blocked', 'behind_goal_goals', 'behind_goal_distance',
    'behind_goal_pctg', 'behind_goal_on_goal_pctg',
]
SHOT_ZONE_ABBREVIATIONS = {
    'slot': 'sl', 'left': 'lf', 'right': 'rg', 'blue_line': 'bl',
    'shots': 'sh', 'on_goal': 'og', 'missed': 'mi', 'blocked': 'bl',
    'goals': 'g', 'distance': 'di', 'pctg': 'p',
}
RAW_STATS_MAPPING = {
    ('shots', 'shotsAttempts'), ('shots_on_goal', 'shotsOnGoal'),
    ('shots_missed', 'shotsMissed'), ('shots_blocked', 'shotsBlocked'),
    ('saves', 'saves'), ('pim', 'penaltyMinutes'),
    ('pp_time', 'powerPlaySeconds'), ('pp_opps', 'ppCount'),
    ('pp_goals', 'ppGoals'), ('sh_opps', 'shCount'), ('sh_goals', 'shGoals'),
}


def get_single_game_team_data(game, grouped_shot_data):
    """
    Retrieves statistics for both teams participating in specified game.
    """
    game_stat_lines = list()
    game_id = game['game_id']
    home_id = game['home_id']
    road_id = game['road_id']
    game_type = get_game_type_from_season_type(game)

    home_stats_src_path = os.path.join(
        CONFIG['base_data_dir'], 'game_team_stats',
        str(game['season']), str(game_type), "%d_%d.json" % (game_id, home_id))
    road_stats_src_path = os.path.join(
        CONFIG['base_data_dir'], 'game_team_stats',
        str(game['season']), str(game_type), "%d_%d.json" % (game_id, road_id))

    # loading raw team game stats (if available)
    raw_stats = dict()
    if os.path.isfile(home_stats_src_path):
        raw_stats['home'] = json.loads(open(home_stats_src_path).read())
    else:
        raw_stats['home'] = dict()
    if os.path.isfile(road_stats_src_path):
        raw_stats['road'] = json.loads(open(road_stats_src_path).read())
    else:
        raw_stats['road'] = dict()

    # counting penalties per team
    penalty_counts = get_penalty_counts(game)

    for key in ['home', 'road']:
        opp_key = 'road' if key == 'home' else 'home'
        game_stat_line = dict()
        # basic game information
        game_stat_line['game_date'] = game['date']
        game_stat_line['season'] = game['season']
        game_stat_line['season_type'] = game['season_type']
        game_stat_line['round'] = game['round']
        game_stat_line['game_id'] = game_id
        # TODO: reactivate when schedule game id is available again
        # game_stat_line['schedule_game_id'] = game['schedule_game_id']
        game_stat_line['arena'] = correct_name(game['arena'])
        game_stat_line['attendance'] = game['attendance']
        # coaches and referees
        if "%s_coach" % key in game:
            game_stat_line['coach'] = correct_name(game["%s_coach" % key])
            if game_stat_line['coach'] not in coaches:
                print("+ Unknown coach '%s'" % game_stat_line['coach'])
        else:
            game_stat_line['coach'] = None
        if "%s_coach" % opp_key in game:
            game_stat_line['opp_coach'] = correct_name(
                game["%s_coach" % opp_key])
            if game_stat_line['opp_coach'] not in coaches:
                print("+ Unknown coach '%s'" % game_stat_line['opp_coach'])
        else:
            game_stat_line['opp_coach'] = None
        game_stat_line['ref_1'] = correct_name(game['referee_1'])
        game_stat_line['ref_2'] = correct_name(game['referee_2'])
        game_stat_line['lma_1'] = correct_name(game['linesman_1'])
        game_stat_line['lma_2'] = correct_name(game['linesman_2'])
        # outcomes
        game_stat_line['games_played'] = 1
        game_stat_line['home_road'] = key
        game_stat_line['team_id'] = game["%s_id" % key]
        game_stat_line['team'] = game["%s_abbr" % key]
        game_stat_line['score'] = game["%s_score" % key]
        game_stat_line['goals'] = game["%s_score" % key]
        game_stat_line['opp_team_id'] = game["%s_id" % opp_key]
        game_stat_line['opp_team'] = game["%s_abbr" % opp_key]
        game_stat_line['opp_score'] = game["%s_score" % opp_key]
        game_stat_line['opp_goals'] = game["%s_score" % opp_key]
        if game['shootout_game']:
            game_stat_line['game_type'] = 'SO'
        elif game['overtime_game']:
            game_stat_line['game_type'] = 'OT'
        else:
            game_stat_line['game_type'] = ''
        for gsl_key in ['w', 'rw', 'ow', 'sw', 'l', 'rl', 'ol', 'sl']:
            game_stat_line[gsl_key] = 0
        if game_stat_line['score'] > game_stat_line['opp_score']:
            game_stat_line['w'] += 1
            if game['shootout_game']:
                game_stat_line['sw'] += 1
                game_stat_line['goals'] -= 1
            elif game['overtime_game']:
                game_stat_line['ow'] += 1
            else:
                game_stat_line['rw'] += 1
        else:
            game_stat_line['l'] += 1
            if game['shootout_game']:
                game_stat_line['sl'] += 1
                game_stat_line['opp_goals'] -= 1
            elif game['overtime_game']:
                game_stat_line['ol'] += 1
            else:
                game_stat_line['rl'] += 1
        game_stat_line['points'] = (
            game_stat_line['rw'] * 3 + game_stat_line['ow'] * 2 +
            game_stat_line['sw'] * 2 + game_stat_line['sl'] * 1 +
            game_stat_line['ol'] * 1)
        # per-period goals
        for period in [1, 2, 3]:
            game_stat_line["goals_%d" % period] = game[
                "%s_goals_%d" % (key, period)]
            game_stat_line["opp_goals_%d" % period] = game[
                "%s_goals_%d" % (opp_key, period)]
        # empty-net and extra-attacker goals
        game_stat_line['en_goals'] = game["%s_en_goals" % key]
        game_stat_line['ea_goals'] = game["%s_ea_goals" % key]
        game_stat_line['opp_en_goals'] = game["%s_en_goals" % opp_key]
        game_stat_line['opp_ea_goals'] = game["%s_ea_goals" % opp_key]
        # situation after 20 and 40 minutes respectively
        for situation in [
            'tied20', 'lead20', 'trail20', 'tied40', 'lead40', 'trail40'
        ]:
            game_stat_line[situation] = False
        if game_stat_line['goals_1'] == game_stat_line['opp_goals_1']:
            game_stat_line['tied20'] = True
        elif game_stat_line['goals_1'] > game_stat_line['opp_goals_1']:
            game_stat_line['lead20'] = True
        else:
            game_stat_line['trail20'] = True
        goals40 = game_stat_line['goals_1'] + game_stat_line['goals_2']
        opp_goals40 = (
            game_stat_line['opp_goals_1'] + game_stat_line['opp_goals_2'])
        if goals40 == opp_goals40:
            game_stat_line['tied40'] = True
        elif goals40 > opp_goals40:
            game_stat_line['lead40'] = True
        else:
            game_stat_line['trail40'] = True
        # scored first?
        if game['first_goal'] == game_stat_line['team']:
            game_stat_line['scored_first'] = True
            game_stat_line['trailed_first'] = False
        elif game['first_goal'] == game_stat_line['opp_team']:
            game_stat_line['scored_first'] = False
            game_stat_line['trailed_first'] = True
        # one-goal, two-goal, three-goal, four-goal-game?
        for goal_game in ['one_goal', 'two_goal', 'three_goal', 'four_goal']:
            game_stat_line[goal_game] = False
        score_diff = abs(
            (game_stat_line['score'] - game_stat_line['en_goals']) -
            (game_stat_line['opp_score'] - game_stat_line['opp_en_goals']))
        # in case the right amount of empty-net goals have been scored, we
        # may end up with a score differential of zero, see game between STR
        # and ING on Mar 3, 2019
        if not score_diff:
            game_stat_line['zero_goal'] = True
        if score_diff == 1:
            game_stat_line['one_goal'] = True
        elif score_diff == 2:
            game_stat_line['two_goal'] = True
        elif score_diff == 3:
            game_stat_line['three_goal'] = True
        elif score_diff > 3:
            game_stat_line['four_goal'] = True

        # retrieving raw stats for team and opposing team
        for category, raw_category in RAW_STATS_MAPPING:
            game_stat_line[category] = raw_stats[key].get(raw_category, None)
            game_stat_line["opp_%s" % category] = raw_stats[opp_key].get(
                raw_category, None)
        # calculating shooting percentages
        if game_stat_line['shots_on_goal']:
            game_stat_line['shot_pctg'] = round(
                game_stat_line['goals'] /
                game_stat_line['shots_on_goal'] * 100., 2)
        else:
            game_stat_line['shot_pctg'] = None
        if game_stat_line['opp_shots_on_goal']:
            game_stat_line['opp_shot_pctg'] = round(
                game_stat_line['opp_goals'] /
                game_stat_line['opp_shots_on_goal'] * 100., 2)
        else:
            game_stat_line['opp_shot_pctg'] = None
        # calculating save percentages
        if game_stat_line['opp_shots_on_goal']:
            game_stat_line['save_pctg'] = round(
                100 - game_stat_line['opp_goals'] /
                game_stat_line['opp_shots_on_goal'] * 100., 2)
        else:
            game_stat_line['save_pctg'] = None
        if game_stat_line['shots_on_goal']:
            game_stat_line['opp_save_pctg'] = round(
                100 - game_stat_line['goals'] /
                game_stat_line['shots_on_goal'] * 100., 2)
        else:
            game_stat_line['opp_save_pctg'] = None
        # calculating pdo values
        if all([game_stat_line['shot_pctg'], game_stat_line['save_pctg']]):
            game_stat_line['pdo'] = round((
                game_stat_line['shot_pctg'] +
                game_stat_line['save_pctg']), 1)
            game_stat_line['opp_pdo'] = round((
                game_stat_line['opp_shot_pctg'] +
                game_stat_line['opp_save_pctg']), 1)
        # calculating power play percentages
        if game_stat_line['pp_opps']:
            game_stat_line['pp_pctg'] = round((
                game_stat_line['pp_goals'] /
                game_stat_line['pp_opps']) * 100., 1)
        else:
            game_stat_line['pp_pctg'] = 0
        if game_stat_line['opp_pp_opps']:
            game_stat_line['opp_pp_pctg'] = round((
                game_stat_line['opp_pp_goals'] /
                game_stat_line['opp_pp_opps']) * 100., 1)
        else:
            game_stat_line['opp_pp_pctg'] = 0
        # calculating penalty killing percentages
        if game_stat_line['sh_opps']:
            game_stat_line['pk_pctg'] = round(
                100 - game_stat_line['opp_pp_goals'] /
                game_stat_line['sh_opps'] * 100., 1)
        else:
            game_stat_line['pk_pctg'] = 0
        if game_stat_line['opp_sh_opps']:
            game_stat_line['opp_pk_pctg'] = round(
                100 - game_stat_line['pp_goals'] /
                game_stat_line['opp_sh_opps'] * 100., 1)
        else:
            game_stat_line['opp_pk_pctg'] = 0
        game_stat_line['ev_goals'] = (
            game_stat_line['goals'] -
            game_stat_line['pp_goals'] -
            game_stat_line['sh_goals'])
        game_stat_line['opp_ev_goals'] = (
            game_stat_line['opp_goals'] -
            game_stat_line['opp_pp_goals'] -
            game_stat_line['opp_sh_goals'])
        # faceoffs are treated separately since each of the team game stats
        # datasets only contains the number of won faceoffs and sometimes this
        # one is stored as a string (wtf?)
        game_stat_line['faceoffs_won'] = int(
            raw_stats[key].get('faceOffsWon', 0))
        game_stat_line['faceoffs_lost'] = int(
            raw_stats[opp_key].get('faceOffsWon', 0))
        # calculating overall number of faceoffs and faceoff percentage
        game_stat_line['faceoffs'] = (
            game_stat_line['faceoffs_won'] + game_stat_line['faceoffs_lost'])
        if game_stat_line['faceoffs']:
            game_stat_line['faceoff_pctg'] = round(
                game_stat_line['faceoffs_won'] /
                game_stat_line['faceoffs'] * 100., 1)
        else:
            game_stat_line['faceoff_pctg'] = 0.
        # best players
        game_stat_line['best_plr_id'] = game.get(
            "%s_best_player_id" % key, None)
        game_stat_line['best_plr'] = game.get("%s_best_player" % key, None)
        game_stat_line['opp_best_plr_id'] = game.get(
            "%s_best_player_id" % opp_key, None)
        game_stat_line['opp_best_plr'] = game.get(
            "%s_best_player" % opp_key, None)
        # game-winning-goal
        game_stat_line['gw_goal_team'] = game['gw_goal']
        game_stat_line['gw_goal_player_id'] = game['gw_goal_player_id']
        game_stat_line['gw_goal_first_name'] = game['gw_goal_first_name']
        game_stat_line['gw_goal_last_name'] = game['gw_goal_last_name']

        shot_zones_to_retain = ['slot', 'left', 'right', 'blue_line']
        # TODO: rename items
        shot_situations_to_retain = [
            'shots_ev', 'shots_oo', 'shots_sh', 'shots_unblocked',
            'shots_unblocked_ev', 'shots_unblocked_pp', 'shots_unblocked_sh',
            'shots_on_goal_ev', 'shots_on_goal_pp', 'shots_on_goal_sh']

        # retrieving shot data for current game and team
        shot_data = grouped_shot_data.get(
            (game_id, game_stat_line['team']), list())
        for item in shot_data:
            if item.startswith(tuple(shot_zones_to_retain)):
                abbr_item = item
                for zone_key, replacement in SHOT_ZONE_ABBREVIATIONS.items():
                    abbr_item = abbr_item.replace(zone_key, replacement)
                game_stat_line[abbr_item] = shot_data[item]
            elif item in shot_situations_to_retain:
                game_stat_line[item] = shot_data[item]

        # retrieving shots against data for current game and team
        shot_against_data = grouped_shot_data.get(
            (game_id, game_stat_line['opp_team']), list())
        for item in shot_against_data:
            if item.startswith(tuple(shot_zones_to_retain)):
                abbr_item = item
                for zone_key, replacement in SHOT_ZONE_ABBREVIATIONS.items():
                    abbr_item = abbr_item.replace(zone_key, replacement)
                game_stat_line["%s_a" % abbr_item] = shot_against_data[item]
            elif item in shot_situations_to_retain:
                game_stat_line["opp_%s" % item] = shot_against_data[item]

        game_stat_line['ev_cf_pctg'] = round(
            game_stat_line['shots_ev'] / (
                game_stat_line['shots_ev'] + game_stat_line['opp_shots_ev']
            ) * 100, 2)

        for penalty_duration in [2, 5, 10, 20]:
            if penalty_counts[key] and penalty_duration in penalty_counts[key]:
                game_stat_line["penalty_%d" % penalty_duration] = (
                    penalty_counts[key][penalty_duration])
            else:
                game_stat_line["penalty_%d" % penalty_duration] = 0

        game_stat_lines.append(game_stat_line)

    return game_stat_lines


def group_shot_data_by_game_team(shots):
    """
    Groups shot data by game and team using the globally defined shot zones
    and target types.
    """
    grouped_shot_data = dict()

    # definining zones
    zones = [
        'slot', 'left', 'right', 'blue_line', 'neutral_zone', 'behind_goal']

    for shot in shots[:]:
        game_team_key = (shot['game_id'], shot['team'])
        if game_team_key not in grouped_shot_data:
            grouped_shot_data[game_team_key] = dict()
            for shot_zone_cat in SHOT_ZONE_CATEGORIES:
                grouped_shot_data[game_team_key][shot_zone_cat] = 0
                if 'distance' in shot_zone_cat:
                    grouped_shot_data[game_team_key][shot_zone_cat] = list()
        # retrieving shot zone, e.g. *slot*, *left*
        zone = shot['shot_zone'].lower()
        # retrieving combined shot zone and outcome used as key below, e.g.
        # *slot_missed*, *left_blocked*, *blue_line_on_goal*
        zone_tgt_type = "%s_%s" % (zone, shot['target_type'])
        # retrieving combined shot zone and distance used as key below, e.g.
        # *right_distance*
        zone_distance = "%s_distance" % zone
        # adding shot incident to counter for shot zone
        grouped_shot_data[game_team_key]["%s_shots" % zone] += 1
        # adding shot incident to counter for shot zone/outcome
        grouped_shot_data[game_team_key][zone_tgt_type] += 1
        # adding distance of shot incident
        grouped_shot_data[game_team_key][zone_distance].append(
            shot['distance'])
        # in case of a goal, adding shot incident to couter for goals
        # from shot zone
        if shot['scored']:
            grouped_shot_data[game_team_key]["%s_goals" % zone] += 1

    # finally calculating percentages and mean distances for shot incidents
    # from each zone
    for key in grouped_shot_data:
        all_shots = 0
        all_on_goal = 0
        for zone in zones:
            # adding shots from current zone to number of shots from all zones
            all_shots += grouped_shot_data[key]["%s_shots" % zone]
            # adding shots on goal from current zone to number of shots on goal
            # from all zones
            all_on_goal += grouped_shot_data[key]["%s_on_goal" % zone]
            # calculating mean distance of shots from the current zone (if
            # applicable)
            if grouped_shot_data[key]["%s_shots" % zone]:
                grouped_shot_data[key]["%s_distance" % zone] = round(
                    sum(grouped_shot_data[key]["%s_distance" % zone]) /
                    grouped_shot_data[key]["%s_shots" % zone], 2
                )
            else:
                grouped_shot_data[key]["%s_distance" % zone] = 0

        # calculating percentage of shots and shots on goal for each shot zone
        for zone in zones:
            grouped_shot_data[key]["%s_pctg" % zone] = round((
                grouped_shot_data[key]["%s_shots" % zone] / all_shots
            ) * 100., 2)
            grouped_shot_data[key]["%s_on_goal_pctg" % zone] = round((
                grouped_shot_data[key]["%s_on_goal" % zone] / all_on_goal
            ) * 100., 2)

    for key in grouped_shot_data:
        game_id, team = key
        per_team_game_shots = list(filter(
            lambda d:
            d['game_id'] == game_id and
            d['team'] == team, shots))
        grouped_shot_data[key]['shots'] = len(per_team_game_shots)
        per_team_game_ev_shots = list(filter(
            lambda d: d['situation'] == 'EV', per_team_game_shots))
        grouped_shot_data[key]['shots_ev'] = len(per_team_game_ev_shots)
        per_team_game_pp_shots = list(filter(
            lambda d: d['situation'] == 'PP', per_team_game_shots))
        grouped_shot_data[key]['shots_pp'] = len(per_team_game_pp_shots)
        per_team_game_sh_shots = list(filter(
            lambda d: d['situation'] == 'SH', per_team_game_shots))
        grouped_shot_data[key]['shots_sh'] = len(per_team_game_sh_shots)
        per_team_game_unblocked_shots = list(filter(
            lambda d: d['target_type'] in ['on_goal', 'missed'],
            per_team_game_shots))
        grouped_shot_data[key]['shots_unblocked'] = len(
            per_team_game_unblocked_shots)
        per_team_game_unblocked_ev_shots = list(filter(
            lambda d: d['situation'] == 'EV', per_team_game_unblocked_shots))
        grouped_shot_data[key]['shots_unblocked_ev'] = len(
            per_team_game_unblocked_ev_shots)
        per_team_game_unblocked_pp_shots = list(filter(
            lambda d: d['situation'] == 'PP', per_team_game_unblocked_shots))
        grouped_shot_data[key]['shots_unblocked_pp'] = len(
            per_team_game_unblocked_pp_shots)
        per_team_game_unblocked_sh_shots = list(filter(
            lambda d: d['situation'] == 'SH', per_team_game_unblocked_shots))
        grouped_shot_data[key]['shots_unblocked_sh'] = len(
            per_team_game_unblocked_sh_shots)
        per_team_game_shots_on_goal = list(filter(
            lambda d: d['target_type'] == 'on_goal', per_team_game_shots))
        grouped_shot_data[key]['shots_on_goal'] = len(
            per_team_game_shots_on_goal)
        per_team_game_ev_shots_on_goal = list(filter(
            lambda d: d['situation'] == 'EV', per_team_game_shots_on_goal))
        grouped_shot_data[key]['shots_on_goal_ev'] = len(
            per_team_game_ev_shots_on_goal)
        per_team_game_pp_shots_on_goal = list(filter(
            lambda d: d['situation'] == 'PP', per_team_game_shots_on_goal))
        grouped_shot_data[key]['shots_on_goal_pp'] = len(
            per_team_game_pp_shots_on_goal)
        per_team_game_sh_shots_on_goal = list(filter(
            lambda d: d['situation'] == 'SH', per_team_game_shots_on_goal))
        grouped_shot_data[key]['shots_on_goal_sh'] = len(
            per_team_game_sh_shots_on_goal)

    return grouped_shot_data


def correct_name(name, corrections=name_corrections):
    for delimiter in [',', ';']:
        if delimiter in name:
            name = " ".join(
                [token.strip() for token in name.split(delimiter)][::-1])
    if name.upper() == name:
        name = name.title()
    if name in name_corrections:
        name = name_corrections[name]
    return name


def get_penalty_counts(game):
    """
    Get penalty counts for specified home or road team, i.e. how many two-,
    five-, ten-, and twenty-minute penalties have been accumulated by its
    players.
    """
    game_type = get_game_type_from_season_type(game)

    pen_counts = dict()
    pen_counts['home'] = defaultdict(int)
    pen_counts['road'] = defaultdict(int)

    game_events_src_path = os.path.join(
        CONFIG['base_data_dir'], 'game_events',
        str(game['season']), str(game_type), "%d.json" % game['game_id'])
    events_data = json.loads(open(game_events_src_path).read())

    for period in events_data:
        for event in events_data[period]:
            if event['type'] == 'penalty':
                duration = int(event['data']['duration'] / 60)
                if event['data']['team'] == 'home':
                    pen_counts['home'][duration] += 1
                else:
                    pen_counts['road'][duration] += 1

    return pen_counts


if __name__ == '__main__':

    # retrieving arguments specified on command line
    parser = argparse.ArgumentParser(
        description='Process DEL team game statistics.')
    parser.add_argument(
        '--initial', dest='initial', required=False,
        action='store_true', help='Re-create list of team games')
    parser.add_argument(
        '--limit', dest='limit', required=False, type=int, default=0,
        help='Number of maximum games to be processed')
    parser.add_argument(
        '-s', '--season', dest='season', required=False, default=2019,
        type=int, choices=[2016, 2017, 2018, 2019],
        metavar='season to process games for',
        help="The season information will be processed for")

    args = parser.parse_args()

    initial = args.initial
    limit = args.limit
    season = args.season

    tgt_dir = os.path.join(CONFIG['tgt_processing_dir'], str(season))

    if not os.path.isdir(tgt_dir):
        os.makedirs(tgt_dir)

    # setting up source and target paths
    src_path = os.path.join(tgt_dir, GAME_SRC)
    shots_src_path = os.path.join(tgt_dir, SHOT_SRC)
    tgt_path = os.path.join(tgt_dir, TEAM_GAME_STATS_TGT)

    # loading games and shots
    games = json.loads(open(src_path).read())
    shots = json.loads(open(shots_src_path).read())
    # grouping shot data by game and team
    grouped_shot_data = group_shot_data_by_game_team(shots)

    # loading existing player game stats
    if not initial and os.path.isfile(tgt_path):
        team_game_stats = json.loads(open(tgt_path).read())[-1]
    else:
        team_game_stats = list()

    # retrieving set of games we already have retrieved player stats for
    registered_games = set([pg['game_id'] for pg in team_game_stats])

    cnt = 0
    for game in games[:]:
        cnt += 1
        # skipping already processed games
        if game['game_id'] in registered_games:
            continue
        print("+ Retrieving team stats for game %s" % get_game_info(game))
        single_team_game_stats = get_single_game_team_data(
            game, grouped_shot_data)
        team_game_stats.extend(single_team_game_stats)

        if limit and cnt >= limit:
            break

    # retrieving current timestamp to indicate last modification of dataset
    current_datetime = datetime.now().timestamp() * 1000
    output = [current_datetime, team_game_stats]

    open(tgt_path, 'w').write(json.dumps(output, indent=2, default=str))
