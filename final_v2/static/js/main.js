// Auto-hide flash messages after 5 seconds
document.addEventListener('DOMContentLoaded', function() {
    const alerts = document.querySelectorAll('.alert');
    alerts.forEach(function(alert) {
        setTimeout(function() {
            alert.style.transition = 'opacity 0.5s ease-out';
            alert.style.opacity = '0';
            setTimeout(function() {
                alert.style.display = 'none';
            }, 500);
        }, 5000);
    });
});

// Confirm before dangerous actions
function confirmAction(message) {
    return confirm(message || 'Are you sure you want to perform this action?');
}

// File size validation
document.addEventListener('DOMContentLoaded', function() {
    const fileInput = document.querySelector('input[type="file"]');
    if (fileInput) {
        fileInput.addEventListener('change', function(e) {
            const file = e.target.files[0];
            if (file && file.size > 5 * 1024 * 1024) { // 5MB
                alert('File size must be less than 5MB');
                e.target.value = '';
            }
        });
    }
});

// FIXED Password visibility toggle functionality for specific pages with IMAGE ICONS
document.addEventListener('DOMContentLoaded', function() {
    // Handle login page password toggle
    const loginPasswordField = document.getElementById('login_password');
    if (loginPasswordField) {
        const loginToggle = loginPasswordField.parentNode.querySelector('.password-toggle');
        if (loginToggle) {
            loginToggle.addEventListener('click', function(e) {
                e.preventDefault();
                toggleSpecificPasswordWithImages(loginPasswordField, loginToggle);
            });
        }
    }
    
    // Handle register page password toggles
    const registerPasswordField = document.getElementById('register_password');
    if (registerPasswordField) {
        const registerToggle = registerPasswordField.parentNode.querySelector('.password-toggle');
        if (registerToggle) {
            registerToggle.addEventListener('click', function(e) {
                e.preventDefault();
                toggleSpecificPasswordWithImages(registerPasswordField, registerToggle);
            });
        }
    }
    
    const confirmPasswordField = document.getElementById('confirm_password');
    if (confirmPasswordField) {
        const confirmToggle = confirmPasswordField.parentNode.querySelector('.password-toggle');
        if (confirmToggle) {
            confirmToggle.addEventListener('click', function(e) {
                e.preventDefault();
                toggleSpecificPasswordWithImages(confirmPasswordField, confirmToggle);
            });
        }
    }
    
    // ADD: Handle admin password toggles
    const adminPasswordField = document.getElementById('admin_password');
    if (adminPasswordField) {
        const adminToggle = adminPasswordField.parentNode.querySelector('.password-toggle');
        if (adminToggle) {
            adminToggle.addEventListener('click', function(e) {
                e.preventDefault();
                toggleSpecificPasswordWithImages(adminPasswordField, adminToggle);
            });
        }
    }
    
    const adminConfirmPasswordField = document.getElementById('admin_confirm_password');
    if (adminConfirmPasswordField) {
        const adminConfirmToggle = adminConfirmPasswordField.parentNode.querySelector('.password-toggle');
        if (adminConfirmToggle) {
            adminConfirmToggle.addEventListener('click', function(e) {
                e.preventDefault();
                toggleSpecificPasswordWithImages(adminConfirmPasswordField, adminConfirmToggle);
            });
        }
    }
});

// Function to toggle specific password field with IMAGE ICONS
function toggleSpecificPasswordWithImages(field, toggle) {
    const icon = toggle.querySelector('img');
    
    if (field.type === 'password') {
        field.type = 'text';
        if (icon) {
            icon.src = '/static/uploads/eye-slash.png';
            icon.alt = 'Hide password';
        }
        toggle.setAttribute('aria-label', 'Hide password');
        toggle.setAttribute('title', 'Hide password');
    } else {
        field.type = 'password';
        if (icon) {
            icon.src = '/static/uploads/eye.png';
            icon.alt = 'Show password';
        }
        toggle.setAttribute('aria-label', 'Show password');
        toggle.setAttribute('title', 'Show password');
    }
}

