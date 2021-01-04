#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import json
import yaml
import argparse

from collections import namedtuple, defaultdict

import intervaltree

from utils import get_game_info, get_game_type_from_season_type, get_home_road

# loading external configuration
CONFIG = yaml.safe_load(open(os.path.join(
    os.path.dirname(os.path.realpath(__file__)), 'config.yml')))

GAME_SRC = 'del_games.json'

# named tuples to define various items
GoalieChange = namedtuple('GoalieChange', ['time', 'team', 'home_road', 'type', 'player_id'])
GoalieShift = namedtuple('GoalieShift', ['player_id', 'team', 'home_road', 'from_time', 'to_time'])
Penalty = namedtuple('Penalty', [
    'id', 'player_id', 'surname', 'team', 'home_road', 'infraction',
    'duration', 'from_time', 'to_time', 'create_time', 'actual_duration'])


def build_interval_tree(game):
    """
    Builds interval tree containing all goalie shifts and penalties from current game.
    """
    game_type = get_game_type_from_season_type(game)

    game_events_src_path = os.path.join(
        CONFIG['base_data_dir'], 'game_events', str(game['season']), str(game_type), "%d.json" % game['game_id'])
    events_data = json.loads(open(game_events_src_path).read())

    # setting up interval tree
    it = intervaltree.IntervalTree()
    # setting up list to contain all end of period times and all times a goal
    # has been scored
    end_period_times = list()
    goal_times = dict()
    # setting up dictionary for goalie changes
    goalie_changes = {'home': list(), 'road': list()}

    for period in sorted(events_data.keys()):
        # adding end time of current period to all end of period times
        if period in ['1', '2', '3']:
            end_period_times.append(int(period) * 1200)

        for event in events_data[period]:
            # retrieving type of event first
            event_type = event['type']

            # adding time of overtime end to list of period end times
            if period == 'overtime' and (event_type == 'periodEnd' or event_type == 'goal'):
                end_period_times.append(event['time'])

            # adding time of goal to list of times a goal has been scored
            if event_type == 'goal':
                goal_times[event['time']] = event['data']['balance']

            # registering goalie changes
            if event_type == 'goalkeeperChange':
                register_goalie_change(event, game, goalie_changes)

            # adding penalties to interval tree
            if event_type == 'penalty':
                create_penalty_interval(event, game, it)

    # (optionally) adding final outgoing goalie change at end of game
    for home_road in goalie_changes:
        # retrieving team and player id for last registered goalie change in current game
        event_team = goalie_changes[home_road][-1].team
        player_id = goalie_changes[home_road][-1].player_id
        if goalie_changes[home_road][-1].type == 'goalie_in':
            # using the maximum time from all period end times as
            # time of game end
            goalie_changes[home_road].append(
                GoalieChange(max(end_period_times), event_team, home_road, 'goalie_out', player_id))

    # creating actual goalie shifts from registered goalie changes
    create_goalie_shifts(goalie_changes, game, it)

    return it, goal_times


def create_goalie_shifts(goalie_changes, game, interval_tree):
    """
    Converting goalie changes at a certain time of the specified game into
    actual goalie shifts ranging from a beginning to an end time.
    """
    for home_road in goalie_changes:
        # for every pair of goalie change items...
        for i in range(0, len(goalie_changes[home_road]) - 1, 2):
            goalie_in_change = goalie_changes[home_road][i]
            goalie_out_change = goalie_changes[home_road][i + 1]

            # dirty workaround to avoid situations where goaltenders are put
            # into a game at its end (c.f. game_id 1626)
            if goalie_in_change.time == goalie_out_change.time:
                continue

            # ...create a goalie shift item
            goalie_shift = GoalieShift(
                goalie_in_change.player_id, goalie_in_change.team,
                home_road, goalie_in_change.time, goalie_out_change.time)

            # adding goalie shift to interval tree
            interval_tree.addi(-goalie_out_change.time, -goalie_in_change.time, goalie_shift)


def register_goalie_change(event, game, goalie_changes):
    """
    Registers a goalie change retrieved from game events by extending the
    specified list of previous changes.
    """
    # retrieving time of goalie change
    event_time = event['data']['time']
    # retrieving team facilitating the goalie change
    event_team, home_road = get_home_road(game, event)

    changes = list()
    players = list()

    # handling outgoing goalie
    if event['data']['outgoingGoalkeeper']:
        changes.append('goalie_out')
        players.append(event['data']['outgoingGoalkeeper']['playerId'])
    # handling incoming goalie
    if event['data']['player']:
        changes.append('goalie_in')
        players.append(event['data']['player']['playerId'])

    for change_type, player_id in zip(changes, players):
        # setting up goalie change item
        goalie_change = GoalieChange(event_time, event_team, home_road, change_type, player_id)
        # adding goalie change to list of goalie changes for current team
        goalie_changes[home_road].append(goalie_change)


