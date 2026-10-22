import json
import os
import csv
from datetime import datetime, timezone
from pathlib import Path
import gspread

from generate.make_image_post import connect, get_content_ws
from generate.story_text import get_story_text
from qc.ai_review import score_post
from qc.visual_analyzer import check_dimensions, check_safe_margins, check_image_quality
from research.fetch_news import load_yaml

LOG_FILE = "output/qc_logs.json"
CSV_FILE = "output/qc_report.csv"

def log_qc_result(cid, score, issues, status):
    """Logs to JSON and CSV for the weekly optimizer to analyze."""
    os.makedirs("output", exist_ok=True)
    
    # JSON Log
    log_entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "content_id": cid,
        "score": score,
        "issues": issues,
        "status": status
    }
    logs = []
    if os.path.exists(LOG_FILE):
        with open(LOG_FILE, "r") as f:
            try: logs = json.load(f)
            except: pass
    logs.append(log_entry)
    with open(LOG_FILE, "w") as f:
        json.dump(logs, f, indent=2)
        
    # CSV Log
    file_exists = os.path.isfile(CSV_FILE)
    with open(CSV_FILE, "a", newline="") as f:
        writer = csv.writer(f)
        if not file_exists:
            writer.writerow(["Timestamp", "Content ID", "Score", "Status", "Issues"])
        writer.writerow([log_entry["timestamp"], cid, score, status, "; ".join(issues)])

def main():
    rules = load_yaml("config/qc_rules.yaml")
    settings = load_yaml("config/settings.yaml") or {}
    feeds = load_yaml("config/sources.yaml")["feeds"]

    sh = connect()
    content_ws = get_content_ws(sh)
    headers = content_ws.row_values(1)
    col = {h: i + 1 for i, h in enumerate(headers)}
    rows = content_ws.get_all_records()

    for idx, row in enumerate(rows):
        if str(row.get("Status")) != "Draft":
            continue
            
        cid = row["Content ID"]
        ctype = row["Content Type"]
        sheet_row = idx + 2
        text = get_story_text(row.get("Source URL", ""), feeds)
        
        issues = []
        
        # --- 1. VISUAL CHECKS ---
        expected_size = rules["design_rules"]["image_size"] if ctype == "image" else rules["design_rules"]["video_size"]
        if ctype == "image":
            path = f"output/images/{cid}.jpg"
            ok, msg = check_dimensions(path, expected_size)
            if not ok: issues.append(f"DESIGN: {msg}")
            ok, msg = check_safe_margins(path)
            if not ok: issues.append(f"DESIGN: {msg}")
            ok, msg = check_image_quality(path)
            if not ok: issues.append(f"IMAGE: {msg}")

        # --- 2. AI CONTENT CHECKS ---
        ai_data = score_post(row.get("Topic", ""), row.get("Caption", ""), text)
        
        if ai_data["spelling_errors"]:
            issues.extend([f"CONTENT: Spelling - {x}" for x in ai_data["spelling_errors"]])
        if ai_data["compliance_flags"]:
            issues.extend([f"COMPLIANCE: {x}" for x in ai_data["compliance_flags"]])
        if ai_data.get("tone") != "neutral":
            issues.append(f"CONTENT: Tone is {ai_data.get('tone')}")
            
        # --- 3. SCORING ---
        # Design score is 100 minus 10 for every visual issue
        design_score = max(0, 100 - (len([i for i in issues if i.startswith("DESIGN") or i.startswith("IMAGE")]) * 15))
        
        w = rules["scoring"]["weights"]
        final_score = (
            (design_score * w["design"]) + 
            (ai_data["factuality_score"] * w["content"]) + 
            (ai_data["compliance_score"] * w["compliance"]) + 
            (ai_data["engagement_score"] * w["engagement"])
        )
        
        final_score = int(final_score)
        thresholds = rules["thresholds"]
        
        # --- 4. ROUTING ---
        if final_score >= thresholds["auto_publish"]:
            status = "Approved"
            content_ws.update_cell(sheet_row, col["Status"], status)
            content_ws.update_cell(sheet_row, col["Validation Result"], f"SCORE: {final_score} (PASS)")
            log_qc_result(cid, final_score, issues, status)
            print(f"✅ APPROVED [{final_score}] {cid}")
            
        elif final_score >= thresholds["auto_fix"]:
            status = "Needs Fix"
            content_ws.update_cell(sheet_row, col["Status"], status)
            content_ws.update_cell(sheet_row, col["Validation Result"], f"SCORE: {final_score} (AUTO-FIX)")
            content_ws.update_cell(sheet_row, col["Error Message"], " | ".join(issues))
            log_qc_result(cid, final_score, issues, status)
            print(f"⚠️ AUTO-FIX [{final_score}] {cid}: {issues}")
            
        else:
            status = "Rejected"
            content_ws.update_cell(sheet_row, col["Status"], status)
            content_ws.update_cell(sheet_row, col["Validation Result"], f"SCORE: {final_score} (REJECTED)")
            content_ws.update_cell(sheet_row, col["Error Message"], " | ".join(issues))
            log_qc_result(cid, final_score, issues, status)
            print(f"❌ REJECTED [{final_score}] {cid}")

if __name__ == "__main__":
    main()
