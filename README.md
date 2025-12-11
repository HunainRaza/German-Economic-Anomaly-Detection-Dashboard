# 🇩🇪 German Economic Anomaly Detection System

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![Django 5.0](https://img.shields.io/badge/django-5.0-green.svg)](https://www.djangoproject.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

> An intelligent system for detecting anomalies and forecasting trends in German economic indicators using Machine Learning and Time Series Analysis.

**Academic Project** | Brandenburg Technical University Cottbus-Senftenberg  
**Course:** Data Exploration and System Management Using AI/ML  
**Program:** MS Artificial Intelligence | Winter Semester 2025-26

---

## 📊 Project Overview

This project implements a comprehensive anomaly detection and forecasting system for the German economy using real data from DESTATIS (German Federal Statistical Office). The system combines machine learning algorithms with interactive visualization to identify unusual economic patterns and predict future trends.

### Key Features

- **🔍 Anomaly Detection:** Isolation Forest algorithm identifies unusual economic patterns
- **📈 Time Series Forecasting:** SARIMA models predict future economic indicators
- **📊 Interactive Dashboard:** Real-time visualization built with Django + Plotly Dash
- **💾 Database Integration:** PostgreSQL backend for efficient data management
- **🎯 Data-Driven Architecture:** Dynamic components that adapt to available data
- **🔄 Real-time Updates:** Auto-refreshing dashboard with live data

### Economic Indicators Analyzed

- **GDP Growth Rate** - Annual GDP growth percentage
- **Inflation Rate** - Consumer Price Index (CPI) annual change
- **Unemployment Rate** - Percentage of labor force unemployed
- **Export Share of GDP** - Exports as percentage of GDP
- **Labor Force Participation** - Working-age population participation rate
- **Industrial Production Index** - Manufacturing output trends

### Dataset Coverage

- **Time Period:** 2015-2024 (10 years)
- **Data Source:** DESTATIS (German Federal Statistical Office)
- **Total Features:** 60+ economic indicators
- **Key Events Captured:** COVID-19 economic impact, 2022 inflation spike, post-pandemic recovery

---

## 🏗️ System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     User Interface Layer                    │
│   ┌─────────────────────────────────────────────────────┐   │
│   │   Django Templates + Plotly Dash Dashboard          │   │
│   │   - Interactive Charts  - Real-time Updates         │   │
│   │   - Anomaly Highlights - Forecast Visualizations    │   │
│   └─────────────────────────────────────────────────────┘   │
└────────────────────────┬────────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────────┐
│                  Application Logic Layer                    │
│   ┌─────────────────────────────────────────────────────┐   │
│   │   Django Backend (Python)                           │   │
│   │   - REST API endpoints                              │   │
│   │   - Business logic                                  │   │
│   │   - Data processing pipeline                        │   │
│   └─────────────────────────────────────────────────────┘   │
└────────────────────────┬────────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────────┐
│                   ML/Analytics Layer                        │
│   ┌──────────────────────┐  ┌───────────────────────────┐   │
│   │  Anomaly Detection   │  │  Time Series Forecasting  │   │
│   │  - Isolation Forest  │  │  - SARIMA Models          │   │
│   │  - Contamination: 20%│  │  - Confidence Intervals   │   │
│   └──────────────────────┘  └───────────────────────────┘   │
└────────────────────────┬────────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────────┐
│                      Data Layer                             │
│   ┌─────────────────────────────────────────────────────┐   │
│   │   PostgreSQL Database                               │   │
│   │   - Economic indicators table                       │   │
│   │   - Anomaly scores and flags                        │   │
│   │   - Forecast data storage                           │   │
│   └─────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```