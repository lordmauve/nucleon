CREATE TABLE test (
    id SERIAL PRIMARY KEY,
    name VARCHAR(50) NOT NULL
);

INSERT INTO test(name) VALUES ('foo'), ('bar'), ('baz');
