let currentToken = localStorage.getItem('api_token');
const API_BASE = "http://localhost:8000";

if (currentToken) {
    showDashboard();
}

function showTab(tab) {
    document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
    document.querySelectorAll('.tab-content').forEach(c => c.classList.add('hidden'));
    
    if (tab === 'login') {
        document.querySelector('.tab-btn:nth-child(1)').classList.add('active');
        document.getElementById('login-form').classList.remove('hidden');
    } else {
        document.querySelector('.tab-btn:nth-child(2)').classList.add('active');
        document.getElementById('register-form').classList.remove('hidden');
    }
}

async function register() {
    const cid = document.getElementById('company-id').value;
    const cname = document.getElementById('company-name').value;
    
    try {
        const res = await fetch(`${API_BASE}/v1/onboarding/register?company_id=${cid}&company_name=${cname}`, {
            method: 'POST'
        });
        const data = await res.json();
        if (data.api_token) {
            document.getElementById('registration-success').classList.remove('hidden');
            document.getElementById('new-token-display').textContent = data.api_token;
        }
    } catch (e) {
        alert("Registration failed: " + e.message);
    }
}

function login() {
    const token = document.getElementById('api-token-input').value;
    if (token) {
        localStorage.setItem('api_token', token);
        currentToken = token;
        showDashboard();
    }
}

function logout() {
    localStorage.removeItem('api_token');
    location.reload();
}

function showDashboard() {
    document.getElementById('onboarding-section').classList.add('hidden');
    document.getElementById('dashboard-section').classList.remove('hidden');
    document.getElementById('logout-btn').classList.remove('hidden');
    fetchQueries();
}

async function fetchQueries() {
    try {
        const res = await fetch(`${API_BASE}/v1/queries`, {
            headers: { 'Authorization': `Bearer ${currentToken}` }
        });
        const json = await res.json();
        const list = document.getElementById('query-list');
        list.innerHTML = '';
        
        document.getElementById('stat-unique-queries').textContent = json.data.length;
        
        json.data.forEach(q => {
            const tr = document.createElement('tr');
            tr.innerHTML = `
                <td>${q.query_hash.substring(0, 8)}...</td>
                <td>${q.query_text.substring(0, 50)}...</td>
                <td>${q.dialect}</td>
                <td><button onclick="viewQuery('${q.query_hash}')" class="primary-btn small">View</button></td>
            `;
            list.appendChild(tr);
        });
    } catch (e) {
        console.error(e);
    }
}

async function viewQuery(hash) {
    // Show modal and fill data
    document.getElementById('detail-modal').classList.remove('hidden');
    // Fetch details...
}

function closeModal() {
    document.getElementById('detail-modal').classList.add('hidden');
}
