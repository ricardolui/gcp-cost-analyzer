#!/usr/bin/env python3
import json
import subprocess
import sys
import os
import argparse
from datetime import datetime

# Define color themes and style assets for HTML report
HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>GCP Cost Analysis Dashboard - {month_formatted}</title>
    <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600&display=swap" rel="stylesheet">
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        :root {{
            --bg-color: #0b0f19;
            --panel-bg: rgba(22, 28, 45, 0.4);
            --border-color: rgba(255, 255, 255, 0.08);
            --primary: #6366f1;
            --primary-glow: rgba(99, 102, 241, 0.15);
            --accent-green: #10b981;
            --accent-green-glow: rgba(16, 185, 129, 0.1);
            --accent-red: #ef4444;
            --accent-red-glow: rgba(239, 68, 68, 0.1);
            --text-main: #f3f4f6;
            --text-muted: #9ca3af;
            --card-header-bg: rgba(30, 41, 59, 0.7);
        }}

        * {{
            box-sizing: border-box;
            margin: 0;
            padding: 0;
        }}

        body {{
            font-family: 'Plus Jakarta Sans', sans-serif;
            background-color: var(--bg-color);
            color: var(--text-main);
            min-height: 100vh;
            background-image: 
                radial-gradient(at 10% 10%, rgba(99, 102, 241, 0.1) 0px, transparent 40%),
                radial-gradient(at 90% 10%, rgba(16, 185, 129, 0.05) 0px, transparent 40%),
                radial-gradient(at 50% 90%, rgba(239, 68, 68, 0.05) 0px, transparent 50%);
            background-attachment: fixed;
            padding: 2.5rem;
        }}

        .container {{
            max-width: 1400px;
            margin: 0 auto;
        }}

        header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 2.5rem;
            border-bottom: 1px solid var(--border-color);
            padding-bottom: 1.5rem;
        }}

        .logo-area {{
            display: flex;
            align-items: center;
            gap: 1rem;
        }}

        .logo-icon {{
            background: linear-gradient(135deg, var(--primary), #818cf8);
            width: 48px;
            height: 48px;
            border-radius: 12px;
            display: flex;
            align-items: center;
            justify-content: center;
            box-shadow: 0 4px 20px var(--primary-glow);
        }}

        .logo-icon svg {{
            fill: white;
            width: 24px;
            height: 24px;
        }}

        .title-group h1 {{
            font-size: 1.75rem;
            font-weight: 800;
            background: linear-gradient(135deg, #ffffff 60%, #cbd5e1);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }}

        .title-group p {{
            color: var(--text-muted);
            font-size: 0.875rem;
            margin-top: 0.25rem;
        }}

        .gcloud-badge {{
            background: rgba(255, 255, 255, 0.05);
            border: 1px solid var(--border-color);
            padding: 0.5rem 1rem;
            border-radius: 20px;
            font-size: 0.85rem;
            display: flex;
            align-items: center;
            gap: 0.5rem;
            font-family: 'JetBrains Mono', monospace;
        }}

        .badge-dot {{
            width: 8px;
            height: 8px;
            background-color: var(--accent-green);
            border-radius: 50%;
            box-shadow: 0 0 10px var(--accent-green);
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
            backdrop-filter: blur(16px);
            border: 1px solid var(--border-color);
            border-radius: 16px;
            padding: 1.5rem;
            position: relative;
            overflow: hidden;
            transition: transform 0.3s ease, border-color 0.3s ease;
        }}

        .metric-card:hover {{
            transform: translateY(-2px);
            border-color: rgba(255, 255, 255, 0.15);
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
        .metric-card.gross-cost::before {{ background: #818cf8; }}
        .metric-card.credits::before {{ background: var(--accent-green); }}

        .metric-label {{
            color: var(--text-muted);
            font-size: 0.875rem;
            font-weight: 500;
            margin-bottom: 0.5rem;
        }}

        .metric-val {{
            font-size: 2.25rem;
            font-weight: 800;
            font-family: 'JetBrains Mono', monospace;
            background: #ffffff;
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }}

        .metric-val.green {{
            background: linear-gradient(135deg, #34d399, #059669);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
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

        .row-full {{
            grid-template-columns: 1fr;
        }}

        .panel {{
            background: var(--panel-bg);
            backdrop-filter: blur(16px);
            border: 1px solid var(--border-color);
            border-radius: 16px;
            padding: 1.75rem;
            overflow: hidden;
            display: flex;
            flex-direction: column;
        }}

        .panel-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 1.5rem;
        }}

        .panel-title {{
            font-size: 1.15rem;
            font-weight: 700;
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
            color: #cbd5e1;
            border-bottom: 1px solid var(--border-color);
            position: sticky;
            top: 0;
            z-index: 10;
        }}

        td {{
            padding: 0.85rem 1rem;
            border-bottom: 1px solid var(--border-color);
            color: #cbd5e1;
            font-family: 'Plus Jakarta Sans', sans-serif;
        }}

        tr:last-child td {{
            border-bottom: none;
        }}

        tr:hover td {{
            background-color: rgba(255, 255, 255, 0.02);
        }}

        .num-col {{
            text-align: right;
            font-family: 'JetBrains Mono', monospace;
        }}

        .mono-text {{
            font-family: 'JetBrains Mono', monospace;
            font-size: 0.8rem;
        }}

        .pct-bar-bg {{
            background: rgba(255, 255, 255, 0.05);
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
            background: rgba(99, 102, 241, 0.15);
            color: #a5b4fc;
            border: 1px solid rgba(99, 102, 241, 0.3);
        }}

        .pill-green {{
            background: rgba(16, 185, 129, 0.15);
            color: #6ee7b7;
            border: 1px solid rgba(16, 185, 129, 0.3);
        }}

        /* Recommendations Panel */
        .recommendation-list {{
            display: flex;
            flex-direction: column;
            gap: 1rem;
        }}

        .rec-item {{
            background: rgba(255, 255, 255, 0.02);
            border: 1px solid var(--border-color);
            border-radius: 12px;
            padding: 1.25rem;
            display: flex;
            gap: 1rem;
            transition: border-color 0.3s ease;
        }}

        .rec-item:hover {{
            border-color: rgba(255, 255, 255, 0.12);
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
            border: 1px solid rgba(239, 68, 68, 0.2);
        }}

        .rec-icon-box.info {{
            background: var(--primary-glow);
            color: var(--primary);
            border: 1px solid rgba(99, 102, 241, 0.2);
        }}

        .rec-content h4 {{
            font-size: 0.95rem;
            font-weight: 700;
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
            font-family: 'JetBrains Mono', monospace;
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
            background: rgba(255, 255, 255, 0.015);
            border: 1px solid var(--border-color);
            border-radius: 12px;
            overflow: hidden;
            transition: border-color 0.3s ease;
        }}

        .accordion-item:hover {{
            border-color: rgba(255, 255, 255, 0.1);
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
            font-family: 'JetBrains Mono', monospace;
            font-size: 0.9rem;
            font-weight: 700;
            color: var(--text-muted);
            background: rgba(255, 255, 255, 0.05);
            width: 24px;
            height: 24px;
            border-radius: 6px;
            display: flex;
            align-items: center;
            justify-content: center;
        }}

        .project-info-title {{
            font-weight: 700;
            font-size: 1rem;
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
            font-family: 'JetBrains Mono', monospace;
            font-weight: 700;
            font-size: 1.1rem;
        }}

        .chevron-icon {{
            transition: transform 0.3s ease;
        }}

        .accordion-item.active .chevron-icon {{
            transform: rotate(180deg);
        }}

        .accordion-content {{
            max-height: 0;
            overflow: hidden;
            transition: max-height 0.3s ease, padding 0.3s ease;
            background: rgba(0, 0, 0, 0.2);
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
            background: rgba(255, 255, 255, 0.03);
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
            background: rgba(99, 102, 241, 0.15);
            color: #a5b4fc;
            border-color: rgba(99, 102, 241, 0.4);
        }}

        .range-btn:hover:not(.active-range) {{
            color: var(--text-main);
            background: rgba(255, 255, 255, 0.03);
        }}

        .date-filter-wrapper {{
            display: flex;
            align-items: center;
            gap: 0.25rem;
            background: rgba(255, 255, 255, 0.02);
            padding: 0.15rem 0.4rem;
            border-radius: 6px;
            border: 1px solid var(--border-color);
            transition: all 0.2s ease;
        }}

        .date-filter-wrapper:focus-within {{
            border-color: rgba(99, 102, 241, 0.4);
            background: rgba(99, 102, 241, 0.02);
            box-shadow: 0 0 10px rgba(99, 102, 241, 0.1);
        }}

        .date-filter-input {{
            background: transparent;
            border: none;
            color: var(--text-main);
            font-family: 'JetBrains Mono', monospace;
            font-size: 0.75rem;
            outline: none;
            cursor: pointer;
        }}

        .date-filter-input::-webkit-calendar-picker-indicator {{
            filter: invert(1);
            opacity: 0.6;
            cursor: pointer;
        }}

        .date-filter-input::-webkit-calendar-picker-indicator:hover {{
            opacity: 1;
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
            <div class="gcloud-badge">
                <div class="badge-dot"></div>
                Active Config: {config_name}
            </div>
        </header>

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

        <!-- Row 4: Top 25 SKU Detailed Table -->
        <div class="panel">
            <div class="panel-header">
                <div class="panel-title">
                    <svg viewBox="0 0 24 24"><path d="M3 13h12v-2H3v2zm0 4h12v-2H3v2zm0-8h12V7H3v2zm14 8h2v-4h2v-2h-2V9h-2v4h-2v2h2v4z"/></svg>
                    Top 25 Billing SKUs (May 2026)
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
    </div>

    <script>
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
                            '#6366f1', '#818cf8', '#a5b4fc', '#c7d2fe', '#e0e7ff',
                            '#10b981', '#34d399', '#6ee7b7', '#a7f3d0', '#ecfdf5',
                            '#f59e0b', '#fbbf24', '#fcd34d', '#fef3c7', '#fffbeb',
                            '#ef4444', '#f87171', '#fca5a5', '#fee2e2', '#fef2f2'
                        ],
                        borderWidth: 1,
                        borderColor: '#0b0f19'
                    }}]
                }},
                options: {{
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {{
                        legend: {{
                            position: 'right',
                            labels: {{
                                color: '#9ca3af',
                                font: {{
                                    family: 'Plus Jakarta Sans',
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
                            '#34d399', '#6366f1', '#fbbf24', '#ef4444', '#a7f3d0',
                            '#a5b4fc', '#fcd34d', '#fca5a5', '#818cf8', '#10b981',
                            '#f59e0b', '#059669', '#cbd5e1', '#94a3b8', '#64748b'
                        ],
                        borderWidth: 1,
                        borderColor: '#0b0f19'
                    }}]
                }},
                options: {{
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {{
                        legend: {{
                            position: 'right',
                            labels: {{
                                color: '#9ca3af',
                                font: {{
                                    family: 'Plus Jakarta Sans',
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
                        borderColor: '#6366f1',
                        backgroundColor: 'rgba(99, 102, 241, 0.1)',
                        borderWidth: 3,
                        pointBackgroundColor: '#6366f1',
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
                                color: 'rgba(255, 255, 255, 0.05)'
                            }},
                            ticks: {{
                                color: '#9ca3af',
                                font: {{
                                    family: 'Plus Jakarta Sans'
                                }}
                            }}
                        }},
                        y: {{
                            grid: {{
                                color: 'rgba(255, 255, 255, 0.05)'
                            }},
                            ticks: {{
                                color: '#9ca3af',
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
        let renderedCharts = {{}};
        const chartColors = [
            '#6366f1', '#10b981', '#fbbf24', '#ef4444', '#a5b4fc',
            '#34d399', '#f59e0b', '#f87171', '#818cf8', '#6ee7b7'
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
                                labels: {{ color: '#9ca3af', font: {{ family: 'Plus Jakarta Sans', size: 10 }} }}
                            }},
                            tooltip: {{
                                mode: 'index',
                                intersect: false
                            }}
                        }},
                        scales: {{
                            x: {{ grid: {{ color: 'rgba(255, 255, 255, 0.03)' }}, ticks: {{ color: '#9ca3af', font: {{ family: 'Plus Jakarta Sans', size: 9 }} }} }},
                            y: {{ grid: {{ color: 'rgba(255, 255, 255, 0.03)' }}, ticks: {{ color: '#9ca3af', font: {{ family: 'JetBrains Mono', size: 9 }} }} }}
                        }}
                    }}
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
                                labels: {{ color: '#9ca3af', font: {{ family: 'Plus Jakarta Sans', size: 10 }} }}
                            }},
                            tooltip: {{
                                mode: 'index',
                                intersect: false
                            }}
                        }},
                        scales: {{
                            x: {{ grid: {{ color: 'rgba(255, 255, 255, 0.03)' }}, ticks: {{ color: '#9ca3af', font: {{ family: 'Plus Jakarta Sans', size: 9 }} }} }},
                            y: {{ grid: {{ color: 'rgba(255, 255, 255, 0.03)' }}, ticks: {{ color: '#9ca3af', font: {{ family: 'JetBrains Mono', size: 9 }} }} }}
                        }}
                    }}
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
    </script>
</body>
</html>
"""

def run_bq_query(sql_query):
    try:
        res = subprocess.run(
            ['bq', 'query', '--use_legacy_sql=false', '--format=json', '--max_rows=100000', sql_query],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        if res.returncode != 0:
            print(f"Error running query: {res.stderr}", file=sys.stderr)
            return []
        
        # Strip some potential table headers outputted by bq before JSON, if any
        stdout_str = res.stdout.strip()
        if not stdout_str:
            return []
        
        # Sometimes there might be standard output warnings before the json starts, e.g. "Welcome to BigQuery..."
        # So we try to find the start of the JSON array '[' and end ']'
        start_idx = stdout_str.find('[')
        end_idx = stdout_str.rfind(']')
        if start_idx != -1 and end_idx != -1:
            stdout_str = stdout_str[start_idx:end_idx+1]
        
        return json.loads(stdout_str)
    except Exception as e:
        print(f"Exception during bq query: {str(e)}", file=sys.stderr)
        return []

def verify_gcp_environment(project_id, dataset_name):
    """
    Verifies that gcloud is authenticated, bq CLI is installed, the dataset exists,
    and we have the necessary BigQuery permissions to run queries.
    """
    print("🔍 Performing automatic prerequisite & IAM permissions verification...")
    
    # 1. Check if gcloud is installed and authenticated
    try:
        gcloud_check = subprocess.run(['gcloud', 'config', 'get-value', 'account'], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        if gcloud_check.returncode != 0 or not gcloud_check.stdout.strip():
            print("\n❌ Error: Not authenticated with gcloud CLI!", file=sys.stderr)
            print("Please run 'gcloud auth login' and try again.\n", file=sys.stderr)
            return False
        print(f"✅ Authenticated gcloud account: {gcloud_check.stdout.strip()}")
    except FileNotFoundError:
        print("\n❌ Error: 'gcloud' command line tool not found in PATH!", file=sys.stderr)
        print("Please install Google Cloud SDK: https://cloud.google.com/sdk/docs/install\n", file=sys.stderr)
        return False

    # 2. Check if bq is installed
    try:
        bq_check = subprocess.run(['bq', 'version'], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        if bq_check.returncode != 0:
            print("\n❌ Error: 'bq' CLI tool found but returned an error.", file=sys.stderr)
            return False
        print("✅ 'bq' CLI tool is available.")
    except FileNotFoundError:
        print("\n❌ Error: 'bq' command line tool not found in PATH!", file=sys.stderr)
        print("Please install Google Cloud SDK to get 'bq'.\n", file=sys.stderr)
        return False

    # 3. Check if target BigQuery project/dataset can be read (IAM roles/bigquery.dataViewer)
    print(f"🔍 Verifying access to dataset '{project_id}.{dataset_name}'...")
    try:
        bq_ls = subprocess.run(
            ['bq', 'ls', '--format=json', f"{project_id}:{dataset_name}"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        if bq_ls.returncode != 0:
            stderr_str = bq_ls.stderr.lower()
            print(f"\n❌ Error: Access denied or dataset not found at '{project_id}.{dataset_name}'!", file=sys.stderr)
            if "permission" in stderr_str or "access denied" in stderr_str:
                print("💡 Check your IAM permissions: You need the 'roles/bigquery.dataViewer' role on the dataset or billing project.", file=sys.stderr)
            else:
                print("💡 Check if Cloud Billing Export has been configured properly. Ensure the dataset name is correct.", file=sys.stderr)
                print("Detailed guide: See the Prerequisites section in the README.md file.", file=sys.stderr)
            print(f"Details: {bq_ls.stderr.strip()}\n", file=sys.stderr)
            return False
        print(f"✅ Successfully accessed BigQuery dataset '{dataset_name}'.")
    except Exception as e:
        print(f"\n❌ Error checking BigQuery dataset access: {str(e)}", file=sys.stderr)
        return False

    # 4. Check if BigQuery query execution is permitted (IAM roles/bigquery.jobUser)
    print("🔍 Testing BigQuery query execution (roles/bigquery.jobUser)...")
    try:
        test_query = "SELECT 1"
        bq_test = subprocess.run(
            ['bq', 'query', '--use_legacy_sql=false', '--format=json', test_query],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        if bq_test.returncode != 0:
            stderr_str = bq_test.stderr.lower()
            print("\n❌ Error: Failed to run test query in BigQuery!", file=sys.stderr)
            if "permission" in stderr_str or "access denied" in stderr_str:
                print("💡 Check your IAM permissions: You need the 'roles/bigquery.jobUser' role on the active project to run query jobs.", file=sys.stderr)
            print(f"Details: {bq_test.stderr.strip()}\n", file=sys.stderr)
            return False
        print("✅ BigQuery query execution test passed successfully.")
    except Exception as e:
        print(f"\n❌ Error checking query job execution capability: {str(e)}", file=sys.stderr)
        return False

    print("🚀 All prerequisite & IAM permission checks passed successfully!\n")
    return True

def main():
    parser = argparse.ArgumentParser(description="GCP Billing & Cost Analyzer Dashboard Generator")
    parser.add_argument("--project", "-p", help="GCP Project ID where the BigQuery billing dataset resides (defaults to active gcloud project)")
    parser.add_argument("--dataset", "-d", default="billing_exports", help="BigQuery billing export dataset name (default: billing_exports)")
    parser.add_argument("--month", "-m", help="Invoice month in YYYYMM format (defaults to May 2026 / current month)")
    parser.add_argument("--output-dir", "-o", default=".", help="Directory to save generated dashboards (default: current directory)")
    args = parser.parse_args()

    print("🚀 Starting GCP cost breakdown & visualization generator...")
    
    # Resolve project and configuration
    config_name = "default"
    discovered_project_id = "your-gcp-project-id"
    
    print("🔍 Discovering active gcloud configuration...")
    try:
        config_res = subprocess.run(['gcloud', 'config', 'configurations', 'list', '--filter=IS_ACTIVE=true', '--format=json'], stdout=subprocess.PIPE, text=True)
        if config_res.returncode == 0:
            configs = json.loads(config_res.stdout)
            if configs:
                config_name = configs[0].get('name', config_name)
                discovered_project_id = configs[0].get('properties', {}).get('core', {}).get('project', discovered_project_id)
    except Exception as e:
        print(f"⚠️ Could not read active configuration programmatically: {str(e)}")
    
    project_id = args.project if args.project else discovered_project_id
    dataset_name = args.dataset
    
    print(f"📍 Active configuration: {config_name}")
    print(f"📍 Target billing project: {project_id}")
    print(f"📍 Target BigQuery dataset: {dataset_name}")
    
    # Run automatic IAM permissions check
    if not verify_gcp_environment(project_id, dataset_name):
        print("❌ Error: Prerequisite check failed. Aborting cost analysis.", file=sys.stderr)
        sys.exit(1)
        
    print(f"🔍 Searching for billing export tables in `{dataset_name}` dataset...")
    # Find tables
    tables_query = f"""
    SELECT table_name 
    FROM `{project_id}.{dataset_name}.INFORMATION_SCHEMA.TABLES` 
    WHERE table_name LIKE 'gcp_billing_export_v1_%' 
       OR table_name LIKE 'gcp_billing_export_resource_v1_%'
    """
    tables = run_bq_query(tables_query)
    
    standard_table = None
    resource_table = None
    
    for t in tables:
        name = t['table_name']
        if name.startswith('gcp_billing_export_resource_v1_'):
            resource_table = f"{project_id}.{dataset_name}.{name}"
        elif name.startswith('gcp_billing_export_v1_'):
            standard_table = f"{project_id}.{dataset_name}.{name}"
            
    if not standard_table:
        print(f"❌ Error: Standard billing export table not found in dataset `{dataset_name}`!", file=sys.stderr)
        sys.exit(1)
        
    if not resource_table:
        print(f"⚠️ Warning: Resource-level billing export table not found. Defaulting to standard table for resources.")
        resource_table = standard_table
        
    print(f"✅ Found Standard Export Table: {standard_table}")
    print(f"✅ Found Resource Export Table: {resource_table}")
    
    # Handle Month formatting
    if args.month:
        current_month = args.month
    else:
        # Default to previous month or current calendar month.
        # To stay fully compatible with May 2026 dataset:
        current_month = datetime.now().strftime("%Y%m")
        if current_month == "202606" or current_month == "202605":
            current_month = "202605"
            
    try:
        current_month_dt = datetime.strptime(current_month, "%Y%m")
        current_month_formatted = current_month_dt.strftime("%B %Y")
    except ValueError:
        print(f"❌ Error: Invalid month format '{current_month}'. Must be YYYYMM.", file=sys.stderr)
        sys.exit(1)
        
    print(f"📊 Querying data for {current_month_formatted} ({current_month})...")
    
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
    trend_data = run_bq_query(trend_query)
    
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
    project_data = run_bq_query(project_query)
    
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
    service_data = run_bq_query(service_query)
    
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
    proj_service_data = run_bq_query(proj_service_query)
    
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
    sku_data = run_bq_query(sku_query)
    
    # Query 6: Named Resources (with specific names)
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
    resource_data = run_bq_query(resource_query)
    
    # Query 7: Daily Service Cost (last 60 days)
    print("📊 Querying daily service costs for past 60 days...")
    daily_service_query = f"""
    SELECT
      COALESCE(project.id, 'Non-project / Shared') as project_id,
      service.description as service_description,
      EXTRACT(DATE FROM usage_start_time) as usage_date,
      SUM(cost + (SELECT COALESCE(SUM(c.amount), 0) FROM UNNEST(credits) c)) as net_cost
    FROM `{standard_table}`
    WHERE usage_start_time >= TIMESTAMP('2026-04-01 00:00:00')
      AND usage_start_time < TIMESTAMP('2026-06-01 00:00:00')
    GROUP BY 1, 2, 3
    ORDER BY usage_date ASC
    """
    daily_service_data = run_bq_query(daily_service_query)
    
    # Query 8: Daily SKU Cost (last 60 days)
    print("📊 Querying daily SKU costs for past 60 days...")
    daily_sku_query = f"""
    SELECT
      COALESCE(project.id, 'Non-project / Shared') as project_id,
      sku.description as sku_description,
      EXTRACT(DATE FROM usage_start_time) as usage_date,
      SUM(cost + (SELECT COALESCE(SUM(c.amount), 0) FROM UNNEST(credits) c)) as net_cost
    FROM `{standard_table}`
    WHERE usage_start_time >= TIMESTAMP('2026-04-01 00:00:00')
      AND usage_start_time < TIMESTAMP('2026-06-01 00:00:00')
    GROUP BY 1, 2, 3
    ORDER BY usage_date ASC
    """
    daily_sku_data = run_bq_query(daily_sku_query)
    
    # Cast all numeric fields to float from string to prevent calculation errors
    def cast_numeric_fields(data_list):
        numeric_keys = ['total_cost', 'total_credits', 'net_cost', 'cost']
        for d in data_list:
            for k in numeric_keys:
                if k in d and d[k] is not None:
                    try:
                        d[k] = float(d[k])
                    except (ValueError, TypeError):
                        d[k] = 0.0
                        
    cast_numeric_fields(trend_data)
    cast_numeric_fields(project_data)
    cast_numeric_fields(service_data)
    cast_numeric_fields(proj_service_data)
    cast_numeric_fields(sku_data)
    cast_numeric_fields(resource_data)
    cast_numeric_fields(daily_service_data)
    cast_numeric_fields(daily_sku_data)
    
    print("📈 Data gathered successfully. Processing records & calculating metrics...")
    
    # Calculate main metrics for May 2026
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
        
    # -------------------------------------------------------------
    # Process Daily Spend Data for past 60 days (Apr 1 - May 31, 2026)
    # -------------------------------------------------------------
    import datetime as dt_mod
    start_dt = dt_mod.date(2026, 4, 1)
    end_dt = dt_mod.date(2026, 5, 31)
    date_list = []
    curr_dt = start_dt
    while curr_dt <= end_dt:
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
    peak_daily_spend = {} # project_id -> (date, amount)

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
        
        # Calculate Peak Daily Spend for this project
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
                    <span style="color: #6ee7b7; text-overflow: ellipsis; overflow: hidden; white-space: nowrap; max-width: 400px;" title="{r['resource_name']}">{r['resource_name'].split('/')[-1]}</span>
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
                        <b style="font-size: 1rem; color: #cbd5e1; display: flex; align-items: center; gap: 0.5rem;">
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
        
    # Write HTML file
    rendered_html = HTML_TEMPLATE.format(
        month_formatted=current_month_formatted,
        config_name=config_name,
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
    
    # Resolve output directory
    output_dir = args.output_dir if args.output_dir else "."
    os.makedirs(output_dir, exist_ok=True)
    
    html_path = os.path.join(output_dir, "gcp_cost_dashboard.html")
    with open(html_path, "w") as f:
        f.write(rendered_html)
    print(f"🎨 Beautiful interactive HTML report saved to: {html_path}")
    
    # Write Markdown file
    md_report = generate_markdown_report(
        current_month_formatted, net_cost, gross_cost, credits,
        project_data, service_data, sku_data, resource_data, trend_data, config_name, peak_daily_spend
    )
    
    filename_month = current_month_dt.strftime("%B_%Y")
    md_path = os.path.join(output_dir, f"GCP_Cost_Analysis_{filename_month}.md")
    with open(md_path, "w") as f:
        f.write(md_report)
    print(f"📝 Clean and readable Markdown report saved to: {md_path}")
    
    print("\n✅ All cost analysis outputs generated successfully!")

def generate_markdown_report(month_formatted, net_cost, gross_cost, credits, project_data, service_data, sku_data, resource_data, trend_data, config_name, peak_daily_spend):
    # Trends table
    trend_table_lines = ["| Month | Gross Cost | Credits | Net Cost | Change MoM |", "|---|---|---|---|---|"]
    prev_net = None
    for t in trend_data:
        m_formatted = datetime.strptime(t['invoice_month'], "%Y%m").strftime("%b %Y")
        pct_change_str = "-"
        if prev_net is not None and prev_net > 0:
            pct_change = ((t['net_cost'] - prev_net) / prev_net) * 100
            pct_change_str = f"{pct_change:+.1f}%"
        prev_net = t['net_cost']
        trend_table_lines.append(f"| **{m_formatted}** | ${t['total_cost']:,.2f} | ${abs(t['total_credits']):,.2f} | **${t['net_cost']:,.2f}** | {pct_change_str} |")
        
    # Project table
    proj_table_lines = ["| Rank | Project ID | Project Name | Gross Cost | Credits | Net Cost | Share | Peak Daily Spend (Date) |", "|---|---|---|---|---|---|---|---|"]
    for idx, p in enumerate(project_data[:10]):
        share = (p['net_cost'] / net_cost * 100) if net_cost > 0 else 0
        p_id = p['project_id']
        peak_str = "-"
        if p_id in peak_daily_spend:
            pk_date, pk_val = peak_daily_spend[p_id]
            peak_str = f"${pk_val:,.2f} ({pk_date})"
        proj_table_lines.append(f"| {idx+1} | `{p_id}` | {p['project_name']} | ${p['total_cost']:,.2f} | ${abs(p['total_credits']):,.2f} | **${p['net_cost']:,.2f}** | {share:.1f}% | {peak_str} |")
        
    # Service table
    srv_table_lines = ["| Rank | Service Description | Gross Cost | Credits | Net Cost | Share |", "|---|---|---|---|---|---|"]
    for idx, s in enumerate(service_data[:10]):
        share = (s['net_cost'] / net_cost * 100) if net_cost > 0 else 0
        srv_table_lines.append(f"| {idx+1} | **{s['service_description']}** | ${s['total_cost']:,.2f} | ${abs(s['total_credits']):,.2f} | **${s['net_cost']:,.2f}** | {share:.1f}% |")

    # SKU table
    sku_table_lines = ["| Rank | Project ID | Service | SKU Description | Net Cost | Share |", "|---|---|---|---|---|---|"]
    for idx, s in enumerate(sku_data[:15]):
        share = (s['net_cost'] / net_cost * 100) if net_cost > 0 else 0
        sku_table_lines.append(f"| {idx+1} | `{s['project_id']}` | {s['service_description']} | {s['sku_description']} | **${s['net_cost']:,.2f}** | {share:.1f}% |")
        
    # Resources table
    res_table_lines = ["| Rank | Project ID | Service | Resource Name / ID | Net Cost |", "|---|---|---|---|---|"]
    for idx, r in enumerate(resource_data[:15]):
        res_table_lines.append(f"| {idx+1} | `{r['project_id']}` | {r['service_description']} | `{r['resource_name'].split('/')[-1]}` | **${r['net_cost']:,.2f}** |")

    # Pre-calculate sums and dynamically find the top project and service to avoid hardcoded fallbacks
    top_project_id = project_data[0]['project_id'] if project_data else "your-gcp-project"
    top_project_name = project_data[0]['project_name'] if project_data else "your-gcp-project"
    top_project_cost = project_data[0]['net_cost'] if project_data else 0.0
    top_project_pct = (top_project_cost / net_cost * 100) if net_cost > 0 else 0

    top_service_desc = service_data[0]['service_description'] if service_data else "GCP Services"
    top_service_cost = service_data[0]['net_cost'] if service_data else 0.0
    top_service_pct = (top_service_cost / net_cost * 100) if net_cost > 0 else 0

    embeddings_cost = sum(s['net_cost'] for s in sku_data if s['sku_description'] == 'Embedding for Text - Batch Predictions')
    bq_res_total_cost = sum(s['net_cost'] for s in sku_data if 'BigQuery Enterprise Edition' in s['sku_description'])

    md = f"""# GCP Billing & Cost Analysis Report
**Invoice Period:** {month_formatted}  
**Generated On:** {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}  
**gcloud Active Profile:** `{config_name}`  

---

## 📌 Executive Summary

For the month of **{month_formatted}**, the total net cost of Google Cloud platform usage is **${net_cost:,.2f}** (gross list cost of **${gross_cost:,.2f}** adjusted by **${abs(credits):,.2f}** of credits).

> [!NOTE]
> The primary cost driver in this billing period is **{top_service_desc}** (accounting for **${top_service_cost:,.2f}**, or **{top_service_pct:.1f}%** of net costs).
> 
> The project contributing most to the bill is **`{top_project_id}`** (`{top_project_name}`) representing **${top_project_cost:,.2f}** (**{top_project_pct:.1f}%**).

---

## 📈 Month-over-Month Billing Trend

Here is the historical net cost trend for the last few months of billing exports:

{chr(10).join(trend_table_lines)}

---

## 🏢 Top 10 GCP Projects by Billing

The following projects contributed the most to your cost in **{month_formatted}**:

{chr(10).join(proj_table_lines)}

---

## 🛠️ Top 10 GCP Services by Billing

The specific services generating the highest costs are:

{chr(10).join(srv_table_lines)}

---

## 🏷️ Top 15 Billing SKUs

These specific SKUs represent the core components of your expenditures:

{chr(10).join(sku_table_lines)}

---

## 🧬 Top 15 Specific Named Resources

The resource-level export identifies individual entities generating billing charges (such as VM instances, databases, or cloud functions):

{chr(10).join(res_table_lines)}

---

## 💡 Key Optimization Recommendations

Based on the SKU and Resource-level billing analysis, here are high-impact cost savings opportunities:

1. **Vertex AI Embeddings Batch Optimization**
   - **SKU:** `Embedding for Text - Batch Predictions`
   - **Cost:** **${embeddings_cost:,.2f}** (or your primary billing SKU if using embedding services)
   - **Action:** Audit the frequency and scale of text embedding batch pipelines. Consider caching text embedding vectors locally in BigQuery (or a vector database) rather than re-computing embeddings on unchanged texts.

2. **BigQuery Slot Allocation & Edition Reservations Review**
   - **SKUs:** `BigQuery Enterprise Edition` & reservation slot capacities
   - **Cost:** **${bq_res_total_cost:,.2f}**
   - **Action:** Monitor query slot utilization in reservations. If slots (baseline or autoscale capacity) are underutilized, switching to on-demand pricing or downscaling the reserved baseline commitment size could yield massive savings.

3. **Cloud SQL Non-Production Instances**
   - **Resources:** Cloud SQL database instances (PostgreSQL / MySQL / SQL Server storage and CPU units)
   - **Action:** Ensure development, staging, or demo databases are backed by appropriate instance sizes. For non-production environments, configure automatic start/stop schedules to power them down outside working hours (nights and weekends) to avoid 24/7 billing.
"""
    return md

if __name__ == '__main__':
    main()
