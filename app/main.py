from fastapi import FastAPI, Depends, HTTPException
from .database import engine, Base, SessionLocal
from . import models, schemas
from sqlalchemy.orm import Session
app = FastAPI()

Base.metadata.create_all(bind=engine)
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.get("/")
def read_root():
    return {"Hello": "World"}
@app.post("/events/", response_model=schemas.Event)
def create_event(event: schemas.EventCreate, db: Session = Depends(get_db)):
    db_event = models.Event(**event.model_dump())
    db.add(db_event)
    db.commit()
    db.refresh(db_event)
    return db_event

@app.get("/events/{event_id}", response_model=schemas.Event)
def read_event(event_id: int, db: Session = Depends(get_db)):
    db_event = db.query(models.Event).filter(models.Event.id == event_id).first()
    if db_event is None:
        raise HTTPException(status_code=404, detail="Event not found")
    return db_event

@app.post("/visitors/", response_model=schemas.Visitor)
def create_visitor(visitor: schemas.VisitorCreate, db: Session = Depends(get_db)):
    db_visitor = models.Visitor(**visitor.model_dump())
    db.add(db_visitor)
    db.commit()
    db.refresh(db_visitor)
    return db_visitor

@app.get("/visitors/{visitor_id}", response_model=schemas.Visitor)
def read_visitor(visitor_id: int, db: Session = Depends(get_db)):
    db_visitor = db.query(models.Visitor).filter(models.Visitor.id == visitor_id).first()
    if db_visitor is None:
        raise HTTPException(status_code=404, detail="Visitor not found")
    return db_visitor

@app.post("/registrations/", response_model=schemas.Registration)
def create_registration(registration: schemas.RegistrationCreate, db: Session = Depends(get_db)):
    db_registration = models.Registration(**registration.model_dump())
    db.add(db_registration)
    db.commit()
    db.refresh(db_registration)
    return db_registration

@app.get("/registrations/{registration_id}", response_model=schemas.Registration)
def read_registration(registration_id: int, db: Session = Depends(get_db)):
    db_registration = db.query(models.Registration).filter(models.Registration.id == registration_id).first()
    if db_registration is None:
        raise HTTPException(status_code=404, detail="Registration not found")
    return db_registration