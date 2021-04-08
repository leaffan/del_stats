#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import json
import yaml
import datetime
import argparse

from collections import defaultdict

from dateutil.parser import parse
from dateutil.rrule import rrule, DAILY
from dateutil.relativedelta import relativedelta

from utils import get_season, get_team_from_game

# loading external configuration
CONFIG = yaml.safe_load(open(os.path.join(
    os.path.dirname(os.path.realpath(__file__)), 'config.yml')))

# TODO: decide whether to put the following stuff into external configuration
PLAYOFF_DATES = {
    2016: datetime.date(2017, 2, 28),
    2017: datetime.date(2018, 3, 6),
    2018: datetime.date(2019, 3, 5),
    2019: datetime.date(2020, 3, 9),
    2020: datetime.date(2021, 4, 19),
}

POS_KEYS = {'1': 'G', '2': 'D', '3': 'F'}

TGT_DIR = CONFIG['tgt_processing_dir']
TGT_FILE = "del_games.json"


def get_games_for_date(date, existing_games=None):
    '''
    Gets detail, event, and roster information for all games played on the
    specified date. Optionally adds found game information to specified list
    of existing games.
    '''
    print("+ Retrieving games played on %s" % date)

    # loading games that may have been registered earlier
    if not existing_games:
        games = list()
    else:
        games = existing_games
    # collecting already registered game ids
    registered_game_ids = [g['game_id'] for g in games]

    # retrieving full league schedule for current season
    schedules_src_path = os.path.join(
        CONFIG['tgt_processing_dir'],
        str(get_season(date)), 'full_schedule.json')
    schedules = json.loads(open(schedules_src_path).read())

    game_ids_rounds = list()

    # determining ids and rounds of games played on current date
    for schedule in schedules:
        try:
            start_date = parse(schedule['start_date']).date()
        except ValueError:
            # TODO: think of something more clever than iterating over all
            # fixtures each day
            # print("+ Unable to parse game start date %s" % schedule[
            #     'start_date'])
            continue
        # comparing start date of game with current date
        if start_date == game_date and schedule['status'] in ['AFTER_MATCH', 'CONTUMACY']:
            game_ids_rounds.append(
                (schedule['game_id'], int(schedule['round'].split('_')[-1])))

    for game_id, round in game_ids_rounds:
        if game_id in registered_game_ids:
            print("\t+ Game with id %d already registered" % game_id)
            continue
        # setting up data container
        single_game_data = dict()
        # setting game date and round information
        single_game_data['date'] = date
        single_game_data['weekday'] = date.weekday()
        season = get_season(date)
        single_game_data['season'] = season
        # TODO: put date for 2020/21 regular season start somewhere else
        if season == 2020 and date < datetime.date(2020, 12, 16):
            single_game_data['season_type'] = 'MSC'
            game_type = 4
        elif date < PLAYOFF_DATES[season]:
            single_game_data['season_type'] = 'RS'
            game_type = 1
        elif date >= PLAYOFF_DATES[season]:
            single_game_data['season_type'] = 'PO'
            game_type = 3
        single_game_data['round'] = round

        # setting game ids
        # TODO: determine schedule game id
        # single_game_data['schedule_game_id'] = schedule_game_id
        single_game_data['game_id'] = game_id

        # retrieving game details
        if 'game_id' in single_game_data:
            try:
                single_game_details = get_single_game_details(
                    game_id, season, game_type)
            except Exception:
                import traceback
                traceback.print_exc()
                print(game_id)
                continue

        # retrieving game rosters
        single_game_rosters = get_game_rosters(game_id, season, game_type)
        # retrieving game events
        single_game_events = get_game_events(game_id, season, game_type)

        single_game_data = {
            **single_game_data, **single_game_details,
            **single_game_rosters, **single_game_events
        }

        single_game_data['first_goal'] = get_team_from_game(
            single_game_data, single_game_data['first_goal'])
        single_game_data['gw_goal'] = get_team_from_game(
            single_game_data, single_game_data['gw_goal'])

        print("\t+ %s (%d) vs. %s (%d)" % (
            single_game_data['home_team'], single_game_data['home_score'],
            single_game_data['road_team'], single_game_data['road_score']
        ))

        games.append(single_game_data)

    return games


