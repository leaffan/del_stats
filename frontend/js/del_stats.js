var app = angular.module('delStatsApp', ['ngResource', 'ngRoute', 'ngStorage', 'moment-picker', 'angularMoment'])

// main application configuration

app.config(['$routeProvider', function($routeProvider){
    $routeProvider
        .when('/home', {
            title: 'DEL-Statistiken',
            templateUrl: 'home.html',
            controller: 'homeController as ctrl',
            reloadOnSearch: false
        })
        .when('/del_stats/:season', {
            title: 'Spielerstatistiken',
            templateUrl: 'player_stats.html',
            controller: 'plrStatsController as ctrl',
            reloadOnSearch: false
        })
        .when('/team_stats/:season', {
            title: 'Teamstatistiken',
            templateUrl: 'team_stats.html',
            controller: 'teamStatsController as ctrl',
            reloadOnSearch: false
        })
        .when('/player_profile/:season/:team/:player_id',
        {
            title: 'Spielerprofil',
            templateUrl: 'player_profile.html',
            controller: 'plrProfileController as ctrl',
            reloadOnSearch: false
        })
        .when('/team_profile/:season/:team/:table_select?',
        {
            title: 'Teamprofil',
            templateUrl: 'team_profile.html',
            controller: 'teamProfileController as ctrl',
            reloadOnSearch: false
        })
        .when('/career_stats',
        {
            title: 'Karrierestatistiken',
            templateUrl: 'career_stats.html',
            controller: 'careerStatsController as ctrl',
            reloadOnSearch: false
        })
        .when('/player_career/:player_id',
        {
            title: 'Karriereverlauf',
            templateUrl: 'player_career.html',
            controller: 'plrCareerController as ctrl',
            reloadOnSearch: false
        })
        .otherwise({
            redirectTo: '/home'
        })
}]);

app.config(['momentPickerProvider', function(momentPickerProvider){
    momentPickerProvider.options({
        locale: 'de',
        format: 'L',
        minView: 'decade',
        maxView: 'day',
        startView: 'month',
        autoclose: true,
        keyboard: true
    })
}]);

app.run(['$rootScope', function($rootScope) {
    $rootScope.$on('$routeChangeSuccess', function (event, current, previous) {
        // TODO: set page title dynamically to include current teams
        $rootScope.title = current.$$route.title;
    });
}]);

app.run(function(amMoment) {
	amMoment.changeLocale('de');
});

