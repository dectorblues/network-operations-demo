"""Escolha da fonte de dados por configuração (DATA_SOURCE).

Esta edição pública traz só a fonte de demonstração. A integração com o Zabbix existe
no sistema original e fica em ambiente privado; aqui ela aparece apenas como o contrato
que qualquer fonte precisa cumprir.
"""
from __future__ import annotations

import os
from typing import Protocol

from .demo_data import DemoSource
from .models import Device, Event, Pop


class DataSource(Protocol):
    name: str
    writable: bool

    def now(self) -> int: ...
    def pops(self) -> list[Pop]: ...
    def devices(self) -> list[Device]: ...
    def events(self) -> list[Event]: ...


def get_source() -> DataSource:
    name = os.getenv('DATA_SOURCE', 'demo').strip().lower()
    if name == 'demo':
        return DemoSource()
    raise RuntimeError(
        f'DATA_SOURCE={name!r} não está disponível nesta edição de demonstração. Use DATA_SOURCE=demo.')
