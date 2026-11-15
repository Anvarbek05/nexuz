"""Admin commands for your own computer.

  python -m app.admin users                       list users
  python -m app.admin grant person@example.com 30   give 30 days of Premium
  python -m app.admin revoke person@example.com     remove Premium
"""
import sys

from app import db
from app.errors import ApiError
from app.services import accounts


def main(argv: list[str]) -> int:
    if not argv or argv[0] not in ("users", "grant", "revoke"):
        print(__doc__)
        return 1
    try:
        if argv[0] == "users":
            for u in db.query_all("SELECT email, premium_until, created_at FROM users ORDER BY created_at"):
                print(u["email"], "| premium until:", u["premium_until"] or "-", "| created:", u["created_at"])
        elif argv[0] == "grant" and len(argv) == 3:
            print(accounts.set_premium(argv[1], int(argv[2]))["premium_until"])
        elif argv[0] == "revoke" and len(argv) == 2:
            accounts.set_premium(argv[1], 0)
            print("Premium removed.")
        else:
            print(__doc__)
            return 1
    except ApiError as err:
        print("Error:", err.code)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
