import sqlalchemy.orm as orm
import sqlalchemy as sa

# Load our models
import btrfs_recon.persistence  # type: ignore


engine = sa.create_engine('postgresql+psycopg://btrfs_recon:btrfs_recon@127.0.0.1:5436/btrfs_recon')
session = orm.sessionmaker(engine)
