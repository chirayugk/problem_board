from sqlalchemy import (
    Column,
    Integer,
    String,
    Text,
    DateTime,
    ForeignKey,
    Boolean
)

from sqlalchemy.orm import relationship

from datetime import datetime

from app.database import Base


class Problem(Base):

    __tablename__ = "problems"

    id = Column(Integer, primary_key=True, index=True)

    title = Column(String, nullable=False, index=True)

    description = Column(Text, nullable=False)

    created_at = Column(
        DateTime,
        default=datetime.utcnow,
        index=True
    )

    upvotes = Column(Integer, default=0, index=True)

    tag = Column(String, nullable=True, index=True)

    status = Column(String, default="open")

    view_count = Column(Integer, default=0)

    is_pinned = Column(Boolean, default=False)

    is_flagged = Column(Boolean, default=False)

    replies = relationship(
        "Reply",
        back_populates="problem",
        cascade="all, delete-orphan"
    )


class Reply(Base):

    __tablename__ = "replies"

    id = Column(Integer, primary_key=True)

    content = Column(Text, nullable=False)

    created_at = Column(
        DateTime,
        default=datetime.utcnow,
        index=True
    )

    helpful_votes = Column(Integer, default=0)

    problem_id = Column(
        Integer,
        ForeignKey("problems.id"),
        index=True
    )

    problem = relationship(
        "Problem",
        back_populates="replies"
    )