def create_penalty_interval(event, game, interval_tree):
    """
    Creates a time interval including all penalty-related information.
    """
    # retrieving team taking the penalty (including home/road indicator)
    event_team, home_road = get_home_road(game, event)
    # retrieving penalized player
    if event['data']['disciplinedPlayer'] and 'playerId' in event['data']['disciplinedPlayer']:
        penalty_player_id = event['data']['disciplinedPlayer']['playerId']
        penalty_player = event['data']['disciplinedPlayer']['surname']
    else:
        penalty_player_id = None
        penalty_player = None
    # retrieving other penalty information
    event_id = event['data']['id']
    penalty_start = event['data']['time']['from']['scoreboardTime']
    penalty_end = event['data']['time']['to']['scoreboardTime']
    # optionally switching start and end time of penalty if necessary due
    # to data errors (e.g. Felix Schütz penalty in game 1247)
    if penalty_start > penalty_end:
        penalty_start, penalty_end = penalty_end, penalty_start
    # retrieving infraction
    infraction = event['data']['codename']
    # retrieving nominal duration and calculating the actual duration of the penalty
    duration = int(event['data']['duration'])
    actual_duration = penalty_end - penalty_start
    # registering create time, i.e. the time of the game when the penalty was called
    create_time = event['data']['createTime']

    # disregarding penalties with zero length, i.e. penalty shots
    if duration:
        # creating penalty item
        penalty = Penalty(
            event_id, penalty_player_id, penalty_player, event_team, home_road,
            infraction, duration, penalty_start, penalty_end, create_time, actual_duration)
        # using dummy times for penalties that effectively start at the end of the game
        if penalty_end == penalty_start and penalty_start >= 3600:
            penalty_start = -2
            penalty_end = -1
        # adding interval to interval tree, using penalty item as payload
        try:
            interval_tree.addi(-penalty_end, -penalty_start, penalty)
        except ValueError as e:
            # TODO: notification
            print(e)


