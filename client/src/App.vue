<template>
  <!-- Shell: [sidebar | content] grid. Only .content scrolls (sidebar is sticky, 100vh). -->
  <div class="app" :class="{ 'is-collapsed': collapsed }">
    <aside id="app-sidebar" class="sidebar">
      <div class="sidebar-brand" :title="collapsed ? t('nav.companyName') : null">
        <span class="brand-mark" aria-hidden="true">{{ t('nav.companyName').charAt(0) }}</span>
        <div class="brand-text">
          <span class="brand-name">{{ t('nav.companyName') }}</span>
          <span class="brand-subtitle">{{ t('nav.subtitle') }}</span>
        </div>
      </div>

      <nav class="sidebar-nav" aria-label="Main">
        <!-- Active state comes from router-link-exact-active (exact, so '/' is not active on every page) -->
        <router-link v-for="item in navItems" :key="item.to" :to="item.to" class="nav-item" :title="t(item.labelKey)">
          <NavIcon :name="item.icon" />
          <span class="nav-label">{{ t(item.labelKey) }}</span>
        </router-link>
      </nav>

      <!-- Controls that used to live in the top bar. Dropdowns open upward when expanded
           and to the right of the rail when collapsed (the `collapsed` prop). -->
      <div class="sidebar-footer">
        <button
          type="button"
          class="sidebar-toggle"
          :aria-label="toggleLabel"
          :title="toggleLabel"
          :aria-expanded="String(!collapsed)"
          aria-controls="app-sidebar"
          @click="toggleSidebar"
        >
          <!-- Panel icon; the chevron flips direction via CSS when collapsed -->
          <svg
            class="nav-icon toggle-icon"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            stroke-width="1.75"
            stroke-linecap="round"
            stroke-linejoin="round"
            aria-hidden="true"
          >
            <rect x="3" y="4" width="18" height="16" rx="2" />
            <path d="M9 4v16" />
            <path class="toggle-chevron" d="M16 9l-3 3 3 3" />
          </svg>
          <span class="nav-label">{{ toggleLabel }}</span>
        </button>
        <button
          type="button"
          class="sidebar-toggle theme-toggle"
          :aria-label="themeLabel"
          :title="themeLabel"
          :aria-pressed="String(isDark)"
          @click="toggleTheme"
        >
          <!-- Shows the mode you would switch TO: sun while dark, moon while light -->
          <svg
            class="nav-icon"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            stroke-width="1.75"
            stroke-linecap="round"
            stroke-linejoin="round"
            aria-hidden="true"
          >
            <template v-if="isDark">
              <circle cx="12" cy="12" r="4" />
              <path
                d="M12 2v2M12 20v2M4.93 4.93l1.41 1.41M17.66 17.66l1.41 1.41M2 12h2M20 12h2M4.93 19.07l1.41-1.41M17.66 6.34l1.41-1.41"
              />
            </template>
            <path v-else d="M21 12.8A9 9 0 1111.2 3a7 7 0 009.8 9.8z" />
          </svg>
          <span class="nav-label">{{ themeLabel }}</span>
        </button>
        <LanguageSwitcher :collapsed="collapsed" />
        <ProfileMenu
          :collapsed="collapsed"
          @show-profile-details="showProfileDetails = true"
          @show-tasks="showTasks = true"
        />
      </div>
    </aside>

    <div class="content">
      <FilterBar />
      <main class="main-content">
        <router-view />
      </main>
    </div>

    <ProfileDetailsModal :is-open="showProfileDetails" @close="showProfileDetails = false" />

    <TasksModal
      :is-open="showTasks"
      :tasks="tasks"
      @close="showTasks = false"
      @add-task="addTask"
      @delete-task="deleteTask"
      @toggle-task="toggleTask"
    />
  </div>
</template>

<script>
import { ref, onMounted, onUnmounted, computed } from 'vue'
import { api } from './api'
import { useAuth } from './composables/useAuth'
import { useI18n } from './composables/useI18n'
import { useTheme } from './composables/useTheme'
import FilterBar from './components/FilterBar.vue'
import ProfileMenu from './components/ProfileMenu.vue'
import ProfileDetailsModal from './components/ProfileDetailsModal.vue'
import TasksModal from './components/TasksModal.vue'
import LanguageSwitcher from './components/LanguageSwitcher.vue'
import NavIcon from './components/NavIcon.vue'

