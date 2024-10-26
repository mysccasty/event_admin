from sqlalchemy import Column, ForeignKey, Integer, String, DateTime, TIMESTAMP, func
from sqlalchemy.orm import relationship
from .database import Base

class Event(Base):
    __tablename__ = "events"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), index=True, nullable=False)
    status = Column(String(255), server_default="planning", nullable=False)
    description = Column(String(255))
    start_at = Column(DateTime, nullable=False)
    location = Column(String(255), nullable=False)
    end_at = Column(DateTime, nullable=False)
    price = Column(Integer, default=0, nullable=False)
    visitor_limit = Column(Integer, default=0)
    created_at = Column(TIMESTAMP, server_default=func.now())
    updated_at = Column(TIMESTAMP, server_default=func.now())
    registrations = relationship("Registration", back_populates="event")

class Visitor(Base):
    __tablename__ = "visitors"

    id = Column(Integer, primary_key=True, index=True)
    first_name = Column(String(255), nullable=False)
    last_name = Column(String(255), nullable=False)
    phone = Column(String(20), unique=True, nullable=False)
    email = Column(String(255), unique=True)
    created_at = Column(TIMESTAMP, server_default=func.now())
    updated_at = Column(TIMESTAMP, server_default=func.now())
    registrations = relationship("Registration", back_populates="visitor")

class Registration(Base):
    __tablename__ = "registrations"

    id = Column(Integer, primary_key=True, index=True)
    visitor_id = Column(Integer, ForeignKey("visitors.id"))
    event_id = Column(Integer, ForeignKey("events.id"))

    visitor = relationship("Visitor", back_populates="registrations")
    event = relationship("Event", back_populates="registrations")
    status = Column(String(255), server_default="unpaid", nullable=False)
    price = Column(Integer)
    billed_amount = Column(Integer)
    refund_amount = Column(Integer)
    billed_at = Column(TIMESTAMP)
    refunded_at = Column(TIMESTAMP)
    created_at = Column(TIMESTAMP, server_default=func.now())
    updated_at = Column(TIMESTAMP, server_default=func.now())
