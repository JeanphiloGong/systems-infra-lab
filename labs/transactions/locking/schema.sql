CREATE TABLE inventory (id integer PRIMARY KEY, quantity integer NOT NULL CHECK (quantity >= 0), version integer NOT NULL);
INSERT INTO inventory VALUES (1, 10, 0);
