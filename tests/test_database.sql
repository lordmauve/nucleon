CREATE ROLE db_test_user WITH PASSWORD 'db_test_password' LOGIN;
CREATE ROLE some_other_user WITH PASSWORD 'another_test_password' LOGIN;

CREATE DATABASE test_database;

GRANT ALL PRIVILEGES ON DATABASE test_database TO db_test_user;
GRANT ALL PRIVILEGES ON DATABASE test_database TO some_other_user;
