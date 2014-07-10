/**
 * @fileoverview Dyffy front-end core
 * @author jack@tinybike.net (Jack Peterson)
 */
(function ($) {
    /**
     * Remote rippled server connection info
     * @const 
     */
    var rippled_params = {
        trace: false,
        trusted: true,
        local_signing: true,
        secure: true,
        local_fee: true,
        fee_cushion: 1.5,
        servers: [{
            host: 's1.ripple.com',
            port: 443,
            secure: true
        }]
    };
    /**
     * Ripple Gateways "certified": http://www.xrpga.org/gateways.html
     * Issuing address & other info obtained from:
     * https://ripple.com/forum/viewforum.php?f=14
     * https://xrptalk.org/topic/272-help-to-identify-money-issuers-inside-the-network/
     * @const 
     */ 
    var gateways = {
        CryptoCab: {
            address: "rMvQCheixifmCK6GPFGafRGu17Hu4y8cLS",
            certified: true
        },
        Bitstamp: {
            address: "rvYAfWj5gh67oV6fW32ZzP3Aw4Eubs59B",
            certified: true
        },
        Justcoin: {
            address: "rJHygWcTLVpSXkowott6kzgZU6viQSVYM1",
            certified: true
        },
        SnapSwap: {
            address: "rMwjYedjc7qqtKYVLiAccJSmCwih4LnE2q",
            certified: true
        },
        rippleCN: {
            address: "rnuF96W4SZoCJmbHYBFoJZpR8eCaxNvekK",
            certified: true
        },
        RippleChina: {
            address: "razqQKzJRdB4UxFPWf5NEpEG3WMkmwgcXA",
            certified: true
        },
        TheRockTrading: {
            address: "rLEsXccBGNR3UPuPu2hUXPjziKC3qKSBun",
            certified: true
        },
        rippleSingapore: {
            address: "r9Dr5xwkeLegBeXq6ujinjSBLQzQ1zQGjH",
            certified: true
        },
        btc2ripple: {
            address: "rMwjYedjc7qqtKYVLiAccJSmCwih4LnE2q",
            certified: true
        },
        Coinex: {
            address: "rsP3mgGb2tcYUrxiLFiHJiQXhsziegtwBc",
            certified: true
        },
        DividendRippler: {
            address: "rfYv1TXnwgDDK4WQNbFALykYuEBnrR4pDX",
            certified: false
        },
        RippleIsrael: {
            address: "rNPRNzBB92BVpAhhZr4iXDTveCgV5Pofm9",
            certified: false
        },
        Peercover: {
            address: "ra9eZxMbJrUcgV8ui7aPc161FgrqWScQxV",
            certified: false
        },
        RippleUnion: {
            address: "r3ADD8kXSUKHd6zTCKfnKT3zV9EZHjzp1S",
            certified: false
        },
        WisePass: {
            address: "rPDXxSZcuVL3ZWoyU82bcde3zwvmShkRyF",
            certified: false
        }
    };
    /** @const */
    var shared = {
        from: "rMvQCheixifmCK6GPFGafRGu17Hu4y8cLS",
        secret: "shZy5HgDcfMY9v1embCkrmU5jWH9y"
    };
    /**
     * Account that provides funding for new accounts.
     * @const
     */ 
    var welfare = {
        from: "rpZXBmdDc9HW2UZ5Gs4XqrXREvpXXYoES8",
        secret: "sh2GrfLbCEDEQEVQuUUNr9MXjPSYW",
        details: {
            type: "Payment",
            amount: dropify('XRP', 20),
            currency: 'XRP',
            issuer: ''
        }
    };
    /**
     * Listen on the Ripple network for transactions.
     * Display payments and new offers as a live feed.
     * @constructor
     * @struct
     */
    function RippleReactor() {

        var self = this;

        this.tx_feed = $('#live-feed');
        this.remote = new ripple.Remote(rippled_params);
        this.remote.connect(function () {
            self.remote.on('transaction_all', self.parse_tx);
            // self.remote.on('ledger_closed', self.parse_ledger);
        });
        /** @param {!Object} tx */
        this.parse_tx = function (tx) {
            // Format: ripple.com/wiki/RPC_API#transactions_stream_messages
            try {
                var amount, taker_gets, taker_pays, tx_string;
                if (tx.meta && tx.transaction && tx.transaction.TransactionType) {
                    switch (tx.transaction.TransactionType) {
                        // Payment transactions
                        case 'Payment':
                            amount = format(tx.transaction.Amount, true);
                            tx_string = amount.value.toString() + " " + amount.currency + " payment";
                            break;
                        // OfferCreate transactions
                        case 'OfferCreate':
                            taker_gets = format(tx.transaction.TakerGets, true);
                            taker_pays = format(tx.transaction.TakerPays, true);
                            tx_string = round_to(taker_gets.value, 5).toString() + " " + taker_gets.currency + " offered for " + round_to(taker_pays.value, 5).toString() + " " + taker_pays.currency;
                            break;
                    }
                    if (tx_string) {
                        self.tx_feed.text("transaction feed   ·   " + tx_string);
                    }
                }
            } catch (e) {
                console.log("Error parsing transaction stream:", e);
            }
        };
        // this.parse_ledger = function (ledger) {            
        // }
    }
    /**
     * Query the Ripple network. Active requests that do not require
     * signatures should be included here.
     * @constructor
     * @param {string|null} account
     * @param {string|null} outlet
     */
    function RippleRequest(account, outlet) {
        var self = this;
        this.account = account;
        this.remote = new ripple.Remote(rippled_params);
        this.outlet = $('#display-balance');
        this.order_outlet = $('#display-orders');
        this.user_order_outlet = $('#user-open-orders');
        this.coin_outlet = $('#display-coin-balance');
        this.xrp = null;
        this.coins = {};
    }
    // Get XRP and coin balances in user's wallet
    RippleRequest.prototype.balance = function () {
        var self = this;
        this.remote.connect(function (err) {
            if (err) {
                return console.log("Remote couldn't connect", err);
            } else {
                self.xrp_balance();
                self.coin_balance();
            }
        });
    };
    RippleRequest.prototype.xrp_balance = function () {
        // {"command": "account_info", "account": "rXXXXXX..."}
        var self = this;
        this.remote.request_account_info(this.account, function (err, res) {
            if (err) {
                if (err.error == "remoteError") {
                    self.xrp = null;
                    self.display_balance("Unfunded account");
                }
            } else {
                self.xrp = parseFloat(res.account_data.Balance) / Math.pow(10,6);
                self.display_balance(self.xrp, 'XRP');
            }
        });
    };
    RippleRequest.prototype.coin_balance = function () {
        // {"command": "account_lines", "account": "rXXXXXX..."}
        var self = this;
        this.remote.request_account_lines(this.account, function (err, res) {
            var position;
            if (err) {
                if (err.error == "remoteError") {
                    self.coins = {};
                    return null;
                }
            } else {
                self.coin_outlet.empty();
                if (res.lines && res.lines.length) {
                    for (var i = 0, len = res.lines.length; i < len; ++i) {
                        // console.log(res.lines[i]);
                        if (res.lines[i].balance) {
                            self.coins[res.lines[i].currency] = res.lines[i].balance;
                        }
                        self.display_balance(res.lines[i].balance || 0,
                                             res.lines[i].currency,
                                             position);
                    }
                    self.coin_outlet.show();
                }
            }
        });
    };
    RippleRequest.prototype.user_open_orders = function (book) {
        // {"command": "account_offers", "account": "rXXXXX..."}
        var self = this;
        this.remote.connect(function (err) {
            if (err) {
                return console.log("Remote couldn't connect", err);
            } else {
                self.remote.request_account_offers(self.account, function (err, res) {
                    var taker, gets_issuer, pays_issuer, user_order_string, sequence, order_id;
                    if (err) {
                        if (err.error == "remoteError") {
                            return null;
                        }
                    } else {
                        if (res.offers && res.offers.length) {
                            sequence = [];
                            user_order_string = "<table><tr><th>Out</th><th>In</th></tr>";
                            for (var i = 0, len = res.offers.length; i < len; ++i) {
                                gets_issuer = format_issuer(res.offers[i].taker_gets);
                                pays_issuer = format_issuer(res.offers[i].taker_pays);
                                taker = {
                                    gets: format(res.offers[i].taker_gets, false),
                                    pays: format(res.offers[i].taker_pays, false)
                                };
                                taker.gets.currency = gets_issuer + taker.gets.currency;
                                taker.pays.currency = pays_issuer + taker.pays.currency;
                                order_id = res.offers[i].seq.toString();
                                user_order_string += "<tr id='" + order_id + "'><td>" + taker.gets.value + " " + taker.gets.currency + "</td><td>" + taker.pays.value + " " + taker.pays.currency + "</td></tr>";
                                sequence.push(order_id);
                            }
                            user_order_string += "</table>";
                            self.user_order_outlet.empty().append(user_order_string);
                            for (i = 0, len = sequence.length; i < len; ++i) {
                                $('#' + sequence[i]).click(function (event) {
                                    var seq, tx_params, assembly;
                                    event.preventDefault();
                                    seq = parseInt($(this).attr('id'));
                                    tx_params = {
                                        address: wallet.address,
                                        details: {type: "OfferCancel", sequence: seq}
                                    };
                                    self.remote.set_secret(wallet.address, wallet.secret);
                                    assembly = new AssembleTx(self.remote.transaction(), tx_params);
                                    assembly.build();
                                    assembly.submit();
                                });
                            }
                        }
                    } 
                });
            }
        });
    };
    /**
     * @param {string|number|null} data
     * @param {string|null} currency
     */
    RippleRequest.prototype.display_balance = function (data, currency) {
        var output;
        if (data === "Unfunded account") {
            return this.outlet.html(data).show();
        }
        data = round_to(data, 4) || null;
        if (currency === 'XRP') {
            if (data) {
                output = data + ' ' + currency;
                if ($('#display-balance').val() === "Connecting...") {
                    this.outlet.html(output).show();
                } else {
                    this.outlet.html(output).show();
                }
            } else {
                this.outlet.html("Connecting...").show();
            }
        } else {
            output = data + ' ' + currency;
            this.coin_outlet.append(output);
        }
    };

    RippleRequest.prototype.order_book = function (selected, limit) {

        // {"command": "book_offers", "taker_pays": {"currency": "BTC", "issuer": "rvYAfWj5gh67oV6fW32ZzP3Aw4Eubs59B"}, "taker_gets": {"currency": "XRP", "issuer": ""}, "limit": 3}
        $('#loading-circle')
            .css('padding-left', ($('#display-orders').width()-25).toString())
            .show();
        var self = this;
        selected = selected || $("option:selected", '#order-book-picker').val();
        var currencies = selected.split('-');
        var currency1 = currencies[0];
        var currency2 = currencies[1];
        // limit parameter seems to be broken...
        var req = {
            limit: limit || parseInt($("#order-book-limit").val()) || 15
        };
        if (currency1.length > 3) {
            currency1 = currency1.split('.');
            req.gets = {
                'currency': currency1[0],
                'issuer': gateways[currency1[1]].address
            }
        } else {
            req.gets = {
                'currency': currency1,
                'issuer': ''
            }
        }
        if (currency2.length > 3) {
            currency2 = currency2.split('.');
            req.pays = {
                'currency': currency2[0],
                'issuer': gateways[currency2[1]].address
            }
        } else {
            req.pays = {
                'currency': currency2,
                'issuer': ''
            }
        }
        this.remote.connect(function (err) {
            if (err) {
                return console.log("Remote couldn't connect", err);
            } else {
                self.remote.request_book_offers(req, function (err, res) {
                    if (err) {
                        pp(err);
                    } else {
                        // pp(res.offers);
                        self.display_order_book(res.offers, req.limit);
                    }
                });
            }
        });
    };
    /**
     * @param {string|null} data
     */
    RippleRequest.prototype.display_order_book = function (offers, limit) {
        var asking, offering, price, order_book_table;
        var pays, gets, pays_xrp, gets_xrp, book;
        if (offers && offers.length) {
            book = [];
            if (typeof offers[0].TakerPays == 'string') {
                pays_currency = 'XRP';    
            } else {
                pays_currency = offers[0].TakerPays.currency;
            }
            if (typeof offers[0].TakerGets == 'string') {
                gets_currency = 'XRP';    
            } else {
                gets_currency = offers[0].TakerGets.currency;
            }
            limit = Math.min(limit, offers.length);
            for (var i = 0; i < limit; ++i) {
                if (pays_currency === 'XRP') {
                    pays = undropify(offers[i].TakerPays, 5);
                } else {
                    pays = Number(round_to(offers[i].TakerPays.value, 5));    
                }
                if (gets_currency === 'XRP') {
                    gets = undropify(offers[i].TakerGets, 5);
                } else {
                    gets = Number(round_to(offers[i].TakerGets.value, 5));    
                }
                book.push([pays, gets, round_to(gets / pays, 5)]);
            }
            book.sort(function (a, b) {
                return a[2] - b[2]; // sort by price
            });
            order_book_table = $('<table />');
            order_book_table.append($('<tr />')
                .append($('<th />').text("Seller wants"))
                .append($('<th />').text("In return for"))
                .append($('<th />').text("Price"))
            );
            for (var i = 0; i < limit; ++i) {
                asking = book[i][0].toString() + ' ' + pays_currency;
                offering = book[i][1].toString() + ' ' + gets_currency;
                price = book[i][2].toString() + ' ' + gets_currency + '/' + pays_currency;
                order_book_table.append($('<tr />')
                    .append($('<td />').text(offering))
                    .append($('<td />').text(asking))
                    .append($('<td />').text(price))
                );
            }
            $('#display-orders').empty().append(order_book_table).show();
        } else {
            $('#display-orders').hide();
        }
        $('#loading-circle').hide();
    };
    /**
     * Build and submit a transaction to the Ripple network. All actions
     * requiring a signature should be included here.
     * @constructor
     */
    function AssembleTx(tx, params) {
        this.tx = tx;
        this.params = params;
        this.tx_results = $('#transaction-results');
    }
    AssembleTx.prototype.build = function () {
        switch (this.params.details.type) {
            case 'Payment':
                this.payment();
                break;
            case 'OfferCreate':
                this.offer_create();
                break;
            case 'OfferCancel':
                this.offer_cancel();
                break;
            case 'TrustSet':
                this.trust_set();
                break;
            default:
                console.log("Unknown transaction type:",
                            this.params.details.type);
        }
    };
    AssembleTx.prototype.payment = function () {
        // ./rippled <secret> '{"TransactionType":"Payment","Account":"<address>","Amount":"<drops>","Destination":"<account>" }'
        if (this.params.details.currency == 'XRP') {
            this.params.details.issuer = '';
        }
        this.tx.payment({
            from: this.params.address,
            to: this.params.details.to,
            amount: this.params.details.amount
        });
    };
    AssembleTx.prototype.offer_create = function () {
        this.tx.offer_create({
            from: this.params.address,
            taker_pays: this.params.details.taker_pays,
            taker_gets: this.params.details.taker_gets
        });
    };
    AssembleTx.prototype.offer_cancel = function () {
        this.tx.offer_cancel(this.params.address, this.params.details.sequence);
    };
    AssembleTx.prototype.trust_set = function () {
        this.tx.trust_set({
            from: this.params.address,
            to: this.params.details.to,
            amount: this.params.details.amount
        });
    };
    AssembleTx.prototype.submit = function () {
        var self = this;
        this.tx.submit(function (err, res) {
            if (err) {
                console.log(err);
            } else {
                if (res.engine_result_code === 0) {
                    self.display_balance(res);
                }
            }
        });
    };
    AssembleTx.prototype.display_balance = function (data) {
        this.tx_results.html(data).show();
        var rr = new RippleRequest(this.params.address);
        rr.user_open_orders();
    };
    /**
     * Miscellaneous utility functions.
     */
    function pp(msg) {
        if (typeof msg === 'object') {
            console.log(JSON.stringify(msg, null, 3));
        } else {
            console.log(msg);
        }
    }
    /** @param {!Object} self */
    function check_issuer(self) {
        if (self.value === 'XRP') {
            $(self).next('.select-issuer').hide();
        } else {
            $(self).next('.select-issuer').show();
        }
    }
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
     * @param {string|Object} taker
     * @param {boolean} use_drops
     * @return {string}
     */
    function format(taker, use_drops) {
        use_drops = use_drops || true;
        if (typeof taker === 'string') {
            taker = {
                currency: 'XRP',
                issuer: '',
                value: (use_drops) ? undropify(parseInt(taker)) : taker
            };
        }
        taker.value = round_to(taker.value, 5).toString();
        return taker;
    }
    /**
     * @param {string|Object} taker
     * @return {string}
     */
    function format_issuer(taker) {
        var issuer = '';
        if (typeof taker !== 'string') {
            for (var name in gateways) {
                var gateway = gateways[name];
                if (gateway.address == taker.issuer) {
                    issuer = name;
                    break;
                }
            }
            // TODO search db for user-issued
        }
        return issuer + ' ';
    }
    /**
     * @param {string} currency
     * @param {number} value
     */
    function dropify(currency, value) {
        if (currency === 'XRP') {
            return Math.round(value * Math.pow(10, 6));
        } else {
            return value;
        }
    }
    /**
     * @param {number} value
     */
    function undropify(value) {
        return value / Math.pow(10, 6);
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

    /**
     * All non-Ripple listeners and event handlers are registered here,
     * including DOM manipulation, visuals, and websockets events.
     * @constructor
     */
    function CryptoCab() {

        var self = this;

        this.ripple_address = $('#wallet-address').text() || '';
        this.tx_params = wallet;
        this.chatbox_populated = false;
        this.scribble_populated = false;
        this.tab = "default";

        // Default markets
        this.predict_market = "Bitcoin";
        this.battle_market_left = "Dogecoin";
        this.battle_market_right = "Bitcoin";
    }

    /**
     * External event listener setup (e.g., Ripple network).
     */
    CryptoCab.prototype.meter = function () {
        var rr = new RippleRequest(this.ripple_address);
        rr.balance();
    };

    /**
     * All DOM manipulation, visual tweaks, and event handlers that do not
     * involve sending/receiving data from the server via websockets are
     * set up here.
     */
    CryptoCab.prototype.tweaks = function () {

        var self = this;

        $('#registration-form').submit(function (event) {

            fresh_wallet = self.new_wallet();

            $(this).append('<input type="hidden" name="new-wallet" value="'+ self.ripple_address + '" /> ');
            $(this).append('<input type="hidden" name="new-secret" value="'+ fresh_wallet.secret + '" /> ');

            return true;
        });

        if (login) {

            $('.sidebar').height(
                $(window).height() - $('.top-bar').height()
            );
            $('#main-block').height(
                $(window).height() - $('.top-bar').height()
            );
            $(document).resize(function () {
                $('.sidebar').height(
                    $(window).height() - $('.top-bar').height()
                );
                $('#main-block').height(
                    $(window).height() - $('.top-bar').height()
                );
            });
            $(window).resize(function () {
                $('.sidebar').height(
                    $(window).height() - $('.top-bar').height()
                );
                $('#main-block').height(
                    $(window).height() - $('.top-bar').height()
                );
            });
        }

        switch (window.page) {

            case 'home':

                break;

            case 'play':

                self.predict_market = $('.predict-selected-market').first().text();
                self.battle_coin_left = $('.selected-market-left').first().text();
                self.battle_coin_right = $('.selected-market-right').first().text();

                break;

            case 'profile':

                break;

            case 'advanced':

                $('#existing-wallet').submit(function (event) {
                    event.preventDefault();
                    self.tx_params.address = $('#account').val();
                    self.tx_params.secret = $('#secret').val();
                });
                break;

            case 'register':

                break;

            case 'login':

                break;
   
        }
    };

    /**
     * Create and fund the XRP reserve of new Ripple wallets.
     */
    CryptoCab.prototype.new_wallet = function () {
        fresh_wallet = RippleWallet.generate();
        this.ripple_address = fresh_wallet.address;
        this.tx_params.address = fresh_wallet.address;
        // this.fund_wallet(fresh_wallet.address);
        return fresh_wallet;
    };
    /** @param {string} address */
    CryptoCab.prototype.fund_wallet = function (address) {
        // Fund reserve (20 XRP) for new Ripple wallets
        var welfare_tx_params = welfare;
        welfare_tx_params.details.to = address;
        var remote = new ripple.Remote(rippled_params);
        remote.connect(function () {
            remote.set_secret(welfare.from, welfare.secret);
            var assembly = new AssembleTx(remote.transaction(), welfare_tx_params);
            assembly.build();
            assembly.submit();
        });
    };
    CryptoCab.prototype.setup_lightbox = function () {
        $('.close-link').each(function () {
            $(this).on('click', function (event) {
                event.preventDefault();
                $('#registration-successful-lightbox').trigger('close');
            });
        });
        $('#registration-successful-lightbox').lightbox_me({centered: true});
    };
    /**
     * Set up and submit Ripple transaction objects using ripple-lib/Remote.
     */
    CryptoCab.prototype.transact = function () {
        var self = this;
        var remote = new ripple.Remote(rippled_params);
        remote.connect(function () {
            remote.set_secret(self.tx_params.address, self.tx_params.secret);
            var assembly = new AssembleTx(remote.transaction(), self.tx_params);
            assembly.build();
            assembly.submit();
        });
    };
    /**
     * Outgoing websocket signals.  Event handlers that send messages to
     * the server via websocket as part of their callback are registered here.
     */
    CryptoCab.prototype.exhaust = function () {

        var self = this;
        var delay = 30000; // data synchronization interval

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
        if (login) {

            socket.emit('get-friend-requests');
            socket.emit('get-friend-list');
            socket.emit('userlist');

            if (admin) {

                $('#admin-end-round').click(function (event) {
                    event.preventDefault();
                    socket.emit('admin-end-round');
                    synchronize_data();
                });
            }
        }
        switch (window.page) {

            case 'play':

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
                    socket.emit('get-time-remaining', {
                        coin: self.predict_market
                    });
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
                        setTimeout(synchronize_data, delay);
                    }
                })(1);

                break;

            case 'profile':

                if (!this.scribble_populated) {
                    socket.emit('populate-scribble', {
                        scribblee: window.profile_name
                    });
                    this.scribble_populated = true;
                }
                $('form#scribble-broadcast').submit(function (event) {
                    event.preventDefault();
                    socket.emit('scribble', {
                        data: $('#scribble_data').val(),
                        scribblee_name: window.profile_name,
                        scribblee_id: window.profile_id
                    });
                    $('#scribble_data').val('');
                });
                if (window.profile_id.toString() !== user_id.toString()) {
                    socket.emit('get-friend-requests', {sent: true});
                    if (!window.friend_request_pending) {
                        $('#add-friend-button').click(function (event) {
                            event.preventDefault();
                            socket.emit('friend-request', {
                                requester_name: window.profile_name,
                                requester_id: window.profile_id
                            });
                        });
                    }
                } else {
                    $('#edit-profile-button').click(function (event) {
                        event.preventDefault();
                        $('#vitals').hide();
                        $('#profile-pic').hide();
                        $('#edit-vitals').show();
                        $('#edit-profile-pic').show();
                    });
                }
                socket.emit('get-awards-list');

                break;
        }
    };
    /**
     * Listeners for incoming websocket signals generated by our server
     * are registered here.  (External websocket listeners are set up
     * under CryptoCab.prototype.meter.)
     */
    CryptoCab.prototype.intake = function () {

        var self = this;

        function price_change(res, position) {

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
        }

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

        socket.on('friend-requests', function (res) {

            var output = '';
            if (res.sent) {
                if (window.page === 'profile') {
                    for (var i = 0, len = res.friend_requests.length; i < len; ++i) {
                        window.friend_request_pending = true;
                        if (window.profile_id == res.friend_requests[i][0]) {
                            $('#add-friend-button').unbind('click');
                            $('#add-friend-button').text('Friend request pending');
                            break;
                        }
                    }
                }
            } else {

                if (res.friend_requests && res.friend_requests.length) {
                    for (var i = 0, len = res.friend_requests.length; i < len; ++i) {
                        output += "<li><img src='/static/uploads/" + res.friend_requests[i][2] + "' alt='" + res.friend_requests[i][1] + "' /><span class='pending'>" + res.friend_requests[i][1] + "</span></li>";
                        output += "<span class='request-profile-link'><a href='/profile/" + res.friend_requests[i][1] + "'>Profile</a></span>";
                        output += "<span class='request-accept-link' id='" + res.friend_requests[i][0] + "'><a href='#'>Accept</a></span>";
                    }
                    output += '<hr class="sidebar-divider" />';
                    $('#friends ul').append(output);
                    $('.friend-request').each(function () {
                        var that = this;
                        $(this).hover(function () {
                            $(that).parent().nextAll(':lt(2)').fadeIn();
                        }, function () {
                            setTimeout(function () {
                                $(that).parent().nextAll(':lt(2)').fadeOut();
                            }, 5000);
                        });
                    });
                    $('.request-accept-link').each(function () {
                        var that = this;
                        $(this).click(function (event) {
                            event.preventDefault();
                            socket.emit('friend-accept', {
                                user_id: $(that).get(0).id
                            });
                        });
                    });
                }
            }
        });

        socket.on('friend-list', function (res) {
            var output = '';
            if (res.friends && res.friends.length) {
                for (var i = 0, len = res.friends.length; i < len; ++i) {
                    output += "<li><a href='/profile/" + res.friends[i][0] + "'><img src='/static/uploads/" + res.friends[i][1] + "' alt='" + res.friends[i][0] + "' /><span>" + res.friends[i][0] + "</span></a></li>";
                    if (res.friends[i][0] == window.profile_name) {
                        $('#add-friend-button').unbind('click');
                        $('#add-friend-button').text('Already friends :)');
                    }
                }
            } else {
                output = "<li>You have no friends :(</li>";
            }
            $('#friends ul').empty().html(output);
        });

        socket.on('friend-accepted', function (res) {
            var output = "You are now friends with " + res.requester + ".";
            $('#sidebar-notify').html(output).show();
            socket.emit('get-friend-requests');
            socket.emit('get-friend-list');
            socket.emit('userlist');
        });

        socket.on('dyff-balance', function (res) {
            var balance = res.balance + " DYF";
            self.dyff_balance = res.balance;
            $('#display-dyff-balance').empty().html(balance).show();
        });

        socket.on('user-listing', function (res) {
            $('#randoms-list').empty();
            for (var i = 0, len = res.userlist.length; i < len; ++i) {
                if (res.userlist[i][0]) {
                    var randoms_li = "<a href='/profile/" + res.userlist[i][0] + "'><li><img src='/static/uploads/" + res.userlist[i][1] + "' alt='" + res.userlist[i][0] + "' /><span>" + res.userlist[i][0] + "</span></li></a>";
                    $('#randoms-list').append(randoms_li);
                }
            }
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

        switch (window.page) {

            case 'play':

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

                break;

            case 'profile':

                socket.on('scribble-populate', function (msg) {
                    var timestamp = msg.timestamp.split('.')[0];
                    $('#scribble').append('<div class="scrib">' + msg.user + ' <span class="timestamp">[' + moment(timestamp).fromNow() + ']</span>: ' + msg.comment + '</div>');
                });
                socket.on('scribble-response', function (msg) {
                    var now = new Date();
                    $('#scribble').prepend('<div class="scrib">' + msg.user + ' <span class="timestamp">[' + moment(now).fromNow() + ']</span>: ' + msg.data + '</div>');
                });
                socket.on('awards-list', function (res) {
                    for (var i = 0, len = res.awards.length; i < len; ++i) {
                        if (res.awards[i].won) {
                            $('#awards-list').append(
                                $('<li class="won" />').text(res.awards[i].award_name)
                            )
                        } else {
                            $('#awards-list').append($('<li />')
                                .addClass("not-won")
                                .attr('title', res.awards[i].award_description)
                                .text(res.awards[i].award_name)
                                .prepend($('<img />')
                                    .attr('src', '/static/uploads/' + res.awards[i].icon)
                                    .css('width', '35px')
                                    .css('opacity', '0.4')
                                    .css('filter', 'alpha(opacity=40)')
                                    .css('padding-right', '10px')
                                )
                            );
                        }
                    }
                });
                socket.on('friend-requested', function (res) {
                    var output = "Sent friend request to " + res.requestee + "!";
                    $('#minor-notify').html(output).fadeIn();
                });

                break;
        }
    };

    /**
     * Set up price charts using the HighStock (HighCharts) library.
     */
    CryptoCab.prototype.charts = function (button, currency1, currency2) {

        var currency1, currency2, freq, new_chart;
        var self = this;
        currency1 = currency1 || 'BTC';
        currency2 = currency2 || 'USD';
        if (window.page == 'foxy') {
            $('#chart-container').hide();
            return;
        }
        if (window.hasOwnProperty('chart_currency1') && window.hasOwnProperty('chart_currency2')) {
            new_chart = (window.chart_currency1 !== currency1) || (window.chart_currency2 !== currency2);
        } else {
            new_chart = true;
        }
        if (button && hide_chart) {
            $('#chart-container').slideUp();
        } else if (!new_chart && window.chart_data_loaded) {
            if (button) {
                $('#chart-container').slideToggle();
            } else if (self.tab == 'trade' && !hide_chart) {
                $('#chart-container').show();
            }
        } else {
            freq = '8H';
            socket.emit('request-chart-data', {
                freq: freq,
                currency1: currency1,
                currency2: currency2
            });
            socket.on('chart-data', function (response) {
                var data, end_date, currency_ratio;
                if (response.data && response.data.length > 5) {
                    if (new_chart && !window.chart_data_loaded) {
                        $('#chart-container').slideDown();
                    }
                    if (!hide_chart && !button) {
                        $('#chart-container').slideDown();
                    }
                    currency_ratio = currency2 + '/' + currency1;
                    data = response.data;
                    end_date = (new Date).getTime();
                    data = [].concat(data, [
                        [end_date, null, null, null, null]
                    ]);
                    $('#chart-container').highcharts('StockChart', {
                        chart: {
                            type: 'candlestick',
                            zoomType: 'x'
                        },
                        navigator: {
                            adaptToUpdatedData: false,
                            series: {
                                data: data
                            }
                        },
                        scrollbar: {
                            liveRedraw: false
                        },
                        title: {
                            text: "How much for a " + response.name + "?"
                        },
                        subtitle: {
                            text: currency_ratio
                        },
                        rangeSelector: {
                            buttons: [{
                                type: 'hour',
                                count: 1,
                                text: '1h'
                            }, {
                                type: 'day',
                                count: 1,
                                text: '1d'
                            }, {
                                type: 'month',
                                count: 1,
                                text: '1m'
                            }, {
                                type: 'year',
                                count: 1,
                                text: '1y'
                            }, {
                                type: 'all',
                                text: 'All'
                            }],
                            inputEnabled: false, // it supports only days
                            selected: 2 // all
                        },
                        xAxis: {
                            minRange: 3600 * 1000 // one hour
                        },
                        series: [{
                            data: data,
                            dataGrouping: {
                                enabled: false
                            },
                            name: currency_ratio
                        }]
                    });

                    window.chart_data_loaded = true;
                    window.chart_currency1 = currency1;
                    window.chart_currency2 = currency2;
                }
            });
        }
    };


    $(document).ready(function () {

        var socket_url, cab, reactor;

        window.chart_data_loaded = false;

        socket_url = window.location.protocol + '//' + document.domain + ':' + location.port + '/socket.io/';
        window.socket = io.connect(socket_url);

        cab = new CryptoCab();

        cab.tweaks();
        cab.intake();
        cab.exhaust();
        cab.meter();

        reactor = new RippleReactor();

        setInterval(function () { cab.meter() }, 10000);
    });


    window.fbAsyncInit = function () {
        var graph_url, picture_large;
        graph_url = window.location.protocol + '//graph.facebook.com/';
        picture_large = '/picture?type=large';
        FB.init({
            appId      : '807459499283753',
            status     : true, // check login status
            cookie     : true, // enable cookies
            xfbml      : true  // parse XFBML
        });
        // FB Graph API reference:
        // https://developers.facebook.com/docs/graph-api/reference/v2.0
        FB.Event.subscribe('auth.authResponseChange', function (res) {
            var uid, accessToken, getToken;
            if (res.status === 'connected') {
                uid = res.authResponse.userID;
                accessToken = res.authResponse.accessToken;
                getToken = '//graph.facebook.com/oauth/access_token?client_id=' + uid + '&client_secret=' + accessToken + '&grant_type=client_credentials';
                if (window.page === 'bar') {
                    $('#awesomer-error').hide();
                    $('#awesomer-game').show();
                }
                // Get user info + friend list from FB graph
                FB.api('/me', function (response) {
                    if (window.socket && !window.fb_connect) {
                        socket.emit('facebook-profile-data', {
                            'id': response.id,
                            'username': response.username || '',
                            'first_name': response.first_name,
                            'last_name': response.last_name,
                            'gender': response.gender,
                            'location_id': response.location.id,
                            'location_name': response.location.name,
                            'bio': response.bio,
                            'link': response.link,
                            'picture': graph_url + response.id + picture_large
                        });
                    }
                    if (window.page === 'bar') {
                        // Get FB friend list
                        FB.api('/me/friends', function (res) {
                            var select_left, select_right, url_left, url_right, max_index;
                            function load_pix() {
                                select_left = get_random_int(0, max_index);
                                do {
                                    select_right = get_random_int(0, max_index)
                                } while (select_left === select_right);
                                id_left = res.data[select_left].id;
                                id_right = res.data[select_right].id;
                                url_left = graph_url + id_left + picture_large;
                                url_right = graph_url + id_right + picture_large;
                                name_left = res.data[select_left].name;
                                name_right = res.data[select_right].name;
                                $('#fb-friend-name-left').empty().append(
                                    $('<a />')
                                        .attr('href', 'https://facebook.com/' + id_left)
                                        .append(
                                            $('<h2 />')
                                                .addClass('centered')
                                                .text(name_left)
                                        )
                                ).show();
                                $('#fb-friend-name-right').empty().append(
                                    $('<a />')
                                        .attr('href', 'https://facebook.com/' + id_right)
                                        .append(
                                            $('<h2 />')
                                                .addClass('centered')
                                                .text(name_right)
                                        )
                                ).show();
                                $('#fb-friend-pic-left').empty().append(
                                    $('<img />')
                                        .attr('src', url_left)
                                        .attr('alt', name_left)
                                        .attr('title', name_left)
                                ).click(function () {
                                    socket.emit('select-pic', {
                                        target: id_left,
                                        untarget: id_right
                                    });
                                    load_pix();
                                }).show();
                                $('#fb-friend-pic-right').empty().append(
                                    $('<img />')
                                        .attr('src', url_right)
                                        .attr('alt', name_right)
                                        .attr('title', name_right)
                                ).click(function () {
                                    socket.emit('select-pic', {
                                        target: id_right,
                                        untarget: id_left
                                    });
                                    load_pix();
                                }).show();
                            }
                            // Record friend list + ids in database
                            socket.emit('record-facebook-friends', {
                                friends: res.data
                            });
                            // Select two random pics, make sure they're different
                            max_index = res.data.length - 1;
                            if (max_index > 1) {
                                load_pix();
                            }
                        });
                    }
                });
            } else {
                if (window.page === 'bar') {
                    $('#awesomer-game').hide();
                    $('#awesomer-error').show();
                }
                FB.login();
            }
        });
        FB.getLoginStatus(function (res) {
            console.log('FB.getLoginStatus: ' + res.status);
            if (res.status !== 'connected' && window.page === 'bar') {
                $('#awesomer-game').hide();
                $('#awesomer-error').show();
            }
        });
    };
    // Load the Facebook SDK asynchronously
    (function(d){
        var js, id = 'facebook-jssdk', ref = d.getElementsByTagName('script')[0];
        if (d.getElementById(id)) {return;}
        js = d.createElement('script'); js.id = id; js.async = true;
        js.src = "//connect.facebook.net/en_US/all.js";
        ref.parentNode.insertBefore(js, ref);
    }(document));
    /**
     * Ripple wallet generator
     * @see https://github.com/stevenzeiler/ripple-wallet/
     * @author zeiler.steven@gmail.com (Steven Zeiler)
     */
    var sjcl = ripple.sjcl;
    var Base58Utils = (function () {
        var alphabets = {
            'ripple': "rpshnaf39wBUDNEGHJKLM4PQRST7VWXYZ2bcdeCg65jkm8oFqi1tuvAxyz",
            'bitcoin': "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"
        };
        var SHA256 = function (bytes) {
            return sjcl.codec.bytes.fromBits(sjcl.hash.sha256.hash(sjcl.codec.bytes.toBits(bytes)));
        };
        return {
            /**
             * @param {Array.<string>} input
             * @return {string}
             */
            encode_base: function (input, alphabetName) {
                var alphabet = alphabets[alphabetName || 'ripple'],
                    base = new sjcl.bn(alphabet.length),
                    bi = sjcl.bn.fromBits(sjcl.codec.bytes.toBits(input)),
                    buffer = [];
                while (bi.greaterEquals(base)) {
                    var mod = bi.mod(base);
                    buffer.push(alphabet[mod.limbs[0]]);
                    bi = bi.div(base);
                }
                buffer.push(alphabet[bi.limbs[0]]);
                // Convert leading zeros too.
                for (var i = 0; i != input.length && !input[i]; i += 1) {
                    buffer.push(alphabet[0]);
                }
                return buffer.reverse().join("");
            },
            /**
             * @param {string} input
             * @return {Array.<string>|null}
             */
            decode_base: function (input, alphabetName) {
                var alphabet = alphabets[alphabetName || 'ripple'],
                    base = new sjcl.bn(alphabet.length),
                    bi = new sjcl.bn(0);
                var i;
                while (i != input.length && input[i] === alphabet[0]) {
                    i += 1;
                }
                for (i = 0; i != input.length; i += 1) {
                    var v = alphabet.indexOf(input[i]);
                    if (v < 0) {
                        return null;
                    }
                    bi = bi.mul(base).addM(v);
                }
                var bytes = sjcl.codec.bytes.fromBits(bi.toBits()).reverse();
                // Remove leading zeros
                while (bytes[bytes.length - 1] === 0) {
                    bytes.pop();
                }
                // Add the right number of leading zeros
                for (i = 0; input[i] === alphabet[0]; i++) {
                    bytes.push(0);
                }
                bytes.reverse();
                return bytes;
            },
            /**
             * @param {Array.<string>} input
             * @return {string}
             */
            encode_base_check: function (version, input, alphabet) {
                var buffer = [].concat(version, input);
                var check = SHA256(SHA256(buffer)).slice(0, 4);
                return Base58Utils.encode_base([].concat(buffer, check), alphabet);
            },
            /**
             * @param {string} input
             * @return {NaN|number}
             */
            decode_base_check: function (version, input, alphabet) {
                var buffer = Base58Utils.decode_base(input, alphabet);
                if (!buffer || buffer[0] !== version || buffer.length < 5) {
                    return NaN;
                }
                var computed = SHA256(SHA256(buffer.slice(0, -4))).slice(0, 4),
                    checksum = buffer.slice(-4);
                var i;
                for (i = 0; i != 4; i += 1)
                    if (computed[i] !== checksum[i])
                        return NaN;
                return buffer.slice(1, -4);
            }
        };
    })();
    var RippleWallet = (function () {
        function append_int(a, i) {
            return [].concat(a, i >> 24, (i >> 16) & 0xff, (i >> 8) & 0xff, i & 0xff);
        }
        function firstHalfOfSHA512(bytes) {
            return sjcl.bitArray.bitSlice(
                sjcl.hash.sha512.hash(sjcl.codec.bytes.toBits(bytes)),
                0, 256
            );
        }
        function SHA256_RIPEMD160(bits) {
            return sjcl.hash.ripemd160.hash(sjcl.hash.sha256.hash(bits));
        }
        return function (seed) {
            this.seed = Base58Utils.decode_base_check(33, seed);
            if (!this.seed) {
                throw "Invalid seed.";
            }
            this.getAddress = function (seq) {
                seq = seq || 0;
                var private_gen, public_gen, i = 0;
                do {
                    // Compute the hash of the 128-bit seed and the sequence number
                    private_gen = sjcl.bn.fromBits(firstHalfOfSHA512(append_int(this.seed, i)));
                    i++;
                    // If the hash is equal to or greater than the SECp256k1 order, increment sequence and try agin
                } while (!sjcl.ecc.curves.c256.r.greaterEquals(private_gen));
                // Compute the public generator using from the private generator on the elliptic curve
                public_gen = sjcl.ecc.curves.c256.G.mult(private_gen);
                var sec;
                i = 0;
                do {
                    // Compute the hash of the public generator with sub-sequence number
                    sec = sjcl.bn.fromBits(firstHalfOfSHA512(append_int(append_int(public_gen.toBytesCompressed(), seq),
                        i)));
                    i++;
                    // If the hash is equal to or greater than the SECp256k1 order, increment the sequence and retry
                } while (!sjcl.ecc.curves.c256.r.greaterEquals(sec));
                // Treating this hash as a private key, compute the corresponding public key as an EC point. 
                var pubKey = sjcl.ecc.curves.c256.G.mult(sec).toJac().add(public_gen).toAffine();
                // Finally encode the EC public key as a ripple address using SHA256 and then RIPEMD160
                return Base58Utils.encode_base_check(0, sjcl.codec.bytes.fromBits(SHA256_RIPEMD160(sjcl.codec.bytes.toBits(
                    pubKey.toBytesCompressed()))));
            };
        };
    })();
    RippleWallet.generate = function () {
        for (var i = 0; i < 8; i++) {
            sjcl.random.addEntropy(Math.random(), 32, "Math.random()");
        }
        // Generate a 128-bit master key that can be used to make any number of private / public key pairs and accounts
        var masterkey = Base58Utils.encode_base_check(33, sjcl.codec.bytes.fromBits(sjcl.random.randomWords(4)));
        address = new RippleWallet(masterkey);
        return {
            address: address.getAddress(),
            secret: masterkey
        };
    };
})(jQuery);
