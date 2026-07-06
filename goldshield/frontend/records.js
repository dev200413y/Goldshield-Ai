/**
 * GoldShield AI — Records Screen
 * Displays all processed jewelry with full details, 3D model, certificate, etc.
 */

class RecordsManager {
    constructor() {
        this.records = [];
        this.filteredRecords = [];
        this.currentFilter = 'all';
        this.searchQuery = '';
        this.detailViewer = null; // Three.js viewer for detail modal
    }

    /**
     * Initialize the records screen
     */
    init() {
        this.setupEventListeners();
        this.loadRecords();
    }

    /**
     * Setup event listeners
     */
    setupEventListeners() {
        const searchInput = document.getElementById('recordsSearch');
        if (searchInput) {
            searchInput.addEventListener('input', (e) => {
                this.searchQuery = e.target.value.toLowerCase();
                this.filterAndRender();
            });
        }

        const filterBtns = document.querySelectorAll('.records-filter-btn');
        filterBtns.forEach(btn => {
            btn.addEventListener('click', () => {
                filterBtns.forEach(b => b.classList.remove('active'));
                btn.classList.add('active');
                this.currentFilter = btn.dataset.filter;
                this.filterAndRender();
            });
        });

        // Close detail modal
        const closeBtn = document.getElementById('closeRecordDetail');
        if (closeBtn) {
            closeBtn.addEventListener('click', () => this.closeDetail());
        }

        // Close on backdrop click
        const modal = document.getElementById('recordDetailModal');
        if (modal) {
            modal.addEventListener('click', (e) => {
                if (e.target === modal) this.closeDetail();
            });
        }
    }

    /**
     * Load all records from API
     */
    async loadRecords() {
        try {
            const res = await fetch('/api/appraisals/detailed');
            if (!res.ok) throw new Error('Failed to load records');
            const data = await res.json();
            this.records = data.appraisals || [];
            this.filterAndRender();
        } catch (err) {
            console.warn('Could not load records:', err);
            // Try fallback to basic endpoint
            try {
                const res = await fetch('/api/appraisals');
                if (res.ok) {
                    const data = await res.json();
                    this.records = data.appraisals || [];
                    this.filterAndRender();
                }
            } catch (e) {
                console.error('Records load failed completely:', e);
            }
        }
    }

    /**
     * Filter records and render
     */
    filterAndRender() {
        let filtered = [...this.records];

        // Status filter
        if (this.currentFilter === 'verified') {
            filtered = filtered.filter(r => r.authenticity_score !== null && r.authenticity_score !== undefined);
        } else if (this.currentFilter === 'flagged') {
            filtered = filtered.filter(r => r.escalated === 1 || r.escalated === true);
        } else if (this.currentFilter === 'pending') {
            filtered = filtered.filter(r => r.authenticity_score === null || r.authenticity_score === undefined);
        }

        // Search filter
        if (this.searchQuery) {
            filtered = filtered.filter(r =>
                (r.customer_ref || '').toLowerCase().includes(this.searchQuery) ||
                (r.item_description || '').toLowerCase().includes(this.searchQuery) ||
                String(r.id).includes(this.searchQuery)
            );
        }

        this.filteredRecords = filtered;
        this.renderGrid();
    }

