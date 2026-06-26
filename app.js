'use strict';

// ─────────────────────────────────────────────────────────────────────────────
// Constants
// ─────────────────────────────────────────────────────────────────────────────
const STATE_KEY = 'tracker_state';
const WS_URL_KEY = 'tracker_ws_url';
const ROOM_CODE_KEY = 'tracker_room_code';
const SPOILER_KEY = 'tracker_spoiler_log';

let applyingRemote = false;

const KINGDOMS = [
  { name: 'Cascade Kingdom', img: 'assets/Cascade.png', multi: 'assets/Cascade_Multi.png', min: 1, max: 10, moontick: 'assets/moontickCascade.png' },
  { name: 'Sand Kingdom', img: 'assets/Sand.png', multi: 'assets/Sand_Multi.png', min: 11, max: 21, moontick: 'assets/moontickSand.png' },
  { name: 'Lake Kingdom', img: 'assets/Lake.png', multi: 'assets/Lake_Multi.png', min: 3, max: 13, moontick: 'assets/moontickLake.png' },
  { name: 'Wooded Kingdom', img: 'assets/Wooded.png', multi: 'assets/Wooded_Multi.png', min: 11, max: 21, moontick: 'assets/moontickWooded.png' },
  { name: 'Lost Kingdom', img: 'assets/Lost.png', multi: 'assets/Lost_Multi.png', min: 5, max: 15, moontick: 'assets/moontickLost.png' },
  { name: 'Metro Kingdom', img: 'assets/Metro.png', multi: 'assets/Metro_Multi.png', min: 15, max: 25, moontick: 'assets/moontickMetro.png' },
  { name: 'Snow Kingdom', img: 'assets/Snow.png', multi: 'assets/Snow_Multi.png', min: 5, max: 15, moontick: 'assets/moontickSnow.png' },
  { name: 'Seaside Kingdom', img: 'assets/Seaside.png', multi: 'assets/Seaside_Multi.png', min: 5, max: 15, moontick: 'assets/moontickSeaside.png' },
  { name: 'Luncheon Kingdom', img: 'assets/Luncheon.png', multi: 'assets/Luncheon_Multi.png', min: 13, max: 23, moontick: 'assets/moontickLuncheon.png' },
  { name: 'Ruined Kingdom', img: 'assets/Ruin.png', multi: 'assets/Ruined_Multi.png', min: 1, max: 8, moontick: 'assets/moontickRuined.png' },
  { name: 'Bowser Kingdom', img: 'assets/Bowser.png', multi: 'assets/Bowser_Multi.png', min: 3, max: 13, moontick: 'assets/moontickBowser.png' },
];

// Optional counters — NOT counted toward total moons
// Moon Kingdom appears in the main list below Bowser; Cap/Cloud/Star/Dark are right-column
const OPTIONAL_COUNTERS = [
  { key: 'moon_kingdom', label: 'Moon Kingdom', img: 'assets/Moon.png', moontick: 'assets/moontickMoon.png', inlineBelow: 'Bowser Kingdom', hasLockPeace: true },
  { key: 'cap_kingdom',   label: 'Cap Kingdom',   img: 'assets/Cap.png',  side: true, order: 1 },
  { key: 'cloud_kingdom', label: 'Cloud Kingdom', img: 'assets/Cloud.png', side: true, order: 2 },
  { key: 'star_counter',  label: 'Capture',       img: 'assets/Star.png', side: true, order: 3 },
  { key: 'dark_counter',  label: 'Movement',      img: 'assets/Dark.png', side: true, order: 4 },
];

const CAPTURE_ICONS = [
  { key: 'parabones', locked: 'assets/Parabones_Capture_Locked.png', unlocked: 'assets/Parabones_Capture.png' },
  { key: 'banzai', locked: 'assets/Banzai_Bill_Capture_Locked.png', unlocked: 'assets/Banzai_Bill_Capture.png' },
  { key: 'wire', locked: 'assets/Spark_pylon_Capture_Locked.png', unlocked: 'assets/Spark_pylon_Capture.png' },
  { key: 'bowser', locked: 'assets/Bowser_Capture_Locked.png', unlocked: 'assets/Bowser_Capture.png' },
];

const ABILITY_ICONS = [
  { key: 'jump', locked: 'assets/Long_Jump_Locked.png', unlocked: 'assets/Long_Jump.png' },
  { key: 'cap', locked: 'assets/Cappy_Locked.png', unlocked: 'assets/Cappy.png' },
  { key: 'wall', locked: 'assets/Wall_Jump_Locked.png', unlocked: 'assets/Wall_Jump.png' },
];

const PICKER_ICONS = [
  'Cascade.png', 'Sand.png', 'Lake.png', 'Wooded.png', 'Lost.png', 'Metro.png',
  'Snow.png', 'Seaside.png', 'Luncheon.png', 'Ruin.png', 'Bowser.png',
  'Cap.png', 'Dark.png', 'Star.png', "Moon.png", "Moon_Dark.png", "checkmark.png", "xmark.png",
];

const DEFAULT_SETTINGS = {
  show_moon_total: true,
  moon_requirement: 124,
  show_icon_colors: true,
  show_ability_lock: true,
  show_peace: true,
  show_captures: true,
  show_save_buttons: false,
  show_multi_moon: true,
  show_moon_range: true,
  show_complete_color: false,
  overlay_scale: 1,
  notes_scroll_px: 500,
  scroll_left_binding: { type: 'mouse', code: 3 },
  scroll_right_binding: { type: 'mouse', code: 4 },
  white_icon_mode: false,
  show_moon_kingdom: false,
  show_cap_kingdom: false,
  show_cloud_kingdom: false,
  show_star_counter: false,
  show_dark_counter: false,
  obs_hide_optional: false,
  obs_bg_color: 'transparent',
  show_moontick: false,
  button_visibility: {
    'btn-toggle-visibility': 1,
    'btn-generate-room': 1,
    'btn-connect-room': 1,
    'btn-copy-obs-url': 1,
    'btn-obs': 1,
    'btn-obs-info': 1,
    'btn-clear': 1,
    'btn-notes': 1,
    'btn-map': 1,
  },
};

function cloneDefaultSettings() {
  return JSON.parse(JSON.stringify(DEFAULT_SETTINGS));
}

const LOADING_ZONES_TEMPLATE = {
  'Cap': { color: '#fff500', icon: 'Cap.png', zones: { 'Orange': { num: 2 }, 'Paragoomba': { num: 2 }, 'Frog': { num: 2 }, 'Rolling On': { num: 2 } } },
  'Cascade': { color: '#ff9900', icon: 'Cascade.png', zones: { 'Dino': { num: 2 }, '2D': { num: 2 }, 'Chain Chomp': { num: 2 }, 'Swings': { num: 2 }, 'Windy': { num: 2 } } },
  'Sand': { color: '#8bf12c', icon: 'Sand.png', zones: { "Icy Cave": { num: 1 }, "Moe-eye": { num: 2 }, "Shop": { num: 1 }, "Employees": { num: 1 }, "Slots": { num: 1 }, "Rumble": { num: 1 }, "Outfit": { num: 1 }, "Jaxi Ruins": { num: 2 }, "Bullet Bill": { num: 2 }, "Gushen": { num: 2 }, "Sphynx": { num: 1 }, "Moving Platform": { num: 2 }, "Rocket": { num: 2 }, "Colossal Ruins": { num: 2 } } },
  'Lake': { color: '#e46cab', icon: 'Lake.png', zones: { "Poison Waves": { num: 2 }, "Zipper": { num: 2 }, "Grab Climb": { num: 2 }, "Shop": { num: 1 }, "Puzzle": { num: 1 } } },
  'Wooded': { color: '#1e65e7', icon: 'Wooded.png', zones: { "DW Odyssey": { num: 0 }, "DW Red Maze": { num: 0 }, "DW Pond": { num: 0 }, "DW Treasure": { num: 1 }, "DW Outfit": { num: 1 }, "Rocket": { num: 2 }, "Sheep": { num: 2 }, "Tank": { num: 2 }, "Vine Clouds": { num: 2 }, "Breakdown": { num: 2 }, "Invisible": { num: 2 }, "Flooded Pipes": { num: 2 }, "Flower Road": { num: 2 }, "Treasure Room": { num: 1 } } },
  'Lost': { color: '#e71edd', icon: 'Lost.png', zones: { 'Wiggler': { num: 2 }, 'Shop': { num: 1 }, 'Klepto': { num: 2 } } },
  'Metro': { color: '#de7d5e', icon: 'Metro.png', zones: { "Yellow Shop": { num: 1 }, "Purple Shop": { num: 1 }, "Dino": { num: 2 }, "Bullet Billding": { num: 2 }, "Taxi": { num: 2 }, "Notes": { num: 1 }, "2D": { num: 2 }, "Slots": { num: 1 }, "People": { num: 2 }, "Outfit": { num: 2 }, "Rocket": { num: 2 }, "Dark": { num: 2 }, "Scaffolding": { num: 2 }, "Scooter": { num: 2 }, "Rotating Maze": { num: 2 }, "RC Car": { num: 2 } } },
  'Snow': { color: '#e7930a', icon: 'Snow.png', zones: { "Puzzle": { num: 1 }, "Capless": { num: 2 }, "Rocket Flower": { num: 2 }, "Iceburn": { num: 2 }, "Flower Road": { num: 2 }, "Tracewalking": { num: 1 }, "Clouds": { num: 2 }, "Outfit": { num: 2 }, "Shop": { num: 1 } } },
  'Seaside': { color: '#b36fe9', icon: 'Seaside.png', zones: { "Well Enter": { num: 1 }, "Well Exit": { num: 1 }, "Rumble": { num: 1 }, "Rocket": { num: 2 }, "Outfit": { num: 1 }, "Gushen": { num: 2 }, "Sphynx": { num: 1 }, "Pokio": { num: 2 }, "Lava Rising": { num: 2 }, "Sandy Bottom": { num: 1 }, "Spinning Maze": { num: 2 } } },
  'Luncheon': { color: '#3fddbb', icon: 'Luncheon.png', zones: { "Magma Swamp": { num: 2 }, "Forks": { num: 2 }, "Cheese Rocks": { num: 2 }, "Veggie Room": { num: 1 }, "Slots": { num: 1 }, "Shop": { num: 1 }, "Outfit": { num: 2 }, "Spinning Athletics": { num: 2 }, "Lava Islands": { num: 2 }, "Volcano Cave": { num: 2 }, "Gears": { num: 2 }, "Magma Path": { num: 2 } } },
  'Ruined': { color: '#ffd7e2', icon: 'Ruin.png', zones: { "Chargin' Chuck": { num: 2 }, 'Rocket': { num: 2 } } },
  "Bowser's": { color: '#d3304c', icon: 'Bowser.png', zones: { "Jizo": { num: 2 }, "Shop": { num: 1 }, "Outfit": { num: 2 }, "Treasure Room": { num: 1 }, "Spinning Tower": { num: 2 }, "Vine Clouds": { num: 2 }, "Hexagon Tower": { num: 2 }, "Wooden Tower": { num: 2 } } },
  'Mushroom': { color: '#fff672', icon: 'Star.png', zones: { "Shop": { num: 1 }, "Castle Door": { num: 2 }, "Outfit": { num: 2 }, "Cloud Sea": { num: 2 }, "Well": { num: 2 }, "Knucklotec": { num: 1 }, "Torkdrift": { num: 1 }, "Mechawiggler": { num: 1 }, "Octopus": { num: 1 }, "Cookatiel": { num: 1 }, "Dragon": { num: 1 }, "Rocket": { num: 2 } } },
  'Darkside': { color: '#fff2c6', icon: 'Dark.png', zones: { 'Breakdown': { num: 2 }, 'Invisible': { num: 2 }, 'Vanishing': { num: 2 }, 'Yoshi Siege': { num: 2 }, 'Lava Rising': { num: 2 }, 'Magma Swamp': { num: 2 } } },
  'Darkerside': { color: '#fff2c6', icon: 'Dark.png', zones: { 'End': { num: 1 } } },
};