export default {
  name: 'App',
  components: {
    FilterBar,
    ProfileMenu,
    ProfileDetailsModal,
    TasksModal,
    LanguageSwitcher,
    NavIcon
  },
  setup() {
    const { currentUser } = useAuth()
    const { t } = useI18n()
    const { isDark, toggleTheme } = useTheme()
    const themeLabel = computed(() => (isDark.value ? t('nav.switchToLight') : t('nav.switchToDark')))
    const showProfileDetails = ref(false)
    const showTasks = ref(false)
    const apiTasks = ref([])

    // Sidebar navigation, data-driven so new items (or a collapsed icons-only
    // mode, which only needs to hide .nav-label) don't require template edits.
    // `to` is the route path and doubles as the v-for key; `labelKey` is an i18n key;
    // `icon` is a NavIcon name.
    const navItems = [
      { to: '/', labelKey: 'nav.overview', icon: 'overview' },
      { to: '/inventory', labelKey: 'nav.inventory', icon: 'inventory' },
      { to: '/suppliers', labelKey: 'nav.suppliers', icon: 'suppliers' },
      { to: '/orders', labelKey: 'nav.orders', icon: 'orders' },
      { to: '/spending', labelKey: 'nav.finance', icon: 'finance' },
      { to: '/demand', labelKey: 'nav.demandForecast', icon: 'demand' },
      { to: '/restocking', labelKey: 'nav.restocking', icon: 'restocking' },
      { to: '/reports', labelKey: 'nav.reports', icon: 'reports' }
    ]

    // ---- Collapsible sidebar ----
    // Effective state = the user's saved choice if there is one, otherwise the
    // viewport default (collapsed below 1024px). A manual toggle therefore
    // always wins over the breakpoint, and is persisted.
    const STORAGE_KEY = 'sidebar-collapsed'
    const NARROW_QUERY = '(max-width: 1023.98px)'

    // localStorage can throw (private mode, blocked site data), so every access is guarded.
    const readStoredPref = () => {
      try {
        const v = localStorage.getItem(STORAGE_KEY)
        return v === 'true' ? true : v === 'false' ? false : null
      } catch (e) {
        return null
      }
    }
    const writeStoredPref = (value) => {
      try {
        localStorage.setItem(STORAGE_KEY, String(value))
      } catch (e) {
        /* storage unavailable: the choice just lasts for this session */
      }
    }

    const userPref = ref(readStoredPref()) // true | false | null (no manual choice)
    const isNarrow = ref(false)
    const collapsed = computed(() => (userPref.value !== null ? userPref.value : isNarrow.value))
    const toggleLabel = computed(() => (collapsed.value ? t('nav.expandSidebar') : t('nav.collapseSidebar')))

    const toggleSidebar = () => {
      userPref.value = !collapsed.value
      writeStoredPref(userPref.value)
    }

    let mql = null
    const onMediaChange = (e) => {
      isNarrow.value = e.matches
    }
    if (typeof window !== 'undefined' && typeof window.matchMedia === 'function') {
      mql = window.matchMedia(NARROW_QUERY)
      isNarrow.value = mql.matches // set before first render to avoid a flash of the wrong width
      mql.addEventListener('change', onMediaChange)
    }
    onUnmounted(() => {
      if (mql) mql.removeEventListener('change', onMediaChange)
    })

    // Merge mock tasks from currentUser with API tasks
    const tasks = computed(() => {
      return [...currentUser.value.tasks, ...apiTasks.value]
    })

    const loadTasks = async () => {
      try {
        apiTasks.value = await api.getTasks()
      } catch (err) {
        console.error('Failed to load tasks:', err)
      }
    }

    const addTask = async (taskData) => {
      try {
        const newTask = await api.createTask(taskData)
        // Add new task to the beginning of the array
        apiTasks.value.unshift(newTask)
      } catch (err) {
        console.error('Failed to add task:', err)
      }
    }

    const deleteTask = async (taskId) => {
      try {
        // Check if it's a mock task (from currentUser)
        const isMockTask = currentUser.value.tasks.some((t) => t.id === taskId)

        if (isMockTask) {
          // Remove from mock tasks
          const index = currentUser.value.tasks.findIndex((t) => t.id === taskId)
          if (index !== -1) {
            currentUser.value.tasks.splice(index, 1)
          }
        } else {
          // Remove from API tasks
          await api.deleteTask(taskId)
          apiTasks.value = apiTasks.value.filter((t) => t.id !== taskId)
        }
      } catch (err) {
        console.error('Failed to delete task:', err)
      }
    }

    const toggleTask = async (taskId) => {
      try {
        // Check if it's a mock task (from currentUser)
        const mockTask = currentUser.value.tasks.find((t) => t.id === taskId)

        if (mockTask) {
          // Toggle mock task status
          mockTask.status = mockTask.status === 'pending' ? 'completed' : 'pending'
        } else {
          // Toggle API task
          const updatedTask = await api.toggleTask(taskId)
          const index = apiTasks.value.findIndex((t) => t.id === taskId)
          if (index !== -1) {
            apiTasks.value[index] = updatedTask
          }
        }
      } catch (err) {
        console.error('Failed to toggle task:', err)
      }
    }

    onMounted(loadTasks)

    return {
      t,
      navItems,
      collapsed,
      toggleLabel,
      toggleSidebar,
      isDark,
      themeLabel,
      toggleTheme,
      showProfileDetails,
      showTasks,
      tasks,
      addTask,
      deleteTask,
      toggleTask
    }
  }
}
</script>

