/**
 * Modern React UI for Test Case Generator v2.0
 * Features: Atomic Behavior Display, Coverage Summary, 9-Dimension Test Types
 * Enhanced with Tailwind CSS, dark mode, and animations
 */

import React, { useState, useEffect } from 'react';

const API_URL = 'http://localhost:9001';

// Animation keyframes injected into the page
const AnimationStyles = () => (
  <style>{`
    @keyframes fadeIn { from { opacity: 0; transform: translateY(10px); } to { opacity: 1; transform: translateY(0); } }
    @keyframes slideUp { from { opacity: 0; transform: translateY(20px); } to { opacity: 1; transform: translateY(0); } }
    @keyframes pulse { 0%, 100% { opacity: 1; } 50% { opacity: 0.5; } }
    @keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }
    .animate-fade-in { animation: fadeIn 0.5s ease-out; }
    .animate-slide-up { animation: slideUp 0.4s ease-out; }
    .progress-bar { transition: width 1s ease-in-out; }
  `}</style>
);

function App() {
  const [activeTab, setActiveTab] = useState('home');
  const [input, setInput] = useState('');
  const [results, setResults] = useState(null);
  const [loading, setLoading] = useState(false);
  const [darkMode, setDarkMode] = useState(false);
  const [toasts, setToasts] = useState([]);
  const [progress, setProgress] = useState(0);
  const [processingStep, setProcessingStep] = useState('');

  // Filter states for Artifacts tab
  const [artifactFilters, setArtifactFilters] = useState({
    priority: [],
    types: []
  });

  // Initialize theme
  useEffect(() => {
    const savedTheme = localStorage.getItem('theme') || 'light';
    setDarkMode(savedTheme === 'dark');
    document.documentElement.classList.add(savedTheme);
  }, []);

  const toggleTheme = () => {
    const newMode = !darkMode;
    setDarkMode(newMode);
    localStorage.setItem('theme', newMode ? 'dark' : 'light');
    document.documentElement.classList.remove(darkMode ? 'dark' : 'light');
    document.documentElement.classList.add(newMode ? 'dark' : 'light');
  };

  const showToast = (message, type = 'info') => {
    const id = Date.now();
    setToasts(prev => [...prev, { id, message, type }]);
    setTimeout(() => {
      setToasts(prev => prev.filter(t => t.id !== id));
    }, 3000);
  };

  const handleGenerate = async () => {
    if (!input.trim()) {
      showToast('Please enter a requirement', 'warning');
      return;
    }
    
    setLoading(true);
    setProgress(0);
    setProcessingStep('Ingesting requirements...');
    
    try {
      const progressInterval = setInterval(() => {
        setProgress(prev => Math.min(prev + 10, 90));
      }, 500);
      
      setProcessingStep('Extracting atomic behaviors...');
      await new Promise(r => setTimeout(r, 800));
      
      setProcessingStep('Generating 9-dimension test cases...');
      await new Promise(r => setTimeout(r, 800));
      
      setProcessingStep('Calculating coverage...');
      
      const response = await fetch(`${API_URL}/generate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text: input })
      });
      
      clearInterval(progressInterval);
      
      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || 'Generation failed');
      }
      
      const data = await response.json();
      setResults(data);
      setProgress(100);
      showToast(`Generated ${data.test_cases?.length || 0} test cases from ${data.behaviors?.length || 0} behaviors!`, 'success');
    } catch (error) {
      console.error('Error:', error);
      showToast('Error: ' + error.message, 'error');
    } finally {
      setLoading(false);
      setTimeout(() => { setProgress(0); setProcessingStep(''); }, 1000);
    }
  };

  const handleExport = (format) => {
    if (!results) return;
    
    let content, filename, mimeType;
    if (format === 'json') {
      content = JSON.stringify(results, null, 2);
      filename = `tc-output-${new Date().toISOString().slice(0,10)}.json`;
      mimeType = 'application/json';
    } else if (format === 'markdown') {
      content = generateMarkdown(results);
      filename = `tc-report-${new Date().toISOString().slice(0,10)}.md`;
      mimeType = 'text/markdown';
    }
    
    const blob = new Blob([content], { type: mimeType });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    a.click();
    URL.revokeObjectURL(url);
    showToast(`Downloaded ${filename}`, 'success');
  };

  const generateMarkdown = (data) => {
    let md = `# Test Case Generation Report v2.0\n\n`;
    md += `## Pipeline Summary\n- Requirements: ${data.requirements?.length || 0}\n`;
    md += `- Behaviors: ${data.behaviors?.length || 0}\n`;
    md += `- Test Cases: ${data.test_cases?.length || 0}\n`;
    md += `- Overall Coverage: ${data.coverage_summary?.overall_coverage || 0}%\n\n`;
    
    md += `## Atomic Behaviors\n\n`;
    data.behaviors?.forEach(b => {
      md += `### ${b.behavior_id}\n`;
      md += `**Actor:** ${b.actor}\n`;
      md += `**Action:** ${b.action}\n`;
      md += `**Object:** ${b.object_name}\n`;
      md += `**Description:** ${b.description}\n\n`;
    });
    
    md += `## Test Cases\n\n`;
    data.test_cases?.forEach(tc => {
      md += `### ${tc.test_case_id}\n`;
      md += `**Title:** ${tc.title}\n`;
      md += `**Type:** ${tc.test_type} | **Priority:** ${tc.priority}\n`;
      md += `**Behavior:** ${tc.behavior_id}\n`;
      md += `**Expected:** ${tc.expected_result}\n\n`;
    });
    return md;
  };

  const templates = {
    flash_sale: 'The system shall display product details including price, stock quantity, and discount percentage. During flash sale events, limited stock shall be allocated on a first-come-first-serve basis. The system shall prevent overselling of stock during high concurrency. When a user adds a product to cart, the product shall be reserved for ten minutes. If checkout is not completed within ten minutes, the reserved stock shall be released automatically. The system shall process payments through integrated payment gateways. Payment response shall be received within five seconds. If payment is successful, order confirmation shall be generated immediately. If payment fails, stock shall be restored automatically. The system shall send confirmation email within one minute of successful order placement. The platform shall handle at least 5,000 transactions per second during flash sales. The system shall prevent duplicate order generation due to repeated submission or page refresh. All payment data shall comply with PCI standards. System availability during flash sale shall not fall below 99.95 percent.',
    parking: 'The system shall detect available parking slots using IoT sensors installed at each slot. Sensor data shall synchronize with the central server every 30 seconds. The system shall display real-time slot availability to users within two seconds of refresh. Users shall reserve a parking slot for a selected future time window. Reserved slots shall not be visible as available to other users. If a user does not enter the parking lot within fifteen minutes of reservation start time, the system shall release the slot automatically. The system shall start the parking session when vehicle entry is detected through RFID or license plate recognition. The system shall calculate parking fees based on duration and configured pricing rules. Overstay charges shall apply automatically after grace period expires. Users shall complete payment before exiting the parking lot. If payment fails, the system shall mark the session as pending payment and restrict future reservations. Operators shall configure pricing rules, operating hours, and total slot capacity through an administrative dashboard. The system shall generate daily occupancy reports and revenue summaries. The system shall handle 100,000 concurrent user sessions. System uptime shall not fall below 99.9 percent. If sensor data becomes unavailable, operators shall manually override slot availability.',
    food_delivery: 'The system shall allow customers to search restaurants based on location and cuisine type. The system shall display estimated delivery time and delivery charges before order confirmation. Customers shall add items to cart and modify item quantity before checkout. The system shall validate item availability before order placement. If an item becomes unavailable during checkout, the system shall notify the user and prevent order confirmation. Customers shall apply discount coupons during checkout. The system shall validate coupon eligibility based on expiration date and minimum order value. The system shall process payments using credit card, debit card, UPI, and wallet. Payment confirmation shall occur within five seconds. If payment is deducted but order creation fails, the system shall automatically initiate refund within ten minutes. The system shall assign delivery partners based on proximity and availability. Delivery partner location shall update every five seconds. Customers shall track order status in real time. The system shall allow cancellation before order preparation starts. The system shall support up to 150,000 concurrent users during peak hours. System availability shall be at least 99.9 percent uptime monthly. All personal and payment information shall be encrypted. The system shall prevent duplicate order creation if the user refreshes the confirmation page repeatedly.',
    wallet: 'The system shall allow users to register using a mobile number and email address. The system shall verify the mobile number using a one-time password before account activation. Users shall create a secure login PIN during registration. The system shall allow users to add money to their wallet using debit card, credit card, or UPI. The wallet balance shall update immediately after successful payment confirmation. If payment fails after deduction from the bank, the system shall automatically reconcile the transaction within five minutes. Users shall transfer money to another registered user using mobile number or wallet ID. The system shall prevent transfers if the sender's wallet balance is insufficient. The system shall block transfers exceeding ₹1,00,000 per day. All wallet transactions shall be recorded in transaction history. Transaction history shall display date, time, transaction ID, amount, and status. Users shall receive a push notification after every successful or failed transaction. The system shall support up to 75,000 concurrent active users. Transaction processing time shall not exceed two seconds under normal load. All financial data shall be encrypted at rest and in transit. The system shall comply with PCI-DSS standards. If the notification service fails, the transaction shall still complete successfully and the notification shall retry asynchronously.',
    telemedicine: 'The system shall allow patients to create an account using email and password. Email verification shall be mandatory before booking appointments. Patients shall book appointments based on doctor availability schedule. The system shall prevent double booking of time slots. Patients shall pay consultation fees before appointment confirmation. If payment fails after deduction, refund shall be processed automatically within fifteen minutes. The system shall enable secure video consultation between patient and doctor. Video latency shall not exceed 300 milliseconds under stable network conditions. Doctors shall create digital prescriptions including diagnosis, medication, dosage, and duration. Patients shall view prescription history but shall not edit prescription details. All medical records shall be encrypted and stored securely. The system shall comply with healthcare data privacy regulations. The platform shall support 10,000 concurrent consultation sessions. If the video connection drops, the system shall attempt automatic reconnection within ten seconds. If reconnection fails, the session shall be marked incomplete and partial refund shall be evaluated.'
  };

  const loadTemplate = (key) => {
    setInput(templates[key]);
    showToast('Template loaded', 'success');
  };

  const tabs = [
    { id: 'home', label: 'Home', icon: '🏠' },
    { id: 'artifacts', label: 'Artifacts', icon: '📦', badge: results?.requirements?.length },
    { id: 'behaviors', label: 'Behaviors', icon: '🎯', badge: results?.behaviors?.length },
    { id: 'testcases', label: 'Test Cases', icon: '✅', badge: results?.test_cases?.length },
    { id: 'rtm', label: 'RTM', icon: '🔗' }
  ];

  const ambigCount = results?.requirements?.filter(r => r.ambiguity?.is_ambiguous).length || 0;

  const getCoverageColor = (pct) => {
    if (pct >= 80) return 'text-green-500';
    if (pct >= 50) return 'text-yellow-500';
    return 'text-red-500';
  };

  const getCoverageBg = (pct) => {
    if (pct >= 80) return 'bg-green-500';
    if (pct >= 50) return 'bg-yellow-500';
    return 'bg-red-500';
  };

  const toggleFilter = (filterType, value) => {
    setArtifactFilters(prev => {
      const current = prev[filterType];
      const updated = current.includes(value)
        ? current.filter(v => v !== value)
        : [...current, value];
      return { ...prev, [filterType]: updated };
    });
  };

  const filteredRequirements = results?.requirements?.filter(req => {
    const matchesPriority = artifactFilters.priority.length === 0 || 
      artifactFilters.priority.includes(req.priority);
    const matchesType = artifactFilters.types.length === 0 || 
      (req.types && req.types.some(t => artifactFilters.types.includes(t)));
    return matchesPriority && matchesType;
  }) || [];

  function StatCard({ label, value, color = 'indigo' }) {
    const colors = {
      indigo: 'from-indigo-500 to-purple-600',
      green: 'from-green-500 to-emerald-600',
      blue: 'from-blue-500 to-cyan-600'
    };
    
    return (
      <div className={`rounded-xl p-4 bg-gradient-to-br ${colors[color] || colors.indigo} text-white shadow-lg animate-fade-in`}>
        <div className="text-3xl font-bold">{value}</div>
        <div className="text-white/80 text-sm">{label}</div>
      </div>
    );
  }

  function ArtifactsTab({ results, darkMode }) {
    if (!results?.requirements) return null;

    const allPriorities = [...new Set(results.requirements.map(r => r.priority).filter(Boolean))];
    const allTypes = [...new Set(results.requirements.flatMap(r => r.types || []))];

    return (
      <div className="space-y-6 animate-fade-in">
        <div className={`rounded-xl p-4 ${darkMode ? 'bg-gray-800' : 'bg-white'}`}>
          <h4 className={`font-medium mb-3 ${darkMode ? 'text-gray-200' : 'text-gray-700'}`}>🔍 Multi-Level Filtering</h4>
          <div className="flex flex-wrap gap-6">
            <div>
              <span className={`text-xs uppercase tracking-wide ${darkMode ? 'text-gray-500' : 'text-gray-400'} mb-2 block`}>Priority</span>
              <div className="flex flex-wrap gap-2">
                {allPriorities.map(priority => (
                  <button key={priority} onClick={() => toggleFilter('priority', priority)}
                    className={`px-3 py-1 rounded-lg text-sm transition-colors ${
                      artifactFilters.priority.includes(priority)
                        ? 'bg-indigo-500 text-white'
                        : darkMode ? 'bg-gray-700 text-gray-300 hover:bg-gray-600' : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                    }`}>
                    {priority}
                  </button>
                ))}
              </div>
            </div>
            <div>
              <span className={`text-xs uppercase tracking-wide ${darkMode ? 'text-gray-500' : 'text-gray-400'} mb-2 block`}>Type</span>
              <div className="flex flex-wrap gap-2">
                {allTypes.map(type => (
                  <button key={type} onClick={() => toggleFilter('types', type)}
                    className={`px-3 py-1 rounded-lg text-sm transition-colors ${
                      artifactFilters.types.includes(type)
                        ? 'bg-indigo-500 text-white'
                        : darkMode ? 'bg-gray-700 text-gray-300 hover:bg-gray-600' : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                    }`}>
                    {type}
                  </button>
                ))}
              </div>
            </div>
          </div>
          {(artifactFilters.priority.length > 0 || artifactFilters.types.length > 0) && (
            <button onClick={() => setArtifactFilters({ priority: [], types: [] })} className="mt-3 text-sm text-indigo-500 hover:text-indigo-600">
              Clear filters
            </button>
          )}
        </div>

        <div className={`text-sm ${darkMode ? 'text-gray-400' : 'text-gray-500'}`}>
          Showing {filteredRequirements.length} of {results.requirements.length} requirements
        </div>

        <div className="space-y-4">
          {filteredRequirements.map((req, idx) => (
            <div key={idx} className={`rounded-xl border overflow-hidden ${darkMode ? 'bg-gray-800 border-gray-700' : 'bg-white border-gray-200'}`}>
              <div className={`px-6 py-4 border-b ${darkMode ? 'border-gray-700 bg-gray-700/50' : 'border-gray-100 bg-gray-50'}`}>
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <span className="px-2 py-1 bg-indigo-100 text-indigo-700 rounded text-sm font-mono dark:bg-indigo-900 dark:text-indigo-300">
                      {req.requirement_id}
                    </span>
                    <span className={`font-medium ${darkMode ? 'text-gray-200' : 'text-gray-800'}`}>
                      {req.original_text?.substring(0, 120)}{req.original_text?.length > 120 ? '...' : ''}
                    </span>
                  </div>
                  <div className="flex items-center gap-2">
                    {req.priority && (
                      <span className={`px-2 py-1 rounded text-xs ${req.priority === 'High' ? 'bg-red-100 text-red-700 dark:bg-red-900 dark:text-red-300' : req.priority === 'Medium' ? 'bg-yellow-100 text-yellow-700 dark:bg-yellow-900 dark:text-yellow-300' : 'bg-green-100 text-green-700 dark:bg-green-900 dark:text-green-300'}`}>
                        {req.priority}
                      </span>
                    )}
                    {req.ambiguity?.is_ambiguous && (
                      <span className="px-2 py-1 bg-amber-100 text-amber-700 rounded text-xs dark:bg-amber-900 dark:text-amber-300">⚠️ Ambiguous</span>
                    )}
                  </div>
                </div>
              </div>
              
              <div className="p-6 grid md:grid-cols-2 gap-6">
                <div>
                  <h5 className={`text-sm font-medium mb-3 ${darkMode ? 'text-gray-300' : 'text-gray-600'}`}>📋 Normalized Data</h5>
                  <div className="space-y-3">
                    <div className={`p-3 rounded-lg ${darkMode ? 'bg-gray-700/50' : 'bg-gray-50'}`}>
                      <span className={`text-xs uppercase tracking-wide ${darkMode ? 'text-gray-500' : 'text-gray-400'}`}>Actor</span>
                      <p className={`font-medium ${darkMode ? 'text-gray-200' : 'text-gray-700'}`}>{req.normalized?.actor || '-'}</p>
                    </div>
                    <div className={`p-3 rounded-lg ${darkMode ? 'bg-gray-700/50' : 'bg-gray-50'}`}>
                      <span className={`text-xs uppercase tracking-wide ${darkMode ? 'text-gray-500' : 'text-gray-400'}`}>Action</span>
                      <p className={`font-medium ${darkMode ? 'text-gray-200' : 'text-gray-700'}`}>{req.normalized?.action || '-'}</p>
                    </div>
                    <div className={`p-3 rounded-lg ${darkMode ? 'bg-gray-700/50' : 'bg-gray-50'}`}>
                      <span className={`text-xs uppercase tracking-wide ${darkMode ? 'text-gray-500' : 'text-gray-400'}`}>Confidence</span>
                      <p className={`font-medium ${darkMode ? 'text-gray-200' : 'text-gray-700'}`}>{req.confidence ? `${Math.round(req.confidence * 100)}%` : '-'}</p>
                    </div>
                  </div>
                </div>
                <div>
                  <h5 className={`text-sm font-medium mb-3 ${darkMode ? 'text-gray-300' : 'text-gray-600'}`}>🏷️ Classification</h5>
                  <div className="space-y-3">
                    <div>
                      <span className={`text-xs uppercase tracking-wide ${darkMode ? 'text-gray-500' : 'text-gray-400'}`}>Types</span>
                      <div className="flex flex-wrap gap-1 mt-1">
                        {req.types?.map(t => (
                          <span key={t} className={`px-2 py-0.5 rounded text-xs ${darkMode ? 'bg-indigo-900/50 text-indigo-300' : 'bg-indigo-100 text-indigo-700'}`}>{t}</span>
                        )) || '-'}
                      </div>
                    </div>
                    <div>
                      <span className={`text-xs uppercase tracking-wide ${darkMode ? 'text-gray-500' : 'text-gray-400'}`}>Feature Area</span>
                      <p className={`font-medium ${darkMode ? 'text-gray-200' : 'text-gray-700'}`}>{req.normalized?.feature_area || '-'}</p>
                    </div>
                    {req.clarifying_questions?.length > 0 && (
                      <div>
                        <span className={`text-xs uppercase tracking-wide ${darkMode ? 'text-gray-500' : 'text-gray-400'}`}>❓ Questions</span>
                        <ul className={`mt-1 space-y-1 text-sm ${darkMode ? 'text-gray-300' : 'text-gray-600'}`}>
                          {req.clarifying_questions.map((q, i) => (<li key={i}>• {q}</li>))}
                        </ul>
                      </div>
                    )}
                  </div>
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>
    );
  }

  function BehaviorsTab({ results, darkMode }) {
    if (!results?.behaviors) return null;

    return (
      <div className="space-y-6 animate-fade-in">
        {results.behaviors.map((behavior, idx) => {
          const behaviorTCs = results.test_cases?.filter(tc => tc.behavior_id === behavior.behavior_id) || [];
          
          return (
            <div key={idx} className={`rounded-xl border overflow-hidden ${darkMode ? 'bg-gray-800 border-gray-700' : 'bg-white border-gray-200'}`}>
              <div className={`px-6 py-4 border-b ${darkMode ? 'border-gray-700 bg-gray-700/50' : 'border-gray-200 bg-gray-50'}`}>
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <span className="px-3 py-1 bg-indigo-100 text-indigo-700 rounded-lg text-sm font-mono dark:bg-indigo-900 dark:text-indigo-300">
                      {behavior.behavior_id}
                    </span>
                    <span className={`font-medium text-lg ${darkMode ? 'text-gray-200' : 'text-gray-800'}`}>
                      {behavior.description}
                    </span>
                  </div>
                  <span className={`px-3 py-1 rounded-lg text-sm ${darkMode ? 'bg-gray-700 text-gray-300' : 'bg-gray-100 text-gray-600'}`}>
                    {behaviorTCs.length} test cases
                  </span>
                </div>
              </div>
              <div className="p-6 grid md:grid-cols-4 gap-6">
                <div className={`p-4 rounded-lg ${darkMode ? 'bg-gray-700/50' : 'bg-gray-50'}`}>
                  <span className={`block text-xs uppercase tracking-wide ${darkMode ? 'text-gray-500' : 'text-gray-400'}`}>Actor</span>
                  <span className={`text-lg font-medium ${darkMode ? 'text-gray-200' : 'text-gray-700'}`}>{behavior.actor}</span>
                </div>
                <div className={`p-4 rounded-lg ${darkMode ? 'bg-gray-700/50' : 'bg-gray-50'}`}>
                  <span className={`block text-xs uppercase tracking-wide ${darkMode ? 'text-gray-500' : 'text-gray-400'}`}>Action</span>
                  <span className={`text-lg font-medium ${darkMode ? 'text-gray-200' : 'text-gray-700'}`}>{behavior.action}</span>
                </div>
                <div className={`p-4 rounded-lg ${darkMode ? 'bg-gray-700/50' : 'bg-gray-50'}`}>
                  <span className={`block text-xs uppercase tracking-wide ${darkMode ? 'text-gray-500' : 'text-gray-400'}`}>Object</span>
                  <span className={`text-lg font-medium ${darkMode ? 'text-gray-200' : 'text-gray-700'}`}>{behavior.object_name || '-'}</span>
                </div>
                <div className={`p-4 rounded-lg ${darkMode ? 'bg-gray-700/50' : 'bg-gray-50'}`}>
                  <span className={`block text-xs uppercase tracking-wide ${darkMode ? 'text-gray-500' : 'text-gray-400'}`}>Condition</span>
                  <span className={`text-lg font-medium ${darkMode ? 'text-gray-200' : 'text-gray-700'}`}>{behavior.condition || 'None'}</span>
                </div>
              </div>
            </div>
          );
        })}
      </div>
    );
  }

  function TestCasesTab({ results, darkMode }) {
    if (!results?.test_cases) return null;

    const testTypeColors = {
      'Functional': 'bg-blue-100 text-blue-700 dark:bg-blue-900 dark:text-blue-300',
      'Negative': 'bg-red-100 text-red-700 dark:bg-red-900 dark:text-red-300',
      'Edge': 'bg-purple-100 text-purple-700 dark:bg-purple-900 dark:text-purple-300',
      'Boundary': 'bg-yellow-100 text-yellow-700 dark:bg-yellow-900 dark:text-yellow-300',
      'Performance': 'bg-green-100 text-green-700 dark:bg-green-900 dark:text-green-300',
      'Security': 'bg-orange-100 text-orange-700 dark:bg-orange-900 dark:text-orange-300',
      'Concurrency': 'bg-cyan-100 text-cyan-700 dark:bg-cyan-900 dark:text-cyan-300',
      'Failure': 'bg-pink-100 text-pink-700 dark:bg-pink-900 dark:text-pink-300',
      'Integration': 'bg-indigo-100 text-indigo-700 dark:bg-indigo-900 dark:text-indigo-300'
    };

    return (
      <div className="space-y-6 animate-fade-in">
        {results.test_cases.map((tc, idx) => (
          <div key={idx} className={`rounded-xl border p-6 ${darkMode ? 'bg-gray-800 border-gray-700' : 'bg-white border-gray-200'}`}>
            <div className="flex items-start gap-4">
              <span className={`px-3 py-1.5 rounded-lg text-sm font-mono ${testTypeColors[tc.test_type] || 'bg-gray-100 text-gray-700'}`}>
                {tc.test_case_id}
              </span>
              <div className="flex-1">
                <h4 className={`text-xl font-medium mb-3 ${darkMode ? 'text-gray-200' : 'text-gray-800'}`}>{tc.title}</h4>
                <div className="flex flex-wrap gap-2 mb-4">
                  <span className={`px-3 py-1 rounded-lg text-sm ${darkMode ? 'bg-gray-700 text-gray-300' : 'bg-gray-100 text-gray-600'}`}>{tc.test_type}</span>
                  <span className={`px-3 py-1 rounded-lg text-sm ${darkMode ? 'bg-gray-700 text-gray-300' : 'bg-gray-100 text-gray-600'}`}>{tc.priority}</span>
                  <span className={`px-3 py-1 rounded-lg text-sm font-mono ${darkMode ? 'bg-gray-700 text-gray-400' : 'bg-gray-100 text-gray-500'}`}>{tc.behavior_id}</span>
                </div>
                
                {tc.preconditions?.length > 0 && (
                  <div className="mb-4">
                    <h5 className={`text-sm font-medium mb-2 ${darkMode ? 'text-gray-400' : 'text-gray-500'}`}>📋 Test Plan / Preconditions</h5>
                    <ul className={`space-y-1 ${darkMode ? 'text-gray-300' : 'text-gray-600'}`}>
                      {tc.preconditions.map((p, i) => (<li key={i} className="flex items-start gap-2"><span className="text-indigo-500 mt-1">•</span><span>{p}</span></li>))}
                    </ul>
                  </div>
                )}
                
                {tc.steps?.length > 0 && (
                  <div className="mb-4">
                    <h5 className={`text-sm font-medium mb-2 ${darkMode ? 'text-gray-400' : 'text-gray-500'}`}>🎬 Test Scenario / Steps</h5>
                    <div className={`rounded-lg p-4 ${darkMode ? 'bg-gray-700/50' : 'bg-gray-50'}`}>
                      <div className="space-y-3">
                        {tc.steps.map((step, i) => (
                          <div key={i} className="flex gap-4">
                            <span className={`px-2 py-0.5 rounded text-xs font-mono ${darkMode ? 'bg-gray-600 text-gray-400' : 'bg-gray-200 text-gray-500'}`}>{step.step_number}</span>
                            <div className="flex-1">
                              <p className={`${darkMode ? 'text-gray-300' : 'text-gray-700'}`}><span className="font-medium">Action:</span> {step.action}</p>
                              <p className={`text-sm ${darkMode ? 'text-gray-400' : 'text-gray-500'}`}><span className="font-medium">Expected:</span> {step.expected_intermediate}</p>
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                  </div>
                )}
                
                <div className={`rounded-lg p-4 ${darkMode ? 'bg-gray-700/50' : 'bg-gray-50'}`}>
                  <h5 className={`text-sm font-medium mb-2 ${darkMode ? 'text-gray-400' : 'text-gray-500'}`}>✅ Expected Result</h5>
                  <p className={`${darkMode ? 'text-gray-300' : 'text-gray-700'}`}>{tc.expected_result}</p>
                </div>
                
                {tc.confidence && (
                  <div className="flex items-center gap-2 mt-4">
                    <span className={`text-sm ${darkMode ? 'text-gray-500' : 'text-gray-400'}`}>Confidence:</span>
                    <div className={`h-3 w-28 rounded-full ${darkMode ? 'bg-gray-700' : 'bg-gray-200'}`}>
                      <div className="h-full bg-indigo-500 rounded-full" style={{ width: `${tc.confidence * 100}%` }} />
                    </div>
                    <span className={`text-sm font-medium ${darkMode ? 'text-gray-400' : 'text-gray-500'}`}>{Math.round(tc.confidence * 100)}%</span>
                  </div>
                )}
              </div>
            </div>
          </div>
        ))}
      </div>
    );
  }

  function CoverageTab({ results, darkMode }) {
    if (!results?.coverage_summary) return null;
    const { requirement_coverage, overall_coverage, gaps_detected, dimension_coverage } = results.coverage_summary;

    return (
      <div className="space-y-6 animate-fade-in">
        <div className={`rounded-xl p-8 ${darkMode ? 'bg-gray-800' : 'bg-white'}`}>
          <h3 className={`text-xl font-semibold mb-4 ${darkMode ? 'text-gray-100' : 'text-gray-800'}`}>Overall Coverage: {overall_coverage}%</h3>
          <div className={`h-6 rounded-full overflow-hidden ${darkMode ? 'bg-gray-700' : 'bg-gray-200'}`}>
            <div className={`h-full ${getCoverageBg(overall_coverage)} progress-bar`} style={{ width: `${overall_coverage}%` }} />
          </div>
        </div>

        <div className={`rounded-xl p-6 ${darkMode ? 'bg-gray-800' : 'bg-white'}`}>
          <h3 className={`text-lg font-semibold mb-4 ${darkMode ? 'text-gray-100' : 'text-gray-800'}`}>Per-Requirement Coverage</h3>
          <div className="space-y-4">
            {Object.entries(requirement_coverage || {}).map(([reqId, pct]) => (
              <div key={reqId} className="flex items-center gap-4">
                <span className={`text-sm font-mono w-28 ${darkMode ? 'text-gray-400' : 'text-gray-600'}`}>{reqId}</span>
                <div className={`flex-1 h-4 rounded-full overflow-hidden ${darkMode ? 'bg-gray-700' : 'bg-gray-200'}`}>
                  <div className={`h-full ${getCoverageBg(pct)} progress-bar`} style={{ width: `${pct}%` }} />
                </div>
                <span className={`text-sm font-medium w-14 ${getCoverageColor(pct)}`}>{pct}%</span>
              </div>
            ))}
          </div>
        </div>

        <div className={`rounded-xl p-6 ${darkMode ? 'bg-gray-800' : 'bg-white'}`}>
          <h3 className={`text-lg font-semibold mb-4 ${darkMode ? 'text-gray-100' : 'text-gray-800'}`}>Dimension Coverage</h3>
          <div className="grid grid-cols-3 gap-4">
            {Object.entries(dimension_coverage || {}).map(([dim, count]) => (
              <div key={dim} className={`p-4 rounded-lg ${darkMode ? 'bg-gray-700' : 'bg-gray-100'}`}>
                <div className={`text-3xl font-bold ${darkMode ? 'text-gray-200' : 'text-gray-800'}`}>{count}</div>
                <div className={`text-sm ${darkMode ? 'text-gray-400' : 'text-gray-500'}`}>{dim}</div>
              </div>
            ))}
          </div>
        </div>

        {gaps_detected?.length > 0 && (
          <div className={`rounded-xl p-6 border border-amber-200 dark:border-amber-800 ${darkMode ? 'bg-amber-900/20' : 'bg-amber-50'}`}>
            <h3 className={`text-lg font-semibold mb-3 ${darkMode ? 'text-amber-400' : 'text-amber-700'}`}>⚠️ Coverage Gaps</h3>
            <ul className={`space-y-1 text-sm ${darkMode ? 'text-amber-300' : 'text-amber-600'}`}>
              {gaps_detected.map((gap, idx) => (<li key={idx}>• {gap}</li>))}
            </ul>
          </div>
        )}
      </div>
    );
  }

  function RTMTab({ results, darkMode }) {
    if (!results?.test_cases) return null;

    return (
      <div className={`rounded-xl overflow-hidden ${darkMode ? 'bg-gray-800' : 'bg-white'}`}>
        <div className={`px-6 py-4 border-b ${darkMode ? 'border-gray-700 bg-gray-700/50' : 'border-gray-200 bg-gray-50'}`}>
          <h3 className={`text-lg font-semibold ${darkMode ? 'text-gray-100' : 'text-gray-800'}`}>🔗 Requirements Traceability Matrix</h3>
          <p className={`text-sm ${darkMode ? 'text-gray-400' : 'text-gray-500'}`}>Maps behaviors → test cases with full coverage tracking</p>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead className={darkMode ? 'bg-gray-700/50' : 'bg-gray-50'}>
              <tr>
                <th className={`px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider ${darkMode ? 'text-gray-300' : 'text-gray-600'}`}>Behavior ID</th>
                <th className={`px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider ${darkMode ? 'text-gray-300' : 'text-gray-600'}`}>Actor</th>
                <th className={`px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider ${darkMode ? 'text-gray-300' : 'text-gray-600'}`}>Action</th>
                <th className={`px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider ${darkMode ? 'text-gray-300' : 'text-gray-600'}`}>Test Types</th>
                <th className={`px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider ${darkMode ? 'text-gray-300' : 'text-gray-600'}`}>Coverage</th>
              </tr>
            </thead>
            <tbody className={`divide-y ${darkMode ? 'divide-gray-700' : 'divide-gray-200'}`}>
              {results.behaviors?.map((behavior) => {
                const behaviorTCs = results.test_cases?.filter(tc => tc.behavior_id === behavior.behavior_id) || [];
                const coverage = Math.min(Math.round((behaviorTCs.length / 6) * 100), 100);
                
                return (
                  <tr key={behavior.behavior_id} className={darkMode ? 'hover:bg-gray-700/30' : 'hover:bg-gray-50'}>
                    <td className={`px-4 py-3 text-sm font-mono ${darkMode ? 'text-indigo-400' : 'text-indigo-600'}`}>{behavior.behavior_id}</td>
                    <td className={`px-4 py-3 text-sm ${darkMode ? 'text-gray-300' : 'text-gray-700'}`}>{behavior.actor}</td>
                    <td className={`px-4 py-3 text-sm ${darkMode ? 'text-gray-300' : 'text-gray-700'}`}>{behavior.action} {behavior.object_name}</td>
                    <td className="px-4 py-3">
                      <div className="flex flex-wrap gap-1">
                        {[...new Set(behaviorTCs.map(tc => tc.test_type))].map(tt => (
                          <span key={tt} className={`px-1.5 py-0.5 rounded text-xs ${darkMode ? 'bg-gray-600 text-gray-300' : 'bg-gray-100 text-gray-600'}`}>{tt}</span>
                        ))}
                      </div>
                    </td>
                    <td className={`px-4 py-3 text-sm font-medium ${getCoverageColor(coverage)}`}>{coverage}%</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>
    );
  }

  return (
    <div className={`min-h-screen transition-colors duration-300 ${darkMode ? 'bg-gray-900' : 'bg-gray-50'}`}>
      <AnimationStyles />
      
      <div className="fixed top-4 right-4 z-50 flex flex-col gap-2">
        {toasts.map(toast => (
          <div key={toast.id} className={`px-4 py-3 rounded-lg shadow-lg text-white flex items-center gap-2 animate-slide-up ${
            toast.type === 'success' ? 'bg-green-500' : toast.type === 'error' ? 'bg-red-500' : toast.type === 'warning' ? 'bg-yellow-500' : 'bg-blue-500'
          }`}>
            {toast.type === 'success' && '✓'} {toast.type === 'error' && '✕'} {toast.message}
          </div>
        ))}
      </div>

      <div className="container mx-auto px-4 py-8 max-w-7xl">
        <header className="bg-gradient-to-r from-indigo-600 via-purple-600 to-pink-600 text-white rounded-2xl p-6 mb-8 shadow-lg">
          <div className="flex justify-between items-start">
            <div>
              <h1 className="text-3xl font-bold mb-2">🤖 AI Test Case Generator v2.0</h1>
              <p className="text-indigo-100 text-lg">Extraction Pipeline: Requirements → Behaviors → 9-Dimension Tests</p>
            </div>
            <button onClick={toggleTheme} className="p-2 rounded-lg bg-white/20 hover:bg-white/30 transition-colors" title="Toggle dark mode">
              {darkMode ? '☀️' : '🌙'}
            </button>
          </div>
        </header>

        {results && (
          <div className="grid grid-cols-2 md:grid-cols-5 gap-4 mb-8 animate-fade-in">
            <StatCard label="Requirements" value={results.requirements?.length || 0} color="indigo" />
            <StatCard label="Behaviors" value={results.behaviors?.length || 0} color="blue" />
            <StatCard label="Test Cases" value={results.test_cases?.length || 0} color="green" />
            <StatCard label="Ambiguous" value={ambigCount} />
            <StatCard label="Coverage" value={results.coverage_summary?.overall_coverage + '%' || '0%'} color="green" />
          </div>
        )}

        {loading && (
          <div className="mb-8 animate-fade-in">
            <div className={`rounded-xl p-4 ${darkMode ? 'bg-gray-800' : 'bg-white'}`}>
              <div className="flex justify-between text-sm mb-2">
                <span className={darkMode ? 'text-gray-400' : 'text-gray-500'}>{processingStep}</span>
                <span className={darkMode ? 'text-gray-300' : 'text-gray-700'}>{progress}%</span>
              </div>
              <div className={`h-3 rounded-full overflow-hidden ${darkMode ? 'bg-gray-700' : 'bg-gray-200'}`}>
                <div className="h-full bg-gradient-to-r from-indigo-500 via-purple-500 to-pink-500 progress-bar" style={{ width: `${progress}%` }} />
              </div>
            </div>
          </div>
        )}

        <div className={`rounded-2xl shadow-sm border p-6 mb-8 transition-colors duration-300 ${darkMode ? 'bg-gray-800 border-gray-700' : 'bg-white border-gray-100'}`}>
          <h2 className={`text-xl font-semibold mb-4 ${darkMode ? 'text-gray-100' : 'text-gray-800'}`}>📝 Input Requirements</h2>
          
          <div className="mb-4 flex flex-wrap gap-2">
            <span className={`text-sm ${darkMode ? 'text-gray-400' : 'text-gray-500'}`}>Load template:</span>
            {Object.keys(templates).map(key => (
              <button key={key} onClick={() => loadTemplate(key)} className="px-3 py-1 text-sm rounded-full transition-colors capitalize bg-indigo-100 text-indigo-700 hover:bg-indigo-200 dark:bg-indigo-900 dark:text-indigo-300">
                {key}
              </button>
            ))}
          </div>

          <textarea value={input} onChange={(e) => setInput(e.target.value)}
            placeholder="Enter your requirement(s)... Example: Users shall be able to reserve a parking slot for a future time window."
            className={`w-full h-40 p-4 border-2 rounded-xl text-base focus:outline-none focus:ring-2 transition-colors resize-y ${
              darkMode ? 'bg-gray-700 border-gray-600 text-gray-100 focus:border-indigo-500' : 'bg-gray-50 border-gray-200 text-gray-800 focus:border-indigo-500'
            }`} />
          
          <div className="flex justify-between items-center mt-4">
            <span className={`text-sm ${darkMode ? 'text-gray-400' : 'text-gray-500'}`}>{input.length} characters</span>
            <div className="flex gap-3">
              <button onClick={() => setInput('')} className={`px-6 py-2.5 border-2 rounded-xl transition-colors font-medium ${
                darkMode ? 'border-gray-600 text-gray-300 hover:bg-gray-700' : 'border-gray-200 text-gray-600 hover:bg-gray-50'
              }`}>Clear</button>
              <button onClick={handleGenerate} disabled={loading}
                className={`px-8 py-2.5 bg-gradient-to-r from-indigo-600 to-purple-600 text-white rounded-xl font-medium shadow-lg hover:shadow-xl transition-all flex items-center gap-2 ${
                  loading ? 'opacity-50 cursor-not-allowed' : 'hover:from-indigo-700 hover:to-purple-700'
                }`}>
                {loading ? '⏳ Processing...' : '⚡ Generate Tests'}
              </button>
            </div>
          </div>
        </div>

        {results && (
          <div className="animate-fade-in">
            <div className={`flex gap-1 p-1 rounded-xl mb-6 ${darkMode ? 'bg-gray-800' : 'bg-gray-100'}`}>
              {tabs.map(tab => (
                <button key={tab.id} onClick={() => setActiveTab(tab.id)}
                  className={`flex-1 flex items-center justify-center gap-2 px-4 py-2.5 rounded-lg transition-all font-medium ${
                    activeTab === tab.id
                      ? darkMode ? 'bg-indigo-600 text-white shadow-lg' : 'bg-white text-indigo-600 shadow-sm'
                      : darkMode ? 'text-gray-400 hover:text-gray-200 hover:bg-gray-700' : 'text-gray-500 hover:text-gray-700 hover:bg-white'
                  }`}>
                  <span>{tab.icon}</span>
                  <span className="hidden sm:inline">{tab.label}</span>
                  {tab.badge !== undefined && tab.badge !== null && tab.badge > 0 && (
                    <span className={`px-2 py-0.5 rounded-full text-xs font-bold ${
                      activeTab === tab.id ? 'bg-white/20 text-white' : darkMode ? 'bg-gray-700 text-gray-300' : 'bg-gray-200 text-gray-600'
                    }`}>{tab.badge}</span>
                  )}
                </button>
              ))}
            </div>

            <div className={activeTab === 'home' ? 'block' : 'hidden'}>
              <div className={`rounded-2xl shadow-sm border p-6 ${darkMode ? 'bg-gray-800 border-gray-700' : 'bg-white border-gray-100'}`}>
                <h3 className={`text-lg font-semibold mb-4 ${darkMode ? 'text-gray-100' : 'text-gray-800'}`}>📊 Generation Summary</h3>
                <div className="grid md:grid-cols-2 gap-4">
                  <div className={`p-4 rounded-xl ${darkMode ? 'bg-gray-700/50' : 'bg-gray-50'}`}>
                    <h4 className={`font-medium mb-2 ${darkMode ? 'text-gray-200' : 'text-gray-700'}`}>Pipeline Steps</h4>
                    <ul className={`text-sm space-y-1 ${darkMode ? 'text-gray-400' : 'text-gray-600'}`}>
                      <li>✓ Requirement Segmentation</li>
                      <li>✓ Atomic Behavior Extraction</li>
                      <li>✓ 9-Dimension Test Generation</li>
                      <li>✓ Enterprise Rule Enforcement</li>
                      <li>✓ Coverage Calculation</li>
                    </ul>
                  </div>
                  <div className={`p-4 rounded-xl ${darkMode ? 'bg-gray-700/50' : 'bg-gray-50'}`}>
                    <h4 className={`font-medium mb-2 ${darkMode ? 'text-gray-200' : 'text-gray-700'}`}>Test Dimensions</h4>
                    <div className="flex flex-wrap gap-1">
                      {['Functional', 'Negative', 'Edge', 'Boundary', 'Performance', 'Security', 'Concurrency', 'Failure', 'Integration'].map(dim => (
                        <span key={dim} className={`px-2 py-0.5 rounded text-xs ${darkMode ? 'bg-indigo-900/50 text-indigo-300' : 'bg-indigo-100 text-indigo-700'}`}>{dim}</span>
                      ))}
                    </div>
                  </div>
                </div>
              </div>
            </div>

            {activeTab === 'artifacts' && <ArtifactsTab results={results} darkMode={darkMode} />}
            {activeTab === 'behaviors' && <BehaviorsTab results={results} darkMode={darkMode} />}
            {activeTab === 'testcases' && <TestCasesTab results={results} darkMode={darkMode} />}
            {activeTab === 'rtm' && <RTMTab results={results} darkMode={darkMode} />}
          </div>
        )}

        {results && (
          <div className={`mt-8 rounded-2xl shadow-sm border p-6 animate-fade-in ${darkMode ? 'bg-gray-800 border-gray-700' : 'bg-white border-gray-100'}`}>
            <h3 className={`text-lg font-semibold mb-4 ${darkMode ? 'text-gray-100' : 'text-gray-800'}`}>💾 Export Options</h3>
            <div className="flex flex-wrap gap-3">
              <button onClick={() => handleExport('json')} className={`px-4 py-2 rounded-lg font-medium transition-colors ${
                darkMode ? 'bg-gray-700 text-gray-300 hover:bg-gray-600' : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
              }`}>📄 Export JSON</button>
              <button onClick={() => handleExport('markdown')} className={`px-4 py-2 rounded-lg font-medium transition-colors ${
                darkMode ? 'bg-gray-700 text-gray-300 hover:bg-gray-600' : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
              }`}>📝 Export Report</button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

export default App;
