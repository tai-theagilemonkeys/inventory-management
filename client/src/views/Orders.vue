<template>
  <div class="orders">
    <div class="page-header">
      <h2>{{ t('orders.title') }}</h2>
      <p>{{ t('orders.description') }}</p>
    </div>

    <div v-if="loading" class="loading">{{ t('common.loading') }}</div>
    <div v-else-if="error" class="error">{{ error }}</div>
    <div v-else>
      <div class="stats-grid">
        <div class="stat-card success">
          <div class="stat-label">{{ t('status.delivered') }}</div>
          <div class="stat-value">{{ getOrdersByStatus('Delivered').length }}</div>
        </div>
        <div class="stat-card info">
          <div class="stat-label">{{ t('status.shipped') }}</div>
          <div class="stat-value">{{ getOrdersByStatus('Shipped').length }}</div>
        </div>
        <div class="stat-card warning">
          <div class="stat-label">{{ t('status.processing') }}</div>
          <div class="stat-value">{{ getOrdersByStatus('Processing').length }}</div>
        </div>
        <div class="stat-card danger">
          <div class="stat-label">{{ t('status.backordered') }}</div>
          <div class="stat-value">{{ getOrdersByStatus('Backordered').length }}</div>
        </div>
      </div>

      <div class="card">
        <div class="card-header">
          <h3 class="card-title">{{ t('orders.allOrders') }} ({{ orders.length }})</h3>
        </div>
        <div class="table-container">
          <table class="orders-table">
            <thead>
              <tr>
                <th class="col-order-number">{{ t('orders.table.orderNumber') }}</th>
                <th class="col-customer">{{ t('orders.table.customer') }}</th>
                <th class="col-items">{{ t('orders.table.items') }}</th>
                <th class="col-status">{{ t('orders.table.status') }}</th>
                <th class="col-date">{{ t('orders.table.orderDate') }}</th>
                <th class="col-date">{{ t('orders.table.expectedDelivery') }}</th>
                <th class="col-value">{{ t('orders.table.totalValue') }}</th>
              </tr>
            </thead>
            <tbody>
              <template v-for="order in orders" :key="order.id">
                <tr>
                  <td class="col-order-number"><strong>{{ order.order_number }}</strong></td>
                  <td class="col-customer">{{ translateCustomerName(order.customer) }}</td>
                  <td class="col-items">
                    <details class="items-details" @toggle="onItemsToggle(order.id, $event)">
                      <summary class="items-summary">
                        {{ t('orders.itemsCount', { count: order.items.length }) }}
                      </summary>
                    </details>
                  </td>
                  <td class="col-status">
                    <span :class="['badge', getOrderStatusClass(order.status)]">
                      {{ t(`status.${order.status.toLowerCase()}`) }}
                    </span>
                  </td>
                  <td class="col-date">{{ formatDate(order.order_date) }}</td>
                  <td class="col-date">{{ formatDate(order.expected_delivery) }}</td>
                  <td class="col-value"><strong>{{ formatCurrency(order.total_value, currentCurrency) }}</strong></td>
                </tr>
                <tr v-if="expandedOrderIds.has(order.id)" class="items-expanded-row">
                  <td colspan="7" class="items-expanded-cell">
                    <div class="items-panel">
                      <div class="items-panel-header">
                        <span>{{ t('orders.itemsPanel.item') }}</span>
                        <span class="items-panel-align-right">{{ t('orders.quantity') }}</span>
                        <span class="items-panel-align-right">{{ t('orders.itemsPanel.unitCost') }}</span>
                        <span class="items-panel-align-right">{{ t('orders.itemsPanel.lineTotal') }}</span>
                      </div>
                      <div v-for="item in order.items" :key="item.sku" class="items-panel-row">
                        <div class="items-panel-item-info">
                          <span class="items-panel-item-name">{{ translateProductName(item.name) }}</span>
                          <span class="items-panel-item-sku">{{ item.sku }}</span>
                        </div>
                        <span class="items-panel-qty">{{ item.quantity }}</span>
                        <span class="items-panel-qty">{{ formatCurrency(item.unit_price, currentCurrency) }}</span>
                        <span class="items-panel-line-total">{{ formatCurrency(item.quantity * item.unit_price, currentCurrency) }}</span>
                      </div>
                      <div class="items-panel-footer">
                        <span>{{ t('orders.itemsPanel.total') }}</span>
                        <span class="items-panel-footer-value">{{ formatCurrency(order.total_value, currentCurrency) }}</span>
                      </div>
                    </div>
                  </td>
                </tr>
              </template>
            </tbody>
          </table>
        </div>
      </div>

      <div class="card">
        <div class="card-header">
          <h3 class="card-title">{{ t('orders.submittedOrders.title') }}</h3>
        </div>
        <div v-if="submittedOrders.length === 0" class="empty-state">
          {{ t('orders.submittedOrders.empty') }}
        </div>
        <div v-else class="table-container">
          <table class="submitted-orders-table">
            <thead>
              <tr>
                <th class="col-submitted-order-number">{{ t('orders.submittedOrders.table.orderNumber') }}</th>
                <th class="col-submitted-items">{{ t('orders.submittedOrders.table.items') }}</th>
                <th class="col-submitted-status">{{ t('orders.table.status') }}</th>
                <th class="col-submitted-total-cost col-numeric">{{ t('orders.submittedOrders.table.totalCost') }}</th>
                <th class="col-submitted-date">{{ t('orders.submittedOrders.table.orderDate') }}</th>
                <th class="col-submitted-lead-time">{{ t('orders.submittedOrders.table.leadTime') }}</th>
                <th class="col-submitted-date">{{ t('orders.submittedOrders.table.expectedDelivery') }}</th>
              </tr>
            </thead>
            <tbody>
              <template v-for="order in submittedOrders" :key="order.id">
                <tr>
                  <td class="col-submitted-order-number"><strong>{{ order.order_number }}</strong></td>
                  <td class="col-submitted-items">
                    <details class="items-details" @toggle="onSubmittedItemsToggle(order.id, $event)">
                      <summary class="items-summary">
                        {{ t('orders.itemsCount', { count: order.items.length }) }}
                      </summary>
                    </details>
                  </td>
                  <td class="col-submitted-status">
                    <span class="badge info">{{ t('status.submitted') }}</span>
                  </td>
                  <td class="col-submitted-total-cost col-numeric"><strong>{{ formatCurrency(order.total_cost, currentCurrency) }}</strong></td>
                  <td class="col-submitted-date">{{ formatDate(order.order_date) }}</td>
                  <td class="col-submitted-lead-time">{{ t('orders.submittedOrders.table.days', { count: order.lead_time_days }) }}</td>
                  <td class="col-submitted-date">{{ formatDate(order.expected_delivery) }}</td>
                </tr>
                <tr v-if="expandedSubmittedOrderIds.has(order.id)" class="items-expanded-row">
                  <td colspan="7" class="items-expanded-cell">
                    <div class="items-panel">
                      <div class="items-panel-header">
                        <span>{{ t('orders.submittedOrders.itemsPanel.item') }}</span>
                        <span>{{ t('orders.submittedOrders.itemsPanel.category') }}</span>
                        <span class="items-panel-align-right">{{ t('orders.submittedOrders.itemsPanel.unitCost') }}</span>
                        <span class="items-panel-align-right">{{ t('orders.submittedOrders.itemsPanel.lineTotal') }}</span>
                      </div>
                      <div v-for="item in order.items" :key="item.sku" class="items-panel-row">
                        <div class="items-panel-item-info">
                          <span class="items-panel-item-name">{{ translateProductName(item.name) }}</span>
                          <span class="items-panel-item-sku">{{ item.sku }}</span>
                        </div>
                        <span class="category-tag">{{ item.category }}</span>
                        <span class="items-panel-qty">{{ item.quantity }} &times; {{ formatCurrency(item.unit_cost, currentCurrency) }}</span>
                        <span class="items-panel-line-total">{{ formatCurrency(item.line_total, currentCurrency) }}</span>
                      </div>
                      <div class="items-panel-footer">
                        <span>{{ t('orders.submittedOrders.itemsPanel.total') }}</span>
                        <span class="items-panel-footer-value">{{ formatCurrency(order.total_cost, currentCurrency) }}</span>
                      </div>
                    </div>
                  </td>
                </tr>
              </template>
            </tbody>
          </table>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import { ref, reactive, onMounted, watch } from 'vue'
