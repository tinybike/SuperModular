CREATE USER babbage WITH PASSWORD 'Coff33_cultur3';
ALTER USER babbage CREATEDB;
CREATE DATABASE babbage ENCODING 'SQL_ASCII' TEMPLATE=template0;
GRANT ALL PRIVILEGES ON DATABASE "babbage" TO babbage;

\c babbage;
ALTER SCHEMA public OWNER TO babbage;
-- psql -Ubabbage -W -hlocalhost -dpostgres