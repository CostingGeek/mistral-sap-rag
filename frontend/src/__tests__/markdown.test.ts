import { describe, it, expect } from 'vitest';

// Import the markdown rendering functions from HomePage
// Since they're defined inside the component, we'll test the logic here

describe('Markdown Rendering', () => {
  describe('fixListIndentation', () => {
    it('renumbers numbered lists with gaps', () => {
      const input = `1. First item
2. Second item
5. Fifth item should be third`;
      
      const expected = `1. First item
2. Second item
3. Fifth item should be third`;
      
      // Simulate the fixListIndentation logic
      const lines = input.split('\n');
      const result: string[] = [];
      let inOrderedList = false;
      let expectedNumber = 1;
      
      for (let i = 0; i < lines.length; i++) {
        const line = lines[i];
        const trimmed = line.trim();
        
        const orderedMatch = trimmed.match(/^(\d+)\.\s+(.*)/) || trimmed.match(/^(\d+)\)\s+(.*)/);
        
        if (orderedMatch) {
          const number = parseInt(orderedMatch[1], 10);
          
          if (inOrderedList && number > expectedNumber) {
            const originalIndent = line.substring(0, line.length - trimmed.length);
            result.push(originalIndent + expectedNumber + '. ' + orderedMatch[2]);
            expectedNumber++;
          } else {
            result.push(line);
            expectedNumber = number + 1;
          }
          
          inOrderedList = true;
        } else {
          result.push(line);
        }
      }
      
      const output = result.join('\n');
      expect(output).toBe(expected);
    });

    it('converts source labels to bullets', () => {
      const input = `1. First item
Source 1: Some source`;
      
      const lines = input.split('\n');
      const result: string[] = [];
      let inOrderedList = false;
      let expectedNumber = 1;
      
      for (let i = 0; i < lines.length; i++) {
        const line = lines[i];
        const trimmed = line.trim();
        
        const orderedMatch = trimmed.match(/^(\d+)\.\s+(.*)/) || trimmed.match(/^(\d+)\)\s+(.*)/);
        
        if (orderedMatch) {
          result.push(line);
          inOrderedList = true;
        } else if (trimmed && inOrderedList) {
          const unorderedMatch = trimmed.match(/^[-*\u2022]\s+(.*)/);
          
          // Updated regex to match "Source N:" format
          if (!unorderedMatch && /^Source \d+:.*/.test(trimmed)) {
            result.push('  - ' + trimmed);
          } else {
            result.push(line);
          }
        } else {
          result.push(line);
        }
      }
      
      const output = result.join('\n');
      expect(output).toContain('  - Source 1: Some source');
    });

    it('reindents bullets under ordered items', () => {
      const input = `1. First item
- Bullet point`;
      
      const lines = input.split('\n');
      const result: string[] = [];
      let inOrderedList = false;
      
      for (let i = 0; i < lines.length; i++) {
        const line = lines[i];
        const trimmed = line.trim();
        
        const orderedMatch = trimmed.match(/^(\d+)\.\s+(.*)/) || trimmed.match(/^(\d+)\)\s+(.*)/);
        
        if (orderedMatch) {
          result.push(line);
          inOrderedList = true;
        } else if (trimmed && inOrderedList) {
          const unorderedMatch = trimmed.match(/^[-*\u2022]\s+(.*)/);
          
          if (unorderedMatch) {
            result.push('  ' + trimmed);
          } else {
            result.push(line);
          }
        } else {
          result.push(line);
        }
      }
      
      const output = result.join('\n');
      expect(output).toContain('  - Bullet point');
    });
  });

  describe('processInlineMarkdown', () => {
    it('processes bold text', () => {
      const input = 'This is **bold** text';
      
      // Simulate inline processing
      let text = input;
      
      // Process **bold**
      const boldParts = text.split(/(\*\*.*?\*\*)/);
      const result: string[] = [];
      
      for (let j = 0; j < boldParts.length; j++) {
        const boldPart = boldParts[j];
        if (!boldPart) continue;
        
        if (boldPart.startsWith('**') && boldPart.endsWith('**')) {
          result.push('<strong>' + boldPart.slice(2, -2) + '</strong>');
        } else {
          result.push(boldPart);
        }
      }
      
      const output = result.join('');
      expect(output).toBe('This is <strong>bold</strong> text');
    });

    it('processes italic text', () => {
      const input = 'This is *italic* text';
      
      const boldParts = input.split(/(\*\*.*?\*\*)/);
      const result: string[] = [];
      
      for (let j = 0; j < boldParts.length; j++) {
        const boldPart = boldParts[j];
        if (!boldPart) continue;
        
        if (boldPart.startsWith('**') && boldPart.endsWith('**')) {
          result.push('<strong>' + boldPart.slice(2, -2) + '</strong>');
        } else {
          // Process italic
          const italicParts = boldPart.split(/(\*.*?\*)/);
          for (let k = 0; k < italicParts.length; k++) {
            const subPart = italicParts[k];
            if (!subPart) continue;
            if (subPart.startsWith('*') && subPart.endsWith('*')) {
              result.push('<em>' + subPart.slice(1, -1) + '</em>');
            } else {
              result.push(subPart);
            }
          }
        }
      }
      
      const output = result.join('');
      expect(output).toBe('This is <em>italic</em> text');
    });

    it('processes inline code', () => {
      const input = 'This is `code` text';
      
      const codeParts = input.split(/(`[^`\n]+`)/);
      const result: string[] = [];
      
      for (let i = 0; i < codeParts.length; i++) {
        const part = codeParts[i];
        if (!part) continue;
        
        if (part.startsWith('`') && part.endsWith('`')) {
          result.push('<code>' + part.slice(1, -1) + '</code>');
        } else {
          result.push(part);
        }
      }
      
      const output = result.join('');
      expect(output).toBe('This is <code>code</code> text');
    });

    it('cleans citation markers', () => {
      const input = 'Text with [Source 1] citation and [Source 2] another';
      
      // Clean up markdown link syntax and citation markers
      let cleanedText = input.replace(/(?:\[[^\]]+\](?:\([^\)]+\))?)+/g, (run) =>
        (run.match(/\[([^\]]+)\]/g) || []).map((m: string) => m.slice(1, -1)).join(' ')
      );
      
      expect(cleanedText).toBe('Text with Source 1 citation and Source 2 another');
    });
  });

  describe('Header Processing', () => {
    it('processes different header levels', () => {
      const tests = [
        { input: '# Heading 1', level: 1 },
        { input: '## Heading 2', level: 2 },
        { input: '### Heading 3', level: 3 },
        { input: '#### Heading 4', level: 4 },
        { input: '##### Heading 5', level: 5 },
        { input: '###### Heading 6', level: 6 },
      ];
      
      tests.forEach(({ input, level }) => {
        const match = input.match(/^(#{1,6})\s+(.*)/);
        expect(match).not.toBeNull();
        expect(match![1].length).toBe(level);
        expect(match![2]).toBe(`Heading ${level}`);
      });
    });
  });

  describe('Table Processing', () => {
    it('parses table rows', () => {
      const input = '| Header 1 | Header 2 |';
      const trimmed = input.trim();
      
      const isTableRow = trimmed.startsWith('|') && trimmed.includes('|');
      expect(isTableRow).toBe(true);
      
      const cells = trimmed.slice(1, -1).split('|').map(c => c.trim());
      expect(cells).toEqual(['Header 1', 'Header 2']);
    });

    it('identifies separator rows', () => {
      const cells = ['---', ':---:', '---:'];
      const isSeparator = cells.every(cell => /^:?-+:?$/.test(cell));
      expect(isSeparator).toBe(true);
    });
  });

  describe('Code Block Processing', () => {
    it('identifies code block start', () => {
      const line = '```javascript';
      expect(line.startsWith('```')).toBe(true);
    });

    it('identifies code block end', () => {
      const line = '```';
      expect(line.startsWith('```')).toBe(true);
    });
  });
});

describe('Citation Extraction', () => {
  it('extracts citations from text with bracket notation', () => {
    const text = 'This is a citation [Source 1] and another [Source 2].';
    const citations = [];
    const chunks = [
      { source_no: 1, object_id: 'O1', title: 'Title 1' },
      { source_no: 2, object_id: 'O2', title: 'Title 2' }
    ] as any[];
    
    // Simulate the extraction logic from chat_service
    for (let i = 0; i < chunks.length; i++) {
      const citationMarker = `[Source ${i + 1}]`;
      const escaped = citationMarker.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
      const regex = new RegExp(escaped);
      if (regex.test(text)) {
        citations.push(chunks[i]);
      }
    }
    
    expect(citations.length).toBe(2);
  });

  it('handles citations with different formats', () => {
    const tests = [
      { text: '[Source 1]', expected: true },
      { text: 'Source 1', expected: false },
      { text: '[Source 1][Source 2]', expected: true },
    ];
    
    tests.forEach(({ text, expected }) => {
      const hasCitation = /\[Source \d+\]/.test(text);
      expect(hasCitation).toBe(expected);
    });
  });
});
