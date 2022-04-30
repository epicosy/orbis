import contextlib
import subprocess
from pathlib import Path
from typing import Any, Callable, Dict, Union

from cement import Handler
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import inspect

from sqlalchemy import Column, Integer, String, Boolean, Float, ForeignKey
from sqlalchemy.orm import declarative_base, relationship
from sqlalchemy_utils import create_database, database_exists

from orbis.core.interfaces import HandlersInterface, DatabaseInterface

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
                'passed': self.passed, 'error': self.get_clean_error(), 'exit_status': self.exit_status,
                'signal': self.sig, 'duration': self.duration}

    def jsonify(self):
        return {'id': self.id, 'name': self.name, 'is pov': self.is_pov, 'passed': self.passed,
                'error': self.get_clean_error(), 'exit_status': self.exit_status, 'signal': self.sig,
                'duration': self.duration}


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

    def jsonify(self):
        return {'id': self.id, 'error': self.error, 'tag': self.tag, 'exit_status': self.exit_status}


class Instance(Base):
    __tablename__ = "instance"

    id = Column('id', Integer, primary_key=True)
    pid = Column('project_id', String)
    sha = Column('sha', String)
    path = Column('path', String)
    pointer = Column('pointer', Integer, nullable=True)
    test_outcome = relationship("TestOutcome", back_populates="instance")
    compile_outcome = relationship("CompileOutcome", back_populates="instance")

    def to_dict(self):
        return {'id': self.id, 'pid': self.pid, 'sha': self.sha, 'path': self.path, 'pointer': self.pointer}

    def __str__(self):
        return f"{self.id} | {self.m_id} | {self.name} | {self.path} | {self.pointer}"


class InstanceHandler(DatabaseInterface, Handler):
    class Meta:
        label = 'instance'

    def delete(self, instance_id: int, destroy: bool = False):
        if destroy:
            instance: Instance = self.get(instance_id)
            instance_path = Path(instance.path)

            if instance_path.exists() and instance_path.is_dir():
                instance_path.rmdir()

        return self.app.db.delete(Instance, instance_id)

    def get(self, instance_id: int):
        return self.app.db.query(Instance, instance_id)

    def get_compile_outcome(self, instance_id: int):
        return self.app.db.query_attr(Instance, instance_id, 'compile_outcome')

    def get_test_outcome(self, instance_id: int):
        return self.app.db.query_attr(Instance, instance_id, 'test_outcome')

    def all(self):
        return self.app.db.query(Instance)


class Database:
    def __init__(self, dialect: str, username: str, password: str, host: str, port: int, database: str,
                 debug: bool = False):
        self.url = f"{dialect}://{username}:{password}@{host}:{port}/{database}"

        if not database_exists(self.url):
            create_database(self.url, encoding='utf8')

        self.engine = create_engine(self.url, echo=debug)
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


def exec_cmd(app, cmd: str, msg: str):
    with subprocess.Popen(args=cmd, shell=True, stdout=subprocess.PIPE,
                          stderr=subprocess.PIPE) as proc:
        app.log.info(msg)
        out = []
        for line in proc.stdout:
            decoded = line.decode()
            out.append(decoded)
            app.log.info(decoded)

        proc.wait(timeout=1)

        if proc.returncode and proc.returncode != 0:
            proc.kill()
            err = proc.stderr.read().decode()

            if err:
                app.log.error(err)
                exit(proc.returncode)

    return ''.join(out)


def start_psql_server(app):
    """
        Verifies if postgresql server is down and starts it.

        :param app: application object
    """
    # check postgresql server status
    output = exec_cmd(app, "/etc/init.d/postgresql status", msg="Checking postgresql server status")

    if 'down' in output:
        # start postgresql
        exec_cmd(app, "/etc/init.d/postgresql start", msg="Starting postgresql server")


def init(app):
    db_config = app.get_config('database')
    start_psql_server(app)

    # try except
    database = Database(dialect=db_config['dialect'], username=db_config['username'], password=db_config['password'],
                        host=db_config['host'], port=db_config['port'], database=db_config['name'],
                        debug=app.config.get('log.colorlog', 'database'))

    app.extend('db', database)


def load(app):
    app.hook.register('post_setup', init)
