/* SQL schema for testing database management operations; 

  This contains syntax that we have to pay particular care
  about handling correctly.

*/

CREATE TABLE test (
    id SERIAL PRIMARY KEY,
    name VARCHAR(50) NOT NULL
);

CREATE TABLE test2 (
    test_id INTEGER REFERENCES test(id)
);


-- Test that various ways of quoting are correctly parsed;
INSERT INTO test(name) VALUES ($val$foo;$val$), ('bar;'), ('baz'''), ('');
INSERT INTO test2(test_id) VALUES (lastval());

