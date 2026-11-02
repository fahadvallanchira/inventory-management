<template>
  <div class="restocking">
    <div class="page-header">
      <h2>{{ t('restocking.title') }}</h2>
      <p>{{ t('restocking.description') }}</p>
    </div>

    <div v-if="initializing" class="loading">{{ t('common.loading') }}</div>
    <div v-else-if="initError" class="error">{{ initError }}</div>
    <div v-else>
      <!-- Budget slider -->
      <div class="card budget-card">
        <div class="card-header">
          <h3 class="card-title">{{ t('restocking.budget') }}</h3>
          <span class="budget-value">{{ formatMoney(budget, 0) }}</span>
        </div>
        <input
          v-model.number="budget"
          type="range"
          class="budget-slider"
          min="0"
          :max="maxBudget"
          :step="step"
          :aria-label="t('restocking.budget')"
          @input="onBudgetInput"
        />
        <div class="budget-scale">
          <span>{{ formatMoney(0, 0) }}</span>
          <span>{{ t('restocking.budgetMax', { amount: formatMoney(maxBudget, 0) }) }}</span>
        </div>
      </div>

      <!-- Summary -->
      <div class="stats-grid">
        <div :class="['stat-card', isOverBudget ? 'danger' : 'info']">
          <div class="stat-label">{{ t('restocking.summary.selectedTotal') }}</div>
          <div class="stat-value">{{ formatMoney(selectedTotal) }}</div>
          <div class="stat-sub">{{ t('restocking.summary.itemsSelected', { count: selectedCount }) }}</div>
        </div>
        <div class="stat-card">
          <div class="stat-label">{{ t('restocking.summary.budget') }}</div>
          <div class="stat-value">{{ formatMoney(budget, 0) }}</div>
        </div>
        <div :class="['stat-card', isOverBudget ? 'danger' : 'success']">
          <div class="stat-label">{{ t('restocking.summary.remaining') }}</div>
          <div class="stat-value">{{ formatMoney(remainingBudget) }}</div>
        </div>
        <div class="stat-card warning">
          <div class="stat-label">{{ t('restocking.summary.leadTime') }}</div>
          <div class="stat-value">{{ orderLeadTime === null ? '-' : t('restocking.days', { count: orderLeadTime }) }}</div>
        </div>
      </div>

      <!-- Order confirmation -->
      <div v-if="confirmation" class="confirmation" role="status">
        <div class="confirmation-title">{{ t('restocking.confirmation.title') }}</div>
        <div class="confirmation-details">
          <span>{{ t('restocking.confirmation.orderNumber') }}: <strong>{{ confirmation.order_number }}</strong></span>
          <span>{{ t('restocking.confirmation.leadTime') }}: <strong>{{ t('restocking.days', { count: confirmation.lead_time_days }) }}</strong></span>
          <span>{{ t('restocking.confirmation.expectedDelivery') }}: <strong>{{ formatDate(confirmation.expected_delivery) }}</strong></span>
        </div>
        <router-link to="/orders" class="confirmation-link">{{ t('restocking.confirmation.viewOrders') }}</router-link>
      </div>

      <div class="card">
        <div class="card-header">
          <h3 class="card-title">{{ t('restocking.recommendations') }} ({{ rows.length }})</h3>
        </div>

        <div v-if="loadError" class="error">{{ loadError }}</div>
        <div v-else-if="!rows.length && !fetching" class="empty-state">{{ t('restocking.empty') }}</div>
        <div v-else :class="['table-container', { refreshing: fetching }]">
          <table class="restock-table">
            <thead>
              <tr>
                <th class="col-check">{{ t('restocking.table.include') }}</th>
                <th>{{ t('restocking.table.item') }}</th>
                <th>{{ t('restocking.table.category') }}</th>
                <th>{{ t('restocking.table.trend') }}</th>
                <th class="num">{{ t('restocking.table.shortfall') }}</th>
                <th class="num">{{ t('restocking.table.quantity') }}</th>
                <th class="num">{{ t('restocking.table.unitCost') }}</th>
                <th class="num">{{ t('restocking.table.lineCost') }}</th>
                <th class="num">{{ t('restocking.table.leadTime') }}</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="row in rows" :key="row.sku" :class="{ unselected: !row.checked }">
                <td class="col-check">
                  <input v-model="row.checked" type="checkbox" :aria-label="row.sku" />
                </td>
                <td>
                  <strong>{{ row.sku }}</strong>
                  <div class="item-name">{{ row.name }}</div>
                </td>
                <td>{{ row.category }}</td>
                <td>
                  <span :class="['badge', row.trend]">{{ t(`trends.${row.trend}`) }}</span>
                </td>
                <td class="num">{{ row.shortfall }}</td>
                <td class="num">
                  <input
                    class="qty-input"
                    type="number"
                    min="0"
                    :max="row.shortfall"
                    step="1"
                    :value="row.qty"
                    :aria-label="t('restocking.table.quantity')"
                    @input="onQtyInput(row, $event)"
                    @change="onQtyChange(row, $event)"
                  />
                </td>
                <td class="num">{{ formatMoney(row.unit_cost) }}</td>
                <td class="num"><strong>{{ formatMoney(lineCost(row)) }}</strong></td>
                <td class="num">{{ t('restocking.days', { count: row.lead_time_days }) }}</td>
              </tr>
            </tbody>
          </table>
        </div>

        <div class="order-actions">
          <div v-if="isOverBudget" class="warning-text" role="alert">{{ t('restocking.overBudget') }}</div>
          <div v-if="submitError" class="error">{{ submitError }}</div>
          <button class="place-order" type="button" :disabled="!canSubmit" @click="placeOrder">
            {{ submitting ? t('restocking.submitting') : t('restocking.placeOrder') }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import { ref, computed, onMounted, onBeforeUnmount } from 'vue'
import { api } from '../api'
import { useI18n } from '../composables/useI18n'
import { formatCurrencyWithDecimals } from '../utils/currency'

const DEBOUNCE_MS = 250

export default {
  name: 'Restocking',
  setup() {
    const { t, currentCurrency, currentLocale } = useI18n()

    const initializing = ref(true)
    const initError = ref(null)
    const loadError = ref(null)
    const submitError = ref(null)
    const confirmation = ref(null)

    const maxBudget = ref(0)
    const budget = ref(0)
    const rows = ref([]) // recommendation items plus local { checked, qty } edit state
    const fetching = ref(false) // a recommendation request is in flight
    const debouncePending = ref(false) // slider moved, refetch not yet sent
    const submitting = ref(false)

    // Slider step scales with the range so it stays usable for any max_budget.
    const step = computed(() => Math.max(10, Math.round(maxBudget.value / 100)))

    // Each fetch gets an id; only the latest request may write results, so fast
    // slider dragging can never display data from an older budget.
    let requestCounter = 0
    let debounceTimer = null

    const formatMoney = (amount, decimals = 2) =>
      formatCurrencyWithDecimals(amount, currentCurrency.value, decimals)

    const formatDate = (dateString) => {
      const date = new Date(dateString)
      if (isNaN(date.getTime())) return dateString
      return date.toLocaleDateString(currentLocale.value === 'ja' ? 'ja-JP' : 'en-US', {
        year: 'numeric',
        month: 'short',
        day: 'numeric'
      })
    }

    // Returns the response, or null if the request was superseded or failed.
    // Initial load (budget 0) is handled separately by the caller via `init`.
    const fetchRecommendations = async (budgetValue) => {
      const requestId = ++requestCounter
      fetching.value = true
      loadError.value = null
      try {
        const data = await api.getRestockRecommendations(budgetValue)
        if (requestId !== requestCounter) return null // stale response
        // Reset all edits: new recommendations replace checkbox/quantity state.
        rows.value = data.items.map(item => ({ ...item, checked: true, qty: item.quantity }))
        return data
      } catch (err) {
        if (requestId !== requestCounter) return null
        rows.value = []
        loadError.value = t('restocking.loadError') + ': ' + err.message
        return null
      } finally {
        if (requestId === requestCounter) fetching.value = false
      }
    }

    const onBudgetInput = () => {
      // Debounce: only refetch once the slider has been still for DEBOUNCE_MS.
      debouncePending.value = true
      clearTimeout(debounceTimer)
      debounceTimer = setTimeout(async () => {
        debouncePending.value = false
        await fetchRecommendations(budget.value)
      }, DEBOUNCE_MS)
    }

    const init = async () => {
      try {
        // budget=0 is only used to learn max_budget (the slider maximum).
        const data = await api.getRestockRecommendations(0)
        maxBudget.value = data.max_budget
        const stepValue = step.value
        // Default to ~50% of max, rounded to a slider step so the thumb sits on a tick.
        budget.value = Math.round((data.max_budget / 2) / stepValue) * stepValue
      } catch (err) {
        initError.value = t('restocking.loadError') + ': ' + err.message
        initializing.value = false
        return
      }
      initializing.value = false
      await fetchRecommendations(budget.value)
    }

    const lineCost = (row) => row.qty * row.unit_cost

    // Only checked rows with qty > 0 count towards the order.
    const activeRows = computed(() => rows.value.filter(r => r.checked && r.qty > 0))
    const selectedCount = computed(() => activeRows.value.length)
    const selectedTotal = computed(() => activeRows.value.reduce((sum, r) => sum + lineCost(r), 0))
    const remainingBudget = computed(() => budget.value - selectedTotal.value)
    // Small epsilon avoids false positives from floating point accumulation.
    const isOverBudget = computed(() => selectedTotal.value > budget.value + 1e-6)
    const orderLeadTime = computed(() =>
      activeRows.value.length ? Math.max(...activeRows.value.map(r => r.lead_time_days)) : null
    )

    // Block ordering while the table is stale (refetch pending/in flight) so the
    // submitted items always match the budget shown.
    const canSubmit = computed(() =>
      selectedCount.value > 0 &&
      selectedTotal.value > 0 &&
      !isOverBudget.value &&
      !submitting.value &&
      !fetching.value &&
      !debouncePending.value
    )

    // Clamp to [0, shortfall] as a whole number; blank/invalid input counts as 0.
    const clampQty = (row, raw) => {
      const n = Math.floor(Number(raw))
      if (!Number.isFinite(n) || n < 0) return 0
      return Math.min(n, row.shortfall)
    }

    const onQtyInput = (row, event) => {
      row.qty = clampQty(row, event.target.value)
    }

    // On blur/commit, rewrite the field so it shows the clamped value.
    const onQtyChange = (row, event) => {
      row.qty = clampQty(row, event.target.value)
      event.target.value = row.qty
    }

    const placeOrder = async () => {
      if (!canSubmit.value) return
      submitting.value = true
      submitError.value = null
      confirmation.value = null
      try {
        // Server re-prices the lines; we only send sku and quantity.
        const order = await api.submitRestockOrder({
          budget: budget.value,
          items: activeRows.value.map(r => ({ sku: r.sku, quantity: r.qty }))
        })
        confirmation.value = order
        await fetchRecommendations(budget.value)
      } catch (err) {
        const detail = err.response && err.response.data && err.response.data.detail
        submitError.value = typeof detail === 'string'
          ? detail
          : t('restocking.submitError') + ': ' + err.message
      } finally {
        submitting.value = false
      }
    }

    onMounted(init)
    onBeforeUnmount(() => {
      clearTimeout(debounceTimer)
      requestCounter++ // invalidate any in-flight request
    })

    return {
      t,
      initializing,
      initError,
      loadError,
      submitError,
      confirmation,
      maxBudget,
      budget,
      step,
      rows,
      fetching,
      submitting,
      formatMoney,
      formatDate,
      lineCost,
      selectedCount,
      selectedTotal,
      remainingBudget,
      isOverBudget,
      orderLeadTime,
      canSubmit,
      onBudgetInput,
      onQtyInput,
      onQtyChange,
      placeOrder
    }
  }
}
</script>

<style scoped>
.budget-card {
  margin-bottom: var(--space-6);
}

.budget-value {
  font-size: 1.5rem;
  font-weight: 700;
  color: var(--text);
}

.budget-slider {
  width: 100%;
  accent-color: var(--accent);
  margin: var(--space-2) 0 var(--space-1);
}

.budget-scale {
  display: flex;
  justify-content: space-between;
  font-size: 0.813rem;
  color: var(--text-muted);
}

.stat-sub {
  font-size: 0.813rem;
  color: var(--text-muted);
  margin-top: var(--space-1);
}

.confirmation {
  background: var(--success-soft);
  border: 1px solid var(--success-tint);
  color: var(--success-ink);
  padding: var(--space-4) 1.25rem;
  border-radius: var(--radius);
  margin-bottom: var(--space-6);
}

.confirmation-title {
  font-weight: 700;
  margin-bottom: var(--space-2);
}

.confirmation-details {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-2) var(--space-6);
  font-size: 0.938rem;
  margin-bottom: var(--space-2);
}

