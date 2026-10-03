import os
import json
import gspread

info = json.loads(os.environ["GOOGLE_SERVICE_ACCOUNT_JSON"])
gc = gspread.service_account_from_dict(info)
sh = gc.open_by_key(os.environ["GOOGLE_SHEET_ID"])
print([ws.title for ws in sh.worksheets()])
print("SHEETS OK")
