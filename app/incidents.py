"""Ocorrências: registro do atendimento (abrir, assumir, anotar, encerrar).

Na demo ficam só na memória e voltam ao estado inicial quando o servidor reinicia.
"""
from __future__ import annotations

import threading
from dataclasses import asdict

from .models import Incident

STATUSES = ('aberta', 'em andamento', 'resolvida')


class IncidentStore:
    def __init__(self, now: int):
        self._lock = threading.Lock()
        self._items: dict[int, Incident] = {}
        self._next = 1
        h = 3600
        seed = [
            ('Queda do link de fibra Norte–Vale', 'pop_down', 'vale', now - 240, 'em andamento', 'operador.demo',
             [('operador.demo', 'Equipe acionada para verificar a fibra entre Norte e Vale.')], None),
            ('AP Centro 1 reiniciou após queda de energia', 'host_down', 'centro', now - 3 * h, 'resolvida', 'operador.demo',
             [('operador.demo', 'Energia voltou; AP e estações normalizados.')], now - 3 * h + 900),
            ('Perda de pacotes no enlace Centro–Serra', 'degraded', 'serra', now - 5 * h, 'resolvida', 'operador.demo',
             [('operador.demo', 'Realinhamento da antena; perda zerada.')], now - 5 * h + 1800),
        ]
        for title, kind, pop, opened, status, owner, notes, closed in seed:
            inc = self.create(title, kind, pop, opened)
            inc.status, inc.owner, inc.closed_ts = status, owner, closed
            inc.notes = [{'ts': opened + 60, 'author': a, 'text': t} for a, t in notes]

    def create(self, title: str, kind: str = 'manual', pop: str | None = None, ts: int = 0) -> Incident:
        with self._lock:
            inc = Incident(self._next, title.strip()[:120], kind, pop, ts)
            self._items[inc.id] = inc
            self._next += 1
            return inc

    def list(self) -> list[dict]:
        with self._lock:
            items = sorted(self._items.values(), key=lambda i: (i.status == 'resolvida', -i.opened_ts))
            return [asdict(i) for i in items]

    def get(self, inc_id: int) -> Incident | None:
        return self._items.get(inc_id)

    def update(self, inc_id: int, now: int, status: str | None = None, owner: str | None = None,
               note: str | None = None, author: str = 'visitante') -> Incident:
        with self._lock:
            inc = self._items.get(inc_id)
            if inc is None:
                raise KeyError(inc_id)
            if status is not None:
                if status not in STATUSES:
                    raise ValueError(f'status inválido: {status}')
                inc.status = status
                inc.closed_ts = now if status == 'resolvida' else None
            if owner is not None:
                inc.owner = owner.strip()[:40] or None
            if note:
                inc.notes.append({'ts': now, 'author': author[:40], 'text': note.strip()[:500]})
                if len(inc.notes) > 50:
                    inc.notes = inc.notes[-50:]
            return inc
