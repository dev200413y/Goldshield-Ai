/**
 * GoldShield AI — Frontend Application Logic
 * Handles form submission, agent pipeline animation, verdict display, and dashboard updates.
 */

const API_BASE = '';  // Same origin

// ─── State ──────────────────────────────────────────────────────────────────
let selectedFiles = [];
let currentAppraisalId = null;

// ─── DOM Elements ───────────────────────────────────────────────────────────
const form = document.getElementById('appraisalForm');
const photoInput = document.getElementById('photoInput');
const photoUploadArea = document.getElementById('photoUploadArea');
const photoPreviews = document.getElementById('photoPreviews');
const submitBtn = document.getElementById('submitBtn');
const resetFormBtn = document.getElementById('resetFormBtn');

const pipelineContainer = document.getElementById('pipelineContainer');
const verdictPanel = document.getElementById('verdictPanel');
const valuationPanel = document.getElementById('valuationPanel');
const fingerprintPanel = document.getElementById('fingerprintPanel');

// ─── Initialize ─────────────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
    loadDashboardStats();
    loadAppraisals();
    setupPhotoUpload();
    setupFormHandlers();
});

// ─── Photo Upload ───────────────────────────────────────────────────────────
function setupPhotoUpload() {
    photoUploadArea.addEventListener('click', () => photoInput.click());

    photoUploadArea.addEventListener('dragover', (e) => {
        e.preventDefault();
        photoUploadArea.classList.add('drag-over');
    });

    photoUploadArea.addEventListener('dragleave', () => {
        photoUploadArea.classList.remove('drag-over');
    });

    photoUploadArea.addEventListener('drop', (e) => {
        e.preventDefault();
        photoUploadArea.classList.remove('drag-over');
        handleFiles(e.dataTransfer.files);
    });

    photoInput.addEventListener('change', (e) => {
        handleFiles(e.target.files);
    });
}

function handleFiles(files) {
    for (const file of files) {
        if (file.type.startsWith('image/')) {
            selectedFiles.push(file);
        }
    }
    renderPhotoPreviews();
}

function renderPhotoPreviews() {
    photoPreviews.innerHTML = '';
    selectedFiles.forEach((file, idx) => {
        const reader = new FileReader();
        reader.onload = (e) => {
            const img = document.createElement('img');
            img.src = e.target.result;
            img.className = 'photo-preview';
            img.title = file.name;
            img.addEventListener('click', () => {
                selectedFiles.splice(idx, 1);
                renderPhotoPreviews();
            });
            photoPreviews.appendChild(img);
        };
        reader.readAsDataURL(file);
    });

    // Update upload area text
    const uploadText = photoUploadArea.querySelector('.upload-text');
    if (selectedFiles.length > 0) {
        uploadText.innerHTML = `<strong>${selectedFiles.length} photo(s) selected</strong><br>Click to add more or click preview to remove`;
    } else {
        uploadText.innerHTML = `<strong>Click to upload</strong> or drag & drop<br>4–10 multi-angle photos recommended`;
    }
}

// ─── Form Handlers ──────────────────────────────────────────────────────────
function setupFormHandlers() {
    form.addEventListener('submit', handleSubmit);
    resetFormBtn.addEventListener('click', resetForm);
}

function resetForm() {
    form.reset();
    selectedFiles = [];
    renderPhotoPreviews();
    pipelineContainer.classList.remove('active');
    verdictPanel.classList.remove('active');
    valuationPanel.classList.remove('active');
    fingerprintPanel.classList.remove('active');
    resetAgentCards();
}