// ORIGINAL Password visibility toggle functionality for general use (admin forms)
function togglePassword(fieldId) {
    const field = document.getElementById(fieldId);
    if (!field) return;
    
    const wrapper = field.closest('.password-input-wrapper');
    if (!wrapper) return;
    
    const toggle = wrapper.querySelector('.password-toggle');
    const icon = toggle.querySelector('img');
    
    if (field.type === 'password') {
        field.type = 'text';
        if (icon) {
            icon.src = '/static/uploads/eye-slash.png'; // Hidden eye icon
            icon.alt = 'Hide password';
        }
        toggle.setAttribute('aria-label', 'Hide password');
        toggle.setAttribute('title', 'Hide password');
    } else {
        field.type = 'password';
        if (icon) {
            icon.src = '/static/uploads/eye.png'; // Visible eye icon
            icon.alt = 'Show password';
        }
        toggle.setAttribute('aria-label', 'Show password');
        toggle.setAttribute('title', 'Show password');
    }
}

// Initialize password toggles for admin forms and other pages
document.addEventListener('DOMContentLoaded', function() {
    // Find all password fields that don't have specific IDs and add toggle functionality
    // UPDATED: Exclude admin password fields since they're handled specifically above
    const passwordFields = document.querySelectorAll('input[type="password"]:not(#login_password):not(#register_password):not(#confirm_password):not(#admin_password):not(#admin_confirm_password)');
    
    passwordFields.forEach(function(field, index) {
        // Ensure the field has an ID for the toggle function
        if (!field.id) {
            field.id = 'password-field-' + index;
        }
        
        const wrapper = field.parentNode;
        
        // Check if this field already has a toggle (to avoid duplicates)
        if (wrapper.querySelector('.password-toggle')) {
            return;
        }
        
        // Add password-field class for styling
        field.classList.add('password-field');
        
        // Create wrapper if it doesn't exist
        if (!wrapper.classList.contains('password-input-wrapper')) {
            const newWrapper = document.createElement('div');
            newWrapper.className = 'password-input-wrapper';
            field.parentNode.insertBefore(newWrapper, field);
            newWrapper.appendChild(field);
        }
        
        // Create toggle button
        const toggle = document.createElement('button');
        toggle.type = 'button';
        toggle.className = 'password-toggle';
        toggle.setAttribute('aria-label', 'Show password');
        toggle.setAttribute('title', 'Show password');
        
        // Use image icons
        const icon = document.createElement('img');
        icon.src = '/static/uploads/eye.png';
        icon.alt = 'Show password';
        icon.width = 20;
        icon.height = 20;
        toggle.appendChild(icon);
        
        // Add click event with proper field ID reference
        toggle.addEventListener('click', function(e) {
            e.preventDefault();
            togglePasswordWithElement(field, toggle);
        });
        
        // Add toggle to wrapper
        wrapper.appendChild(toggle);
    });
});

// Enhanced toggle function that works with the actual elements
function togglePasswordWithElement(field, toggle) {
    const icon = toggle.querySelector('img');
    
    if (field.type === 'password') {
        field.type = 'text';
        if (icon) {
            icon.src = '/static/uploads/eye-slash.png';
            icon.alt = 'Hide password';
        }
        toggle.setAttribute('aria-label', 'Hide password');
        toggle.setAttribute('title', 'Hide password');
    } else {
        field.type = 'password';
        if (icon) {
            icon.src = '/static/uploads/eye.png';
            icon.alt = 'Show password';
        }
        toggle.setAttribute('aria-label', 'Show password');
        toggle.setAttribute('title', 'Show password');
    }
}

