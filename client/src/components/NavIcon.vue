<template>
  <!-- Inline SVG icon; color comes from currentColor so hover/active states need no extra CSS -->
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
    <path v-for="(d, i) in paths" :key="i" :d="d" />
  </svg>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  name: { type: String, required: true }
})

// One entry per nav destination; each value is a list of path strings.
const ICONS = {
  overview: ['M3 3h7v9H3z', 'M14 3h7v5h-7z', 'M14 12h7v9h-7z', 'M3 16h7v5H3z'],
  inventory: ['M21 8l-9-5-9 5 9 5 9-5z', 'M3 8v8l9 5 9-5V8', 'M12 13v8'],
  orders: ['M9 3h6a1 1 0 011 1v1H8V4a1 1 0 011-1z', 'M16 5h2a1 1 0 011 1v14a1 1 0 01-1 1H6a1 1 0 01-1-1V6a1 1 0 011-1h2', 'M9 12h6', 'M9 16h6'],
  finance: ['M12 2v20', 'M17 6.5C17 4.8 14.8 4 12 4S7 5 7 7c0 4.5 10 2.5 10 7 0 2-2.2 3-5 3s-5-1-5-2.8'],
  demand: ['M3 3v18h18', 'M7 15l4-4 3 3 5-6'],
  restocking: ['M21 12a9 9 0 01-15.5 6.2', 'M3 12A9 9 0 0118.5 5.8', 'M18.5 2v4h-4', 'M5.5 22v-4h4'],
  reports: ['M14 3H7a2 2 0 00-2 2v14a2 2 0 002 2h10a2 2 0 002-2V8l-5-5z', 'M14 3v5h5', 'M9 13h6', 'M9 17h4']
}

const paths = computed(() => ICONS[props.name] || [])
</script>