    /**
     * Render the records grid
     */
    renderGrid() {
        const container = document.getElementById('recordsGrid');
        if (!container) return;

        if (this.filteredRecords.length === 0) {
            container.innerHTML = `
                <div class="records-empty">
                    <div class="empty-icon">📋</div>
                    <p>No records found</p>
                    <span>Process jewelry on the Dashboard to see records here</span>
                </div>
            `;
            return;
        }

        container.innerHTML = this.filteredRecords.map(record => {
            const score = record.authenticity_score;
            const scoreClass = score >= 70 ? 'high' : score >= 40 ? 'medium' : score !== null && score !== undefined ? 'low' : 'pending';
            const statusText = record.escalated ? '⚠ Flagged' : score !== null && score !== undefined ? '✓ Verified' : '⏳ Pending';
            const statusClass = record.escalated ? 'flag' : score !== null && score !== undefined ? 'pass' : 'pending';
            const itemIcon = this._getItemIcon(record.item_type);

            return `
                <div class="record-card animate-in" onclick="recordsManager.openDetail(${record.id})">
                    <div class="record-card-header">
                        <div class="record-item-icon">${itemIcon}</div>
                        <span class="record-id">#${record.id}</span>
                        <span class="status-badge ${statusClass}">${statusText}</span>
                    </div>
                    <div class="record-card-body">
                        <div class="record-item-type">${this._formatItemType(record.item_type)} — ${record.declared_purity || '22K'}</div>
                        <div class="record-description">${this._escapeHtml(record.item_description || 'Gold Jewelry')}</div>
                        <div class="record-meta">
                            <span>👤 ${this._escapeHtml(record.customer_ref)}</span>
                            <span>⚖️ ${record.weight_grams}g</span>
                        </div>
                    </div>
                    <div class="record-card-footer">
                        <div class="record-score-display">
                            <div class="mini-gauge ${scoreClass}">
                                <svg viewBox="0 0 36 36" class="circular-chart">
                                    <path class="circle-bg" d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831" />
                                    <path class="circle" stroke-dasharray="${score || 0}, 100" d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831" />
                                    <text x="18" y="21" class="percentage">${score !== null && score !== undefined ? score : '—'}</text>
                                </svg>
                            </div>
                        </div>
                        <div class="record-date">${this._formatDate(record.created_at)}</div>
                    </div>
                </div>
            `;
        }).join('');

        // Update records count
        const countEl = document.getElementById('recordsCount');
        if (countEl) countEl.textContent = `${this.filteredRecords.length} record(s)`;
    }

    /**
     * Open detail view for a record
     */
    async openDetail(appraisalId) {
        const modal = document.getElementById('recordDetailModal');
        const content = document.getElementById('recordDetailContent');
        if (!modal || !content) return;

        modal.classList.add('active');
        content.innerHTML = '<div class="detail-loading"><div class="spinner"></div><p>Loading details...</p></div>';

        try {
            const res = await fetch(`/api/appraisal/${appraisalId}/full`);
            let data;
            if (res.ok) {
                data = await res.json();
            } else {
                // Fallback to basic endpoint
                const basicRes = await fetch(`/api/appraisal/${appraisalId}`);
                if (!basicRes.ok) throw new Error('Record not found');
                data = await basicRes.json();
            }

            this.renderDetail(data, appraisalId);
        } catch (err) {
            content.innerHTML = `<div class="detail-error">❌ Error loading record: ${err.message}</div>`;
        }
    }

