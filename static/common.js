// Partes comuns a todas as páginas: faixa de demonstração, menu, relógio e utilidades.
const NAV = [
  ['/', 'NOC'],
  ['/visao-geral', 'Visão geral'],
  ['/topologia', 'Topologia'],
  ['/olt', 'OLT / ONUs'],
  ['/ocorrencias', 'Ocorrências'],
];

function esc(s) {
  return String(s ?? '').replace(/[&<>"']/g, c => ({'&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'}[c]));
}

const STATE_LABEL = {up: 'no ar', down: 'fora', unknown: 'sem coleta', maintenance: 'manutenção'};
const ROLE_LABEL = {router: 'Roteador', switch: 'Switch', ap: 'AP', station: 'Estação', backhaul: 'Enlace', olt: 'OLT', onu: 'ONU'};
const RF_LABEL = {ok: 'ok', degradado: 'degradado', nao_aplicavel: 'sem associação'};
const SEVERITY = {info: 'info', warning: 'aviso', high: 'alta', disaster: 'desastre'};
const LINK_LABEL = {fibra: 'fibra', radio: 'rádio', core: 'núcleo'};

function pill(value, label) {
  if (!value) return '<span class="small">—</span>';
  return `<span class="pill ${esc(value)}">${esc(label ?? value)}</span>`;
}

function ago(ts, now) {
  const s = Math.max(0, (now ?? Date.now() / 1000) - ts);
  if (s < 60) return 'agora';
  if (s < 3600) return `${Math.round(s / 60)} min`;
  if (s < 86400) return `${Math.round(s / 3600)} h`;
  return `${Math.round(s / 86400)} d`;
}

async function api(path, opts) {
  const r = await fetch(path, opts);
  if (!r.ok) throw new Error(`${r.status} ${await r.text()}`);
  return r.json();
}

(function chrome() {
  const banner = document.createElement('div');
  banner.className = 'demo-banner';
  banner.textContent = 'AMBIENTE DE DEMONSTRAÇÃO — DADOS FICTÍCIOS';
  const header = document.createElement('header');
  header.className = 'top';
  const here = location.pathname.replace(/\/$/, '') || '/';
  header.innerHTML = `<div class="brand">Network <span>Operations</span> Demo</div>
    <nav class="menu">${NAV.map(([href, label]) =>
      `<a href="${href}" class="${href === here ? 'active' : ''}">${label}</a>`).join('')}</nav>
    <div class="clock" id="clock"></div>`;
  document.body.prepend(header);
  document.body.prepend(banner);
  const footer = document.createElement('footer');
  footer.textContent = 'Demonstração com dados sintéticos. Não está conectada a nenhuma rede real.';
  document.body.append(footer);
  const tick = () => { document.getElementById('clock').textContent = new Date().toLocaleTimeString('pt-BR'); };
  tick(); setInterval(tick, 1000);
})();
