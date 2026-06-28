(function () {
    'use strict';

    function prefersReducedMotion() {
        return window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    }

    function animateProgressBars() {
        document.querySelectorAll('[data-animate-width]').forEach(function (el) {
            var target = el.getAttribute('data-animate-width');
            if (prefersReducedMotion()) {
                el.style.width = target;
                return;
            }
            el.style.width = '0%';
            requestAnimationFrame(function () {
                requestAnimationFrame(function () {
                    el.style.width = target;
                });
            });
        });
    }

    function initReviewFilters() {
        var root = document.getElementById('tr-review-root');
        if (!root) return;

        var cards = root.querySelectorAll('.tr-q[data-review-state]');
        var filterBtns = root.querySelectorAll('[data-review-filter]');
        var searchInput = document.getElementById('tr-review-search');
        var emptyMsg = document.getElementById('tr-review-empty');
        var visibleCount = document.getElementById('tr-review-visible-count');
        var activeFilter = 'all';

        function applyFilters() {
            var q = (searchInput && searchInput.value || '').trim().toLowerCase();
            var shown = 0;

            cards.forEach(function (card) {
                var state = card.getAttribute('data-review-state');
                var text = (card.getAttribute('data-search-text') || '').toLowerCase();
                var matchFilter = activeFilter === 'all' || state === activeFilter;
                var matchSearch = !q || text.indexOf(q) !== -1;
                var show = matchFilter && matchSearch;
                card.classList.toggle('tr-q--hidden', !show);
                if (show) shown += 1;
            });

            if (emptyMsg) {
                emptyMsg.classList.toggle('d-none', shown > 0);
            }
            if (visibleCount) {
                visibleCount.textContent = shown;
            }
        }

        filterBtns.forEach(function (btn) {
            btn.addEventListener('click', function () {
                activeFilter = btn.getAttribute('data-review-filter');
                filterBtns.forEach(function (b) {
                    b.classList.toggle('is-active', b === btn);
                });
                applyFilters();
            });
        });

        if (searchInput) {
            searchInput.addEventListener('input', applyFilters);
        }

        applyFilters();
    }

    function initEssayToggles() {
        document.querySelectorAll('[data-essay-toggle]').forEach(function (btn) {
            btn.addEventListener('click', function () {
                var wrap = btn.closest('.answer-essay-wrap');
                if (!wrap) return;
                var expanded = wrap.classList.toggle('is-expanded');
                btn.textContent = expanded ? 'Kamroq' : "Ko'proq o'qish";
            });
        });
    }

    function launchConfetti() {
        if (prefersReducedMotion()) return;
        var canvas = document.getElementById('tr-confetti');
        if (!canvas) return;

        var ctx = canvas.getContext('2d');
        var w = canvas.width = window.innerWidth;
        var h = canvas.height = window.innerHeight;
        var colors = ['#6366f1', '#10b981', '#f59e0b', '#06b6d4', '#ec4899'];
        var pieces = [];
        var count = 80;

        for (var i = 0; i < count; i++) {
            pieces.push({
                x: Math.random() * w,
                y: Math.random() * h - h,
                r: 4 + Math.random() * 6,
                d: 2 + Math.random() * 4,
                color: colors[Math.floor(Math.random() * colors.length)],
                tilt: Math.random() * 10 - 5
            });
        }

        var frame = 0;
        var maxFrames = 120;

        function draw() {
            ctx.clearRect(0, 0, w, h);
            pieces.forEach(function (p) {
                ctx.beginPath();
                ctx.fillStyle = p.color;
                ctx.fillRect(p.x, p.y, p.r, p.r * 0.6);
                p.y += p.d;
                p.x += Math.sin(frame * 0.05 + p.tilt);
            });
            frame += 1;
            if (frame < maxFrames) {
                requestAnimationFrame(draw);
            } else {
                canvas.classList.add('d-none');
            }
        }
        canvas.classList.remove('d-none');
        draw();
    }

    document.addEventListener('DOMContentLoaded', function () {
        animateProgressBars();
        initReviewFilters();
        initEssayToggles();
        if (document.body.getAttribute('data-show-confetti') === '1') {
            setTimeout(launchConfetti, 400);
        }
    });
})();
