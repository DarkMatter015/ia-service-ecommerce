from sqlalchemy import Column, String, JSON, TIMESTAMP, text, BIGINT
from sqlalchemy.dialects.postgresql import UUID
from pgvector.sqlalchemy import Vector
from app.core.database import Base

class ProductEmbedding(Base):
    __tablename__ = "product_embeddings"

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    product_id = Column(BIGINT, nullable=False)
    embedding = Column(Vector(768)) 
    content = Column(String)
    metadata_ = Column("metadata", JSON)
    created_at = Column(TIMESTAMP, server_default=text("CURRENT_TIMESTAMP"))