<style>
/* ---------- Design tokens: the only place raw values live ---------- */
:root {
  /* color */
  --bg: #f8fafc;
  --surface: #ffffff;
  --border: #e2e8f0;
  --text: #0f172a;
  --text-muted: #64748b;
  --accent: #4f46e5;
  --accent-soft: #eef2ff;
  --success: #16a34a;
  --info: #2563eb;
  --warning: #d97706;
  --danger: #dc2626;
  /* Tinted backgrounds for status badges (derived from the status colors above) */
  --success-soft: #dcfce7;
  --info-soft: #dbeafe;
  --warning-soft: #fef3c7;
  --danger-soft: #fee2e2;
  /* Neutrals and status tints that used to be hardcoded hex in components. Light values are the
     original hex so the light theme is unchanged; dark values are overridden below. */
  --border-strong: #cbd5e1;
  --text-faint: #94a3b8;
  --text-secondary: #475569;
  --success-tint: #d1fae5;
  --warning-tint: #fed7aa;
  --danger-tint: #fecaca;
  --success-ink: #065f46;
  --warning-ink: #92400e;
  --danger-ink: #991b1b;
  --info-ink: #1e40af;
  color-scheme: light;
  /* spacing: 4px base */
  --space-1: 4px;
  --space-2: 8px;
  --space-3: 12px;
  --space-4: 16px;
  --space-6: 24px;
  --space-8: 32px;
  /* shape */
  --radius: 10px;
  --radius-sm: 6px;
  --shadow-sm: 0 1px 2px rgba(15, 23, 42, 0.06);
  --shadow-md: 0 4px 12px rgba(15, 23, 42, 0.08);
  /* layout */
  --sidebar-width: 240px;
  --sidebar-width-collapsed: 64px;
}

/* Dark theme: only the color tokens change; spacing/shape/layout tokens are inherited from :root.
   Accent stays a mid-tone indigo so white text on .btn-primary keeps adequate contrast, while
   status colors are lightened so they stay legible on dark surfaces. Soft tints become
   translucent so they sit on any surface instead of glowing as pastel blocks. */
:root[data-theme='dark'] {
  color-scheme: dark; /* native form controls, scrollbars and autofill follow the theme */
  --bg: #020617;
  --surface: #0f172a;
  --border: #1e293b;
  --text: #e2e8f0;
  --text-muted: #94a3b8;
  --accent: #6366f1;
  --accent-soft: rgba(99, 102, 241, 0.16);
  --success: #4ade80;
  --info: #60a5fa;
  --warning: #fbbf24;
  --danger: #f87171;
  --success-soft: rgba(74, 222, 128, 0.15);
  --info-soft: rgba(96, 165, 250, 0.15);
  --warning-soft: rgba(251, 191, 36, 0.15);
  --danger-soft: rgba(248, 113, 113, 0.15);
  --border-strong: #475569;
  --text-faint: #64748b;
  --text-secondary: #cbd5e1;
  --success-tint: rgba(74, 222, 128, 0.18);
  --warning-tint: rgba(251, 191, 36, 0.18);
  --danger-tint: rgba(248, 113, 113, 0.18);
  --success-ink: #86efac;
  --warning-ink: #fcd34d;
  --danger-ink: #fca5a5;
  --info-ink: #93c5fd;
  --shadow-sm: 0 1px 2px rgba(0, 0, 0, 0.4);
  --shadow-md: 0 4px 12px rgba(0, 0, 0, 0.5);
}

* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

