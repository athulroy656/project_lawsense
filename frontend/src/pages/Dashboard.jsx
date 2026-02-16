import { useEffect, useState } from "react";
import { useAuth } from "../contexts/AuthContext";
import { useLocation, useNavigate, Link } from "react-router-dom";
import {
    fetchDocuments,
    fetchClauses,
    askQuestion,
    uploadDocument,
    fetchDocumentReport,
    deleteDocument,
} from "../api";
import "../App.css";
import "../enhancements.css";
import "../modern-things.css";

export default function Dashboard() {
    const { user, logoutUser } = useAuth();
    const location = useLocation();
    const navigate = useNavigate();

    // State
    const [documents, setDocuments] = useState([]);
    const [selectedDoc, setSelectedDoc] = useState(null);
    const [clauses, setClauses] = useState([]);
    const [riskSummary, setRiskSummary] = useState(null);
    const [report, setReport] = useState(null);
    const [question, setQuestion] = useState("");
    const [answer, setAnswer] = useState("");

    const [uploadFile, setUploadFile] = useState(null);
    const [uploadTitle, setUploadTitle] = useState("");
    const [uploadDocType, setUploadDocType] = useState("");
    const [uploadStatus, setUploadStatus] = useState("");
    const [expandedClause, setExpandedClause] = useState(null);
    const [hasConsent, setHasConsent] = useState(false);
    const [inputMethod, setInputMethod] = useState("file");
    const [pastedText, setPastedText] = useState("");
    const [charCount, setCharCount] = useState(0);
    const [aiLoading, setAiLoading] = useState(false);
    const [expandedRisks, setExpandedRisks] = useState({});
    const [showFullSummary, setShowFullSummary] = useState(false);
    const [docLoading, setDocLoading] = useState(false);
    const [toasts, setToasts] = useState([]);
    const [initialLoading, setInitialLoading] = useState(true);
    const [docTypeOverride, setDocTypeOverride] = useState("AUTO"); // Manual override for document type
    const [showAdvancedSettings, setShowAdvancedSettings] = useState(false); // Toggle for advanced section


    // Auto-upload effect for Guest Mode
    useEffect(() => {
        if (location.state?.fileToAnalyze && !uploadFile) {
            const file = location.state.fileToAnalyze;
            setUploadFile(file);
            setInputMethod("file");
            setHasConsent(true); // User dropped it specifically to analyze
            // We need to wait for state to update, or pass directly to a function
            performUpload(file, true);

            // Clear state so it doesn't re-trigger on refresh
            window.history.replaceState({}, document.title);
        }
    }, [location.state]);

    // Utility function to clean markdown from AI responses
    const cleanMarkdown = (text) => {
        if (!text) return '';
        return text
            .replace(/\*\*([^*]+)\*\*/g, '$1')  // Remove **bold**
            .replace(/\*([^*]+)\*/g, '$1')      // Remove *italic*
            .replace(/^\s*[\*\-]\s+/gm, '• ')   // Convert * or - to bullet
            .replace(/\n{3,}/g, '\n\n')         // Remove extra newlines
            .trim();
    };

    // Truncate text with ellipsis
    const truncateText = (text, maxLength = 150) => {
        if (!text || text.length <= maxLength) return text;
        return text.substring(0, maxLength).trim() + '...';
    };

    // Toast notification system
    const showToast = (message, type = 'info') => {
        const id = Date.now();
        const newToast = { id, message, type };
        setToasts(prev => [...prev, newToast]);

        // Auto-dismiss after 4 seconds
        setTimeout(() => {
            setToasts(prev => prev.filter(t => t.id !== id));
        }, 4000);
    };

    const dismissToast = (id) => {
        setToasts(prev => prev.filter(t => t.id !== id));
    };

    // Toggle risk explanation
    const toggleRiskExpanded = (idx) => {
        setExpandedRisks(prev => ({
            ...prev,
            [idx]: !prev[idx]
        }));
    };

    useEffect(() => {
        setInitialLoading(true);
        if (user) {
            fetchDocuments()
                .then(setDocuments)
                .catch(err => {
                    if (err.message !== "Unauthorized") console.error(err);
                })
                .finally(() => setInitialLoading(false));
        } else {
            setInitialLoading(false);
        }
    }, [user]);

    const loadDocument = async (doc) => {
        setSelectedDoc(doc);
        setRiskSummary(null);
        setReport(null);
        setDocLoading(true);
        // Reset Q&A state
        setQuestion("");
        setAnswer("");

        try {
            const [clausesData, reportData] = await Promise.all([
                fetchClauses(doc.id),
                fetchDocumentReport(doc.id, false, docTypeOverride),
            ]);

            setClauses(clausesData);
            setRiskSummary(reportData.risk_summary);
            setReport(reportData);
        } catch (error) {
            showToast("Failed to load document details. Please try again.", "error");
        } finally {
            setDocLoading(false);
        }
    };

    // Strict reset when document changes
    useEffect(() => {
        setQuestion("");
        setAnswer("");
    }, [selectedDoc]);

    const performUpload = async (fileObj = null, autoConsent = false) => {
        const currentFile = fileObj || uploadFile;
        // Validation handled in UI normally, but double check here

        if (!autoConsent && !hasConsent) {
            setUploadStatus("Please confirm you have the legal right to analyze this content.");
            return;
        }

        setUploadStatus("Uploading and analyzing...");

        try {
            const doc = await uploadDocument(
                inputMethod === "file" ? currentFile : null,
                uploadTitle,
                uploadDocType,
                inputMethod,
                inputMethod === "text" ? pastedText : null
            );
            setUploadStatus("Upload complete!");
            showToast("Document uploaded and analyzed successfully!", "success");
            setUploadFile(null);
            setPastedText("");
            setCharCount(0);
            setUploadTitle("");
            setUploadDocType("");
            setHasConsent(false);

            if (user) {
                const docs = await fetchDocuments();
                setDocuments(docs);
            }

            // For guest mode (or auth), load the new doc immediately
            if (doc && doc.id) {
                // Determine if we need to add it to local list (for Guests who don't have list)
                if (!user) {
                    setDocuments([doc]); // Just show this one doc
                }
                await loadDocument(doc);
            }
        } catch (error) {
            const errorMessage = error.message || "Upload failed. Please try again.";
            setUploadStatus(errorMessage);
            showToast(errorMessage, "error");
        }
    };

    const handleUpload = async (e) => {
        e.preventDefault();

        // Validation based on input method
        if (inputMethod === "file") {
            if (!uploadFile) {
                setUploadStatus("Please choose a PDF or DOCX file.");
                return;
            }
            if (uploadFile.size > 10 * 1024 * 1024) {
                setUploadStatus("File too large. Maximum size is 10MB.");
                return;
            }
        } else if (inputMethod === "text") {
            if (!pastedText.trim()) {
                setUploadStatus("Please paste a valid agreement text.");
                return;
            }
            if (pastedText.length < 200) {
                setUploadStatus("Text too short. Please paste a complete legal document (minimum 200 characters).");
                return;
            }
        }

        performUpload();
    };

    const handleDelete = async (docId) => {
        if (!confirm("Are you sure you want to delete this document?")) {
            return;
        }

        try {
            await deleteDocument(docId);
            setDocuments((prev) => prev.filter((d) => d.id !== docId));

            if (selectedDoc && selectedDoc.id === docId) {
                setSelectedDoc(null);
                setClauses([]);
                setRiskSummary(null);
                setReport(null);
                setAnswer("");
                setQuestion("");
            }
        } catch (error) {
            showToast("Failed to delete document. Please try again.", "error");
        }
    };

    const submitQuestion = async () => {
        if (!question.trim()) return;

        // Ensure a document is selected for scoped Q&A
        if (!selectedDoc) {
            showToast("Please select a document first to ask questions about it.", "error");
            return;
        }

        try {
            const res = await askQuestion(question, selectedDoc.id);
            // Backend returns: { question: "...", answer: { answer: "text", source_clauses: [] } }
            // We need to extract the inner 'answer' object to avoid React trying to render an object

            if (res.answer && typeof res.answer === 'object') {
                setAnswer(res.answer);
            } else {
                // Fallback for unexpected format
                setAnswer({ answer: res.answer || "No response received", source_clauses: [], confidence: 0 });
            }
        } catch (err) {
            console.error(err);
            showToast("Failed to get answer. Please try again.", "error");
        }
    };

    const generateAISummary = async () => {
        if (!selectedDoc) return;

        setAiLoading(true);
        try {
            const reportData = await fetchDocumentReport(selectedDoc.id, true, docTypeOverride);
            setReport(reportData);
            setRiskSummary(reportData.risk_summary);
            showToast("AI summary generated successfully!", "success");
        } catch (error) {
            console.error("AI generation error:", error);
            showToast("Failed to generate AI summary. Make sure Ollama is running.", "error");
        } finally {
            setAiLoading(false);
        }
    };


    // -- FINANCIAL DATA HELPERS --
    const renderFinancialSource = (sourceText) => {
        if (!sourceText) return null;
        return (
            <details style={{ marginTop: '0.5rem' }}>
                <summary style={{ cursor: 'pointer', color: 'var(--text-muted)', fontSize: '0.8rem', userSelect: 'none' }}>View source text</summary>
                <div style={{ marginTop: '0.4rem', padding: '0.5rem', background: 'var(--bg-2)', borderRadius: '4px', fontSize: '0.8rem', color: 'var(--text-main)', fontStyle: 'italic', borderLeft: '2px solid #cbd5e1' }}>
                    "{sourceText}"
                </div>
            </details>
        );
    };

    // Safe value formatter - prevents React crash from rendering objects
    const safeFormatValue = (value) => {
        if (value === null || value === undefined) return "—";
        if (typeof value === 'string' || typeof value === 'number') return value;
        if (typeof value === 'object') {
            // Handle structured amount objects {currency, value, original}
            if (value.original) return value.original;
            if (value.expression) return value.expression;
            if (value.value && value.currency) return `${value.currency} ${value.value.toLocaleString()}`;
            // Fallback for unknown object structure
            return "—";
        }
        return "—";
    };

    const formatAmount = (a) => {
        return safeFormatValue(a);
    };

    const renderFinancialRow = (label, value, source, isMissing = false) => (
        <div style={{ padding: '0.75rem 0', borderBottom: '1px solid #f1f5f9' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline' }}>
                <span style={{ color: 'var(--text-muted)', fontSize: '0.9rem', fontWeight: 500 }}>{label}</span>
                <span style={{ color: isMissing ? 'var(--text-muted)' : 'var(--text-main)', fontWeight: isMissing ? 400 : 600, fontSize: '0.95rem' }}>
                    {formatAmount(value)}
                </span>
            </div>
            {renderFinancialSource(source)}
        </div>
    );

    // Rule B: Financial Exposure - show if liability cap OR meaningful penalties exist
    const showFinancialExposure = (financialData) => {
        if (!financialData) return false;

        const hasLiabilityCap = financialData.liability_cap?.found;
        const hasPenalties = Array.isArray(financialData.penalties) &&
            financialData.penalties.some(p => {
                const amt = formatAmount(p.amount);
                return amt && amt !== "—" && amt !== "Not specified" && (p.source || p.source_text);
            });

        return hasLiabilityCap || hasPenalties;
    };

    // Rule A: Term & Validity - show if duration OR expiration exists
    const showTermValidity = (financialData) => {
        if (!financialData) return false;
        return financialData.duration?.found || financialData.expiration?.found;
    };

    // Rule C: Deadlines - show if deadlines array has items
    const showDeadlines = (financialData) => {
        if (!financialData) return false;
        return Array.isArray(financialData.deadlines) && financialData.deadlines.length > 0;
    };

    // Render Analysis Highlights - shows immediately after analysis
    const renderAnalysisHighlights = () => {
        if (!report) return null;

        const highlights = [];


        // Document type - HIDDEN (auto-detection not shown to users)
        // Manual override available in Advanced Settings

        // Exposure Level (replaces safety score)
        if (report.exposure_level) {
            const level = report.exposure_level;
            const levelConfig = {
                'Low': { icon: '✅', color: '#10b981' },
                'Moderate': { icon: '⚠️', color: '#f59e0b' },
                'Elevated': { icon: '⚠️', color: '#f97316' },
                'High': { icon: '🔴', color: '#ef4444' }
            };
            const config = levelConfig[level] || { icon: '❓', color: '#6b7280' };
            highlights.push({
                icon: config.icon,
                label: "Exposure Level",
                value: level,
                color: config.color
            });
        }

        // Total clauses found
        if (riskSummary?.total_clauses) {
            highlights.push({
                icon: "📋",
                label: "Clauses Identified",
                value: `${riskSummary.total_clauses} sections`
            });
        }

        // Key risks count
        if (report.top_risks && report.top_risks.length > 0) {
            highlights.push({
                icon: "⚠️",
                label: "Key Points to Review",
                value: `${report.top_risks.length} items`
            });
        }

        // If no highlights, show message
        if (highlights.length === 0) {
            return (
                <div style={{
                    background: 'var(--bg-1)',
                    padding: '1.5rem',
                    borderRadius: '12px',
                    textAlign: 'center',
                    marginBottom: '2rem'
                }}>
                    <p style={{ color: 'var(--text-muted)', margin: 0 }}>
                        No major highlights detected. Review the detailed analysis below.
                    </p>
                </div>
            );
        }


        return (
            <div className="ls-card" style={{
                marginBottom: '2rem',
                border: '1px solid var(--primary-glow)'
            }}>
                <h3 style={{ fontSize: '1.1rem', fontWeight: 700, margin: '0 0 1rem 0', color: 'var(--text-main)' }}>
                    📊 Analysis Highlights
                </h3>
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '1rem' }}>
                    {highlights.map((h, idx) => (
                        <div key={idx} style={{
                            padding: '1rem',
                            background: 'var(--bg-card-hover)',
                            borderRadius: '8px',
                            border: '1px solid var(--border-color)'
                        }}>
                            <div style={{ fontSize: '1.5rem', marginBottom: '0.5rem' }}>{h.icon}</div>
                            <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginBottom: '0.25rem', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                                {h.label}
                            </div>
                            <div style={{ fontSize: '1rem', fontWeight: 600, color: h.color || 'var(--text-main)', }}>
                                {h.value}
                            </div>
                        </div>
                    ))}
                </div>
            </div >
        );
    };

    return (
        <div className="app">
            {/* Toast Notifications */}
            <div className="toast-container">
                {toasts.map(toast => (
                    <div key={toast.id} className={`toast toast-${toast.type} fade-in`}>
                        <span className="toast-icon">
                            {toast.type === 'success' ? '✓' : toast.type === 'error' ? '✕' : 'ℹ'}
                        </span>
                        <span className="toast-message">{toast.message}</span>
                        <button className="toast-close" onClick={() => dismissToast(toast.id)}>×</button>
                    </div>
                ))}
            </div>

            {/* Header */}
            <header className="app-header">
                <div className="header-content">
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', width: '100%' }}>
                        <div className="header-brand" style={{ cursor: 'pointer' }} onClick={() => navigate('/')}>
                            <span className="header-logo">⚖️</span>
                            <div>
                                <h1>LawSense AI</h1>
                                <p className="app-subtitle">
                                    Context-aware legal document analysis for risk, clarity, and structural insight.
                                </p>
                            </div>
                        </div>

                        {user ? (
                            <button
                                onClick={logoutUser}
                                className="quick-action-link"
                                style={{ background: 'rgba(255,255,255,0.1)', padding: '0.5rem 1rem', borderRadius: '8px', border: '1px solid rgba(255,255,255,0.2)', cursor: 'pointer', color: 'white' }}
                            >
                                Sign Out
                            </button>
                        ) : (
                            <div style={{ display: 'flex', gap: '1rem' }}>
                                <Link to="/login" style={{ color: 'white' }}>Login</Link>
                                <Link to="/register" style={{
                                    background: 'var(--primary-500)',
                                    padding: '0.5rem 1rem',
                                    borderRadius: '8px',
                                    color: 'white',
                                    textDecoration: 'none'
                                }}>Register</Link>
                            </div>
                        )}
                    </div>
                </div>
            </header>

            <main className="layout">
                {/* Guest Banner - Professional Slim */}
                {!user && (
                    <div className="guest-banner-slim" style={{
                        gridColumn: '1 / -1',
                        background: 'var(--bg-1)', // Slate-50
                        borderBottom: '1px solid var(--bg-2)', // Slate-200
                        padding: '0.5rem 1rem',
                        textAlign: 'center',
                        color: 'var(--text-muted)', // Slate-500
                        fontSize: '0.85rem',
                        display: 'flex',
                        justifyContent: 'center',
                        alignItems: 'center',
                        gap: '0.5rem'
                    }}>
                        <span><strong>Guest Mode</strong> — This analysis is temporary.</span>
                        <Link to="/register" style={{ color: 'var(--primary)', fontWeight: '500', textDecoration: 'none' }}>Create an Account</Link>
                        <span>to save your history.</span>
                    </div>
                )}

                {/* Sidebar */}
                <aside className="sidebar">
                    <div className="sidebar-actions" style={{ marginBottom: '2rem' }}>
                        <button
                            onClick={() => {
                                setSelectedDoc(null);
                                setReport(null);
                                setRiskSummary(null);
                                setClauses([]);
                                setAnswer("");
                                setQuestion("");
                                setUploadStatus("");
                                setUploadFile(null);
                            }}
                            style={{
                                width: '100%',
                                padding: '0.8rem',
                                background: 'linear-gradient(135deg, #4f46e5 0%, #4338ca 100%)',
                                color: 'white',
                                border: 'none',
                                borderRadius: '8px',
                                cursor: 'pointer',
                                fontWeight: '600',
                                display: 'flex',
                                alignItems: 'center',
                                justifyContent: 'center',
                                gap: '0.5rem',
                                boxShadow: '0 4px 6px -1px rgba(79, 70, 229, 0.2)'
                            }}
                        >
                            <span>+</span> New Analysis
                        </button>
                    </div>

                    <div className="sidebar-section">
                        <h3 style={{ fontSize: '0.85rem', textTransform: 'uppercase', letterSpacing: '0.05em', color: 'var(--text-muted)', marginBottom: '1rem' }}>
                            Recent Documents
                        </h3>
                        {documents.length === 0 ? (
                            <p style={{ color: 'var(--text-muted)', fontSize: '0.9rem', fontStyle: 'italic' }}>No documents yet.</p>
                        ) : (
                            <div className="sidebar-doc-list" style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
                                {documents.map((doc) => (
                                    <div
                                        key={doc.id}
                                        onClick={() => loadDocument(doc)}
                                        className={`sidebar-doc-item ${selectedDoc && selectedDoc.id === doc.id ? "active" : ""}`}
                                        style={{
                                            padding: '0.75rem',
                                            borderRadius: '8px',
                                            cursor: 'pointer',
                                            background: selectedDoc && selectedDoc.id === doc.id ? 'rgba(99, 102, 241, 0.15)' : 'transparent',
                                            border: selectedDoc && selectedDoc.id === doc.id ? '1px solid #6366f1' : '1px solid transparent',
                                            transition: 'all 0.2s ease'
                                        }}
                                    >
                                        <div style={{
                                            fontWeight: 500,
                                            color: selectedDoc && selectedDoc.id === doc.id ? 'white' : '#e2e8f0',
                                            whiteSpace: 'nowrap',
                                            overflow: 'hidden',
                                            textOverflow: 'ellipsis',
                                            marginBottom: '0.2rem'
                                        }}>
                                            {doc.title || `Document ${doc.id}`}
                                        </div>
                                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                                            <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>{new Date(doc.uploaded_at).toLocaleDateString()}</span>
                                            {user && (
                                                <button
                                                    onClick={(e) => {
                                                        e.stopPropagation();
                                                        handleDelete(doc.id);
                                                    }}
                                                    style={{
                                                        background: 'none',
                                                        border: 'none',
                                                        color: 'var(--text-muted)',
                                                        cursor: 'pointer',
                                                        fontSize: '0.8rem',
                                                        padding: '2px'
                                                    }}
                                                    title="Delete"
                                                >
                                                    🗑️
                                                </button>
                                            )}
                                        </div>
                                    </div>
                                ))}
                            </div>
                        )}
                    </div>
                </aside>

                {/* Main Content */}
                <section className="main-content">
                    {!selectedDoc ? (
                        <div className="analysis-setup-wrapper" style={{ maxWidth: '800px', margin: '0 auto', paddingTop: '3rem' }}>
                            {/* 1. Header */}
                            <div className="setup-header" style={{ textAlign: 'center', marginBottom: '3rem' }}>
                                <h2 style={{ fontSize: '2rem', marginBottom: '0.75rem', fontWeight: 700, color: 'var(--text-main)' }}>Prepare Document for Analysis</h2>
                                <p style={{ color: 'var(--text-muted)', fontSize: '1.1rem' }}>
                                    Review and confirm document details before running context-aware analysis.
                                </p>
                            </div>

                            <form onSubmit={handleUpload}>
                                {/* 2. Smart Upload Card */}
                                <div className="smart-upload-card ls-card" style={{
                                    padding: '2.5rem',
                                    marginBottom: '2rem',
                                    textAlign: 'center',
                                    cursor: 'pointer',
                                    transition: 'all 0.2s ease',
                                    outline: uploadFile ? '2px solid var(--primary)' : 'none'
                                }}
                                    onClick={() => !uploadFile && document.getElementById('hidden-file-input').click()}
                                    onDragOver={(e) => { e.preventDefault(); e.currentTarget.style.borderColor = '#6366f1'; e.currentTarget.style.backgroundColor = '#f8fafc'; }}
                                    onDragLeave={(e) => { e.preventDefault(); e.currentTarget.style.borderColor = 'var(--border-color)'; e.currentTarget.style.backgroundColor = 'var(--bg-card)'; }}
                                    onDrop={(e) => {
                                        e.preventDefault();
                                        e.currentTarget.style.borderColor = 'var(--border-color)';
                                        e.currentTarget.style.backgroundColor = 'var(--bg-card)';
                                        if (e.dataTransfer.files[0]) {
                                            setUploadFile(e.dataTransfer.files[0]);
                                            setInputMethod("file");
                                        }
                                    }}
                                >
                                    <input
                                        id="hidden-file-input"
                                        type="file"
                                        accept=".pdf,.docx"
                                        style={{ display: 'none' }}
                                        onChange={(e) => {
                                            setUploadFile(e.target.files[0] || null);
                                            if (e.target.files[0]) setInputMethod("file");
                                        }}
                                    />

                                    {!uploadFile ? (
                                        // Empty State
                                        <div>
                                            <div style={{
                                                width: '64px', height: '64px', background: 'var(--bg-2)', borderRadius: '50%', color: 'var(--primary)',
                                                display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: '1.75rem', margin: '0 auto 1.5rem auto'
                                            }}>
                                                📂
                                            </div>
                                            <h3 style={{ color: 'var(--text-main)', fontSize: '1.2rem', fontWeight: 600, marginBottom: '0.5rem' }}>Drop your document here or click to upload</h3>
                                            <p style={{ color: 'var(--text-muted)', fontSize: '0.95rem' }}>PDF or DOCX • Max 10MB • Secure processing</p>
                                        </div>
                                    ) : (
                                        // Uploaded State
                                        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', textAlign: 'left', padding: '0 1rem' }}>
                                            <div style={{ display: 'flex', alignItems: 'center', gap: '1.5rem' }}>
                                                <div style={{ fontSize: '2.5rem' }}>📄</div>
                                                <div>
                                                    <h3 style={{ color: 'var(--text-main)', fontWeight: 600, fontSize: '1.1rem', marginBottom: '0.2rem' }}>{uploadFile.name}</h3>
                                                    <p style={{ color: 'var(--text-muted)', fontSize: '0.9rem' }}>
                                                        {(uploadFile.size / 1024 / 1024).toFixed(2)} MB • Ready for analysis
                                                    </p>
                                                </div>
                                            </div>
                                            <button
                                                type="button"
                                                onClick={(e) => { e.stopPropagation(); setUploadFile(null); }}
                                                className="remove-btn"
                                                style={{
                                                    background: 'transparent', border: '1px solid var(--border-color)', color: 'var(--text-muted)',
                                                    padding: '0.5rem 1rem', borderRadius: '8px', cursor: 'pointer', fontWeight: 500, fontSize: '0.9rem'
                                                }}
                                            >
                                                Change File
                                            </button>
                                        </div>
                                    )}
                                </div>

                                {/* 2b. Secondary actions (Paste text) */}
                                {!uploadFile && (
                                    <div style={{ textAlign: 'center', marginBottom: '2rem' }}>
                                        <button
                                            type="button"
                                            onClick={() => setInputMethod(inputMethod === "text" ? "file" : "text")}
                                            style={{ background: 'transparent', border: 'none', color: '#6366f1', fontSize: '0.95rem', cursor: 'pointer', fontWeight: 500 }}
                                        >
                                            {inputMethod === "text" ? "Cancel Text Entry" : "Or paste text directly"}
                                        </button>
                                    </div>
                                )}

                                {inputMethod === "text" && !uploadFile && (
                                    <div className="text-entry-panel" style={{ marginBottom: '2rem' }}>
                                        <textarea
                                            placeholder="Paste the full contract text here..."
                                            value={pastedText}
                                            onChange={(e) => {
                                                if (e.target.value.length <= 25000) {
                                                    setPastedText(e.target.value);
                                                    setCharCount(e.target.value.length);
                                                }
                                            }}
                                            style={{
                                                width: '100%',
                                                minHeight: '200px',
                                                padding: '1rem',
                                                borderRadius: '12px',
                                                background: 'var(--bg-1)',
                                                border: '1px solid var(--bg-2)',
                                                color: 'var(--text-main)',
                                                fontFamily: 'monospace',
                                                fontSize: '0.9rem',
                                                resize: 'vertical',
                                                boxShadow: '0 1px 2px 0 rgba(0,0,0,0.05)'
                                            }}
                                        />
                                        <div style={{ textAlign: 'right', fontSize: '0.85rem', color: 'var(--text-muted)', marginTop: '0.5rem' }}>
                                            {charCount.toLocaleString()} / 25,000 chars
                                        </div>
                                    </div>
                                )}

                                {/* 3. Detected & Config Panel (Only show if file or text present) */}
                                {(uploadFile || (inputMethod === "text" && pastedText.trim().length > 100)) && (
                                    <div className="config-panel" style={{ display: 'grid', gridTemplateColumns: 'minmax(300px, 1.5fr) 1fr', gap: '2rem', alignItems: 'start', marginBottom: '3rem' }}>

                                        {/* Left: Settings */}
                                        <div className="settings-box ls-card" style={{ padding: '1.5rem' }}>
                                            <h4 style={{ fontSize: '0.95rem', fontWeight: 700, color: 'var(--text-main)', marginBottom: '1.25rem' }}>Document Settings</h4>

                                            <div style={{ marginBottom: '1.25rem' }}>
                                                <label style={{ display: 'block', fontSize: '0.85rem', fontWeight: 500, color: 'var(--text-muted)', marginBottom: '0.5rem' }}>Document Type</label>
                                                <select
                                                    value={uploadDocType}
                                                    onChange={(e) => setUploadDocType(e.target.value)}
                                                    style={{
                                                        width: '100%', padding: '0.6rem', borderRadius: '8px', border: '1px solid var(--border-color)', color: 'var(--text-main)', fontSize: '0.95rem', background: 'var(--bg-card-hover)'
                                                    }}
                                                >
                                                    <option value="">✨ Auto-detect</option>
                                                    <option value="NDA_MUTUAL">NDA (Mutual)</option>
                                                    <option value="NDA_ONEWAY">NDA (One-way)</option>
                                                    <option value="TERMS_CONDITIONS">Terms & Conditions</option>
                                                    <option value="SERVICE_AGREEMENT">Service Agreement</option>
                                                    <option value="PRIVACY_POLICY">Privacy Policy</option>
                                                    <option value="OTHER">Other</option>
                                                </select>
                                            </div>

                                            <div style={{ marginBottom: '1.5rem' }}>
                                                <label style={{ display: 'block', fontSize: '0.85rem', fontWeight: 500, color: 'var(--text-muted)', marginBottom: '0.5rem' }}>Title (Optional)</label>
                                                <input
                                                    type="text"
                                                    placeholder="e.g. Vendor Agreement 2026"
                                                    value={uploadTitle}
                                                    onChange={(e) => setUploadTitle(e.target.value)}
                                                    style={{
                                                        width: '100%', padding: '0.6rem', borderRadius: '8px', border: '1px solid var(--border-color)', color: 'var(--text-main)', fontSize: '0.95rem', background: 'var(--bg-1)'
                                                    }}
                                                />
                                            </div>

                                            <label style={{ display: 'flex', alignItems: 'start', gap: '0.75rem', cursor: 'pointer', color: 'var(--text-muted)' }}>
                                                <input
                                                    type="checkbox"
                                                    checked={hasConsent}
                                                    onChange={(e) => setHasConsent(e.target.checked)}
                                                    style={{ width: '1.1rem', height: '1.1rem', marginTop: '2px' }}
                                                />
                                                <span style={{ fontSize: '0.85rem', lineHeight: 1.4 }}>
                                                    I confirm that I have the legal right to upload and analyze this document.
                                                </span>
                                            </label>
                                        </div>

                                        {/* Right: Readiness Checklist */}
                                        <div className="readiness-box ls-card" style={{ padding: '1.5rem', height: 'fit-content' }}>
                                            <h4 style={{ fontSize: '0.95rem', fontWeight: 700, color: 'var(--text-main)', marginBottom: '1rem' }}>Analysis Readiness</h4>
                                            <ul style={{ listStyle: 'none', padding: 0 }}>
                                                <li style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', marginBottom: '0.75rem', color: '#10b981', fontSize: '0.9rem' }}>
                                                    <span>✔</span> Document source provided
                                                </li>
                                                <li style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', marginBottom: '0.75rem', color: uploadDocType ? '#10b981' : 'var(--text-muted)', fontSize: '0.9rem' }}>
                                                    <span>{uploadDocType ? '✔' : '○'}</span> {uploadDocType ? 'Type selected manually' : 'Will auto-detect type'}
                                                </li>
                                                <li style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', marginBottom: '0.75rem', color: uploadTitle ? '#10b981' : '#f59e0b', fontSize: '0.9rem' }}>
                                                    <span>{uploadTitle ? '✔' : '!'}</span> {uploadTitle ? 'Title provided' : 'No title (will use filename)'}
                                                </li>
                                                <li style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', color: hasConsent ? '#10b981' : '#ef4444', fontSize: '0.9rem', fontWeight: 500 }}>
                                                    <span>{hasConsent ? '✔' : '✖'}</span> Client consent confirmed
                                                </li>
                                            </ul>
                                        </div>
                                    </div>
                                )}

                                {/* 4. Primary Action Button */}
                                <button
                                    type="submit"
                                    disabled={!hasConsent || (!uploadFile && (!pastedText.trim() || pastedText.length < 200))}
                                    style={{
                                        width: '100%',
                                        padding: '1.25rem',
                                        fontSize: '1.1rem',
                                        background: (!hasConsent || (!uploadFile && (!pastedText.trim() || pastedText.length < 200)))
                                            ? 'var(--bg-2)'
                                            : 'linear-gradient(135deg, #4f46e5 0%, #4338ca 100%)',
                                        color: (!hasConsent || (!uploadFile && (!pastedText.trim() || pastedText.length < 200)))
                                            ? 'var(--text-muted)'
                                            : 'white',
                                        border: 'none',
                                        borderRadius: '12px',
                                        cursor: (!hasConsent || (!uploadFile && (!pastedText.trim() || pastedText.length < 200)))
                                            ? 'not-allowed'
                                            : 'pointer',
                                        fontWeight: '700',
                                        boxShadow: (!hasConsent || (!uploadFile && (!pastedText.trim() || pastedText.length < 200)))
                                            ? 'none'
                                            : '0 10px 25px -5px rgba(79, 70, 229, 0.4)',
                                        transition: 'all 0.2s ease',
                                        transform: 'translateY(0)'
                                    }}
                                >
                                    {uploadStatus.includes("Uploading") ? (
                                        <span style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '1rem' }}>
                                            <span className="spinner-small"></span> Running Context Analysis...
                                        </span>
                                    ) : (
                                        "▶ Run Context-Aware Analysis"
                                    )}
                                </button>

                                {uploadStatus && (
                                    <p style={{ marginTop: '1.5rem', textAlign: 'center', color: uploadStatus.includes('failed') ? '#f87171' : '#4ade80' }}>
                                        {uploadStatus}
                                    </p>
                                )}
                            </form>

                            <div className="setup-footer" style={{ marginTop: '3rem', textAlign: 'center', color: 'var(--text-muted)', fontSize: '0.85rem' }}>
                                <p>🔒 Secure Processing • Private-by-Default • No Training on User Data</p>
                            </div>
                        </div>
                    ) : docLoading ? (
                        <div className="loading-state" style={{ padding: '6rem', textAlign: 'center' }}>
                            <div className="spinner" style={{ margin: '0 auto 2rem auto' }}></div>
                            <h3 style={{ color: 'var(--text-muted)' }}>Analyzing Document...</h3>
                        </div>
                    ) : !report ? (
                        <div className="error-state" style={{ padding: '6rem', textAlign: 'center' }}>
                            <div style={{ fontSize: '3rem', marginBottom: '1rem' }}>⚠️</div>
                            <h3 style={{ color: 'var(--text-muted)' }}>Analysis Data Unavailable</h3>
                            <p style={{ color: 'var(--text-muted)' }}>Please try uploading the document again.</p>
                        </div>
                    ) : (
                        <div className="analysis-container inverted-pyramid">
                            {/* Document Results Header (Replacing old one to match context) */}

                            {/* ===== NEW PROFESSIONAL HEADER SECTION ===== */}
                            <div className="analysis-header-grid" style={{
                                display: 'grid',
                                gridTemplateColumns: 'minmax(300px, 1fr) minmax(300px, 1.5fr)', // Sidebar-like split if space allows, or use flex-wrap
                                gap: '1.5rem',
                                marginBottom: '2rem',
                                alignItems: 'stretch'
                            }}>
                                {/* 1. Document Identity Card (Neutral) */}
                                <div className="doc-identity-card" style={{
                                    background: 'var(--bg-card)',
                                    border: '1px solid var(--border-color)',
                                    borderRadius: '12px',
                                    padding: '1.5rem',
                                    display: 'flex',
                                    flexDirection: 'column',
                                    justifyContent: 'center',
                                    boxShadow: '0 1px 2px 0 rgba(0, 0, 0, 0.05)'
                                }}>
                                    <div style={{ display: 'flex', alignItems: 'center', gap: '1rem', marginBottom: '1rem' }}>
                                        <div style={{
                                            background: 'var(--bg-2)',
                                            width: '48px',
                                            height: '48px',
                                            borderRadius: '8px',
                                            display: 'flex',
                                            alignItems: 'center',
                                            justifyContent: 'center',
                                            fontSize: '1.5rem'
                                        }}>
                                            📄
                                        </div>
                                        <div>
                                            <h2 style={{ fontSize: '1.1rem', fontWeight: 600, color: 'var(--text-main)', margin: 0, wordBreak: 'break-word' }}>
                                                {selectedDoc.title || selectedDoc.document_type_display}
                                            </h2>
                                            <p style={{ margin: '0.25rem 0 0 0', fontSize: '0.85rem', color: '#64748b' }}>
                                                {selectedDoc.filename || "Uploaded Document"}
                                            </p>
                                        </div>
                                    </div>

                                    <div style={{ borderTop: '1px solid var(--border-color)', paddingTop: '1rem', display: 'flex', gap: '1.5rem', fontSize: '0.85rem', color: '#64748b' }}>
                                        <div>
                                            <span style={{ display: 'block', fontSize: '0.75rem', textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: '0.25rem' }}>Analyzed On</span>
                                            <span style={{ color: 'var(--text-main)', fontWeight: 500 }}>
                                                {new Date(selectedDoc.uploaded_at).toLocaleDateString('en-US', { month: 'long', day: 'numeric', year: 'numeric' })}
                                            </span>
                                        </div>
                                        {/* Document Type - HIDDEN (auto-detection not shown) */}
                                    </div>
                                </div>

                                {/* 2. Overall Assessment Card (Calm/Professional) */}
                                <div className="assessment-card" style={{
                                    background: 'var(--bg-card)',
                                    border: '1px solid var(--border-color)',
                                    borderLeft: `4px solid ${report.verdict?.color === 'green' ? '#10b981' : report.verdict?.color === 'yellow' ? '#f59e0b' : report.verdict?.color === 'orange' ? '#f97316' : '#ef4444'}`,
                                    borderRadius: '12px',
                                    padding: '1.5rem',
                                    boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.05)',
                                    display: 'flex',
                                    flexDirection: 'column',
                                    justifyContent: 'center'
                                }}>
                                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '0.75rem' }}>
                                        <h3 style={{ fontSize: '0.9rem', textTransform: 'uppercase', letterSpacing: '0.05em', color: 'var(--text-muted)', margin: 0, fontWeight: 600 }}>
                                            Overall Assessment
                                        </h3>
                                        {/* Exposure Level Badge */}
                                        {report.exposure_level && (() => {
                                            const levelConfig = {
                                                'Low': { bg: '#d1fae5', border: '#6ee7b7', text: '#065f46' },
                                                'Moderate': { bg: '#fef3c7', border: '#fde68a', text: '#92400e' },
                                                'Elevated': { bg: '#fed7aa', border: '#fdba74', text: '#9a3412' },
                                                'High': { bg: '#fecaca', border: '#fca5a5', text: '#991b1b' }
                                            };
                                            const config = levelConfig[report.exposure_level] || { bg: '#f3f4f6', border: '#d1d5db', text: '#374151' };
                                            return (
                                                <div style={{
                                                    background: config.bg,
                                                    border: `1px solid ${config.border}`,
                                                    padding: '0.25rem 0.75rem',
                                                    borderRadius: '20px',
                                                    fontSize: '0.75rem',
                                                    color: config.text,
                                                    fontWeight: 600
                                                }}>
                                                    {report.exposure_level} Exposure
                                                </div>
                                            );
                                        })()}
                                    </div>

                                    {/* Assessment Text from Backend */}
                                    <p style={{ margin: '0 0 1rem 0', color: 'var(--text-muted)', fontSize: '0.95rem', lineHeight: 1.6 }}>
                                        {report.overall_assessment_text || "Analysis complete. Review the details below."}
                                    </p>

                                    {/* Top Contributing Factors */}
                                    {report.top_factors && report.top_factors.length > 0 && (
                                        <div style={{ marginBottom: '1rem' }}>
                                            <h4 style={{ fontSize: '0.85rem', fontWeight: 600, color: 'var(--text-muted)', margin: '0 0 0.5rem 0', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                                                Key Factors
                                            </h4>
                                            <ul style={{ margin: 0, paddingLeft: '1.25rem', color: 'var(--text-muted)', fontSize: '0.9rem', lineHeight: 1.6 }}>
                                                {report.top_factors.map((factor, idx) => (
                                                    <li key={idx} style={{ marginBottom: '0.25rem' }}>{factor}</li>
                                                ))}
                                            </ul>
                                        </div>
                                    )}

                                    {/* Clause Coverage */}
                                    {report.clause_coverage && (
                                        <div style={{
                                            background: 'var(--bg-card-hover)',
                                            border: '1px solid var(--border-color)',
                                            borderRadius: '8px',
                                            padding: '0.75rem',
                                            fontSize: '0.85rem',
                                            color: '#64748b'
                                        }}>
                                            <strong style={{ color: 'var(--text-muted)' }}>Coverage:</strong> Found {report.clause_coverage.found}/{report.clause_coverage.expected} key clause categories
                                        </div>
                                    )}
                                </div>
                            </div>

                            {/* ===== ANALYSIS HIGHLIGHTS (Shows immediately) ===== */}
                            {renderAnalysisHighlights()}

                            {/* ===== SECTION 2: HUMAN-IMPACT SUMMARY ===== */}
                            {report.top_risks && report.top_risks.length > 0 && (
                                <div className="things-to-know-card">
                                    <h3 className="things-header">⚠️ Most Important Points for You</h3>
                                    <div className="things-list">
                                        {report.top_risks.map((risk, idx) => (
                                            <div key={idx} className="thing-item-modern">
                                                <div className="thing-header-modern">
                                                    <span className="thing-icon-modern">{risk.icon || '📝'}</span>
                                                    <h4 className="thing-title-modern">{risk.title}</h4>
                                                </div>

                                                <div className="thing-body-modern" style={{ padding: '0 0.5rem 0.5rem 3.5rem' }}>
                                                    {/* What is happening (Primary) */}
                                                    <div style={{ marginBottom: '0.75rem' }}>
                                                        <strong style={{ display: 'block', color: 'var(--text-main)', fontSize: '0.95rem', marginBottom: '0.2rem' }}>What's happening:</strong>
                                                        <p style={{ margin: 0, color: 'var(--text-muted)', fontSize: '1rem' }}>
                                                            {risk.what_is_happening || risk.explanation}
                                                        </p>
                                                    </div>

                                                    {/* Why it matters (Primary) */}
                                                    <div style={{ marginBottom: '1rem' }}>
                                                        <strong style={{ display: 'block', color: 'var(--text-main)', fontSize: '0.95rem', marginBottom: '0.2rem' }}>Why this matters:</strong>
                                                        <p style={{ margin: 0, color: 'var(--text-main)', fontSize: '1rem' }}>
                                                            {risk.why_this_matters || risk.what_this_means}
                                                        </p>
                                                    </div>

                                                    {/* Context/Commonality (Secondary - subtle) */}
                                                    {risk.how_common && (
                                                        <div style={{
                                                            background: 'var(--bg-2)',
                                                            padding: '0.75rem',
                                                            borderRadius: '8px',
                                                            fontSize: '0.9rem',
                                                            color: '#64748b'
                                                        }}>
                                                            <strong style={{ color: 'var(--text-muted)' }}>Context:</strong> {risk.how_common}
                                                        </div>
                                                    )}
                                                </div>
                                            </div>
                                        ))}
                                    </div>
                                </div>
                            )}

                            {/* Show message if no risks */}
                            {(!report.top_risks || report.top_risks.length === 0) && (
                                <div className="things-to-know-card no-risks">
                                    <h3 className="things-header">✅ All Clear</h3>
                                    <p className="no-risks-text">This document appears to have standard, balanced terms. No significant concerns were detected. Always read carefully before signing.</p>
                                </div>
                            )}

                            {/* ===== TERM & VALIDITY CARD ===== */}
                            {/* Rule A: Show if duration OR expiration exists */}
                            {report.financial_data && showTermValidity(report.financial_data) && (
                                <div style={{
                                    background: 'var(--bg-card)',
                                    borderRadius: '16px',
                                    padding: '1.5rem',
                                    marginBottom: '2rem',
                                    border: '1px solid var(--border-color)',
                                    boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.05)'
                                }}>
                                    <h3 style={{ fontSize: '1.1rem', fontWeight: 700, margin: '0 0 1rem 0', color: 'var(--text-main)', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                                        📅 Term & Validity
                                    </h3>

                                    <div style={{ display: 'flex', flexDirection: 'column' }}>
                                        {/* Duration */}
                                        {report.financial_data.duration?.found && renderFinancialRow(
                                            "Contract Term",
                                            report.financial_data.duration.term,
                                            report.financial_data.duration.source,
                                            false
                                        )}

                                        {/* Expiration */}
                                        {report.financial_data.expiration?.found && renderFinancialRow(
                                            "Expiration Date",
                                            report.financial_data.expiration.date,
                                            report.financial_data.expiration.source,
                                            false
                                        )}
                                    </div>
                                </div>
                            )}

                            {/* ===== FINANCIAL EXPOSURE CARD ===== */}
                            {/* Rule B: Show if liability cap OR penalties exist */}
                            {report.financial_data && showFinancialExposure(report.financial_data) && (
                                <div className="financial-data-card" style={{
                                    background: 'var(--bg-card)',
                                    borderRadius: '16px',
                                    padding: '1.5rem',
                                    marginBottom: '2rem',
                                    border: '1px solid var(--border-color)',
                                    boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.05)'
                                }}>
                                    <h3 style={{ fontSize: '1.1rem', fontWeight: 700, margin: '0 0 1rem 0', color: 'var(--text-main)', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                                        💰 Financial Exposure
                                    </h3>

                                    <div style={{ display: 'flex', flexDirection: 'column' }}>
                                        {/* Liability Cap */}
                                        {(() => {
                                            const cap = report.financial_data.liability_cap;
                                            const val = cap?.found ? (cap.amount || "Cap found (details not specified)") : "Not detected";
                                            return renderFinancialRow("Liability Cap", val, cap?.source, !cap?.found);
                                        })()}

                                        {/* Penalties */}
                                        <div style={{ padding: '0.75rem 0', borderBottom: '1px solid #f1f5f9' }}>
                                            <span style={{ display: 'block', color: 'var(--text-muted)', fontSize: '0.9rem', fontWeight: 500, marginBottom: '0.4rem' }}>
                                                Financial Penalties
                                            </span>
                                            {(Array.isArray(report.financial_data.penalties) && report.financial_data.penalties.length > 0) ? (
                                                <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
                                                    {report.financial_data.penalties.map((p, idx) => {
                                                        const amt = formatAmount(p.amount);
                                                        if (!amt || amt === "Not specified") return null;
                                                        return (
                                                            <div key={idx} style={{ background: '#fff1f2', border: '1px solid #fecdd3', borderRadius: '6px', padding: '0.5rem 0.75rem' }}>
                                                                <div style={{ color: '#be123c', fontWeight: 600, fontSize: '0.9rem' }}>
                                                                    {amt}
                                                                </div>
                                                                {p.condition && p.condition !== "See clause text" && (
                                                                    <div style={{ fontSize: '0.8rem', color: '#881337' }}>Condition: {p.condition}</div>
                                                                )}
                                                                {renderFinancialSource(p.source || p.source_text)}
                                                            </div>
                                                        );
                                                    })}
                                                    {/* Fallback check if all were filtered out */}
                                                </div>
                                            ) : (
                                                <span style={{ color: 'var(--text-muted)', fontSize: '0.9rem' }}>None detected</span>
                                            )}
                                        </div>
                                    </div>

                                    {/* Advanced Raw JSON */}
                                    <details style={{ marginTop: '1.5rem', borderTop: '1px solid var(--border-color)', paddingTop: '1rem' }}>
                                        <summary style={{ color: 'var(--text-muted)', fontSize: '0.85rem', cursor: 'pointer' }}>Advanced: Show extraction data</summary>
                                        <div style={{ background: 'var(--bg-card-hover)', padding: '1rem', borderRadius: '8px', overflowX: 'auto', marginTop: '0.5rem' }}>
                                            <pre style={{ margin: 0, fontSize: '0.75rem', color: 'var(--text-muted)', fontFamily: 'monospace' }}>
                                                {JSON.stringify(report.financial_data, null, 2)}
                                            </pre>
                                        </div>
                                    </details>
                                </div>
                            )}

                            {/* ===== TIME-BASED OBLIGATIONS ===== */}
                            {/* Rule C: Show if deadlines array has items */}
                            {report.financial_data && showDeadlines(report.financial_data) && (() => {
                                // De-duplicate deadlines by grouping similar items
                                const deadlinesMap = new Map();

                                report.financial_data.deadlines.forEach((deadline) => {
                                    // Create stable grouping key
                                    const action = String(deadline.action || "unknown");
                                    const trigger = String(deadline.trigger || "unknown");
                                    const time = String(deadline.time || deadline.duration || "unknown");
                                    const key = `${action}|${trigger}|${time}`;

                                    if (!deadlinesMap.has(key)) {
                                        deadlinesMap.set(key, {
                                            ...deadline,
                                            count: 1,
                                            sources: [deadline.source || deadline.source_text]
                                        });
                                    } else {
                                        const existing = deadlinesMap.get(key);
                                        existing.count += 1;
                                        if (deadline.source || deadline.source_text) {
                                            existing.sources.push(deadline.source || deadline.source_text);
                                        }
                                    }
                                });

                                const uniqueDeadlines = Array.from(deadlinesMap.values());

                                // If no deadlines after de-dup, don't render
                                if (uniqueDeadlines.length === 0) return null;

                                // Helper: Map generic labels to human-readable text
                                const formatTrigger = (trigger) => {
                                    const t = String(trigger || "");
                                    if (t.toLowerCase().includes("specified event")) return "When relevant event happens";
                                    if (t === "unknown") return "";
                                    return t;
                                };

                                const formatAction = (action) => {
                                    const a = String(action || "");
                                    if (a.toLowerCase().includes("general obligation")) return "Required action";
                                    if (a === "unknown") return "";
                                    return a;
                                };

                                return (
                                    <div style={{
                                        background: 'var(--bg-card)',
                                        borderRadius: '16px',
                                        padding: '1.5rem',
                                        marginBottom: '2rem',
                                        border: '1px solid var(--border-color)',
                                        boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.05)'
                                    }}>
                                        <h3 style={{ fontSize: '1.1rem', fontWeight: 700, margin: '0 0 0.5rem 0', color: 'var(--text-main)', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                                            📋 Time-based Obligations
                                        </h3>
                                        <p style={{ fontSize: '0.9rem', color: 'var(--text-muted)', marginBottom: '1rem' }}>
                                            Time-sensitive requirements identified in this document.
                                        </p>

                                        <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
                                            {uniqueDeadlines.map((deadline, idx) => (
                                                <div key={idx} style={{
                                                    background: 'var(--bg-card-hover)',
                                                    border: '1px solid var(--border-color)',
                                                    borderRadius: '8px',
                                                    padding: '1rem'
                                                }}>
                                                    <div style={{ display: 'flex', alignItems: 'baseline', gap: '0.5rem', marginBottom: '0.5rem', flexWrap: 'wrap' }}>
                                                        <strong style={{ color: 'var(--text-main)', fontSize: '0.95rem' }}>
                                                            Deadline: {safeFormatValue(deadline.time) || safeFormatValue(deadline.duration) || "Timeframe specified"}
                                                        </strong>
                                                        {deadline.count > 1 && (
                                                            <span style={{
                                                                fontSize: '0.75rem',
                                                                color: 'var(--text-muted)',
                                                                background: '#e2e8f0',
                                                                padding: '0.15rem 0.5rem',
                                                                borderRadius: '12px',
                                                                fontWeight: 500
                                                            }}>
                                                                {deadline.count} occurrences
                                                            </span>
                                                        )}
                                                    </div>

                                                    {formatTrigger(deadline.trigger) && (
                                                        <div style={{ fontSize: '0.85rem', color: 'var(--text-muted)', marginBottom: '0.25rem' }}>
                                                            <span style={{ fontWeight: 600 }}>When:</span> {formatTrigger(deadline.trigger)}
                                                        </div>
                                                    )}

                                                    {formatAction(deadline.action) && (
                                                        <div style={{ fontSize: '0.85rem', color: 'var(--text-muted)', marginBottom: '0.5rem' }}>
                                                            <span style={{ fontWeight: 600 }}>Action:</span> {formatAction(deadline.action)}
                                                        </div>
                                                    )}

                                                    {deadline.sources && deadline.sources[0] && (
                                                        <details style={{ marginTop: '0.5rem' }}>
                                                            <summary style={{ cursor: 'pointer', color: 'var(--text-muted)', fontSize: '0.8rem', userSelect: 'none' }}>
                                                                View source text
                                                            </summary>
                                                            <div style={{
                                                                marginTop: '0.4rem',
                                                                padding: '0.5rem',
                                                                background: 'var(--bg-2)',
                                                                borderRadius: '4px',
                                                                fontSize: '0.8rem',
                                                                color: 'var(--text-muted)',
                                                                fontStyle: 'italic',
                                                                borderLeft: '2px solid #cbd5e1'
                                                            }}>
                                                                "{safeFormatValue(deadline.sources[0])}"
                                                                {deadline.count > 1 && (
                                                                    <div style={{ marginTop: '0.5rem', fontSize: '0.75rem', color: '#64748b' }}>
                                                                        + {deadline.count - 1} more similar {deadline.count === 2 ? 'occurrence' : 'occurrences'}
                                                                    </div>
                                                                )}
                                                            </div>
                                                        </details>
                                                    )}
                                                </div>
                                            ))}
                                        </div>
                                    </div>
                                );
                            })()}

                            {/* ===== ADVANCED SETTINGS (COLLAPSIBLE) ===== */}
                            <div style={{
                                background: 'var(--bg-card)',
                                borderRadius: '16px',
                                padding: '1.5rem',
                                marginBottom: '2rem',
                                border: '1px solid var(--border-color)',
                                boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.05)'
                            }}>
                                <button
                                    onClick={() => setShowAdvancedSettings(!showAdvancedSettings)}
                                    style={{
                                        width: '100%',
                                        display: 'flex',
                                        justifyContent: 'space-between',
                                        alignItems: 'center',
                                        background: 'none',
                                        border: 'none',
                                        padding: 0,
                                        cursor: 'pointer',
                                        color: 'var(--text-muted)',
                                        fontSize: '0.9rem',
                                        fontWeight: 600,
                                        textTransform: 'uppercase',
                                        letterSpacing: '0.05em'
                                    }}
                                >
                                    <span>⚙️ Advanced Settings</span>
                                    <span style={{ fontSize: '1.2rem' }}>{showAdvancedSettings ? '▼' : '▶'}</span>
                                </button>

                                {showAdvancedSettings && (
                                    <div style={{ marginTop: '1rem', paddingTop: '1rem', borderTop: '1px solid var(--border-color)' }}>
                                        <div style={{ marginBottom: '1rem' }}>
                                            <label style={{
                                                display: 'block',
                                                fontSize: '0.9rem',
                                                fontWeight: 600,
                                                color: 'var(--text-muted)',
                                                marginBottom: '0.5rem'
                                            }}>
                                                Document Type Override (Optional)
                                            </label>
                                            <p style={{ fontSize: '0.85rem', color: 'var(--text-muted)', margin: '0 0 0.75rem 0' }}>
                                                By default, the system auto-detects the document type. You can manually override it here to improve analysis accuracy.
                                            </p>
                                            <select
                                                value={docTypeOverride}
                                                onChange={(e) => setDocTypeOverride(e.target.value)}
                                                style={{
                                                    width: '100%',
                                                    padding: '0.75rem',
                                                    border: '1px solid var(--border-color)',
                                                    borderRadius: '8px',
                                                    fontSize: '0.95rem',
                                                    color: 'var(--text-main)',
                                                    background: 'var(--bg-card)',
                                                    cursor: 'pointer'
                                                }}
                                            >
                                                <option value="AUTO">Auto-detect (Default)</option>
                                                <option value="NDA_MUTUAL">NDA (Mutual)</option>
                                                <option value="NDA_ONEWAY">NDA (One-way)</option>
                                                <option value="SERVICE_AGREEMENT">Service Agreement</option>
                                                <option value="TERMS_CONDITIONS">Terms & Conditions</option>
                                                <option value="EMPLOYMENT_AGREEMENT">Employment Agreement</option>
                                                <option value="PRIVACY_POLICY">Privacy Policy</option>
                                                <option value="OTHER">Other/Unknown</option>
                                            </select>
                                        </div>

                                        {docTypeOverride !== "AUTO" && (
                                            <div style={{
                                                background: '#fef3c7',
                                                border: '1px solid #fde68a',
                                                borderRadius: '8px',
                                                padding: '0.75rem',
                                                fontSize: '0.85rem',
                                                color: '#92400e'
                                            }}>
                                                ℹ️ Analysis will use <strong>{docTypeOverride.replace(/_/g, ' ')}</strong> expectations. Click "Generate AI Summary" to re-analyze with this type.
                                            </div>
                                        )}
                                    </div>
                                )}
                            </div>

                            {/* ===== SECTION 3: AI EXECUTIVE SUMMARY ===== */}
                            <div className="summary-card" style={{
                                background: 'var(--bg-card)',
                                borderRadius: '16px',
                                padding: '1.5rem',
                                marginBottom: '2rem',
                                border: '1px solid var(--border-color)',
                                boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.05)'
                            }}>
                                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem', flexWrap: 'wrap', gap: '1rem' }}>
                                    <h3 style={{ fontSize: '1.3rem', fontWeight: 700, margin: 0, color: 'var(--text-main)', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                                        ✨ Executive Summary
                                    </h3>
                                    {!report.ai_summary && !aiLoading && (
                                        <button
                                            onClick={generateAISummary}
                                            className="quick-action-button"
                                            style={{ background: '#4f46e5', color: 'white', border: 'none' }}
                                        >
                                            Generate AI Summary
                                        </button>
                                    )}
                                </div>

                                {aiLoading && (
                                    <div className="ai-loading-state" style={{ padding: '2rem', textAlign: 'center', background: 'var(--bg-card-hover)', borderRadius: '12px' }}>
                                        <div className="spinner" style={{ margin: '0 auto 1rem auto' }}></div>
                                        <p style={{ color: '#64748b' }}>Consulting AI Model... This may take a minute.</p>
                                    </div>
                                )}

                                {!aiLoading && !report.ai_summary && (
                                    <div style={{ background: 'var(--bg-card-hover)', padding: '1.5rem', borderRadius: '12px', textAlign: 'center' }}>
                                        <p style={{ color: 'var(--text-muted)', margin: 0 }}>
                                            Get a concise, plain-English summary of this document's key points, obligations, and rights.
                                            Powered by local LLM.
                                        </p>
                                    </div>
                                )}

                                {report.ai_summary && (
                                    <div className="ai-content" style={{ fontSize: '1rem', lineHeight: 1.7, color: 'var(--text-main)' }}>
                                        {cleanMarkdown(report.ai_summary).split('\n').map((line, i) => {
                                            const trimmed = line.trim();
                                            if (trimmed.startsWith('•') || trimmed.startsWith('-')) {
                                                return (
                                                    <div key={i} style={{ display: 'flex', gap: '0.75rem', marginBottom: '0.5rem', paddingLeft: '1rem' }}>
                                                        <span style={{ color: 'var(--primary)', fontWeight: 'bold' }}>•</span>
                                                        <span>{trimmed.substring(1).trim()}</span>
                                                    </div>
                                                );
                                            }
                                            // Make headers distinct and visible
                                            // Regex catches standard questions, numbered headings (1. ...), and "Key ..."
                                            if (trimmed.match(/^(\d+\.|What|Who|When|Where|Why|How|Key|Financial|Termination).*/i) || (trimmed.length < 60 && trimmed.endsWith(':'))) {
                                                return <h4 key={i} style={{ marginTop: '1.25rem', marginBottom: '0.5rem', fontWeight: 700, fontSize: '1.05rem', color: 'var(--text-accent)', borderBottom: '1px solid var(--border-color)', paddingBottom: '0.25rem' }}>{trimmed}</h4>
                                            }
                                            return <p key={i} style={{ marginBottom: '1rem', color: 'var(--text-muted)' }}>{line}</p>;
                                        })}

                                        {report.ai_suggestions && (
                                            <div style={{ marginTop: '1.5rem', paddingTop: '1.5rem', borderTop: '1px solid #e2e8f0' }}>
                                                <h4 style={{ fontSize: '1.1rem', fontWeight: 600, marginBottom: '1rem', color: 'var(--text-accent)' }}>💡 AI Suggestions</h4>
                                                <div className="ai-content" style={{ fontSize: '0.95rem', lineHeight: 1.6, color: 'var(--text-muted)' }}>
                                                    {typeof report.ai_suggestions === 'string' ? (
                                                        cleanMarkdown(report.ai_suggestions).split('\n').map((line, i) => (
                                                            // Simple heuristic: if it looks like a list item, style it, otherwise just p
                                                            <p key={i} style={{ marginBottom: '0.5rem', paddingLeft: line.trim().startsWith('•') ? '1rem' : '0' }}>
                                                                {line}
                                                            </p>
                                                        ))
                                                    ) : Array.isArray(report.ai_suggestions) ? (
                                                        <ul style={{ paddingLeft: '1.5rem' }}>
                                                            {report.ai_suggestions.map((sug, i) => (
                                                                <li key={i} style={{ marginBottom: '0.5rem' }}>{sug}</li>
                                                            ))}
                                                        </ul>
                                                    ) : null}
                                                </div>
                                            </div>
                                        )}
                                    </div>
                                )}
                            </div>

                            {/* ===== SECTION 4: ASK QUESTIONS ===== */}
                            <div className="qa-card-simple">
                                <h3>💬 Have a specific question?</h3>
                                <div className="qa-input-row">
                                    <input
                                        type="text"
                                        placeholder="e.g. Can I get a refund?"
                                        value={question}
                                        maxLength={1000}
                                        onChange={(e) => setQuestion(e.target.value)}
                                        onKeyPress={(e) => e.key === 'Enter' && submitQuestion()}
                                    />
                                    <button onClick={submitQuestion}>Ask</button>
                                </div>

                                {report.suggested_questions && !answer && (
                                    <div className="popular-questions">
                                        <p>💡 Popular questions:</p>
                                        <div className="question-pills">
                                            {report.suggested_questions.slice(0, 3).map((q, i) => (
                                                <button key={i} onClick={() => setQuestion(q)}>{q}</button>
                                            ))}
                                        </div>
                                    </div>
                                )}

                                {answer && (
                                    <div className="qa-answer">
                                        <h4>Answer:</h4>
                                        <p>{typeof answer === 'object' ? answer.answer : answer}</p>
                                        {typeof answer === 'object' && answer.source_clauses?.length > 0 && (
                                            <div className="answer-sources">
                                                <p>📎 Sources:</p>
                                                {answer.source_clauses.slice(0, 2).map((c, i) => (
                                                    <div key={i} className="source-card">
                                                        <span className="source-label">{c.label}</span>
                                                        <span className="source-text">{truncateText(c.text, 100)}</span>
                                                    </div>
                                                ))}
                                            </div>
                                        )}
                                    </div>
                                )}
                            </div>

                            {/* ===== SECTION 5: FULL DETAILS (COLLAPSED) ===== */}
                            <details className="full-details-section">
                                <summary className="full-details-toggle">
                                    📊 View Full Technical Analysis
                                </summary>
                                <div className="full-details-content">

                                    {/* Stats Summary */}
                                    <div className="detail-section">
                                        <h4>📊 Document Statistics</h4>
                                        <div className="mini-stats">
                                            {/* Document Type - HIDDEN (auto-detection not shown) */}
                                            <span>✅ {riskSummary.good?.length || 0} clause types found</span>
                                            <span>📋 {riskSummary.total_clauses} total clauses</span>
                                        </div>
                                    </div>

                                    {/* Fairness Analysis */}
                                    {report.favorability && report.favorability.unfavorable_clauses && report.favorability.unfavorable_clauses.length > 0 && (
                                        <div className="detail-section">
                                            <h4>⚖️ Fairness Analysis</h4>
                                            <div className="favorability-summary">
                                                <div className="fav-stat high-risk">
                                                    <span className="fav-stat-number">{report.favorability.high_risk_count}</span>
                                                    <span className="fav-stat-label">High Risk</span>
                                                </div>
                                                <div className="fav-stat medium-risk">
                                                    <span className="fav-stat-number">{report.favorability.medium_risk_count}</span>
                                                    <span className="fav-stat-label">Medium Risk</span>
                                                </div>
                                                <div className="fav-stat low-risk">
                                                    <span className="fav-stat-number">{report.favorability.low_risk_count}</span>
                                                    <span className="fav-stat-label">Low Risk</span>
                                                </div>
                                            </div>
                                            <div className="favorability-clauses">
                                                {report.favorability.unfavorable_clauses.slice(0, 5).map((item, idx) => (
                                                    <div key={idx} className={`fairness-card risk-${item.risk_level.toLowerCase()}`}>
                                                        <div className="fairness-header">
                                                            <span className="clause-label-badge">{item.clause_label}</span>
                                                            <span className={`risk-badge ${item.risk_level.toLowerCase()}`}>
                                                                {item.risk_level === 'HIGH' ? '🔴' : '🟡'} {item.risk_level}
                                                            </span>
                                                        </div>
                                                        <div className="clause-excerpt">{truncateText(item.clause_text, 150)}</div>
                                                    </div>
                                                ))}
                                            </div>
                                        </div>
                                    )}

                                    {/* Asymmetry Detection */}
                                    {report.asymmetries && report.asymmetries.length > 0 && (
                                        <div className="detail-section">
                                            <h4>⚖️ One-Sided Terms ({report.asymmetries.length})</h4>
                                            <div className="asymmetry-list">
                                                {report.asymmetries.map((asym, idx) => (
                                                    <div key={idx} className={`asymmetry-item severity-${asym.severity.toLowerCase()}`}>
                                                        <div className="asymmetry-icon">
                                                            {asym.severity === 'HIGH' ? '🔴' : '🟡'}
                                                        </div>
                                                        <div className="asymmetry-content">
                                                            <div className="asymmetry-type">
                                                                {asym.type.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())}
                                                            </div>
                                                            <div className="asymmetry-description">{asym.description}</div>
                                                        </div>
                                                    </div>
                                                ))}
                                            </div>
                                        </div>
                                    )}

                                    {/* Risk & Ambiguity Insights (Redesigned) */}
                                    {report.loopholes && report.loopholes.total_count > 0 && (
                                        <div className="detail-section">
                                            <h4>⚠️ Risk & Ambiguity Insights</h4>

                                            {/* SECTION 1 — Risk Indicators (Primary) */}
                                            {report.loopholes.risk_indicators && report.loopholes.risk_indicators.length > 0 && (
                                                <div className="insight-group">
                                                    <h5 className="insight-group-title">🛑 Risk Indicators</h5>
                                                    <p className="insight-group-subtitle">Clauses that may expose you to disproportionate risk.</p>
                                                    <div className="loopholes-list">
                                                        {report.loopholes.risk_indicators.map((item, idx) => (
                                                            <div key={idx} className={`loophole-item severity-${item.severity.toLowerCase()} risk-indicator-card`}>
                                                                <div className="loophole-header">
                                                                    <span className={`severity-badge ${item.severity.toLowerCase()}`}>{item.severity}</span>
                                                                    <span className="loophole-category">{item.category}</span>
                                                                </div>
                                                                <div className="loophole-content">
                                                                    <p className="loophole-reasoning"><strong>Why this matters:</strong> {item.why_this_matters}</p>
                                                                    {item.matched_text && (
                                                                        <p className="loophole-issue"><strong>Risk Term:</strong> "{item.matched_text}"</p>
                                                                    )}
                                                                </div>
                                                            </div>
                                                        ))}
                                                    </div>
                                                </div>
                                            )}

                                            {/* SECTION 2 — Ambiguous Language (Secondary) */}
                                            {report.loopholes.ambiguous_language && report.loopholes.ambiguous_language.length > 0 && (
                                                <div className="insight-group" style={{ marginTop: '1.5rem' }}>
                                                    <h5 className="insight-group-title">🟡 Ambiguity Signals</h5>
                                                    <p className="insight-group-subtitle">Words that lack definition and may cause interpretation disputes.</p>
                                                    <div className="loopholes-list">
                                                        {report.loopholes.ambiguous_language.map((item, idx) => (
                                                            <div key={idx} className="loophole-item severity-medium ambiguity-card">
                                                                <div className="loophole-header">
                                                                    <span className="severity-badge medium">AMBIGUITY</span>
                                                                    <span className="loophole-category">{item.category || 'Vague Term'}</span>
                                                                </div>
                                                                <div className="loophole-content">
                                                                    {item.matched_text && (
                                                                        <p className="loophole-issue"><strong>Term:</strong> "{item.matched_text}"</p>
                                                                    )}
                                                                    <p className="loophole-reasoning">{item.why_this_matters}</p>
                                                                </div>
                                                            </div>
                                                        ))}
                                                    </div>
                                                </div>
                                            )}

                                            {/* SECTION 3 — Structural Observations */}
                                            {report.loopholes.structural_observations && report.loopholes.structural_observations.length > 0 && (
                                                <div className="insight-group" style={{ marginTop: '1.5rem' }}>
                                                    <h5 className="insight-group-title">🏗️ Contextual Observations</h5>
                                                    <p className="insight-group-subtitle">Missing standard clauses or unusual formatting.</p>
                                                    <div className="loopholes-list">
                                                        {report.loopholes.structural_observations.map((item, idx) => (
                                                            <div key={idx} className="loophole-item severity-low structure-card">
                                                                <div className="loophole-header">
                                                                    <span className="severity-badge low">MISSING</span>
                                                                    <strong className="loophole-category" style={{ marginLeft: '0.5rem' }}>{item.category || item.issue}</strong>
                                                                </div>
                                                                <div className="loophole-content">
                                                                    <p className="loophole-reasoning" style={{ marginBottom: '0.5rem' }}>{item.why_this_matters}</p>
                                                                    {item.suggestion && (
                                                                        <div style={{ marginTop: '0.5rem', fontSize: '0.9em', color: '#059669', background: '#ecfdf5', padding: '0.5rem', borderRadius: '4px' }}>
                                                                            <strong>💡 Suggestion:</strong> {item.suggestion}
                                                                        </div>
                                                                    )}
                                                                </div>
                                                            </div>
                                                        ))}
                                                    </div>
                                                </div>
                                            )}
                                        </div>
                                    )}

                                    {/* AI Executive Summary was moved up */}


                                </div>
                            </details>

                        </div>
                    )}
                </section>
            </main>
        </div >
    );
}
