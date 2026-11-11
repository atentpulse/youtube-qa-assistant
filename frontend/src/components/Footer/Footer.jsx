import React from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import { Github, Linkedin } from 'lucide-react';
import styles from './Footer.module.css';

export default function Footer() {
  const location = useLocation();
  const navigate = useNavigate();

  const handleSectionLink = (e, sectionId) => {
    e.preventDefault();
    if (location.pathname === '/') {
      const el = document.getElementById(sectionId);
      if (el) {
        el.scrollIntoView({ behavior: 'smooth' });
      }
    } else {
      navigate(`/#${sectionId}`);
    }
  };

  return (
    <footer className={styles.footer}>
      <div className={styles.footerContainer}>
        <div className={styles.footerGrid}>
          {/* Brand section */}
          <div className={styles.footerBrandCol}>
            <Link to="/" className={styles.footerBrand} aria-label="YtGenius Home">
              <div className={styles.brandLogoIconSmall}>▶</div>
              <span className={styles.footerBrandName}>
                <span className={styles.brandYt}>Yt</span>
                <span className={styles.brandGenius}>Genius</span>
              </span>
            </Link>
            <p className={styles.footerTagline}>
              Ask questions. Explore videos. Discover insights.
            </p>
            <p className={styles.footerSupportingText}>
              Free video research and learning.
            </p>
            <div className={styles.footerSocial}>
              <a
                href="https://github.com/rajashik-web/youtube-qa-assistant"
                target="_blank"
                rel="noopener noreferrer"
                className={styles.socialLink}
                aria-label="YtGenius on GitHub"
                data-testid="footer-github-link"
                title="Source Code on GitHub"
              >
                <Github size={16} />
              </a>
              <a
                href="https://www.linkedin.com/in/ashik-raj-000598396"
                target="_blank"
                rel="noopener noreferrer"
                className={styles.socialLink}
                aria-label="Ashik Raj on LinkedIn"
                data-testid="footer-linkedin-link"
                title="LinkedIn Profile"
              >
                <Linkedin size={16} />
              </a>
            </div>
          </div>

          {/* Product */}
          <div className={styles.footerCol}>
            <h3 className={styles.footerColTitle}>Product</h3>
            <a
              href="/#features"
              className={styles.footerLink}
              onClick={(e) => handleSectionLink(e, 'features')}
              data-testid="footer-features-link"
            >
              Features
            </a>
            <a
              href="/#how-it-works"
              className={styles.footerLink}
              onClick={(e) => handleSectionLink(e, 'how-it-works')}
              data-testid="footer-how-it-works-link"
            >
              How It Works
            </a>
            <Link
              to="/login"
              className={styles.footerLink}
              data-testid="footer-get-started-btn"
            >
              Get Started
            </Link>
          </div>

          {/* Resources */}
          <div className={styles.footerCol}>
            <h3 className={styles.footerColTitle}>Resources</h3>
            <Link
              to="/docs"
              className={styles.footerLink}
              data-testid="footer-docs-link"
            >
              Documentation
            </Link>
            <a
              href="https://github.com/rajashik-web/youtube-qa-assistant"
              target="_blank"
              rel="noopener noreferrer"
              className={styles.footerLink}
              data-testid="footer-repo-link"
            >
              GitHub Repository
            </a>
            <Link
              to="/contact"
              className={styles.footerLink}
              data-testid="footer-contact-link"
            >
              Contact
            </Link>
          </div>

          {/* Legal & Notice */}
          <div className={styles.footerCol}>
            <h3 className={styles.footerColTitle}>Legal &amp; Notice</h3>
            <Link
              to="/privacy"
              className={styles.footerLink}
              data-testid="footer-privacy-btn"
            >
              Privacy Policy
            </Link>
            <Link
              to="/terms"
              className={styles.footerLink}
              data-testid="footer-terms-btn"
            >
              Terms of Use
            </Link>
            <Link
              to="/disclaimer"
              className={styles.footerLink}
              data-testid="footer-disclaimer-btn"
            >
              Disclaimer
            </Link>
          </div>
        </div>

        {/* Bottom footer */}
        <div className={styles.footerBottom}>
          <p className={styles.footerMeta}>© 2026 YtGenius. Built for everyone.</p>
          <p className={styles.footerMeta}>Free to use • AI-powered video research</p>
        </div>
      </div>
    </footer>
  );
}