body {
  font-family:
    system-ui,
    -apple-system,
    BlinkMacSystemFont,
    'Segoe UI',
    Roboto,
    sans-serif;
  font-size: 14px;
  background: var(--bg);
  color: var(--text);
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
}

:focus-visible {
  outline: 2px solid var(--accent);
  outline-offset: 2px;
}

/* ---------- Shell ---------- */
.app {
  display: grid;
  grid-template-columns: var(--sidebar-width) 1fr;
  min-height: 100vh;
  /* Animating the track size slides the content over smoothly (modern browsers interpolate grid tracks) */
  transition: grid-template-columns 0.2s ease;
}

.app.is-collapsed {
  grid-template-columns: var(--sidebar-width-collapsed) 1fr;
}

.sidebar {
  position: sticky;
  top: 0;
  height: 100vh;
  display: flex;
  flex-direction: column;
  background: var(--surface);
  border-right: 1px solid var(--border);
  z-index: 100;
}

.sidebar-brand {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  padding: var(--space-4) var(--space-4) var(--space-6);
}

.brand-mark {
  flex-shrink: 0;
  width: 32px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: var(--radius-sm);
  background: var(--accent);
  color: #fff;
  font-weight: 600;
  font-size: 16px;
}

.brand-text {
  display: flex;
  flex-direction: column;
  min-width: 0;
}

