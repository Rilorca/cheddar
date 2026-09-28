#!/usr/bin/env python3
import os
import re

# Read clean G600 SVG
with open('design/g600_inline.svg') as f:
    svg_g600 = f.read()

# Add resolution leader line inside a <g id="ResLeader"> pointing from middle button down-right
res_leader_svg = """
  <g id="ResLeader" class="layer-res-leader">
    <path d="M 308 238 L 340 282 L 380 282" fill="none" stroke="#888a85" stroke-width="1.2" stroke-linecap="round"/>
    <rect x="305" y="235" width="6" height="6" fill="#2e3436" rx="1"/>
    <text x="310" y="300" fill="var(--window-fg)" font-size="11" font-family="'Cantarell', sans-serif" font-weight="500">Ciclo de resolución siguiente</text>
  </g>
"""

# Insert ResLeader before </svg>
svg_g600_enhanced = svg_g600.replace('</svg>', res_leader_svg + '\n</svg>')
svg_g600_enhanced = svg_g600_enhanced.replace('<svg', '<svg class="mouse-hardware-svg" id="mouse-hardware-svg"', 1)

# SVGs for GNOME Symbolic Icons
gear_icon = '<svg width="14" height="14" viewBox="0 0 16 16" fill="currentColor"><path d="M7.07 1a1 1 0 0 0-.96.73L5.8 2.82a5.5 5.5 0 0 0-1.2.69L3.4 2.84a1 1 0 0 0-1.2.24l-1 1.25a1 1 0 0 0 .1 1.37l1.04.93a5.7 5.7 0 0 0-.1 1.37l-1.04.93a1 1 0 0 0-.1 1.37l1 1.25a1 1 0 0 0 1.2.24l1.2-.67c.37.28.77.51 1.2.69l.31 1.09a1 1 0 0 0 .96.73h1.6a1 1 0 0 0 .96-.73l.31-1.09a5.5 5.5 0 0 0 1.2-.69l1.2.67a1 1 0 0 0 1.2-.24l1-1.25a1 1 0 0 0-.1-1.37l-1.04-.93c.06-.45.06-.92 0-1.37l1.04-.93a1 1 0 0 0 .1-1.37l-1-1.25a1 1 0 0 0-1.2-.24l-1.2.67a5.5 5.5 0 0 0-1.2-.69l-.31-1.09A1 1 0 0 0 8.93 1h-1.6zm.93 5a2 2 0 1 1 0 4 2 2 0 0 1 0-4z"/></svg>'
undo_icon = '<svg width="13" height="13" viewBox="0 0 16 16" fill="currentColor"><path d="M6.5 2a.5.5 0 0 0-.35.15L2.15 6.15a.5.5 0 0 0 0 .7l4 4a.5.5 0 0 0 .85-.35V7.5c3.5 0 6 1.5 7 5.5.5-5-2.5-9-7-9.5V2.5a.5.5 0 0 0-.5-.5z"/></svg>'

