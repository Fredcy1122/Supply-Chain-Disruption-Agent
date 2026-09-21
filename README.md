# Supply-Chain Disruption Agent

An Azure-based AI solution that predicts shipment delays, investigates
likely disruption causes, recommends alternative actions, and generates
an operational briefing.

## Problem Statement

Late shipments can lead to operational disruption and stockouts.
Operations teams need earlier visibility into shipment risks and
recommended actions.

## Proposed Solution

The application will:

1. Collect shipment, inventory, weather, supplier, and related data.
2. Predict the probability of shipment delay.
3. Investigate the likely causes of disruption.
4. Retrieve supplier and operational procedure information.
5. Recommend alternative routes, suppliers, or actions.
6. Generate a concise disruption briefing.
7. Present the results through a web application deployed on Azure.

## Core Technologies

- Python
- FastAPI
- React
- Machine learning
- Retrieval-Augmented Generation
- AI agent tool-calling
- Azure
- GitHub Actions

## Project Architecture

```text
React Frontend
      |
FastAPI Backend
      |
AI Agent Orchestrator
  |       |        |
ML Model  Tools    RAG
  |       |        |
Shipment  Weather  Supplier and procedure documents
Data      APIs
