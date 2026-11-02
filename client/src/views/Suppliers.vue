<template>
  <div class="suppliers">
    <div class="page-header">
      <h2>{{ t('suppliers.title') }}</h2>
      <p>{{ t('suppliers.description') }}</p>
    </div>

    <div v-if="loading" class="loading">{{ t('common.loading') }}</div>
    <div v-else-if="error" class="error">{{ error }}</div>
    <div v-else>
      <div class="card">
        <div class="card-header">
          <h3 class="card-title">{{ t('suppliers.allSuppliers') }} ({{ rows.length }})</h3>
        </div>
        <div class="table-container">
          <table>
            <thead>
              <tr>
                <th>{{ t('suppliers.table.name') }}</th>
                <th>{{ t('suppliers.table.country') }}</th>
                <th>{{ t('suppliers.table.leadTime') }}</th>
                <th>{{ t('suppliers.table.rating') }}</th>
                <th>{{ t('suppliers.table.itemsSupplied') }}</th>
                <th>{{ t('suppliers.table.status') }}</th>
              </tr>
            </thead>
            <tbody>
              <tr
                v-for="s in rows"
                :key="s.id"
                :class="['clickable-row', { selected: selected && selected.id === s.id }]"
                tabindex="0"
                @click="selectSupplier(s)"
                @keydown.enter="selectSupplier(s)"
              >
                <td>
                  <strong>{{ s.name }}</strong>
                </td>
                <td>{{ s.country }}</td>
                <td>{{ t('suppliers.leadTimeDays', { count: s.lead_time_days }) }}</td>
                <td>{{ t('suppliers.ratingOutOf', { rating: s.rating }) }}</td>
                <td>
                  <strong>{{ s.itemCount }}</strong>
                </td>
                <td>
                  <span :class="['badge', s.active ? 'success' : 'warning']">
                    {{ s.active ? t('suppliers.status.active') : t('suppliers.status.inactive') }}
                  </span>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      <!-- Detail panel: shown inline under the table for the clicked supplier -->
      <div v-if="selected" class="card detail-card">
        <div class="card-header">
          <h3 class="card-title">{{ selected.name }}</h3>
          <button class="close-detail" @click="selected = null">{{ t('suppliers.close') }}</button>
        </div>
        <div class="detail-body">
          <h4 class="section-title">{{ t('suppliers.contactDetails') }}</h4>
          <dl class="info-grid">
            <div class="info-item">
              <dt>{{ t('suppliers.table.country') }}</dt>
              <dd>{{ selected.country }}</dd>
            </div>
            <div class="info-item">
              <dt>{{ t('suppliers.table.contactEmail') }}</dt>
              <dd>{{ selected.contact_email }}</dd>
            </div>
            <div class="info-item">
              <dt>{{ t('suppliers.table.leadTime') }}</dt>
              <dd>{{ t('suppliers.leadTimeDays', { count: selected.lead_time_days }) }}</dd>
            </div>
            <div class="info-item">
              <dt>{{ t('suppliers.table.rating') }}</dt>
              <dd>{{ t('suppliers.ratingOutOf', { rating: selected.rating }) }}</dd>
            </div>
          </dl>

          <h4 class="section-title">{{ t('suppliers.suppliedItems') }}</h4>
          <div v-if="itemsLoading" class="muted">{{ t('common.loading') }}</div>
          <div v-else-if="itemsError" class="error-inline">{{ itemsError }}</div>
          <div v-else-if="suppliedItems.length === 0" class="muted">{{ t('suppliers.noItems') }}</div>
          <div v-else class="table-container">
            <table>
              <thead>
                <tr>
                  <th>{{ t('inventory.table.sku') }}</th>
                  <th>{{ t('inventory.table.itemName') }}</th>
                  <th>{{ t('inventory.table.category') }}</th>
                  <th>{{ t('inventory.table.quantityOnHand') }}</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="item in suppliedItems" :key="item.id">
                  <td>
                    <strong>{{ item.sku }}</strong>
                  </td>
                  <td>{{ translateProductName(item.name) }}</td>
                  <td>{{ item.category }}</td>
                  <td>{{ item.quantity_on_hand }}</td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { api } from '../api'
