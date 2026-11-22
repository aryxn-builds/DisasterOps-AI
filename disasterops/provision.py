import argparse
from getpass import getpass

from sqlalchemy import create_engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from .config import Settings
from .models import Account
from .schemas import Register
from .services.auth import password_hasher


def main():
    parser = argparse.ArgumentParser(
        description="Create a local research operator account"
    )
    parser.add_argument("role", choices=["dispatcher", "responder"])
    parser.add_argument("username")
    args = parser.parse_args()
    password = getpass("Password (at least 12 characters): ")
    if password != getpass("Confirm password: "):
        parser.error("Passwords do not match")
    try:
        data = Register(username=args.username, password=password)
    except ValueError:
        parser.error("Username or password does not meet the requirements")
    engine = create_engine(Settings().postgres_url(), hide_parameters=True)
    with Session(engine) as db:
        db.add(
            Account(
                username=data.username,
                role=args.role,
                password_hash=password_hasher.hash(password),
            )
        )
        try:
            db.commit()
        except IntegrityError:
            parser.error("Username unavailable")
    print(f"Created {args.role} account {data.username}")


if __name__ == "__main__":
    main()
