import gradient from "gradient-string";

const VYAPAARCLAW_ASCII = [
  "██╗   ██╗██╗   ██╗ █████╗ ██████╗  █████╗  █████╗ ██████╗  ██████╗██╗      █████╗ ██╗    ██╗",
  "██║   ██║╚██╗ ██╔╝██╔══██╗██╔══██╗██╔══██╗██╔══██╗██╔══██╗██╔════╝██║     ██╔══██╗██║    ██║",
  "██║   ██║ ╚████╔╝ ███████║██████╔╝███████║███████║██████╔╝██║     ██║     ███████║██║ █╗ ██║",
  "╚██╗ ██╔╝  ╚██╔╝  ██╔══██║██╔═══╝ ██╔══██║██╔══██║██╔══██╗██║     ██║     ██╔══██║██║███╗██║",
  " ╚████╔╝    ██║   ██║  ██║██║     ██║  ██║██║  ██║██║  ██║╚██████╗███████╗██║  ██║╚███╔███╔╝",
  "  ╚═══╝     ╚═╝   ╚═╝  ╚═╝╚═╝     ╚═╝  ╚═╝╚═╝  ╚═╝╚═╝  ╚═╝ ╚═════╝╚══════╝╚═╝  ╚═╝ ╚══╝╚══╝ ",
];

// Saffron → White → Green gradient (Indian tricolour)
const TRICOLOUR_GRADIENT = [
  "#FF9933", // saffron
  "#FFAD47",
  "#FFD699",
  "#FFFFFF", // white
  "#FFFFFF",
  "#99E6A0",
  "#4CAF50",
  "#138808", // green
];

// Gold → Deep Green gradient (finance/rupee theme)
const GOLD_GRADIENT = [
  "#DAA520", // goldenrod
  "#FFD700", // gold
  "#FFFACD", // lemon chiffon
  "#FFD700",
  "#00D4AA", // teal accent
  "#00C853", // green
  "#1B5E20", // deep green
];

function rotateArray<T>(arr: T[], offset: number): T[] {
  const n = arr.length;
  const o = ((offset % n) + n) % n;
  return [...arr.slice(o), ...arr.slice(0, o)];
}

function renderFrame(lines: string[], frame: number): string {
  const colors = rotateArray(GOLD_GRADIENT, frame);
  return gradient(colors).multiline(lines.join("\n"));
}

const sleep = (ms: number) =>
  new Promise<void>((resolve) => setTimeout(resolve, ms));

let bannerEmitted = false;

export async function emitBanner(): Promise<void> {
  if (bannerEmitted) return;
  bannerEmitted = true;

  const rich = process.stdout.isTTY;

  process.stdout.write("\n");

  if (rich) {
    const lineCount = VYAPAARCLAW_ASCII.length;
    const fps = 12;
    const totalFrames = GOLD_GRADIENT.length * 3;
    const frameMs = Math.round(1000 / fps);

    process.stdout.write(
      renderFrame(VYAPAARCLAW_ASCII, 0) + "\n"
    );

    for (let frame = 1; frame < totalFrames; frame++) {
      await sleep(frameMs);
      process.stdout.write(`\x1b[${lineCount}A\r`);
      process.stdout.write(
        renderFrame(VYAPAARCLAW_ASCII, frame) + "\n"
      );
    }
  } else {
    process.stdout.write(VYAPAARCLAW_ASCII.join("\n") + "\n");
  }

  const tagline = rich
    ? `  \x1b[1;33mVYAPAARCLAW\x1b[0m \x1b[2mv0.1.0\x1b[0m \x1b[2m—\x1b[0m \x1b[36mThe AI CFO for the Agentic Economy\x1b[0m`
    : "  VYAPAARCLAW v0.1.0 — The AI CFO for the Agentic Economy";

  process.stdout.write(`${tagline}\n\n`);
}