.confirmation-link {
  color: var(--info);
  font-weight: 600;
  font-size: 0.875rem;
}

.empty-state {
  padding: var(--space-8);
  text-align: center;
  color: var(--text-muted);
}

/* Dim the table while a refetch is in flight instead of blanking it. */
.refreshing {
  opacity: 0.6;
  transition: opacity 0.15s;
}

.restock-table th.num,
.restock-table td.num {
  text-align: right;
}

.col-check {
  width: 70px;
  text-align: center;
}

.item-name {
  font-size: 0.813rem;
  color: var(--text-muted);
}

.unselected td {
  color: var(--text-faint);
}

.qty-input {
  width: 80px;
  padding: 0.375rem var(--space-2);
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  text-align: right;
  font-size: 0.875rem;
  color: var(--text);
}

.qty-input:focus {
  outline: 2px solid var(--accent-soft);
  border-color: var(--accent);
}

.order-actions {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: var(--space-3);
  padding: var(--space-4) var(--space-6) var(--space-6);
}

.order-actions .error {
  align-self: stretch;
  margin: 0;
}

.warning-text {
  align-self: stretch;
  background: var(--warning-soft);
  border: 1px solid var(--warning-tint);
  color: var(--warning-ink);
  padding: var(--space-3) var(--space-4);
  border-radius: var(--radius);
  font-size: 0.875rem;
}

.place-order {
  background: var(--text);
  color: white;
  border: none;
  border-radius: var(--radius);
  padding: 0.625rem var(--space-6);
  font-size: 0.938rem;
  font-weight: 600;
  cursor: pointer;
  transition: background 0.2s;
}

.place-order:hover:not(:disabled) {
  background: var(--text);
}

.place-order:disabled {
  background: var(--border-strong);
  cursor: not-allowed;
}
</style>
