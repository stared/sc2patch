/**
 * Text measurement utility for SVG text wrapping.
 * Uses off-screen Canvas for fast, accurate width measurement.
 */

let ctx: CanvasRenderingContext2D | null = null;

function getContext(): CanvasRenderingContext2D {
  if (!ctx) {
    const canvas = document.createElement('canvas');
    ctx = canvas.getContext('2d');
  }
  return ctx!;
}

/**
 * Wraps text into lines based on maximum width and font settings.
 * @param text - The text to wrap
 * @param maxWidth - Maximum width in pixels
 * @param font - CSS font string (default matches .change-note in index.css)
 * @returns Array of lines
 */
export function wrapText(
  text: string,
  maxWidth: number,
  font: string = '13px Inter, sans-serif'
): string[] {
  if (maxWidth <= 0) return [text];

  const context = getContext();
  context.font = font;

  // Fast path: check if whole text fits
  if (context.measureText(text).width <= maxWidth) {
    return [text];
  }

  const words = text.split(' ');
  const lines: string[] = [];
  let currentLine = words[0];

  for (let i = 1; i < words.length; i++) {
    const word = words[i];
    const width = context.measureText(currentLine + ' ' + word).width;

    if (width < maxWidth) {
      currentLine += ' ' + word;
    } else {
      lines.push(currentLine);
      currentLine = word;
    }
  }
  lines.push(currentLine);

  return lines;
}