def get_single_game_details(game_id, season, game_type):
    """
    Gets game details for a single game with the specified id.
    """
    game_detail_src_path = os.path.join(
        CONFIG['base_data_dir'], 'game_info',
        str(season), str(game_type), "%d.json" % game_id)
    game_details = json.loads(open(game_detail_src_path).read())

    single_game_data = dict()

    single_game_data['arena'] = game_details['stadium']
    # quick fix for wrongly registered arena in 2020 MagentaSport Cup
    if season == 2020 and game_type == 4 and single_game_data['arena'] == 'Mercedes-Benz Arena':
        single_game_data['arena'] = 'Sportforum Berlin'
    single_game_data['attendance'] = game_details['numberOfViewers']

    single_game_data['home_id'] = game_details['teamInfo']['home']['id']
    single_game_data['home_team'] = game_details['teamInfo']['home']['name']
    single_game_data['home_abbr'] = game_details[
        'teamInfo']['home']['shortcut']
    if game_details['trainers']:
        if 'homeHeadCoach' in game_details['trainers']:
            if type(game_details['trainers']['homeHeadCoach']) is str:
                single_game_data['home_coach'] = game_details[
                    'trainers']['homeHeadCoach']
            else:
                single_game_data['home_coach_id'] = game_details[
                    'trainers']['homeHeadCoach']['id']
                single_game_data['home_coach'] = game_details[
                    'trainers']['homeHeadCoach']['name']
    single_game_data['road_id'] = game_details['teamInfo']['visitor']['id']
    single_game_data['road_team'] = game_details['teamInfo']['visitor']['name']
    single_game_data['road_abbr'] = game_details[
        'teamInfo']['visitor']['shortcut']
    if game_details['trainers']:
        if 'visitorHeadCoach' in game_details['trainers']:
            if type(game_details['trainers']['visitorHeadCoach']) is str:
                single_game_data['road_coach'] = game_details[
                    'trainers']['visitorHeadCoach']
            else:
                single_game_data['road_coach_id'] = game_details[
                    'trainers']['visitorHeadCoach']['id']
                single_game_data['road_coach'] = game_details[
                    'trainers']['visitorHeadCoach']['name']

    single_game_data['home_score'] = game_details[
        'results']['score']['final']['score_home']
    single_game_data['road_score'] = game_details[
        'results']['score']['final']['score_guest']

    single_game_data['home_goals_1'] = game_details[
        'results']['score']['first_period']['score_home']
    single_game_data['road_goals_1'] = game_details[
        'results']['score']['first_period']['score_guest']
    single_game_data['home_goals_2'] = game_details[
        'results']['score']['second_period']['score_home']
    single_game_data['road_goals_2'] = game_details[
        'results']['score']['second_period']['score_guest']
    single_game_data['home_goals_3'] = game_details[
        'results']['score']['third_period']['score_home']
    single_game_data['road_goals_3'] = game_details[
        'results']['score']['third_period']['score_guest']

    single_game_data['overtime_game'] = False
    single_game_data['shootout_game'] = False

    if (sum([
        single_game_data['home_goals_1'],
        single_game_data['home_goals_2'],
        single_game_data['home_goals_3']
    ]) != single_game_data['home_score']) or (sum([
        single_game_data['road_goals_1'],
        single_game_data['road_goals_2'],
        single_game_data['road_goals_3']
    ]) != single_game_data['road_score']):
        if game_details['results']['extra_time']:
            single_game_data['overtime_game'] = True
        if game_details['results']['shooting']:
            single_game_data['shootout_game'] = True

    if type(game_details['referees']['headReferee1']) is str:
        single_game_data['referee_1'] = game_details[
            'referees']['headReferee1']
    else:
        single_game_data['referee_1_id'] = game_details[
            'referees']['headReferee1']['id']
        single_game_data['referee_1'] = game_details[
            'referees']['headReferee1']['name']
    if type(game_details['referees']['headReferee2']) is str:
        single_game_data['referee_2'] = game_details[
            'referees']['headReferee2']
    else:
        single_game_data['referee_2_id'] = game_details[
            'referees']['headReferee2']['id']
        single_game_data['referee_2'] = game_details[
            'referees']['headReferee2']['name']
    if type(game_details['referees']['lineReferee1']) is str:
        single_game_data['linesman_1'] = game_details[
            'referees']['lineReferee1']
    else:
        single_game_data['linesman_1_id'] = game_details[
            'referees']['lineReferee1']['id']
        single_game_data['linesman_1'] = game_details[
            'referees']['lineReferee1']['name']
    if type(game_details['referees']['lineReferee2']) is str:
        single_game_data['linesman_2'] = game_details[
            'referees']['lineReferee2']
    else:
        single_game_data['linesman_2_id'] = game_details[
            'referees']['lineReferee2']['id']
        single_game_data['linesman_2'] = game_details[
            'referees']['lineReferee2']['name']

    if 'bestPlayers' in game_details:
        single_game_data['home_best_player_id'] = game_details[
            'bestPlayers']['home']['id']
        single_game_data['home_best_player'] = game_details[
            'bestPlayers']['home']['name']
        single_game_data['road_best_player_id'] = game_details[
            'bestPlayers']['visitor']['id']
        single_game_data['road_best_player'] = game_details[
            'bestPlayers']['visitor']['name']

    return single_game_data


