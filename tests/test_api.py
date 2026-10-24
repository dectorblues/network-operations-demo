import unittest

from fastapi.testclient import TestClient

from app.main import app


class ApiTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)

    def test_status_e_demo_e_somente_leitura(self):
        r = self.client.get('/api/status').json()
        self.assertTrue(r['demo'])
        self.assertEqual(r['data_source'], 'demo')
        self.assertFalse(r['writable'])

    def test_paginas(self):
        for path in ('/', '/visao-geral', '/topologia', '/olt', '/ocorrencias'):
            r = self.client.get(path)
            self.assertEqual(r.status_code, 200, path)
            self.assertIn('/static/common.js', r.text)

    def test_noc(self):
        d = self.client.get('/api/noc').json()
        self.assertGreater(d['summary']['total'], 30)
        self.assertTrue(d['alarms'])
        self.assertEqual(d['alarms'][0]['kind'], 'pop_down')

    def test_onus_ordenadas_do_pior(self):
        onus = self.client.get('/api/onus').json()['onus']
        values = [o['rx_power_dbm'] for o in onus]
        self.assertEqual(values, sorted(values))

    def test_fluxo_de_ocorrencia(self):
        r = self.client.post('/api/incidents', json={'title': 'Teste de fluxo', 'pop': 'centro'})
        self.assertEqual(r.status_code, 201)
        inc = r.json()['id']
        self.client.patch(f'/api/incidents/{inc}', json={'status': 'em andamento', 'owner': 'ana'})
        self.client.patch(f'/api/incidents/{inc}', json={'note': 'verificando'})
        r = self.client.patch(f'/api/incidents/{inc}', json={'status': 'resolvida'})
        self.assertEqual(r.json()['status'], 'resolvida')
        item = next(i for i in self.client.get('/api/incidents').json()['incidents'] if i['id'] == inc)
        self.assertEqual(item['owner'], 'ana')
        self.assertEqual(item['notes'][0]['text'], 'verificando')
        self.assertIsNotNone(item['closed_ts'])

    def test_validacoes(self):
        self.assertEqual(self.client.post('/api/incidents', json={'title': 'x'}).status_code, 422)
        self.assertEqual(self.client.post('/api/incidents', json={'title': 'abc', 'pop': 'nao-existe'}).status_code, 400)
        self.assertEqual(self.client.patch('/api/incidents/999', json={'note': 'a'}).status_code, 404)
        self.assertEqual(self.client.patch('/api/incidents/1', json={'status': 'apagada'}).status_code, 400)


if __name__ == '__main__':
    unittest.main()
