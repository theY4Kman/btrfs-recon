from __future__ import annotations

import uuid
from pathlib import Path
from typing import BinaryIO, TYPE_CHECKING

import sqlalchemy.orm as orm
import sqlalchemy as sa
import sqlalchemy.dialects.postgresql as pg

from .base import BaseModel

if TYPE_CHECKING:
    from .physical import Device

__all__ = ['Filesystem']


class FilesystemDevice(BaseModel):
    filesystem_id: orm.Mapped[int] = sa.Column(sa.ForeignKey('filesystem.id'), primary_key=True)
    device_id: orm.Mapped[int] = sa.Column(sa.ForeignKey('device.id'), primary_key=True)


class Filesystem(BaseModel):
    id = sa.Column(sa.Integer, primary_key=True, autoincrement=True)
    fsid: orm.Mapped[uuid.UUID] = sa.Column(pg.UUID)
    label = sa.Column(sa.String, unique=True)

    devices: orm.Mapped['Device'] = orm.relationship(
        'Device', secondary=FilesystemDevice.__table__, uselist=True, lazy='selectin'
    )

    @classmethod
    def from_devices(cls, *paths: Path | str, **attrs) -> 'Filesystem':
        from .physical import Device
        return cls(
            devices=[Device(path=str(Path(path).resolve())) for path in paths],
            **attrs,
        )

    def open_all(
        self, *, write: bool = False, buffering: int = -1
    ) -> list[BinaryIO]:
        """Open file handles to all device images"""
        return [
            device.open(write=write, buffering=buffering)
            for device in self.devices
        ]