def get_game_rosters(game_id, season, game_type):
    """
    Retrieves rosters for all teams in game with the specified game id.
    """
    roster_data = defaultdict(list)

    game_roster_src_path = os.path.join(
        CONFIG['base_data_dir'], 'game_roster',
        str(season), str(game_type), "%d.json" % game_id)
    if not os.path.isfile(game_roster_src_path):
        return roster_data

    game_rosters = json.loads(open(game_roster_src_path).read())

    collected_tgt_keys = set()

    for home_road_key in ['home', 'visitor']:
        roster = game_rosters[home_road_key]
        for roster_key in sorted(roster.keys()):
            # splitting key into single string digits
            pos, line, clr = list(str(roster_key))
            # converting coded position into actual position
            pos = POS_KEYS[pos]
            # goaltender's starting status is coded in third, not second digit
            if pos == 'G':
                line = clr
            # setting up target key
            tgt_key = ("%s_%s%s" % (
                home_road_key.replace('visitor', 'road'), pos, line)).lower()
            collected_tgt_keys.add(tgt_key)
            # appending a dummy player id if necessary, e.g. for fourth
            # defensive pairs only consisting of a right defenseman
            if pos != 'G' and int(clr) > len(roster_data[tgt_key]) + 1:
                roster_data[tgt_key].append(0)
            roster_data[tgt_key].append(roster[roster_key]['playerId'])
        else:
            for tgt_key in collected_tgt_keys:
                if '_d' in tgt_key:
                    while len(roster_data[tgt_key]) < 2:
                        roster_data[tgt_key].append(0)
                if '_f' in tgt_key:
                    while len(roster_data[tgt_key]) < 3:
                        roster_data[tgt_key].append(0)

    return roster_data


def get_time_tied_leading_trailing(event, previous_score, last_goal_time):
    """
    Calculate time of previous score state according to current event time
    and time of last goal scored.
    """
    if previous_score['home'] == previous_score['road']:
        return 'tied', event['time'] - last_goal_time
    elif previous_score['home'] > previous_score['road']:
        return 'home_leading', event['time'] - last_goal_time
    elif previous_score['home'] < previous_score['road']:
        return 'road_leading', event['time'] - last_goal_time