import { api } from '../api'
import { useFilters } from '../composables/useFilters'
import { useI18n } from '../composables/useI18n'
import { formatCurrency } from '../utils/currency'

export default {
  name: 'Orders',
  setup() {
    const { t, currentCurrency, translateProductName, translateCustomerName } = useI18n()

    const loading = ref(true)
    const error = ref(null)
    const orders = ref([])
    const submittedOrders = ref([])

    // Tracks which orders have their line items expanded. Kept as two separate
    // sets (rather than one shared set) because restock order IDs are generated
    // independently from regular order IDs and can collide (e.g. both "1"),
    // which would otherwise expand unrelated rows across the two tables together.
    const expandedOrderIds = reactive(new Set())
    const expandedSubmittedOrderIds = reactive(new Set())

    const toggleExpanded = (set, orderId, event) => {
      if (event.target.open) {
        set.add(orderId)
      } else {
        set.delete(orderId)
      }
    }

    const onItemsToggle = (orderId, event) => toggleExpanded(expandedOrderIds, orderId, event)
    const onSubmittedItemsToggle = (orderId, event) => toggleExpanded(expandedSubmittedOrderIds, orderId, event)

    // Use shared filters
    const {
      selectedPeriod,
      selectedLocation,
      selectedCategory,
      selectedStatus,
      getCurrentFilters
    } = useFilters()

    const loadOrders = async () => {
      try {
        loading.value = true
        const filters = getCurrentFilters()
        const fetchedOrders = await api.getOrders(filters)

        // Sort orders by order_date (earliest first)
        orders.value = fetchedOrders.sort((a, b) => {
          const dateA = new Date(a.order_date)
          const dateB = new Date(b.order_date)
          return dateA - dateB
        })
      } catch (err) {
        error.value = 'Failed to load orders: ' + err.message
      } finally {
        loading.value = false
      }
    }

    // Watch for filter changes and reload data
    watch([selectedPeriod, selectedLocation, selectedCategory, selectedStatus], () => {
      loadOrders()
    })

    // Submitted restocking orders are intentionally unfiltered - loaded once on mount
    const loadSubmittedOrders = async () => {
      try {
        submittedOrders.value = await api.getRestockOrders()
      } catch (err) {
        console.error('Failed to load submitted restocking orders:', err)
      }
    }

    const getOrdersByStatus = (status) => {
      return orders.value.filter(order => order.status === status)
    }

    const getOrderStatusClass = (status) => {
      const statusMap = {
        'Delivered': 'success',
        'Shipped': 'info',
        'Processing': 'warning',
        'Backordered': 'danger'
      }
      return statusMap[status] || 'info'
    }

    const formatDate = (dateString) => {
      const { currentLocale } = useI18n()
      const locale = currentLocale.value === 'ja' ? 'ja-JP' : 'en-US'
      return new Date(dateString).toLocaleDateString(locale, {
        year: 'numeric',
        month: 'short',
        day: 'numeric'
      })
    }

    onMounted(() => {
      loadOrders()
      loadSubmittedOrders()
    })

    return {
      t,
      loading,
      error,
      orders,
      submittedOrders,
      expandedOrderIds,
      expandedSubmittedOrderIds,
      onItemsToggle,
      onSubmittedItemsToggle,
      getOrdersByStatus,
      getOrderStatusClass,
      formatDate,
      currentCurrency,
      formatCurrency,
      translateProductName,
      translateCustomerName
    }
  }
}
</script>

