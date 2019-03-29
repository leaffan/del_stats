#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import json

from collections import OrderedDict, namedtuple, defaultdict

import requests
import intervaltree

from utils import get_game_info

BASE_URL = 'https://www.del.org/live-ticker'
EVENTS_SUFFIX = "matches/%d/period-events.json"
GAME_SRC = 'del_games.json'
TGT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data')

# named tuples to define various items
GoalieChange = namedtuple(
    'GoalieChange', ['time', 'team', 'home_road', 'type', 'player_id'])
GoalieShift = namedtuple(
    'GoalieShift', ['player_id', 'team', 'home_road', 'from_time', 'to_time'])
Penalty = namedtuple('Penalty', [
    'player_id', 'surname', 'team', 'home_road', 'infraction', 'duration',
    'from_time', 'to_time', 'create_time'])


def build_interval_tree(game):
    """
    Builds interval tree containing all goalie shifts and penalties from
    current game.
    """
    # retrieving raw events data
    events_path = EVENTS_SUFFIX % game['game_id']
    events_url = "%s/%s" % (BASE_URL, events_path)
    r = requests.get(events_url)
    events_data = r.json()

    # using ordered dictionary to maintain insertion order of keys
    goalie_changes = OrderedDict()
    goalie_changes['home'] = list()
    goalie_changes['road'] = list()

    # setting up interval tree
    it = intervaltree.IntervalTree()
    # setting up list to contain all end of period times and all times a goal
    # has been scored
    end_period_times = list()
    goal_times = list()
    penalty_times = dict()

    for period in sorted(events_data.keys()):
        # adding end time of current period to all end of period times
        if period in ['1', '2', '3']:
            end_period_times.append(int(period) * 1200)

        for event in events_data[period]:
            # retrieving type of event first
            event_type = event['type']

            # adding time of overtime end to list of period end times
            if (
                period == 'overtime' and (
                    event_type == 'periodEnd' or event_type == 'goal')
            ):
                end_period_times.append(event['time'])
            # adding time of goal to list of times a goal has been scored
            if event_type == 'goal':
                goal_times.append(event['time'])

            # registering goalie changes
            if event_type == 'goalkeeperChange':
                register_goalie_change(event, game, goalie_changes)

            if event_type == 'penalty':
                create_penalty_interval(event, game, it, penalty_times)

    else:
        # (optionally) adding final outgoing goalie change at end of game
        for home_road in goalie_changes:
            event_team = goalie_changes[home_road][-1].team
            player_id = goalie_changes[home_road][-1].player_id
            if goalie_changes[home_road][-1].type == 'goalie_in':
                goalie_changes[home_road].append(
                    GoalieChange(
                        # using the maximum time from all period end times as
                        # time of game end
                        max(end_period_times), event_team,
                        home_road, 'goalie_out', player_id))

    create_goalie_shifts(goalie_changes, game, it)

    return it, goal_times, penalty_times


def create_penalty_interval(event, game, interval_tree, penalty_times):
    """
    Creates a time interval including all penalty-related information.
    """
    # retrieving team involved in penalty (including home/road indicator)
    event_team, home_road = get_home_road(game, event)
    # retrieving penalized player
    if (
        event['data']['disciplinedPlayer'] and
        'playerId' in event['data']['disciplinedPlayer']
    ):
        penalty_player_id = event['data']['disciplinedPlayer']['playerId']
        penalty_player = event['data']['disciplinedPlayer']['surname']
    else:
        penalty_player_id = None
        penalty_player = None
    # retrieving other penalty information
    penalty_start = event['data']['time']['from']['scoreboardTime']
    penalty_end = event['data']['time']['to']['scoreboardTime']
    # optionally switching start and end time of penalty if necessary due
    # to data errors (e.g. Felix Schütz penalty in game 1247)
    if penalty_start > penalty_end:
        penalty_start, penalty_end = penalty_end, penalty_start
    duration = event['data']['duration']
    infraction = event['data']['codename']
    create_time = event['data']['createTime']

    # disregarding penalties with zero length, i.e. penalty shots
    if penalty_end != penalty_start:
        # creating penalty item
        penalty = Penalty(
            penalty_player_id, penalty_player, event_team, home_road,
            infraction, int(duration), penalty_start, penalty_end, create_time)
        # adding interval to interval tree, using penalty item as payload
        interval_tree.addi(-penalty_end, -penalty_start, penalty)

    # adding penalty creation time of current penalty to list of all penalty
    # times
    # only two- and five-minute-penalties do influence skater situation on ice
    if duration in (120, 300):
        if create_time not in penalty_times:
            penalty_times[create_time] = dict()
        if event_team not in penalty_times[create_time]:
            penalty_times[create_time][event_team] = (1, [duration])
        else:
            previous_penalties, previous_durations = penalty_times[
                create_time][event_team]
            penalty_times[create_time][event_team] = (
                previous_penalties + 1, previous_durations + [duration])


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

            # ...create a goalie shift item
            goalie_shift = GoalieShift(
                goalie_in_change.player_id, goalie_in_change.team,
                home_road, goalie_in_change.time, goalie_out_change.time)

            interval_tree.addi(
                -goalie_out_change.time, -goalie_in_change.time, goalie_shift)


