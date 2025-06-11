<script setup lang="ts">
import Markdown from '@/components/Markdown.vue'
import rulesMarkdown from '@/content/rules.md?raw'
</script>

<template>
  <Markdown :value="rulesMarkdown" />
</template>