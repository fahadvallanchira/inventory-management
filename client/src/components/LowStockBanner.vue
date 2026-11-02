<template>
  <div v-if="showBanner" class="low-stock-banner" :class="{ 'is-critical': criticalCount > 0 }" role="alert">
    <svg
      class="banner-icon"
      viewBox="0 0 20 20"
      fill="none"
      stroke="currentColor"
      stroke-width="1.8"
      stroke-linecap="round"
      stroke-linejoin="round"
      aria-hidden="true"
    >
      <path d="M10 3 2 17h16L10 3Z" />
      <path d="M10 8v4M10 14.5v.01" />
    </svg>
    <div class="banner-text">
      <strong class="banner-title">{{ t('alerts.lowStockTitle') }}</strong>
      <span class="banner-summary">{{ summary }}</span>
      <span v-if="criticalCount > 0" class="banner-critical">{{
        t('alerts.criticalCount', { count: criticalCount })
      }}</span>
    </div>
    <router-link to="/restocking" class="banner-link">{{ t('alerts.reviewRestocking') }}</router-link>
    <button
      type="button"
      class="banner-dismiss"
      :aria-label="t('alerts.dismiss')"
      :title="t('alerts.dismiss')"
      @click="dismiss"
    >
      <svg
        viewBox="0 0 20 20"
        fill="none"
        stroke="currentColor"
        stroke-width="1.8"
        stroke-linecap="round"
        aria-hidden="true"
      >
        <path d="m5 5 10 10M15 5 5 15" />
      </svg>
    </button>
  </div>
</template>

<script setup>
import { computed, onMounted } from 'vue'
import { useI18n } from '../composables/useI18n'
import { useLowStockAlerts } from '../composables/useLowStockAlerts'

const { t } = useI18n()
const { count, criticalCount, showBanner, loadAlerts, dismiss } = useLowStockAlerts()

const summary = computed(() =>
  count.value === 1 ? t('alerts.lowStockSummaryOne') : t('alerts.lowStockSummary', { count: count.value })
)

// Refresh on mount so the banner is current when navigating between views.
onMounted(loadAlerts)
</script>

<style scoped>
/* Warning by default; escalates to danger when any item is critical. Tokens only, so both themes work. */
.low-stock-banner {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  margin-bottom: var(--space-4);
  padding: var(--space-3) var(--space-4);
  background: var(--warning-soft);
  border: 1px solid var(--warning);
  border-radius: var(--radius);
  color: var(--text);
}

.low-stock-banner.is-critical {
  background: var(--danger-soft);
  border-color: var(--danger);
}

.banner-icon {
  width: 20px;
  height: 20px;
  flex-shrink: 0;
  color: var(--warning);
}

.is-critical .banner-icon {
  color: var(--danger);
}

.banner-text {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-wrap: wrap;
  align-items: baseline;
  gap: var(--space-1) var(--space-3);
  font-size: 14px;
}

.banner-summary {
  color: var(--text-secondary);
}

.banner-critical {
  font-weight: 600;
  color: var(--danger);
}

.banner-link {
  flex-shrink: 0;
  font-size: 14px;
  font-weight: 600;
  color: var(--accent);
  text-decoration: none;
}

.banner-link:hover {
  text-decoration: underline;
}

.banner-dismiss {
  flex-shrink: 0;
  display: inline-flex;
  padding: var(--space-1);
  background: transparent;
  border: 0;
  border-radius: var(--radius-sm);
  color: var(--text-muted);
  cursor: pointer;
}

.banner-dismiss:hover {
  color: var(--text);
}

.banner-dismiss svg {
  width: 16px;
  height: 16px;
}

@media (max-width: 640px) {
  .low-stock-banner {
    flex-wrap: wrap;
  }
}
</style>
