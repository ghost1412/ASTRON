const API_BASE = window.location.origin;
let currentTenant = localStorage.getItem('tenant_id');
let currentToken = localStorage.getItem('api_token');
let activityChart = null;

// Initialize view state
document.addEventListener('DOMContentLoaded', () => {
    if (currentTenant && currentToken) {
        showDashboard();
    }
});

// View Switching Logic
function switchView(view) {
    // Toggle active state in sidebar
    document.querySelectorAll('.nav-item').forEach(el => el.classList.remove('active'));
    // Find the clicked item - might be the icon or the text
    const activeItem = event?.currentTarget || document.querySelector(`[onclick="switchView('${view}')"]`);
    if (activeItem) activeItem.classList.add('active');
    
    // Switch panels
    document.querySelectorAll('section').forEach(s => s.classList.add('hidden'));
    document.getElementById(`${view}-view`).classList.remove('hidden');
    
    if (view === 'assets') fetchAssets();
    if (view === 'dashboard') {
        fetchQueries();
        renderActivityChart();
    }
    lucide.createIcons();
}

function showDashboard() {
    document.getElementById('onboarding-section').classList.add('hidden');
    document.getElementById('sidebar-nav').classList.remove('hidden');
    switchView('dashboard');
}

async function fetchAssets() {
    try {
        const res = await fetch(`${API_BASE}/v1/assets`, {
            headers: { 'Authorization': `Bearer ${currentToken}`, 'X-Tenant-ID': currentTenant }
        });
        const json = await res.json();
        const list = document.getElementById('asset-list');
        list.innerHTML = '';
        
        document.getElementById('stat-asset-count').textContent = json.data.length;

        json.data.forEach(a => {
            const tr = document.createElement('tr');
            tr.innerHTML = `
                <td>${a.db_alias}</td>
                <td style="color:var(--accent)">${a.asset_name}</td>
                <td><span class="tag">${a.asset_type || 'TABLE'}</span></td>
                <td>v${a.schema_version}</td>
                <td style="font-size:0.8rem">${new Date(a.last_synced).toLocaleString()}</td>
            `;
            list.appendChild(tr);
        });
    } catch (e) { console.error(e); }
}

async function login() {
    const tid = document.getElementById('api-tenant-input').value;
    const token = document.getElementById('api-token-input').value;
    if (!tid || !token) return alert("Missing credentials");

    localStorage.setItem('tenant_id', tid);
    localStorage.setItem('api_token', token);
    currentTenant = tid;
    currentToken = token;
    showDashboard();
}

function logout() {
    localStorage.clear();
    location.reload();
}

// Charting Logic (Mock Activity for Demo Visuals)
function renderActivityChart() {
    const ctx = document.getElementById('activityChart').getContext('2d');
    if (activityChart) activityChart.destroy();

    activityChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: ['12am', '4am', '8am', '12pm', '4pm', '8pm', '12am'],
            datasets: [{
                label: 'Query Ingestion',
                data: [120, 450, 3000, 8500, 12000, 7500, 2000],
                borderColor: '#22d3ee',
                backgroundColor: 'rgba(34, 211, 238, 0.1)',
                borderWidth: 3,
                tension: 0.4,
                fill: true
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: { legend: { display: false } },
            scales: {
                y: { display: false },
                x: { grid: { color: 'rgba(255,255,255,0.05)' }, ticks: { color: '#94a3b8' } }
            }
        }
    });
}

