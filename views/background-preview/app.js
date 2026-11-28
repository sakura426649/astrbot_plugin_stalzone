const bridge = window.AstrBotPluginView;
const grid = document.getElementById("grid");
const status = document.getElementById("status");
const upload = document.getElementById("upload");
const resetButton = document.getElementById("reset");
const saveButton = document.getElementById("save");

let image = null;
let profiles = [];
let crops = {};
let tiles = new Map();
let drag = null;

const clamp = (value, low, high) => Math.min(high, Math.max(low, value));

function setStatus(text, kind = "") {
  status.textContent = text;
  status.className = `status ${kind}`.trim();
}

function payloadOf(result) {
  if (!result || typeof result !== "object") return result;
  if (result.image) return result;
  if (result.data && typeof result.data === "object") return result.data;
  return result;
}

function defaultCrop(profile) {
  const target = profile.width / profile.height;
  const source = image.width / image.height;
  let w = 1;
  let h = 1;
  if (source > target) {
    w = target / source;
  } else {
    h = source / target;
  }
  return { x: (1 - w) / 2, y: (1 - h) / 2, w, h };
}

function normalizeCrop(profile, raw) {
  if (!raw || typeof raw !== "object") return defaultCrop(profile);
  let x = Number(raw.x);
  let y = Number(raw.y);
  let w = Number(raw.w);
  let h = Number(raw.h);
  if (![x, y, w, h].every(Number.isFinite) || w <= 0 || h <= 0) {
    return defaultCrop(profile);
  }
  const target = profile.width / profile.height;
  if (w / h > target) {
    w = h * target;
  } else {
    h = w / target;
  }
  w = clamp(w, 0.02, 1);
  h = clamp(h, 0.02, 1);
  x = clamp(x, 0, 1 - w);
  y = clamp(y, 0, 1 - h);
  return { x, y, w, h };
}

function loadImage(source) {
  return new Promise((resolve, reject) => {
    const img = new Image();
    img.onload = () => resolve(img);
    img.onerror = () => reject(new Error("背景图片加载失败"));
    img.src = source;
  });
}

async function refreshState() {
  if (!bridge) {
    throw new Error("请从 AstrBot 插件页面打开此预览");
  }
  await bridge.ready();
  const result = await bridge.apiGet("background-preview/state");
  const payload = payloadOf(result);
  if (!payload || !payload.image) {
    throw new Error(result?.message || "没有可预览的背景图片");
  }
  profiles = Array.isArray(payload.profiles) ? payload.profiles : [];
  image = await loadImage(payload.image);
  crops = {};
  const saved = payload.crops && typeof payload.crops === "object" ? payload.crops : {};
  for (const profile of profiles) {
    crops[profile.key] = normalizeCrop(profile, saved[profile.key]);
  }
  setStatus(`当前背景：${payload.filename || "内置背景"} · ${image.width}×${image.height}`);
  buildGrid();
}

function canvasSize(profile) {
  const aspect = profile.width / profile.height;
  const width = 640;
  const height = Math.max(1, Math.round(width / aspect));
  return { width, height };
}

function drawTile(key) {
  const tile = tiles.get(key);
  const profile = profiles.find((item) => item.key === key);
  if (!tile || !profile || !image) return;
  const crop = crops[key] || defaultCrop(profile);
  const ctx = tile.canvas.getContext("2d");
  ctx.clearRect(0, 0, tile.canvas.width, tile.canvas.height);
  ctx.drawImage(
    image,
    crop.x * image.width,
    crop.y * image.height,
    crop.w * image.width,
    crop.h * image.height,
    0,
    0,
    tile.canvas.width,
    tile.canvas.height,
  );
}

