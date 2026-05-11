from fastapi import (
    FastAPI,
    Request,
    Form,
    Depends,
    Query
)

from fastapi.responses import RedirectResponse

from fastapi.staticfiles import StaticFiles

from fastapi.templating import Jinja2Templates

from sqlalchemy.orm import Session

from sqlalchemy import or_, and_

from app.database import (
    engine,
    SessionLocal
)

from app import models

from app.models import (
    Problem,
    Reply
)

import re
import time
from functools import wraps
from collections import defaultdict

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

# Rate limiting tracker
rate_limit_tracker = defaultdict(list)

# Bad words filter
BAD_WORDS = [
    "spam", "abuse", "hate", "violence"
]

def check_rate_limit(
    ip: str,
    max_requests: int = 10,
    window_seconds: int = 60
) -> bool:
    
    current_time = time.time()
    
    rate_limit_tracker[ip] = [
        t for t in rate_limit_tracker[ip]
        if current_time - t < window_seconds
    ]
    
    if len(rate_limit_tracker[ip]) >= max_requests:
        return False
    
    rate_limit_tracker[ip].append(current_time)
    return True


def filter_bad_words(text: str) -> str:
    
    for word in BAD_WORDS:
        text = re.sub(
            f"\\b{word}\\b",
            "*" * len(word),
            text,
            flags=re.IGNORECASE
        )
    
    return text


def get_db():

    db = SessionLocal()

    try:
        yield db

    finally:
        db.close()


@app.get("/")
def home(
    request: Request,
    sort: str = "newest",
    search: str = "",
    tag_filter: str = "",
    page: int = 1,
    db: Session = Depends(get_db)
):
    
    ITEMS_PER_PAGE = 5
    
    query = db.query(Problem).filter(
        Problem.is_flagged == False
    )
    
    if search:
        search_term = f"%{search}%"
        query = query.filter(
            or_(
                Problem.title.ilike(search_term),
                Problem.description.ilike(search_term)
            )
        )
    
    if tag_filter:
        query = query.filter(
            Problem.tag == tag_filter
        )
    
    if sort == "upvotes":
        problems_list = query.order_by(
            Problem.upvotes.desc()
        ).all()
    
    elif sort == "replies":
        problems_list = sorted(
            query.all(),
            key=lambda p: len(p.replies),
            reverse=True
        )
    
    else:
        problems_list = query.order_by(
            Problem.id.desc()
        ).all()
    
    total_problems = len(problems_list)
    total_pages = (
        total_problems + ITEMS_PER_PAGE - 1
    ) // ITEMS_PER_PAGE
    
    start = (page - 1) * ITEMS_PER_PAGE
    end = start + ITEMS_PER_PAGE
    problems = problems_list[start:end]
    
    all_tags = db.query(
        Problem.tag
    ).distinct().filter(
        Problem.tag.isnot(None)
    ).all()
    tags = [t[0] for t in all_tags]
    
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={
            "problems": problems,
            "current_sort": sort,
            "search": search,
            "tag_filter": tag_filter,
            "page": page,
            "total_pages": total_pages,
            "tags": tags
        }
    )


@app.post("/add-problem")
def add_problem(
    request: Request,
    title: str = Form(...),
    description: str = Form(...),
    tag: str = Form(...),
    db: Session = Depends(get_db)
):
    
    client_ip = request.client.host
    
    if not check_rate_limit(client_ip, max_requests=5):
        return RedirectResponse(
            "/?error=rate_limit",
            status_code=303
        )
    
    description = filter_bad_words(description)
    title = filter_bad_words(title)
    
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
    reply_sort: str = "newest",
    db: Session = Depends(get_db)
):
    
    problem = db.query(Problem).filter(
        Problem.id == problem_id
    ).first()
    
    if problem:
        problem.view_count += 1
        db.commit()
    
    if reply_sort == "helpful":
        problem.replies = sorted(
            problem.replies,
            key=lambda r: r.helpful_votes,
            reverse=True
        )
    else:
        problem.replies = sorted(
            problem.replies,
            key=lambda r: r.created_at,
            reverse=True
        )
    
    return templates.TemplateResponse(
        request=request,
        name="problem.html",
        context={
            "problem": problem,
            "reply_sort": reply_sort
        }
    )


@app.post("/problem/{problem_id}/reply")
def add_reply(
    request: Request,
    problem_id: int,
    content: str = Form(...),
    db: Session = Depends(get_db)
):
    
    client_ip = request.client.host
    
    if not check_rate_limit(
        client_ip,
        max_requests=20
    ):
        return RedirectResponse(
            f"/problem/{problem_id}?error=rate_limit",
            status_code=303
        )
    
    content = filter_bad_words(content)
    
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
    sort: str = "newest",
    db: Session = Depends(get_db)
):
    
    problem = db.query(Problem).filter(
        Problem.id == problem_id
    ).first()
    
    if problem:
        problem.upvotes += 1
        db.commit()
    
    return RedirectResponse(
        f"/?sort={sort}",
        status_code=303
    )


