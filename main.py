from database import Base, engine, Session
from fastapi import FastAPI, Request, Header, Depends, Form, HTTPException, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from typing import Optional
from fastapi.staticfiles import StaticFiles
from tables import Task, DailyTask
from apscheduler.schedulers.background import BackgroundScheduler
import logging
from starlette.middleware.sessions import SessionMiddleware
from dotenv import load_dotenv
import os

load_dotenv()
Base.metadata.create_all(engine)

#Secrets
SECRET_KEY = os.environ.get("SECRET_KEY")
username_login = os.environ.get("username")
password_login  = os.environ.get("password")

app = FastAPI()
app.add_middleware(SessionMiddleware, secret_key=SECRET_KEY) #add max_age = ... (seconds) to set session expiry time.

templates = Jinja2Templates(directory="templates")

#CSS connection when fastapi involved
app.mount("/static", StaticFiles(directory="static"), name="static")    
app.mount("/images", StaticFiles(directory="images"), name="images")

def authenticate_user(username: str, password: str):  
    #This project is designed to have only 1 user (my friend), so this is sufficient.
    if username == username_login and password == password_login:
        return {"username": username}
    return None

def get_db():
    db = Session()
    try:
        yield db
    finally:
        db.close()

@app.get("/index", response_class=HTMLResponse)
def todo(request: Request, hx_request: Optional[str] = Header(None)):   
    context = {"request": request}
    if hx_request:
        return templates.TemplateResponse("table.html", context)
    return templates.TemplateResponse("index.html", context)

@app.get("/", response_class=HTMLResponse)
def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})
    
@app.post("/login") 
def login(request: Request, username: str = Form(...), password: str = Form(...)):
    user = authenticate_user(username, password)
    if not user:
        return templates.TemplateResponse("index.html", {"request": request, "error": "Invalid credentials"})
    
    #Set session flag if login is successful
    request.session["user"] = user["username"]
    return RedirectResponse(url="/main", status_code=303)

def get_current_user(request: Request): 
    user = request.session.get("user")
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authorized to access main")
    return user

@app.get("/main", response_class=HTMLResponse)  
def main(request: Request, current_user: str = Depends(get_current_user)):
    return templates.TemplateResponse("main.html", {"request": request, "user": current_user})

def get_dailies_access(request: Request):
    if request.session.get("user") or request.session.get("dailies_access"):
        return True
    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authorized to access dailies")

@app.post("/unlock-dailies")
def unlock_dailies(request: Request):
    request.session["dailies_access"] = True
    return RedirectResponse(url="/dailies", status_code=303)

@app.get("/dailies", response_class=HTMLResponse)
def dailies(request: Request, access_granted: bool = Depends(get_dailies_access)):
    return templates.TemplateResponse("daily.html", {"request": request})

@app.post("/dailies", response_class=RedirectResponse)
def dailies_page():
    return RedirectResponse(url="/dailies", status_code=302)

#Load table.html with HTMX
@app.get("/update-table", response_class=HTMLResponse)      
def update_table(request: Request, db = Depends(get_db), search: str = ""):
    # Get tasks from the database (optionally filter based on search input)
    query = db.query(Task)
    if search:
        query = query.filter(Task.category.startswith(search))
    
    tasks = query.all()
    return templates.TemplateResponse("table.html", {"request": request, "tasks": tasks})

#Load daily_table.html with HTMX
@app.get("/update-daily", response_class=HTMLResponse)
def update_daily(request: Request, db = Depends(get_db)):
    tasks = db.query(DailyTask).all()
    return templates.TemplateResponse("daily_table.html", {"request": request, "tasks": tasks})

@app.get("/dailies", response_class=HTMLResponse)
def daily(request: Request):
    return templates.TemplateResponse("daily.html", {"request": request})

@app.post("/add-task", response_class=RedirectResponse)
def add_task(
    request: Request,
    category: str = Form(...),
    description: str = Form(...),
    priority: str = Form(...),
    due_date: str = Form(...),
    db = Depends(get_db)
    ):
    try:
        new_task = Task(
            category=category,
            description=description,
            priority=priority,
            due_date=due_date
        )
        db.add(new_task)
        db.commit()
        return RedirectResponse(url="/main", status_code=303)
        #return templates.TemplateResponse("main.html", {"request": request, "tasks": tasks})
    except Exception:
        db.rollback()
        return {"message": "Error adding task."}
    
@app.post("/update-task", response_class=RedirectResponse)
def update_task(
    request: Request,
    id: str=Form(...),
    category: str = Form(...),
    description: str = Form(...),
    priority: str = Form(...),
    due_date: str = Form(...),
    db = Depends(get_db)
):
    
    if id=="":
        return RedirectResponse(url="/main", status_code=303)
    id = int(id)
    task = db.query(Task).filter(Task.id == id).first()
    if  not task:
        return RedirectResponse(url="/main", status_code=303)
    if category != "":
        task.category = category
    if description != "":
        task.description = description
    if priority != "":
        task.priority = priority
    if due_date != "":
        task.due_date = due_date
    db.commit()
    return RedirectResponse(url="/main", status_code=303)
    