.brand-name {
  font-size: 14px;
  font-weight: 600;
  color: var(--text);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.brand-subtitle {
  font-size: 12px;
  color: var(--text-muted);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.sidebar-nav {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
  padding: 0 var(--space-3);
  overflow-y: auto;
  overflow-x: hidden; /* labels are nowrap; never let them create a horizontal scrollbar mid-transition */
}

.nav-item {
  position: relative;
  display: flex;
  align-items: center;
  gap: var(--space-3);
  height: 40px;
  padding: 0 var(--space-3);
  border-radius: var(--radius-sm);
  color: var(--text-muted);
  text-decoration: none;
  font-size: 14px;
  font-weight: 500;
  transition:
    background-color 0.15s ease,
    color 0.15s ease;
}

.nav-item .nav-icon {
  width: 20px;
  height: 20px;
  flex-shrink: 0;
}

.nav-item:hover {
  background: var(--accent-soft);
  color: var(--text);
}

.nav-item.router-link-exact-active {
  background: var(--accent-soft);
  color: var(--accent);
}

/* 3px accent bar so the active item is not signalled by color alone */
.nav-item.router-link-exact-active::before {
  content: '';
  position: absolute;
  left: 0;
  top: 8px;
  bottom: 8px;
  width: 3px;
  border-radius: 0 3px 3px 0;
  background: var(--accent);
}

.sidebar-footer {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
  padding: var(--space-3);
  border-top: 1px solid var(--border);
}

/* Toggle button: styled like a nav item but is a <button> */
.sidebar-toggle {
  position: relative;
  display: flex;
  align-items: center;
  gap: var(--space-3);
  height: 40px;
  padding: 0 var(--space-3);
  border: none;
  border-radius: var(--radius-sm);
  background: none;
  color: var(--text-muted);
  font-family: inherit;
  font-size: 14px;
  font-weight: 500;
  white-space: nowrap;
  cursor: pointer;
  transition:
    background-color 0.15s ease,
    color 0.15s ease;
}

.sidebar-toggle:hover {
  background: var(--accent-soft);
  color: var(--text);
}

.sidebar-toggle .nav-icon {
  width: 20px;
  height: 20px;
  flex-shrink: 0;
}

/* Chevron points left (= collapse) when expanded; mirrored when collapsed (= expand) */
.toggle-chevron {
  transform-origin: 14.5px 12px;
  transition: transform 0.2s ease;
}

.is-collapsed .toggle-chevron {
  transform: scaleX(-1);
}

/* ---------- Collapsed (icons-only) rail ---------- */
.is-collapsed .sidebar-brand {
  justify-content: center;
  padding-left: 0;
  padding-right: 0;
}

.is-collapsed .brand-text {
  display: none;
}

/* Labels are visually hidden, not display:none, so links/buttons keep an accessible name.
   (Nav links also carry a title tooltip.) */
.is-collapsed .nav-label {
  position: absolute;
  width: 1px;
  height: 1px;
  overflow: hidden;
  clip: rect(0 0 0 0);
  white-space: nowrap;
}

.is-collapsed .nav-item,
.is-collapsed .sidebar-toggle {
  justify-content: center;
  padding: 0;
}

.is-collapsed .sidebar-footer {
  align-items: stretch;
}

.content {
  min-width: 0; /* let wide tables scroll inside cards instead of stretching the grid column */
}

.main-content {
  max-width: 1400px;
  width: 100%;
  margin: 0 auto;
  padding: var(--space-8);
}

/* Phones: the sidebar stays as the 64px rail; reclaim horizontal room for content */
@media (max-width: 639.98px) {
  .main-content {
    padding: var(--space-4);
  }
}

@media (prefers-reduced-motion: reduce) {
  .app,
  .toggle-chevron {
    transition: none;
  }
}

/* ---------- Shared components ---------- */
.page-header {
  margin-bottom: var(--space-6);
}

.page-header h2 {
  font-size: 24px;
  font-weight: 600;
  color: var(--text);
  margin-bottom: var(--space-1);
}

.page-header p {
  color: var(--text-muted);
  font-size: 14px;
}

.stats-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
  gap: var(--space-4);
  margin-bottom: var(--space-6);
}

.stat-card {
  background: var(--surface);
  padding: var(--space-6);
  border-radius: var(--radius);
  border: 1px solid var(--border);
  box-shadow: var(--shadow-sm);
}

.stat-label {
  color: var(--text-muted);
  font-size: 13px;
  font-weight: 500;
  margin-bottom: var(--space-2);
}

.stat-value {
  font-size: 28px;
  font-weight: 600;
  color: var(--text);
}

/* Status variants keep the card white and only tint the value (no colored card backgrounds) */
.stat-card.warning .stat-value {
  color: var(--warning);
}
.stat-card.success .stat-value {
  color: var(--success);
}
.stat-card.danger .stat-value {
  color: var(--danger);
}
.stat-card.info .stat-value {
  color: var(--info);
}

.card {
  background: var(--surface);
  border-radius: var(--radius);
  padding: var(--space-6);
  border: 1px solid var(--border);
  box-shadow: var(--shadow-sm);
  margin-bottom: var(--space-6);
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: var(--space-4);
  padding-bottom: var(--space-4);
  border-bottom: 1px solid var(--border);
}

.card-title {
  font-size: 16px;
  font-weight: 600;
  color: var(--text);
}

.table-container {
  overflow-x: auto;
}

table {
  width: 100%;
  border-collapse: collapse;
}

thead {
  background: var(--bg);
}

th {
  text-align: left;
  padding: var(--space-3);
  font-weight: 600;
  color: var(--text-muted);
  font-size: 12px;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

td {
  height: 48px; /* acts as min row height on table cells */
  padding: 0 var(--space-3);
  border-top: 1px solid var(--border);
  color: var(--text);
  font-size: 14px;
}

tbody tr {
  transition: background-color 0.15s ease;
}

tbody tr:hover {
  background: var(--accent-soft);
}

.badge {
  display: inline-block;
  padding: var(--space-1) var(--space-2);
  border-radius: var(--radius-sm);
  font-size: 12px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.025em;
}

/* Status badges: soft tint + strong text, mapped onto the four status tokens */
.badge.success,
.badge.increasing {
  background: var(--success-soft);
  color: var(--success);
}

.badge.warning,
.badge.medium {
  background: var(--warning-soft);
  color: var(--warning);
}

.badge.danger,
.badge.decreasing,
.badge.high {
  background: var(--danger-soft);
  color: var(--danger);
}

.badge.info,
.badge.low {
  background: var(--info-soft);
  color: var(--info);
}

.badge.stable {
  background: var(--accent-soft);
  color: var(--accent);
}

/* Global button looks. Views with their own .btn-* scoped rules keep working; these only supply defaults. */
.btn-primary,
.btn-secondary {
  height: 36px;
  padding: 0 var(--space-4);
  border-radius: var(--radius-sm);
  font-family: inherit;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
}

.btn-primary {
  background: var(--accent);
  color: #fff;
  border: 1px solid var(--accent);
}

.btn-secondary {
  background: var(--surface);
  color: var(--text);
  border: 1px solid var(--border);
}

.loading {
  text-align: center;
  padding: var(--space-8);
  color: var(--text-muted);
  font-size: 14px;
}

.error {
  background: var(--danger-soft);
  border: 1px solid var(--danger);
  color: var(--danger);
  padding: var(--space-4);
  border-radius: var(--radius-sm);
  margin: var(--space-4) 0;
  font-size: 14px;
}
</style>
