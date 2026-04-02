"""
BanglaTruth Backend API - FastAPI Server
Handles parallel LLM processing, web scraping, and fact-checking coordination
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import asyncio
from concurrent.futures import ThreadPoolExecutor
from groq import Groq
import os
import json
import re
import requests
import time
from dotenv import load_dotenv
from ddgs import DDGS
from newspaper import Article
import logging

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()

# Initialize FastAPI
app = FastAPI(title="BanglaTruth API", version="2.0")

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Groq Client
client = Groq(api_key=os.getenv("GROQ_API_KEY"))

# Models
MODELS = [
    {"id": "llama-3.3-70b-versatile", "name": "Llama 3.3"},
    {"id": "llama-3.1-8b-instant", "name": "Llama 3.1"},
]


# ============================================================================
# PYDANTIC MODELS
# ============================================================================

class FactCheckRequest(BaseModel):
    claim: str
    deep: bool = False
    reporter: bool = False
    engine: str = "duckduckgo"
    selected_model: str = "both"
    lang_code: str = "en"


class AnalyzeArticleRequest(BaseModel):
    url: str


# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def clean_json(raw_text):
    """
    Tries to find and clean JSON from AI response.
    Handles common formatting errors from LLMs.
    """
    try:
        # Try direct parsing first
        return json.loads(raw_text.strip())
    except:
        pass

    try:
        # Try extracting from markdown code blocks
        if "```json" in raw_text:
            json_str = raw_text.split("```json")[1].split("```")[0].strip()
            return json.loads(json_str)
        elif "```" in raw_text:
            json_str = raw_text.split("```")[1].split("```")[0].strip()
            return json.loads(json_str)
    except:
        pass

    try:
        # Try finding JSON object with regex
        match = re.search(r'\{.*\}', raw_text, re.DOTALL)
        if match:
            json_str = match.group()
            json_str = json_str.replace("'", '"')  # Fix single quotes
            return json.loads(json_str)
    except:
        pass

    # Fallback: extract what we can
    try:
        verdict = "UNVERIFIED"
        confidence = 50
        for v in ["TRUE", "FALSE", "MISLEADING", "UNVERIFIED"]:
            if v in raw_text.upper():
                verdict = v
                break
        numbers = re.findall(r'\b(\d{1,3})%', raw_text)
        if numbers:
            confidence = int(numbers[0])
        return {
            "verdict": verdict,
            "confidence": confidence,
            "explanation": raw_text[:200],
            "source": None
        }
    except:
        pass

    return None


def get_prompt(lang_code, deep=False, reporter=False):
    """Generate the appropriate prompt based on analysis mode."""
    if reporter:
        return """You are an investigative journalist and expert fact-checker.
        Analyse the claim deeply and respond ONLY in this exact JSON format (no markdown, no extra text):
        {
            "verdict": "TRUE or FALSE or MISLEADING or UNVERIFIED",
            "confidence": 85,
            "explanation": "detailed analysis",
            "source": "source name or null",
            "follow_up_questions": ["question 1", "question 2", "question 3"],
            "what_to_investigate": "what a journalist should look into",
            "red_flags": "suspicious elements in the claim"
        }"""
    elif deep:
        return """You are an expert fact-checker.
        First argue FOR the claim. Then argue AGAINST it. Then give final verdict.
        Reply ONLY in this exact JSON format (no markdown, no extra text):
        {"verdict": "TRUE or FALSE or MISLEADING or UNVERIFIED", "confidence": 85, "for_arguments": "arguments for the claim", "against_arguments": "arguments against the claim", "explanation": "final analysis", "source": "source or null"}"""
    else:
        return """You are an expert fact-checker.
        Reply ONLY in this exact JSON format (no markdown, no extra text):
        {"verdict": "TRUE or FALSE or MISLEADING or UNVERIFIED", "confidence": 85, "explanation": "your explanation", "source": "source or null"}"""


def search_duckduckgo(query):
    """Search using DuckDuckGo (free, no API key needed)."""
    try:
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=3))
            if results:
                return [r["href"] for r in results]
    except Exception as e:
        logger.warning(f"DuckDuckGo search failed: {e}")
    return []


def search_google(query):
    """Search using Google Custom Search (requires API key and CX)."""
    try:
        api_key = os.getenv("GOOGLE_API_KEY")
        cx = os.getenv("GOOGLE_CX")

        if not api_key or not cx:
            logger.warning("Google API key or CX not configured. Falling back to DuckDuckGo.")
            return search_duckduckgo(query)

        url = f"https://www.googleapis.com/customsearch/v1"
        params = {
            "q": query,
            "key": api_key,
            "cx": cx,
            "num": 3
        }
        response = requests.get(url, params=params, timeout=10)

        if response.status_code == 403:
            logger.warning("Google API returned 403. Falling back to DuckDuckGo.")
            return search_duckduckgo(query)

        data = response.json()
        if "items" in data:
            return [item["link"] for item in data["items"]]
    except requests.exceptions.Timeout:
        logger.warning("Google API timeout. Falling back to DuckDuckGo.")
        return search_duckduckgo(query)
    except Exception as e:
        logger.warning(f"Google search failed: {e}. Falling back to DuckDuckGo.")
        return search_duckduckgo(query)

    return []


def get_source_links(query, engine="duckduckgo", limit=3):
    """Get source links based on selected search engine."""
    if engine.lower() == "google":
        links = search_google(query)
        if not links:  # Fallback if Google fails
            links = search_duckduckgo(query)
    else:
        links = search_duckduckgo(query)

    return links[:limit]


def search_image(query):
    """Search for relevant images using DuckDuckGo."""
    try:
        time.sleep(1)  # Rate limiting
        clean_query = re.sub(r'[^\w\s]', '', query)
        short_query = " ".join(clean_query.split()[:5])

        for attempt in range(3):
            try:
                with DDGS() as ddgs:
                    results = list(ddgs.images(short_query, max_results=3))
                    if results:
                        return [r["image"] for r in results]
            except Exception as e:
                logger.warning(f"Image search attempt {attempt + 1} failed: {e}")
                time.sleep(2 * (attempt + 1))
    except Exception as e:
        logger.warning(f"Image search error: {e}")
    return []


def extract_claim_from_url(url):
    """Extract text from a URL using newspaper3k."""
    if not url.strip().startswith("http"):
        logger.warning("Invalid URL - not http/https")
        return None
    try:
        article = Article(url)
        article.config.browser_user_agent = (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        )
        article.config.request_timeout = 10
        article.download()
        article.parse()
        text = article.text
        return text[:500].strip() if text else None
    except Exception as e:
        logger.warning(f"URL extraction error: {e}")
        return None


# ============================================================================
# ASYNC LLM QUERY FUNCTION
# ============================================================================

async def query_model_async(model_id, claim, lang_code, deep=False, reporter=False):
    """
    Query a single LLM model asynchronously.
    Includes robust JSON parsing and error handling.
    """
    try:
        loop = asyncio.get_event_loop()

        # Run the Groq API call in a thread pool (since it's sync)
        response = await loop.run_in_executor(
            None,
            lambda: client.chat.completions.create(
                model=model_id,
                messages=[
                    {"role": "system", "content": get_prompt(lang_code, deep, reporter)},
                    {"role": "user", "content": f"Fact-check this claim: {claim}"}
                ],
                temperature=0.1  # Low temp for consistent JSON output
            )
        )

        raw_content = response.choices[0].message.content
        logger.info(f"Raw response from {model_id}: {raw_content[:100]}...")

        # Try to extract JSON
        data = clean_json(raw_content)

        if data is None:
            logger.warning(f"Could not parse JSON from {model_id}. Raw: {raw_content[:200]}")
            return {
                "verdict": "UNVERIFIED",
                "confidence": 0,
                "explanation": "Failed to parse model output",
                "source": None
            }

        return data

    except Exception as e:
        logger.error(f"Error querying {model_id}: {e}")
        return {
            "verdict": "ERROR",
            "confidence": 0,
            "explanation": f"Model error: {str(e)}",
            "source": None
        }


# ============================================================================
# VERDICT AGGREGATION
# ============================================================================

def get_final_verdict(results):
    """Aggregate verdicts from multiple models (jury voting)."""
    if not results:
        return "UNVERIFIED", 0

    verdicts = [r.get("verdict", "UNVERIFIED") for r in results]
    confidences = [int(r.get("confidence", 0)) for r in results]

    verdict_counts = {}
    for v in verdicts:
        verdict_counts[v] = verdict_counts.get(v, 0) + 1

    avg_confidence = sum(confidences) // len(confidences) if confidences else 0
    final_verdict = max(verdict_counts, key=verdict_counts.get)

    # If no clear majority, mark as CONTESTED
    if len(set(verdicts)) > 1 and verdict_counts.get(final_verdict, 0) == 1:
        final_verdict = "CONTESTED"

    return final_verdict, avg_confidence


# ============================================================================
# API ENDPOINTS
# ============================================================================

@app.get("/health")
async def health_check():
    """Health check endpoint for deployment."""
    return {"status": "ok", "version": "2.0"}


@app.post("/fact-check")
async def fact_check(request: FactCheckRequest):
    """
    Main fact-checking endpoint.
    Accepts a claim and returns verdicts from multiple LLMs.
    """
    try:
        claim = request.claim.strip()
        if not claim:
            raise HTTPException(status_code=400, detail="Claim cannot be empty")

        logger.info(f"Fact-checking claim: {claim[:100]}...")

        # Determine which models to run
        models_to_run = MODELS
        if request.selected_model != "both":
            models_to_run = [m for m in MODELS if m["name"] == request.selected_model]

        # Run models in parallel asynchronously
        tasks = [
            query_model_async(model["id"], claim, request.lang_code, request.deep, request.reporter)
            for model in models_to_run
        ]

        individual_results = await asyncio.gather(*tasks)

        # Add model names to results
        for i, model in enumerate(models_to_run):
            individual_results[i]["model_name"] = model["name"]

        # Get final verdict from jury
        final_verdict, avg_confidence = get_final_verdict(individual_results)

        # Get source links (if needed)
        sources = get_source_links(f"{claim[:100]}", request.engine, limit=3)

        logger.info(f"Final verdict: {final_verdict} (confidence: {avg_confidence}%)")

        return {
            "final_verdict": final_verdict,
            "avg_confidence": avg_confidence,
            "individual": individual_results,
            "engine_used": request.engine,
            "source_links": sources
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Fact-check error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/analyze-article")
async def analyze_article(request: AnalyzeArticleRequest):
    """
    Extract claims from an article URL and fact-check them.
    """
    try:
        url = request.url.strip()
        if not url:
            raise HTTPException(status_code=400, detail="URL cannot be empty")

        logger.info(f"Analyzing article: {url}")

        # Extract text from URL
        text = extract_claim_from_url(url)
        if not text:
            raise HTTPException(status_code=400, detail="Could not extract text from URL")

        # Ask LLM to extract claims from the text
        response = await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[
                    {"role": "system",
                     "content": "You are an expert at extracting claims from articles. Return ONLY a JSON array of claims. Example: [\"claim 1\", \"claim 2\", \"claim 3\"]. No other text."},
                    {"role": "user", "content": f"Extract 3-5 main claims from this text:\n\n{text}"}
                ]
            )
        )

        raw_claims = response.choices[0].message.content
        claims = clean_json(f"[{raw_claims}]") or []

        # If it's a dict, try to extract the array
        if isinstance(claims, dict):
            claims = claims.get("claims", [])

        # Make sure it's a list
        if not isinstance(claims, list):
            claims = [text[:200]]  # Fallback: use first 200 chars

        logger.info(f"Extracted {len(claims)} claims from article")

        return {
            "url": url,
            "claims": claims,
            "source_text": text[:500]
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Article analysis error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/search")
async def search(q: str, engine: str = "duckduckgo"):
    """
    Direct search endpoint.
    Returns links from specified search engine.
    """
    try:
        if not q:
            raise HTTPException(status_code=400, detail="Query cannot be empty")

        links = get_source_links(q, engine, limit=5)
        return {"query": q, "engine": engine, "links": links}

    except Exception as e:
        logger.error(f"Search error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/images")
async def get_images(q: str):
    """Search for images related to a query."""
    try:
        if not q:
            raise HTTPException(status_code=400, detail="Query cannot be empty")

        images = search_image(q)
        return {"query": q, "images": images}

    except Exception as e:
        logger.error(f"Image search error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# STARTUP
# ============================================================================

if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)