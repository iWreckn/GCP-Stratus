import math
from typing import Dict, Tuple

# Stage 1: The Brutal Filter
# If an event contains these, it gets a score of -1 (discarded)
LOW_SIGNAL = [
    "region",
    "available in",
    "pricing",
    "console ui",
    "documentation",
    "renamed",
    "minor bug fix",
    "performance improvement",
    "general availability in asia",
    "preview image",
    "sdk",
    "resolved an issue",
    "fixed a bug"
]

# Stage 2: The Signal Scorer
HIGH_SIGNAL = {
    "iam": 5,
    "permission": 5,
    "role": 4,
    "service account": 5,
    "vpc": 4,
    "firewall": 5,
    "egress": 5,
    "ingress": 5,
    "cmek": 5,
    "kms": 5,
    "audit": 4,
    "logging": 3,
    "gemini": 4,
    "vertex ai": 3,
    "gke": 3,
    "cloud run": 3,
    "policy": 4,
    "security command center": 5,
    "scc": 5,
    "armor": 5,
    "identity": 4,
    "access": 4
}

# Stage 2.5: The Phrase Bonus
PHRASE_BONUS = {
    "breaking change": 10.0,
    "org policy": 8.0,
    "privilege escalation": 10.0,
    "deprecated": 6.0,
    "mandatory migration": 8.0,
    "security vulnerability": 10.0
}

# Stage 3: Audience Popularity Multiplier
POPULAR_SERVICES = {
    "kubernetes engine", "gke", "cloud run", "bigquery", 
    "iam", "cloud storage", "cloud sql", "vpc", "cloud logging", 
    "looker", "vpc service controls", "gemini", "security command center",
    "codeassist", "gce", "compute engine"
}

def evaluate_event(service: str, raw_text: str) -> Tuple[float, float, float]:
    """
    Evaluates a raw event text and returns (rule_score, popularity_score, final_score).
    Returns (-1.0, 0.0, -1.0) if the event hits the trash filter or is too short.
    """
    text_lower = raw_text.lower()
    service_lower = service.lower()
    
    # 1. Hard Filter: Trash short noise or low signal keywords
    if len(text_lower) < 50:
        return -1.0, 0.0, -1.0
        
    for junk in LOW_SIGNAL:
        if junk in text_lower:
            return -1.0, 0.0, -1.0
            
    # 2. Rule Scoring: Sum up high signal hits
    raw_rule_score = 0.0
    for keyword, points in HIGH_SIGNAL.items():
        if keyword in text_lower or keyword in service_lower:
            raw_rule_score += points
            
    # Score density: divide by log(word count)
    word_count = len(text_lower.split())
    # math.e prevents log from returning < 1.0 (which would artificially boost short notes)
    density_score = raw_rule_score / math.log(max(math.e, word_count))

    # Phrase bonus (Added directly, unaffected by density penalty)
    for phrase, points in PHRASE_BONUS.items():
        if phrase in text_lower:
            density_score += points
            
    # 3. Popularity Multiplier (x1.3 if in popular services list)
    popularity_score = (density_score * 0.3) if service_lower in POPULAR_SERVICES else 0.0
    final_score = round(density_score + popularity_score, 2)
    
    return round(density_score, 2), round(popularity_score, 2), final_score