    /**
     * Render detail view content
     */
    renderDetail(data, appraisalId) {
        const content = document.getElementById('recordDetailContent');
        if (!content) return;

        const verification = data.verification || {};
        const valuation = data.valuation || {};
        const fingerprint = data.fingerprint || {};
        const score = verification.authenticity_score;
        const scoreClass = score >= 70 ? 'high' : score >= 40 ? 'medium' : score !== null && score !== undefined ? 'low' : '';

        content.innerHTML = `
            <!-- Header -->
            <div class="detail-header">
                <div class="detail-title-section">
                    <h2>${this._getItemIcon(data.item_type)} ${this._escapeHtml(data.item_description || 'Gold Jewelry')}</h2>
                    <span class="detail-id">Appraisal #${appraisalId}</span>
                </div>
                <div class="detail-score-big ${scoreClass}">
                    ${score !== null && score !== undefined ? score : '—'}
                    <span>/ 100</span>
                </div>
            </div>

            <!-- Original Photos -->
            ${data.photos_count && data.photos_count > 0 ? `
            <div class="detail-section">
                <div class="detail-section-title">📸 Uploaded Photos</div>
                <div class="detail-photos-grid" style="display: flex; gap: 12px; overflow-x: auto; padding-bottom: 8px; margin-bottom: 12px;">
                    ${Array.from({length: data.photos_count}).map((_, i) => `
                        <a href="/api/photos/${appraisalId}/${i}" target="_blank">
                            <img src="/api/photos/${appraisalId}/${i}" alt="Jewelry Photo ${i+1}" style="height: 140px; border-radius: 8px; object-fit: cover; border: 1px solid var(--gold-700); cursor: zoom-in;">
                        </a>
                    `).join('')}
                </div>
            </div>
            ` : ''}

            <!-- ═══ PANEL 1: 3D Visual Reference ═══ -->
            <div class="detail-section">
                <div class="detail-section-title">🧊 3D Visual Reference</div>
                <div class="model-viewer-wrapper" style="height: 300px; margin-bottom: 12px;">
                    <model-viewer
                        id="detailGlbViewer"
                        alt="AI-generated 3D visual reference of jewelry item"
                        auto-rotate
                        camera-controls
                        shadow-intensity="1"
                        style="width: 100%; height: 100%; display: none;"
                    ></model-viewer>
                    <!-- Fallback: Three.js procedural model -->
                    <div class="viewer3d-canvas-wrapper" id="detail3DContainer" style="width: 100%; height: 100%;"></div>
                </div>
                <div class="detail-3d-controls" style="display: flex; gap: 8px; justify-content: space-between; align-items: center;">
                    <button class="btn btn-sm btn-secondary" onclick="recordsManager.resetDetailCamera()">🔄 Reset View</button>
                    <span class="detail-3d-hint" style="font-size: 0.75rem; color: var(--dark-200);">🖱️ Drag to rotate • Scroll to zoom</span>
                </div>
            </div>

            <!-- ═══ PANEL 2: Measured Volume & Density ═══ -->
            <div class="detail-section">
                <div class="detail-section-title">⚖️ Measured Volume & Density</div>
                <div class="measurement-grid" style="grid-template-columns: repeat(3, 1fr); gap: 12px; display: grid;">
                    <div class="measurement-card" style="padding: 12px;">
                        <div class="measurement-icon" style="font-size: 1.2rem; margin-bottom: 4px;">📐</div>
                        <div class="measurement-label" style="font-size: 0.7rem;">Estimated Volume</div>
                        <div class="measurement-value" style="font-size: 1.2rem;">${verification.density_result && verification.density_result.volume_cm3 ? verification.density_result.volume_cm3.toFixed(2) : '—'}</div>
                        <div class="measurement-unit" style="font-size: 0.7rem;">cm³</div>
                    </div>
                    <div class="measurement-card" style="padding: 12px;">
                        <div class="measurement-icon" style="font-size: 1.2rem; margin-bottom: 4px;">⚖️</div>
                        <div class="measurement-label" style="font-size: 0.7rem;">Computed Density</div>
                        <div class="measurement-value" style="font-size: 1.2rem; color: var(--gold-400);">${verification.density_result && verification.density_result.density_gcm3 ? verification.density_result.density_gcm3.toFixed(2) : '—'}</div>
                        <div class="measurement-unit" style="font-size: 0.7rem;">g/cm³</div>
                    </div>
                    <div class="measurement-card" style="padding: 12px;">
                        <div class="measurement-icon" style="font-size: 1.2rem; margin-bottom: 4px;">🔍</div>
                        <div class="measurement-label" style="font-size: 0.7rem;">Reference Scale</div>
                        <div class="measurement-value" style="font-size: 1.2rem;">${verification.density_result && verification.density_result.scale_detected ? 'Yes' : 'No'}</div>
                        <div class="measurement-unit" style="font-size: 0.7rem;">${verification.density_result && verification.density_result.method ? verification.density_result.method : ''}</div>
                    </div>
                </div>
            </div>

            <!-- Customer & Item Info Grid -->
            <div class="detail-info-grid">
                <div class="detail-info-card">
                    <div class="detail-info-label">👤 Customer</div>
                    <div class="detail-info-value">${this._escapeHtml(data.customer_ref)}</div>
                </div>
                <div class="detail-info-card">
                    <div class="detail-info-label">📿 Item Type</div>
                    <div class="detail-info-value">${this._formatItemType(data.item_type)}</div>
                </div>
                <div class="detail-info-card">
                    <div class="detail-info-label">⚖️ Weight</div>
                    <div class="detail-info-value">${data.weight_grams}g</div>
                </div>
                <div class="detail-info-card">
                    <div class="detail-info-label">✨ Purity</div>
                    <div class="detail-info-value">${data.declared_purity || '22K'}</div>
                </div>
                <div class="detail-info-card">
                    <div class="detail-info-label">🏦 Branch</div>
                    <div class="detail-info-value">${data.branch_id || 'BR-001'}</div>
                </div>
                <div class="detail-info-card">
                    <div class="detail-info-label">📅 Date</div>
                    <div class="detail-info-value">${this._formatDate(data.created_at)}</div>
                </div>
            </div>

            <!-- Verification Results -->
            ${verification.authenticity_score !== undefined ? `
            <div class="detail-section">
                <div class="detail-section-title">🛡️ Verification Results</div>
                <div class="detail-verification-grid">
                    <div class="detail-gauge-card">
                        <div class="detail-gauge ${score >= 70 ? 'high' : score >= 40 ? 'medium' : 'low'}">
                            <svg viewBox="0 0 36 36" class="circular-chart-lg">
                                <path class="circle-bg" d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831" />
                                <path class="circle" stroke-dasharray="${score || 0}, 100" d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831" />
                                <text x="18" y="21" class="percentage">${score}</text>
                            </svg>
                            <div class="gauge-text">Authenticity</div>
                        </div>
                    </div>
                    <div class="detail-gauge-card">
                        <div class="detail-gauge low">
                            <svg viewBox="0 0 36 36" class="circular-chart-lg">
                                <path class="circle-bg" d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831" />
                                <path class="circle" stroke-dasharray="${verification.fraud_probability || 0}, 100" d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831" />
                                <text x="18" y="21" class="percentage">${verification.fraud_probability || 0}</text>
                            </svg>
                            <div class="gauge-text">Fraud Risk</div>
                        </div>
                    </div>
                    <div class="detail-gauge-card">
                        <div class="detail-gauge high">
                            <svg viewBox="0 0 36 36" class="circular-chart-lg">
                                <path class="circle-bg" d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831" />
                                <path class="circle" stroke-dasharray="${verification.confidence || 0}, 100" d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831" />
                                <text x="18" y="21" class="percentage">${verification.confidence || 0}</text>
                            </svg>
                            <div class="gauge-text">Confidence</div>
                        </div>
                    </div>
                </div>

                <!-- Inspector Results -->
                <div class="detail-inspectors">
                    ${this._renderInspectorResult('⚖️ Density', verification.density_result)}
                    ${this._renderInspectorResult('🔎 Surface', verification.surface_result)}
                    ${this._renderInspectorResult('🏛️ Hallmark', verification.hallmark_result)}
                    ${this._renderInspectorResult('💎 Touchstone', verification.touchstone_result)}
                    ${this._renderInspectorResult('💡 Light-Signature', verification.light_signature_result)}
                </div>

                ${verification.reasoning ? `
                <div class="detail-reasoning">
                    <div class="detail-reasoning-title">📝 AI Reasoning</div>
                    <div class="detail-reasoning-text">${this._escapeHtml(verification.reasoning)}</div>
                </div>
                ` : ''}

                ${verification.recommendation ? `
                <div class="detail-recommendation ${verification.escalated ? 'escalated' : ''}">
                    ${verification.escalated ? '⚠️' : '✅'} ${this._escapeHtml(verification.recommendation)}
                </div>
                ` : ''}
            </div>
            ` : '<div class="detail-section"><div class="detail-pending">⏳ Verification pending</div></div>'}

            <!-- Valuation Details -->
            ${valuation.fair_market_value ? `
            <div class="detail-section">
                <div class="detail-section-title">💰 Valuation & Bill</div>
                <div class="detail-valuation-grid">
                    <div class="detail-val-card">
                        <div class="detail-val-icon">📈</div>
                        <div class="detail-val-value">₹${this._formatNumber(valuation.gold_rate_per_gram)}</div>
                        <div class="detail-val-label">Rate/Gram (${valuation.rate_source || 'cached'})</div>
                    </div>
                    <div class="detail-val-card highlight">
                        <div class="detail-val-icon">💎</div>
                        <div class="detail-val-value">₹${this._formatNumber(valuation.fair_market_value)}</div>
                        <div class="detail-val-label">Fair Market Value</div>
                    </div>
                    <div class="detail-val-card ${valuation.violation ? 'danger' : ''}">
                        <div class="detail-val-icon">📊</div>
                        <div class="detail-val-value">${(valuation.ltv_percent || 0).toFixed(1)}%</div>
                        <div class="detail-val-label">LTV Ratio (Cap: ${valuation.ltv_cap || 75}%)</div>
                    </div>
                    <div class="detail-val-card">
                        <div class="detail-val-icon">🏦</div>
                        <div class="detail-val-value">₹${this._formatNumber(valuation.loan_amount_requested || 0)}</div>
                        <div class="detail-val-label">Loan Amount</div>
                    </div>
                </div>
            </div>
            ` : ''}

            <!-- Digital Fingerprint -->
            ${fingerprint.fingerprint_id ? `
            <div class="detail-section">
                <div class="detail-section-title">🔐 Digital Gold Fingerprint</div>
                <div class="detail-fingerprint">
                    <div class="detail-fp-icon">🔐</div>
                    <div class="detail-fp-info">
                        <div class="detail-fp-id">${fingerprint.fingerprint_id}</div>
                        <div class="detail-fp-meta">
                            <span>Visual Hash: <code>${fingerprint.visual_hash || '—'}</code></span>
                            ${fingerprint.hallmark_signature ? `<span>Hallmark: <code>${fingerprint.hallmark_signature}</code></span>` : ''}
                            ${fingerprint.density_signature ? `<span>Density: <code>${fingerprint.density_signature} g/cm³</code></span>` : ''}
                        </div>
                    </div>
                </div>
            </div>
            ` : ''}

            <!-- Certificate -->
            <div class="detail-section">
                <div class="detail-section-title">📜 Verification Certificate</div>
                <div class="detail-certificate" id="certificateSection">
                    <div class="certificate-inner">
                        <div class="cert-header">
                            <div class="cert-logo">🛡️</div>
                            <h3>GoldShield AI</h3>
                            <p>Gold Verification Certificate</p>
                        </div>
                        <div class="cert-divider"></div>
                        <div class="cert-body">
                            <div class="cert-row"><span>Certificate No:</span> <strong>GS-CERT-${String(appraisalId).padStart(6, '0')}</strong></div>
                            <div class="cert-row"><span>Date of Verification:</span> <strong>${this._formatDate(data.created_at)}</strong></div>
                            <div class="cert-row"><span>Item Description:</span> <strong>${this._escapeHtml(data.item_description || 'Gold Jewelry')}</strong></div>
                            <div class="cert-row"><span>Weight:</span> <strong>${data.weight_grams}g</strong></div>
                            <div class="cert-row"><span>Declared Purity:</span> <strong>${data.declared_purity || '22K'}</strong></div>
                            <div class="cert-row"><span>Authenticity Score:</span> <strong class="${scoreClass}">${score !== null && score !== undefined ? score + '/100' : 'Pending'}</strong></div>
                            ${valuation.fair_market_value ? `<div class="cert-row"><span>Fair Market Value:</span> <strong>₹${this._formatNumber(valuation.fair_market_value)}</strong></div>` : ''}
                            ${fingerprint.fingerprint_id ? `<div class="cert-row"><span>Digital Fingerprint:</span> <strong>${fingerprint.fingerprint_id}</strong></div>` : ''}
                            <div class="cert-row"><span>Verification Status:</span> <strong>${verification.escalated ? '⚠️ Requires Manual Review' : score >= 70 ? '✅ Authenticated' : score >= 40 ? '⚠️ Review Recommended' : score !== null ? '❌ Suspicious' : '⏳ Pending'}</strong></div>
                        </div>
                        <div class="cert-footer">
                            <p>This certificate was generated by the GoldShield AI multi-agent verification system.</p>
                            <p>Non-destructive analysis using density, surface, hallmark, touchstone, and light-signature inspectors.</p>
                        </div>
                    </div>
                </div>
                <button class="btn btn-primary btn-sm" onclick="recordsManager.printCertificate()" style="margin-top: 12px;">🖨️ Print Certificate</button>
            </div>
        `;

        // Initialize 3D viewer in the detail
        setTimeout(() => {
            this._initDetail3DViewer(data.item_type || 'ring', appraisalId);
        }, 100);
    }

