import { useState } from 'react';
import { login } from '../api';
import { useAuth } from '../contexts/AuthContext';
import { Link, useNavigate } from 'react-router-dom';
import '../App.css';

export default function Login() {
    const [username, setUsername] = useState('');
    const [password, setPassword] = useState('');
    const [error, setError] = useState('');
    const { loginUser } = useAuth();
    const navigate = useNavigate();

    const handleSubmit = async (e) => {
        e.preventDefault();
        try {
            const data = await login(username, password);
            loginUser(data);
            navigate('/');
        } catch (err) {
            setError('Invalid credentials. Please try again.');
        }
    };

    return (
        <div className="auth-container" style={{
            display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100vh',
            background: 'linear-gradient(135deg, #1e293b 0%, #0f172a 100%)', color: 'white'
        }}>
            <div className="auth-card" style={{
                background: 'rgba(255, 255, 255, 0.05)',
                backdropFilter: 'blur(10px)',
                padding: '2rem',
                borderRadius: '16px',
                border: '1px solid rgba(255, 255, 255, 0.1)',
                width: '100%',
                maxWidth: '400px',
                boxShadow: '0 4px 6px rgba(0, 0, 0, 0.1)'
            }}>
                <div style={{ textAlign: 'center', marginBottom: '2rem' }}>
                    <span style={{ fontSize: '3rem' }}>⚖️</span>
                    <h2 style={{ marginTop: '1rem', color: '#60a5fa' }}>Welcome Back</h2>
                    <p style={{ color: '#94a3b8' }}>Sign in to continue to LawSense AI</p>
                </div>

                {error && <div style={{ background: 'rgba(239, 68, 68, 0.2)', color: '#fca5a5', padding: '0.75rem', borderRadius: '8px', marginBottom: '1rem', textAlign: 'center' }}>{error}</div>}

                <form onSubmit={handleSubmit}>
                    <div style={{ marginBottom: '1rem' }}>
                        <label style={{ display: 'block', marginBottom: '0.5rem', color: '#e2e8f0' }}>Username</label>
                        <input
                            type="text"
                            value={username}
                            onChange={(e) => setUsername(e.target.value)}
                            required
                            style={{
                                width: '100%', padding: '0.75rem', borderRadius: '8px', border: '1px solid #334155',
                                background: '#1e293b', color: 'white'
                            }}
                        />
                    </div>
                    <div style={{ marginBottom: '2rem' }}>
                        <label style={{ display: 'block', marginBottom: '0.5rem', color: '#e2e8f0' }}>Password</label>
                        <input
                            type="password"
                            value={password}
                            onChange={(e) => setPassword(e.target.value)}
                            required
                            style={{
                                width: '100%', padding: '0.75rem', borderRadius: '8px', border: '1px solid #334155',
                                background: '#1e293b', color: 'white'
                            }}
                        />
                    </div>
                    <button type="submit" style={{
                        width: '100%', padding: '0.75rem', borderRadius: '8px', border: 'none',
                        background: 'linear-gradient(to right, #3b82f6, #2563eb)', color: 'white', fontWeight: 'bold',
                        cursor: 'pointer', transition: 'transform 0.1s'
                    }}>
                        Sign In
                    </button>
                </form>
                <div style={{ marginTop: '1.5rem', textAlign: 'center', color: '#94a3b8' }}>
                    Don't have an account? <Link to="/register" style={{ color: '#60a5fa' }}>Register</Link>
                </div>
                <div style={{ marginTop: '1rem', textAlign: 'center' }}>
                    <Link to="/" style={{ color: '#94a3b8', textDecoration: 'none', fontSize: '0.9rem' }}>← Back to Home</Link>
                </div>
                <div style={{
                    marginTop: '1.5rem',
                    paddingTop: '1.5rem',
                    borderTop: '1px solid rgba(255, 255, 255, 0.1)',
                    textAlign: 'center'
                }}>
                    <Link
                        to="/admin/login"
                        style={{
                            color: '#a78bfa',
                            textDecoration: 'none',
                            fontSize: '0.85rem',
                            display: 'flex',
                            alignItems: 'center',
                            justifyContent: 'center',
                            gap: '0.5rem'
                        }}
                    >
                        🔐 Admin Login
                    </Link>
                </div>
            </div>
        </div>
    );
}
