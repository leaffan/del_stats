app.controller('previewsController', function($scope, $http, $localStorage, $routeParams, svc) {
    $scope.svc = svc;
    $scope.season = $routeParams.season;
    $scope.round_from_url = $routeParams.round;
    $scope.playoff_rounds = new Set();
    $scope.next_round = "0";
    $scope.min_days_left = 365;
    // loading schedule from external json file
    var now = moment();
    $http.get('data/'+ $scope.season + '/full_schedule.json').then(function (res) {
        $scope.fixtures = res.data;
        $scope.fixtures.forEach(fixture => {
            fixture['game_date'] = moment(fixture['start_date']);
            // retrieving start of day for game date
            fixture['game_day'] = moment(fixture['start_date']).startOf('day');
            // calculating days left until current fixture
            fixture['days_left'] = fixture['game_day'].diff(now, 'days');
            if (fixture['days_left'] >= 0 && fixture['days_left'] < $scope.min_days_left) {
                $scope.next_round = fixture['round'];
                $scope.min_days_left = fixture['days_left'];
            }
            // registering current round as playoff round if it is not numeric
            if (!svc.isNumeric(fixture['round'])) {
                $scope.playoff_rounds.add(fixture['round']);
            };
        });
        if ($scope.round_from_url === undefined) {
            $scope.roundFilter = $scope.next_round;
        } else {
            $scope.roundFilter = $scope.round_from_url.toString();
        }
        // converting set of playoff round names to an array
        $scope.playoff_rounds = Array.from($scope.playoff_rounds);
        // determining previous and following round for table view navigation
        $scope.previous_round = $scope.getPreviousRound();
        $scope.following_round = $scope.getFollowingRound();
    });

    // // restoring previously set round filter, if possible
    // if ($localStorage.roundFilter != null) {
    //     $scope.roundFilter = $localStorage.roundFilter;
    // } else {
    //     $scope.roundFilter = '1';
    // }

    $scope.getPreviousRound = function() {
        if ($scope.roundFilter == 1) {
            return;
        } 
        if ($scope.roundFilter == 'first_round_1') {
            return 52;
        }
        if (svc.isNumeric($scope.roundFilter)) {
            return svc.parseFloat($scope.roundFilter) - 1;
        }
        else {
            return $scope.playoff_rounds[$scope.playoff_rounds.findIndex(element => element === $scope.roundFilter) - 1];
        }
    };

    $scope.getFollowingRound = function() {
        if ($scope.roundFilter == 52) {
            return $scope.playoff_rounds[0];
        }
        if ($scope.playoff_rounds.findIndex(element => element === $scope.roundFilter) + 1 === $scope.playoff_rounds.length)
            return;
        if (svc.isNumeric($scope.roundFilter)) {
            return svc.parseFloat($scope.roundFilter) + 1;
        }
        else {
            return $scope.playoff_rounds[$scope.playoff_rounds.findIndex(element => element === $scope.roundFilter) + 1];
        }
    };

    $scope.changeRound = function() {
        // storing round filter set by user
        $localStorage.roundFilter = $scope.roundFilter;
        // adjusting previous and following round for table view navigation
        $scope.previous_round = $scope.getPreviousRound();
        $scope.following_round = $scope.getFollowingRound();
    };

});
