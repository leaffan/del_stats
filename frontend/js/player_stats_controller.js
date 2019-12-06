app.controller('plrStatsController', function ($scope, $http, $routeParams, svc) {

    $scope.svc = svc;
    $scope.season = $routeParams.season;
    // default table selection and sort criterion for skater page
    $scope.tableSelect = 'basic_stats';
    $scope.seasonTypeFilter = 'RS';
    $scope.scoringStreakTypeFilter = 'points';
    $scope.showStrictStreaks = true;
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

	$scope.readCSV = function() {
		// http get request to read CSV file content
        $http.get('/data/' + $scope.season + '/del_player_game_stats.csv').then($scope.processData);
	};

	$scope.processData = function(allText) {
        // split content based on new line
		var allTextLines = allText.data.split(/\r\n|\n/);
		var headers = allTextLines[0].split(';');
		var lines = [];

		for ( var i = 0; i < allTextLines.length; i++) {
			// split content based on separator
			var data = allTextLines[i].split(';');
			if (data.length == headers.length) {
				var tarr = [];
				for ( var j = 0; j < headers.length; j++) {
                    tarr.push(data[j]);
				}
				lines.push(tarr);
			}
        }
        var headers = lines[0];
        $scope.player_games = lines.slice(1).map(function(line) {
            return line.reduce(function(player_game, value, i) {
                if ($scope.svc.player_stats_to_aggregate().indexOf(headers[i]) !== -1) {
                    player_game[headers[i]] = parseInt(value);
                } else {
                    player_game[headers[i]] = value;
                }
                return player_game;
            }, {})
        });
        console.log($scope.player_games);
	};

    $scope.readCSV();

    $scope.filterStats() = function(stats) {
        filtered_player_stats = {};
        if ($scope.player_games === undefined)
            return filtered_player_stats;
        $scope.player_games.forEach(element => {
            plr_id = element['player_id'];
            if (!filtered_player_stats[plr_id]) {
                filtered_player_stats[plr_id] = {};
                filtered_player_stats[plr_id]['first_name'] = element['first_name'];
                filtered_player_stats[plr_id]['last_name'] = element['last_name'];
                $scope.svc.player_stats_to_aggregate().forEach(category => {
                    filtered_player_stats[plr_id][category] = 0;
                });
            }
            // determine filter status
            

        });
    }

    // loading strictly defined player scoring streaks from external json file
    $http.get('data/' + $scope.season + '/del_streaks_strict.json').then(function (res) {
        $scope.strict_streaks = res.data;
        $scope.streaks = $scope.strict_streaks;
    });
    // loading loosely defined player scoring streaks from external json file
    $http.get('data/' + $scope.season + '/del_streaks_loose.json').then(function (res) {
        $scope.loose_streaks = res.data;
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
    };

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
    };

    $scope.changeStreakType = function() {
        if ($scope.showStrictStreaks) {
            $scope.streaks = $scope.strict_streaks;
        } else {
            $scope.streaks = $scope.loose_streaks;
        }
    };

});