def get_game_events(game_id, season, game_type):
    """
    Register game events for current game from separate data source.
    """
    game_events_src_path = os.path.join(
        CONFIG['base_data_dir'], 'game_events',
        str(season), str(game_type), "%d.json" % game_id)
    game_events = json.loads(open(game_events_src_path).read())

    single_game_events = dict()

    # setting up containers for all goals
    all_goals = list()
    goals_per_team = {'home': list(), 'road': list()}
    empty_net_goals_per_team = {'home': 0, 'road': 0}
    extra_attacker_goals_per_team = {'home': 0, 'road': 0}

    # setting up score state container and helper variables
    tied_leading_trailing = defaultdict(int)
    last_goal_time = 0
    current_score = {'home': 0, 'road': 0}

    # collecting all goals scored in the game in order to
    # retrieve the team that scored the first goal of the game
    for period in sorted(game_events):
        for event in game_events[period]:
            if event['type'] == 'goal':
                all_goals.append(event)
                home_road = event['data']['team'].replace('visitor', 'road')
                goals_per_team[home_road].append(event)
                # calculating timespan of previous score state
                score_state, timespan = get_time_tied_leading_trailing(
                    event, current_score, last_goal_time)
                tied_leading_trailing[score_state] += timespan
                # re-setting helper variables for score state time retrieval
                # setting time of previous goal to current time
                last_goal_time = event['time']
                # adjusting score
                current_score['home'], current_score['road'] = [
                    int(x) for x in event['data']['currentScore'].split(":")]
    else:
        # calculating timespan of score state between last goal scored in game
        # and end of game
        score_state, timespan = get_time_tied_leading_trailing(
            event, current_score, last_goal_time)
        tied_leading_trailing[score_state] += timespan

        # finally storing score state timespans
        time_played = 0
        for sit in ['tied', 'home_leading', 'road_leading']:
            single_game_events[sit] = tied_leading_trailing[sit]
            time_played += tied_leading_trailing[sit]
        else:
            single_game_events['time_played'] = time_played

    # retrieving first goal of the game
    # making sure the goals are sorted by time
    first_goal = sorted(all_goals, key=lambda d: d['time'])[0]

    single_game_events['first_goal'] = first_goal[
        'data']['team'].replace('visitor', 'road')
    single_game_events['first_goal_time'] = first_goal['time']
    single_game_events['first_goal_player_id'] = first_goal[
        'data']['scorer']['playerId']
    single_game_events['first_goal_first_name'] = first_goal[
        'data']['scorer']['name']
    single_game_events['first_goal_last_name'] = first_goal[
        'data']['scorer']['surname']

    # retrieving game-winning goal
    if len(goals_per_team['home']) > len(goals_per_team['road']):
        winning_goal = goals_per_team['home'][len(goals_per_team['road'])]
    else:
        winning_goal = goals_per_team['road'][len(goals_per_team['home'])]

    single_game_events['gw_goal'] = winning_goal[
        'data']['team'].replace('visitor', 'road')
    single_game_events['gw_goal_time'] = winning_goal['time']
    single_game_events['gw_goal_player_id'] = winning_goal[
        'data']['scorer']['playerId']
    single_game_events['gw_goal_first_name'] = winning_goal[
        'data']['scorer']['name']
    single_game_events['gw_goal_last_name'] = winning_goal[
        'data']['scorer']['surname']

    # counting empty net and extra attacker goals per team
    for key in ['home', 'road']:
        for goal in goals_per_team[key]:
            if goal['data']['en']:
                empty_net_goals_per_team[key] += 1
            if goal['data']['ea']:
                # some empty net goals are also falsely registered as extra
                # attacker goals
                if goal['data']['en']:
                    continue
                # game-winning shootout goals are falsely registered as extra
                # attacker goals
                if goal['data']['balance'] == 'GWS':
                    continue
                extra_attacker_goals_per_team[key] += 1
        else:
            single_game_events[
                "%s_en_goals" % key] = empty_net_goals_per_team[key]
            single_game_events[
                "%s_ea_goals" % key] = extra_attacker_goals_per_team[key]

    return single_game_events


if __name__ == '__main__':
    # retrieving arguments specified on command line
    parser = argparse.ArgumentParser(
        description='Process DEL game information.')
    parser.add_argument(
        '-f', '--from', dest='from_date', required=False,
        metavar='first date to process games for',
        help="The first date information will be processed for")
    parser.add_argument(
        '-t', '--to', dest='to_date', required=False,
        metavar='last date to process games for',
        help="The last date information will be processed for")
    parser.add_argument(
        '-s', '--season', dest='season', required=False, default=2020,
        type=int, choices=[2016, 2017, 2018, 2019, 2020],
        metavar='season to process games for',
        help="The season information will be processed for")
    parser.add_argument(
        '--initial', dest='initial', required=False,
        action='store_true', help='Re-create list of games')

    args = parser.parse_args()

    # setting time interval of interest from command line options
    tgt_season = args.season
    from_date = args.from_date
    to_date = args.to_date
    initial = args.initial

    if from_date is None:
        # using yesterday's date as default from date
        from_date = datetime.date.today() - relativedelta(days=1)
    else:
        from_date = parse(from_date).date()

    if to_date is None:
        # using from date as default to date
        to_date = from_date
    else:
        to_date = parse(to_date).date()

    # determining end date of target season
    season_end_date = datetime.date(tgt_season + 1, 5, 31)
    previous_season_end_date = datetime.date(tgt_season, 5, 31)

    # setting up list of all game dates
    game_dates = list(rrule(DAILY, dtstart=from_date, until=to_date))
    game_dates = [
        game_date.date() for game_date in game_dates if
        game_date.date() <= season_end_date and
        game_date.date() > previous_season_end_date]

    # setting up target path
    tgt_path = os.path.join(TGT_DIR, str(tgt_season), TGT_FILE)

    if initial:
        games = list()
    else:
        if not os.path.isfile(tgt_path):
            print("+ Unable to load existing games from %s" % tgt_path)
            games = list()
        else:
            games = json.loads(open(tgt_path).read())

    # retrieving games for each game date
    for game_date in game_dates:
        games = get_games_for_date(game_date, games)

    open(tgt_path, 'w').write(
        json.dumps(games, indent=2, default=str))
