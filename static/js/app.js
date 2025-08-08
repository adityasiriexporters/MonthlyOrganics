// Monthly Organics - Frontend JavaScript
document.addEventListener('DOMContentLoaded', function() {
    console.log('Monthly Organics application loaded');
    
    // Initialize Alpine.js components (lightweight)
    initializeAlpineComponents();
    
    // Add smooth scrolling for anchor links (only when needed)
    if (document.querySelector('a[href^="#"]')) {
        addSmoothScrolling();
    }
    
    // Initialize logo animation (placeholder for backward compatibility)
    initializeLogoAnimation();
});

function initializeAlpineComponents() {
    // Alpine.js will automatically initialize components
    // This function can be extended for custom Alpine.js initialization
    console.log('Alpine.js components initialized');
}

function addSmoothScrolling() {
    // Add smooth scrolling behavior to all anchor links (excluding store page category items)
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        // Skip if this is on the store page and is a category item
        if (window.location.pathname === '/store' && anchor.closest('.category-item')) {
            return;
        }
        
        anchor.addEventListener('click', function (e) {
            console.log('Smooth scroll link clicked!');
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
    // Logo animation functionality removed as it was unused
    // This function kept for backward compatibility
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

// Health check function (optimized - only run when needed)
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

// Removed automatic health check on page load for better performance
// Health check can be called manually when needed: checkApplicationHealth();