const ZONE_SPLIT_THRESHOLD = 10;
const MOBILE_BREAKPOINT = 540;

function bindingLabel(binding) {
  if (!binding) return 'Not Set';
  if (binding.type === 'mouse') {
    const names = { 0: 'Left Click', 1: 'Middle Click', 2: 'Right Click', 3: 'Mouse 4', 4: 'Mouse 5' };
    return names[binding.code] !== undefined ? names[binding.code] : `Mouse ${binding.code + 1}`;
  }
  if (binding.type === 'key') {
    const map = {
      ArrowLeft: 'Left Arrow', ArrowRight: 'Right Arrow',
      ArrowUp: 'Up Arrow', ArrowDown: 'Down Arrow',
      Space: 'Space', Enter: 'Enter', Tab: 'Tab',
    };
    if (map[binding.code]) return map[binding.code];
    if (binding.code.startsWith('Key')) return binding.code.slice(3);
    if (binding.code.startsWith('Digit')) return binding.code.slice(5);
    return binding.code;
  }
  return 'Unknown';
}

const TOGGLE_SETTINGS = [
  { id: 'toggle-moon-total',     key: 'show_moon_total' },
  { id: 'toggle-icon-colors',    key: 'show_icon_colors' },
  { id: 'toggle-ability-lock',   key: 'show_ability_lock' },
  { id: 'toggle-peace',          key: 'show_peace' },
  { id: 'toggle-captures',       key: 'show_captures' },
  { id: 'toggle-save-buttons',   key: 'show_save_buttons' },
  { id: 'toggle-multi-moon',     key: 'show_multi_moon' },
  { id: 'toggle-moon-range',     key: 'show_moon_range' },
  { id: 'toggle-complete-color', key: 'show_complete_color' },
  { id: 'toggle-white-icons',    key: 'white_icon_mode' },
  { id: 'toggle-moon-kingdom',   key: 'show_moon_kingdom' },
  { id: 'toggle-cap-kingdom',    key: 'show_cap_kingdom' },
  { id: 'toggle-cloud-kingdom',  key: 'show_cloud_kingdom' },
  { id: 'toggle-star-counter',   key: 'show_star_counter' },
  { id: 'toggle-dark-counter',   key: 'show_dark_counter' },
  { id: 'toggle-obs-hide-optional', key: 'obs_hide_optional' },
  { id: 'toggle-moontick',       key: 'show_moontick' },
];

// ─────────────────────────────────────────────────────────────────────────────
// State
// ─────────────────────────────────────────────────────────────────────────────
let state = {};

function buildDefaultLoadingZones() {
  const result = {};
  for (const [kingdom, data] of Object.entries(LOADING_ZONES_TEMPLATE)) {
    result[kingdom] = { color: data.color, icon: data.icon, zones: {} };
    for (const [zone, zd] of Object.entries(data.zones)) {
      result[kingdom].zones[zone] = { note: '', icon: 'Moon.png', icon2: 'Moon.png', collapsed: false, num: zd.num };
    }
  }
  return result;
}

function getDefaultState() {
  return {
    settings: cloneDefaultSettings(),
    moons: KINGDOMS.map(() => ({ count: 0, max: null, lock: false, peace: false, multi: false })),
    optional_counters: Object.fromEntries(OPTIONAL_COUNTERS.map(c => [c.key, { count: 0, max: null, lock: false, peace: false }])),
    captures: { parabones: false, banzai: false, wire: false, bowser: false },
    abilities: { jump: false, cap: false, wall: false },
    loading_zones: buildDefaultLoadingZones(),
    kingdom_collapsed: Object.fromEntries(Object.keys(LOADING_ZONES_TEMPLATE).map(k => [k, false])),
  };
}

function loadState() {
  try {
    const raw = localStorage.getItem(STATE_KEY);
    if (!raw) { state = getDefaultState(); return; }
    const saved = JSON.parse(raw);
    state = getDefaultState();
    if (saved.settings) {
      for (const key of Object.keys(DEFAULT_SETTINGS)) {
        if (key === 'button_visibility') {
          if (saved.settings.button_visibility && typeof saved.settings.button_visibility === 'object') {
            state.settings.button_visibility = Object.assign({}, DEFAULT_SETTINGS.button_visibility, saved.settings.button_visibility);
          }
        } else if (key in saved.settings) {
          state.settings[key] = saved.settings[key];
        }
      }
    }
    if (Array.isArray(saved.moons)) {
      saved.moons.forEach((m, i) => {
        if (state.moons[i]) Object.assign(state.moons[i], m);
      });
    }
    if (saved.optional_counters) {
      for (const k of Object.keys(state.optional_counters)) {
        if (saved.optional_counters[k]) Object.assign(state.optional_counters[k], saved.optional_counters[k]);
      }
    }
    if (saved.captures) Object.assign(state.captures, saved.captures);
    if (saved.abilities) Object.assign(state.abilities, saved.abilities);
    if (saved.loading_zones) {
      for (const [kingdom, data] of Object.entries(state.loading_zones)) {
        if (!saved.loading_zones[kingdom]) continue;
        const savedKingdom = saved.loading_zones[kingdom];
        for (const zone of Object.keys(data.zones)) {
          if (savedKingdom.zones && savedKingdom.zones[zone]) {
            Object.assign(state.loading_zones[kingdom].zones[zone], savedKingdom.zones[zone]);
          }
        }
      }
    }
    if (saved.kingdom_collapsed) {
      for (const k of Object.keys(state.kingdom_collapsed)) {
        if (k in saved.kingdom_collapsed) state.kingdom_collapsed[k] = saved.kingdom_collapsed[k];
      }
    }
  } catch (e) {
    console.error('Failed to load state:', e);
    state = getDefaultState();
  }
}

function saveState() {
  try {
    localStorage.setItem(STATE_KEY, JSON.stringify(state));
  } catch (e) {
    console.error('Failed to save state:', e);
  }
  if (!applyingRemote && window.SMOSync && window.SMOSync.getRoom()) {
    window.SMOSync.broadcast(state);
  }
}

// ─────────────────────────────────────────────────────────────────────────────
// Total Moon Count
// ─────────────────────────────────────────────────────────────────────────────
function getTotalMoons() {
  // Sum main KINGDOMS plus Moon Kingdom (counted toward total)
  const mainTotal = state.moons.reduce((sum, m) => sum + (m.count || 0), 0);
  const mkCount = (state.optional_counters && state.optional_counters['moon_kingdom'])
    ? (state.optional_counters['moon_kingdom'].count || 0)
    : 0;
  const mkShown = state.settings && state.settings.show_moon_kingdom;
  return mainTotal + (mkShown ? mkCount : 0);
}

