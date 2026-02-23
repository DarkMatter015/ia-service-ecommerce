from pydantic import BaseModel


class ProductEventDTO(BaseModel):
    id: int | None = None
    name: str | None = None
    description: str | None = None
    price: float | None = None
    category: str | None = None
    stock: int | None = None


class ProductMetadata(BaseModel):
    price: float
    category: str
    stock: int
