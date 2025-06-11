<template>
  <div class="custom-select">
    <div class="select-background-click-handler" v-if="dropdownOpen" @click="toggleDropdown"/>
    
    <div :class="{
      'select-selected': true,
      'active': dropdownOpen
    }" @click="toggleDropdown">
      <slot v-if="selectedItem" name="selected" :item="selectedItem" />
      <template v-else>{{ props.placeholder || "Select an item" }}</template>
    </div>
    
    
    <div v-if="dropdownOpen" :class="{
      'select-items': true,
      'active': dropdownOpen
    }">
      <div v-for="item in props.items" :class="{
        'select-item': true,
        'active': item === selectedItem
      }" @click="selectItem(item)">
        <slot name="item" :item="item" />
      </div>
    </div>

  </div>
</template>

<style scoped>
.custom-select {
  position: relative;
  width: 100%;
}

.select-selected {
  padding: 0.5em;
  border: 1px solid var(--color-border);
  border-radius: 5px;
  box-shadow: 1px 1px 5px var(--color-shadow);
  cursor: pointer;
  white-space: normal;
  word-wrap: break-word;
}

.select-selected.active {
  border-radius: 5px 5px 0 0;
}

.select-selected::after {
  display: flex;
  content: '▼';
  position: absolute;
  top: 0;
  right: 0;
  bottom: 0;
  padding: 0.5em;
  flex-direction: column;
  justify-content: center;
  color: var(--color-border);
  transition: transform 0.3s ease;
}

.select-selected.active::after {
  transform: rotate(180deg);
}

.select-items {
  position: absolute;
  width: 100%;
  max-height: 200px;
  overflow-y: auto;
  border: 1px solid var(--color-border);
  border-radius:0 0 5px 5px;
  color: var(--color-text);
  background-color: var(--color-bg);
  z-index: 99;
}

.select-item {
  padding: 0.5em;
  border-left: 4px solid var(--color-bg);
  cursor: pointer;
  white-space: normal;
  word-wrap: break-word;
  transition: background-color 0.3s ease;
}

.select-item:hover {
  border-left: 4px solid var(--color-bg-dark);
  background-color: var(--color-bg-dark);
}

.select-item.active {
  background-color: var(--color-bg-dark);
  border-left: 4px solid var(--color-primary);
}

.select-background-click-handler {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
}
</style>

<script setup lang="ts" generic="T">
import { ref } from 'vue';

const props = defineProps<{
  items: T[],
  placeholder?: string
}>()

const emits = defineEmits<{
  update: [value: T]
}>()

const dropdownOpen = ref(false);
const selectedItem = ref<T | null>(null);

function toggleDropdown() {
  dropdownOpen.value = !dropdownOpen.value;
}

function selectItem(i: T) {
  selectedItem.value = i;
  dropdownOpen.value = false;
  emits('update', i);
}
</script>