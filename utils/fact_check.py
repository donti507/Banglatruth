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

load_dotenv()

client = Groq(
    api_key=os.getenv("GROQ_API_KEY")
)

MODELS = [
    {"id": "llama-3.3-70b-versatile", "name": "Llama 3.3"},
    {"id": "llama-3.1-8b-instant", "name": "Llama 3.1"},
]

def get_prompt(lang_code, deep=False, reporter=False):
    if reporter:
        return """You are an investigative journalist and expert fact-checker.
        Analyse the claim deeply and respond ONLY in this exact JSON format:
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
        if lang_code == "bn":
            return """আপনি একজন বিশেষজ্ঞ তথ্য যাচাইকারী।
            প্রথমে দাবির পক্ষে যুক্তি দিন। তারপর বিপক্ষে যুক্তি দিন। তারপর চূড়ান্ত সিদ্ধান্ত নিন।
            শুধুমাত্র এই JSON ফরম্যাটে উত্তর দিন:
            {"verdict": "সত্য অথবা মিথ্যা অথবা বিভ্রান্তিকর অথবা অযাচাইকৃত", "confidence": 85, "for_arguments": "পক্ষে যুক্তি", "against_arguments": "বিপক্ষে যুক্তি", "explanation": "চূড়ান্ত বিশ্লেষণ", "source": "উৎস অথবা null"}"""
        else:
            return """You are an expert fact-checker.
            First argue FOR the claim. Then argue AGAINST it. Then give final verdict.
            Reply ONLY in this exact JSON format:
            {"verdict": "TRUE or FALSE or MISLEADING or UNVERIFIED", "confidence": 85, "for_arguments": "arguments for the claim", "against_arguments": "arguments against the claim", "explanation": "final analysis", "source": "source or null"}"""
    else:
        if lang_code == "bn":
            return """আপনি একজন বিশেষজ্ঞ তথ্য যাচাইকারী।
            শুধুমাত্র নিচের JSON ফরম্যাটে উত্তর দিন:
            {"verdict": "সত্য অথবা মিথ্যা অথবা বিভ্রান্তিকর অথবা অযাচাইকৃত", "confidence": 85, "explanation": "আপনার বিশ্লেষণ", "source": "উৎস অথবা null"}"""
        else:
            return """You are an expert fact-checker.
            Reply ONLY in this exact JSON format:
            {"verdict": "TRUE or FALSE or MISLEADING or UNVERIFIED", "confidence": 85, "explanation": "your explanation", "source": "source or null"}"""

def extract_json(raw):
    try:
        return json.loads(raw.strip())
    except Exception:
        pass
    try:
        if "```json" in raw:
            raw = raw.split("```json")[1].split("```")[0].strip()
            return json.loads(raw)
        elif "```" in raw:
            raw = raw.split("```")[1].split("```")[0].strip()
            return json.loads(raw)
    except Exception:
        pass
    try:
        match = re.search(r'\{.*?\}', raw, re.DOTALL)
        if match:
            return json.loads(match.group())
    except Exception:
        pass
    try:
        verdict = "UNVERIFIED"
        confidence = 50
        explanation = raw
        for v in ["TRUE", "FALSE", "MISLEADING", "UNVERIFIED"]:
            if v in raw.upper():
                verdict = v
                break
        numbers = re.findall(r'\b(\d{1,3})%', raw)
        if numbers:
            confidence = int(numbers[0])
        return {
            "verdict": verdict,
            "confidence": confidence,
            "explanation": explanation,
            "source": None
        }
    except Exception:
        pass
    return None

def extract_claim_from_url(url):
    # Guard against non-HTTP inputs (iframe HTML, etc.)
    if not url.strip().startswith("http"):
        print(f"URL EXTRACT ERROR: Invalid URL — not http/https")
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
        print(f"URL EXTRACT ERROR: {e}")
        return None
def search_duckduckgo(query):
    try:
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=1))
            if results:
                return results[0]["href"]
    except Exception:
        pass
    return None

def search_google(query):
    try:
        api_key = os.getenv("GOOGLE_API_KEY")
        cx = os.getenv("GOOGLE_CX")
        url = f"https://www.googleapis.com/customsearch/v1?q={query}&key={api_key}&cx={cx}&num=1"
        response = requests.get(url)
        data = response.json()
        if "items" in data:
            return data["items"][0]["link"]
    except Exception:
        pass
    return None

def search_image(query):
    try:
        time.sleep(2)  # slightly longer pause to avoid rate limits
        # Clean query — remove special chars, keep first 5 words
        clean_query = re.sub(r'[^\w\s]', '', query)
        short_query = " ".join(clean_query.split()[:5])
        print(f"IMAGE QUERY: {short_query}")

        for attempt in range(3):  # retry up to 3 times
            try:
                with DDGS() as ddgs:
                    results = list(ddgs.images(
                        short_query,
                        max_results=3,
                    ))
                    if results:
                        return [r["image"] for r in results]
            except Exception as e:
                print(f"IMAGE SEARCH attempt {attempt + 1} failed: {e}")
                time.sleep(2 * (attempt + 1))  # back off each retry

    except Exception as e:
        print(f"IMAGE SEARCH ERROR: {e}")
    return []

def get_source_link(query, engine="duckduckgo"):
    if engine == "google":
        result = search_google(query)
        if result:
            return result
        return search_duckduckgo(query)
    else:
        return search_duckduckgo(query)

def find_similar_claim(claim, history):
    if not history:
        return None
    claim_words = set(claim.lower().split())
    for item in reversed(history):
        past_words = set(item["claim"].lower().split())
        if len(claim_words) == 0:
            continue
        overlap = len(claim_words & past_words) / len(claim_words)
        if overlap > 0.7:
            return item
    return None

def query_model(model_id, claim, lang_code, deep=False, search_engine="duckduckgo", reporter=False):
    try:
        response = client.chat.completions.create(
            model=model_id,
            messages=[
                {"role": "system", "content": get_prompt(lang_code, deep, reporter)},
                {"role": "user", "content": f"Fact-check this claim: {claim}"}
            ]
        )
        raw = response.choices[0].message.content
        data = extract_json(raw)

        if data is None:
            raise ValueError("Could not parse response")

        source_name = data.get("source")
        if source_name and source_name != "null":
            link = get_source_link(f"{source_name} {claim[:50]}", search_engine)
            data["source_link"] = link
        else:
            data["source_link"] = None

        return data

    except Exception:
        return {
            "verdict": "UNVERIFIED",
            "confidence": 0,
            "explanation": "Model could not analyse this claim.",
            "source": None,
            "source_link": None
        }

def get_final_verdict(results):
    votes = [r["verdict"] for r in results]
    avg_confidence = sum(int(r["confidence"]) for r in results) // len(results)

    verdict_counts = {}
    for v in votes:
        verdict_counts[v] = verdict_counts.get(v, 0) + 1

    final = max(verdict_counts, key=verdict_counts.get)

    all_same = len(set(votes)) == 1
    if not all_same and verdict_counts.get(final, 0) == 1:
        final = "CONTESTED"

    return final, avg_confidence

def get_evidence_map(claim, lang_code):
    prompt = """You are an expert fact-checker.
    Analyse this claim and return ONLY this exact JSON:
    {
        "supporting": ["point 1", "point 2", "point 3"],
        "contradicting": ["point 1", "point 2", "point 3"],
        "neutral": ["context point 1", "context point 2"]
    }
    Maximum 3 points per category. Be concise."""

    try:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": prompt},
                {"role": "user", "content": f"Claim: {claim}"}
            ]
        )
        raw = response.choices[0].message.content
        return extract_json(raw)
    except Exception:
        return None

def analyse_claim(claim, lang_code, deep=False, search_engine="duckduckgo", selected_model="both", reporter=False):
    results = []

    models_to_run = MODELS
    if selected_model != "both":
        models_to_run = [m for m in MODELS if m["name"] == selected_model]

    with ThreadPoolExecutor() as executor:
        futures = {
            executor.submit(query_model, model["id"], claim, lang_code, deep, search_engine, reporter): model
            for model in models_to_run
        }
        for future, model in futures.items():
            data = future.result()
            data["model_name"] = model["name"]
            results.append(data)

    final_verdict, avg_confidence = get_final_verdict(results)

    return {
        "final_verdict": final_verdict,
        "avg_confidence": avg_confidence,
        "individual": results,
    }