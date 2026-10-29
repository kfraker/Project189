/* Page lifecycle: how a page starts up and cleans up after itself.

   Each page script calls registerPage(name, init) once. init(page) sets the page up
   and gets a page context:
     page.name       the page's name
     page.signal     pass to addEventListener(type, fn, { signal: page.signal }) and the
                     listener is removed automatically when the page is left
     page.onLeave(fn)
                     anything else to undo on leave (charts, observers, timers);
                     these run newest first
     page.fetch      fetch() for the page's own requests: if the page has been left by
                     the time the answer (or its body) arrives, the page's follow-up
                     code never runs, so it can't write into the next page. The request
                     itself still completes, so a save sent just before leaving is kept.

   The shell (header, footer, menus) loads once and never registers here. With full page
   loads the browser wipes everything anyway; with in-page navigation, whatever a page
   leaves behind would pile up, so every page must clean up through its context.

   Shared functions and values a page puts on window (window.refreshChart, …) are removed
   when it is left, so the shell can't call into a page that is gone. App-wide names
   (APP_WIDE below: everything shell.js puts on window, plus loaded libraries) are kept.

   appRouter.remount() leaves the current page and starts it again in place: the tests
   use it to prove a page leaves nothing behind.

   In-page navigation: a click on a header page link fetches that page and swaps in only
   what changes (the [data-region] parts, its <style data-page-style> and its script),
   then starts it. The shell stays as it is, so the cursor and menus are never rebuilt.
   Back/Forward swap pages the same way. The latest click wins, and clicking the page
   you're on does nothing. The page's parts fade out while the next page downloads and
   fade back in once it's swapped in; backgrounds cross-fade once the new one has loaded
   (all instant with reduced motion). Anything unexpected falls back to a normal full
   page load. */
