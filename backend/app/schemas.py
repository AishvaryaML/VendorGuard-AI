from pydantic import BaseModel

class VendorRequest(BaseModel):
    url: str