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

confirmation_trigger = DDL(
'''
CREATE TRIGGER confirmation_trigger
    AFTER UPDATE ON bridge
    FOR EACH ROW
    EXECUTE PROCEDURE confirmation_notify();
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
        (user_id, red, blue, amount, currency,
        target, time_of_bet)
    SELECT
        NEW.user_id, NEW.red, NEW.blue, NEW.amount, NEW.currency,
        NEW.target, NEW.time_of_bet;
    RETURN NULL;
END;
$$ LANGUAGE plpgsql
''')

confirmation_notify = DDL(
'''
CREATE OR REPLACE FUNCTION confirmation_notify()
RETURNS trigger AS $$
DECLARE
BEGIN
    PERFORM pg_notify('confirmation', NEW.txid);
    RETURN new;
END;
$$ LANGUAGE plpgsql
''')
