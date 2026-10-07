# Style QA Checklist

Run this checklist before publishing. If any check fails, reassemble the HTML automatically.

## Structure Checks

- [ ] Article structure matches the approved template
- [ ] Headings are formatted identically across all articles
- [ ] Paragraphs are formatted identically
- [ ] Lists are formatted identically
- [ ] Tables are formatted identically
- [ ] FAQ block matches the template
- [ ] CTA block matches the template
- [ ] Spacing and indentation are consistent

## Style Integrity Checks

- [ ] Color palette matches brand colors only (`#cf391b`, `#666666`, `#222222`, `#ffffff`)
- [ ] No new CSS classes added
- [ ] No inline styles outside the template
- [ ] No new decorative elements
- [ ] No new fonts
- [ ] HTML hierarchy matches the editorial system

## Prohibited Modifications

Verify NONE of the following were changed:
- Typography
- HTML block structure
- Indentation logic
- Element border-radius
- Button styles
- List styles
- Table styles
- FAQ styles
- CTA styles
- Quote styles
- Color palette
- Page composition
- CSS classes
- Fonts or icons

## Content Length Validation

- [ ] Article length >= 10,000 characters (with spaces)
- [ ] Article length <= 16,000 characters (with spaces)
- [ ] Target range: 11,500–14,500 characters

## Template Manifest Compliance

- [ ] All HTML blocks are from `template_manifest.json`
- [ ] All CSS classes are from `template_manifest.json`
- [ ] All colors are from `template_manifest.json`
- [ ] All spacing values are from `template_manifest.json`