// Enhanced dropdown functionality with hover delay - EXTENDED TO 2 SECONDS
document.addEventListener('DOMContentLoaded', function() {
    const dropdowns = document.querySelectorAll('.dropdown');
    
    dropdowns.forEach(function(dropdown) {
        const toggle = dropdown.querySelector('.dropdown-toggle');
        const menu = dropdown.querySelector('.dropdown-menu');
        let hoverTimeout;
        let isHovering = false;
        
        if (toggle && menu) {
            // Mouse enter events
            dropdown.addEventListener('mouseenter', function() {
                clearTimeout(hoverTimeout);
                isHovering = true;
                menu.style.display = 'block';
                menu.style.opacity = '1';
                menu.style.visibility = 'visible';
            });
            
            // Mouse leave events with EXTENDED delay (2 seconds instead of 1)
            dropdown.addEventListener('mouseleave', function() {
                isHovering = false;
                hoverTimeout = setTimeout(function() {
                    if (!isHovering) {
                        menu.style.opacity = '0';
                        menu.style.visibility = 'hidden';
                        setTimeout(function() {
                            if (!isHovering) {
                                menu.style.display = 'none';
                            }
                        }, 300); // Match CSS transition duration
                    }
                }, 2000); // EXTENDED: 2 second delay instead of 1 second
            });
            
            // Prevent menu from disappearing when hovering over the menu itself
            menu.addEventListener('mouseenter', function() {
                clearTimeout(hoverTimeout);
                isHovering = true;
            });
            
            menu.addEventListener('mouseleave', function() {
                isHovering = false;
                hoverTimeout = setTimeout(function() {
                    if (!isHovering) {
                        menu.style.opacity = '0';
                        menu.style.visibility = 'hidden';
                        setTimeout(function() {
                            if (!isHovering) {
                                menu.style.display = 'none';
                            }
                        }, 300);
                    }
                }, 2000); // EXTENDED: 2 second delay instead of 1 second
            });
            
            // Handle mobile touch events
            toggle.addEventListener('touchstart', function(e) {
                e.preventDefault();
                
                // Close other open dropdowns
                dropdowns.forEach(function(otherDropdown) {
                    if (otherDropdown !== dropdown) {
                        const otherMenu = otherDropdown.querySelector('.dropdown-menu');
                        otherMenu.style.display = 'none';
                        otherMenu.style.opacity = '0';
                        otherMenu.style.visibility = 'hidden';
                    }
                });
                
                // Toggle current dropdown
                if (menu.style.display === 'block') {
                    menu.style.opacity = '0';
                    menu.style.visibility = 'hidden';
                    setTimeout(function() {
                        menu.style.display = 'none';
                    }, 300);
                } else {
                    menu.style.display = 'block';
                    menu.style.opacity = '1';
                    menu.style.visibility = 'visible';
                }
            });
        }
    });
    
    // Close dropdowns when clicking outside
    document.addEventListener('click', function(e) {
        if (!e.target.closest('.dropdown')) {
            dropdowns.forEach(function(dropdown) {
                const menu = dropdown.querySelector('.dropdown-menu');
                menu.style.opacity = '0';
                menu.style.visibility = 'hidden';
                setTimeout(function() {
                    menu.style.display = 'none';
                }, 300);
            });
        }
    });
});

// Enhanced form validation feedback
document.addEventListener('DOMContentLoaded', function() {
    const forms = document.querySelectorAll('form');
    
    forms.forEach(function(form) {
        form.addEventListener('submit', function(e) {
            const requiredFields = form.querySelectorAll('[required]');
            let hasErrors = false;
            
            requiredFields.forEach(function(field) {
                if (!field.value.trim()) {
                    field.style.borderColor = 'var(--danger-color)';
                    hasErrors = true;
                } else {
                    field.style.borderColor = 'var(--border-color)';
                }
            });
            
            if (hasErrors) {
                e.preventDefault();
                alert('Please fill in all required fields.');
            }
        });
    });
});

