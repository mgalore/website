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
