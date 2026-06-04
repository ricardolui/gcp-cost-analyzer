#!/usr/bin/env python3
import json
import os
import sys
from datetime import datetime, timedelta
from google.cloud import bigquery

# Import the HTML template from standard configuration
# We keep the beautiful styling from the original dashboard
HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>GCP Cost Analysis Dashboard - {month_formatted}</title>
    <link href="https://fonts.googleapis.com/css2?family=Hanken+Grotesk:wght@400;500;600;700;800&family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500;600&display=swap" rel="stylesheet">
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/chartjs-plugin-zoom@2.0.1/dist/chartjs-plugin-zoom.min.js"></script>
    <style>
        :root {{
            --bg-color: #f8f9fa;
            --surface-white: #ffffff;
            --panel-bg: #ffffff;
            --surface-container: #f1f3f4;
            --surface-container-high: #e8eaed;
            --border-color: #dadce0;
            --border-strong: #c1c6d6;
            --primary: #1a73e8;
            --primary-strong: #1557b0;
            --primary-glow: rgba(26, 115, 232, 0.10);
            --accent-green: #1e8e3e;
            --accent-green-glow: rgba(30, 142, 62, 0.10);
            --accent-red: #d93025;
            --accent-red-glow: rgba(217, 48, 37, 0.10);
            --accent-yellow: #f9ab00;
            --text-main: #202124;
            --text-muted: #5f6368;
            --card-header-bg: #f8f9fa;
            --shadow-sm: 0 1px 2px rgba(60,64,67,0.08), 0 1px 3px rgba(60,64,67,0.10);
            --shadow-md: 0 1px 3px rgba(60,64,67,0.12), 0 6px 16px rgba(60,64,67,0.10);
            --font-head: 'Hanken Grotesk', sans-serif;
            --font-body: 'Inter', sans-serif;
            --font-mono: 'JetBrains Mono', monospace;
        }}

        * {{
            box-sizing: border-box;
            margin: 0;
            padding: 0;
        }}

        body {{
            font-family: var(--font-body);
            background-color: var(--bg-color);
            color: var(--text-main);
            min-height: 100vh;
            -webkit-font-smoothing: antialiased;
            padding: 2.5rem;
            padding-top: calc(56px + 2.5rem);
            padding-left: calc(240px + 2.5rem);
        }}

        .container {{
            max-width: 1400px;
            margin: 0 auto;
        }}

        /* Fixed top navbar (talent-scraper style) */
        header {{
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            z-index: 100;
            height: 56px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 0 1.5rem;
            background: var(--surface-white);
            border-bottom: 1px solid var(--border-color);
        }}

        .logo-area {{
            display: flex;
            align-items: center;
            gap: 0.85rem;
        }}

        .logo-icon {{
            background: var(--primary);
            width: 36px;
            height: 36px;
            border-radius: 8px;
            display: flex;
            align-items: center;
            justify-content: center;
            flex-shrink: 0;
        }}

        .logo-icon svg {{
            fill: white;
            width: 20px;
            height: 20px;
        }}

        .title-group h1 {{
            font-family: var(--font-head);
            font-size: 1.1rem;
            font-weight: 700;
            color: var(--text-main);
            line-height: 1.2;
        }}

        .title-group p {{
            color: var(--text-muted);
            font-size: 0.75rem;
            margin-top: 0.05rem;
        }}

        .header-controls {{
            display: flex;
            align-items: center;
            gap: 1rem;
        }}

        .refresh-btn {{
            background: var(--primary);
            color: white;
            border: none;
            padding: 0.5rem 1.1rem;
            border-radius: 9999px;
            font-weight: 600;
            font-size: 0.85rem;
            cursor: pointer;
            font-family: inherit;
            display: flex;
            align-items: center;
            gap: 0.5rem;
            box-shadow: var(--shadow-sm);
            transition: all 0.2s ease;
        }}

        .refresh-btn:hover {{
            background: var(--primary-strong);
            box-shadow: var(--shadow-md);
        }}

        .refresh-btn:active {{
            transform: translateY(1px);
        }}

        .refresh-btn.loading {{
            opacity: 0.7;
            cursor: not-allowed;
        }}

        .refresh-btn.loading svg {{
            animation: spin 1s linear infinite;
        }}

        @keyframes spin {{
            0% {{ transform: rotate(0deg); }}
            100% {{ transform: rotate(360deg); }}
        }}

        .gcloud-badge {{
            background: var(--surface-container);
            border: 1px solid var(--border-color);
            color: var(--text-muted);
            padding: 0.4rem 0.9rem;
            border-radius: 9999px;
            font-size: 0.8rem;
            display: flex;
            align-items: center;
            gap: 0.5rem;
            font-family: var(--font-mono);
        }}

        .badge-dot {{
            width: 8px;
            height: 8px;
            background-color: var(--accent-green);
            border-radius: 50%;
        }}

        /* Metrics Grid */
        .metrics-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
            gap: 1.5rem;
            margin-bottom: 2.5rem;
        }}

        .metric-card {{
            background: var(--panel-bg);
            border: 1px solid var(--border-color);
            border-radius: 16px;
            padding: 1.5rem;
            position: relative;
            overflow: hidden;
            box-shadow: var(--shadow-sm);
            transition: transform 0.2s ease, box-shadow 0.2s ease;
        }}

        .metric-card:hover {{
            transform: translateY(-2px);
            box-shadow: var(--shadow-md);
        }}

        .metric-card::before {{
            content: '';
            position: absolute;
            top: 0;
            left: 0;
            width: 100%;
            height: 3px;
        }}

        .metric-card.net-cost::before {{ background: var(--primary); }}
        .metric-card.gross-cost::before {{ background: #4285f4; }}
        .metric-card.credits::before {{ background: var(--accent-green); }}

        .metric-label {{
            color: var(--text-muted);
            font-size: 0.875rem;
            font-weight: 500;
            margin-bottom: 0.5rem;
        }}

        .metric-val {{
            font-size: 2.25rem;
            font-weight: 700;
            font-family: var(--font-mono);
            color: var(--text-main);
        }}

        .metric-val.green {{
            color: var(--accent-green);
        }}

        .metric-subtext {{
            color: var(--text-muted);
            font-size: 0.75rem;
            margin-top: 0.5rem;
            display: flex;
            align-items: center;
            gap: 0.25rem;
        }}

        /* Dashboard Layout */
        .dashboard-row {{
            display: grid;
            grid-template-columns: 2fr 1fr;
            gap: 1.5rem;
            margin-bottom: 2.5rem;
        }}

        .row-equal {{
            grid-template-columns: 1fr 1fr;
        }}

        .panel {{
            background: var(--panel-bg);
            border: 1px solid var(--border-color);
            border-radius: 16px;
            padding: 1.75rem;
            overflow: hidden;
            display: flex;
            flex-direction: column;
            box-shadow: var(--shadow-sm);
        }}

        .panel-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 1.5rem;
        }}

        .panel-title {{
            font-family: var(--font-head);
            font-size: 1.15rem;
            font-weight: 700;
            color: var(--text-main);
            display: flex;
            align-items: center;
            gap: 0.5rem;
        }}

        .panel-title svg {{
            width: 20px;
            height: 20px;
            fill: var(--primary);
        }}

        .chart-container {{
            position: relative;
            flex-grow: 1;
            min-height: 280px;
            display: flex;
            align-items: center;
            justify-content: center;
        }}

        /* Table Styling */
        .table-scroll {{
            overflow-x: auto;
            max-height: 400px;
            border-radius: 8px;
            border: 1px solid var(--border-color);
        }}

        table {{
            width: 100%;
            border-collapse: collapse;
            font-size: 0.875rem;
            text-align: left;
        }}

        th {{
            background-color: var(--card-header-bg);
            padding: 0.85rem 1rem;
            font-weight: 600;
            color: var(--text-muted);
            border-bottom: 1px solid var(--border-color);
            position: sticky;
            top: 0;
            z-index: 10;
        }}

        td {{
            padding: 0.85rem 1rem;
            border-bottom: 1px solid var(--border-color);
            color: var(--text-main);
            font-family: var(--font-body);
        }}

        tr:last-child td {{
            border-bottom: none;
        }}

        tr:hover td {{
            background-color: var(--surface-container);
        }}

        .num-col {{
            text-align: right;
            font-family: var(--font-mono);
        }}

        .mono-text {{
            font-family: var(--font-mono);
            font-size: 0.8rem;
        }}

        .pct-bar-bg {{
            background: var(--surface-container-high);
            width: 100px;
            height: 6px;
            border-radius: 3px;
            display: inline-block;
            vertical-align: middle;
            margin-right: 0.5rem;
            overflow: hidden;
        }}

        .pct-bar-fill {{
            background: var(--primary);
            height: 100%;
            border-radius: 3px;
        }}

        .pill {{
            padding: 0.15rem 0.5rem;
            border-radius: 4px;
            font-size: 0.75rem;
            font-weight: 600;
            display: inline-block;
        }}

        .pill-primary {{
            background: var(--primary-glow);
            color: var(--primary);
            border: 1px solid rgba(26, 115, 232, 0.30);
        }}

        .pill-green {{
            background: var(--accent-green-glow);
            color: var(--accent-green);
            border: 1px solid rgba(30, 142, 62, 0.30);
        }}

        /* Recommendations Panel */
        .recommendation-list {{
            display: flex;
            flex-direction: column;
            gap: 1rem;
        }}

        .rec-item {{
            background: var(--surface-white);
            border: 1px solid var(--border-color);
            border-radius: 12px;
            padding: 1.25rem;
            display: flex;
            gap: 1rem;
            transition: border-color 0.2s ease, box-shadow 0.2s ease;
        }}

        .rec-item:hover {{
            border-color: var(--border-strong);
            box-shadow: var(--shadow-sm);
        }}

        .rec-icon-box {{
            width: 40px;
            height: 40px;
            border-radius: 10px;
            display: flex;
            align-items: center;
            justify-content: center;
            flex-shrink: 0;
        }}

        .rec-icon-box.warning {{
            background: var(--accent-red-glow);
            color: var(--accent-red);
            border: 1px solid rgba(217, 48, 37, 0.20);
        }}

        .rec-icon-box.info {{
            background: var(--primary-glow);
            color: var(--primary);
            border: 1px solid rgba(26, 115, 232, 0.20);
        }}

        .rec-content h4 {{
            font-family: var(--font-head);
            font-size: 0.95rem;
            font-weight: 700;
            color: var(--text-main);
            margin-bottom: 0.25rem;
        }}

        .rec-content p {{
            font-size: 0.85rem;
            color: var(--text-muted);
            line-height: 1.4;
            margin-bottom: 0.5rem;
        }}

        .rec-saving {{
            font-size: 0.8rem;
            font-weight: 600;
            color: var(--accent-green);
            font-family: var(--font-mono);
            background: var(--accent-green-glow);
            padding: 0.15rem 0.5rem;
            border-radius: 4px;
            display: inline-block;
        }}

        /* Expandable Accordions for project detail breakdown */
        .accordion-list {{
            display: flex;
            flex-direction: column;
            gap: 0.75rem;
            margin-top: 1rem;
        }}

        .accordion-item {{
            background: var(--surface-white);
            border: 1px solid var(--border-color);
            border-radius: 12px;
            overflow: hidden;
            transition: border-color 0.2s ease, box-shadow 0.2s ease;
        }}

        .accordion-item:hover {{
            border-color: var(--border-strong);
            box-shadow: var(--shadow-sm);
        }}

        .accordion-trigger {{
            padding: 1.25rem;
            display: flex;
            justify-content: space-between;
            align-items: center;
            cursor: pointer;
            user-select: none;
        }}

        .accordion-trigger-left {{
            display: flex;
            align-items: center;
            gap: 1rem;
        }}

        .project-rank {{
            font-family: var(--font-mono);
            font-size: 0.9rem;
            font-weight: 700;
            color: var(--text-muted);
            background: var(--surface-container);
            width: 24px;
            height: 24px;
            border-radius: 6px;
            display: flex;
            align-items: center;
            justify-content: center;
        }}

        .project-info-title {{
            font-family: var(--font-head);
            font-weight: 700;
            font-size: 1rem;
            color: var(--text-main);
        }}

        .project-info-meta {{
            font-size: 0.75rem;
            color: var(--text-muted);
            margin-top: 0.15rem;
        }}

        .accordion-trigger-right {{
            display: flex;
            align-items: center;
            gap: 1.5rem;
        }}

        .project-accordion-cost {{
            font-family: var(--font-mono);
            font-weight: 700;
            font-size: 1.1rem;
            color: var(--text-main);
        }}

        .chevron-icon {{
            transition: transform 0.3s ease;
            color: var(--text-muted);
        }}

        .accordion-item.active .chevron-icon {{
            transform: rotate(180deg);
        }}

        .accordion-content {{
            max-height: 0;
            overflow: hidden;
            transition: max-height 0.3s ease, padding 0.3s ease;
            background: var(--surface-container);
            border-top: 1px solid transparent;
        }}

        .accordion-item.active .accordion-content {{
            max-height: 1000px;
            padding: 1.25rem;
            border-top: 1px solid var(--border-color);
            overflow-y: auto;
        }}

        .accordion-grid {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 1rem;
        }}

        @media (max-width: 900px) {{
            .dashboard-row {{
                grid-template-columns: 1fr;
            }}
            .accordion-grid {{
                grid-template-columns: 1fr;
            }}
            body {{
                padding: 1rem;
                padding-top: calc(56px + 1rem);
            }}
            .title-group p {{
                display: none;
            }}
        }}

        .tab-btn {{
            background: transparent;
            color: var(--text-muted);
            border: none;
            padding: 0.35rem 0.75rem;
            border-radius: 4px;
            font-size: 0.75rem;
            cursor: pointer;
            font-weight: 600;
            font-family: inherit;
            transition: all 0.2s ease;
        }}

        .tab-btn.active {{
            background: var(--primary);
            color: white;
        }}

        .tab-btn:hover:not(.active) {{
            color: var(--text-main);
            background: var(--surface-container);
        }}

        .range-btn {{
            background: transparent;
            color: var(--text-muted);
            border: 1px solid transparent;
            padding: 0.25rem 0.5rem;
            border-radius: 4px;
            font-size: 0.7rem;
            cursor: pointer;
            font-weight: 600;
            font-family: inherit;
            transition: all 0.2s ease;
        }}

        .range-btn.active-range {{
            background: var(--primary-glow);
            color: var(--primary);
            border-color: rgba(26, 115, 232, 0.40);
        }}

        .range-btn:hover:not(.active-range) {{
            color: var(--text-main);
            background: var(--surface-container);
        }}

        .date-filter-wrapper {{
            display: flex;
            align-items: center;
            gap: 0.25rem;
            background: var(--surface-container);
            padding: 0.15rem 0.4rem;
            border-radius: 6px;
            border: 1px solid var(--border-color);
            transition: all 0.2s ease;
        }}

        .date-filter-wrapper:focus-within {{
            border-color: rgba(26, 115, 232, 0.40);
            background: var(--primary-glow);
            box-shadow: 0 0 0 3px rgba(26, 115, 232, 0.10);
        }}

        .date-filter-input {{
            background: transparent;
            border: none;
            color: var(--text-main);
            font-family: var(--font-mono);
            font-size: 0.75rem;
            outline: none;
            cursor: pointer;
        }}

        .date-filter-input::-webkit-calendar-picker-indicator {{
            opacity: 0.6;
            cursor: pointer;
        }}

        .date-filter-input::-webkit-calendar-picker-indicator:hover {{
            opacity: 1;
        }}

        /* ===== App shell: sidebar + tabbed views ===== */
        .sidebar {{
            position: fixed;
            top: 56px;
            left: 0;
            bottom: 0;
            width: 240px;
            background: var(--surface-white);
            border-right: 1px solid var(--border-color);
            padding: 1rem 0.75rem;
            overflow-y: auto;
            z-index: 90;
        }}
        .sidebar-nav {{ display: flex; flex-direction: column; gap: 0.25rem; }}
        .nav-item {{
            display: flex;
            align-items: center;
            gap: 0.85rem;
            width: 100%;
            padding: 0.7rem 1rem;
            border: none;
            background: transparent;
            color: var(--text-muted);
            font-family: var(--font-body);
            font-size: 0.9rem;
            font-weight: 600;
            cursor: pointer;
            border-radius: 0 9999px 9999px 0;
            transition: background 0.15s ease, color 0.15s ease;
            text-align: left;
        }}
        .nav-item svg {{ flex-shrink: 0; }}
        .nav-item:hover {{ background: var(--surface-container); color: var(--text-main); }}
        .nav-item.active {{ background: var(--primary-glow); color: var(--primary); }}

        /* Tab views */
        .tab-view {{ display: none; }}
        .tab-view.active {{ display: block; animation: fadeIn 0.2s ease; }}
        @keyframes fadeIn {{ from {{ opacity: 0; transform: translateY(4px); }} to {{ opacity: 1; transform: none; }} }}

        /* Filters */
        .filter-bar {{ display: flex; align-items: center; gap: 0.75rem; flex-wrap: wrap; }}
        .filter-select {{
            background: var(--surface-white);
            border: 1px solid var(--border-color);
            color: var(--text-main);
            font-family: var(--font-body);
            font-size: 0.8rem;
            padding: 0.45rem 0.75rem;
            border-radius: 9999px;
            cursor: pointer;
            outline: none;
        }}
        .filter-select:focus {{ border-color: var(--primary); }}
        .range-group {{ display: flex; gap: 0.25rem; background: var(--surface-container); padding: 0.2rem; border-radius: 9999px; }}
        .search-input {{
            display: flex;
            align-items: center;
            gap: 0.4rem;
            background: var(--surface-white);
            border: 1px solid var(--border-color);
            border-radius: 9999px;
            padding: 0.4rem 0.85rem;
            min-width: 220px;
        }}
        .search-input:focus-within {{ border-color: var(--primary); }}
        .search-input input {{ border: none; outline: none; background: transparent; font-family: var(--font-body); font-size: 0.8rem; color: var(--text-main); width: 100%; }}

        /* Period summary band */
        .summary-band {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(190px, 1fr));
            gap: 1rem;
            margin-bottom: 2rem;
        }}
        .summary-card {{
            background: var(--panel-bg);
            border: 1px solid var(--border-color);
            border-radius: 14px;
            padding: 1.1rem 1.25rem;
            box-shadow: var(--shadow-sm);
        }}
        .summary-label {{ font-size: 0.7rem; text-transform: uppercase; letter-spacing: 0.04em; color: var(--text-muted); font-weight: 600; }}
        .summary-value {{ font-family: var(--font-mono); font-size: 1.5rem; font-weight: 700; color: var(--text-main); margin-top: 0.35rem; }}
        .summary-sub {{ font-size: 0.72rem; color: var(--text-muted); margin-top: 0.2rem; }}

        /* Tracker stat cards */
        .tracker-stats {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(170px, 1fr));
            gap: 1rem;
            margin-bottom: 1.5rem;
        }}
        .stat-card {{
            background: var(--panel-bg);
            border: 1px solid var(--border-color);
            border-radius: 14px;
            padding: 1rem 1.15rem;
            box-shadow: var(--shadow-sm);
        }}
        .stat-card .summary-value {{ font-size: 1.3rem; }}
        .delta-up {{ color: var(--accent-red); }}
        .delta-down {{ color: var(--accent-green); }}

        /* Top movers */
        .movers-list {{ display: flex; flex-direction: column; gap: 0.5rem; }}
        .mover-row {{
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding: 0.6rem 0.85rem;
            border: 1px solid var(--border-color);
            border-radius: 10px;
            font-size: 0.85rem;
        }}
        .mover-row .mover-name {{ color: var(--text-main); font-weight: 600; }}
        .mover-delta {{ font-family: var(--font-mono); font-weight: 700; }}

        /* Sidebar -> horizontal bar on small screens */
        @media (max-width: 900px) {{
            .sidebar {{
                top: 56px;
                width: 100%;
                bottom: auto;
                height: auto;
                border-right: none;
                border-bottom: 1px solid var(--border-color);
                padding: 0.4rem 0.5rem;
            }}
            .sidebar-nav {{ flex-direction: row; overflow-x: auto; gap: 0.25rem; }}
            .nav-item {{ border-radius: 9999px; padding: 0.5rem 0.85rem; white-space: nowrap; }}
            .nav-item span {{ font-size: 0.8rem; }}
            body {{ padding-left: 1rem; padding-top: calc(56px + 54px + 1rem); }}
        }}

    </style>
