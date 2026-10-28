/* Workouts page script. */
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
    function tierClass(met) { if (met >= 9) return 'tier-intense'; if (met >= 6) return 'tier-hard'; if (met >= 3.5) return 'tier-moderate'; return 'tier-light'; }
    function tierClassByName(name) { const w = WORKOUTS.find(e => e.name === name); return tierClass(w ? w.met : 5); }
    function todayISO() { return new Date().toLocaleDateString('en-CA'); }
    function fmtDate(iso) { const d=new Date(iso+'T00:00:00'); return d.toLocaleDateString('en-US',{weekday:'short',month:'short',day:'numeric'}); }

    /* ── Table render ── */
    const tableInner = document.getElementById('wp-table-inner');
    const emptyMsg   = document.getElementById('wp-empty');

    function renderTable(rows, dayNotes) {
        dayNotes = dayNotes || {};
        tableInner.querySelectorAll('.wp-date-group').forEach(el => el.remove());
        if (!rows.length) { emptyMsg.hidden = false; return; }
        emptyMsg.hidden = true;
        const groups = {};
        rows.forEach(w => { (groups[w.date] || (groups[w.date] = [])).push(w); });
        Object.keys(groups).sort((a,b) => b.localeCompare(a)).forEach(date => {
            const group = document.createElement('div');
            group.className = 'wp-date-group';
            const dayRows = groups[date];
            const totalDur  = dayRows.reduce((s,w) => s+w.duration_min, 0);
            const totalKcal = dayRows.reduce((s,w) => s+w.kcal, 0);
            const headerRow = document.createElement('div');
            headerRow.className = 'wp-date-header-row';
            const heading = document.createElement('div');
            heading.className = 'wp-date-heading'; heading.textContent = fmtDate(date);
            const count = document.createElement('div');
            count.className = 'wp-date-count';
            count.innerHTML = `<span class="wp-count-num">${dayRows.length}</span><span class="wp-count-word">&nbsp;${dayRows.length===1?'workout':'workouts'}</span>`;
            const headerValues = document.createElement('div');
            headerValues.className = 'wp-header-values';
            headerValues.innerHTML = `<div class="wp-header-dur">${totalDur} min</div><div class="wp-header-kcal">${totalKcal.toLocaleString()}<span>kcal</span></div>`;
            const chevron = document.createElement('span');
            chevron.className = 'wp-chevron'; chevron.textContent = '▾';
            headerRow.appendChild(heading); headerRow.appendChild(count); headerRow.appendChild(headerValues); headerRow.appendChild(chevron);
            headerRow.addEventListener('click', () => group.classList.toggle('collapsed'));
            group.appendChild(headerRow);
            const rowsWrap = document.createElement('div');
            rowsWrap.className = 'wp-rows-wrap';
            if (dayNotes[date]) {
                const noteEl = document.createElement('div');
                noteEl.className = 'wp-day-note'; noteEl.textContent = dayNotes[date];
                rowsWrap.appendChild(noteEl);
            }
            dayRows.forEach(w => {
                const row = document.createElement('div');
                row.className = 'wp-row'; row.dataset.wid = w.id;
                row.innerHTML = `<div class="wp-row-main"><span class="workout-badge ${tierClassByName(w.type)}">${w.type.replace(/</g,'&lt;')}</span></div><div class="wp-row-values"><div class="wp-row-dur">${w.duration_min} min</div><div class="wp-row-kcal">${w.kcal.toLocaleString()}<span>kcal</span></div></div><button class="table-delete-btn wp-del-btn" aria-label="Delete workout">&#10005;</button>`;
                row.addEventListener('click', e => { if (!e.target.closest('.wp-del-btn')) openModal(date); });
                row.querySelector('.wp-del-btn').addEventListener('click', e => {
                    e.stopPropagation();
                    window.showAppConfirm('Delete Workout', `Delete "${w.type}" (${w.duration_min} min)?\n\nThis cannot be undone.`, 'Delete', async () => {
                        await fetch('/api/workout/'+w.id, {method:'DELETE'});
                        row.remove();
                        allWorkouts = allWorkouts.filter(x => x.id !== w.id);
                        if (!rowsWrap.querySelectorAll('.wp-row').length) group.remove();
                        await refreshStats();
                        if (!tableInner.querySelectorAll('.wp-date-group').length) emptyMsg.hidden = false;
                    });
                });
                rowsWrap.appendChild(row);
            });
            group.appendChild(rowsWrap);
            tableInner.appendChild(group);
        });
    }

    let allWorkouts = [], allDayNotes = {}, currentRange = '7d';
    let customDays = 30;

    function filterRows(rows, range) {
        if (range === 'all') return rows;
        const days = range === 'custom' ? customDays : {'7d':7,'30d':30,'90d':90,'1y':365}[range];
        const cutoff = new Date(Date.now()-(days-1)*86400000).toLocaleDateString('en-CA');
        return rows.filter(r => r.date >= cutoff);
    }
    function applyFilter() { renderTable(filterRows(allWorkouts, currentRange), allDayNotes); }
    async function loadTable() {
        [allWorkouts, allDayNotes] = await Promise.all([fetch('/api/workouts').then(r=>r.json()), fetch('/api/workout-day-notes').then(r=>r.json())]);
        applyFilter();
    }

    /* ── Filter button / range menu ── */
    (function () {
        const filterBtn  = document.getElementById('wp-filter-btn');
        const rangeMenu  = document.getElementById('wp-range-menu');
        const customWrap = document.getElementById('wp-custom-days-wrap');
        const customIn   = document.getElementById('wp-custom-days');

        function closeMenu() { filterBtn.classList.remove('open'); rangeMenu.classList.remove('open'); }

        filterBtn.addEventListener('click', e => { e.stopPropagation(); filterBtn.classList.toggle('open'); rangeMenu.classList.toggle('open'); });

        rangeMenu.querySelectorAll('.wp-range-btn').forEach(btn => {
            btn.addEventListener('click', e => {
                e.stopPropagation();
                rangeMenu.querySelectorAll('.wp-range-btn').forEach(b => b.classList.remove('active'));
                btn.classList.add('active');
                currentRange = btn.dataset.range;
                window.savePref('pref_workouts_range', currentRange);
                if (currentRange === 'custom') {
                    customWrap.hidden = false;
                    customIn.focus(); customIn.select();
                    customDays = Math.min(Math.max(parseInt(customIn.value) || 30, 7), 1095);
                } else {
                    customWrap.hidden = true;
                }
                applyFilter();
            });
        });

        function applyCustom() {
            customDays = Math.min(Math.max(parseInt(customIn.value) || 30, 7), 1095);
            customIn.value = customDays;
            window.savePref('pref_workouts_custom_days', String(customDays));
            applyFilter();
        }
        customIn.addEventListener('keydown', e => { if (e.key === 'Enter') applyCustom(); });
        customIn.addEventListener('change', applyCustom);

        document.addEventListener('click', e => {
            if (!rangeMenu.classList.contains('open')) return;
            if (!e.composedPath().includes(rangeMenu) && !e.composedPath().includes(filterBtn)) closeMenu();
        });
        document.addEventListener('keydown', e => { if (e.key === 'Escape') closeMenu(); });

        const savedRange         = localStorage.getItem('pref_workouts_range') || '7d';
        const savedCustomDaysStr = localStorage.getItem('pref_workouts_custom_days');
        customDays = parseInt(savedCustomDaysStr) || 30;
        const savedBtn = rangeMenu.querySelector(`.wp-range-btn[data-range="${savedRange}"]`);
        if (savedBtn) {
            rangeMenu.querySelectorAll('.wp-range-btn').forEach(b => b.classList.remove('active'));
            savedBtn.classList.add('active');
        }
        customWrap.hidden = savedRange !== 'custom';
        if (savedRange === 'custom') customIn.value = savedCustomDaysStr || '';
        currentRange = savedRange;

        /* Called from the Settings modal when the Workouts default range is saved. */
        window.setWorkoutsRange = function (range, days) {
            currentRange = range;
            if (range === 'custom' && days) customDays = days;
            rangeMenu.querySelectorAll('.wp-range-btn').forEach(b => b.classList.toggle('active', b.dataset.range === range));
            customWrap.hidden = range !== 'custom';
            if (range === 'custom' && days) customIn.value = days;
            applyFilter();
        };
    })();

    /* ── Stats ── */
    async function refreshStats() {
        const rows = await fetch('/api/workouts').then(r => r.json());
        const today = todayISO();
        const weekAgo = new Date(Date.now()-6*86400000).toLocaleDateString('en-CA');
        const thisWeek = rows.filter(r => r.date >= weekAgo && r.date <= today);
        document.getElementById('wp-count').textContent = thisWeek.length;
        document.getElementById('wp-kcal').textContent  = thisWeek.reduce((s,r) => s+r.kcal, 0).toLocaleString();
        const dateSet = new Set(rows.map(r => r.date));
        let streak = 0, d = new Date();
        if (!dateSet.has(d.toLocaleDateString('en-CA'))) d.setDate(d.getDate()-1);
        while (dateSet.has(d.toLocaleDateString('en-CA'))) { streak++; d.setDate(d.getDate()-1); }
        const wpStreakEl = document.getElementById('wp-streak');
        wpStreakEl.textContent = streak;
        applyStreakGlow(wpStreakEl, wpStreakEl.closest('.wp-stat--streak')?.querySelector('.site-stat-label'), streak);
    }

    /* ── Log Workout Modal calendar ── */
    const dpInput=document.getElementById('wp-date-input'), dpCalEl=document.getElementById('wpm-calendar');
    const dpGridEl=document.getElementById('wpm-dp-grid'), dpMonthLbl=document.getElementById('wpm-dp-month-label');
    const dpDayNames=dpCalEl.querySelector('.dp-day-names');
    const DP_MONTHS=['January','February','March','April','May','June','July','August','September','October','November','December'];
    let dpViewDate=new Date(), dpSelected='', dpCalMode='days', dpYearPage=new Date().getFullYear()-5;
    function dpIsoFromParts(y,m,d){return y+'-'+String(m+1).padStart(2,'0')+'-'+String(d).padStart(2,'0');}
    function dpDisplayFromISO(iso){const[y,m,d]=iso.split('-');return DP_MONTHS[parseInt(m)-1]+' '+parseInt(d)+', '+y;}
    function dpRenderCalendar(){dpCalMode='days';dpDayNames.style.display='';dpGridEl.style.gridTemplateColumns='repeat(7,1fr)';const today=todayISO(),y=dpViewDate.getFullYear(),m=dpViewDate.getMonth();dpMonthLbl.textContent=DP_MONTHS[m]+' '+y;const firstDow=new Date(y,m,1).getDay(),daysInMonth=new Date(y,m+1,0).getDate(),daysInPrev=new Date(y,m,0).getDate();dpGridEl.innerHTML='';for(let i=firstDow-1;i>=0;i--){const btn=document.createElement('button');btn.type='button';btn.className='dp-day dp-other-month';btn.textContent=daysInPrev-i;btn.disabled=true;dpGridEl.appendChild(btn);}for(let day=1;day<=daysInMonth;day++){const iso=dpIsoFromParts(y,m,day),btn=document.createElement('button');btn.type='button';btn.className='dp-day';btn.textContent=day;if(iso===today)btn.classList.add('dp-today');if(iso===dpSelected)btn.classList.add('dp-selected');if(iso>today){btn.disabled=true;}else{btn.addEventListener('click',()=>{dpSelected=iso;dpInput.value=dpDisplayFromISO(iso);dpCalEl.hidden=true;loadDayEntries(iso);});}dpGridEl.appendChild(btn);}const rem=(firstDow+daysInMonth)%7;if(rem>0)for(let i=1;i<=7-rem;i++){const btn=document.createElement('button');btn.type='button';btn.className='dp-day dp-other-month';btn.textContent=i;btn.disabled=true;dpGridEl.appendChild(btn);}}
    function dpRenderYearGrid(){dpCalMode='years';dpDayNames.style.display='none';dpGridEl.style.gridTemplateColumns='repeat(3,1fr)';const todayY=new Date().getFullYear();dpMonthLbl.textContent=dpYearPage+' – '+(dpYearPage+11);dpGridEl.innerHTML='';for(let i=0;i<12;i++){const yr=dpYearPage+i,btn=document.createElement('button');btn.type='button';btn.className='dp-day dp-year';btn.textContent=yr;if(yr===todayY)btn.classList.add('dp-today');if(yr===dpViewDate.getFullYear())btn.classList.add('dp-selected');if(yr>todayY){btn.disabled=true;}else{btn.addEventListener('click',()=>{dpViewDate=new Date(yr,dpViewDate.getMonth(),1);dpRenderCalendar();});}dpGridEl.appendChild(btn);}}
    dpMonthLbl.addEventListener('click',()=>{if(dpCalMode==='days'){dpYearPage=dpViewDate.getFullYear()-5;dpRenderYearGrid();}else dpRenderCalendar();});
    dpInput.addEventListener('click',()=>{if(dpCalEl.hidden){dpViewDate=dpSelected?new Date(dpSelected+'T12:00:00'):new Date();dpRenderCalendar();dpCalEl.hidden=false;}else{dpCalEl.hidden=true;}});
    document.getElementById('wpm-dp-prev').addEventListener('click',()=>{if(dpCalMode==='years'){dpYearPage-=12;dpRenderYearGrid();}else{dpViewDate=new Date(dpViewDate.getFullYear(),dpViewDate.getMonth()-1,1);dpRenderCalendar();}});
    document.getElementById('wpm-dp-next').addEventListener('click',()=>{if(dpCalMode==='years'){dpYearPage+=12;dpRenderYearGrid();}else{dpViewDate=new Date(dpViewDate.getFullYear(),dpViewDate.getMonth()+1,1);dpRenderCalendar();}});
    document.addEventListener('click',e=>{const wrap=document.getElementById('wpm-dp-wrap');if(!dpCalEl.hidden&&!e.composedPath().includes(wrap))dpCalEl.hidden=true;});
    function dpSetDate(iso){dpSelected=iso;dpInput.value=iso?dpDisplayFromISO(iso):'';dpCalEl.hidden=true;}

    /* ── Log Workout Modal ── */
    const logModal=document.getElementById('wp-log-modal'), dayHeading=document.getElementById('wpm-day-heading');
    const dayEntries=document.getElementById('wpm-day-entries'), dayEmpty=document.getElementById('wpm-day-empty');
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
    chip.hidden=true; speedField.classList.add('speed-inactive');
    document.getElementById('workout-speed-up').disabled=true; document.getElementById('workout-speed-down').disabled=true;
    setFormActive(false);
    document.getElementById('workout-speed-up').addEventListener('click',()=>{speedMph=Math.round((speedMph+0.5)*10)/10;speedVal.textContent=speedMph.toFixed(1);if(isSpeedBased){selectedMet=speedToMet(speedMph,speedTable);refreshKcal();}});
    document.getElementById('workout-speed-down').addEventListener('click',()=>{speedMph=Math.max(0.5,Math.round((speedMph-0.5)*10)/10);speedVal.textContent=speedMph.toFixed(1);if(isSpeedBased){selectedMet=speedToMet(speedMph,speedTable);refreshKcal();}});
    document.getElementById('workout-dur-up').addEventListener('click',()=>{duration=Math.min(duration+5,300);durVal.textContent=duration;refreshKcal();});
    document.getElementById('workout-dur-down').addEventListener('click',()=>{duration=Math.max(duration-5,5);durVal.textContent=duration;refreshKcal();});
    function buildDropdown(results){dropdown.innerHTML='';results.forEach((w,i)=>{const item=document.createElement('div');item.className='wsd-item';item.dataset.idx=i;item.innerHTML=`<span>${w.name}</span><span class="wsd-met">${w.speedBased?'speed-based':w.met+' MET'}</span>`;item.addEventListener('mousedown',e=>{e.preventDefault();selectWorkout(w);});dropdown.appendChild(item);});dropdownIdx=-1;}
    function selectWorkout(w){isSpeedBased=!!w.speedBased;selectedLabel=w.name;const su=document.getElementById('workout-speed-up'),sd=document.getElementById('workout-speed-down');if(isSpeedBased){speedTable=w.speedTable||'running';speedMph=w.defaultSpeed||5.0;speedVal.textContent=speedMph.toFixed(1);selectedMet=speedToMet(speedMph,speedTable);speedField.classList.remove('speed-inactive');su.disabled=false;sd.disabled=false;}else{selectedMet=w.met;speedField.classList.add('speed-inactive');su.disabled=true;sd.disabled=true;}chipLabel.textContent=w.name;chipTier.className='workout-chip-tier '+tierClass(selectedMet);typeInput.style.display='none';chip.hidden=false;chip.style.display='flex';typeInput.value='';dropdown.hidden=true;refreshKcal();setFormActive(true);}
    chipClear.addEventListener('click',()=>{chip.hidden=true;chip.style.display='none';typeInput.style.display='';speedField.classList.add('speed-inactive');typeInput.value='';selectedMet=null;selectedLabel=null;isSpeedBased=false;refreshKcal();setFormActive(false);});
    typeInput.addEventListener('input',()=>{const q=typeInput.value.trim().toLowerCase();if(!q){dropdown.hidden=true;return;}const matches=WORKOUTS.filter(w=>w.name.toLowerCase().includes(q));matches.sort((a,b)=>{const rank=n=>{const lo=n.toLowerCase();if(lo.startsWith(q))return 0;if(lo.split(/[\s(/]/).some(w=>w.startsWith(q)))return 1;return 2;};return rank(a.name)-rank(b.name);});const results=matches.slice(0,10);if(!results.length){dropdown.hidden=true;return;}buildDropdown(results);dropdown.hidden=false;});
    typeInput.addEventListener('keydown',e=>{const items=dropdown.querySelectorAll('.wsd-item');if(e.key==='ArrowDown'){e.preventDefault();dropdownIdx=Math.min(dropdownIdx+1,items.length-1);items.forEach((el,i)=>el.classList.toggle('highlighted',i===dropdownIdx));}else if(e.key==='ArrowUp'){e.preventDefault();dropdownIdx=Math.max(dropdownIdx-1,0);items.forEach((el,i)=>el.classList.toggle('highlighted',i===dropdownIdx));}else if(e.key==='Enter'&&dropdownIdx>=0){e.preventDefault();const q=typeInput.value.trim().toLowerCase();const results=WORKOUTS.filter(w=>w.name.toLowerCase().includes(q));if(results[dropdownIdx])selectWorkout(results[dropdownIdx]);}else if(e.key==='Escape'){dropdown.hidden=true;}});
    document.addEventListener('click',e=>{if(!e.target.closest('#workout-type-input,#workout-search-dropdown,.workout-search-wrap'))dropdown.hidden=true;});
    dropdown.addEventListener('wheel',e=>{e.preventDefault();dropdown.scrollTop+=e.deltaY;},{passive:false});
    const stagedEntriesEl=document.getElementById('wpm-staged-entries');
    let stagedActivities=[],pendingDeletes=[],loadedNote='';
    function renderStagedRow(item,idx){const el=document.createElement('div');el.className='wpm-staged-row';el.dataset.idx=idx;el.innerHTML=`<div class="wpm-staged-row-info"><span class="workout-badge ${tierClassByName(item.type)}">${item.type.replace(/</g,'&lt;')}</span></div><div class="wpm-day-dur">${item.duration_min} min</div><div class="wpm-day-kcal">${item.kcal.toLocaleString()} kcal</div><button class="table-delete-btn" aria-label="Remove">&#10005;</button>`;el.querySelector('.table-delete-btn').addEventListener('click',()=>{const i=parseInt(el.dataset.idx,10);stagedActivities.splice(i,1);el.remove();stagedEntriesEl.querySelectorAll('.wpm-staged-row').forEach((r,j)=>{r.dataset.idx=j;});if(!dayEntries.querySelectorAll('.wpm-day-row').length&&!stagedActivities.length)dayEmpty.hidden=false;});stagedEntriesEl.appendChild(el);}
    async function loadDayEntries(isoDate){const isToday=isoDate===todayISO();dayHeading.textContent=isToday?'Logged today':`Logged for ${fmtDate(isoDate)}`;dayEntries.querySelectorAll('.wpm-day-row').forEach(el=>el.remove());stagedEntriesEl.innerHTML='';stagedActivities=[];pendingDeletes=[];dayEmpty.hidden=false;const[rows,noteData]=await Promise.all([fetch('/api/workouts?date='+isoDate).then(r=>r.json()),fetch('/api/workout-day-note?date='+isoDate).then(r=>r.json())]);loadedNote=noteData.note||'';noteInput.value=loadedNote;if(rows.length){dayEmpty.hidden=true;rows.forEach(w=>{const el=document.createElement('div');el.className='wpm-day-row';el.dataset.wid=w.id;el.innerHTML=`<div class="wpm-day-row-info"><span class="workout-badge ${tierClassByName(w.type)}">${w.type.replace(/</g,'&lt;')}</span></div><div class="wpm-day-dur">${w.duration_min} min</div><div class="wpm-day-kcal">${w.kcal.toLocaleString()} kcal</div><button class="table-delete-btn" aria-label="Delete">&#10005;</button>`;el.querySelector('.table-delete-btn').addEventListener('click',()=>{pendingDeletes.push({id:w.id,type:w.type,duration_min:w.duration_min});el.remove();if(!dayEntries.querySelectorAll('.wpm-day-row').length&&!stagedActivities.length)dayEmpty.hidden=false;});dayEntries.appendChild(el);});}}
    function clearActivityForm(){typeInput.value='';typeInput.style.display='';chip.hidden=true;chip.style.display='none';speedField.classList.add('speed-inactive');document.getElementById('workout-speed-up').disabled=true;document.getElementById('workout-speed-down').disabled=true;selectedMet=null;selectedLabel=null;isSpeedBased=false;speedMph=5.0;speedVal.textContent='5.0';duration=30;durVal.textContent='30';setFormActive(false);refreshKcal();dropdown.hidden=true;}
    function clearDayView(){dayHeading.textContent='Select a date';dayEntries.querySelectorAll('.wpm-day-row').forEach(el=>el.remove());stagedEntriesEl.innerHTML='';stagedActivities=[];pendingDeletes=[];loadedNote='';noteInput.value='';dayEmpty.hidden=false;}
    async function openModal(isoDate){try{const w=await fetch('/api/latest-weight').then(r=>r.json());weightKg=w.weight_lbs?w.weight_lbs/2.2046:80;}catch{weightKg=80;}let startDate=isoDate;if(!startDate){const today=todayISO();const todayRows=await fetch('/api/workouts?date='+today).then(r=>r.json());startDate=todayRows.length?'':today;}dpSetDate(startDate);clearActivityForm();if(startDate)await loadDayEntries(startDate);else clearDayView();logModal.hidden=false;requestAnimationFrame(()=>document.getElementById('wpm-entries-scroll').dispatchEvent(new Event('scroll')));typeInput.focus();}
    function closeModal(){logModal.hidden=true;dpCalEl.hidden=true;dropdown.hidden=true;}
    function hasUnsavedChanges(){return stagedActivities.length>0||pendingDeletes.length>0||noteInput.value.trim()!==loadedNote;}
    function maybeClose(){if(!hasUnsavedChanges()){closeModal();return;}window.showAppConfirm('Discard changes?','You have unsaved changes. Discard them?','Discard',closeModal);}
    document.getElementById('wp-add-btn').addEventListener('click', () => openModal());
    document.getElementById('wp-modal-x').addEventListener('click', maybeClose);
    document.getElementById('wp-modal-cancel').addEventListener('click', maybeClose);
    logModal.addEventListener('click', e => { if (e.target===logModal) maybeClose(); });
    logModal.addEventListener('keydown', e => { if (e.key==='Escape') maybeClose(); });
    document.getElementById('wpm-add-activity-btn').addEventListener('click',()=>{if(!selectedLabel)return;const kcal=calcKcal(),typeLabel=isSpeedBased?`${selectedLabel} (${speedMph.toFixed(1)} mph)`:selectedLabel;const item={type:typeLabel,duration_min:duration,kcal};stagedActivities.push(item);renderStagedRow(item,stagedActivities.length-1);dayEmpty.hidden=true;clearActivityForm();});
    function showDeleteConfirm(onCommit){const modal=document.getElementById('wp-del-check-modal'),checks=document.getElementById('wp-del-checks'),okBtn=document.getElementById('wp-del-check-ok');checks.innerHTML='';pendingDeletes.forEach((d,i)=>{const lbl=document.createElement('label');lbl.className='row-delete-check-label';const cb=document.createElement('input');cb.type='checkbox';cb.checked=true;cb.dataset.idx=i;lbl.append(cb,document.createTextNode(`${d.type} (${d.duration_min} min)`));checks.appendChild(lbl);});function syncOk(){okBtn.disabled=checks.querySelectorAll('input:checked').length===0;}checks.querySelectorAll('input[type="checkbox"]').forEach(cb=>cb.addEventListener('change',syncOk));okBtn.disabled=false;modal.hidden=false;document.getElementById('wp-del-check-cancel').onclick=()=>{modal.hidden=true;};okBtn.onclick=()=>{modal.hidden=true;const kept=new Set();checks.querySelectorAll('input[type="checkbox"]').forEach(cb=>{if(!cb.checked)kept.add(parseInt(cb.dataset.idx,10));});pendingDeletes=pendingDeletes.filter((_,i)=>kept.has(i));onCommit();};}
    document.getElementById('wp-modal-save').addEventListener('click', async () => {
        if (!dpSelected) { dpInput.focus(); return; }
        const isoDate = dpSelected;
        async function commitSave(){for(const d of pendingDeletes)await fetch('/api/workout/'+d.id,{method:'DELETE'});for(const item of stagedActivities)await fetch('/api/workout',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({date:isoDate,type:item.type,duration_min:item.duration_min,kcal:item.kcal,note:''})});await fetch('/api/workout-day-note',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({date:isoDate,note:noteInput.value.trim()})});closeModal();await Promise.all([loadTable(),refreshStats()]);}
        if(pendingDeletes.length>0){showDeleteConfirm(commitSave);}else{await commitSave();}
    });

    /* ── Logged-entries scrollbar ── */
    (function(){const scroll=document.getElementById('wpm-entries-scroll'),thumb=document.getElementById('wpm-scroll-thumb');function sync(){const track=thumb.parentElement;if(scroll.scrollHeight<=scroll.clientHeight){thumb.style.display='none';return;}thumb.style.display='block';const ratio=scroll.clientHeight/scroll.scrollHeight,thumbH=Math.max(16,ratio*track.clientHeight),maxTop=track.clientHeight-thumbH,pct=scroll.scrollTop/(scroll.scrollHeight-scroll.clientHeight);thumb.style.height=thumbH+'px';thumb.style.top=(pct*maxTop)+'px';}scroll.addEventListener('scroll',sync);new MutationObserver(sync).observe(scroll,{childList:true,subtree:true});let drag=false,dragY=0,dragTop=0;thumb.addEventListener('mousedown',e=>{drag=true;dragY=e.clientY;dragTop=scroll.scrollTop;e.preventDefault();e.stopPropagation();});document.addEventListener('mousemove',e=>{if(!drag)return;const track=thumb.parentElement,thumbH=parseFloat(thumb.style.height)||16,maxTop=track.clientHeight-thumbH,maxScroll=scroll.scrollHeight-scroll.clientHeight;scroll.scrollTop=Math.max(0,Math.min(dragTop+(maxTop>0?(e.clientY-dragY)/maxTop:0)*maxScroll,maxScroll));});document.addEventListener('mouseup',()=>{drag=false;});})();

    /* ── Table page-edge scrollbar ── */
    (function(){const wrap=document.querySelector('.wp-table-wrap'),track=document.getElementById('wp-scrollbar-track'),thumb=document.getElementById('wp-scrollbar-thumb');function sync(){if(wrap.scrollHeight<=wrap.clientHeight){thumb.style.display='none';return;}const thumbH=Math.max((wrap.clientHeight/wrap.scrollHeight)*track.clientHeight,30),maxTop=track.clientHeight-thumbH,maxScroll=wrap.scrollHeight-wrap.clientHeight;thumb.style.display='block';thumb.style.height=thumbH+'px';thumb.style.top=(wrap.scrollTop/maxScroll)*maxTop+'px';}wrap.addEventListener('scroll',sync);new ResizeObserver(sync).observe(document.getElementById('wp-table-inner'));let drag=false,dragY=0,dragScroll=0;function startDrag(e){drag=true;dragY=e.clientY;dragScroll=wrap.scrollTop;e.preventDefault();}thumb.addEventListener('mousedown',startDrag);track.addEventListener('mousedown',e=>{if(e.target===thumb)return;const tr=track.getBoundingClientRect(),th=parseFloat(thumb.style.height)||30,mt=track.clientHeight-th,ms=wrap.scrollHeight-wrap.clientHeight,cy=Math.min(Math.max(e.clientY-tr.top-th/2,0),mt);wrap.scrollTop=(cy/mt)*ms;startDrag(e);});document.addEventListener('mousemove',e=>{if(!drag)return;const mt=track.clientHeight-parseFloat(thumb.style.height),ms=wrap.scrollHeight-wrap.clientHeight;wrap.scrollTop=Math.max(0,Math.min(ms,dragScroll+(e.clientY-dragY)*(ms/mt)));});document.addEventListener('mouseup',()=>{drag=false;});})();

    /* ── Init ── */
    (async () => { await Promise.all([loadTable(), refreshStats()]); })();