@app.post("/delete-task", response_class=RedirectResponse)
def delete_task(
    request: Request,
    id: str = Form(...),
    db = Depends(get_db)
    ):
    if id=="":
        return RedirectResponse(url="/main", status_code=303)
    id=int(id)
    task = db.query(Task).filter(Task.id == id).first()
    if not task:
        return RedirectResponse(url="/main", status_code=303)
    
    # Delete the task and commit the change
    db.delete(task)
    db.commit()
    return RedirectResponse(url="/main", status_code=303)
    

@app.post("/daily-add-task", response_class=RedirectResponse)
def daily_add_task(
    request: Request,
    name: str = Form(...),
    description: str = Form(...),
    db = Depends(get_db)
    ):
    try:
        new_task = DailyTask(
            name=name,
            description=description,
            status="Incomplete"
        )
        db.add(new_task)
        db.commit()
        return RedirectResponse(url="/dailies", status_code=303)
    except Exception:
        db.rollback()
        return {"message": "Error adding task."}

@app.post("/daily-update-task", response_class=RedirectResponse)
def daily_update_task(   
    request: Request,
    id: str=Form(...),
    name: str=Form(...),
    description: str = Form(...),
    db = Depends(get_db)
):
    if id =="":
        return RedirectResponse(url="/dailies", status_code=303)
    id =int(id)
    task = db.query(DailyTask).filter(DailyTask.id == id).first()
    if not task:
        return RedirectResponse(url="/dailies", status_code=303)
    if name != "":
        task.name = name
    if description != "":
        task.description = description
    db.commit()
    return RedirectResponse(url="/dailies", status_code=303)

@app.post("/daily-delete-task", response_class=RedirectResponse)
def daily_delete_task(
    request: Request,
    id: str = Form(...),
    db = Depends(get_db)
    ):
    if id=="":
        return RedirectResponse(url="/dailies", status_code=303)
    id = int(id)
    task = db.query(DailyTask).filter(DailyTask.id == id).first()
    if not task:
        return RedirectResponse(url="/dailies", status_code=303)
    
    # Delete the task and commit the change
    db.delete(task)
    db.commit()
    return RedirectResponse(url="/dailies", status_code=303)

@app.post("/daily-complete-task", response_class=HTMLResponse)
def daily_complete_task(
    request: Request,
    id: str = Form(...),
    db = Depends(get_db)
    ):
    if id=="":
        return RedirectResponse(url="/dailies", status_code=303)
    id = int(id)
    task = db.query(DailyTask).filter(DailyTask.id == id).first()
    if not task:
        return RedirectResponse(url="/dailies", status_code=303)
    task.status="Complete"
    db.commit()
    return RedirectResponse(url="/dailies", status_code=303)

# Function to reset daily tasks
def reset_daily_tasks():
    db = Session() 
    try:
        # For example: Update all tasks marked complete to incomplete. updated = number of rows that are updated
        updated = db.query(DailyTask).filter(DailyTask.status == "Complete").update({DailyTask.status: "Incomplete"})
        db.commit()
        logging.info(f"Reset {updated} daily tasks at midnight.")
    except Exception as e:
        db.rollback()
        logging.error("Error resetting daily tasks: %s", e)
    finally:
        db.close()

#Scheduler for automatic task restarting at midnight for daily tasks
scheduler = BackgroundScheduler()
scheduler.add_job(reset_daily_tasks, 'cron', hour=0, minute=0)
scheduler.start()

#Shutdown the scheduler when FastAPI shuts down
@app.on_event("shutdown")
def shutdown_event():
    scheduler.shutdown()

#Get fraction of completed dailies
@app.get("/daily_fraction", response_class=HTMLResponse)
def daily_fraction(request: Request, db = Depends(get_db)):
    total_tasks = db.query(DailyTask).count()
    if total_tasks == 0:
        fraction = "0/0"
    else:
        complete_tasks = db.query(DailyTask).filter(DailyTask.status == "Complete").count()
        fraction = f"{complete_tasks}/{total_tasks}"
    return templates.TemplateResponse("daily_fraction.html", {"request": request, "fraction": fraction})

#Reset daily rasks manually
@app.post("/daily-reset-task", response_class=RedirectResponse)  
def manual_reset_daily_tasks(
    request: Request
    ):
    db = Session()
    try:
        db.query(DailyTask).update({DailyTask.status: "Incomplete"}, synchronize_session=False)
        db.commit()
    except Exception as e:
        db.rollback()
        raise e
    finally:
        db.close()
        return RedirectResponse(url="/dailies", status_code=303)

