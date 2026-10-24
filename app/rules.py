"""Regras de operação: o conhecimento de redes transformado em código.

Tudo aqui é função pura (entra dado, sai resultado), por isso é fácil de testar e não
depende de qual fonte de dados está em uso.
"""
from __future__ import annotations

from collections import defaultdict
from typing import Any

from .models import Device, Pop

STALE_AFTER_S = 600          # sem coleta há mais de 10 min = estado desconhecido
RF_NOT_APPLICABLE_DBM = -95  # -96 dBm / CCQ 0% = rádio sem associação, não "sinal ruim"
RF_WEAK_DBM = -75
RF_WEAK_CCQ = 70
ONU_LOW_DBM = -27.0
ONU_WARN_DBM = -25.0
BATTERY_CRITICAL_V = 11.5
POP_DOWN_SHARE = 0.8         # POP fora quando 80% ou mais dos equipamentos caem
POP_DOWN_MIN_HOSTS = 3
STATIONS_DOWN_MIN = 2


# ---------------------------------------------------------------- estado de um equipamento

def classify(dev: Device) -> str:
    """up / down / unknown / maintenance.

    A diferença entre "fora" e "sem coleta" importa: um equipamento sem dado novo não está
    necessariamente fora, e tratar os dois iguais gera alarme falso.
    """
    if dev.maintenance:
        return 'maintenance'
    if dev.ping_ok is None or dev.last_seen_s > STALE_AFTER_S:
        return 'unknown'
    return 'up' if dev.ping_ok else 'down'


def rf_status(dev: Device) -> str | None:
    """ok / degradado / nao_aplicavel (None para quem não é rádio)."""
    if dev.signal_dbm is None and dev.ccq_pct is None:
        return None
    if (dev.signal_dbm is not None and dev.signal_dbm <= RF_NOT_APPLICABLE_DBM) or dev.ccq_pct == 0:
        return 'nao_aplicavel'
    if (dev.signal_dbm is not None and dev.signal_dbm < RF_WEAK_DBM) or \
            (dev.ccq_pct is not None and dev.ccq_pct < RF_WEAK_CCQ):
        return 'degradado'
    return 'ok'


def onu_status(dev: Device) -> str | None:
    if dev.rx_power_dbm is None:
        return None
    if dev.rx_power_dbm < ONU_LOW_DBM:
        return 'baixo'
    if dev.rx_power_dbm < ONU_WARN_DBM:
        return 'atencao'
    return 'ok'


def power_status(dev: Device) -> str | None:
    if dev.on_grid is None and dev.voltage_v is None:
        return None
    if dev.voltage_v is not None and dev.voltage_v < BATTERY_CRITICAL_V:
        return 'bateria_critica'
    if dev.on_grid is False:
        return 'bateria'
    return 'rede'


# ---------------------------------------------------------------- visão geral

def records(devices: list[Device]) -> list[dict[str, Any]]:
    out = []
    for d in devices:
        out.append({
            'id': d.id, 'name': d.name, 'role': d.role, 'pop': d.pop, 'ip': d.ip,
            'model': d.model, 'ap': d.ap, 'state': classify(d),
            'latency_ms': d.latency_ms if d.ping_ok else None, 'loss_pct': d.loss_pct,
            'signal_dbm': d.signal_dbm, 'ccq_pct': d.ccq_pct, 'rf': rf_status(d),
            'rx_power_dbm': d.rx_power_dbm, 'onu': onu_status(d),
            'voltage_v': d.voltage_v, 'power': power_status(d), 'last_seen_s': d.last_seen_s,
        })
    return out


def pop_summary(pops: list[Pop], recs: list[dict]) -> list[dict[str, Any]]:
    by_pop: dict[str, list[dict]] = defaultdict(list)
    for r in recs:
        by_pop[r['pop']].append(r)
    down_pops = {p.id for p in pops if _pop_is_down(by_pop[p.id])}
    out = []
    for p in pops:
        items = by_pop[p.id]
        known = [r for r in items if r['state'] in ('up', 'down')]
        up = sum(r['state'] == 'up' for r in known)
        power = next((r['power'] for r in items if r['power']), None)
        status = 'fora' if p.id in down_pops else (
            'atencao' if any(r['state'] == 'down' for r in items) or power in ('bateria', 'bateria_critica')
            or any(r['rf'] == 'degradado' or r['onu'] == 'baixo' for r in items) else 'ok')
        out.append({
            'id': p.id, 'name': p.name, 'parent': p.parent, 'link': p.link, 'x': p.x, 'y': p.y,
            'total': len(items), 'up': up, 'down': sum(r['state'] == 'down' for r in items),
            'unknown': sum(r['state'] == 'unknown' for r in items),
            'availability': round(100 * up / len(known), 1) if known else None,
            'power': power, 'status': status,
            'parent_down': p.parent in down_pops,
        })
    return out