def register_goalie_change(event, game, goalie_changes):
    """
    Registers a goalie change retrieved from game events by extending the
    specified list of previous changes and by updating the specified dictioary
    holding the current goalie for a team involved in the game.
    """
    # retrieving time of goalie change
    event_time = event['data']['time']
    # retrieving team involved in goalie change
    event_team, home_road = get_home_road(game, event)
    # handling outgoing goalie
    if event['data']['outgoingGoalkeeper']:
        change_type = 'goalie_out'
        player_id = event['data']['outgoingGoalkeeper']['playerId']
    # handling incoming goalie
    if event['data']['player']:
        change_type = 'goalie_in'
        player_id = event['data']['player']['playerId']

    # setting up goalie change item
    goalie_change = GoalieChange(
        event_time, event_team, home_road, change_type, player_id)
    # adding goalie change to list of goalie changes for current team
    goalie_changes[home_road].append(goalie_change)


def reconstruct_goalie_situation(interval_tree):
    """
    Reconstructs goaltender situation, i.e. which goaltender was on ice for
    each second of the current game.
    """
    game_end = - interval_tree.range().begin
    goalies_on_ice = dict()

    for t in range(0, game_end + 1):
        # retrieving currently ongoing goalie shifts
        goalie_shift_intervals = query_interval_tree_by_type(
            interval_tree, -t, GoalieShift)
        # adjusting for start of the game
        if t == 0:
            goalie_shift_intervals = query_interval_tree_by_type(
                interval_tree, -t - 1, GoalieShift)
            print(goalie_shift_intervals)
        # container for current goalies
        current_goalies = {'home_goalie': None, 'road_goalie': None}
        # setting current goalies according to ongoing goalie shifts
        for interval in goalie_shift_intervals:
            goalie_shift = interval[-1]
            current_goalies[
                "%s_goalie" % goalie_shift.home_road] = goalie_shift.player_id

        goalies_on_ice[t] = current_goalies

    return goalies_on_ice


def query_interval_tree_by_type(interval_tree, time, type):
    """
    Returns only items of specified type from interval tree at given time.
    """
    all_intervals = interval_tree[time]

    selected_intervals = set()
    for interval in all_intervals:
        if isinstance(interval[-1], type):
            selected_intervals.add(interval)

    return selected_intervals


def adjust_skater_counts_for_goalies(time, goalies_on_ice, curr_delta):
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
        if (
            current_goalies[home_road] is None and previous_goalies[home_road]
        ):
            curr_delta[home_road.replace("_goalie", "")] += 1
        # subtracting skater if goalie has come back on ice after being off
        # the previous second
        if (
            current_goalies[home_road] and previous_goalies[home_road] is None
        ):
            curr_delta[home_road.replace("_goalie", "")] -= 1

    return current_goalies


def change_skater_count(
    effective_intervals, ongoing_penalties, extra_penalties, curr_delta
):
    """
    Changes skater count effectively.
    """
    for team in effective_intervals:
        for ei in effective_intervals[team]:
            # reducing the number of skaters for
            # corresponding team starting at current time
            if ei not in ongoing_penalties.union(extra_penalties):
                print("not ongoing, not extra:", ei)
                curr_delta[team] -= 1
            # add current interval to set of currently on-
            # going intervals
            ongoing_penalties.add(ei)