    /**
     * Render individual inspector result
     */
    _renderInspectorResult(name, result) {
        if (!result) return `
            <div class="inspector-item pending">
                <span class="inspector-name">${name}</span>
                <span class="inspector-status">No Data</span>
            </div>
        `;

        const status = (result.result || 'PASS').toUpperCase();
        const statusClass = status === 'PASS' ? 'pass' : status === 'FLAG' ? 'flag' : 'inconclusive';

        let detail = '';
        if (result.density_gcm3) detail = `${result.density_gcm3} g/cm³`;
        else if (result.hallmark_detected) detail = result.hallmark_detected;
        else if (result.observation) detail = result.observation;
        else if (result.streak_color_match) detail = result.streak_color_match;
        else if (result.reflectance_consistency) detail = result.reflectance_consistency;

        return `
            <div class="inspector-item ${statusClass}">
                <span class="inspector-name">${name}</span>
                <span class="inspector-detail">${this._escapeHtml(detail)}</span>
                <span class="inspector-status">${status === 'PASS' ? '✓ PASS' : status === 'FLAG' ? '⚠ FLAG' : '? INCONCLUSIVE'}</span>
                ${result.provider ? `<span class="inspector-provider">${result.provider}</span>` : ''}
            </div>
        `;
    }

    _initDetail3DViewer(itemType, appraisalId) {
        const glbViewer = document.getElementById('detailGlbViewer');
        const fallbackContainer = document.getElementById('detail3DContainer');
        
        if (glbViewer) {
            glbViewer.style.display = 'none';
            glbViewer.removeAttribute('src');
        }
        
        if (this.detailViewer) {
            if (fallbackContainer) fallbackContainer.innerHTML = '';
            this.detailViewer.dispose();
            this.detailViewer = null;
        }

        if (fallbackContainer) {
            fallbackContainer.style.display = 'block';
            this.detailViewer = new GoldShield3DViewer('detail3DContainer');
        }

        const bust = "?t=" + new Date().getTime();
        const modelUrl = `/api/models/${appraisalId}/visual_model.glb`;
        
        fetch(modelUrl + bust, { method: 'HEAD' })
            .then(res => {
                if (res.ok) {
                    if (glbViewer) {
                        glbViewer.src = modelUrl + bust;
                        glbViewer.style.display = 'block';
                    }
                    if (fallbackContainer) fallbackContainer.style.display = 'none';
                    
                    const controls = document.querySelector('.detail-3d-controls');
                    if (controls) controls.style.display = 'none';
                } else {
                    if (fallbackContainer) {
                        fallbackContainer.style.display = 'flex';
                        fallbackContainer.style.flexDirection = 'column';
                        fallbackContainer.style.alignItems = 'center';
                        fallbackContainer.style.justifyContent = 'center';
                        fallbackContainer.innerHTML = `
                            <div style="font-size: 2rem; margin-bottom: 12px;">⚠️</div>
                            <p style="color: var(--danger); font-weight: 500;">3D Visual Reference Unavailable</p>
                            <p style="font-size: 0.8rem; color: var(--dark-200); margin-top: 6px;">The API connection timed out</p>
                        `;
                    }
                    const controls = document.querySelector('.detail-3d-controls');
                    if (controls) controls.style.display = 'none';
                }
            })
            .catch(err => {
                if (fallbackContainer) {
                    fallbackContainer.style.display = 'flex';
                    fallbackContainer.style.flexDirection = 'column';
                    fallbackContainer.style.alignItems = 'center';
                    fallbackContainer.style.justifyContent = 'center';
                    fallbackContainer.innerHTML = `
                        <div style="font-size: 2rem; margin-bottom: 12px;">⚠️</div>
                        <p style="color: var(--danger); font-weight: 500;">3D Visual Reference Unavailable</p>
                        <p style="font-size: 0.8rem; color: var(--dark-200); margin-top: 6px;">Failed to connect</p>
                    `;
                }
                const controls = document.querySelector('.detail-3d-controls');
                if (controls) controls.style.display = 'none';
            });
    }

