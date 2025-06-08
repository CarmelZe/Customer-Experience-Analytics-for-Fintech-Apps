import pandas as pd
import spacy
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.cluster import KMeans
import numpy as np

# -----------------------------
# Step 1: Load CSV file
# -----------------------------
df = pd.read_csv("../data/ethiopian_bank_reviews_400_each.csv")

# -----------------------------
# Step 2: Preprocess text using spaCy
# -----------------------------
nlp = spacy.load("en_core_web_sm")

def preprocess_text(text):
    doc = nlp(str(text).lower())
    tokens = [
        token.lemma_ for token in doc
        if token.is_alpha and not token.is_stop and not token.is_punct and len(token) > 2
    ]
    return " ".join(tokens)

df['cleaned_review'] = df['review'].astype(str).apply(preprocess_text)

# -----------------------------
# Step 3: TF-IDF Keyword Extraction (1-2 grams)
# -----------------------------
vectorizer = TfidfVectorizer(ngram_range=(1, 2), max_features=1000)
tfidf_matrix = vectorizer.fit_transform(df['cleaned_review'])
feature_names = vectorizer.get_feature_names_out()

# -----------------------------
# Step 4: Cluster reviews into 5 themes using KMeans
# -----------------------------
NUM_CLUSTERS = 5
kmeans = KMeans(n_clusters=NUM_CLUSTERS, random_state=42)
kmeans.fit(tfidf_matrix)

df['theme_cluster'] = kmeans.labels_

# -----------------------------
# Step 5: Extract top keywords per cluster
# -----------------------------
cluster_keywords = {}

for cluster_num in range(NUM_CLUSTERS):
    indices = np.where(kmeans.labels_ == cluster_num)[0]
    cluster_tfidf = tfidf_matrix[indices].mean(axis=0)
    top_indices = np.asarray(cluster_tfidf).flatten().argsort()[-10:][::-1]
    top_keywords = [feature_names[i] for i in top_indices]
    cluster_keywords[cluster_num] = top_keywords

# -----------------------------
# Step 6: Print or save results
# -----------------------------
for cluster, keywords in cluster_keywords.items():
    print(f"\nCluster {cluster} Keywords:")
    print(", ".join(keywords))

# Optional: Save reviews with cluster labels
df.to_csv("../data/reviews_with_themes.csv", index=False)
