import pandas as pd
from transformers import pipeline

# Step 1: Load the CSV file
df = pd.read_csv("../data/ethiopian_bank_reviews_400_each.csv")

# Step 2: Initialize the sentiment analysis pipeline
sentiment_pipeline = pipeline(
    "sentiment-analysis",
    model="distilbert-base-uncased-finetuned-sst-2-english"
)

# Step 3: Run sentiment analysis on the reviews
df['review'] = df['review'].astype(str)
sentiment_results = sentiment_pipeline(df['review'].tolist(), truncation=True)

# Step 4: Extract sentiment results into the DataFrame
df['sentiment_label'] = [result['label'] for result in sentiment_results]
df['sentiment_score'] = [result['score'] for result in sentiment_results]

# Step 5: Define a 'sentiment_category' (positive, negative, neutral)
df['sentiment_category'] = df['sentiment_score'].apply(
    lambda score: 'neutral' if score < 0.6 else None
)
df['sentiment_category'] = df.apply(
    lambda row: row['sentiment_label'].lower() if row['sentiment_category'] is None else row['sentiment_category'],
    axis=1
)

# Step 6: Aggregate mean sentiment score by bank and rating
agg_df = df.groupby(['bank', 'rating'])['sentiment_score'].mean().reset_index()
agg_df.rename(columns={'sentiment_score': 'mean_sentiment_score'}, inplace=True)

# Step 7: Save the full DataFrame with sentiment columns
df.to_csv("../data/reviews_with_sentiment.csv", index=False)

# Step 8: Save the aggregated results
agg_df.to_csv("../data/aggregated_sentiment_by_bank_and_rating.csv", index=False)

# Optionally, print results
print("Sample reviews with sentiment:")
print(df[['review', 'rating', 'bank', 'sentiment_label', 'sentiment_score', 'sentiment_category']].head())

print("\nAggregated sentiment score by bank and rating:")
print(agg_df)
