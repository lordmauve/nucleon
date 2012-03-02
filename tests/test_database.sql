CREATE ROLE db_test_user WITH PASSWORD 'db_test_password' LOGIN;
CREATE ROLE some_other_user WITH PASSWORD 'another_test_password' LOGIN;

CREATE ROLE nucleondb1 WITH PASSWORD 'nucleondb1' LOGIN;
CREATE ROLE nucleondb2 WITH PASSWORD 'nucleondb2' LOGIN;

CREATE DATABASE test_database;
CREATE DATABASE nucleondb1 OWNER nucleondb1;
CREATE DATABASE nucleondb2 OWNER nucleondb2;

GRANT ALL PRIVILEGES ON DATABASE test_database TO db_test_user;
GRANT ALL PRIVILEGES ON DATABASE test_database TO some_other_user;
