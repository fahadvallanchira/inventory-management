import { ref, computed } from 'vue'

const STORAGE_KEY = 'app-theme'

// localStorage can throw (private mode, blocked site data), so every access is guarded.
const readStored = () => {
  try {
    const v = localStorage.getItem(STORAGE_KEY)
    return v === 'dark' || v === 'light' ? v : null
  } catch (e) {
    return null
  }
}

const systemPrefersDark = () =>
  typeof window !== 'undefined' &&
  typeof window.matchMedia === 'function' &&
  window.matchMedia('(prefers-color-scheme: dark)').matches

// Module-level ref (same pattern as useFilters/useI18n) so every consumer shares one theme.
// An explicit saved choice wins; otherwise follow the OS setting on first visit.
const theme = ref(readStored() || (systemPrefersDark() ? 'dark' : 'light'))

// The CSS tokens in App.vue switch on [data-theme="dark"] on <html>.
const applyTheme = (value) => {
  if (typeof document !== 'undefined') {
    document.documentElement.setAttribute('data-theme', value)
  }
}
applyTheme(theme.value)

export function useTheme() {
  const isDark = computed(() => theme.value === 'dark')

  const toggleTheme = () => {
    theme.value = isDark.value ? 'light' : 'dark'
    applyTheme(theme.value)
    try {
      localStorage.setItem(STORAGE_KEY, theme.value)
    } catch (e) {
      /* storage unavailable: the choice just lasts for this session */
    }
  }

  return { theme, isDark, toggleTheme }
}
