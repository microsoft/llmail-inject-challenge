<script setup lang="ts">
import Markdown from '@/components/Markdown.vue'
import homeMarkdown from '@/content/home.md?raw'
</script>

<template>
  <Markdown :value="homeMarkdown" />
</template>
