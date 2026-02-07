// Premium JavaScript for IELTS Center

// Navbar scroll effect
let lastScroll = 0;

window.addEventListener('scroll', function() {
    const navbar = document.querySelector('.navbar');
    if (!navbar) return;
    
    const currentScroll = window.pageYOffset;
    
    if (currentScroll > 50) {
        navbar.classList.add('scrolled');
    } else {
        navbar.classList.remove('scrolled');
    }
    
    lastScroll = currentScroll;
});

// Navbar collapse toggle
function initNavbarCollapse() {
    const navbarToggler = document.querySelector('.navbar-toggler');
    const navbarCollapse = document.querySelector('.navbar-collapse');
    
    if (navbarToggler && navbarCollapse) {
        navbarToggler.addEventListener('click', function() {
            navbarCollapse.classList.toggle('show');
        });
        
        // Close navbar when clicking outside
        document.addEventListener('click', function(event) {
            if (!navbarToggler.contains(event.target) && !navbarCollapse.contains(event.target)) {
                navbarCollapse.classList.remove('show');
            }
        });
    }
}

// Intersection Observer for animations
const observerOptions = {
    threshold: 0.1,
    rootMargin: '0px 0px -50px 0px'
};

const observer = new IntersectionObserver(function(entries) {
    entries.forEach(entry => {
        if (entry.isIntersecting) {
            entry.target.style.opacity = '1';
            entry.target.style.transform = 'translateY(0)';
        }
    });
}, observerOptions);

// Observe all stagger items
document.addEventListener('DOMContentLoaded', function() {
    const staggerItems = document.querySelectorAll('.stagger-item');
    staggerItems.forEach(item => {
        item.style.opacity = '0';
        item.style.transform = 'translateY(30px)';
        item.style.transition = 'all 0.8s cubic-bezier(0.4, 0, 0.2, 1)';
        observer.observe(item);
    });
});

// Initialize on page load
document.addEventListener('DOMContentLoaded', function() {
    initNavbarCollapse();
    
    // Body loaded class qo'shish (FOUC oldini olish)
    if (document.body) {
        document.body.classList.add('loaded');
        
        // Add smooth fade-in to page
        document.body.style.opacity = '0';
        setTimeout(() => {
            if (document.body) {
                document.body.style.transition = 'opacity 0.5s ease';
                document.body.style.opacity = '1';
            }
        }, 100);
    }
});

// Global error handler - filter out browser extension errors
window.addEventListener('error', function(event) {
    const errorSource = event.filename || event.source || '';
    const errorMessage = event.message || '';
    
    // Filter out browser extension errors
    if (errorSource.includes('content-youtube-embed.js') ||
        errorSource.includes('extension://') ||
        errorMessage.includes('browser extension') ||
        errorMessage.includes('content-youtube-embed')) {
        event.preventDefault();
        return false;
    }
});

// Unhandled promise rejection handler
window.addEventListener('unhandledrejection', function(event) {
    const errorMessage = event.reason?.message || event.reason || '';
    
    // Filter out browser extension errors
    if (errorMessage.includes('browser extension') ||
        errorMessage.includes('content-youtube-embed')) {
        event.preventDefault();
        return false;
    }
});

// Ripple effect for buttons
document.addEventListener('click', function(e) {
    if (!e.target || !e.target.classList) return;
    
    if (e.target.classList.contains('btn') || e.target.closest('.btn')) {
        const button = e.target.classList.contains('btn') ? e.target : e.target.closest('.btn');
        if (!button) return;
        
        const ripple = document.createElement('span');
        const rect = button.getBoundingClientRect();
        const size = Math.max(rect.width, rect.height);
        const x = e.clientX - rect.left - size / 2;
        const y = e.clientY - rect.top - size / 2;
        
        ripple.style.width = ripple.style.height = size + 'px';
        ripple.style.left = x + 'px';
        ripple.style.top = y + 'px';
        ripple.classList.add('ripple');
        
        button.style.position = 'relative';
        button.style.overflow = 'hidden';
        button.appendChild(ripple);
        
        setTimeout(() => {
            if (ripple && ripple.parentNode) {
                ripple.remove();
            }
        }, 600);
    }
});

// Add ripple CSS dynamically
document.addEventListener('DOMContentLoaded', function() {
    if (!document.head) return;
    
    // Check if style already exists
    if (document.getElementById('ripple-style')) return;
    
    const style = document.createElement('style');
    style.id = 'ripple-style';
    style.textContent = `
        .ripple {
            position: absolute;
            border-radius: 50%;
            background: rgba(255, 255, 255, 0.6);
            transform: scale(0);
            animation: ripple-animation 0.6s ease-out;
            pointer-events: none;
        }
        
        @keyframes ripple-animation {
            to {
                transform: scale(4);
                opacity: 0;
            }
        }
    `;
    document.head.appendChild(style);
});

// Smooth scroll to top
function scrollToTop() {
    window.scrollTo({
        top: 0,
        behavior: 'smooth'
    });
}

// Add scroll to top button (only if body exists)
document.addEventListener('DOMContentLoaded', function() {
    if (!document.body) return;
    
    const scrollTopBtn = document.createElement('button');
    scrollTopBtn.innerHTML = '<i class="fas fa-arrow-up"></i>';
    scrollTopBtn.className = 'scroll-to-top';
    scrollTopBtn.style.cssText = `
        position: fixed;
        bottom: 2rem;
        right: 2rem;
        width: 50px;
        height: 50px;
        border-radius: 50%;
        background: linear-gradient(135deg, var(--primary) 0%, var(--purple) 100%);
        color: white;
        border: none;
        box-shadow: 0 8px 24px rgba(99, 102, 241, 0.4);
        cursor: pointer;
        z-index: 999;
        opacity: 0;
        transform: translateY(20px);
        transition: all 0.3s ease;
        font-size: 1.25rem;
    `;

    scrollTopBtn.addEventListener('click', scrollToTop);
    document.body.appendChild(scrollTopBtn);

    window.addEventListener('scroll', function() {
        if (window.pageYOffset > 300) {
            scrollTopBtn.style.opacity = '1';
            scrollTopBtn.style.transform = 'translateY(0)';
        } else {
            scrollTopBtn.style.opacity = '0';
            scrollTopBtn.style.transform = 'translateY(20px)';
        }
    });

    // Add hover effect to scroll button
    scrollTopBtn.addEventListener('mouseenter', function() {
        this.style.transform = 'translateY(-4px) scale(1.1)';
        this.style.boxShadow = '0 12px 32px rgba(99, 102, 241, 0.6)';
    });

    scrollTopBtn.addEventListener('mouseleave', function() {
        if (window.pageYOffset > 300) {
            this.style.transform = 'translateY(0) scale(1)';
        } else {
            this.style.transform = 'translateY(20px) scale(1)';
        }
        this.style.boxShadow = '0 8px 24px rgba(99, 102, 241, 0.4)';
    });
});