def _pop_is_down(items: list[dict]) -> bool:
    known = [r for r in items if r['state'] in ('up', 'down')]
    if len(known) < POP_DOWN_MIN_HOSTS:
        return False
    return sum(r['state'] == 'down' for r in known) / len(known) >= POP_DOWN_SHARE


def summarize(recs: list[dict]) -> dict[str, int]:
    s = {'total': len(recs), 'up': 0, 'down': 0, 'unknown': 0, 'maintenance': 0}
    for r in recs:
        s[r['state']] += 1
    s['degraded'] = sum(r['rf'] == 'degradado' or r['onu'] == 'baixo' for r in recs)
    return s


# ---------------------------------------------------------------- alarmes agrupados

PRIORITY = {'pop_down': 0, 'power': 1, 'stations_down': 2, 'host_down': 3, 'degraded': 4, 'no_data': 5}


def alarms(pops: list[Pop], recs: list[dict]) -> list[dict[str, Any]]:
    """Agrupa falhas pela causa provável, para o operador ver um problema e não vinte.

    - POP com 80%+ fora vira UM alarme; os equipamentos dele não geram alarme próprio.
    - AP no ar com todas as estações fora vira UM alarme do AP.
    - Bateria em uso, enlace degradado, ONU com sinal baixo e falta de coleta aparecem à parte.
    """
    names = {p.id: p.name for p in pops}
    by_pop: dict[str, list[dict]] = defaultdict(list)
    for r in recs:
        by_pop[r['pop']].append(r)

    out: list[dict] = []
    covered: set[str] = set()

    for p in pops:
        items = by_pop[p.id]
        if _pop_is_down(items):
            down = [r for r in items if r['state'] == 'down']
            out.append(_alarm('pop_down', f'{p.name} fora do ar', p.id,
                              f'{len(down)} de {len(items)} equipamentos sem resposta. '
                              f'Verificar o link de {"rádio" if p.link == "radio" else p.link} '
                              f'vindo de {names.get(p.parent, "-")}.',
                              [r['id'] for r in down]))
            covered.update(r['id'] for r in items)

    stations: dict[str, list[dict]] = defaultdict(list)
    for r in recs:
        if r['role'] == 'station' and r['ap']:
            stations[r['ap']].append(r)
    for r in recs:
        if r['role'] != 'ap' or r['id'] in covered or r['state'] != 'up':
            continue
        sts = stations.get(r['id'], [])
        down = [s for s in sts if s['state'] == 'down']
        if len(sts) >= STATIONS_DOWN_MIN and len(down) == len(sts):
            out.append(_alarm('stations_down', f'{r["name"]}: no ar, mas sem nenhuma estação', r['pop'],
                              f'{len(down)} estações fora. Provável problema no rádio do AP '
                              f'(frequência, interferência) e não nas estações.',
                              [s['id'] for s in down]))
            covered.update(s['id'] for s in down)

    for r in recs:
        if r['power'] in ('bateria', 'bateria_critica'):
            critical = r['power'] == 'bateria_critica'
            out.append(_alarm('power', f'{names[r["pop"]]}: sem energia da rede', r['pop'],
                              f'{r["name"]} na bateria ({r["voltage_v"]} V)'
                              + (' — tensão crítica, o POP pode desligar.' if critical else '.'),
                              [r['id']]))

    for r in recs:
        if r['id'] in covered:
            continue
        if r['state'] == 'down':
            out.append(_alarm('host_down', f'{r["name"]} sem resposta', r['pop'], r['ip'], [r['id']]))
        elif r['state'] == 'unknown':
            out.append(_alarm('no_data', f'{r["name"]}: sem coleta', r['pop'],
                              f'Último dado há {r["last_seen_s"] // 60} min. Não é possível '
                              f'dizer se está fora.', [r['id']]))
        elif r['rf'] == 'degradado':
            out.append(_alarm('degraded', f'{r["name"]}: enlace degradado', r['pop'],
                              f'Sinal {r["signal_dbm"]} dBm, CCQ {r["ccq_pct"]}%.', [r['id']]))
        elif r['onu'] == 'baixo':
            out.append(_alarm('degraded', f'{r["name"]}: sinal óptico baixo', r['pop'],
                              f'Rx {r["rx_power_dbm"]} dBm (limite {ONU_LOW_DBM} dBm).', [r['id']]))

    out.sort(key=lambda a: PRIORITY[a['kind']])
    return out


def _alarm(kind: str, title: str, pop: str | None, detail: str, devices: list[str]) -> dict:
    return {'kind': kind, 'title': title, 'pop': pop, 'detail': detail, 'devices': devices,
            'priority': PRIORITY[kind]}
