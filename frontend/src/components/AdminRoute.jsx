import { Navigate } from "react-router-dom";
import { useState, useEffect } from "react";
import { checkAdminStatus } from "../adminApi";

export default function AdminRoute({ children }) {
    const [isAdmin, setIsAdmin] = useState(null);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        verifyAdmin();
    }, []);

    const verifyAdmin = async () => {
        const token = localStorage.getItem("access_token");

        if (!token) {
            setIsAdmin(false);
            setLoading(false);
            return;
        }

        try {
            const status = await checkAdminStatus();
            setIsAdmin(status.is_admin);
        } catch (error) {
            setIsAdmin(false);
        } finally {
            setLoading(false);
        }
    };

    if (loading) {
        return (
            <div style={{
                minHeight: '100vh',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                background: '#f8fafc'
            }}>
                <div style={{ textAlign: 'center' }}>
                    <div className="spinner" style={{ margin: '0 auto 1rem' }}></div>
                    <p style={{ color: '#64748b' }}>Verifying admin access...</p>
                </div>
            </div>
        );
    }

    if (!isAdmin) {
        return <Navigate to="/admin/login" replace />;
    }

    return children;
}
