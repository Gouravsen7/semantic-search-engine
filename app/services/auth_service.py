"""Create accounts and check passwords."""

import uuid

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.exceptions import ConflictError, UnauthorizedError
from app.core.security import hash_password, verify_password
from app.db.models import User


class AuthService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def register(self, email: str, password: str) -> User:
        if self._by_email(email) is not None:
            raise ConflictError("An account with this email already exists.")

        user = User(id=uuid.uuid4(), email=email, password_hash=hash_password(password))
        try:
            self.db.add(user)
            self.db.commit()
        except IntegrityError:
            self.db.rollback()
            raise ConflictError("An account with this email already exists.") from None
        except SQLAlchemyError:
            self.db.rollback()
            raise
        self.db.refresh(user)
        return user

    def authenticate(self, email: str, password: str) -> User:
        user = self._by_email(email)
        if user is None or not verify_password(password, user.password_hash):
            raise UnauthorizedError("Invalid email or password.")
        return user

    def get_user(self, user_id: uuid.UUID) -> User | None:
        return self.db.get(User, user_id)

    def _by_email(self, email: str) -> User | None:
        return self.db.scalar(select(User).where(User.email == email))
