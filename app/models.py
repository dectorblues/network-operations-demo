"""Contrato de dados comum a qualquer fonte (demo ou real).

As páginas e as regras só conhecem estes tipos. Trocar a fonte de dados não muda nada
acima desta camada.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

Role = Literal['router', 'switch', 'ap', 'station', 'backhaul', 'olt', 'onu']
State = Literal['up', 'down', 'unknown', 'maintenance']


@dataclass
class Pop:
    id: str
    name: str
    parent: str | None          # POP de onde vem o link (None = núcleo)
    link: Literal['fibra', 'radio', 'core']
    x: int                      # posição no desenho da topologia (fictícia)
    y: int
    battery: bool = False       # tem banco de baterias


@dataclass
class Device:
    id: str
    name: str
    role: Role
    pop: str
    ip: str
    model: str
    ap: str | None = None       # estação: a qual AP está associada
    # métricas "cruas", como viriam do monitoramento
    ping_ok: bool | None = True       # None = sem coleta
    last_seen_s: int = 30             # segundos desde a última coleta
    latency_ms: float | None = None
    loss_pct: float | None = None
    signal_dbm: float | None = None   # rádio
    ccq_pct: float | None = None      # rádio
    rx_power_dbm: float | None = None # ONU (óptico)
    voltage_v: float | None = None    # roteador com bateria
    on_grid: bool | None = None       # True = energia da rede presente
    maintenance: bool = False


@dataclass
class Event:
    ts: int            # epoch (s)
    device: str
    severity: Literal['info', 'warning', 'high', 'disaster']
    text: str
    resolved: bool = False


@dataclass
class Incident:
    id: int
    title: str
    kind: str
    pop: str | None
    opened_ts: int
    status: Literal['aberta', 'em andamento', 'resolvida'] = 'aberta'
    owner: str | None = None
    notes: list[dict] = field(default_factory=list)
    closed_ts: int | None = None
