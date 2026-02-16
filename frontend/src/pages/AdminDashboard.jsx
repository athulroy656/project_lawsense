import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import {
    fetchAdminOverview,
    fetchAdminDocumentTypes,
    fetchAdminSystemHealth,
    fetchAdminRecentDocuments,
    adminDeleteDocument,
    adminRerunDocument
} from "../adminApi";
import AdminNavigation from "../components/AdminNavigation";
// App.css is loaded but theme.css overrides with higher specificity or we use direct styles
import "../App.css";

export default function AdminDashboard() {
    const [overview, setOverview] = useState(null);
    const [documentTypes, setDocumentTypes] = useState(null);
    const [systemHealth, setSystemHealth] = useState(null);
    const [recentDocs, setRecentDocs] = useState([]);

    const [loading, setLoading] = useState(true);
    const [error, setError] = useState("");
    const navigate = useNavigate();

    useEffect(() => {
        loadDashboardData();
    }, []);

    const loadDashboardData = async () => {
        setLoading(true);
        setError("");

        try {
            const [overviewData, typesData, healthData, docsData] = await Promise.all([
                fetchAdminOverview(),
                fetchAdminDocumentTypes(),
                fetchAdminSystemHealth(),
                fetchAdminRecentDocuments()
            ]);

            setOverview(overviewData);
            setDocumentTypes(typesData);
            setSystemHealth(healthData);
            setRecentDocs((docsData.documents || []).slice(0, 10)); // Top 10
        } catch (err) {
            setError(err.message || "Failed to load dashboard data");
            if (err.message.includes("Admin access required") || err.message.includes("logged in")) {
                setTimeout(() => navigate("/admin/login"), 2000);
            }
        } finally {
            setLoading(false);
        }
    };

    const handleRerun = async (id) => {
        try {
            if (!window.confirm("Re-run analysis for this document?")) return;
            await adminRerunDocument(id);
            alert("Analysis queued/completed.");
            loadDashboardData(); // Refresh
        } catch (e) {
            alert("Failed to re-run: " + e.message);
        }
    };

    const handleDelete = async (id) => {
        try {
            if (!window.confirm("Are you sure you want to delete this document?")) return;
            await adminDeleteDocument(id);
            setRecentDocs(prev => prev.filter(d => d.id !== id));
            loadDashboardData(); // Refresh stats
        } catch (e) {
            alert("Failed to delete: " + e.message);
        }
    };

    const handleView = (doc) => {
        const safeData = {
            id: doc.id,
            title: doc.title,
            type: doc.document_type_display,
            uploaded: doc.uploaded_at,
            status: doc.processed ? "Processed" : "Pending",
            owner: doc.owner_type
        };
        alert(JSON.stringify(safeData, null, 2));
    };

    if (loading) {
        return (
            <div className="ls-dashboard-container" style={{ display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                <div style={{ textAlign: 'center' }}>
                    <div className="spinner" style={{ margin: '0 auto 1rem', borderColor: 'var(--primary)', borderRightColor: 'transparent' }}></div>
                    <p style={{ color: 'var(--text-muted)' }}>Loading dashboard...</p>
                </div>
            </div>
        );
    }

    if (error) {
        return (
            <div className="ls-dashboard-container" style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', padding: '2rem' }}>
                <div className="error-container" style={{ background: 'rgba(239, 68, 68, 0.1)', border: '1px solid var(--danger)', color: 'var(--danger)', padding: '2rem', borderRadius: '12px', maxWidth: '500px', textAlign: 'center' }}>
                    <h2 style={{ marginBottom: '1rem' }}>⚠️ Error</h2>
                    <p>{error}</p>
                </div>
            </div>
        );
    }

    const trends = overview?.daily_trends || [];
    const risk = overview?.risk_overview || {};
    const processing = overview?.processing_metrics || {};
    const usage = overview?.usage_insights || {};

    return (
        <div className="ls-dashboard-container" style={{ height: '100vh', overflowY: 'auto', padding: '2rem' }}>
            <AdminNavigation />

            {/* KPI Cards */}
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))', gap: '1.5rem', marginBottom: '2rem' }}>
                <KPICard label="Total Documents" value={overview?.total_documents} icon="📄" color="blue" />
                <KPICard
                    label="Last 7 Days"
                    value={overview?.documents_last_7_days}
                    prevValue={overview?.documents_prev_7_days}
                    icon="📈"
                    color="green"
                />
                <KPICard label="Total Users" value={overview?.total_users} icon="👥" color="purple" />
                <KPICard label="Processing Failed" value={processing.failed_count || 0} icon="⚠️" color="red" />
            </div>

            {/* Analytics Row 1: Trends & Usage */}
            <div style={{ display: 'grid', gridTemplateColumns: 'repea(auto-fit, minmax(500px, 1fr))', gap: '1.5rem', marginBottom: '2rem' }}>
                {/* Daily Upload Trend */}
                <div className="ls-card" style={{ padding: '1.5rem' }}>
                    <h3 style={{ fontSize: '1.1rem', marginBottom: '1.5rem', color: 'var(--text-main)' }}>Daily Uploads (Last 7 Days)</h3>
                    <TrendChart data={trends} />
                </div>
            </div>

            {/* Analytics Row 2: Risk & Metrics */}
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(350px, 1fr))', gap: '1.5rem', marginBottom: '2rem' }}>

                {/* Risk Overview */}
                <div className="ls-card" style={{ padding: '1.5rem' }}>
                    <h3 style={{ fontSize: '1.1rem', marginBottom: '1rem', color: 'var(--text-main)' }}>Risk Exposure Overview</h3>
                    <RiskBarChart data={risk} />
                </div>

                {/* Processing & Health */}
                <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>

                    {/* Processing Metrics */}
                    <div className="ls-card" style={{ padding: '1.5rem', flex: 1 }}>
                        <h3 style={{ fontSize: '1.1rem', marginBottom: '1rem', color: 'var(--text-main)' }}>System Performance</h3>
                        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem' }}>
                            <MetricBox label="Avg Processing Time" value={`${processing.avg_time_seconds || 0}s`} />
                            <MetricBox label="Pending/Failed" value={processing.failed_count || 0} color={processing.failed_count > 0 ? '#ef4444' : '#10b981'} />
                            <MetricBox label="Guest Uploads" value={`${usage.guest_pct || 0}%`} />
                            <MetricBox label="Registered" value={`${100 - (usage.guest_pct || 0)}%`} />
                        </div>
                    </div>

                    {/* System Status */}
                    <div className="ls-card" style={{ padding: '1.5rem' }}>
                        <h3 style={{ fontSize: '1.1rem', marginBottom: '1rem', color: 'var(--text-main)' }}>Health Status</h3>
                        <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
                            <HealthItem label="Ollama AI" status={systemHealth?.ollama_status} />
                            <HealthItem label="ChromaDB" status={systemHealth?.chroma_db_status} />
                        </div>
                    </div>
                </div>
            </div>

            {/* Recent Activity Table */}
            <div className="ls-card" style={{ padding: '1.5rem' }}>
                <h3 style={{ fontSize: '1.1rem', marginBottom: '1.5rem', color: 'var(--text-main)' }}>Recent Activity</h3>
                <div style={{ overflowX: 'auto' }}>
                    <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.9rem', color: 'var(--text-muted)' }}>
                        <thead>
                            <tr style={{ borderBottom: '1px solid var(--border-color)', color: 'var(--text-main)' }}>
                                <th style={{ padding: '0.75rem', textAlign: 'left' }}>ID</th>
                                <th style={{ padding: '0.75rem', textAlign: 'left' }}>Title</th>
                                <th style={{ padding: '0.75rem', textAlign: 'left' }}>Type</th>
                                <th style={{ padding: '0.75rem', textAlign: 'left' }}>Format</th>
                                <th style={{ padding: '0.75rem', textAlign: 'left' }}>Owner</th>
                                <th style={{ padding: '0.75rem', textAlign: 'left' }}>Status</th>
                                <th style={{ padding: '0.75rem', textAlign: 'right' }}>Actions</th>
                            </tr>
                        </thead>
                        <tbody>
                            {recentDocs.map((doc) => (
                                <tr key={doc.id} style={{ borderBottom: '1px solid var(--border-color)' }}>
                                    <td style={{ padding: '0.75rem' }}>#{doc.id}</td>
                                    <td style={{ padding: '0.75rem', fontWeight: 500, maxWidth: '200px', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis', color: 'var(--text-main)' }}>{doc.title}</td>
                                    <td style={{ padding: '0.75rem' }}><Badge>{doc.document_type_display}</Badge></td>
                                    <td style={{ padding: '0.75rem' }}>{doc.file_type}</td>
                                    <td style={{ padding: '0.75rem', color: doc.owner_type === 'Registered' ? 'var(--primary)' : 'inherit' }}>{doc.owner_type}</td>
                                    <td style={{ padding: '0.75rem' }}>
                                        <span style={{ color: doc.processed ? 'var(--success)' : 'var(--warning)', fontWeight: 500 }}>
                                            {doc.processed ? 'Processed' : 'Pending'}
                                        </span>
                                    </td>
                                    <td style={{ padding: '0.75rem', textAlign: 'right' }}>
                                        <div style={{ display: 'flex', gap: '0.5rem', justifyContent: 'flex-end' }}>
                                            <ActionButton label="View" onClick={() => handleView(doc)} color="var(--primary)" />
                                            <ActionButton label="⟳" onClick={() => handleRerun(doc.id)} color="var(--warning)" title="Re-run Analysis" />
                                            <ActionButton label="×" onClick={() => handleDelete(doc.id)} color="var(--danger)" title="Delete" />
                                        </div>
                                    </td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>
            </div>
        </div>
    );
}

// --- Helper Components ---

function KPICard({ label, value, icon, color, prevValue }) {
    // Colors mapped to dark theme equivalents
    const colors = {
        blue: { bg: 'rgba(59, 130, 246, 0.1)', text: '#60a5fa' },
        green: { bg: 'rgba(34, 197, 94, 0.1)', text: '#4ade80' },
        purple: { bg: 'rgba(168, 85, 247, 0.1)', text: '#c084fc' },
        red: { bg: 'rgba(239, 68, 68, 0.1)', text: '#f87171' },
    };
    const c = colors[color] || colors.blue;

    let delta = null;
    if (prevValue !== undefined && value !== undefined) {
        const diff = value - prevValue;
        const pct = prevValue > 0 ? Math.round((diff / prevValue) * 100) : (diff > 0 ? 100 : 0);
        delta = { diff, pct };
    }

    return (
        <div className="ls-card" style={{ padding: '1.5rem', display: 'flex', alignItems: 'center', gap: '1rem' }}>
            <div style={{ width: '48px', height: '48px', borderRadius: '12px', background: c.bg, color: c.text, display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: '1.5rem' }}>
                {icon}
            </div>
            <div>
                <div style={{ fontSize: '0.85rem', color: 'var(--text-muted)', fontWeight: 500 }}>{label}</div>
                <div style={{ fontSize: '1.5rem', fontWeight: 700, color: 'var(--text-main)' }}>{value !== undefined ? value : '-'}</div>
                {delta && (
                    <div style={{ fontSize: '0.75rem', color: delta.diff >= 0 ? 'var(--success)' : 'var(--danger)', fontWeight: 600, marginTop: '0.2rem' }}>
                        {delta.diff >= 0 ? '▲' : '▼'} {Math.abs(delta.pct)}% ({delta.diff > 0 ? '+' : ''}{delta.diff})
                    </div>
                )}
            </div>
        </div>
    );
}

function TrendChart({ data }) {
    if (!data || data.length === 0) return <div style={{ color: 'var(--text-muted)' }}>No data</div>;
    const counts = data.map(d => d.count);
    const max = Math.max(...counts, 1);
    const niceMax = Math.ceil(max / 5) * 5;

    return (
        <div style={{ position: 'relative', height: '220px', paddingLeft: '40px', paddingBottom: '30px', borderBottom: '1px solid var(--border-color)' }}>
            <div style={{ position: 'absolute', left: 0, top: 0, bottom: '30px', width: '30px', display: 'flex', flexDirection: 'column', justifyContent: 'space-between', color: 'var(--text-muted)', fontSize: '0.7rem' }}>
                <span>{niceMax}</span>
                <span>{Math.round(niceMax / 2)}</span>
                <span>0</span>
            </div>

            <div style={{ display: 'flex', alignItems: 'flex-end', height: '100%', gap: '2%' }}>
                {data.map((d, i) => (
                    <div key={i} style={{ flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center', height: '100%', position: 'relative' }}>
                        <div style={{ flex: 1, width: '100%', display: 'flex', alignItems: 'flex-end', justifyContent: 'center' }}>
                            <div
                                style={{
                                    width: '60%',
                                    height: `${(d.count / niceMax) * 100}%`,
                                    background: 'var(--primary)',
                                    borderRadius: '4px 4px 0 0',
                                    transition: 'height 0.3s ease',
                                    minHeight: d.count > 0 ? '4px' : '0',
                                    position: 'relative'
                                }}
                                title={`${d.count} uploads on ${d.date}`}
                            >
                                <span style={{
                                    position: 'absolute',
                                    top: '-20px',
                                    left: '50%',
                                    transform: 'translateX(-50%)',
                                    fontSize: '0.75rem',
                                    fontWeight: 600,
                                    color: 'var(--text-main)'
                                }}>
                                    {d.count}
                                </span>
                            </div>
                        </div>
                        <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: '0.5rem', transform: 'rotate(-45deg)', transformOrigin: 'top left', whiteSpace: 'nowrap', position: 'absolute', bottom: '-25px' }}>
                            {d.date.slice(5)}
                        </div>
                    </div>
                ))}
            </div>
        </div>
    );
}

function RiskBarChart({ data }) {
    const levels = ["Low", "Moderate", "Elevated", "High"];
    const colors = { Low: "var(--success)", Moderate: "var(--warning)", Elevated: "#f97316", High: "var(--danger)" };
    const total = Object.values(data).reduce((a, b) => a + b, 0);

    return (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
            {levels.map(lvl => {
                const count = data[lvl] || 0;
                const pct = total > 0 ? (count / total) * 100 : 0;
                return (
                    <div key={lvl}>
                        <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.85rem', marginBottom: '0.25rem' }}>
                            <span style={{ fontWeight: 500, color: 'var(--text-muted)' }}>{lvl}</span>
                            <span style={{ color: 'var(--text-muted)' }}>{count} ({Math.round(pct)}%)</span>
                        </div>
                        <div style={{ width: '100%', height: '8px', background: 'var(--bg-card-hover)', borderRadius: '4px', overflow: 'hidden' }}>
                            <div style={{ width: `${pct}%`, height: '100%', background: colors[lvl], borderRadius: '4px' }}></div>
                        </div>
                    </div>
                );
            })}
        </div>
    );
}

function MetricBox({ label, value, color }) {
    return (
        <div style={{ padding: '1rem', background: 'var(--bg-card-hover)', borderRadius: '8px', textAlign: 'center' }}>
            <div style={{ fontSize: '1.25rem', fontWeight: 700, color: color || 'var(--text-main)' }}>{value}</div>
            <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', fontWeight: 500 }}>{label}</div>
        </div>
    );
}

function HealthItem({ label, status }) {
    const getStyle = (s) => {
        if (s === "up" || s === "ok") return { color: 'var(--success)', bg: 'rgba(16, 185, 129, 0.1)', text: 'Operational' };
        if (s === "down" || s === "fail") return { color: 'var(--danger)', bg: 'rgba(239, 68, 68, 0.1)', text: 'Down' };
        return { color: 'var(--text-muted)', bg: 'var(--bg-card-hover)', text: 'Unknown' };
    };
    const style = getStyle(status);
    return (
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '0.75rem', background: 'var(--bg-card-hover)', borderRadius: '8px' }}>
            <span style={{ fontSize: '0.9rem', color: 'var(--text-muted)', fontWeight: 500 }}>{label}</span>
            <span style={{ fontSize: '0.75rem', padding: '0.2rem 0.6rem', borderRadius: '99px', background: style.bg, color: style.color, fontWeight: 600 }}>
                {style.text}
            </span>
        </div>
    );
}

function Badge({ children }) {
    return <span style={{ background: 'var(--bg-card-hover)', color: 'var(--text-muted)', padding: '0.2rem 0.5rem', borderRadius: '4px', fontSize: '0.75rem' }}>{children}</span>;
}

function ActionButton({ label, onClick, color, title }) {
    return (
        <button
            onClick={onClick}
            title={title}
            style={{
                background: 'none',
                border: `1px solid ${color}`,
                color: color,
                borderRadius: '4px',
                padding: '0.2rem 0.5rem',
                cursor: 'pointer',
                fontSize: '0.8rem',
                fontWeight: 600,
                minWidth: '24px'
            }}
        >
            {label}
        </button>
    );
}
