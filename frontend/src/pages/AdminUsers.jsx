import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom"; // Added for potential navigation
import { fetchAdminUsers } from "../adminApi";
import AdminNavigation from "../components/AdminNavigation";
import "../App.css";

export default function AdminUsers() {
    const [users, setUsers] = useState([]);
    const [loading, setLoading] = useState(true);
    const [total, setTotal] = useState(0);
    const [page, setPage] = useState(1);
    const [search, setSearch] = useState("");
    const [pageSize] = useState(25);
    const [error, setError] = useState("");

    useEffect(() => {
        loadUsers();
    }, [page, search]);

    const loadUsers = async () => {
        setLoading(true);
        setError("");
        try {
            const data = await fetchAdminUsers(page, pageSize, search);
            setUsers(data.results);
            setTotal(data.total);
        } catch (err) {
            setError(err.message || "Failed to load users");
        } finally {
            setLoading(false);
        }
    };

    const handleSearch = (e) => {
        setSearch(e.target.value);
        setPage(1); // Reset to page 1 on search
    };

    const totalPages = Math.ceil(total / pageSize);

    return (
        <div className="ls-theme-dark" style={{ height: '100vh', overflowY: 'auto', padding: '2rem' }}>
            <AdminNavigation />

            <div className="ls-card">
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem', flexWrap: 'wrap', gap: '1rem' }}>
                    <h2 style={{ fontSize: '1.25rem', color: 'var(--text-main)', margin: 0 }}>Registered Users</h2>
                    <input
                        type="text"
                        placeholder="Search by username..."
                        value={search}
                        onChange={handleSearch}
                        style={{
                            padding: '0.5rem 1rem',
                            borderRadius: '8px',
                            width: '250px'
                        }}
                    />
                </div>

                {error && <div style={{ color: 'var(--danger)', padding: '1rem', background: 'rgba(239, 68, 68, 0.1)', borderRadius: '8px', marginBottom: '1rem' }}>{error}</div>}

                {loading ? (
                    <div style={{ padding: '2rem', textAlign: 'center', color: 'var(--text-muted)' }}>Loading users...</div>
                ) : (
                    <>
                        <div style={{ overflowX: 'auto' }}>
                            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.9rem' }}>
                                <thead>
                                    <tr style={{ background: 'var(--bg-2)', borderBottom: '2px solid var(--bg-1)' }}>
                                        <th style={{ padding: '0.75rem', textAlign: 'left', color: 'var(--text-main)' }}>ID</th>
                                        <th style={{ padding: '0.75rem', textAlign: 'left', color: 'var(--text-main)' }}>Username</th>
                                        <th style={{ padding: '0.75rem', textAlign: 'left', color: 'var(--text-main)' }}>Role</th>
                                        <th style={{ padding: '0.75rem', textAlign: 'left', color: 'var(--text-main)' }}>Joined</th>
                                        <th style={{ padding: '0.75rem', textAlign: 'left', color: 'var(--text-main)' }}>Last Login</th>
                                        <th style={{ padding: '0.75rem', textAlign: 'right', color: 'var(--text-main)' }}>Documents</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {users.length === 0 ? (
                                        <tr><td colSpan="6" style={{ padding: '1.5rem', textAlign: 'center', color: 'var(--text-muted)' }}>No users found.</td></tr>
                                    ) : (
                                        users.map(u => (
                                            <tr key={u.id} style={{ borderBottom: '1px solid var(--bg-2)' }}>
                                                <td style={{ padding: '0.75rem', color: 'var(--text-muted)' }}>#{u.id}</td>
                                                <td style={{ padding: '0.75rem', fontWeight: 500, color: 'var(--text-main)' }}>{u.username}</td>
                                                <td style={{ padding: '0.75rem' }}>
                                                    {u.is_staff || u.is_superuser ? (
                                                        <span style={{ background: 'var(--primary-glow)', color: 'white', padding: '0.2rem 0.6rem', borderRadius: '99px', fontSize: '0.75rem', fontWeight: 600 }}>Admin</span>
                                                    ) : (
                                                        <span style={{ color: 'var(--text-muted)' }}>User</span>
                                                    )}
                                                </td>
                                                <td style={{ padding: '0.75rem', color: 'var(--text-muted)' }}>{new Date(u.date_joined).toLocaleDateString()}</td>
                                                <td style={{ padding: '0.75rem', color: 'var(--text-muted)' }}>{u.last_login ? new Date(u.last_login).toLocaleDateString() : ('-')}</td>
                                                <td style={{ padding: '0.75rem', textAlign: 'right', fontWeight: 500, color: 'var(--text-main)' }}>{u.document_count}</td>
                                            </tr>
                                        ))
                                    )}
                                </tbody>
                            </table>
                        </div>

                        {/* Pagination */}
                        <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', gap: '1rem', marginTop: '2rem' }}>
                            <button
                                onClick={() => setPage(p => Math.max(1, p - 1))}
                                disabled={page === 1}
                                className="ls-btn-outline"
                                style={{ opacity: page === 1 ? 0.5 : 1, cursor: page === 1 ? 'not-allowed' : 'pointer' }}
                            >
                                Previous
                            </button>
                            <span style={{ color: 'var(--text-muted)', fontSize: '0.9rem' }}>Page {page} of {totalPages || 1}</span>
                            <button
                                onClick={() => setPage(p => Math.min(totalPages, p + 1))}
                                disabled={page >= totalPages}
                                className="ls-btn-outline"
                                style={{ opacity: page >= totalPages ? 0.5 : 1, cursor: page >= totalPages ? 'not-allowed' : 'pointer' }}
                            >
                                Next
                            </button>
                        </div>
                    </>
                )}
            </div>
        </div>
    );
}
