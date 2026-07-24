from sqlalchemy import Column, Integer, String
from app.database import Base


class Vendor(Base):
    __tablename__ = "vendors"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255))
    website = Column(String(255), unique=True)