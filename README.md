# ☁️ GCP Release Intel Pipeline

A specialized, local intelligence pipeline built to turn hundreds of noisy Google Cloud Platform (GCP) release notes into a high-signal, YouTube-ready security digest.

## 🎯 The Problem
GCP publishes hundreds of release notes every week. However, 90% of them are low-signal noise—cosmetic UI changes, region expansions, or minor bug fixes. Reviewing them manually to find critical security updates, breaking changes, or high-impact features is exhausting and inefficient.

## 💡 The Solution
This tool acts as a ruthless, publisher-focused filter:
1. **Extracts:** Pulls the raw GCP release notes RSS feed and splits "digest blobs" into atomic, individual database events.
2. **Filters & Scores:** Uses a deterministic Python engine to instantly discard noise, penalize keyword-stuffing, and boost scores for high-impact security keywords (e.g., IAM, CMEK, VPC) and widely-used services (e.g., GKE, BigQuery).
3. **Visualizes:** Spins up a sleek, interactive Streamlit dashboard allowing you to skim the highest-scoring winners effortlessly, complete with color-coded keyword highlighting and direct documentation links.
4. *(Coming Soon) AI Enrichment:* Uses Gemini AI exclusively on the shortlisted winners to generate 1-sentence TL;DRs.

## 🛠️ Tech Stack
* **Python 3.12+**
* **Streamlit & Pandas** (Interactive Dashboard UI)
* **SQLite** (Local atomic event storage)
* **BeautifulSoup4 & Feedparser** (RSS / HTML Parsing)
* **Typer** (CLI interface)

## Setup

1. **Clone the repository:**
```bash
git clone https://github.com/your-username/gcp-release-intel.git
cd gcp-release-intel
```

2. **Create and activate a virtual environment:**
```bash
python3 -m venv .venv
source .venv/bin/activate
```

3. **Install dependencies:**
```bash
pip install -r requirements.txt
```

4. **Set up environment variables:**
```bash
cp .env.example .env
# (Optional for now) Add your Gemini API key to the .env file
```

## Usage

The best way to use this tool is via the interactive dashboard. From the project root, run:
```bash
python -m app.main ui
```
This will launch a local web server and open the Streamlit interface in your browser. From the sidebar, simply click **"🚀 Run Parse & Score"** to ingest the latest updates and review your shortlist!