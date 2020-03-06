app.controller('previewController', function($scope, $http, $routeParams, $location, $anchorScroll, $timeout, $sce, svc) {
    $scope.svc = svc;
    $scope.Math = window.Math;
    $scope.season = $routeParams.season;
    $scope.current_game_id = $routeParams.game_id;

    // loading current game data from full schedule
    $http.get('data/'+ $scope.season + '/full_schedule.json').then(function (res) {
        $scope.games = res.data;
        $scope.games.forEach(game => {
            game['game_date'] = moment(game['start_date']);
        });
        // finding current game by game_id
        $scope.current_game = $scope.games.find(function(game) {
            return game['game_id'] == $scope.current_game_id;
        });
        // retrieving the date before game date
        // moment needs to be cloned first (by calling moment() on it) before subtracting a day
        $scope.previous_date = moment($scope.current_game['game_date']).subtract(1, 'days');
        $scope.current_home_team = $scope.current_game.home.name;
        $scope.current_road_team = $scope.current_game.guest.name;
        $scope.current_season = parseInt($scope.current_game.season);
        if ($scope.current_game.round == '1')
            $scope.season = $scope.season - 1;
        $scope.current_season = $scope.current_season.toString() + "/" + ($scope.current_season + 1 - 2000).toString();
        $scope.current_home_team_fixtures = $scope.games.filter(function(value, index, arr) {
            return value['status'] == 'BEFORE_MATCH' && ($scope.current_game.home.name == value['home']['name'] || $scope.current_game.home.name == value['guest']['name']);
        });
        $scope.current_home_vs_road_fixtures = $scope.current_home_team_fixtures.filter(function(value, index, arr) {
            return value['home']['name'] == $scope.current_game.guest.name || value['guest']['name'] == $scope.current_game.guest.name;
    	});
        $scope.current_road_team_fixtures = $scope.games.filter(function(value, index, arr) {
            return value['status'] == 'BEFORE_MATCH' && ($scope.current_game.guest.name == value['home']['name'] || $scope.current_game.guest.name == value['guest']['name']);
        });
        $scope.current_road_vs_home_fixtures = $scope.current_road_team_fixtures.filter(function(value, index, arr) {
            return value['home']['name'] == $scope.current_game.home.name || value['guest']['name'] == $scope.current_game.home.name;
        });
        $http.get('data/career_stats/per_team/'+ $scope.current_game.home.shortcut + '_stats.json').then(function (res) {
            $scope.home_career_stats = res.data;
        });
        $http.get('data/career_stats/per_team/'+ $scope.current_game.guest.shortcut + '_stats.json').then(function (res) {
            $scope.road_career_stats = res.data;
        });
        // loading stats from external json file
        $http.get('data/'+ $scope.season + '/del_team_game_stats.json').then(function (res) {
            $scope.last_modified = res.data[0];
            $scope.team_stats = res.data[1];
            // retrieving regular season team statistics
            $scope.full_season_stats = $scope.getSeasonStats($scope.team_stats, $scope.current_game, 'RS');
            $scope.home_season_stats = $scope.getSeasonStats($scope.team_stats, $scope.current_game, 'RS', 'home');
            $scope.road_season_stats = $scope.getSeasonStats($scope.team_stats, $scope.current_game, 'RS', 'road');
            $scope.game_log_home = $scope.team_stats.filter(function(value, index, arr) {
                // returning only regular season games of current home team
                // return value['season_type'] == 'RS' && value['team'] == $scope.current_game.home.shortcut;
                // returning all games of current home team
                return value['team'] == $scope.current_game.home.shortcut;
            });
            $scope.game_log_road = $scope.team_stats.filter(function(value, index, arr) {
                // returning only regular season games of current road team
                // return value['season_type'] == 'RS' && value['team'] == $scope.current_game.guest.shortcut;
                // returning all games of current home team
                return value['team'] == $scope.current_game.guest.shortcut;
            });
            $scope.game_log_home_vs_road = $scope.game_log_home.filter(function(value, index, arr) {
                return value['opp_team'] == $scope.current_game.guest.shortcut;
            });

            // if head-to-head game log is empty, i.e. no games between the current teams this season
            // then load it from previous season
            if ($scope.game_log_home_vs_road.length == 0) {
                $http.get('data/2018/del_team_game_stats.json').then(function (res) {
                    $scope.team_stats_last_season = res.data[1];
                    $scope.game_log_home_vs_road = $scope.team_stats_last_season.filter(function(value, index, arr) {
                        return value['team'] == $scope.current_game.home.shortcut && value['opp_team'] == $scope.current_game.guest.shortcut;
                    });
                });
            }

            $scope.game_log_road_vs_home = $scope.game_log_road.filter(function(value, index, arr) {
                return value['opp_team'] == $scope.current_game.home.shortcut;
            });

            // if head-to-head game log is empty, i.e. no games between the current teams this season
            // then load it from previous season
            if ($scope.game_log_road_vs_home.length == 0) {
                $http.get('data/2018/del_team_game_stats.json').then(function (res) {
                    $scope.team_stats_last_season = res.data[1];
                    $scope.game_log_road_vs_home = $scope.team_stats_last_season.filter(function(value, index, arr) {
                        return value['team'] == $scope.current_game.guest.shortcut && value['opp_team'] == $scope.current_game.home.shortcut;
                    });
                });
            }
        });
    });


    // loading game facts
    $http.get('data/'+ $scope.season + '/facts.json').then(function (res) {
        facts = res.data;
        $scope.facts = res.data[$scope.current_game_id] || {};
        // trusting each fact's html source
        for (var key in $scope.facts) {
            if ($scope.facts.hasOwnProperty(key)) {
                $scope.facts[key] = $sce.trustAsHtml($scope.facts[key]);
            }
        }
    });

    // setting average attendance for previous season
    // TODO: move to external file (arenas.json?)
    $scope.avg_attendance_last_season = {
        'EBB': 12026, 'KEC': 11573, 'MAN': 11422, 'DEG': 8531, 'AEV': 5481,
        'NIT': 5163, 'RBM': 4819, 'KEV': 4814, 'BHV': 4438, 'IEC': 4344,
        'STR': 4129, 'ING': 3883, 'SWW': 3576, 'WOB': 2815
    }

    $scope.sorting_config = {
        'h2h_recent_table': ['game_date'],
        'game_log_table': ['game_date'],
        'standings': ['-points', '-score_diff', '-score'],
        'powerplay_standings': ['-pp_pctg', '-pp_goals', 'opp_sh_goals'],
        'penalty_killing_standings': ['-pk_pctg', 'opp_pp_goals', '-sh_goals'],
        'goals_by_period_1_standings': ['-goals_1', '-goals_diff_1'],
        'goals_by_period_2_standings': ['-goals_2', '-goals_diff_2'],
        'goals_by_period_3_standings': ['-goals_3', '-goals_diff_3'],
        'faceoffs_standings': ['-faceoff_pctg', '-faceoffs_won'],
        'shots_for_standings': ['-shots_on_goal', '-goals'],
        'shots_on_goal_for_zones_standings': ['-sl_og_p', '-sl_og'],
        'shots_on_goal_against_zones_standings': ['sl_og_p_a', 'sl_og_a'],
        'attendance_standings': ['-util_capacity', '-attendance'],
        'penalties_standings': ['pim_per_game', 'penalties'],
        'scoring_rankings': ['-points', '-points_per_game', '-goals', '-primary_points'],
        'scoring_powerplay_rankings': ['-pp_points', '-pp_points_per_60', '-pp_goals'],
        'scoring_shorthanded_rankings': ['-sh_points', '-sh_points_per_60', '-sh_goals'],
        'plr_time_on_ice_shift_rankings': ['-time_on_ice_per_game_seconds', '-time_on_ice_seconds'],
        'plr_on_goal_shot_zones_rankings': ['-shots_on_goal', '-slot_on_goal'],
        'plr_faceoffs_rankings': ['-faceoff_pctg', '-faceoffs'],
        'plr_blocks_rankings': ['-blocked_shots', '-blocked_shots_per_game'],
        'plr_missed_rankings': ['-shots_missed', '-shots_missed_per_game'],
        'plr_plus_minus_pos_rankings': ['-plus_minus', 'games_played'],
        'plr_plus_minus_neg_rankings': ['plus_minus', 'games_played'],
        'goalie_stats_rankings': ['-save_pctg', 'gaa'],
        'goalie_zone_stats_rankings': ['-save_pctg_slot', 'sa_slot'],
        'rosters': ['jersey'],
        'coaches_rankings': ['-win_pctg', '-wins'],
        'streaks_goals': ['-length', '-goals'],
        'streaks_assists': ['-length', '-assists'],
        'streaks_points': ['-length', '-points'],
        'slot_shots_goals': ['-sl_og']
    }

    // retrieving column headers (and abbreviations + explanations)
    $http.get('./js/preview_columns.json').then(function (res) {
        $scope.stats_cols = res.data;
    });

    // loading teams from external json file
    $http.get('./js/teams.json').then(function (res) {
        $scope.teams = res.data;
        // creating lookup structures...
        // ...for team locations
        $scope.team_location_lookup = $scope.teams.reduce((o, key) => Object.assign(o, {[key.abbr]: key.location}), {});
        // ...for playoff participation indicator
        // $scope.team_playoff_lookup = $scope.teams.reduce((o, key) => Object.assign(o, {[key.abbr]: key.po}), {});
    });

    // loading arenas from external json file
    $http.get('./js/arenas.json').then(function (res) {
        $scope.arenas = res.data;
    });

    // loading h2h data from external json file
    $http.get('data/'+ $scope.season + '/h2h.json').then(function (res) {
        $scope.h2h = res.data;
    });

    // loading playoff series from external json file
    $http.get('data/po_series.json').then(function (res) {
        $scope.po_series = res.data;
    });
    
    // loading player scoring streaks from external json file
    $http.get('data/'+ $scope.season + '/del_streaks_loose.json').then(function (res) {
        $scope.streaks = res.data;
    });

    // loading coaches from external json file
    $http.get('data/'+ $scope.season + '/coaches.json').then(function (res) {
        $scope.coaches = res.data;
    });

    // loading aggregated player stats from external json file
    $http.get('data/'+ $scope.season + '/del_player_game_stats_aggregated.json').then(function (res) {
        $scope.last_modified = res.data[0];
        $scope.plr_stats = res.data[1];
    });

    $scope.getSeasonStats = function(stats, current_game, season_type, home_road_type) {
        full_team_stats = {};
        if (stats === undefined)
            return full_team_stats;
        stats.forEach(team_game => {
            team = team_game['team'];
            game_date = moment(team_game['game_date']);
            // don't include current team game element if game date was after the previewed game
            if (game_date.diff(current_game['game_date'], 'days') >= 0)
                return;
            if (team_game['season_type'] != season_type)
                return;
            // only retain home/road games if specified
            if (home_road_type && home_road_type != team_game['home_road'])
                return;
            if (!full_team_stats[team]) {
                full_team_stats[team] = {};
                full_team_stats[team]['team'] = team;
                full_team_stats[team]['capacity'] = 0;
                $scope.svc.stats_to_aggregate().forEach(category => {
                    full_team_stats[team][category] = 0;
                });
            };
            $scope.svc.stats_to_aggregate().forEach(category => {
                full_team_stats[team][category] += team_game[category];
            });
        });

        full_team_stats = Object.values(full_team_stats);

        full_team_stats.forEach(team_game => {
            // calculating score and goal differentials
            team_game['score_diff'] = team_game['score'] - team_game['opp_score'];
            team_game['goals_diff'] = team_game['goals'] - team_game['opp_goals'];
            team_game['goals_diff_1'] = team_game['goals_1'] - team_game['opp_goals_1'];
            team_game['goals_diff_2'] = team_game['goals_2'] - team_game['opp_goals_2'];
            team_game['goals_diff_3'] = team_game['goals_3'] - team_game['opp_goals_3'];
            // calculating points percentage
            if (team_game['games_played']) {
                team_game['pt_pctg'] = parseFloat((team_game['points'] / (team_game['games_played'] * 3.) * 100).toFixed(2));
            } else {
                team_game['pt_pctg'] = parseFloat((0).toFixed(2));
            }
            // calculating shot zone percentages
            if (team_game['shots']) {
                team_game['sl_p'] = parseFloat(((team_game['sl_sh'] / team_game['shots']) * 100).toFixed(2));
                team_game['lf_p'] = parseFloat(((team_game['lf_sh'] / team_game['shots']) * 100).toFixed(2));
                team_game['rg_p'] = parseFloat(((team_game['rg_sh'] / team_game['shots']) * 100).toFixed(2));
                team_game['bl_p'] = parseFloat(((team_game['bl_sh'] / team_game['shots']) * 100).toFixed(2));
            } else {
                team_game['sl_p'] = parseFloat((0).toFixed(2));
                team_game['lf_p'] = parseFloat((0).toFixed(2));
                team_game['rg_p'] = parseFloat((0).toFixed(2));
                team_game['bl_p'] = parseFloat((0).toFixed(2));
            }
            // calculating zone percentages for shots against
            if (team_game['opp_shots']) {
                team_game['sl_p_a'] = parseFloat(((team_game['sl_sh_a'] / team_game['opp_shots']) * 100).toFixed(2));
                team_game['lf_p_a'] = parseFloat(((team_game['lf_sh_a'] / team_game['opp_shots']) * 100).toFixed(2));
                team_game['rg_p_a'] = parseFloat(((team_game['rg_sh_a'] / team_game['opp_shots']) * 100).toFixed(2));
                team_game['bl_p_a'] = parseFloat(((team_game['bl_sh_a'] / team_game['opp_shots']) * 100).toFixed(2));
            } else {
                team_game['sl_p_a'] = parseFloat((0).toFixed(2));
                team_game['lf_p_a'] = parseFloat((0).toFixed(2));
                team_game['rg_p_a'] = parseFloat((0).toFixed(2));
                team_game['bl_p_a'] = parseFloat((0).toFixed(2));
            }
            // calculating shooting, save and zone percentages for shots on goal
            if (team_game['shots_on_goal']) {
                team_game['shot_pctg'] = parseFloat(((team_game['goals'] / team_game['shots_on_goal']) * 100).toFixed(2));
                team_game['opp_save_pctg'] = parseFloat(((team_game['opp_saves'] / team_game['shots_on_goal']) * 100).toFixed(2));
                team_game['sl_og_p'] = parseFloat(((team_game['sl_og'] / team_game['shots_on_goal']) * 100).toFixed(2));
                team_game['lf_og_p'] = parseFloat(((team_game['lf_og'] / team_game['shots_on_goal']) * 100).toFixed(2));
                team_game['rg_og_p'] = parseFloat(((team_game['rg_og'] / team_game['shots_on_goal']) * 100).toFixed(2));
                team_game['bl_og_p'] = parseFloat(((team_game['bl_og'] / team_game['shots_on_goal']) * 100).toFixed(2));
            } else {
                team_game['shot_pct'] = parseFloat((0).toFixed(2));
                team_game['opp_save_pct'] = parseFloat((0).toFixed(2));
                team_game['sl_og_p'] = parseFloat((0).toFixed(2));
                team_game['lf_og_p'] = parseFloat((0).toFixed(2));
                team_game['rg_og_p'] = parseFloat((0).toFixed(2));
                team_game['bl_og_p'] = parseFloat((0).toFixed(2));
            }
            // calculating opponent shooting, save and zone percentages for shots on goal against
            if (team_game['opp_shots_on_goal']) {
                team_game['opp_shot_pctg'] = parseFloat(((team_game['opp_goals'] / team_game['opp_shots_on_goal']) * 100).toFixed(2));
                team_game['save_pctg'] = parseFloat(((team_game['saves'] / team_game['opp_shots_on_goal']) * 100).toFixed(2));
                team_game['sl_og_p_a'] = parseFloat(((team_game['sl_og_a'] / team_game['opp_shots_on_goal']) * 100).toFixed(2));
                team_game['lf_og_p_a'] = parseFloat(((team_game['lf_og_a'] / team_game['opp_shots_on_goal']) * 100).toFixed(2));
                team_game['rg_og_p_a'] = parseFloat(((team_game['rg_og_a'] / team_game['opp_shots_on_goal']) * 100).toFixed(2));
                team_game['bl_og_p_a'] = parseFloat(((team_game['bl_og_a'] / team_game['opp_shots_on_goal']) * 100).toFixed(2));
            } else {
                team_game['opp_shot_pct'] = parseFloat((0).toFixed(2));
                team_game['save_pct'] = parseFloat((0).toFixed(2));
                team_game['sl_og_p_a'] = parseFloat((0).toFixed(2));
                team_game['lf_og_p_a'] = parseFloat((0).toFixed(2));
                team_game['rg_og_p_a'] = parseFloat((0).toFixed(2));
                team_game['bl_og_p_a'] = parseFloat((0).toFixed(2));
            }
            // calculating PDO
            team_game['pdo'] = parseFloat((parseFloat(team_game['shot_pctg']) + parseFloat(team_game['save_pctg'])).toFixed(2));
            team_game['opp_pdo'] = parseFloat((parseFloat(team_game['opp_shot_pctg']) + parseFloat(team_game['opp_save_pctg'])).toFixed(2));
            // calculating shots on goal for percentage
            if (team_game['shots_on_goal'] + team_game['opp_shots_on_goal']) {
                team_game['shot_for_pctg'] = parseFloat((team_game['shots_on_goal'] / (team_game['shots_on_goal'] + team_game['opp_shots_on_goal']) * 100).toFixed(2));
                team_game['opp_shot_for_pctg'] = parseFloat((team_game['opp_shots_on_goal'] / (team_game['shots_on_goal'] + team_game['opp_shots_on_goal']) * 100).toFixed(2));
            } else {
                team_game['shot_for_pctg'] = parseFloat((0).toFixed(2));
                team_game['opp_shot_for_pctg'] = parseFloat((0).toFixed(2));
            }
            // calculating unblocked shots (i.e. Fenwick) for percentage
            team_game['fenwick_events'] = team_game['shots_on_goal'] + team_game['shots_missed']; 
            team_game['opp_fenwick_events'] = team_game['opp_shots_on_goal'] + team_game['opp_shots_missed']; 
            if (team_game['fenwick_events'] + team_game['opp_fenwick_events']) {
                team_game['fenwick_for_pctg'] = parseFloat(((team_game['fenwick_events']) / (team_game['fenwick_events' ]+ team_game['opp_fenwick_events']) * 100).toFixed(2));
                team_game['opp_fenwick_for_pctg'] = parseFloat(((team_game['opp_fenwick_events']) / (team_game['fenwick_events' ]+ team_game['opp_fenwick_events']) * 100).toFixed(2));
            } else {
                team_game['fenwick_for_pctg'] = parseFloat((0).toFixed(2));
                team_game['opp_fenwick_for_pctg'] = parseFloat((0).toFixed(2));
            }
            // calculating shots (i.e. Corsi) for percentage
            if (team_game['shots'] + team_game['opp_shots']) {
                team_game['corsi_for_pctg'] = parseFloat((team_game['shots'] / (team_game['shots'] + team_game['opp_shots']) * 100).toFixed(2));
                team_game['opp_corsi_for_pctg'] = parseFloat((team_game['opp_shots'] / (team_game['shots'] + team_game['opp_shots']) * 100).toFixed(2));
            } else {
                team_game['corsi_for_pctg'] = parseFloat((0).toFixed(2));
                team_game['opp_corsi_for_pctg'] = parseFloat((0).toFixed(2));
            }
            // calculating power play percentage
            if (team_game['pp_opps']) {
                team_game['pp_pctg'] = parseFloat(((team_game['pp_goals'] / team_game['pp_opps']) * 100).toFixed(2));
            } else {
                team_game['pp_pctg'] = parseFloat((0).toFixed(2));
            }
            // calculating penalty killing percentage
            if (team_game['sh_opps']) {
                team_game['pk_pctg'] = parseFloat((100 - (team_game['opp_pp_goals'] / team_game['sh_opps']) * 100).toFixed(2));
            } else {
                team_game['pk_pctg'] = parseFloat((0).toFixed(2));
            }
            // calculating powerplay/penalty killing times per game
            if (team_game['games_played']) {
                team_game['pp_time_per_game'] = parseFloat((team_game['pp_time'] / team_game['games_played']).toFixed(2));
                team_game['pk_time_per_game'] = parseFloat((team_game['opp_pp_time'] / team_game['games_played']).toFixed(2));
            } else {
                team_game['pp_time_per_game'] = parseFloat((0).toFixed(2));
                team_game['pk_time_per_game'] = parseFloat((0).toFixed(2));
            }
            // calculating powerplay time per powerplay goal
            if (team_game['pp_goals']) {
                team_game['pp_time_per_pp_goal'] = parseFloat((team_game['pp_time'] / team_game['pp_goals']).toFixed(2));
            } else {
                team_game['pp_time_per_pp_goal'] = parseFloat((0).toFixed(2));
            }
            // calculating penalty killing time per opponent powerplay goal
            if (team_game['opp_pp_goals']) {
                team_game['pk_time_per_opp_pp_goal'] = parseFloat((team_game['opp_pp_time'] / team_game['opp_pp_goals']).toFixed(2));
            } else {
                team_game['pk_time_per_opp_pp_goal'] = parseFloat((0).toFixed(2));
            }
            // calculating special teams goal differential and combined special team percentages
            team_game['pp_pk_gdiff'] = team_game['pp_goals'] + team_game['sh_goals'] - team_game['opp_pp_goals'] - team_game['opp_sh_goals'];
            team_game['pp_pk_comb_pctg'] = team_game['pp_pctg'] + team_game['pk_pctg'];
            // calculating team faceoff percentage
            if (team_game['faceoffs']) {
                team_game['faceoff_pctg'] = parseFloat(((team_game['faceoffs_won'] / team_game['faceoffs']) * 100).toFixed(2));
            } else {
                team_game['faceoff_pctg'] = parseFloat((0).toFixed(2));
            }
            // calculating team penalty minutes per game
            if (team_game['games_played']) {
                team_game['pim_per_game'] = parseFloat((team_game['pim'] / team_game['games_played']).toFixed(2));
            } else {
                team_game['pim_per_game'] = parseFloat((0).toFixed(2));
            }
            // calculating average attendance per game
            if (home_road_type == 'home' && team_game['games_played']) {
                team_game['avg_attendance'] = parseFloat((team_game['attendance'] / team_game['games_played']).toFixed(0));
                // console.log(team_game['team'], home_road_type, team_game['avg_attendance'], team_game['capacity']);
            } else {
                team_game['avg_attendance'] = parseFloat((0).toFixed(2));
            }
            // calculating utilized capacity
            if (home_road_type == 'home' && team_game['games_played']) {
                team_game['util_capacity'] = parseFloat(((team_game['attendance'] / team_game['capacity']) * 100).toFixed(2));
                // console.log(home_road_type, team_game['util_capacity']);
            } else {
                team_game['util_capacity'] = parseFloat((0).toFixed(2));
            }
        });

        return full_team_stats;
    };

    $scope.scrollTo = function(id, to = 0) {
        // alert(id);
        var old = $location.hash();
        $timeout(function() {
            $location.hash(id);
            $anchorScroll();
        }, to);
        $location.hash(old);
    };

    if ($routeParams.anchor)
        $scope.scrollTo($routeParams.anchor, 500);

    // displaying only players with at least 10 faceoffs per game
    $scope.faceoffFilter = function(a) {
        if (!a['games_played']) {
            return false;
        };
        if (a['faceoffs'] / a['games_played'] < 10) {
            return false;
        };
        return true;
    };

    $scope.minPowerPlayPointsFilter = function(a) {
        if (!a['pp_points']) {
            return false;
        };
        if (a['pp_points'] < 1) {
            return false;
        };
        return true;
    };

    $scope.minShorthandedPointsFilter = function(a) {
        if (!a['sh_points']) {
            return false;
        };
        if (a['sh_points'] < 1) {
            return false;
        };
        return true;
    };

});
