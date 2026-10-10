import ipaddress
import json
import re
import socket
from io import BytesIO
from urllib.parse import urljoin, urlparse, urldefrag
from xml.sax.saxutils import escape

import pandas as pd
import requests
import streamlit as st
from bs4 import BeautifulSoup

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle


# ============================================================
# PAGE SETUP
# ============================================================
st.set_page_config(
    page_title="NexaRank SEO Studio",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="collapsed",
)

MAX_LINKS_TO_CHECK = 15
REQUEST_TIMEOUT = 8
USER_AGENT = "Mozilla/5.0 (compatible; NexaRankSEOStudio/1.0)"


# ============================================================
# COLORFUL GUI CSS
# Important: input text is explicitly dark so it stays visible
# even when the browser/Streamlit theme is dark.
# ============================================================
st.markdown(
    """
    <style>
    .stApp {
        background: linear-gradient(135deg, #f5f7ff 0%, #fdf2f8 52%, #effaff 100%);
    }
    [data-testid="stHeader"] { background: transparent; }
    .block-container {
        max-width: 1400px;
        padding-top: 1.6rem;
        padding-bottom: 3rem;
    }
    .hero {
        display: flex;
        align-items: center;
        gap: 22px;
        background: linear-gradient(115deg, #312e81 0%, #6d28d9 55%, #db2777 100%);
        padding: 30px 34px;
        border-radius: 24px;
        margin-bottom: 24px;
        box-shadow: 0 14px 34px rgba(79, 70, 229, 0.20);
    }
    .brand-logo {
        width: 88px;
        height: 88px;
        flex: 0 0 88px;
        border-radius: 24px;
        display: flex;
        justify-content: center;
        align-items: center;
        background: rgba(255,255,255,0.16);
        border: 1px solid rgba(255,255,255,0.32);
        font-size: 43px;
        box-shadow: inset 0 1px 0 rgba(255,255,255,0.15);
    }
    .hero-badge {
        display: inline-block;
        background: rgba(255,255,255,0.15);
        color: #f5f3ff;
        border: 1px solid rgba(255,255,255,0.28);
        padding: 6px 11px;
        border-radius: 30px;
        font-size: 11px;
        font-weight: 800;
        letter-spacing: 1px;
        margin-bottom: 9px;
    }
    .hero h1 {
        color: #ffffff !important;
        font-size: 2.55rem !important;
        font-weight: 850 !important;
        line-height: 1.12 !important;
        margin: 0 0 8px 0 !important;
    }
    .hero p {
        color: #ede9fe !important;
        font-size: 1rem;
        line-height: 1.65;
        margin: 0;
    }
    [data-testid="stTextInput"] input {
        background: #ffffff !important;
        color: #172033 !important;
        -webkit-text-fill-color: #172033 !important;
        caret-color: #6d28d9 !important;
        border: 1.5px solid #c4b5fd !important;
        border-radius: 13px !important;
        min-height: 48px;
        font-size: 16px !important;
    }
    [data-testid="stTextInput"] input::placeholder {
        color: #7c8498 !important;
        -webkit-text-fill-color: #7c8498 !important;
        opacity: 1 !important;
    }
    [data-testid="stTextInput"] input:focus {
        border-color: #7c3aed !important;
        box-shadow: 0 0 0 3px rgba(124, 58, 237, 0.13) !important;
    }
    [data-testid="stTextInput"] label {
        color: #312e81 !important;
        font-weight: 700 !important;
    }
    [data-testid="stMetric"] {
        background: rgba(255,255,255,0.96);
        border: 1px solid #e4e4ff;
        border-radius: 18px;
        padding: 17px 19px;
        box-shadow: 0 7px 20px rgba(70,60,140,0.08);
    }
    [data-testid="stMetricLabel"] {
        color: #625b85 !important;
        font-weight: 650 !important;
    }
    [data-testid="stMetricValue"] {
        color: #4338ca !important;
        font-weight: 800 !important;
    }
    div.stButton > button[kind="primaryFormSubmit"],
    div.stFormSubmitButton > button,
    button[kind="primary"] {
        background: linear-gradient(100deg, #4f46e5, #9333ea, #db2777) !important;
        color: #ffffff !important;
        border: 0 !important;
        border-radius: 12px !important;
        min-height: 46px;
        font-weight: 750 !important;
        box-shadow: 0 6px 16px rgba(124,58,237,0.22);
        transition: 0.2s ease;
    }
    div.stButton > button[kind="primaryFormSubmit"]:hover,
    div.stFormSubmitButton > button:hover,
    button[kind="primary"]:hover {
        transform: translateY(-1px);
        box-shadow: 0 9px 20px rgba(124,58,237,0.30);
    }
    div[data-testid="stDownloadButton"] > button {
        background: #ffffff !important;
        color: #5b21b6 !important;
        border: 1px solid #c4b5fd !important;
        border-radius: 12px !important;
        font-weight: 750 !important;
        min-height: 43px;
    }
    div[data-testid="stDownloadButton"] > button:hover {
        background: #f3e8ff !important;
        border-color: #8b5cf6 !important;
    }
    /* Custom colorful SEO results table */
    .seo-table-shell {
        width: 100%;
        overflow-x: auto;
        border: 1px solid #e7e3ff;
        border-radius: 18px;
        background: #ffffff;
        box-shadow: 0 12px 28px rgba(79, 70, 229, 0.10);
        margin: 12px 0 22px 0;
    }
    table.seo-results-table {
        width: 100%;
        min-width: 1050px;
        border-collapse: separate;
        border-spacing: 0;
        table-layout: fixed;
        font-size: 13px;
        color: #252744;
    }
    .seo-results-table thead th {
        background: linear-gradient(105deg, #4338ca 0%, #7c3aed 56%, #db2777 100%);
        color: #ffffff !important;
        text-align: left;
        padding: 16px 15px;
        font-weight: 800;
        font-size: 11px;
        text-transform: uppercase;
        letter-spacing: .7px;
        border: none;
        vertical-align: top;
    }
    .seo-results-table thead th:first-child { border-top-left-radius: 16px; }
    .seo-results-table thead th:last-child { border-top-right-radius: 16px; }
    .seo-results-table tbody td {
        padding: 15px;
        border-bottom: 1px solid #efedfb;
        vertical-align: top;
        line-height: 1.6;
        overflow-wrap: anywhere;
        white-space: normal;
        background: #ffffff;
    }
    .seo-results-table tbody tr:nth-child(even) td { background: #f8f7ff; }
    .seo-results-table tbody tr:hover td { background: #f0edff; }
    .seo-results-table tbody tr:last-child td { border-bottom: none; }
    .seo-results-table .check-name { color: #393080; font-weight: 800; }
    .seo-results-table .status-badge {
        display: inline-block;
        padding: 5px 10px;
        border-radius: 999px;
        font-size: 10px;
        line-height: 1.45;
        font-weight: 850;
        letter-spacing: .25px;
        white-space: nowrap;
        border: 1px solid transparent;
    }
    .seo-results-table .badge-pass {
        color: #166534;
        background: #dcfce7;
        border-color: #bbf7d0;
    }
    .seo-results-table .badge-fail {
        color: #9f1239;
        background: #ffe4e6;
        border-color: #fecdd3;
    }
    .seo-results-table .badge-improve {
        color: #92400e;
        background: #fef3c7;
        border-color: #fde68a;
    }
    .seo-results-table .badge-not-checked {
        color: #5b21b6;
        background: #ede9fe;
        border-color: #ddd6fe;
    }
    .seo-results-table .row-pass td:first-child { border-left: 4px solid #22c55e; }
    .seo-results-table .row-fail td:first-child { border-left: 4px solid #f43f5e; }
    .seo-results-table .row-improve td:first-child { border-left: 4px solid #f59e0b; }
    .seo-results-table .row-not-checked td:first-child { border-left: 4px solid #8b5cf6; }
    .seo-table-note {
        display: flex;
        flex-wrap: wrap;
        gap: 8px;
        margin: 0 0 12px 0;
        color: #625b85;
        font-size: 12px;
    }
    .seo-table-note span {
        display: inline-block;
        background: rgba(255,255,255,.85);
        border: 1px solid #e7e3ff;
        border-radius: 999px;
        padding: 5px 9px;
    }
    h2, h3 { color: #312e81 !important; }
    [data-testid="stAlert"] { border-radius: 14px; }
    .score-card {
        background: rgba(255,255,255,0.94);
        border: 1px solid #e7e5ff;
        border-radius: 22px;
        padding: 24px 16px;
        text-align: center;
        box-shadow: 0 9px 24px rgba(70,60,140,0.08);
        height: 100%;
    }
    .score-ring {
        width: 188px;
        height: 188px;
        margin: 8px auto 14px auto;
        border-radius: 50%;
        display: grid;
        place-items: center;
        background: conic-gradient(
            var(--score-color) 0deg var(--score-deg),
            #e9eaf3 var(--score-deg) 360deg
        );
    }
    .score-center {
        width: 148px;
        height: 148px;
        border-radius: 50%;
        background: #ffffff;
        display: flex;
        flex-direction: column;
        justify-content: center;
        align-items: center;
        box-shadow: inset 0 0 0 1px #f0edff;
    }
    .score-number {
        color: var(--score-color);
        font-size: 39px;
        font-weight: 850;
        line-height: 1.1;
    }
    .score-out-of {
        color: #77758b;
        font-size: 13px;
        font-weight: 650;
        margin-top: 4px;
    }
    .score-caption {
        color: #312e81;
        font-size: 18px;
        font-weight: 800;
    }
    .score-subcaption {
        color: #77758b;
        font-size: 12px;
        margin-top: 5px;
    }
    .section-kicker {
        color: #7c3aed;
        font-size: 11px;
        font-weight: 800;
        letter-spacing: 1.2px;
        text-transform: uppercase;
    }
    /* Modern audit cards replace the old table layout */
    .audit-grid {
        display: grid;
        grid-template-columns: repeat(2, minmax(0, 1fr));
        gap: 15px;
        margin: 14px 0 24px 0;
    }
    .audit-card {
        background: rgba(255,255,255,0.96);
        border: 1px solid #e8e5fa;
        border-left: 5px solid #8b5cf6;
        border-radius: 18px;
        padding: 17px 18px;
        box-shadow: 0 8px 22px rgba(70,60,140,0.07);
        min-width: 0;
        transition: transform .18s ease, box-shadow .18s ease;
    }
    .audit-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 13px 28px rgba(70,60,140,0.12);
    }
    .audit-card.status-pass { border-left-color: #16a34a; }
    .audit-card.status-fail { border-left-color: #e11d48; }
    .audit-card.status-improve { border-left-color: #d97706; }
    .audit-card.status-not-checked { border-left-color: #8b5cf6; }
    .audit-card-top {
        display: flex;
        justify-content: space-between;
        align-items: flex-start;
        gap: 10px;
        margin-bottom: 12px;
    }
    .audit-card-title {
        color: #312e81;
        font-size: 15px;
        line-height: 1.4;
        font-weight: 850;
        overflow-wrap: anywhere;
    }
    .audit-status {
        display: inline-block;
        border-radius: 999px;
        padding: 5px 9px;
        font-size: 10px;
        line-height: 1.4;
        font-weight: 850;
        text-transform: uppercase;
        letter-spacing: .35px;
        white-space: nowrap;
        flex-shrink: 0;
    }
    .audit-status.pass { color: #166534; background: #dcfce7; border: 1px solid #bbf7d0; }
    .audit-status.fail { color: #9f1239; background: #ffe4e6; border: 1px solid #fecdd3; }
    .audit-status.improve { color: #92400e; background: #fef3c7; border: 1px solid #fde68a; }
    .audit-status.not-checked { color: #5b21b6; background: #ede9fe; border: 1px solid #ddd6fe; }
    .audit-card-label {
        color: #8a86a6;
        font-size: 10px;
        font-weight: 850;
        letter-spacing: .9px;
        text-transform: uppercase;
        margin: 8px 0 4px 0;
    }
    .audit-card-result {
        color: #272744;
        font-size: 13px;
        line-height: 1.6;
        overflow-wrap: anywhere;
        white-space: pre-wrap;
    }
    .audit-card-recommendation {
        color: #625b85;
        background: #f7f5ff;
        border: 1px solid #efedff;
        border-radius: 11px;
        padding: 10px 11px;
        margin-top: 11px;
        font-size: 12px;
        line-height: 1.55;
        overflow-wrap: anywhere;
    }
    .audit-summary-strip {
        display: flex;
        flex-wrap: wrap;
        gap: 8px;
        margin: 8px 0 14px 0;
    }
    .audit-summary-pill {
        display: inline-block;
        padding: 7px 11px;
        background: #ffffff;
        border: 1px solid #e7e3ff;
        border-radius: 999px;
        color: #514879;
        font-size: 11px;
        font-weight: 750;
    }
    .audit-section-heading {
        color: #312e81;
        font-size: 19px;
        font-weight: 850;
        margin: 20px 0 6px 0;
    }
    .audit-section-subheading {
        color: #77758b;
        font-size: 12px;
        margin-bottom: 10px;
        line-height: 1.6;
    }
    .method-note {
        background: #f5f3ff;
        border: 1px solid #ddd6fe;
        border-radius: 14px;
        padding: 12px 14px;
        color: #5b4b88;
        font-size: 12px;
        line-height: 1.65;
        margin-top: 10px;
    }

    @media (max-width: 700px) {
        .audit-grid { grid-template-columns: 1fr; }
        .hero { padding: 23px 19px; gap: 14px; }
        .brand-logo { width: 62px; height: 62px; flex-basis: 62px; font-size: 31px; border-radius: 18px; }
        .hero h1 { font-size: 1.8rem !important; }
        .hero p { font-size: 0.9rem; }
        .score-ring { width: 160px; height: 160px; }
        .score-center { width: 124px; height: 124px; }
    }
    

    /* --------------------------------------------------------
       NEXARANK SIGNATURE THEME — midnight teal, ocean blue, coral
       -------------------------------------------------------- */
    .stApp {
        background:
            radial-gradient(circle at 8% 5%, rgba(45, 212, 191, .12), transparent 26%),
            radial-gradient(circle at 96% 12%, rgba(96, 165, 250, .13), transparent 25%),
            linear-gradient(135deg, #f3fbfa 0%, #f5f8ff 53%, #fff8f5 100%) !important;
        color: #17313b;
    }
    .block-container {
        max-width: 1420px;
        padding-top: 1.1rem;
        padding-bottom: 2.4rem;
    }
    .hero {
        position: relative;
        isolation: isolate;
        overflow: hidden;
        display: flex;
        align-items: center;
        gap: 23px;
        background: linear-gradient(118deg, #102a43 0%, #115e59 52%, #0e7490 100%) !important;
        padding: 31px 34px;
        border: 1px solid rgba(255,255,255,.18);
        border-radius: 26px;
        margin-bottom: 24px;
        box-shadow: 0 18px 42px rgba(15, 76, 80, .19);
    }
    .hero::before {
        content: "";
        position: absolute;
        z-index: -1;
        width: 320px;
        height: 320px;
        border: 1px solid rgba(255,255,255,.12);
        border-radius: 50%;
        right: -95px;
        top: -180px;
        box-shadow: 0 0 0 26px rgba(255,255,255,.035), 0 0 0 58px rgba(255,255,255,.025);
    }
    .hero::after {
        content: "";
        position: absolute;
        z-index: -1;
        width: 160px;
        height: 160px;
        right: 16%;
        bottom: -120px;
        border-radius: 50%;
        background: rgba(45, 212, 191, .12);
        filter: blur(3px);
    }
    .brand-logo {
        width: 92px;
        height: 92px;
        flex: 0 0 92px;
        border-radius: 27px;
        display: flex;
        justify-content: center;
        align-items: center;
        background: linear-gradient(145deg, #2dd4bf 0%, #22d3ee 48%, #60a5fa 100%);
        border: 1px solid rgba(255,255,255,.56);
        box-shadow: 0 10px 24px rgba(2, 20, 30, .24), inset 0 1px 0 rgba(255,255,255,.55);
    }
    .brand-logo svg { width: 64px; height: 64px; display: block; }
    .hero-copy { position: relative; z-index: 1; flex: 1; min-width: 0; }
    .hero-badge {
        display: inline-flex;
        align-items: center;
        gap: 8px;
        background: rgba(204, 251, 241, .12);
        color: #ccfbf1 !important;
        border: 1px solid rgba(153, 246, 228, .30);
        padding: 7px 12px;
        border-radius: 30px;
        font-size: 10px;
        font-weight: 850;
        letter-spacing: 1.2px;
        margin-bottom: 10px;
    }
    .hero-pulse {
        width: 7px;
        height: 7px;
        display: inline-block;
        border-radius: 50%;
        background: #5eead4;
        box-shadow: 0 0 0 4px rgba(94,234,212,.14);
    }
    .hero h1 {
        color: #ffffff !important;
        font-size: 2.65rem !important;
        font-weight: 850 !important;
        letter-spacing: -1.2px;
        line-height: 1.1 !important;
        margin: 0 0 9px 0 !important;
    }
    .hero h1 .brand-accent { color: #5eead4; }
    .hero p {
        color: #d8f3f2 !important;
        font-size: .98rem;
        line-height: 1.7;
        margin: 0;
        max-width: 790px;
    }
    .hero-pills {
        display: flex;
        flex-wrap: wrap;
        gap: 8px;
        margin-top: 16px;
    }
    .hero-pills span {
        color: #ecfeff;
        background: rgba(255,255,255,.095);
        border: 1px solid rgba(255,255,255,.17);
        border-radius: 999px;
        padding: 6px 10px;
        font-size: 10px;
        font-weight: 750;
        letter-spacing: .25px;
    }
    .hero-visual {
        z-index: 1;
        flex: 0 0 150px;
        min-width: 150px;
        padding: 18px 14px;
        text-align: center;
        border-radius: 22px;
        background: rgba(2, 25, 38, .20);
        border: 1px solid rgba(255,255,255,.16);
        backdrop-filter: blur(10px);
    }
    .hero-visual-icon { font-size: 30px; line-height: 1; margin-bottom: 8px; }
    .hero-visual-title { color: #fff; font-size: 12px; font-weight: 850; }
    .hero-visual-copy { color: #a7f3d0; font-size: 10px; margin-top: 5px; letter-spacing: .4px; }

    /* Search area and controls */
    [data-testid="stForm"] {
        background: rgba(255,255,255,.87);
        border: 1px solid #d4e9e7;
        border-radius: 20px;
        padding: 18px 20px 10px 20px;
        box-shadow: 0 10px 28px rgba(15, 76, 80, .065);
    }
    [data-testid="stTextInput"] input {
        background: #ffffff !important;
        color: #142f3a !important;
        -webkit-text-fill-color: #142f3a !important;
        caret-color: #0f9488 !important;
        border: 1.5px solid #b7d9d6 !important;
        border-radius: 13px !important;
        min-height: 49px;
        font-size: 16px !important;
    }
    [data-testid="stTextInput"] input::placeholder {
        color: #718792 !important;
        -webkit-text-fill-color: #718792 !important;
        opacity: 1 !important;
    }
    [data-testid="stTextInput"] input:focus {
        border-color: #0f9488 !important;
        box-shadow: 0 0 0 3px rgba(20,184,166,.16) !important;
    }
    [data-testid="stTextInput"] label { color: #164e63 !important; font-weight: 750 !important; }
    [data-testid="stMetric"] {
        background: rgba(255,255,255,.97) !important;
        border: 1px solid #d6e9e7 !important;
        border-radius: 18px !important;
        padding: 17px 19px !important;
        box-shadow: 0 9px 23px rgba(15, 76, 80, .07) !important;
    }
    [data-testid="stMetricLabel"] { color: #55717b !important; font-weight: 700 !important; }
    [data-testid="stMetricValue"] { color: #0f766e !important; font-weight: 850 !important; }
    div.stButton > button[kind="primaryFormSubmit"],
    div.stFormSubmitButton > button,
    button[kind="primary"] {
        background: linear-gradient(105deg, #0f766e 0%, #0891b2 58%, #2563eb 100%) !important;
        color: #ffffff !important;
        border: 0 !important;
        border-radius: 13px !important;
        min-height: 47px;
        font-weight: 800 !important;
        letter-spacing: .1px;
        box-shadow: 0 8px 19px rgba(8,145,178,.20) !important;
        transition: transform .18s ease, box-shadow .18s ease;
    }
    div.stButton > button[kind="primaryFormSubmit"]:hover,
    div.stFormSubmitButton > button:hover,
    button[kind="primary"]:hover {
        transform: translateY(-1px);
        box-shadow: 0 11px 24px rgba(8,145,178,.28) !important;
    }
    div[data-testid="stDownloadButton"] > button {
        background: #ffffff !important;
        color: #0f766e !important;
        border: 1px solid #a8d8d2 !important;
        border-radius: 12px !important;
        font-weight: 800 !important;
        min-height: 44px;
        transition: all .18s ease;
    }
    div[data-testid="stDownloadButton"] > button:hover {
        background: #ecfdf5 !important;
        border-color: #0d9488 !important;
    }

    /* Dashboard and issue cards */
    h2, h3 { color: #123b46 !important; }
    .score-card {
        background: linear-gradient(165deg, #ffffff 0%, #f1fbfa 100%) !important;
        border: 1px solid #cde6e3 !important;
        border-radius: 24px !important;
        box-shadow: 0 12px 30px rgba(15,76,80,.085) !important;
    }
    .score-center { background: #ffffff !important; box-shadow: inset 0 0 0 1px #d9efec !important; }
    .score-caption { color: #164e63 !important; }
    .score-out-of, .score-subcaption, .audit-section-subheading { color: #66818b !important; }
    .section-kicker { color: #0f9488 !important; letter-spacing: 1.35px; }
    .audit-grid { gap: 16px; }
    .audit-card {
        background: rgba(255,255,255,.97) !important;
        border: 1px solid #dcebe9 !important;
        border-left: 5px solid #0d9488 !important;
        border-radius: 19px !important;
        box-shadow: 0 9px 23px rgba(15,76,80,.065) !important;
    }
    .audit-card:hover { box-shadow: 0 14px 30px rgba(15,76,80,.12) !important; }
    .audit-card.status-pass { border-left-color: #16a34a !important; }
    .audit-card.status-fail { border-left-color: #e11d48 !important; }
    .audit-card.status-improve { border-left-color: #d97706 !important; }
    .audit-card.status-not-checked { border-left-color: #0891b2 !important; }
    .audit-card-title, .audit-section-heading { color: #123b46 !important; }
    .audit-card-recommendation {
        color: #496772 !important;
        background: linear-gradient(110deg, #effcf9, #f0f9ff) !important;
        border: 1px solid #d8eeea !important;
        border-radius: 12px !important;
    }
    .audit-summary-pill {
        background: #ffffff !important;
        border: 1px solid #d5e8e6 !important;
        color: #345d66 !important;
    }
    .method-note {
        background: linear-gradient(110deg, #effcf9, #f1f8ff) !important;
        border: 1px solid #cde5e2 !important;
        color: #456671 !important;
        border-radius: 15px !important;
    }
    [data-testid="stAlert"] { border-radius: 15px !important; }
    [data-testid="stProgress"] > div > div > div {
        background: linear-gradient(90deg, #14b8a6, #0891b2, #3b82f6) !important;
    }

    /* Branded footer */
    .app-footer {
        margin-top: 34px;
        padding: 22px 24px 16px 24px;
        border-radius: 22px;
        border: 1px solid #d4e8e5;
        background: linear-gradient(135deg, rgba(255,255,255,.97), rgba(239,252,250,.97));
        box-shadow: 0 10px 26px rgba(15,76,80,.06);
    }
    .footer-top {
        display: flex;
        align-items: center;
        justify-content: space-between;
        flex-wrap: wrap;
        gap: 15px;
        padding-bottom: 17px;
    }
    .footer-brand { display: flex; align-items: center; gap: 12px; }
    .footer-mark {
        width: 43px; height: 43px;
        display: grid; place-items: center;
        border-radius: 13px;
        color: #ffffff;
        font-weight: 900;
        letter-spacing: -1px;
        background: linear-gradient(145deg, #0f766e, #0891b2);
        box-shadow: 0 6px 14px rgba(8,145,178,.20);
    }
    .footer-name { color: #123b46; font-size: 15px; font-weight: 900; }
    .footer-name span { color: #0f9488; font-weight: 750; }
    .footer-tagline { color: #69828b; font-size: 11px; margin-top: 3px; }
    .footer-tags { display: flex; gap: 7px; flex-wrap: wrap; }
    .footer-tags span {
        border: 1px solid #d1e8e4;
        background: #ffffff;
        color: #3e6b72;
        border-radius: 999px;
        padding: 6px 9px;
        font-size: 10px;
        font-weight: 800;
    }
    .footer-bottom {
        display: flex;
        justify-content: space-between;
        flex-wrap: wrap;
        gap: 8px;
        padding-top: 13px;
        border-top: 1px solid #dcece9;
        color: #70868e;
        font-size: 10px;
        line-height: 1.6;
    }

    @media (max-width: 800px) {
        .hero { align-items: flex-start; padding: 22px 19px; gap: 14px; }
        .brand-logo { width: 64px; height: 64px; flex-basis: 64px; border-radius: 19px; }
        .brand-logo svg { width: 46px; height: 46px; }
        .hero h1 { font-size: 1.75rem !important; letter-spacing: -.6px; }
        .hero p { font-size: .88rem; }
        .hero-visual { display: none; }
        .hero-pills span { font-size: 9px; }
    }
    @media (max-width: 500px) {
        .hero { flex-direction: column; }
        .hero h1 { font-size: 1.65rem !important; }
        .footer-top { align-items: flex-start; }
    }

    </style>
    """,
    unsafe_allow_html=True,
)


