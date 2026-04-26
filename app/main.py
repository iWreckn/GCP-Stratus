import typer
import sqlite3

from app.config import logger
from app.db import init_db, get_connection
from app.parser import fetch_release_notes

app = typer.Typer(
    help="GCP Release Intel - An intelligence pipeline for cloud security product updates.",
    add_completion=False
)

@app.command()
def parse():
    """Extract atomic release notes and store them in the database idempotently."""
    init_db()
    events = fetch_release_notes(days_back=10)
    
    inserted_count = 0
    with get_connection() as conn:
        cursor = conn.cursor()
        for event in events:
            try:
                cursor.execute("""
                    INSERT INTO release_note_events 
                    (service, published_date, raw_text, source_url, doc_links, event_hash, category, published_week)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    event.service, event.published_date, event.raw_text, 
                    event.source_url, event.doc_links, event.event_hash, event.category, event.published_week
                ))
                inserted_count += 1
            except sqlite3.IntegrityError:
                # Skip duplicates gracefully (Idempotent insert)
                pass
        conn.commit()

    logger.info(f"Parse step complete. Inserted {inserted_count} new atomic events.")

@app.command()
def score():
    """Run deterministic rule-based scoring and audience weighting."""
    from app.scorer import evaluate_event
    
    logger.info("Starting deterministic scoring engine...")
    with get_connection() as conn:
        cursor = conn.cursor()
        # Fetch all events that haven't been scored yet
        cursor.execute("SELECT id, service, raw_text FROM release_note_events WHERE final_score = 0")
        rows = cursor.fetchall()
        
        if not rows:
            logger.info("No new events to score.")
            return
            
        scored = 0
        discarded = 0
        
        for row in rows:
            rule_score, pop_score, final_score = evaluate_event(row["service"], row["raw_text"])
            
            if final_score == -1.0:
                discarded += 1
                
            cursor.execute("""
                UPDATE release_note_events 
                SET rule_score = ?, popularity_score = ?, final_score = ?
                WHERE id = ?
            """, (rule_score, pop_score, final_score, row["id"]))
            scored += 1
            
        conn.commit()
        
    logger.info(f"Scoring complete. Evaluated: {scored} | Discarded: {discarded} | Shortlisted: {scored - discarded}")

@app.command()
def enrich():
    """Transform & Enrich unclassified records using Gemini AI."""
    logger.info("Enrichment step placeholder - Awaiting AI refactor.")

@app.command()
def report():
    """Generate YouTube-ready reports."""
    logger.info("Reporting step placeholder - Awaiting Publisher refactor.")

@app.command()
def shortlist(top: int = 60):
    """Generate and view the top highest-scoring events in an HTML dashboard."""
    from app.reports import generate_shortlist_html
    generate_shortlist_html(top)

@app.command()
def ui():
    """Launch the interactive web dashboard."""
    import os
    os.system("streamlit run app/ui.py")

@app.command()
def run_all():
    """Run parse, score, enrich, and report in sequence."""
    parse()
    score()
    # enrich()
    # report()

if __name__ == "__main__":
    app()