// Smooth scroll for anchor links - Landing Page
document.addEventListener('DOMContentLoaded', function() {
    const anchorLinks = document.querySelectorAll('a[href^="#"]');
    
    anchorLinks.forEach(function(link) {
        link.addEventListener('click', function(e) {
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
});

// Add loading state to form submissions
document.addEventListener('DOMContentLoaded', function() {
    const forms = document.querySelectorAll('form');
    
    forms.forEach(function(form) {
        const submitBtn = form.querySelector('input[type="submit"], button[type="submit"]');
        if (submitBtn) {
            // Store original text
            submitBtn.setAttribute('data-original-text', submitBtn.innerHTML);
        }
        
        form.addEventListener('submit', function() {
            if (submitBtn) {
                submitBtn.disabled = true;
                submitBtn.innerHTML = 'Processing...';
                
                // Re-enable after 10 seconds as fallback
                setTimeout(function() {
                    submitBtn.disabled = false;
                    submitBtn.innerHTML = submitBtn.getAttribute('data-original-text') || 'Submit';
                }, 10000);
            }
        });
    });
});

// Admin navigation card animations
document.addEventListener('DOMContentLoaded', function() {
    const navCards = document.querySelectorAll('.admin-nav-card');
    
    navCards.forEach(function(card, index) {
        // Add staggered animation on load
        card.style.opacity = '0';
        card.style.transform = 'translateY(20px)';
        
        setTimeout(function() {
            card.style.transition = 'opacity 0.5s ease, transform 0.5s ease';
            card.style.opacity = '1';
            card.style.transform = 'translateY(0)';
        }, index * 100); // Stagger by 100ms
    });
});

// Landing Page Specific JavaScript
document.addEventListener('DOMContentLoaded', function() {
    // Only run landing page animations if we're on the landing page
    if (document.body.classList.contains('landing-page')) {
        // Simple animation on scroll for landing page
        const observerOptions = {
            threshold: 0.1,
            rootMargin: '0px 0px -50px 0px'
        };
        
        const observer = new IntersectionObserver((entries) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    entry.target.style.opacity = '1';
                    entry.target.style.transform = 'translateY(0)';
                }
            });
        }, observerOptions);
        
        // Observe feature cards and impact items
        document.querySelectorAll('.feature-card, .impact-item').forEach(card => {
            card.style.opacity = '0';
            card.style.transform = 'translateY(20px)';
            card.style.transition = 'opacity 0.6s ease, transform 0.6s ease';
            observer.observe(card);
        });
        
        // Animate stats numbers on scroll
        const statsObserver = new IntersectionObserver((entries) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    const statNumber = entry.target.querySelector('.stat-number');
                    if (statNumber && !statNumber.classList.contains('animated')) {
                        statNumber.classList.add('animated');
                        animateNumber(statNumber);
                    }
                }
            });
        }, { threshold: 0.5 });
        
        document.querySelectorAll('.stat-item').forEach(item => {
            statsObserver.observe(item);
        });
    }
});

// Animate numbers counting up
function animateNumber(element) {
    const text = element.textContent;
    const number = parseInt(text.replace(/\D/g, ''));
    const suffix = text.replace(/\d/g, '');
    const duration = 2000; // 2 seconds
    const increment = number / (duration / 16); // 60fps
    let current = 0;
    
    const timer = setInterval(() => {
        current += increment;
        if (current >= number) {
            current = number;
            clearInterval(timer);
        }
        element.textContent = Math.floor(current) + suffix;
    }, 16);
}

// Enhanced navigation for mobile devices
document.addEventListener('DOMContentLoaded', function() {
    // Add mobile menu toggle functionality if needed
    const navToggle = document.querySelector('.nav-toggle');
    const navLinks = document.querySelector('.nav-links');
    
    if (navToggle && navLinks) {
        navToggle.addEventListener('click', function() {
            navLinks.classList.toggle('nav-open');
        });
    }
    
    // Close mobile menu when clicking on a link
    document.querySelectorAll('.nav-links a').forEach(link => {
        link.addEventListener('click', function() {
            if (navLinks) {
                navLinks.classList.remove('nav-open');
            }
        });
    });
});

