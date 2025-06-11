<script setup lang="ts">
import { computed } from "vue"
import MarkdownIt from "markdown-it"
import hljs from "highlight.js"

const props = defineProps({
    value: String,
    inline: {
        type: Boolean,
        default: false,
        required: false
    }
})

const markdown = new MarkdownIt({
    html: true,
    linkify: true,

    highlight: (src: string, lang: string) => {
        if (!lang) return src

        try {
            return hljs.highlight(lang, src).value
        } catch {
            return src
        }
    }
})

const html = computed(() => {
    if (props.inline) return markdown.renderInline(props.value || '')
    return markdown.render(props.value || '')
})
</script>

<template>
    <span v-html="html"></span>
</template>

