CREATE TABLE accounts (
    id integer PRIMARY KEY,
    balance integer NOT NULL CHECK (balance >= 0)
);
INSERT INTO accounts VALUES (1, 100), (2, 100);