# ============================================================
# TOP LOGO AND HEADER
# ============================================================
st.markdown(
    """
    <div class="hero">
        <div class="brand-logo" aria-label="NexaRank logo">
            <svg viewBox="0 0 64 64" role="img" aria-hidden="true">
                <circle cx="28" cy="27" r="17" fill="none" stroke="#ffffff" stroke-width="5"/>
                <circle cx="28" cy="27" r="8" fill="none" stroke="#ffffff" stroke-width="2.5" opacity=".78"/>
                <path d="M40 40 L54 54" fill="none" stroke="#ffffff" stroke-width="6" stroke-linecap="round"/>
                <path d="M18 31 L25 24 L30 28 L38 18" fill="none" stroke="#ffffff" stroke-width="3.5" stroke-linecap="round" stroke-linejoin="round"/>
                <path d="M33 18 L38 18 L38 23" fill="none" stroke="#ffffff" stroke-width="3.5" stroke-linecap="round" stroke-linejoin="round"/>
            </svg>
        </div>
        <div class="hero-copy">
            <div class="hero-badge"><span class="hero-pulse"></span> SEO INTELLIGENCE STUDIO</div>
            <h1>NexaRank <span class="brand-accent">SEO Studio</span></h1>
            <p>Clear website signals. Smarter SEO decisions. Audit on-page elements, technical health, structured data and social metadata — all in one workspace.</p>
            <div class="hero-pills">
                <span>✦ ON-PAGE SEO</span>
                <span>◈ TECHNICAL HEALTH</span>
                <span>↗ REPORT EXPORTS</span>
            </div>
        </div>
        <div class="hero-visual">
            <div class="hero-visual-icon">⌁</div>
            <div class="hero-visual-title">WEBSITE INTELLIGENCE</div>
            <div class="hero-visual-copy">SCAN · REVIEW · IMPROVE</div>
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

st.markdown('<div class="section-kicker">START A NEW AUDIT</div>', unsafe_allow_html=True)
st.write("Enter the public webpage you want to analyze. Press Enter or use the button to start.")


# ============================================================
# URL HELPERS
# ============================================================
def normalize_url(raw_url):
    raw_url = (raw_url or "").strip()
    if not raw_url:
        raise ValueError("Please enter a website URL first.")

    if not raw_url.startswith(("https://", "http://")):
        raw_url = "https://" + raw_url

    parsed = urlparse(raw_url)
    if (
        parsed.scheme not in ("http", "https")
        or not parsed.hostname
        or parsed.username
        or parsed.password
    ):
        raise ValueError("Please enter a valid public HTTP or HTTPS URL, such as https://example.com")

    return raw_url


def is_public_host(hostname):
    """Return True only when a hostname resolves exclusively to public IPs."""
    if not hostname:
        return False

    try:
        addresses = socket.getaddrinfo(hostname, None, type=socket.SOCK_STREAM)
        if not addresses:
            return False

        for address in addresses:
            ip = ipaddress.ip_address(address[4][0])
            if not ip.is_global:
                return False
        return True
    except (socket.gaierror, ValueError, OSError):
        return False


def add_check(rows, name, status, result, recommendation, weight):
    rows.append({
        "SEO Check": name,
        "Status": status,
        "Result": result,
        "Recommendation": recommendation,
        "Weight": weight,
    })


# ============================================================
# INTERNAL LINKS
# ============================================================
def check_internal_links(session, links, page_url):
    page_host = (urlparse(page_url).hostname or "").lower()
    candidates = []

    for link in links:
        href = link.get("href", "").strip()
        if not href or href.startswith(("#", "mailto:", "tel:", "javascript:")):
            continue

        absolute_url = urldefrag(urljoin(page_url, href))[0]
        parsed = urlparse(absolute_url)
        if parsed.scheme not in ("http", "https") or not parsed.hostname:
            continue
        if parsed.hostname.lower() == page_host and absolute_url not in candidates:
            candidates.append(absolute_url)

    candidates = candidates[:MAX_LINKS_TO_CHECK]
    if not candidates:
        return (
            "NOT CHECKED",
            "No internal links found to test",
            "Add relevant internal links where they help visitors navigate.",
        )

    broken = []
    could_not_check = []

    for link_url in candidates:
        try:
            # Only test a link after confirming its hostname is public.
            link_host = urlparse(link_url).hostname
            if not is_public_host(link_host):
                could_not_check.append(link_url)
                continue

            response = session.get(
                link_url,
                timeout=REQUEST_TIMEOUT,
                allow_redirects=True,
                stream=True,
            )
            status_code = response.status_code
            response.close()
            if status_code >= 400:
                broken.append(f"{link_url} (HTTP {status_code})")
        except requests.RequestException:
            could_not_check.append(link_url)

    if broken:
        return (
            "FAIL",
            f"{len(broken)} broken/error link(s) out of {len(candidates)} checked. " + "; ".join(broken[:5]),
            "Fix incorrect URLs and links returning HTTP 4xx/5xx errors.",
        )
    if could_not_check:
        return (
            "NEEDS IMPROVEMENT",
            f"{len(could_not_check)} link(s) could not be verified; {len(candidates)} attempted",
            "Manually test links that timed out or blocked automated requests.",
        )
    return (
        "PASS",
        f"All {len(candidates)} checked internal links responded below HTTP 400",
        "Continue checking internal links regularly.",
    )


# ============================================================
# MAIN SEO AUDIT
# ============================================================
def analyze_website(website):
    session = requests.Session()
    session.headers.update({"User-Agent": USER_AGENT})

    try:
        parsed_input = urlparse(website)
        if not is_public_host(parsed_input.hostname):
            raise ValueError(
                "This tool could not verify a public website address. Check the URL and try again. "
                "Localhost and private network addresses are not allowed."
            )

        response = session.get(website, timeout=REQUEST_TIMEOUT, allow_redirects=True)
        final_url = response.url
        final_parsed = urlparse(final_url)

        if not is_public_host(final_parsed.hostname):
            raise ValueError("The website redirected to a non-public host, so analysis was stopped for safety.")

        soup = BeautifulSoup(response.text, "html.parser")
        rows = []

        # 1. HTTP response
        if response.status_code == 200:
            add_check(rows, "HTTP Status", "PASS", f"HTTP {response.status_code}", "The page returned HTTP 200.", 15)
        else:
            add_check(rows, "HTTP Status", "FAIL", f"HTTP {response.status_code}", "Investigate the response code. The page should normally return HTTP 200 when accessible and working.", 15)

        # 2. HTTPS
        if final_parsed.scheme == "https":
            add_check(rows, "HTTPS", "PASS", "HTTPS is enabled", "The final page URL uses HTTPS.", 10)
        else:
            add_check(rows, "HTTPS", "FAIL", "Page uses HTTP", "Configure HTTPS and redirect visitors to the secure URL.", 10)

        # 3. Page title
        title_tag = soup.find("title")
        title = title_tag.get_text(" ", strip=True) if title_tag else ""
        if title:
            add_check(rows, "Page Title", "PASS", title, "A title element is present.", 10)
        else:
            add_check(rows, "Page Title", "FAIL", "Missing", "Add a unique, descriptive title element.", 10)

        # 4. Title length
        if not title:
            add_check(rows, "Title Length", "NOT CHECKED", "No title", "Add a title before reviewing its length.", 3)
        elif 30 <= len(title) <= 60:
            add_check(rows, "Title Length", "PASS", f"{len(title)} characters", "The title length is within a common guideline.", 3)
        else:
            add_check(rows, "Title Length", "NEEDS IMPROVEMENT", f"{len(title)} characters", "Review whether the title is clear and concise. 30–60 characters is only a guideline.", 3)

        # 5. Meta description
        meta_description = soup.find(
            "meta",
            attrs={"name": lambda value: value and value.lower() == "description"},
        )
        description = meta_description.get("content", "").strip() if meta_description else ""
        if description:
            add_check(rows, "Meta Description", "PASS", description, "A meta description is present.", 8)
        else:
            add_check(rows, "Meta Description", "FAIL", "Missing", "Add a useful description that accurately summarizes the page.", 8)

        # 6. Description length
        if not description:
            add_check(rows, "Description Length", "NOT CHECKED", "No description", "Add a meta description before reviewing its length.", 2)
        elif 120 <= len(description) <= 160:
            add_check(rows, "Description Length", "PASS", f"{len(description)} characters", "The length is within a common guideline.", 2)
        else:
            add_check(rows, "Description Length", "NEEDS IMPROVEMENT", f"{len(description)} characters", "Review clarity and usefulness. 120–160 characters is a guideline, not a strict rule.", 2)

        # 7. H1
        h1_tags = soup.find_all("h1")
        h1_text = " | ".join(heading.get_text(" ", strip=True) for heading in h1_tags)
        if len(h1_tags) == 1 and h1_text:
            add_check(rows, "Main H1", "PASS", h1_text, "One non-empty H1 heading was found.", 8)
        elif len(h1_tags) == 0:
            add_check(rows, "Main H1", "FAIL", "No H1 found", "Add a clear main heading when appropriate for the page.", 8)
        else:
            add_check(rows, "Main H1", "NEEDS IMPROVEMENT", f"{len(h1_tags)} H1 tags", "Review whether the page has a clear, meaningful main heading. Multiple H1s are not automatically a Google penalty.", 8)

        # 8. Heading structure
        headings = {f"H{i}": len(soup.find_all(f"h{i}")) for i in range(1, 7)}
        heading_summary = ", ".join(f"{key}: {value}" for key, value in headings.items())
        if any(headings[f"H{i}"] for i in range(1, 7)):
            add_check(rows, "Heading Structure", "PASS", heading_summary, "Review headings for a logical structure and useful content.", 5)
        else:
            add_check(rows, "Heading Structure", "FAIL", "No heading tags found", "Use headings to organize the page content where appropriate.", 5)

        # 9. Image alt attributes
        images = soup.find_all("img")
        missing_alt = [img for img in images if not img.has_attr("alt")]
        if not images:
            add_check(rows, "Image ALT Text", "NOT CHECKED", "No images found", "No image ALT check was applicable to this HTML page.", 7)
        elif not missing_alt:
            add_check(rows, "Image ALT Text", "PASS", f"All {len(images)} images have an ALT attribute", "Ensure ALT text is descriptive for meaningful images. Decorative images can use alt=\"\".", 7)
        else:
            add_check(rows, "Image ALT Text", "FAIL", f"{len(missing_alt)} of {len(images)} images lack ALT", "Add appropriate ALT text to meaningful images. Use alt=\"\" for decorative images.", 7)

        # 10. Canonical URL
        canonical = soup.find(
            "link",
            rel=lambda value: value and "canonical" in [
                part.lower() for part in (value if isinstance(value, list) else value.split())
            ],
        )
        canonical_url = (
            urljoin(final_url, canonical.get("href", "").strip())
            if canonical and canonical.get("href", "").strip()
            else ""
        )
        if canonical_url:
            add_check(rows, "Canonical URL", "PASS", canonical_url, "Verify that the canonical points to the preferred page URL.", 8)
        else:
            add_check(rows, "Canonical URL", "NEEDS IMPROVEMENT", "Not found", "Review whether this page needs a canonical tag. It is not required on every page.", 8)

        # 11. Mobile viewport
        viewport = soup.find(
            "meta",
            attrs={"name": lambda value: value and value.lower() == "viewport"},
        )
        if viewport and viewport.get("content", "").strip():
            add_check(rows, "Mobile Viewport", "PASS", viewport.get("content", "").strip(), "The viewport meta tag is present. Actual mobile usability requires a separate test.", 7)
        else:
            add_check(rows, "Mobile Viewport", "FAIL", "Not found", "Add a suitable viewport meta tag and test the page on mobile.", 7)

        # 12. Indexing directives
        robots_meta = soup.find_all(
            "meta",
            attrs={"name": lambda value: value and value.lower() in ("robots", "googlebot")},
        )
        robots_values = [tag.get("content", "").lower() for tag in robots_meta]
        x_robots = response.headers.get("X-Robots-Tag", "").lower()
        directives = robots_values + ([x_robots] if x_robots else [])
        noindex_found = any("noindex" in value for value in directives)
        if noindex_found:
            add_check(rows, "Indexing Directives", "FAIL", "; ".join(directives), "A noindex directive was detected. Confirm that the page is intentionally excluded from search results.", 10)
        else:
            add_check(rows, "Indexing Directives", "PASS", "; ".join(directives) if directives else "No noindex directive detected", "This check does not prove that Google can index the page. Check robots.txt, rendering and Search Console too.", 10)

        # 13. Internal links count
        links = soup.find_all("a", href=True)
        internal_links = []
        page_host = (final_parsed.hostname or "").lower()
        for link in links:
            absolute = urljoin(final_url, link.get("href", "").strip())
            link_host = (urlparse(absolute).hostname or "").lower()
            if link_host == page_host and urlparse(absolute).scheme in ("http", "https"):
                internal_links.append(absolute)

        if internal_links:
            add_check(rows, "Internal Links", "PASS", f"{len(set(internal_links))} internal link(s) found", "Make sure important pages link to each other with useful anchor text.", 3)
        else:
            add_check(rows, "Internal Links", "NEEDS IMPROVEMENT", "None found", "Add relevant internal links if appropriate for this page.", 3)

        # 14. Test a limited sample of links
        with st.spinner("Checking a sample of internal links..."):
            link_status, link_result, link_recommendation = check_internal_links(session, links, final_url)
        add_check(rows, "Sample Internal Link Test", link_status, link_result, link_recommendation, 2)

        # 15. HTML language attribute
        html_tag = soup.find("html")
        html_language = (html_tag.get("lang", "").strip() if html_tag else "")
        if html_language:
            add_check(
                rows, "HTML Language", "PASS", html_language,
                "Keep the language code accurate for the page's primary content.", 2
            )
        else:
            add_check(
                rows, "HTML Language", "NEEDS IMPROVEMENT", "Missing lang attribute",
                "Add an appropriate lang attribute to the opening html element for accessibility and language interpretation.", 2
            )

        # 16. Approximate readable word count (not a content-quality verdict)
        content_soup = BeautifulSoup(response.text, "html.parser")
        for unwanted in content_soup(["script", "style", "noscript", "svg", "template"]):
            unwanted.decompose()
        body_node = content_soup.body or content_soup
        visible_text = body_node.get_text(" ", strip=True)
        word_count = len(re.findall(r"\b[\w’'-]+\b", visible_text, flags=re.UNICODE))
        if word_count >= 300:
            add_check(
                rows, "Approximate Page Word Count", "PASS", f"About {word_count} words",
                "Check that the content satisfies search intent. Word count alone does not determine rankings; short pages can be appropriate.", 2
            )
        elif word_count >= 100:
            add_check(
                rows, "Approximate Page Word Count", "NEEDS IMPROVEMENT", f"About {word_count} words",
                "Review whether the page gives visitors enough useful information. This is only a rough HTML text estimate, not a target word count.", 2
            )
        else:
            add_check(
                rows, "Approximate Page Word Count", "NEEDS IMPROVEMENT", f"About {word_count} words",
                "Confirm the page is intentionally concise and that key information is visible in the returned HTML. This tool may not see JavaScript-rendered text.", 2
            )

        # 17. Open Graph metadata for social sharing
        og_title = soup.find("meta", property="og:title")
        og_description = soup.find("meta", property="og:description")
        og_image = soup.find("meta", property="og:image")
        og_present = sum(bool(tag and tag.get("content", "").strip()) for tag in (og_title, og_description, og_image))
        if og_present == 3:
            add_check(
                rows, "Open Graph Metadata", "PASS", "og:title, og:description and og:image found",
                "Keep social preview metadata accurate and use an accessible, representative image. Open Graph is primarily for sharing previews, not a direct ranking score.", 2
            )
        elif og_present > 0:
            add_check(
                rows, "Open Graph Metadata", "NEEDS IMPROVEMENT", f"{og_present}/3 core Open Graph tags found",
                "Consider adding og:title, og:description and og:image for more consistent social sharing previews.", 2
            )
        else:
            add_check(
                rows, "Open Graph Metadata", "NEEDS IMPROVEMENT", "Core Open Graph tags not found",
                "Add Open Graph tags if the page is likely to be shared on social platforms. These tags are not a direct Google ranking requirement.", 2
            )

        # 18. Structured data syntax (JSON-LD)
        jsonld_scripts = soup.find_all(
            "script", attrs={"type": lambda value: value and "ld+json" in value.lower()}
        )
        if not jsonld_scripts:
            add_check(
                rows, "Structured Data (JSON-LD)", "NEEDS IMPROVEMENT", "No JSON-LD block detected",
                "Consider relevant schema markup where appropriate, then validate it with a dedicated structured-data testing tool. Schema is not required on every page.", 3
            )
        else:
            jsonld_valid = 0
            jsonld_invalid = 0
            for schema_script in jsonld_scripts:
                try:
                    json.loads(schema_script.string or schema_script.get_text())
                    jsonld_valid += 1
                except (json.JSONDecodeError, TypeError):
                    jsonld_invalid += 1
            if jsonld_valid and not jsonld_invalid:
                add_check(
                    rows, "Structured Data (JSON-LD)", "PASS", f"{jsonld_valid} valid JSON-LD block(s) found",
                    "Syntax looks like valid JSON, but this does not confirm that schema properties are eligible for rich results. Validate the structured data separately.", 3
                )
            elif jsonld_valid:
                add_check(
                    rows, "Structured Data (JSON-LD)", "NEEDS IMPROVEMENT", f"{jsonld_valid} valid and {jsonld_invalid} invalid block(s)",
                    "Fix invalid JSON-LD blocks and validate the schema vocabulary and required properties.", 3
                )
            else:
                add_check(
                    rows, "Structured Data (JSON-LD)", "FAIL", f"{jsonld_invalid} JSON-LD block(s) could not be parsed",
                    "Fix the JSON syntax and validate structured data. A parsed JSON block alone does not guarantee eligibility for rich results.", 3
                )

        # 19. Hreflang language/region alternates (optional)
        hreflang_links = soup.find_all(
            "link", rel=lambda value: value and "alternate" in (
                value if isinstance(value, list) else str(value).split()
            ), hreflang=True
        )
        if hreflang_links:
            add_check(
                rows, "Hreflang Annotations", "PASS", f"{len(hreflang_links)} alternate language link(s) found",
                "Review language codes, target URLs and reciprocal annotations. Presence alone does not validate the hreflang setup.", 1
            )
        else:
            add_check(
                rows, "Hreflang Annotations", "NOT CHECKED", "No hreflang annotations found",
                "Usually only needed for pages with language or regional variants.", 1
            )

        # 20. Robots.txt availability (helpful, but not mandatory for every site)
        origin = f"{final_parsed.scheme}://{final_parsed.netloc}"
        robots_url = urljoin(origin + "/", "robots.txt")
        robots_response = None
        try:
            if is_public_host(urlparse(robots_url).hostname):
                robots_response = session.get(
                    robots_url, timeout=4, allow_redirects=True
                )
                if not is_public_host(urlparse(robots_response.url).hostname):
                    robots_response = None
        except requests.RequestException:
            robots_response = None

        robots_text = ""
        if robots_response is not None and robots_response.status_code == 200:
            robots_text = robots_response.text[:200000]
            add_check(
                rows, "Robots.txt", "PASS", f"Found at {robots_url}",
                "Review its rules carefully. A robots.txt file controls crawler access; it does not itself guarantee indexing.", 2
            )
        elif robots_response is not None and robots_response.status_code == 404:
            add_check(
                rows, "Robots.txt", "NEEDS IMPROVEMENT", "Not found (HTTP 404)",
                "A robots.txt file is optional, but creating one can help document crawler rules for the site.", 1
            )
        else:
            add_check(
                rows, "Robots.txt", "NOT CHECKED", "Could not verify robots.txt",
                "Check the robots.txt URL manually; the server may block automated requests.", 1
            )

        # 21. Sitemap discovery: robots.txt sitemap directive first, common paths second
        sitemap_candidates = re.findall(r"(?im)^\s*sitemap:\s*(\S+)", robots_text)
        if not sitemap_candidates:
            sitemap_candidates = [
                urljoin(origin + "/", "sitemap.xml"),
                urljoin(origin + "/", "sitemap_index.xml"),
                urljoin(origin + "/", "wp-sitemap.xml"),
            ]
        sitemap_found = ""
        sitemap_not_checked = False
        for sitemap_url in sitemap_candidates[:3]:
            try:
                if not is_public_host(urlparse(sitemap_url).hostname):
                    continue
                sitemap_response = session.get(
                    sitemap_url, timeout=4, allow_redirects=True
                )
                if not is_public_host(urlparse(sitemap_response.url).hostname):
                    sitemap_not_checked = True
                    continue
                if sitemap_response.status_code == 200 and re.search(
                    r"<(urlset|sitemapindex|rss|feed)\b", sitemap_response.text[:10000], re.IGNORECASE
                ):
                    sitemap_found = sitemap_url
                    break
            except requests.RequestException:
                sitemap_not_checked = True

        if sitemap_found:
            add_check(
                rows, "XML Sitemap", "PASS", sitemap_found,
                "Make sure the sitemap lists preferred, canonical URLs and is updated when important pages change.", 3
            )
        elif sitemap_not_checked:
            add_check(
                rows, "XML Sitemap", "NOT CHECKED", "Could not fully verify a sitemap",
                "Check your sitemap URL and ensure it returns valid XML. Automated access may have been blocked.", 1
            )
        else:
            add_check(
                rows, "XML Sitemap", "NEEDS IMPROVEMENT", "No sitemap found at common locations",
                "A sitemap is useful for discovery on many sites but is not mandatory. Check the sitemap URL in your CMS or robots.txt.", 2
            )

        # 22. Initial HTTP response-header timing (not a Core Web Vital)
        response_seconds = response.elapsed.total_seconds()
        if response_seconds <= 1.5:
            add_check(
                rows, "Initial Response Time Estimate", "PASS", f"{response_seconds:.2f} seconds",
                "This is the time until the HTTP response headers were received by this tool. It is affected by network conditions and is not a full-page speed or Core Web Vitals measurement.", 3
            )
        elif response_seconds <= 3.0:
            add_check(
                rows, "Initial Response Time Estimate", "NEEDS IMPROVEMENT", f"{response_seconds:.2f} seconds",
                "Review hosting, caching and server response, then retest from a performance testing tool. This estimate is affected by network conditions and is not a Core Web Vitals measurement.", 3
            )
        else:
            add_check(
                rows, "Initial Response Time Estimate", "FAIL", f"{response_seconds:.2f} seconds",
                "Investigate redirects, hosting, caching and server response. Confirm the result with a performance testing tool before drawing conclusions.", 3
            )

        # 23. Social card metadata (optional)
        twitter_card = soup.find(
            "meta", attrs={"name": lambda value: value and value.lower() == "twitter:card"}
        )
        if twitter_card and twitter_card.get("content", "").strip():
            add_check(
                rows, "Social Card Metadata", "PASS", twitter_card.get("content", "").strip(),
                "Confirm social preview title, description and image are appropriate for the sharing platform.", 1
            )
        else:
            add_check(
                rows, "Social Card Metadata", "NOT CHECKED", "Twitter/X card tag not found",
                "Optional: add social card metadata if your content is shared on X or other compatible platforms.", 1
            )

        # Weighted score; NOT CHECKED checks are excluded from calculation.
        report = pd.DataFrame(rows)
        eligible = report[report["Status"] != "NOT CHECKED"].copy()
        total_weight = eligible["Weight"].sum()
        points = {"PASS": 1.0, "NEEDS IMPROVEMENT": 0.5, "FAIL": 0.0}
        earned = sum(row["Weight"] * points.get(row["Status"], 0) for _, row in eligible.iterrows())
        score = round((earned / total_weight) * 100) if total_weight else 0

        return {
            "report": report,
            "score": score,
            "passed": int((report["Status"] == "PASS").sum()),
            "failed": int((report["Status"] == "FAIL").sum()),
            "needs_improvement": int((report["Status"] == "NEEDS IMPROVEMENT").sum()),
            "not_checked": int((report["Status"] == "NOT CHECKED").sum()),
            "final_url": final_url,
            "http_status": response.status_code,
        }
    finally:
        session.close()


# ============================================================
# PDF REPORT GENERATOR
# ============================================================
def make_pdf(result):
    pdf_buffer = BytesIO()
    pdf_doc = SimpleDocTemplate(
        pdf_buffer,
        pagesize=A4,
        rightMargin=36,
        leftMargin=36,
        topMargin=36,
        bottomMargin=36,
    )
    styles = getSampleStyleSheet()
    small_style = ParagraphStyle(
        "SmallText",
        parent=styles["BodyText"],
        fontSize=7,
        leading=9,
        wordWrap="CJK",
    )
    header_style = ParagraphStyle(
        "TableHeader",
        parent=small_style,
        textColor=colors.white,
    )

    content = [
        Paragraph("NexaRank SEO Audit Report", styles["Title"]),
        Spacer(1, 14),
        Paragraph(f"<b>Website:</b> {escape(str(result['final_url']))}", styles["BodyText"]),
        Spacer(1, 8),
        Paragraph(f"<b>SEO Score:</b> {result['score']}/100", styles["Heading2"]),
        Paragraph(f"<b>HTTP Status:</b> {result['http_status']}", styles["BodyText"]),
        Spacer(1, 8),
        Paragraph(
            f"<b>Passed:</b> {result['passed']} &nbsp; | &nbsp; "
            f"<b>Failed:</b> {result['failed']} &nbsp; | &nbsp; "
            f"<b>Needs Improvement:</b> {result['needs_improvement']} &nbsp; | &nbsp; "
            f"<b>Not Checked:</b> {result['not_checked']}",
            styles["BodyText"],
        ),
        Spacer(1, 16),
        Paragraph("Detailed SEO Checks", styles["Heading2"]),
        Spacer(1, 8),
    ]

    pdf_report = result["report"].drop(columns=["Weight"], errors="ignore")
    table_data = [[Paragraph(escape(str(col)), header_style) for col in pdf_report.columns]]
    for row in pdf_report.astype(str).itertuples(index=False, name=None):
        table_data.append([Paragraph(escape(value), small_style) for value in row])

    usable_width = A4[0] - 72
    widths = [usable_width * 0.20, usable_width * 0.14, usable_width * 0.27, usable_width * 0.39]
    pdf_table = Table(table_data, colWidths=widths, repeatRows=1)
    pdf_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0F766E")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))
    content.append(pdf_table)
    pdf_doc.build(content)
    pdf_buffer.seek(0)
    return pdf_buffer.getvalue()


# ============================================================
# COLORFUL HTML TABLE RENDERER
# Escape every audit value before placing it into HTML.
# ============================================================
def render_html_report(report):
    """Render each SEO check as a responsive card instead of a table."""
    status_config = {
        "PASS": ("pass", "✅ PASS"),
        "FAIL": ("fail", "❌ FAIL"),
        "NEEDS IMPROVEMENT": ("improve", "🟠 NEEDS IMPROVEMENT"),
        "NOT CHECKED": ("not-checked", "⚪ NOT CHECKED"),
    }

    cards = []
    for _, row in report.iterrows():
        name = escape(str(row.get("SEO Check", "SEO Check")))
        status = str(row.get("Status", "NOT CHECKED")).strip().upper()
        result_text = escape(str(row.get("Result", "—")))
        recommendation = escape(str(row.get("Recommendation", "—")))
        css_status, status_label = status_config.get(
            status, ("not-checked", escape(status))
        )
        status_label = escape(status_label)
        cards.append(
            f'<article class="audit-card status-{css_status}">'
            f'<div class="audit-card-top">'
            f'<div class="audit-card-title">{name}</div>'
            f'<span class="audit-status {css_status}">{status_label}</span>'
            f'</div>'
            f'<div class="audit-card-label">Finding</div>'
            f'<div class="audit-card-result">{result_text}</div>'
            f'<div class="audit-card-recommendation">'
            f'<strong>💡 Recommendation:</strong> {recommendation}'
            f'</div>'
            f'</article>'
        )

    counts = report["Status"].value_counts().to_dict() if not report.empty else {}
    summary = (
        f'<div class="audit-summary-strip">'
        f'<span class="audit-summary-pill">🔎 {len(report)} checks</span>'
        f'<span class="audit-summary-pill">✅ {counts.get("PASS", 0)} passed</span>'
        f'<span class="audit-summary-pill">❌ {counts.get("FAIL", 0)} failed</span>'
        f'<span class="audit-summary-pill">🟠 {counts.get("NEEDS IMPROVEMENT", 0)} need improvement</span>'
        f'<span class="audit-summary-pill">⚪ {counts.get("NOT CHECKED", 0)} not checked</span>'
        f'</div>'
    )
    return summary + '<div class="audit-grid">' + "".join(cards) + '</div>'


# ============================================================
# SESSION STATE: results stay visible after button/download clicks
# ============================================================
if "seo_result" not in st.session_state:
    st.session_state.seo_result = None
if "seo_error" not in st.session_state:
    st.session_state.seo_error = None


# ============================================================
# SEARCH FORM
# Press Enter in the URL box OR click the Analyze button.
# clear_on_submit=False keeps the user's typed URL in the field.
# ============================================================
with st.form("seo_analyzer_form", clear_on_submit=False):
    website = st.text_input(
        "Website URL",
        placeholder="Type a website URL here...",
        help="Enter the website address you want to analyze.",
        key="website_url",
    )
    analyze_clicked = st.form_submit_button(
        "🚀 Analyze Website",
        type="primary",
        use_container_width=True,
    )

if analyze_clicked:
    st.session_state.seo_result = None
    st.session_state.seo_error = None
    try:
        clean_url = normalize_url(website)
        with st.spinner("🔍 Analyzing page SEO and checking internal links..."):
            st.session_state.seo_result = analyze_website(clean_url)
    except ValueError as error:
        st.session_state.seo_error = str(error)
    except requests.RequestException as error:
        st.session_state.seo_error = (
            f"Could not access the webpage: {error}. The website may block automated requests or be unavailable."
        )
    except Exception as error:
        st.session_state.seo_error = f"Unexpected error: {error}"

if st.session_state.seo_error:
    st.error(st.session_state.seo_error)


# ============================================================
# RESULTS DASHBOARD WITH CIRCULAR SEO SCORE
# ============================================================
result = st.session_state.seo_result

if result is not None:
    st.markdown("---")
    st.markdown('<div class="section-kicker">Your results</div>', unsafe_allow_html=True)
    st.subheader("📊 SEO Audit Dashboard")
    st.caption(f"Page analyzed: {result['final_url']}")

    if result["score"] >= 85:
        score_color = "#16a34a"
        score_label = "Strong"
        score_message = "Strong result for the checks performed. Continue monitoring the page."
    elif result["score"] >= 65:
        score_color = "#d97706"
        score_label = "Fair"
        score_message = "Some SEO improvements may be needed. Review the recommendations below."
    else:
        score_color = "#e11d48"
        score_label = "Needs Work"
        score_message = "Several checked items need attention. Start with the failed checks below."

    score_degrees = result["score"] * 3.6
    score_col, metrics_col = st.columns([1, 2.4], gap="large")

    with score_col:
        st.markdown(
            f"""
            <div class="score-card">
                <div class="section-kicker">Overall SEO Score</div>
                <div class="score-ring" style="--score-deg:{score_degrees}deg; --score-color:{score_color};">
                    <div class="score-center">
                        <div class="score-number">{result['score']}</div>
                        <div class="score-out-of">out of 100</div>
                    </div>
                </div>
                <div class="score-caption">{score_label}</div>
                <div class="score-subcaption">Based on the checks performed</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with metrics_col:
        metric1, metric2 = st.columns(2)
        metric3, metric4 = st.columns(2)
        with metric1:
            st.metric("✅ Passed", result["passed"])
        with metric2:
            st.metric("❌ Failed", result["failed"])
        with metric3:
            st.metric("🛠️ Needs Improvement", result["needs_improvement"])
        with metric4:
            st.metric("➖ Not Checked", result["not_checked"])
        st.progress(result["score"] / 100)
        if result["score"] >= 85:
            st.success("🎉 " + score_message)
        elif result["score"] >= 65:
            st.info("👍 " + score_message)
        else:
            st.warning("⚠️ " + score_message)

    st.markdown('<div class="audit-section-heading">🧾 SEO Findings & Recommendations</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="audit-section-subheading">Every check is shown as an individual card. '
        'Use the status badges to prioritize what to review first.</div>',
        unsafe_allow_html=True,
    )
    visible_report = result["report"].drop(columns=["Weight"], errors="ignore")
    st.markdown(render_html_report(visible_report), unsafe_allow_html=True)

    st.subheader("📥 Download Your Reports")
    download_col1, download_col2 = st.columns(2)
    csv_data = result["report"].to_csv(index=False).encode("utf-8-sig")
    pdf_data = make_pdf(result)
    with download_col1:
        st.download_button(
            "📄 Download SEO Report (CSV)",
            data=csv_data,
            file_name="nexarank_seo_report.csv",
            mime="text/csv",
            use_container_width=True,
        )
    with download_col2:
        st.download_button(
            "📘 Download SEO Report (PDF)",
            data=pdf_data,
            file_name="nexarank_seo_audit_report.pdf",
            mime="application/pdf",
            use_container_width=True,
        )

    st.markdown(
        '<div class="method-note"><strong>How to interpret this score:</strong> '
        'It is a weighted checklist score calculated from the checks this tool can observe. '
        'PASS earns full points, NEEDS IMPROVEMENT earns half points, FAIL earns zero, '
        'and NOT CHECKED items are excluded. It is not an official Google score and cannot '
        'predict an exact ranking. Real rankings also depend on search intent, content quality, '
        'competition, links, JavaScript rendering, actual Core Web Vitals and Google indexing. '
        'Response time here is a simple request-duration estimate, not a Core Web Vitals test.</div>',
        unsafe_allow_html=True,
    )

st.markdown(
    """
    <footer class="app-footer">
        <div class="footer-top">
            <div class="footer-brand">
                <div class="footer-mark">NR</div>
                <div>
                    <div class="footer-name">NexaRank <span>SEO Studio</span></div>
                    <div class="footer-tagline">Clear signals. Better SEO decisions.</div>
                </div>
            </div>
            <div class="footer-tags">
                <span>PYTHON POWERED</span>
                <span>TECHNICAL SEO</span>
                <span>PDF + CSV EXPORT</span>
            </div>
        </div>
        <div class="footer-bottom">
            <span>© 2026 NexaRank SEO Studio · Built with Python and Streamlit</span>
            <span>Scores are diagnostic estimates, not official Google scores.</span>
        </div>
    </footer>
    """,
    unsafe_allow_html=True,
)