import { useI18n } from '../composables/useI18n'

const { t, translateProductName } = useI18n()

const loading = ref(true)
const error = ref(null)
const suppliers = ref([])
const inventory = ref([])

const selected = ref(null)
const suppliedItems = ref([])
const itemsLoading = ref(false)
const itemsError = ref(null)

// Supplier rows plus the number of inventory SKUs each supplies.
// Counted client-side from one inventory fetch (avoids one request per supplier).
const rows = computed(() => {
  const counts = {}
  for (const item of inventory.value) {
    counts[item.supplier_id] = (counts[item.supplier_id] || 0) + 1
  }
  return suppliers.value.map((s) => ({ ...s, itemCount: counts[s.id] || 0 }))
})

const loadData = async () => {
  try {
    loading.value = true
    error.value = null
    const [supplierList, inventoryList] = await Promise.all([api.getSuppliers(), api.getInventory()])
    suppliers.value = supplierList
    inventory.value = inventoryList
  } catch (err) {
    error.value = t('suppliers.loadError')
    console.error('Suppliers load error:', err)
  } finally {
    loading.value = false
  }
}

const selectSupplier = async (supplier) => {
  selected.value = supplier
  itemsLoading.value = true
  itemsError.value = null
  suppliedItems.value = []
  try {
    // Uses the server-side supplier filter on /api/inventory
    const items = await api.getInventory({ supplier: supplier.id })
    // Guard against a slow response for a previously clicked supplier
    // overwriting the list for the current one.
    if (selected.value && selected.value.id === supplier.id) {
      suppliedItems.value = items
    }
  } catch (err) {
    itemsError.value = t('suppliers.itemsLoadError')
    console.error('Supplied items load error:', err)
  } finally {
    if (selected.value && selected.value.id === supplier.id) {
      itemsLoading.value = false
    }
  }
}

onMounted(loadData)
</script>

<style scoped>
.page-header {
  margin-bottom: var(--space-6);
}

.page-header h2 {
  margin-bottom: var(--space-1);
}

.page-header p {
  color: var(--text-muted);
  font-size: 0.875rem;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: var(--space-6);
  padding: 1.25rem var(--space-6);
  border-bottom: 1px solid var(--border);
}

.card-title {
  font-size: 1rem;
  font-weight: 600;
  color: var(--text);
  margin: 0;
}

.loading,
.error {
  padding: var(--space-8);
  text-align: center;
  color: var(--text-muted);
}

.error,
.error-inline {
  color: var(--danger);
}

.muted {
  color: var(--text-muted);
  font-size: 0.875rem;
}

.clickable-row {
  cursor: pointer;
  transition: background-color 0.15s ease;
}

.clickable-row:hover,
.clickable-row:focus-visible,
.clickable-row.selected {
  background: var(--info-soft) !important;
  outline: none;
}

.detail-card {
  margin-top: var(--space-6);
}

.detail-body {
  padding: var(--space-6);
}

.section-title {
  font-size: 0.8125rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  color: var(--text-muted);
  margin: 0 0 var(--space-3);
}

.info-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: var(--space-4);
  margin: 0 0 var(--space-6);
}

.info-item dt {
  font-size: 0.75rem;
  color: var(--text-muted);
  margin-bottom: var(--space-1);
}

.info-item dd {
  margin: 0;
  color: var(--text);
  font-weight: 500;
  overflow-wrap: anywhere;
}

.close-detail {
  padding: var(--space-2) var(--space-3);
  border: 1px solid var(--border-strong);
  border-radius: var(--radius-sm);
  background: var(--surface);
  color: var(--text-secondary);
  font-size: 0.8125rem;
  cursor: pointer;
}

.close-detail:hover {
  background: var(--bg);
  color: var(--text);
}
</style>