function refreshTotalMoonDisplay() {
  const el = document.getElementById('total-moon-display');
  if (!el) return;
  const total = getTotalMoons();
  const req = state.settings.moon_requirement || 124;
  el.textContent = `${total} / ${req}`;
  el.classList.toggle('count-complete', total >= req && state.settings.show_complete_color);
}

// ─────────────────────────────────────────────────────────────────────────────
// Moon Rows Build
// ─────────────────────────────────────────────────────────────────────────────
function buildAllMoonRows() {
  const container = document.getElementById('moon-rows');
  container.innerHTML = '';

  KINGDOMS.forEach((k, i) => {
    container.appendChild(buildMoonRow(i));
    // Insert Moon Kingdom row directly below Bowser Kingdom
    if (k.name === 'Bowser Kingdom') {
      container.appendChild(buildMoonKingdomRow());
    }
  });

  buildSideCounters();
}

function buildMoonRow(i) {
  const kingdom = KINGDOMS[i];
  const row = document.createElement('div');
  row.className = 'moon-row';
  row.dataset.idx = i;

  function makeCounterSpacer() {
    const sp = document.createElement('span');
    sp.className = 'counter-spacer';
    return sp;
  }

  // ── Left group: lock (above) + peace (below) + kingdom icon + moontick ──
  const left = document.createElement('div');
  left.className = 'moon-row-left';

  // Lock/Peace stacked vertically
  const lockPeaceStack = document.createElement('div');
  lockPeaceStack.className = 'lock-peace-stack';

  const lockBtn = document.createElement('button');
  lockBtn.className = 'icon-btn lock-btn';
  lockBtn.title = 'Toggle lock';
  lockBtn.innerHTML = `<img src="assets/lock.png" alt="lock">`;
  lockBtn.addEventListener('click', () => { toggleLock(i); saveState(); });

  const peaceBtn = document.createElement('button');
  peaceBtn.className = 'icon-btn peace-btn';
  peaceBtn.title = 'Toggle peace';
  peaceBtn.innerHTML = `<img src="assets/peace.png" alt="peace">`;
  peaceBtn.addEventListener('click', () => { togglePeace(i); saveState(); });

  lockPeaceStack.appendChild(lockBtn);
  lockPeaceStack.appendChild(peaceBtn);

  const kingdomImg = document.createElement('img');
  kingdomImg.src = kingdom.img;
  kingdomImg.alt = kingdom.name;
  kingdomImg.className = 'kingdom-icon';
  kingdomImg.title = kingdom.name;

  // Moon tick icon (SmallAnt-style)
  const moontickImg = document.createElement('img');
  moontickImg.src = kingdom.moontick || kingdom.img;
  moontickImg.alt = 'moontick';
  moontickImg.className = 'moontick-icon';
  moontickImg.title = kingdom.name + ' tick';

  left.appendChild(lockPeaceStack);
  left.appendChild(kingdomImg);
  left.appendChild(moontickImg);

  // ── Counter group ──
  const counter = document.createElement('div');
  counter.className = 'moon-row-counter';

  const decrBtn = document.createElement('button');
  decrBtn.className = 'count-btn decr-btn';
  decrBtn.textContent = '−';
  decrBtn.addEventListener('click', () => { decrement(i); saveState(); });

  const minStack = document.createElement('div');
  minStack.className = 'range-stack range-min';
  minStack.innerHTML = `<span class="range-label">min</span><span class="range-value">${kingdom.min}</span>`;

  const countLabel = document.createElement('span');
  countLabel.className = 'count-label';

  const maxStack = document.createElement('div');
  maxStack.className = 'range-stack range-max';
  maxStack.innerHTML = `<span class="range-label">max</span><span class="range-value">${kingdom.max}</span>`;

  if (!state.settings.show_moon_range) {
    minStack.classList.add('hidden');
    maxStack.classList.add('hidden');
  }

  const incrBtn = document.createElement('button');
  incrBtn.className = 'count-btn incr-btn';
  incrBtn.textContent = '+';
  incrBtn.addEventListener('click', () => { increment(i); saveState(); });

  counter.appendChild(decrBtn);
  counter.appendChild(makeCounterSpacer());
  counter.appendChild(minStack);
  counter.appendChild(makeCounterSpacer());
  counter.appendChild(countLabel);
  counter.appendChild(makeCounterSpacer());
  counter.appendChild(maxStack);
  counter.appendChild(makeCounterSpacer());
  counter.appendChild(incrBtn);

  // ── Entry group ──
  const entryGroup = document.createElement('div');
  entryGroup.className = 'moon-row-entry';

  const multiBtn = document.createElement('button');
  multiBtn.className = 'multi-moon-btn';
  multiBtn.title = `Multi Moon (+3)`;
  const multiImg = document.createElement('img');
  multiImg.src = kingdom.multi;
  multiImg.alt = 'Multi Moon';
  multiBtn.appendChild(multiImg);
  if (!state.settings.show_multi_moon) multiBtn.classList.add('hidden');
  multiBtn.addEventListener('click', () => { addMulti(i); saveState(); });

  const maxEntry = document.createElement('input');
  maxEntry.type = 'number';
  maxEntry.className = 'max-entry';
  maxEntry.placeholder = '?';
  maxEntry.min = '0';
  maxEntry.max = '9999';
  maxEntry.addEventListener('input', () => {
    if (!state.settings.show_save_buttons) {
      const v = parseInt(maxEntry.value);
      state.moons[i].max = (!isNaN(v) && v >= 0) ? v : null;
      refreshCountLabel(i);
      saveState();
    }
  });

  const saveBtn = document.createElement('button');
  saveBtn.className = 'save-btn';
  saveBtn.textContent = 'Save';
  saveBtn.addEventListener('click', () => { saveMax(i); });

  entryGroup.appendChild(multiBtn);
  entryGroup.appendChild(maxEntry);
  entryGroup.appendChild(saveBtn);

  row.appendChild(left);
  row.appendChild(counter);
  row.appendChild(entryGroup);

  refreshMoonRow(i, row);
  return row;
}

// Moon Kingdom inline row (below Bowser, not counted toward total)
function buildMoonKingdomRow() {
  const wrapper = document.createElement('div');
  wrapper.id = 'moon-kingdom-row-wrap';
  wrapper.className = 'moon-kingdom-row-wrap';
  if (!state.settings.show_moon_kingdom) wrapper.classList.add('hidden');

  const row = document.createElement('div');
  row.className = 'moon-row optional-counter-row';
  row.dataset.optKey = 'moon_kingdom';

  const left = document.createElement('div');
  left.className = 'moon-row-left';

  // Lock/Peace stack (same as main rows)
  const lockPeaceStack = document.createElement('div');
  lockPeaceStack.className = 'lock-peace-stack';

  const lockBtn = document.createElement('button');
  lockBtn.className = 'icon-btn lock-btn';
  lockBtn.title = 'Toggle lock';
  const mkState = state.optional_counters['moon_kingdom'] || {};
  lockBtn.innerHTML = `<img src="${mkState.lock ? 'assets/unlock.png' : 'assets/lock.png'}" alt="lock">`;
  lockBtn.addEventListener('click', () => {
    state.optional_counters['moon_kingdom'].lock = !state.optional_counters['moon_kingdom'].lock;
    lockBtn.querySelector('img').src = state.optional_counters['moon_kingdom'].lock ? 'assets/unlock.png' : 'assets/lock.png';
    saveState();
  });

  const peaceBtn = document.createElement('button');
  peaceBtn.className = 'icon-btn peace-btn';
  peaceBtn.title = 'Toggle peace';
  peaceBtn.innerHTML = `<img src="${mkState.peace ? 'assets/peace_unlock.png' : 'assets/peace.png'}" alt="peace">`;
  peaceBtn.addEventListener('click', () => {
    state.optional_counters['moon_kingdom'].peace = !state.optional_counters['moon_kingdom'].peace;
    peaceBtn.querySelector('img').src = state.optional_counters['moon_kingdom'].peace ? 'assets/peace_unlock.png' : 'assets/peace.png';
    saveState();
  });

  lockBtn.classList.toggle('hidden', !state.settings.show_peace);
  peaceBtn.classList.toggle('hidden', !state.settings.show_peace);

  lockPeaceStack.appendChild(lockBtn);
  lockPeaceStack.appendChild(peaceBtn);

  const img = document.createElement('img');
  img.src = 'assets/Moon.png';
  img.alt = 'Moon Kingdom';
  img.className = 'kingdom-icon';

  const moontick = document.createElement('img');
  moontick.src = 'assets/moontickMoon.png';
  moontick.alt = 'moontick';
  moontick.className = 'moontick-icon';
  moontick.classList.toggle('hidden', !state.settings.show_moontick);

  const label = document.createElement('span');
  label.className = 'optional-label';
  label.textContent = 'Moon';

  const notCounted = document.createElement('span');
  notCounted.className = 'not-counted-badge counted-badge';
  notCounted.textContent = '✓ total';
  notCounted.title = 'Counts toward moon total';

  left.appendChild(lockPeaceStack);
  left.appendChild(img);
  left.appendChild(moontick);
  left.appendChild(label);
  left.appendChild(notCounted);

  const counter = buildOptionalCounter('moon_kingdom');
  row.appendChild(left);
  row.appendChild(counter);
  wrapper.appendChild(row);
  return wrapper;
}