async function handleSubmit(e) {
    e.preventDefault();

    const customerRef = document.getElementById('customerRef').value;
    const itemDescription = document.getElementById('itemDescription').value;
    const itemType = document.getElementById('itemType').value;
    const weightGrams = document.getElementById('weightGrams').value;
    const declaredPurity = document.getElementById('declaredPurity').value;
    const loanAmount = document.getElementById('loanAmount').value || 0;

    if (!customerRef || !weightGrams) {
        showToast('Please fill in required fields', 'error');
        return;
    }

    if (selectedFiles.length === 0) {
        showToast('Please upload at least one photo for verification', 'error');
        return;
    }

    submitBtn.disabled = true;
    submitBtn.innerHTML = '<span class="spinner"></span> Processing...';

    try {
        // Step 1: Create appraisal
        const formData = new FormData();
        formData.append('customer_ref', customerRef);
        formData.append('item_description', itemDescription || `${declaredPurity} Gold ${itemType}`);
        formData.append('item_type', itemType);
        formData.append('weight_grams', weightGrams);
        formData.append('declared_purity', declaredPurity);
        formData.append('branch_id', 'BR-001');

        selectedFiles.forEach(file => {
            formData.append('photos', file);
        });

        showToast('Creating appraisal...', 'success');
        const createRes = await fetch(`${API_BASE}/api/appraisal`, {
            method: 'POST',
            body: formData,
        });

        if (!createRes.ok) throw new Error('Failed to create appraisal');
        const createData = await createRes.json();
        currentAppraisalId = createData.appraisal_id;

        // Step 2: Show pipeline and animate agents
        showPipeline();
        showVolumeReconScanning();
        await animateAgentRunning();

        // Step 3: Run verification
        showToast('Running AI verification pipeline...', 'success');
        const verifyRes = await fetch(`${API_BASE}/api/appraisal/${currentAppraisalId}/verify`, {
            method: 'POST',
        });

        if (!verifyRes.ok) throw new Error('Verification failed');
        const verifyData = await verifyRes.json();

        // Step 4: Update agent cards with results
        updateAgentResults(verifyData.verdict);

        // Step 5: Show verdict
        showVerdict(verifyData.verdict);

        // Step 6: Show fingerprint
        showFingerprint(verifyData.fingerprint);

        // Step 7: Run valuation
        const valFormData = new FormData();
        valFormData.append('appraisal_id', currentAppraisalId);
        valFormData.append('loan_amount', loanAmount);

        const valRes = await fetch(`${API_BASE}/api/valuation`, {
            method: 'POST',
            body: valFormData,
        });

        if (valRes.ok) {
            const valData = await valRes.json();
            showValuation(valData.valuation);
        }

        // Step 8: Refresh dashboard
        loadDashboardStats();
        loadAppraisals();

        showToast('Verification complete!', 'success');

    } catch (err) {
        console.error(err);
        showToast(`Error: ${err.message}`, 'error');
    } finally {
        submitBtn.disabled = false;
        submitBtn.innerHTML = '🛡️ Run Full Verification';
    }
}

// ─── Agent Pipeline Animation ───────────────────────────────────────────────
function showPipeline() {
    pipelineContainer.classList.add('active');
    resetAgentCards();
}

function resetAgentCards() {
    const cards = document.querySelectorAll('.agent-card');
    cards.forEach(card => {
        card.className = 'agent-card waiting';
        card.querySelector('.agent-status').textContent = 'Waiting';
        card.querySelector('.agent-provider').textContent = '';
    });
}

async function animateAgentRunning() {
    const agents = ['density', 'surface', 'hallmark', 'touchstone', 'light', 'risk'];
    for (const agent of agents) {
        const card = document.getElementById(`agent-${agent}`);
        if (card) {
            card.className = 'agent-card running';
            card.querySelector('.agent-status').textContent = 'Analyzing...';
        }
        await sleep(300);
    }
}

