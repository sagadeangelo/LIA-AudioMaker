"""Regression: inherited production settings must never reach the application engine."""
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys


def test_conftest_overrides_database_and_audio_before_app_import(tmp_path):
 production=tmp_path/'production.sqlite'
 with sqlite3.connect(production) as db:
  db.execute('CREATE TABLE protected(value TEXT)');db.execute("INSERT INTO protected VALUES ('keep')")
 original=production.read_bytes()
 env={**os.environ,'DATABASE_URL':'sqlite:///'+str(production),'DATA_DIR':str(tmp_path/'real-audio')}
 conftest=Path(__file__).with_name('conftest.py')
 script="""import os,runpy,json
runpy.run_path(CONFTEST)
from app import main as m
from sqlalchemy import text
with m.engine.begin() as c:
 c.execute(text("INSERT INTO projects VALUES ('isolation-proof','{}')"))
print(json.dumps({'url':str(m.engine.url),'data':str(m.DATA)}))
""".replace('CONFTEST',repr(str(conftest)))
 result=subprocess.run([sys.executable,'-c',script],env=env,text=True,capture_output=True,timeout=30,check=True)
 state=json.loads(result.stdout.strip().splitlines()[-1])
 assert str(production) not in state['url'] and state['url'].startswith('sqlite:///')
 assert str(tmp_path/'real-audio')!=state['data'] and not (tmp_path/'real-audio').exists()
 assert production.read_bytes()==original


def test_inherited_postgres_url_is_not_used_even_if_unreachable():
 conftest=Path(__file__).with_name('conftest.py')
 env={**os.environ,'DATABASE_URL':'postgresql+psycopg://invalid:invalid@127.0.0.1:1/production'}
 code=f"import runpy;runpy.run_path({str(conftest)!r});from app import main as m;assert m.engine.dialect.name=='sqlite'"
 subprocess.run([sys.executable,'-c',code],env=env,capture_output=True,timeout=30,check=True)
