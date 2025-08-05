// FIXED Password visibility toggle functionality - Add this to your main.js

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

// FIXED Password visibility toggle functionality
document.addEventListener('DOMContentLoaded', function() {
    // Find all password fields and add toggle functionality
    const passwordFields = document.querySelectorAll('input[type="password"]');
    
    passwordFields.forEach(function(field, index) {
        // Check if this field already has a toggle button
        const existingToggle = field.parentNode.querySelector('.password-toggle');
        if (existingToggle) {
            // If toggle already exists, just add the event listener
            existingToggle.addEventListener('click', function(e) {
                e.preventDefault();
                togglePasswordField(field, existingToggle);
            });
            return;
        }
        
        // Create wrapper if it doesn't exist
        let wrapper = field.parentNode;
        if (!wrapper.classList.contains('password-input-wrapper')) {
            wrapper = document.createElement('div');
            wrapper.className = 'password-input-wrapper';
            field.parentNode.insertBefore(wrapper, field);
            wrapper.appendChild(field);
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
        
        // Add click event
        toggle.addEventListener('click', function(e) {
            e.preventDefault();
            togglePasswordField(field, toggle);
        });
        
        // Add toggle to wrapper
        wrapper.appendChild(toggle);
    });
});

// Function to toggle a specific password field
function togglePasswordField(field, toggle) {
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

// Account lockout countdown timer
document.addEventListener('DOMContentLoaded', function() {
    const lockoutAlert = document.querySelector('.lockout-alert');
    
    if (lockoutAlert) {
        const lockoutText = lockoutAlert.querySelector('.lockout-reason');
        if (lockoutText) {
            const message = lockoutText.textContent;
            
            // Extract time from the message
            const timeMatch = message.match(/(\d+)\s+minute\(s\)\s+and\s+(\d+)\s+second\(s\)|(\d+)\s+second\(s\)/);
            
            if (timeMatch) {
                let totalSeconds;
                
                if (timeMatch[1] && timeMatch[2]) {
                    // Format: "X minute(s) and Y second(s)"
                    totalSeconds = parseInt(timeMatch[1]) * 60 + parseInt(timeMatch[2]);
                } else if (timeMatch[3]) {
                    // Format: "X second(s)"
                    totalSeconds = parseInt(timeMatch[3]);
                }
                
                if (totalSeconds && totalSeconds > 0) {
                    // Create countdown element
                    const countdownContainer = document.createElement('div');
                    countdownContainer.className = 'lockout-countdown';
                    countdownContainer.innerHTML = `
                        <div class="countdown-header">
                            <h5>⏱️ Time Remaining:</h5>
                        </div>
                        <div class="countdown-display">
                            <span id="lockout-timer">${formatTime(totalSeconds)}</span>
                        </div>
                        <div class="countdown-progress">
                            <div class="progress-bar" id="progress-bar"></div>
                        </div>
                        <div class="countdown-info">
                            <small>Your account will automatically unlock when the timer reaches zero.</small>
                        </div>
                    `;
                    
                    // Insert countdown after the lockout reason
                    lockoutText.parentNode.insertBefore(countdownContainer, lockoutText.nextSibling);
                    
                    // Start countdown
                    startLockoutCountdown(totalSeconds);
                }
            }
        }
    }
});

function startLockoutCountdown(totalSeconds) {
    const timerElement = document.getElementById('lockout-timer');
    const progressBar = document.getElementById('progress-bar');
    const originalSeconds = totalSeconds;
    
    const countdown = setInterval(function() {
        totalSeconds--;
        
        if (timerElement) {
            timerElement.textContent = formatTime(totalSeconds);
        }
        
        // Update progress bar
        if (progressBar) {
            const progressPercentage = ((originalSeconds - totalSeconds) / originalSeconds) * 100;
            progressBar.style.width = progressPercentage + '%';
        }
        
        // Check if countdown finished
        if (totalSeconds <= 0) {
            clearInterval(countdown);
            showLockoutExpired();
        }
    }, 1000);
}

function formatTime(seconds) {
    const minutes = Math.floor(seconds / 60);
    const remainingSeconds = seconds % 60;
    
    if (minutes > 0) {
        return `${minutes}:${remainingSeconds.toString().padStart(2, '0')}`;
    } else {
        return `${remainingSeconds}s`;
    }
}

function showLockoutExpired() {
    const lockoutAlert = document.querySelector('.lockout-alert');
    const countdownContainer = document.querySelector('.lockout-countdown');
    
    if (countdownContainer) {
        countdownContainer.innerHTML = `
            <div class="lockout-expired">
                <div class="expired-icon">✅</div>
                <h5>Account Unlocked!</h5>
                <p>Your account lockout has expired. You can now try logging in again.</p>
                <button type="button" class="btn btn-success btn-small" onclick="location.reload()">
                    Refresh Page
                </button>
            </div>
        `;
    }
    
    // Change alert styling to success
    if (lockoutAlert) {
        lockoutAlert.classList.remove('lockout-alert');
        lockoutAlert.classList.add('alert-success');
        lockoutAlert.style.background = 'linear-gradient(135deg, #f0fff4, #c6f6d5)';
        lockoutAlert.style.borderColor = '#68d391';
    }
}

// Enhanced form submission with lockout check
document.addEventListener('DOMContentLoaded', function() {
    const loginForm = document.querySelector('form[action=""]'); // Login form
    
    if (loginForm) {
        loginForm.addEventListener('submit', function(e) {
            const lockoutAlert = document.querySelector('.lockout-alert');
            
            // Prevent submission if account is still locked
            if (lockoutAlert && !lockoutAlert.classList.contains('alert-success')) {
                e.preventDefault();
                
                // Shake the form to indicate it's locked
                loginForm.style.animation = 'shake 0.5s ease-in-out';
                
                // Show additional warning
                const existingWarning = document.querySelector('.lockout-submission-warning');
                if (!existingWarning) {
                    const warning = document.createElement('div');
                    warning.className = 'lockout-submission-warning alert alert-warning';
                    warning.innerHTML = `
                        <strong>⚠️ Cannot Login:</strong> Your account is still locked. 
                        Please wait for the lockout period to expire before trying again.
                    `;
                    lockoutAlert.parentNode.insertBefore(warning, lockoutAlert.nextSibling);
                    
                    // Remove warning after 5 seconds
                    setTimeout(() => {
                        if (warning.parentNode) {
                            warning.parentNode.removeChild(warning);
                        }
                    }, 5000);
                }
                
                // Reset animation
                setTimeout(() => {
                    loginForm.style.animation = '';
                }, 500);
                
                return false;
            }
        });
    }
});

// Enhanced dropdown functionality with hover delay
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
            
            // Mouse leave events with delay
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
                        }, 300);
                    }
                }, 2000);
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
                }, 2000);
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