@app.post("/problem/{problem_id}/delete")
def delete_problem(
    problem_id: int,
    db: Session = Depends(get_db)
):
    
    problem = db.query(Problem).filter(
        Problem.id == problem_id
    ).first()
    
    if problem:
        db.delete(problem)
        db.commit()
    
    return RedirectResponse(
        "/",
        status_code=303
    )


@app.post("/problem/{problem_id}/edit")
def edit_problem(
    problem_id: int,
    title: str = Form(...),
    description: str = Form(...),
    tag: str = Form(...),
    db: Session = Depends(get_db)
):
    
    description = filter_bad_words(description)
    title = filter_bad_words(title)
    
    problem = db.query(Problem).filter(
        Problem.id == problem_id
    ).first()
    
    if problem:
        problem.title = title
        problem.description = description
        problem.tag = tag
        db.commit()
    
    return RedirectResponse(
        f"/problem/{problem_id}",
        status_code=303
    )


@app.post("/problem/{problem_id}/status")
def update_status(
    problem_id: int,
    status: str = Form(...),
    db: Session = Depends(get_db)
):
    
    problem = db.query(Problem).filter(
        Problem.id == problem_id
    ).first()
    
    if problem and status in ["open", "closed", "resolved"]:
        problem.status = status
        db.commit()
    
    return RedirectResponse(
        f"/problem/{problem_id}",
        status_code=303
    )


@app.post("/reply/{reply_id}/helpful")
def reply_helpful(
    reply_id: int,
    problem_id: int,
    db: Session = Depends(get_db)
):
    
    reply = db.query(Reply).filter(
        Reply.id == reply_id
    ).first()
    
    if reply:
        reply.helpful_votes += 1
        db.commit()
    
    return RedirectResponse(
        f"/problem/{problem_id}",
        status_code=303
    )


@app.post("/problem/{problem_id}/flag")
def flag_problem(
    problem_id: int,
    db: Session = Depends(get_db)
):
    
    problem = db.query(Problem).filter(
        Problem.id == problem_id
    ).first()
    
    if problem:
        problem.is_flagged = True
        db.commit()
    
    return RedirectResponse(
        "/",
        status_code=303
    )


@app.post("/problem/{problem_id}/pin")
def pin_problem(
    problem_id: int,
    db: Session = Depends(get_db)
):
    
    problem = db.query(Problem).filter(
        Problem.id == problem_id
    ).first()
    
    if problem:
        problem.is_pinned = not problem.is_pinned
        db.commit()
    
    return RedirectResponse(
        f"/problem/{problem_id}",
        status_code=303
    )


@app.get("/admin")
def admin_panel(
    request: Request,
    db: Session = Depends(get_db)
):
    
    flagged_problems = db.query(Problem).filter(
        Problem.is_flagged == True
    ).all()
    
    all_problems = db.query(Problem).all()
    
    total_problems = len(all_problems)
    total_replies = db.query(Reply).count()
    
    top_tags = {}
    for problem in all_problems:
        if problem.tag:
            top_tags[problem.tag] = (
                top_tags.get(problem.tag, 0) + 1
            )
    
    top_tags = sorted(
        top_tags.items(),
        key=lambda x: x[1],
        reverse=True
    )[:10]
    
    return templates.TemplateResponse(
        request=request,
        name="admin.html",
        context={
            "flagged_problems": flagged_problems,
            "total_problems": total_problems,
            "total_replies": total_replies,
            "top_tags": top_tags
        }
    )


@app.get("/analytics")
def analytics(
    request: Request,
    db: Session = Depends(get_db)
):
    
    all_problems = db.query(Problem).all()
    
    total_problems = len(all_problems)
    total_replies = db.query(Reply).count()
    
    trending_problems = sorted(
        all_problems,
        key=lambda p: p.upvotes,
        reverse=True
    )[:10]
    
    most_viewed = sorted(
        all_problems,
        key=lambda p: p.view_count,
        reverse=True
    )[:10]
    
    top_tags = {}
    for problem in all_problems:
        if problem.tag:
            top_tags[problem.tag] = (
                top_tags.get(problem.tag, 0) + 1
            )
    
    top_tags = sorted(
        top_tags.items(),
        key=lambda x: x[1],
        reverse=True
    )[:10]
    
    return templates.TemplateResponse(
        request=request,
        name="analytics.html",
        context={
            "total_problems": total_problems,
            "total_replies": total_replies,
            "trending_problems": trending_problems,
            "most_viewed": most_viewed,
            "top_tags": top_tags
        }
    )
