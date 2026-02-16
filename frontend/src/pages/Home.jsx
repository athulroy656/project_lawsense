import { useNavigate, Link } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { useEffect, useState, useRef } from 'react';
import '../home.css';

export default function Home() {
    const { user } = useAuth();
    const navigate = useNavigate();
    const [scrolled, setScrolled] = useState(false);
    const scrollContainerRef = useRef(null);
    const fileInputRef = useRef(null);

    useEffect(() => {
        if (user) {
            navigate('/dashboard');
        }

        const handleScroll = () => {
            if (scrollContainerRef.current) {
                const isScrolled = scrollContainerRef.current.scrollTop > 50;
                if (isScrolled !== scrolled) {
                    setScrolled(isScrolled);
                }
            }
        };

        const container = scrollContainerRef.current;
        if (container) {
            container.addEventListener('scroll', handleScroll);
        }
        return () => {
            if (container) container.removeEventListener('scroll', handleScroll);
        };
    }, [user, navigate, scrolled]);

    const handleFileSelect = (e) => {
        const file = e.target.files[0];
        if (file) {
            // Navigate to guest analysis route with the file
            navigate('/analyze', { state: { fileToAnalyze: file } });
        }
    };

    return (
        <div
            ref={scrollContainerRef}
            className="home-page"
            style={{
                height: '100vh',
                overflowY: 'auto',
                overflowX: 'hidden',
                background: 'var(--bg-0)' // Match hero bg to prevent white flashes
            }}
        >

            {/* 1️⃣ Advanced Sticky Header */}
            <header className={`app-header glass-nav ${scrolled ? 'scrolled' : ''}`} style={{ position: 'sticky', top: 0, zIndex: 1000, padding: '1rem 2rem' }}>
                <div className="header-content" style={{ maxWidth: '1280px', margin: '0 auto', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <div className="header-brand" style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
                        <span className="header-logo" style={{ fontSize: '2rem' }}>⚖️</span>
                        <h1 style={{ fontSize: '1.5rem', fontWeight: '800', margin: 0, letterSpacing: '-0.02em', color: 'white' }}>LawSense AI</h1>
                    </div>

                    <nav className="desktop-nav" style={{ display: 'flex', gap: '2rem', alignItems: 'center' }}>
                        {['Home', 'About', 'How it Works', 'Features'].map((item) => (
                            <a
                                key={item}
                                href={`#${item.toLowerCase().replace(/\s+/g, '-')}`}
                                className="nav-link"
                                style={{ color: 'rgba(255,255,255,0.7)', textDecoration: 'none', fontSize: '0.95rem' }}
                            >
                                {item}
                            </a>
                        ))}
                    </nav>

                    <div className="header-actions" style={{ display: 'flex', gap: '1rem', alignItems: 'center' }}>
                        <Link to="/login" className="nav-link" style={{
                            color: 'white',
                            textDecoration: 'none',
                            padding: '0.5rem 1rem',
                            fontWeight: 500
                        }}>Login</Link>
                        <Link to="/register" className="btn-primary-glow" style={{
                            color: 'white',
                            padding: '0.6rem 1.5rem',
                            borderRadius: '8px',
                            textDecoration: 'none',
                            fontWeight: '600',
                            fontSize: '0.95rem'
                        }}>Register</Link>
                    </div>
                </div>
            </header>

            {/* 2️⃣ Dynamic Hero Section */}
            <section id="home" className="hero-bg" style={{
                padding: '6rem 2rem 8rem 2rem',
                textAlign: 'center',
                color: 'white'
            }}>
                <div className="hero-content" style={{ maxWidth: '900px', margin: '0 auto' }}>
                    <div className="fade-up">
                        <span style={{
                            background: 'rgba(99, 102, 241, 0.2)',
                            color: '#a5b4fc',
                            padding: '0.5rem 1rem',
                            borderRadius: '99px',
                            fontSize: '0.85rem',
                            fontWeight: '600',
                            letterSpacing: '0.05em',
                            textTransform: 'uppercase',
                            border: '1px solid rgba(99, 102, 241, 0.3)',
                            display: 'inline-block',
                            marginBottom: '1.5rem'
                        }}>
                            New Generation Legal Tech
                        </span>
                        <h1 className="hero-title" style={{
                            fontSize: 'clamp(2.5rem, 5vw, 4.5rem)',
                            fontWeight: 800,
                            marginBottom: '1.5rem',
                            lineHeight: 1.1,
                            letterSpacing: '-0.02em'
                        }}>
                            Legal Clarity, <br />
                            <span className="text-gradient-accent">Powered by AI Context.</span>
                        </h1>
                        <p style={{
                            fontSize: '1.25rem',
                            color: '#cbd5e1',
                            marginBottom: '3rem',
                            maxWidth: '600px',
                            margin: '0 auto 3rem auto',
                            lineHeight: 1.6
                        }} className="fade-up fade-up-delay-1">
                            Instantly analyze contracts for hidden risks, ambiguous terms, and structural gaps.
                            Decision support, reimagined.
                        </p>
                    </div>
                </div>

                {/* Action Buttons */}
                <div className="hero-content fade-up fade-up-delay-2" style={{
                    marginTop: '2rem',
                    maxWidth: '700px',
                    margin: '2rem auto 0 auto',
                    position: 'relative',
                    zIndex: 20,
                    display: 'flex',
                    justifyContent: 'center',
                    gap: '1.5rem',
                    flexWrap: 'wrap'
                }}>
                    <button
                        onClick={() => navigate('/analyze')}
                        className="btn-primary-glow"
                        style={{
                            padding: '1rem 2.5rem',
                            fontSize: '1.2rem',
                            fontWeight: 'bold',
                            borderRadius: '12px',
                            border: 'none',
                            color: 'white',
                            cursor: 'pointer',
                            background: 'linear-gradient(135deg, #4f46e5 0%, #3730a3 100%)',
                            boxShadow: '0 10px 25px -5px rgba(79, 70, 229, 0.4)',
                            transition: 'all 0.2s ease',
                            display: 'flex',
                            alignItems: 'center',
                            gap: '0.75rem'
                        }}
                    >
                        <span>Analyze Now</span>
                        <span>→</span>
                    </button>

                    <button
                        onClick={() => {
                            const howItWorks = document.getElementById('how-it-works');
                            if (howItWorks) howItWorks.scrollIntoView({ behavior: 'smooth' });
                        }}
                        style={{
                            padding: '1rem 2.5rem',
                            fontSize: '1.1rem',
                            fontWeight: '600',
                            borderRadius: '12px',
                            border: '1px solid rgba(255,255,255,0.2)',
                            background: 'rgba(255,255,255,0.05)',
                            color: 'white',
                            cursor: 'pointer',
                            backdropFilter: 'blur(10px)',
                            transition: 'all 0.2s ease'
                        }}
                    >
                        How it works
                    </button>
                </div>
            </section>

            {/* 3️⃣ About / Mission Section */}
            <section id="about" style={{ padding: '8rem 2rem', background: 'var(--bg-0)' }}>
                <div style={{ maxWidth: '1000px', margin: '0 auto', textAlign: 'center' }}>
                    <h2 style={{ fontSize: '2.5rem', color: 'var(--text-main)', marginBottom: '1.5rem', fontWeight: 800 }}>Understanding Documents, <br /> Not Replacing Lawyers</h2>
                    <p style={{ fontSize: '1.2rem', color: 'var(--text-muted)', lineHeight: 1.8, marginBottom: '3rem', maxWidth: '800px', margin: '0 auto 3rem auto' }}>
                        Traditional keyword search isn't enough. LawSense AI uses advanced Large Language Models (LLMs) to understand the
                        <em> semantic context</em> of your legal agreements. It highlights risks, clarifies ambiguities, and identifies structural gaps
                        that strict rule-based systems miss.
                    </p>
                    <div style={{
                        background: 'var(--bg-1)',
                        borderLeft: '4px solid #6366f1',
                        padding: '2rem',
                        borderRadius: '12px',
                        display: 'inline-block',
                        textAlign: 'left',
                        boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.05)'
                    }}>
                        <div style={{ display: 'flex', gap: '1rem', alignItems: 'start' }}>
                            <span style={{ fontSize: '1.5rem' }}>⚖️</span>
                            <div>
                                <h4 style={{ margin: '0 0 0.5rem 0', color: 'var(--text-main)' }}>Legal Disclaimer</h4>
                                <p style={{ margin: 0, color: 'var(--text-muted)', fontSize: '0.95rem', lineHeight: 1.5 }}>
                                    This system provides decision-support insights and does <strong>not</strong> offer legal advice.
                                    Always consult with a qualified attorney for professional legal counsel.
                                </p>
                            </div>
                        </div>
                    </div>
                </div>
            </section>

            {/* 4️⃣ How It Works Section */}
            <section id="how-it-works" style={{ padding: '8rem 2rem', background: 'var(--bg-1)' }}>
                <div style={{ maxWidth: '1200px', margin: '0 auto' }}>
                    <div style={{ textAlign: 'center', marginBottom: '4rem' }}>
                        <span style={{ color: 'var(--primary)', fontWeight: 'bold', textTransform: 'uppercase', letterSpacing: '0.05em', fontSize: '0.9rem' }}>Workflow</span>
                        <h2 style={{ fontSize: '2.5rem', color: 'var(--text-main)', marginTop: '0.5rem', fontWeight: 800 }}>From Chaos to Clarity</h2>
                    </div>

                    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '2rem' }}>
                        {[
                            { icon: '📤', title: 'Upload', desc: 'Securely upload PDFs or DOCX files. Your data is processed in-memory for privacy.' },
                            { icon: '🤖', title: 'Analyze', desc: 'Our AI engine scans for over 50 types of risk indicators and structural patterns.' },
                            { icon: '📊', title: 'Review', desc: 'Explore the interactive dashboard with prioritized risk scores and plain-English summaries.' },
                            { icon: '✅', title: 'Decide', desc: 'Make informed decisions faster with context-aware insights at your fingertips.' }
                        ].map((item, idx) => (
                            <div key={idx} className="feature-card" style={{ textAlign: 'center', padding: '2.5rem 2rem' }}>
                                <div style={{ fontSize: '3rem', marginBottom: '1.5rem', background: 'var(--bg-2)', width: '80px', height: '80px', lineHeight: '80px', borderRadius: '50%', margin: '0 auto 1.5rem auto' }}>{item.icon}</div>
                                <h3 style={{ fontSize: '1.25rem', color: 'var(--text-main)', marginBottom: '0.75rem', fontWeight: 700 }}>{item.title}</h3>
                                <p style={{ color: 'var(--text-muted)', lineHeight: 1.6 }}>{item.desc}</p>
                            </div>
                        ))}
                    </div>
                </div>
            </section>

            {/* 5️⃣ Features Grid */}
            <section id="features" style={{ padding: '8rem 2rem', background: 'var(--bg-0)' }}>
                <div style={{ maxWidth: '1200px', margin: '0 auto' }}>
                    <div style={{ textAlign: 'center', marginBottom: '5rem' }}>
                        <span style={{ color: 'var(--primary)', fontWeight: 'bold', textTransform: 'uppercase', letterSpacing: '0.05em', fontSize: '0.9rem' }}>Capabilities</span>
                        <h2 style={{ fontSize: '2.5rem', color: 'var(--text-main)', marginTop: '0.5rem', fontWeight: 800 }}>Intelligent Analysis Features</h2>
                    </div>

                    <div style={{
                        display: 'grid',
                        gridTemplateColumns: 'repeat(auto-fit, minmax(340px, 1fr))',
                        gap: '2rem'
                    }}>
                        {[
                            { title: '📝 Clause Extraction', desc: 'Automatically identifies and categorizes clauses like Indemnification, Termination, and Liability.' },
                            { title: '⚠️ Risk Scoring', desc: 'Calculates a composite safety score based on missing clauses, one-sided terms, and ambiguous language.' },
                            { title: '🔍 Ambiguity Detection', desc: 'Flags vague terms like "promptly" or "reasonable efforts" that leads to downstream disputes.' },
                            { title: '💬 Q&A Interface', desc: 'Ask questions about your document ("Can I terminate early?") and get answers with citations.' },
                            { title: '🏗️ Structural Gaps', desc: 'Identifies missing standard clauses expected for the specific document type (e.g., Missing NDA Exclusions).' },
                            { title: '🔒 Privacy First', desc: 'Documents are processed securely. We don\'t train our Models on your private contracts.' }
                        ].map((feature, idx) => (
                            <div key={idx} className="feature-card" style={{ display: 'flex', gap: '1.5rem', alignItems: 'start' }}>
                                <div style={{
                                    minWidth: '24px',
                                    height: '24px',
                                    background: '#4f46e5',
                                    borderRadius: '50%',
                                    color: 'white',
                                    display: 'flex',
                                    alignItems: 'center',
                                    justifyContent: 'center',
                                    fontSize: '0.9rem',
                                    marginTop: '0.2rem'
                                }}>✓</div>
                                <div>
                                    <h3 style={{ fontSize: '1.1rem', fontWeight: 700, color: 'var(--text-main)', marginBottom: '0.5rem' }}>{feature.title}</h3>
                                    <p style={{ color: 'var(--text-muted)', fontSize: '0.95rem', lineHeight: 1.5, margin: 0 }}>{feature.desc}</p>
                                </div>
                            </div>
                        ))}
                    </div>
                </div>
            </section>

            {/* 6️⃣ CTA Section */}
            <section style={{
                padding: '8rem 2rem',
                background: 'linear-gradient(135deg, #1e293b 0%, #312e81 100%)',
                color: 'white',
                textAlign: 'center',
                position: 'relative',
                overflow: 'hidden'
            }}>
                <div style={{ position: 'absolute', top: 0, left: 0, width: '100%', height: '100%', background: 'url("data:image/svg+xml,%3Csvg width=\'60\' height=\'60\' viewBox=\'0 0 60 60\' xmlns=\'http://www.w3.org/2000/svg\'%3E%3Cg fill=\'none\' fill-rule=\'evenodd\'%3E%3Cg fill=\'%23ffffff\' fill-opacity=\'0.05\'%3E%3Cpath d=\'M36 34v-4h-2v4h-4v2h4v4h2v-4h4v-2h-4zm0-30V0h-2v4h-4v2h4v4h2V6h4V4h-4zM6 34v-4H4v4H0v2h4v4h2v-4h4v-2H6zM6 4V0H4v4H0v2h4v4h2V6h4V4H6z\'/%3E%3C/g%3E%3C/g%3E%3C/svg%3E")', opacity: 0.1 }}></div>
                <div style={{ maxWidth: '800px', margin: '0 auto', position: 'relative', zIndex: 10 }}>
                    <h2 style={{ fontSize: '3rem', fontWeight: 800, marginBottom: '1.5rem', lineHeight: 1.1 }}>Ready to Analyze?</h2>
                    <p style={{ fontSize: '1.25rem', color: '#a5b4fc', marginBottom: '3rem' }}>Join now to bring clarity and confidence to your legal review process.</p>
                    <Link to="/register" className="btn-primary-glow" style={{
                        display: 'inline-block',
                        color: 'white',
                        padding: '1.25rem 3.5rem',
                        borderRadius: '12px',
                        fontSize: '1.2rem',
                        fontWeight: 'bold',
                        textDecoration: 'none'
                    }}>Create Free Account</Link>
                    <p style={{ marginTop: '1.5rem', fontSize: '0.9rem', color: '#64748b' }}>No credit card required for standard tier.</p>
                </div>
            </section>

            {/* 7️⃣ Footer */}
            <footer style={{ background: '#0f172a', color: '#94a3b8', padding: '5rem 2rem 2rem 2rem', borderTop: '1px solid #1e293b' }}>
                <div style={{ maxWidth: '1200px', margin: '0 auto', display: 'flex', justifyContent: 'space-between', flexWrap: 'wrap', gap: '3rem' }}>
                    <div style={{ flex: 1, minWidth: '250px' }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '1.5rem' }}>
                            <span style={{ fontSize: '1.5rem' }}>⚖️</span>
                            <h4 style={{ color: 'white', fontSize: '1.25rem', fontWeight: 700, margin: 0 }}>LawSense AI</h4>
                        </div>
                        <p style={{ fontSize: '0.95rem', lineHeight: 1.6, maxWidth: '300px' }}>
                            Providing context-aware AI insights for complex legal documents.
                            Empowering non-lawyers to understand their agreements.
                        </p>
                    </div>

                    <div style={{ display: 'flex', gap: '4rem', flexWrap: 'wrap' }}>
                        <div>
                            <h4 style={{ color: 'white', fontSize: '1rem', marginBottom: '1.5rem', fontWeight: 600 }}>Product</h4>
                            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.8rem' }}>
                                <a href="#" style={{ color: '#94a3b8', textDecoration: 'none', transition: 'color 0.2s', fontSize: '0.95rem' }}>Features</a>
                                <a href="#" style={{ color: '#94a3b8', textDecoration: 'none', transition: 'color 0.2s', fontSize: '0.95rem' }}>Pricing</a>
                                <a href="#" style={{ color: '#94a3b8', textDecoration: 'none', transition: 'color 0.2s', fontSize: '0.95rem' }}>Security</a>
                            </div>
                        </div>
                        <div>
                            <h4 style={{ color: 'white', fontSize: '1rem', marginBottom: '1.5rem', fontWeight: 600 }}>Company</h4>
                            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.8rem' }}>
                                <a href="#" style={{ color: '#94a3b8', textDecoration: 'none', transition: 'color 0.2s', fontSize: '0.95rem' }}>About Us</a>
                                <a href="#" style={{ color: '#94a3b8', textDecoration: 'none', transition: 'color 0.2s', fontSize: '0.95rem' }}>Contact</a>
                                <a href="#" style={{ color: '#94a3b8', textDecoration: 'none', transition: 'color 0.2s', fontSize: '0.95rem' }}>Privacy</a>
                            </div>
                        </div>
                    </div>
                </div>
                <div style={{ maxWidth: '1200px', margin: '4rem auto 0 auto', borderTop: '1px solid #1e293b', paddingTop: '2rem' }}>
                    <div style={{ textAlign: 'center', marginBottom: '1.5rem' }}>
                        <Link
                            to="/admin/login"
                            style={{
                                color: '#a78bfa',
                                textDecoration: 'none',
                                fontSize: '0.85rem',
                                display: 'inline-flex',
                                alignItems: 'center',
                                gap: '0.5rem',
                                padding: '0.5rem 1rem',
                                border: '1px solid rgba(167, 139, 250, 0.3)',
                                borderRadius: '8px',
                                transition: 'all 0.2s'
                            }}
                            onMouseEnter={(e) => {
                                e.target.style.background = 'rgba(167, 139, 250, 0.1)';
                                e.target.style.borderColor = '#a78bfa';
                            }}
                            onMouseLeave={(e) => {
                                e.target.style.background = 'transparent';
                                e.target.style.borderColor = 'rgba(167, 139, 250, 0.3)';
                            }}
                        >
                            🔐 Admin Portal
                        </Link>
                    </div>
                    <div style={{ textAlign: 'center', fontSize: '0.85rem' }}>
                        &copy; {new Date().getFullYear()} LawSense AI. Educational AI System for Legal Document Analysis.
                    </div>
                </div>
            </footer>
        </div>
    );
}
