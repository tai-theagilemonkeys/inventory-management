<template>
  <div class="restocking">
    <div class="page-header">
      <h2>{{ t('restocking.title') }}</h2>
      <p>{{ t('restocking.description') }}</p>
    </div>

    <div v-if="loading" class="loading">{{ t('common.loading') }}</div>
    <div v-else-if="error" class="error">{{ error }}</div>
    <div v-else>
      <div class="card budget-card">
        <div class="card-header">
          <h3 class="card-title">{{ t('restocking.budgetLabel') }}</h3>
          <span v-if="refreshing" class="refreshing-indicator">{{ t('restocking.refreshing') }}</span>
        </div>
        <div class="budget-controls">
          <input
            type="range"
            class="budget-slider"
            min="0"
            :max="sliderMax"
            step="50"
            v-model.number="budget"
          />
          <div class="budget-readout">{{ formatCurrency(budget, currentCurrency) }}</div>
        </div>
      </div>

      <div class="stats-grid">
        <div class="stat-card info">
          <div class="stat-label">{{ t('restocking.summary.totalCost') }}</div>
          <div class="stat-value">{{ formatCurrency(summary.total_cost, currentCurrency) }}</div>
        </div>
        <div class="stat-card success">
          <div class="stat-label">{{ t('restocking.summary.remainingBudget') }}</div>
          <div class="stat-value">{{ formatCurrency(summary.remaining_budget, currentCurrency) }}</div>
        </div>
        <div class="stat-card warning">
          <div class="stat-label">{{ t('restocking.summary.maxAddressableCost') }}</div>
          <div class="stat-value">{{ formatCurrency(summary.max_addressable_cost, currentCurrency) }}</div>
        </div>
        <div class="stat-card">
          <div class="stat-label">{{ t('restocking.summary.candidateCount', { count: summary.candidate_count }) }}</div>
          <div class="stat-value">{{ t('restocking.summary.recommendedCount', { count: recommendations.length }) }}</div>
        </div>
      </div>

      <div v-if="placedOrder" class="success-banner">
        {{ t('restocking.orderPlaced', { orderNumber: placedOrder.order_number }) }}
        <router-link to="/orders">{{ t('restocking.viewInOrders') }}</router-link>
      </div>
      <div v-if="orderError" class="error">{{ orderError }}</div>

      <div class="card">
        <div class="card-header">
          <h3 class="card-title">{{ t('restocking.title') }}</h3>
          <button
            class="place-order-btn"
            :disabled="recommendations.length === 0 || placingOrder"
            @click="placeOrder"
          >
            {{ placingOrder ? t('restocking.placingOrder') : t('restocking.placeOrder') }}
          </button>
        </div>

        <div v-if="summary.candidate_count === 0" class="empty-state">
          {{ t('restocking.noCandidates') }}
        </div>
        <div v-else-if="recommendations.length === 0" class="empty-state">
          {{ t('restocking.noRecommendations') }}
        </div>
        <div v-else class="table-container">
          <table>
            <thead>
              <tr>
                <th>{{ t('restocking.table.sku') }}</th>
                <th>{{ t('restocking.table.itemName') }}</th>
                <th>{{ t('restocking.table.category') }}</th>
                <th>{{ t('restocking.table.warehouse') }}</th>
                <th>{{ t('restocking.table.onHand') }}</th>
                <th>{{ t('restocking.table.reorderPoint') }}</th>
                <th>{{ t('restocking.table.forecastedDemand') }}</th>
                <th>{{ t('restocking.table.trend') }}</th>
                <th>{{ t('restocking.table.unitCost') }}</th>
                <th>{{ t('restocking.table.quantity') }}</th>
                <th>{{ t('restocking.table.lineCost') }}</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="rec in recommendations" :key="rec.sku">
                <td><strong>{{ rec.sku }}</strong></td>
                <td>
                  {{ rec.item_name }}
                  <span v-if="rec.is_partial" class="badge warning partial-tag">{{ t('restocking.partial') }}</span>
                </td>
                <td>{{ rec.category }}</td>
                <td>{{ rec.warehouse }}</td>
                <td>{{ rec.quantity_on_hand }}</td>
                <td>{{ rec.reorder_point }}</td>
                <td>{{ rec.forecasted_demand }}</td>
                <td>
                  <span :class="['badge', rec.trend]">{{ t(`trends.${rec.trend}`) }}</span>
                </td>
                <td>{{ formatCurrency(rec.unit_cost, currentCurrency) }}</td>
                <td>{{ rec.recommended_quantity }}</td>
                <td>{{ formatCurrency(rec.line_cost, currentCurrency) }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import { ref, onMounted, watch } from 'vue'
import { api } from '../api'
import { useFilters } from '../composables/useFilters'
import { useI18n } from '../composables/useI18n'
import { formatCurrency } from '../utils/currency'

export default {
  name: 'Restocking',
  setup() {
    const { t, currentCurrency } = useI18n()
    const { selectedLocation, selectedCategory } = useFilters()

    const loading = ref(true)
    const refreshing = ref(false)
    const error = ref(null)
    const orderError = ref(null)
    const placingOrder = ref(false)
    const placedOrder = ref(null)

    const budget = ref(0)
    const sliderMax = ref(1000)
    const recommendations = ref([])
    const summary = ref({
      total_cost: 0,
      remaining_budget: 0,
      max_addressable_cost: 0,
      candidate_count: 0
    })

    // Guard so programmatic budget resets (from the size/reset flow) don't
    // trigger a redundant debounced fetch on top of the one we already run.
    let suppressBudgetWatch = false
    let debounceTimer = null

    const setBudget = (value) => {
      // If the value isn't actually changing, the watcher never fires,
      // so don't arm the suppress flag or it would swallow the next
      // genuine user drag.
      if (budget.value === value) return
      suppressBudgetWatch = true
      budget.value = value
    }

    const fetchRecommendations = async (currentBudget) => {
      const data = await api.getRestockRecommendations({
        budget: currentBudget,
        warehouse: selectedLocation.value,
        category: selectedCategory.value
      })
      recommendations.value = data.recommendations
      summary.value = {
        total_cost: data.total_cost,
        remaining_budget: data.remaining_budget,
        max_addressable_cost: data.max_addressable_cost,
        candidate_count: data.candidate_count
      }
      return data
    }

    // Full "size + fetch" flow: determine the slider ceiling and a sensible
    // default budget for the current filter scope, then fetch real
    // recommendations for that budget.
    const sizeAndLoad = async (isInitial) => {
      try {
        if (isInitial) {
          loading.value = true
        } else {
          refreshing.value = true
        }
        error.value = null

        const sizingData = await api.getRestockRecommendations({
          budget: 0,
          warehouse: selectedLocation.value,
          category: selectedCategory.value
        })

        const maxAddressable = sizingData.max_addressable_cost || 0
        sliderMax.value = maxAddressable > 0 ? Math.ceil(maxAddressable * 1.1 / 50) * 50 : 1000

        const defaultBudget = sizingData.candidate_count > 0
          ? Math.round((sliderMax.value * 0.3) / 50) * 50
          : 0

        setBudget(defaultBudget)

        await fetchRecommendations(defaultBudget)
      } catch (err) {
        error.value = 'Failed to load restock recommendations: ' + err.message
      } finally {
        loading.value = false
        refreshing.value = false
      }
    }

    watch([selectedLocation, selectedCategory], () => {
      sizeAndLoad(false)
    })

    watch(budget, (newBudget) => {
      if (suppressBudgetWatch) {
        suppressBudgetWatch = false
        return
      }

      if (debounceTimer) clearTimeout(debounceTimer)
      debounceTimer = setTimeout(async () => {
        try {
          refreshing.value = true
          await fetchRecommendations(newBudget)
        } catch (err) {
          error.value = 'Failed to load restock recommendations: ' + err.message
        } finally {
          refreshing.value = false
        }
      }, 300)
    })

    const placeOrder = async () => {
      if (recommendations.value.length === 0 || placingOrder.value) return

      placingOrder.value = true
      orderError.value = null
      try {
        const order = await api.placeRestockOrder({
          budget: budget.value,
          warehouse: selectedLocation.value,
          category: selectedCategory.value
        })
        placedOrder.value = order
      } catch (err) {
        orderError.value = t('restocking.noRecommendations')
      } finally {
        placingOrder.value = false
      }
    }

    onMounted(() => sizeAndLoad(true))

    return {
      t,
      currentCurrency,
      formatCurrency,
      loading,
      refreshing,
      error,
      orderError,
      placingOrder,
      placedOrder,
      budget,
      sliderMax,
      recommendations,
      summary,
      placeOrder
    }
  }
}
</script>

<style scoped>
.budget-card {
  margin-bottom: 1.5rem;
}

.refreshing-indicator {
  font-size: 0.813rem;
  color: #64748b;
  font-style: italic;
}

.budget-controls {
  display: flex;
  align-items: center;
  gap: 1.5rem;
}

.budget-slider {
  flex: 1;
  -webkit-appearance: none;
  appearance: none;
  height: 6px;
  border-radius: 999px;
  background: #e2e8f0;
  outline: none;
  cursor: pointer;
}

.budget-slider::-webkit-slider-thumb {
  -webkit-appearance: none;
  appearance: none;
  width: 20px;
  height: 20px;
  border-radius: 50%;
  background: #2563eb;
  border: 3px solid white;
  box-shadow: 0 1px 4px rgba(15, 23, 42, 0.25);
  cursor: pointer;
  transition: transform 0.15s ease;
}

.budget-slider::-webkit-slider-thumb:hover {
  transform: scale(1.1);
}

.budget-slider::-moz-range-thumb {
  width: 20px;
  height: 20px;
  border-radius: 50%;
  background: #2563eb;
  border: 3px solid white;
  box-shadow: 0 1px 4px rgba(15, 23, 42, 0.25);
  cursor: pointer;
  transition: transform 0.15s ease;
}

.budget-slider::-moz-range-thumb:hover {
  transform: scale(1.1);
}

.budget-slider::-moz-range-track {
  height: 6px;
  border-radius: 999px;
  background: #e2e8f0;
}

.budget-readout {
  min-width: 140px;
  text-align: right;
  font-size: 1.25rem;
  font-weight: 700;
  color: #0f172a;
}

.empty-state {
  padding: 2rem;
  text-align: center;
  color: #64748b;
  font-size: 0.938rem;
}

.success-banner {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  background: #d1fae5;
  color: #065f46;
  border: 1px solid #6ee7b7;
  padding: 1rem;
  border-radius: 8px;
  margin-bottom: 1.25rem;
  font-size: 0.938rem;
}

.success-banner a {
  color: #065f46;
  font-weight: 600;
  text-decoration: underline;
}

.place-order-btn {
  background: #2563eb;
  color: white;
  border: none;
  padding: 0.5rem 1.25rem;
  border-radius: 6px;
  font-weight: 600;
  font-size: 0.875rem;
  cursor: pointer;
  transition: background 0.2s ease;
}

.place-order-btn:hover:not(:disabled) {
  background: #1d4ed8;
}

.place-order-btn:disabled {
  background: #cbd5e1;
  cursor: not-allowed;
}

.partial-tag {
  margin-left: 0.5rem;
  font-size: 0.625rem;
  padding: 0.15rem 0.5rem;
}
</style>
