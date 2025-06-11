<script setup lang="ts">
import Markdown from '@/components/Markdown.vue'
import scenariosMarkdown from '@/content/scenarios.md?raw'
</script>

<template>
  <Markdown :value="scenariosMarkdown" />
</template>