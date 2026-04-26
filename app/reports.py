import html
import webbrowser
from pathlib import Path
from app.db import get_connection
from app.config import logger

def generate_shortlist_html(top: int = 60):
    """Pulls top scored events and generates a static HTML dashboard."""
    logger.info(f"Generating HTML dashboard for top {top} shortlisted events...")
    
    # Ensure exports directory exists
    export_dir = Path("exports")
    export_dir.mkdir(parents=True, exist_ok=True)
    
    html_path = export_dir / "shortlist.html"
    
    with get_connection() as conn:
        cursor = conn.cursor()
        # Fetch top scored events
        cursor.execute("""
            SELECT service, category, final_score, published_date, raw_text, doc_links 
            FROM release_note_events 
            WHERE final_score > 0
            ORDER BY final_score DESC
            LIMIT ?
        """, (top,))
        rows = cursor.fetchall()
        
    if not rows:
        logger.warning("No scored data found to generate report. Run score first!")
        return

    # Build a clean HTML structure with basic CSS styling
    html_content = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>GCP Release Intel - Top Shortlist</title>
    <style>
        body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; background-color: #f4f6f8; color: #333; margin: 0; padding: 40px 20px; }
        h1 { text-align: center; color: #1a73e8; margin-bottom: 30px; font-size: 2.2em; }
        .table-container { max-width: 1400px; margin: 0 auto; background: #fff; border-radius: 8px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); overflow: hidden; }
        table { width: 100%; border-collapse: collapse; }
        th, td { padding: 16px 20px; text-align: left; border-bottom: 1px solid #eee; vertical-align: top; }
        th { background-color: #1a73e8; color: white; font-weight: 600; font-size: 1.1em; }
        tr:hover { background-color: #f8f9fa; }
        .score-col { width: 10%; font-weight: bold; color: #d93025; font-size: 1.2em; text-align: center; }
        .service-col { width: 20%; font-weight: bold; color: #1a73e8; font-size: 1.1em; }
        .date-col { width: 15%; color: #666; font-weight: 500; }
        .content-col { width: 55%; white-space: pre-wrap; line-height: 1.6; font-size: 0.95em; color: #444; }
        .category-badge { display: inline-block; background-color: #e8f0fe; color: #1a73e8; padding: 4px 8px; border-radius: 4px; font-size: 0.8em; margin-top: 8px; font-weight: normal;}
    </style>
</head>
<body>
    <h1>GCP Release Intel - Top Shortlist</h1>
    <div class="table-container">
        <table>
            <thead>
                <tr>
                    <th class="score-col">Score</th>
                    <th class="service-col">Service</th>
                    <th class="date-col">Release Date</th>
                    <th class="content-col">Description</th>
                </tr>
            </thead>
            <tbody>"""
            
    for row in rows:
        score = f"{row['final_score']:.2f}"
        service = html.escape(row["service"])
        category = html.escape(row["category"])
        date = html.escape(row["published_date"].split("T")[0]) if row["published_date"] else "Unknown"
        content = html.escape(row["raw_text"])
        
        # Safely parse and generate buttons for documentation links
        doc_links = row["doc_links"]
        links_html = ""
        if doc_links:
            links = doc_links.split(",")
            links_html = "<div style='margin-top: 12px;'>"
            for i, link in enumerate(links, 1):
                links_html += f"<a href='{html.escape(link)}' target='_blank' style='display: inline-block; background-color: #f8f9fa; color: #1a73e8; padding: 6px 12px; border-radius: 16px; font-size: 0.85em; text-decoration: none; margin-right: 8px; margin-top: 6px; border: 1px solid #dadce0; font-weight: 500;'>📘 Docs Link {i}</a>"
            links_html += "</div>"
        
        html_content += f"""
                <tr>
                    <td class="score-col">{score}</td>
                    <td class="service-col">{service}<br><span class="category-badge">{category}</span></td>
                    <td class="date-col">{date}</td>
                    <td class="content-col">{content}{links_html}</td>
                </tr>"""
        
    html_content += "\n            </tbody>\n        </table>\n    </div>\n</body>\n</html>"

    with open(html_path, "w", encoding="utf-8") as f:
        f.write(html_content)
        
    logger.info(f"HTML report successfully generated at {html_path.absolute()}")
    
    # Automatically open the report in the default web browser
    try:
        webbrowser.open(f"file://{html_path.absolute()}")
        logger.info("Opened report in your default web browser.")
    except Exception as e:
        pass