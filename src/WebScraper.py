from google_play_scraper import app, reviews, Sort
import pandas as pd
from datetime import datetime
import time

# Configuration
bank_apps = {
    "Combanketh": "com.combanketh.mobilebanking",
    "boa": "com.boa.boaMobileBanking",
    "dashen": "com.dashen.dashensuperapp"
}

target_count = 400
max_attempts = 5  # Increased from 3
overscrape_factor = 1.5  # Collect 50% more than needed

# Storage
final_reviews = {bank: [] for bank in bank_apps}

def get_reviews(app_name, app_id):
    attempts = 0
    collected = 0
    
    while collected < target_count and attempts < max_attempts:
        try:
            # Calculate how many more we need (with overscraping)
            needed = int((target_count - collected) * overscrape_factor)
            
            # Scrape reviews
            new_reviews, _ = reviews(
                app_id,
                lang='en',
                country='et',
                sort=Sort.NEWEST,
                count=needed,
                filter_score_with=None
            )
            
            # Process and deduplicate
            for review in new_reviews:
                clean_review = {
                    "review": review['content'].strip(),
                    "rating": review['score'],
                    "date": review['at'].strftime('%Y-%m-%d'),
                    "bank": app_name,
                    "source": "Google Play"
                }
                
                # Only add if not already collected
                if clean_review not in final_reviews[app_name]:
                    final_reviews[app_name].append(clean_review)
                    collected = len(final_reviews[app_name])
                    
                    # Early exit if target reached
                    if collected >= target_count:
                        break
            
            print(f"{app_name}: Attempt {attempts+1} - Collected {collected}/{target_count}")
            
        except Exception as e:
            print(f"Error: {str(e)}")
        
        attempts += 1
        time.sleep(3)  # Be gentle with the API
        
    return final_reviews[app_name][:target_count]  # Return exact count

# Scrape all banks
for bank, app_id in bank_apps.items():
    bank_reviews = get_reviews(bank, app_id)
    print(f"✅ {bank}: {len(bank_reviews)} reviews")

# Combine and save
all_reviews = []
for bank in bank_apps:
    all_reviews.extend(final_reviews[bank][:target_count])  # Force exact count

df = pd.DataFrame(all_reviews)
print("\nFinal Counts:")
print(df['bank'].value_counts())

df.to_csv('../data/ethiopian_bank_reviews_400_each.csv', index=False)
print(f"\nSaved {len(df)} reviews (Goal: {len(bank_apps)*target_count})")