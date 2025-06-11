<script setup lang="ts">
    import { computed } from 'vue'
    import { useApiStore } from '@/stores/api'
    import Markdown from '@/components/Markdown.vue'
    import apiMarkdown from '@/content/api.md?raw'

    const api = useApiStore()

    const replacements = computed(() => {
        return {
            'apiServer': window.location.origin,
            'apiHost': window.location.host,

            'teamId': api.team?.team_id || '{teamId}',
            'apiKey': api.user?.api_key || '{apiKey}',

            'teamName': api.team?.name || '{teamName}',
            'teamMembers': JSON.stringify(api.team?.members || ['Alice', 'Bob'])
        } as Record<string, string>
    })

    const markdown = computed(() => apiMarkdown.replace(/\$\{([\w.]+?)\}/g, (original: string, tag: string) => replacements.value[tag] || original))
</script>

<template>
    <Markdown :value="markdown"/>
</template>
