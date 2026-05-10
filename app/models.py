from sqlalchemy import (
    Column,
    Integer,
    String,
    Text,
    DateTime,
    ForeignKey
)

from sqlalchemy.orm import relationship

from datetime import datetime

from app.database import Base


class Problem(Base):

    __tablename__ = "problems"

    id = Column(Integer, primary_key=True, index=True)

    title = Column(String, nullable=False)

    description = Column(Text, nullable=False)

    created_at = Column(
        DateTime,
        default=datetime.utcnow
    )

    upvotes = Column(Integer, default=0)

    tag = Column(String, nullable=True)

    replies = relationship(
        "Reply",
        back_populates="problem"
    )


class Reply(Base):

    __tablename__ = "replies"

    id = Column(Integer, primary_key=True)

    content = Column(Text, nullable=False)

    created_at = Column(
        DateTime,
        default=datetime.utcnow
    )

    problem_id = Column(
        Integer,
        ForeignKey("problems.id")
    )

    problem = relationship(
        "Problem",
        back_populates="replies"
    )