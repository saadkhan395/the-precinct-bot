"""QC orchestrator with visual, AI, and strict video checks."""
from datetime import datetime, timezone

import gspread

from generate.make_image_post import connect, get_content_ws
from generate.story_text import get_story_text
from qc.ai_review import score_post
from qc.visual_analyzer import (
    check_dimensions, 
    check_safe_margins, 
    check_image_quality, 
    check_video_specs
)
from research.fetch_news import load_yaml

MAX_PER_RUN = 10
REVIEW_HEADERS = [
    "Content ID", "Reason Rejected", "Failed Check", "Created At", "Reviewer Decision", "Reviewed At",
]

def get_review_ws(sh):
    try:
        ws = sh.worksheet("ReviewQueue")
    except gspread.WorksheetNotFound:
        ws = sh.add_worksheet(title="ReviewQueue", rows=1000, cols=len(REVIEW_HEADERS))
    if not ws.row_values(1):
        ws.append_row(REVIEW_HEADERS)
    return ws

def main():
    rules = load_yaml("config/qc_rules.yaml")
    settings = load_yaml("config/settings.yaml") or {}
    feeds = load_yaml("config/sources.yaml")["feeds"]

    sh = connect()
    content_ws = get_content_ws(sh)
    headers = content_ws.row_values(1)
    col = {h: i + 1 for i, h in enumerate(headers)}
    rows = content_ws.get_all_records()
    review_ws = None
    done = 0

    for idx, row in enumerate(rows):
        if str(row.get("Status")) != "Draft":
            continue
        if done >= MAX_PER_RUN:
            break
            
        done += 1
        cid = row["Content ID"]
        
        ctype = str(row.get("Content Type", "")).strip()
        sheet_row = idx + 2
        
        text = get_story_text(row.get("Source URL", ""), feeds)
        issues = []
        design_score = 100
        
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
            
        elif ctype == "reel":
            path = f"output/reels/{cid}.mp4"
            ok, msg = check_video_specs(path)
            if not ok: 
                issues.append(f"VIDEO_QC: {msg}")
                design_score = 0

        # --- 2. AI CONTENT CHECKS ---
        ai_data = score_post(row.get("Topic", ""), row.get("Caption", ""), text)
        
        if ai_data.get("spelling_errors"):
            issues.extend([f"CONTENT: Spelling - {x}" for x in ai_data["spelling_errors"]])
        if ai_data.get("compliance_flags"):
            issues.extend([f"COMPLIANCE: {x}" for x in ai_data["compliance_flags"]])
        if ai_data.get("tone") != "neutral":
            issues.append(f"CONTENT: Tone is {ai_data.get('tone')}")

        # --- 3. SCORING ---
        if design_score != 0:
            design_score = max(0, 100 - (len([i for i in issues if i.startswith("DESIGN") or i.startswith("IMAGE")]) * 15))
            
        w = rules["scoring"]["weights"]
        final_score = (
            (design_score * w["design"]) + 
            (ai_data.get("factuality_score", 0) * w["content"]) + 
            (ai_data.get("compliance_score", 0) * w["compliance"]) + 
            (ai_data.get("engagement_score", 0) * w["engagement"])
        )
        
        final_score = int(final_score)
        thresholds = rules["thresholds"]
        
        # --- 4. ROUTING ---
        if final_score >= thresholds["auto_publish"]:
            status = "Approved"
            content_ws.update_cell(sheet_row, col["Status"], status)
            content_ws.update_cell(sheet_row, col["Validation Result"], f"SCORE: {final_score} (PASS)")
            print(f"✅ APPROVED [{final_score}] {cid}")
            
        elif final_score >= thresholds["auto_fix"]:
            status = "Needs Fix"
            content_ws.update_cell(sheet_row, col["Status"], status)
            content_ws.update_cell(sheet_row, col["Validation Result"], f"SCORE: {final_score} (AUTO-FIX)")
            content_ws.update_cell(sheet_row, col["Error Message"], " | ".join(issues)[:900])
            print(f"⚠️ AUTO-FIX [{final_score}] {cid}: {issues}")
            
        else:
            status = "Rejected"
            content_ws.update_cell(sheet_row, col["Status"], status)
            content_ws.update_cell(sheet_row, col["Validation Result"], f"SCORE: {final_score} (REJECTED)")
            content_ws.update_cell(sheet_row, col["Error Message"], " | ".join(issues)[:900])
            
            if review_ws is None:
                review_ws = get_review_ws(sh)
                
            # THE FIX IS HERE: value_input_option instead of value_input_type
            review_ws.append_row([
                cid,
                " | ".join(issues)[:900],
                "QC Fail",
                datetime.now(timezone.utc).isoformat(timespec="seconds"),
                "",
                "",
            ], value_input_option="RAW")
            print(f"❌ REJECTED [{final_score}] {cid}")

    if done == 0:
        print("No Draft items to check.")
    print("QC OK")

if __name__ == "__main__":
    main()
