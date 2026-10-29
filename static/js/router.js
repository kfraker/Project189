/* Page lifecycle: how a page starts up and cleans up after itself.

   Each page script calls registerPage(name, init) once. init(page) sets the page up
   and gets a page context:
     page.name       the page's name
     page.signal     pass to addEventListener(type, fn, { signal: page.signal }) and the
                     listener is removed automatically when the page is left
     page.onLeave(fn)
                     anything else to undo on leave (charts, observers, timers);
                     these run newest first

   The shell (header, footer, menus) loads once and never registers here. With full page
   loads the browser wipes everything anyway; with in-page navigation, whatever a page
   leaves behind would pile up, so every page must clean up through its context.

   Shared functions and values a page puts on window (window.refreshChart, …) are removed
   when it is left, so the shell can't call into a page that is gone. App-wide names
   (APP_WIDE below: everything shell.js puts on window, plus loaded libraries) are kept.

   appRouter.remount() leaves the current page and starts it again in place: the tests
   use it to prove a page leaves nothing behind. */
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
    let current = null;      // { name, leave }

    function start(name) {
        const controller = new AbortController();
        const cleanups = [];
        const globalsBefore = new Set(Object.keys(window));
        const page = {
            name,
            signal: controller.signal,
            onLeave(fn) { cleanups.push(fn); },
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
        leave();
        start(name);
    };

    window.appRouter = {
        get current() { return current ? current.name : null; },
        leave,
        remount() {
            if (!current) return false;
            const name = current.name;
            leave();
            start(name);
            return true;
        },
    };
})();
