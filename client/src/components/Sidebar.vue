<template>
  <aside class="sidebar" :class="{ collapsed: isCollapsed }">
    <div class="sidebar-brand">
      <template v-if="!isCollapsed">
        <h1>{{ t('nav.companyName') }}</h1>
        <span class="subtitle">{{ t('nav.subtitle') }}</span>
      </template>
      <div v-else class="brand-mark" :title="t('nav.companyName')">
        {{ t('nav.brandMark') }}
      </div>
    </div>

    <nav class="sidebar-nav">
      <router-link
        to="/"
        class="nav-item"
        :class="{ active: $route.path === '/' }"
        :aria-label="t('nav.overview')"
        :title="t('nav.overview')"
      >
        <svg class="nav-icon" width="20" height="20" viewBox="0 0 20 20" fill="none" v-html="icons.overview"></svg>
        <span v-if="!isCollapsed" class="nav-label">{{ t('nav.overview') }}</span>
      </router-link>

      <div class="nav-section">
        <span v-if="!isCollapsed" class="nav-section-label">{{ t('nav.sectionOperations') }}</span>
        <div v-else class="sidebar-divider sidebar-divider-section"></div>

        <router-link
          v-for="item in operationsItems"
          :key="item.path"
          :to="item.path"
          class="nav-item"
          :class="{ active: $route.path === item.path }"
          :aria-label="t(item.labelKey)"
          :title="t(item.labelKey)"
        >
          <svg class="nav-icon" width="20" height="20" viewBox="0 0 20 20" fill="none" v-html="icons[item.icon]"></svg>
          <span v-if="!isCollapsed" class="nav-label">{{ t(item.labelKey) }}</span>
        </router-link>
      </div>

      <div class="nav-section">
        <span v-if="!isCollapsed" class="nav-section-label">{{ t('nav.sectionInsights') }}</span>
        <div v-else class="sidebar-divider sidebar-divider-section"></div>

        <router-link
          v-for="item in insightsItems"
          :key="item.path"
          :to="item.path"
          class="nav-item"
          :class="{ active: $route.path === item.path }"
          :aria-label="t(item.labelKey)"
          :title="t(item.labelKey)"
        >
          <svg class="nav-icon" width="20" height="20" viewBox="0 0 20 20" fill="none" v-html="icons[item.icon]"></svg>
          <span v-if="!isCollapsed" class="nav-label">{{ t(item.labelKey) }}</span>
        </router-link>
      </div>
    </nav>

    <button
      class="collapse-toggle"
      type="button"
      @click="toggleCollapse"
      :aria-label="isCollapsed ? t('nav.expandSidebar') : t('nav.collapseSidebar')"
      :title="isCollapsed ? t('nav.expandSidebar') : t('nav.collapseSidebar')"
    >
      <svg
        class="chevron-icon"
        :class="{ 'chevron-rotated': isCollapsed }"
        width="18"
        height="18"
        viewBox="0 0 18 18"
        fill="none"
      >
        <path d="M11 4L6 9L11 14" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
      </svg>
    </button>

    <div class="sidebar-divider"></div>

    <div class="sidebar-footer">
      <LanguageSwitcher :collapsed="isCollapsed" />
      <ProfileMenu
        :collapsed="isCollapsed"
        @show-profile-details="$emit('show-profile-details')"
        @show-tasks="$emit('show-tasks')"
      />
    </div>
  </aside>
</template>

<script>
import { useI18n } from '../composables/useI18n'
import { useSidebar } from '../composables/useSidebar'
import LanguageSwitcher from './LanguageSwitcher.vue'
import ProfileMenu from './ProfileMenu.vue'

// Inline SVG icon paths (stroke-only, 20x20 viewBox, stroke-width 1.5) shared
// by both the expanded and collapsed nav rendering.
const icons = {
  overview: '<rect x="3" y="3" width="6" height="6" rx="1" stroke="currentColor" stroke-width="1.5"/><rect x="11" y="3" width="6" height="6" rx="1" stroke="currentColor" stroke-width="1.5"/><rect x="3" y="11" width="6" height="6" rx="1" stroke="currentColor" stroke-width="1.5"/><rect x="11" y="11" width="6" height="6" rx="1" stroke="currentColor" stroke-width="1.5"/>',
  inventory: '<path d="M3 6L10 3L17 6V14L10 17L3 14V6Z" stroke="currentColor" stroke-width="1.5" stroke-linejoin="round"/><path d="M3 6L10 9L17 6" stroke="currentColor" stroke-width="1.5" stroke-linejoin="round"/><path d="M10 9V17" stroke="currentColor" stroke-width="1.5"/>',
  orders: '<rect x="4" y="3" width="12" height="14" rx="1.5" stroke="currentColor" stroke-width="1.5"/><path d="M7 3V2.5C7 2.22 7.22 2 7.5 2H12.5C12.78 2 13 2.22 13 2.5V3" stroke="currentColor" stroke-width="1.5"/><path d="M7 8H13M7 11H13M7 14H10" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/>',
  finance: '<path d="M4 16V10M10 16V4M16 16V7" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/>',
  demand: '<path d="M3 14L8 9L11 12L17 5" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/><path d="M12 5H17V10" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>',
  restocking: '<path d="M16 8C15.5 5 12.5 3 10 3C6 3 3 6 3 10" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/><path d="M13 3V7H9" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/><path d="M4 12C4.5 15 7.5 17 10 17C14 17 17 14 17 10" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/><path d="M7 17V13H11" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>',
  reports: '<path d="M6 2.5H12L15 5.5V16.5C15 17.05 14.55 17.5 14 17.5H6C5.45 17.5 5 17.05 5 16.5V3.5C5 2.95 5.45 2.5 6 2.5Z" stroke="currentColor" stroke-width="1.5" stroke-linejoin="round"/><path d="M12 2.5V5.5H15" stroke="currentColor" stroke-width="1.5" stroke-linejoin="round"/><path d="M7.5 9H12.5M7.5 11.5H12.5M7.5 14H10.5" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/>',
  backlog: '<path d="M10 3L17 16H3L10 3Z" stroke="currentColor" stroke-width="1.5" stroke-linejoin="round"/><path d="M10 8V11" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/><circle cx="10" cy="13.5" r="0.75" fill="currentColor"/>'
}

