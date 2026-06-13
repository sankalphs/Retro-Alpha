const API = {
    async call(name, data = {}) {
        const client = await window.gradioClient || (window.gradioClient = await import('https://cdn.jsdelivr.net/npm/@gradio/client/dist/index.min.js').then(m => m.Client.connect(window.location.origin)));
        return await client.predict(`/${name}`, data);
    }
};

const ASSETS = ['cash', 'fd', 'gov_bonds', 'nifty_50', 'nifty_it', 'real_estate', 'crypto', 'gold'];
const ASSET_LABELS = {
    cash: 'Cash (INR)',
    fd: 'Bank FD',
    gov_bonds: 'Gov Bonds',
    nifty_50: 'Nifty 50',
    nifty_it: 'Nifty IT',
    real_estate: 'Real Estate',
    crypto: 'Crypto',
    gold: 'Gold'
};

let history = [];

function formatMoney(n) {
    return '₹' + Math.round(n).toLocaleString('en-IN');
}

function formatPrice(n) {
    return n.toFixed(3);
}

function updateClock() {
    const now = new Date();
    document.getElementById('clock').textContent = now.toLocaleTimeString('en-IN');
}
setInterval(updateClock, 1000);
updateClock();

async function fetchState() {
    const result = await API.call('state');
    return result.data;
}

function renderState(state) {
    document.getElementById('total-value').textContent = formatMoney(state.total_value);
    document.getElementById('game-time').textContent = `YEAR ${state.year} / MONTH ${state.month}`;

    // Ticker
    const tickerItems = ASSETS.map(a => `${ASSET_LABELS[a]}: ${formatPrice(state.prices[a])}`).join('   ');
    document.getElementById('ticker').textContent = tickerItems;

    // News
    const newsEl = document.getElementById('news-display');
    if (state.news && state.news.headline) {
        newsEl.innerHTML = `<strong>${state.news.headline}</strong><br><br>${formatImpact(state.news.impact)}`;
    }

    // Holdings
    const tbody = document.querySelector('#holdings-table tbody');
    tbody.innerHTML = '';
    ASSETS.forEach(asset => {
        const price = state.prices[asset];
        const qty = state.portfolio[asset];
        const value = qty * price;
        const row = document.createElement('tr');
        row.innerHTML = `<td>${ASSET_LABELS[asset]}</td><td>${formatPrice(price)}</td><td>${qty.toFixed(2)}</td><td>${formatMoney(value)}</td>`;
        tbody.appendChild(row);
    });

    // Agent log
    const logEl = document.getElementById('agent-log');
    logEl.innerHTML = '';
    (state.agent_actions || []).forEach(action => {
        const div = document.createElement('div');
        div.className = `agent-entry agent-${action.agent}`;
        const acts = (action.actions || []).map(a => `${a.action.toUpperCase()} ${ASSET_LABELS[a.asset]} ${(a.amount_pct * 100).toFixed(0)}%`).join(', ');
        div.innerHTML = `<strong>${action.agent.toUpperCase()}</strong> [${action.sentiment}]<br>${acts}<br><em>${action.actions[0]?.reason || ''}</em>`;
        logEl.appendChild(div);
    });

    // Chart
    history.push(state.total_value);
    if (history.length > 50) history.shift();
    drawChart(history);
}

function formatImpact(impact) {
    if (!impact) return '';
    return ASSETS.map(a => `${ASSET_LABELS[a]}: ${(impact[a] * 100).toFixed(1)}%`).join(' | ');
}

function drawChart(data) {
    const canvas = document.getElementById('chart');
    const ctx = canvas.getContext('2d');
    const w = canvas.width;
    const h = canvas.height;
    ctx.clearRect(0, 0, w, h);
    if (data.length < 2) return;

    const min = Math.min(...data);
    const max = Math.max(...data);
    const range = max - min || 1;

    ctx.strokeStyle = '#33ff33';
    ctx.lineWidth = 2;
    ctx.beginPath();
    data.forEach((v, i) => {
        const x = (i / (data.length - 1)) * (w - 20) + 10;
        const y = h - 10 - ((v - min) / range) * (h - 20);
        if (i === 0) ctx.moveTo(x, y);
        else ctx.lineTo(x, y);
    });
    ctx.stroke();
}

async function init() {
    // Populate asset select
    const select = document.getElementById('trade-asset');
    ASSETS.forEach(a => {
        const opt = document.createElement('option');
        opt.value = a;
        opt.textContent = ASSET_LABELS[a];
        select.appendChild(opt);
    });

    // Load initial state
    const state = await fetchState();
    renderState(state);

    // Event listeners
    document.getElementById('btn-trade').addEventListener('click', async () => {
        const asset = document.getElementById('trade-asset').value;
        const action = document.getElementById('trade-action').value;
        const amount = parseFloat(document.getElementById('trade-amount').value) / 100;
        const result = await API.call('trade', { asset, action, amount_pct: amount });
        renderState(result.data);
    });

    document.getElementById('btn-advance').addEventListener('click', async () => {
        const result = await API.call('advance');
        renderState(result.data);
        if (result.data.month === 0 || result.data.month === 12) {
            showMentor();
        }
    });

    document.getElementById('btn-reset').addEventListener('click', async () => {
        history = [];
        const result = await API.call('reset');
        renderState(result.data);
    });

    document.getElementById('btn-close-mentor').addEventListener('click', () => {
        document.getElementById('mentor-modal').classList.add('hidden');
    });
}

async function showMentor() {
    const result = await API.call('mentor');
    const review = result.data.review;
    document.getElementById('mentor-roast').textContent = review.roast;
    document.getElementById('mentor-lesson').textContent = review.lesson;
    document.getElementById('mentor-suggestion').textContent = review.suggestion;
    document.getElementById('mentor-modal').classList.remove('hidden');
}

init().catch(console.error);
