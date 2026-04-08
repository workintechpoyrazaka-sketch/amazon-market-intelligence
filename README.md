# Amazon Market Intelligence

Amazon sellers make pricing decisions blindly. I built the thing that fixes that.

## What This Is

A full-stack data intelligence pipeline that processes 37 GB of product metadata and 571M customer reviews to discover what actually drives success on Amazon -- and turns those discoveries into an interactive tool any seller can use.

## The Question

What predicts success on Amazon -- and is it universal or category-dependent?

## Scale

- 1.4M Kaggle products with prices, ratings, sales
- 35M McAuley Lab metadata with stores, brands, descriptions
- 571M McAuley Lab reviews with text, timestamps, ratings
- 33 product categories analyzed

## Stack

DuckDB - Python - Jupyter - Plotly - scikit-learn - XGBoost - VADER - Streamlit

## The Tool -- 5 Modes

- Category Scout: Where should I sell? Is my category growing or dying?
- Competitive Positioning: How should I price? Who am I competing with?
- Health Check: What am I doing wrong? How long until traction?
- Voice of Customer: What are customers actually saying?
- Review Trust Score: Can I trust these reviews?

## Pipeline

Raw Data (200+ GB) --> Bronze (flag, dont filter) --> Silver (join, enrich, classify) --> Gold (analysis-ready) --> Tool

## Status

In Progress -- Pipeline build + EDA phase

## Author

Poi -- Data professional building real products from real data.
