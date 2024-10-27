from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, EmailStr, validators, Field, validator

EVENT_STATUSES = ["planning", "ready", "active", "completed", "canceled"]
class BaseSchema(BaseModel):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        orm_mode = True

class EventBase(BaseModel):
    title: str = Field(..., description="Название события")
    status: str = Field(..., description="Статус события")
    description: Optional[str] = Field(None, description="Описание события")
    start_at: datetime = Field(..., description="Дата и время начала события")
    location: str = Field(..., description="Место проведения события")
    end_at: datetime = Field(..., description="Дата и время окончания события")
    price: int = Field(..., description="Цена события")
    visitor_limit: Optional[int] = Field(None, description="Лимит посетителей")

    @validator('price')
    def price_non_negative(cls, v):
        if v < 0:
            raise ValueError('price must be non-negative')
        return v

    @validator('visitor_limit')
    def visitor_limit_non_negative(cls, v):
        if v is not None and v < 0:
            raise ValueError('visitor_limit must be non-negative')
        return v

class EventCreate(EventBase):
    pass

class Event(EventBase, BaseSchema):
    pass

class VisitorBase(BaseModel):
    first_name: str = Field(..., description="Имя")
    last_name: str = Field(..., description="Фамилия")
    phone: str = Field(..., description="Телефон")
    email: EmailStr = Field(None, description="Почта")

class VisitorCreate(VisitorBase):
    pass

class Visitor(VisitorBase, BaseSchema):
    pass

REGISTRATION_STATUSES = ["unpaid", "paid", "refunded", "cancelled", "completed"]
class RegistrationBase(BaseModel):
    visitor_id: int = Field(..., description="ID посетителя")
    event_id: int = Field(..., description="ID мероприятия")
    status: str = Field("unpaid", description="Статус регистрации")
    price: Optional[int] = Field(None, description="Цена")
    billed_amount: Optional[int] = Field(None, description="Оплаченная сумма")
    refund_amount: Optional[int] = Field(None, description="Сумма возврата")
    billed_at: datetime = Field(None, description="Оплата в")
    refunded_at: datetime = Field(None, description="Возврат в")


class RegistrationCreate(RegistrationBase):
    pass

class Registration(RegistrationBase, BaseSchema):
    pass