// Form accessibility improvements
document.addEventListener('DOMContentLoaded', function() {
    // Add focus management for better accessibility
    const inputs = document.querySelectorAll('input, textarea, select');
    
    inputs.forEach(input => {
        input.addEventListener('focus', function() {
            this.parentNode.classList.add('focused');
        });
        
        input.addEventListener('blur', function() {
            this.parentNode.classList.remove('focused');
            if (this.value) {
                this.parentNode.classList.add('has-value');
            } else {
                this.parentNode.classList.remove('has-value');
            }
        });
        
        // Initial check for pre-filled values
        if (input.value) {
            input.parentNode.classList.add('has-value');
        }
    });
});

// Enhanced error handling for forms
document.addEventListener('DOMContentLoaded', function() {
    const forms = document.querySelectorAll('form');
    
    forms.forEach(form => {
        const inputs = form.querySelectorAll('input[required], textarea[required], select[required]');
        
        inputs.forEach(input => {
            input.addEventListener('blur', function() {
                validateField(this);
            });
            
            input.addEventListener('input', function() {
                if (this.classList.contains('error')) {
                    validateField(this);
                }
            });
        });
    });
});

// Field validation function
function validateField(field) {
    const value = field.value.trim();
    const type = field.type;
    let isValid = true;
    
    // Remove existing error classes
    field.classList.remove('error');
    const existingError = field.parentNode.querySelector('.field-error');
    if (existingError) {
        existingError.remove();
    }
    
    // Check if required field is empty
    if (field.hasAttribute('required') && !value) {
        isValid = false;
        showFieldError(field, 'This field is required');
    }
    
    // Email validation
    if (type === 'email' && value) {
        const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
        if (!emailRegex.test(value)) {
            isValid = false;
            showFieldError(field, 'Please enter a valid email address');
        }
    }
    
    // Password validation for registration
    if (field.id === 'register_password' && value) {
        if (value.length < 8) {
            isValid = false;
            showFieldError(field, 'Password must be at least 8 characters long');
        }
    }
    
    // Confirm password validation
    if (field.id === 'confirm_password' && value) {
        const passwordField = document.getElementById('register_password');
        if (passwordField && value !== passwordField.value) {
            isValid = false;
            showFieldError(field, 'Passwords do not match');
        }
    }
    
    return isValid;
}

// Show field error function
function showFieldError(field, message) {
    field.classList.add('error');
    
    const errorElement = document.createElement('span');
    errorElement.className = 'field-error';
    errorElement.textContent = message;
    errorElement.style.color = 'var(--danger-color)';
    errorElement.style.fontSize = '14px';
    errorElement.style.display = 'block';
    errorElement.style.marginTop = '5px';
    
    field.parentNode.appendChild(errorElement);
}

// Admin form volunteer checkbox functionality
document.addEventListener('DOMContentLoaded', function() {
    // Handle volunteer checkbox on admin forms
    const volunteerCheckbox = document.getElementById('is_volunteer');
    const approveGroup = document.getElementById('approve-volunteer-group');
    
    if (volunteerCheckbox && approveGroup) {
        function toggleApproveOption() {
            if (volunteerCheckbox.checked) {
                approveGroup.style.display = 'block';
            } else {
                approveGroup.style.display = 'none';
                const approveCheckbox = document.getElementById('approve_volunteer');
                if (approveCheckbox) {
                    approveCheckbox.checked = false;
                }
            }
        }
        
        // Initial check
        toggleApproveOption();
        
        // Listen for changes
        volunteerCheckbox.addEventListener('change', toggleApproveOption);
    }
});

// Console log for debugging (remove in production)
console.log('SilverSage main.js loaded successfully');
console.log('Password toggle functionality initialized with image icons');
console.log('Landing page animations ready');
console.log('Form validation enhanced');
console.log('Admin password fields support added');