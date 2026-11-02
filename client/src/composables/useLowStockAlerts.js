import { ref, computed } from 'vue'
import { api } from '../api'

const DISMISS_KEY = 'low-stock-alert-dismissed'

// sessionStorage can throw (private mode, blocked site data), so every access is guarded.
const readDismissed = () => {
  try {
    return sessionStorage.getItem(DISMISS_KEY) === '1'
  } catch (e) {
    return false
  }
}

// Module-level refs (same pattern as useFilters/useI18n) so the nav badge in
// App.vue and the page banners share one fetch and one dismissed flag.
const count = ref(0)
const criticalCount = ref(0)
const dismissed = ref(readDismissed())

// Deliberately unfiltered: the banner and the nav badge describe overall stock
// health, so they must show the same number regardless of the FilterBar.
const loadAlerts = async () => {
  try {
    const data = await api.getLowStockAlerts()
    count.value = data.count
    criticalCount.value = data.critical_count
  } catch (err) {
    // An alert failure should never break the page; just show nothing.
    console.error('Failed to load low-stock alerts:', err)
  }
}

const dismiss = () => {
  dismissed.value = true
  try {
    sessionStorage.setItem(DISMISS_KEY, '1')
  } catch (e) {
    // Dismissal still holds for this page load via the ref.
  }
}

export function useLowStockAlerts() {
  // The nav badge ignores dismissal: dismissing hides the banner only.
  const showBanner = computed(() => count.value > 0 && !dismissed.value)
  return { count, criticalCount, showBanner, loadAlerts, dismiss }
}