export default {
  name: 'Sidebar',
  components: {
    LanguageSwitcher,
    ProfileMenu
  },
  emits: ['show-profile-details', 'show-tasks'],
  setup() {
    const { t } = useI18n()
    const { isCollapsed, toggleCollapse } = useSidebar()

    const operationsItems = [
      { path: '/inventory', labelKey: 'nav.inventory', icon: 'inventory' },
      { path: '/demand', labelKey: 'nav.demandForecast', icon: 'demand' },
      { path: '/restocking', labelKey: 'nav.restocking', icon: 'restocking' },
      { path: '/orders', labelKey: 'nav.orders', icon: 'orders' },
      { path: '/backlog', labelKey: 'nav.backlog', icon: 'backlog' }
    ]

    const insightsItems = [
      { path: '/spending', labelKey: 'nav.finance', icon: 'finance' },
      { path: '/reports', labelKey: 'nav.reports', icon: 'reports' }
    ]

    return {
      t,
      isCollapsed,
      toggleCollapse,
      operationsItems,
      insightsItems,
      icons
    }
  }
}
</script>

<style scoped>
.sidebar {
  display: flex;
  flex-direction: column;
  width: var(--sidebar-width);
  flex-shrink: 0;
  height: 100vh;
  position: sticky;
  top: 0;
  align-self: flex-start;
  background: #ffffff;
  border-right: 1px solid #e2e8f0;
  transition: width 0.2s ease;
  overflow: visible;
}

.sidebar.collapsed {
  width: var(--sidebar-width-collapsed);
}

.sidebar-brand {
  padding: 1.25rem 1.5rem;
  display: flex;
  flex-direction: column;
  gap: 0.125rem;
  border-bottom: 1px solid #e2e8f0;
  min-height: 70px;
  justify-content: center;
  overflow: hidden;
}

.sidebar.collapsed .sidebar-brand {
  padding: 1.25rem 0;
  align-items: center;
}

.sidebar-brand h1 {
  font-size: 1.125rem;
  font-weight: 700;
  color: #0f172a;
  letter-spacing: -0.025em;
  line-height: 1.2;
}

.sidebar-brand .subtitle {
  font-size: 0.75rem;
  color: #64748b;
  font-weight: 400;
}

.brand-mark {
  width: 36px;
  height: 36px;
  border-radius: 8px;
  background: linear-gradient(135deg, #2563eb 0%, #1e40af 100%);
  color: white;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 700;
  font-size: 0.875rem;
  letter-spacing: 0.025em;
}

.sidebar-nav {
  flex: 1;
  overflow-y: auto;
  overflow-x: hidden;
  padding: 0.75rem;
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}

.nav-section {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
  margin-top: 0.75rem;
}

.nav-section-label {
  color: #64748b;
  font-size: 0.875rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  padding: 0.5rem 0.75rem 0.25rem;
}

.sidebar-divider {
  height: 1px;
  background: #e2e8f0;
  margin: 0.5rem 0;
}

.sidebar-divider-section {
  margin: 0.5rem 0.75rem;
}

.nav-item {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 0.625rem 0.75rem;
  color: #64748b;
  text-decoration: none;
  font-weight: 500;
  font-size: 0.938rem;
  border-radius: 6px;
  transition: all 0.2s ease;
  position: relative;
  white-space: nowrap;
}

.sidebar.collapsed .nav-item {
  justify-content: center;
  padding: 0.625rem;
}

.nav-icon {
  flex-shrink: 0;
  color: inherit;
}

.nav-item:hover {
  color: #0f172a;
  background: #f1f5f9;
}

.nav-item.active {
  color: #2563eb;
  background: #eff6ff;
}

.nav-item.active::before {
  content: '';
  position: absolute;
  left: 0;
  top: 0;
  bottom: 0;
  width: 3px;
  background: #2563eb;
}

.nav-item:focus-visible {
  outline: none;
  background: #f1f5f9;
  box-shadow: 0 0 0 2px #2563eb inset;
}

.collapse-toggle {
  display: flex;
  align-items: center;
  justify-content: center;
  margin: 0.5rem 0.75rem;
  padding: 0.5rem;
  background: white;
  border: 1px solid #e2e8f0;
  border-radius: 6px;
  color: #64748b;
  cursor: pointer;
  transition: all 0.2s ease;
}

.collapse-toggle:hover {
  background: #f8fafc;
  border-color: #cbd5e1;
  color: #0f172a;
}

.collapse-toggle:focus-visible {
  outline: none;
  box-shadow: 0 0 0 2px #2563eb;
}

.chevron-icon {
  transition: transform 0.2s ease;
}

.chevron-icon.chevron-rotated {
  transform: rotate(180deg);
}

.sidebar-footer {
  display: flex;
  flex-direction: column;
  gap: 0.375rem;
  padding: 0.75rem;
}
</style>
