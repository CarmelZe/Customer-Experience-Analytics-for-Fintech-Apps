-- data.sql
INSERT INTO banks (bank_id, bank_name) VALUES (1, 'Commercial Bank of Ethiopia');
INSERT INTO reviews (review_id, bank_id, review_text, rating, date_posted, sentiment_label, theme) 
VALUES (1, 1, 'Great app but slow transfers', 4, TO_DATE('2024-06-01', 'YYYY-MM-DD'), 'positive', 'Transaction Performance');