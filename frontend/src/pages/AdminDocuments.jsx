import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { fetchAdminRecentDocuments } from "../adminApi";
import AdminNavigation from "../components/AdminNavigation";
import "../App.css";

export default function AdminDocuments() {
    const [allDocs, setAllDocs] = useState([]);
    const [filteredDocs, setFilteredDocs] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState("");
    const navigate = useNavigate();

    // Filters
    const [search, setSearch] = useState("");
    const [typeFilter, setTypeFilter] = useState("ALL");
    const [statusFilter, setStatusFilter] = useState("ALL");

    useEffect(() => {
        loadDocuments();
    }, []);

    useEffect(() => {
        let result = allDocs;

        if (search) {
            const q = search.toLowerCase();
            result = result.filter(d =>
                d.title.toLowerCase().includes(q) ||
                String(d.id).includes(q)
            );
        }

        if (typeFilter !== "ALL") {
            result = result.filter(d => d.document_type === typeFilter);
        }

        if (statusFilter !== "ALL") {
            const isProcessed = statusFilter === "PROCESSED";
            result = result.filter(d => d.processed === isProcessed);
        }

        setFilteredDocs(result);
    }, [search, typeFilter, statusFilter, allDocs]);

    const loadDocuments = async () => {
        setLoading(true);
        setError("");

        try {
            const docsData = await fetchAdminRecentDocuments();
            setAllDocs(docsData.documents || []);
            setFilteredDocs(docsData.documents || []);
        } catch (err) {
            setError(err.message || "Failed to load documents");
            if (err.message.includes("Admin access required") || err.message.includes("logged in")) {
                setTimeout(() => navigate("/admin/login"), 2000);
            }
        } finally {
            setLoading(false);
        }
    };

    // Extract unique document types for filter
    const docTypes = [...new Set(allDocs.map(d => d.document_type))];

    if (loading) {
        return (
            <div className="ls-theme-dark" style={{ height: '100vh', overflowY: 'auto', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                <div style={{ textAlign: 'center' }}>
                    <div className="spinner" style={{ margin: '0 auto 1rem', borderColor: 'var(--primary)', borderRightColor: 'transparent' }}></div>
                    <p style={{ color: 'var(--text-muted)' }}>Loading documents...</p>
                </div>
            </div>
        );
    }

    if (error) {
        return (
            <div className="ls-theme-dark" style={{ height: '100vh', overflowY: 'auto', display: 'flex', alignItems: 'center', justifyContent: 'center', padding: '2rem' }}>
                <div style={{ background: 'rgba(239, 68, 68, 0.1)', border: '1px solid var(--danger)', color: 'var(--danger)', padding: '2rem', borderRadius: '12px', maxWidth: '500px', textAlign: 'center' }}>
                    <h2 style={{ marginBottom: '1rem' }}>⚠️ Error</h2>
                    <p>{error}</p>
                </div>
            </div>
        );
    }

    return (
        <div className="ls-theme-dark" style={{ height: '100vh', overflowY: 'auto', padding: '2rem' }}>
            <AdminNavigation />

            <div className="ls-card">
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem', flexWrap: 'wrap', gap: '1rem' }}>
                    <h2 style={{ fontSize: '1.25rem', fontWeight: 600, color: 'var(--text-main)', margin: 0 }}>
                        📋 Documents ({filteredDocs.length})
                    </h2>

                    {/* Filters */}
                    <div style={{ display: 'flex', gap: '0.75rem', flexWrap: 'wrap' }}>
                        <input
                            type="text"
                            placeholder="Search title or ID..."
                            value={search}
                            onChange={(e) => setSearch(e.target.value)}
                            style={{ padding: '0.5rem 1rem', borderRadius: '8px', width: '200px' }}
                        />

                        <select
                            value={typeFilter}
                            onChange={(e) => setTypeFilter(e.target.value)}
                            style={{ padding: '0.5rem 1rem', borderRadius: '8px' }}
                        >
                            <option value="ALL">All Types</option>
                            {docTypes.map(t => (
                                <option key={t} value={t}>{t.replace(/_/g, ' ')}</option>
                            ))}
                        </select>

                        <select
                            value={statusFilter}
                            onChange={(e) => setStatusFilter(e.target.value)}
                            style={{ padding: '0.5rem 1rem', borderRadius: '8px' }}
                        >
                            <option value="ALL">All Status</option>
                            <option value="PROCESSED">Processed</option>
                            <option value="PENDING">Pending</option>
                        </select>
                    </div>
                </div>

                <div style={{ overflowX: 'auto' }}>
                    <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.9rem', color: 'var(--text-muted)' }}>
                        <thead>
                            <tr style={{ borderBottom: '1px solid var(--bg-2)', color: 'var(--text-main)' }}>
                                <th style={{ padding: '0.75rem', textAlign: 'left' }}>ID</th>
                                <th style={{ padding: '0.75rem', textAlign: 'left' }}>Title</th>
                                <th style={{ padding: '0.75rem', textAlign: 'left' }}>Type</th>
                                <th style={{ padding: '0.75rem', textAlign: 'left' }}>Format</th>
                                <th style={{ padding: '0.75rem', textAlign: 'left' }}>Owner</th>
                                <th style={{ padding: '0.75rem', textAlign: 'left' }}>Uploaded At</th>
                                <th style={{ padding: '0.75rem', textAlign: 'left' }}>Status</th>
                            </tr>
                        </thead>
                        <tbody>
                            {filteredDocs.map((doc) => (
                                <tr key={doc.id} style={{ borderBottom: '1px solid var(--bg-2)' }}>
                                    <td style={{ padding: '0.75rem' }}>#{doc.id}</td>
                                    <td style={{ padding: '0.75rem', color: 'var(--text-main)', fontWeight: 500, maxWidth: '200px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{doc.title}</td>
                                    <td style={{ padding: '0.75rem' }}>
                                        <span style={{ padding: '0.2rem 0.6rem', background: 'var(--bg-2)', color: 'var(--text-muted)', borderRadius: '4px', fontSize: '0.8rem' }}>
                                            {doc.document_type_display}
                                        </span>
                                    </td>
                                    <td style={{ padding: '0.75rem' }}>
                                        {doc.file_type || (doc.input_method === 'FILE' ? 'File' : 'Text')}
                                    </td>
                                    <td style={{ padding: '0.75rem' }}>
                                        <span style={{ padding: '0.2rem 0.6rem', background: (doc.owner_type === 'Registered' || doc.user_id) ? 'rgba(99, 102, 241, 0.1)' : 'var(--bg-2)', color: (doc.owner_type === 'Registered' || doc.user_id) ? 'var(--primary)' : 'var(--text-muted)', borderRadius: '99px', fontSize: '0.75rem', fontWeight: 600 }}>
                                            {doc.owner_type || (doc.user_id ? 'Registered' : 'Guest')}
                                        </span>
                                    </td>
                                    <td style={{ padding: '0.75rem' }}>
                                        {new Date(doc.uploaded_at).toLocaleString()}
                                    </td>
                                    <td style={{ padding: '0.75rem' }}>
                                        <span style={{ display: 'inline-flex', alignItems: 'center', gap: '0.4rem', color: doc.processed ? 'var(--success)' : 'var(--warning)', fontWeight: 500 }}>
                                            <span style={{ width: '8px', height: '8px', borderRadius: '50%', background: doc.processed ? 'var(--success)' : 'var(--warning)' }}></span>
                                            {doc.processed ? 'Processed' : 'Pending'}
                                        </span>
                                    </td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>
                {filteredDocs.length === 0 && (
                    <div style={{ textAlign: 'center', padding: '3rem', color: 'var(--text-muted)' }}>
                        No documents found matching your filters.
                    </div>
                )}
            </div>
        </div>
    );
}