    /**
     * Reset the detail modal camera
     */
    resetDetailCamera() {
        if (this.detailViewer) {
            this.detailViewer.resetView();
        }
    }

    /**
     * Close detail modal
     */
    closeDetail() {
        const modal = document.getElementById('recordDetailModal');
        if (modal) modal.classList.remove('active');

        if (this.detailViewer) {
            document.getElementById('detail3DContainer').innerHTML = '';
            this.detailViewer = null;
        }
    }

    /**
     * Print certificate
     */
    printCertificate() {
        const cert = document.getElementById('certificateSection');
        if (!cert) return;

        const printWindow = window.open('', '_blank');
        printWindow.document.write(`
            <html>
            <head>
                <title>GoldShield AI - Verification Certificate</title>
                <style>
                    body { font-family: 'Inter', sans-serif; padding: 40px; color: #1a1a2e; }
                    .certificate-inner { border: 3px double #ffd740; padding: 40px; max-width: 700px; margin: 0 auto; }
                    .cert-header { text-align: center; margin-bottom: 24px; }
                    .cert-logo { font-size: 3rem; }
                    .cert-header h3 { font-size: 1.8rem; color: #b8860b; margin: 8px 0 4px; }
                    .cert-header p { color: #666; }
                    .cert-divider { height: 2px; background: linear-gradient(90deg, transparent, #ffd740, transparent); margin: 20px 0; }
                    .cert-body { padding: 20px 0; }
                    .cert-row { display: flex; justify-content: space-between; padding: 8px 0; border-bottom: 1px dotted #ddd; }
                    .cert-row span { color: #666; }
                    .cert-row strong { color: #1a1a2e; }
                    .cert-row .high { color: #00c853; }
                    .cert-row .medium { color: #ff8f00; }
                    .cert-row .low { color: #ff5252; }
                    .cert-footer { text-align: center; margin-top: 24px; font-size: 0.8rem; color: #888; }
                    @media print { body { padding: 20px; } }
                </style>
            </head>
            <body>
                ${cert.innerHTML}
                <script>window.onload = function() { window.print(); }</script>
            </body>
            </html>
        `);
        printWindow.document.close();
    }

