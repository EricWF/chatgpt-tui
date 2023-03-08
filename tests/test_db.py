import random
from pathlib import Path

import pytest

from ai.database import (
    LATEST_VERSION,
    Connection,
    DBSchema,
    MessageSchema,
    MetaDataSchema,
    session,
)


@pytest.fixture(autouse=True)
def clear_session():
    yield
    session._db_path = None


@pytest.fixture
def empty_db_file(tmpdir):
    return Path(tmpdir / "db.json")


@pytest.fixture()
def db_file(empty_db_file):
    db_file = empty_db_file
    sess = session.use_database(db_file)
    id_ = random.random()
    api_key = random.random()
    metadata = MetaDataSchema.latest(id_=id_, api_key=api_key)
    sess.setup(metadata)
    return db_file


@pytest.fixture
def active_session(db_file):
    yield
    session._db_path = None


def test_initial_setup(empty_db_file):
    db_file = empty_db_file
    sess = session.use_database(db_file)
    assert not sess.is_setup

    id_ = random.random()
    api_key = random.random()
    expected = DBSchema(version=LATEST_VERSION, id_=id_, api_key=api_key, agents=[])

    metadata = MetaDataSchema.latest(id_=id_, api_key=api_key)
    sess.setup(metadata)

    assert sess.is_setup

    actual = DBSchema.parse_file(db_file)
    assert actual.dict() == expected.dict()


@pytest.mark.usefixtures("active_session")
def test_context_handler():
    sess = session()
    db_path = sess.db_path
    assert sess.is_setup
    num_agents = 5

    with sess as db:
        for i in range(num_agents):
            db.add(MessageSchema(role="system", content=i))
        expected = db.db.copy()
        db.commit()

    actual = DBSchema.parse_file(db_path)
    assert len(actual.agents) == num_agents
    assert actual.dict() == expected.dict()


@pytest.mark.usefixtures("active_session")
def test_data_not_saved_if_no_commit():
    sess = session()
    db_path = sess.db_path
    assert sess.is_setup

    with sess as db:
        db.add(MessageSchema(role="system", content="dne"))

    actual = DBSchema.parse_file(db_path)
    assert len(actual.agents) == 0


@pytest.mark.usefixtures("active_session")
def test_decorator():
    sess = session()
    db_path = sess.db_path
    num_agents = 5

    @sess
    def foo(bar, *, db):
        db.add(MessageSchema(role="system", content=bar))
        expected = db.db.copy()
        db.commit()
        return expected

    for i in range(num_agents):
        expected = foo(i)

    actual = DBSchema.parse_file(db_path)
    assert len(actual.agents) == num_agents
    assert actual.dict() == expected.dict()


def test_assert_connection():
    conn = Connection()

    with pytest.raises(AssertionError):
        conn.commit()

    with pytest.raises(AssertionError):
        conn.add("foo")

    with pytest.raises(AssertionError):
        conn.dne
