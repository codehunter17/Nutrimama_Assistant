"""CLI helper to authorize and upload/download backups to Google Drive.

Usage examples:
  python -m scripts.drive_cli authorize /path/to/client_secrets.json creds.json
  python -m scripts.drive_cli upload user_001 creds.json
  python -m scripts.drive_cli download <file_id> creds.json out.json
"""
import sys
import os
import logging

from typing import Optional

from app.drive_backup import authorize_with_browser, upload_backup_to_drive, download_backup_from_drive

LOGGER = logging.getLogger(__name__)


def _usage():
    print(__doc__)


def main(argv):
    if len(argv) < 2:
        _usage(); return 1

    cmd = argv[1]
    if cmd == "authorize" and len(argv) == 4:
        client_secrets = argv[2]; creds_out = argv[3]
        authorize_with_browser(client_secrets, creds_out)
        return 0

    if cmd == "upload" and len(argv) >= 4:
        user_id = argv[2]; creds = argv[3]; name = argv[4] if len(argv) > 4 else None
        fid = upload_backup_to_drive(user_id, creds, name)
        print("uploaded:", fid)
        return 0

    if cmd == "download" and len(argv) == 5:
        fid = argv[2]; creds = argv[3]; out = argv[4]
        data = download_backup_from_drive(fid, creds)
        if data:
            with open(out, "wb") as f:
                f.write(data)
            print("downloaded to", out)
            return 0
        return 2

    _usage()
    return 2


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    sys.exit(main(sys.argv))