// Side counters (Cap, Cloud, Star, Dark) — right column
function buildSideCounters() {
  let sideCol = document.getElementById('side-counters-col');
  if (!sideCol) return;
  sideCol.innerHTML = '';

  const sideOpts = OPTIONAL_COUNTERS.filter(c => c.side).sort((a, b) => a.order - b.order);
  const obsHide = state.settings.obs_hide_optional;

  sideOpts.forEach(opt => {
    const shown = state.settings[`show_${opt.key}`];
    const wrap = document.createElement('div');
    wrap.className = 'side-counter-item';
    wrap.dataset.sideKey = opt.key;
    if (!shown) wrap.classList.add('hidden');

    const img = document.createElement('img');
    img.src = opt.img;
    img.alt = opt.label;
    img.className = 'side-counter-icon';

    const notCounted = document.createElement('span');
    notCounted.className = 'not-counted-badge';
    notCounted.textContent = '✗';
    notCounted.title = 'Not counted in total';

    const counter = buildOptionalCounter(opt.key);
    counter.className = 'side-counter-inner';

    wrap.appendChild(img);
    wrap.appendChild(notCounted);
    wrap.appendChild(counter);
    sideCol.appendChild(wrap);
  });
}

function buildOptionalCounter(key) {
  const group = document.createElement('div');
  group.className = 'optional-counter-group';

  const decr = document.createElement('button');
  decr.className = 'count-btn decr-btn opt-decr';
  decr.textContent = '−';

  const display = document.createElement('span');
  display.className = 'opt-count-label';
  const oc = state.optional_counters[key] || { count: 0, max: null };
  display.textContent = `${oc.count} / ${oc.max !== null ? oc.max : '?'}`;

  const incr = document.createElement('button');
  incr.className = 'count-btn incr-btn opt-incr';
  incr.textContent = '+';

  const maxInput = document.createElement('input');
  maxInput.type = 'number';
  maxInput.className = 'max-entry opt-max-entry';
  maxInput.placeholder = '?';
  maxInput.min = '0';
  maxInput.value = oc.max !== null ? oc.max : '';

  decr.addEventListener('click', () => {
    state.optional_counters[key].count = Math.max(0, (state.optional_counters[key].count || 0) - 1);
    display.textContent = `${state.optional_counters[key].count} / ${state.optional_counters[key].max !== null ? state.optional_counters[key].max : '?'}`;
    if (key === 'moon_kingdom') refreshTotalMoonDisplay();
    saveState();
  });
  incr.addEventListener('click', () => {
    state.optional_counters[key].count = (state.optional_counters[key].count || 0) + 1;
    display.textContent = `${state.optional_counters[key].count} / ${state.optional_counters[key].max !== null ? state.optional_counters[key].max : '?'}`;
    if (key === 'moon_kingdom') refreshTotalMoonDisplay();
    saveState();
  });
  maxInput.addEventListener('input', () => {
    const v = parseInt(maxInput.value);
    state.optional_counters[key].max = (!isNaN(v) && v >= 0) ? v : null;
    display.textContent = `${state.optional_counters[key].count} / ${state.optional_counters[key].max !== null ? state.optional_counters[key].max : '?'}`;
    saveState();
  });

  group.appendChild(decr);
  group.appendChild(display);
  group.appendChild(incr);
  group.appendChild(maxInput);
  return group;
}

// ── Moon Row updates ──────────────────────────────────────────────
function getMoonRow(i) {
  return document.querySelector(`.moon-row[data-idx="${i}"]`);
}

function refreshCountLabel(i) {
  const row = getMoonRow(i);
  if (!row) return;
  const m = state.moons[i];
  row.querySelector('.count-label').textContent =
    `${m.count} / ${m.max !== null ? m.max : '?'}`;
  updateCountColor(i);
  refreshTotalMoonDisplay();
}

function updateCountColor(i) {
  const row = getMoonRow(i);
  if (!row) return;
  const m = state.moons[i];
  const kingdom = KINGDOMS[i];
  const label = row.querySelector('.count-label');
  const isComplete = state.settings.show_complete_color && (
    (m.max !== null && m.count >= m.max) ||
    (m.count >= kingdom.max)
  );
  label.classList.toggle('count-complete', isComplete);
  row.classList.toggle('row-complete', isComplete);
}

function refreshMoonRow(i, rowEl) {
  const row = rowEl || getMoonRow(i);
  if (!row) return;
  const m = state.moons[i];

  row.querySelector('.count-label').textContent =
    `${m.count} / ${m.max !== null ? m.max : '?'}`;

  row.querySelector('.lock-btn img').src =
    m.lock ? 'assets/unlock.png' : 'assets/lock.png';
  row.querySelector('.peace-btn img').src =
    m.peace ? 'assets/peace_unlock.png' : 'assets/peace.png';

  const entry = row.querySelector('.max-entry');
  if (document.activeElement !== entry) {
    entry.value = m.max !== null ? m.max : '';
  }

  // White icon mode for kingdom icons only (not moontick)
  const kImg = row.querySelector('.kingdom-icon');
  const isWhite = state.settings.white_icon_mode;
  if (isWhite) {
    kImg.classList.add('icon-white');
  } else if (!state.settings.show_icon_colors) {
    kImg.classList.add('icon-white');
  } else {
    kImg.classList.remove('icon-white');
  }

  // Moontick icon - never affected by white icon mode
  const moontickImg = row.querySelector('.moontick-icon');
  if (moontickImg) {
    moontickImg.classList.toggle('hidden', !state.settings.show_moontick);
    moontickImg.classList.remove('icon-white'); // Never white
  }

  // Lock/Peace visibility — both controlled by show_peace
  row.querySelector('.lock-btn').classList.toggle('hidden', !state.settings.show_peace);
  row.querySelector('.peace-btn').classList.toggle('hidden', !state.settings.show_peace);

  const multiBtn = row.querySelector('.multi-moon-btn');
  multiBtn.classList.toggle('hidden', !state.settings.show_multi_moon);

  row.querySelectorAll('.range-stack').forEach(el => {
    el.classList.toggle('hidden', !state.settings.show_moon_range);
  });

  updateCountColor(i);
  row.querySelector('.save-btn').classList.toggle('hidden', !state.settings.show_save_buttons);
}

// ── Moon actions ──────────────────────────────────────────────────
function increment(i) { state.moons[i].count++; refreshCountLabel(i); }
function decrement(i) { state.moons[i].count = Math.max(0, state.moons[i].count - 1); refreshCountLabel(i); }

function addMulti(i) {
  state.moons[i].count += 3;
  refreshMoonRow(i);
  refreshTotalMoonDisplay();
}

function toggleLock(i) {
  state.moons[i].lock = !state.moons[i].lock;
  const row = getMoonRow(i);
  if (row) row.querySelector('.lock-btn img').src =
    state.moons[i].lock ? 'assets/unlock.png' : 'assets/lock.png';
}

function togglePeace(i) {
  state.moons[i].peace = !state.moons[i].peace;
  const row = getMoonRow(i);
  if (row) row.querySelector('.peace-btn img').src =
    state.moons[i].peace ? 'assets/peace_unlock.png' : 'assets/peace.png';
}

function saveMax(i) {
  const row = getMoonRow(i);
  if (!row) return;
  const v = parseInt(row.querySelector('.max-entry').value);
  state.moons[i].max = (!isNaN(v) && v >= 0) ? v : null;
  refreshCountLabel(i);
  saveState();
}

// ─────────────────────────────────────────────────────────────────────────────
// Capture Row Build
// ─────────────────────────────────────────────────────────────────────────────
function buildCaptureRow() {
  const container = document.getElementById('capture-row');
  container.innerHTML = '';
  CAPTURE_ICONS.forEach(ic => {
    const btn = document.createElement('button');
    btn.className = 'icon-toggle-btn';
    btn.dataset.key = ic.key;
    btn.title = ic.key;
    const img = document.createElement('img');
    img.src = state.captures[ic.key] ? ic.unlocked : ic.locked;
    img.alt = ic.key;
    btn.appendChild(img);
    btn.classList.toggle('active', state.captures[ic.key]);
    btn.addEventListener('click', () => {
      state.captures[ic.key] = !state.captures[ic.key];
      img.src = state.captures[ic.key] ? ic.unlocked : ic.locked;
      btn.classList.toggle('active', state.captures[ic.key]);
      saveState();
    });
    container.appendChild(btn);
  });
}

// ─────────────────────────────────────────────────────────────────────────────
// Ability Row Build
// ─────────────────────────────────────────────────────────────────────────────
function buildAbilityRow() {
  const container = document.getElementById('ability-row');
  container.innerHTML = '';

  ABILITY_ICONS.forEach(ic => {
    const btn = document.createElement('button');
    btn.className = 'icon-toggle-btn ability-icon';
    btn.dataset.key = ic.key;
    btn.title = ic.key;
    const img = document.createElement('img');
    img.src = state.abilities[ic.key] ? ic.unlocked : ic.locked;
    img.alt = ic.key;
    btn.appendChild(img);
    btn.classList.toggle('active', state.abilities[ic.key]);
    btn.addEventListener('click', () => {
      state.abilities[ic.key] = !state.abilities[ic.key];
      img.src = state.abilities[ic.key] ? ic.unlocked : ic.locked;
      btn.classList.toggle('active', state.abilities[ic.key]);
      saveState();
    });
    container.appendChild(btn);
  });

  const notesSection = document.getElementById('notes-section');
  notesSection.innerHTML = '';
  const notesBtn = document.createElement('button');
  notesBtn.className = 'notes-btn';
  notesBtn.id = 'btn-notes';
  notesBtn.textContent = 'Loading Zone Notes';
  notesBtn.addEventListener('click', openLoadingZones);
  notesSection.appendChild(notesBtn);
  const mapBtn = document.createElement('button');
  mapBtn.className = 'map-btn';
  mapBtn.id = 'btn-map';
  mapBtn.textContent = 'Connection Map';
  mapBtn.addEventListener('click', openMap);
  notesSection.appendChild(mapBtn);
}