html_template = f"""<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Cheddar — Diseño Libadwaita (GNOME)</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Cantarell:ital,wght@0,400;0,600;0,700;1,400&family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
  <style>
    :root {{
      /* GNOME Libadwaita Dark Palette Tokens (Faithful to upstream HIG) */
      --window-bg: #242424;
      --window-fg: #ffffff;
      --headerbar-bg: #2f2f2f;
      --headerbar-fg: #ffffff;
      --headerbar-border: rgba(255, 255, 255, 0.08);
      
      --card-bg: rgba(255, 255, 255, 0.06);
      --card-bg-hover: rgba(255, 255, 255, 0.09);
      --card-border: rgba(255, 255, 255, 0.07);
      --row-divider: rgba(255, 255, 255, 0.06);
      
      --accent-color: #1c71d8;
      --accent-hover: #185fb4;
      --accent-active: #13529d;
      --accent-fg: #ffffff;
      
      --destructive-color: #e01b24;
      --destructive-bg: rgba(224, 27, 36, 0.15);
      
      --success-color: #2ec27e;
      --success-bg: rgba(46, 194, 126, 0.15);
      
      --dim-label: rgba(255, 255, 255, 0.65);
      --dim-label-subtle: rgba(255, 255, 255, 0.45);
      
      --switch-bg: rgba(255, 255, 255, 0.18);
      --switch-bg-active: #3584e4;
      --switch-slider: #ffffff;

      --dialog-bg: #303030;
      --dialog-surface: rgba(255, 255, 255, 0.05);

      --radius-large: 12px;
      --radius-medium: 8px;
      --radius-small: 6px;
      --radius-pill: 9999px;
      
      /* Subtle neutral elevation shadows, zero chromatic bloom */
      --shadow-window: 0 20px 50px rgba(0, 0, 0, 0.6), 0 4px 12px rgba(0, 0, 0, 0.4);
      --shadow-card: 0 1px 2px rgba(0, 0, 0, 0.25);
      --shadow-popover: 0 8px 24px rgba(0, 0, 0, 0.4);
    }}

    [data-theme="light"] {{
      --window-bg: #fafafa;
      --window-fg: #2e3436;
      --headerbar-bg: #ebebeb;
      --headerbar-fg: #2e3436;
      --headerbar-border: rgba(0, 0, 0, 0.1);
      
      --card-bg: #ffffff;
      --card-bg-hover: #f5f5f5;
      --card-border: rgba(0, 0, 0, 0.08);
      --row-divider: rgba(0, 0, 0, 0.06);
      
      --dim-label: rgba(0, 0, 0, 0.65);
      --dim-label-subtle: rgba(0, 0, 0, 0.45);
      
      --switch-bg: rgba(0, 0, 0, 0.15);
      --dialog-bg: #ffffff;
      --dialog-surface: #f6f6f6;
      
      --shadow-window: 0 16px 40px rgba(0, 0, 0, 0.2);
      --shadow-card: 0 1px 2px rgba(0, 0, 0, 0.06);
      --shadow-popover: 0 6px 20px rgba(0, 0, 0, 0.15);
    }}

    * {{
      box-sizing: border-box;
      margin: 0;
      padding: 0;
      user-select: none;
      scrollbar-width: thin;
      scrollbar-color: rgba(255, 255, 255, 0.2) transparent;
    }}

    [data-theme="light"] * {{
      scrollbar-color: rgba(0, 0, 0, 0.2) transparent;
    }}

    ::-webkit-scrollbar {{
      width: 6px;
      height: 6px;
    }}
    ::-webkit-scrollbar-track {{
      background: transparent;
    }}
    ::-webkit-scrollbar-thumb {{
      background: rgba(255, 255, 255, 0.2);
      border-radius: var(--radius-pill);
    }}
    [data-theme="light"] ::-webkit-scrollbar-thumb {{
      background: rgba(0, 0, 0, 0.2);
    }}

    ::selection {{
      background: var(--accent-color);
      color: #ffffff;
    }}

    :focus-visible {{
      outline: 2px solid var(--accent-color);
      outline-offset: 2px;
    }}

    body {{
      background: #111418;
      background-image: 
        radial-gradient(circle at 50% 15%, rgba(53, 132, 228, 0.12), transparent 55%),
        linear-gradient(180deg, #15181e 0%, #0d0f12 100%);
      font-family: 'Cantarell', 'Inter', system-ui, -apple-system, sans-serif;
      min-height: 100vh;
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      padding: 24px 16px;
      color: var(--window-fg);
      -webkit-font-smoothing: antialiased;
    }}

    /* Top Controls Bar for the Mockup */
    .mockup-toolbar {{
      display: flex;
      align-items: center;
      gap: 12px;
      margin-bottom: 16px;
      background: rgba(28, 28, 28, 0.85);
      backdrop-filter: blur(12px);
      border: 1px solid rgba(255, 255, 255, 0.1);
      padding: 7px 18px;
      border-radius: var(--radius-pill);
      font-size: 13px;
      color: var(--dim-label);
      flex-wrap: wrap;
      justify-content: center;
    }}
    .mockup-toolbar button {{
      background: none;
      border: none;
      color: #fff;
      font-family: inherit;
      font-size: 12.5px;
      font-weight: 600;
      cursor: pointer;
      display: flex;
      align-items: center;
      gap: 6px;
      padding: 6px 14px;
      border-radius: var(--radius-pill);
      background: rgba(255, 255, 255, 0.08);
      transition: all 0.15s ease;
    }}
    .mockup-toolbar button:hover {{
      background: rgba(255, 255, 255, 0.15);
      color: #fff;
    }}
    .mockup-tag {{
      background: rgba(53, 132, 228, 0.18);
      color: #78aeed;
      padding: 3px 10px;
      border-radius: var(--radius-pill);
      font-size: 12px;
      font-weight: 700;
    }}

    /* ── Reset Button in Libadwaita Style ──────────────────────────────── */
    .btn-reset {{
      display: inline-flex;
      align-items: center;
      gap: 6px;
      background: rgba(255, 255, 255, 0.06);
      border: 1px solid var(--card-border);
      color: var(--dim-label);
      padding: 4px 10px;
      border-radius: var(--radius-pill);
      font-size: 11.5px;
      font-weight: 600;
      cursor: pointer;
      white-space: nowrap;
      flex-shrink: 0;
      transition: all 0.15s ease;
    }}
    .btn-reset:hover {{
      background: rgba(224, 27, 36, 0.14);
      color: #ff7b82;
      border-color: rgba(224, 27, 36, 0.35);
    }}
    .btn-reset svg {{
      transition: transform 0.25s ease;
    }}
    .btn-reset:hover svg {{
      transform: rotate(-90deg);
    }}

    /* ── GNOME Libadwaita Window ───────────────────────────────────────── */
    .adw-window {{
      width: 100%;
      max-width: 1060px;
      height: 720px;
      color: var(--window-fg);
      border-radius: 14px;
      box-shadow: 0 0 0 1px var(--headerbar-border), var(--shadow-window);
      display: flex;
      flex-direction: column;
      overflow: hidden;
      position: relative;
      transition: background 0.25s ease, color 0.25s ease;
    }}

    /* ── AdwHeaderBar ──────────────────────────────────────────────────── */
    .adw-headerbar {{
      height: 52px;
      background: var(--headerbar-bg);
      border-bottom: 1px solid var(--headerbar-border);
      display: flex;
      align-items: center;
      justify-content: space-between;
      padding: 0 14px;
      flex-shrink: 0;
      z-index: 20;
    }}

    .header-left, .header-right {{
      display: flex;
      align-items: center;
      gap: 8px;
      min-width: 200px;
    }}

    .header-right {{
      justify-content: flex-end;
    }}

    /* Profile Selector Dropdown */
    .adw-profile-button {{
      display: flex;
      align-items: center;
      gap: 8px;
      background: rgba(255, 255, 255, 0.08);
      border: 1px solid rgba(255, 255, 255, 0.06);
      color: var(--window-fg);
      padding: 6px 12px;
      border-radius: var(--radius-small);
      font-size: 13px;
      font-weight: 600;
      cursor: pointer;
      transition: background 0.15s ease;
      position: relative;
    }}
    .adw-profile-button:hover {{
      background: rgba(255, 255, 255, 0.14);
    }}
    .adw-profile-button svg {{
      opacity: 0.8;
    }}

    /* View Switcher Pill Bar (HeaderBar Top Tabs) */
    .adw-view-switcher {{
      display: flex;
      background: rgba(0, 0, 0, 0.22);
      border: 1px solid rgba(255, 255, 255, 0.05);
      border-radius: var(--radius-pill);
      padding: 3px;
      gap: 2px;
    }}
    .adw-view-tab {{
      display: flex;
      align-items: center;
      gap: 8px;
      padding: 6px 18px;
      border-radius: var(--radius-pill);
      font-size: 13px;
      font-weight: 600;
      color: var(--dim-label);
      cursor: pointer;
      transition: all 0.18s ease;
    }}
    .adw-view-tab:hover {{
      color: var(--window-fg);
    }}
    .adw-view-tab.active {{
      background: var(--accent-color);
      color: #fff;
    }}

    /* Apply button (in HeaderBar) */
    .btn-apply {{
      padding: 6px 14px;
      border-radius: var(--radius-small);
      font-size: 13px;
      font-weight: 600;
      background: rgba(255, 255, 255, 0.08);
      border: 1px solid var(--card-border);
      color: var(--window-fg);
      cursor: pointer;
      transition: all 0.15s ease;
      display: none;
    }}
    .btn-apply.active {{
      background: var(--accent-color);
      color: #fff;
      border-color: transparent;
    }}
    .btn-apply:hover {{
      background: var(--accent-hover);
      color: #fff;
    }}

    /* Icon Buttons */
    .icon-button {{
      width: 32px;
      height: 32px;
      border-radius: var(--radius-small);
      border: none;
      background: transparent;
      color: var(--window-fg);
      display: flex;
      align-items: center;
      justify-content: center;
      cursor: pointer;
      transition: background 0.15s ease;
    }}
    .icon-button:hover {{
      background: rgba(255, 255, 255, 0.1);
    }}

    /* Window Controls (Libadwaita specifications) */
    .adw-window-controls {{
      display: flex;
      align-items: center;
      gap: 6px;
      margin-left: 6px;
    }}
    .window-button {{
      width: 24px;
      height: 24px;
      border-radius: 50%;
      border: none;
      background: transparent;
      color: var(--window-fg);
      opacity: 0.75;
      display: flex;
      align-items: center;
      justify-content: center;
      cursor: pointer;
      transition: background 0.15s ease, opacity 0.15s ease, color 0.15s ease;
      padding: 0;
    }}
    .window-button:hover {{
      opacity: 1;
      background: rgba(255, 255, 255, 0.12);
    }}
    body.light-theme .window-button:hover {{
      background: rgba(0, 0, 0, 0.08);
    }}
    .window-button.close:hover {{
      background: #e01b24;
      color: #ffffff;
      opacity: 1;
    }}

    /* ── Content Container ─────────────────────────────────────────────── */
    .adw-content {{
      background: var(--window-bg);
      flex: 1;
      overflow-y: auto;
      overflow-x: hidden;
      display: flex;
      flex-direction: column;
      position: relative;
    }}

    .main-page {{
      flex: 1;
      display: none;
      flex-direction: column;
      animation: fadeIn 0.18s ease;
    }}
    .main-page.active {{
      display: flex;
    }}

    @keyframes fadeIn {{
      from {{ opacity: 0; }}
      to {{ opacity: 1; }}
    }}

    /* ── AutoPilot View Styles ─────────────────────────────────────────── */
    .adw-clamp {{
      width: 100%;
      max-width: 680px;
      margin: 0 auto;
      padding: 24px 20px 40px;
      display: flex;
      flex-direction: column;
      gap: 22px;
    }}

    .adw-hero-card {{
      background: rgba(53, 132, 228, 0.1);
      border: 1px solid rgba(53, 132, 228, 0.25);
      border-radius: var(--radius-large);
      padding: 18px 22px;
      display: flex;
      align-items: center;
      justify-content: space-between;
    }}
    .hero-info {{
      display: flex;
      align-items: center;
      gap: 16px;
    }}
    .status-pulse-container {{
      position: relative;
      width: 28px;
      height: 28px;
      display: flex;
      align-items: center;
      justify-content: center;
    }}
    .status-dot {{
      width: 12px;
      height: 12px;
      border-radius: 50%;
      background: var(--success-color);
      z-index: 2;
    }}
    .status-ring {{
      position: absolute;
      width: 24px;
      height: 24px;
      border-radius: 50%;
      border: 2px solid var(--success-color);
      opacity: 0.5;
      animation: pulseRing 2s infinite ease-out;
    }}
    @keyframes pulseRing {{
      0% {{ transform: scale(0.6); opacity: 0.8; }}
      100% {{ transform: scale(1.2); opacity: 0; }}
    }}
    .hero-title {{
      font-size: 15px;
      font-weight: 700;
      letter-spacing: -0.1px;
    }}
    .hero-subtitle {{
      font-size: 13px;
      color: var(--dim-label);
      margin-top: 3px;
      display: flex;
      align-items: center;
      gap: 8px;
    }}
    .hero-badge {{
      display: inline-block;
      font-size: 12px;
      font-weight: 700;
      padding: 2px 8px;
      border-radius: var(--radius-pill);
      background: var(--success-bg);
      color: var(--success-color);
    }}

    .group-header {{
      display: flex;
      align-items: center;
      justify-content: space-between;
      margin-bottom: 8px;
      padding: 0 4px;
    }}
    .group-title {{
      font-size: 13px;
      font-weight: 700;
      color: var(--dim-label);
    }}
    .group-description {{
      font-size: 13px;
      color: var(--dim-label-subtle);
      margin-top: 2px;
    }}

    .adw-boxed-list {{
      background: var(--card-bg);
      border: 1px solid var(--card-border);
      border-radius: var(--radius-large);
      overflow: hidden;
    }}
    .adw-row {{
      display: flex;
      align-items: center;
      padding: 13px 16px;
      border-bottom: 1px solid var(--row-divider);
      transition: background 0.15s ease;
      gap: 14px;
    }}
    .adw-row:last-child {{
      border-bottom: none;
    }}
    .adw-row:hover {{
      background: var(--card-bg-hover);
    }}

    .game-icon-squircle {{
      width: 40px;
      height: 40px;
      border-radius: 8px;
      display: flex;
      align-items: center;
      justify-content: center;
      font-weight: 700;
      font-size: 17px;
      flex-shrink: 0;
      overflow: hidden;
    }}
    .game-details {{
      flex: 1;
      min-width: 0;
    }}
    .game-name {{
      font-size: 14.5px;
      font-weight: 600;
      color: var(--window-fg);
      display: flex;
      align-items: center;
      gap: 8px;
    }}
    .game-meta {{
      font-size: 13px;
      color: var(--dim-label);
      margin-top: 2px;
      font-family: 'Cantarell', sans-serif;
    }}
    .faugus-chip {{
      font-size: 12px;
      font-weight: 600;
      padding: 2px 8px;
      border-radius: var(--radius-pill);
      background: rgba(255, 120, 0, 0.15);
      color: #ff8c37;
    }}

    .adw-dropdown {{
      background: rgba(255, 255, 255, 0.08);
      border: 1px solid var(--card-border);
      color: var(--window-fg);
      border-radius: var(--radius-small);
      padding: 6px 12px;
      font-size: 13px;
      font-weight: 500;
      cursor: pointer;
      display: flex;
      align-items: center;
      gap: 8px;
      transition: background 0.15s ease;
    }}

    .adw-switch {{
      width: 44px;
      height: 24px;
      background: var(--switch-bg);
      border-radius: var(--radius-pill);
      position: relative;
      cursor: pointer;
      transition: background 0.22s ease;
      flex-shrink: 0;
    }}
    .adw-switch.active {{
      background: var(--switch-bg-active);
    }}
    .switch-slider {{
      width: 18px;
      height: 18px;
      background: var(--switch-slider);
      border-radius: 50%;
      position: absolute;
      top: 3px;
      left: 3px;
      transition: transform 0.22s cubic-bezier(0.16, 1, 0.3, 1);
      box-shadow: 0 1px 3px rgba(0, 0, 0, 0.3);
    }}
    .adw-switch.active .switch-slider {{
      transform: translateX(20px);
    }}

    .btn-suggested {{
      background: var(--accent-color);
      color: #fff;
      border: none;
      padding: 6px 14px;
      border-radius: var(--radius-small);
      font-size: 13px;
      font-weight: 600;
      cursor: pointer;
      display: flex;
      align-items: center;
      gap: 6px;
      transition: background 0.15s ease;
    }}
    .btn-suggested:hover {{
      background: var(--accent-hover);
    }}

    /* ── Mouse Setup View Styles ───────────────────────────────────────── */
    .mouse-setup-container {{
      flex: 1;
      display: flex;
      flex-direction: column;
      height: 100%;
    }}

    /* Sub-Stack Switcher (Resoluciones | Botones | LEDs | Advanced) */
    .sub-switcher-bar {{
      display: flex;
      justify-content: center;
      padding: 12px 24px;
      flex-shrink: 0;
    }}
    .sub-switcher {{
      display: flex;
      background: rgba(0, 0, 0, 0.2);
      border: 1px solid var(--card-border);
      border-radius: var(--radius-pill);
      padding: 3px;
      gap: 3px;
    }}
    .sub-tab {{
      padding: 6px 20px;
      border-radius: var(--radius-pill);
      font-size: 13px;
      font-weight: 600;
      color: var(--dim-label);
      cursor: pointer;
      transition: all 0.18s ease;
    }}
    .sub-tab:hover {{
      color: var(--window-fg);
      background: rgba(255, 255, 255, 0.04);
    }}
    .sub-tab.active {{
      background: var(--card-bg-hover);
      color: var(--window-fg);
    }}
    [data-theme="light"] .sub-tab.active {{
      background: #ffffff;
      box-shadow: 0 1px 3px rgba(0, 0, 0, 0.08);
    }}

    /* Single Grounded Stage for the Mouse Setup Views */
    .stage-container {{
      flex: 1;
      display: grid;
      grid-template-columns: 210px 1fr 300px;
      align-items: center;
      padding: 16px 20px;
      gap: 16px;
      min-height: 520px;
      position: relative;
    }}
    .mode-buttons .stage-container,
    .mode-leds .stage-container {{
      grid-template-columns: 210px 1fr 300px;
    }}
    .mode-resolutions .stage-container {{
      grid-template-columns: 0 1fr 340px;
    }}
    .mode-advanced .stage-container {{
      grid-template-columns: 0 1fr 400px;
    }}

    .left-panel {{
      display: flex;
      flex-direction: column;
      gap: 5px;
      z-index: 10;
    }}
    .center-stage {{
      display: flex;
      align-items: center;
      justify-content: center;
      position: relative;
      height: 100%;
    }}
    .right-panel {{
      display: flex;
      flex-direction: column;
      gap: 12px;
      z-index: 10;
    }}

    .panel-header-row {{
      display: flex;
      align-items: center;
      justify-content: space-between;
      margin-bottom: 2px;
    }}
    .panel-title {{
      font-size: 15px;
      font-weight: 700;
      color: var(--window-fg);
    }}

    /* Option Buttons (Mapeo de botones) */
    .option-button {{
      display: flex;
      align-items: center;
      justify-content: space-between;
      background: var(--card-bg);
      border: 1px solid var(--card-border);
      border-radius: var(--radius-small);
      padding: 5px 10px;
      font-size: 12.5px;
      font-weight: 500;
      color: var(--window-fg);
      cursor: pointer;
      transition: all 0.15s ease;
      height: 31px;
    }}
    .option-button:hover {{
      background: var(--card-bg-hover);
      border-color: rgba(53, 132, 228, 0.4);
      transform: translateX(2px);
    }}
    .option-button.highlight {{
      border-color: var(--accent-color);
      background: var(--accent-color);
      color: #ffffff !important;
      font-weight: 600;
      transform: translateX(2px);
    }}
    .option-button.highlight .gear-btn {{
      opacity: 1;
      color: #ffffff !important;
    }}
    .btn-label-text {{
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
      max-width: 170px;
    }}
    .gear-btn {{
      opacity: 0.6;
      display: flex;
      align-items: center;
      justify-content: center;
      transition: opacity 0.15s ease;
      flex-shrink: 0;
    }}
    .option-button:hover .gear-btn {{
      opacity: 1;
      color: var(--accent-color);
    }}

    /* DPI Rows */
    .dpi-list {{
      display: flex;
      flex-direction: column;
      background: var(--card-bg);
      border: 1px solid var(--card-border);
      border-radius: var(--radius-large);
      overflow: hidden;
    }}
    .dpi-row {{
      display: flex;
      align-items: center;
      justify-content: space-between;
      padding: 13px 18px;
      border-bottom: 1px solid var(--row-divider);
      cursor: pointer;
      transition: background 0.15s ease;
    }}
    .dpi-row:last-child {{
      border-bottom: none;
    }}
    .dpi-row:hover {{
      background: var(--card-bg-hover);
    }}
    .dpi-row.active {{
      background: rgba(53, 132, 228, 0.12);
    }}
    .dpi-val {{
      font-size: 15px;
      font-weight: 600;
      display: flex;
      align-items: baseline;
      gap: 6px;
    }}
    .dpi-unit {{
      font-size: 12.5px;
      color: var(--dim-label);
      font-weight: 500;
    }}
    .dpi-badge {{
      font-size: 12px;
      font-weight: 700;
      padding: 3px 8px;
      border-radius: var(--radius-pill);
      background: rgba(255, 255, 255, 0.1);
      color: var(--dim-label);
    }}
    .dpi-badge.active {{
      background: var(--accent-color);
      color: #fff;
    }}

    /* LED Mode Card */
    .led-pill-btn {{
      display: flex;
      align-items: center;
      gap: 10px;
      background: var(--card-bg);
      border: 1px solid var(--card-border);
      padding: 8px 16px;
      border-radius: var(--radius-small);
      font-size: 13px;
      font-weight: 600;
      color: var(--window-fg);
      cursor: pointer;
      transition: all 0.15s ease;
    }}
    .led-pill-btn:hover {{
      background: var(--card-bg-hover);
      border-color: rgba(53, 132, 228, 0.4);
    }}
    .color-swatch-dot {{
      width: 12px;
      height: 12px;
      border-radius: 50%;
      background: #3584e4;
      border: 2px solid rgba(255, 255, 255, 0.25);
    }}

    /* Advanced Rows */
    .adv-row {{
      display: flex;
      align-items: center;
      justify-content: space-between;
      padding: 14px 18px;
      border-bottom: 1px solid var(--row-divider);
      transition: background 0.15s ease, opacity 0.2s ease;
      gap: 16px;
    }}
    .adv-row:last-child {{
      border-bottom: none;
    }}
    .adv-row:hover:not(.disabled) {{
      background: var(--card-bg-hover);
    }}
    .adv-label-col {{
      display: flex;
      flex-direction: column;
      gap: 3px;
    }}
    .adv-title {{
      font-size: 14.5px;
      font-weight: 600;
      color: var(--window-fg);
      white-space: nowrap;
    }}
    .adv-subtitle {{
      font-size: 12.5px;
      color: var(--dim-label);
    }}

    /* Disabled / Unsupported State */
    .adv-row.disabled {{
      opacity: 0.38;
      filter: grayscale(0.9);
      cursor: not-allowed;
      background: rgba(0, 0, 0, 0.08);
    }}
    .adv-row.disabled * {{
      cursor: not-allowed !important;
      pointer-events: none !important;
    }}
    .unsupported-tag {{
      font-size: 11.5px;
      font-weight: 600;
      padding: 2px 8px;
      border-radius: var(--radius-pill);
      background: rgba(255, 255, 255, 0.08);
      color: var(--dim-label);
      white-space: nowrap;
      flex-shrink: 0;
    }}
    [data-theme="light"] .unsupported-tag {{
      background: rgba(0, 0, 0, 0.08);
      color: rgba(0, 0, 0, 0.5);
    }}

    /* Segmented pill selector (125 | 250 | 500 | 1000 Hz) */
    .segmented-control {{
      display: flex;
      background: rgba(0, 0, 0, 0.25);
      border: 1px solid var(--card-border);
      border-radius: var(--radius-small);
      padding: 2px;
      gap: 2px;
    }}
    .seg-btn {{
      padding: 5px 12px;
      border-radius: 6px;
      font-size: 12.5px;
      font-weight: 600;
      color: var(--dim-label);
      border: none;
      background: transparent;
      cursor: pointer;
      transition: all 0.15s ease;
    }}
    .seg-btn:hover {{
      color: var(--window-fg);
    }}
    .seg-btn.active {{
      background: var(--accent-color);
      color: #fff;
    }}

    /* ── SVG Hardware Styling ──────────────────────────────────────────── */
    .mouse-hardware-svg {{
      max-width: 420px;
      height: auto;
      max-height: 460px;
      filter: drop-shadow(0 4px 16px rgba(0, 0, 0, 0.3));
      transition: all 0.2s ease;
    }}

    /* Mode switching for layers on the single mouse SVG */
    .mode-resolutions #Buttons,
    .mode-resolutions #LEDs {{
      display: none !important;
    }}
    .mode-resolutions #ResLeader {{
      display: inline !important;
    }}

    .mode-buttons #LEDs,
    .mode-buttons #ResLeader {{
      display: none !important;
    }}
    .mode-buttons #Buttons {{
      display: inline !important;
    }}

    .mode-leds #Buttons,
    .mode-leds #ResLeader {{
      display: none !important;
    }}
    .mode-leds #LEDs {{
      display: inline !important;
    }}

    .mode-advanced #Buttons,
    .mode-advanced #LEDs,
    .mode-advanced #ResLeader {{
      display: none !important;
    }}

    /* Highlighting button on SVG */
    .svg-btn-highlight {{
      fill: #3584e4 !important;
      fill-opacity: 0.9 !important;
      stroke: #78aeed !important;
      stroke-width: 2px !important;
      transition: all 0.15s ease;
    }}

    /* ── Toast Notification (AdwToast) ─────────────────────────────────── */
    .adw-toast {{
      position: fixed;
      bottom: 28px;
      left: 50%;
      transform: translateX(-50%) translateY(100px);
      background: rgba(36, 36, 36, 0.96);
      backdrop-filter: blur(16px);
      color: #ffffff;
      border: 1px solid rgba(255, 255, 255, 0.15);
      border-radius: var(--radius-pill);
      padding: 10px 22px;
      font-size: 13.5px;
      font-weight: 600;
      display: flex;
      align-items: center;
      gap: 10px;
      box-shadow: 0 10px 32px rgba(0, 0, 0, 0.55);
      z-index: 2000;
      transition: transform 0.28s cubic-bezier(0.16, 1, 0.3, 1), opacity 0.28s ease;
      opacity: 0;
      pointer-events: none;
    }}
    [data-theme="light"] .adw-toast {{
      background: rgba(245, 245, 245, 0.96);
      color: #2e3436;
      border-color: rgba(0, 0, 0, 0.12);
      box-shadow: 0 8px 24px rgba(0, 0, 0, 0.2);
    }}
    .adw-toast.show {{
      transform: translateX(-50%) translateY(0);
      opacity: 1;
    }}

    /* ── Popover Dialogs ───────────────────────────────────────────────── */
    .popover-menu {{
      position: absolute;
      background: var(--dialog-bg);
      border: 1px solid var(--card-border);
      border-radius: var(--radius-medium);
      box-shadow: var(--shadow-popover);
      padding: 6px;
      display: none;
      flex-direction: column;
      z-index: 100;
      min-width: 190px;
      animation: fadeIn 0.15s ease;
    }}
    .popover-menu.open {{
      display: flex;
    }}
    .popover-item {{
      display: flex;
      align-items: center;
      justify-content: space-between;
      padding: 8px 12px;
      border-radius: var(--radius-small);
      font-size: 13px;
      font-weight: 500;
      color: var(--window-fg);
      cursor: pointer;
      transition: background 0.12s ease;
    }}
    .popover-item:hover {{
      background: rgba(255, 255, 255, 0.08);
    }}
    .popover-item.active {{
      font-weight: 700;
      color: var(--accent-color);
    }}
    .popover-divider {{
      height: 1px;
      background: var(--row-divider);
      margin: 4px 0;
    }}

    /* Modal Sheet */
    .modal-overlay {{
      position: absolute;
      top: 0;
      left: 0;
      right: 0;
      bottom: 0;
      background: rgba(0, 0, 0, 0.55);
      backdrop-filter: blur(4px);
      display: none;
      align-items: center;
      justify-content: center;
      z-index: 1000;
      animation: fadeIn 0.15s ease;
    }}
    .modal-overlay.open {{
      display: flex;
    }}
    .adw-dialog {{
      width: 440px;
      background: var(--dialog-bg);
      border-radius: var(--radius-large);
      border: 1px solid var(--card-border);
      box-shadow: 0 20px 48px rgba(0,0,0,0.5);
      overflow: hidden;
      animation: slideUp 0.2s cubic-bezier(0.16, 1, 0.3, 1);
    }}
    @keyframes slideUp {{
      from {{ transform: translateY(20px) scale(0.97); opacity: 0; }}
      to {{ transform: translateY(0) scale(1); opacity: 1; }}
    }}
    .dialog-header {{
      height: 48px;
      padding: 0 16px;
      display: flex;
      align-items: center;
      justify-content: space-between;
      border-bottom: 1px solid var(--row-divider);
    }}
    .dialog-title {{
      font-weight: 700;
      font-size: 14.5px;
    }}
    .dialog-body {{
      padding: 20px;
      display: flex;
      flex-direction: column;
      gap: 16px;
    }}
    .btn-flat {{
      background: none;
      border: none;
      color: var(--dim-label);
      font-size: 13px;
      font-weight: 600;
      cursor: pointer;
      padding: 6px 10px;
      border-radius: var(--radius-small);
    }}
    .btn-flat:hover {{
      background: rgba(255, 255, 255, 0.08);
      color: var(--window-fg);
    }}
    .search-input-wrapper {{
      display: flex;
      align-items: center;
      background: rgba(255, 255, 255, 0.08);
      border: 1px solid var(--card-border);
      border-radius: var(--radius-small);
      padding: 8px 12px;
      gap: 10px;
    }}
    .search-input {{
      background: none;
      border: none;
      color: var(--window-fg);
      font-size: 13.5px;
      width: 100%;
      outline: none;
      font-family: inherit;
    }}
    .game-picker-list {{
      display: flex;
      flex-direction: column;
      border-top: 1px solid var(--row-divider);
      border-bottom: 1px solid var(--row-divider);
      max-height: 180px;
      overflow-y: auto;
    }}
    .picker-item {{
      display: flex;
      align-items: center;
      gap: 12px;
      padding: 10px 14px;
      border-bottom: 1px solid var(--row-divider);
      cursor: pointer;
    }}
    .picker-item:last-child {{
      border-bottom: none;
    }}
    .picker-item:hover {{
      background: rgba(255, 255, 255, 0.06);
    }}
    .picker-item.selected {{
      background: rgba(53, 132, 228, 0.15);
    }}
  </style>
</head>
<body>

  <!-- Top Mockup Info & Quick Switcher -->
  <div class="mockup-toolbar">
    <span class="mockup-tag">Libadwaita</span>
    <span>Demostración con tu mouse <strong>Logitech G600</strong>:</span>
    <button id="toggle-theme">
      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="5"/><line x1="12" y1="1" x2="12" y2="3"/><line x1="12" y1="21" x2="12" y2="23"/><line x1="4.22" y1="4.22" x2="5.64" y2="5.64"/><line x1="18.36" y1="18.36" x2="19.78" y2="19.78"/><line x1="1" y1="12" x2="3" y2="12"/><line x1="21" y1="12" x2="23" y2="12"/><line x1="4.22" y1="19.78" x2="5.64" y2="18.36"/><line x1="18.36" y1="5.64" x2="19.78" y2="4.22"/></svg>
      Oscuro / Claro
    </button>
    <button id="toggle-hw-mode" title="Alternar entre simular tu G600 real (con opciones no soportadas en gris) y un mouse con todo soportado">
      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z"/></svg>
      Modo: <span id="hw-mode-text" style="color:#78aeed;">Tu G600 (En gris)</span>
    </button>
    <button id="btn-quick-autopilot">AutoPilot</button>
    <button id="btn-quick-mouse">Mouse Setup</button>
  </div>

  <!-- Libadwaita Main Window -->
  <div class="adw-window">

    <!-- AdwHeaderBar -->
    <header class="adw-headerbar">
      <!-- Left: Device / Active Profile Selection -->
      <div class="header-left">
        <button class="adw-profile-button" id="profile-select-btn" title="Seleccionar Perfil">
          <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/>
            <circle cx="12" cy="7" r="4"/>
          </svg>
          <span id="current-profile-label">Mobas</span>
          <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="6 9 12 15 18 9"/></svg>
        </button>

        <!-- Profile Popover Menu -->
        <div class="popover-menu" id="profile-popover" style="top:48px; left:14px;">
          <div class="popover-item active" data-prof="Mobas">
            <span>Mobas</span>
            <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3"><polyline points="20 6 9 17 4 12"/></svg>
          </div>
          <div class="popover-item" data-prof="Default">
            <span>Default</span>
          </div>
          <div class="popover-item" data-prof="World of Warcraft">
            <span>World of Warcraft</span>
          </div>
          <div class="popover-item" data-prof="Shooter">
            <span>Shooter</span>
          </div>
          <div class="popover-divider"></div>
          <div class="popover-item" style="color:var(--accent-color); font-weight:600;">
            <span>+ Añadir perfil</span>
          </div>
        </div>
      </div>

      <!-- Center: AdwViewSwitcher (Top-Level Tabs) -->
      <nav class="adw-view-switcher">
        <div class="adw-view-tab active" data-tab="autopilot" id="tab-autopilot">
          <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/>
          </svg>
          AutoPilot
        </div>
        <div class="adw-view-tab" data-tab="mousesetup" id="tab-mousesetup">
          <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <rect x="5" y="2" width="14" height="20" rx="7"/>
            <line x1="12" y1="6" x2="12" y2="10"/>
          </svg>
          Mouse setup
        </div>
      </nav>

      <!-- Right: Primary Actions & Window Controls -->
      <div class="header-right">
        <!-- Apply Button (Only in Mouse Setup) -->
        <button class="btn-apply" id="btn-apply">Aplicar</button>

        <button class="icon-button" title="Menú Principal">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="1"/><circle cx="12" cy="5" r="1"/><circle cx="12" cy="19" r="1"/></svg>
        </button>
        <div class="adw-window-controls">
          <button class="window-button" title="Minimizar">
            <svg width="12" height="12" viewBox="0 0 16 16" fill="none">
              <path d="M3 8.5h10" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/>
            </svg>
          </button>
          <button class="window-button" title="Maximizar">
            <svg width="12" height="12" viewBox="0 0 16 16" fill="none">
              <rect x="3.5" y="3.5" width="9" height="9" rx="1.5" stroke="currentColor" stroke-width="1.5" fill="none"/>
            </svg>
          </button>
          <button class="window-button close" title="Cerrar">
            <svg width="12" height="12" viewBox="0 0 16 16" fill="none">
              <path d="M4.5 4.5l7 7M11.5 4.5l-7 7" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/>
            </svg>
          </button>
        </div>
      </div>
    </header>

    <!-- Main Content Area -->
    <main class="adw-content">

      <!-- ══════════════════════════════════════════════════════════════════
           PAGE 1: AUTOPILOT
           ══════════════════════════════════════════════════════════════════ -->
      <div class="main-page active" id="page-autopilot">
        <div class="adw-clamp">

          <!-- 1. Hero Status Card (Automatic Profile Switching) -->
          <section class="adw-hero-card">
            <div class="hero-info">
              <div class="status-pulse-container">
                <div class="status-ring"></div>
                <div class="status-dot"></div>
              </div>
              <div>
                <div class="hero-title">Cambio Automático de Perfiles</div>
                <div class="hero-subtitle">
                  <span class="hero-badge">Activo</span>
                  <span>Último cambio: <strong style="color:var(--window-fg);">Mobas</strong></span>
                </div>
              </div>
            </div>
            <div class="adw-switch active" id="master-switch" title="Activar/Desactivar AutoPilot">
              <div class="switch-slider"></div>
            </div>
          </section>

          <!-- 2. Your Games Section -->
          <section>
            <div class="group-header">
              <div>
                <div class="group-title">Tus juegos</div>
                <div class="group-description">Cuando un juego se ejecuta o toma foco, su perfil se carga al ratón automáticamente.</div>
              </div>
              <div style="display:flex; align-items:center; gap:8px;">
                <button class="btn-suggested" id="add-game-btn">
                  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg>
                  Añadir juego
                </button>
              </div>
            </div>

            <!-- Boxed List of Game Rules -->
            <div class="adw-boxed-list" id="games-list">
              
              <!-- World of Warcraft (Faugus / Battle.net) -->
              <div class="adw-row">
                <div class="game-icon-squircle" style="background: radial-gradient(circle, #2b4970 0%, #0d1726 100%);">
                  <svg viewBox="0 0 100 100" width="28" height="28" fill="#ffb400">
                    <path d="M50 5 L65 35 L95 40 L70 65 L78 95 L50 78 L22 95 L30 65 L5 40 L35 35 Z" opacity="0.9"/>
                    <circle cx="50" cy="50" r="22" fill="#12253d" stroke="#ffb400" stroke-width="4"/>
                    <text x="50" y="58" font-size="22" font-weight="900" text-anchor="middle" fill="#ffb400" font-family="'Cinzel', serif">W</text>
                  </svg>
                </div>
                <div class="game-details">
                  <div class="game-name">
                    World of Warcraft
                    <span class="faugus-chip">Faugus</span>
                  </div>
                  <div class="game-meta">wow.exe • Battle.net</div>
                </div>
                <div class="adw-dropdown">
                  <span>Mobas</span>
                  <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="6 9 12 15 18 9"/></svg>
                </div>
                <button class="icon-button delete" title="Eliminar regla">
                  <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="var(--destructive-color)" stroke-width="2"><polyline points="3 6 5 6 21 6"/><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/></svg>
                </button>
              </div>

              <!-- Heroes of the Storm (Faugus / Battle.net) -->
              <div class="adw-row">
                <div class="game-icon-squircle" style="background: radial-gradient(circle, #5b1e9c 0%, #17042a 100%);">
                  <svg viewBox="0 0 100 100" width="28" height="28" fill="#a46cfc">
                    <polygon points="50,10 90,50 50,90 10,50" stroke="#cbb2ff" stroke-width="4" fill="none"/>
                    <circle cx="50" cy="50" r="16" fill="#a46cfc"/>
                  </svg>
                </div>
                <div class="game-details">
                  <div class="game-name">
                    Heroes of the Storm
                    <span class="faugus-chip">Faugus</span>
                  </div>
                  <div class="game-meta">heroesofthestorm_x64.exe</div>
                </div>
                <div class="adw-dropdown">
                  <span>Mobas</span>
                  <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="6 9 12 15 18 9"/></svg>
                </div>
                <button class="icon-button delete" title="Eliminar regla">
                  <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="var(--destructive-color)" stroke-width="2"><polyline points="3 6 5 6 21 6"/><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/></svg>
                </button>
              </div>

              <!-- Battle.net Launcher -->
              <div class="adw-row">
                <div class="game-icon-squircle" style="background: #0066cc;">
                  <span style="color:white;font-weight:900;font-size:20px;">B</span>
                </div>
                <div class="game-details">
                  <div class="game-name">
                    Battle.net Launcher
                    <span class="faugus-chip">Faugus</span>
                  </div>
                  <div class="game-meta">battle.net.exe</div>
                </div>
                <div class="adw-dropdown">
                  <span>Default</span>
                  <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="6 9 12 15 18 9"/></svg>
                </div>
                <button class="icon-button delete" title="Eliminar regla">
                  <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="var(--destructive-color)" stroke-width="2"><polyline points="3 6 5 6 21 6"/><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/></svg>
                </button>
              </div>

            </div>
          </section>

          <!-- 3. Global AutoPilot Settings -->
          <section>
            <div class="group-header">
              <div class="group-title">Ajustes del sistema</div>
            </div>
            <div class="adw-boxed-list">
              <div class="adw-row">
                <div class="game-details">
                  <div class="game-name">Ejecutar al iniciar sesión</div>
                  <div class="game-meta">Inicia el demonio de fondo en segundo plano silenciosamente</div>
                </div>
                <div class="adw-switch active">
                  <div class="switch-slider"></div>
                </div>
              </div>
              <div class="adw-row">
                <div class="game-details">
                  <div class="game-name">Notificaciones de cambio</div>
                  <div class="game-meta">Muestra una burbuja del sistema al conmutar perfil</div>
                </div>
                <div class="adw-switch active">
                  <div class="switch-slider"></div>
                </div>
              </div>
            </div>
          </section>

        </div>
      </div>

      <!-- ══════════════════════════════════════════════════════════════════
           PAGE 2: MOUSE SETUP (PERSPECTIVA DE HARDWARE)
           ══════════════════════════════════════════════════════════════════ -->
      <div class="main-page" id="page-mousesetup">
        <div class="mouse-setup-container mode-resolutions" id="mouse-setup-container">
          
          <!-- Sub-Stack Switcher (Resoluciones | Botones | LEDs | Advanced) -->
          <div class="sub-switcher-bar">
            <div class="sub-switcher">
              <div class="sub-tab active" data-sub="resolutions" id="subtab-resolutions">Resoluciones</div>
              <div class="sub-tab" data-sub="buttons" id="subtab-buttons">Botones</div>
              <div class="sub-tab" data-sub="leds" id="subtab-leds">LEDs</div>
              <div class="sub-tab" data-sub="advanced" id="subtab-advanced">Advanced</div>
            </div>
          </div>

          <!-- Single Centered Stage: Mouse stays rock-solid while controls transition -->
          <div class="stage-container">
            
            <!-- LEFT PANEL: Dynamic according to active sub-tab -->
            <div class="left-panel" id="stage-left-panel">
              
              <!-- Left Column: Botones Tab (12 side buttons G9 - G20) -->
              <div id="left-controls-buttons" style="display:none; flex-direction:column; gap:5px;">
                <div class="option-button" data-btn="button8" data-default="Semicolon ;" title="G9">
                  <span class="btn-label-text">Semicolon ;</span>
                  <span class="gear-btn">{gear_icon}</span>
                </div>
                <div class="option-button" data-btn="button9" data-default="E" title="G10">
                  <span class="btn-label-text">E</span>
                  <span class="gear-btn">{gear_icon}</span>
                </div>
                <div class="option-button" data-btn="button10" data-default="V" title="G11">
                  <span class="btn-label-text">V</span>
                  <span class="gear-btn">{gear_icon}</span>
                </div>
                <div class="option-button" data-btn="button11" data-default="R" title="G12">
                  <span class="btn-label-text">R</span>
                  <span class="gear-btn">{gear_icon}</span>
                </div>
                <div class="option-button" data-btn="button12" data-default="5" title="G13">
                  <span class="btn-label-text">5</span>
                  <span class="gear-btn">{gear_icon}</span>
                </div>
                <div class="option-button" data-btn="button13" data-default="6" title="G14">
                  <span class="btn-label-text">6</span>
                  <span class="gear-btn">{gear_icon}</span>
                </div>
                <div class="option-button" data-btn="button14" data-default="F" title="G15">
                  <span class="btn-label-text">F</span>
                  <span class="gear-btn">{gear_icon}</span>
                </div>
                <div class="option-button" data-btn="button15" data-default="8" title="G16">
                  <span class="btn-label-text">8</span>
                  <span class="gear-btn">{gear_icon}</span>
                </div>
                <div class="option-button" data-btn="button16" data-default="9" title="G17">
                  <span class="btn-label-text">9</span>
                  <span class="gear-btn">{gear_icon}</span>
                </div>
                <div class="option-button" data-btn="button17" data-default="0" title="G18">
                  <span class="btn-label-text">0</span>
                  <span class="gear-btn">{gear_icon}</span>
                </div>
                <div class="option-button" data-btn="button18" data-default="Minus –" title="G19">
                  <span class="btn-label-text">Minus –</span>
                  <span class="gear-btn">{gear_icon}</span>
                </div>
                <div class="option-button" data-btn="button19" data-default="Equal =" title="G20">
                  <span class="btn-label-text">Equal =</span>
                  <span class="gear-btn">{gear_icon}</span>
                </div>
              </div>

              <!-- Left Column: LEDs Tab (Single mode button) -->
              <div id="left-controls-leds" style="display:none; align-items:center; justify-content:center; height:100%;">
                <div class="led-pill-btn" id="led-mode-btn" title="Modificar modo de iluminación">
                  <div class="color-swatch-dot" id="led-dot-color"></div>
                  <span id="led-mode-label">Sólido</span>
                  <span class="gear-btn">{gear_icon}</span>
                </div>
              </div>

            </div>

            <!-- CENTER STAGE: Single Grounded Vector Graphic of Logitech G600 -->
            <div class="center-stage">
              {svg_g600_enhanced}
            </div>

            <!-- RIGHT PANEL: Dynamic according to active sub-tab -->
            <div class="right-panel" id="stage-right-panel">

              <!-- 1. Resolutions Panel -->
              <div id="right-controls-resolutions" style="display:flex; flex-direction:column; gap:14px;">
                <div class="panel-header-row">
                  <div class="panel-title">Resoluciones</div>
                  <button class="btn-reset" id="reset-dpi-btn" title="Restablecer los 4 niveles de DPI a valores de fábrica">
                    {undo_icon}
                    Restablecer
                  </button>
                </div>

                <div class="dpi-list" id="dpi-list-container">
                  <div id="dpi-rows-wrapper">
                    <div class="dpi-row active" data-dpi="1200">
                      <div class="dpi-val">1200 <span class="dpi-unit">DPI</span></div>
                      <span class="dpi-badge active">active</span>
                    </div>
                    <div class="dpi-row" data-dpi="1200">
                      <div class="dpi-val">1200 <span class="dpi-unit">DPI</span></div>
                      <span class="dpi-badge">2</span>
                    </div>
                    <div class="dpi-row" data-dpi="2000">
                      <div class="dpi-val">2000 <span class="dpi-unit">DPI</span></div>
                      <span class="dpi-badge">3</span>
                    </div>
                    <div class="dpi-row" data-dpi="3200">
                      <div class="dpi-val">3200 <span class="dpi-unit">DPI</span></div>
                      <span class="dpi-badge">4</span>
                    </div>
                  </div>
                  <div style="padding:14px 18px; border-top:1px solid var(--row-divider); display:flex; flex-direction:column; gap:10px;">
                    <div style="font-size:12.5px; color:var(--dim-label); font-weight:600;">Sensibilidad DPI activa</div>
                    <input type="range" min="200" max="8200" step="50" value="1200" id="dpi-slider" style="width:100%; accent-color:var(--accent-color); cursor:pointer;">
                    <div style="display:flex; justify-content:space-between; font-size:12px; color:var(--dim-label);">
                      <span>200 DPI</span>
                      <span id="dpi-slider-val" style="color:var(--accent-color); font-weight:700;">1200 DPI</span>
                      <span>8200 DPI</span>
                    </div>
                  </div>
                </div>
              </div>

              <!-- 2. Buttons Panel (Right side main mouse buttons) -->
              <div id="right-controls-buttons" style="display:none; flex-direction:column; gap:5px;">
                <div class="panel-header-row" style="margin-bottom:4px;">
                  <span style="font-size:12.5px; color:var(--dim-label); font-weight:600;">Botones principales</span>
                  <button class="btn-reset" id="reset-buttons-btn" title="Restablecer asignación de botones de fábrica">
                    {undo_icon}
                    Restablecer
                  </button>
                </div>
                <div class="option-button" data-btn="button0" data-default="Pulsación del botón primario" title="Botón Izquierdo">
                  <span class="btn-label-text">Pulsación del botón primario</span>
                  <span class="gear-btn">{gear_icon}</span>
                </div>
                <div class="option-button" data-btn="button1" data-default="Pulsación del botón secundario" title="Botón Derecho">
                  <span class="btn-label-text">Pulsación del botón secundario</span>
                  <span class="gear-btn">{gear_icon}</span>
                </div>
                <div class="option-button" data-btn="button2" data-default="Pulsación del botón central" title="Botón Central">
                  <span class="btn-label-text">Pulsación del botón central</span>
                  <span class="gear-btn">{gear_icon}</span>
                </div>
                <div class="option-button" data-btn="button3" data-default="Adelante" title="Inclinación Rueda">
                  <span class="btn-label-text">Adelante</span>
                  <span class="gear-btn">{gear_icon}</span>
                </div>
                <div class="option-button" data-btn="button4" data-default="Atrás" title="Inclinación Rueda">
                  <span class="btn-label-text">Atrás</span>
                  <span class="gear-btn">{gear_icon}</span>
                </div>
                <div class="option-button" data-btn="button5" data-default="Esc" title="G-Shift">
                  <span class="btn-label-text">Esc</span>
                  <span class="gear-btn">{gear_icon}</span>
                </div>
                <div class="option-button" data-btn="button7" data-default="Ciclo de perfil siguiente" title="Botón Perfil">
                  <span class="btn-label-text">Ciclo de perfil siguiente</span>
                  <span class="gear-btn">{gear_icon}</span>
                </div>
                <div class="option-button" data-btn="button6" data-default="Ciclo de resolución siguiente" title="Botón DPI">
                  <span class="btn-label-text">Ciclo de resolución siguiente</span>
                  <span class="gear-btn">{gear_icon}</span>
                </div>
              </div>

              <!-- 3. LEDs Panel (Right side: info + reset) -->
              <div id="right-controls-leds" style="display:none; flex-direction:column; gap:12px;">
                <div class="panel-header-row">
                  <div class="panel-title">Iluminación</div>
                  <button class="btn-reset" id="reset-led-btn" title="Restablecer iluminación a modo predeterminado">
                    {undo_icon}
                    Restablecer
                  </button>
                </div>
                <div style="font-size:13.5px; color:var(--dim-label); line-height:1.6; padding:8px 4px;">
                  Configura el color y patrón del teclado lateral de tu Logitech G600. Haz clic en el botón de la izquierda para seleccionar entre color sólido, ciclo de color o respiración.
                </div>
              </div>

              <!-- 4. Advanced Panel (Polling rate, debounce, angle snapping) -->
              <div id="right-controls-advanced" style="display:none; flex-direction:column; gap:12px;">
                <div class="panel-header-row">
                  <div class="panel-title">Ajustes del sensor</div>
                  <button class="btn-reset" id="reset-adv-btn" title="Restablecer tasa de sondeo a 1000 Hz">
                    {undo_icon}
                    Restablecer
                  </button>
                </div>

                <div class="adw-boxed-list" id="adv-boxed-list">
                  <div class="adv-row" id="adv-poll-row" style="flex-direction:column; align-items:stretch; gap:10px;">
                    <div style="display:flex; justify-content:space-between; align-items:center;">
                      <div class="adv-label-col">
                        <div class="adv-title">Velocidad de respuesta</div>
                        <div class="adv-subtitle">Tasa de sondeo USB del sensor</div>
                      </div>
                      <span style="font-size:12.5px; color:var(--dim-label); font-weight:600;">Hz</span>
                    </div>
                    <div class="segmented-control" id="poll-rate-control" style="width:100%;">
                      <button class="seg-btn" data-rate="125" style="flex:1;">125</button>
                      <button class="seg-btn" data-rate="250" style="flex:1;">250</button>
                      <button class="seg-btn" data-rate="500" style="flex:1;">500</button>
                      <button class="seg-btn active" data-rate="1000" style="flex:1;">1000</button>
                    </div>
                  </div>

                  <!-- Debounce Time (GRAYED OUT / UNSUPPORTED ON G600) -->
                  <div class="adv-row disabled" id="adv-debounce-row" title="Tu mouse Logitech G600 no admite modificar el tiempo de debounce por hardware">
                    <div class="adv-label-col" style="flex:1;">
                      <div style="display:flex; align-items:center; gap:8px;">
                        <span class="adv-title">Debounce time</span>
                        <span class="unsupported-tag" id="tag-debounce">No disponible</span>
                      </div>
                      <div class="adv-subtitle" id="sub-debounce">No admitido por el hardware de tu Logitech G600</div>
                    </div>
                    <div style="display:flex; align-items:center; gap:8px; flex-shrink:0;">
                      <div class="adw-dropdown" style="padding:6px 12px; min-width:80px; justify-content:space-between; opacity:0.6;">
                        <span id="debounce-val">–</span>
                        <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="6 9 12 15 18 9"/></svg>
                      </div>
                      <span style="font-size:12.5px; color:var(--dim-label); font-weight:600;">ms</span>
                    </div>
                  </div>

                  <!-- Angle Snapping (GRAYED OUT / UNSUPPORTED ON G600) -->
                  <div class="adv-row disabled" id="adv-angle-row" title="Tu mouse Logitech G600 no dispone de sensor con corrección predictiva de ángulo">
                    <div class="adv-label-col" style="flex:1;">
                      <div style="display:flex; align-items:center; gap:8px;">
                        <span class="adv-title">Angle snapping</span>
                        <span class="unsupported-tag" id="tag-angle">No disponible</span>
                      </div>
                      <div class="adv-subtitle" id="sub-angle">El sensor óptico no admite corrección angular predictiva</div>
                    </div>
                    <div class="adw-switch" id="switch-angle-snap" style="opacity:0.4; flex-shrink:0;">
                      <div class="switch-slider"></div>
                    </div>
                  </div>
                </div>
              </div>

            </div>

          </div>

        </div>
      </div>

    </main>
  </div>

  <!-- Libadwaita Floating Toast Notification (AdwToastOverlay) -->
  <div class="adw-toast" id="adw-toast">
    <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="var(--success-color)" stroke-width="2.5"><polyline points="20 6 9 17 4 12"/></svg>
    <span id="toast-text">Ajustes restablecidos correctamente</span>
  </div>

  <!-- Modal Dialog Sheet Mockup (AdwDialog) -->
  <div class="modal-overlay" id="modal-overlay">
    <div class="adw-dialog">
      <div class="dialog-header">
        <button class="btn-flat" id="modal-cancel">Cancelar</button>
        <div class="dialog-title">Añadir regla de juego</div>
        <button class="btn-suggested" id="modal-add">Añadir</button>
      </div>
      <div class="dialog-body">
        
        <div class="search-input-wrapper">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg>
          <input type="text" class="search-input" placeholder="Buscar juego instalado o .exe…" value="Battle.net">
        </div>

        <div class="group-title" style="margin-top:4px;">Juegos detectados (Faugus / Steam / Flatpak)</div>
        <div class="game-picker-list">
          <div class="picker-item selected">
            <div class="game-icon-squircle" style="width:28px;height:28px;border-radius:6px;background:#0066cc;">
              <span style="font-weight:900;font-size:12px;color:white;">B</span>
            </div>
            <div style="flex:1;">
              <div style="font-size:13.5px;font-weight:600;">Battle.net</div>
              <div style="font-size:12.5px;color:var(--dim-label);">Faugus Launcher • battle.net.exe</div>
            </div>
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="var(--accent-color)" stroke-width="3"><polyline points="20 6 9 17 4 12"/></svg>
          </div>
          <div class="picker-item">
            <div class="game-icon-squircle" style="width:28px;height:28px;border-radius:6px;background:#ffb400;">
              <span style="font-weight:900;font-size:12px;color:#12253d;">W</span>
            </div>
            <div style="flex:1;">
              <div style="font-size:13.5px;font-weight:600;">World of Warcraft</div>
              <div style="font-size:12.5px;color:var(--dim-label);">Faugus Launcher • wow.exe</div>
            </div>
          </div>
        </div>

        <div style="display:flex;flex-direction:column;gap:6px;margin-top:6px;">
          <div class="group-title">Perfil de ratón a cargar</div>
          <div class="adw-dropdown" style="justify-content:space-between;padding:10px 14px;">
            <span>Mobas</span>
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="6 9 12 15 18 9"/></svg>
          </div>
        </div>

      </div>
    </div>
  </div>

  <script>
    // ── Toast Notification Helper ───────────────────────────────────────
    const toast = document.getElementById('adw-toast');
    const toastText = document.getElementById('toast-text');
    let toastTimeout = null;

    function showToast(msg) {{
      toastText.textContent = msg;
      toast.classList.add('show');
      if (toastTimeout) clearTimeout(toastTimeout);
      toastTimeout = setTimeout(() => {{
        toast.classList.remove('show');
      }}, 2600);
    }}

    // ── Theme toggle ────────────────────────────────────────────────────
    const toggleThemeBtn = document.getElementById('toggle-theme');
    toggleThemeBtn.addEventListener('click', () => {{
      const current = document.documentElement.getAttribute('data-theme');
      document.documentElement.setAttribute('data-theme', current === 'light' ? 'dark' : 'light');
    }});

    // ── Hardware Capabilities Mode Toggle (G600 limited vs Full mouse) ──
    const toggleHwBtn = document.getElementById('toggle-hw-mode');
    const hwModeText = document.getElementById('hw-mode-text');
    const rowDebounce = document.getElementById('adv-debounce-row');
    const rowAngle = document.getElementById('adv-angle-row');
    const tagDebounce = document.getElementById('tag-debounce');
    const tagAngle = document.getElementById('tag-angle');
    const subDebounce = document.getElementById('sub-debounce');
    const subAngle = document.getElementById('sub-angle');
    const debounceVal = document.getElementById('debounce-val');
    const switchAngle = document.getElementById('switch-angle-snap');

    let isG600Mode = true;

    toggleHwBtn.addEventListener('click', () => {{
      isG600Mode = !isG600Mode;
      if (isG600Mode) {{
        hwModeText.textContent = 'Tu G600 (En gris)';
        hwModeText.style.color = '#78aeed';
        rowDebounce.classList.add('disabled');
        rowAngle.classList.add('disabled');
        tagDebounce.textContent = 'No disponible';
        tagAngle.textContent = 'No disponible';
        subDebounce.textContent = 'No admitido por el hardware de tu Logitech G600';
        subAngle.textContent = 'El sensor óptico no admite corrección angular predictiva';
        debounceVal.textContent = '–';
        switchAngle.style.opacity = '0.4';
        showToast('Modo: Logitech G600 (Funciones no soportadas en gris)');
      }} else {{
        hwModeText.textContent = 'Mouse Full (Activo)';
        hwModeText.style.color = '#33d17a';
        rowDebounce.classList.remove('disabled');
        rowAngle.classList.remove('disabled');
        tagDebounce.textContent = 'Soportado';
        tagAngle.textContent = 'Soportado';
        subDebounce.textContent = 'Filtro anti-rebote para switches mecánicos';
        subAngle.textContent = 'Corrección predictiva de líneas rectas';
        debounceVal.textContent = '16 ms';
        switchAngle.style.opacity = '1';
        showToast('Modo: Ratón con todas las funciones soportadas');
      }}
    }});

    // ── Top-Level View Switcher (AutoPilot <-> Mouse Setup) ──────────────
    const tabAutoPilot = document.getElementById('tab-autopilot');
    const tabMouseSetup = document.getElementById('tab-mousesetup');
    const pageAutoPilot = document.getElementById('page-autopilot');
    const pageMouseSetup = document.getElementById('page-mousesetup');
    const btnApply = document.getElementById('btn-apply');

    function showAutoPilot() {{
      tabAutoPilot.classList.add('active');
      tabMouseSetup.classList.remove('active');
      pageAutoPilot.classList.add('active');
      pageMouseSetup.classList.remove('active');
      btnApply.style.display = 'none';
    }}

    function showMouseSetup() {{
      tabMouseSetup.classList.add('active');
      tabAutoPilot.classList.remove('active');
      pageMouseSetup.classList.add('active');
      pageAutoPilot.classList.remove('active');
      btnApply.style.display = 'block';
    }}

    tabAutoPilot.addEventListener('click', showAutoPilot);
    tabMouseSetup.addEventListener('click', showMouseSetup);

    document.getElementById('btn-quick-autopilot').addEventListener('click', showAutoPilot);
    document.getElementById('btn-quick-mouse').addEventListener('click', showMouseSetup);

    // ── Sub-Switcher Tabs (Resoluciones, Botones, LEDs, Advanced) ────────
    const subTabs = document.querySelectorAll('.sub-tab');
    const mouseSetupContainer = document.getElementById('mouse-setup-container');
    const leftButtons = document.getElementById('left-controls-buttons');
    const leftLeds = document.getElementById('left-controls-leds');
    const rightResolutions = document.getElementById('right-controls-resolutions');
    const rightButtons = document.getElementById('right-controls-buttons');
    const rightLeds = document.getElementById('right-controls-leds');
    const rightAdvanced = document.getElementById('right-controls-advanced');

    function switchSubTab(subName) {{
      subTabs.forEach(t => t.classList.remove('active'));
      const activeTab = document.querySelector(`.sub-tab[data-sub="${{subName}}"]`);
      if (activeTab) activeTab.classList.add('active');

      mouseSetupContainer.className = 'mouse-setup-container mode-' + subName;

      // Toggle panels smoothly
      leftButtons.style.display = (subName === 'buttons') ? 'flex' : 'none';
      leftLeds.style.display = (subName === 'leds') ? 'flex' : 'none';

      rightResolutions.style.display = (subName === 'resolutions') ? 'flex' : 'none';
      rightButtons.style.display = (subName === 'buttons') ? 'flex' : 'none';
      rightLeds.style.display = (subName === 'leds') ? 'flex' : 'none';
      rightAdvanced.style.display = (subName === 'advanced') ? 'flex' : 'none';
    }}

    subTabs.forEach(tab => {{
      tab.addEventListener('click', () => {{
        const sub = tab.getAttribute('data-sub');
        switchSubTab(sub);
        window.location.hash = sub;
      }});
    }});

    function handleHash() {{
      const hash = (window.location.hash || '').toLowerCase().replace('#', '');
      if (['resolutions', 'buttons', 'leds', 'advanced'].includes(hash)) {{
        showMouseSetup();
        switchSubTab(hash);
      }} else if (hash === 'mousesetup') {{
        showMouseSetup();
      }} else if (hash === 'autopilot') {{
        showAutoPilot();
      }}
    }}
    window.addEventListener('hashchange', handleHash);
    handleHash();

    // ── Button Remapping & Hover Effects on Mouse Graphic ───────────────
    document.querySelectorAll('.option-button').forEach(btn => {{
      const btnId = btn.getAttribute('data-btn');
      
      btn.addEventListener('mouseenter', () => {{
        btn.classList.add('highlight');
        const targetElem = document.getElementById(btnId);
        if (targetElem) targetElem.classList.add('svg-btn-highlight');
        const leaderLine = document.querySelector('#' + btnId + '-path path');
        if (leaderLine) {{
          leaderLine.dataset.origStroke = leaderLine.getAttribute('stroke') || '#888a85';
          leaderLine.style.stroke = '#3584e4';
          leaderLine.style.strokeWidth = '2px';
        }}
      }});

      btn.addEventListener('mouseleave', () => {{
        btn.classList.remove('highlight');
        const targetElem = document.getElementById(btnId);
        if (targetElem) targetElem.classList.remove('svg-btn-highlight');
        const leaderLine = document.querySelector('#' + btnId + '-path path');
        if (leaderLine) {{
          leaderLine.style.stroke = leaderLine.dataset.origStroke || '#888a85';
          leaderLine.style.strokeWidth = '1px';
        }}
      }});

      btn.addEventListener('click', () => {{
        const text = btn.querySelector('.btn-label-text');
        const newKey = prompt('Asignar nueva tecla o acción para este botón:', text.textContent.trim());
        if (newKey && newKey.trim()) {{
          text.textContent = newKey.trim();
          btnApply.classList.add('active');
          showToast(`Botón asignado a: ${{newKey.trim()}}`);
        }}
      }});
    }});

    // ── Resolution Presets Click ────────────────────────────────────────
    function setupDpiRows() {{
      document.querySelectorAll('.dpi-row').forEach(row => {{
        row.addEventListener('click', () => {{
          document.querySelectorAll('.dpi-row').forEach((r, i) => {{
            r.classList.remove('active');
            const badge = r.querySelector('.dpi-badge');
            badge.textContent = String(i + 1);
            badge.classList.remove('active');
          }});
          row.classList.add('active');
          const badge = row.querySelector('.dpi-badge');
          badge.textContent = 'active';
          badge.classList.add('active');

          const dpi = row.getAttribute('data-dpi');
          document.getElementById('dpi-slider').value = dpi;
          document.getElementById('dpi-slider-val').textContent = dpi + ' DPI';
          btnApply.classList.add('active');
        }});
      }});
    }}
    setupDpiRows();

    // DPI Slider
    const dpiSlider = document.getElementById('dpi-slider');
    const dpiSliderVal = document.getElementById('dpi-slider-val');
    dpiSlider.addEventListener('input', (e) => {{
      dpiSliderVal.textContent = e.target.value + ' DPI';
      const activeRow = document.querySelector('.dpi-row.active .dpi-val');
      if (activeRow) activeRow.innerHTML = `${{e.target.value}} <span class="dpi-unit">DPI</span>`;
      const activeRowEl = document.querySelector('.dpi-row.active');
      if (activeRowEl) activeRowEl.setAttribute('data-dpi', e.target.value);
      btnApply.classList.add('active');
    }});

    // ── RESET BUTTONS IN EACH TAB ───────────────────────────────────────
    
    // 1. Reset Resoluciones
    document.getElementById('reset-dpi-btn').addEventListener('click', () => {{
      const wrapper = document.getElementById('dpi-rows-wrapper');
      wrapper.innerHTML = `
        <div class="dpi-row active" data-dpi="1200">
          <div class="dpi-val">1200 <span class="dpi-unit">DPI</span></div>
          <span class="dpi-badge active">active</span>
        </div>
        <div class="dpi-row" data-dpi="1200">
          <div class="dpi-val">1200 <span class="dpi-unit">DPI</span></div>
          <span class="dpi-badge">2</span>
        </div>
        <div class="dpi-row" data-dpi="2000">
          <div class="dpi-val">2000 <span class="dpi-unit">DPI</span></div>
          <span class="dpi-badge">3</span>
        </div>
        <div class="dpi-row" data-dpi="3200">
          <div class="dpi-val">3200 <span class="dpi-unit">DPI</span></div>
          <span class="dpi-badge">4</span>
        </div>
      `;
      setupDpiRows();
      dpiSlider.value = 1200;
      dpiSliderVal.textContent = '1200 DPI';
      btnApply.classList.add('active');
      showToast('Resoluciones restablecidas a valores de fábrica');
    }});

    // 2. Reset Botones
    document.getElementById('reset-buttons-btn').addEventListener('click', () => {{
      document.querySelectorAll('.option-button').forEach(btn => {{
        const def = btn.getAttribute('data-default');
        if (def) {{
          btn.querySelector('.btn-label-text').textContent = def;
        }}
      }});
      btnApply.classList.add('active');
      showToast('Mapeo de botones restablecido a valores predeterminados');
    }});

    // 3. Reset LEDs
    document.getElementById('reset-led-btn').addEventListener('click', () => {{
      document.getElementById('led-mode-label').textContent = 'Sólido';
      document.getElementById('led-dot-color').style.background = '#3584e4';
      btnApply.classList.add('active');
      showToast('Iluminación restablecida a modo Sólido predeterminado');
    }});

    // 4. Reset Advanced
    document.getElementById('reset-adv-btn').addEventListener('click', () => {{
      document.querySelectorAll('#poll-rate-control .seg-btn').forEach(b => b.classList.remove('active'));
      const b1000 = document.querySelector('#poll-rate-control .seg-btn[data-rate="1000"]');
      if (b1000) b1000.classList.add('active');
      btnApply.classList.add('active');
      showToast('Ajustes del sensor restablecidos a 1000 Hz');
    }});

    // ── Polling Rate Buttons ────────────────────────────────────────────
    document.querySelectorAll('#poll-rate-control .seg-btn').forEach(btn => {{
      btn.addEventListener('click', () => {{
        document.querySelectorAll('#poll-rate-control .seg-btn').forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        btnApply.classList.add('active');
        showToast(`Tasa de sondeo fijada en ${{btn.getAttribute('data-rate')}} Hz`);
      }});
    }});

    // ── Switches ────────────────────────────────────────────────────────
    document.querySelectorAll('.adw-switch').forEach(sw => {{
      sw.addEventListener('click', () => {{
        if (sw.closest('.disabled')) return;
        sw.classList.toggle('active');
        if (sw.id === 'master-switch') {{
          const badge = document.querySelector('.hero-badge');
          const dot = document.querySelector('.status-dot');
          const ring = document.querySelector('.status-ring');
          if (sw.classList.contains('active')) {{
            badge.textContent = 'Activo';
            badge.style.background = 'var(--success-bg)';
            badge.style.color = 'var(--success-color)';
            dot.style.background = 'var(--success-color)';
            ring.style.display = 'block';
            showToast('AutoPilot activado');
          }} else {{
            badge.textContent = 'Pausado';
            badge.style.background = 'rgba(255,255,255,0.1)';
            badge.style.color = 'var(--dim-label)';
            dot.style.background = 'var(--dim-label)';
            ring.style.display = 'none';
            showToast('AutoPilot pausado');
          }}
        }} else {{
          btnApply.classList.add('active');
        }}
      }});
    }});

    // ── Profile Popover ─────────────────────────────────────────────────
    const profileBtn = document.getElementById('profile-select-btn');
    const profilePopover = document.getElementById('profile-popover');
    const profileLabel = document.getElementById('current-profile-label');

    profileBtn.addEventListener('click', (e) => {{
      e.stopPropagation();
      profilePopover.classList.toggle('open');
    }});

    document.querySelectorAll('#profile-popover .popover-item[data-prof]').forEach(item => {{
      item.addEventListener('click', () => {{
        const profName = item.getAttribute('data-prof');
        profileLabel.textContent = profName;
        document.querySelectorAll('#profile-popover .popover-item').forEach(i => i.classList.remove('active'));
        item.classList.add('active');
        profilePopover.classList.remove('open');
        showToast(`Perfil cargado: ${{profName}}`);
      }});
    }});

    document.addEventListener('click', (e) => {{
      if (!profilePopover.contains(e.target) && e.target !== profileBtn) {{
        profilePopover.classList.remove('open');
      }}
    }});

    // ── Apply Button ────────────────────────────────────────────────────
    btnApply.addEventListener('click', () => {{
      btnApply.classList.remove('active');
      btnApply.textContent = '¡Aplicado!';
      showToast('Configuración grabada al ratón exitosamente');
      setTimeout(() => btnApply.textContent = 'Aplicar', 1400);
    }});

    // ── Modal Dialog Controls ───────────────────────────────────────────
    const modal = document.getElementById('modal-overlay');
    const openModalBtn = document.getElementById('add-game-btn');
    const cancelModalBtn = document.getElementById('modal-cancel');
    const addModalBtn = document.getElementById('modal-add');

    const openModal = () => modal.classList.add('open');
    const closeModal = () => modal.classList.remove('open');

    openModalBtn.addEventListener('click', openModal);
    cancelModalBtn.addEventListener('click', closeModal);
    addModalBtn.addEventListener('click', () => {{
      closeModal();
      showToast('Juego añadido correctamente a AutoPilot');
    }});
    modal.addEventListener('click', (e) => {{
      if (e.target === modal) closeModal();
    }});

    // Row deletion animation
    document.querySelectorAll('.icon-button.delete').forEach(btn => {{
      btn.addEventListener('click', (e) => {{
        e.stopPropagation();
        const row = btn.closest('.adw-row');
        row.style.opacity = '0';
        row.style.transform = 'translateX(20px)';
        row.style.transition = 'all 0.2s ease';
        setTimeout(() => {{
          row.remove();
          showToast('Regla de juego eliminada');
        }}, 200);
      }});
    }});
  </script>
</body>
</html>
"""

with open('design/libadwaita_mockup.html', 'w') as f:
    f.write(html_template)

print("Generated polished design/libadwaita_mockup.html successfully! Size:", len(html_template))
