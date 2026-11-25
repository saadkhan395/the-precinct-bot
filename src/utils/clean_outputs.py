import os
import json
import gspread
from datetime import datetime, timedelta, timezone

def main():
    print("Starting output cleanup...")
    info = json.loads(os.environ["GOOGLE_SERVICE_ACCOUNT_JSON"])
    gc = gspread.service_account_from_dict(info)
    sh = gc.open_by_key(os.environ["GOOGLE_SHEET_ID"])
    content_ws = sh.worksheet("Content")
    
    rows = content_ws.get_all_records()
    now = datetime.now(timezone.utc)
    deleted_count = 0

    for row in rows:
        status = str(row.get("Status", "")).strip()
        cid = str(row.get("Content ID", "")).strip()
        
        # Delete files if the post is Published AND older than 3 days
        if status == "Published":
            pub_time_str = str(row.get("Published Time", "")).strip()
            if not pub_time_str:
                continue
                
            try:
                pub_time = datetime.fromisoformat(pub_time_str.replace("Z", "+00:00"))
            except:
                continue
                
            if now - pub_time > timedelta(days=3):
                # Delete files
                paths_to_delete = [
                    f"output/images/{cid}.jpg",
                    f"output/reels/{cid}.mp4"
                ]
                for p in paths_to_delete:
                    if os.path.exists(p):
                        os.remove(p)
                        print(f"Deleted {p}")
                        deleted_count += 1
                        
                # Delete carousel folder
                carousel_dir = f"output/carousels/{cid}"
                if os.path.isdir(carousel_dir):
                    import shutil
                    shutil.rmtree(carousel_dir)
                    print(f"Deleted folder {carousel_dir}")
                    deleted_count += 1

    print(f"Cleanup complete. Removed {deleted_count} items.")

if __name__ == "__main__":
    main()
