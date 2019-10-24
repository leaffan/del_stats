var app = angular.module('delStatsApp', ['ngResource', 'ngRoute', 'ngStorage', 'moment-picker', 'angularMoment'])

// main application configuration

app.config(['$routeProvider', function($routeProvider){
    $routeProvider
        .when('/home', {
            title: 'DEL-Statistiken',
            templateUrl: 'home.html',
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
            return Math.floor(timeInSeconds / 60) + ":" + ('00' + (Math.floor(timeInSeconds) % 60)).slice(-2);
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
                'capacity', 'sl_g', 'tied', 'leading', 'trailing', 'time_played'
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
        }
    }
});
