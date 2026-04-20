/* ============================================
   DocIntel AI — Animation & Interactivity Engine
   ============================================ */

// Intersection Observer for scroll-reveal animations
document.addEventListener('DOMContentLoaded', () => {
  // Scroll reveal
  const revealElements = document.querySelectorAll('.reveal, .reveal-left, .reveal-right');
  if (revealElements.length) {
    const observer = new IntersectionObserver((entries) => {
      entries.forEach(entry => {
        if (entry.isIntersecting) {
          entry.target.classList.add('visible');
          observer.unobserve(entry.target);
        }
      });
    }, { threshold: 0.15, rootMargin: '0px 0px -40px 0px' });
    revealElements.forEach(el => observer.observe(el));
  }

  // Staggered reveal for children
  document.querySelectorAll('[data-stagger]').forEach(parent => {
    const delay = parseFloat(parent.dataset.stagger) || 0.1;
    Array.from(parent.children).forEach((child, i) => {
      child.style.animationDelay = `${i * delay}s`;
    });
  });

  // Animated counters
  document.querySelectorAll('[data-count]').forEach(el => {
    const target = parseFloat(el.dataset.count);
    const suffix = el.dataset.suffix || '';
    const prefix = el.dataset.prefix || '';
    const duration = 1500;
    const observer = new IntersectionObserver((entries) => {
      entries.forEach(entry => {
        if (entry.isIntersecting) {
          animateCount(el, target, duration, prefix, suffix);
          observer.unobserve(entry.target);
        }
      });
    }, { threshold: 0.5 });
    observer.observe(el);
  });

  // Bar chart animation
  document.querySelectorAll('.bar[data-height]').forEach(bar => {
    const observer = new IntersectionObserver((entries) => {
      entries.forEach(entry => {
        if (entry.isIntersecting) {
          bar.style.height = bar.dataset.height;
          observer.unobserve(entry.target);
        }
      });
    }, { threshold: 0.3 });
    bar.style.height = '0';
    observer.observe(bar);
  });

  // Ripple effect on buttons
  document.querySelectorAll('.btn-ripple').forEach(btn => {
    btn.addEventListener('click', function(e) {
      const circle = document.createElement('span');
      circle.classList.add('ripple-circle');
      const rect = this.getBoundingClientRect();
      const size = Math.max(rect.width, rect.height);
      circle.style.width = circle.style.height = size + 'px';
      circle.style.left = (e.clientX - rect.left - size / 2) + 'px';
      circle.style.top = (e.clientY - rect.top - size / 2) + 'px';
      this.appendChild(circle);
      setTimeout(() => circle.remove(), 600);
    });
  });

  // Smooth toggle
  document.querySelectorAll('.toggle').forEach(toggle => {
    toggle.addEventListener('click', () => toggle.classList.toggle('active'));
  });

  // Sidebar active link
  const currentPage = window.location.pathname.split('/').pop() || 'index.html';
  document.querySelectorAll('.sidebar-nav a').forEach(link => {
    const href = link.getAttribute('href');
    if (href && (href === currentPage || href.endsWith('/' + currentPage))) {
      link.classList.add('active');
    }
  });

  // Mobile menu toggle
  const menuBtn = document.getElementById('mobile-menu-btn');
  const sidebar = document.querySelector('.sidebar');
  if (menuBtn && sidebar) {
    menuBtn.addEventListener('click', () => {
      sidebar.style.display = sidebar.style.display === 'flex' ? 'none' : 'flex';
    });
  }

  // Typewriter effect
  document.querySelectorAll('[data-typewriter]').forEach(el => {
    const text = el.textContent;
    el.textContent = '';
    el.style.visibility = 'visible';
    let i = 0;
    const speed = parseInt(el.dataset.typewriter) || 40;
    function type() {
      if (i < text.length) {
        el.textContent += text.charAt(i);
        i++;
        setTimeout(type, speed);
      }
    }
    const observer = new IntersectionObserver((entries) => {
      entries.forEach(entry => {
        if (entry.isIntersecting) {
          type();
          observer.unobserve(entry.target);
        }
      });
    }, { threshold: 0.5 });
    observer.observe(el);
  });

  // Parallax effect
  document.querySelectorAll('[data-parallax]').forEach(el => {
    const speed = parseFloat(el.dataset.parallax) || 0.3;
    window.addEventListener('scroll', () => {
      const y = window.scrollY;
      el.style.transform = `translateY(${y * speed}px)`;
    });
  });

  // Hover tilt effect for cards
  document.querySelectorAll('.tilt-card').forEach(card => {
    card.addEventListener('mousemove', (e) => {
      const rect = card.getBoundingClientRect();
      const x = e.clientX - rect.left;
      const y = e.clientY - rect.top;
      const centerX = rect.width / 2;
      const centerY = rect.height / 2;
      const rotateX = (y - centerY) / 20;
      const rotateY = (centerX - x) / 20;
      card.style.transform = `perspective(1000px) rotateX(${rotateX}deg) rotateY(${rotateY}deg) scale(1.02)`;
    });
    card.addEventListener('mouseleave', () => {
      card.style.transform = 'perspective(1000px) rotateX(0) rotateY(0) scale(1)';
    });
  });

  // Progress bar animations
  document.querySelectorAll('.progress-fill[data-width]').forEach(fill => {
    const observer = new IntersectionObserver((entries) => {
      entries.forEach(entry => {
        if (entry.isIntersecting) {
          fill.style.width = fill.dataset.width;
          observer.unobserve(entry.target);
        }
      });
    }, { threshold: 0.5 });
    fill.style.width = '0';
    observer.observe(fill);
  });
});

