#!/usr/bin/env python3
import json
import os
import sys
from datetime import datetime
from google.cloud import bigquery

# Import the HTML template from standard configuration
# We keep the beautiful styling from the original dashboard
HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>GCP Cost Analysis Dashboard - {month_formatted}</title>
    <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600&display=swap" rel="stylesheet">
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/chartjs-plugin-zoom@2.0.1/dist/chartjs-plugin-zoom.min.js"></script>
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

        .header-controls {{
            display: flex;
            align-items: center;
            gap: 1rem;
        }}

        .refresh-btn {{
            background: linear-gradient(135deg, var(--primary), #4f46e5);
            color: white;
            border: none;
            padding: 0.65rem 1.25rem;
            border-radius: 8px;
            font-weight: 600;
            cursor: pointer;
            font-family: inherit;
            display: flex;
            align-items: center;
            gap: 0.5rem;
            box-shadow: 0 4px 15px rgba(99, 102, 241, 0.3);
            transition: all 0.2s ease;
        }}

        .refresh-btn:hover {{
            transform: translateY(-1px);
            box-shadow: 0 6px 20px rgba(99, 102, 241, 0.45);
        }}

        .refresh-btn:active {{
            transform: translateY(0);
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
        
        .tab-btn:hover:not(.active) {
            color: var(--text-main);
            background: rgba(255, 255, 255, 0.03);
        }

        .range-btn {
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
        }

        .range-btn.active-range {
            background: rgba(99, 102, 241, 0.15);
            color: #a5b4fc;
            border-color: rgba(99, 102, 241, 0.4);
        }

        .range-btn:hover:not(.active-range) {
            color: var(--text-main);
            background: rgba(255, 255, 255, 0.03);
        }

        .date-filter-wrapper {
            display: flex;
            align-items: center;
            gap: 0.25rem;
            background: rgba(255, 255, 255, 0.02);
            padding: 0.15rem 0.4rem;
            border-radius: 6px;
            border: 1px solid var(--border-color);
            transition: all 0.2s ease;
        }

        .date-filter-wrapper:focus-within {
            border-color: rgba(99, 102, 241, 0.4);
            background: rgba(99, 102, 241, 0.02);
            box-shadow: 0 0 10px rgba(99, 102, 241, 0.1);
        }

        .date-filter-input {
            background: transparent;
            border: none;
            color: var(--text-main);
            font-family: 'JetBrains Mono', monospace;
            font-size: 0.75rem;
            outline: none;
            cursor: pointer;
        }

        .date-filter-input::-webkit-calendar-picker-indicator {
            filter: invert(1);
            opacity: 0.6;
            cursor: pointer;
        }

        .date-filter-input::-webkit-calendar-picker-indicator:hover {
            opacity: 1;
        }
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
                                labels: {{ color: '#9ca3af', font: {{ family: 'Plus Jakarta Sans', size: 10 }} }}
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
                            x: {{ grid: {{ color: 'rgba(255, 255, 255, 0.03)' }}, ticks: {{ color: '#9ca3af', font: {{ family: 'Plus Jakarta Sans', size: 9 }} }} }},
                            y: {{ grid: {{ color: 'rgba(255, 255, 255, 0.03)' }}, ticks: {{ color: '#9ca3af', font: {{ family: 'JetBrains Mono', size: 9 }} }} }}
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
                                labels: {{ color: '#9ca3af', font: {{ family: 'Plus Jakarta Sans', size: 10 }} }}
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
                            x: {{ grid: {{ color: 'rgba(255, 255, 255, 0.03)' }}, ticks: {{ color: '#9ca3af', font: {{ family: 'Plus Jakarta Sans', size: 9 }} }} }},
                            y: {{ grid: {{ color: 'rgba(255, 255, 255, 0.03)' }}, ticks: {{ color: '#9ca3af', font: {{ family: 'JetBrains Mono', size: 9 }} }} }}
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
    
    print(f"📍 Billing Project: {project_id}")
    print(f"📍 Config Name: {config_name}")
    
    # Initialize BigQuery client
    client = bigquery.Client(project=project_id)
    
    # Run automatic IAM permissions check
    if not verify_bigquery_access(client, project_id, "billing_exports"):
        raise Exception("Prerequisite check failed. Aborting cost analysis.")
    
    # Discover table names in billing_exports dataset
    tables_query = f"""
    SELECT table_name 
    FROM `{project_id}.billing_exports.INFORMATION_SCHEMA.TABLES` 
    WHERE table_name LIKE 'gcp_billing_export_v1_%' 
       OR table_name LIKE 'gcp_billing_export_resource_v1_%'
    """
    tables = run_bq_query(client, tables_query)
    
    standard_table = None
    resource_table = None
    
    for t in tables:
        name = t['table_name']
        if name.startswith('gcp_billing_export_resource_v1_'):
            resource_table = f"{project_id}.billing_exports.{name}"
        elif name.startswith('gcp_billing_export_v1_'):
            standard_table = f"{project_id}.billing_exports.{name}"
            
    if not standard_table:
        raise Exception("Error: Standard billing export table not found in dataset `billing_exports`!")
        
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
        current_month = "202605"
        current_month_formatted = "May 2026"
        
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
