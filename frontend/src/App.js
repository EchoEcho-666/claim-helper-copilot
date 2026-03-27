import React, { useState } from 'react';
import './App.css';

function App() {
  const [note, setNote] = useState('Patient presented with severe pain tooth 14. Performed pulpectomy and placed temporary filling. Recommended crown placement in 2 weeks.');
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const analyzeNote = async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await fetch('http://127.0.0.1:8000/api/analyze-note', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ text: note }),
      });

      if (!response.ok) {
        throw new Error('Failed to connect to AI Backend');
      }

      const data = await response.json();
      setResult(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{ fontFamily: 'Arial, sans-serif', padding: '40px', maxWidth: '1200px', margin: '0 auto' }}>
      <header style={{ borderBottom: '2px solid #eee', paddingBottom: '20px', marginBottom: '30px' }}>
        <h1 style={{ margin: 0, color: '#2c3e50' }}>TDO Claim Copilot</h1>
        <p style={{ margin: '5px 0 0 0', color: '#7f8c8d' }}>AI-Powered Clinical Note to CDT Code Translator</p>
      </header>

      <div style={{ display: 'flex', gap: '40px' }}>
        {/* Left Column: Input */}
        <div style={{ flex: 1 }}>
          <h3 style={{ marginTop: 0 }}>Doctor's Clinical Notes</h3>
          <textarea
            value={note}
            onChange={(e) => setNote(e.target.value)}
            style={{ width: '100%', height: '300px', padding: '15px', borderRadius: '8px', border: '1px solid #ccc', fontSize: '16px', boxSizing: 'border-box' }}
            placeholder="Paste messy clinical notes here..."
          />
          <button 
            onClick={analyzeNote}
            disabled={loading}
            style={{ marginTop: '20px', padding: '15px 30px', backgroundColor: '#3498db', color: 'white', border: 'none', borderRadius: '8px', fontSize: '16px', cursor: loading ? 'not-allowed' : 'pointer', width: '100%', fontWeight: 'bold' }}
          >
            {loading ? 'Analyzing...' : 'Generate Billing Codes'}
          </button>
          {error && <p style={{ color: '#e74c3c', marginTop: '10px' }}>Error: {error}</p>}
        </div>

        {/* Right Column: Output */}
        <div style={{ flex: 1, backgroundColor: '#f8f9fa', padding: '30px', borderRadius: '8px', border: '1px solid #eee' }}>
          <h3 style={{ marginTop: 0 }}>AI Billing Output</h3>
          
          {!result && !loading && (
            <p style={{ color: '#95a5a6', fontStyle: 'italic' }}>Waiting for clinical notes...</p>
          )}

          {loading && (
            <p style={{ color: '#3498db' }}>Scanning notes against CDT database...</p>
          )}

          {result && !loading && (
            <div>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
                <span style={{ padding: '8px 16px', borderRadius: '20px', fontWeight: 'bold', backgroundColor: result.status === 'Ready to File' ? '#2ecc71' : '#e74c3c', color: 'white' }}>
                  {result.status}
                </span>
                <h2 style={{ margin: 0, color: '#2c3e50' }}>Est: ${result.total_estimated_value}</h2>
              </div>

              <h4>Suggested Codes</h4>
              <ul style={{ listStyleType: 'none', padding: 0 }}>
                {result.suggested_codes.map((codeItem, index) => (
                  <li key={index} style={{ backgroundColor: 'white', padding: '15px', border: '1px solid #ddd', borderRadius: '6px', marginBottom: '10px', display: 'flex', justifyContent: 'space-between' }}>
                    <div>
                      <strong>{codeItem.code}</strong> - {codeItem.description}
                    </div>
                    <div style={{ color: '#27ae60', fontWeight: 'bold' }}>${codeItem.fee_estimate}</div>
                  </li>
                ))}
              </ul>

              {result.denial_risks && result.denial_risks.length > 0 && (
                <div style={{ marginTop: '30px', backgroundColor: '#fdf3f2', padding: '15px', borderRadius: '6px', borderLeft: '4px solid #e74c3c' }}>
                  <h4 style={{ margin: '0 0 10px 0', color: '#c0392b' }}>⚠️ Insurance Denial Risks</h4>
                  <ul style={{ margin: 0, paddingLeft: '20px', color: '#c0392b' }}>
                    {result.denial_risks.map((risk, index) => (
                      <li key={index}>{risk}</li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

export default App;