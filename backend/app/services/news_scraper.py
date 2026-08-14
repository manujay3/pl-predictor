import feedparser
import uuid
from app.ai.rag_adjuster import add_news_to_vector_store

BBC_PL_RSS_URL = "http://feeds.bbci.co.uk/sport/football/premier-league/rss.xml"

TEAM_KEYWORDS = {
    "Arsenal FC": ["Arsenal"],
    "Aston Villa FC": ["Aston Villa", "Villa"],
    "Bournemouth": ["Bournemouth", "Cherries"],
    "Brentford FC": ["Brentford"],
    "Brighton & Hove Albion FC": ["Brighton"],
    "Chelsea FC": ["Chelsea"],
    "Coventry City FC": ["Coventry"],
    "Crystal Palace FC": ["Crystal Palace", "Palace"],
    "Everton FC": ["Everton"],
    "Fulham FC": ["Fulham"],
    "Hull City FC": ["Hull"],
    "Ipswich Town FC": ["Ipswich"],
    "Leeds United FC": ["Leeds"],
    "Liverpool FC": ["Liverpool"],
    "Manchester City FC": ["Manchester City", "Man City"],
    "Manchester United FC": ["Manchester United", "Man Utd"],
    "Newcastle United FC": ["Newcastle"],
    "Nottingham Forest FC": ["Nottingham Forest", "Forest"],
    "Sunderland AFC": ["Sunderland", "Black Cats"],
    "Tottenham Hotspur FC": ["Tottenham", "Spurs"]
}

def scrape_latest_news():
    print(f"Fetching RSS feed from {BBC_PL_RSS_URL}...")
    feed = feedparser.parse(BBC_PL_RSS_URL)
    
    articles_added = 0

    if feed.entries:
        for entry in feed.entries:
            title = entry.title
            summary = entry.get('summary', '')
            
            # Convert text to lowercase for safer matching
            full_text_lower = f"{title}. {summary}".lower()
            
            for official_team, keywords in TEAM_KEYWORDS.items():
                if any(keyword.lower() in full_text_lower for keyword in keywords):
                    doc_id = str(uuid.uuid4())
                    print(f"Found news for {official_team}: {title}")
                    
                    add_news_to_vector_store(
                        doc_id=doc_id,
                        text=f"{title}. {summary}", # Keep original case for the AI
                        metadata={"team": official_team, "source": "BBC"}
                    )
                    articles_added += 1

    # --- FALLBACK FOR TESTING ---
    if articles_added == 0:
        print("Live feed is dry today. Injecting a mock transfer to test the UI...")
        add_news_to_vector_store(
            doc_id="mock_chelsea_transfer",
            text="Chelsea FC confirm the £110M signing of an elite, world-class center-back to heavily bolster their defense.",
            metadata={"team": "Chelsea FC", "source": "Mock"}
        )
        articles_added += 1
    # ----------------------------

    print(f"\nIngestion complete. Added {articles_added} articles to ChromaDB.")

if __name__ == "__main__":
    scrape_latest_news()