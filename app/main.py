"""Network Operations Demo — servidor web (FastAPI).

Rodar:  uvicorn app.main:app --reload   e abrir http://127.0.0.1:8000
"""
from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from . import rules
from .incidents import IncidentStore
from .sources import get_source

ROOT = Path(__file__).resolve().parent.parent
PAGES = ROOT / 'pages'
VERSION = '1.0.0'

source = get_source()
store = IncidentStore(source.now())

app = FastAPI(title='Network Operations Demo', version=VERSION,
              description='Demonstração com dados fictícios. Não se conecta a nenhuma rede real.')
app.mount('/static', StaticFiles(directory=ROOT / 'static'), name='static')


def _page(name: str) -> FileResponse:
    return FileResponse(PAGES / f'{name}.html')


@app.get('/', include_in_schema=False)
def page_noc():
    return _page('noc')


@app.get('/visao-geral', include_in_schema=False)
def page_overview():
    return _page('overview')


@app.get('/topologia', include_in_schema=False)
def page_topology():
    return _page('topology')


@app.get('/olt', include_in_schema=False)
def page_olt():
    return _page('olt')


@app.get('/ocorrencias', include_in_schema=False)
def page_incidents():
    return _page('incidents')


# ---------------------------------------------------------------- API (só leitura de rede)

def _snapshot():
    pops = source.pops()
    recs = rules.records(source.devices())
    return pops, recs


@app.get('/api/status')
def api_status():
    return {'version': VERSION, 'data_source': source.name, 'writable': source.writable,
            'demo': True, 'now': source.now()}


@app.get('/api/noc')
def api_noc():
    pops, recs = _snapshot()
    names = {r['id']: r['name'] for r in recs}
    events = sorted(source.events(), key=lambda e: -e.ts)
    return {
        'now': source.now(),
        'summary': rules.summarize(recs),
        'pops': rules.pop_summary(pops, recs),
        'alarms': rules.alarms(pops, recs),
        'events': [{'ts': e.ts, 'device': names.get(e.device, e.device), 'severity': e.severity,
                    'text': e.text, 'resolved': e.resolved} for e in events],
    }


@app.get('/api/devices')
def api_devices():
    pops, recs = _snapshot()
    return {'pops': [{'id': p.id, 'name': p.name} for p in pops], 'devices': recs}


@app.get('/api/topology')
def api_topology():
    pops, recs = _snapshot()
    return {'pops': rules.pop_summary(pops, recs)}


@app.get('/api/onus')
def api_onus():
    pops, recs = _snapshot()
    names = {p.id: p.name for p in pops}
    onus = [dict(r, pop_name=names.get(r['pop'], r['pop'])) for r in recs if r['role'] == 'onu']
    onus.sort(key=lambda r: r['rx_power_dbm'])
    return {'limits': {'low': rules.ONU_LOW_DBM, 'warn': rules.ONU_WARN_DBM}, 'onus': onus}


# ---------------------------------------------------------------- ocorrências (memória)

class NewIncident(BaseModel):
    title: str = Field(min_length=3, max_length=120)
    pop: str | None = None


class IncidentPatch(BaseModel):
    status: str | None = None
    owner: str | None = Field(default=None, max_length=40)
    note: str | None = Field(default=None, max_length=500)
    author: str = Field(default='visitante', max_length=40)


@app.get('/api/incidents')
def list_incidents():
    return {'incidents': store.list()}


@app.post('/api/incidents', status_code=201)
def create_incident(body: NewIncident):
    known = {p.id for p in source.pops()}
    if body.pop and body.pop not in known:
        raise HTTPException(400, 'POP desconhecido')
    inc = store.create(body.title, 'manual', body.pop, source.now())
    return {'id': inc.id}


@app.patch('/api/incidents/{inc_id}')
def update_incident(inc_id: int, body: IncidentPatch):
    try:
        inc = store.update(inc_id, source.now(), body.status, body.owner, body.note, body.author)
    except KeyError:
        raise HTTPException(404, 'ocorrência não encontrada')
    except ValueError as exc:
        raise HTTPException(400, str(exc))
    return {'id': inc.id, 'status': inc.status}
