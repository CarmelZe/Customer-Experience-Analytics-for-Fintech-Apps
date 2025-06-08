import pandas as pd
import numpy as np
import spacy
from transformers import pipeline
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.cluster import KMeans

# Load spaCy and transformer sentiment model
nlp = spacy.load("en_core_web_sm")
sentiment_pipeline = pipeline("sentiment-analysis", model="distilbert-base-uncased-finetuned-sst-2-english")

# -------------------------
# Load data
# -------------------------
df = pd.read_csv("../data/ethiopian_bank_reviews_400_each.csv")

# -------------------------
# Preprocessing function
# -------------------------
def preprocess(text):
    doc = nlp(str(text).lower())
    tokens = [token.lemma_ for token in doc if token.is_alpha and not token.is_stop and len(token) > 2]
    return " ".join(tokens)

df['cleaned_review'] = df['review'].astype(str).apply(preprocess)

# -------------------------
# Sentiment Analysis
# -------------------------
sentiment_results = sentiment_pipeline(df['review'].astype(str).tolist(), truncation=True)

df['sentiment_label'] = [res['label'].lower() for res in sentiment_results]
df['sentiment_score'] = [res['score'] for res in sentiment_results]
df['sentiment_category'] = df['sentiment_score'].apply(lambda score: 'neutral' if score < 0.6 else None)
df['sentiment_category'] = df.apply(
    lambda row: row['sentiment_label'] if row['sentiment_category'] is None else row['sentiment_category'],
    axis=1
)

# -------------------------
# Theme Clustering per Bank
# -------------------------
def extract_themes_per_bank(df, num_clusters=5):
    all_results = []
    banks = df['bank'].dropna().unique()

    for bank in banks:
        bank_df = df[df['bank'] == bank].copy()
        if len(bank_df) < num_clusters:
            continue

        vectorizer = TfidfVectorizer(ngram_range=(1, 2), max_features=1000)
        tfidf_matrix = vectorizer.fit_transform(bank_df['cleaned_review'])
        kmeans = KMeans(n_clusters=num_clusters, random_state=42)
        kmeans.fit(tfidf_matrix)

        bank_df['theme_cluster'] = kmeans.labels_
        feature_names = vectorizer.get_feature_names_out()

        # Extract keywords for each cluster
        cluster_keywords = {}
        for cluster_num in range(num_clusters):
            indices = np.where(kmeans.labels_ == cluster_num)[0]
            cluster_tfidf = tfidf_matrix[indices].mean(axis=0)
            top_indices = np.asarray(cluster_tfidf).flatten().argsort()[-5:][::-1]
            top_keywords = [feature_names[i] for i in top_indices]
            cluster_keywords[cluster_num] = ", ".join(top_keywords)

        bank_df['identified_theme'] = bank_df['theme_cluster'].map(cluster_keywords)
        all_results.append(bank_df)

    return pd.concat(all_results)

# Apply the per-bank theme extraction
df_with_themes = extract_themes_per_bank(df, num_clusters=5)

# -------------------------
# Save Final Output
# -------------------------
df_with_themes[['review', 'sentiment_label', 'sentiment_score', 'identified_theme']].to_csv("../data/final_reviews_with_themes.csv", index=False)
