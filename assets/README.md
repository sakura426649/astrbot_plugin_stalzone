# 帮助菜单背景与字体

`help_background.jpg` 来自 STALZONE 官方壁纸图库：

<https://stalzone.wiki/en/wallpapers>

原图为 3840×2160，插件内裁剪为 1600×1000、降低亮度并压缩，仅作为 `/sz help` 图片菜单的半透明背景使用。版权归 EXBO / STALZONE 所有；如果不需要该背景，删除此文件后插件会自动回退到纯色渐变背景。

## Playfair Display Italic

`PlayfairDisplay-Italic.ttf` 用于图片右下角 `Created By` 署名。选择衬线斜体而不是连笔手写体，保证在 QQ 压缩后仍清晰可读。字体来自 Google Fonts 的 Playfair Display，采用 SIL Open Font License 1.1，许可证全文见同目录 `PlayfairDisplay-OFL.txt`。

<https://fonts.google.com/specimen/Playfair+Display>


## 阵营图标

`factions/freedom.png`、`factions/duty.png`、`factions/mercenaries.png`、`factions/covenant.png`、`factions/stalkers.png`、`factions/bandits.png` 用于玩家/战队卡右上角的阵营标识（含前期潜行者/强盗），原始图标来自 StalzoneHQ 的阵营图标 CDN（游戏官方阵营徽记），版权归 EXBO / STALZONE 所有。

来源核对（2026-10-23）：

- 潜行者：HQ `/characters` 列表里 `alt="Stalkers"` 的图标实际指向 `https://stalzonehq.com/img/icons/factions/loners.webp`，本地 `stalkers.png` 与该文件解码后逐像素一致；`loners.webp` 只是 HQ 的历史文件名，页面语义是 Stalkers。图案与 STALCRAFT Wiki 的 `File:Stalker.webp` 一致。
- 强盗：`alt="Bandits"` 指向 `https://stalzonehq.com/img/icons/factions/bandits.webp`，本地 `bandits.png` 与之一致；对应 Wiki 的 `File:Bandit.webp`。
- HQ 把 `Rise` 映射到 `freedom.webp`、`Frontier` 映射到 `duty.webp`，插件里的 `rise` / `frontier` 别名沿用同一映射。