function updateAgentResults(verdict) {
    const agentMap = {
        'density': { result: verdict.density_result, key: 'result' },
        'surface': { result: verdict.surface_result, key: 'result' },
        'hallmark': { result: verdict.hallmark_result, key: 'result' },
        'touchstone': { result: verdict.touchstone_result, key: 'result' },
        'light': { result: verdict.light_signature_result, key: 'result' },
    };

    for (const [agentId, info] of Object.entries(agentMap)) {
        const card = document.getElementById(`agent-${agentId}`);
        if (!card) continue;

        const result = info.result;
        if (!result) {
            card.className = 'agent-card inconclusive';
            card.querySelector('.agent-status').textContent = 'No Data';
            continue;
        }

        const status = (result.result || 'PASS').toUpperCase();
        if (status === 'PASS') {
            card.className = 'agent-card pass';
            card.querySelector('.agent-status').textContent = '✓ PASS';
        } else if (status === 'FLAG') {
            card.className = 'agent-card flag';
            card.querySelector('.agent-status').textContent = '⚠ FLAG';
        } else {
            card.className = 'agent-card inconclusive';
            card.querySelector('.agent-status').textContent = '? INCONCLUSIVE';
        }

        // Show provider
        const provider = result.provider || 'mock';
        card.querySelector('.agent-provider').textContent = `Powered by: ${provider}`;
    }

    // Risk Officer
    const riskCard = document.getElementById('agent-risk');
    if (riskCard) {
        if (verdict.escalated) {
            riskCard.className = 'agent-card flag';
            riskCard.querySelector('.agent-status').textContent = '⚠ ESCALATED';
        } else {
            riskCard.className = 'agent-card pass';
            riskCard.querySelector('.agent-status').textContent = '✓ CLEAR';
        }
        riskCard.querySelector('.agent-provider').textContent = `Score: ${verdict.authenticity_score}/100`;
    }

    // Update provider badge
    const providers = new Set();
    for (const info of Object.values(agentMap)) {
        if (info.result && info.result.provider) providers.add(info.result.provider);
    }
    const badge = document.getElementById('providerBadge');
    badge.querySelector('span:last-child').textContent = 
        `Powered by: ${[...providers].join(', ') || 'mock'}`;
}

// ─── 3D Volume Reconstruction Animation ──────────────────────────────────────
function showVolumeReconScanning() {
    const reconPanel = document.getElementById('volumeReconPanel');
    if (reconPanel) reconPanel.classList.add('active');
    
    // Reset stats
    document.getElementById('reconVolume').textContent = 'Scanning...';
    document.getElementById('reconDensity').textContent = 'Scanning...';
    
    const container = document.getElementById('modelViewerContainer');
    if (container) container.classList.remove('complete');
    
    // Inject photo into the 3D space
    const firstPhoto = document.querySelector('.photo-preview');
    if (firstPhoto && container) {
        const oldImg = container.querySelector('.injected-3d-model');
        if (oldImg) oldImg.remove();
        
        const img = document.createElement('img');
        img.src = firstPhoto.src;
        img.className = 'injected-3d-model';
        // Append to container (behind rings), not to the spinning ring itself
        container.appendChild(img);
    }
}

// ─── Verdict Display ────────────────────────────────────────────────────────
function showVerdict(verdict) {
    verdictPanel.classList.add('active');
    
    // Complete 3D Model Stats
    if (verdict.density_result) {
        document.getElementById('reconVolume').textContent = `${verdict.density_result.estimated_volume_cm3} cm³`;
        document.getElementById('reconDensity').textContent = `${verdict.density_result.density_gcm3} g/cm³`;
        
        const container = document.getElementById('modelViewerContainer');
        if (container) container.classList.add('complete');
    }

    // Animate gauges
    animateGauge('authenticityGauge', 'authenticityValue', verdict.authenticity_score,
        verdict.authenticity_score >= 70 ? 'var(--success)' : verdict.authenticity_score >= 40 ? 'var(--warning)' : 'var(--danger)');
    animateGauge('fraudGauge', 'fraudValue', verdict.fraud_probability, 'var(--danger)');
    animateGauge('confidenceGauge', 'confidenceValue', verdict.confidence, 'var(--info)');

    // Reasoning
    const reasoningBox = document.getElementById('reasoningBox');
    const reasoning = verdict.reasoning || '';
    reasoningBox.innerHTML = reasoning
        .split('\n')
        .map(line => {
            if (line.startsWith('✓')) return `<div class="pass-line">${escapeHtml(line)}</div>`;
            if (line.startsWith('⚠')) return `<div class="flag-line">${escapeHtml(line)}</div>`;
            if (line.startsWith('⚡')) return `<div class="info-line">${escapeHtml(line)}</div>`;
            if (line.startsWith('→') || line.startsWith('\n→')) return `<div class="conclusion-line">${escapeHtml(line)}</div>`;
            return `<div>${escapeHtml(line)}</div>`;
        })
        .join('');

    // Recommendation
    const recBox = document.getElementById('recommendationBox');
    recBox.textContent = verdict.recommendation || '';
    recBox.className = `recommendation-box ${verdict.escalated ? 'escalated' : ''}`;

    // Scroll to verdict
    verdictPanel.scrollIntoView({ behavior: 'smooth', block: 'start' });
}