// ─────────────────────────────────────────────────────────────────────────────
// Settings
// ─────────────────────────────────────────────────────────────────────────────
let settingsWindow = null;

function openSettings() {
  const modal = document.getElementById('settings-modal');
  if (settingsWindow && !settingsWindow.closed) {
    settingsWindow.focus();
    return;
  }
  TOGGLE_SETTINGS.forEach(({ id, key }) => {
    const el = document.getElementById(id);
    if (el) el.checked = !!state.settings[key];
  });
  document.getElementById('input-moon-req').value = state.settings.moon_requirement || 124;
  document.getElementById('input-overlay-scale').value = state.settings.overlay_scale || 1;
  const wsUrlInput = document.getElementById('input-ws-url');
  if (wsUrlInput) wsUrlInput.value = loadWsUrl();
  document.getElementById('input-notes-scroll').value = state.settings.notes_scroll_px || 500;
  document.getElementById('rebind-scroll-left').textContent = bindingLabel(state.settings.scroll_left_binding);
  document.getElementById('rebind-scroll-right').textContent = bindingLabel(state.settings.scroll_right_binding);
  const obsBgInput = document.getElementById('input-obs-bg-color');
  if (obsBgInput) obsBgInput.value = state.settings.obs_bg_color !== 'transparent' ? (state.settings.obs_bg_color || '#181818') : '#181818';
  // Populate button visibility inputs
  const bv = state.settings.button_visibility || {};
  document.querySelectorAll('.bv-input').forEach(input => {
    const bvId = input.dataset.bvId;
    input.value = (bvId in bv) ? bv[bvId] : 1;
  });
  applyBVSectionHeaders();
  modal.classList.remove('hidden');
}

function applyAllSettings() {
  const s = state.settings;

  // Icon colors / white icon mode - kingdom icons only (not moontick)
  document.querySelectorAll('.kingdom-icon').forEach(img => {
    if (s.white_icon_mode) {
      img.classList.add('icon-white');
    } else if (!s.show_icon_colors) {
      img.classList.add('icon-white');
    } else {
      img.classList.remove('icon-white');
    }
  });

  // Moontick icons — never white
  document.querySelectorAll('.moontick-icon').forEach(img => {
    img.classList.remove('icon-white');
    img.classList.toggle('hidden', !s.show_moontick);
  });

  // Save buttons
  document.querySelectorAll('.save-btn').forEach(btn => {
    btn.classList.toggle('hidden', !s.show_save_buttons);
  });

  // Capture section
  document.getElementById('capture-section').classList.toggle('hidden', !s.show_captures);

  // Ability section visibility
  document.getElementById('ability-section').classList.toggle('abilities-hidden', !s.show_ability_lock);

  // Lock/peace buttons — both controlled by show_peace toggle
  document.querySelectorAll('.lock-btn').forEach(btn => btn.classList.toggle('hidden', !s.show_peace));
  document.querySelectorAll('.peace-btn').forEach(btn => btn.classList.toggle('hidden', !s.show_peace));

  // Multi moon buttons
  document.querySelectorAll('.multi-moon-btn').forEach(btn => {
    btn.classList.toggle('hidden', !s.show_multi_moon);
  });

  // Min/max range stacks
  document.querySelectorAll('.range-stack').forEach(el => {
    el.classList.toggle('hidden', !s.show_moon_range);
  });

  // Total moon display
  const totalWrap = document.getElementById('total-moon-wrap');
  if (totalWrap) totalWrap.classList.toggle('hidden', !s.show_moon_total);
  refreshTotalMoonDisplay();

  // Moon Kingdom row
  const mkWrap = document.getElementById('moon-kingdom-row-wrap');
  if (mkWrap) mkWrap.classList.toggle('hidden', !s.show_moon_kingdom);

  // Side counters
  OPTIONAL_COUNTERS.filter(c => c.side).forEach(opt => {
    const el = document.querySelector(`.side-counter-item[data-side-key="${opt.key}"]`);
    if (el) el.classList.toggle('hidden', !s[`show_${opt.key}`]);
  });

  // Green-when-complete recompute
  KINGDOMS.forEach((_, i) => updateCountColor(i));

  // Button visibility
  applyButtonVisibility();
}

// ─────────────────────────────────────────────────────────────────────────────
// Button Visibility
// ─────────────────────────────────────────────────────────────────────────────

// Sections: each has a header element ID and the button IDs it contains
const BUTTON_VISIBILITY_SECTIONS = [
  {
    headerId: 'bv-section-sync',
    buttons: [
      { id: 'btn-toggle-visibility', label: 'Show/Hide Room Code' },
      { id: 'btn-generate-room',     label: 'Generate Room' },
      { id: 'btn-connect-room',      label: 'Connect/Disconnect' },
      { id: 'btn-copy-obs-url',      label: 'Copy OBS URL' },
    ],
  },
  {
    headerId: 'bv-section-obs',
    buttons: [
      { id: 'btn-obs',      label: 'Open OBS Popup' },
      { id: 'btn-obs-info', label: 'OBS Info (ℹ️)' },
    ],
  },
  {
    headerId: 'bv-section-tracker',
    buttons: [
      { id: 'btn-clear', label: 'Clear Tracker' },
      { id: 'btn-notes', label: 'Loading Zone Notes' },
      { id: 'btn-map',   label: 'Connection Map' },
    ],
  },
];

function applyButtonVisibility() {
  const bv = state.settings.button_visibility || {};
  BUTTON_VISIBILITY_SECTIONS.forEach(section => {
    let anyVisible = false;
    section.buttons.forEach(b => {
      const val = (b.id in bv) ? bv[b.id] : 1;
      const el = document.getElementById(b.id);
      if (el) el.classList.toggle('hidden', val === 0 || val === '0');
      if (val !== 0 && val !== '0') anyVisible = true;
    });
    // If btn-obs and btn-obs-info are both hidden, hide the obs-btn-row wrapper too
    if (section.headerId === 'bv-section-obs') {
      const obsRow = document.getElementById('obs-btn-row');
      if (obsRow) obsRow.classList.toggle('hidden', !anyVisible);
    }
  });
  applyBVSectionHeaders();
}

function applyBVSectionHeaders() {
  const bv = state.settings.button_visibility || {};
  BUTTON_VISIBILITY_SECTIONS.forEach(section => {
    const headerEl = document.getElementById(section.headerId);
    if (!headerEl) return;
    const allHidden = section.buttons.every(b => {
      const val = (b.id in bv) ? bv[b.id] : 1;
      return val === 0 || val === '0';
    });
    // Find the settings-rows that belong to this section: all rows between this header and the next
    // We hide the subsection header if all its buttons are 0
    headerEl.classList.toggle('hidden', allHidden);
    // Also hide the settings-rows for those buttons
    section.buttons.forEach(b => {
      const val = (b.id in bv) ? bv[b.id] : 1;
      const input = document.querySelector(`.bv-input[data-bv-id="${b.id}"]`);
      // We don't hide the setting rows themselves (user needs to set them back to 1)
      // Only the actual UI buttons are hidden
    });
  });
}

// ─────────────────────────────────────────────────────────────────────────────
// Reset (Clear Tracker)
// ─────────────────────────────────────────────────────────────────────────────
function resetAll() {
  if (!confirm('Clear all tracker progress? This will reset moon counts, captures, abilities, and optional counters. Settings and notes will be kept.')) return;
  const savedSettings = JSON.parse(JSON.stringify(state.settings));
  const savedZones = JSON.parse(JSON.stringify(state.loading_zones));
  const savedCollapsed = JSON.parse(JSON.stringify(state.kingdom_collapsed));
  state = getDefaultState();
  state.settings = savedSettings;
  state.loading_zones = savedZones;
  state.kingdom_collapsed = savedCollapsed;
  saveState();
  buildAllMoonRows();
  buildCaptureRow();
  buildAbilityRow();
  applyAllSettings();
  refreshTotalMoonDisplay();
}

// ─────────────────────────────────────────────────────────────────────────────
// OBS Overlay
// ─────────────────────────────────────────────────────────────────────────────
let obsWindow = null;

function openOBS() {
  const room = window.SMOSync ? window.SMOSync.getRoom() : null;
  const wsUrl = room ? encodeURIComponent(window.SMOSync.getWsUrl()) : '';
  const scale = state.settings.overlay_scale || 1;
  const width = Math.round(315 * scale);
  const height = Math.round(450 * scale);
  const bgColor = encodeURIComponent(state.settings.obs_bg_color || 'transparent');
  let url = `obs.html?popup=1&bg=${bgColor}`;
  if (room) url += `&room=${room}&ws=${wsUrl}&scale=${scale}`;

  const features = `width=${width},height=${height},resizable=yes,scrollbars=no,toolbar=no,menubar=no`;
  if (!obsWindow || obsWindow.closed) {
    obsWindow = window.open(url, 'MoonTrackerOBS', features);
  } else {
    obsWindow.focus();
  }
}

// ─────────────────────────────────────────────────────────────────────────────
// Sync
// ─────────────────────────────────────────────────────────────────────────────
function loadWsUrl() {
  try { return localStorage.getItem(WS_URL_KEY) || ''; } catch (e) { return ''; }
}