// providing functions to several controllers as services
app.factory('svc', function() {
    return {
        // sets sorting order according to selected sort criterion
        setSortOrder: function(sortCriterion, oldSortCriterion, oldStatsSortDescending, ascendingAttrs) {
            // if current criterion equals the new one
            if (oldSortCriterion === sortCriterion) {
                // just change sort direction
                return !oldStatsSortDescending;
            } else {
                // ascending for a few columns
                if (ascendingAttrs.indexOf(sortCriterion) !== -1) {
                    return false;
                } else {
                    // otherwise descending sort order
                    return true;
                }
            }
        },
        setSortOrder2: function(sortKey, oldSortConfig, globalSortConfig, ascendingAttrs) {
            // if previous sort key equals the new one
            if (oldSortConfig['sortKey'] == sortKey) {
                // just change sort direction
                return {
                    'sortKey': oldSortConfig['sortKey'],
                    'sortCriteria': oldSortConfig['sortCriteria'],
                    'sortDescending': !oldSortConfig['sortDescending']
                }
            } else {
                // ascending sort order for a few columns
                if (ascendingAttrs.indexOf(sortKey) !== -1) {
                    sortCriteria = globalSortConfig[sortKey] || sortKey;
                    return {
                        'sortKey': sortKey,
                        'sortCriteria': sortCriteria,
                        'sortDescending': false
                    }
                } else {
                    // otherwise descending sort order
                    sortCriteria = globalSortConfig[sortKey] || sortKey;
                    return {
                        'sortKey': sortKey,
                        'sortCriteria': sortCriteria,
                        'sortDescending': true
                    }
                }
            }
        },
        // formats time (in seconds) as mm:ss
        formatTime: function(timeInSeconds) {
            return this.pad(Math.floor(timeInSeconds / 60), 2) + ":" + ('00' + (Math.floor(timeInSeconds) % 60)).slice(-2);
        },
        // gets total sum of filtered attribute values
        getFilteredTotal: function(list, attribute, dataSource) {
            if (dataSource === undefined)
                return;
            if (list === undefined)
                return;
            var total = 0;
            for(var i = 0; i < list.length; i++){
                total += list[i][attribute];
            }
            return total;
        },
        // gets total sum of filtered attributed values through a specified game date
        getFilteredAccumulatedTotal: function(list, attribute, dataSource, to) {
            if (dataSource === undefined) {
                return
            }
            var total = 0;
            for (var i = list.length-1; i >= 0; i--) {
                total += list[i][attribute];
                if (list[i]['game_date'] == to)
                {
                    return total;
                }
            }
            return total;
        },
        // gets average of filtered attributed values through a specified game date
        getFilteredAverageTotal: function(list, attribute, dataSource, to) {
            if (dataSource === undefined) {
                return;
            }
            var total = 0;
            var cnt_data = 0;
            for (var i = list.length-1; i >= 0; i--) {
                cnt_data++;
                total += list[i][attribute];
                
                if (list[i]['game_date'] == to)
                {
                    return total / cnt_data;
                }
            }
            return total / cnt_data;
        },
        parseFloat: function(floatAsString) {
            return parseFloat(floatAsString);
        },
        parseInt: function(intAsString) {
            return parseInt(intAsString);
        },
        isNumeric: function(num) {
            return !isNaN(num);
        },
        replaceRoundNames: function(roundName, short) {
            if (roundName === undefined)
                return;
            if (!isNaN(roundName))
                return roundName;
            if (short) {
                return roundName.replace(
                    "first_round_", "1. PR "
                ).replace(
                    "quarter_finals_", "VF "
                ).replace(
                    "semi_finals_", "HF "
                ).replace(
                    "finals_", "F ");
            } else {
                return roundName.replace(
                    "first_round_", "1. Playoff-Runde "
                ).replace(
                    "quarter_finals_", "Viertelfinale "
                ).replace(
                    "semi_finals_", "Halbfinale "
                ).replace(
                    "finals_", "Finale ");
            }
        },     
        setTextColor: function(score, opp_score) {
            if (score > opp_score) {
                return " green";
            }
            else if (opp_score > score) {
                return " red";
            }
            else {
                return "";
            }
        },
        range: function(min, max, step) {
            step = step || 1;
            var input = [];
            for (var i = min; i <= max; i += step) {
                input.push(i);
            }
            return input;
        },
        // team stats to be simply aggregated
        stats_to_aggregate: function() {
            return [
                'games_played', 'score', 'opp_score', 'goals', 'opp_goals',
                'w', 'rw', 'ow', 'sw', 'l', 'rl', 'ol', 'sl', 'points', 'goals_1',
                'opp_goals_1', 'goals_2', 'opp_goals_2', 'goals_3', 'opp_goals_3',
                'shots', 'shots_on_goal', 'shots_missed', 'shots_blocked',
                'opp_shots', 'opp_shots_on_goal', 'opp_shots_missed',
                'opp_shots_blocked', 'saves', 'opp_saves', 'pim', 'pp_time',
                'pp_opps', 'pp_goals', 'opp_pim', 'opp_pp_time', 'opp_pp_opps',
                'opp_pp_goals', 'sh_opps', 'sh_goals', 'opp_sh_opps', 'opp_sh_goals',
                'faceoffs_won', 'faceoffs_lost', 'faceoffs', 'sl_sh', 'lf_sh', 'rg_sh',
                'bl_sh', 'sl_og', 'lf_og', 'rg_og', 'bl_og', 'sl_sh_a', 'lf_sh_a',
                'rg_sh_a', 'bl_sh_a', 'sl_og_a', 'lf_og_a', 'rg_og_a', 'bl_og_a',
                'attendance', 'penalty_2', 'penalty_5', 'penalty_10', 'penalty_20',
                'shots_on_goal_5v5', 'goals_5v5', 'opp_shots_on_goal_5v5', 'opp_goals_5v5',
                'capacity', 'sl_g', 'tied', 'leading', 'trailing', 'time_played',
                'shots_5v5', 'opp_shots_5v5', 'shots_unblocked_5v5', 'opp_shots_unblocked_5v5',
                'so_rounds', 'so_a', 'so_g', 'opp_so_a', 'opp_so_g', 'hit_post', 'opp_hit_post',
                'pp_5v4', 'ppg_5v4', 'pp_5v3', 'ppg_5v3', 'pp_4v3', 'ppg_4v3',
                'opp_pp_5v4', 'opp_ppg_5v4', 'opp_pp_5v3', 'opp_ppg_5v3', 'opp_pp_4v3', 'opp_ppg_4v3'
            ];    
        },
        player_stats_to_aggregate: function() {
            return [
                'assists', 'blocked_shots', 'faceoffs', 'faceoffs_lost', 'faceoffs_won',
                'first_goals', 'games_played', 'goals', 'goals_5v5', 'assists_5v5', 'points_5v5',
                'primary_assists_5v5', 'primary_points_5v5', 'secondary_assists_5v5', 'gw_goals', 'lazy',
                'minus', 'other', 'penalties', 'penalty_shots', 'pim', 'pim_from_events',
                'plus', 'plus_minus', 'points', 'pp_points', 'pp_goals', 'pp_assists',
                'pp_primary_assists', 'pp_secondary_assists', 'primary_assists', 'primary_points',
                'reckless', 'roughing', 'secondary_assists', 'sh_assists', 'sh_goals', 'sh_points',
                'shifts', 'shots', 'shots_5v5', 'shots_blocked', 'shots_missed', 'shots_missed_5v5',
                'shots_on_goal', 'shots_on_goal_5v5', 'time_on_ice', 'time_on_ice_pp', 'time_on_ice_sh',
                '_2min', '_5min', '_10min', '_20min', 'slot_shots', 'left_shots', 'right_shots',
                'blue_line_shots', 'slot_on_goal', 'left_on_goal', 'right_on_goal', 'blue_line_on_goal',
                'neutral_zone_shots', 'neutral_zone_on_goal', 'neutral_zone_goals', 'behind_goal_shots',
                'behind_goal_on_goal', 'behind_goal_goals', 'goals_5v5_from_events',
                'on_ice_sh_f', 'on_ice_sh_a', 'on_ice_unblocked_sh_f', 'on_ice_unblocked_sh_a',
                'on_ice_sh_f_5v5', 'on_ice_sh_a_5v5', 'on_ice_unblocked_sh_f_5v5', 'on_ice_unblocked_sh_a_5v5',
                'on_ice_sog_f', 'on_ice_sog_a', 'on_ice_goals_f', 'on_ice_goals_a',
                'on_ice_sog_f_5v5', 'on_ice_sog_a_5v5', 'on_ice_goals_f_5v5', 'on_ice_goals_a_5v5',
                'nzone_faceoffs', 'nzone_faceoffs_won', 'nzone_faceoffs_lost',
                'ozone_faceoffs', 'ozone_faceoffs_won', 'ozone_faceoffs_lost',
                'dzone_faceoffs', 'dzone_faceoffs_won', 'dzone_faceoffs_lost',
                'left_side_faceoffs', 'left_side_faceoffs_won', 'left_side_faceoffs_lost',
                'right_side_faceoffs', 'right_side_faceoffs_won', 'right_side_faceoffs_lost',
                'so_games_played', 'so_attempts', 'so_goals', 'so_gw_goals',
                'go_ahead_g', 'tying_g', 'clutch_g', 'blowout_g', 'w_winning_g', 'w_losing_g', 'hit_post',
                'empty_net_goals'
            ];
        },
        player_float_stats_to_aggregate: function() {
            return ['game_score'];
        },
        goalie_stats_to_aggregate: function() {
            return [
                'games_dressed', 'games_played', 'games_started', 'toi', 'of_record',
                'w', 'rw', 'ow', 'sw', 'l', 'rl', 'ol', 'sl', 'shots_against', 'goals_against',
                'sa_5v5', 'sa_4v4', 'sa_3v3', 'sa_5v4', 'sa_5v3', 'sa_4v3', 'sa_4v5', 'sa_3v4', 'sa_3v5',
                'ga_5v5', 'ga_4v4', 'ga_3v3', 'ga_5v4', 'ga_5v3', 'ga_4v3', 'ga_4v5', 'ga_3v4', 'ga_3v5',
                'sa_blue_line', 'sa_left', 'sa_right', 'sa_slot', 'sa_neutral_zone',
                'ga_blue_line', 'ga_left', 'ga_right', 'ga_slot', 'ga_neutral_zone',
                'sa_ev', 'ga_ev', 'sa_sh', 'ga_sh', 'sa_pp', 'ga_pp', 'so',
                'ga_avg', 'gsaa', 'ga_avg_5v5', 'gsaa_5v5',
                'so_games_played', 'so_attempts_a', 'so_goals_a'
            ];    
        },
        pad: function pad(num, size) {
            var s = num+"";
            while (s.length < size) s = "0" + s;
            return s;
        },
        germanDays: function() {
            return [0, 1, 2, 3, 4, 5, 6].map(day => moment().locale('de').weekday(day).format('dddd'));
        },
        germanMonths: function() {
            return [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11].map(month => moment().locale('de').month(month).format('MMMM'));
        },
        shortenName: function(full_name) {
            if (!full_name) {
                return '';
            }
            var names = full_name.split(' ');
            return names[0][0] + '. ' + names.slice(-1)[0];
        },
        calculateRate: function(value_to_rate, rating_parameter) {
            if (rating_parameter) {
                return value_to_rate / rating_parameter;
            } else {
                return 0;
            }
        },
        calculatePercentage: function(part_value, base_value, factor, return_null) {
            if (factor === undefined)
                factor = 1
            if (base_value) {
                return (part_value / (base_value * factor)) * 100
            } else {
                if (return_null) {
                    return null;
                } else {
                    return 0;
                }
            }
        },
        calculateFrom100Percentage: function(part_value, base_value, factor) {
            if (factor === undefined)
                factor = 1
            if (base_value) {
                return 100 - (part_value / (base_value * factor)) * 100
            } else {
                return null;
            }
        },
        calculatePer60: function(value, toi_seconds) {
            if (toi_seconds) {
                return value / (toi_seconds / 60) * 60;
            } else {
                return 0;
            }
        }
    }
});