function animateGauge(gaugeId, valueId, targetValue, color) {
    const gauge = document.getElementById(gaugeId);
    const valueEl = document.getElementById(valueId);

    gauge.style.setProperty('--gauge-color', color);

    let current = 0;
    const duration = 1000;
    const startTime = Date.now();

    function step() {
        const elapsed = Date.now() - startTime;
        const progress = Math.min(elapsed / duration, 1);
        const eased = 1 - Math.pow(1 - progress, 3); // ease-out cubic
        current = Math.round(eased * targetValue);

        gauge.style.setProperty('--gauge-value', current);
        valueEl.textContent = current;

        if (progress < 1) requestAnimationFrame(step);
    }

    requestAnimationFrame(step);
}

// ─── Valuation Display ──────────────────────────────────────────────────────
function showValuation(valuation) {
    valuationPanel.classList.add('active');

    const grid = document.getElementById('valuationGrid');
    const ltvClass = valuation.violation ? 'violation' : '';

    grid.innerHTML = `
        <div class="val-item">
            <div class="val-value">₹${formatNumber(valuation.gold_rate_per_gram)}</div>
            <div class="val-label">Rate / Gram</div>
        </div>
        <div class="val-item">
            <div class="val-value">₹${formatNumber(valuation.fair_market_value)}</div>
            <div class="val-label">Fair Market Value</div>
        </div>
        <div class="val-item ${ltvClass}">
            <div class="val-value">${valuation.ltv_percent.toFixed(1)}%</div>
            <div class="val-label">LTV ${valuation.violation ? '⚠ EXCEEDS CAP' : `(Cap: ${valuation.ltv_cap}%)`}</div>
        </div>
        <div class="val-item">
            <div class="val-value">${valuation.rate_source}</div>
            <div class="val-label">Rate Source</div>
        </div>
    `;
}

// ─── Fingerprint Display ────────────────────────────────────────────────────
function showFingerprint(fingerprint) {
    fingerprintPanel.classList.add('active');

    const display = document.getElementById('fingerprintDisplay');
    display.innerHTML = `
        <div>
            <div style="font-size: 3rem;">🔐</div>
        </div>
        <div>
            <div class="fingerprint-id">${fingerprint.fingerprint_id}</div>
            <div style="font-size: 0.8rem; color: var(--dark-100); margin-top: 4px;">Digital Gold Fingerprint</div>
        </div>
        <div style="flex: 1;">
            <div style="font-size: 0.75rem; color: var(--dark-200); margin-bottom: 4px;">Visual Hash</div>
            <div class="fingerprint-hash">${fingerprint.visual_hash}</div>
            ${fingerprint.hallmark_signature ? `
                <div style="font-size: 0.75rem; color: var(--dark-200); margin-top: 8px; margin-bottom: 4px;">Hallmark</div>
                <div class="fingerprint-hash">${fingerprint.hallmark_signature}</div>
            ` : ''}
            ${fingerprint.density_signature ? `
                <div style="font-size: 0.75rem; color: var(--dark-200); margin-top: 8px; margin-bottom: 4px;">Density Signature</div>
                <div class="fingerprint-hash">${fingerprint.density_signature} g/cm³</div>
            ` : ''}
        </div>
    `;
}

