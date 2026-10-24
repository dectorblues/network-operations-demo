"""Fonte de dados de demonstração: uma rede inteiramente inventada.

Nada aqui vem de uma rede real. Os nomes de POP são genéricos, os IPs usam as faixas
reservadas para documentação (RFC 5737: 192.0.2.0/24, 198.51.100.0/24, 203.0.113.0/24)
e os seriais começam com DEMO.

A rede tem cenários montados de propósito, para as regras terem o que mostrar:
- POP Vale: o link de fibra caiu e o POP inteiro está fora;
- POP Serra: sem energia da rede, roteador funcionando na bateria;
- AP Norte 2: o AP responde, mas todas as estações dele estão fora;
- ST Serra 3: rádio no ar com sinal e CCQ ruins (enlace degradado);
- ST Centro 4: sem coleta há 15 minutos (não dá para dizer se está fora);
- ONU Centro 05: sinal óptico baixo;
- eventos já resolvidos, para a linha do tempo.
"""
from __future__ import annotations

import random
import time

from .models import Device, Event, Pop

POPS = [
    Pop('nucleo', 'Núcleo', None, 'core', 420, 70),
    Pop('centro', 'POP Centro', 'nucleo', 'fibra', 220, 210),
    Pop('norte', 'POP Norte', 'nucleo', 'fibra', 620, 210),
    Pop('serra', 'POP Serra', 'centro', 'radio', 120, 370, battery=True),
    Pop('vale', 'POP Vale', 'norte', 'fibra', 700, 370),
]


def _routers_and_switches() -> list[Device]:
    return [
        Device('mk-core', 'MK Núcleo', 'router', 'nucleo', '192.0.2.1', 'CCR2004', latency_ms=1),
        Device('sw-core', 'SW Núcleo', 'switch', 'nucleo', '192.0.2.2', 'Switch L2 24p', latency_ms=1),
        Device('olt-01', 'OLT 01', 'olt', 'nucleo', '192.0.2.10', 'OLT GPON 8 PON', latency_ms=1),
        Device('mk-centro', 'MK Centro', 'router', 'centro', '192.0.2.21', 'RB5009', latency_ms=2),
        Device('sw-centro', 'SW Centro', 'switch', 'centro', '192.0.2.22', 'Switch L2 16p', latency_ms=2),
        Device('mk-norte', 'MK Norte', 'router', 'norte', '192.0.2.31', 'RB5009', latency_ms=3),
        Device('sw-norte', 'SW Norte', 'switch', 'norte', '192.0.2.32', 'Switch L2 16p', latency_ms=3),
        Device('mk-serra', 'MK Serra', 'router', 'serra', '192.0.2.41', 'hEX S', latency_ms=6,
               voltage_v=12.3, on_grid=False),
        Device('mk-vale', 'MK Vale', 'router', 'vale', '192.0.2.51', 'hEX S', ping_ok=False),
        Device('sw-vale', 'SW Vale', 'switch', 'vale', '192.0.2.52', 'Switch L2 8p', ping_ok=False),
        Device('cam-vale', 'Câmera Vale', 'switch', 'vale', '192.0.2.53', 'Câmera IP', ping_ok=False),
    ]


def _radios() -> list[Device]:
    d = [
        Device('bh-centro-serra', 'Enlace Centro–Serra', 'backhaul', 'serra', '198.51.100.2',
               'PTP 5 GHz', latency_ms=4, signal_dbm=-58, ccq_pct=96),
        Device('ap-centro-1', 'AP Centro 1', 'ap', 'centro', '198.51.100.10', 'Setorial 5 GHz',
               latency_ms=2, signal_dbm=None, ccq_pct=94),
        Device('ap-norte-1', 'AP Norte 1', 'ap', 'norte', '198.51.100.20', 'Setorial 5 GHz',
               latency_ms=3, ccq_pct=92),
        Device('ap-norte-2', 'AP Norte 2', 'ap', 'norte', '198.51.100.21', 'Setorial 5 GHz',
               latency_ms=3, ccq_pct=0),
        Device('ap-serra', 'AP Serra', 'ap', 'serra', '198.51.100.30', 'Omni 5 GHz',
               latency_ms=7, ccq_pct=81),
    ]
    stations = [
        # (id, nome, ap, pop, sinal, ccq, ping, último dado)
        ('st-centro-1', 'ST Centro 1 — Escola', 'ap-centro-1', 'centro', -61, 95, True, 30),
        ('st-centro-2', 'ST Centro 2 — Posto de Saúde', 'ap-centro-1', 'centro', -64, 93, True, 30),
        ('st-centro-3', 'ST Centro 3 — Biblioteca', 'ap-centro-1', 'centro', -66, 90, True, 30),
        ('st-centro-4', 'ST Centro 4 — Ginásio', 'ap-centro-1', 'centro', None, None, None, 900),
        ('st-norte-1', 'ST Norte 1 — Creche', 'ap-norte-1', 'norte', -60, 96, True, 30),
        ('st-norte-2', 'ST Norte 2 — Almoxarifado', 'ap-norte-1', 'norte', -67, 89, True, 30),
        ('st-norte-3', 'ST Norte 3 — Garagem', 'ap-norte-1', 'norte', -69, 86, True, 30),
        ('st-norte-4', 'ST Norte 4 — Escola Rural', 'ap-norte-2', 'norte', -96, 0, False, 30),
        ('st-norte-5', 'ST Norte 5 — Unidade de Saúde', 'ap-norte-2', 'norte', -96, 0, False, 30),
        ('st-norte-6', 'ST Norte 6 — Praça', 'ap-norte-2', 'norte', -96, 0, False, 30),
        ('st-serra-1', 'ST Serra 1 — Escola', 'ap-serra', 'serra', -63, 92, True, 30),
        ('st-serra-2', 'ST Serra 2 — Posto Policial', 'ap-serra', 'serra', -68, 88, True, 30),
        ('st-serra-3', 'ST Serra 3 — Reservatório', 'ap-serra', 'serra', -79, 54, True, 30),
    ]
    for i, (sid, name, ap, pop, sig, ccq, ok, seen) in enumerate(stations):
        d.append(Device(sid, name, 'station', pop, f'198.51.100.{100 + i}', 'CPE 5 GHz',
                        ap=ap, ping_ok=ok, last_seen_s=seen,
                        latency_ms=(8 + i % 5) if ok else None,
                        signal_dbm=sig, ccq_pct=ccq))
    return d