def reconstruct_skater_situation(game, verbose=False):
    """
    Reconstruct skater on-ice situation for specified game.
    """
    print("+ Reconstructing on-ice skater situation for game %s" % get_game_info(game))

    # building interval tree to query goalies and player situations
    # receiving a list of times when goals has been scored
    it, goal_times = build_interval_tree(game)

    # retrieving all penalties
    all_penalties = list()
    for interval in it:
        if isinstance(interval.data, Penalty):
            penalty = interval.data
            all_penalties.append(penalty)

    # retrieving game end (in seconds) from interval tree
    game_end = - it.range().begin
    # retrieving goalies on ice and extra attackers for current game
    goalies_on_ice, extra_attackers = reconstruct_goalie_situation(it)

    # setting up dictionary to hold skater situations for each second of the game
    time_dict = dict()

    # setting up container to hold goalie/penalty intervals that have been
    # valid previously
    last_intervals = ''
    # setting up sets to hold a) penalties that effectively influence the
    # skater situation on ice, b) penalties that cancel each other out, c)
    # penalties that actually have started
    effective_penalties = set()
    cancelling_penalties = set()
    started_penalties = set()
    # initial setting for skater counts per team
    skr_count = {'home': 5, 'road': 5}

    # setting up skater situation at the beginning of the game
    time_dict[0] = {**skr_count, **goalies_on_ice[0]}

    for t in range(1, game_end + 1):
        # setting up containers holding the difference in skater/goalie numbers
        # in comparison to previous numbers produced by the currently
        # ongoing intervals
        curr_delta = {'home': 0, 'road': 0}
        curr_goalie_delta = {'home': 0, 'road': 0}
        # checking whether we're in the overtime of a regular season game and
        # adjusting skater counts accordingly
        in_ot = adjust_skater_count_in_overtime(game, t, skr_count)
        # adjusting skater counts according to the goaltenders currently on ice
        current_goalies = adjust_skater_counts_for_goalies(t, goalies_on_ice, curr_goalie_delta)

        if t in goal_times and verbose:
            print("- Goal: %d:%02d (%dv%d)" % (t // 60, t % 60, skr_count['home'], skr_count['road']))

        # retrieving all currently valid goalie and penalty intervals, i.e.
        # on-going goalie shifts and currently served penalties
        current_intervals = it[-t]
        current_penalties = defaultdict(list)

        # doing further processing for the current second of the game only
        # if currently valid intervals have changed from previous second of
        # the game
        if current_intervals != last_intervals:
            # if verbose:
            #     print("%d:%02d (%d) --> " % (t // 60, t % 60, t), end='')
            # retaining only penalty intervals
            penalty_intervals = list(filter(lambda item: (isinstance(item.data, Penalty)), current_intervals))
            # collecting currently on-going penalties by team
            for pi in sorted(penalty_intervals, key=lambda interval: interval.data.from_time):
                penalty = pi.data
                if penalty.duration in (120, 300):
                    if verbose:
                        print(
                            "- Penalty: %d:%02d" % (pi.end // -60, -pi.end % 60),
                            "%d:%02d" % (pi.begin // -60, -pi.begin % 60),
                            penalty.duration, penalty.team, penalty.infraction,
                            penalty.actual_duration, penalty.surname)
                    current_penalties[penalty.home_road].append(penalty)

            # collecting penalties that have been created at the current time
            penalties = list(filter(
                lambda penalty: penalty.create_time == (t - 1) and penalty.duration in (120, 300), all_penalties))
            # if no penalties have been created at the current time, collect
            # all penalties that have started at the current time
            if not penalties:
                penalties = list(filter(
                    lambda penalty: penalty.from_time == (t - 1) and penalty.duration in (120, 300), all_penalties))

            # sorting collected penalties by actual duration and start time
            penalties = sorted(penalties, key=lambda penalty: (penalty.actual_duration, penalty.from_time))
            # retrieving and sorting penalties taken by home team
            home_penalties = list(filter(lambda penalty: penalty.home_road == 'home', penalties))
            home_penalties = sorted(home_penalties, key=lambda penalty: (penalty.actual_duration, penalty.from_time))
            # retrieving and sorting penalties taken by road team
            road_penalties = list(filter(lambda penalty: penalty.home_road == 'road', penalties))
            road_penalties = sorted(road_penalties, key=lambda penalty: (penalty.actual_duration, penalty.from_time))
            # grouping minor and major penalties taken by home team
            home_min_penalties = list(filter(lambda penalty: penalty.duration == 120, home_penalties))
            home_maj_penalties = list(filter(lambda penalty: penalty.duration == 300, home_penalties))
            # grouping minor and major penalties taken by road team
            road_min_penalties = list(filter(lambda penalty: penalty.duration == 120, road_penalties))
            road_maj_penalties = list(filter(lambda penalty: penalty.duration == 300, road_penalties))
            # retrieving all teams taking penalties at current time
            penalty_teams = set([p.home_road for p in penalties])

            # continuing if no penalties have been created or started at
            # the current time of the game
            if not penalties:
                pass
            # if only one team has taken penalties
            elif len(penalty_teams) == 1:
                for penalty in penalties:
                    # skipping penalty if it hasn't already started
                    if penalty.from_time > t:
                        continue
                    # checking if current penalty has not started yet or has
                    # been cancelled by other penalties
                    if penalty not in started_penalties.union(cancelling_penalties):
                        team = penalty.home_road
                        # in overtime the other team gets another player
                        if in_ot:
                            curr_delta[switch_team(team)] += 1
                        # in regulation the current team loses a player
                        else:
                            curr_delta[team] -= 1
                        # adding current penalty to effective penalties
                        effective_penalties.add(penalty)
                    # adding current penalty to started penalties
                    started_penalties.add(penalty)
            # if both teams have taken penalties
            else:
                # registering major penalties that cancel each other out, i.e. if both teams received the same number
                # of major penalties at the current time
                if len(home_maj_penalties) == len(road_maj_penalties):
                    for penalty in home_maj_penalties:
                        cancelling_penalties.add(penalty)
                    for penalty in road_maj_penalties:
                        cancelling_penalties.add(penalty)
                elif len(home_maj_penalties) > len(road_maj_penalties):
                    pen_cnt_diff = len(home_maj_penalties) - len(road_maj_penalties)
                    pen_cnt = 0
                    for penalty in home_maj_penalties:
                        if pen_cnt < pen_cnt_diff:
                            # adjusting the number of skaters for corresponding
                            # team starting at current time
                            if penalty not in started_penalties.union(cancelling_penalties):
                                # in regular season overtime the other team usually gets an additional player
                                if in_ot:
                                    curr_delta['road'] += 1
                                else:
                                    curr_delta['home'] -= 1
                                pen_cnt += 1
                                effective_penalties.add(penalty)
                            started_penalties.add(penalty)
                        else:
                            started_penalties.add(penalty)
                            cancelling_penalties.add(penalty)
                    for penalty in road_maj_penalties:
                        started_penalties.add(penalty)
                        cancelling_penalties.add(penalty)
                elif len(home_maj_penalties) < len(road_maj_penalties):
                    pen_cnt_diff = len(road_maj_penalties) - len(home_maj_penalties)
                    pen_cnt = 0
                    for penalty in road_maj_penalties:
                        if pen_cnt < pen_cnt_diff:
                            # adjusting the number of skaters for corresponding
                            # team starting at current time
                            if penalty not in started_penalties.union(cancelling_penalties):
                                # in regular season overtime the other team usually gets an additional player
                                if in_ot:
                                    curr_delta['home'] += 1
                                else:
                                    curr_delta['road'] -= 1
                                pen_cnt += 1
                                effective_penalties.add(penalty)
                            started_penalties.add(penalty)
                        else:
                            started_penalties.add(penalty)
                            cancelling_penalties.add(penalty)
                    for penalty in home_maj_penalties:
                        started_penalties.add(penalty)
                        cancelling_penalties.add(penalty)

                # registering minor penalties that cancel each other out, i.e. if both teams received the same number
                # of major penalties at the current time
                if len(home_min_penalties) == len(road_min_penalties):
                    # if current skater situation is 5-on-5 and only one minor
                    # penalty was taken by each team we're going to 4-on-4 now
                    if (
                        len(home_min_penalties) == 1 and
                        len(road_min_penalties) == 1 and  # redundant
                        list(skr_count.values()) == [5, 5]
                    ):
                        for pens in [home_min_penalties, road_min_penalties]:
                            for penalty in pens:
                                team = penalty.home_road
                                if penalty not in started_penalties.union(cancelling_penalties):
                                    if in_ot:
                                        curr_delta[switch_team(team)] += 1
                                    else:
                                        curr_delta[team] -= 1
                                    effective_penalties.add(penalty)
                                started_penalties.add(penalty)
                    # otherwise all penalties are cancelling each other out
                    else:
                        for penalty in home_min_penalties:
                            cancelling_penalties.add(penalty)
                        for penalty in road_min_penalties:
                            cancelling_penalties.add(penalty)
                elif len(home_min_penalties) > len(road_min_penalties):
                    pen_cnt_diff = len(home_min_penalties) - len(road_min_penalties)
                    pen_cnt = 0
                    for penalty in home_min_penalties:
                        if pen_cnt < pen_cnt_diff:
                            # adjusting the number of skaters for corresponding
                            # team starting at current time
                            if penalty not in started_penalties.union(cancelling_penalties):
                                if in_ot:
                                    curr_delta['road'] += 1
                                else:
                                    curr_delta['home'] -= 1
                                pen_cnt += 1
                                effective_penalties.add(penalty)
                            started_penalties.add(penalty)
                        else:
                            started_penalties.add(penalty)
                            cancelling_penalties.add(penalty)
                    for penalty in road_min_penalties:
                        started_penalties.add(penalty)
                        cancelling_penalties.add(penalty)
                elif len(home_min_penalties) < len(road_min_penalties):
                    pen_cnt_diff = len(road_min_penalties) - len(home_min_penalties)
                    pen_cnt = 0
                    for penalty in road_min_penalties:
                        if pen_cnt < pen_cnt_diff:
                            # adjusting the number of skaters for corresponding
                            # team starting at current time
                            if penalty not in started_penalties.union(cancelling_penalties):
                                if in_ot:
                                    curr_delta['home'] += 1
                                else:
                                    curr_delta['road'] -= 1
                                pen_cnt += 1
                                effective_penalties.add(penalty)
                            started_penalties.add(penalty)
                        else:
                            started_penalties.add(penalty)
                            cancelling_penalties.add(penalty)
                    for penalty in home_min_penalties:
                        started_penalties.add(penalty)
                        cancelling_penalties.add(penalty)

            # handling expired penalties
            expired_penalties = set()
            for penalty in started_penalties:
                if t < penalty.from_time:
                    continue
                # checking whether penalty interval currently registered as
                # ongoing is in fact still ongoing
                if penalty not in current_penalties[penalty.home_road]:
                    expired_penalties.add(penalty)
                    if penalty in effective_penalties:
                        if in_ot:
                            # this turned out to be wrong, since it lead to
                            # skater counts below 3, but is it correct now?
                            # curr_delta[switch_team(penalty.home_road)] -= 1
                            curr_delta[penalty.home_road] += 1
                        else:
                            curr_delta[penalty.home_road] += 1
            # actually removing no longer on-going intervals
            effective_penalties.difference_update(expired_penalties)
            started_penalties.difference_update(expired_penalties)

            if verbose:
                print("%d:%02d (%d) --> " % (t // 60, t % 60, t), end='')

        # actually calculating current skater count from previous count
        # and deltas collected from all current intervals
        for key in skr_count:
            skr_count[key] = skr_count[key] + curr_delta[key] + curr_goalie_delta[key]
        # re-adjusting skater counts in overtime, e.g. after penalties have
        # expired
        adjust_skater_count_in_overtime(game, t, skr_count)

        # testing modified skater counts
        test_skater_counts(skr_count)

        if verbose:
            addendum = ''
            if any(extra_attackers[t].values()):
                addendum = '(with extra attacker)'
            if current_intervals != last_intervals:
                print("%dv%d %s" % (skr_count['home'], skr_count['road'], addendum))
            if t == 3601:
                print("--> %d:%02d (%d)" % (t // 60, t % 60, t))
                print("%dv%d %s" % (skr_count['home'], skr_count['road'], addendum))

        time_dict[t] = {**skr_count, **current_goalies}
        # saving currently valid intervals for comparison at next
        # second in the game
        last_intervals = current_intervals

    for t in time_dict:
        for key in ['home', 'road']:
            if time_dict[t][key] < 3:
                time_dict[t][key] = 3
            if time_dict[t][key] > 6:
                time_dict[t][key] = 6
            time_dict[t][game["%s_abbr" % key]] = time_dict[t][key]

    return time_dict, goal_times


def reconstruct_goalie_situation(interval_tree):
    """
    Reconstructs goaltender situation, i.e. which goaltender was on ice for
    each second of the current game.
    """
    game_end = - interval_tree.range().begin
    goalies_on_ice = dict()
    extra_attackers = dict()

    for t in range(0, game_end + 1):
        # retrieving currently ongoing goalie shifts
        goalie_shift_intervals = query_interval_tree_by_type(interval_tree, -t, GoalieShift)
        # adjusting for start of the game
        if t == 0:
            goalie_shift_intervals = query_interval_tree_by_type(interval_tree, -t - 1, GoalieShift)
        # container for current goalies
        current_goalies = {'home_goalie': None, 'road_goalie': None}
        # container for extra attacker info
        current_extra_attacker = {'home': False, 'road': False}
        # setting current goalies according to ongoing goalie shifts
        for goalie_shift in goalie_shift_intervals:
            current_goalies["%s_goalie" % goalie_shift.home_road] = goalie_shift.player_id
        if current_goalies['home_goalie'] is None:
            current_extra_attacker['home'] = True
        if current_goalies['road_goalie'] is None:
            current_extra_attacker['road'] = True

        goalies_on_ice[t] = current_goalies
        extra_attackers[t] = current_extra_attacker

    return goalies_on_ice, extra_attackers


def query_interval_tree_by_type(interval_tree, time, type):
    """
    Returns only items of specified type from interval tree at given time.
    """
    all_intervals = interval_tree[time]

    selected_intervals = set()
    for interval in all_intervals:
        if isinstance(interval[-1], type):
            selected_intervals.add(interval.data)

    return selected_intervals


def adjust_skater_count_in_overtime(game, time, skr_count):
    """
    Adjusts skater count in regular season overtimes according to skater
    situation at the end of regulation and/or previous second.
    """
    if game['season_type'] == 'RS' and time >= 3601:
        # if the same number of skaters is on ice for both teams, we're setting
        # the skater situation to 3-on-3 regardless
        # NB: this doesn't account for penalties expiring in overtime that may
        # lead to legitimate 4-on-4 (or even 5-on-5) situations since we have
        # no information when exactly the play was interrupted, i.e. faceoff
        # times
        if skr_count['home'] == skr_count['road']:
            skr_count['home'] = 3
            skr_count['road'] = 3
        # if home team is on a 5-on-4 power play change that to a 4-on-3
        # NB: other player advantages (4-on-3, 5-on-3) remain unchanged
        elif skr_count['home'] > skr_count['road']:
            if skr_count['home'] == 5 and skr_count['road'] == 4:
                skr_count['home'] = 4
                skr_count['road'] = 3
        # if road team is on a 5-on-4 power play change that to a 4-on-3
        # NB: other player advantages (4-on-3, 5-on-3) remain unchanged
        elif skr_count['road'] > skr_count['home']:
            if skr_count['road'] == 5 and skr_count['home'] == 4:
                skr_count['road'] = 4
                skr_count['home'] = 3
        return True
    else:
        return False


def adjust_skater_counts_for_goalies(time, goalies_on_ice, curr_goalie_delta):
    """
    Adjusts skater counts in accordance to goalies currently on ice.
    """
    # determining goalies currently on ice
    current_goalies = goalies_on_ice[time]
    # determining goalies on ice in the previous second
    previous_goalies = goalies_on_ice[time - 1]
    for home_road in current_goalies:
        # adding skater if goalie has left the ice between now and the
        # previous second
        if current_goalies[home_road] is None and previous_goalies[home_road]:
            curr_goalie_delta[home_road.replace("_goalie", "")] += 1
        # subtracting skater if goalie has come back on ice after being off
        # the previous second
        if current_goalies[home_road] and previous_goalies[home_road] is None:
            curr_goalie_delta[home_road.replace("_goalie", "")] -= 1

    return current_goalies


def test_skater_counts(skater_count):
    """
    Testing modified skater counts and notifying user if lower and upper limits
    have been exceeded.
    """
    for key in ['home', 'road']:
        try:
            assert skater_count[key] >= 3
        except AssertionError:
            print("Skater number for %s team under limit of 3: %d" % (key, skater_count[key]))
        try:
            assert skater_count[key] <= 6
        except AssertionError:
            print("Skater number for %s team over limit of 6: %d" % (key, skater_count[key]))


def switch_team(team):
    """
    Returns the opponent team given the specified team.
    """
    if team == 'home':
        return 'road'
    elif team == 'road':
        return 'home'


if __name__ == '__main__':

    # retrieving arguments specified on command line
    parser = argparse.ArgumentParser(
        description='Process DEL team game statistics.')
    parser.add_argument(
        '-s', '--season', dest='season', required=False, default=2020,
        type=int, choices=[2016, 2017, 2018, 2019, 2020],
        metavar='season to process games for',
        help="The season information will be processed for")
    parser.add_argument(
        '-g', '--game_id', dest='game_id', required=False, type=int,
        metavar='game to reconstruct skater situation for',
        help="The ID of the game skater situations will be reconstructed for")

    args = parser.parse_args()

    season = args.season
    game_id = args.game_id

    # setting up path to source data file
    src_dir = os.path.join(CONFIG['tgt_processing_dir'], str(season))
    src_path = os.path.join(src_dir, GAME_SRC)

    # loading games
    games = json.loads(open(src_path).read())

    for game in games:
        if game_id and game['game_id'] != game_id:
            continue
        print(get_game_info(game))

        skr_sit, goal_times = reconstruct_skater_situation(game, True)

    # for x in skr_sit:
    #     print(x, skr_sit[x])
    # print()
    # sits = defaultdict(int)
    # goals = defaultdict(int)
    # prev_sit = (5, 5)

    # for x in skr_sit:
    #     curr_sit = (skr_sit[x]['home'], skr_sit[x]['road'])
    #     if curr_sit != prev_sit:
    #         sits[curr_sit] += 1
    #         print(x, skr_sit[x])
    #         prev_sit = curr_sit
    #     if x in goal_times and goal_times[x].startswith("PP"):
    #         goals[curr_sit] += 1
    #         print("Goal at", x, "in", curr_sit)

    # final_home_sits = dict()
    # final_road_sits = dict()
    # final_home_goals = dict()
    # final_road_goals = dict()

    # for sit in [(5, 4), (5, 3), (4, 3), (4, 5), (3, 5), (3, 4)]:
    #     if sit in sits:
    #         final_home_sits[sit] = sits[sit]
    #         final_road_sits[sit[::-1]] = sits[sit]
    #     else:
    #         final_home_sits[sit] = 0
    #         final_road_sits[sit[::-1]] = 0
    #     if sit in goals:
    #         final_home_goals[sit] = goals[sit]
    #         final_road_goals[sit[::-1]] = goals[sit]
    #     else:
    #         final_home_goals[sit] = 0
    #         final_road_goals[sit[::-1]] = 0

    # print(final_home_sits)
    # print(final_home_goals)
    # print(final_road_sits)
    # print(final_road_goals)
