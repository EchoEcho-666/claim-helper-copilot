import React, { useState, useEffect, useRef } from 'react';
import './App.css';

const SAMPLE_NOTES = [
  {
    label: 'Select a sample clinical note...',
    text: '',
  },
  {
    label: 'Endodontic — Molar Root Canal (#14)',
    text: 'Patient presented with severe spontaneous pain and lingering thermal sensitivity in tooth #14. Pulp vitality testing confirmed irreversible pulpitis. Periapical radiograph reveals periapical radiolucency at the mesial root apex. Performed pulpectomy under rubber dam isolation. Canals located, instrumented, and irrigated with NaOCl. Calcium hydroxide placed as intracanal medicament. Temporary filling placed with Cavit. Patient to return in 2 weeks for obturation. Recommended full-coverage crown following completion of endodontic therapy.',
  },
  {
    label: 'Emergency — Palliative Treatment',
    text: 'Patient presents as emergency walk-in with acute throbbing pain in the lower right quadrant, 9/10 severity, waking patient from sleep. Tooth #30 exhibits large carious lesion with exposure of the pulp chamber. Percussion positive, cold test lingering >30 seconds. Prescribed Amoxicillin 500mg TID x 7 days. Performed palliative pulpotomy to relieve acute symptoms. Temporary sedative filling placed. Patient to return for definitive root canal therapy.',
  },
  {
    label: 'Retreatment — Failed Prior Root Canal',
    text: 'Patient referred for evaluation of persistent pain tooth #8, previously treated with root canal 3 years ago. Clinical exam reveals sinus tract on the buccal mucosa. CBCT scan shows missed MB2 canal and periapical pathology at apex. Previous obturation appears short of working length by 2mm. Treatment plan: endodontic retreatment of tooth #8. Removed existing gutta percha using ProTaper retreatment files. Located and negotiated missed MB2 canal. Working length confirmed with apex locator and radiograph. Canals re-instrumented and dressed with calcium hydroxide.',
  },
  {
    label: 'Surgical — Apicoectomy Anterior',
    text: 'Patient presents with persistent periapical pathology tooth #9 despite adequate prior root canal treatment. CBCT reveals 6mm periapical radiolucency with proximity to nasal floor. Conservative retreatment unlikely to resolve pathology due to well-condensed obturation and post-and-core. Surgical apicoectomy performed: full-thickness mucoperiosteal flap reflected, osteotomy performed with surgical bur to expose root apex. 3mm of root apex resected at 0-degree bevel. Retropreparation made with ultrasonic tips. MTA retrograde filling placed. Xenograft bone substitute placed, collagen membrane adapted. Primary closure with 5-0 chromic gut sutures. Hemostasis achieved.',
  },
];

