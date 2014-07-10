(function ($) {

    function Cab() {

        this.tab = "battle";
        this.battle_market = {
            left: {
                artist: "darkmatter",
                song: "1-1arr3",
                embed: '<iframe width="100%" height="450" scrolling="no" frameborder="no" src="https://w.soundcloud.com/player/?url=https%3A//api.soundcloud.com/tracks/119207566&amp;auto_play=false&amp;hide_related=false&amp;show_comments=true&amp;show_user=true&amp;show_reposts=false&amp;visual=true"></iframe>'
            },
            right: {
                artist: "eatdatcake",
                song: "zigga-zig-caked-up-feat-the-spice-girls-free-download",
                embed: '<iframe width="100%" height="450" scrolling="no" frameborder="no" src="https://w.soundcloud.com/player/?url=https%3A//api.soundcloud.com/tracks/156874095&amp;auto_play=false&amp;hide_related=false&amp;show_comments=true&amp;show_user=true&amp;show_reposts=false&amp;visual=true"></iframe>'
            }
        };
        this.balance = {
            'DYF': 0,
            'ROX': 0,
            'BTC': 0
        };
    }


    // setup methods called as part of the page load.
    Cab.prototype.ignition = function () {

        socket.emit('get-chat');
        return this;
    };

    // incoming websocket signals
    Cab.prototype.intake = function () {

    	// wallet balances
        var self = this;
        socket.on('wallet-balance', function (message) {
            var balance = mesage.dyf + " DYF";
            self.dyf_balance = balance;
            $('#display-dyff-balance').empty().html(balance).show();
        });

        // countdown timer
        socket.on('time-remaining', function (message) {
            $(".digits").each(function () {
                $(this).empty().countdown({
                    image: "static/img/digits.png",
                    format: "mm:ss",
                    startTime: res.time_remaining,
                    timerEnd: function () { self.tuneup(); }
                });
            });
        });

        // chat
        socket.on('chat', function (message) {
            $.each(message.chat, function(i, c) {
            	var chat = $("<li/>").html('<b>'+c.author+'</b><i>'+c.timestamp+'</i>'+c.comment)
            	$('#chat-box ul').append(chat);
            })
        });


        // process battle data
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

        socket.on('battle-bet-response', function (res) {

            var alert_text, alert_header, direction, coin_target;
            if (res.success) {
                alert_header = "Bet placed!";
                alert_text = "You have successfully bet " + res.amount + " " +
                    res.denomination + " on " + res.bet_target + "!";
            } else {
                alert_header = "Bet not placed";
                alert_text = "Your bet of " + res.amount + " " + res.denomination +
                    " on " + res.bet_target + " could not be placed.";
            }
            self.modal(alert_text, 'h5', alert_header);
            self.tuneup();
        });
        socket.on('updated-data', function (res) { self.updated_data(res); });
        return this;
    };

    // outgoing websocket signals
    Cab.prototype.exhaust = function () {

        var self = this;

        // chat
        $('form#broadcast').submit(function (event) {
            event.preventDefault();
            socket.emit('chat', {
                data: $('#broadcast_data').val()
            });
            $('#broadcast_data').val('');
        });

        // bets
        $('form#bet-left').submit(function (event) {
            event.preventDefault();
            self.bet('left');
        });
        $('form#bet-right').submit(function (event) {
            event.preventDefault();
            self.bet('right');
        });
        return this;
    };

    // data synchronizer
    Cab.prototype.tuneup = function (repeat) {

        socket.emit('get-wallet-balance');
        socket.emit('get-time-remaining');
        socket.emit('battle-bets', self.battle_market);
        socket.emit('update-data', self.battle_market);
        if (repeat) { setTimeout(self.tuneup, repeat); }
        return this;
    };

    // Actions: methods that must be actively called.
    Cab.prototype.bet = function (direction) {

        var self = this;
        var amount, error_text, target;
        target = self.battle_market[direction];
        amount = $('#bet-input-' + direction).val();

        if (!isNaN(amount)) {

            amount = parseFloat(amount);

            // Make sure we've got enough coins to make the bet
            if (amount <= self.dyff_balance) {

                $('#bet-input-' + direction).val(null);
                socket.emit('battle-bet', {
                    amount: amount,
                    denomination: $('#bet-denomination-' + direction).val(),
                    left: self.battle_market.left,
                    right: self.battle_market.right,
                    target: target
                });

            } else {

                error_text = "You do not have enough dyffs in your account to place this bet.";
                self.modal(error_text, 'h5', 'Betting error');
            }

        } else {

            error_text = "You must enter a number!";
            self.modal(error_text, 'h5', 'Betting error');
        }
    };

    Cab.prototype.updated_data = function (res, position) {

        var self = this;
        var change_display;
        if (position) {
            change_display = res.price_ratio.toFixed(4);
        } else {
            change_display = res.price_change.toFixed(2);
            $('#current-price').html(res.price);
        }
        position = (position) ? '-' + position : '';
        if (res.price_change == 0) {
            $('#price-change' + position).html('(no change)');
        } else if (res.price_change > 0) {
            $('#price-change' + position).html(
                '(<span class="blue-text">+' + change_display + '</span>)'
            );
        } else {
            $('#price-change' + position).html(
                '(<span class="red-text">' + change_display + '</span>)'
            );
        }
    };

    Cab.prototype.modal = function (bodytext, bodytag, headertext) {

        var self = this;
        if (headertext) {
            $('#modal-header').empty().text(headertext);
        }
        if (bodytext) {
            var modal_body = (bodytag) ? $('<' + bodytag + ' />') : $('<p />');
            $('#modal-body').empty().append(
                modal_body.addClass('modal-error-text').text(bodytext)
            );
        }
        $('#modal-dynamic').foundation('reveal', 'open');
    };

    $(document).ready(function () {

        var repeat = 30000;   // data synchronization interval

        window.socket = io.connect(window.location.protocol + '//' + document.domain + ':' + location.port + '/socket.io/');

        new Cab()
            .ignition()
            .intake()
            .exhaust()
            .tuneup(repeat);

    });

})(jQuery);