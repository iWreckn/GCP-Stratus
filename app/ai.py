import json
import google.generativeai as genai
from typing import Dict, Any, Optional

from app.config import GEMINI_API_KEY, logger

if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)

MODEL_NAME = "gemini-1.5-flash"

def analyze_release_note(service: str, title: str, content: str) -> Optional[Dict[str, Any]]:
    """
    Send a GCP release note to Gemini for security classification and enrichment.
    Returns a parsed JSON dictionary with relevance, severity, summary, etc.
    """
    if not GEMINI_API_KEY:
        logger.error("GEMINI_API_KEY is missing in .env. Cannot run AI enrichment.")
        return None

    prompt = f"""
You are a cloud security expert analyzing Google Cloud Platform (GCP) release notes.
I only care about updates relevant to: security, governance, IAM, networking, logging, encryption, Kubernetes, org policy, storage risk, and medium/high operational impact.

Analyze the following release note:
Service: {service}
Title: {title}
Content: {content}

Provide a JSON response with the following keys exactly:
- relevance: "High", "Medium", or "Low" (based on the domains listed above)
- severity: "High", "Medium", "Low", or "Info"
- summary: A 1-2 sentence security-focused summary.
- recommended_action: What a security team should do about this (or "None" if irrelevant).
- tags: A list of relevant string tags (e.g., ["IAM", "Security", "Networking"]).
"""

    try:
        model = genai.GenerativeModel(MODEL_NAME)
        response = model.generate_content(
            prompt,
            generation_config=genai.GenerationConfig(
                response_mime_type="application/json",
                temperature=0.1, # Keep generations strict and deterministic
            )
        )
        return json.loads(response.text)
    except Exception as e:
        logger.error(f"Failed to analyze release note '{title}': {e}")
        return None