<script setup lang="ts">
const props = defineProps<{
    kind?: string
}>()
</script>

<template>
    <div class="notification" :class="props.kind || 'primary'">
        <slot></slot>
    </div>
</template>
