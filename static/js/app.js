// Monthly Organics - Frontend JavaScript
document.addEventListener('DOMContentLoaded', function() {
    console.log('Monthly Organics application loaded');
    
    // Initialize Alpine.js components
    initializeAlpineComponents();
    
    // Add smooth scrolling for anchor links
    addSmoothScrolling();
    
    // Initialize logo animation
    initializeLogoAnimation();
});

function initializeAlpineComponents() {
    // Alpine.js will automatically initialize components
    // This function can be extended for custom Alpine.js initialization
    console.log('Alpine.js components initialized');
}

function addSmoothScrolling() {
    // Add smooth scrolling behavior to all anchor links
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', function (e) {
            console.log('Category link clicked!'); // The new line is added here
            e.preventDefault();
            const target = document.querySelector(this.getAttribute('href'));
            if (target) {
                target.scrollIntoView({
                    behavior: 'smooth',
                    block: 'start'
                });
            }
        });
    });
}

function initializeLogoAnimation() {
    // Add entrance animation to logo
    const logo = document.querySelector('.brand-logo');
    if (logo) {
        logo.classList.add('animate-fade-in-up');
        
        // Add hover effect
        logo.addEventListener('mouseenter', function() {
            this.style.transform = 'scale(1.05)';
        });
        
        logo.addEventListener('mouseleave', function() {
            this.style.transform = 'scale(1)';
        });
    }
}

// Utility functions for Alpine.js components
window.monthlyOrganics = {
    // Navigation utilities
    navigation: {
        isOpen: false,
        toggle() {
            this.isOpen = !this.isOpen;
        },
        close() {
            this.isOpen = false;
        }
    },
    
    // Form utilities
    forms: {
        submitForm(formData) {
            console.log('Form submitted:', formData);
            // This can be extended for form handling
        }
    },
    
    // Animation utilities
    animations: {
        fadeIn(element) {
            element.style.opacity = '0';
            element.style.transform = 'translateY(20px)';
            element.style.transition = 'all 0.6s ease-out';
            
            setTimeout(() => {
                element.style.opacity = '1';
                element.style.transform = 'translateY(0)';
            }, 100);
        }
    }
};

// Health check function
async function checkApplicationHealth() {
    try {
        const response = await fetch('/health');
        const data = await response.json();
        console.log('Application health:', data);
        return data;
    } catch (error) {
        console.error('Health check failed:', error);
        return { status: 'unhealthy', error: error.message };
    }
}

// Initialize health check on page load
checkApplicationHealth();