function buildGrid() {
  grid.replaceChildren();
  tiles = new Map();
  for (const profile of profiles) {
    const tile = document.createElement("section");
    tile.className = "tile";

    const head = document.createElement("div");
    head.className = "tile-head";
    const title = document.createElement("span");
    title.className = "tile-title";
    title.textContent = profile.label || profile.key;
    const meta = document.createElement("span");
    meta.className = "tile-meta";
    meta.textContent = `${profile.width}×${profile.height}`;
    head.append(title, meta);

    const wrap = document.createElement("div");
    wrap.className = "canvas-wrap";
    const canvas = document.createElement("canvas");
    const { width, height } = canvasSize(profile);
    canvas.width = width;
    canvas.height = height;
    wrap.append(canvas);

    const foot = document.createElement("div");
    foot.className = "tile-foot";
    const hint = document.createElement("span");
    hint.textContent = "拖动平移 · 滚轮缩放";
    const reset = document.createElement("button");
    reset.className = "mini";
    reset.type = "button";
    reset.textContent = "重置";
    reset.addEventListener("click", () => {
      crops[profile.key] = defaultCrop(profile);
      drawTile(profile.key);
    });
    foot.append(hint, reset);

    tile.append(head, wrap, foot);
    grid.append(tile);
    tiles.set(profile.key, { canvas, wrap });
    drawTile(profile.key);

    wrap.addEventListener("pointerdown", (event) => {
      if (!image) return;
      const crop = crops[profile.key];
      drag = {
        key: profile.key,
        pointerId: event.pointerId,
        startX: event.clientX,
        startY: event.clientY,
        rect: wrap.getBoundingClientRect(),
        origin: { ...crop },
      };
      wrap.setPointerCapture(event.pointerId);
      event.preventDefault();
    });

    wrap.addEventListener("pointermove", (event) => {
      if (!drag || drag.key !== profile.key || drag.pointerId !== event.pointerId) {
        return;
      }
      const crop = crops[profile.key];
      const dx = (event.clientX - drag.startX) / Math.max(1, drag.rect.width);
      const dy = (event.clientY - drag.startY) / Math.max(1, drag.rect.height);
      crop.x = clamp(drag.origin.x - dx * drag.origin.w, 0, 1 - crop.w);
      crop.y = clamp(drag.origin.y - dy * drag.origin.h, 0, 1 - crop.h);
      drawTile(profile.key);
    });

    const endDrag = (event) => {
      if (!drag || drag.pointerId !== event.pointerId) return;
      drag = null;
    };
    wrap.addEventListener("pointerup", endDrag);
    wrap.addEventListener("pointercancel", endDrag);

    wrap.addEventListener(
      "wheel",
      (event) => {
        if (!image) return;
        event.preventDefault();
        const crop = crops[profile.key];
        const target = profile.width / profile.height;
        const rect = wrap.getBoundingClientRect();
        const px = clamp((event.clientX - rect.left) / Math.max(1, rect.width), 0, 1);
        const py = clamp((event.clientY - rect.top) / Math.max(1, rect.height), 0, 1);
        const factor = event.deltaY > 0 ? 1.1 : 0.9;
        const minW = Math.min(1, Math.max(0.05, 0.05 * target));
        let nextW = clamp(crop.w * factor, minW, 1);
        let nextH = nextW / target;
        if (nextH > 1) {
          nextH = 1;
          nextW = target;
        }
        const focusX = crop.x + px * crop.w;
        const focusY = crop.y + py * crop.h;
        crop.w = nextW;
        crop.h = nextH;
        crop.x = clamp(focusX - px * nextW, 0, 1 - nextW);
        crop.y = clamp(focusY - py * nextH, 0, 1 - nextH);
        drawTile(profile.key);
      },
      { passive: false },
    );
  }
}

async function saveCrops() {
  if (!bridge || !image) return;
  saveButton.disabled = true;
  setStatus("正在保存裁剪…");
  try {
    await bridge.apiPost("background-preview/crops", { profiles: crops });
    setStatus("裁剪已保存，下一次出图生效。", "ok");
  } catch (error) {
    setStatus(`保存失败：${error.message || error}`, "error");
  } finally {
    saveButton.disabled = false;
  }
}

async function uploadBackground(file) {
  if (!bridge) {
    setStatus("请从 AstrBot 插件页面打开此预览。", "error");
    return;
  }
  setStatus(`正在上传 ${file.name}…`);
  try {
    await bridge.upload("background-preview/upload", file);
    await refreshState();
    setStatus("背景已上传，可继续调整裁剪。", "ok");
  } catch (error) {
    setStatus(`上传失败：${error.message || error}`, "error");
  }
}

resetButton.addEventListener("click", () => {
  if (!image) return;
  for (const profile of profiles) {
    crops[profile.key] = defaultCrop(profile);
  }
  for (const key of tiles.keys()) drawTile(key);
  setStatus("已重置为居中裁剪，记得保存。");
});

saveButton.addEventListener("click", saveCrops);

upload.addEventListener("change", async () => {
  const file = upload.files?.[0];
  upload.value = "";
  if (file) await uploadBackground(file);
});

refreshState().catch((error) => {
  console.error(error);
  setStatus(`${error.message || error}`, "error");
});