def _onus() -> list[Device]:
    rx = [-19.8, -21.2, -22.4, -20.9, -28.6, -23.1, -24.0, -21.7, -22.9, -25.6]
    out = []
    for i, value in enumerate(rx, start=1):
        pop = 'centro' if i <= 6 else 'norte'
        out.append(Device(f'onu-{i:02d}', f'ONU {pop.capitalize()} {i:02d} (DEMO{i:04d})', 'onu', pop,
                          f'203.0.113.{i}', 'ONU GPON', latency_ms=4 + i % 3, rx_power_dbm=value))
    return out


def _events(now: int) -> list[Event]:
    m = 60
    return [
        Event(now - 4 * m, 'mk-vale', 'disaster', 'Link de fibra Norte–Vale sem resposta'),
        Event(now - 4 * m, 'sw-vale', 'high', 'Sem resposta ao ping'),
        Event(now - 9 * m, 'mk-serra', 'high', 'Sem energia da rede: funcionando na bateria'),
        Event(now - 22 * m, 'ap-norte-2', 'warning', 'Todas as estações desassociadas'),
        Event(now - 35 * m, 'st-serra-3', 'warning', 'Sinal abaixo de -75 dBm e CCQ abaixo de 70%'),
        Event(now - 51 * m, 'onu-05', 'warning', 'Potência óptica abaixo de -27 dBm'),
        Event(now - 3 * 60 * m, 'ap-centro-1', 'high', 'AP reiniciou após queda de energia', True),
        Event(now - 5 * 60 * m, 'bh-centro-serra', 'warning', 'Enlace com perda de 12% por 8 min', True),
        Event(now - 26 * 60 * m, 'mk-norte', 'high', 'Interface sfp1 caiu e voltou (fibra)', True),
    ]


class DemoSource:
    """Fonte de dados fictícios. `seed` deixa os números estáveis nos testes."""

    name = 'demo'
    writable = False   # nunca grava em equipamento nem em monitoramento

    def __init__(self, seed: int | None = None, clock=time.time):
        self._seed = seed
        self._clock = clock

    def now(self) -> int:
        return int(self._clock())

    def pops(self) -> list[Pop]:
        return list(POPS)

    def devices(self) -> list[Device]:
        devices = _routers_and_switches() + _radios() + _onus()
        # pequena variação a cada minuto, para a tela parecer viva
        rng = random.Random(self._seed if self._seed is not None else self.now() // 60)
        for dev in devices:
            if dev.latency_ms is not None and dev.ping_ok:
                dev.latency_ms = round(dev.latency_ms * rng.uniform(0.85, 1.25), 1)
                dev.loss_pct = 0.0 if rng.random() > 0.08 else round(rng.uniform(0.5, 3), 1)
            if dev.signal_dbm is not None and dev.ping_ok and dev.signal_dbm > -90:
                dev.signal_dbm = round(dev.signal_dbm + rng.uniform(-1.5, 1.5), 1)
            if dev.rx_power_dbm is not None:
                dev.rx_power_dbm = round(dev.rx_power_dbm + rng.uniform(-0.3, 0.3), 1)
        return devices

    def events(self) -> list[Event]:
        return _events(self.now())