    // ─── Utility functions ──────────────────────────────────────────────

    _getItemIcon(type) {
        const icons = {
            ring: '💍', bangle: '⭕', chain: '🔗', pendant: '📿',
            earring: '✨', bracelet: '⌚', coin: '🪙', bar: '📦',
        };
        return icons[(type || '').toLowerCase()] || '💍';
    }

    _formatItemType(type) {
        const names = {
            ring: 'Ring', bangle: 'Bangle', chain: 'Chain / Necklace',
            pendant: 'Pendant', earring: 'Earring', bracelet: 'Bracelet',
            coin: 'Coin', bar: 'Bar / Biscuit',
        };
        return names[(type || '').toLowerCase()] || type || 'Jewelry';
    }

    _escapeHtml(str) {
        if (!str) return '';
        const div = document.createElement('div');
        div.textContent = str;
        return div.innerHTML;
    }

    _formatNumber(num) {
        if (!num) return '0';
        if (num >= 10000000) return (num / 10000000).toFixed(2) + ' Cr';
        if (num >= 100000) return (num / 100000).toFixed(2) + ' L';
        if (num >= 1000) return num.toLocaleString('en-IN');
        return num.toString();
    }

    _formatDate(dateStr) {
        if (!dateStr) return '—';
        try {
            const d = new Date(dateStr);
            return d.toLocaleDateString('en-IN', { day: '2-digit', month: 'short', year: 'numeric' });
        } catch {
            return dateStr;
        }
    }
}

// Global instance
const recordsManager = new RecordsManager();