function saveWsUrl(url) {
  try {
    if (url) localStorage.setItem(WS_URL_KEY, url);
    else localStorage.removeItem(WS_URL_KEY);
  } catch (e) { console.error('Failed to save WS URL:', e); }
}

function getObsPageUrl(room, wsUrl) {
  const base = 'https://firerisingraging.github.io/Online_SMO_Randomizer_Tracker/obs.html';
  if (!room) return base;
  const scale = state.settings.overlay_scale || 1;
  const bg = encodeURIComponent(state.settings.obs_bg_color || 'transparent');
  return `${base}?room=${room}&ws=${encodeURIComponent(wsUrl || window.SMOSync.getWsUrl())}&scale=${scale}&bg=${bg}`;
}

function updateSyncUI() {
  const sync = window.SMOSync;
  const room = sync ? sync.getRoom() : null;
  const roomInput = document.getElementById('input-room-code');
  const connectBtn = document.getElementById('btn-connect-room');
  const statusEl = document.getElementById('sync-status');
  const urlRow = document.getElementById('sync-url-row');
  const urlInput = document.getElementById('input-obs-url');
  const sizeRow = document.getElementById('sync-size-row');
  const scale = state.settings.overlay_scale || 1;

  if (roomInput) roomInput.value = room || '';

  if (room) {
    connectBtn.textContent = 'Disconnect';
    if (urlRow) urlRow.classList.remove('hidden');
    if (sizeRow) sizeRow.classList.remove('hidden');
    if (urlInput) urlInput.value = getObsPageUrl(room);
    if (sizeRow) sizeRow.innerHTML = `OBS size: <strong>${Math.round(315 * scale)}</strong> × <strong>${Math.round(450 * scale)}</strong>`;
  } else {
    connectBtn.textContent = 'Connect';
    if (urlRow) urlRow.classList.add('hidden');
    if (sizeRow) sizeRow.classList.add('hidden');
    if (statusEl && !room) statusEl.textContent = 'Offline. Enter a room code to sync';
  }
}

function applyRemoteState(remote) {
  if (!remote || typeof remote !== 'object') return;
  applyingRemote = true;

  if (remote.settings) {
    for (const key of Object.keys(DEFAULT_SETTINGS)) {
      if (key in remote.settings) state.settings[key] = remote.settings[key];
    }
  }
  if (Array.isArray(remote.moons)) {
    remote.moons.forEach((m, i) => {
      if (state.moons[i]) Object.assign(state.moons[i], m);
    });
  }
  if (remote.optional_counters) {
    for (const k of Object.keys(state.optional_counters)) {
      if (remote.optional_counters[k]) Object.assign(state.optional_counters[k], remote.optional_counters[k]);
    }
  }
  if (remote.captures) Object.assign(state.captures, remote.captures);
  if (remote.abilities) Object.assign(state.abilities, remote.abilities);
  if (remote.loading_zones) {
    for (const [kingdom, data] of Object.entries(state.loading_zones)) {
      if (!remote.loading_zones[kingdom]) continue;
      const savedKingdom = remote.loading_zones[kingdom];
      for (const zone of Object.keys(data.zones)) {
        if (savedKingdom.zones && savedKingdom.zones[zone]) {
          Object.assign(state.loading_zones[kingdom].zones[zone], savedKingdom.zones[zone]);
        }
      }
    }
  }
  if (remote.kingdom_collapsed) {
    for (const k of Object.keys(state.kingdom_collapsed)) {
      if (k in remote.kingdom_collapsed) state.kingdom_collapsed[k] = remote.kingdom_collapsed[k];
    }
  }

  saveState();
  refreshAll();
  applyingRemote = false;
}

function refreshAll() {
  buildAllMoonRows();
  buildCaptureRow();
  buildAbilityRow();
  applyAllSettings();
  refreshTotalMoonDisplay();
  const settingsModal = document.getElementById('settings-modal');
  if (settingsModal && !settingsModal.classList.contains('hidden')) {
    openSettings();
  }
}

function connectRoom() {
  const roomInput = document.getElementById('input-room-code');
  const room = roomInput.value.trim();
  if (!room) return;
  const wsUrlInput = document.getElementById('input-ws-url');
  const wsUrl = wsUrlInput ? wsUrlInput.value.trim() : '';
  saveWsUrl(wsUrl);
  try { localStorage.setItem(ROOM_CODE_KEY, room); } catch (e) { }
  if (window.SMOSync) window.SMOSync.connect(room, wsUrl);
}

function disconnectRoom() {
  if (window.SMOSync) window.SMOSync.disconnect();
  try { localStorage.removeItem(ROOM_CODE_KEY); } catch (e) { }
  updateSyncUI();
}

function generateAndConnectRoom() {
  if (!window.SMOSync) return;
  const code = window.SMOSync.generateRoomCode(12);
  const roomInput = document.getElementById('input-room-code');
  if (roomInput) roomInput.value = code;
  connectRoom();
}

function copyObsUrl() {
  const input = document.getElementById('input-obs-url');
  if (!input) return;
  input.select();
  navigator.clipboard.writeText(input.value).catch(() => { });
}

function toggleVisibility() {
  const roomInput = document.getElementById('input-room-code');
  const urlInput = document.getElementById('input-obs-url');
  const btn = document.getElementById('btn-toggle-visibility');
  if (!roomInput || !btn) return;
  const makeVisible = roomInput.type === 'password';
  const newType = makeVisible ? 'text' : 'password';
  roomInput.type = newType;
  if (urlInput) urlInput.type = newType;
  btn.textContent = makeVisible ? 'Hide' : 'Show';
}

function setupSyncUI() {
  if (!window.SMOSync) return;
  const savedWsUrl = loadWsUrl();
  const wsUrlInput = document.getElementById('input-ws-url');
  if (wsUrlInput && savedWsUrl) wsUrlInput.value = savedWsUrl;

  window.SMOSync.onStatus((status) => {
    const statusEl = document.getElementById('sync-status');
    if (statusEl) {
      const labels = {
        connected: 'Connected — state is syncing',
        connecting: 'Connecting...',
        disconnected: 'Disconnected',
        error: 'Connection error — OBS overlay will not work'
      };
      statusEl.textContent = labels[status] || status;
    }
    updateSyncUI();
  });

  window.SMOSync.onState((remoteState) => {
    applyRemoteState(remoteState);
  });

  const connectBtn = document.getElementById('btn-connect-room');
  const generateBtn = document.getElementById('btn-generate-room');
  const copyBtn = document.getElementById('btn-copy-obs-url');
  const visibilityBtn = document.getElementById('btn-toggle-visibility');

  if (connectBtn) connectBtn.addEventListener('click', () => {
    if (window.SMOSync.getRoom()) disconnectRoom();
    else connectRoom();
  });
  if (generateBtn) generateBtn.addEventListener('click', generateAndConnectRoom);
  if (copyBtn) copyBtn.addEventListener('click', copyObsUrl);
  if (visibilityBtn) visibilityBtn.addEventListener('click', toggleVisibility);

  const params = new URLSearchParams(window.location.search);
  let room = params.get('room');
  if (!room) { try { room = localStorage.getItem(ROOM_CODE_KEY); } catch (e) { } }
  if (room) {
    const roomInput = document.getElementById('input-room-code');
    if (roomInput) roomInput.value = room;
    connectRoom();
  }
  updateSyncUI();
}

// ─────────────────────────────────────────────────────────────────────────────
// Loading Zones Modal
// ─────────────────────────────────────────────────────────────────────────────
let notesWindow = null;

function openMap() {
  window.open('map.html', 'ConnectionMap', 'resizable=yes,toolbar=no,menubar=no');
}

function openLoadingZones() {
  if (notesWindow && !notesWindow.closed) {
    notesWindow.focus();
    return;
  }
  resyncLoadingZonesFromStorage();
  document.getElementById('lz-modal').classList.remove('hidden');
  buildLoadingZonesContent();
}

function resyncLoadingZonesFromStorage() {
  try {
    const raw = localStorage.getItem(STATE_KEY);
    if (!raw) return;
    const saved = JSON.parse(raw);
    if (saved.loading_zones) {
      for (const [kingdom, data] of Object.entries(state.loading_zones)) {
        if (!saved.loading_zones[kingdom]) continue;
        const savedKingdom = saved.loading_zones[kingdom];
        for (const zone of Object.keys(data.zones)) {
          if (savedKingdom.zones && savedKingdom.zones[zone]) {
            Object.assign(state.loading_zones[kingdom].zones[zone], savedKingdom.zones[zone]);
          }
        }
      }
    }
    if (saved.kingdom_collapsed) {
      for (const k of Object.keys(state.kingdom_collapsed)) {
        if (k in saved.kingdom_collapsed) state.kingdom_collapsed[k] = saved.kingdom_collapsed[k];
      }
    }
  } catch (e) { console.error('Failed to resync loading zones from storage:', e); }
}

function popOutNotes() {
  notesWindow = window.open('notes.html', 'MoonTrackerNotes', 'width=1150,height=750,resizable=yes,scrollbars=yes,toolbar=no,menubar=no');
  document.getElementById('lz-modal').classList.add('hidden');
}

function clearNotes() {
  if (!confirm('Clear ALL notes? This cannot be undone.')) return;
  for (const kData of Object.values(state.loading_zones)) {
    for (const zData of Object.values(kData.zones)) {
      zData.note = '';
    }
  }
  saveState();
  buildLoadingZonesContent();
}

