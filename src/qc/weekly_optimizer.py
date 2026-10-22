"""Analyzes weekly QC and Analytics data to upgrade design templates."""
import csv
import json
import os
from collections import defaultdict

def analyze_weekly_performance():
    print("Starting Weekly Design Upgrade Analysis...")
    
    # 1. Read QC Logs to find common design failures
    design_fails = defaultdict(int)
    if os.path.exists("output/qc_report.csv"):
        with open("output/qc_report.csv", "r") as f:
            reader = csv.DictReader(f)
            for row in reader:
                if "DESIGN" in row["Issues"]:
                    design_fails["layout_overlap"] += 1
                if "IMAGE" in row["Issues"]:
                    design_fails["image_quality"] += 1

    # 2. Read Analytics for Engagement
    # (In a full production system, this would pull from the Google Sheet Analytics tab)
    
    # 3. Auto-Upgrade Logic
    current_template = {
        "version": "1.0",
        "footer_color": "#000000",
        "text_color": "#FFFFFF",
        "highlight_color": "#DC2828",
        "padding": 90
    }
    
    new_template = dict(current_template)
    
    if design_fails.get("layout_overlap", 0) > 5:
        print("Detected high layout overlap. Increasing safe margins.")
        new_template["padding"] += 20
        new_template["version"] = "1.1"
        
    if design_fails.get("image_quality", 0) > 3:
        print("Detected poor image quality. Forcing higher resolution fetch.")
        # (This would trigger a flag in the fetch_image script)
        
    # Save the new template
    os.makedirs("config", exist_ok=True)
    with open("config/design_template.json", "w") as f:
        json.dump(new_template, f, indent=2)
        
    print(f"✅ Design upgraded to version {new_template['version']}. Report saved.")

if __name__ == "__main__":
    analyze_weekly_performance()