<style scoped>
/* Fixed table layout to prevent column shifting */
.orders-table {
  table-layout: fixed;
  width: 100%;
}

/* Column widths */
.col-order-number {
  width: 130px;
}

.col-customer {
  width: 180px;
}

.col-items {
  width: 200px;
}

.col-status {
  width: 130px;
}

.col-date {
  width: 140px;
}

.col-value {
  width: 120px;
}

/* Items details styling */
.items-details {
  position: relative;
}

.items-summary {
  cursor: pointer;
  color: #3b82f6;
  font-weight: 500;
  list-style: none;
  user-select: none;
  display: inline-block;
}

.items-summary::-webkit-details-marker {
  display: none;
}

.items-summary::before {
  content: '▶';
  display: inline-block;
  margin-right: 0.375rem;
  font-size: 0.75rem;
  transition: transform 0.2s;
}

.items-details[open] .items-summary::before {
  transform: rotate(90deg);
}

.items-summary:hover {
  color: #2563eb;
  text-decoration: underline;
}

/* Submitted Restocking Orders table */
.submitted-orders-table {
  width: 100%;
  table-layout: fixed;
}

.col-submitted-order-number {
  width: 130px;
}

.col-submitted-items {
  width: 140px;
}

.col-submitted-status {
  width: 120px;
}

