from pgvector.sqlalchemy import Vector
from sqlalchemy import BIGINT, JSON, TIMESTAMP, Column, String, text
from sqlalchemy.dialects.postgresql import TSVECTOR, UUID

from app.core.database import Base


class ProductEmbedding(Base):
    __tablename__ = "product_embeddings"

    id = Column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    product_id = Column(BIGINT, nullable=False)
    embedding = Column(Vector(768))
    content = Column(String)
    metadata_ = Column("metadata", JSON)
    created_at = Column(TIMESTAMP, server_default=text("CURRENT_TIMESTAMP"))
    search_vector = Column(TSVECTOR)
