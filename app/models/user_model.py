from sqlalchemy import BIGINT, TIMESTAMP, Column, String

from app.core.database import Base


class User(Base):
    __tablename__ = "tb_user"

    id = Column(BIGINT, primary_key=True, autoincrement=True)
    display_name = Column(String(255), nullable=False)
    email = Column(String(255), nullable=False, unique=True)
    password = Column(String(255), nullable=False)
    cpf = Column(String(255), nullable=False)
    deleted_at = Column(TIMESTAMP)