// Smooth scroll for anchor links
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
            submitBtn.setAttribute('data-original-text', submitBtn.innerHTML);
        }
        
        form.addEventListener('submit', function() {
            if (submitBtn) {
                submitBtn.disabled = true;
                submitBtn.innerHTML = 'Processing...';
                
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
        card.style.opacity = '0';
        card.style.transform = 'translateY(20px)';
        
        setTimeout(function() {
            card.style.transition = 'opacity 0.5s ease, transform 0.5s ease';
            card.style.opacity = '1';
            card.style.transform = 'translateY(0)';
        }, index * 100);
    });
});

// Landing Page animations
document.addEventListener('DOMContentLoaded', function() {
    if (document.body.classList.contains('landing-page')) {
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
        
        document.querySelectorAll('.feature-card, .impact-item').forEach(card => {
            card.style.opacity = '0';
            card.style.transform = 'translateY(20px)';
            card.style.transition = 'opacity 0.6s ease, transform 0.6s ease';
            observer.observe(card);
        });
        
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

function animateNumber(element) {
    const text = element.textContent;
    const number = parseInt(text.replace(/\D/g, ''));
    const suffix = text.replace(/\d/g, '');
    const duration = 2000;
    const increment = number / (duration / 16);
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
    const navToggle = document.querySelector('.nav-toggle');
    const navLinks = document.querySelector('.nav-links');
    
    if (navToggle && navLinks) {
        navToggle.addEventListener('click', function() {
            navLinks.classList.toggle('nav-open');
        });
    }
    
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

function validateField(field) {
    const value = field.value.trim();
    const type = field.type;
    let isValid = true;
    
    field.classList.remove('error');
    const existingError = field.parentNode.querySelector('.field-error');
    if (existingError) {
        existingError.remove();
    }
    
    if (field.hasAttribute('required') && !value) {
        isValid = false;
        showFieldError(field, 'This field is required');
    }
    
    if (type === 'email' && value) {
        const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
        if (!emailRegex.test(value)) {
            isValid = false;
            showFieldError(field, 'Please enter a valid email address');
        }
    }
    
    if (field.id === 'register_password' && value) {
        if (value.length < 8) {
            isValid = false;
            showFieldError(field, 'Password must be at least 8 characters long');
        }
    }
    
    if (field.id === 'confirm_password' && value) {
        const passwordField = document.getElementById('register_password');
        if (passwordField && value !== passwordField.value) {
            isValid = false;
            showFieldError(field, 'Passwords do not match');
        }
    }
    
    return isValid;
}

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
        
        toggleApproveOption();
        volunteerCheckbox.addEventListener('change', toggleApproveOption);
    }
});

console.log('SilverSage main.js loaded successfully - Password toggles restored!');