def handle_ongoing_penalties(
    time, penalty_times, effective_intervals, ongoing_penalties,
    extra_penalties, curr_delta, skr_count
):
    """
    Handles ongoing penalties.
    """
    # retrieving all penalties created at current time
    penalties_from_time = dict()
    if time - 1 in penalty_times:
        penalties_from_time = penalty_times[time - 1]

    print("eis:", effective_intervals)

    if not penalties_from_time:
        pass
    # if only one team has been handed one or multiple penalties at the
    # current time handle that/these correspondingly
    elif len(penalties_from_time) == 1:
        change_skater_count(
            effective_intervals, ongoing_penalties,
            extra_penalties, curr_delta)
        # for team in effective_intervals:
        #     for ei in effective_intervals[team]:
        #         # reducing the number of skaters for
        #         # corresponding team starting at current time
        #         if (
        #             ei not in
        #             ongoing_penalties.union(extra_penalties)
        #         ):
        #             curr_delta[team] -= 1
        #         # add current interval to set of currently on-
        #         # going intervals
        #         ongoing_penalties.add(ei)
    # handling incidental penalties
    else:
        # retrieving number and durations of penalties per team
        # handed out first
        home_pen_cnt, home_durations = penalty_times[time - 1][
            game['home_abbr']]
        road_pen_cnt, road_durations = penalty_times[time - 1][
            game['road_abbr']]

        # if number and durations of penalties for both teams
        # match, we have incidental penalties (DEL Rulebook,
        # Rule #112)
        if (
            home_pen_cnt == road_pen_cnt and
            sum(home_durations) == sum(road_durations)
        ):
            # if previous skater situation was 5-on-5 we're going to
            # 4-on-4 then
            if (
                home_pen_cnt == 1 and
                list(skr_count.values()) == [5, 5]
            ):
                change_skater_count(
                    effective_intervals, ongoing_penalties,
                    extra_penalties, curr_delta)
                # for team in effective_intervals:
                #     for ei in effective_intervals[team]:
                #         # reducing the number of skaters for
                #         # corresponding team starting at current
                #         # time
                #         if (
                #             ei not in
                #             ongoing_penalties.union(extra_penalties)
                #         ):
                #             curr_delta[team] -= 1
                #         # add current interval to set of currently
                #         # on-going intervals
                #         ongoing_penalties.add(ei)
        elif (
            home_pen_cnt == road_pen_cnt and
            sum(home_durations) != sum(road_durations)
        ):
            change_skater_count(
                effective_intervals, ongoing_penalties,
                extra_penalties, curr_delta)
            # for team in effective_intervals:
            #     for ei in effective_intervals[team]:
            #         # reducing the number of skaters for
            #         # corresponding team starting at current
            #         # time
            #         if (
            #             ei not in
            #             ongoing_penalties.union(extra_penalties)
            #         ):
            #             curr_delta[team] -= 1
            #         # add current interval to set of currently
            #         # on-going intervals
            #         ongoing_penalties.add(ei)

        elif home_pen_cnt > road_pen_cnt:
            pen_cnt_diff = home_pen_cnt - road_pen_cnt
            pen_cnt = 0
            for ei in effective_intervals['home']:
                if pen_cnt < pen_cnt_diff:
                    # reducing the number of skaters for
                    # corresponding team starting at current
                    # time
                    if (
                        ei not in
                        ongoing_penalties.union(extra_penalties)
                    ):
                        curr_delta['home'] -= 1
                    # add current interval to set of currently
                    # on-going intervals
                    ongoing_penalties.add(ei)
                else:
                    extra_penalties.add(ei)
                pen_cnt += 1
            for ei in effective_intervals['road']:
                if ei not in ongoing_penalties:
                    extra_penalties.add(ei)

        elif road_pen_cnt > home_pen_cnt:
            pen_cnt_diff = road_pen_cnt - home_pen_cnt
            pen_cnt = 0
            for ei in effective_intervals['road']:
                if pen_cnt < pen_cnt_diff:
                    # reducing the number of skaters for
                    # corresponding team starting at current
                    # time
                    if (
                        ei not in
                        ongoing_penalties.union(extra_penalties)
                    ):
                        curr_delta['road'] -= 1
                    # add current interval to set of currently
                    # on-going intervals
                    ongoing_penalties.add(ei)
                else:
                    extra_penalties.add(ei)
                pen_cnt += 1
            for ei in effective_intervals['home']:
                if ei not in ongoing_penalties:
                    extra_penalties.add(ei)


def handle_expired_penalties(
    ongoing_penalties, extra_penalties, current_intervals, curr_delta
):
    """
    Processes expired penalties, i.e. checks whether any of the specified
    ongoing penalties is still ongoing, i.e. contained by the currently valid
    intervals. Adjust the delta in skaters on ice accordingly.
    """
    # preparing to remove penalties from set of ongoing penalties
    # if they have expired
    expired_penalties = set()
    # doing the following for each penalty currently registered as
    # ongoing
    for penalty_interval in ongoing_penalties:
        penalty = penalty_interval.data
        # checking whether penalty interval currently registered as
        # ongoing is in fact still ongoing
        if penalty_interval not in current_intervals:
            expired_penalties.add(penalty_interval)
            if penalty_interval not in extra_penalties:
                curr_delta[penalty.home_road] += 1
    # actually removing no longer on-going intervals
    ongoing_penalties.difference_update(expired_penalties)


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


