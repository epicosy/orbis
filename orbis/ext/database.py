import contextlib
from typing import Any, Callable, Dict, Union

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import inspect

from sqlalchemy import Column, Integer, String, Boolean, Float, ForeignKey
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


class TestOutcome(Base):
    __tablename__ = "test_outcome"

    id = Column('id', Integer, primary_key=True)
    instance_id = Column('instance_id', Integer, ForeignKey('instance.id'), nullable=False)
    co_id = Column('co_id', Integer, ForeignKey('compile_outcome.id'), nullable=False)
    instance = relationship("Instance", back_populates="test_outcome")
    compile_outcome = relationship("CompileOutcome", back_populates="test_outcome")
    name = Column('name', String, nullable=False)
    is_pov = Column('is_pov', Boolean, nullable=False)
    passed = Column('passed', Boolean, nullable=False)
    msg = Column('msg', String, nullable=True)
    error = Column('error', String, nullable=True)
    exit_status = Column('exit_status', Integer, nullable=False)
    sig = Column('sig', Integer, nullable=True)
    duration = Column('duration', Float, nullable=False)

    def get_clean_error(self):
        return self.error.strip().replace('\n', ' ') if self.error else ''

    def __str__(self):
        return f"{self.id} | {self.co_id} | {self.name} | {self.is_pov} | {self.msg} | {self.passed} | " \
               f" {self.get_clean_error()} | {self.exit_status} | {self.sig} | {self.duration}"

    def to_dict(self):
        return {'id': self.id, 'compile id': self.co_id, 'name': self.name, 'is pov': self.is_pov,
                'result': self.result, 'status': self.status, 'total': self.total, 'passed': self.passed,
                'failed': self.failed, 'error': self.get_clean_error(), 'exit status': self.exit_status,
                'signal': self.sig, 'duration': self.duration}


class CompileOutcome(Base):
    __tablename__ = "compile_outcome"

    id = Column('id', Integer, primary_key=True)
    instance_id = Column('instance_id', Integer, ForeignKey('instance.id'))
    instance = relationship("Instance", back_populates="compile_outcome")
    test_outcome = relationship("TestOutcome", back_populates="compile_outcome")
    error = Column('error', String, nullable=True)
    tag = Column('tag', String, nullable=False)
    exit_status = Column('exit_status', Integer)

    def __str__(self):
        clean_error = self.error.strip().replace('\n', ' ') if self.error else ''
        return f"{self.id} | {clean_error} | {self.tag} | {self.exit_status}"


class Instance(Base):
    __tablename__ = "instance"

    id = Column('id', Integer, primary_key=True)
    pid = Column('pid', String)
    path = Column('path', String)
    pointer = Column('pointer', Integer, nullable=True)
    test_outcome = relationship("TestOutcome", back_populates="instance")
    compile_outcome = relationship("CompileOutcome", back_populates="instance")

    def __str__(self):
        return f"{self.id} | {self.m_id} | {self.name} | {self.path} | {self.pointer}"


class Database:
    def __init__(self, dialect: str, username: str, password: str, host: str, port: int, database: str,
                 debug: bool = False):
        self.engine = create_engine(f"{dialect}://{username}:{password}@{host}:{port}/{database}", echo=debug)
        Base.metadata.create_all(bind=self.engine)

    def refresh(self, entity: Base):
        with Session(self.engine) as session, session.begin():
            session.refresh(entity)

        return entity

    def add(self, entity: Base):
        with Session(self.engine) as session, session.begin():
            session.add(entity)
            session.flush()
            session.refresh(entity)
            session.expunge_all()

            if hasattr(entity, 'id'):
                return entity.id

    def destroy(self):
        # metadata = MetaData(self.engine, reflect=True)
        with contextlib.closing(self.engine.connect()) as con:
            trans = con.begin()
            Base.metadata.drop_all(bind=self.engine)
            trans.commit()

    def delete(self, entity: Base, entity_id: Union[int, str]):
        with Session(self.engine) as session, session.begin():
            return session.query(entity).filter(entity.id == entity_id).delete(synchronize_session='evaluate')

    def has_table(self, name: str):
        inspector = inspect(self.engine)
        return inspector.reflect_table(name, None)

    def query(self, entity: Base, entity_id: Union[int, str] = None, load: str = None):
        with Session(self.engine) as session, session.begin():
            if load:
                query = session.query(entity).options(joinedload(load))
            else:
                query = session.query(entity)

            if entity_id and hasattr(entity, 'id'):
                query = query.filter(entity.id == entity_id).first()
            else:
                query = query.all()

            session.expunge_all()

            return query

    def query_attr(self, entity: Base, entity_id: int, attr: str):
        with Session(self.engine) as session, session.begin():
            if hasattr(entity, 'id') and hasattr(entity, attr):
                results = session.query(entity).filter(entity.id == entity_id).first()
                attr_result = getattr(results, attr)
                session.expunge_all()
                return attr_result

    def filter(self, entity: Base, filters: Dict[Any, Callable], distinct: Any = None):
        with Session(self.engine) as session, session.begin():
            query = session.query(entity)

            for attr, exp in filters.items():
                query = query.filter(exp(attr))
            if distinct:
                query = query.distinct(distinct)
            session.expunge_all()
            return query

    def count(self, entity: Base):
        with Session(self.engine) as session, session.begin():
            return session.query(entity).count()

    def update(self, entity: Base, entity_id: int, attr: str, value):
        with Session(self.engine) as session, session.begin():
            if hasattr(entity, 'id') and hasattr(entity, attr):
                session.query(entity).filter(entity.id == entity_id).update({attr: value})
            else:
                raise ValueError(f"Could not update {type(entity)} {attr} with value {value}")


def init(app):
    db_config = app.get_config('database')
    database = Database(dialect=db_config['dialect'], username=db_config['username'], password=db_config['password'],
                        host=db_config['host'], port=db_config['port'], database=db_config['name'],
                        debug=app.config.get('log.colorlog', 'database'))

    app.extend('db', database)


def load(app):
    app.hook.register('post_setup', init)
