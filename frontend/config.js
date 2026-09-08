/**
 * DCSION3 - Central Environment & API Configuration
 *
 * Automatically resolves the backend API endpoint:
 * - In Native Mobile (Capacitor Android): Targets the live cloud backend.
 * - In Web Browser (Localhost / Vercel): Uses standard relative paths.
 */
(function() {
    const isNativeMobile = !!(
        window.Capacitor &&
        typeof window.Capacitor.isNativePlatform === 'function' &&
        window.Capacitor.isNativePlatform()
    );

    // Default cloud backend URL (can be updated with your live domain)
    const PRODUCTION_CLOUD_BACKEND = 'https://api.dcsion3.com';

    window.DCSION3_CONFIG = {
        IS_NATIVE: isNativeMobile,
        API_BASE_URL: isNativeMobile ? PRODUCTION_CLOUD_BACKEND : '',
        VERSION: '1.0.0',
        ENV: isNativeMobile ? 'production_mobile' : 'web'
    };
})();