</head>
<body>
    <div class="container">
        <header>
            <div class="logo-area">
                <div class="logo-icon">
                    <svg viewBox="0 0 24 24"><path d="M19 3H5c-1.1 0-2 .9-2 2v14c0 1.1.9 2 2 2h14c1.1 0 2-.9 2-2V5c0-1.1-.9-2-2-2zm-2 10h-4v4h-2v-4H7v-2h4V7h2v4h4v2z"/></svg>
                </div>
                <div class="title-group">
                    <h1>GCP Monthly Cost Dashboard</h1>
                    <p>Analysis of billing per Project, Service, SKU, and Resource</p>
                </div>
            </div>
            <div class="header-controls">
                <div style="text-align: right; font-size: 0.85rem; color: var(--text-muted);">
                    <div>User: <span style="color: var(--text-main); font-weight: 600;">{user_email}</span></div>
                    <div style="font-size: 0.75rem; margin-top: 0.15rem;">Cached: {cached_time}</div>
                </div>
                <button class="refresh-btn" id="refreshBtn" onclick="triggerRefresh()">
                    <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
                        <path d="M23 4v6h-6M1 20v-6h6"></path>
                        <path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15"></path>
                    </svg>
                    Refresh Data
                </button>
                <div class="gcloud-badge">
                    <div class="badge-dot"></div>
                    Config: {config_name}
                </div>
            </div>
        </header>

        <aside class="sidebar">
            <nav class="sidebar-nav">
                <button class="nav-item active" data-view="overview" onclick="switchView('overview')">
                    <svg viewBox="0 0 24 24" width="20" height="20" fill="currentColor"><path d="M3 13h8V3H3v10zm0 8h8v-6H3v6zm10 0h8V11h-8v10zm0-18v6h8V3h-8z"/></svg>
                    <span>Overview</span>
                </button>
                <button class="nav-item" data-view="tracker" onclick="switchView('tracker')">
                    <svg viewBox="0 0 24 24" width="20" height="20" fill="currentColor"><path d="M3.5 18.49l6-6.01 4 4L22 6.92l-1.41-1.41-7.09 7.97-4-4L2 16.99z"/></svg>
                    <span>Spending Tracker</span>
                </button>
                <button class="nav-item" data-view="projects" onclick="switchView('projects')">
                    <svg viewBox="0 0 24 24" width="20" height="20" fill="currentColor"><path d="M10 4H4c-1.1 0-1.99.9-1.99 2L2 18c0 1.1.9 2 2 2h16c1.1 0 2-.9 2-2V8c0-1.1-.9-2-2-2h-8l-2-2z"/></svg>
                    <span>Projects</span>
                </button>
                <button class="nav-item" data-view="services" onclick="switchView('services')">
                    <svg viewBox="0 0 24 24" width="20" height="20" fill="currentColor"><path d="M3 13h12v-2H3v2zm0 4h12v-2H3v2zm0-8h12V7H3v2zm14 8h2v-4h2v-2h-2V9h-2v4h-2v2h2v4z"/></svg>
                    <span>Services &amp; SKUs</span>
                </button>
            </nav>
        </aside>


        <section id="view-overview" class="tab-view active">
        <div class="summary-band">
            <div class="summary-card">
                <div class="summary-label">Analyzed period</div>
                <div class="summary-value" id="sumPeriod">&mdash;</div>
                <div class="summary-sub" id="sumRange">&mdash;</div>
            </div>
            <div class="summary-card">
                <div class="summary-label">Days with spend</div>
                <div class="summary-value" id="sumDays">&mdash;</div>
                <div class="summary-sub">in selected month</div>
            </div>
            <div class="summary-card">
                <div class="summary-label">Daily average</div>
                <div class="summary-value" id="sumAvg">&mdash;</div>
                <div class="summary-sub">net cost / active day</div>
            </div>
            <div class="summary-card">
                <div class="summary-label">Projected month-end</div>
                <div class="summary-value" id="sumProjected">&mdash;</div>
                <div class="summary-sub" id="sumProjectedSub">run-rate estimate</div>
            </div>
            <div class="summary-card">
                <div class="summary-label">vs previous month</div>
                <div class="summary-value" id="sumMoM">&mdash;</div>
                <div class="summary-sub" id="sumMoMSub">net cost change</div>
            </div>
        </div>

        <!-- Metrics Grid -->
        <div class="metrics-grid">
            <div class="metric-card net-cost">
                <div class="metric-label">Net Cost (Current Month)</div>
                <div class="metric-val">${net_cost:,.2f}</div>
                <div class="metric-subtext">Total costs minus applied credits</div>
            </div>
            <div class="metric-card gross-cost">
                <div class="metric-label">Gross Cost (Current Month)</div>
                <div class="metric-val">${gross_cost:,.2f}</div>
                <div class="metric-subtext">Sum of list-price service usage</div>
            </div>
            <div class="metric-card credits">
                <div class="metric-label">Applied Credits</div>
                <div class="metric-val green">${credits:,.2f}</div>
                <div class="metric-subtext">Promotions, free tiers, and discounts</div>
            </div>
        </div>

        <!-- Row 1: Charts -->
        <div class="dashboard-row row-equal">
            <div class="panel">
                <div class="panel-header">
                    <div class="panel-title">
                        <svg viewBox="0 0 24 24"><path d="M19 3H5c-1.1 0-2 .9-2 2v14c0 1.1.9 2 2 2h14c1.1 0 2-.9 2-2V5c0-1.1-.9-2-2-2zm-7 14H5v-2h7v2zm3-4H5v-2h10v2zm3-4H5V7h13v2z"/></svg>
                        Share of Costs by Project
                    </div>
                </div>
                <div class="chart-container">
                    <canvas id="projectChart"></canvas>
                </div>
            </div>
            <div class="panel">
                <div class="panel-header">
                    <div class="panel-title">
                        <svg viewBox="0 0 24 24"><path d="M19 3H5c-1.1 0-2 .9-2 2v14c0 1.1.9 2 2 2h14c1.1 0 2-.9 2-2V5c0-1.1-.9-2-2-2zm-7 14H5v-2h7v2zm3-4H5v-2h10v2zm3-4H5V7h13v2z"/></svg>
                        Share of Costs by Service
                    </div>
                </div>
                <div class="chart-container">
                    <canvas id="serviceChart"></canvas>
                </div>
            </div>
        </div>

        <!-- Row 2: Trend and Optimization -->
        <div class="dashboard-row">
            <div class="panel">
                <div class="panel-header">
                    <div class="panel-title">
                        <svg viewBox="0 0 24 24"><path d="M16 6l2.29 2.29-4.88 4.88-4-4L2 16.59 3.41 18l6-6 4 4 6.3-6.29L22 12V6z"/></svg>
                        Month-over-Month Trend
                    </div>
                </div>
                <div style="min-height: 250px; display: flex; align-items: center; justify-content: center;">
                    <canvas id="trendChart"></canvas>
                </div>
            </div>

            <div class="panel">
                <div class="panel-header">
                    <div class="panel-title">
                        <svg viewBox="0 0 24 24"><path d="M9 21c0 .55.45 1 1 1h6c.55 0 1-.45 1-1v-1H9v1zm3-19C8.14 2 5 5.14 5 9c0 2.38 1.19 4.47 3 5.74V17c0 .55.45 1 1 1h6c.55 0 1-.45 1-1v-2.26c1.81-1.27 3-3.36 3-5.74 0-3.86-3.14-7-7-7zm2.85 11.1l-.85.6V16h-4v-2.3l-.85-.6C7.8 12.16 7 10.63 7 9c0-2.76 2.24-5 5-5s5 2.24 5 5c0 1.63-.8 3.16-2.15 4.1z"/></svg>
                        Cost Insights & Optimization
                    </div>
                </div>
                <div class="recommendation-list">
                    <div class="rec-item">
                        <div class="rec-icon-box warning">
                            <svg viewBox="0 0 24 24" width="20" height="20" fill="currentColor"><path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm1 15h-2v-2h2v2zm0-4h-2V7h2v6z"/></svg>
                        </div>
                        <div class="rec-content">
                            <h4>High Vertex AI Batch Embedding Costs</h4>
                            <p>Vertex AI is your #1 cost source. Text Embeddings Batch Predictions alone costs <b>${embedding_cost:,.2f}</b>, which is <b>{embedding_pct:.1f}%</b> of your total budget. Consider scheduling batches more efficiently or caching text embeddings.</p>
                            <span class="rec-saving">Potential Savings: $50 - $120 /mo</span>
                        </div>
                    </div>
                    <div class="rec-item">
                        <div class="rec-icon-box info">
                            <svg viewBox="0 0 24 24" width="20" height="20" fill="currentColor"><path d="M11 7h2v2h-2zm0 4h2v6h-2zm1-9C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm0 18c-4.41 0-8-3.59-8-8s3.59-8 8-8 8 3.59 8 8-3.59 8-8 8z"/></svg>
                        </div>
                        <div class="rec-content">
                            <h4>BigQuery Reservation Underutilization</h4>
                            <p>You have continuous Reservation expenses (<b>${bq_res_cost:,.2f}</b>) for Enterprise Edition. Audit slot utilization to ensure edition-based reservation capacity (baseline and autoscale slots) is more economical than on-demand queries for your active query profile.</p>
                            <span class="rec-saving">Potential Savings: Audit Needed</span>
                        </div>
                    </div>
                    <div class="rec-item">
                        <div class="rec-icon-box info">
                            <svg viewBox="0 0 24 24" width="20" height="20" fill="currentColor"><path d="M11 7h2v2h-2zm0 4h2v6h-2zm1-9C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm0 18c-4.41 0-8-3.59-8-8s3.59-8 8-8 8 3.59 8 8-3.59 8-8 8z"/></svg>
                        </div>
                        <div class="rec-content">
                            <h4>Cloud SQL Databases Check</h4>
                            <p>Zonal PostgreSQL and MySQL instances in MDM projects (<b>postgres-source</b>, <b>postgres-instance</b>, <b>mysql-customer</b>) are generating 24/7 charges. Ensure standard instances are shut down or resized in non-prod environments when idle.</p>
                            <span class="rec-saving">Potential Savings: $40 - $80 /mo</span>
                        </div>
                    </div>
                </div>
            </div>
        </div>

        </section>

        <section id="view-tracker" class="tab-view">
        <div class="panel" style="margin-bottom: 1.5rem;">
            <div class="panel-header" style="flex-wrap: wrap; gap: 1rem;">
                <div class="panel-title">
                    <svg viewBox="0 0 24 24"><path d="M3.5 18.49l6-6.01 4 4L22 6.92l-1.41-1.41-7.09 7.97-4-4L2 16.99z"/></svg>
                    Daily Spending Tracker
                </div>
                <div class="filter-bar">
                    <select class="filter-select" id="trackerProject" onchange="updateTracker()">
                        <option value="__all__">All projects</option>
                    </select>
                    <div class="range-group">
                        <button class="range-btn" onclick="trackerRange(7, this)">7D</button>
                        <button class="range-btn" onclick="trackerRange(14, this)">14D</button>
                        <button class="range-btn" onclick="trackerRange(30, this)">30D</button>
                        <button class="range-btn active-range" onclick="trackerRange(60, this)">60D</button>
                    </div>
                    <div class="date-filter-wrapper">
                        <input type="date" class="date-filter-input" id="trackerStart" onchange="trackerCustom()">
                        <span style="color: var(--text-muted); font-size: 0.7rem;">to</span>
                        <input type="date" class="date-filter-input" id="trackerEnd" onchange="trackerCustom()">
                    </div>
                </div>
            </div>
            <div style="position: relative; height: 360px;">
                <canvas id="trackerChart"></canvas>
            </div>
        </div>

        <div class="tracker-stats" id="trackerStats"></div>

        <div class="panel">
            <div class="panel-header">
                <div class="panel-title">
                    <svg viewBox="0 0 24 24"><path d="M16 6l2.29 2.29-4.88 4.88-4-4L2 16.59 3.41 18l6-6 4 4 6.3-6.29L22 12V6z"/></svg>
                    Top Movers &mdash; last 7 days vs prior 7 days
                </div>
            </div>
            <div class="movers-list" id="moversList"></div>
        </div>
        </section>

        <section id="view-projects" class="tab-view">
        <div class="filter-bar" style="margin-bottom: 1.5rem;">
            <div class="search-input">
                <svg viewBox="0 0 24 24" width="16" height="16" fill="var(--text-muted)"><path d="M15.5 14h-.79l-.28-.27C15.41 12.59 16 11.11 16 9.5 16 5.91 13.09 3 9.5 3S3 5.91 3 9.5 5.91 16 9.5 16c1.61 0 3.09-.59 4.23-1.57l.27.28v.79l5 4.99L20.49 19l-4.99-5zm-6 0C7.01 14 5 11.99 5 9.5S7.01 5 9.5 5 14 7.01 14 9.5 11.99 14 9.5 14z"/></svg>
                <input type="text" id="projectSearch" placeholder="Filter projects by name or ID&hellip;" oninput="filterProjects()">
            </div>
        </div>
        <!-- Row 3: Project Detail Breakdown (Expandable Accordions) -->
        <div class="panel" style="margin-bottom: 2.5rem;">
            <div class="panel-header">
                <div class="panel-title">
                    <svg viewBox="0 0 24 24"><path d="M4 6H2v14c0 1.1.9 2 2 2h14v-2H4V6zm16-4H8c-1.1 0-2 .9-2 2v12c0 1.1.9 2 2 2h12c1.1 0 2-.9 2-2V4c0-1.1-.9-2-2-2zm0 14H8V4h12v12z"/></svg>
                    Project Deep Dive Breakdown
                </div>
                <div style="color: var(--text-muted); font-size: 0.85rem;">Click a project to expand and view Service, SKU & Resource details</div>
            </div>

            <div class="accordion-list">
                {accordion_items_html}
            </div>
        </div>

        </section>

        <section id="view-services" class="tab-view">
        <div class="filter-bar" style="margin-bottom: 1.5rem;">
            <select class="filter-select" id="skuProject" onchange="filterSkuTable()">
                <option value="__all__">All projects</option>
            </select>
            <div class="search-input">
                <svg viewBox="0 0 24 24" width="16" height="16" fill="var(--text-muted)"><path d="M15.5 14h-.79l-.28-.27C15.41 12.59 16 11.11 16 9.5 16 5.91 13.09 3 9.5 3S3 5.91 3 9.5 5.91 16 9.5 16c1.61 0 3.09-.59 4.23-1.57l.27.28v.79l5 4.99L20.49 19l-4.99-5zm-6 0C7.01 14 5 11.99 5 9.5S7.01 5 9.5 5 14 7.01 14 9.5 11.99 14 9.5 14z"/></svg>
                <input type="text" id="skuSearch" placeholder="Search service, SKU or project&hellip;" oninput="filterSkuTable()">
            </div>
        </div>
        <!-- Row 4: Top 25 SKU Detailed Table -->
        <div class="panel">
            <div class="panel-header">
                <div class="panel-title">
                    <svg viewBox="0 0 24 24"><path d="M3 13h12v-2H3v2zm0 4h12v-2H3v2zm0-8h12V7H3v2zm14 8h2v-4h2v-2h-2V9h-2v4h-2v2h2v4z"/></svg>
                    Top 25 Billing SKUs ({month_formatted})
                </div>
            </div>
            <div class="table-scroll">
                <table>
                    <thead>
                        <tr>
                            <th>Project ID</th>
                            <th>Service</th>
                            <th>SKU Description</th>
                            <th class="num-col" style="width: 120px;">Net Cost</th>
                            <th class="num-col" style="width: 80px;">Share</th>
                        </tr>
                    </thead>
                    <tbody>
                        {sku_table_rows_html}
                    </tbody>
                </table>
            </div>
        </div>
        </section>
    </div>

    <script>
        function triggerRefresh() {{
            const btn = document.getElementById("refreshBtn");
            btn.classList.add("loading");
            btn.innerHTML = `<svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" style="animation: spin 1s linear infinite;"><path d="M23 4v6h-6M1 20v-6h6"></path><path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15"></path></svg> Refreshing...`;
            
            // Make a POST request to /refresh to recalculate
            fetch('/refresh', {{ method: 'POST' }})
                .then(res => {{
                    if (res.ok) {{
                        window.location.reload();
                    }} else {{
                        alert("Failed to refresh billing data. Check backend logs.");
                        btn.classList.remove("loading");
                        btn.innerHTML = `<svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M23 4v6h-6M1 20v-6h6"></path><path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15"></path></svg> Refresh Data`;
                    }}
                }})
                .catch(err => {{
                    alert("Error contacting backend server: " + err);
                    btn.classList.remove("loading");
                }});
        }}

        // Setup Charts
        document.addEventListener("DOMContentLoaded", function() {{
            const pCtx = document.getElementById('projectChart').getContext('2d');
            const projectChart = new Chart(pCtx, {{
                type: 'doughnut',
                data: {{
                    labels: {project_labels_json},
                    datasets: [{{
                        data: {project_costs_json},
                        backgroundColor: [
                            '#1a73e8', '#4285f4', '#669df6', '#8ab4f8', '#aecbfa',
                            '#1e8e3e', '#34a853', '#5bb974', '#81c995', '#a8dab5',
                            '#f9ab00', '#fbbc04', '#fcc934', '#fdd663', '#fde293',
                            '#d93025', '#ea4335', '#ee675c', '#f28b82', '#f6aea9'
                        ],
                        borderWidth: 1,
                        borderColor: '#ffffff'
                    }}]
                }},
                options: {{
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {{
                        legend: {{
                            position: 'right',
                            labels: {{
                                color: '#5f6368',
                                font: {{
                                    family: 'Inter',
                                    size: 11
                                }},
                                boxWidth: 12,
                                padding: 12
                            }}
                        }}
                    }}
                }}
            }});

            const sCtx = document.getElementById('serviceChart').getContext('2d');
            const serviceChart = new Chart(sCtx, {{
                type: 'doughnut',
                data: {{
                    labels: {service_labels_json},
                    datasets: [{{
                        data: {service_costs_json},
                        backgroundColor: [
                            '#4285f4', '#34a853', '#fbbc04', '#ea4335', '#1a73e8',
                            '#1e8e3e', '#f9ab00', '#d93025', '#669df6', '#5bb974',
                            '#fcc934', '#ee675c', '#80868b', '#9aa0a6', '#5f6368'
                        ],
                        borderWidth: 1,
                        borderColor: '#ffffff'
                    }}]
                }},
                options: {{
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {{
                        legend: {{
                            position: 'right',
                            labels: {{
                                color: '#5f6368',
                                font: {{
                                    family: 'Inter',
                                    size: 11
                                }},
                                boxWidth: 12,
                                padding: 12
                            }}
                        }}
                    }}
                }}
            }});

            const tCtx = document.getElementById('trendChart').getContext('2d');
            const trendChart = new Chart(tCtx, {{
                type: 'line',
                data: {{
                    labels: {trend_labels_json},
                    datasets: [{{
                        label: 'Net Monthly Cost ($)',
                        data: {trend_costs_json},
                        borderColor: '#1a73e8',
                        backgroundColor: 'rgba(26, 115, 232, 0.12)',
                        borderWidth: 3,
                        pointBackgroundColor: '#1a73e8',
                        pointBorderColor: '#ffffff',
                        pointHoverRadius: 6,
                        fill: true,
                        tension: 0.3
                    }}]
                }},
                options: {{
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {{
                        legend: {{
                            display: false
                        }}
                    }},
                    scales: {{
                        x: {{
                            grid: {{
                                color: 'rgba(60, 64, 67, 0.12)'
                            }},
                            ticks: {{
                                color: '#5f6368',
                                font: {{
                                    family: 'Inter'
                                }}
                            }}
                        }},
                        y: {{
                            grid: {{
                                color: 'rgba(60, 64, 67, 0.12)'
                            }},
                            ticks: {{
                                color: '#5f6368',
                                font: {{
                                    family: 'JetBrains Mono'
                                }}
                            }}
                        }}
                    }}
                }}
            }});
        }});

        const dailyChartData = {daily_chart_data_json};
        const trendLabels = {trend_labels_json};
        const trendCosts = {trend_costs_json};
        const netCostTotal = {net_cost};
        let renderedCharts = {{}};
        const chartColors = [
            '#4285f4', '#34a853', '#fbbc04', '#ea4335', '#1a73e8',
            '#1e8e3e', '#f9ab00', '#d93025', '#669df6', '#5bb974'
        ];

        function getChartColor(idx, alpha = 1) {{
            const hex = chartColors[idx % chartColors.length];
            if (alpha === 1) return hex;
            const r = parseInt(hex.slice(1, 3), 16);
            const g = parseInt(hex.slice(3, 5), 16);
            const b = parseInt(hex.slice(5, 7), 16);
            return `rgba(${{r}}, ${{g}}, ${{b}}, ${{alpha}})`;
        }}

        function switchProjTab(event, projId, viewType) {{
            event.stopPropagation();
            const btnContainer = event.currentTarget.parentElement;
            btnContainer.querySelectorAll('.tab-btn').forEach(btn => {{
                btn.classList.remove('active');
            }});
            event.currentTarget.classList.add('active');
            
            const sContainer = document.getElementById(`service-chart-container-${{projId}}`);
            const skuContainer = document.getElementById(`sku-chart-container-${{projId}}`);
            
            if (viewType === 'service') {{
                if (sContainer) sContainer.style.display = 'block';
                if (skuContainer) skuContainer.style.display = 'none';
            }} else {{
                if (sContainer) sContainer.style.display = 'none';
                if (skuContainer) skuContainer.style.display = 'block';
            }}
        }}

        function filterChartRange(projId, days) {{
            const accordionItem = document.querySelector(`.accordion-item[data-project-id="${{projId}}"]`);
            if (accordionItem) {{
                accordionItem.querySelectorAll('.range-btn').forEach(btn => {{
                    btn.classList.remove('active-range');
                }});
            }}
            
            if (event && event.currentTarget) {{
                event.currentTarget.classList.add('active-range');
            }}
            
            const origData = dailyChartData[projId];
            if (!origData) return;
            
            let filteredDates = [...origData.dates];
            if (days !== 'all') {{
                const numDays = parseInt(days, 10);
                filteredDates = filteredDates.slice(-numDays);
            }}
            
            const startInput = document.getElementById(`date-start-${{projId}}`);
            const endInput = document.getElementById(`date-end-${{projId}}`);
            if (startInput && endInput) {{
                startInput.value = filteredDates[0] || '';
                endInput.value = filteredDates[filteredDates.length - 1] || '';
            }}
            
            updateProjectChartData(projId, filteredDates);
        }}

        function customDateFilter(projId) {{
            const startInput = document.getElementById(`date-start-${{projId}}`);
            const endInput = document.getElementById(`date-end-${{projId}}`);
            if (!startInput || !endInput) return;
            
            const startDate = startInput.value;
            const endDate = endInput.value;
            
            const origData = dailyChartData[projId];
            if (!origData) return;
            
            const accordionItem = document.querySelector(`.accordion-item[data-project-id="${{projId}}"]`);
            if (accordionItem) {{
                accordionItem.querySelectorAll('.range-btn').forEach(btn => {{
                    btn.classList.remove('active-range');
                }});
            }}
            
            const filteredDates = origData.dates.filter(d => {{
                if (startDate && d < startDate) return false;
                if (endDate && d > endDate) return false;
                return true;
            }});
            
            updateProjectChartData(projId, filteredDates);
        }}

        function updateProjectChartData(projId, filteredDates) {{
            const origData = dailyChartData[projId];
            if (!origData) return;
            
            const dateIndices = filteredDates.map(d => origData.dates.indexOf(d)).filter(idx => idx !== -1);
            
            const filterDataset = (origDatasets) => {{
                return origDatasets.map(dataset => {{
                    const filteredData = dateIndices.map(idx => dataset.data[idx]);
                    return {{
                        label: dataset.label,
                        data: filteredData
                    }};
                }});
            }};
            
            const sChart = renderedCharts[projId + '_service'];
            if (sChart) {{
                if (typeof sChart.resetZoom === 'function') {{
                    sChart.resetZoom('none');
                }}
                sChart.data.labels = filteredDates;
                const newDatasets = filterDataset(origData.services);
                sChart.data.datasets.forEach((ds, dIdx) => {{
                    if (newDatasets[dIdx]) {{
                        ds.data = newDatasets[dIdx].data;
                    }}
                }});
                sChart.update();
            }}
            
            const skuChart = renderedCharts[projId + '_sku'];
            if (skuChart) {{
                if (typeof skuChart.resetZoom === 'function') {{
                    skuChart.resetZoom('none');
                }}
                skuChart.data.labels = filteredDates;
                const newDatasets = filterDataset(origData.skus);
                skuChart.data.datasets.forEach((ds, dIdx) => {{
                    if (newDatasets[dIdx]) {{
                        ds.data = newDatasets[dIdx].data;
                    }}
                }});
                skuChart.update();
            }}
        }}

        let isSyncingZoom = false;
        function syncDateFiltersFromChart(projId, chart) {{
            if (isSyncingZoom) return;
            isSyncingZoom = true;
            
            try {{
                const xAxis = chart.scales.x;
                if (!xAxis) return;
                
                const minIdx = Math.max(0, Math.round(xAxis.min));
                const maxIdx = Math.min(chart.data.labels.length - 1, Math.round(xAxis.max));
                const startDate = chart.data.labels[minIdx];
                const endDate = chart.data.labels[maxIdx];
                
                const startInput = document.getElementById(`date-start-${{projId}}`);
                const endInput = document.getElementById(`date-end-${{projId}}`);
                if (startInput && endInput) {{
                    startInput.value = startDate || '';
                    endInput.value = endDate || '';
                }}
                
                const accordionItem = document.querySelector(`.accordion-item[data-project-id="${{projId}}"]`);
                if (accordionItem) {{
                    accordionItem.querySelectorAll('.range-btn').forEach(btn => {{
                        btn.classList.remove('active-range');
                    }});
                }}

                // Sync the other daily chart zoom to match!
                const isService = chart.canvas.id.includes('service');
                const otherChartKey = projId + (isService ? '_sku' : '_service');
                const otherChart = renderedCharts[otherChartKey];
                if (otherChart && otherChart.scales.x) {{
                    otherChart.scales.x.options.min = xAxis.min;
                    otherChart.scales.x.options.max = xAxis.max;
                    otherChart.update('none');
                }}
            }} finally {{
                isSyncingZoom = false;
            }}
        }}

        function initProjectCharts(projId) {{
            if (renderedCharts[projId]) return;
            const data = dailyChartData[projId];
            if (!data) return;
            
            // Service Daily
            const sCanvas = document.getElementById(`service-daily-chart-${{projId}}`);
            if (sCanvas) {{
                const ctx = sCanvas.getContext('2d');
                renderedCharts[projId + '_service'] = new Chart(ctx, {{
                    type: 'line',
                    data: {{
                        labels: data.dates,
                        datasets: data.services.map((s, idx) => ({{
                            label: s.label,
                            data: s.data,
                            borderColor: getChartColor(idx),
                            backgroundColor: getChartColor(idx, 0.05),
                            borderWidth: 2,
                            pointRadius: 1.5,
                            pointHoverRadius: 5,
                            fill: true,
                            tension: 0.3
                        }}))
                    }},
                    options: {{
                        responsive: true,
                        maintainAspectRatio: false,
                        plugins: {{
                            legend: {{
                                position: 'top',
                                labels: {{ color: '#5f6368', font: {{ family: 'Inter', size: 10 }} }}
                            }},
                            tooltip: {{
                                mode: 'index',
                                intersect: false
                            }},
                            zoom: {{
                                zoom: {{
                                    drag: {{
                                        enabled: true,
                                        backgroundColor: 'rgba(99, 102, 241, 0.15)',
                                        borderColor: 'rgba(99, 102, 241, 0.4)',
                                        borderWidth: 1,
                                        threshold: 3
                                    }},
                                    mode: 'x',
                                    onZoomComplete: function({{chart}}) {{
                                        syncDateFiltersFromChart(projId, chart);
                                    }}
                                }}
                            }}
                        }},
                        scales: {{
                            x: {{ grid: {{ color: 'rgba(60, 64, 67, 0.10)' }}, ticks: {{ color: '#5f6368', font: {{ family: 'Inter', size: 9 }} }} }},
                            y: {{ grid: {{ color: 'rgba(60, 64, 67, 0.10)' }}, ticks: {{ color: '#5f6368', font: {{ family: 'JetBrains Mono', size: 9 }} }} }}
                        }}
                    }}
                }});
                
                sCanvas.addEventListener('dblclick', () => {{
                    filterChartRange(projId, 'all');
                }});
            }}
            
            // SKU Daily
            const skuCanvas = document.getElementById(`sku-daily-chart-${{projId}}`);
            if (skuCanvas) {{
                const ctx = skuCanvas.getContext('2d');
                renderedCharts[projId + '_sku'] = new Chart(ctx, {{
                    type: 'line',
                    data: {{
                        labels: data.dates,
                        datasets: data.skus.map((s, idx) => ({{
                            label: s.label,
                            data: s.data,
                            borderColor: getChartColor(idx + 3),
                            backgroundColor: getChartColor(idx + 3, 0.05),
                            borderWidth: 2,
                            pointRadius: 1.5,
                            pointHoverRadius: 5,
                            fill: true,
                            tension: 0.3
                        }}))
                    }},
                    options: {{
                        responsive: true,
                        maintainAspectRatio: false,
                        plugins: {{
                            legend: {{
                                position: 'top',
                                labels: {{ color: '#5f6368', font: {{ family: 'Inter', size: 10 }} }}
                            }},
                            tooltip: {{
                                mode: 'index',
                                intersect: false
                            }},
                            zoom: {{
                                zoom: {{
                                    drag: {{
                                        enabled: true,
                                        backgroundColor: 'rgba(99, 102, 241, 0.15)',
                                        borderColor: 'rgba(99, 102, 241, 0.4)',
                                        borderWidth: 1,
                                        threshold: 3
                                    }},
                                    mode: 'x',
                                    onZoomComplete: function({{chart}}) {{
                                        syncDateFiltersFromChart(projId, chart);
                                    }}
                                }}
                            }}
                        }},
                        scales: {{
                            x: {{ grid: {{ color: 'rgba(60, 64, 67, 0.10)' }}, ticks: {{ color: '#5f6368', font: {{ family: 'Inter', size: 9 }} }} }},
                            y: {{ grid: {{ color: 'rgba(60, 64, 67, 0.10)' }}, ticks: {{ color: '#5f6368', font: {{ family: 'JetBrains Mono', size: 9 }} }} }}
                        }}
                    }}
                }});
                
                skuCanvas.addEventListener('dblclick', () => {{
                    filterChartRange(projId, 'all');
                }});
            }}
            
            // Pre-populate date inputs limits and defaults
            const startInput = document.getElementById(`date-start-${{projId}}`);
            const endInput = document.getElementById(`date-end-${{projId}}`);
            if (startInput && endInput && data.dates.length > 0) {{
                const minDate = data.dates[0];
                const maxDate = data.dates[data.dates.length - 1];
                
                startInput.min = minDate;
                startInput.max = maxDate;
                startInput.value = minDate;
                
                endInput.min = minDate;
                endInput.max = maxDate;
                endInput.value = maxDate;
            }}
            
            renderedCharts[projId] = true;
        }}

        // Accordion Trigger Logic
        function toggleAccordion(element) {{
            const item = element.parentElement;
            const isActive = item.classList.contains('active');
            
            // Close all active first
            document.querySelectorAll('.accordion-item').forEach(el => {{
                el.classList.remove('active');
            }});

            if (!isActive) {{
                item.classList.add('active');
                const projId = item.getAttribute('data-project-id');
                if (projId) {{
                    initProjectCharts(projId);
                }}
            }}
        }}

        // ===== Tabbed views =====
        function switchView(view) {{
            document.querySelectorAll('.tab-view').forEach(function(s) {{ s.classList.remove('active'); }});
            var target = document.getElementById('view-' + view);
            if (target) target.classList.add('active');
            document.querySelectorAll('.nav-item').forEach(function(b) {{
                b.classList.toggle('active', b.getAttribute('data-view') === view);
            }});
            if (view === 'tracker') {{
                if (!window.__trackerInit) {{ window.__trackerInit = true; initTracker(); }}
                else if (window.trackerChart) {{ window.trackerChart.resize(); }}
            }}
            if (history.replaceState) history.replaceState(null, '', '#' + view);
            window.scrollTo(0, 0);
        }}

        // ===== Spending tracker (derived from dailyChartData) =====
        var trackerFull = null;
        function trackerProjects() {{ return Object.keys(dailyChartData); }}
        function trackerDatesAll() {{
            var keys = trackerProjects();
            if (!keys.length) return [];
            return dailyChartData[keys[0]].dates || [];
        }}
        function buildTotals(projId) {{
            var keys = (projId && projId !== '__all__') ? [projId] : trackerProjects();
            var dates = trackerDatesAll();
            var totals = new Array(dates.length).fill(0);
            keys.forEach(function(k) {{
                var proj = dailyChartData[k];
                if (!proj || !proj.services) return;
                proj.services.forEach(function(ds) {{
                    (ds.data || []).forEach(function(v, i) {{ totals[i] += (v || 0); }});
                }});
            }});
            return {{ dates: dates, totals: totals }};
        }}
        function movingAvg(arr, win) {{
            var out = [];
            for (var i = 0; i < arr.length; i++) {{
                var s = 0, c = 0;
                for (var j = Math.max(0, i - win + 1); j <= i; j++) {{ s += arr[j]; c++; }}
                out.push(c ? s / c : 0);
            }}
            return out;
        }}
        function fmtMoney(v) {{
            return '$' + Number(v).toLocaleString(undefined, {{ minimumFractionDigits: 2, maximumFractionDigits: 2 }});
        }}
        function populateProjectSelects() {{
            var projects = trackerProjects();
            ['trackerProject', 'skuProject'].forEach(function(id) {{
                var sel = document.getElementById(id);
                if (!sel) return;
                projects.forEach(function(p) {{
                    var o = document.createElement('option');
                    o.value = p; o.textContent = p; sel.appendChild(o);
                }});
            }});
        }}
        function initTracker() {{
            trackerFull = buildTotals('__all__');
            var ctx = document.getElementById('trackerChart');
            if (!ctx || typeof Chart === 'undefined') return;
            window.trackerChart = new Chart(ctx, {{
                type: 'line',
                data: {{
                    labels: trackerFull.dates,
                    datasets: [
                        {{ label: 'Daily net cost', data: trackerFull.totals, borderColor: '#1a73e8',
                          backgroundColor: 'rgba(26, 115, 232, 0.12)', fill: true, tension: 0.35,
                          pointRadius: 0, borderWidth: 2 }},
                        {{ label: '7-day average', data: movingAvg(trackerFull.totals, 7), borderColor: '#f9ab00',
                          backgroundColor: 'transparent', fill: false, tension: 0.35, pointRadius: 0,
                          borderWidth: 2, borderDash: [6, 4] }}
                    ]
                }},
                options: {{
                    responsive: true, maintainAspectRatio: false,
                    interaction: {{ mode: 'index', intersect: false }},
                    plugins: {{
                        legend: {{ labels: {{ color: '#5f6368', font: {{ family: 'Inter', size: 11 }}, usePointStyle: true }} }},
                        zoom: {{ zoom: {{ drag: {{ enabled: true, backgroundColor: 'rgba(26,115,232,0.15)' }}, mode: 'x',
                                onZoomComplete: function(c) {{ syncTrackerZoom(c.chart); }} }} }}
                    }},
                    scales: {{
                        x: {{ grid: {{ color: 'rgba(60, 64, 67, 0.10)' }}, ticks: {{ color: '#5f6368', font: {{ family: 'Inter', size: 9 }}, maxTicksLimit: 12 }} }},
                        y: {{ grid: {{ color: 'rgba(60, 64, 67, 0.10)' }}, ticks: {{ color: '#5f6368', font: {{ family: 'JetBrains Mono', size: 9 }},
                             callback: function(v) {{ return '$' + Number(v).toLocaleString(); }} }} }}
                    }}
                }}
            }});
            ctx.addEventListener('dblclick', function() {{ if (window.trackerChart) window.trackerChart.resetZoom(); }});
            renderTrackerStats(trackerFull.dates, trackerFull.totals);
            renderTopMovers('__all__');
        }}
        function refreshTrackerChart(slice) {{
            if (!window.trackerChart) return;
            window.trackerChart.data.labels = slice.dates;
            window.trackerChart.data.datasets[0].data = slice.totals;
            window.trackerChart.data.datasets[1].data = movingAvg(slice.totals, 7);
            window.trackerChart.resetZoom('none');
            window.trackerChart.update();
            renderTrackerStats(slice.dates, slice.totals);
        }}
        function currentTrackerSlice() {{
            var all = trackerFull;
            var s = document.getElementById('trackerStart').value;
            var e = document.getElementById('trackerEnd').value;
            if (!s || !e) return all;
            var d = [], t = [];
            all.dates.forEach(function(dt, i) {{ if (dt >= s && dt <= e) {{ d.push(dt); t.push(all.totals[i]); }} }});
            return {{ dates: d, totals: t }};
        }}
        function updateTracker() {{
            var proj = document.getElementById('trackerProject').value;
            trackerFull = buildTotals(proj);
            document.getElementById('trackerStart').value = '';
            document.getElementById('trackerEnd').value = '';
            document.querySelectorAll('#view-tracker .range-btn').forEach(function(b) {{ b.classList.remove('active-range'); }});
            refreshTrackerChart(trackerFull);
            renderTopMovers(proj);
        }}
        function trackerRange(days, btn) {{
            document.querySelectorAll('#view-tracker .range-btn').forEach(function(b) {{ b.classList.remove('active-range'); }});
            if (btn) btn.classList.add('active-range');
            var all = trackerFull;
            var slice = all;
            if (days && all.dates.length > days) {{
                slice = {{ dates: all.dates.slice(-days), totals: all.totals.slice(-days) }};
            }}
            if (slice.dates.length) {{
                document.getElementById('trackerStart').value = slice.dates[0];
                document.getElementById('trackerEnd').value = slice.dates[slice.dates.length - 1];
            }}
            refreshTrackerChart(slice);
        }}
        function trackerCustom() {{
            document.querySelectorAll('#view-tracker .range-btn').forEach(function(b) {{ b.classList.remove('active-range'); }});
            refreshTrackerChart(currentTrackerSlice());
        }}
        function syncTrackerZoom(chart) {{
            var xs = chart.scales.x;
            var labels = chart.data.labels;
            var lo = Math.max(0, Math.ceil(xs.min));
            var hi = Math.min(labels.length - 1, Math.floor(xs.max));
            if (labels[lo]) document.getElementById('trackerStart').value = labels[lo];
            if (labels[hi]) document.getElementById('trackerEnd').value = labels[hi];
        }}
        function renderTrackerStats(dates, totals) {{
            var el = document.getElementById('trackerStats');
            if (!el) return;
            var sum = totals.reduce(function(a, b) {{ return a + b; }}, 0);
            var active = totals.filter(function(v) {{ return v > 0; }}).length;
            var avg = active ? sum / active : 0;
            var peak = 0, peakIdx = -1;
            totals.forEach(function(v, i) {{ if (v > peak) {{ peak = v; peakIdx = i; }} }});
            var peakDate = peakIdx >= 0 ? dates[peakIdx] : '\u2014';
            var cards = [
                ['Total (range)', fmtMoney(sum), dates.length + ' days'],
                ['Daily average', fmtMoney(avg), active + ' active days'],
                ['Peak day', fmtMoney(peak), peakDate],
                ['Run-rate / 30d', fmtMoney(avg * 30), 'avg x 30 days']
            ];
            el.innerHTML = cards.map(function(c) {{
                return '<div class="stat-card"><div class="summary-label">' + c[0] + '</div>' +
                       '<div class="summary-value">' + c[1] + '</div>' +
                       '<div class="summary-sub">' + c[2] + '</div></div>';
            }}).join('');
        }}
        function renderTopMovers(projId) {{
            var el = document.getElementById('moversList');
            if (!el) return;
            var keys = (projId && projId !== '__all__') ? [projId] : trackerProjects();
            var agg = {{}};
            keys.forEach(function(k) {{
                var proj = dailyChartData[k];
                if (!proj || !proj.services) return;
                var n = (proj.dates || []).length;
                proj.services.forEach(function(ds) {{
                    var data = ds.data || [];
                    var recent = 0, prior = 0, i;
                    for (i = Math.max(0, n - 7); i < n; i++) recent += (data[i] || 0);
                    for (i = Math.max(0, n - 14); i < n - 7; i++) prior += (data[i] || 0);
                    if (!agg[ds.label]) agg[ds.label] = {{ recent: 0, prior: 0 }};
                    agg[ds.label].recent += recent;
                    agg[ds.label].prior += prior;
                }});
            }});
            var rows = Object.keys(agg).map(function(name) {{
                return {{ name: name, delta: agg[name].recent - agg[name].prior }};
            }}).filter(function(r) {{ return Math.abs(r.delta) > 0.005; }});
            rows.sort(function(a, b) {{ return Math.abs(b.delta) - Math.abs(a.delta); }});
            var top = rows.slice(0, 6);
            if (!top.length) {{ el.innerHTML = '<div style="color: var(--text-muted); font-size: 0.85rem;">Not enough history for movers.</div>'; return; }}
            el.innerHTML = top.map(function(r) {{
                var up = r.delta > 0;
                var cls = up ? 'delta-up' : 'delta-down';
                var sign = up ? '\u25b2 +' : '\u25bc -';
                return '<div class="mover-row"><span class="mover-name">' + r.name + '</span>' +
                       '<span class="mover-delta ' + cls + '">' + sign + fmtMoney(Math.abs(r.delta)).slice(1) + '</span></div>';
            }}).join('');
        }}

        // ===== Period summary band (Overview) =====
        function renderSummaryBand() {{
            var keys = Object.keys(dailyChartData);
            if (!keys.length) return;
            var dates = dailyChartData[keys[0]].dates || [];
            if (!dates.length) return;
            var lastDate = dates[dates.length - 1];
            var ym = lastDate.slice(0, 7);
            var totals = buildTotals('__all__').totals;
            var monthSum = 0, activeDays = 0, firstD = null, lastD = null;
            dates.forEach(function(dt, i) {{
                if (dt.slice(0, 7) === ym) {{
                    monthSum += totals[i];
                    if (totals[i] > 0) {{ activeDays++; if (!firstD) firstD = dt; lastD = dt; }}
                }}
            }});
            var dim = new Date(parseInt(ym.slice(0, 4)), parseInt(ym.slice(5, 7)), 0).getDate();
            var avg = activeDays ? monthSum / activeDays : 0;
            var projected = avg * dim;
            function setT(id, v) {{ var e = document.getElementById(id); if (e) e.textContent = v; }}
            var monthName = new Date(ym + '-01T00:00:00').toLocaleDateString(undefined, {{ month: 'long', year: 'numeric' }});
            setT('sumPeriod', monthName);
            setT('sumRange', (firstD || dates[0]) + '  to  ' + (lastD || lastDate));
            setT('sumDays', activeDays + ' / ' + dim);
            setT('sumAvg', fmtMoney(avg));
            setT('sumProjected', fmtMoney(projected));
            if (typeof trendCosts !== 'undefined' && trendCosts.length >= 2) {{
                var cur = trendCosts[trendCosts.length - 1];
                var prev = trendCosts[trendCosts.length - 2];
                var e2 = document.getElementById('sumMoM');
                if (prev > 0 && e2) {{
                    var pct = ((cur - prev) / prev) * 100;
                    var up = pct >= 0;
                    e2.textContent = (up ? '+' : '') + pct.toFixed(1) + '%';
                    e2.className = 'summary-value ' + (up ? 'delta-up' : 'delta-down');
                    setT('sumMoMSub', 'vs ' + (trendLabels[trendLabels.length - 2] || 'previous'));
                }}
            }}
            var projSub = document.getElementById('sumProjectedSub');
            if (projSub && activeDays >= dim) projSub.textContent = 'month complete (actual)';
        }}

        // ===== Filters =====
        function filterSkuTable() {{
            var projSel = document.getElementById('skuProject');
            var proj = projSel ? projSel.value : '__all__';
            var sInput = document.getElementById('skuSearch');
            var q = (sInput ? sInput.value : '').toLowerCase();
            var rows = document.querySelectorAll('#view-services tbody tr');
            rows.forEach(function(tr) {{
                var cells = tr.querySelectorAll('td');
                var projId = cells.length ? cells[0].textContent.trim() : '';
                var text = tr.textContent.toLowerCase();
                var okProj = (proj === '__all__') || (projId === proj);
                var okText = !q || text.indexOf(q) !== -1;
                tr.style.display = (okProj && okText) ? '' : 'none';
            }});
        }}
        function filterProjects() {{
            var sInput = document.getElementById('projectSearch');
            var q = (sInput ? sInput.value : '').toLowerCase();
            document.querySelectorAll('#view-projects .accordion-item').forEach(function(item) {{
                var text = item.textContent.toLowerCase();
                item.style.display = (!q || text.indexOf(q) !== -1) ? '' : 'none';
            }});
        }}

        // ===== Init on load =====
        document.addEventListener('DOMContentLoaded', function() {{
            populateProjectSelects();
            renderSummaryBand();
            var hash = (location.hash || '').replace('#', '');
            if (hash && document.getElementById('view-' + hash)) switchView(hash);
        }});

    </script>
