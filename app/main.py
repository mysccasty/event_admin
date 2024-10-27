import traceback
from datetime import datetime
from typing import Type, Optional
from urllib.parse import urlencode

from fastapi import FastAPI, Depends, Request, HTTPException, Query, Form
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import EmailStr
from sqlalchemy import func
from sqlalchemy.orm import Session
from starlette.responses import JSONResponse, RedirectResponse

from .database import engine, Base, SessionLocal
from . import models, schemas
from .schemas import EventBase, VisitorBase, RegistrationBase

app = FastAPI()

templates = Jinja2Templates(directory="templates")

@app.exception_handler(Exception)
async def internal_server_error_handler(request: Request, exc: Exception):
    stack_trace = traceback.format_exc()

    error_line = stack_trace.splitlines()[-1]

    return JSONResponse(
        status_code=500,
        content={
            "detail": "Internal Server Error",
            "error": str(exc),
            "error_line": error_line,
            "stack_trace": stack_trace,
        },
    )

def build_url_with_query(base_url, **kwargs):
    query_string = urlencode(kwargs)
    return f"{base_url}?{query_string}"


def order_query(model: Type[Base], query: Query, sort_by: str, sort_order: int)->Query:
    if sort_by and hasattr(model, sort_by):
        if sort_order:
            query = query.order_by(getattr(model, sort_by).desc())
        else:
            query = query.order_by(getattr(model, sort_by))
    return query


def format_price(value):
    return f"{value if value else 0:.2f} ₽"

def format_datetime_ru(value):
    if isinstance(value, datetime):
        return value.strftime('%d.%m.%Y %H:%M:%S')
    return value

templates.env.filters["format_price"] = format_price
templates.env.filters["format_datetime_ru"] = format_datetime_ru

app.mount("/static", StaticFiles(directory="static"), name="static")

