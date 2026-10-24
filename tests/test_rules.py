import unittest

from app import rules
from app.demo_data import DemoSource
from app.models import Device, Pop


def dev(**kw):
    base = dict(id='x', name='X', role='router', pop='p1', ip='192.0.2.1', model='m')
    base.update(kw)
    return Device(**base)


class ClassifyTest(unittest.TestCase):
    def test_up_down(self):
        self.assertEqual(rules.classify(dev(ping_ok=True)), 'up')
        self.assertEqual(rules.classify(dev(ping_ok=False)), 'down')

    def test_sem_coleta_nao_e_fora(self):
        self.assertEqual(rules.classify(dev(ping_ok=None)), 'unknown')
        self.assertEqual(rules.classify(dev(ping_ok=False, last_seen_s=rules.STALE_AFTER_S + 1)), 'unknown')

    def test_manutencao_vence(self):
        self.assertEqual(rules.classify(dev(ping_ok=False, maintenance=True)), 'maintenance')


class RfTest(unittest.TestCase):
    def test_valores_sem_associacao_nao_sao_sinal_ruim(self):
        self.assertEqual(rules.rf_status(dev(signal_dbm=-96, ccq_pct=0)), 'nao_aplicavel')
        self.assertEqual(rules.rf_status(dev(signal_dbm=-60, ccq_pct=0)), 'nao_aplicavel')

    def test_degradado(self):
        self.assertEqual(rules.rf_status(dev(signal_dbm=-80, ccq_pct=90)), 'degradado')
        self.assertEqual(rules.rf_status(dev(signal_dbm=-60, ccq_pct=50)), 'degradado')

    def test_ok_e_nao_radio(self):
        self.assertEqual(rules.rf_status(dev(signal_dbm=-60, ccq_pct=95)), 'ok')
        self.assertIsNone(rules.rf_status(dev()))


class OnuPowerTest(unittest.TestCase):
    def test_onu(self):
        self.assertEqual(rules.onu_status(dev(role='onu', rx_power_dbm=-28)), 'baixo')
        self.assertEqual(rules.onu_status(dev(role='onu', rx_power_dbm=-26)), 'atencao')
        self.assertEqual(rules.onu_status(dev(role='onu', rx_power_dbm=-20)), 'ok')

    def test_energia(self):
        self.assertEqual(rules.power_status(dev(on_grid=True, voltage_v=13.5)), 'rede')
        self.assertEqual(rules.power_status(dev(on_grid=False, voltage_v=12.4)), 'bateria')
        self.assertEqual(rules.power_status(dev(on_grid=False, voltage_v=11.2)), 'bateria_critica')
        self.assertIsNone(rules.power_status(dev()))


class AlarmsTest(unittest.TestCase):
    pops = [Pop('p1', 'POP 1', None, 'core', 0, 0), Pop('p2', 'POP 2', 'p1', 'fibra', 0, 0)]

    def test_pop_fora_vira_um_alarme_so(self):
        devs = [dev(id=f'd{i}', pop='p2', ping_ok=(i == 0)) for i in range(5)]  # 4 de 5 fora = 80%
        alarms = rules.alarms(self.pops, rules.records(devs))
        self.assertEqual([a['kind'] for a in alarms], ['pop_down'])

    def test_abaixo_de_80_porcento_alarma_cada_um(self):
        devs = [dev(id=f'd{i}', pop='p2', ping_ok=(i < 2)) for i in range(5)]  # 3 de 5 fora
        kinds = [a['kind'] for a in rules.alarms(self.pops, rules.records(devs))]
        self.assertEqual(kinds, ['host_down'] * 3)

    def test_ap_no_ar_com_todas_estacoes_fora(self):
        devs = [dev(id='ap', role='ap', pop='p1')] + \
               [dev(id=f's{i}', role='station', pop='p1', ap='ap', ping_ok=False) for i in range(3)] + \
               [dev(id=f'r{i}', pop='p1') for i in range(10)]
        alarms = rules.alarms(self.pops, rules.records(devs))
        self.assertEqual([a['kind'] for a in alarms], ['stations_down'])
        self.assertEqual(len(alarms[0]['devices']), 3)

    def test_prioridade(self):
        devs = [dev(id='a', pop='p1', signal_dbm=-80, ccq_pct=90),
                dev(id='b', pop='p1', ping_ok=False),
                dev(id='c', pop='p1', on_grid=False, voltage_v=12.0)]
        kinds = [a['kind'] for a in rules.alarms(self.pops, rules.records(devs))]
        self.assertEqual(kinds, ['power', 'host_down', 'degraded'])


class DemoScenarioTest(unittest.TestCase):
    """A rede de demonstração precisa mostrar todos os cenários prometidos no README."""

    def setUp(self):
        src = DemoSource(seed=1)
        self.pops = src.pops()
        self.recs = rules.records(src.devices())
        self.alarms = rules.alarms(self.pops, self.recs)

    def test_cenarios(self):
        kinds = {a['kind'] for a in self.alarms}
        self.assertEqual(kinds, {'pop_down', 'power', 'stations_down', 'degraded', 'no_data'})

    def test_pop_vale_fora_e_sub_pops(self):
        summary = {p['id']: p for p in rules.pop_summary(self.pops, self.recs)}
        self.assertEqual(summary['vale']['status'], 'fora')
        self.assertEqual(summary['serra']['power'], 'bateria')
        self.assertEqual(summary['centro']['status'], 'atencao')

    def test_so_enderecos_de_documentacao(self):
        for r in self.recs:
            self.assertTrue(r['ip'].startswith(('192.0.2.', '198.51.100.', '203.0.113.')), r['ip'])


if __name__ == '__main__':
    unittest.main()