function buildLoadingZonesContent() {
  const container = document.getElementById('lz-content');
  container.innerHTML = '';
  for (const [kingdom, data] of Object.entries(state.loading_zones)) {
    container.appendChild(buildKingdomColumn(kingdom, data));
  }
}

function buildKingdomColumn(kingdom, data) {
  const col = document.createElement('div');
  col.className = 'kingdom-col';

  const header = document.createElement('div');
  header.className = 'kingdom-col-header';

  const icon = document.createElement('img');
  icon.src = `assets/${data.icon}`;
  icon.height = 20;
  icon.alt = kingdom;

  const title = document.createElement('span');
  title.className = 'col-title';
  title.textContent = kingdom;
  title.style.color = data.color;

  const chevron = document.createElement('span');
  chevron.className = 'col-chevron';
  chevron.textContent = '▾';

  header.appendChild(icon);
  header.appendChild(title);
  header.appendChild(chevron);

  const zoneEntries = Object.entries(data.zones);
  const needsSplit = zoneEntries.length > ZONE_SPLIT_THRESHOLD;
  let zonesRoot;

  if (needsSplit) {
    const mid = Math.ceil(zoneEntries.length / 2);
    zonesRoot = document.createElement('div');
    zonesRoot.className = 'zones-split-wrap';
    const col1 = document.createElement('div');
    col1.className = 'zones-container';
    const col2 = document.createElement('div');
    col2.className = 'zones-container';
    zoneEntries.slice(0, mid).forEach(([zone, zd]) => col1.appendChild(buildZoneRow(kingdom, zone, zd, data.color)));
    zoneEntries.slice(mid).forEach(([zone, zd]) => col2.appendChild(buildZoneRow(kingdom, zone, zd, data.color)));
    zonesRoot.appendChild(col1);
    zonesRoot.appendChild(col2);
  } else {
    zonesRoot = document.createElement('div');
    zonesRoot.className = 'zones-container';
    zoneEntries.forEach(([zone, zd]) => zonesRoot.appendChild(buildZoneRow(kingdom, zone, zd, data.color)));
  }

  if (state.kingdom_collapsed[kingdom]) {
    zonesRoot.style.display = 'none';
    header.classList.add('collapsed');
  }

  header.addEventListener('click', () => {
    const willCollapse = zonesRoot.style.display !== 'none';
    zonesRoot.style.display = willCollapse ? 'none' : '';
    header.classList.toggle('collapsed', willCollapse);
    state.kingdom_collapsed[kingdom] = willCollapse;
    saveState();
  });

  col.appendChild(header);
  col.appendChild(zonesRoot);
  return col;
}

function buildZoneRow(kingdom, zone, zoneData, color) {
  const zs = state.loading_zones[kingdom].zones[zone];
  const row = document.createElement('div');
  row.className = 'zone-row';

  const top = document.createElement('div');
  top.className = 'zone-row-top';

  function makeZoneIcon(iconKey) {
    const img = document.createElement('img');
    img.className = 'zone-icon';
    img.src = `assets/${zs[iconKey] || 'Moon.png'}`;
    img.alt = 'zone icon';
    img.addEventListener('click', (e) => {
      openIconPicker(e, (chosen) => {
        zs[iconKey] = chosen;
        img.src = `assets/${chosen}`;
        saveState();
      });
      e.stopPropagation();
    });
    return img;
  }

  top.appendChild(makeZoneIcon('icon'));
  if (zoneData.num > 1) top.appendChild(makeZoneIcon('icon2'));

  const nameLabel = document.createElement('span');
  nameLabel.className = 'zone-name';
  nameLabel.textContent = zone;
  nameLabel.style.color = zs.collapsed ? '#888' : color;
  top.appendChild(nameLabel);
  row.appendChild(top);

  const noteArea = document.createElement('textarea');
  noteArea.className = 'zone-note';
  noteArea.value = zs.note || '';
  noteArea.placeholder = 'Note…';
  noteArea.rows = 1;
  if (zs.collapsed) noteArea.style.display = 'none';

  noteArea.addEventListener('input', () => {
    noteArea.style.height = 'auto';
    noteArea.style.height = noteArea.scrollHeight + 'px';
    zs.note = noteArea.value;
    saveState();
  });

  nameLabel.addEventListener('click', () => {
    zs.collapsed = !zs.collapsed;
    nameLabel.style.color = zs.collapsed ? '#888' : color;
    noteArea.style.display = zs.collapsed ? 'none' : '';
    saveState();
  });

  row.appendChild(noteArea);
  return row;
}

// ─────────────────────────────────────────────────────────────────────────────
// Spoiler Log
// ─────────────────────────────────────────────────────────────────────────────
let spoilerData = null;