(function () {
    const APP_WIDE = new Set([
        // shell.js
        'savePref', 'activeUnit', 'activeModal', 'loadScriptOnce', 'showAppConfirm', 'openExclusive',
        'openFightCard', 'openInsights', 'openSettings', 'setProfilePic', 'applyCursorSet',
        '__returnToMenu', '__consumeReturnToMenu',
        // router.js
        'registerPage', 'appRouter',
        // libraries loaded with loadScriptOnce stay loaded
        'Chart',
    ]);
    const pages = {};        // name → init
    const scriptPages = {};  // page script URL → page name, once that script has run
    let awaitedScript = null; // set while navigating: the only page script allowed to start
    let current = null;      // { name, leave }

    function start(name) {
        const controller = new AbortController();
        const cleanups = [];
        const globalsBefore = new Set(Object.keys(window));
        // Settles like p, unless the page has been left by then: then never settles.
        const untilLeft = p => p.then(
            value => controller.signal.aborted ? new Promise(() => {}) : value,
            error => controller.signal.aborted ? new Promise(() => {}) : Promise.reject(error));
        const page = {
            name,
            signal: controller.signal,
            onLeave(fn) { cleanups.push(fn); },
            fetch(...args) {
                return untilLeft(window.fetch(...args)).then(res => {
                    for (const read of ['json', 'text', 'blob']) {
                        const original = res[read].bind(res);
                        res[read] = () => untilLeft(original());
                    }
                    return res;
                });
            },
        };
        current = {
            name,
            leave() {
                controller.abort();
                while (cleanups.length) {
                    const fn = cleanups.pop();
                    try { fn(); } catch (err) { console.error('Page "' + name + '" cleanup failed:', err); }
                }
                for (const key of Object.keys(window)) {
                    if (globalsBefore.has(key) || APP_WIDE.has(key)) continue;
                    if (!delete window[key])
                        console.error('Page "' + name + '" left window.' + key + ' behind (declared with var or function at the top level?)');
                }
            },
        };
        pages[name](page);
    }

    function leave() {
        if (!current) return;
        const leaving = current;
        current = null;
        leaving.leave();
    }

    window.registerPage = function (name, init) {
        pages[name] = init;
        const src = document.currentScript && document.currentScript.src;
        if (src) scriptPages[src] = name;
        // A page script that finishes loading after a newer click has moved on
        // registers, but must not take over the page that click showed.
        if (src && awaitedScript && src !== awaitedScript) return;
        leave();
        start(name);
    };

    /* ── In-page navigation ── */
    const NAV_LINKS = '.site-nav[aria-label="Pages"] a[href]';
    const pathOf = url => { const u = new URL(url, location.href); return u.pathname + u.search; };
    let shownPath = pathOf(location.href);   // the page on screen (ignores #fragments)
    let latestNav = 0;                       // each navigation's number; only the latest may finish

    function loadPageScript(src) {
        return new Promise((resolve, reject) => {
            const el = document.createElement('script');
            el.src = src;
            el.dataset.pageScript = '';
            el.onload = resolve;
            el.onerror = () => reject(new Error('Could not load ' + src));
            document.body.appendChild(el);
        });
    }

    /* Fade (styles in base.html): out takes FADE_MS, in takes FADE_MS. */
    const FADE_MS = 125;
    const root = document.documentElement;
    const motionOK = () => !matchMedia('(prefers-reduced-motion: reduce)').matches;
    let fadeDone = null;
    function fadeOut() {
        clearTimeout(fadeDone);
        root.classList.add('page-fading', 'page-leaving');
        return new Promise(resolve => setTimeout(resolve, motionOK() ? FADE_MS : 0));
    }
    function fadeIn() {
        void document.body.offsetHeight;    // new parts render hidden first, so they fade in
        root.classList.remove('page-leaving');
        fadeDone = setTimeout(() => root.classList.remove('page-fading'), motionOK() ? FADE_MS : 0);
    }

    /* Background cross-fade. The old background's look comes from its page style, which
       is about to be swapped out, so it's copied ("frozen") onto a ghost element in the
       shell, laid over the new background, and faded out once the new image is ready. */
    const BG_FADE_MS = 250, BG_WAIT_MAX_MS = 2000;
    const BG_LOOK = ['backgroundImage', 'backgroundColor', 'backgroundSize', 'backgroundPosition', 'backgroundRepeat'];

    function freezeBackground() {
        const region = document.querySelector('[data-region="bg"]');
        const old = region && region.firstElementChild;
        if (!old) return null;
        const ghost = document.createElement('div'), tint = document.createElement('div');
        const copy = (to, pseudo) => { const look = getComputedStyle(old, pseudo); for (const p of BG_LOOK) to.style[p] = look[p]; };
        copy(ghost);
        copy(tint, '::after');
        ghost.className = 'bg-ghost';
        ghost.appendChild(tint);
        region.after(ghost);
        return ghost;
    }

    // The new page's background image, read from its page style (null if it has none).
    function backgroundUrlOf(next, pageUrl) {
        const bg = next.querySelector('[data-region="bg"] > [class]');
        if (!bg) return null;
        const css = [...next.querySelectorAll('style[data-page-style]')].map(el => el.textContent).join('\n');
        const rule = css.match(new RegExp('\\.' + bg.classList[0] + '\\s*\\{[^}]*url\\([\'"]?([^\'")]+)'));
        return rule ? new URL(rule[1], pageUrl).href : null;
    }

    function whenImageReady(url) {
        if (!url) return Promise.resolve();
        const img = new Image();
        img.src = url;
        const loaded = img.decode().catch(() => {});        // a broken image mustn't hold things up
        return Promise.race([loaded, new Promise(resolve => setTimeout(resolve, BG_WAIT_MAX_MS))]);
    }

    function fadeAwayGhost(ghost, ready) {
        if (!ghost) return;
        ready.then(() => {
            void ghost.offsetHeight;
            ghost.style.opacity = '0';
            setTimeout(() => ghost.remove(), motionOK() ? BG_FADE_MS : 0);
        });
    }

    // push: false for Back/Forward, where the browser has already moved in its history.
    async function navigate(url, { push = true } = {}) {
        const nav = ++latestNav;
        const overtaken = () => nav !== latestNav;
        const fadedOut = fadeOut();             // runs while the page downloads
        try {
            const res = await fetch(url);
            if (overtaken()) return;
            // Redirected = e.g. signed out and sent to the login page, which isn't an app page.
            if (!res.ok || res.redirected) throw new Error('Not an app page: ' + url);
            const html = await res.text();
            if (overtaken()) return;
            const next = new DOMParser().parseFromString(html, 'text/html');
            const regions = [...document.querySelectorAll('[data-region]')].map(el =>
                [el, next.querySelector('[data-region="' + el.dataset.region + '"]')]);
            const script = next.querySelector('script[data-page-script]');
            if (!script || regions.some(([, incoming]) => !incoming)) throw new Error('Not an app page: ' + url);
            const scriptSrc = new URL(script.getAttribute('src'), res.url).href;
            const backgroundReady = whenImageReady(backgroundUrlOf(next, res.url));   // starts downloading now
            await fadedOut;
            if (overtaken()) return;

            awaitedScript = scriptSrc;
            const ghost = freezeBackground();
            leave();
            for (const [el, incoming] of regions)
                el.replaceChildren(...[...incoming.childNodes].map(node => document.adoptNode(node)));
            document.querySelectorAll('style[data-page-style]').forEach(el => el.remove());
            next.querySelectorAll('style[data-page-style]').forEach(el => document.head.appendChild(document.adoptNode(el)));

            // Address bar, tab title and highlighted nav button, as the server rendered them.
            if (push) history.pushState(null, '', res.url);
            shownPath = pathOf(res.url);
            document.title = next.title;
            for (const link of document.querySelectorAll(NAV_LINKS)) {
                const twin = next.querySelector(NAV_LINKS.replace('a[href]', 'a[href="' + link.getAttribute('href') + '"]'));
                if (twin) link.className = twin.className;
            }

            fadeIn();
            fadeAwayGhost(ghost, backgroundReady);

            // Keyboard and screen-reader users land at the new page's content (a full page
            // load does this by itself): focus moves off the nav link, and the page is named.
            document.getElementById('main-content').focus({ preventScroll: true });
            const activeLink = document.querySelector(NAV_LINKS + '.active');
            if (activeLink && typeof announce === 'function') announce(activeLink.getAttribute('aria-label') + ' page');

            // A page script runs once; coming back to that page just starts it again.
            if (scriptPages[scriptSrc]) start(scriptPages[scriptSrc]);
            else await loadPageScript(scriptSrc);
        } catch (err) {
            if (overtaken()) return;          // a newer click has taken over anyway
            console.warn('In-page navigation failed, loading the page normally:', err);
            if (push) location.assign(url);
            else location.replace(url);        // don't add a second entry for this page
        }
    }

    window.addEventListener('popstate', () => {
        if (pathOf(location.href) === shownPath) return;   // only the #fragment changed
        navigate(location.href, { push: false });
    });

    document.addEventListener('click', e => {
        const link = e.target.closest('a[href]');
        if (!link || !link.matches(NAV_LINKS)) return;
        if (e.defaultPrevented || e.button !== 0 || e.metaKey || e.ctrlKey || e.shiftKey || e.altKey) return;
        if (new URL(link.href).origin !== location.origin) return;
        e.preventDefault();
        if (pathOf(link.href) === shownPath) {   // already here: cancel a pending click, if any
            if (root.classList.contains('page-leaving')) { latestNav++; fadeIn(); }
            return;
        }
        navigate(link.href);
    });

    window.appRouter = {
        get current() { return current ? current.name : null; },
        leave,
        navigate,
        remount() {
            if (!current) return false;
            const name = current.name;
            leave();
            start(name);
            return true;
        },
    };
})();
