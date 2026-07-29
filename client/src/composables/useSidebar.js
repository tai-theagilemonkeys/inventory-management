import { ref } from 'vue'

// Responsive breakpoint below which the sidebar defaults to icons-only.
const BREAKPOINT = 768
const STORAGE_KEY = 'sidebar-collapsed'

const mediaQuery = typeof window !== 'undefined'
  ? window.matchMedia(`(max-width: ${BREAKPOINT - 1}px)`)
  : null

const storedPreference = typeof window !== 'undefined'
  ? localStorage.getItem(STORAGE_KEY)
  : null

// Shared collapse state (singleton pattern, matching useFilters/useI18n).
// Initial value: an explicit stored preference always wins; otherwise fall
// back to the viewport-based default (collapsed below the breakpoint).
const isCollapsed = ref(
  storedPreference !== null
    ? storedPreference === 'true'
    : !!(mediaQuery && mediaQuery.matches)
)

const persist = (value) => {
  if (typeof window !== 'undefined') {
    localStorage.setItem(STORAGE_KEY, String(value))
  }
}

// Auto-collapse when crossing into the narrow breakpoint (live, not just on
// first load). Crossing back to a wide viewport intentionally does NOT
// force-expand or persist anything here, so it never stomps an explicit
// preference the user set while on a wide screen (e.g. manually collapsing
// for more content width) - the manual toggle below remains the only way to
// change state going forward from a narrow->wide crossing.
if (mediaQuery) {
  mediaQuery.addEventListener('change', (event) => {
    if (event.matches) {
      isCollapsed.value = true
      persist(true)
    }
  })
}

export function useSidebar() {
  const toggleCollapse = () => {
    isCollapsed.value = !isCollapsed.value
    persist(isCollapsed.value)
  }

  return {
    isCollapsed,
    toggleCollapse
  }
}