function loadSpoilerLog() {
  const input = document.createElement('input');
  input.type = 'file';
  input.accept = '.txt,.json';
  input.addEventListener('change', (e) => {
    const file = e.target.files[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = (ev) => {
      try {
        parseSpoilerLog(ev.target.result, file.name);
      } catch (err) {
        alert('Failed to parse spoiler log: ' + err.message);
      }
    };
    reader.readAsText(file);
  });
  input.click();
}

function parseSpoilerLog(content, filename) {
  let parsed = null;
  if (filename.endsWith('.json')) {
    try { parsed = JSON.parse(content); } catch (e) { }
  }
  if (!parsed) {
    // Parse as text — build array of {location, item} pairs
    parsed = [];
    const lines = content.split('\n');
    for (const line of lines) {
      const trimmed = line.trim();
      if (!trimmed) continue;
      // Common formats: "Location: Item" or "Location - Item" or tab-separated
      let loc, item;
      if (trimmed.includes('\t')) {
        [loc, item] = trimmed.split('\t').map(s => s.trim());
      } else if (trimmed.includes(' - ')) {
        const idx = trimmed.indexOf(' - ');
        loc = trimmed.slice(0, idx).trim();
        item = trimmed.slice(idx + 3).trim();
      } else if (trimmed.includes(': ')) {
        const idx = trimmed.indexOf(': ');
        loc = trimmed.slice(0, idx).trim();
        item = trimmed.slice(idx + 2).trim();
      } else {
        loc = trimmed;
        item = '';
      }
      if (loc) parsed.push({ location: loc, item: item || '' });
    }
  }
  spoilerData = Array.isArray(parsed) ? parsed : Object.entries(parsed).map(([k, v]) => ({ location: k, item: String(v) }));
  try { localStorage.setItem(SPOILER_KEY, JSON.stringify(spoilerData)); } catch (e) { }
  openSpoilerSearch();
}

function openSpoilerSearch() {
  // Load from storage if not in memory
  if (!spoilerData) {
    try {
      const raw = localStorage.getItem(SPOILER_KEY);
      if (raw) spoilerData = JSON.parse(raw);
    } catch (e) { }
  }

  const modal = document.getElementById('spoiler-modal');
  if (!modal) return;
  modal.classList.remove('hidden');
  renderSpoilerResults('');

  const searchInput = document.getElementById('spoiler-search-input');
  if (searchInput) {
    searchInput.value = '';
    searchInput.focus();
    searchInput.oninput = () => renderSpoilerResults(searchInput.value);
  }
}

function normalize(str) {
  return str.toLowerCase().replace(/\s+/g, ' ').trim();
}

function fuzzyMatch(haystack, needle) {
  const h = normalize(haystack);
  const n = normalize(needle);
  if (h.includes(n)) return true;
  // Tolerance: allow up to 1 char different per 4 chars of needle (simple)
  if (n.length <= 2) return h.includes(n);
  const words = n.split(' ');
  return words.every(w => h.includes(w));
}

function renderSpoilerResults(query) {
  const container = document.getElementById('spoiler-results');
  if (!container) return;
  container.innerHTML = '';

  if (!spoilerData || spoilerData.length === 0) {
    container.innerHTML = '<div class="spoiler-empty">No spoiler log loaded. Use Settings → Load Spoiler Log.</div>';
    return;
  }

  const results = query.trim()
    ? spoilerData.filter(e => fuzzyMatch(e.location || '', query) || fuzzyMatch(e.item || '', query))
    : spoilerData.slice(0, 100);

  if (results.length === 0) {
    container.innerHTML = '<div class="spoiler-empty">No matches found.</div>';
    return;
  }

  results.slice(0, 200).forEach(entry => {
    const row = document.createElement('div');
    row.className = 'spoiler-row';
    row.innerHTML = `<span class="spoiler-loc">${escHtml(entry.location || '')}</span><span class="spoiler-sep">→</span><span class="spoiler-item">${escHtml(entry.item || '')}</span>`;
    container.appendChild(row);
  });

  if (results.length > 200) {
    const more = document.createElement('div');
    more.className = 'spoiler-empty';
    more.textContent = `${results.length - 200} more results — refine your search`;
    container.appendChild(more);
  }
}

function escHtml(str) {
  return str.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
}

// ─────────────────────────────────────────────────────────────────────────────
// Notes Horizontal Scroll
// ─────────────────────────────────────────────────────────────────────────────
function isLzOpen() {
  const modal = document.getElementById('lz-modal');
  return modal && !modal.classList.contains('hidden');
}

function setupNotesScroll() {
  const scrollWrap = document.querySelector('.lz-scroll-wrap');
  if (!scrollWrap) return;

  scrollWrap.addEventListener('wheel', (e) => {
    if (scrollWrap.scrollWidth <= scrollWrap.clientWidth) return;
    e.preventDefault();
    const px = state.settings.notes_scroll_px || 500;
    scrollWrap.scrollLeft += e.deltaY > 0 ? px : -px;
  }, { passive: false });

  scrollWrap.addEventListener('mousedown', (e) => {
    const lb = state.settings.scroll_left_binding;
    const rb = state.settings.scroll_right_binding;
    if ((lb && lb.type === 'mouse' && e.button === lb.code) ||
      (rb && rb.type === 'mouse' && e.button === rb.code)) {
      e.preventDefault();
    }
  });
  scrollWrap.addEventListener('mouseup', (e) => {
    const px = state.settings.notes_scroll_px || 500;
    const lb = state.settings.scroll_left_binding;
    const rb = state.settings.scroll_right_binding;
    if (lb && lb.type === 'mouse' && e.button === lb.code) {
      e.preventDefault();
      scrollWrap.scrollLeft -= px;
    } else if (rb && rb.type === 'mouse' && e.button === rb.code) {
      e.preventDefault();
      scrollWrap.scrollLeft += px;
    }
  });

  document.addEventListener('keydown', (e) => {
    if (!isLzOpen()) return;
    if (e.target && e.target.classList && e.target.classList.contains('zone-note')) return;
    const px = state.settings.notes_scroll_px || 500;
    const lb = state.settings.scroll_left_binding;
    const rb = state.settings.scroll_right_binding;
    if (lb && lb.type === 'key' && e.code === lb.code) {
      e.preventDefault();
      scrollWrap.scrollLeft -= px;
    } else if (rb && rb.type === 'key' && e.code === rb.code) {
      e.preventDefault();
      scrollWrap.scrollLeft += px;
    }
  });
}

// ─────────────────────────────────────────────────────────────────────────────
// Scroll Button Rebinding
// ─────────────────────────────────────────────────────────────────────────────
function setupRebindButtons() {
  const leftBtn = document.getElementById('rebind-scroll-left');
  const rightBtn = document.getElementById('rebind-scroll-right');
  if (leftBtn) leftBtn.addEventListener('click', () => startRebind('scroll_left_binding', leftBtn));
  if (rightBtn) rightBtn.addEventListener('click', () => startRebind('scroll_right_binding', rightBtn));
}

function startRebind(settingKey, btnEl) {
  btnEl.textContent = 'Press any button…';
  btnEl.classList.add('listening');
  function onMouseDown(e) { e.preventDefault(); e.stopPropagation(); apply({ type: 'mouse', code: e.button }); }
  function onKeyDown(e) {
    e.preventDefault(); e.stopPropagation();
    if (e.code === 'Escape') { cancel(); return; }
    apply({ type: 'key', code: e.code });
  }
  function apply(binding) {
    cleanup();
    state.settings[settingKey] = binding;
    btnEl.textContent = bindingLabel(binding);
    btnEl.classList.remove('listening');
    saveState();
  }
  function cancel() {
    cleanup();
    btnEl.textContent = bindingLabel(state.settings[settingKey]);
    btnEl.classList.remove('listening');
  }
  function cleanup() {
    window.removeEventListener('mousedown', onMouseDown, true);
    window.removeEventListener('keydown', onKeyDown, true);
  }
  window.addEventListener('mousedown', onMouseDown, true);
  window.addEventListener('keydown', onKeyDown, true);
}

// ─────────────────────────────────────────────────────────────────────────────
// Icon Picker
// ─────────────────────────────────────────────────────────────────────────────
function openIconPicker(event, onSelect) {
  document.querySelectorAll('.icon-picker-popup').forEach(p => p.remove());
  const picker = document.createElement('div');
  picker.className = 'icon-picker-popup';
  PICKER_ICONS.forEach(iconFile => {
    const img = document.createElement('img');
    img.src = `assets/${iconFile}`;
    img.alt = iconFile;
    img.title = iconFile.replace('.png', '');
    img.addEventListener('click', (e) => { onSelect(iconFile); picker.remove(); e.stopPropagation(); });
    picker.appendChild(img);
  });
  document.body.appendChild(picker);
  const pw = 170, ph = 90;
  let x = event.clientX, y = event.clientY;
  if (x + pw > window.innerWidth) x = window.innerWidth - pw - 8;
  if (y + ph > window.innerHeight) y = window.innerHeight - ph - 8;
  picker.style.left = `${Math.max(8, x)}px`;
  picker.style.top = `${Math.max(8, y)}px`;
  setTimeout(() => {
    document.addEventListener('click', function closePicker(e) {
      if (!picker.contains(e.target)) { picker.remove(); document.removeEventListener('click', closePicker); }
    });
  }, 10);
}

// ─────────────────────────────────────────────────────────────────────────────
// Init
// ─────────────────────────────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
  loadState();
  buildAllMoonRows();
  buildCaptureRow();
  buildAbilityRow();
  applyAllSettings();
  setupNotesScroll();
  setupRebindButtons();
  refreshTotalMoonDisplay();

  // ── Main buttons ───────────────────────────────
  document.getElementById('btn-obs').addEventListener('click', openOBS);
  document.getElementById('btn-clear').addEventListener('click', resetAll);
  document.getElementById('btn-settings').addEventListener('click', openSettings);

  // ── Sync UI ────────────────────────────────────
  setupSyncUI();

  // ── OBS Info modal ─────────────────────────────
  document.getElementById('btn-obs-info').addEventListener('click', () => {
    document.getElementById('obs-info-modal').classList.remove('hidden');
  });
  document.getElementById('obs-info-close').addEventListener('click', () => {
    document.getElementById('obs-info-modal').classList.add('hidden');
  });

  // ── Settings modal ─────────────────────────────
  document.getElementById('settings-close').addEventListener('click', () => {
    document.getElementById('settings-modal').classList.add('hidden');
  });

  TOGGLE_SETTINGS.forEach(({ id, key }) => {
    const el = document.getElementById(id);
    if (!el) return;
    el.addEventListener('change', (e) => {
      state.settings[key] = e.target.checked;
      applyAllSettings();
      saveState();
    });
  });

  document.getElementById('save-moon-req').addEventListener('click', () => {
    const v = parseInt(document.getElementById('input-moon-req').value);
    state.settings.moon_requirement = (!isNaN(v) && v > 0) ? v : 124;
    refreshTotalMoonDisplay();
    saveState();
  });

  document.getElementById('save-overlay-scale').addEventListener('click', () => {
    const v = parseFloat(document.getElementById('input-overlay-scale').value);
    if (!isNaN(v) && v > 0) { state.settings.overlay_scale = v; saveState(); updateSyncUI(); }
  });

  document.getElementById('save-ws-url').addEventListener('click', () => {
    const v = document.getElementById('input-ws-url').value.trim();
    saveWsUrl(v);
    if (window.SMOSync && window.SMOSync.getRoom()) connectRoom();
  });

  document.getElementById('save-notes-scroll').addEventListener('click', () => {
    const v = parseInt(document.getElementById('input-notes-scroll').value);
    if (!isNaN(v) && v >= 10) { state.settings.notes_scroll_px = v; saveState(); }
  });

  // OBS BG color
  document.getElementById('save-obs-bg').addEventListener('click', () => {
    const colorInput = document.getElementById('input-obs-bg-color');
    const useTransparent = document.getElementById('toggle-obs-transparent').checked;
    state.settings.obs_bg_color = useTransparent ? 'transparent' : (colorInput.value || '#181818');
    saveState();
    updateSyncUI();
  });
  document.getElementById('toggle-obs-transparent').addEventListener('change', (e) => {
    document.getElementById('input-obs-bg-color').disabled = e.target.checked;
  });

  // Button visibility save handlers
  document.querySelectorAll('.bv-save-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      const bvId = btn.dataset.bvId;
      const input = document.querySelector(`.bv-input[data-bv-id="${bvId}"]`);
      if (!input) return;
      const val = parseInt(input.value);
      if (!state.settings.button_visibility) state.settings.button_visibility = {};
      state.settings.button_visibility[bvId] = (val === 0) ? 0 : 1;
      applyButtonVisibility();
      applyBVSectionHeaders();
      saveState();
    });
  });

  // Spoiler log
  document.getElementById('btn-load-spoiler').addEventListener('click', loadSpoilerLog);
  document.getElementById('btn-open-spoiler').addEventListener('click', openSpoilerSearch);
  document.getElementById('btn-open-spoiler').addEventListener('click', openSpoilerSearch);

  document.getElementById('btn-revert-settings').addEventListener('click', () => {
    if (!confirm('Revert all settings to default? This will not affect your moon progress, captures, abilities, or notes.')) return;
    state.settings = cloneDefaultSettings();
    saveState();
    applyAllSettings();
    openSettings();
  });

  // ── Loading zones modal ────────────────────────
  document.getElementById('lz-close').addEventListener('click', () => {
    document.getElementById('lz-modal').classList.add('hidden');
  });
  document.getElementById('lz-popout').addEventListener('click', popOutNotes);
  document.getElementById('lz-clear-notes').addEventListener('click', clearNotes);

  // ── Spoiler modal ──────────────────────────────
  document.getElementById('spoiler-close').addEventListener('click', () => {
    document.getElementById('spoiler-modal').classList.add('hidden');
  });

  // Close any modal on backdrop click
  document.querySelectorAll('.modal-backdrop').forEach(backdrop => {
    backdrop.addEventListener('click', (e) => {
      if (e.target === backdrop) backdrop.classList.add('hidden');
    });
  });
});
