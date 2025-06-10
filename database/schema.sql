-- schema.sql
CREATE TABLE banks (
    bank_id NUMBER PRIMARY KEY,
    bank_name VARCHAR2(100) NOT NULL
);

CREATE TABLE reviews (
    review_id NUMBER PRIMARY KEY,
    bank_id NUMBER REFERENCES banks(bank_id),
    review_text CLOB,
    rating NUMBER,
    date_posted DATE,
    sentiment_label VARCHAR2(20),
    theme VARCHAR2(100)
);