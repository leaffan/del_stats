app.controller('previewsController', function($scope, $http, $localStorage, $routeParams, svc) {
    $scope.svc = svc;
    $scope.season = $routeParams.season;
    $scope.round_from_url = $routeParams.round;
    $scope.next_round = "0";
    $scope.min_days_left = 365;
    // loading schedule from external json file
    $http.get('data/'+ $scope.season + '/full_schedule.json').then(function (res) {
        $scope.fixtures = res.data;
        $scope.fixtures.forEach(fixture => {
            fixture['game_date'] = moment(fixture['start_date']);
            // calculating days left until current fixture
            fixture['days_left'] = fixture['game_date'].diff(moment(), 'days');
            if (fixture['days_left'] >= 0 && fixture['days_left'] < $scope.min_days_left) {
                $scope.next_round = fixture['round'];
                $scope.min_days_left = fixture['days_left'];
            }
        });
        if ($scope.round_from_url === undefined) {
            $scope.roundFilter = $scope.next_round;
        } else {
            $scope.roundFilter = $scope.round_from_url.toString();
        }
    });

    // // restoring previously set round filter, if possible
    // if ($localStorage.roundFilter != null) {
    //     $scope.roundFilter = $localStorage.roundFilter;
    // } else {
    //     $scope.roundFilter = '1';
    // }

    $scope.changeRound = function() {
        // storing round filter set by user
        $localStorage.roundFilter = $scope.roundFilter;
    };

});
