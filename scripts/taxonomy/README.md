Update taxonomy and locations based on the spreadsheet hosted on the COAT Box storage.

Requirements:
- rclone
- duckdb
- jq

A remote named must be configured in rclone: type "box", type enterprise, and authenticate via web browser.

Run `./sync.sh` to update the taxonomy and locations.