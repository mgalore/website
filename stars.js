// Stars background animation with motion
document.addEventListener('DOMContentLoaded', function() {
    const starsContainer = document.createElement('div');
    starsContainer.classList.add('stars-container');
    document.body.appendChild(starsContainer);
    
    const starCount = 100; // Number of stars
    
    // Create stars
    for (let i = 0; i < starCount; i++) {
        createStar(starsContainer);
    }
    
    // Animate stars
    animateStars();
    
    // Handle window resize
    window.addEventListener('resize', function() {
        // Clear existing stars
        starsContainer.innerHTML = '';
        
        // Create new stars
        for (let i = 0; i < starCount; i++) {
            createStar(starsContainer);
        }
        
        // Restart animation
        animateStars();
    });
});

// Function to create a single star
function createStar(container) {
    const star = document.createElement('div');
    star.classList.add('star');
    
    // Random position
    const posX = Math.random() * window.innerWidth;
    const posY = Math.random() * window.innerHeight;
    
    // Random size (tiny to small)
    const size = Math.random() * 2 + 1;
    
    // Random opacity for twinkling effect
    const opacity = Math.random() * 0.7 + 0.3;
    
    // Random speed for movement
    const speed = Math.random() * 0.5 + 0.1;
    star.dataset.speed = speed;
    
    // Random direction
    const direction = Math.random() > 0.5 ? 1 : -1;
    star.dataset.direction = direction;
    
    // Set initial position as data attributes for animation
    star.dataset.x = posX;
    star.dataset.y = posY;
    
    // Set star styles
    star.style.left = `${posX}px`;
    star.style.top = `${posY}px`;
    star.style.width = `${size}px`;
    star.style.height = `${size}px`;
    star.style.opacity = opacity;
    
    // Add star to container
    container.appendChild(star);
    
    // Cross markers (occasional)
    if (Math.random() > 0.9) {
        star.classList.add('star-cross');
        star.style.width = `${size * 6}px`;
        star.style.height = `${size * 6}px`;
    }
}

// Animate stars with requestAnimationFrame for smooth motion
function animateStars() {
    const stars = document.querySelectorAll('.star');
    
    function animate() {
        stars.forEach(star => {
            // Get current position
            let x = parseFloat(star.dataset.x);
            let y = parseFloat(star.dataset.y);
            
            // Get speed and direction
            const speed = parseFloat(star.dataset.speed);
            const direction = parseFloat(star.dataset.direction);
            
            // Update position with diagonal motion
            x += speed * direction;
            y += speed * 0.5 * direction;
            
            // Reset position if star goes out of viewport
            if (x > window.innerWidth + 100) {
                x = -50;
            } else if (x < -50) {
                x = window.innerWidth + 50;
            }
            
            if (y > window.innerHeight + 100) {
                y = -50;
            } else if (y < -50) {
                y = window.innerHeight + 50;
            }
            
            // Update position data
            star.dataset.x = x;
            star.dataset.y = y;
            
            // Apply new position
            star.style.left = `${x}px`;
            star.style.top = `${y}px`;
        });
        
        // Continue animation
        requestAnimationFrame(animate);
    }
    
    // Start animation
    animate();
}
