from sqlalchemy import DDL

############
# Triggers #
############

insert_user_trigger = DDL(
'''
CREATE TRIGGER insert_user_trigger
    AFTER INSERT ON users
    FOR EACH ROW
    EXECUTE PROCEDURE create_wallet()
''')

bet_trigger = DDL(
'''
CREATE TRIGGER bet_trigger
    AFTER INSERT ON bets
    FOR EACH ROW
    EXECUTE PROCEDURE bet_history_record()
''')


#############
# Functions #
#############

create_wallet = DDL(
'''
CREATE OR REPLACE FUNCTION create_wallet()
RETURNS trigger AS $$
BEGIN
    INSERT INTO wallets
        (user_id, dyf_balance)
    SELECT
        NEW.id, 100;
    RETURN NULL;
END;
$$ LANGUAGE plpgsql
''')

bet_history_record = DDL(
'''
CREATE OR REPLACE FUNCTION bet_history_record()
RETURNS trigger AS $$
BEGIN
    INSERT INTO bet_history
        (user_id, game_id, game, amount, currency,
        guess, time_of_bet)
    SELECT
        NEW.user_id, NEW.game_id, NEW.game, NEW.amount, NEW.currency,
        NEW.guess, NEW.time_of_bet;
    RETURN NULL;
END;
$$ LANGUAGE plpgsql
''')
