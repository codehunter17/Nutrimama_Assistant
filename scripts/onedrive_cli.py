"""CLI helper to authorize and upload/download backups to OneDrive via MSAL.

Usage:
  python -m scripts.onedrive_cli authorize <client_id> cache.json
  python -m scripts.onedrive_cli upload <user_id> <client_id> cache.json [filename]
  python -m scripts.onedrive_cli download <file_id> <client_id> cache.json out.json
"""
import sys
import logging

from app.onedrive_backup import authorize_device_flow, upload_backup_to_onedrive, download_backup_from_onedrive

LOGGER = logging.getLogger(__name__)


def _usage():
    print(__doc__)


def main(argv):
    if len(argv) < 2:
        _usage(); return 1

    cmd = argv[1]
    if cmd == "authorize" and len(argv) == 4:
        client_id = argv[2]; cache = argv[3]
        authorize_device_flow(client_id, cache)
        return 0

    if cmd == "upload" and len(argv) >= 5:
        user = argv[2]; client_id = argv[3]; cache = argv[4]; name = argv[5] if len(argv) > 5 else None
        fid = upload_backup_to_onedrive(user, client_id, cache, name)
        print("uploaded:", fid)
        return 0

    if cmd == "download" and len(argv) == 5:
        fid = argv[2]; client_id = argv[3]; cache = argv[4]; out = argv[5]
        data = download_backup_from_onedrive(fid, client_id, cache)
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