function App() {
  const [note, setNote] = useState(SAMPLE_NOTES[1].text);
  const [selectedSample, setSelectedSample] = useState(1);
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [loadingStep, setLoadingStep] = useState(0);
  const [expandedReasoning, setExpandedReasoning] = useState({});
  const loadingInterval = useRef(null);

  const handleSampleChange = (e) => {
    const idx = parseInt(e.target.value);
    setSelectedSample(idx);
    if (idx > 0) {
      setNote(SAMPLE_NOTES[idx].text);
    }
  };

  const analyzeNote = async () => {
    setLoading(true);
    setError(null);
    setResult(null);
    setLoadingStep(0);
    setExpandedReasoning({});

    // Animate loading steps
    let step = 0;
    loadingInterval.current = setInterval(() => {
      step++;
      setLoadingStep(step);
      if (step >= 3) clearInterval(loadingInterval.current);
    }, 1200);

    try {
      const response = await fetch('http://127.0.0.1:8000/api/analyze-note', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text: note }),
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => null);
        throw new Error(errorData?.detail || 'Failed to connect to AI backend');
      }

      const data = await response.json();
      clearInterval(loadingInterval.current);
      setLoadingStep(4);
      // Small delay so "Done" step renders before results appear
      setTimeout(() => setResult(data), 300);
    } catch (err) {
      clearInterval(loadingInterval.current);
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    return () => {
      if (loadingInterval.current) clearInterval(loadingInterval.current);
    };
  }, []);

  const getConfidenceLevel = (score) => {
    if (score >= 85) return 'high';
    if (score >= 60) return 'medium';
    return 'low';
  };

  const toggleReasoning = (index) => {
    setExpandedReasoning(prev => ({ ...prev, [index]: !prev[index] }));
  };

  const isReady = result?.status === 'Ready to File';
  const isClarification = result?.status === 'Clarification Needed';

  return (
    <div>
      {/* ---- Header ---- */}
      <header className="app-header">
        <h1 className="header-logo-text">Claim Helper<span className="red-dot">.</span></h1>
        <div className="header-tagline">AI-Powered Dental Billing Intelligence</div>
      </header>

      {/* ---- Main Content ---- */}
      <div className="app-container">
        <div className="columns">

          {/* ---- Left: Input ---- */}
          <div className="card">
            <div className="card-header">
              <h3>Clinical Notes</h3>
              <span style={{ fontSize: '12px', color: '#94a3b8' }}>Paste or select a sample</span>
            </div>
            <div className="card-body">
              <select
                className="sample-select"
                value={selectedSample}
                onChange={handleSampleChange}
              >
                {SAMPLE_NOTES.map((s, i) => (
                  <option key={i} value={i}>{s.label}</option>
                ))}
              </select>

              <textarea
                className="note-textarea"
                value={note}
                onChange={(e) => { setNote(e.target.value); setSelectedSample(0); }}
                placeholder="Paste clinical notes here or select a sample above..."
              />

              <button
                className="analyze-btn"
                onClick={analyzeNote}
                disabled={loading || !note.trim()}
              >
                {loading ? (
                  <>
                    <div className="loading-spinner" style={{ width: 18, height: 18, borderWidth: 2 }} />
                    Analyzing...
                  </>
                ) : (
                  'Generate Billing Codes'
                )}
              </button>

              {error && <div className="error-msg">{error}</div>}
            </div>
          </div>

          {/* ---- Right: Output ---- */}
          <div className="card">
            <div className="card-header">
              <h3>AI Billing Output</h3>
              {result && (
                <span className={`status-badge ${isReady ? 'ready' : isClarification ? 'clarification' : 'clarification'}`}>
                  {result.status}
                </span>
              )}
            </div>
            <div className="card-body">

              {/* Empty state */}
              {!result && !loading && (
                <div className="empty-state">
                  <div className="empty-icon">
                    <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="#cbd5e1" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
                      <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
                      <polyline points="14 2 14 8 20 8" />
                      <line x1="16" y1="13" x2="8" y2="13" />
                      <line x1="16" y1="17" x2="8" y2="17" />
                      <polyline points="10 9 9 9 8 9" />
                    </svg>
                  </div>
                  <p>Paste a clinical note and click <strong>Generate Billing Codes</strong> to get AI-powered CDT code suggestions with confidence scoring and denial risk analysis.</p>
                </div>
              )}

              {/* Loading state */}
              {loading && (
                <div className="loading-container">
                  <div className="loading-spinner" />
                  <div className="loading-steps">
                    {[
                      'Scrubbing PII from clinical text',
                      'Matching against CDT code database',
                      'Running predictive adjudication',
                      'Generating results',
                    ].map((label, i) => (
                      <div key={i} className={`loading-step ${loadingStep > i ? 'done' : loadingStep === i ? 'active' : ''}`}>
                        <span className="step-dot" />
                        {label}
                        {loadingStep > i && ' \u2713'}
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Results */}
              {result && !loading && (
                <div>
                  {/* Total value */}
                  <div className="result-header">
                    <div>
                      <div className="total-label">Estimated Reimbursement</div>
                      <div className="total-value">${result.total_estimated_value?.toLocaleString()}</div>
                    </div>
                    <div style={{ textAlign: 'right' }}>
                      <div className="total-label">Codes Found</div>
                      <div style={{ fontSize: '28px', fontWeight: 800, color: '#1e293b' }}>
                        {result.suggested_codes?.length || 0}
                      </div>
                    </div>
                  </div>

                  {/* Code cards */}
                  {result.suggested_codes?.map((item, index) => (
                    <div key={index} className="code-card animate-in">
                      <div className="code-card-header">
                        <div style={{ flex: 1 }}>
                          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flexWrap: 'wrap' }}>
                            <span className="code-id">{item.code}</span>
                            {item.verified === true && <span className="badge badge-verified">Verified</span>}
                            {item.verified === false && <span className="badge badge-unverified">Unverified</span>}
                            {item.category && item.category !== 'Unknown' && (
                              <span className="badge badge-category">{item.category}</span>
                            )}
                          </div>
                          <div className="code-desc">{item.description}</div>
                        </div>
                        <div className="code-fee">
                          <div className="fee-main">${item.fee_estimate?.toLocaleString()}</div>
                          {item.reference_fee != null && item.reference_fee !== item.fee_estimate && (
                            <div className="fee-ref">CDT ref: ${item.reference_fee}</div>
                          )}
                        </div>
                      </div>

                      {/* Confidence */}
                      {item.confidence_score != null && (
                        <div className="confidence-row">
                          <span className="confidence-label">Confidence</span>
                          <div className="confidence-track">
                            <div
                              className={`confidence-fill ${getConfidenceLevel(item.confidence_score)}`}
                              style={{ width: `${item.confidence_score}%` }}
                            />
                          </div>
                          <span className={`confidence-value ${getConfidenceLevel(item.confidence_score)}`}>
                            {item.confidence_score}%
                          </span>
                        </div>
                      )}

                      {/* Denial risks */}
                      {item.denial_risk_factors?.length > 0 && (
                        <div className="risk-box">
                          <div className="risk-title">Denial Risk Factors</div>
                          <ul>
                            {item.denial_risk_factors.map((risk, i) => (
                              <li key={i}>{risk}</li>
                            ))}
                          </ul>
                        </div>
                      )}

                      {/* Reasoning */}
                      {item.reasoning && (
                        <div>
                          <button
                            className="reasoning-toggle"
                            onClick={() => toggleReasoning(index)}
                          >
                            {expandedReasoning[index] ? '\u25BC' : '\u25B6'} AI Reasoning
                          </button>
                          {expandedReasoning[index] && (
                            <div className="reasoning-text">{item.reasoning}</div>
                          )}
                        </div>
                      )}
                    </div>
                  ))}

                  {/* Global denial risks */}
                  {result.denial_risks?.length > 0 && (
                    <div className="global-risk animate-in">
                      <h4>Insurance Denial Risks</h4>
                      <ul>
                        {result.denial_risks.map((risk, i) => (
                          <li key={i}>{risk}</li>
                        ))}
                      </ul>
                    </div>
                  )}
                </div>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* ---- Footer ---- */}
      <footer className="footer">
        Prototype for demonstration purposes. CDT codes require <a href="https://www.ada.org/publications/cdt/licensing" target="_blank" rel="noreferrer">ADA license</a> for production use.
      </footer>
    </div>
  );
}

export default App;
