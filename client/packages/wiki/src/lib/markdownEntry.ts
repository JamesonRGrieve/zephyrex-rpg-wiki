// SPDX-License-Identifier: AGPL-3.0-or-later
/**
 * A short Markdown body as an entry, as the server's wiki_shared/Markdown.py
 * (contract/markdown-entry-cases.json): headings, bulleted lists and paragraphs, text as written.
 */
type Block = { type: string; children: ({ text: string } | Block)[] };

export function markdownEntry(markdown: string): Block[] {
  const blocks: Block[] = [];
  const paragraph: string[] = [];
  const items: string[] = [];
  const flush = (): void => {
    if (paragraph.length > 0) blocks.push({ type: 'p', children: [{ text: paragraph.splice(0).join(' ') }] });
    if (items.length > 0) blocks.push({ type: 'ul', children: items.splice(0).map((item) => ({ type: 'li', children: [{ text: item }] })) });
  };
  for (const raw of (markdown ?? '').split(/\r?\n/)) {
    const line = raw.trim();
    const heading = /^(#{1,6})\s+(.*)$/.exec(line);
    const bullet = /^[-*]\s+(.*)$/.exec(line);
    if (!line) flush();
    else if (heading) {
      flush();
      blocks.push({ type: `h${heading[1]!.length}`, children: [{ text: heading[2]!.trim() }] });
    } else if (bullet) {
      if (paragraph.length > 0) flush();
      items.push(bullet[1]!.trim());
    } else {
      if (items.length > 0) flush();
      paragraph.push(line);
    }
  }
  flush();
  return blocks;
}
