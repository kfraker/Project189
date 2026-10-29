/* Home page script. */
    /* ── Healthbar functions ── */
    function updateLostWeight() {
        const mode       = localStorage.getItem('fight_goal_mode') || 'lean';
        const startLbs   = parseFloat(document.getElementById('start-lbs-num').textContent);
        const currentLbs = parseFloat(document.getElementById('current-lbs-num').textContent);
        const labelEl    = document.getElementById('lost-plate-label');
        if (labelEl) labelEl.textContent = mode === 'muscle' ? 'GAINED' : 'LOST';
        if (isNaN(startLbs) || isNaN(currentLbs)) {
            document.getElementById('lost-lbs-num').textContent = '—';
            document.getElementById('lost-kg-num').textContent  = '—';
        } else {
            const diff = mode === 'muscle'
                ? Math.max(0, Math.round((currentLbs - startLbs) * 10) / 10)
                : Math.max(0, Math.round((startLbs - currentLbs) * 10) / 10);
            document.getElementById('lost-lbs-num').textContent = fmtLbs(diff);
            document.getElementById('lost-kg-num').textContent  = (diff / 2.2046).toFixed(1);
        }
        if (window.updateHealthBar) window.updateHealthBar();
    }
    window.updateLostWeight = updateLostWeight;

    window.updateHealthBar = function () {
        const fill = document.getElementById('healthbar-fill');
        if (!fill) return;
        const mode       = localStorage.getItem('fight_goal_mode') || 'lean';
        const startLbs   = parseFloat(document.getElementById('start-lbs-num').textContent);
        const currentLbs = parseFloat(document.getElementById('current-lbs-num').textContent);
        const goalLbs    = parseFloat(document.getElementById('goal-lbs-num').textContent);
        let pct = 0;
        if (mode === 'muscle') {
            if (!isNaN(startLbs) && !isNaN(currentLbs) && !isNaN(goalLbs) && goalLbs > startLbs)
                pct = Math.min(1, Math.max(0, (currentLbs - startLbs) / (goalLbs - startLbs))) * 100;
        } else {
            if (!isNaN(startLbs) && !isNaN(currentLbs) && !isNaN(goalLbs) && startLbs > goalLbs)
                pct = Math.min(1, Math.max(0, (startLbs - currentLbs) / (startLbs - goalLbs))) * 100;
        }
        fill.style.width = pct.toFixed(1) + '%';
        const track = document.getElementById('healthbar-fill-track');
        if (track) track.setAttribute('aria-valuenow', pct.toFixed(1));
        const tt = document.getElementById('healthbar-tooltip');
        if (tt && !isNaN(currentLbs) && !isNaN(goalLbs)) {
            const diffLbs = mode === 'muscle' ? goalLbs - currentLbs : currentLbs - goalLbs;
            if (diffLbs <= 0) {
                tt.textContent = 'Goal reached!';
            } else {
                const useKg = window.activeUnit === 'kg';
                const val   = useKg ? (diffLbs / 2.2046).toFixed(1) : diffLbs.toFixed(1);
                tt.textContent = val + ' ' + (useKg ? 'kg' : 'lbs') + ' to goal';
            }
        }
    };

    window.updateHealthBarName = function () {
        const el = document.getElementById('healthbar-name');
        if (!el) return;
        el.textContent = localStorage.getItem('fight_name') || '';
        const hudOn  = (localStorage.getItem('pref_healthbar')     ?? '1') !== '0';
        const nameOn = (localStorage.getItem('pref_fighter_name')  ?? '1') !== '0';
        el.style.visibility = (hudOn && nameOn) ? '' : 'hidden';
    };

    window.applyHealthbarPref = function () {
        const on = localStorage.getItem('pref_healthbar') !== '0';
        const hud = document.getElementById('healthbar-hud');
        if (hud) hud.style.display = on ? '' : 'none';
    };

    requestAnimationFrame(() => {
        if (window.updateHealthBar)     window.updateHealthBar();
        if (window.updateHealthBarName) window.updateHealthBarName();
        if (window.applyHealthbarPref)  window.applyHealthbarPref();
        const legendOn       = (localStorage.getItem('pref_legend')         ?? '1') !== '0';
        const weeklyLegendOn = (localStorage.getItem('pref_weekly_legend')  ?? '1') !== '0';
        const dlEl = document.getElementById('daily-chart-legend');
        const wlEl = document.getElementById('weekly-chart-legend');
        if (dlEl) dlEl.style.display  = legendOn       ? '' : 'none';
        if (wlEl) wlEl.style.display  = weeklyLegendOn ? '' : 'none';
    });

    /* ── Strip white fill zone from health bar PNG ── */
    (function () {
        const img = document.getElementById('healthbar-img');
        function strip() {
            const c = document.createElement('canvas');
            c.width = img.naturalWidth; c.height = img.naturalHeight;
            const ctx = c.getContext('2d');
            ctx.drawImage(img, 0, 0);
            const d  = ctx.getImageData(0, 0, c.width, c.height), px = d.data;
            for (let i = 0; i < px.length; i += 4) {
                if (px[i] > 240 && px[i + 1] > 240 && px[i + 2] > 240) px[i + 3] = 0;
            }
            ctx.putImageData(d, 0, 0);
            img.src = c.toDataURL('image/png');
        }
        if (img.complete && img.naturalWidth) strip();
        else img.addEventListener('load', strip, { once: true });
    })();

    /* ── Sync plates from DB on load ── */
    Promise.all([
        fetch('/api/latest-weight').then(r => r.json()),
        fetch('/api/settings').then(r => r.json())
    ]).then(([latest, settings]) => {
        window.oldestEntryDate = latest.oldest_date || null;
        if (latest.weight_lbs !== undefined) {
            document.getElementById('current-lbs-num').textContent = fmtLbs(latest.weight_lbs);
            document.getElementById('current-kg-num').textContent  = latest.weight_kg.toFixed(1);
        }
        const sw = settings['starting_weight'];
        if (sw) {
            document.getElementById('start-lbs-num').textContent = fmtLbs(sw.value_lbs);
            document.getElementById('start-kg-num').textContent  = sw.value_kg.toFixed(1);
        }
        const gw = settings['goal_weight'];
        if (gw) {
            document.getElementById('goal-lbs-num').textContent = fmtLbs(gw.value_lbs);
            document.getElementById('goal-kg-num').textContent  = gw.value_kg.toFixed(1);
        }
        updateLostWeight();
    });

    /* ── Weight edit modal — shared by all editable weight cards ── */
    function setupWeightModal(cfg) {
        const modal    = document.getElementById(cfg.modal);
        const input    = document.getElementById(cfg.input);
        const preview  = document.getElementById(cfg.preview);
        const lbsNum   = document.getElementById(cfg.lbsNum);
        const kgNum    = document.getElementById(cfg.kgNum);
        const screenEl = cfg.screens ? document.getElementById(cfg.screens[0]) : modal;
        const labelEl  = screenEl ? screenEl.querySelector('.modal-label') : null;
        const unitTag  = screenEl ? screenEl.querySelector('.modal-unit-tag') : null;
        const baseLabel = labelEl ? labelEl.textContent.replace(/\s*\((lbs|kgs)\)$/, '') : '';

        function toKg(lbs)  { return (lbs / 2.2046).toFixed(1); }
        function toLbs(kg)  { return (kg  * 2.2046).toFixed(1); }
        function isKgMode() { return window.activeUnit === 'kg'; }

        function updatePreview() {
            const v = parseFloat(input.value);
            preview.textContent = (!isNaN(v) && v > 0)
                ? (isKgMode() ? toLbs(v) + ' lbs' : toKg(v) + ' kgs') : '';
        }
        function close() { modal.hidden = true; modalClose(modal); }
        function commitSave(lbs) {
            lbsNum.textContent = fmtLbs(lbs); kgNum.textContent = toKg(lbs);
            close(); if (cfg.onSave) cfg.onSave();
        }
        function showConfirmScreen(v, message) {
            document.getElementById(cfg.confirmMsgId).textContent = message;
            document.getElementById(cfg.screens[0]).hidden = true;
            document.getElementById(cfg.screens[1]).hidden = false;
            document.getElementById(cfg.confirmBtnId).onclick = () => doSave(v, true);
        }
        async function doSave(v, overwrite) {
            const lbs = isKgMode() ? parseFloat(toLbs(v)) : v;
            if (cfg.apiSave) {
                const result = await cfg.apiSave(lbs, overwrite);
                if (typeof result === 'string' && result.startsWith('conflict:')) {
                    showConfirmScreen(v, result.slice('conflict:'.length)); return;
                }
                if (!result) return;
            }
            commitSave(lbs);
        }
        function open() {
            if (cfg.screens) {
                document.getElementById(cfg.screens[0]).hidden = false;
                document.getElementById(cfg.screens[1]).hidden = true;
            }
            const kg = isKgMode();
            if (labelEl) labelEl.textContent = baseLabel + (kg ? ' (kgs)' : ' (lbs)');
            if (unitTag) unitTag.textContent  = kg ? 'kgs' : 'lbs';
            input.min   = kg ? '20'  : '50';
            input.max   = kg ? '450' : '999';
            input.value = kg ? kgNum.textContent : lbsNum.textContent;
            updatePreview(); modal.hidden = false; modalOpen(modal);
            setTimeout(() => { input.focus(); input.select(); }, 50);
        }
        function step(amount) {
            const cur = parseFloat(input.value) || 0;
            let next = Math.round((cur + amount) * 10) / 10;
            next = Math.min(parseFloat(input.max), Math.max(parseFloat(input.min), next));
            input.value = next; updatePreview();
        }
        document.getElementById(cfg.plate).addEventListener('click', open);
        document.getElementById(cfg.plate).addEventListener('keydown', e => { if (e.key === 'Enter' || e.key === ' ') open(); });
        document.getElementById(cfg.cancel).addEventListener('click', close);
        document.getElementById(cfg.save).addEventListener('click', () => { const v = parseFloat(input.value); if (!isNaN(v) && v > 0) doSave(v, false); });
        document.getElementById(cfg.stepUp).addEventListener('click', () => step(1));
        document.getElementById(cfg.stepDown).addEventListener('click', () => step(-1));
        modal.addEventListener('click', e => { if (e.target === modal) close(); });
        document.addEventListener('keydown', e => { if (e.key === 'Escape') close(); });
        input.addEventListener('keydown', e => { if (e.key === 'Enter') { const v = parseFloat(input.value); if (!isNaN(v) && v > 0) doSave(v, false); } });
        input.addEventListener('input', updatePreview);
        if (cfg.screens) document.getElementById(cfg.confirmCancelId).addEventListener('click', close);
    }

    setupWeightModal({
        plate: 'goal-plate', modal: 'goal-modal', input: 'goal-input', preview: 'goal-kg-preview',
        lbsNum: 'goal-lbs-num', kgNum: 'goal-kg-num', cancel: 'goal-cancel', save: 'goal-save',
        stepUp: 'goal-step-up', stepDown: 'goal-step-down',
        screens: ['goal-screen-input', 'goal-screen-confirm'],
        confirmMsgId: 'goal-overwrite-message', confirmBtnId: 'goal-overwrite-confirm', confirmCancelId: 'goal-overwrite-cancel',
        onSave: () => window.updateHealthBar(),
        apiSave: async (lbs, overwrite) => {
            const mode     = localStorage.getItem('fight_goal_mode') || 'lean';
            const startLbs = parseFloat(document.getElementById('start-lbs-num').textContent);
            const preview  = document.getElementById('goal-kg-preview');
            if (!isNaN(startLbs) && startLbs > 0) {
                if (mode === 'muscle' && lbs <= startLbs) { if (preview) preview.textContent = '↑ Must exceed starting weight'; return false; }
                if (mode === 'lean' && lbs >= startLbs)   { if (preview) preview.textContent = '↓ Must be below starting weight'; return false; }
            }
            const res  = await fetch('/api/setting', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ key: 'goal_weight', value_lbs: lbs, overwrite }) });
            const data = await res.json();
            if (data.success)  return true;
            if (data.conflict) return 'conflict:Are you sure you want to update your goal weight?';
            return false;
        }
    });

    setupWeightModal({
        plate: 'start-plate', modal: 'start-modal', input: 'start-input', preview: 'start-kg-preview',
        lbsNum: 'start-lbs-num', kgNum: 'start-kg-num', cancel: 'start-cancel', save: 'start-save',
        stepUp: 'start-step-up', stepDown: 'start-step-down',
        screens: ['start-screen-input', 'start-screen-confirm'],
        confirmMsgId: 'start-overwrite-message', confirmBtnId: 'start-overwrite-confirm', confirmCancelId: 'start-overwrite-cancel',
        onSave: updateLostWeight,
        apiSave: async (lbs, overwrite) => {
            const res  = await fetch('/api/setting', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ key: 'starting_weight', value_lbs: lbs, overwrite }) });
            const data = await res.json();
            if (data.success)  return true;
            if (data.conflict) return 'conflict:Are you sure you want to update your starting weight?';
            return false;
        }
    });

    setupWeightModal({
        plate: 'current-plate', modal: 'current-modal', input: 'current-input', preview: 'current-kg-preview',
        lbsNum: 'current-lbs-num', kgNum: 'current-kg-num', cancel: 'current-cancel', save: 'current-save',
        stepUp: 'current-step-up', stepDown: 'current-step-down',
        screens: ['current-screen-input', 'current-screen-confirm'],
        confirmMsgId: 'current-overwrite-message', confirmBtnId: 'current-overwrite-confirm', confirmCancelId: 'current-overwrite-cancel',
        onSave: () => { updateLostWeight(); if (window.refreshChart) window.refreshChart(); if (window.renderTable) window.renderTable(); if (window.refreshHeaderStats) window.refreshHeaderStats(); },
        apiSave: async (lbs, overwrite) => {
            const today = getTodayISO();
            const res   = await fetch('/api/weight', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ weight_lbs: lbs, date: today, overwrite }) });
            const data  = await res.json();
            if (data.success)  return true;
            if (data.conflict) return 'conflict:Are you sure you want to overwrite your weight for ' + formatDateDisplay(today) + '?';
            return false;
        }
    });

    window.applyPlateUnit = function(unit) {
        document.querySelectorAll('.plate').forEach(p => p.classList.toggle('kg-primary', unit === 'kg'));
    };
    window.applyPlateUnit(window.activeUnit);

    /* ── Refresh plates from DB (callable after quick-log) ── */
    window.refreshPlatesData = function() {
        Promise.all([
            fetch('/api/latest-weight').then(r => r.json()),
            fetch('/api/settings').then(r => r.json())
        ]).then(([latest, settings]) => {
            window.oldestEntryDate = latest.oldest_date || null;
            if (latest.weight_lbs !== undefined) {
                document.getElementById('current-lbs-num').textContent = fmtLbs(latest.weight_lbs);
                document.getElementById('current-kg-num').textContent  = latest.weight_kg.toFixed(1);
            }
            const sw = settings['starting_weight'];
            if (sw) {
                document.getElementById('start-lbs-num').textContent = fmtLbs(sw.value_lbs);
                document.getElementById('start-kg-num').textContent  = sw.value_kg.toFixed(1);
            }
            const gw = settings['goal_weight'];
            if (gw) {
                document.getElementById('goal-lbs-num').textContent = fmtLbs(gw.value_lbs);
                document.getElementById('goal-kg-num').textContent  = gw.value_kg.toFixed(1);
            }
            updateLostWeight();
        });
    };

    /* ── Quick-add modal ── */
    (function () {
        const addBtn = document.getElementById('mp-footer-add-btn');
        const modal  = document.getElementById('quick-add-modal');
        function openQA()  { modal.hidden = false; modalOpen(modal); addBtn.setAttribute('aria-expanded', 'true'); }
        function closeQA() { modal.hidden = true; modalClose(modal); addBtn.setAttribute('aria-expanded', 'false'); }
        addBtn.addEventListener('click', openQA);
        modal.addEventListener('click', e => { if (e.target === modal) closeQA(); });
        document.addEventListener('keydown', e => { if (e.key === 'Escape' && !modal.hidden) closeQA(); });
        document.getElementById('qa-log-weight').addEventListener('click', () => { closeQA(); if (window.openWeightModal) window.openWeightModal(); });
        document.getElementById('qa-log-workout').addEventListener('click', () => { closeQA(); if (window.openWorkoutModal) window.openWorkoutModal(); });
    })();

    /* ── Log Past Weight modal ── */
    (function () {
        const modal    = document.getElementById('history-modal');
        const dateIn   = document.getElementById('history-date');
        const weightIn = document.getElementById('history-weight');
        const preview  = document.getElementById('history-kg-preview');
        const screenEl = document.getElementById('history-screen-input');
        const labelEl  = screenEl ? screenEl.querySelector('label[for="history-weight"]') : null;
        const unitTag  = screenEl ? screenEl.querySelector('.modal-unit-tag') : null;
        const baseLabel = labelEl ? labelEl.textContent.replace(/\s*\((lbs|kgs)\)$/,'') : '';
        const calEl    = document.getElementById('history-calendar');
        const gridEl   = document.getElementById('dp-grid');
        const monthLbl = document.getElementById('dp-month-label');
        const dayNames = calEl ? calEl.querySelector('.dp-day-names') : null;
        const MONTHS   = ['January','February','March','April','May','June','July','August','September','October','November','December'];
        let viewDate=new Date(), selectedDateISO='', calMode='days', yearPage=new Date().getFullYear()-5;

        function isoFromParts(y,m,d){return y+'-'+String(m+1).padStart(2,'0')+'-'+String(d).padStart(2,'0');}
        function displayFromISO(iso){const[y,m,d]=iso.split('-');return MONTHS[parseInt(m)-1]+' '+parseInt(d)+', '+y;}
        function renderCalendar(){
            if(!gridEl)return; calMode='days'; if(dayNames)dayNames.style.display=''; gridEl.style.gridTemplateColumns='repeat(7,1fr)';
            const today=getTodayISO(),todayD=new Date();
            const minDate=isoFromParts(todayD.getFullYear()-10,todayD.getMonth(),todayD.getDate());
            const y=viewDate.getFullYear(),m=viewDate.getMonth();
            if(monthLbl)monthLbl.textContent=MONTHS[m]+' '+y;
            const firstDow=new Date(y,m,1).getDay(),daysInMonth=new Date(y,m+1,0).getDate(),daysInPrev=new Date(y,m,0).getDate();
            gridEl.innerHTML='';
            for(let i=firstDow-1;i>=0;i--){const btn=document.createElement('button');btn.type='button';btn.className='dp-day dp-other-month';btn.textContent=daysInPrev-i;btn.disabled=true;gridEl.appendChild(btn);}
            for(let day=1;day<=daysInMonth;day++){
                const iso=isoFromParts(y,m,day),btn=document.createElement('button');
                btn.type='button';btn.className='dp-day';btn.textContent=day;
                if(iso===today)btn.classList.add('dp-today');if(iso===selectedDateISO)btn.classList.add('dp-selected');
                if(iso>today||iso<minDate){btn.disabled=true;}else{btn.addEventListener('click',()=>{selectedDateISO=iso;if(dateIn)dateIn.value=displayFromISO(iso);if(calEl)calEl.hidden=true;});}
                gridEl.appendChild(btn);
            }
            const rem=(firstDow+daysInMonth)%7;
            if(rem>0){for(let i=1;i<=7-rem;i++){const btn=document.createElement('button');btn.type='button';btn.className='dp-day dp-other-month';btn.textContent=i;btn.disabled=true;gridEl.appendChild(btn);}}
        }
        function renderYearGrid(){
            if(!gridEl)return; calMode='years'; if(dayNames)dayNames.style.display='none'; gridEl.style.gridTemplateColumns='repeat(3,1fr)';
            const todayY=new Date().getFullYear(),minY=todayY-10,curY=viewDate.getFullYear();
            if(monthLbl)monthLbl.textContent=yearPage+' – '+(yearPage+11); gridEl.innerHTML='';
            for(let i=0;i<12;i++){
                const yr=yearPage+i,btn=document.createElement('button');
                btn.type='button';btn.className='dp-day dp-year';btn.textContent=yr;
                if(yr===todayY)btn.classList.add('dp-today');if(yr===curY)btn.classList.add('dp-selected');
                if(yr>todayY||yr<minY){btn.disabled=true;}else{btn.addEventListener('click',()=>{viewDate=new Date(yr,viewDate.getMonth(),1);renderCalendar();});}
                gridEl.appendChild(btn);
            }
        }
        if(monthLbl)monthLbl.addEventListener('click',()=>{if(calMode==='days'){yearPage=viewDate.getFullYear()-5;renderYearGrid();}else{renderCalendar();}});
        if(dateIn)dateIn.addEventListener('click',()=>{if(calEl.hidden){viewDate=selectedDateISO?new Date(selectedDateISO+'T12:00:00'):new Date();renderCalendar();calEl.hidden=false;}else{calEl.hidden=true;}});
        const dpPrev=document.getElementById('dp-prev'),dpNext=document.getElementById('dp-next');
        if(dpPrev)dpPrev.addEventListener('click',()=>{if(calMode==='years'){yearPage-=12;renderYearGrid();}else{viewDate=new Date(viewDate.getFullYear(),viewDate.getMonth()-1,1);renderCalendar();}});
        if(dpNext)dpNext.addEventListener('click',()=>{if(calMode==='years'){yearPage+=12;renderYearGrid();}else{viewDate=new Date(viewDate.getFullYear(),viewDate.getMonth()+1,1);renderCalendar();}});
        document.addEventListener('click',e=>{const wrap=document.getElementById('history-date-wrap');if(calEl&&!calEl.hidden&&!e.composedPath().includes(wrap))calEl.hidden=true;});

        function isKgMode(){return window.activeUnit==='kg';}
        function close(){modal.hidden=true;if(calEl)calEl.hidden=true;const si=document.getElementById('history-screen-input'),sc=document.getElementById('history-screen-confirm');if(si)si.hidden=false;if(sc)sc.hidden=true;modalClose(modal);}
        function updatePreview(){const v=parseFloat(weightIn.value);preview.textContent=(!isNaN(v)&&v>0)?(isKgMode()?(v*2.2046).toFixed(1)+' lbs':(v/2.2046).toFixed(1)+' kgs'):'';}
        async function doSave(dt,lbs,overwrite){
            const res=await fetch('/api/weight',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({weight_lbs:lbs,date:dt,overwrite})});
            const data=await res.json();
            if(data.success){close();if(window.refreshHeaderStats)window.refreshHeaderStats();if(window.refreshPlatesData)window.refreshPlatesData();return;}
            if(data.conflict){
                const om=document.getElementById('history-overwrite-message');if(om)om.textContent='Are you sure you want to overwrite your weight for '+formatDateDisplay(dt)+'?';
                const si=document.getElementById('history-screen-input'),sc=document.getElementById('history-screen-confirm');
                if(si)si.hidden=true;if(sc)sc.hidden=false;
                const oc=document.getElementById('history-overwrite-cancel'),ocf=document.getElementById('history-overwrite-confirm');
                if(oc)oc.onclick=close; if(ocf)ocf.onclick=()=>doSave(dt,lbs,true);
            }
        }
        function trySave(){const dt=selectedDateISO,raw=parseFloat(weightIn.value);if(!dt){if(dateIn)dateIn.focus();return;}if(isNaN(raw)||raw<=0){weightIn.focus();return;}const lbs=isKgMode()?parseFloat((raw*2.2046).toFixed(1)):raw;doSave(dt,lbs,false);}
        function step(amount){const kg=isKgMode(),min=kg?20:50,max=kg?450:999,cur=parseFloat(weightIn.value)||0;weightIn.value=Math.min(max,Math.max(min,Math.round((cur+amount)*10)/10));updatePreview();}

        window.openWeightModal = async function() {
            const kg=isKgMode();
            if(labelEl)labelEl.textContent=baseLabel+(kg?' (kgs)':' (lbs)');
            if(unitTag)unitTag.textContent=kg?'kgs':'lbs';
            weightIn.min=kg?'20':'50'; weightIn.max=kg?'450':'999';
            let startDate='';
            try{
                const today=getTodayISO();
                const rows=await fetch('/api/weights?range=7d').then(r=>r.json());
                if(!rows.some(r=>r.date===today))startDate=today;
            }catch{}
            selectedDateISO=startDate; if(dateIn)dateIn.value=startDate?displayFromISO(startDate):''; weightIn.value=''; preview.textContent='';
            const si=document.getElementById('history-screen-input'),sc=document.getElementById('history-screen-confirm');
            if(si)si.hidden=false; if(sc)sc.hidden=true;
            modal.hidden=false; modalOpen(modal);
            setTimeout(()=>{if(dateIn)dateIn.focus();},50);
        };
        const hCancel=document.getElementById('history-cancel'),hSave=document.getElementById('history-save');
        const hStepUp=document.getElementById('history-step-up'),hStepDown=document.getElementById('history-step-down');
        if(hCancel)hCancel.addEventListener('click',close);
        if(hSave)hSave.addEventListener('click',trySave);
        if(hStepUp)hStepUp.addEventListener('click',()=>step(1));
        if(hStepDown)hStepDown.addEventListener('click',()=>step(-1));
        modal.addEventListener('click',e=>{if(e.target===modal)close();});
        document.addEventListener('keydown',e=>{if(e.key==='Escape'){if(calEl&&!calEl.hidden){calEl.hidden=true;return;}if(!modal.hidden)close();}});
        weightIn.addEventListener('input',updatePreview);
        weightIn.addEventListener('keydown',e=>{if(e.key==='Enter')trySave();});
    })();

    /* ── Workout data ── */
    const WORKOUTS = [
        { name: 'Aerobics Class',                  met: 6.5  },
        { name: 'Backpacking',                     met: 7.0  },
        { name: 'Badminton',                       met: 5.5  },
        { name: 'Ballet',                          met: 6.0  },
        { name: 'Ballroom Dancing',                met: 3.0  },
        { name: 'Baseball / Softball',             met: 5.0  },
        { name: 'Basketball',                      met: 6.5  },
        { name: 'Boxing',                          met: 7.8  },
        { name: 'Calisthenics',                    met: 3.8  },
        { name: 'Cardio (general)',                met: 7.5  },
        { name: 'Circuit Training',                met: 8.0  },
        { name: 'CrossFit',                        met: 8.0  },
        { name: 'Cross-Country Skiing',            met: 9.0  },
        { name: 'Cycling',                         speedBased: true, speedTable: 'cycling', defaultSpeed: 12.0 },
        { name: 'Disc Golf',                       met: 3.5  },
        { name: 'Downhill Skiing',                 met: 5.3  },
        { name: 'Elliptical (moderate)',           met: 5.0  },
        { name: 'Elliptical (vigorous)',           met: 6.5  },
        { name: 'Football',                        met: 8.0  },
        { name: 'Golf (cart)',                     met: 3.5  },
        { name: 'Golf (walking)',                  met: 4.3  },
        { name: 'Hiking',                          met: 5.3  },
        { name: 'HIIT',                            met: 9.5  },
        { name: 'Hip Hop Dance',                   met: 6.5  },
        { name: 'Hockey',                          met: 8.0  },
        { name: 'Ice Hockey',                      met: 8.0  },
        { name: 'Ice Skating',                     met: 5.5  },
        { name: 'Jogging',                         met: 7.0  },
        { name: 'Jump Rope',                       met: 10.0 },
        { name: 'Kayaking',                        met: 5.0  },
        { name: 'Kettlebell Training',             met: 8.0  },
        { name: 'Lacrosse',                        met: 8.0  },
        { name: 'Martial Arts',                    met: 10.3 },
        { name: 'Mountain Biking',                 met: 8.5  },
        { name: 'Open Water Swimming',             met: 6.0  },
        { name: 'Paddleboarding',                  met: 6.0  },
        { name: 'Pickleball',                      met: 4.0  },
        { name: 'Pilates',                         met: 3.0  },
        { name: 'Powerlifting',                    met: 6.0  },
        { name: 'Power Yoga',                      met: 4.0  },
        { name: 'Racquetball',                     met: 7.0  },
        { name: 'Rock Climbing',                   met: 7.5  },
        { name: 'Rollerblading',                   met: 7.5  },
        { name: 'Rowing (water)',                  met: 7.0  },
        { name: 'Rowing Machine (moderate)',       met: 7.0  },
        { name: 'Rowing Machine (vigorous)',       met: 8.5  },
        { name: 'Rugby',                           met: 8.3  },
        { name: 'Running',                         speedBased: true, speedTable: 'running', defaultSpeed: 5.0  },
        { name: 'Salsa Dancing',                   met: 5.5  },
        { name: 'Skateboarding',                   met: 5.0  },
        { name: 'Snowboarding',                    met: 5.3  },
        { name: 'Snowshoeing',                     met: 5.3  },
        { name: 'Soccer',                          met: 7.0  },
        { name: 'Spin Class',                      met: 8.5  },
        { name: 'Squash',                          met: 7.3  },
        { name: 'Stair Climbing',                  met: 8.0  },
        { name: 'Stair Climber Machine',           met: 9.0  },
        { name: 'Stationary Bike (moderate)',      met: 5.5  },
        { name: 'Stationary Bike (vigorous)',      met: 8.5  },
        { name: 'Step Aerobics',                   met: 8.5  },
        { name: 'Strength Training (moderate)',    met: 3.5  },
        { name: 'Strength Training (vigorous)',    met: 6.0  },
        { name: 'Stretching',                      met: 2.3  },
        { name: 'Surfing',                         met: 3.0  },
        { name: 'Swimming (backstroke)',           met: 4.8  },
        { name: 'Swimming (breaststroke)',         met: 5.3  },
        { name: 'Swimming (butterfly)',            met: 13.8 },
        { name: 'Swimming (freestyle, moderate)', met: 5.8  },
        { name: 'Swimming (freestyle, vigorous)', met: 9.8  },
        { name: 'Table Tennis',                    met: 4.0  },
        { name: 'Tabata',                          met: 9.5  },
        { name: 'Tai Chi',                         met: 3.0  },
        { name: 'Tennis (doubles)',                met: 5.0  },
        { name: 'Tennis (singles)',                met: 7.3  },
        { name: 'Trail Running',                   met: 9.0  },
        { name: 'Treadmill Running',               speedBased: true, speedTable: 'running', defaultSpeed: 5.0  },
        { name: 'Ultimate Frisbee',                met: 7.0  },
        { name: 'Volleyball',                      met: 4.0  },
        { name: 'Beach Volleyball',                met: 8.0  },
        { name: 'Walking',                         speedBased: true, speedTable: 'walking', defaultSpeed: 3.0  },
        { name: 'Water Aerobics',                  met: 5.3  },
        { name: 'Weight Training (moderate)',      met: 3.5  },
        { name: 'Weight Training (vigorous)',      met: 6.0  },
        { name: 'Wrestling',                       met: 6.0  },
        { name: 'Yoga',                            met: 2.5  },
        { name: 'Zumba',                           met: 6.5  },
    ];
    const SPEED_TABLES = {
        running: [[0.5,1.8],[1.0,2.3],[1.5,2.8],[2.0,3.0],[2.5,3.3],[3.0,3.8],[3.5,4.3],[4.0,5.0],[4.5,6.3],[5.0,8.3],[5.5,9.0],[6.0,9.8],[6.5,10.5],[7.0,11.0],[7.5,11.5],[8.0,11.8],[8.5,12.3],[9.0,12.8],[9.5,13.5],[10.0,14.5],[11.0,16.0],[12.0,19.0]],
        cycling: [[3.0,3.5],[5.0,4.0],[8.0,5.0],[10.0,6.8],[12.0,8.0],[14.0,10.0],[16.0,12.0],[19.0,14.0],[22.0,16.0],[25.0,19.0]],
        walking: [[0.5,1.5],[1.0,2.0],[1.5,2.3],[2.0,2.5],[2.5,3.0],[3.0,3.5],[3.5,4.3],[4.0,5.0],[4.5,6.0],[5.0,7.0]]
    };
    function speedToMet(mph, table) {
        const pts = SPEED_TABLES[table] || SPEED_TABLES.running;
        for (let i = 0; i < pts.length - 1; i++) {
            const [lo,loM] = pts[i], [hi,hiM] = pts[i+1];
            if (mph >= lo && mph <= hi) { const t=(mph-lo)/(hi-lo); return Math.round((loM+t*(hiM-loM))*10)/10; }
        }
        return mph < pts[0][0] ? pts[0][1] : pts[pts.length-1][1];
    }
    function tierClass(met) {
        if (met >= 9)   return 'tier-intense';
        if (met >= 6)   return 'tier-hard';
        if (met >= 3.5) return 'tier-moderate';
        return 'tier-light';
    }
    function tierClassByName(name) { const w = WORKOUTS.find(e => e.name === name); return tierClass(w ? w.met : 5); }
    function fmtDateWO(iso) { const d = new Date(iso + 'T00:00:00'); return d.toLocaleDateString('en-US', { weekday: 'short', month: 'short', day: 'numeric' }); }

    /* ── Log Workout modal ── */
    (function () {
        const logModal   = document.getElementById('wp-log-modal');
        const dayHeading = document.getElementById('wpm-day-heading');
        const dayEntries = document.getElementById('wpm-day-entries');
        const dayEmpty   = document.getElementById('wpm-day-empty');
        let duration=30, selectedMet=null, selectedLabel=null, isSpeedBased=false, speedMph=5.0, speedTable='running', weightKg=80, dropdownIdx=-1;
        const speedField=document.getElementById('workout-speed-field'), speedVal=document.getElementById('workout-speed-val');
        const durVal=document.getElementById('workout-dur-val'), kcalNum=document.getElementById('workout-kcal-num');
        const noteInput=document.getElementById('workout-note-input'), typeInput=document.getElementById('workout-type-input');
        const dropdown=document.getElementById('workout-search-dropdown'), chip=document.getElementById('workout-selected-chip');
        const chipLabel=document.getElementById('workout-selected-label'), chipTier=document.getElementById('workout-chip-tier');
        const chipClear=document.getElementById('workout-chip-clear'), durField=document.getElementById('workout-dur-field');
        const addActivityBtn=document.getElementById('wpm-add-activity-btn');
        function calcKcal(){return Math.round(selectedMet*weightKg*(duration/60));}
        function refreshKcal(){kcalNum.textContent=selectedMet?calcKcal().toLocaleString():'—';}
        function setFormActive(active){durField.classList.toggle('speed-inactive',!active);addActivityBtn.disabled=!active;}
        chip.style.display='none'; speedField.classList.add('speed-inactive');
        document.getElementById('workout-speed-up').disabled=true; document.getElementById('workout-speed-down').disabled=true;
        setFormActive(false);
        document.getElementById('workout-speed-up').addEventListener('click',()=>{speedMph=Math.round((speedMph+0.5)*10)/10;speedVal.textContent=speedMph.toFixed(1);if(isSpeedBased){selectedMet=speedToMet(speedMph,speedTable);refreshKcal();}});
        document.getElementById('workout-speed-down').addEventListener('click',()=>{speedMph=Math.max(0.5,Math.round((speedMph-0.5)*10)/10);speedVal.textContent=speedMph.toFixed(1);if(isSpeedBased){selectedMet=speedToMet(speedMph,speedTable);refreshKcal();}});
        document.getElementById('workout-dur-up').addEventListener('click',()=>{duration=Math.min(duration+5,300);durVal.textContent=duration;refreshKcal();});
        document.getElementById('workout-dur-down').addEventListener('click',()=>{duration=Math.max(duration-5,5);durVal.textContent=duration;refreshKcal();});
        function buildDropdown(results){dropdown.innerHTML='';results.forEach((w,i)=>{const item=document.createElement('div');item.className='wsd-item';item.dataset.idx=i;item.innerHTML=`<span>${w.name}</span><span class="wsd-met">${w.speedBased?'speed-based':w.met+' MET'}</span>`;item.addEventListener('mousedown',e=>{e.preventDefault();selectWorkout(w);});dropdown.appendChild(item);});dropdownIdx=-1;}
        function selectWorkout(w){isSpeedBased=!!w.speedBased;selectedLabel=w.name;const su=document.getElementById('workout-speed-up'),sd=document.getElementById('workout-speed-down');if(isSpeedBased){speedTable=w.speedTable||'running';speedMph=w.defaultSpeed||5.0;speedVal.textContent=speedMph.toFixed(1);selectedMet=speedToMet(speedMph,speedTable);speedField.classList.remove('speed-inactive');su.disabled=false;sd.disabled=false;}else{selectedMet=w.met;speedField.classList.add('speed-inactive');su.disabled=true;sd.disabled=true;}chipLabel.textContent=w.name;chipTier.className='workout-chip-tier '+tierClass(selectedMet);typeInput.style.display='none';chip.style.display='flex';typeInput.value='';dropdown.hidden=true;refreshKcal();setFormActive(true);}
        chipClear.addEventListener('click',()=>{chip.style.display='none';typeInput.style.display='';speedField.classList.add('speed-inactive');typeInput.value='';selectedMet=null;selectedLabel=null;isSpeedBased=false;refreshKcal();setFormActive(false);});
        typeInput.addEventListener('input',()=>{const q=typeInput.value.trim().toLowerCase();if(!q){dropdown.hidden=true;return;}const matches=WORKOUTS.filter(w=>w.name.toLowerCase().includes(q));matches.sort((a,b)=>{const rank=n=>{const lo=n.toLowerCase();if(lo.startsWith(q))return 0;if(lo.split(/[\s(/]/).some(w=>w.startsWith(q)))return 1;return 2;};return rank(a.name)-rank(b.name);});const results=matches.slice(0,10);if(!results.length){dropdown.hidden=true;return;}buildDropdown(results);dropdown.hidden=false;});
        typeInput.addEventListener('keydown',e=>{const items=dropdown.querySelectorAll('.wsd-item');if(e.key==='ArrowDown'){e.preventDefault();dropdownIdx=Math.min(dropdownIdx+1,items.length-1);items.forEach((el,i)=>el.classList.toggle('highlighted',i===dropdownIdx));}else if(e.key==='ArrowUp'){e.preventDefault();dropdownIdx=Math.max(dropdownIdx-1,0);items.forEach((el,i)=>el.classList.toggle('highlighted',i===dropdownIdx));}else if(e.key==='Enter'&&dropdownIdx>=0){e.preventDefault();const q=typeInput.value.trim().toLowerCase();const results=WORKOUTS.filter(w=>w.name.toLowerCase().includes(q));if(results[dropdownIdx])selectWorkout(results[dropdownIdx]);}else if(e.key==='Escape'){dropdown.hidden=true;}});
        document.addEventListener('click',e=>{if(!e.target.closest('#workout-type-input,#workout-search-dropdown,.workout-search-wrap'))dropdown.hidden=true;});
        dropdown.addEventListener('wheel',e=>{e.preventDefault();dropdown.scrollTop+=e.deltaY;},{passive:false});
        const stagedEntriesEl=document.getElementById('wpm-staged-entries');
        let stagedActivities=[],pendingDeletes=[],loadedNote='';
        function renderStagedRow(item,idx){const el=document.createElement('div');el.className='wpm-staged-row';el.dataset.idx=idx;el.innerHTML=`<div class="wpm-staged-row-info"><span class="workout-badge ${tierClassByName(item.type)}">${item.type.replace(/</g,'&lt;')}</span></div><div class="wpm-day-dur">${item.duration_min} min</div><div class="wpm-day-kcal">${item.kcal.toLocaleString()} kcal</div><button class="table-delete-btn" aria-label="Remove">&#10005;</button>`;el.querySelector('.table-delete-btn').addEventListener('click',()=>{const i=parseInt(el.dataset.idx,10);stagedActivities.splice(i,1);el.remove();stagedEntriesEl.querySelectorAll('.wpm-staged-row').forEach((r,j)=>{r.dataset.idx=j;});if(!dayEntries.querySelectorAll('.wpm-day-row').length&&!stagedActivities.length)dayEmpty.hidden=false;});stagedEntriesEl.appendChild(el);}
        async function loadDayEntries(isoDate){const isToday=isoDate===getTodayISO();dayHeading.textContent=isToday?'Logged today':`Logged for ${fmtDateWO(isoDate)}`;dayEntries.querySelectorAll('.wpm-day-row').forEach(el=>el.remove());stagedEntriesEl.innerHTML='';stagedActivities=[];pendingDeletes=[];dayEmpty.hidden=false;const[rows,noteData]=await Promise.all([fetch('/api/workouts?date='+isoDate).then(r=>r.json()),fetch('/api/workout-day-note?date='+isoDate).then(r=>r.json())]);loadedNote=noteData.note||'';noteInput.value=loadedNote;if(rows.length){dayEmpty.hidden=true;rows.forEach(w=>{const el=document.createElement('div');el.className='wpm-day-row';el.dataset.wid=w.id;el.innerHTML=`<div class="wpm-day-row-info"><span class="workout-badge ${tierClassByName(w.type)}">${w.type.replace(/</g,'&lt;')}</span></div><div class="wpm-day-dur">${w.duration_min} min</div><div class="wpm-day-kcal">${w.kcal.toLocaleString()} kcal</div><button class="table-delete-btn" aria-label="Delete">&#10005;</button>`;el.querySelector('.table-delete-btn').addEventListener('click',()=>{pendingDeletes.push({id:w.id,type:w.type,duration_min:w.duration_min});el.remove();if(!dayEntries.querySelectorAll('.wpm-day-row').length&&!stagedActivities.length)dayEmpty.hidden=false;});dayEntries.appendChild(el);});}}
        const dpInput=document.getElementById('wp-date-input'),dpCalEl=document.getElementById('wpm-calendar'),dpGridEl=document.getElementById('wpm-dp-grid'),dpMonthLbl=document.getElementById('wpm-dp-month-label');
        const dpDayNames=dpCalEl.querySelector('.dp-day-names'),DP_MONTHS=['January','February','March','April','May','June','July','August','September','October','November','December'];
        let dpViewDate=new Date(),dpSelected='',dpCalMode='days',dpYearPage=new Date().getFullYear()-5;
        function dpIsoFromParts(y,m,d){return y+'-'+String(m+1).padStart(2,'0')+'-'+String(d).padStart(2,'0');}
        function dpDisplayFromISO(iso){const[y,m,d]=iso.split('-');return DP_MONTHS[parseInt(m)-1]+' '+parseInt(d)+', '+y;}
        function dpRenderCalendar(){dpCalMode='days';dpDayNames.style.display='';dpGridEl.style.gridTemplateColumns='repeat(7,1fr)';const today=getTodayISO(),y=dpViewDate.getFullYear(),m=dpViewDate.getMonth();dpMonthLbl.textContent=DP_MONTHS[m]+' '+y;const firstDow=new Date(y,m,1).getDay(),daysInMonth=new Date(y,m+1,0).getDate(),daysInPrev=new Date(y,m,0).getDate();dpGridEl.innerHTML='';for(let i=firstDow-1;i>=0;i--){const btn=document.createElement('button');btn.type='button';btn.className='dp-day dp-other-month';btn.textContent=daysInPrev-i;btn.disabled=true;dpGridEl.appendChild(btn);}for(let day=1;day<=daysInMonth;day++){const iso=dpIsoFromParts(y,m,day),btn=document.createElement('button');btn.type='button';btn.className='dp-day';btn.textContent=day;if(iso===today)btn.classList.add('dp-today');if(iso===dpSelected)btn.classList.add('dp-selected');if(iso>today){btn.disabled=true;}else{btn.addEventListener('click',()=>{dpSelected=iso;dpInput.value=dpDisplayFromISO(iso);dpCalEl.hidden=true;loadDayEntries(iso);});}dpGridEl.appendChild(btn);}const rem=(firstDow+daysInMonth)%7;if(rem>0){for(let i=1;i<=7-rem;i++){const btn=document.createElement('button');btn.type='button';btn.className='dp-day dp-other-month';btn.textContent=i;btn.disabled=true;dpGridEl.appendChild(btn);}}}
        function dpRenderYearGrid(){dpCalMode='years';dpDayNames.style.display='none';dpGridEl.style.gridTemplateColumns='repeat(3,1fr)';const todayY=new Date().getFullYear();dpMonthLbl.textContent=dpYearPage+' – '+(dpYearPage+11);dpGridEl.innerHTML='';for(let i=0;i<12;i++){const yr=dpYearPage+i,btn=document.createElement('button');btn.type='button';btn.className='dp-day dp-year';btn.textContent=yr;if(yr===todayY)btn.classList.add('dp-today');if(yr===dpViewDate.getFullYear())btn.classList.add('dp-selected');if(yr>todayY){btn.disabled=true;}else{btn.addEventListener('click',()=>{dpViewDate=new Date(yr,dpViewDate.getMonth(),1);dpRenderCalendar();});}dpGridEl.appendChild(btn);}}
        dpMonthLbl.addEventListener('click',()=>{if(dpCalMode==='days'){dpYearPage=dpViewDate.getFullYear()-5;dpRenderYearGrid();}else dpRenderCalendar();});
        dpInput.addEventListener('click',()=>{if(dpCalEl.hidden){dpViewDate=dpSelected?new Date(dpSelected+'T12:00:00'):new Date();dpRenderCalendar();dpCalEl.hidden=false;}else{dpCalEl.hidden=true;}});
        document.getElementById('wpm-dp-prev').addEventListener('click',()=>{if(dpCalMode==='years'){dpYearPage-=12;dpRenderYearGrid();}else{dpViewDate=new Date(dpViewDate.getFullYear(),dpViewDate.getMonth()-1,1);dpRenderCalendar();}});
        document.getElementById('wpm-dp-next').addEventListener('click',()=>{if(dpCalMode==='years'){dpYearPage+=12;dpRenderYearGrid();}else{dpViewDate=new Date(dpViewDate.getFullYear(),dpViewDate.getMonth()+1,1);dpRenderCalendar();}});
        document.addEventListener('click',e=>{const wrap=document.getElementById('wpm-dp-wrap');if(!dpCalEl.hidden&&!e.composedPath().includes(wrap))dpCalEl.hidden=true;});
        function dpSetDate(isoDate){dpSelected=isoDate;dpInput.value=isoDate?dpDisplayFromISO(isoDate):'';dpCalEl.hidden=true;}
        function clearActivityForm(){typeInput.value='';typeInput.style.display='';chip.style.display='none';speedField.classList.add('speed-inactive');document.getElementById('workout-speed-up').disabled=true;document.getElementById('workout-speed-down').disabled=true;selectedMet=null;selectedLabel=null;isSpeedBased=false;speedMph=5.0;speedVal.textContent='5.0';duration=30;durVal.textContent='30';setFormActive(false);refreshKcal();dropdown.hidden=true;}
        function closeModal(){logModal.hidden=true;dpCalEl.hidden=true;dropdown.hidden=true;}
        function hasUnsavedChanges(){return stagedActivities.length>0||pendingDeletes.length>0||noteInput.value.trim()!==loadedNote;}
        function maybeClose(){if(!hasUnsavedChanges()){closeModal();return;}window.showAppConfirm('Discard changes?','You have unsaved changes. Discard them?','Discard',closeModal);}
        function clearDayView(){dayHeading.textContent='Select a date';dayEntries.querySelectorAll('.wpm-day-row').forEach(el=>el.remove());stagedEntriesEl.innerHTML='';stagedActivities=[];pendingDeletes=[];loadedNote='';noteInput.value='';dayEmpty.hidden=false;}
        async function openModal(isoDate){try{const w=await fetch('/api/latest-weight').then(r=>r.json());weightKg=w.weight_lbs?w.weight_lbs/2.2046:80;}catch{weightKg=80;}let startDate=isoDate;if(!startDate){const today=getTodayISO();const todayRows=await fetch('/api/workouts?date='+today).then(r=>r.json());startDate=todayRows.length?'':today;}dpSetDate(startDate);clearActivityForm();if(startDate)await loadDayEntries(startDate);else clearDayView();logModal.hidden=false;requestAnimationFrame(()=>document.getElementById('wpm-entries-scroll').dispatchEvent(new Event('scroll')));typeInput.focus();}
        window.openWorkoutModal = function(){openModal();};
        document.getElementById('wp-modal-x').addEventListener('click',maybeClose);
        document.getElementById('wp-modal-cancel').addEventListener('click',maybeClose);
        logModal.addEventListener('click',e=>{if(e.target===logModal)maybeClose();});
        logModal.addEventListener('keydown',e=>{if(e.key==='Escape')maybeClose();});
        document.getElementById('wpm-add-activity-btn').addEventListener('click',()=>{if(!selectedLabel)return;const kcal=calcKcal(),typeLabel=isSpeedBased?`${selectedLabel} (${speedMph.toFixed(1)} mph)`:selectedLabel;const item={type:typeLabel,duration_min:duration,kcal};const idx=stagedActivities.length;stagedActivities.push(item);renderStagedRow(item,idx);dayEmpty.hidden=true;clearActivityForm();});
        function showDeleteConfirm(onCommit){const modal=document.getElementById('idx-del-check-modal'),checks=document.getElementById('idx-del-checks'),okBtn=document.getElementById('idx-del-check-ok');checks.innerHTML='';pendingDeletes.forEach((d,i)=>{const lbl=document.createElement('label');lbl.className='row-delete-check-label';const cb=document.createElement('input');cb.type='checkbox';cb.checked=true;cb.dataset.idx=i;lbl.append(cb,document.createTextNode(`${d.type} (${d.duration_min} min)`));checks.appendChild(lbl);});function syncOk(){okBtn.disabled=checks.querySelectorAll('input:checked').length===0;}checks.querySelectorAll('input[type="checkbox"]').forEach(cb=>cb.addEventListener('change',syncOk));okBtn.disabled=false;modal.hidden=false;document.getElementById('idx-del-check-cancel').onclick=()=>{modal.hidden=true;};okBtn.onclick=()=>{modal.hidden=true;const ticked=new Set();checks.querySelectorAll('input[type="checkbox"]').forEach(cb=>{if(cb.checked)ticked.add(parseInt(cb.dataset.idx,10));});pendingDeletes=pendingDeletes.filter((_,i)=>ticked.has(i));onCommit();};}
        document.getElementById('wp-modal-save').addEventListener('click',async()=>{if(!dpSelected){dpInput.focus();return;}const isoDate=dpSelected;async function commitSave(){for(const d of pendingDeletes)await fetch('/api/workout/'+d.id,{method:'DELETE'});for(const item of stagedActivities)await fetch('/api/workout',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({date:isoDate,type:item.type,duration_min:item.duration_min,kcal:item.kcal,note:''})});await fetch('/api/workout-day-note',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({date:isoDate,note:noteInput.value.trim()})});closeModal();if(window.refreshHeaderStats)window.refreshHeaderStats();}if(pendingDeletes.length>0){showDeleteConfirm(commitSave);}else{await commitSave();}});
        (function(){const scroll=document.getElementById('wpm-entries-scroll'),thumb=document.getElementById('wpm-scroll-thumb');function sync(){const track=thumb.parentElement;if(scroll.scrollHeight<=scroll.clientHeight){thumb.style.display='none';return;}thumb.style.display='block';const ratio=scroll.clientHeight/scroll.scrollHeight,thumbH=Math.max(16,ratio*track.clientHeight),maxTop=track.clientHeight-thumbH,pct=scroll.scrollTop/(scroll.scrollHeight-scroll.clientHeight);thumb.style.height=thumbH+'px';thumb.style.top=(pct*maxTop)+'px';}scroll.addEventListener('scroll',sync);new MutationObserver(sync).observe(scroll,{childList:true,subtree:true});let drag=false,dragY=0,dragTop=0;thumb.addEventListener('mousedown',e=>{drag=true;dragY=e.clientY;dragTop=scroll.scrollTop;e.preventDefault();e.stopPropagation();});document.addEventListener('mousemove',e=>{if(!drag)return;const track=thumb.parentElement,thumbH=parseFloat(thumb.style.height)||16,maxTop=track.clientHeight-thumbH,maxScroll=scroll.scrollHeight-scroll.clientHeight;scroll.scrollTop=Math.max(0,Math.min(dragTop+(maxTop>0?(e.clientY-dragY)/maxTop:0)*maxScroll,maxScroll));});document.addEventListener('mouseup',()=>{drag=false;});})();
    })();

    /* ── Header stats ── */
    (function () {
        async function updateHeaderStats() {
            const stats = await fetch('/api/home-stats').then(r => r.json());
            const streakNumEl = document.getElementById('mp-active-streak');
            const streakLblEl = streakNumEl.closest('.mp-stat--streak').querySelector('.site-stat-label');
            streakNumEl.textContent = stats.streak + (stats.streak === 1 ? ' day' : ' days');
            applyStreakGlow(streakNumEl, streakLblEl, stats.streak);
            document.getElementById('mp-kcal-week').textContent = stats.kcal_week.toLocaleString();
            const trendEl = document.getElementById('mp-trend');
            const unit = window.activeUnit || 'lbs';
            const delta = unit === 'kg' ? stats.trend_kg : stats.trend_lbs;
            trendEl.textContent = delta != null
                ? (delta >= 0 ? '+' : '−') + Math.abs(delta).toFixed(1)
                : '—';
        }
        updateHeaderStats().catch(e => console.warn('Header stats failed:', e));
        window.refreshHeaderStats = updateHeaderStats;
    })();
