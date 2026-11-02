import { describe, it, expect } from 'vitest'
import { buildGraph, detectLinkKind, renderMarkdown, resolveLink, wikilinks, type Doc, type Note, type Task } from '../components/app/pm/pm'

const note = (id: number, title: string, body = '') => ({ id, title, body }) as Note
const doc = { id: 7, title: 'API spec', extension: 'pdf' } as Doc
const task = { id: 3, key: 'ATL-3', title: 'Ship it' } as Task

describe('Project knowledge graph', () => {
  it('parses [[wikilinks]] with aliases, de-duplicated', () => {
    expect(wikilinks('See [[Roadmap]], [[ API spec |the spec]] and [[Roadmap]] again')).toEqual(['Roadmap', 'API spec'])
  })
  it('resolves notes, then documents, then task keys; unknown targets become ghost notes', () => {
    const notes = [note(1, 'Roadmap')]
    expect(resolveLink('roadmap', notes, [doc], [task], []).id).toBe('note:1')
    expect(resolveLink('API Spec', notes, [doc], [task], []).id).toBe('doc:7')
    expect(resolveLink('atl-3', notes, [doc], [task], []).kind).toBe('task')
    expect(resolveLink('Someday', notes, [doc], [task], []).kind).toBe('ghost')
  })
  it('links every note and doc, adds referenced tasks/ghosts, and never self-links', () => {
    const notes = [note(1, 'Roadmap', '[[API spec]] [[ATL-3]] [[Roadmap]] [[Later]]'), note(2, 'Ideas', '[[Roadmap]]')]
    const { nodes, edges } = buildGraph(notes, [doc], [task], [])
    expect(nodes.map((n) => n.id).sort()).toEqual(['doc:7', 'ghost:later', 'note:1', 'note:2', 'task:3'])
    expect(edges).toHaveLength(4)
    expect(edges.some((e) => e.source === e.target)).toBe(false)
  })
})

describe('Markdown rendering', () => {
  it('strips scripts and event handlers but keeps wikilinks clickable', () => {
    const html = renderMarkdown('# Hi <img src=x onerror="alert(1)"><script>alert(1)</script> [[Roadmap|map]]')
    expect(html).not.toMatch(/script|onerror/)
    expect(html).toContain('href="#wiki:Roadmap"')
    expect(html).toContain('>map</a>')
  })
  it('opens external links in a new tab without opener access', () => {
    expect(renderMarkdown('[x](https://example.com)')).toContain('rel="noopener noreferrer"')
  })
})

describe('Link kinds', () => {
  it('detects common hosts', () => {
    expect(detectLinkKind('https://github.com/thimi/x')).toBe('github')
    expect(detectLinkKind('https://www.figma.com/file/1')).toBe('figma')
    expect(detectLinkKind('https://x.com/thimitech')).toBe('x')
    expect(detectLinkKind('https://thimitech.com')).toBe('web')
    expect(detectLinkKind('not a url')).toBe('web')
  })
})
