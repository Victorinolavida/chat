import bcrypt
from sqlalchemy.exc import IntegrityError

from app.dtos.user_dto import UserCreateDTO
from app.extensions import db
from app.models.user import User


class UserAlreadyExistsError(Exception):
    def __init__(self, field: str) -> None:
        self.field = field
        super().__init__(f"A user with this {field} already exists")


class InvalidCredentialsError(Exception):
    pass


class UserService:
    def _hash_password(self, password: str) -> str:
        hashed = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt())
        return hashed.decode("utf-8")

    def _verify_password(self, password: str, password_hash: str) -> bool:
        return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))

    def get_by_email(self, email: str) -> User | None:
        return db.session.execute(
            db.select(User).filter_by(email=email)
        ).scalar_one_or_none()

    def get_by_username(self, username: str) -> User | None:
        return db.session.execute(
            db.select(User).filter_by(username=username)
        ).scalar_one_or_none()

    def register(self, data: UserCreateDTO) -> User:
        if self.get_by_email(data.email) is not None:
            raise UserAlreadyExistsError("email")
        if self.get_by_username(data.username) is not None:
            raise UserAlreadyExistsError("username")

        user = User(
            username=data.username,
            email=data.email,
            password_hash=self._hash_password(data.password),
        )
        db.session.add(user)
        try:
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
            raise UserAlreadyExistsError("email")
        return user

    def authenticate(self, email: str, password: str) -> User:
        user = self.get_by_email(email)
        if user is None or not self._verify_password(password, user.password_hash):
            raise InvalidCredentialsError("Invalid email or password")
        return user


def build_user_service() -> UserService:
    return UserService()
