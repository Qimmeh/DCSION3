/**
 * Emora Modular Navigation Sidebar Controller
 * - Automatically loads sidebar.html into #sidebar-container
 * - Activates the matching tab according to the current page
 * - Manages mobile drawer open/close and backdrop overlay
 * - Manages night mode / day mode theme toggle and local storage
 */
(function () {
	// Immediately apply theme to root elements to prevent white flash
	try {
		const currentTheme = localStorage.getItem('theme') || localStorage.getItem('emora-theme');
		if (currentTheme === 'night') {
			document.documentElement.classList.add('night');
			document.documentElement.style.backgroundColor = '#14100c';
			document.documentElement.style.colorScheme = 'dark';
			if (document.body) {
				document.body.classList.add('night');
			}
		}
	} catch (e) {}
	const SIDEBAR_TEMPLATE = `
<button class="hamburger-btn" id="hamburgerBtn" aria-label="Open navigation menu" title="Open navigation" type="button">☰</button>
<div class="sidebar-overlay" id="sidebarOverlay"></div>

<aside class="sidebar" id="sidebar" aria-label="Sidebar navigation">
    <div class="sidebar-top">
        <div class="brand">
            <div class="brand-left">
                <div class="brand-mark">e</div>
                <div class="brand-name">emora <span>Wellbeing &amp; Work</span></div>
            </div>
            <button class="sidebar-close-btn" id="sidebarCloseBtn" aria-label="Close navigation" title="Close navigation" type="button">✕</button>
        </div>

        <span class="nav-label">YOUR SPACE</span>

        <nav class="nav" aria-label="Sidebar navigation">
            <a href="index.html" class="tab-item" data-page="home">
                <span class="nav-icon">⌂</span>
                <span class="tab-label">Home</span>
            </a>
            <a href="timetable.html" class="tab-item" data-page="timetable">
                <span class="nav-icon">◫</span>
                <span class="tab-label">Timetable</span>
            </a>
            <a href="ai.html" class="tab-item" data-page="ai">
                <span class="nav-icon">✦</span>
                <span class="tab-label">AI Assistant</span>
            </a>
            <a href="insights.html" class="tab-item" data-page="insights">
                <span class="nav-icon">▤</span>
                <span class="tab-label">Insights</span>
            </a>
        </nav>
    </div>

    <div class="sidebar-bottom">
        <div class="profile-card">
            <a href="profile.html" class="profile-box tab-item-profile" data-page="profile" title="View Profile" style="text-decoration: none; color: inherit;">
                <div class="profile-avatar">CJ</div>
                <div class="profile-meta">
                    <div class="profile-name">Clara Jensen</div>
                    <div class="profile-email">clara@university.edu</div>
                </div>
            </a>
            <div class="privacy">
                <div>
                    <strong>Focused mode</strong>
                    On • Recovery-first schedule
                </div>
            </div>
        </div>

        <button class="theme-toggle" id="themeToggle" type="button">◐ Switch to night mode</button>
    </div>
</aside>
`;

	function getActivePageKey() {
		if (document.body && document.body.dataset && document.body.dataset.page) {
			return document.body.dataset.page.toLowerCase();
		}
		const path = (window.location.pathname || '').toLowerCase();
		if (path.includes('timetable')) return 'timetable';
		if (path.includes('ai.')) return 'ai';
		if (path.includes('insights')) return 'insights';
		if (path.includes('profile')) return 'profile';
		if (path.includes('journal')) return 'journal';
		return 'home';
	}

	function setupSidebarEvents(container) {
		const hamburgerBtn = container.querySelector('#hamburgerBtn') || document.getElementById('hamburgerBtn');
		const sidebarCloseBtn = container.querySelector('#sidebarCloseBtn') || document.getElementById('sidebarCloseBtn');
		const sidebarOverlay = container.querySelector('#sidebarOverlay') || document.getElementById('sidebarOverlay');
		const themeToggle = container.querySelector('#themeToggle') || document.getElementById('themeToggle');

		function openSidebar() {
			document.body.classList.add('sidebar-open');
		}

		function closeSidebar() {
			document.body.classList.remove('sidebar-open');
		}

		if (hamburgerBtn) hamburgerBtn.addEventListener('click', openSidebar);
		if (sidebarCloseBtn) sidebarCloseBtn.addEventListener('click', closeSidebar);
		if (sidebarOverlay) sidebarOverlay.addEventListener('click', closeSidebar);

		document.addEventListener('keydown', (e) => {
			if (e.key === 'Escape') closeSidebar();
		});

		// Theme logic
		function updateThemeButtonLabel() {
			if (!themeToggle) return;
			const isNight = document.body.classList.contains('night');
			themeToggle.textContent = isNight ? '☀ Switch to day mode' : '◐ Switch to night mode';
		}

		// Initialize from localStorage
		const savedTheme = localStorage.getItem('theme') || localStorage.getItem('emora-theme');
		if (savedTheme === 'night') {
			document.body.classList.add('night');
		}
		updateThemeButtonLabel();

		if (themeToggle) {
			themeToggle.addEventListener('click', () => {
				const isNight = document.body.classList.toggle('night');
				document.documentElement.classList.toggle('night', isNight);
				document.documentElement.style.backgroundColor = isNight ? '#14100c' : '';
				document.documentElement.style.colorScheme = isNight ? 'dark' : 'light';
				localStorage.setItem('theme', isNight ? 'night' : 'day');
				localStorage.setItem('emora-theme', isNight ? 'night' : 'day');
				updateThemeButtonLabel();
				window.dispatchEvent(new CustomEvent('themechange', { detail: { isNight } }));
			});
		}

		// Highlight active navigation tab
		const activeKey = getActivePageKey();
		container.querySelectorAll('[data-page]').forEach((link) => {
			const page = link.dataset.page;
			if (page === activeKey) {
				link.classList.add('active');
			} else {
				link.classList.remove('active');
			}
		});
	}

	function initSidebar() {
		let container = document.getElementById('sidebar-container');
		if (!container) {
			// If not present, create a placeholder as first child of body or main container
			container = document.createElement('div');
			container.id = 'sidebar-container';
			const shell = document.querySelector('.screen-timetable, .screen-ai, .screen-journal, .app-shell, body');
			if (shell && shell !== document.body) {
				shell.insertBefore(container, shell.firstChild);
			} else {
				document.body.insertBefore(container, document.body.firstChild);
			}
		}

		// Try fetching sidebar.html first (works on server)
		fetch('sidebar.html')
			.then((res) => {
				if (!res.ok) throw new Error('Failed to fetch sidebar.html');
				return res.text();
			})
			.then((html) => {
				container.innerHTML = html;
				setupSidebarEvents(container);
			})
			.catch(() => {
				// Fallback to embedded template (works with local file:// protocol)
				container.innerHTML = SIDEBAR_TEMPLATE;
				setupSidebarEvents(container);
			});
	}

	if (document.readyState === 'loading') {
		document.addEventListener('DOMContentLoaded', initSidebar);
	} else {
		initSidebar();
	}
})();