</body>
</html>
"""

def run_bq_query(client, sql_query):
    try:
        print(f"Executing query in BigQuery...")
        query_job = client.query(sql_query)
        results = query_job.result()
        
        rows = []
        for row in results:
            row_dict = {}
            for key, val in row.items():
                # Check for decimal numbers or date objects to format them correctly for JSON serializability
                if hasattr(val, 'to_eng_string') or type(val).__name__ == 'Decimal':
                    row_dict[key] = float(val)
                elif type(val).__name__ == 'date':
                    row_dict[key] = val.strftime("%Y-%m-%d")
                elif val is None:
                    row_dict[key] = 0.0 if key in ['total_cost', 'total_credits', 'net_cost', 'cost'] else ""
                else:
                    row_dict[key] = val
            rows.append(row_dict)
        return rows
    except Exception as e:
        print(f"Error querying BigQuery: {str(e)}", file=sys.stderr)
        return []

def verify_bigquery_access(client, project_id, dataset_name="billing_exports"):
    """
    Verifies that the BigQuery client has the necessary permissions to read the dataset
    and execute query jobs.
    """
    print("🔍 Performing automatic BigQuery access & IAM permissions verification...")
    try:
        dataset_ref = client.dataset(dataset_name, project=project_id)
        client.get_dataset(dataset_ref)
        print(f"✅ Successfully accessed BigQuery dataset '{project_id}.{dataset_name}'.")
    except Exception as e:
        print(f"❌ Error: Access denied or dataset not found at '{project_id}.{dataset_name}'!", file=sys.stderr)
        print("💡 Check your IAM permissions: You need the 'roles/bigquery.dataViewer' role on the dataset or billing project.", file=sys.stderr)
        print(f"Details: {str(e)}\n", file=sys.stderr)
        return False

    try:
        print("🔍 Testing BigQuery query execution capability (roles/bigquery.jobUser)...")
        query_job = client.query("SELECT 1")
        query_job.result()
        print("✅ BigQuery query execution test passed successfully.")
    except Exception as e:
        print("\n❌ Error: Failed to execute a test query in BigQuery!", file=sys.stderr)
        print("💡 Check your IAM permissions: You need the 'roles/bigquery.jobUser' role on the project running queries.", file=sys.stderr)
        print(f"Details: {str(e)}\n", file=sys.stderr)
        return False

    print("🚀 All BigQuery access and IAM permission checks passed successfully!\n")
    return True

def generate_dashboard_html(user_email="user@example.com"):
    print("🚀 Starting GCP cost breakdown & visualization generator...")
    
    # Configure environment variables
    project_id = os.getenv("GCP_PROJECT", "your-gcp-project-id")
    config_name = os.getenv("GCP_CONFIG_NAME", "default")
    dataset_name = os.getenv("GCP_DATASET", "billing_exports")

    print(f"📍 Billing Project: {project_id}")
    print(f"📍 Config Name: {config_name}")
    print(f"📍 Billing Dataset: {dataset_name}")
    
    # Initialize BigQuery client
    client = bigquery.Client(project=project_id)
    
    # Run automatic IAM permissions check
    if not verify_bigquery_access(client, project_id, dataset_name):
        raise Exception("Prerequisite check failed. Aborting cost analysis.")

    # Discover table names in the billing export dataset
    tables_query = f"""
    SELECT table_name
    FROM `{project_id}.{dataset_name}.INFORMATION_SCHEMA.TABLES`
    WHERE table_name LIKE 'gcp_billing_export_v1_%'
       OR table_name LIKE 'gcp_billing_export_resource_v1_%'
    """
    tables = run_bq_query(client, tables_query)
    
    standard_table = None
    resource_table = None
    
    for t in tables:
        name = t['table_name']
        if name.startswith('gcp_billing_export_resource_v1_'):
            resource_table = f"{project_id}.{dataset_name}.{name}"
        elif name.startswith('gcp_billing_export_v1_'):
            standard_table = f"{project_id}.{dataset_name}.{name}"

    if not standard_table and not resource_table:
        raise Exception(f"Error: No billing export tables found in dataset `{project_id}.{dataset_name}`!")

    if not standard_table:
        print("⚠️ Warning: Standard billing export table not found. Using resource-level table for aggregate queries.")
        standard_table = resource_table

    if not resource_table:
        print("⚠️ Warning: Resource-level billing export table not found. Defaulting to standard table for resources.")
        resource_table = standard_table
        
    print(f"✅ Standard Export Table: {standard_table}")
    print(f"✅ Resource Export Table: {resource_table}")
    
    # Dynamically determine the most recent month with invoice billing data
    latest_month_query = f"SELECT DISTINCT invoice.month FROM `{standard_table}` ORDER BY invoice.month DESC LIMIT 1"
    latest_month_data = run_bq_query(client, latest_month_query)
    
    if latest_month_data:
        current_month = latest_month_data[0]['month']
        parsed_date = datetime.strptime(current_month, "%Y%m")
        current_month_formatted = parsed_date.strftime("%B %Y")
    else:
        # No invoice data found: fall back to the previous calendar month.
        today = datetime.now()
        parsed_date = (today.replace(day=1) - timedelta(days=1))
        current_month = parsed_date.strftime("%Y%m")
        current_month_formatted = parsed_date.strftime("%B %Y")
        
    print(f"📊 Querying billing data for: {current_month_formatted} ({current_month})...")
    
    # Query 1: Monthly Trends (last 6 months)
    trend_query = f"""
    SELECT
      invoice.month as invoice_month,
      SUM(cost) as total_cost,
      SUM((SELECT COALESCE(SUM(c.amount), 0) FROM UNNEST(credits) c)) as total_credits,
      SUM(cost + (SELECT COALESCE(SUM(c.amount), 0) FROM UNNEST(credits) c)) as net_cost
    FROM `{standard_table}`
    GROUP BY 1
    ORDER BY 1 ASC
    """
    trend_data = run_bq_query(client, trend_query)
    
    # Query 2: Project Breakdown
    project_query = f"""
    SELECT
      COALESCE(project.id, 'Non-project / Shared') as project_id,
      COALESCE(project.name, 'Non-project / Shared') as project_name,
      SUM(cost) as total_cost,
      SUM((SELECT COALESCE(SUM(c.amount), 0) FROM UNNEST(credits) c)) as total_credits,
      SUM(cost + (SELECT COALESCE(SUM(c.amount), 0) FROM UNNEST(credits) c)) as net_cost
    FROM `{standard_table}`
    WHERE invoice.month = '{current_month}'
    GROUP BY 1, 2
    ORDER BY net_cost DESC
    """
    project_data = run_bq_query(client, project_query)
    
    # Query 3: Service Breakdown
    service_query = f"""
    SELECT
      service.description as service_description,
      SUM(cost) as total_cost,
      SUM((SELECT COALESCE(SUM(c.amount), 0) FROM UNNEST(credits) c)) as total_credits,
      SUM(cost + (SELECT COALESCE(SUM(c.amount), 0) FROM UNNEST(credits) c)) as net_cost
    FROM `{standard_table}`
    WHERE invoice.month = '{current_month}'
    GROUP BY 1
    ORDER BY net_cost DESC
    """
    service_data = run_bq_query(client, service_query)
    
    # Query 4: Project and Service Detailed Grid
    proj_service_query = f"""
    SELECT
      COALESCE(project.id, 'Non-project / Shared') as project_id,
      service.description as service_description,
      SUM(cost) as total_cost,
      SUM((SELECT COALESCE(SUM(c.amount), 0) FROM UNNEST(credits) c)) as total_credits,
      SUM(cost + (SELECT COALESCE(SUM(c.amount), 0) FROM UNNEST(credits) c)) as net_cost
    FROM `{standard_table}`
    WHERE invoice.month = '{current_month}'
    GROUP BY 1, 2
    ORDER BY net_cost DESC
    """
    proj_service_data = run_bq_query(client, proj_service_query)
    
    # Query 5: Top SKUs
    sku_query = f"""
    SELECT
      COALESCE(project.id, 'Non-project / Shared') as project_id,
      service.description as service_description,
      sku.description as sku_description,
      SUM(cost) as total_cost,
      SUM((SELECT COALESCE(SUM(c.amount), 0) FROM UNNEST(credits) c)) as total_credits,
      SUM(cost + (SELECT COALESCE(SUM(c.amount), 0) FROM UNNEST(credits) c)) as net_cost
    FROM `{standard_table}`
    WHERE invoice.month = '{current_month}'
    GROUP BY 1, 2, 3
    ORDER BY net_cost DESC
    """
    sku_data = run_bq_query(client, sku_query)
    
    # Query 6: Named Resources (with specific names)
    # Using dynamic dates derived from month to capture correct window
    start_date_str = f"{current_month[:4]}-{current_month[4:6]}-01"
    if current_month[4:6] == "12":
        end_date_str = f"{int(current_month[:4])+1}-01-01"
    else:
        end_date_str = f"{current_month[:4]}-{int(current_month[4:6])+1:02d}-01"
        
    resource_query = f"""
    SELECT
      COALESCE(project.id, 'Non-project / Shared') as project_id,
      service.description as service_description,
      sku.description as sku_description,
      resource.name as resource_name,
      SUM(cost) as total_cost,
      SUM(cost + (SELECT COALESCE(SUM(c.amount), 0) FROM UNNEST(credits) c)) as net_cost
    FROM `{resource_table}`
    WHERE invoice.month = '{current_month}' AND resource.name IS NOT NULL AND resource.name != ''
    GROUP BY 1, 2, 3, 4
    HAVING net_cost > 0.01
    ORDER BY net_cost DESC
    LIMIT 200
    """
    resource_data = run_bq_query(client, resource_query)
    
    # Query 7: Daily Service Cost (past 60 days)
    # Dynamically calculate date range
    end_dt_parsed = parsed_date
    import datetime as dt_mod
    # set end date to last day of target month
    if end_dt_parsed.month == 12:
        next_month_start = dt_mod.date(end_dt_parsed.year + 1, 1, 1)
    else:
        next_month_start = dt_mod.date(end_dt_parsed.year, end_dt_parsed.month + 1, 1)
    end_date_obj = next_month_start - dt_mod.timedelta(days=1)
    start_date_obj = end_date_obj - dt_mod.timedelta(days=60)
    
    start_date_iso = start_date_obj.strftime("%Y-%m-%d")
    end_date_iso = end_date_obj.strftime("%Y-%m-%d")
    
    print(f"📊 Querying daily service costs from {start_date_iso} to {end_date_iso}...")
    daily_service_query = f"""
    SELECT
      COALESCE(project.id, 'Non-project / Shared') as project_id,
      service.description as service_description,
      EXTRACT(DATE FROM usage_start_time) as usage_date,
      SUM(cost + (SELECT COALESCE(SUM(c.amount), 0) FROM UNNEST(credits) c)) as net_cost
    FROM `{standard_table}`
    WHERE usage_start_time >= TIMESTAMP('{start_date_iso} 00:00:00')
      AND usage_start_time <= TIMESTAMP('{end_date_iso} 23:59:59')
    GROUP BY 1, 2, 3
    ORDER BY usage_date ASC
    """
    daily_service_data = run_bq_query(client, daily_service_query)
    
    # Query 8: Daily SKU Cost (past 60 days)
    print(f"📊 Querying daily SKU costs from {start_date_iso} to {end_date_iso}...")
    daily_sku_query = f"""
    SELECT
      COALESCE(project.id, 'Non-project / Shared') as project_id,
      sku.description as sku_description,
      EXTRACT(DATE FROM usage_start_time) as usage_date,
      SUM(cost + (SELECT COALESCE(SUM(c.amount), 0) FROM UNNEST(credits) c)) as net_cost
    FROM `{standard_table}`
    WHERE usage_start_time >= TIMESTAMP('{start_date_iso} 00:00:00')
      AND usage_start_time <= TIMESTAMP('{end_date_iso} 23:59:59')
    GROUP BY 1, 2, 3
    ORDER BY usage_date ASC
    """
    daily_sku_data = run_bq_query(client, daily_sku_query)
    
    print("📈 Data gathered successfully. Processing metrics...")
    
    # Calculate main metrics
    current_trend = [t for t in trend_data if t['invoice_month'] == current_month]
    if current_trend:
        gross_cost = current_trend[0]['total_cost']
        credits = current_trend[0]['total_credits']
        net_cost = current_trend[0]['net_cost']
    else:
        gross_cost = sum(p['total_cost'] for p in project_data)
        credits = sum(p['total_credits'] for p in project_data)
        net_cost = sum(p['net_cost'] for p in project_data)
        
    # Get values for specific highlighted components
    embedding_cost = 0.0
    bq_res_cost = 0.0
    for s in sku_data:
        if s['sku_description'] == 'Embedding for Text - Batch Predictions':
            embedding_cost += s['net_cost']
        if 'BigQuery Enterprise Edition' in s['sku_description']:
            bq_res_cost += s['net_cost']
            
    embedding_pct = (embedding_cost / net_cost * 100) if net_cost > 0 else 0
    
    # Generate Project & Service arrays for JS
    top_projects = project_data[:10]
    other_projects_cost = sum(p['net_cost'] for p in project_data[10:])
    project_labels = [p['project_id'] for p in top_projects]
    project_costs = [p['net_cost'] for p in top_projects]
    if other_projects_cost > 0:
        project_labels.append("Other Projects")
        project_costs.append(other_projects_cost)
        
    top_services = service_data[:10]
    other_services_cost = sum(s['net_cost'] for s in service_data[10:])
    service_labels = [s['service_description'] for s in top_services]
    service_costs = [s['net_cost'] for s in top_services]
    if other_services_cost > 0:
        service_labels.append("Other Services")
        service_costs.append(other_services_cost)
        
    trend_labels = [datetime.strptime(t['invoice_month'], "%Y%m").strftime("%b %Y") for t in trend_data]
    trend_costs = [t['net_cost'] for t in trend_data]
    
    # Build Top 25 SKU Table HTML
    sku_table_rows = []
    for s in sku_data[:25]:
        share = (s['net_cost'] / net_cost * 100) if net_cost > 0 else 0
        sku_table_rows.append(f"""
        <tr>
            <td class="mono-text">{s['project_id']}</td>
            <td><span class="pill pill-primary">{s['service_description']}</span></td>
            <td>{s['sku_description']}</td>
            <td class="num-col">${s['net_cost']:,.2f}</td>
            <td class="num-col">
                <span class="pct-bar-bg"><span class="pct-bar-fill" style="width: {share:.1f}%;"></span></span>
                {share:.1f}%
            </td>
        </tr>
        """)
        
    # Process Daily Spend Data
    date_list = []
    curr_dt = start_date_obj
    while curr_dt <= end_date_obj:
        date_list.append(curr_dt.strftime("%Y-%m-%d"))
        curr_dt += dt_mod.timedelta(days=1)

    # Structure service daily data: project_id -> service_desc -> date -> cost
    daily_service_map = {}
    for d in daily_service_data:
        p_id = d['project_id']
        s_desc = d['service_description']
        u_date = str(d['usage_date'])
        cost = d['net_cost']
        
        if p_id not in daily_service_map:
            daily_service_map[p_id] = {}
        if s_desc not in daily_service_map[p_id]:
            daily_service_map[p_id][s_desc] = {}
        daily_service_map[p_id][s_desc][u_date] = cost

    # Structure SKU daily data: project_id -> sku_desc -> date -> cost
    daily_sku_map = {}
    for d in daily_sku_data:
        p_id = d['project_id']
        sku_desc = d['sku_description']
        u_date = str(d['usage_date'])
        cost = d['net_cost']
        
        if p_id not in daily_sku_map:
            daily_sku_map[p_id] = {}
        if sku_desc not in daily_sku_map[p_id]:
            daily_sku_map[p_id][sku_desc] = {}
        daily_sku_map[p_id][sku_desc][u_date] = cost

    daily_chart_payload = {}
    peak_daily_spend = {}

    for p in project_data:
        p_id = p['project_id']
        
        # Service Daily
        proj_services = daily_service_map.get(p_id, {})
        s_totals = []
        for s_desc, dates_costs in proj_services.items():
            tot = sum(dates_costs.values())
            s_totals.append((s_desc, tot))
        s_totals.sort(key=lambda x: x[1], reverse=True)
        
        top_5_services = [x[0] for x in s_totals[:5]]
        other_services = [x[0] for x in s_totals[5:]]
        
        service_datasets = []
        for s_desc in top_5_services:
            costs_arr = [proj_services[s_desc].get(d_str, 0.0) for d_str in date_list]
            service_datasets.append({"label": s_desc, "data": costs_arr})
            
        if other_services:
            other_costs = []
            for d_str in date_list:
                other_sum = sum(proj_services[s_desc].get(d_str, 0.0) for s_desc in other_services)
                other_costs.append(other_sum)
            service_datasets.append({"label": "Other Services", "data": other_costs})
            
        # SKU Daily
        proj_skus = daily_sku_map.get(p_id, {})
        sku_tots = []
        for sku_desc, dates_costs in proj_skus.items():
            tot = sum(dates_costs.values())
            sku_tots.append((sku_desc, tot))
        sku_tots.sort(key=lambda x: x[1], reverse=True)
        
        top_5_skus = [x[0] for x in sku_tots[:5]]
        other_skus = [x[0] for x in sku_tots[5:]]
        
        sku_datasets = []
        for sku_desc in top_5_skus:
            costs_arr = [proj_skus[sku_desc].get(d_str, 0.0) for d_str in date_list]
            sku_datasets.append({"label": sku_desc, "data": costs_arr})
            
        if other_skus:
            other_costs = []
            for d_str in date_list:
                other_sum = sum(proj_skus[sku_desc].get(d_str, 0.0) for sku_desc in other_skus)
                other_costs.append(other_sum)
            sku_datasets.append({"label": "Other SKUs", "data": other_costs})
            
        daily_chart_payload[p_id] = {
            "dates": date_list,
            "services": service_datasets,
            "skus": sku_datasets
        }
        
        # Calculate Peak Daily Spend
        daily_totals = {}
        for s in service_datasets:
            for idx, val in enumerate(s['data']):
                d_str = date_list[idx]
                daily_totals[d_str] = daily_totals.get(d_str, 0.0) + val
                
        p_max_val = 0.0
        p_max_date = "-"
        for d_str, val in daily_totals.items():
            if val > p_max_val:
                p_max_val = val
                p_max_date = d_str
        if p_max_val > 0.01:
            peak_daily_spend[p_id] = (p_max_date, p_max_val)

    # Build Project Expandable Accordions
    accordion_items = []
    for i, p in enumerate(project_data[:8]):
        proj_id = p['project_id']
        proj_name = p['project_name']
        proj_cost = p['net_cost']
        proj_share = (proj_cost / net_cost * 100) if net_cost > 0 else 0
        
        # Get services for this project
        p_services = [s for s in proj_service_data if s['project_id'] == proj_id][:5]
        services_rows_html = ""
        for s in p_services:
            s_share = (s['net_cost'] / proj_cost * 100) if proj_cost > 0 else 0
            services_rows_html += f"""
            <div style="display: flex; justify-content: space-between; font-size: 0.85rem; padding: 0.25rem 0;">
                <span style="color: var(--text-muted);">{s['service_description']}</span>
                <span class="mono-text">${s['net_cost']:,.2f} ({s_share:.1f}%)</span>
            </div>
            """
            
        # Get SKUs for this project
        p_skus = [s for s in sku_data if s['project_id'] == proj_id][:5]
        skus_rows_html = ""
        for s in p_skus:
            s_share = (s['net_cost'] / proj_cost * 100) if proj_cost > 0 else 0
            skus_rows_html += f"""
            <div style="display: flex; justify-content: space-between; font-size: 0.85rem; padding: 0.25rem 0;">
                <span style="color: var(--text-muted); text-overflow: ellipsis; overflow: hidden; white-space: nowrap; max-width: 250px;" title="{s['sku_description']}">{s['sku_description']}</span>
                <span class="mono-text">${s['net_cost']:,.2f} ({s_share:.1f}%)</span>
            </div>
            """
            
        # Get specific resources for this project
        p_resources = [r for r in resource_data if r['project_id'] == proj_id][:5]
        resources_html = ""
        if p_resources:
            resources_html = "<div style='margin-top: 1rem; border-top: 1px solid var(--border-color); padding-top: 0.75rem;'><b>Top Named Resources</b>"
            for r in p_resources:
                r_share = (r['net_cost'] / proj_cost * 100) if proj_cost > 0 else 0
                resources_html += f"""
                <div style="display: flex; justify-content: space-between; font-size: 0.8rem; padding: 0.2rem 0; font-family: 'JetBrains Mono', monospace;">
                    <span style="color: var(--accent-green); text-overflow: ellipsis; overflow: hidden; white-space: nowrap; max-width: 400px;" title="{r['resource_name']}">{r['resource_name'].split('/')[-1]}</span>
                    <span style="color: var(--text-muted);">{r['service_description'].split(' ')[0]}</span>
                    <span>${r['net_cost']:,.2f} ({r_share:.1f}%)</span>
                </div>
                """
            resources_html += "</div>"
            
        accordion_items.append(f"""
        <div class="accordion-item" data-project-id="{proj_id}">
            <div class="accordion-trigger" onclick="toggleAccordion(this)">
                <div class="accordion-trigger-left">
                    <span class="project-rank">{i+1}</span>
                    <div>
                        <div class="project-info-title">{proj_name}</div>
                        <div class="project-info-meta">ID: {proj_id}</div>
                    </div>
                </div>
                <div class="accordion-trigger-right">
                    <span class="project-accordion-cost">${proj_cost:,.2f}</span>
                    <span class="pill pill-primary">{proj_share:.1f}% of total</span>
                    <svg class="chevron-icon" viewBox="0 0 24 24" width="24" height="24" fill="currentColor"><path d="M7 10l5 5 5-5H7z"/></svg>
                </div>
            </div>
            <div class="accordion-content">
                <div class="accordion-grid">
                    <div style="border-right: 1px solid var(--border-color); padding-right: 1rem;">
                        <b style="font-size: 0.9rem; display: block; margin-bottom: 0.5rem; color: var(--primary);">Top Contributing Services</b>
                        {services_rows_html}
                    </div>
                    <div>
                        <b style="font-size: 0.9rem; display: block; margin-bottom: 0.5rem; color: var(--primary);">Top Billing SKUs</b>
                        {skus_rows_html}
                    </div>
                </div>
                {resources_html}
                
                <div style="margin-top: 1.5rem; border-top: 1px solid var(--border-color); padding-top: 1.25rem;">
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 1rem; flex-wrap: wrap; gap: 0.75rem;">
                        <b style="font-size: 1rem; color: var(--text-main); display: flex; align-items: center; gap: 0.5rem;">
                            <svg viewBox="0 0 24 24" width="18" height="18" fill="var(--primary)"><path d="M16 6l2.29 2.29-4.88 4.88-4-4L2 16.59 3.41 18l6-6 4 4 6.3-6.29L22 12V6z"/></svg>
                            Daily Spending Snapshot
                        </b>
                        <div style="display: flex; align-items: center; gap: 0.75rem; flex-wrap: wrap;">
                            <!-- Range Presets -->
                            <div style="display: flex; gap: 0.25rem; background: rgba(255,255,255,0.03); padding: 0.15rem; border-radius: 6px; border: 1px solid var(--border-color);">
                                <button class="range-btn" onclick="filterChartRange('{proj_id}', 7)">7D</button>
                                <button class="range-btn" onclick="filterChartRange('{proj_id}', 14)">14D</button>
                                <button class="range-btn" onclick="filterChartRange('{proj_id}', 30)">30D</button>
                                <button class="range-btn active-range" onclick="filterChartRange('{proj_id}', 'all')">All</button>
                            </div>
                            <!-- Custom Date Pickers -->
                            <div class="date-filter-wrapper">
                                <input type="date" id="date-start-{proj_id}" class="date-filter-input" onchange="customDateFilter('{proj_id}')">
                                <span style="color: var(--text-muted); font-size: 0.7rem; font-weight: 600;">to</span>
                                <input type="date" id="date-end-{proj_id}" class="date-filter-input" onchange="customDateFilter('{proj_id}')">
                            </div>
                            <!-- Services / SKUs Tabs -->
                            <div style="display: flex; gap: 0.25rem; background: rgba(255,255,255,0.05); padding: 0.15rem; border-radius: 6px; border: 1px solid var(--border-color);">
                                <button class="tab-btn active" onclick="switchProjTab(event, '{proj_id}', 'service')">Services</button>
                                <button class="tab-btn" onclick="switchProjTab(event, '{proj_id}', 'sku')">SKUs</button>
                            </div>
                        </div>
                    </div>
                    
                    <div id="service-chart-container-{proj_id}" style="height: 250px; position: relative;">
                        <canvas id="service-daily-chart-{proj_id}"></canvas>
                    </div>
                    
                    <div id="sku-chart-container-{proj_id}" style="height: 250px; position: relative; display: none;">
                        <canvas id="sku-daily-chart-{proj_id}"></canvas>
                    </div>
                </div>
            </div>
        </div>
        """)
        
    # Render and return completed HTML page
    return HTML_TEMPLATE.format(
        month_formatted=current_month_formatted,
        config_name=config_name,
        user_email=user_email,
        cached_time=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        net_cost=net_cost,
        gross_cost=gross_cost,
        credits=abs(credits),
        embedding_cost=embedding_cost,
        embedding_pct=embedding_pct,
        bq_res_cost=bq_res_cost,
        project_labels_json=json.dumps(project_labels),
        project_costs_json=json.dumps(project_costs),
        service_labels_json=json.dumps(service_labels),
        service_costs_json=json.dumps(service_costs),
        trend_labels_json=json.dumps(trend_labels),
        trend_costs_json=json.dumps(trend_costs),
        sku_table_rows_html="\n".join(sku_table_rows),
        accordion_items_html="\n".join(accordion_items),
        daily_chart_data_json=json.dumps(daily_chart_payload)
    )

if __name__ == "__main__":
    # Quick local dry-run test
    try:
        html = generate_dashboard_html()
        with open("gcp_cost_dashboard.html", "w") as f:
            f.write(html)
        print("Dry-run completed! HTML successfully generated and saved.")
    except Exception as e:
        print(f"Dry-run failed: {str(e)}")
