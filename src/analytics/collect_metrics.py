def main():
    sh = connect()
    content_ws = sh.worksheet("Content")
    analytics_ws = get_analytics_ws(sh)

    fb_token = os.environ.get("META_PAGE_ACCESS_TOKEN", "")
    ig_token = os.environ.get("INSTAGRAM_ACCESS_TOKEN", "")
    
    rows = content_ws.get_all_records()
    existing = analytics_ws.get_all_records()
    existing_by_id = {str(r.get("Content ID", "")).strip(): i + 2 for i, r in enumerate(existing)}
    headers_an = analytics_ws.row_values(1)

    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    collected = 0

    for row in rows:
        if str(row.get("Status", "")).strip() != "Published":
            continue
        cid = str(row.get("Content ID", "")).strip()
        if not cid:
            continue

        fb_id = str(row.get("Facebook Post ID", "")).strip()
        ig_id = str(row.get("Instagram Media ID", "")).strip()

        print(f"\n=== {cid} ===")
        
        try:
            metrics = {}
            if fb_id:
                metrics.update(_get_fb_metrics(fb_id, fb_token))
            if ig_id:
                metrics.update(_get_ig_metrics(ig_id, ig_token))

            values = {
                "Content ID": cid,
                "Content Type": str(row.get("Content Type", "")),
                "Topic": str(row.get("Topic", ""))[:200],
                "Published Time": str(row.get("Published Time", "")),
                "Last Collected": now,
                "FB Post ID": fb_id,
                "IG Media ID": ig_id,
            }
            values.update(metrics)

            row_values = [values.get(h, "") for h in headers_an]

            if cid in existing_by_id:
                sheet_row = existing_by_id[cid]
                # THE FIX: Update the entire row at once (1 write request instead of 17)
                analytics_ws.update(f"A{sheet_row}:Q{sheet_row}", [row_values])
            else:
                analytics_ws.append_row(row_values, value_input_type="RAW")
            collected += 1
            print(f"  Collected: {metrics}")
            
        except Exception as e:
            print(f"  ERROR saving metrics for {cid}: {e}. Skipping to next post.")

    print(f"\nDone. Collected metrics for {collected} published item(s).")