// Query Fetching with Filters
async function fetchQueries() {
    try {
        const search = document.getElementById('search-query').value || '';
        const dialect = document.getElementById('filter-dialect').value || '';
        
        const url = new URL(`${API_BASE}/v1/queries`);
        if (dialect) url.searchParams.append('dialect', dialect);
        if (search) url.searchParams.append('search', search);

        const res = await fetch(url.toString(), {
            headers: { 
                'Authorization': `Bearer ${currentToken}`,
                'X-Tenant-ID': currentTenant
            }
        });
        const json = await res.json();
        
        // Handle unauth/error
        if (res.status === 401) return logout();

        const dataArr = Array.isArray(json.data) ? json.data : [];
        const list = document.getElementById('query-list');
        list.innerHTML = '';
        
        const filteredData = dataArr.filter(q => 
            !search || q.query_text.toLowerCase().includes(search.toLowerCase())
        );

        document.getElementById('stat-unique-queries').textContent = filteredData.length;
        
        filteredData.forEach(q => {
            const tr = document.createElement('tr');
            tr.innerHTML = `
                <td style="color:var(--accent)">${q.query_hash.substring(0, 8)}</td>
                <td>${q.query_text.substring(0, 60)}...</td>
                <td><span class="tag">${q.dialect}</span></td>
                <td><button onclick="viewQuery('${q.query_hash}')" class="primary-btn small-btn">Intelligence</button></td>
            `;
            list.appendChild(tr);
        });
    } catch (e) {
        console.error("Fetch failed", e);
    }
}

// Detail Modal Management
async function viewQuery(hash) {
    const modal = document.getElementById('detail-modal');
    modal.classList.remove('hidden');
    document.getElementById('modal-query-hash').textContent = `Query: ${hash.substring(0, 12)}`;
    
    // UI Loading state
    document.getElementById('lineage-graph').innerHTML = '<div class="loader">Analysing lineage...</div>';
    
    try {
        const res = await fetch(`${API_BASE}/v1/queries/${hash}?include=lineage,suggestions`, {
            headers: { 'Authorization': `Bearer ${currentToken}`, 'X-Tenant-ID': currentTenant }
        });
        const q = await res.json();

        // 1. Lineage Tab
        const linCont = document.getElementById('lineage-graph');
        linCont.innerHTML = '<table class="table-container"><thead><tr><th>Asset</th><th>Column</th><th>Clause</th></tr></thead><tbody id="lineage-rows"></tbody></table>';
        const tbody = document.getElementById('lineage-rows');
        q.lineage.forEach(l => {
            const row = `<tr><td>${l.table_name}</td><td style="color:var(--accent)">${l.column_name}</td><td>${l.clause_type}</td></tr>`;
            tbody.innerHTML += row;
        });

        // 2. AI Tab
        const aiCont = document.getElementById('ai-suggestions-grid');
        aiCont.innerHTML = '';
        if (q.suggestions) {
            const sug = q.suggestions.suggestions;
            const cost = sug.estimated_cost || 0.00;
            const savings = sug.savings_potential || 0;
            
            aiCont.innerHTML = `
                <div class="row" style="display:flex; gap:1rem; margin-bottom: 2rem;">
                    <div class="cost-badge">Est. Cost: $${cost.toFixed(2)}</div>
                    <div class="savings-badge">🔥 SAVINGS potential: ${Math.round(savings*100)}%</div>
                </div>
                <h3>Optimizations</h3>
                <ul>${sug.performance_warnings.map(w => `<li>${w}</li>`).join('')}</ul>
                <h3 style="margin-top:2rem">Optimized Query</h3>
                <pre class="sql-banner">${sug.optimized_query}</pre>
            `;
        }

        // 3. SQL Tab
        document.getElementById('modal-query-text').textContent = q.query_text;

        // Reset to Lineage tab
        switchModalTab('lineage');

    } catch (e) {
        console.error(e);
    }
}

function switchModalTab(tab) {
    document.querySelectorAll('.modal-tab-btn').forEach(b => b.classList.remove('active'));
    document.getElementById(`tab-${tab}`).classList.add('active');
    
    document.querySelectorAll('.tab-panel').forEach(p => p.classList.add('hidden'));
    document.getElementById(`modal-content-${tab}`).classList.remove('hidden');
}

function closeModal() {
    document.getElementById('detail-modal').classList.add('hidden');
}
