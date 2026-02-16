import { useState } from 'react';
import { register } from '../api';
import { Link, useNavigate } from 'react-router-dom';
import '../App.css';

export default function Register() {
    const [username, setUsername] = useState('');
    const [email, setEmail] = useState('');
    const [password, setPassword] = useState('');
    const [confirmPassword, setConfirmPassword] = useState('');
    const [error, setError] = useState('');
    const navigate = useNavigate();

    const handleSubmit = async (e) => {
        e.preventDefault();
        setError('');
        if (password !== confirmPassword) {
            return setError('Passwords do not match');
        }
        try {
            await register(username, email, password, confirmPassword);
            navigate('/login');
        } catch (err) {
            setError(err.message || 'Failed to register');
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
                    <h2 style={{ marginTop: '1rem', color: '#60a5fa' }}>Create Account</h2>
                    <p style={{ color: '#94a3b8' }}>Join LawSense AI today</p>
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
                    <div style={{ marginBottom: '1rem' }}>
                        <label style={{ display: 'block', marginBottom: '0.5rem', color: '#e2e8f0' }}>Email</label>
                        <input
                            type="email"
                            value={email}
                            onChange={(e) => setEmail(e.target.value)}
                            required
                            style={{
                                width: '100%', padding: '0.75rem', borderRadius: '8px', border: '1px solid #334155',
                                background: '#1e293b', color: 'white'
                            }}
                        />
                    </div>
                    <div style={{ marginBottom: '1rem' }}>
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
                    <div style={{ marginBottom: '2rem' }}>
                        <label style={{ display: 'block', marginBottom: '0.5rem', color: '#e2e8f0' }}>Confirm Password</label>
                        <input
                            type="password"
                            value={confirmPassword}
                            onChange={(e) => setConfirmPassword(e.target.value)}
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
                        Register
                    </button>
                </form>
                <div style={{ marginTop: '1.5rem', textAlign: 'center', color: '#94a3b8' }}>
                    Already have an account? <Link to="/login" style={{ color: '#60a5fa' }}>Sign In</Link>
                </div>
                <div style={{ marginTop: '1rem', textAlign: 'center' }}>
                    <Link to="/" style={{ color: '#94a3b8', textDecoration: 'none', fontSize: '0.9rem' }}>← Back to Home</Link>
                </div>
            </div>
        </div>
    );
}
