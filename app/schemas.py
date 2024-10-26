from pydantic import BaseModel, EmailStr
from datetime import datetime

class BaseSchema(BaseModel):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        orm_mode = True

class EventBase(BaseModel):
    title: str
    status: str = "active"
    description: str = None
    start_at: datetime
    location: str
    end_at: datetime
    price: int = 0
    visitor_limit: int = 0

class EventCreate(EventBase):
    pass

class Event(EventBase, BaseSchema):
    pass

class VisitorBase(BaseModel):
    first_name: str
    last_name: str
    phone: str
    email: EmailStr = None

class VisitorCreate(VisitorBase):
    pass

class Visitor(VisitorBase, BaseSchema):
    pass

class RegistrationBase(BaseModel):
    visitor_id: int
    event_id: int
    status: str = "unpaid"
    price: int = None
    billed_amount: int = None
    refund_amount: int = None
    billed_at: datetime = None
    refunded_at: datetime = None

class RegistrationCreate(RegistrationBase):
    pass

class Registration(RegistrationBase, BaseSchema):
    pass