.col-submitted-total-cost {
  width: 130px;
}

.col-submitted-date {
  width: 140px;
}

.col-submitted-lead-time {
  width: 110px;
}

.col-numeric {
  text-align: right;
}

/* Expanded items row - spans the full table width so the panel is never
   clipped by an ancestor's overflow, unlike the old absolutely-positioned
   dropdown. */
.items-expanded-row:hover {
  background: transparent;
}

.items-expanded-cell {
  padding: 0 !important;
  border-top: none !important;
}

.items-panel {
  width: 100%;
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  margin: 0.5rem 0 0.75rem 0;
  padding: 0.25rem 1rem;
}

.items-panel-header,
.items-panel-row {
  display: grid;
  grid-template-columns: minmax(200px, 2fr) minmax(120px, 1fr) minmax(160px, 1fr) minmax(120px, 1fr);
  align-items: center;
  gap: 1rem;
  padding: 0.75rem 0;
}

.items-panel-header {
  border-bottom: 1px solid #e2e8f0;
  font-size: 0.75rem;
  font-weight: 600;
  color: #64748b;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.items-panel-row {
  border-bottom: 1px solid #e2e8f0;
}

.items-panel-row:last-of-type {
  border-bottom: none;
}

.items-panel-align-right {
  text-align: right;
}

.items-panel-item-info {
  display: flex;
  flex-direction: column;
  gap: 0.125rem;
  min-width: 0;
}

.items-panel-item-name {
  font-size: 0.875rem;
  font-weight: 500;
  color: #0f172a;
}

.items-panel-item-sku {
  font-size: 0.75rem;
  color: #64748b;
  font-family: monospace;
}

.category-tag {
  display: inline-block;
  align-self: start;
  padding: 0.188rem 0.625rem;
  border-radius: 6px;
  background: #f1f5f9;
  color: #64748b;
  font-size: 0.75rem;
  font-weight: 500;
  white-space: nowrap;
  justify-self: start;
}

.items-panel-qty {
  font-size: 0.875rem;
  color: #64748b;
  text-align: right;
}

.items-panel-line-total {
  font-size: 0.875rem;
  font-weight: 600;
  color: #0f172a;
  text-align: right;
}

.items-panel-footer {
  display: flex;
  justify-content: flex-end;
  align-items: center;
  gap: 1.5rem;
  padding: 0.75rem 0 0.625rem;
  font-size: 0.875rem;
  font-weight: 600;
  color: #0f172a;
}

.items-panel-footer-value {
  min-width: 100px;
  text-align: right;
}

.empty-state {
  padding: 2rem;
  text-align: center;
  color: #64748b;
  font-size: 0.938rem;
}
</style>