def reconstruct_skater_situation(game):
    """
    Reconstruct skater on-ice situation for specified game.
    """
    print(
        "+ Reconstructing on-ice skater situation for " +
        "game %s" % get_game_info(game))

    # building interval tree to query goalies and player situations
    # receiving a list of times when goals has been scored
    it, goal_times, penalty_times = build_interval_tree(game)

    # retrieving game end (in seconds) from interval tree
    game_end = - it.range().begin
    goalies_on_ice = reconstruct_goalie_situation(it)

    # setting up dictionary to hold skater situations for each second
    # of the game
    time_dict = dict()

    # setting up container to hold goalie/penalty intervals that have been
    # valid previously
    last_intervals = ''
    ongoing_penalties = set()
    extra_penalties = set()
    # initial setting for skater counts per team
    skr_count = {'home': 5, 'road': 5}
    # goalies_not_on_ice = list()

    time_dict[0] = {**skr_count, **goalies_on_ice[0]}

    for t in range(1, game_end + 1):
        # setting up containers holding the difference in skater numbers
        # in comparison to previous numbers produced by the currently
        # ongoing intervals
        curr_delta = {'home': 0, 'road': 0}
        adjust_skater_count_in_overtime(game, t, skr_count)

        current_goalies = adjust_skater_counts_for_goalies(
            t, goalies_on_ice, curr_delta)

        # retrieving all currently valid goalie and penalty intervals, i.e.
        # on-going goalie shifts and currently served penalties
        current_intervals = it[-t]
        effective_intervals = defaultdict(list)

        # doing further processing for the current second of the game only
        # if penalty intervals have changed from previous second of the game
        if current_intervals != last_intervals:
            print(t)
            # retaining only penalty intervals
            penalty_intervals = list(filter(lambda item: (
                isinstance(item.data, Penalty)), current_intervals))
            for pi in penalty_intervals:
                penalty = pi.data
                print(
                    pi.end, pi.begin, penalty.duration,
                    penalty.team, penalty.infraction)
                if penalty.duration in (120, 300):
                    effective_intervals[penalty.home_road].append(pi)

            handle_ongoing_penalties(
                t, penalty_times, effective_intervals, ongoing_penalties,
                extra_penalties, curr_delta, skr_count)

            handle_expired_penalties(
                ongoing_penalties, extra_penalties,
                current_intervals, curr_delta)

        # actually calculating current skater count from previous count
        # and deltas collected from all current intervals
        skr_count['home'] = skr_count['home'] + curr_delta['home']
        skr_count['road'] = skr_count['road'] + curr_delta['road']
        # re-adjusting skater counts in overtime, e.g. after penalties have
        # expired
        adjust_skater_count_in_overtime(game, t, skr_count)

        assert 3 <= skr_count['home'] <= 6
        assert 3 <= skr_count['road'] <= 6

        if current_intervals != last_intervals:
            print(skr_count)

        # time_dict[t] = deepcopy(skr_count)
        time_dict[t] = {**skr_count, **current_goalies}

        # saving currently valid intervals for comparison at next
        # second in the game
        last_intervals = current_intervals

    return time_dict


def get_home_road(game, event):
    if event['data']['team'] == 'home':
        return game['home_abbr'], 'home'
    else:
        return game['road_abbr'], 'road'


if __name__ == '__main__':

    # setting up source path
    src_path = os.path.join(TGT_DIR, GAME_SRC)

    # loading games
    games = json.loads(open(src_path).read())

    cnt = 0
    for game in games[10:11]:
        # if game['game_id'] not in [1056, 1070, 1064]:
        # if game['game_id'] not in [1070, 1073, 1040, 1247]:
        # if game['game_id'] not in [1064]:
            # continue
        print(game['game_id'])
        print()
        cnt += 1

        it, _, _ = build_interval_tree(game)

        skr_sit = reconstruct_skater_situation(game)
        prev_skr_sit = ''
        for t in skr_sit:
            if skr_sit[t] != prev_skr_sit:
                print(t, skr_sit[t])
                prev_skr_sit = skr_sit[t]

        # for interval in sorted(it, reverse=True):
        #     print(interval)

        # time_dict, goal_times = reconstruct_skater_situation(game)

        # for t in time_dict:
        #     print(t, time_dict[t])
