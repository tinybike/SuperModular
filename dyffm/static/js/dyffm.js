/**
 * @fileoverview dyf.fm front-end core
 * @author jack@tinybike.net (Jack Peterson)
 */
(function ($) {
    /**
     * All listeners and event handlers are registered here:
     * DOM manipulation, visuals, and websockets events.
     * @constructor
     */
    function CryptoCab() {
        var self = this;
        this.chatbox_populated = false;
        this.scribble_populated = false;
        this.tab = "default";
        this.predict_market = "Bitcoin";
        this.battle_market_left = "Dogecoin";
        this.battle_market_right = "Bitcoin";
    }
    /**
     * All DOM manipulation, visual tweaks, and event handlers that do not
     * involve sending/receiving data from the server via websockets are
     * set up here.
     */
    CryptoCab.prototype.tweaks = function () {
        var self = this;
        self.predict_market = $('.predict-selected-market').first().text();
        self.battle_coin_left = $('.selected-market-left').first().text();
        self.battle_coin_right = $('.selected-market-right').first().text();
        if (login) {
            $('.select-currency').each(function () {
                check_issuer(this);
                $(this).change(function () {
                    check_issuer(this);
                });
            });
            $('#predict-tab').click(function () {
                self.tab = "predict";
                self.predict_market = $('.predict-selected-market').first().text();
            });
            $('#battle-tab').click(function () {
                self.tab = "battle";
                self.battle_coin_left = $('.selected-market-left').first().text();
                self.battle_coin_right = $('.selected-market-right').first().text();
            });
        }
    };
    /**
     * Outgoing websocket signals.  Event handlers that send messages to
     * the server via websocket as part of their callback are registered here.
     */
    CryptoCab.prototype.exhaust = function () {
        var self = this;
        function place_bet(market, direction) {
            var amount, error_text, target, bet_parameters;
            if (market == 'predict') {
                target = (direction == 'up') ? '+' : '-';
            } else {
                if (direction == 'left') {
                    target = self.battle_coin_left;
                } else {
                    target = self.battle_coin_right;
                }
            }
            amount = $('#bet-input-' + direction).val();
            if (!isNaN(amount)) {
                amount = parseFloat(amount);
                // Make sure we've got enough dyffs to make the bet
                if (amount <= self.dyff_balance) {
                    $('#bet-input-' + direction).val(null);
                    bet_parameters = {
                        amount: amount,
                        denomination: $('#bet-denomination-' + direction).val()
                    };
                    if (market == 'predict') {
                        bet_parameters.market = self.predict_market;
                        bet_parameters.direction = target;
                    } else {
                        bet_parameters.left = self.battle_coin_left;
                        bet_parameters.right = self.battle_coin_right;
                        bet_parameters.target = target;
                    }
                    socket.emit(market + '-bet', bet_parameters);
                } else {
                    error_text = "You do not have enough dyffs in your account to place this bet.";
                    modal_alert(error_text, 'h5', 'Betting error');
                }
            } else {
                error_text = "You must enter a number!";
                modal_alert(error_text, 'h5', 'Betting error');
            }
        }
        if (!this.chatbox_populated) {
            socket.emit('populate-chatbox');
            this.chatbox_populated = true;
        }
        $('form#broadcast').submit(function (event) {
            event.preventDefault();
            socket.emit('chat', {
                data: $('#broadcast_data').val()
            });
            $('#broadcast_data').val('');
        });
        $('form#bet-down').submit(function (event) {
            event.preventDefault();
            place_bet('predict', 'down');
        });
        $('form#bet-up').submit(function (event) {
            event.preventDefault();
            place_bet('predict', 'up');
        });
        $('form#bet-left').submit(function (event) {
            event.preventDefault();
            place_bet('battle', 'left');
        });
        $('form#bet-right').submit(function (event) {
            event.preventDefault();
            place_bet('battle', 'right');
        });
        /**
         * Synchronize countdown timer and market data.
         */
        (synchronize_data = function (repeat) {
            socket.emit('get-dyff-balance');
            socket.emit('get-time-remaining');
            socket.emit('predict-bets', {
                coin: self.predict_market
            });
            socket.emit('get-current-prices', {
                coin: self.predict_market
            });
            socket.emit('battle-bets', {
                left: self.battle_coin_left,
                right: self.battle_coin_right
            });
            socket.emit('get-current-prices', {
                coin: self.battle_coin_left,
                battle: 'left'
            });
            socket.emit('get-current-prices', {
                coin: self.battle_coin_right,
                battle: 'right'
            });
            if (repeat) {
                setTimeout(synchronize_data, window.delay);
            }
        })(1);
    }
    /**
     * Listeners for incoming websocket signals.
     */
    CryptoCab.prototype.intake = function () {
        var self = this;
        function bet_success(market, res) {
            var alert_text, alert_header, direction, coin_target;
            if (res.success) {
                alert_header = "Bet placed!";
                if (market == 'predict') {
                    direction = (res.bet_direction == '+') ? "HIGHER" : "LOWER";
                    alert_text = "You have successfully bet " + res.amount + " " + res.denomination + " on " + res.coin + "'s price to be " + direction + " at the end of the round.";
                } else {
                    alert_text = "You have successfully bet " + res.amount + " " + res.denomination + " on " + res.bet_target + "!";
                }
                
            } else {
                alert_header = "Bet not placed";
                coin_target = (market == 'predict') ? res.coin : res.bet_target;
                alert_text = "Your bet of " + res.amount + " " + res.denomination + " on " + coin_target + " could not be placed.";
            }
            modal_alert(alert_text, 'h5', alert_header);
            synchronize_data();
        }
        socket.on('dyff-balance', function (res) {
            var balance = res.balance + " DYF";
            self.dyff_balance = res.balance;
            $('#display-dyff-balance').empty().html(balance).show();
        });
        
        socket.on('time-remaining', function (res) {
            $(".digits").each(function () {
                $(this).empty().countdown({
                    image: "static/img/digits.png",
                    format: "mm:ss",
                    startTime: res.time_remaining,
                    timerEnd: function () {
                        socket.emit('get-time-remaining', {
                            coin: self.predict_market
                        });
                        socket.emit('predict-bets', {
                            coin: self.predict_market
                        });
                        socket.emit('get-dyff-balance');
                    }
                });
            });
        });
        socket.on('chat-populate', function (msg) {
            var timestamp = msg.timestamp.split('.')[0];
            $('#babble').append('<br />' + msg.user + ' <span class="timestamp">[' + moment(timestamp).fromNow() + ']</span>: ' + msg.comment);
        });
        socket.on('chat-response', function (msg) {
            var now = new Date();
            $('#babble').append('<br />' + msg.user + ' <span class="timestamp">[' + moment(now).fromNow() + ']</span>: ' + msg.data);
            var cb = document.getElementById('chat-box');
            cb.scrollTop = cb.scrollHeight;
        });
        socket.on('predict-data', function (res) {
            var timestamp, bets_down_table, bets_up_table, pool_down, pool_up;
            if (res.starting_price && res.starting_price.price) {
                $('#starting-price').html(res.starting_price.price + " USD/BTC");
                if (res.bets_down && res.bets_down.length) {
                    pool_down = 0;
                    bets_down_table = "<table class='centered full-width'>";
                    for (var i = 0, len = res.bets_down.length; i < len; ++i) {
                        timestamp = res.bets_down[i][3].split('.')[0];
                        bets_down_table += "<tr><td>" + res.bets_down[i][0] + "</td><td>" + res.bets_down[i][1] + " " + res.bets_down[i][2] + "</td><td>" + moment(timestamp).fromNow() + "</td></tr>";
                        pool_down += res.bets_down[i][1];
                    }
                    bets_down_table += "</table>";
                    $('#pool-down').html(pool_down.toFixed(2));
                    $('#pool-down-denomination').html(res.bets_down[0][2]);
                    $('#current-bets-down').html(bets_down_table);
                }
                if (res.bets_up && res.bets_up.length) {
                    pool_up = 0;
                    bets_up_table = "<table class='centered full-width'>";
                    for (i = 0, len = res.bets_up.length; i < len; ++i) {
                        timestamp = res.bets_up[i][3].split('.')[0];
                        bets_up_table += "<tr><td>" + res.bets_up[i][0] + "</td><td>" + res.bets_up[i][1] + " " + res.bets_up[i][2] + "</td><td>" + moment(timestamp).fromNow() + "</td></tr>";
                        pool_up += res.bets_up[i][1];
                    }
                    bets_up_table += "</table>";
                    $('#pool-up').html(pool_up.toFixed(2));
                    $('#pool-up-denomination').html(res.bets_up[0][2]);
                    $('#current-bets-up').html(bets_up_table);
                }
            }
        });
        socket.on('battle-data', function (res) {
            var timestamp, bets_down_table, bets_up_table, pool_down, pool_up;
            if (res) {
                if (res.bets_left && res.bets_left.length) {
                    pool_left = 0;
                    bets_left_table = "<table class='centered full-width'>";
                    for (var i = 0, len = res.bets_left.length; i < len; ++i) {
                        timestamp = res.bets_left[i][3].split('.')[0];
                        bets_left_table += "<tr><td>" + res.bets_left[i][0] + "</td><td>" + res.bets_left[i][1] + " " + res.bets_left[i][2] + "</td><td>" + moment(timestamp).fromNow() + "</td></tr>";
                        pool_left += res.bets_left[i][1];
                    }
                    bets_left_table += "</table>";
                    $('#pool-left').html(pool_left.toFixed(2));
                    $('#pool-left-denomination').html(res.bets_left[0][2]);
                    $('#current-bets-left').html(bets_left_table);
                }
                if (res.bets_right && res.bets_right.length) {
                    pool_right = 0;
                    bets_right_table = "<table class='centered full-width'>";
                    for (i = 0, len = res.bets_right.length; i < len; ++i) {
                        timestamp = res.bets_right[i][3].split('.')[0];
                        bets_right_table += "<tr><td>" + res.bets_right[i][0] + "</td><td>" + res.bets_right[i][1] + " " + res.bets_right[i][2] + "</td><td>" + moment(timestamp).fromNow() + "</td></tr>";
                        pool_right += res.bets_right[i][1];
                    }
                    bets_right_table += "</table>";
                    $('#pool-right').html(pool_right.toFixed(2));
                    $('#pool-right-denomination').html(res.bets_right[0][2]);
                    $('#current-bets-right').html(bets_right_table);
                }
            }
        });
        socket.on('predict-bet-response', function (res) {
            bet_success('predict', res);
        });
        socket.on('battle-bet-response', function (res) {
            bet_success('battle', res);
        });
        socket.on('current-prices', function (res) {
            price_change(res); 
        });
        socket.on('current-left-prices', function (res) {
            price_change(res, 'left');
        });
        socket.on('current-right-prices', function (res) {
            price_change(res, 'right');
        });
    };
    // Some useful functions I like to keep around
    /**
     * @param {number|string} n
     * @param {number} d
     */
    function round_to(n, d) {
        if (typeof n !== 'number') {
            try {
                n = parseFloat(n);
            } catch (e) {
                console.log("Rounding error:", e);
                return n;
            }
        }
        var m = Math.pow(10, d);
        return Math.round(n * m) / m;
    }
    /**
     * @param {number} min
     * @param {number} max
     */
    function get_random_int(min, max) {
        return Math.floor(Math.random() * (max - min + 1)) + min;
    }
    /**
     * Create modal alert window using Foundation reveal
     * @param {string|null} bodytext
     * @param {string|null} bodytag
     * @param {string|null} headertext
     */
    function modal_alert(bodytext, bodytag, headertext) {
        var modal_body;
        if (headertext) {
            $('#modal-header').empty().text(headertext);
        }
        if (bodytext) {
            modal_body = (bodytag) ? $('<' + bodytag + ' />') : $('<p />');
            $('#modal-body').empty().append(
                modal_body.addClass('modal-error-text').text(bodytext)
            );
        }
        $('#modal-dynamic').foundation('reveal', 'open');
    }
    // docready let's do this
    $(document).ready(function () {
        var socket_url, cab, reactor;
        window.chart_data_loaded = false;
        window.delay = 30000;   // data synchronization interval
        socket_url = window.location.protocol + '//' + document.domain + ':' + location.port + '/socket.io/';
        window.socket = io.connect(socket_url);
        cab = new CryptoCab();
        cab.tweaks();
        cab.intake();
        cab.exhaust();
    });
})(jQuery);