// ─── Dashboard Stats ────────────────────────────────────────────────────────
async function loadDashboardStats() {
    try {
        const res = await fetch(`${API_BASE}/api/dashboard/stats`);
        if (!res.ok) return;
        const stats = await res.json();

        document.getElementById('statTotal').textContent = stats.total_appraisals || 0;
        document.getElementById('statToday').textContent = stats.today_appraisals || 0;
        document.getElementById('statFlagged').textContent = stats.flagged_cases || 0;
        document.getElementById('statAvgScore').textContent = 
            stats.average_authenticity_score ? `${stats.average_authenticity_score}` : '—';
        document.getElementById('statTotalGrams').textContent = `${stats.total_gold_grams || 0}g`;
        document.getElementById('statPortfolio').textContent = `₹${formatNumber(stats.total_portfolio_value || 0)}`;
    } catch (err) {
        console.warn('Could not load dashboard stats:', err);
    }
}

// ─── Appraisals Table ───────────────────────────────────────────────────────
async function loadAppraisals() {
    try {
        const res = await fetch(`${API_BASE}/api/appraisals`);
        if (!res.ok) return;
        const data = await res.json();

        const tbody = document.getElementById('appraisalsBody');

        if (!data.appraisals || data.appraisals.length === 0) {
            tbody.innerHTML = `<tr><td colspan="8">
                <div class="empty-state">
                    <div class="empty-icon">📋</div>
                    <p>No appraisals yet. Create your first one above.</p>
                </div>
            </td></tr>`;
            return;
        }

        tbody.innerHTML = data.appraisals.map(a => {
            const score = a.authenticity_score;
            const scoreClass = score >= 70 ? 'high' : score >= 40 ? 'medium' : score !== null ? 'low' : '';
            const statusClass = a.escalated ? 'flag' : score !== null ? 'pass' : 'pending';
            const statusText = a.escalated ? '⚠ Escalated' : score !== null ? '✓ Verified' : '⏳ Pending';

            return `<tr>
                <td>#${a.id}</td>
                <td>${escapeHtml(a.customer_ref)}</td>
                <td>${escapeHtml(a.item_description || '—')}</td>
                <td>${a.weight_grams}g</td>
                <td>${a.declared_purity || '22K'}</td>
                <td class="score-cell ${scoreClass}">${score !== null && score !== undefined ? score : '—'}</td>
                <td><span class="status-badge ${statusClass}">${statusText}</span></td>
                <td>${formatDate(a.created_at)}</td>
            </tr>`;
        }).join('');
    } catch (err) {
        console.warn('Could not load appraisals:', err);
    }
}

// ─── Utilities ──────────────────────────────────────────────────────────────
function sleep(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
}

function escapeHtml(str) {
    if (!str) return '';
    const div = document.createElement('div');
    div.textContent = str;
    return div.innerHTML;
}

function formatNumber(num) {
    if (num >= 10000000) return (num / 10000000).toFixed(2) + ' Cr';
    if (num >= 100000) return (num / 100000).toFixed(2) + ' L';
    if (num >= 1000) return num.toLocaleString('en-IN');
    return num.toString();
}

function formatDate(dateStr) {
    if (!dateStr) return '—';
    try {
        const d = new Date(dateStr);
        return d.toLocaleDateString('en-IN', { day: '2-digit', month: 'short', year: 'numeric' });
    } catch {
        return dateStr;
    }
}

function showToast(message, type = 'success') {
    const container = document.getElementById('toastContainer');
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    toast.innerHTML = `
        <span>${type === 'success' ? '✓' : type === 'error' ? '✗' : '⚠'}</span>
        <span>${escapeHtml(message)}</span>
    `;
    container.appendChild(toast);
    setTimeout(() => {
        toast.style.opacity = '0';
        toast.style.transform = 'translateX(100px)';
        toast.style.transition = 'all 0.3s ease-in';
        setTimeout(() => toast.remove(), 300);
    }, 4000);
}
