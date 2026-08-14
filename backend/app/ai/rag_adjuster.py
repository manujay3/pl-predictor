import os
import json
import chromadb
import re
from google import genai
from dotenv import load_dotenv

load_dotenv()

# Initialize the modern Gemini Client
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

# Initialize ChromaDB client (stores data locally in a /chroma_db folder)
chroma_client = chromadb.PersistentClient(path="./chroma_db")

# Create or get the collection for Premier League news
news_collection = chroma_client.get_or_create_collection(name="pl_news")

def add_news_to_vector_store(doc_id: str, text: str, metadata: dict):
    """
    Embeds and stores a news snippet into the ChromaDB collection.
    """
    news_collection.add(
        documents=[text],
        metadatas=[metadata],
        ids=[doc_id]
    )
    print(f"Added document {doc_id} to vector store.")

def query_team_news(team_name: str, n_results: int = 3) -> list:
    """
    Retrieves the most relevant news snippets for a specific team.
    """
    results = news_collection.query(
        query_texts=[f"Recent news, transfers, and injuries for {team_name}"],
        n_results=n_results
    )
    return results['documents'][0] if results['documents'] else []

def calculate_team_delta(team_name: str, news_context: str, fpl_injuries: list) -> dict:
    """
    Prompts Gemini to analyze text context and FPL injury data to return a structured JSON math adjustment.
    """
    # Format the FPL injuries into a string list
    injury_text = "\n- ".join(fpl_injuries) if fpl_injuries else "No known FPL injuries."
    
    # If there is no news and no injuries, skip the AI call
    if not news_context and not fpl_injuries:
        return {"att_delta": 0.0, "def_delta": 0.0, "reasoning": "No relevant news or injuries found."}

    prompt = f"""
    You are a quantitative sports analyst. Analyze the following context for {team_name}.
    Determine the statistical impact on their attacking and defensive strength multipliers.
    A major injury to a striker should result in a negative att_delta (e.g., -0.15).
    A major defensive signing should result in a positive def_delta (e.g., +0.10).
    
    Current Official Injuries (from FPL):
    - {injury_text}
    
    Recent News Context (BBC):
    {news_context if news_context else "No recent BBC news."}
    
    Synthesize both data sources. Output strictly valid JSON with no markdown formatting or code blocks.
    Format required: {{"att_delta": float, "def_delta": float, "reasoning": "string"}}
    """

    try:
        response = client.models.generate_content(
            model='gemini-3.6-flash',
            contents=prompt,
        )
        
        raw_text = response.text.strip().replace("```json", "").replace("```", "")
        return json.loads(raw_text)
        
    except Exception as e:
        print(f"Failed to generate delta for {team_name}: {e}")
        return {"att_delta": 0.0, "def_delta": 0.0, "reasoning": "Error generating adjustment."}
    
def batch_calculate_team_deltas(team_contexts: dict) -> dict:
    """
    Analyzes multiple teams in a SINGLE Gemini API call to prevent rate limits.
    
    Expected team_contexts format:
    {
        "Arsenal FC": {"news": "...", "injuries": [...]},
        "Chelsea FC": {"news": "...", "injuries": [...]}
    }
    """
    if not team_contexts:
        return {}

    prompt = f"""
    You are a quantitative sports analyst. Analyze the following recent news and official FPL injuries for Premier League teams.
    For EACH team provided in the JSON payload below, determine the statistical impact on their attacking (att_delta) and defensive (def_delta) strength multipliers.
    A major injury to a key striker should result in a negative att_delta (e.g., -0.15).
    A major defensive signing should result in a positive def_delta (e.g., +0.10).

    Team Data Payload:
    {json.dumps(team_contexts, indent=2)}

    Output strictly valid JSON mapping each team name to its deltas and concise reasoning. Do not wrap in markdown or code blocks.
    
    Required format:
    {{
      "Arsenal FC": {{"att_delta": -0.15, "def_delta": -0.05, "reasoning": "Key injuries..."}},
      "Chelsea FC": {{"att_delta": 0.0, "def_delta": 0.10, "reasoning": "Defensive boost..."}}
    }}
    """

    try:
        response = client.models.generate_content(
            model='gemini-3.6-flash',
            contents=prompt,
        )
        
        raw_text = response.text.strip().replace("```json", "").replace("```", "")
        return json.loads(raw_text)
        
    except Exception as e:
        print(f"Failed to generate batch deltas: {e}")
        return {}
    

import json
import re

def evaluate_custom_scenario(team_name: str, scenario_text: str) -> dict:
    """Takes a natural language scenario and converts it to numerical rating adjustments."""
    
    prompt = f"""
    You are an expert Premier League data scientist. 
    Evaluate this hypothetical scenario for {team_name}:
    "{scenario_text}"
    
    Determine how this specific event affects their attack and defense strength multipliers.
    Even if the player doesn't play for this team, evaluate the hypothetical impact AS IF they did.
    
    Required JSON structure:
    {{
        "att_delta": float (e.g., -0.3 for an injury),
        "def_delta": float,
        "reasoning": "A concise 1-sentence explanation."
    }}
    """
    
    try:
        # Assuming model is already initialized in this file as 'model'
        response = client.models.generate_content(
            model='gemini-3.6-flash',
            contents=prompt,
        )
        text = response.text.strip()
        
        # Robust Regex extraction: Find everything between the first { and last }
        match = re.search(r'\{.*\}', text, re.DOTALL)
        
        if not match:
            raise ValueError(f"No JSON block found in AI output. Raw text: {text}")
            
        clean_json_string = match.group(0)
        result = json.loads(clean_json_string)
        
        return {
            "att_delta": float(result.get("att_delta", 0.0)),
            "def_delta": float(result.get("def_delta", 0.0)),
            "reasoning": str(result.get("reasoning", "Scenario applied."))
        }
        
    except Exception as e:
        print(f"Scenario AI Error: {e}")
        return {
            "att_delta": 0.0, 
            "def_delta": 0.0, 
            "reasoning": f"Failed to parse AI response. Check backend terminal for details."
        }