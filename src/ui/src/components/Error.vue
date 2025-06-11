<script setup lang="ts">
import Notification from './Notification.vue';

const props = defineProps<{
    error: { message: string; advice: string, trace_id?: string }|Record<string, string>|null|undefined
    kind?: string
}>()
</script>

<template>
    <Notification :kind="props.kind || 'error'" v-if="props.error">
        <p>
            <strong>Error:</strong> {{ props.error.message }}
        </p>
        <p>
            <strong>Advice:</strong> {{ props.error.advice }}
        </p>
        <p v-if="props.error.trace_id">
            <strong>Trace ID:</strong> <code>{{ props.error.trace_id }}</code>
        </p>
    </Notification>
</template>
