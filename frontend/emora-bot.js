/**
 * Emora Living Page Water Waves & Companion AI Bot
 * - Waves and water physics applied to top-left & bottom-right corners of viewport
 * - Small, elegant, non-intrusive wave sizes with gentle ripples
 * - Responsive to ANY emotion user expresses (e.g. angry, bad/sad, stressed, tired, happy, anxious, calm, etc.)
 * - Smooth "High Tide" transition swelling the corner waters and morphing colors to match the user's emotion
 */
(function() {
	if (window.__EMORA_BOT_INITIALIZED__) return;
	window.__EMORA_BOT_INITIALIZED__ = true;

	const API_BASE = (window.DCSION3_CONFIG && window.DCSION3_CONFIG.API_BASE_URL) || '';

	// =========================================================================
	// EXPANDED EMOTION COLOR PALETTES
	// Tailored for natural emotional expression and harmonious aesthetic
	// =========================================================================
	const EMOTION_PALETTES = {
		// 1. Anger / Frustration / Irritation
		angry: {
			name: "Fiery Crimson",
			status: "Sensing Anger & Frustration",
			primary: [220, 38, 38],       // #DC2626 (Fiery Red)
			secondary: [153, 27, 27],     // #991B1B (Deep Burn)
			accent: [254, 202, 202],      // #FECACA (Soft Heat Mist)
			glow: "rgba(220, 38, 38, 0.35)"
		},
		// 2. Sadness / Feeling Bad / Down / Melancholy
		bad: {
			name: "Rainy Slate Blue",
			status: "Sensing Low Mood & Sadness",
			primary: [71, 85, 105],       // #475569 (Rainy Slate Blue)
			secondary: [30, 41, 59],      // #1E293B (Storm Cloud)
			accent: [148, 163, 184],      // #94A3B8 (Soft Fog)
			glow: "rgba(71, 85, 105, 0.35)"
		},
		// 3. Stress / Burnout / Overwhelmed
		stressed: {
			name: "Terracotta Sunset",
			status: "Sensing High Stress & Overwhelm",
			primary: [217, 122, 83],      // #D97A53 (Emora Alert Terracotta)
			secondary: [154, 76, 44],     // #9A4C2C (Deep Rust)
			accent: [251, 146, 60],       // #FB923C (Amber Spark)
			glow: "rgba(217, 122, 83, 0.35)"
		},
		// 4. Anxiety / Fear / Nervousness
		anxious: {
			name: "Uneasy Indigo",
			status: "Sensing Anxiety & Tension",
			primary: [79, 70, 229],       // #4F46E5 (Electric Indigo)
			secondary: [49, 46, 129],     // #312E81 (Deep Night)
			accent: [165, 180, 252],      // #A5B4FC (Tense Electric Foam)
			glow: "rgba(79, 70, 229, 0.35)"
		},
		// 5. Fatigue / Tired / Exhausted / Low Battery
		tired: {
			name: "Twilight Lavender",
			status: "Sensing Fatigue & Low Energy",
			primary: [139, 92, 246],      // #8B5CF6 (Twilight Purple)
			secondary: [91, 33, 182],     // #5B21B6 (Deep Violet)
			accent: [221, 214, 254],      // #DDD6FE (Lavender Dream)
			glow: "rgba(139, 92, 246, 0.35)"
		},
		// 6. Joy / Happy / Great / Motivated / Energized
		happy: {
			name: "Sunlit Golden Amber",
			status: "Sensing Joy & Positive Energy",
			primary: [245, 158, 11],      // #F59E0B (Golden Amber)
			secondary: [180, 83, 9],      // #B45309 (Warm Ochre)
			accent: [254, 240, 138],      // #FEF08A (Sunlit Foam)
			glow: "rgba(245, 158, 11, 0.35)"
		},
		// 7. Calm / Serene / Relaxed / Content (Default Baseline)
		calm: {
			name: "Warm Emora Orange",
			status: "Tranquil & Balanced",
			primary: [243, 123, 50],       // #F37B32 (Signature Emora Orange)
			secondary: [217, 101, 30],     // #D9651E (Warm Amber Shade)
			accent: [255, 234, 219],      // #FFEADB (Soft Peach Foam)
			glow: "rgba(243, 123, 50, 0.35)"
		},
		// 8. Lonely / Isolated / Empty
		lonely: {
			name: "Cold Fog Teal",
			status: "Sensing Loneliness",
			primary: [13, 148, 136],      // #0D9488 (Cold Ocean Teal)
			secondary: [17, 94, 89],      // #115E59 (Deep Deep Ocean)
			accent: [153, 246, 228],      // #99F6E4 (Pale Aqua)
			glow: "rgba(13, 148, 136, 0.35)"
		},
		// 9. Love / Grateful / Hopeful
		grateful: {
			name: "Warm Rose Blush",
			status: "Sensing Gratitude & Warmth",
			primary: [236, 72, 153],      // #EC4899 (Warm Rose)
			secondary: [157, 23, 77],     // #9D174D (Deep Magenta)
			accent: [251, 207, 232],      // #FBCFE8 (Blush Foam)
			glow: "rgba(236, 72, 153, 0.35)"
		}
	};

	// Comprehensive Natural Sentiment & Keyword Detector
	function detectEmotionFromText(text) {
		const t = text.toLowerCase();

		// 1. Anger / Rage / Annoyance
		if (/\b(angry|mad|furious|pissed|rage|irritat|annoy|hate|agitated|livid|frustrat|cross)\b/.test(t)) {
			return 'angry';
		}
		// 2. Anxiety / Fear / Panic / Worry
		if (/\b(anxious|anxiety|nervous|worry|worried|scared|fear|afraid|panic|freak|tense|dread)\b/.test(t)) {
			return 'anxious';
		}
		// 3. Stress / Burnout / Overwhelm
		if (/\b(stress|stressed|overwhelm|burnout|burnt out|burned out|swamped|pressure|hectic|too much)\b/.test(t)) {
			return 'stressed';
		}
		// 4. Sadness / Bad / Low / Crying
		if (/\b(bad|sad|down|unhappy|terrible|awful|crying|cry|depressed|depression|horrible|hopeless|hurt|gloomy|miserable|heartbroken|poorly|not good)\b/.test(t)) {
			return 'bad';
		}
		// 5. Fatigue / Tired / Sleepy
		if (/\b(tired|exhausted|sleepy|fatigue|drained|drowsy|no energy|weary|sleepless|need sleep|sleep deprivation)\b/.test(t)) {
			return 'tired';
		}
		// 6. Lonely / Isolated
		if (/\b(lonely|alone|isolated|empty|abandoned|nobody|disconnected)\b/.test(t)) {
			return 'lonely';
		}
		// 7. Love / Grateful / Hopeful
		if (/\b(love|loved|grateful|thankful|hopeful|blessed|warmth|appreciat)\b/.test(t)) {
			return 'grateful';
		}
		// 8. Happy / Joy / Great / Excited
		if (/\b(good|great|happy|energized|excited|awesome|wonderful|amazing|cheerful|motivated|fantastic|well|refreshed|super|pumped|yay)\b/.test(t)) {
			return 'happy';
		}
		// 9. Calm / Peace / Balanced
		if (/\b(calm|peace|peaceful|relax|relaxed|serene|chill|balanced|content|fine|okay|ok)\b/.test(t)) {
			return 'calm';
		}

		return 'calm';
	}

	// =========================================================================
	// SMALL, ELEGANT CORNER WATER WAVE ENGINE
	// =========================================================================
	class CompactWaveEngine {
		constructor() {
			this.currentPalette = { ...EMOTION_PALETTES.calm };
			this.targetPalette = { ...EMOTION_PALETTES.calm };
			this.colorLerpRate = 0.05;

			// Corner wave dimension scale (Compact & subtle!)
			this.tideScale = 1.0;            // 1.0 = resting small corner, 1.45 = high tide
			this.targetTideScale = 1.0;
			this.tideLerpRate = 0.04;

			this.waveSpeed = 0.024;
			this.targetWaveSpeed = 0.024;
			this.phase = 0;

			this.isHighTide = false;
			this.highTideTimer = null;

			this.canvas = null;
			this.ctx = null;
			this.surgeOverlay = null;
		}

		init() {
			let surge = document.getElementById('emoraPageTideSurge');
			if (!surge) {
				surge = document.createElement('div');
				surge.className = 'emora-page-tide-surge';
				surge.id = 'emoraPageTideSurge';
				document.body.appendChild(surge);
			}
			this.surgeOverlay = surge;

			let c = document.getElementById('emoraPageWaveCanvas');
			if (!c) {
				c = document.createElement('canvas');
				c.className = 'emora-page-wave-canvas';
				c.id = 'emoraPageWaveCanvas';
				document.body.appendChild(c);
			}
			this.canvas = c;
			this.ctx = this.canvas.getContext('2d');

			this.resize();
			window.addEventListener('resize', () => this.resize());
			this.syncSiteTheme(true);
			this.startAnimationLoop();
		}

		resize() {
			if (this.canvas) {
				this.canvas.width = window.innerWidth;
				this.canvas.height = window.innerHeight;
			}
		}

		setEmotion(emotionKey, isDirectChat = true) {
			const target = EMOTION_PALETTES[emotionKey] || EMOTION_PALETTES.calm;
			this.targetPalette = target;

			if (isDirectChat) {
				this.triggerHighTide(target);
			}
		}

		triggerHighTide(targetPalette) {
			this.isHighTide = true;
			// Water flows up noticeably higher into High Tide!
			this.targetTideScale = 2.4;
			this.targetWaveSpeed = 0.046;

			if (this.surgeOverlay) this.surgeOverlay.classList.add('active');

			const tideBadge = document.getElementById('emoraTideBadge');
			if (tideBadge) {
				tideBadge.innerHTML = `🌊 High Tide &bull; ${targetPalette.name}`;
				tideBadge.style.background = `rgba(${targetPalette.primary.join(',')}, 0.22)`;
				tideBadge.style.color = `rgb(${targetPalette.primary.join(',')})`;
			}

			if (this.highTideTimer) clearTimeout(this.highTideTimer);

			// After done (reading feedback), high tide smoothly goes back down to resting level
			this.highTideTimer = setTimeout(() => {
				this.targetTideScale = 1.0;
				this.targetWaveSpeed = 0.024;
				this.isHighTide = false;

				if (this.surgeOverlay) this.surgeOverlay.classList.remove('active');
				if (tideBadge) {
					tideBadge.innerHTML = `🌊 ${targetPalette.name}`;
					tideBadge.style.background = `rgba(${targetPalette.primary.join(',')}, 0.12)`;
				}
			}, 3800);
		}

		lerpColor(current, target, rate) {
			return current.map((c, i) => Math.round(c + (target[i] - c) * rate));
		}

		updatePhysics() {
			this.phase += this.waveSpeed;
			this.waveSpeed += (this.targetWaveSpeed - this.waveSpeed) * 0.05;
			this.tideScale += (this.targetTideScale - this.tideScale) * this.tideLerpRate;

			this.currentPalette.primary = this.lerpColor(this.currentPalette.primary, this.targetPalette.primary, this.colorLerpRate);
			this.currentPalette.secondary = this.lerpColor(this.currentPalette.secondary, this.targetPalette.secondary, this.colorLerpRate);
			this.currentPalette.accent = this.lerpColor(this.currentPalette.accent, this.targetPalette.accent, this.colorLerpRate);

			this.syncSiteTheme();
		}

		syncSiteTheme(force = false) {
			const cp = this.currentPalette.primary;
			const cs = this.currentPalette.secondary;
			const ca = this.currentPalette.accent;

			const key = `${cp[0]},${cp[1]},${cp[2]}`;
			if (!force && this._lastThemeKey === key) return;
			this._lastThemeKey = key;

			const rootStyle = document.documentElement.style;

			// 1. Wave and bot tokens
			rootStyle.setProperty('--wave-color-primary', `${cp[0]}, ${cp[1]}, ${cp[2]}`);
			rootStyle.setProperty('--wave-color-secondary', `${cs[0]}, ${cs[1]}, ${cs[2]}`);
			rootStyle.setProperty('--wave-color-accent', `${ca[0]}, ${ca[1]}, ${ca[2]}`);
			rootStyle.setProperty('--wave-glow-color', `rgba(${cp[0]}, ${cp[1]}, ${cp[2]}, 0.35)`);

			// 2. Site Primary & Accent Colors (Timetable, Insights, Journal, Dashboard, Profile)
			const primaryRgb = `rgb(${cp[0]}, ${cp[1]}, ${cp[2]})`;
			const primaryDark = `rgb(${cs[0]}, ${cs[1]}, ${cs[2]})`;
			const primaryLight = `rgba(${cp[0]}, ${cp[1]}, ${cp[2]}, 0.12)`;
			const primarySoft = `rgba(${cp[0]}, ${cp[1]}, ${cp[2]}, 0.15)`;

			// Timetable & Insights & Journal variables
			rootStyle.setProperty('--primary-green', primaryRgb);
			rootStyle.setProperty('--primary-green-light', primaryLight);
			rootStyle.setProperty('--fixed-schedule', `rgba(${cp[0]}, ${cp[1]}, ${cp[2]}, 0.08)`);
			rootStyle.setProperty('--alert-orange', primaryDark);
			rootStyle.setProperty('--alert-bg', `rgba(${cp[0]}, ${cp[1]}, ${cp[2]}, 0.12)`);
			rootStyle.setProperty('--sidebar-bg', `linear-gradient(180deg, rgba(${cp[0]}, ${cp[1]}, ${cp[2]}, 0.05) 0%, #ffffff 100%)`);
			rootStyle.setProperty('--sidebar-line', `rgba(${cp[0]}, ${cp[1]}, ${cp[2]}, 0.15)`);

			// Index / Dashboard variables
			rootStyle.setProperty('--accent', primaryRgb);
			rootStyle.setProperty('--accent-strong', primaryDark);
			rootStyle.setProperty('--accent-soft', primarySoft);
			rootStyle.setProperty('--primary', primaryRgb);

			// Companion bot variables
			rootStyle.setProperty('--ebot-primary', primaryRgb);
			rootStyle.setProperty('--ebot-primary-dark', primaryDark);
			rootStyle.setProperty('--ebot-primary-light', primaryLight);
			rootStyle.setProperty('--ebot-primary-glow', `rgba(${cp[0]}, ${cp[1]}, ${cp[2]}, 0.35)`);
			rootStyle.setProperty('--ebot-accent', primaryRgb);
		}

		drawWaves() {
			if (!this.ctx || !this.canvas) return;
			const ctx = this.ctx;
			const w = this.canvas.width;
			const h = this.canvas.height;
			ctx.clearRect(0, 0, w, h);

			const pRgb = this.currentPalette.primary;
			const sRgb = this.currentPalette.secondary;
			const aRgb = this.currentPalette.accent;

			// Detect sidebar offset if present
			const sidebarEl = document.querySelector('.sidebar');
			let offsetX = 0;
			if (sidebarEl) {
				const sRect = sidebarEl.getBoundingClientRect();
				if (sRect.width > 0 && sRect.right > 0 && window.getComputedStyle(sidebarEl).position === 'fixed') {
					offsetX = sRect.right;
				}
			}

			// =================================================================
			// 1. TOP-LEFT WAVES (Clearly visible on top-left of screen & workspace)
			// =================================================================
			ctx.save();

			// 1A. Top-Left of Main Workspace (right next to sidebar at x: offsetX)
			const startX = offsetX;
			const tlW = (startX > 0 ? 170 : 160) * this.tideScale;
			const tlH = 100 * this.tideScale;
			const tlAmp = 5 + (this.tideScale - 1) * 3;

			// Back Wave (Workspace Top-Left)
			ctx.beginPath();
			ctx.moveTo(startX, 0);
			ctx.lineTo(startX + tlW, 0);
			for (let x = startX + tlW; x >= startX; x -= 8) {
				const prog = (startX + tlW - x) / tlW;
				const y = Math.sin((x - startX) * 0.04 + this.phase * 1.3) * tlAmp + (prog * tlH);
				ctx.lineTo(x, Math.max(0, y));
			}
			ctx.lineTo(startX, 0);
			ctx.closePath();
			ctx.fillStyle = `rgba(${sRgb[0]}, ${sRgb[1]}, ${sRgb[2]}, 0.24)`;
			ctx.fill();

			// Front Wave (Workspace Top-Left)
			ctx.beginPath();
			ctx.moveTo(startX, 0);
			const fTlW = tlW * 0.88;
			const fTlH = tlH * 0.88;
			ctx.lineTo(startX + fTlW, 0);
			for (let x = startX + fTlW; x >= startX; x -= 8) {
				const prog = (startX + fTlW - x) / fTlW;
				const y = Math.cos((x - startX) * 0.045 - this.phase * 1.5) * (tlAmp * 0.85) + (prog * fTlH);
				ctx.lineTo(x, Math.max(0, y));
			}
			ctx.lineTo(startX, 0);
			ctx.closePath();
			ctx.fillStyle = `rgba(${pRgb[0]}, ${pRgb[1]}, ${pRgb[2]}, 0.32)`;
			ctx.fill();

			// Foam Crest Line (Workspace Top-Left)
			ctx.beginPath();
			for (let x = startX + fTlW; x >= startX; x -= 8) {
				const prog = (startX + fTlW - x) / fTlW;
				const y = Math.cos((x - startX) * 0.045 - this.phase * 1.5) * (tlAmp * 0.85) + (prog * fTlH);
				if (x === startX + fTlW) ctx.moveTo(x, y);
				else ctx.lineTo(x, y);
			}
			ctx.strokeStyle = `rgba(${aRgb[0]}, ${aRgb[1]}, ${aRgb[2]}, 0.65)`;
			ctx.lineWidth = 2.2;
			ctx.stroke();

			ctx.restore();

			// =================================================================
			// 2. COMPACT BOTTOM-RIGHT CORNER WATER (Small, refined, gently flows up on high tide)
			// =================================================================
			const brW = 190 * this.tideScale;
			const brH = 150 * this.tideScale;
			const brAmp = 6 + (this.tideScale - 1) * 3.5;

			ctx.save();
			// Back Wave Layer
			ctx.beginPath();
			ctx.moveTo(w, h);
			ctx.lineTo(w - brW, h);
			for (let x = w - brW; x <= w; x += 8) {
				const prog = (x - (w - brW)) / brW;
				const curveY = h - (prog * brH) + Math.sin(x * 0.035 + this.phase) * brAmp;
				ctx.lineTo(x, curveY);
			}
			ctx.lineTo(w, h);
			ctx.closePath();
			ctx.fillStyle = `rgba(${sRgb[0]}, ${sRgb[1]}, ${sRgb[2]}, 0.24)`;
			ctx.fill();

			// Front Wave Layer
			ctx.beginPath();
			ctx.moveTo(w, h);
			const fBrW = brW * 0.88;
			const fBrH = brH * 0.88;
			ctx.lineTo(w - fBrW, h);
			for (let x = w - fBrW; x <= w; x += 8) {
				const prog = (x - (w - fBrW)) / fBrW;
				const curveY = h - (prog * fBrH) + Math.cos(x * 0.04 - this.phase * 1.2) * (brAmp * 0.85);
				ctx.lineTo(x, curveY);
			}
			ctx.lineTo(w, h);
			ctx.closePath();
			ctx.fillStyle = `rgba(${pRgb[0]}, ${pRgb[1]}, ${pRgb[2]}, 0.32)`;
			ctx.fill();

			// Foam Crest Line
			ctx.beginPath();
			for (let x = w - fBrW; x <= w; x += 8) {
				const prog = (x - (w - fBrW)) / fBrW;
				const curveY = h - (prog * fBrH) + Math.cos(x * 0.04 - this.phase * 1.2) * (brAmp * 0.85);
				if (x === w - fBrW) ctx.moveTo(x, curveY);
				else ctx.lineTo(x, curveY);
			}
			ctx.strokeStyle = `rgba(${aRgb[0]}, ${aRgb[1]}, ${aRgb[2]}, 0.65)`;
			ctx.lineWidth = 2.2;
			ctx.stroke();

			// Subtle gentle bubbles during high tide
			if (this.isHighTide) {
				for (let i = 0; i < 5; i++) {
					const prog = 0.35 + (i * 0.12);
					const bx = (w - fBrW) + prog * fBrW;
					const by = h - (prog * fBrH) - 10 - Math.sin(this.phase * 2 + i) * 12;
					ctx.beginPath();
					ctx.arc(bx, by, 2.5, 0, Math.PI * 2);
					ctx.fillStyle = `rgba(${aRgb[0]}, ${aRgb[1]}, ${aRgb[2]}, 0.6)`;
					ctx.fill();
				}
			}
			ctx.restore();
		}

		startAnimationLoop() {
			const loop = () => {
				this.updatePhysics();
				this.drawWaves();
				requestAnimationFrame(loop);
			};
			requestAnimationFrame(loop);
		}
	}

	const waveEngine = new CompactWaveEngine();

	// =========================================================================
	// CHAT & BOT WIDGET CONTROLLER
	// =========================================================================
	let botHistory = [];
	try {
		const stored = sessionStorage.getItem('emora_bot_history');
		if (stored) botHistory = JSON.parse(stored);
	} catch (e) {
		botHistory = [];
	}

	function saveHistory() {
		try {
			sessionStorage.setItem('emora_bot_history', JSON.stringify(botHistory.slice(-10)));
		} catch (e) {}
	}

	function formatBotText(text) {
		if (!text) return '';
		let sanitized = text
			.replace(/&/g, '&amp;')
			.replace(/</g, '&lt;')
			.replace(/>/g, '&gt;');
		sanitized = sanitized.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
		return sanitized.split('\n\n').map(p => `<p>${p.replace(/\n/g, '<br>')}</p>`).join('');
	}

	function getCurrentTimeLabel() {
		const now = new Date();
		let hours = now.getHours();
		const minutes = now.getMinutes().toString().padStart(2, '0');
		const ampm = hours >= 12 ? 'PM' : 'AM';
		hours = hours % 12 || 12;
		return `${hours}:${minutes} ${ampm}`;
	}

	function createBotWidget() {
		waveEngine.init();

		// Floating Launcher Button
		const launcher = document.createElement('div');
		launcher.className = 'emora-bot-launcher';
		launcher.id = 'emoraBotLauncher';
		launcher.innerHTML = `
			<button class="emora-bot-circle-btn" id="emoraBotBtn" aria-label="Open Emora AI Companion" title="Open Emora AI Companion" type="button">
				<span class="emora-bot-status-dot"></span>
				<div class="emora-bot-icon-chat">
					<svg viewBox="0 0 24 24"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"></path></svg>
				</div>
				<div class="emora-bot-icon-close">
					<svg viewBox="0 0 24 24"><line x1="18" y1="6" x2="6" y2="18"></line><line x1="6" y1="6" x2="18" y2="18"></line></svg>
				</div>
			</button>
			<div class="emora-bot-tooltip">Ask Emora AI</div>
		`;

		// Chat Popup Window
		const popup = document.createElement('div');
		popup.className = 'emora-bot-popup';
		popup.id = 'emoraBotPopup';
		popup.setAttribute('role', 'dialog');
		popup.setAttribute('aria-labelledby', 'emoraBotTitle');
		popup.innerHTML = `
			<div class="emora-bot-header">
				<div class="emora-bot-header-left">
					<div class="emora-bot-avatar">e</div>
					<div class="emora-bot-title-group">
						<div class="emora-bot-title" id="emoraBotTitle">
							<span>Emora AI</span>
							<span class="emora-tide-badge" id="emoraTideBadge">🌊 Warm Emora Orange</span>
						</div>
						<div class="emora-bot-status-tag">Emotion-Responsive Tide Companion</div>
					</div>
				</div>
				<div class="emora-bot-header-actions">
					<a href="ai.html" class="emora-bot-action-btn" title="Open Full AI Tab" aria-label="Open Full AI Tab">
						<svg viewBox="0 0 24 24"><path d="M15 3h6v6"></path><path d="M10 14L21 3"></path><path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"></path></svg>
					</a>
					<button class="emora-bot-action-btn" id="emoraBotCloseBtn" title="Minimize" aria-label="Minimize" type="button">
						<svg viewBox="0 0 24 24"><line x1="18" y1="6" x2="6" y2="18"></line><line x1="6" y1="6" x2="18" y2="18"></line></svg>
					</button>
				</div>
			</div>

			<div class="emora-bot-chips-bar">
				<button class="emora-bot-chip" data-query="I am really angry and frustrated right now!" type="button">😡 I'm angry</button>
				<button class="emora-bot-chip" data-query="ah today im feeling bad" type="button">🌧️ Feeling bad</button>
				<button class="emora-bot-chip" data-query="I feel completely exhausted and tired" type="button">🌙 Exhausted</button>
				<button class="emora-bot-chip" data-query="I am feeling great and happy!" type="button">☀️ Great &amp; Happy</button>
			</div>

			<div class="emora-bot-messages" id="emoraBotMessages"></div>

			<div class="emora-bot-footer">
				<form class="emora-bot-input-form" id="emoraBotForm">
					<input type="text" class="emora-bot-input" id="emoraBotInput" placeholder="Tell Emora how you feel (e.g. 'I'm angry', 'feeling bad')..." autocomplete="off" required />
					<button type="submit" class="emora-bot-send-btn" id="emoraBotSendBtn" aria-label="Send query">
						<svg viewBox="0 0 24 24"><line x1="22" y1="2" x2="11" y2="13"></line><polygon points="22 2 15 22 11 13 2 9 22 2"></polygon></svg>
					</button>
				</form>
			</div>
		`;

		document.body.appendChild(launcher);
		document.body.appendChild(popup);

		const btn = document.getElementById('emoraBotBtn');
		const closeBtn = document.getElementById('emoraBotCloseBtn');
		const messagesContainer = document.getElementById('emoraBotMessages');
		const form = document.getElementById('emoraBotForm');
		const input = document.getElementById('emoraBotInput');

		function renderInitialMessages() {
			messagesContainer.innerHTML = '';

			const welcomeMsg = document.createElement('div');
			welcomeMsg.className = 'emora-bot-msg bot';
			welcomeMsg.innerHTML = `
				<div class="emora-bot-msg-meta">Emora AI &bull; Ready</div>
				<div class="emora-bot-msg-bubble">
					<p>Hello! Share whatever you're feeling (e.g. <em>"I'm angry"</em>, <em>"feeling bad"</em>, <em>"stressed"</em>, <em>"tired"</em>, <em>"happy"</em>).</p>
					<p>The corner water waves will rise in High Tide and smoothly transit to the color of your emotion.</p>
				</div>
			`;
			messagesContainer.appendChild(welcomeMsg);

			botHistory.forEach(item => {
				appendMessage(item.role === 'user' ? 'user' : 'bot', item.content, false);
			});

			scrollMessagesToBottom();
		}

		function scrollMessagesToBottom() {
			messagesContainer.scrollTop = messagesContainer.scrollHeight;
		}

		function togglePopup(forceState) {
			const isOpen = popup.classList.contains('open');
			const shouldOpen = typeof forceState === 'boolean' ? forceState : !isOpen;

			if (shouldOpen) {
				popup.classList.add('open');
				launcher.classList.add('open');
				setTimeout(() => {
					input.focus();
					scrollMessagesToBottom();
				}, 150);
			} else {
				popup.classList.remove('open');
				launcher.classList.remove('open');
			}
		}

		btn.addEventListener('click', (e) => {
			e.stopPropagation();
			togglePopup();
		});

		closeBtn.addEventListener('click', (e) => {
			e.stopPropagation();
			togglePopup(false);
		});

		document.addEventListener('click', (e) => {
			if (popup.classList.contains('open') && !popup.contains(e.target) && !launcher.contains(e.target)) {
				togglePopup(false);
			}
		});

		popup.querySelectorAll('.emora-bot-chip').forEach(chip => {
			chip.addEventListener('click', (e) => {
				e.stopPropagation();
				const query = chip.dataset.query;
				if (query) {
					input.value = query;
					sendMessage(query);
				}
			});
		});

		function appendMessage(role, text, isMarkdown = true) {
			const msgDiv = document.createElement('div');
			msgDiv.className = `emora-bot-msg ${role}`;
			const name = role === 'user' ? 'You' : 'Emora AI';
			const content = isMarkdown ? formatBotText(text) : `<p>${text.replace(/</g, '&lt;').replace(/>/g, '&gt;')}</p>`;

			msgDiv.innerHTML = `
				<div class="emora-bot-msg-meta">${name} &bull; ${getCurrentTimeLabel()}</div>
				<div class="emora-bot-msg-bubble">${content}</div>
			`;
			messagesContainer.appendChild(msgDiv);
			scrollMessagesToBottom();
		}

		function showTypingIndicator() {
			const typing = document.createElement('div');
			typing.className = 'emora-bot-typing';
			typing.id = 'emoraBotTyping';
			typing.innerHTML = `
				<span class="emora-bot-dot"></span>
				<span class="emora-bot-dot"></span>
				<span class="emora-bot-dot"></span>
			`;
			messagesContainer.appendChild(typing);
			scrollMessagesToBottom();
			return typing;
		}

		async function sendMessage(text) {
			const trimmed = text.trim();
			if (!trimmed) return;

			input.value = '';

			// 1. USER INPUT: append user message to chat and history (NO wave change yet!)
			appendMessage('user', trimmed, false);
			botHistory.push({ role: 'user', content: trimmed });
			saveHistory();

			// 2. AI THINKING: show typing indicator (water remains in calm resting state)
			const typingIndicator = showTypingIndicator();

			try {
				const response = await fetch(`${API_BASE}/api/v1/ai/chat`, {
					method: 'POST',
					headers: { 'Content-Type': 'application/json' },
					body: JSON.stringify({
						message: trimmed,
						history: botHistory.slice(-8),
						include_context: true
					})
				});

				const data = await response.json();
				if (typingIndicator) typingIndicator.remove();

				const replyText = data.ok ? data.reply : (data.fallback_reply || data.error || 'Emora AI is temporarily unavailable.');

				// 3. AI OUTPUT: display feedback message
				appendMessage('bot', replyText, true);
				botHistory.push({ role: 'assistant', content: replyText });
				saveHistory();

				// 4. NOW TRIGGER TRANSITION: AI output arrived -> High tide flows up + color changes to user emotion!
				const detectedEmotion = (data && data.emotion && data.emotion.label) || detectEmotionFromText(trimmed);
				waveEngine.setEmotion(detectedEmotion, true);

			} catch (err) {
				if (typingIndicator) typingIndicator.remove();
				const fallback = "I hear you. Whatever you're going through, I'm here to help lighten your workload and make space for your wellbeing.";
				appendMessage('bot', fallback, false);

				// Even on fallback feedback: AI output arrived -> trigger high tide + color change
				const detectedEmotion = detectEmotionFromText(trimmed);
				waveEngine.setEmotion(detectedEmotion, true);
			}
		}

		form.addEventListener('submit', (e) => {
			e.preventDefault();
			const msg = input.value;
			sendMessage(msg);
		});

		renderInitialMessages();
	}

	if (document.readyState === 'loading') {
		document.addEventListener('DOMContentLoaded', createBotWidget);
	} else {
		createBotWidget();
	}
})();
