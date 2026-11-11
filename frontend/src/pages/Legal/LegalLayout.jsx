import React, { useEffect } from 'react';
import { Link, useLocation } from 'react-router-dom';
import { ArrowLeft } from 'lucide-react';
import Footer from '../../components/Footer/Footer';
import styles from './LegalLayout.module.css';

export default function LegalLayout({ title, subtitle, lastUpdated, children }) {
  const location = useLocation();

  useEffect(() => {
    window.scrollTo(0, 0);
  }, [location.pathname]);

  return (
    <div className={styles.page}>
      {/* Top Navbar */}
      <header className={styles.navbar}>
        <div className={styles.navContainer}>
          <Link to="/" className={styles.navBrand} aria-label="YtGenius Home">
            <div className={styles.brandBadge}>▶</div>
            <span className={styles.brandText}>
              <span className={styles.brandYt}>Yt</span>
              <span className={styles.brandGenius}>Genius</span>
            </span>
          </Link>

          <nav className={styles.navLinks}>
            <Link to="/" className={styles.navLink}>Home</Link>
            <Link to="/docs" className={styles.navLink}>Docs</Link>
            <Link to="/contact" className={styles.navLink}>Contact</Link>
            <Link to="/login" className={styles.navCta}>Get Started</Link>
          </nav>
        </div>
      </header>

      {/* Main Content Area */}
      <main className={styles.main}>
        <div className={styles.container}>
          <div className={styles.header}>
            <Link to="/" className={styles.backLink}>
              <ArrowLeft size={14} /> Back to Home
            </Link>
            <h1 className={styles.title}>{title}</h1>
            {subtitle && <p className={styles.subtitle}>{subtitle}</p>}
            {lastUpdated && (
              <div className={styles.metaRow}>
                <span>Effective &amp; Last Updated: {lastUpdated}</span>
              </div>
            )}
          </div>

          <article className={styles.content}>
            {children}
          </article>
        </div>
      </main>

      {/* Shared Professional Footer */}
      <Footer />
    </div>
  );
}
