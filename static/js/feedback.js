/**
 * feedback.js — Public feedback form interactivity
 */
(() => {
  'use strict';

  const emojiBtns  = document.querySelectorAll('.emoji-btn');
  const submitBtn  = document.getElementById('submitBtn');
  const statusText = document.getElementById('statusText');
  const commentEl  = document.getElementById('comment');
  const charCount  = document.getElementById('charCount');

  if (!emojiBtns.length) return;

  /* ── Emoji selection ── */
  function selectEmoji(btn) {
    emojiBtns.forEach(b => {
      b.classList.remove('active');
      b.setAttribute('aria-checked', 'false');
      b.querySelector('input[type="radio"]').checked = false;
    });
    btn.classList.add('active');
    btn.setAttribute('aria-checked', 'true');
    btn.querySelector('input[type="radio"]').checked = true;

    if (statusText) {
      statusText.textContent = `You selected: ${btn.dataset.label || btn.querySelector('.emoji-label').textContent}`;
      statusText.classList.add('selected');
    }
    if (submitBtn) {
      submitBtn.disabled = false;
      submitBtn.removeAttribute('aria-disabled');
    }
  }

  emojiBtns.forEach(btn => {
    btn.addEventListener('click', () => selectEmoji(btn));
    btn.addEventListener('keydown', e => {
      if (e.key === 'Enter' || e.key === ' ') {
        e.preventDefault();
        selectEmoji(btn);
      }
    });
  });

  /* ── Char counter ── */
  if (commentEl && charCount) {
    commentEl.addEventListener('input', () => {
      const len = commentEl.value.length;
      charCount.textContent = len;
      const wrap = charCount.closest('.char-counter');
      wrap && wrap.classList.toggle('warn', len >= 270);
    });
  }

  /* ── Submit: prevent double-click ── */
  if (submitBtn) {
    submitBtn.addEventListener('click', function () {
      if (!this.disabled) {
        setTimeout(() => { this.disabled = true; }, 10);
      }
    });
    // Re-enable if form validation stops submission
    const form = document.getElementById('feedbackForm');
    if (form) form.addEventListener('submit', e => {
      const hasRating = [...emojiBtns].some(b => b.classList.contains('active'));
      if (!hasRating) {
        e.preventDefault();
        if (statusText) {
          statusText.textContent = 'Please select a rating first.';
          statusText.classList.remove('selected');
          statusText.style.color = 'var(--red)';
        }
        submitBtn.disabled = false;
      }
    });
  }
})();
