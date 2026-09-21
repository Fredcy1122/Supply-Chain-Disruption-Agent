# Supply-Chain Disruption Agent

An Azure-based AI application that predicts shipment delays, investigates
likely disruption causes, recommends alternative actions, and generates
an operational briefing.

## Problem Statement

Late shipments can create operational disruptions and stockouts.
Operations teams need early visibility into shipment risks and practical
recommendations for responding to disruptions.

## Proposed Solution

The application will:

1. Process shipment, inventory, weather, supplier, and related data.
2. Predict the probability of a shipment delay.
3. Investigate likely causes of the disruption.
4. Retrieve relevant supplier and operational procedure information.
5. Recommend alternative routes, suppliers, or actions.
6. Generate a concise briefing for the operations team.
7. Present the results through a web application deployed on Azure.

## Minimum Viable Product

The first version will support this workflow:

1. A user selects or enters a shipment.
2. The system calculates a delay-risk score.
3. The agent checks shipment and weather information.
4. The system identifies likely contributing factors.
5. RAG retrieves relevant supplier or procedure information.
6. The system recommends an operational action.
7. The system generates an operations briefing.
8. The frontend displays the complete result.

## Core Technologies

- Python
- FastAPI
- React
- Machine learning
- Retrieval-Augmented Generation
- AI agent tool-calling
- Microsoft Azure
- GitHub Actions


## Proposed Repository Structure

```text
supply-chain-disruption-agent/
├── .github/
│   ├── ISSUE_TEMPLATE/
│   ├── workflows/
│   └── pull_request_template.md
├── backend/
├── frontend/
├── data/
│   ├── raw/
│   └── processed/
├── models/
├── rag/
│   └── documents/
├── notebooks/
├── tests/
├── docs/
├── scripts/
├── .env.example
├── .gitignore
├── CONTRIBUTING.md
├── README.md
└── requirements.txt
