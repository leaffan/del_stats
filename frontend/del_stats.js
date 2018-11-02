angular.module('delStatsApp', [])

    .controller('mainController', function ($scope, $http) {
        // default table selection and sort criterion for skater page
        $scope.tableSelect = 'basic_stats';
        $scope.sortCriterion = 'points';
        // default sort order is descending
        $scope.statsSortDescending = true;

        // default filter values
        $scope.nameFilter = ''; // empty name filter
        $scope.teamFilter = ''; // empty name filter

        $scope.changeTable = function () {
            if ($scope.tableSelect === 'player_information') {
                $scope.sortCriterion = 'last_name';
                $scope.statsSortDescending = false;
            } else if ($scope.tableSelect === 'basic_stats') {
                $scope.sortCriterion = 'points';
                $scope.statsSortDescending = true;
            } else if ($scope.tableSelect === 'per_game_stats') {
                $scope.sortCriterion = 'points_per_game';
                $scope.statsSortDescending = true;
            } else if ($scope.tableSelect === 'time_on_ice_shift_stats') {
                $scope.sortCriterion = 'time_on_ice_seconds';
                $scope.statsSortDescending = true;
            } else if ($scope.tableSelect === 'power_play_stats') {
                $scope.sortCriterion = 'time_on_ice_pp_seconds';
                $scope.statsSortDescending = true;
            } else if ($scope.tableSelect === 'additional_stats') {
                $scope.sortCriterion = 'faceoff_pctg';
                $scope.statsSortDescending = true;
            } else if ($scope.tableSelect === 'per_60_stats') {
                $scope.sortCriterion = 'points_per_60';
                $scope.statsSortDescending = true;
            }
        };

        // setting column sort order according to current and new sort criteria, and current sort order 
        $scope.setSortOrder = function (sortCriterion, oldSortCriterion, oldStatsSortDescending) {
            // if current criterion equals the new one
            if (oldSortCriterion === sortCriterion) {
                // just change sort direction
                return !oldStatsSortDescending;
            } else {
                // ascending for a few columns
                if ([
                        'goals', 'assists', 'shots_on_goal', 'shot_pctg',
                        'points', 'game_played', 'points_per_game', 'goals_per_game',
                        'assists_per_game', 'primary_assists_per_game',
                        'secondary_assists_per_game', 'shots_on_goal_per_game',
                        'shots_on_goal_per_60', 'points_per_60', 'goals_per_60',
                        'primary_assists_per_60', 'secondary_assists_per_60',
                        'assists_per_60', 'time_on_ice_seconds',
                        'time_on_ice_pp_seconds', 'time_on_ice_sh_seconds', 'shifts',
                        'time_on_ice_per_game_seconds', 'shifts_per_game',
                        'time_on_ice_pp_per_game_seconds',
                        'time_on_ice_sh_per_game_seconds',
                        'pp_goals', 'pp_assists', 'pp_points',
                        'pp_goals_per_60', 'pp_assists_per_60', 'pp_points_per_60',
                        'shots', 'shots_missed', 'shots_blocked', 'faceoffs',
                        'faceoffs_lost', 'faceoffs_won', 'faceoff_pctg',
                        'blocked_shots'
                    ].indexOf(sortCriterion) !== -1) {
                    return true;
                } else {
                    // otherwise descending sort order
                    return false;
                }
            }
        };

        $scope.greaterThan = function (prop, val) {
            return function (item) {
                return item[prop] > val;
            }
        }

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

        // $scope.countryFilter = function (a) {
        //     if ($scope.countrySelect) {
        //         if (a.country == $scope.country) {
        //             return false;
        //         } else {
        //             return true;
        //         }
        //     } else {
        //         return true;
        //     }
        // }

        // loading stats from external json file
        $http.get('del_player_game_stats_aggregated.json').then(function (res) {
            $scope.last_modified = res.data[0];
            $scope.stats = res.data[1];
        });


    });