// Counter animation helper
function animateCount(el, target, duration, prefix, suffix) {
  const start = performance.now();
  const isFloat = target % 1 !== 0;
  function update(now) {
    const progress = Math.min((now - start) / duration, 1);
    const eased = 1 - Math.pow(1 - progress, 3); // easeOutCubic
    const current = target * eased;
    el.textContent = prefix + (isFloat ? current.toFixed(1) : Math.floor(current).toLocaleString()) + suffix;
    if (progress < 1) requestAnimationFrame(update);
  }
  requestAnimationFrame(update);
}

// Page navigation helper
function navigateTo(url) {
  document.body.style.opacity = '0';
  document.body.style.transition = 'opacity 0.3s ease';
  setTimeout(() => window.location.href = url, 300);
}

// Notification popup
function showNotification(message, type = 'success') {
  const notif = document.createElement('div');
  notif.style.cssText = `
    position: fixed; bottom: 2rem; right: 2rem; z-index: 9999;
    padding: 1rem 1.5rem; border-radius: 0.75rem; font-size: 0.875rem;
    font-weight: 600; font-family: var(--font); color: white;
    background: ${type === 'success' ? '#059669' : type === 'error' ? '#dc2626' : '#553520'};
    box-shadow: 0 10px 30px rgba(0,0,0,0.2);
    animation: fadeInUp 0.4s ease;
    display: flex; align-items: center; gap: 0.5rem;
  `;
  const icon = type === 'success' ? 'check_circle' : type === 'error' ? 'error' : 'info';
  notif.innerHTML = `<span class="material-symbols-outlined">${icon}</span> ${message}`;
  document.body.appendChild(notif);
  setTimeout(() => {
    notif.style.opacity = '0';
    notif.style.transform = 'translateY(10px)';
    notif.style.transition = 'all 0.3s ease';
    setTimeout(() => notif.remove(), 300);
  }, 3000);
}

// Drag & drop for upload zones
function initDropzone(dropzoneEl, onFiles) {
  if (!dropzoneEl) return;
  ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(evt => {
    dropzoneEl.addEventListener(evt, e => { e.preventDefault(); e.stopPropagation(); });
  });
  ['dragenter', 'dragover'].forEach(evt => {
    dropzoneEl.addEventListener(evt, () => dropzoneEl.classList.add('dragover'));
  });
  ['dragleave', 'drop'].forEach(evt => {
    dropzoneEl.addEventListener(evt, () => dropzoneEl.classList.remove('dragover'));
  });
  dropzoneEl.addEventListener('drop', (e) => {
    const files = e.dataTransfer.files;
    if (onFiles) onFiles(files);
  });
}
