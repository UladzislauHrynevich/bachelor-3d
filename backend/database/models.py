from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import DateTime, String, func, ForeignKey, BigInteger
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.database.database import Base

class Project(Base):
    __tablename__ = "projects"
    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid4
    )
    status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="created"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now()
    )
    images:Mapped[list["ProjectImage"]] = relationship(
        back_populates="project"
    )

class ProjectImage(Base):
    __tablename__ = "images"
    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid4
    )
    project_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("projects.id"),
        nullable=False
    )
    original_name: Mapped[str] = mapped_column(
        String(255),
        nullable=False
    )
    storage_path:Mapped[str] = mapped_column(
        String(),
        nullable=False
    )
    size_bytes:Mapped[int] = mapped_column(
        BigInteger,
        nullable=False

    )
    created_at:Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now()
    )
    project: Mapped["Project"] = relationship(
    back_populates="images"
)
