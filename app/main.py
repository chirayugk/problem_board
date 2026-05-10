from fastapi import (
    FastAPI,
    Request,
    Form,
    Depends
)

from fastapi.responses import RedirectResponse

from fastapi.staticfiles import StaticFiles

from fastapi.templating import Jinja2Templates

from sqlalchemy.orm import Session

from app.database import (
    engine,
    SessionLocal
)

from app import models

from app.models import (
    Problem,
    Reply
)

models.Base.metadata.create_all(bind=engine)

app = FastAPI()

app.mount(
    "/static",
    StaticFiles(directory="app/static"),
    name="static"
)

templates = Jinja2Templates(
    directory="app/templates"
)


def get_db():

    db = SessionLocal()

    try:
        yield db

    finally:
        db.close()


@app.get("/")
def home(
    request: Request,
    db: Session = Depends(get_db)
):

    problems = db.query(Problem).order_by(
        Problem.id.desc()
    ).all()

    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={
            "problems": problems
        }
    )


@app.post("/add-problem")
def add_problem(

    title: str = Form(...),

    description: str = Form(...),

    tag: str = Form(...),

    db: Session = Depends(get_db)
):

    problem = Problem(
        title=title,
        description=description,
        tag=tag
    )

    db.add(problem)

    db.commit()

    return RedirectResponse(
        "/",
        status_code=303
    )


@app.get("/problem/{problem_id}")
def problem_page(

    request: Request,

    problem_id: int,

    db: Session = Depends(get_db)
):

    problem = db.query(Problem).filter(
        Problem.id == problem_id
    ).first()

    return templates.TemplateResponse(
        request=request,
        name="problem.html",
        context={
            "problem": problem
        }
    )


@app.post("/problem/{problem_id}/reply")
def add_reply(

    problem_id: int,

    content: str = Form(...),

    db: Session = Depends(get_db)
):

    reply = Reply(
        content=content,
        problem_id=problem_id
    )

    db.add(reply)

    db.commit()

    return RedirectResponse(
        f"/problem/{problem_id}",
        status_code=303
    )


@app.post("/upvote/{problem_id}")
def upvote_problem(

    problem_id: int,

    db: Session = Depends(get_db)
):

    problem = db.query(Problem).filter(
        Problem.id == problem_id
    ).first()

    problem.upvotes += 1

    db.commit()

    return RedirectResponse(
        "/",
        status_code=303
    )