Base.metadata.create_all(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.get("/", response_class=HTMLResponse)
def get_route(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/events/", response_class=HTMLResponse)
def get_events(
        request: Request,
        db: Session = Depends(get_db),
        visitor_id = Query(None),
        sort_by: str = Query(None),
        sort_order: int = Query(None),
        search: str = Query(None),
        status: str = Query(None)
    ):
    if not (visitor_id=="" or visitor_id is None or visitor_id.isdigit()):
        raise HTTPException(status_code=400, detail="Invalid visitor id")
    query = db.query(models.Event)
    if visitor_id:
        query = query.filter(models.Registration.visitor_id == visitor_id)
    if search:
        query = query.filter(
            models.Event.title.ilike(f"%{search}%") |
            models.Event.description.ilike(f"%{search}%") |
            models.Event.location.ilike(f"%{search}%")
        )
    if status:
        query = query.filter(models.Event.status == status)
    query = order_query(models.Event, query, sort_by, sort_order)
    events = query.all()
    return templates.TemplateResponse("event/index.html", {
        "request": request,
        "events": events,
        "sort_by": sort_by,
        "sort_order": sort_order,
        "search": search,
        "statuses": schemas.EVENT_STATUSES,
        "status": status
    })

@app.get("/events/{event_id}", response_model=schemas.Event)
def read_event(event_id: int, request: Request, db: Session = Depends(get_db)):
    db_event = db.query(models.Event).filter(models.Event.id == event_id).first()
    if db_event is None:
        raise HTTPException(status_code=404, detail="Event not found")
    visitors = db.query(models.Visitor).join(models.Registration).filter(models.Registration.event_id == event_id).all()
    total_income = db.query(func.sum(
        func.coalesce(models.Registration.billed_amount, 0) - func.coalesce(models.Registration.refund_amount,0)
    )).filter(
        models.Registration.event_id == event_id).scalar() or 0
    expected_income = db.query(func.sum(
        func.coalesce(models.Registration.price, 0)
    )).filter(
        models.Registration.event_id == event_id).scalar() or 0
    return templates.TemplateResponse("event/view.html", {
        "request": request,
        "event": db_event,
        "visitors": visitors,
        "total_income": total_income,
        "expected_income": expected_income,
        "build_url_with_query": build_url_with_query
    })

@app.get("/events/create/", response_class=HTMLResponse, description="Страница создания события")
def create_event_form(request: Request):
    return templates.TemplateResponse("event/create.html", {
        "request": request,
        "statuses": schemas.EVENT_STATUSES,
    })
@app.get("/events/{event_id}/update/", response_class=HTMLResponse)
def update_event_form(event_id: int, request: Request, db: Session = Depends(get_db)):
    db_event = db.query(models.Event).filter(models.Event.id == event_id).first()
    if db_event is None:
        raise HTTPException(status_code=404, detail="Event not found")
    return templates.TemplateResponse("event/update.html", {
        "request": request,
        "event": db_event,
        "statuses": schemas.EVENT_STATUSES,
    })
@app.post("/events/create/", response_model=EventBase, description="Создать новое событие")
def create_event(
    title: str = Form(...),
    description: Optional[str] = Form(None),
    status: str = Form("planning"),
    location: str = Form(...),
    start_at: str = Form(...),
    end_at: str = Form(...),
    price: float = Form(...),
    visitor_limit: str = Form(None),
    db: Session = Depends(get_db)
):
    if not (visitor_limit == "" or visitor_limit is None or visitor_limit.isdigit()):
        raise HTTPException(status_code=400, detail=f"Invalid visitor limit")
    if visitor_limit == "":
        visitor_limit = None
    event_data = schemas.EventCreate(
        title=title,
        description=description,
        status=status,
        location=location,
        start_at=start_at,
        end_at=end_at,
        price=price,
        visitor_limit=visitor_limit
    )
    db_event = models.Event(**event_data.dict())
    db.add(db_event)
    db.commit()
    db.refresh(db_event)
    return RedirectResponse(url=f"/events/{db_event.id}", status_code=303)
@app.post("/events/{event_id}/update/", response_model=EventBase, description="Обновить мероприятие")
def update_event(
    event_id: int,
    title: str = Form(...),
    description: Optional[str] = Form(None),
    status: str = Form("planning"),
    location: str = Form(...),
    start_at: str = Form(...),
    end_at: str = Form(...),
    price: float = Form(...),
    visitor_limit: str = Form(None),
    db: Session = Depends(get_db)
):
    if not (visitor_limit == "" or visitor_limit is None or visitor_limit.isdigit()):
        raise HTTPException(status_code=400, detail=f"Invalid visitor limit")
    if visitor_limit == "":
        visitor_limit = None
    db_event = db.query(models.Event).filter(models.Event.id == event_id).first()
    if db_event is None:
        raise HTTPException(status_code=404, detail="Event not found")
    event = schemas.EventCreate(
        title=title,
        description=description,
        status=status,
        location=location,
        start_at=start_at,
        end_at=end_at,
        price=price,
        visitor_limit=visitor_limit
    )
    for key, value in event.dict().items():
        if key != 'created_at':
            setattr(db_event, key, value)
    db.commit()
    db.refresh(db_event)
    return RedirectResponse(url=f"/events/{db_event.id}", status_code=303)

@app.get("/events/{event_id}/delete/", response_model=None)
def delete_event(event_id: int, db: Session = Depends(get_db)):
    event = db.query(models.Event).filter(models.Event.id == event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    db.delete(event)
    db.commit()

    return RedirectResponse(url="/events/", status_code=303)
@app.get("/visitors/", response_class=HTMLResponse)
def get_visitors(request: Request, db: Session = Depends(get_db), event_id: int = Query(None), sort_by: str = Query(None), sort_order: int = Query(None), search: str = Query(None)):
    query = db.query(models.Visitor)
    if event_id:
        query = query.filter(models.Registration.event_id == event_id)
    if search:
        query = query.filter(
            models.Visitor.first_name.ilike(f"%{search}%") |
            models.Visitor.last_name.ilike(f"%{search}%") |
            models.Visitor.email.ilike(f"%{search}%")
        )
    query = order_query(models.Visitor, query, sort_by, sort_order)
    visitors = query.all()
    return templates.TemplateResponse("visitor/index.html", {
        "request": request,
        "visitors": visitors,
        "sort_by": sort_by,
        "sort_order": sort_order})

@app.get("/visitors/{visitor_id}", response_model=schemas.Visitor)
def read_visitor(visitor_id: int, request: Request, db: Session = Depends(get_db)):
    db_visitor = db.query(models.Visitor).filter(models.Visitor.id == visitor_id).first()
    if db_visitor is None:
        raise HTTPException(status_code=404, detail="Visitor not found")
    events = db.query(models.Event).join(models.Registration).filter(models.Registration.visitor_id == visitor_id).all()
    return templates.TemplateResponse("visitor/view.html", {
        "request": request,
        "visitor": db_visitor,
        "events": events,
        "build_url_with_query": build_url_with_query
    })
@app.get("/visitors/create/", response_class=HTMLResponse, description="Страница создания посетителя")
def create_visitor_form(request: Request):
    return templates.TemplateResponse("visitor/create.html", {
        "request": request,
    })
@app.get("/visitors/{visitor_id}/update/", response_class=HTMLResponse)
def update_visitor_form(visitor_id: int, request: Request, db: Session = Depends(get_db)):
    db_visitor = db.query(models.Visitor).filter(models.Visitor.id == visitor_id).first()
    if db_visitor is None:
        raise HTTPException(status_code=404, detail="Visitor not found")
    return templates.TemplateResponse("visitor/update.html", {
        "request": request,
        "visitor": db_visitor,
    })
@app.post("/visitors/create/", response_model=VisitorBase, description="Создать нового посетителя")
def create_visitor(
    first_name: str = Form(...),
    last_name: str = Form(...),
    phone: str = Form(...),
    email: Optional[EmailStr] = Form(None),
    db: Session = Depends(get_db)
):
    visitor_data = schemas.VisitorCreate(
        first_name=first_name,
        last_name=last_name,
        phone=phone,
        email=email,
    )
    db_visitor = models.Visitor(**visitor_data.dict())
    db.add(db_visitor)
    db.commit()
    db.refresh(db_visitor)
    return RedirectResponse(url=f"/visitors/{db_visitor.id}", status_code=303)
@app.post("/visitors/{visitor_id}/update/", response_model=VisitorBase, description="Обновить посетителя")
def update_visitor(
    visitor_id: int,
    first_name: str = Form(...),
    last_name: str = Form(...),
    phone: str = Form(...),
    email: Optional[EmailStr] = Form(None),
    db: Session = Depends(get_db)
):
    db_visitor = db.query(models.Visitor).filter(models.Visitor.id == visitor_id).first()
    if db_visitor is None:
        raise HTTPException(status_code=404, detail="Visitor not found")
    visitor = schemas.VisitorCreate(
        first_name=first_name,
        last_name=last_name,
        phone=phone,
        email=email,
    )
    for key, value in visitor.dict().items():
        setattr(db_visitor, key, value)
    db.commit()
    db.refresh(db_visitor)
    return RedirectResponse(url=f"/visitors/{db_visitor.id}", status_code=303)
@app.get("/visitors/{visitor_id}/delete/", response_model=None)
def delete_visitor(visitor_id: int, db: Session = Depends(get_db)):
    visitor = db.query(models.Visitor).filter(models.Visitor.id == visitor_id).first()
    if not visitor:
        raise HTTPException(status_code=404, detail="Visitor not found")

    db.delete(visitor)
    db.commit()

    return RedirectResponse(url="/visitors/", status_code=303)
@app.get("/registrations/", response_class=HTMLResponse)
def get_registrations(
        request: Request,
        db: Session = Depends(get_db),
        event_id = Query(None),
        visitor_id = Query(None),
        sort_by: str = Query(None),
        sort_order: int = Query(None),
        status: str = Query(None),
    ):
    if not (event_id == "" or event_id is None or event_id.isdigit()):
        raise HTTPException(status_code=400, detail=f"Invalid event id")
    if not (visitor_id=="" or visitor_id is None or visitor_id.isdigit()):
        raise HTTPException(status_code=400, detail="Invalid visitor id")
    query = db.query(models.Registration)
    events = {}
    visitors = {}
    for registration in query.all():
        events.setdefault(registration.event_id, registration.event.title)
        visitors.setdefault(
            registration.visitor_id,
            f"{registration.visitor.first_name} {registration.visitor.last_name}"
        )
    if event_id:
        query = query.filter(models.Registration.event_id == event_id)
    if visitor_id:
        query = query.filter(models.Registration.visitor_id == visitor_id)
    if status:
        query = query.filter(models.Event.status == status)
    query = order_query(models.Registration, query, sort_by, sort_order)
    registrations = query.all()
    return templates.TemplateResponse("registration/index.html", {
        "request": request,
        "registrations": registrations,
        "sort_by": sort_by,
        "sort_order": sort_order,
        "statuses": schemas.REGISTRATION_STATUSES,
        "status": status,
        "event_id": event_id,
        "events": events,
        "visitors": visitors,
        "visitor_id": visitor_id
    })

@app.get("/registrations/create/", response_class=HTMLResponse, description="Регистрация посетителя")
def create_registration_form(request: Request, db: Session = Depends(get_db)):
    events = db.query(models.Event).all()
    visitors = db.query(models.Visitor).all()
    return templates.TemplateResponse("registration/create.html", {
        "request": request,
        "events": events,
        "visitors": visitors,
    })
@app.get("/registrations/{registration_id}/update/", response_class=HTMLResponse)
def update_registration_form(registration_id: int, request: Request, db: Session = Depends(get_db)):
    db_registration = db.query(models.Registration).filter(models.Registration.id == registration_id).first()
    if db_registration is None:
        raise HTTPException(status_code=404, detail="Registration not found")
    return templates.TemplateResponse("registration/update.html", {
        "request": request,
        "registration": db_registration,
    })
@app.post("/registrations/create/", response_model=RegistrationBase, description="Регистрация посетителя")
def create_registration(
    event_id: int = Form(...),
    visitor_id: int = Form(...),
    db: Session = Depends(get_db)
):
    db_visitor = db.query(models.Visitor).filter(models.Visitor.id == visitor_id).first()
    if db_visitor is None:
        raise HTTPException(status_code=404, detail="Visitor not found")
    db_event = db.query(models.Event).filter(models.Event.id == event_id).first()
    if db_event is None:
        raise HTTPException(status_code=404, detail="Event not found")
    price = db_event.price
    status = "unpaid"
    if not price:
        status = "paid"
    registration_data = schemas.RegistrationCreate(
        visitor_id=visitor_id,
        event_id=event_id,
        price=db_event.price,
        status=status
    )
    db_registration = models.Registration(**registration_data.dict())
    db.add(db_registration)
    db.commit()
    db.refresh(db_registration)
    return RedirectResponse(url=f"/registrations/", status_code=303)
@app.post("/registrations/{registration_id}/update/", response_model=RegistrationBase, description="Обновить регистрацию")
def update_registration(
    registration_id: int,
    billed_amount: Optional[str] = Form(None),
    refund_amount: Optional[str] = Form(None),
    db: Session = Depends(get_db)
):
    if not (billed_amount == "" or billed_amount is None or billed_amount.isdigit()):
        raise HTTPException(status_code=400, detail=f"Invalid billed amount")
    if billed_amount == "":
        billed_amount = None
    else:
        billed_amount = int(billed_amount if billed_amount else 0)
    if not (refund_amount == "" or refund_amount is None or refund_amount.isdigit()):
        raise HTTPException(status_code=400, detail=f"Invalid refund amount")
    if refund_amount == "":
        refund_amount = None
    else:
        refund_amount = int(refund_amount if refund_amount else 0)
    db_registration = db.query(models.Registration).filter(models.Registration.id == registration_id).first()
    if db_registration is None:
        raise HTTPException(status_code=404, detail="Registration not found")
    price = db_registration.price
    if billed_amount is not None and billed_amount > 0 and billed_amount == price:
        db_registration.status = "paid"
        db_registration.billed_amount = billed_amount
        db_registration.billed_at = datetime.now()
    if refund_amount is not None and refund_amount > 0:
        db_registration.status = "refunded"
        db_registration.refund_amount = refund_amount
        db_registration.refunded_at = datetime.now()
    db.commit()
    db.refresh(db_registration)
    return RedirectResponse(url=f"/registrations/", status_code=303)
@app.get("/registrations/{registration_id}/delete/", response_model=None)
def delete_registration(registration_id: int, db: Session = Depends(get_db)):
    registration = db.query(models.Registration).filter(models.Registration.id == registration_id).first()
    if not registration:
        raise HTTPException(status_code=404, detail="Registration not found")

    db.delete(registration)
    db.commit()

    return RedirectResponse(url="/registrations/", status_code=303)