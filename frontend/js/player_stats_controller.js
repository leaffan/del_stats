app.controller('plrStatsController', function ($scope, $http, $routeParams, svc) {

    $scope.svc = svc;
    $scope.season = $routeParams.season;
    // default table selection and sort criterion for skater page
    $scope.tableSelect = 'basic_stats';
    $scope.seasonTypeFilter = 'RS';
    $scope.scoringStreakTypeFilter = 'points';
    $scope.u23Check = false;
    // setting default sort configuration
    $scope.sortConfig = {
        'sortKey': 'points',
        'sortCriteria': ['points', '-games_played', 'goals', 'primary_points'],
        'sortDescending': true
    }

    // loading stats from external json file
    $http.get('data/' + $scope.season + '/del_player_game_stats_aggregated.json').then(function (res) {
        $scope.last_modified = res.data[0];
        $scope.stats = res.data[1];
    });

    // loading player scoring streaks from external json file
    $http.get('data/' + $scope.season + '/del_streaks.json').then(function (res) {
        $scope.streaks = res.data;
    });

    // retrieving column headers (and abbreviations + explanations)
    $http.get('./js/player_stats_columns.json').then(function (res) {
        $scope.stats_cols = res.data;
    });

    // default filter values
    $scope.nameFilter = ''; // empty name filter
    $scope.teamFilter = ''; // empty name filter

    // default sorting criteria for all defined tables
    $scope.tableSortCriteria = {
        'player_information': 'last_name',
        'streaks': 'length',
        'basic_stats': 'points',
        'on_goal_shot_zones': 'shots_on_goal',
        'shot_zones': 'shots',
        'per_game_stats': 'points_per_game',
        'time_on_ice_shift_stats': 'time_on_ice_seconds',
        'power_play_stats': 'time_on_ice_pp_seconds',
        'penalty_stats': 'pim_from_events',
        'additional_stats': 'faceoff_pctg',
        'on_ice_stats': 'plus_minus',
        'per_60_stats': 'points_per_60',
        'goalie_stats': 'save_pctg',
        'goalie_stats_ev': 'save_pctg_5v5',
        'goalie_stats_sh': 'save_pctg_4v5',
        'goalie_stats_pp': 'save_pctg_5v4',
        'goalie_zone_stats_near': 'save_pctg_slot',
        'goalie_zone_stats_far': 'save_pctg_blue_line'
    }

    // sorting attributes to be used in ascending order
    $scope.ascendingAttrs = [
        'last_name', 'team', 'position', 'shoots',
        'date_of_birth', 'iso_country', 'gaa', 'from_date', 'to_date'
    ];

    // actual sorting criteria for various sorting attributes, including
    // criteria for tie breaking
    $scope.sortCriteria = {
        "last_name": ['last_name', 'team'],
        "points": ['points', '-games_played', 'goals', 'primary_points'],
        "assists": ['assists', '-games_played', 'primary_assists'],
        "goals": ['goals', '-games_played', 'points'],
        "games_played": ['games_played', '-team'],
        "length": ['length', 'points', 'from_date'],
        "save_pctg_blue_line": ['save_pctg_blue_line', 'sa_blue_line'],
        'save_pctg_slot': ['save_pctg_slot', 'sa_slot'],
        'save_pctg_5v4': ['save_pctg_5v4', 'sa_5v4'],
        'save_pctg_4v5': ['save_pctg_4v5', 'sa_4v5'],
        'save_pctg_5v5': ['save_pctg_5v5', 'sa_5v5'],
        'save_pctg': ['save_pctg', 'shots_against', 'toi'],
        'points_per_60': ['points_per_60', 'time_on_ice_seconds'],
        'shots_on_goal': ['shots_on_goal', 'slot_on_goal_pctg', 'slot_on_goal'],
        'shots': ['shots', 'slot_pctg', 'slot_shots'],
        'points_per_game': ['points_per_game', 'primary_points_per_game'],
        'time_on_ice_seconds': ['time_on_ice_seconds', 'shifts'],
        'time_on_ice_pp_seconds': ['time_on_ice_pp_seconds', 'pp_goals_per_60'],
        'pim_from_events': ['pim_from_events', '-games_played'],
        'faceoff_pctg': ['faceoff_pctg', 'faceoffs'],
        'plus_minus': ['plus_minus']
    };

    // changing sorting criteria according to table selected for display
    $scope.changeTable = function() {
        sortKey = $scope.tableSortCriteria[$scope.tableSelect];
        if ($scope.ascendingAttrs.indexOf(sortKey) !== -1) {
            sortDescending = false;
        } else {
            sortDescending = true;
        }
        $scope.sortConfig = {
            'sortKey': sortKey,
            'sortCriteria': $scope.sortCriteria[sortKey],
            'sortDescending': sortDescending
        };
        console.log($scope.sortConfig);
    };

    // function to change sort order, actually just a wrapper around a service
    // function defined above
    $scope.setSortOrder = function(sortKey, oldSortConfig) {
        return svc.setSortOrder2(sortKey, oldSortConfig, $scope.sortCriteria, $scope.ascendingAttrs);
    };

    // filter definitions
    $scope.greaterThanFilter = function (prop, val) {
        return function (item) {
            return item[prop] > val;
        }
    }

    $scope.u23Filter = function(a) {
        if (!$scope.u23Check)
            return true;
        if ($scope.u23Check && a.u23) {
            return true;
        } else {
            return false;
        }
    };

    $scope.longestStreakFilter = function(a) {
        if (!$scope.showOnlyLongestStreak) {
            return true;
        }
        if ($scope.showOnlyLongestStreak && a.longest) {
            return true;
        } else {
            return false;
        }
    };

    $scope.currentStreakFilter = function(a) {
        if (!$scope.showOnlyCurrentStreak)
            return true;
        if ($scope.showOnlyCurrentStreak && a.current) {
            return true;
        } else {
            return false;
        }
    };

    $scope.minimumAgeFilter = function (a) {
        if ($scope.minimumAge) {
            if (a.age < $scope.minimumAge) {
                return false;
            } else {
                return true;
            }
        } else {
            return true;
        }
    }

    $scope.maximumAgeFilter = function (a) {
        if ($scope.maximumAge) {
            if (a.age > $scope.maximumAge) {
                return false;
            } else {
                return true;
            }
        } else {
            return true;
        }
    }
});