from pathlib import Path

import sqlalchemy.orm as orm
import sqlalchemy as sa
import sqlalchemy.dialects.postgresql as pg

from .base import BaseModel

__all__ = ['Filesystem']


class FilesystemDevice(BaseModel):
    filesystem_id = sa.Column(sa.ForeignKey('filesystem.id'), primary_key=True)
    device_id = sa.Column(sa.ForeignKey('device.id'), primary_key=True)


class Filesystem(BaseModel):
    id = sa.Column(sa.Integer, primary_key=True, autoincrement=True)
    fsid = sa.Column(pg.UUID)
    label = sa.Column(sa.String)

    devices = orm.relationship('Device', secondary=FilesystemDevice.__table__)

    @classmethod
    def from_devices(cls, *paths: Path | str, **attrs) -> 'Filesystem':
        from .physical import Device
        return cls(
            devices=[Device(path=Path(path).resolve()) for path in paths]
            **attrs,
        )
