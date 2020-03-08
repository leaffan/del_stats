app.controller('teamStatsController', function($scope, $http, $routeParams, svc) {

    $scope.svc = svc;
    var ctrl = this;
    $scope.season = $routeParams.season;
    // setting default table selection and sort keys and criteria/order
    $scope.tableSelect = 'standings';
    $scope.seasonTypeSelect = 'RS'
    $scope.isStandingsView = true;
    $scope.isAttendanceView = false;
    $scope.sort_def = {
        // standings
        "points": ['points', 'score_diff', 'score'],
        "games_played": ['games_played', '-team'],
        // goal stats
        "goals_diff": ['goals_diff', 'goals'],
        "goals_diff_1": ['goals_diff_1', 'goals_1'],
        "goals_diff_2": ['goals_diff_2', 'goals_2'],
        "goals_diff_3": ['goals_diff_3', 'goals_3'],
        "goals_1": ['goals_1', 'goals_diff_1'],
        "goals_2": ['goals_2', 'goals_diff_2'],
        "goals_3": ['goals_3', 'goals_diff_3'],
        "opp_goals_1": ['opp_goals_1', '-goals_diff_1'],
        "opp_goals_2": ['opp_goals_2', '-goals_diff_2'],
        "opp_goals_3": ['opp_goals_3', '-goals_diff_3'],
        // shots
        "opp_shots_on_goal": ['opp_shots_on_goal', 'games_played'],
        "opp_shots": ['opp_shots', 'games_played'],
        "shots_on_goal": ['shots_on_goal', 'goals', 'games_played'],
        "shots": ['shots', 'games_played'],
        "faceoff_pctg": ['faceoff_pctg', 'faceoffs'],
        // special team stats
        "pp_pctg": ['pp_pctg', '-pp_opps'],
        "pp_goals": ['pp_goals', 'pp_pctg'],
        "sh_goals": ['sh_goals', '-sh_opps'],
        "opp_pp_goals": ['opp_pp_goals', '-pk_pctg'],
        "opp_sh_goals": ['opp_sh_goals', '-sh_opps'],
        // shot shares
        "corsi_for_pctg": ['corsi_for_pctg', 'shots'],
        "shots_on_goal_5v5": ['shots_on_goal_5v5', 'goals_5v5', '-games_played'],
        "goals_diff": ['goals_diff', 'goals', '-games_played'],
        "pt_pctg": ['pt_pctg', 'points', 'goals_diff', '-games_played']
    };
    $scope.sortConfig = {
        'sortKey': 'points',
        'sortCriteria': ['points', 'score_diff', 'score'],
        'sortDescending': true
    }
    $scope.fromRoundSelect = '1';

    // retrieving column headers (and abbreviations + explanations)
    $http.get('./js/team_stats_columns.json').then(function (res) {
        $scope.stats_cols = res.data;
    });

    // retrieving significant dates and previous year's attendance from external file
    $http.get('./data/' + $scope.season + '/dates_attendance.json').then(function (res) {
        $scope.dcup_date = moment(res.data['dates']['dcup_date']);
        $scope.avg_attendance_last_season = res.data['avg_attendance_last_season'];
    });

    // retrieving teams
    $http.get('./js/teams.json').then(function (res) {
        $scope.teams = res.data;
        // creating lookup structures...
        // ...for team locations
        $scope.team_location_lookup = $scope.teams.reduce((o, key) => Object.assign(o, {[key.abbr]: key.location}), {});
        // ...for playoff participation indicator
        $scope.team_playoff_lookup = $scope.teams.reduce((o, key) => Object.assign(o, {[key.abbr]: key.po[$scope.season]}), {});
    });

    // starting to watch filter selection lists
    $scope.$watchGroup([
            'situationSelect', 'homeAwaySelect', 'seasonTypeSelect',
            'fromRoundSelect', 'toRoundSelect', 'weekdaySelect', 'timespanSelect'
        ], function() {
        if ($scope.team_stats) {
            $scope.filtered_team_stats = $scope.filterStats($scope.team_stats);
        }
    }, true);

    // loading stats from external json file
    $http.get('data/' + $scope.season + '/del_team_game_stats.json').then(function (res) {
        $scope.last_modified = res.data[0];
        $scope.team_stats = res.data[1];
        // retrieving maximum round played
        $scope.maxRoundPlayed = Math.max.apply(Math, $scope.team_stats.map(function(o) { return o.round; })).toString();
        // retrieving all weekdays a game was played by the current team
        $scope.weekdaysPlayed = [...new Set($scope.team_stats.map(item => item.weekday))].sort();
        // retrieving all months a game was played by the current team
        $scope.monthsPlayed = [...new Set($scope.team_stats.map(item => moment(item.game_date).month()))];
        // setting to round selection to maximum round played
        $scope.toRoundSelect = $scope.maxRoundPlayed;
        $scope.filtered_team_stats = $scope.filterStats($scope.team_stats);
    });

    // TODO: move to out-of-controller location
    $scope.filterStats = function (stats) {
        filtered_team_stats = {};
        if ($scope.team_stats === undefined)
            return filtered_team_stats;
        $scope.team_stats.forEach(element => {
            team = element['team'];
            if (!filtered_team_stats[team]) {
                // leaving out non-playoff teams in playoff standings
                if ($scope.seasonTypeSelect != 'PO' || $scope.team_playoff_lookup[team]) {
                    filtered_team_stats[team] = {};
                    filtered_team_stats[team]['team'] = team;
                    $scope.svc.stats_to_aggregate().forEach(category => {
                        filtered_team_stats[team][category] = 0;
                    });
                }
            }
            is_equal_past_from_date = false;
            is_prior_equal_to_date = false;
            is_selected_home_away_type = false;
            is_selected_game_situation = false;
            is_selected_season_type = false;
            is_selected_weekday = false;
            is_equal_past_from_round = false;
            is_prior_equal_to_round = false;

            // retrieving game date as moment structure
            date_to_test = moment(element.game_date);

            if (ctrl.fromDate) {
                if (date_to_test >= ctrl.fromDate.startOf('day'))
                    is_equal_past_from_date = true;
            } else {
                is_equal_past_from_date = true;
            }
            if (ctrl.toDate) {
                if (date_to_test <= ctrl.toDate.startOf('day'))
                    is_prior_equal_to_date = true;
            } else {
                is_prior_equal_to_date = true;
            }
            if ($scope.homeAwaySelect) {
                if ($scope.homeAwaySelect === element.home_road)
                    is_selected_home_away_type = true;
            } else {
                is_selected_home_away_type = true;
            }
            if ($scope.situationSelect) {
                if (element[$scope.situationSelect])
                    is_selected_game_situation = true;
            } else {
                is_selected_game_situation = true;
            }
            if ($scope.seasonTypeSelect) {
                if ($scope.seasonTypeSelect === element.season_type)
                    is_selected_season_type = true;
            } else {
                is_selected_season_type = true;
            }
            if ($scope.weekdaySelect) {
                if ($scope.weekdaySelect == element.weekday)
                    is_selected_weekday = true;
            } else {
                is_selected_weekday = true;
            }
            if ($scope.fromRoundSelect) {
                if (element.round >= parseFloat($scope.fromRoundSelect))
                    is_equal_past_from_round = true;
            } else {
                is_equal_past_from_round = true;
            }
            if ($scope.toRoundSelect) {
                if (element.round <= parseFloat($scope.toRoundSelect))
                    is_prior_equal_to_round = true;
            } else {
                is_prior_equal_to_round = true;
            }

            // finally aggregating values of all season stat lines that have been filtered
            if (
                is_equal_past_from_date && is_prior_equal_to_date &&
                is_selected_home_away_type && is_selected_game_situation &&
                is_selected_season_type && is_selected_weekday &&
                is_equal_past_from_round && is_prior_equal_to_round
            ) {
                $scope.svc.stats_to_aggregate().forEach(category => {
                    filtered_team_stats[team][category] += element[category];
                })
            }
        });
        filtered_team_stats = Object.values(filtered_team_stats);

        filtered_team_stats.forEach(element => {
            // calculating score and goal differentials
            element['score_diff'] = element['score'] - element['opp_score'];
            element['goals_diff'] = element['goals'] - element['opp_goals'];
            element['goals_diff_1'] = element['goals_1'] - element['opp_goals_1'];
            element['goals_diff_2'] = element['goals_2'] - element['opp_goals_2'];
            element['goals_diff_3'] = element['goals_3'] - element['opp_goals_3'];
            // calculating points percentage
            if (element['games_played']) {
                element['pt_pctg'] = parseFloat((element['points'] / (element['games_played'] * 3.) * 100).toFixed(2));
            } else {
                element['pt_pctg'] = parseFloat((0).toFixed(2));
            }
            // calculating shot zone percentages
            if (element['shots']) {
                element['sl_p'] = parseFloat(((element['sl_sh'] / element['shots']) * 100).toFixed(2));
                element['lf_p'] = parseFloat(((element['lf_sh'] / element['shots']) * 100).toFixed(2));
                element['rg_p'] = parseFloat(((element['rg_sh'] / element['shots']) * 100).toFixed(2));
                element['bl_p'] = parseFloat(((element['bl_sh'] / element['shots']) * 100).toFixed(2));
            } else {
                element['sl_p'] = parseFloat((0).toFixed(2));
                element['lf_p'] = parseFloat((0).toFixed(2));
                element['rg_p'] = parseFloat((0).toFixed(2));
                element['bl_p'] = parseFloat((0).toFixed(2));
            }
            // calculating zone percentages for shots against
            if (element['opp_shots']) {
                element['sl_p_a'] = parseFloat(((element['sl_sh_a'] / element['opp_shots']) * 100).toFixed(2));
                element['lf_p_a'] = parseFloat(((element['lf_sh_a'] / element['opp_shots']) * 100).toFixed(2));
                element['rg_p_a'] = parseFloat(((element['rg_sh_a'] / element['opp_shots']) * 100).toFixed(2));
                element['bl_p_a'] = parseFloat(((element['bl_sh_a'] / element['opp_shots']) * 100).toFixed(2));
            } else {
                element['sl_p_a'] = parseFloat((0).toFixed(2));
                element['lf_p_a'] = parseFloat((0).toFixed(2));
                element['rg_p_a'] = parseFloat((0).toFixed(2));
                element['bl_p_a'] = parseFloat((0).toFixed(2));
            }
            // calculating shooting, save and zone percentages for shots on goal
            if (element['shots_on_goal']) {
                element['shot_pctg'] = parseFloat(((element['goals'] / element['shots_on_goal']) * 100).toFixed(2));
                element['opp_save_pctg'] = parseFloat(((element['opp_saves'] / element['shots_on_goal']) * 100).toFixed(2));
                element['sl_og_p'] = parseFloat(((element['sl_og'] / element['shots_on_goal']) * 100).toFixed(2));
                element['lf_og_p'] = parseFloat(((element['lf_og'] / element['shots_on_goal']) * 100).toFixed(2));
                element['rg_og_p'] = parseFloat(((element['rg_og'] / element['shots_on_goal']) * 100).toFixed(2));
                element['bl_og_p'] = parseFloat(((element['bl_og'] / element['shots_on_goal']) * 100).toFixed(2));
            } else {
                element['shot_pct'] = parseFloat((0).toFixed(2));
                element['opp_save_pct'] = parseFloat((0).toFixed(2));
                element['sl_og_p'] = parseFloat((0).toFixed(2));
                element['lf_og_p'] = parseFloat((0).toFixed(2));
                element['rg_og_p'] = parseFloat((0).toFixed(2));
                element['bl_og_p'] = parseFloat((0).toFixed(2));
            }
            // calculating shooting and save percentages for shots on goal in 5-on-5 play
            if (element['shots_on_goal_5v5']) {
                element['shot_pctg_5v5'] = parseFloat(((element['goals_5v5'] / element['shots_on_goal_5v5']) * 100).toFixed(2));
                element['opp_save_pctg_5v5'] = parseFloat((((element['shots_on_goal_5v5'] - element['goals_5v5']) / element['shots_on_goal_5v5']) * 100).toFixed(2));
            } else {
                element['shot_pct_5v5'] = parseFloat((0).toFixed(2));
                element['opp_save_pct_5v5'] = parseFloat((0).toFixed(2));
            }
            // calculating opponent shooting, save and zone percentages for shots on goal against
            if (element['opp_shots_on_goal']) {
                element['opp_shot_pctg'] = parseFloat(((element['opp_goals'] / element['opp_shots_on_goal']) * 100).toFixed(2));
                element['save_pctg'] = parseFloat(((element['saves'] / element['opp_shots_on_goal']) * 100).toFixed(2));
                element['sl_og_p_a'] = parseFloat(((element['sl_og_a'] / element['opp_shots_on_goal']) * 100).toFixed(2));
                element['lf_og_p_a'] = parseFloat(((element['lf_og_a'] / element['opp_shots_on_goal']) * 100).toFixed(2));
                element['rg_og_p_a'] = parseFloat(((element['rg_og_a'] / element['opp_shots_on_goal']) * 100).toFixed(2));
                element['bl_og_p_a'] = parseFloat(((element['bl_og_a'] / element['opp_shots_on_goal']) * 100).toFixed(2));
            } else {
                element['opp_shot_pct'] = parseFloat((0).toFixed(2));
                element['save_pct'] = parseFloat((0).toFixed(2));
                element['sl_og_p_a'] = parseFloat((0).toFixed(2));
                element['lf_og_p_a'] = parseFloat((0).toFixed(2));
                element['rg_og_p_a'] = parseFloat((0).toFixed(2));
                element['bl_og_p_a'] = parseFloat((0).toFixed(2));
            }
            // calculating opponent shooting and save percentages for shots on goal against in 5-on-5 play
            if (element['opp_shots_on_goal_5v5']) {
                element['opp_shot_pctg_5v5'] = parseFloat(((element['opp_goals_5v5'] / element['opp_shots_on_goal_5v5']) * 100).toFixed(2));
                element['save_pctg_5v5'] = parseFloat((((element['opp_shots_on_goal_5v5'] - element['opp_goals_5v5']) / element['opp_shots_on_goal_5v5']) * 100).toFixed(2));
            } else {
                element['opp_shot_pct_5v5'] = parseFloat((0).toFixed(2));
                element['save_pct_5v5'] = parseFloat((0).toFixed(2));
            }
            // calculating PDO
            element['pdo'] = parseFloat((parseFloat(element['shot_pctg']) + parseFloat(element['save_pctg'])).toFixed(2));
            element['opp_pdo'] = parseFloat((parseFloat(element['opp_shot_pctg']) + parseFloat(element['opp_save_pctg'])).toFixed(2));
            // calculating PDO in 5-on-5 play
            element['pdo_5v5'] = parseFloat((parseFloat(element['shot_pctg_5v5']) + parseFloat(element['save_pctg_5v5'])).toFixed(2));
            element['opp_pdo_5v5'] = parseFloat((parseFloat(element['opp_shot_pctg_5v5']) + parseFloat(element['opp_save_pctg_5v5'])).toFixed(2));
            // calculating shots on goal for percentage
            if (element['shots_on_goal'] + element['opp_shots_on_goal']) {
                element['shot_for_pctg'] = parseFloat((element['shots_on_goal'] / (element['shots_on_goal'] + element['opp_shots_on_goal']) * 100).toFixed(2));
                element['opp_shot_for_pctg'] = parseFloat((element['opp_shots_on_goal'] / (element['shots_on_goal'] + element['opp_shots_on_goal']) * 100).toFixed(2));
            } else {
                element['shot_for_pctg'] = parseFloat((0).toFixed(2));
                element['opp_shot_for_pctg'] = parseFloat((0).toFixed(2));
            }
            // calculating unblocked shots (i.e. Fenwick) for percentage
            element['fenwick_events'] = element['shots_on_goal'] + element['shots_missed']; 
            element['opp_fenwick_events'] = element['opp_shots_on_goal'] + element['opp_shots_missed']; 
            if (element['fenwick_events'] + element['opp_fenwick_events']) {
                element['fenwick_for_pctg'] = parseFloat(((element['fenwick_events']) / (element['fenwick_events' ]+ element['opp_fenwick_events']) * 100).toFixed(2));
                element['opp_fenwick_for_pctg'] = parseFloat(((element['opp_fenwick_events']) / (element['fenwick_events' ]+ element['opp_fenwick_events']) * 100).toFixed(2));
            } else {
                element['fenwick_for_pctg'] = parseFloat((0).toFixed(2));
                element['opp_fenwick_for_pctg'] = parseFloat((0).toFixed(2));
            }
            // calculating shots (i.e. Corsi) for percentage
            if (element['shots'] + element['opp_shots']) {
                element['corsi_for_pctg'] = parseFloat((element['shots'] / (element['shots'] + element['opp_shots']) * 100).toFixed(2));
                element['opp_corsi_for_pctg'] = parseFloat((element['opp_shots'] / (element['shots'] + element['opp_shots']) * 100).toFixed(2));
            } else {
                element['corsi_for_pctg'] = parseFloat((0).toFixed(2));
                element['opp_corsi_for_pctg'] = parseFloat((0).toFixed(2));
            }
            // calculating power play percentage
            if (element['pp_opps']) {
                element['pp_pctg'] = parseFloat(((element['pp_goals'] / element['pp_opps']) * 100).toFixed(2));
            } else {
                element['pp_pctg'] = parseFloat((0).toFixed(2));
            }
            // calculating penalty killing percentage
            if (element['sh_opps']) {
                element['pk_pctg'] = parseFloat((100 - (element['opp_pp_goals'] / element['sh_opps']) * 100).toFixed(2));
            } else {
                element['pk_pctg'] = parseFloat((0).toFixed(2));
            }
            // calculating special teams goal differential and combined special team percentages
            element['pp_pk_gdiff'] = element['pp_goals'] + element['sh_goals'] - element['opp_pp_goals'] - element['opp_sh_goals'];
            element['pp_pk_comb_pctg'] = element['pp_pctg'] + element['pk_pctg'];
            // calculating team faceoff percentage
            if (element['faceoffs']) {
                element['faceoff_pctg'] = parseFloat(((element['faceoffs_won'] / element['faceoffs']) * 100).toFixed(2));
            } else {
                element['faceoff_pctg'] = parseFloat((0).toFixed(2));
            }
            // calculating team penalty minutes per game
            if (element['games_played']) {
                element['pim_per_game'] = parseFloat((element['pim'] / element['games_played']).toFixed(2));
            } else {
                element['pim_per_game'] = parseFloat((0).toFixed(2));
            }
            // calculating average attendance
            if (element['games_played']) {
                element['avg_attendance'] = parseFloat((element['attendance'] / element['games_played']).toFixed(0));
            } else {
                element['avg_attendance'] = 0;
            }
            // retrieving last year's average attendance
            element['avg_attendance_last_season'] = $scope.avg_attendance_last_season[element['team']];
            element['avg_attendance_delta'] = element['avg_attendance'] - element['avg_attendance_last_season']; 
            // calculating utilized attendance capacity
            if (element['capacity']) {
                element['util_capacity_pctg'] = parseFloat(((element['attendance'] / element['capacity']) * 100).toFixed(2));
            } else {
                element['util_capacity_pctg'] = parseFloat((0).toFixed(2));
            }
            // calculating score state percentages
            if (element['time_played']) {
                element['leading_pctg'] = parseFloat(((element['leading'] / element['time_played']) * 100).toFixed(2));
                element['trailing_pctg'] = parseFloat(((element['trailing'] / element['time_played']) * 100).toFixed(2));
                element['tied_pctg'] = parseFloat(((element['tied'] / element['time_played']) * 100).toFixed(2));
            } else {
                element['leading_pctg'] = parseFloat((0).toFixed(2));
                element['trailing_pctg'] = parseFloat((0).toFixed(2));
                element['tied_pctg'] = parseFloat((0).toFixed(2));
            }
            // calculating 5-on-5 shot share percentages
            if (element['shots_5v5'] + element['opp_shots_5v5']) {
                element['shots_5v5_pctg'] = parseFloat(((element['shots_5v5'] / (element['shots_5v5'] + element['opp_shots_5v5'])) * 100).toFixed(2));
            } else {
                element['shots_5v5_pctg'] = parseFloat((0).toFixed(2));
            }
            if (element['shots_unblocked_5v5'] + element['opp_shots_unblocked_5v5']) {
                element['shots_unblocked_5v5_pctg'] = parseFloat(((element['shots_unblocked_5v5'] / (element['shots_unblocked_5v5'] + element['opp_shots_unblocked_5v5'])) * 100).toFixed(2));
            } else {
                element['shots_unblocked_5v5_pctg'] = parseFloat((0).toFixed(2));
            }
            if (element['shots_on_goal_5v5'] + element['opp_shots_on_goal_5v5']) {
                element['shots_on_goal_5v5_pctg'] = parseFloat(((element['shots_on_goal_5v5'] / (element['shots_on_goal_5v5'] + element['opp_shots_on_goal_5v5'])) * 100).toFixed(2));
            } else {
                element['shots_on_goal_5v5_pctg'] = parseFloat((0).toFixed(2));
            }
        });
        
        return filtered_team_stats;
    };

    // event function to call after table change
    $scope.changeTable = function () {
        if ($scope.tableSelect === 'standings') {
            if ($scope.situationSelect) {
                $scope.sortConfig = {
                    'sortKey': 'pt_pctg',
                    'sortCriteria': ['pt_pctg', 'points', 'goals_diff'],
                    'sortDescending': true
                }
            } else {
                $scope.sortConfig = {
                    'sortKey': 'points',
                    'sortCriteria': ['points', 'score_diff', 'score'],
                    'sortDescending': true
                }
            }
            $scope.isStandingsView = true;
            $scope.isAttendanceView = false;
        } else if ($scope.tableSelect === 'goal_stats') {
            $scope.sortConfig = {
                'sortKey': 'goals_diff',
                'sortCriteria': ['goals_diff', 'goals'],
                'sortDescending': true
            }
            $scope.isStandingsView = false;
            $scope.isAttendanceView = false;
            $scope.situationSelect = undefined;
        } else if ($scope.tableSelect === 'shot_stats') {
            $scope.sortConfig = {
                'sortKey': 'shots_on_goal',
                'sortCriteria': ['shots_on_goal', 'goals'],
                'sortDescending': true
            }
            $scope.isStandingsView = false;
            $scope.isAttendanceView = false;
            $scope.situationSelect = undefined;
        } else if ($scope.tableSelect === 'shot_stats_5v5') {
            $scope.sortConfig = {
                'sortKey': 'shots_on_goal_5v5',
                'sortCriteria': ['shots_on_goal_5v5', 'goals_5v5'],
                'sortDescending': true
            }
            $scope.isStandingsView = false;
            $scope.isAttendanceView = false;
            $scope.situationSelect = undefined;
        } else if ($scope.tableSelect === 'shot_shares') {
            $scope.sortConfig = {
                'sortKey': 'corsi_for_pctg',
                'sortCriteria': ['corsi_for_pctg', 'shots'],
                'sortDescending': true
            }
            $scope.isStandingsView = false;
            $scope.isAttendanceView = false;
            $scope.situationSelect = undefined;
        } else if ($scope.tableSelect === 'shot_shares_5v5') {
            $scope.sortConfig = {
                'sortKey': 'shots_5v5_pctg',
                'sortCriteria': ['shots_5v5_pctg', 'shots_5v5'],
                'sortDescending': true
            }
            $scope.isStandingsView = false;
            $scope.isAttendanceView = false;
            $scope.situationSelect = undefined;
        } else if ($scope.tableSelect === 'attendance_stats') {
            $scope.sortConfig = {
                'sortKey': 'util_capacity_pctg',
                'sortCriteria': ['util_capacity_pctg', 'attendance'],
                'sortDescending': true
            }
            $scope.isStandingsView = false;
            $scope.isAttendanceView = true;
            $scope.situationSelect = undefined;
        } else if ($scope.tableSelect === 'special_team_stats') {
            $scope.sortConfig = {
                'sortKey': 'pp_pctg',
                'sortCriteria': ['pp_pctg', '-pp_opps'],
                'sortDescending': true
            }
            $scope.isStandingsView = false;
            $scope.isAttendanceView = false;
            $scope.situationSelect = undefined;
        } else if ($scope.tableSelect === 'additional_stats') {
            $scope.sortConfig = {
                'sortKey': 'faceoff_pctg',
                'sortCriteria': ['faceoff_pctg', 'faceoffs'],
                'sortDescending': true
            }
            $scope.isStandingsView = false;
            $scope.isAttendanceView = false;
            $scope.situationSelect = undefined;
        } else if ($scope.tableSelect === 'penalty_stats') {
            $scope.sortConfig = {
                'sortKey': 'pim_per_game',
                'sortCriteria': ['pim_per_game', 'penalties'],
                'sortDescending': true
            }
            $scope.isStandingsView = false;
            $scope.isAttendanceView = false;
            $scope.situationSelect = undefined;
        } else if ($scope.tableSelect === 'shot_zones') {
            $scope.sortConfig = {
                'sortKey': 'shots',
                'sortCriteria': ['shots'],
                'sortDescending': true
            }
            $scope.isStandingsView = false;
            $scope.isAttendanceView = false;
            $scope.situationSelect = undefined;
        } else if ($scope.tableSelect === 'shot_on_goal_zones') {
            $scope.sortConfig = {
                'sortKey': 'shots_on_goal',
                'sortCriteria': ['shots_on_goal'],
                'sortDescending': true
            }
            $scope.isStandingsView = false;
            $scope.isAttendanceView = false;
            $scope.situationSelect = undefined;
        } else if ($scope.tableSelect === 'shot_zones_against') {
            $scope.sortConfig = {
                'sortKey': 'opp_shots',
                'sortCriteria': ['opp_shots'],
                'sortDescending': true
            }
            $scope.isStandingsView = false;
            $scope.isAttendanceView = false;
            $scope.situationSelect = undefined;
        } else if ($scope.tableSelect === 'shot_on_goal_zones_against') {
            $scope.sortConfig = {
                'sortKey': 'opp_shots_on_goal',
                'sortCriteria': ['opp_shots_on_goal'],
                'sortDescending': true
            }
            $scope.isStandingsView = false;
            $scope.isAttendanceView = false;
            $scope.situationSelect = undefined;
        } else if ($scope.tableSelect === 'score_state_stats') {
            $scope.sortConfig = {
                'sortKey': 'leading_pctg',
                'sortCriteria': ['leading_pctg'],
                'sortDescending': true
            }
            $scope.isStandingsView = false;
            $scope.isAttendanceView = false;
            $scope.situationSelect = undefined;
        }
    };

    $scope.setSortOrder = function(sortKey, oldSortConfig) {
        ascendingAttrs = ['team'];
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
                sort_descending = false;
            // otherwise descending sort order
            } else {
                sort_descending = true;
            }
            // retrieving actual (and minor) sort criteria from scope-wide
            // definition of sort criteria
            // use plain sort key if nothing has been defined otherwise
            sort_criteria = $scope.sort_def[sortKey] || sortKey;
            return {
                'sortKey': sortKey,
                'sortCriteria': sort_criteria,
                'sortDescending': sort_descending
            }
        }
    }

    $scope.changeTimespan = function() {
        if (!$scope.timespanSelect) {
            ctrl.fromDate = null;
            ctrl.toDate = null;
            return;
        }
        if ($scope.timespanSelect == 'pre_dcup')
        {
            ctrl.fromDate = moment($scope.season + '-09-01');
            ctrl.toDate = $scope.dcup_date;
        } else if ($scope.timespanSelect == 'post_dcup') {
            ctrl.fromDate = $scope.dcup_date;
            var nextSeason = parseFloat($scope.season) + 1;
            ctrl.toDate = moment(nextSeason + '-05-01');
        } else {
            timespanSelect = parseInt($scope.timespanSelect) + 1;
            if (timespanSelect < 9) {
                season = parseInt($scope.season) + 1;
            } else {
                season = parseInt($scope.season);
            }
            ctrl.fromDate = moment(season + '-' + timespanSelect + '-1', 'YYYY-M-D');
            ctrl.toDate = moment(season + '-' + timespanSelect + '-1', 'YYYY-M-D').endOf('month');
            }
    }

    $scope.changeDate = function() {
        if ($scope.team_stats) {
            $scope.filtered_team_stats = $scope.filterStats($scope.team_stats);
        };
    }

});
