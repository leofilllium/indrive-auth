from fastapi import FastAPI, Depends, HTTPException, status, Request, Form
from fastapi.security import HTTPBasic, HTTPBasicCredentials
import secrets
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
import os

import models
import schemas
from database import engine, SessionLocal

models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="Auth & Admin Service")

# Create templates directory if it doesn't exist
os.makedirs("templates", exist_ok=True)
templates = Jinja2Templates(directory="templates")

security = HTTPBasic()

def authenticate_admin(credentials: HTTPBasicCredentials = Depends(security)):
    is_correct_username = secrets.compare_digest(credentials.username, "admin")
    is_correct_password = secrets.compare_digest(credentials.password, "kS2dcKMd134")
    if not (is_correct_username and is_correct_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Basic"},
        )
    return credentials.username

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.post("/auth/login")
def login(request: schemas.AuthRequest, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.id == request.id).first()
    
    # Check if user exists
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # First time login process
    if user.device_id is None or user.device_id == "":
        user.device_id = request.device_id
        db.commit()
        db.refresh(user)
        return {
            "status": "success", 
            "message": "First login successful. Device ID registered.", 
            "id": user.id, 
            "device_id": user.device_id
        }
    
    # Subsequent login process
    if user.device_id == request.device_id:
        return {
            "status": "success", 
            "message": "Login successful", 
            "id": user.id, 
            "device_id": user.device_id
        }
    else:
        raise HTTPException(status_code=401, detail="Unauthorized: Device ID mismatch")

# Admin APIs (JSON)
@app.get("/api/admin/users", response_model=list[schemas.UserResponse], dependencies=[Depends(authenticate_admin)])
def get_users(db: Session = Depends(get_db)):
    return db.query(models.User).all()

@app.post("/api/admin/users", response_model=schemas.UserResponse, dependencies=[Depends(authenticate_admin)])
def create_user(user: schemas.UserCreate, db: Session = Depends(get_db)):
    db_user = db.query(models.User).filter(models.User.id == user.id).first()
    if db_user:
        raise HTTPException(status_code=400, detail="User already exists")
    new_user = models.User(id=user.id, device_id=user.device_id)
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user

# Admin UI Routes
@app.get("/admin", response_class=HTMLResponse)
def view_admin_panel(request: Request, db: Session = Depends(get_db), auth: str = Depends(authenticate_admin)):
    users = db.query(models.User).all()
    return templates.TemplateResponse("admin.html", {"request": request, "users": users})

@app.post("/admin/users/add", dependencies=[Depends(authenticate_admin)])
def form_create_user(
    request: Request,
    id: str = Form(...),
    device_id: str = Form(None),
    db: Session = Depends(get_db)
):
    db_user = db.query(models.User).filter(models.User.id == id).first()
    if not db_user:
        new_user = models.User(id=id, device_id=device_id if device_id else None)
        db.add(new_user)
        db.commit()
    return RedirectResponse(url="/admin", status_code=status.HTTP_303_SEE_OTHER)

@app.post("/admin/users/delete", dependencies=[Depends(authenticate_admin)])
def form_delete_user(
    request: Request,
    id: str = Form(...),
    db: Session = Depends(get_db)
):
    db_user = db.query(models.User).filter(models.User.id == id).first()
    if db_user:
        db.delete(db_user)
        db.commit()
    return RedirectResponse(url="/admin", status_code=status.HTTP_303_SEE_OTHER)

@app.post("/admin/users/clear_device", dependencies=[Depends(authenticate_admin)])
def form_clear_device(
    request: Request,
    id: str = Form(...),
    db: Session = Depends(get_db)
):
    db_user = db.query(models.User).filter(models.User.id == id).first()
    if db_user:
        db_user.device_id = None
        db.commit()
    return RedirectResponse(url="/admin", status_code=status.HTTP_303_SEE_OTHER)

@app.post("/admin/users/edit", dependencies=[Depends(authenticate_admin)])
def form_edit_user(
    request: Request,
    old_id: str = Form(...),
    new_id: str = Form(...),
    new_device_id: str = Form(None),
    db: Session = Depends(get_db)
):
    db_user = db.query(models.User).filter(models.User.id == old_id).first()
    if db_user:
        # If ID is changing, check if new ID already exists
        if old_id != new_id:
            existing_user = db.query(models.User).filter(models.User.id == new_id).first()
            if existing_user:
                # In a real app, you'd show an error message. For now, just skip.
                return RedirectResponse(url="/admin", status_code=status.HTTP_303_SEE_OTHER)
        
        db_user.id = new_id
        db_user.device_id = new_device_id if new_device_id else None
        db.commit()
    return RedirectResponse(url="/admin", status_code=status.HTTP_303_SEE_OTHER)
