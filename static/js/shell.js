/* Shared app shell: cursor, modals, menu, settings, fight card, insights, profile. */

    /* ── savePref ── */
    window.savePref = function (key, value) {
        localStorage.setItem(key, value);
        fetch('/api/preference', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ key: key, value: value })
        });
    };

    if ('scrollRestoration' in history) history.scrollRestoration = 'manual';
    requestAnimationFrame(() => requestAnimationFrame(() => {
        document.body.classList.remove('preload');
    }));

    /* ── Load a third-party script on demand, once ──
       Pages that need a library (e.g. Chart.js on Weigh-ins) ask for it here instead of
       linking it in <head>, so other pages never download it and coming back to a page
       never loads it twice. Returns a promise that resolves once the script has run. */
    const loadedScripts = {};
    window.loadScriptOnce = function (src) {
        if (!loadedScripts[src]) {
            loadedScripts[src] = new Promise((resolve, reject) => {
                const el = document.createElement('script');
                el.src = src;
                el.onload = resolve;
                el.onerror = () => { delete loadedScripts[src]; reject(new Error('Could not load ' + src)); };
                document.head.appendChild(el);
            });
        }
        return loadedScripts[src];
    };

    /* ── Active unit ── */
    window.activeUnit = localStorage.getItem('pref_unit') || 'lbs';

    /* ── Shared helpers ── */
    function getTodayISO() {
        const d = new Date();
        return d.getFullYear() + '-' +
            String(d.getMonth() + 1).padStart(2, '0') + '-' +
            String(d.getDate()).padStart(2, '0');
    }

    function formatDateDisplay(isoDate) {
        const [y, m, d] = isoDate.split('-').map(Number);
        const dt = new Date(y, m - 1, d);
        const mon = dt.toLocaleDateString('en-US', { month: 'long' });
        return (localStorage.getItem('pref_date_format') || 'mdy') === 'mdy'
            ? mon + ' ' + d + ', ' + y : d + ' ' + mon + ' ' + y;
    }

    function formatDateShort(isoDate) {
        const [y, m, d] = isoDate.split('-').map(Number);
        const dt = new Date(y, m - 1, d);
        const mon = dt.toLocaleDateString('en-US', { month: 'short' });
        return (localStorage.getItem('pref_date_format') || 'mdy') === 'mdy'
            ? mon + ' ' + d : d + ' ' + mon;
    }

    function fmtDateShort(dt) {
        const mon = dt.toLocaleDateString('en-US', { month: 'short' });
        const y = dt.getFullYear(), d = dt.getDate();
        return (localStorage.getItem('pref_date_format') || 'mdy') === 'mdy'
            ? mon + ' ' + d + ', ' + y
            : d + ' ' + mon + ' ' + y;
    }

    function fmtLbs(n) { return n === Math.round(n) ? Math.round(n) : parseFloat(n.toFixed(1)); }

    /* ── Custom cursor: DOM element follows the mouse (rAF-throttled) so it
       never gets clipped/suppressed near viewport edges the way a native
       CSS cursor: url() does, and still works over scrollbars. ── */
    (function () {
        const el = document.getElementById('site-cursor');

        /* Pre-baked images (white background already transparent, 2x res) —
           no per-page canvas processing, so the cursor is usable immediately.
           [src, hotX, hotY] with the hotspot in display px (88x48 render), then
           the same for the open-hand cursor shown over editable things (117x64). */
        const CURSOR_W = 88, CURSOR_H = 48, EDIT_W = 117, EDIT_H = 64;
        const CURSOR_SETS = {
            '1': ['/static/cursor-pointer.png',  15, 1, '/static/cursor-edit.png',  55, 3],
            '2': ['/static/cursor-pointer2.png', 17, 1, '/static/cursor-edit2.png', 53, 3],
            '3': ['/static/cursor-pointer3.png', 17, 1, '/static/cursor-edit3.png', 53, 3],
            '4': ['/static/cursor-pointer4.png', 17, 1, '/static/cursor-edit4.png', 53, 3],
        };
        const EDITABLE = '#start-plate, #current-plate, #goal-plate, .note-resize-handle';
        let active = CURSOR_SETS[localStorage.getItem('pref_profile_pic')] || CURSOR_SETS['1'];
        let lastMX = 0, lastMY = 0, mouseInDoc = false, rafPending = false, editing = false;

        function applyCursor() {
            el.style.width = (editing ? EDIT_W : CURSOR_W) + 'px';
            el.style.height = (editing ? EDIT_H : CURSOR_H) + 'px';
            el.style.backgroundImage = `url(${active[editing ? 3 : 0]})`;
        }
        function place() {
            const hotX = active[editing ? 4 : 1], hotY = active[editing ? 5 : 2];
            el.style.transform = `translate3d(${lastMX - hotX}px, ${lastMY - hotY}px, 0)`;
        }
        applyCursor();
        Object.values(CURSOR_SETS).forEach(set => { new Image().src = set[3]; });   // no blank frame on the first swap

        function setEditing(target) {
            const next = !!(target && target.closest && target.closest(EDITABLE));
            if (next === editing) return;
            editing = next;
            applyCursor();
            place();
        }
        document.addEventListener('mouseover', e => setEditing(e.target));
        /* A click can open a modal or swap the page under a mouse that hasn't moved. */
        document.addEventListener('click', () => {
            setTimeout(() => setEditing(document.elementFromPoint(lastMX, lastMY)), 0);
        });

        window.applyCursorSet = function(n) {
            active = CURSOR_SETS[String(n)] || active;
            applyCursor();
            place();
        };

        /* A refresh or direct link is a full page load (nav clicks aren't: see
           router.js), and mouseenter/mousemove don't fire until the mouse
           physically moves, so the cursor would vanish until then. Carry the
           last position across the load instead. */
        try {
            const saved = JSON.parse(sessionStorage.getItem('cursor_pos'));
            if (saved) {
                lastMX = saved.x; lastMY = saved.y; mouseInDoc = true;
                place();
                el.style.display = 'block';
            }
        } catch (e) {}
        window.addEventListener('pagehide', () => {
            try {
                if (mouseInDoc) sessionStorage.setItem('cursor_pos', JSON.stringify({ x: lastMX, y: lastMY }));
                else sessionStorage.removeItem('cursor_pos');
            } catch (e) {}
        });

        /* A tap also fires browser-made mouse events; ignore those so touchscreens
           never show the cursor, while a touchscreen laptop's real mouse still does. */
        let lastTouch = 0;
        function fromTouch() { return Date.now() - lastTouch < 1000; }
        ['touchstart', 'touchend'].forEach(type => document.addEventListener(type, () => {
            lastTouch = Date.now();
            mouseInDoc = false;
            el.style.display = 'none';
        }, { capture: true, passive: true }));

        document.addEventListener('mousemove', e => {
            if (fromTouch()) return;
            lastMX = e.clientX; lastMY = e.clientY;
            if (!mouseInDoc) { mouseInDoc = true; el.style.display = 'block'; }
            if (rafPending) return;
            rafPending = true;
            requestAnimationFrame(() => { rafPending = false; place(); });
        });

        document.addEventListener('mouseleave', () => { mouseInDoc = false; el.style.display = 'none'; });
        document.addEventListener('mouseenter', () => { if (fromTouch()) return; mouseInDoc = true; el.style.display = 'block'; });
    })();

    /* ── Accessibility: toggle-group roles + aria-pressed sync ── */
    (function () {
        document.querySelectorAll('.profile-setting-group, .overlay-item').forEach((container, i) => {
            const lbl = container.querySelector('.profile-setting-label');
            const row = container.querySelector('.profile-toggle-row');
            if (!lbl || !row) return;
            if (!lbl.id) lbl.id = 'ptlbl-' + i;
            row.setAttribute('role', 'group');
            row.setAttribute('aria-labelledby', lbl.id);
        });
        const sexMale = document.getElementById('fight-sex-male');
        if (sexMale) {
            const sexRow = sexMale.closest('.profile-toggle-row');
            if (sexRow) { sexRow.setAttribute('role', 'group'); sexRow.setAttribute('aria-label', 'Sex'); }
        }
        const ftEl = document.getElementById('fight-height-ft');
        const inEl = document.getElementById('fight-height-in');
        const cmEl = document.getElementById('fight-height-cm');
        if (ftEl) ftEl.setAttribute('aria-label', 'Feet');
        if (inEl) inEl.setAttribute('aria-label', 'Inches');
        if (cmEl) cmEl.setAttribute('aria-label', 'Centimeters');
        const pressedBtns = document.querySelectorAll('.profile-opt-btn, .range-btn, .weekly-range-btn');
        pressedBtns.forEach(btn => btn.setAttribute('aria-pressed', String(btn.classList.contains('active'))));
        const obs = new MutationObserver(muts => {
            muts.forEach(m => {
                const btn = m.target;
                if (btn.hasAttribute('aria-pressed'))
                    btn.setAttribute('aria-pressed', String(btn.classList.contains('active')));
            });
        });
        pressedBtns.forEach(btn => obs.observe(btn, { attributes: true, attributeFilter: ['class'] }));
    })();

    /* ── Hide the chart's data tooltip on scroll ── */
    document.addEventListener('wheel', () => {
        const ct = document.getElementById('chart-tooltip');
        if (ct) ct.style.opacity = '0';
    }, { passive: true });

    /* ── Streak temperature glow (shared across all pages) ── */
    const STREAK_STOPS = [
        [ 60, 120, 255],
        [100, 175, 255],
        [155, 215, 255],
        [255, 245, 110],
        [255, 225,  40],
        [255, 155,  30],
        [255,  90,  30],
        [255,  60,  60],
    ];
    function applyStreakGlow(numEl, labelEl, val) {
        numEl.classList.remove('streak-flame-num');
        if (labelEl) labelEl.classList.remove('streak-flame-label');
        if (val >= 7) {
            numEl.style.color = ''; numEl.style.textShadow = '';
            numEl.classList.add('streak-flame-num');
            if (labelEl) { labelEl.style.color = ''; labelEl.style.textShadow = ''; labelEl.classList.add('streak-flame-label'); }
        } else {
            const [r, g, b] = STREAK_STOPS[Math.min(Math.max(Math.round(val), 0), 7)];
            const color = `rgb(${r},${g},${b})`, fade = `rgba(${r},${g},${b},0.35)`;
            numEl.style.color = color;
            numEl.style.textShadow = `0 0 6px ${color}, 0 0 18px ${color}, 0 0 36px ${fade}`;
            if (labelEl) { labelEl.style.color = color; labelEl.style.textShadow = `0 0 5px ${color}, 0 0 14px ${fade}`; }
        }
    }

    /* ── Modal infrastructure ── */
    function makeFocusTrap(card) {
        return function(e) {
            if (e.key !== 'Tab') return;
            const focusable = [...card.querySelectorAll(
                'button:not([disabled]), [href], input:not([disabled]), select, textarea, [tabindex]:not([tabindex="-1"])'
            )].filter(el => !el.closest('[hidden]') && el.offsetParent !== null);
            if (!focusable.length) return;
            const first = focusable[0], last = focusable[focusable.length - 1];
            if (e.shiftKey && document.activeElement === first) { e.preventDefault(); last.focus(); }
            else if (!e.shiftKey && document.activeElement === last) { e.preventDefault(); first.focus(); }
        };
    }
    const _modalOpeners = new WeakMap(), _modalTraps = new WeakMap();
    function modalOpen(overlay) {
        _modalOpeners.set(overlay, document.activeElement);
        const card = overlay.querySelector('[role="dialog"]') || overlay;
        const trap = makeFocusTrap(card);
        _modalTraps.set(overlay, trap);
        overlay.addEventListener('keydown', trap);
    }
    function modalClose(overlay) {
        const trap = _modalTraps.get(overlay);
        if (trap) overlay.removeEventListener('keydown', trap);
        const opener = _modalOpeners.get(overlay);
        if (opener && opener.focus) opener.focus();
    }
    function announce(msg) {
        const el = document.getElementById('status-announce');
        if (el) { el.textContent = ''; requestAnimationFrame(() => { el.textContent = msg; }); }
    }

    /* ── App-wide confirm modal ── */
    /* onCancel/cancelLabel are optional: e.g. the "Unsaved Changes" prompts turn the
       second button into "Close" (discard + close) instead of a plain Cancel. */
    window.showAppConfirm = function(title, message, okLabel, onOk, onCancel, cancelLabel) {
        const modal = document.getElementById('app-confirm-modal');
        document.getElementById('app-confirm-title').textContent  = title;
        document.getElementById('app-confirm-msg').textContent    = message;
        document.getElementById('app-confirm-ok').textContent     = okLabel || 'Confirm';
        document.getElementById('app-confirm-cancel').textContent = cancelLabel || 'Cancel';
        modal.hidden = false;
        document.getElementById('app-confirm-ok').onclick    = () => { modal.hidden = true; if (onOk) onOk(); };
        document.getElementById('app-confirm-cancel').onclick = () => { modal.hidden = true; if (onCancel) onCancel(); };
    };

    /* ── Modal coordinator ── */
    window.activeModal = null;
    window.openExclusive = function(openFn) {
        if (window.activeModal) { window.activeModal.tryClose(openFn); } else { openFn(); }
    };

    /* Set by the Menu modal before launching Insights/Profile/Settings so those
       modals return to the Menu on close instead of dropping back to the page. */
    window.__returnToMenu = null;
    window.__consumeReturnToMenu = function() {
        if (window.__returnToMenu) { const fn = window.__returnToMenu; window.__returnToMenu = null; fn(); }
    };

    /* ── Scroll lock while any modal is open ── */
    window.addEventListener('wheel', function (e) {
        const activeOverlay = document.querySelector('.modal-overlay:not([hidden])');
        if (!activeOverlay) return;
        e.preventDefault();
        const scrollEl = activeOverlay.querySelector('.settings-scroll-body');
        if (scrollEl) scrollEl.scrollTop += e.deltaY;
    }, { passive: false, capture: true });

    /* ── Profile button → fight card modal ── */
    (() => {
        const btn       = document.getElementById('profile-btn');
        const modal     = document.getElementById('fight-card-modal');
        const saveBtn   = document.getElementById('fight-card-save');
        const cancelBtn = document.getElementById('fight-card-cancel');
        const dobIn     = document.getElementById('fight-dob');
        const ageNumEl  = document.getElementById('fight-age-num');
        const ftIn      = document.getElementById('fight-height-ft');
        const inIn      = document.getElementById('fight-height-in');
        const cmIn      = document.getElementById('fight-height-cm');
        const usRow     = document.getElementById('fight-height-us-row');
        const metRow    = document.getElementById('fight-height-metric-row');
        const preview   = document.getElementById('fight-height-preview');
        const nameIn    = document.getElementById('fight-name');
        const sexMaleBtn    = document.getElementById('fight-sex-male');
        const sexFemaleBtn  = document.getElementById('fight-sex-female');
        const actBtns       = document.querySelectorAll('.fight-activity-row .profile-opt-btn');
        const goalLeanBtn   = document.getElementById('fight-goal-lean');
        const goalMuscleBtn = document.getElementById('fight-goal-muscle');

        const calEl    = document.getElementById('fight-dob-calendar');
        const gridEl   = document.getElementById('fight-dp-grid');
        const monthLbl = document.getElementById('fight-dp-month-label');
        const dayNames = calEl.querySelector('.dp-day-names');
        const MONTHS   = ['January','February','March','April','May','June','July','August','September','October','November','December'];
        let viewDate = new Date(), selectedDobISO = '', calMode = 'days', yearPage = new Date().getFullYear() - 35;

        function isoFromParts(y, m, d) { return y + '-' + String(m + 1).padStart(2,'0') + '-' + String(d).padStart(2,'0'); }
        function displayFromISO(iso) { const [y,m,d] = iso.split('-'); return MONTHS[parseInt(m)-1] + ' ' + parseInt(d) + ', ' + y; }
        function calcAge(dobISO) {
            const [y,m,d] = dobISO.split('-').map(Number), t = new Date();
            let age = t.getFullYear() - y;
            if (t.getMonth()+1 < m || (t.getMonth()+1 === m && t.getDate() < d)) age--;
            return age;
        }
        function updateAgeDisplay() { ageNumEl.textContent = selectedDobISO ? calcAge(selectedDobISO) : '—'; }

        function renderDobCalendar() {
            calMode = 'days'; dayNames.style.display = ''; gridEl.style.gridTemplateColumns = 'repeat(7, 1fr)';
            const today = getTodayISO(), todayD = new Date();
            const minDate = isoFromParts(todayD.getFullYear()-100, todayD.getMonth(), todayD.getDate());
            const y = viewDate.getFullYear(), m = viewDate.getMonth();
            monthLbl.textContent = MONTHS[m] + ' ' + y;
            const firstDow = new Date(y,m,1).getDay(), daysInMonth = new Date(y,m+1,0).getDate(), daysInPrev = new Date(y,m,0).getDate();
            gridEl.innerHTML = '';
            for (let i = firstDow-1; i >= 0; i--) { const b = document.createElement('button'); b.type='button'; b.className='dp-day dp-other-month'; b.textContent=daysInPrev-i; b.disabled=true; gridEl.appendChild(b); }
            for (let day = 1; day <= daysInMonth; day++) {
                const iso = isoFromParts(y, m, day), b = document.createElement('button');
                b.type='button'; b.className='dp-day'; b.textContent=day;
                if (iso===selectedDobISO) b.classList.add('dp-selected');
                if (iso > today || iso < minDate) { b.disabled=true; } else {
                    b.addEventListener('click', () => { selectedDobISO=iso; dobIn.value=displayFromISO(iso); updateAgeDisplay(); calEl.hidden=true; });
                }
                gridEl.appendChild(b);
            }
            const rem = (firstDow+daysInMonth)%7;
            if (rem>0) for (let i=1;i<=7-rem;i++) { const b=document.createElement('button'); b.type='button'; b.className='dp-day dp-other-month'; b.textContent=i; b.disabled=true; gridEl.appendChild(b); }
        }

        function renderDobYearGrid() {
            calMode='years'; dayNames.style.display='none'; gridEl.style.gridTemplateColumns='repeat(3, 1fr)';
            const todayY=new Date().getFullYear(), minY=todayY-100, curY=viewDate.getFullYear();
            monthLbl.textContent=yearPage+' – '+(yearPage+11); gridEl.innerHTML='';
            for (let i=0;i<12;i++) {
                const yr=yearPage+i, b=document.createElement('button');
                b.type='button'; b.className='dp-day dp-year'; b.textContent=yr;
                if (yr===curY) b.classList.add('dp-selected');
                if (yr>todayY||yr<minY) { b.disabled=true; } else {
                    b.addEventListener('click',()=>{ viewDate=new Date(yr,viewDate.getMonth(),1); renderDobCalendar(); });
                }
                gridEl.appendChild(b);
            }
        }

        monthLbl.addEventListener('click', () => { if (calMode==='days') { yearPage=viewDate.getFullYear()-5; renderDobYearGrid(); } else renderDobCalendar(); });
        dobIn.addEventListener('click', () => {
            if (calEl.hidden) {
                viewDate = selectedDobISO ? new Date(selectedDobISO+'T12:00:00') : new Date(new Date().getFullYear()-30, new Date().getMonth(), 1);
                renderDobCalendar(); calEl.hidden=false;
            } else calEl.hidden=true;
        });
        document.getElementById('fight-dp-prev').addEventListener('click', () => {
            if (calMode==='years') { yearPage-=12; renderDobYearGrid(); }
            else { viewDate=new Date(viewDate.getFullYear(),viewDate.getMonth()-1,1); renderDobCalendar(); }
        });
        document.getElementById('fight-dp-next').addEventListener('click', () => {
            if (calMode==='years') { yearPage+=12; renderDobYearGrid(); }
            else { viewDate=new Date(viewDate.getFullYear(),viewDate.getMonth()+1,1); renderDobCalendar(); }
        });
        document.addEventListener('click', e => { const wrap=document.getElementById('fight-dob-wrap'); if (!calEl.hidden && !e.composedPath().includes(wrap)) calEl.hidden=true; });

        let openState = null;
        function heightUnit() { return localStorage.getItem('pref_height_unit') || 'us'; }
        function getSelectedSex() { return sexMaleBtn.classList.contains('active') ? 'male' : sexFemaleBtn.classList.contains('active') ? 'female' : ''; }
        function getSelectedActivity() { for (const b of actBtns) if (b.classList.contains('active')) return b.dataset.activity; return ''; }
        function getSelectedGoal() { return goalMuscleBtn.classList.contains('active') ? 'muscle' : 'lean'; }

        function snapshot() {
            return { name:nameIn.value, dob:selectedDobISO, ft:ftIn.value, inch:inIn.value, cm:cmIn.value, sex:getSelectedSex(), activity:getSelectedActivity(), goal:getSelectedGoal() };
        }
        function hasChanges() {
            if (!openState) return false;
            const s = snapshot();
            return s.name!==openState.name||s.dob!==openState.dob||s.ft!==openState.ft||s.inch!==openState.inch||s.cm!==openState.cm||s.sex!==openState.sex||s.activity!==openState.activity||s.goal!==openState.goal;
        }

        function updatePreview() {
            if (heightUnit()==='us') {
                const ft=parseInt(ftIn.value), i=parseInt(inIn.value)||0;
                preview.textContent = (!isNaN(ft)&&ft>0) ? Math.round((ft*30.48)+(i*2.54))+' cm' : '';
            } else {
                const cm=parseInt(cmIn.value)||0;
                preview.textContent = cm>0 ? Math.floor(cm/2.54/12)+' ft '+Math.round((cm/2.54)%12)+' in' : '';
            }
        }

        function forceClose() { modal.hidden=true; calEl.hidden=true; openState=null; window.activeModal=null; modalClose(modal); window.__consumeReturnToMenu(); }

        function tryClose(onClosed) {
            if (hasChanges()) {
                window.showAppConfirm('Unsaved Changes','Close without saving?','Save & Close',
                    () => { doSave(); if (onClosed) onClosed(); },
                    () => { forceClose(); if (onClosed) onClosed(); }, 'Close');
            } else { forceClose(); if (onClosed) onClosed(); }
        }

        function doSave() {
            window.savePref('fight_name', nameIn.value.trim());
            if (window.updateHealthBarName) window.updateHealthBarName();
            if (selectedDobISO) window.savePref('fight_dob', selectedDobISO);
            const sex = getSelectedSex(); if (sex) window.savePref('fight_sex', sex);
            const act = getSelectedActivity(); if (act) window.savePref('fight_activity', act);
            window.savePref('fight_goal_mode', getSelectedGoal());
            if (window.updateLostWeight) window.updateLostWeight();
            if (heightUnit()==='us') {
                if (ftIn.value) window.savePref('fight_height_ft', ftIn.value);
                if (inIn.value!=='') window.savePref('fight_height_in', inIn.value);
            } else {
                if (cmIn.value!=='') window.savePref('fight_height_cm', cmIn.value);
            }
            forceClose();
        }

        function openFightCard() {
            const isUs = heightUnit()==='us';
            usRow.style.display=isUs?'':'none'; metRow.style.display=isUs?'none':'';
            const storedDob=localStorage.getItem('fight_dob')||'';
            selectedDobISO=storedDob; dobIn.value=storedDob?displayFromISO(storedDob):'';
            updateAgeDisplay(); calEl.hidden=true;
            nameIn.value=localStorage.getItem('fight_name')||'';
            const storedSex=localStorage.getItem('fight_sex')||'';
            sexMaleBtn.classList.toggle('active',storedSex==='male');
            sexFemaleBtn.classList.toggle('active',storedSex==='female');
            const storedAct=localStorage.getItem('fight_activity')||'';
            actBtns.forEach(b=>b.classList.toggle('active',b.dataset.activity===storedAct));
            const storedGoal=localStorage.getItem('fight_goal_mode')||'lean';
            goalLeanBtn.classList.toggle('active',storedGoal==='lean');
            goalMuscleBtn.classList.toggle('active',storedGoal==='muscle');
            if (isUs) {
                ftIn.value=localStorage.getItem('fight_height_ft')||'';
                inIn.value=localStorage.getItem('fight_height_in')||'';
                if (!ftIn.value) {
                    const sc=parseFloat(localStorage.getItem('fight_height_cm'));
                    if (!isNaN(sc)&&sc>0) { const ti=sc/2.54; ftIn.value=Math.floor(ti/12); inIn.value=Math.round(ti%12); }
                }
            } else {
                cmIn.value=localStorage.getItem('fight_height_cm')||'';
                if (!cmIn.value) {
                    const sf=parseFloat(localStorage.getItem('fight_height_ft')), si=parseFloat(localStorage.getItem('fight_height_in'))||0;
                    if (!isNaN(sf)&&sf>0) cmIn.value=Math.round((sf*30.48)+(si*2.54));
                }
            }
            updatePreview(); modal.hidden=false; modalOpen(modal);
            openState=snapshot(); window.activeModal={tryClose};
        }

        window.openFightCard = openFightCard;

        /* Profile button: image swap on hover, open menu modal on click */
        const PICS = {
            '1': ['profilebutton.png','profilebuttonsmile.png'],
            '2': ['profile2button.png','profile2buttonsmile.png'],
            '3': ['profile3button.png','profile3buttonsmile.png'],
            '4': ['profile4button.png','profile4buttonsmile.png'],
        };
        function bases() { return PICS[localStorage.getItem('pref_profile_pic')||'1']||PICS['1']; }
        const profImg = document.getElementById('profile-btn-img');
        profImg.src = '/static/' + bases()[0];
        btn.addEventListener('mouseenter', () => { profImg.src='/static/'+bases()[1]; });
        btn.addEventListener('mouseleave', () => { profImg.src='/static/'+bases()[0]; });
        btn.addEventListener('click', () => {
            const mm = document.getElementById('menu-modal');
            if (mm) { mm.hidden = false; modalOpen(mm); }
        });

        window.setProfilePic = function(n) {
            window.savePref('pref_profile_pic', String(n));
            profImg.src = '/static/' + bases()[0];
            if (window.applyCursorSet) window.applyCursorSet(n);
        };

        [sexMaleBtn,sexFemaleBtn].forEach(b => b.addEventListener('click',()=>{ sexMaleBtn.classList.remove('active'); sexFemaleBtn.classList.remove('active'); b.classList.add('active'); }));
        actBtns.forEach(b => b.addEventListener('click',()=>{ actBtns.forEach(x=>x.classList.remove('active')); b.classList.add('active'); }));
        [goalLeanBtn,goalMuscleBtn].forEach(b => b.addEventListener('click',()=>{ goalLeanBtn.classList.remove('active'); goalMuscleBtn.classList.remove('active'); b.classList.add('active'); }));
        ftIn.addEventListener('input',updatePreview); inIn.addEventListener('input',updatePreview); cmIn.addEventListener('input',updatePreview);
        saveBtn.addEventListener('click',doSave); cancelBtn.addEventListener('click',()=>tryClose());
        modal.addEventListener('click',e=>{if(e.target===modal)tryClose();});
        document.addEventListener('keydown',e=>{ if(e.key==='Escape'){if(!calEl.hidden){calEl.hidden=true;return;}if(!modal.hidden)tryClose();}});
    })();

    /* ── Menu modal ── */
    (() => {
        const modal      = document.getElementById('menu-modal');
        const closeBtn   = document.getElementById('menu-modal-close');
        const insightsBtn = document.getElementById('menu-insights-btn');
        const profileBtn = document.getElementById('menu-profile-btn');
        const settingsBtn = document.getElementById('menu-settings-btn');
        const logoutBtn = document.getElementById('menu-logout-btn');

        function close() { modal.hidden = true; modalClose(modal); }
        function reopenMenu() { modal.hidden = false; modalOpen(modal); }

        closeBtn.addEventListener('click', close);
        modal.addEventListener('click', e => { if (e.target === modal) close(); });
        document.addEventListener('keydown', e => { if (e.key === 'Escape' && !modal.hidden) close(); });

        insightsBtn.addEventListener('click', () => {
            close();
            window.__returnToMenu = reopenMenu;
            if (window.openInsights) window.openExclusive(window.openInsights);
        });
        profileBtn.addEventListener('click', () => {
            close();
            window.__returnToMenu = reopenMenu;
            if (window.openFightCard) window.openExclusive(window.openFightCard);
        });
        settingsBtn.addEventListener('click', () => {
            close();
            window.__returnToMenu = reopenMenu;
            if (window.openSettings) window.openSettings();
        });
        logoutBtn.addEventListener('click', () => {
            window.location.href = '/logout';
        });
    })();

    /* ── Profile pic picker ── */
    (() => {
        const picker    = document.getElementById('profile-pic-picker');
        const backdrop  = document.getElementById('profile-pic-backdrop');
        const openBtn   = document.getElementById('change-pic-btn');
        const saveBtn   = document.getElementById('pic-save-btn');
        const cancelBtn = document.getElementById('pic-cancel-btn');
        const options   = picker.querySelectorAll('.pic-option');
        let pending = null, saved = null;
        const PICS = { '1':['profilebutton.png','profilebuttonsmile.png'],'2':['profile2button.png','profile2buttonsmile.png'],'3':['profile3button.png','profile3buttonsmile.png'],'4':['profile4button.png','profile4buttonsmile.png'] };

        function showPicker() {
            saved=localStorage.getItem('pref_profile_pic')||'1'; pending=saved;
            options.forEach(opt=>opt.classList.toggle('active',opt.dataset.pic===pending));
            backdrop.hidden=false; picker.hidden=false;
        }
        function forceClose() { picker.hidden=true; backdrop.hidden=true; pending=null; saved=null; }
        function tryClose() {
            if (pending!==saved) {
                picker.hidden=true; backdrop.hidden=true;
                window.showAppConfirm('Unsaved Changes','Close without saving your profile pic?','Save & Close',
                    ()=>{if(pending)window.setProfilePic(pending);forceClose();},()=>{forceClose();},'Close');
            } else forceClose();
        }

        openBtn.addEventListener('click', showPicker);
        options.forEach(opt => {
            const img=opt.querySelector('img'), pics=PICS[opt.dataset.pic];
            opt.addEventListener('mouseenter',()=>{img.src='/static/'+pics[1];});
            opt.addEventListener('mouseleave',()=>{img.src='/static/'+pics[0];});
            opt.addEventListener('click',()=>{ pending=opt.dataset.pic; options.forEach(o=>o.classList.toggle('active',o.dataset.pic===pending)); });
        });
        saveBtn.addEventListener('click',()=>{if(pending)window.setProfilePic(pending);forceClose();});
        cancelBtn.addEventListener('click',tryClose);
        backdrop.addEventListener('click',tryClose);
    })();

    /* ── Insights modal ── */
    (() => {
        const modal    = document.getElementById('insights-modal');
        const grid     = document.getElementById('insights-grid');
        const closeBtn = document.getElementById('insights-close');

        const DAY_NAMES = ['Sunday','Monday','Tuesday','Wednesday','Thursday','Friday','Saturday'];
        function isKg() { return (localStorage.getItem('pref_unit')||'lbs')==='kg'; }
        function fmt(v)  { return isKg()?v.toFixed(1)+' kg':v.toFixed(1)+' lbs'; }
        function fmtR(v) { return isKg()?v.toFixed(2)+' kg':v.toFixed(2)+' lbs'; }
        function fmtRate(v) { return (v>=0?'−':'+') + fmtR(Math.abs(v)); }

        async function compute() {
            const [rows, settings] = await Promise.all([
                fetch('/api/weights?range=all').then(r=>r.json()),
                fetch('/api/settings').then(r=>r.json())
            ]);
            if (!rows.length) return null;
            const kg=isKg(), weights=rows.map(r=>kg?r.weight_kg:r.weight_lbs), dates=rows.map(r=>new Date(r.date+'T00:00:00')), n=rows.length;
            const tN=Math.min(7,n), trend=weights.slice(-tN).reduce((a,b)=>a+b,0)/tN;
            const spanDays=(dates[n-1]-dates[0])/86400000, totalLoss=weights[0]-weights[n-1];
            const weeklyRate=spanDays>=7?(totalLoss/spanDays)*7:null, monthlyRate=spanDays>=30?(totalLoss/spanDays)*30.44:null;
            const dayCounts=Array(7).fill(0); dates.forEach(d=>dayCounts[d.getDay()]++);
            const topDay=DAY_NAMES[dayCounts.indexOf(Math.max(...dayCounts))];
            let longest=1,curS=1;
            for (let i=1;i<n;i++) { if((dates[i]-dates[i-1])/86400000===1){curS++;if(curS>longest)longest=curS;}else curS=1; }
            let curStreak=0; const today=new Date(); today.setHours(0,0,0,0);
            if ((today-dates[n-1])/86400000<=1) { curStreak=1; for(let i=n-1;i>0;i--){if((dates[i]-dates[i-1])/86400000===1)curStreak++;else break;} }
            const total=n, lowest=Math.min(...weights);
            let bestWeek=0;
            for (let i=0;i<n;i++) { const cutoff=dates[i].getTime()+7*86400000; for(let j=i+1;j<n&&dates[j].getTime()<=cutoff;j++){const loss=weights[i]-weights[j];if(loss>bestWeek)bestWeek=loss;} }
            let totalFluc=0,flucCount=0;
            for (let i=1;i<n;i++){const d=(dates[i]-dates[i-1])/86400000;if(d>=1&&d<=3){totalFluc+=Math.abs(weights[i]-weights[i-1])/d;flucCount++;}}
            const avgFluc=flucCount?totalFluc/flucCount:0;
            function getHeightCm(){const cm=parseFloat(localStorage.getItem('fight_height_cm')||'0')||0;if(cm>0)return cm;const ft=parseInt(localStorage.getItem('fight_height_ft')||'0')||0,ins=parseInt(localStorage.getItem('fight_height_in')||'0')||0;return ft>0?(ft*12+ins)*2.54:0;}
            function msJeorBMR(wKg,hCm,age,sex){return 10*wKg+6.25*hCm-5*age+(sex==='male'?5:-161);}
            function calcAgeMSJ(dobISO){const[y,m,d]=dobISO.split('-').map(Number),t=new Date();let a=t.getFullYear()-y;if(t.getMonth()+1<m||(t.getMonth()+1===m&&t.getDate()<d))a--;return a;}
            let goalDateStr='No goal set',goalDateSub='at current rate';
            const gw=settings['goal_weight'];
            if (gw){
                const curW_kg=rows[n-1].weight_kg,goalW_kg=gw.value_kg,curW_disp=weights[n-1],goalW_disp=kg?goalW_kg:gw.value_lbs;
                if(curW_disp<=goalW_disp){goalDateStr='Goal reached!';goalDateSub='congrats!';}
                else{
                    const sex=localStorage.getItem('fight_sex')||'',dob=localStorage.getItem('fight_dob')||'',activityStored=parseFloat(localStorage.getItem('fight_activity')||'0')||0,activity=activityStored>0?activityStored:1.4,noActEst=activityStored<=0,hCm=getHeightCm(),canBMR=!!(sex&&dob&&hCm>0);
                    if(canBMR){
                        const age0=calcAgeMSJ(dob),bmr0=msJeorBMR(curW_kg,hCm,age0,sex),tdee0=bmr0*activity;
                        let dailyDeficit,noRateEst=false;
                        if(weeklyRate&&weeklyRate>0){const weeklyKg=kg?weeklyRate:weeklyRate/2.2046;dailyDeficit=Math.min(weeklyKg*7700/7,tdee0*0.85);}else{dailyDeficit=500;noRateEst=true;}
                        const dailyIntake=tdee0-dailyDeficit;let simW=curW_kg;const simD=new Date(dates[n-1]);let weeks=0,plateau=false;
                        while(simW>goalW_kg&&weeks<520){const deficit=msJeorBMR(simW,hCm,age0,sex)*activity-dailyIntake;if(deficit<=0){plateau=true;break;}simW-=(deficit*7)/7700;simD.setDate(simD.getDate()+7);weeks++;}
                        if(plateau){goalDateStr='Plateau ahead';goalDateSub='adjust intake to continue';}
                        else if(weeks>=520){goalDateStr='10+ years';goalDateSub='Mifflin-St. Jeor';}
                        else{goalDateStr=fmtDateShort(simD);const msjLabel=noActEst?'MSJ · 1.4× activity est.':'Mifflin-St. Jeor';goalDateSub=noRateEst?'MSJ · 500 kcal/day deficit est.':msjLabel;}
                    }else if(weeklyRate&&weeklyRate>0){const daysLeft=((curW_disp-goalW_disp)/weeklyRate)*7;const g=new Date(dates[n-1]);g.setDate(g.getDate()+Math.round(daysLeft));goalDateStr=fmtDateShort(g);goalDateSub='linear (complete Fight Card)';}
                    else goalDateStr='Need more data';
                }
            }
            return [
                {label:'Predicted Goal Date',value:goalDateStr,sub:goalDateSub,wide:true},
                {label:'Total Weigh-ins',value:String(total),sub:'all time'},
                {label:'Longest Streak',value:String(longest),sub:longest===1?'day':'consecutive days'},
                {label:'Current Streak',value:String(curStreak),sub:curStreak?(curStreak===1?'day and counting':'consecutive days and counting'):'inactive'},
                {label:'Current Trend',value:fmt(trend),sub:'last 7 entries'},
                {label:'Weekly Loss Rate',value:weeklyRate!=null?fmtRate(weeklyRate)+'/wk':'—',sub:'avg over history'},
                {label:'Monthly Loss Rate',value:monthlyRate!=null?fmtRate(monthlyRate)+'/mo':'—',sub:'avg over history'},
                {label:'Lowest Weight',value:fmt(lowest),sub:'all time'},
                {label:'Largest Weekly Loss',value:bestWeek>0?fmtR(bestWeek):'—',sub:'best 7-day window'},
                {label:'Avg Daily Fluctuation',value:avgFluc>0?fmtR(avgFluc)+'/day':'—',sub:'day-to-day noise'},
            ];
        }

        function render(stats) {
            grid.innerHTML='';
            if(!stats){const msg=document.createElement('p');msg.style.cssText='color:rgba(255,200,220,0.5);text-align:center;grid-column:1/-1;padding:32px 0;margin:0';msg.textContent='No weight data yet.';grid.appendChild(msg);return;}
            stats.forEach(s=>{const card=document.createElement('div');card.className='insight-card'+(s.wide?' insight-card-wide':'');card.innerHTML='<div class="insight-label">'+s.label+'</div><div class="insight-value">'+s.value+'</div><div class="insight-sub">'+s.sub+'</div>';grid.appendChild(card);});
        }
        function close() { modal.hidden=true; window.activeModal=null; modalClose(modal); window.__consumeReturnToMenu(); }
        async function openInsights() {
            window.activeModal={tryClose:cb=>{close();if(cb)cb();}};
            grid.innerHTML='<p style="color:rgba(255,200,220,0.4);text-align:center;grid-column:1/-1;padding:32px 0;margin:0">Loading…</p>';
            modal.hidden=false; modalOpen(modal); render(await compute());
        }
        window.openInsights = openInsights;
        closeBtn.addEventListener('click',close);
        modal.addEventListener('click',e=>{if(e.target===modal)close();});
        document.addEventListener('keydown',e=>{if(e.key==='Escape'&&!modal.hidden)close();});
    })();

    /* ── Settings modal ── */
    (() => {
        const modal       = document.getElementById('settings-modal');
        const saveBtn     = document.getElementById('settings-save');
        const cancelBtn   = document.getElementById('settings-cancel');

        const profCustomDays  = document.getElementById('prof-custom-days');
        const profCustomWeeks = document.getElementById('prof-custom-weeks-setting');
        const profCustomWorkoutsDays = document.getElementById('prof-wp-custom-days');
        let openState = null;

        function getSelections() {
            const landing = document.getElementById('prof-landing-table-weekly').classList.contains('active') ? 'table-weekly'
                          : document.getElementById('prof-landing-table-daily').classList.contains('active')  ? 'table-daily'
                          : document.getElementById('prof-landing-weekly').classList.contains('active')        ? 'weekly' : 'daily';
            return {
                unit:       document.getElementById('prof-kg-btn').classList.contains('active')?'kg':'lbs',
                range:      document.querySelector('.profile-opt-btn[data-range].active')?.dataset.range||'7d',
                customDays: profCustomDays.value,
                weeklyRange:   document.querySelector('.profile-opt-btn[data-weeks].active')?.dataset.weeks||'4',
                customWeeks:   profCustomWeeks.value,
                workoutsRange: document.querySelector('.profile-opt-btn[data-wp-range].active')?.dataset.wpRange||'7d',
                customWorkoutsDays: profCustomWorkoutsDays.value,
                defaultLanding: landing,
                heightUnit: document.getElementById('prof-height-metric').classList.contains('active')?'metric':'us',
                goalLine:        document.getElementById('prof-goal-line-on').classList.contains('active')?'1':'0',
                maLine:          document.getElementById('prof-ma-line-on').classList.contains('active')?'1':'0',
                trendLine:       document.getElementById('prof-trend-line-on').classList.contains('active')?'1':'0',
                chartType:       document.getElementById('prof-chart-interp').classList.contains('active')?'interpolated':document.getElementById('prof-chart-actual').classList.contains('active')?'actual':document.getElementById('prof-chart-dots').classList.contains('active')?'dots-only':'no-data',
                weeklyGoalLine:  document.getElementById('prof-weekly-goal-on').classList.contains('active')?'1':'0',
                weeklyTrendLine: document.getElementById('prof-weekly-trend-on').classList.contains('active')?'1':'0',
                weeklyMinMax:    document.getElementById('prof-weekly-minmax-on').classList.contains('active')?'1':'0',
                weeklyMode:      document.getElementById('prof-weekly-mode-iso').classList.contains('active')?'iso':'rolling',
                legend:          document.getElementById('prof-legend-on').classList.contains('active')?'1':'0',
                weeklyLegend:    document.getElementById('prof-weekly-legend-on').classList.contains('active')?'1':'0',
                healthBar:       document.getElementById('prof-healthbar-on').classList.contains('active')?'1':'0',
                fighterName:     document.getElementById('prof-fighter-name-on').classList.contains('active')?'1':'0',
                dateFormat:      document.getElementById('prof-date-dmy').classList.contains('active')?'dmy':'mdy',
                weeklyTableExpanded: document.getElementById('prof-weekly-table-exp-on').classList.contains('active')
            };
        }

        function hasChanges() {
            if (!openState) return false;
            const cur = getSelections();
            return cur.unit!==openState.unit||cur.range!==openState.range||cur.customDays!==openState.customDays||cur.weeklyRange!==openState.weeklyRange||cur.customWeeks!==openState.customWeeks||cur.workoutsRange!==openState.workoutsRange||cur.customWorkoutsDays!==openState.customWorkoutsDays||cur.defaultLanding!==openState.defaultLanding||cur.heightUnit!==openState.heightUnit||cur.goalLine!==openState.goalLine||cur.maLine!==openState.maLine||cur.trendLine!==openState.trendLine||cur.chartType!==openState.chartType||cur.weeklyGoalLine!==openState.weeklyGoalLine||cur.weeklyTrendLine!==openState.weeklyTrendLine||cur.weeklyMinMax!==openState.weeklyMinMax||cur.weeklyMode!==openState.weeklyMode||cur.legend!==openState.legend||cur.weeklyLegend!==openState.weeklyLegend||cur.healthBar!==openState.healthBar||cur.fighterName!==openState.fighterName||cur.dateFormat!==openState.dateFormat;
        }

        function forceClose() { modal.hidden=true; openState=null; window.activeModal=null; modalClose(modal); window.__consumeReturnToMenu(); }
        function tryClose(onClosed) {
            if (hasChanges()) {
                window.showAppConfirm('Unsaved Changes','Close without saving your settings?','Save & Close',()=>{doSave();if(onClosed)onClosed();},()=>{forceClose();if(onClosed)onClosed();},'Close');
            } else { forceClose(); if(onClosed)onClosed(); }
        }

        function openModal() {
            const curUnit=localStorage.getItem('pref_unit')||'lbs';
            const _cs=window.getChartRange?window.getChartRange():null, curRange=(_cs&&_cs.range)||localStorage.getItem('pref_range')||'7d', curCustomDays=localStorage.getItem('pref_custom_days')||'';
            const _ws=window.getWeeklyChartRange?window.getWeeklyChartRange():null, curWeeklyRange=(_ws&&_ws.range)||localStorage.getItem('pref_weekly_range')||'4';
            const curCustomWeeks=(_ws&&_ws.range==='custom'&&_ws.weeks)?String(_ws.weeks):(localStorage.getItem('pref_custom_weeks')||'');
            const curWorkoutsRange=localStorage.getItem('pref_workouts_range')||'7d', curCustomWorkoutsDays=localStorage.getItem('pref_workouts_custom_days')||'';
            const curDefaultLanding=localStorage.getItem('pref_default_landing')||'daily', curHeightUnit=localStorage.getItem('pref_height_unit')||'us';
            const curGoalLine=localStorage.getItem('pref_goal_line')||'0', curMaLine=localStorage.getItem('pref_ma_line')||'1', curTrendLine=localStorage.getItem('pref_trend_line')||'0';
            const curChartType=localStorage.getItem('pref_chart_type')||'interpolated', curHealthBar=localStorage.getItem('pref_healthbar')||'1', curFighterName=localStorage.getItem('pref_fighter_name')||'1';
            const curWeeklyMinMax=localStorage.getItem('pref_weekly_minmax')||'1', curWeeklyGoalLine=localStorage.getItem('pref_weekly_goal_line')||'0', curWeeklyTrendLine=localStorage.getItem('pref_weekly_trend_line')||'0';
            const curWeeklyTableExpanded=localStorage.getItem('pref_weekly_table_expanded')==='true', curWeeklyMode=localStorage.getItem('pref_weekly_mode')||'rolling';
            const curLegend=localStorage.getItem('pref_legend')||'1', curWeeklyLegend=localStorage.getItem('pref_weekly_legend')||'1', curDateFormat=localStorage.getItem('pref_date_format')||'mdy';

            document.getElementById('prof-lbs-btn').classList.toggle('active',curUnit==='lbs');
            document.getElementById('prof-kg-btn').classList.toggle('active',curUnit==='kg');
            document.getElementById('prof-landing-daily').classList.toggle('active',curDefaultLanding==='daily');
            document.getElementById('prof-landing-weekly').classList.toggle('active',curDefaultLanding==='weekly');
            document.getElementById('prof-landing-table-daily').classList.toggle('active',curDefaultLanding==='table-daily');
            document.getElementById('prof-landing-table-weekly').classList.toggle('active',curDefaultLanding==='table-weekly');
            document.getElementById('prof-height-us').classList.toggle('active',curHeightUnit==='us');
            document.getElementById('prof-height-metric').classList.toggle('active',curHeightUnit==='metric');
            document.getElementById('prof-goal-line-on').classList.toggle('active',curGoalLine==='1');
            document.getElementById('prof-goal-line-off').classList.toggle('active',curGoalLine!=='1');
            document.getElementById('prof-ma-line-on').classList.toggle('active',curMaLine==='1');
            document.getElementById('prof-ma-line-off').classList.toggle('active',curMaLine!=='1');
            document.getElementById('prof-trend-line-on').classList.toggle('active',curTrendLine==='1');
            document.getElementById('prof-trend-line-off').classList.toggle('active',curTrendLine!=='1');
            document.getElementById('prof-chart-interp').classList.toggle('active',curChartType==='interpolated');
            document.getElementById('prof-chart-actual').classList.toggle('active',curChartType==='actual');
            document.getElementById('prof-chart-dots').classList.toggle('active',curChartType==='dots-only');
            document.getElementById('prof-chart-none').classList.toggle('active',curChartType==='no-data');
            document.getElementById('prof-healthbar-on').classList.toggle('active',curHealthBar!=='0');
            document.getElementById('prof-healthbar-off').classList.toggle('active',curHealthBar==='0');
            document.getElementById('prof-fighter-name-on').classList.toggle('active',curFighterName!=='0');
            document.getElementById('prof-fighter-name-off').classList.toggle('active',curFighterName==='0');
            document.getElementById('prof-weekly-minmax-on').classList.toggle('active',curWeeklyMinMax==='1');
            document.getElementById('prof-weekly-minmax-off').classList.toggle('active',curWeeklyMinMax!=='1');
            document.getElementById('prof-weekly-goal-on').classList.toggle('active',curWeeklyGoalLine==='1');
            document.getElementById('prof-weekly-goal-off').classList.toggle('active',curWeeklyGoalLine!=='1');
            document.getElementById('prof-weekly-trend-on').classList.toggle('active',curWeeklyTrendLine==='1');
            document.getElementById('prof-weekly-trend-off').classList.toggle('active',curWeeklyTrendLine!=='1');
            document.getElementById('prof-weekly-table-exp-on').classList.toggle('active',curWeeklyTableExpanded);
            document.getElementById('prof-weekly-table-exp-off').classList.toggle('active',!curWeeklyTableExpanded);
            document.getElementById('prof-weekly-mode-rolling').classList.toggle('active',curWeeklyMode!=='iso');
            document.getElementById('prof-weekly-mode-iso').classList.toggle('active',curWeeklyMode==='iso');
            document.getElementById('prof-date-mdy').classList.toggle('active',curDateFormat==='mdy');
            document.getElementById('prof-date-dmy').classList.toggle('active',curDateFormat==='dmy');
            document.getElementById('prof-legend-on').classList.toggle('active',curLegend==='1');
            document.getElementById('prof-legend-off').classList.toggle('active',curLegend!=='1');
            document.getElementById('prof-weekly-legend-on').classList.toggle('active',curWeeklyLegend==='1');
            document.getElementById('prof-weekly-legend-off').classList.toggle('active',curWeeklyLegend!=='1');
            document.querySelectorAll('.profile-opt-btn[data-range]').forEach(b=>b.classList.toggle('active',b.dataset.range===curRange));
            document.querySelectorAll('.profile-opt-btn[data-weeks]').forEach(b=>b.classList.toggle('active',b.dataset.weeks===curWeeklyRange));
            document.querySelectorAll('.profile-opt-btn[data-wp-range]').forEach(b=>b.classList.toggle('active',b.dataset.wpRange===curWorkoutsRange));
            document.getElementById('prof-custom-wrap-weekly').hidden=curWeeklyRange!=='custom';
            profCustomDays.value=curCustomDays; profCustomWeeks.value=curCustomWeeks; profCustomWorkoutsDays.value=curCustomWorkoutsDays;
            syncFighterNameToHealthBar();
            modal.hidden=false; modalOpen(modal);
            modal.querySelector('.settings-scroll-body').scrollTop=0;
            openState=getSelections(); window.activeModal={tryClose};
        }

        window.openSettings = () => window.openExclusive(openModal);

        function wireToggle(ids) {
            ids.forEach(id=>{ document.getElementById(id).addEventListener('click',()=>{ ids.forEach(x=>document.getElementById(x).classList.remove('active')); document.getElementById(id).classList.add('active'); }); });
        }
        wireToggle(['prof-lbs-btn','prof-kg-btn']);
        wireToggle(['prof-landing-daily','prof-landing-weekly','prof-landing-table-daily','prof-landing-table-weekly']);
        wireToggle(['prof-height-us','prof-height-metric']);
        wireToggle(['prof-date-mdy','prof-date-dmy']);
        wireToggle(['prof-goal-line-on','prof-goal-line-off']);
        wireToggle(['prof-ma-line-on','prof-ma-line-off']);
        wireToggle(['prof-trend-line-on','prof-trend-line-off']);
        wireToggle(['prof-chart-interp','prof-chart-actual','prof-chart-dots','prof-chart-none']);
        wireToggle(['prof-fighter-name-on','prof-fighter-name-off']);
        wireToggle(['prof-weekly-minmax-on','prof-weekly-minmax-off']);
        wireToggle(['prof-weekly-goal-on','prof-weekly-goal-off']);
        wireToggle(['prof-weekly-trend-on','prof-weekly-trend-off']);
        wireToggle(['prof-weekly-table-exp-on','prof-weekly-table-exp-off']);
        wireToggle(['prof-weekly-mode-rolling','prof-weekly-mode-iso']);
        wireToggle(['prof-legend-on','prof-legend-off']);
        wireToggle(['prof-weekly-legend-on','prof-weekly-legend-off']);

        document.querySelectorAll('.profile-opt-btn[data-weeks]').forEach(b=>{
            b.addEventListener('click',()=>{
                document.querySelectorAll('.profile-opt-btn[data-weeks]').forEach(x=>x.classList.remove('active'));
                b.classList.add('active');
                const isCustom=b.dataset.weeks==='custom';
                document.getElementById('prof-custom-wrap-weekly').hidden=!isCustom;
                if(isCustom){profCustomWeeks.focus();profCustomWeeks.select();}
            });
        });
        profCustomWeeks.addEventListener('change',()=>{ const v=parseInt(profCustomWeeks.value); if(!v||v<4)profCustomWeeks.value=4; else if(v>156)profCustomWeeks.value=156; });
        document.querySelectorAll('.profile-opt-btn[data-range]').forEach(b=>{
            b.addEventListener('click',()=>{
                document.querySelectorAll('.profile-opt-btn[data-range]').forEach(x=>x.classList.remove('active'));
                b.classList.add('active');
                if(b.dataset.range==='custom'){profCustomDays.focus();profCustomDays.select();}
            });
        });
        profCustomDays.addEventListener('change',()=>{ const v=parseInt(profCustomDays.value); if(v&&v<7)profCustomDays.value=7; else if(v>1095)profCustomDays.value=1095; });
        document.querySelectorAll('.profile-opt-btn[data-wp-range]').forEach(b=>{
            b.addEventListener('click',()=>{
                document.querySelectorAll('.profile-opt-btn[data-wp-range]').forEach(x=>x.classList.remove('active'));
                b.classList.add('active');
                if(b.dataset.wpRange==='custom'){profCustomWorkoutsDays.focus();profCustomWorkoutsDays.select();}
            });
        });
        profCustomWorkoutsDays.addEventListener('change',()=>{ const v=parseInt(profCustomWorkoutsDays.value); if(v&&v<7)profCustomWorkoutsDays.value=7; else if(v>1095)profCustomWorkoutsDays.value=1095; });

        wireToggle(['prof-healthbar-on','prof-healthbar-off']);
        document.querySelectorAll('#prof-healthbar-on,#prof-healthbar-off').forEach(b=>{
            b.addEventListener('click',syncFighterNameToHealthBar);
        });

        function syncFighterNameToHealthBar() {
            const hudOff=document.getElementById('prof-healthbar-off').classList.contains('active');
            const fnOn=document.getElementById('prof-fighter-name-on'), fnOff=document.getElementById('prof-fighter-name-off');
            fnOn.disabled=hudOff; fnOff.disabled=hudOff;
            if(hudOff){fnOn.classList.remove('active');fnOff.classList.add('active');}
        }

        function doSave() {
            const _rangeNow=document.querySelector('.profile-opt-btn[data-range].active')?.dataset.range||'7d';
            const _weeksNow=document.querySelector('.profile-opt-btn[data-weeks].active')?.dataset.weeks||'4';
            const _wpRangeNow=document.querySelector('.profile-opt-btn[data-wp-range].active')?.dataset.wpRange||'7d';
            if(_rangeNow==='custom'&&!profCustomDays.value){window.showAppConfirm('Missing Value','Custom range is selected — enter a number of days to save.','Enter Days',()=>{profCustomDays.focus();profCustomDays.select();},null,'Dismiss');return;}
            if(_weeksNow==='custom'&&!profCustomWeeks.value){window.showAppConfirm('Missing Value','Custom range is selected — enter a number of weeks to save.','Enter Weeks',()=>{document.getElementById('prof-custom-wrap-weekly').hidden=false;profCustomWeeks.focus();profCustomWeeks.select();},null,'Dismiss');return;}
            if(_wpRangeNow==='custom'&&!profCustomWorkoutsDays.value){window.showAppConfirm('Missing Value','Custom range is selected — enter a number of days to save.','Enter Days',()=>{profCustomWorkoutsDays.focus();profCustomWorkoutsDays.select();},null,'Dismiss');return;}

            const newUnit=document.getElementById('prof-kg-btn').classList.contains('active')?'kg':'lbs';
            const newRange=_rangeNow, _days=parseInt(profCustomDays.value), newCustomDays=_days?String(Math.min(Math.max(_days,7),1095)):'';
            const newWeeklyRange=_weeksNow, _wks=parseInt(profCustomWeeks.value), newCustomWeeks=_wks?String(Math.min(Math.max(_wks,4),156)):'';
            const newWorkoutsRange=_wpRangeNow, _wpDays=parseInt(profCustomWorkoutsDays.value), newCustomWorkoutsDays=_wpDays?String(Math.min(Math.max(_wpDays,7),1095)):'';
            const newDefaultLanding=document.getElementById('prof-landing-table-weekly').classList.contains('active')?'table-weekly':document.getElementById('prof-landing-table-daily').classList.contains('active')?'table-daily':document.getElementById('prof-landing-weekly').classList.contains('active')?'weekly':'daily';
            const newHeightUnit=document.getElementById('prof-height-metric').classList.contains('active')?'metric':'us';
            const newGoalLine=document.getElementById('prof-goal-line-on').classList.contains('active')?'1':'0';
            const newMaLine=document.getElementById('prof-ma-line-on').classList.contains('active')?'1':'0';
            const newTrendLine=document.getElementById('prof-trend-line-on').classList.contains('active')?'1':'0';
            const newChartType=document.getElementById('prof-chart-interp').classList.contains('active')?'interpolated':document.getElementById('prof-chart-actual').classList.contains('active')?'actual':document.getElementById('prof-chart-dots').classList.contains('active')?'dots-only':'no-data';
            const newHealthBar=document.getElementById('prof-healthbar-on').classList.contains('active')?'1':'0';
            const newFighterName=document.getElementById('prof-fighter-name-on').classList.contains('active')?'1':'0';
            const newWeeklyMinMax=document.getElementById('prof-weekly-minmax-on').classList.contains('active')?'1':'0';
            const newWeeklyGoal=document.getElementById('prof-weekly-goal-on').classList.contains('active')?'1':'0';
            const newWeeklyTrend=document.getElementById('prof-weekly-trend-on').classList.contains('active')?'1':'0';
            const newWeeklyTableExp=document.getElementById('prof-weekly-table-exp-on').classList.contains('active')?'true':'false';
            const newWeeklyMode=document.getElementById('prof-weekly-mode-iso').classList.contains('active')?'iso':'rolling';
            const newLegend=document.getElementById('prof-legend-on').classList.contains('active')?'1':'0';
            const newWeeklyLegend=document.getElementById('prof-weekly-legend-on').classList.contains('active')?'1':'0';
            const newDateFormat=document.getElementById('prof-date-dmy').classList.contains('active')?'dmy':'mdy';

            window.savePref('pref_unit',newUnit); window.savePref('pref_range',newRange); window.savePref('pref_custom_days',newCustomDays);
            window.savePref('pref_weekly_range',newWeeklyRange); window.savePref('pref_custom_weeks',newCustomWeeks);
            window.savePref('pref_workouts_range',newWorkoutsRange); window.savePref('pref_workouts_custom_days',newCustomWorkoutsDays);
            window.savePref('pref_default_landing',newDefaultLanding); window.savePref('pref_height_unit',newHeightUnit);
            window.savePref('pref_goal_line',newGoalLine); window.savePref('pref_ma_line',newMaLine); window.savePref('pref_trend_line',newTrendLine);
            window.savePref('pref_chart_type',newChartType); window.savePref('pref_healthbar',newHealthBar); window.savePref('pref_fighter_name',newFighterName);
            window.savePref('pref_weekly_minmax',newWeeklyMinMax); window.savePref('pref_weekly_goal_line',newWeeklyGoal);
            window.savePref('pref_weekly_trend_line',newWeeklyTrend); window.savePref('pref_weekly_table_expanded',newWeeklyTableExp);
            window.savePref('pref_weekly_mode',newWeeklyMode); window.savePref('pref_legend',newLegend);
            window.savePref('pref_weekly_legend',newWeeklyLegend); window.savePref('pref_date_format',newDateFormat);

            const _dlEl=document.getElementById('daily-chart-legend'), _wlEl=document.getElementById('weekly-chart-legend');
            if(_dlEl)_dlEl.style.display=newLegend==='1'?'':'none';
            if(_wlEl)_wlEl.style.display=newWeeklyLegend==='1'?'':'none';
            const hud=document.getElementById('healthbar-hud');
            if(hud)hud.style.display=newHealthBar==='1'?'':'none';
            if(window.updateHealthBarName)window.updateHealthBarName();

            if(newUnit!==window.activeUnit){
                window.activeUnit=newUnit;
                if(window.applyPlateUnit)window.applyPlateUnit(newUnit);
            }

            const chartNeedsRefresh=!openState||newUnit!==openState.unit||newRange!==openState.range||String(newCustomDays)!==openState.customDays||newGoalLine!==openState.goalLine||newMaLine!==openState.maLine||newTrendLine!==openState.trendLine||newChartType!==openState.chartType||newDateFormat!==openState.dateFormat;
            if(chartNeedsRefresh){
                const days=newRange==='custom'?(parseInt(newCustomDays)||30):undefined;
                document.querySelectorAll('.range-btn').forEach(b=>b.classList.remove('active'));
                const rangeBtn=document.querySelector('.range-btn[data-range="'+newRange+'"]');
                if(rangeBtn)rangeBtn.classList.add('active');
                if(newRange==='custom'){const ci=document.getElementById('custom-days');if(ci)ci.value=newCustomDays;}
                if(window.refreshChart)window.refreshChart(newRange,days);
            }
            if(window.applyChartNav)window.applyChartNav();
            if(openState&&newDefaultLanding!==openState.defaultLanding){
                const isTableLanding=newDefaultLanding==='table-daily'||newDefaultLanding==='table-weekly';
                if(isTableLanding){if(window.setTablePage)window.setTablePage(newDefaultLanding==='table-weekly'?'weekly':'daily');if(window.setView)window.setView('table');}
                else if(window.setView)window.setView('chart');
            }
            if(window.setWeeklyRange)window.setWeeklyRange(newWeeklyRange,newCustomWeeks);
            if(window.setWorkoutsRange)window.setWorkoutsRange(newWorkoutsRange,newWorkoutsRange==='custom'?(parseInt(newCustomWorkoutsDays)||30):undefined);
            if(openState){
                const weeklyNeedsRefresh=window.weeklyChartLoaded&&(newUnit!==openState.unit||newWeeklyRange!==openState.weeklyRange||newCustomWeeks!==String(openState.customWeeks)||newWeeklyGoal!==openState.weeklyGoalLine||newWeeklyTrend!==openState.weeklyTrendLine||newWeeklyMinMax!==openState.weeklyMinMax||newWeeklyMode!==openState.weeklyMode||newDateFormat!==openState.dateFormat);
                if(weeklyNeedsRefresh&&window.refreshWeeklyChart)window.refreshWeeklyChart();
                if(window.renderTable){const tableNeedsRefresh=newUnit!==openState.unit||newWeeklyMode!==openState.weeklyMode||newDateFormat!==openState.dateFormat||newWeeklyRange!==openState.weeklyRange||newCustomWeeks!==String(openState.customWeeks);if(tableNeedsRefresh)window.renderTable();}
            }
            forceClose();
        }

        /* Collapsible section headers */
        ['measurements','landing','overtime','weekly','workouts','hud'].forEach(key=>{
            const hdr=document.querySelector('.settings-section-label[data-section="'+key+'"]');
            const body=document.getElementById('ssb-'+key);
            if(!hdr||!body)return;
            hdr.setAttribute('role','button'); hdr.setAttribute('tabindex','0'); hdr.setAttribute('aria-controls','ssb-'+key);
            const initCollapsed=localStorage.getItem('pref_section_'+key)==='0';
            if(initCollapsed){body.style.height='0px';hdr.classList.add('collapsed');}
            hdr.setAttribute('aria-expanded',initCollapsed?'false':'true');
            hdr.addEventListener('click',()=>{
                const nowCollapsed=!hdr.classList.contains('collapsed');
                hdr.classList.toggle('collapsed',nowCollapsed); hdr.setAttribute('aria-expanded',nowCollapsed?'false':'true');
                localStorage.setItem('pref_section_'+key,nowCollapsed?'0':'1');
                if(nowCollapsed){body.style.height=body.scrollHeight+'px';body.offsetHeight;body.style.height='0px';}
                else{body.style.height=body.scrollHeight+'px';body.addEventListener('transitionend',()=>{body.style.height='';},{once:true});}
            });
            hdr.addEventListener('keydown',e=>{if(e.key==='Enter'||e.key===' '){e.preventDefault();hdr.click();}});
        });

        function resetDefaults() {
            const activate=(onId,offId)=>{document.getElementById(onId).classList.add('active');document.getElementById(offId).classList.remove('active');};
            activate('prof-lbs-btn','prof-kg-btn'); activate('prof-height-us','prof-height-metric'); activate('prof-date-mdy','prof-date-dmy');
            ['prof-landing-daily','prof-landing-weekly','prof-landing-table-daily','prof-landing-table-weekly'].forEach(id=>document.getElementById(id).classList.remove('active'));
            document.getElementById('prof-landing-daily').classList.add('active');
            document.querySelectorAll('.profile-opt-btn[data-range]').forEach(b=>b.classList.remove('active'));
            document.getElementById('prof-range-7d').classList.add('active'); profCustomDays.value='';
            activate('prof-ma-line-on','prof-ma-line-off'); activate('prof-chart-interp','prof-chart-actual');
            document.getElementById('prof-chart-dots').classList.remove('active'); document.getElementById('prof-chart-none').classList.remove('active');
            activate('prof-trend-line-off','prof-trend-line-on'); activate('prof-goal-line-off','prof-goal-line-on');
            document.querySelectorAll('.profile-opt-btn[data-weeks]').forEach(b=>b.classList.remove('active'));
            document.getElementById('prof-wrange-4').classList.add('active'); document.getElementById('prof-custom-wrap-weekly').hidden=true; profCustomWeeks.value='';
            document.querySelectorAll('.profile-opt-btn[data-wp-range]').forEach(b=>b.classList.remove('active'));
            document.getElementById('prof-wp-range-7d').classList.add('active'); profCustomWorkoutsDays.value='';
            activate('prof-weekly-trend-off','prof-weekly-trend-on'); activate('prof-weekly-goal-off','prof-weekly-goal-on');
            activate('prof-weekly-minmax-on','prof-weekly-minmax-off'); activate('prof-weekly-table-exp-off','prof-weekly-table-exp-on');
            activate('prof-weekly-mode-rolling','prof-weekly-mode-iso');
            activate('prof-healthbar-on','prof-healthbar-off'); activate('prof-fighter-name-on','prof-fighter-name-off');
            activate('prof-legend-on','prof-legend-off'); activate('prof-weekly-legend-on','prof-weekly-legend-off');
            syncFighterNameToHealthBar();
        }

        document.getElementById('settings-reset').addEventListener('click',()=>{
            window.showAppConfirm('Reset to Defaults','All settings will be restored to their original defaults. Click Save afterwards to make the changes permanent, or Cancel to discard.','Reset',resetDefaults,null,'Cancel');
        });
        cancelBtn.addEventListener('click',()=>tryClose());
        saveBtn.addEventListener('click',doSave);
        modal.addEventListener('click',e=>{if(e.target===modal)tryClose();});
        document.addEventListener('keydown',e=>{if(e.key==='Escape'&&!modal.hidden)tryClose();});
    })();

    /* ── Settings custom scrollbar ── */
    (function () {
        const scrollBody=document.querySelector('.settings-scroll-body');
        const track=document.getElementById('settings-scrollbar-track');
        const thumb=document.getElementById('settings-scrollbar-thumb');
        const modal=document.getElementById('settings-modal');
        function syncThumb(){
            if(scrollBody.scrollHeight<=scrollBody.clientHeight){thumb.style.display='none';return;}
            const thumbH=Math.max((scrollBody.clientHeight/scrollBody.scrollHeight)*track.clientHeight,30);
            const maxTop=track.clientHeight-thumbH,maxScroll=scrollBody.scrollHeight-scrollBody.clientHeight;
            thumb.style.display='block'; thumb.style.height=thumbH+'px'; thumb.style.top=(scrollBody.scrollTop/maxScroll)*maxTop+'px';
        }
        scrollBody.addEventListener('scroll',syncThumb,{passive:true});
        new ResizeObserver(syncThumb).observe(scrollBody);
        new MutationObserver(()=>{if(!modal.hidden)syncThumb();}).observe(modal,{attributes:true,attributeFilter:['hidden']});
        let drag=false,dragY=0,dragScroll=0;
        function startDrag(e){drag=true;dragY=e.clientY;dragScroll=scrollBody.scrollTop;e.preventDefault();}
        thumb.addEventListener('mousedown',startDrag);
        track.addEventListener('mousedown',e=>{
            if(e.target===thumb)return;
            const rect=track.getBoundingClientRect(),thumbH=parseFloat(thumb.style.height)||30,maxTop=track.clientHeight-thumbH,maxScroll=scrollBody.scrollHeight-scrollBody.clientHeight;
            const clickY=Math.min(Math.max(e.clientY-rect.top-thumbH/2,0),maxTop);
            scrollBody.scrollTop=(clickY/maxTop)*maxScroll; startDrag(e);
        });
        document.addEventListener('mousemove',e=>{
            if(!drag)return;
            const maxTop=track.clientHeight-parseFloat(thumb.style.height),maxScroll=scrollBody.scrollHeight-scrollBody.clientHeight;
            scrollBody.scrollTop=Math.max(0,Math.min(maxScroll,dragScroll+(e.clientY-dragY)*(maxScroll/maxTop)));
        });
        document.addEventListener('mouseup',()=>{drag=false;});
    })();

    /* ── Coming soon tip ── */
    (() => {
        const tip=document.createElement('div');
        tip.className='coming-soon-tip'; tip.textContent='Coming Soon'; document.body.appendChild(tip);
        let hideTimer=null;
        function showComingSoon(btn) {
            // Out to the right of the button, clear of the other nav buttons.
            const r=btn.getBoundingClientRect();
            tip.style.top=(r.top+r.height/2)+'px'; tip.style.left=(r.right+10)+'px';
            tip.classList.add('visible'); clearTimeout(hideTimer);
            hideTimer=setTimeout(()=>tip.classList.remove('visible'),1500);
        }
        ['protein-btn'].forEach(id=>{ const el=document.getElementById(id); if(el)el.addEventListener('click',()=>showComingSoon(el)); });
    })();

    /* ── Click-anywhere-to-toggle for .is-toggle rows ── */
    (function () {
        document.querySelectorAll('.profile-toggle-row.is-toggle').forEach(function(row) {
            var busy = false;
            row.addEventListener('click', function(e) {
                if (busy) return;
                var clicked = e.target.closest('.profile-opt-btn');
                if (clicked && !clicked.classList.contains('active')) return;
                e.stopPropagation();
                busy = true;
                var onBtn = row.querySelector('.profile-opt-btn:first-child');
                var offBtn = row.querySelector('.profile-opt-btn:last-child');
                if (onBtn.classList.contains('active')) { offBtn.click(); } else { onBtn.click(); }
                busy = false;
            }, true);
        });
    })();
