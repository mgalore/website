// Smooth scrolling for navigation links
document.querySelectorAll('a[href^="#"]').forEach(anchor => {
    anchor.addEventListener('click', function (e) {
        e.preventDefault();
        
        const targetId = this.getAttribute('href');
        const targetElement = document.querySelector(targetId);
        
        window.scrollTo({
            top: targetElement.offsetTop - 70, // Account for header height
            behavior: 'smooth'
        });
    });
});

// Hide navbar on scroll for mobile
let lastScrollTop = 0;
const header = document.querySelector('header');
const SCROLL_THRESHOLD = 10; // Minimum scroll amount before hiding/showing
const MOBILE_WIDTH = 768; // Match your media query breakpoint

window.addEventListener('scroll', function() {
    // Only apply this on mobile
    if (window.innerWidth <= MOBILE_WIDTH) {
        const currentScroll = window.pageYOffset || document.documentElement.scrollTop;
        
        // Check if we've scrolled enough to trigger the effect
        if (Math.abs(lastScrollTop - currentScroll) <= SCROLL_THRESHOLD) 
            return;
            
        // Hide header when scrolling down, show when scrolling up
        if (currentScroll > lastScrollTop && currentScroll > 100) {
            // Scrolling down & past the threshold
            header.classList.add('nav-hidden');
        } else {
            // Scrolling up or at the top
            header.classList.remove('nav-hidden');
        }
        
        lastScrollTop = currentScroll <= 0 ? 0 : currentScroll; // For Mobile or negative scrolling
    }
}, { passive: true }); // Improves scroll performance

// Reset header visibility when screen size changes
window.addEventListener('resize', function() {
    if (window.innerWidth > MOBILE_WIDTH) {
        header.classList.remove('nav-hidden');
    }
});

// Simple form submission handling
const contactForm = document.querySelector('.contact-form');
if (contactForm) {
    contactForm.addEventListener('submit', function(e) {
        e.preventDefault();
        
        // In a real implementation, you would send the form data to a server
        // For now, we'll just show a confirmation message
        const formElements = Array.from(this.elements);
        let isValid = true;
        
        formElements.forEach(element => {
            if (element.hasAttribute('required') && !element.value) {
                isValid = false;
                element.classList.add('error');
            } else {
                element.classList.remove('error');
            }
        });
        
        if (isValid) {
            alert('Thank you for your message! We will get back to you soon.');
            this.reset();
        } else {
            alert('Please fill in all required fields.');
        }
    });
}

// Add active class to navigation items based on scroll position
window.addEventListener('scroll', function() {
    const sections = document.querySelectorAll('section');
    const navLinks = document.querySelectorAll('nav ul li a');
    
    let current = '';
    
    sections.forEach(section => {
        const sectionTop = section.offsetTop;
        const sectionHeight = section.clientHeight;
        
        if (pageYOffset >= sectionTop - 100) {
            current = section.getAttribute('id');
        }
    });
    
    navLinks.forEach(link => {
        link.classList.remove('active');
        if (link.getAttribute('href') === `#${current}`) {
            link.classList.add('active');
        }
    });
});

// Add active class on page load
document.addEventListener('DOMContentLoaded', function() {
    // Set the home link as active by default
    const homeLink = document.querySelector('nav ul li a[href="#home"]');
    if (homeLink) {
        homeLink.classList.add('active');
    }
    
    // Slight parallax effect on home section
    const homeSection = document.querySelector('#home');
    if (homeSection) {
        window.addEventListener('scroll', function() {
            const scrollPosition = window.pageYOffset;
            homeSection.style.backgroundPositionY = scrollPosition * 0.5 + 'px';
        });
    }
});
