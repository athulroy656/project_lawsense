import { Link, useLocation, useNavigate } from "react-router-dom";

export default function AdminNavigation() {
    const location = useLocation();
    const navigate = useNavigate();

    const handleLogout = () => {
        localStorage.removeItem("access_token");
        localStorage.removeItem("refresh_token");
        navigate("/admin/login");
    };

    const isActive = (path) => location.pathname === path;

    return (
        <div style={{
            background: 'var(--bg-card)',
            borderRadius: '16px',
            padding: '1rem 2rem',
            marginBottom: '2rem',
            boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.1)',
            border: '1px solid var(--border-color)',
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            flexWrap: 'wrap',
            gap: '1rem'
        }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '2rem' }}>
                <div>
                    <h1 style={{
                        fontSize: '1.5rem',
                        fontWeight: 700,
                        color: 'var(--text-main)',
                        margin: 0
                    }}>
                        🔐 Admin Portal
                    </h1>
                </div>

                <nav style={{ display: 'flex', gap: '0.5rem' }}>
                    <Link
                        to="/admin/dashboard"
                        style={{
                            padding: '0.5rem 1rem',
                            borderRadius: '8px',
                            textDecoration: 'none',
                            color: isActive('/admin/dashboard') ? 'white' : 'var(--text-muted)',
                            background: isActive('/admin/dashboard') ? 'var(--primary)' : 'transparent',
                            fontWeight: 500
                        }}
                    >
                        Dashboard
                    </Link>
                    <Link
                        to="/admin/documents"
                        style={{
                            padding: '0.5rem 1rem',
                            borderRadius: '8px',
                            textDecoration: 'none',
                            color: isActive('/admin/documents') ? 'white' : 'var(--text-muted)',
                            background: isActive('/admin/documents') ? 'var(--primary)' : 'transparent',
                            fontWeight: 500
                        }}
                    >
                        Documents
                    </Link>
                    <Link
                        to="/admin/users"
                        style={{
                            padding: '0.5rem 1rem',
                            borderRadius: '8px',
                            textDecoration: 'none',
                            color: isActive('/admin/users') ? 'white' : 'var(--text-muted)',
                            background: isActive('/admin/users') ? 'var(--primary)' : 'transparent',
                            fontWeight: 500
                        }}
                    >
                        Users
                    </Link>
                </nav>
            </div>

            <button
                onClick={handleLogout}
                style={{
                    padding: '0.5rem 1rem',
                    background: 'var(--danger)',
                    color: 'white',
                    border: 'none',
                    borderRadius: '8px',
                    cursor: 'pointer',
                    fontWeight: 500,
                    fontSize: '0.9rem'
                }}
            >
                Logout
            </button>
        </div>
    );
}
