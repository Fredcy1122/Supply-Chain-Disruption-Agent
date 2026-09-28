# 🚚 Supply-Chain Disruption Agent

> **AI-powered supply-chain monitoring, disruption prediction, investigation, and decision support system**

A three-week AI engineering project focused on building an intelligent **Supply-Chain Disruption Agent** that monitors shipment and supply-chain signals, predicts potential disruptions, investigates their causes, and recommends actionable alternatives to logistics and operations teams.

The system combines:

* 🤖 AI Agents & tool calling
* 📊 Machine Learning
* 🔎 Retrieval-Augmented Generation (RAG)
* 🧠 Large Language Models (LLMs)
* 🌦️ Weather and external signals
* 📦 Shipment and inventory data
* 👥 Supplier intelligence
* ☁️ Microsoft Azure
* ⚡ FastAPI
* ⚛️ React

---

# 📌 Table of Contents

* [1. Project Overview](#1-project-overview)
* [2. Problem Statement](#2-problem-statement)
* [3. Project Objectives](#3-project-objectives)
* [4. Solution Overview](#4-solution-overview)
* [5. System Architecture](#5-system-architecture)
* [6. Architecture Components](#6-architecture-components)
* [7. End-to-End Workflow](#7-end-to-end-workflow)
* [8. Machine Learning Layer](#8-machine-learning-layer)
* [9. AI Agent Layer](#9-ai-agent-layer)
* [10. RAG Layer](#10-rag-layer)
* [11. LLM Layer](#11-llm-layer)
* [12. Application Layer](#12-application-layer)
* [13. Data Architecture](#13-data-architecture)
* [14. Technology Stack](#14-technology-stack)
* [15. Repository Structure](#15-repository-structure)
* [16. Development Roadmap](#16-development-roadmap)
* [17. Team Responsibilities](#17-team-responsibilities)
* [18. Getting Started](#18-getting-started)
* [19. Environment Variables](#19-environment-variables)
* [20. Development Principles](#20-development-principles)
* [21. Expected Demo](#21-expected-demo)
* [22. Future Improvements](#22-future-improvements)
* [23. Team](#23-team)

---

# 1. Project Overview

The **Supply-Chain Disruption Agent** is an AI-powered logistics decision-support system designed to identify potential shipment disruptions before they develop into major operational problems.

The system combines multiple supply-chain signals, including:

* Shipment status
* Expected delivery dates
* Inventory levels
* Supplier performance
* Weather conditions
* Route conditions
* External disruption signals
* Operational procedures and supplier knowledge

Machine learning is used to estimate the probability of shipment delays or disruption.

An AI agent then investigates high-risk shipments by calling appropriate tools, retrieving relevant knowledge through RAG, and using an LLM to generate an understandable **operations briefing and recommended actions**.

---

# 2. Problem Statement

A late shipment can create a chain reaction:

```text
Shipment Delay
      ↓
Inventory Shortage
      ↓
Production / Operations Disruption
      ↓
Customer Service Impact
      ↓
Financial Impact
```

The problem is that logistics teams may only become aware of the disruption after it has already occurred.

The goal of this project is therefore to build a system that can answer:

> **Which shipments are likely to be disrupted, why are they at risk, what could be affected, and what should the operations team consider doing?**

---

# 3. Project Objectives

The system should be able to:

### 1. Monitor

Monitor shipment and supply-chain signals from multiple sources.

### 2. Predict

Predict whether a shipment is likely to arrive late or experience disruption.

### 3. Investigate

Investigate the potential causes of the disruption using external tools and data.

### 4. Assess Impact

Determine whether the disruption could create meaningful inventory or operational exposure.

### 5. Recommend

Identify potential alternative suppliers, routes, or operational actions.

### 6. Explain

Use RAG and an LLM to explain the situation using relevant operational knowledge.

### 7. Brief

Generate a concise disruption briefing for the operations team.

### 8. Deploy

Deploy the application as a working cloud-based AI product on Microsoft Azure.

---

# 4. Solution Overview

The proposed solution follows this flow:

```text
        SUPPLY-CHAIN DATA
               │
               ▼
       ┌───────────────┐
       │ Data Pipeline │
       └───────┬───────┘
               │
               ▼
       ┌───────────────┐
       │ Feature       │
       │ Engineering   │
       └───────┬───────┘
               │
               ▼
       ┌───────────────┐
       │ ML Risk Model │
       └───────┬───────┘
               │
               ▼
       ┌────────────────┐
       │ AI Supply Chain│
       │     Agent      │
       └───────┬────────┘
               │
       ┌───────┼────────┐
       │       │        │
       ▼       ▼        ▼
   Shipment Weather  Supplier
     Tool      Tool    Tool
       │       │        │
       └───────┼────────┘
               │
               ▼
       ┌───────────────┐
       │      RAG      │
       │ Knowledge Base│
       └───────┬───────┘
               │
               ▼
       ┌───────────────┐
       │      LLM      │
       │ Explanation & │
       │   Briefing    │
       └───────┬───────┘
               │
               ▼
       ┌────────────────┐
       │ React Dashboard│
       └────────────────┘
```

---


# 5. System Architecture

## 5.1 High-Level Architecture

The system uses a **risk-first, investigation-on-demand architecture**. Every shipment is first evaluated by the ML risk model. A risk gate then determines whether deeper AI investigation is required.

~~~text
┌────────────────────────────────────────────────────────────────────┐
│                         OPERATIONS USER                            │
│                        React Dashboard                             │
└───────────────────────────────┬────────────────────────────────────┘
                                │
                                ▼
┌────────────────────────────────────────────────────────────────────┐
│                         FASTAPI BACKEND                            │
│                  API / Validation / Orchestration                  │
└───────────────────────────────┬────────────────────────────────────┘
                                │
                                ▼
┌────────────────────────────────────────────────────────────────────┐
│                          ML RISK LAYER                             │
│                                                                    │
│ DataCo → Feature Engineering → XGBoost → Probability + Risk Level │
└───────────────────────────────┬────────────────────────────────────┘
                                │
                                ▼
                       ┌──────────────────┐
                       │     RISK GATE    │
                       └────────┬─────────┘
                                │
                  ┌─────────────┴─────────────┐
                  │                           │
             LOW RISK                  MEDIUM / HIGH RISK
                  │                           │
                  ▼                           ▼
             MONITOR /                  AI AGENT
            QUICK CHECK                      │
                                             │
                         ┌───────────────────┼───────────────────┐
                         ▼                   ▼                   ▼
                  Shipment Tool       Weather Tool       Supplier Tool
                         │                   │                   │
                       DataCo            Open-Meteo       Synthetic MVP
                         │                   │                   │
                         └───────────────────┼───────────────────┘
                                             │
                                             ▼
                                  INVESTIGATION EVIDENCE
                                             │
                                             ▼
                                      RAG KNOWLEDGE
                                             │
                                             ▼
                                             LLM
                                             │
                                             ▼
                                  DISRUPTION BRIEFING
                                             │
                                             ▼
                                  OPERATIONS DASHBOARD
                                             │
                                             ▼
                                      HUMAN DECISION
~~~

### Architecture Responsibilities

| Component | Responsibility |
| --- | --- |
| Data layer | Prepare shipment and supporting data |
| ML model | Estimate shipment delay risk |
| Risk gate | Decide whether deeper investigation is required |
| AI agent | Orchestrate the investigation and select relevant tools |
| Tools | Retrieve operational evidence |
| RAG | Retrieve documented procedures and operational knowledge |
| LLM | Explain evidence and generate the briefing |
| Dashboard | Present risk, evidence, impact and recommendations |
| Human operator | Make the final operational decision |

---

## 5.2 Detailed Architecture

~~~mermaid
flowchart TB

    USER["Operations User"]
    UI["React Dashboard"]
    API["FastAPI Backend"]

    DATA["DataCo Supply-Chain Dataset"]
    FEATURES["Feature Engineering / Preprocessing"]
    ML["XGBoost Risk Model"]
    RISK["Risk Gate<br/>LOW / MEDIUM / HIGH"]

    AGENT["Supply-Chain AI Agent"]

    SHIPMENT["Shipment Tool<br/>get_shipment_status()"]
    WEATHER["Weather Tool<br/>get_weather()"]
    SUPPLIER["Supplier Tool<br/>find_alternative_supplier()"]

    SHIPDATA["DataCo Test Data"]
    WEATHERDATA["Open-Meteo<br/>Historical Weather"]
    SUPPLIERDATA["Synthetic Supplier Intelligence"]

    EVIDENCE["Investigation Evidence"]

    KB["Operational Knowledge Base<br/>SOPs / Policies / Procedures / Playbooks"]
    VECTOR["Vector Store"]
    RAG["RAG Retrieval"]

    LLM["LLM"]
    BRIEF["Disruption Briefing"]
    HUMAN["Human Operational Decision"]

    USER --> UI
    UI --> API

    API --> DATA
    DATA --> FEATURES
    FEATURES --> ML
    ML --> RISK

    RISK -->|LOW| UI
    RISK -->|MEDIUM / HIGH| AGENT

    AGENT --> SHIPMENT
    AGENT --> WEATHER
    AGENT --> SUPPLIER

    SHIPMENT --> SHIPDATA
    WEATHER --> WEATHERDATA
    SUPPLIER --> SUPPLIERDATA

    SHIPMENT --> EVIDENCE
    WEATHER --> EVIDENCE
    SUPPLIER --> EVIDENCE

    EVIDENCE --> AGENT
    AGENT --> RAG

    KB --> VECTOR
    VECTOR --> RAG

    RAG --> LLM
    AGENT --> LLM
    ML --> LLM

    LLM --> BRIEF
    BRIEF --> API
    API --> UI
    UI --> HUMAN
~~~

### Important Design Rule

The system does **not** call every tool for every shipment.

~~~text
Every shipment
      ↓
ML risk prediction
      ↓
Risk gate
      │
      ├── LOW → monitor / no full investigation
      │
      └── MEDIUM/HIGH → AI agent
                              ↓
                     Select relevant tools
                              ↓
                     Collect evidence
                              ↓
                       Retrieve RAG
                              ↓
                         LLM briefing
~~~

### MVP Data Sources

| Component | Source | Purpose |
| --- | --- | --- |
| Shipment Tool | DataCo test-period data | Shipment/order information |
| Weather Tool | Open-Meteo historical data | Weather for destination/date |
| Supplier Tool | Synthetic supplier dataset | Supplier risk and alternatives |
| ML Model | DataCo training data | Delay-risk prediction |
| RAG | Project/SOP/procedure documents | Operational knowledge |

**Important:** the supplier intelligence dataset is synthetic for the MVP and must be labelled as synthetic. DataCo outcome fields such as Late_delivery_risk, Delivery Status, Days for shipping (real), and post-outcome shipping dates are not ML input features.

# 6. Architecture Components

## 6.1 React Frontend

The frontend provides the operations control tower.

It should display:

* Active shipments
* High-risk shipments
* Delay probabilities
* Inventory exposure
* Supplier risk
* Shipment details
* Risk explanations
* Recommended actions
* Generated disruption briefings

Example:

```text
SUPPLY CHAIN CONTROL TOWER

Active Shipments        148
High Risk                12
Potential Stockouts       5
At-Risk Suppliers         7
```

---

# 6.2 FastAPI Backend

FastAPI acts as the main application/API layer.

Responsibilities include:

* API endpoints
* Authentication where applicable
* Request validation
* Communication with the AI agent
* ML inference
* Data retrieval
* RAG retrieval
* Response formatting

Example endpoints:

```text
GET  /shipments
GET  /shipments/{shipment_id}
GET  /shipments/{shipment_id}/risk

POST /predict-risk
POST /agent/investigate

GET  /suppliers
GET  /inventory

POST /briefing/generate

GET  /health
```

---

# 6.3 AI Agent

The AI agent is responsible for orchestrating the investigation.

It should not simply respond like a chatbot.

Instead, it should determine which tools are required to answer the user's request.

Example:

```text
User:
"Why is shipment SHP001 at risk?"

        ↓

Agent
        ↓

get_shipment_status()
        ↓

get_weather()
        ↓

get_supplier_information()
        ↓

get_inventory_position()
        ↓

run_risk_prediction()
        ↓

retrieve_relevant_procedure()
        ↓

generate_explanation()
```

The agent therefore acts as the **reasoning and orchestration layer**.

---

# 6.4 Tool Layer

The project should expose operational capabilities as tools.

### Shipment Tool

```python
get_shipment_status(shipment_id)
```

Returns information such as:

* Current location
* Shipment status
* Expected arrival
* Route
* Supplier
* Transit information

### Weather Tool

```python
get_weather(location)
```

Returns:

* Current weather
* Forecast
* Severity
* Potential route impact

### Supplier Tool

```python
find_alternative_supplier(product_id, location)
```

Returns:

* Alternative suppliers
* Supplier performance
* Estimated availability
* Relevant supplier information

### Inventory Tool

```python
get_inventory_status(product_id, warehouse_id)
```

Returns:

* Current stock
* Daily demand
* Days of inventory
* Safety stock

---


# 7. End-to-End Workflow

The system follows a **predict → gate → investigate → explain → decide** workflow.

~~~text
SHIPMENT DATA
      ↓
FEATURE ENGINEERING
      ↓
XGBOOST ML MODEL
      ↓
DELAY PROBABILITY
      ↓
RISK GATE
      │
      ├──────── LOW ─────────► MONITOR
      │
      └──── MEDIUM / HIGH
                    ↓
                AI AGENT
                    │
          ┌─────────┼─────────┐
          ▼         ▼         ▼
       SHIPMENT   WEATHER   SUPPLIER
          │         │         │
          └─────────┼─────────┘
                    ↓
          INVESTIGATION EVIDENCE
                    ↓
                   RAG
                    ↓
                   LLM
                    ↓
          DISRUPTION BRIEFING
                    ↓
          OPERATIONS DASHBOARD
                    ↓
             HUMAN DECISION
~~~

### Step 1 — Predict

The ML model evaluates the shipment using information available at the prediction point and produces a delay probability.

### Step 2 — Gate

The risk gate determines whether the shipment requires deeper investigation.

### Step 3 — Investigate

For medium/high-risk shipments, the agent selects the tools relevant to the investigation. It does not automatically call every tool.

### Step 4 — Retrieve Knowledge

RAG retrieves the relevant SOPs, escalation procedures, supplier policies or disruption playbooks.

### Step 5 — Explain

The LLM combines the ML result, tool evidence, business-impact information and retrieved knowledge into an operational briefing.

### Step 6 — Decide

The operations team reviews the briefing and makes the final decision.

> **ML predicts. The agent investigates. Tools provide evidence. RAG provides knowledge. The LLM communicates. Humans decide.**

# 8. Machine Learning Layer

## Objective

The ML component predicts the probability that a shipment will experience a delay or disruption.

### Potential Target

```text
Delayed
```

Example:

```text
0 = On Time
1 = Delayed
```

The model may also produce a probability:

```text
Delay Probability = 0.87
```

Which can be translated into:

```text
0.00 - 0.39 → LOW
0.40 - 0.69 → MEDIUM
0.70 - 1.00 → HIGH
```

Thresholds will be validated during model development.

---

## Potential Features

```text
supplier_delay_rate
historical_transit_time
current_transit_time
distance_remaining
days_to_expected_arrival
weather_severity
route_risk
supplier_reliability
port_congestion
inventory_days
shipment_priority
```

---

## Model Development

The initial approach should include a baseline model and at least one stronger tree-based model.

Potential models:

```text
Logistic Regression
        ↓
Random Forest
        ↓
XGBoost / Gradient Boosting
```

Models will be evaluated using appropriate classification metrics, including:

* Precision
* Recall
* F1 Score
* ROC-AUC
* Confusion Matrix

For supply-chain disruption detection, particular attention should be paid to **false negatives**, because failing to identify a genuinely risky shipment may have significant operational consequences.

---

# 9. AI Agent Layer

The agent is responsible for deciding:

> **What information do I need to investigate this disruption?**

### Example

```text
User:
"Investigate shipment SHP001."

Agent
│
├── get_shipment_status()
│
├── get_weather()
│
├── get_supplier_information()
│
├── get_inventory_status()
│
├── run_risk_prediction()
│
├── search_knowledge_base()
│
└── generate_briefing()
```

The agent should provide traceable reasoning through **tool outputs and retrieved evidence**, rather than relying on unsupported assumptions.

---

# 10. RAG Layer

The RAG system provides the agent/LLM with domain-specific knowledge.

## Knowledge Base

Potential documents include:

```text
SOPs
Supplier procedures
Procurement policies
Logistics procedures
Escalation procedures
Inventory policies
Disruption response procedures
Supplier profiles
```

### RAG Pipeline

```text
Documents
    ↓
Document Loading
    ↓
Text Extraction
    ↓
Chunking
    ↓
Embeddings
    ↓
Vector Database
    ↓
Similarity Search
    ↓
Relevant Context
    ↓
LLM
```

The purpose of RAG is to ground recommendations in available operational knowledge rather than allowing the LLM to invent procedures.

---

# 11. LLM Layer

The LLM is responsible primarily for:

* Explaining risk
* Summarizing investigation results
* Translating technical outputs into operational language
* Generating disruption briefings
* Presenting recommendations clearly

The LLM should **not replace the ML risk model**.

The intended architecture is:

```text
ML Model
   ↓
Risk Prediction
   ↓
AI Agent
   ↓
Investigation
   ↓
RAG + Tools
   ↓
LLM
   ↓
Human-readable briefing
```

---

# 12. Business Impact Assessment

A key principle of the project is:

> **Risk is not the same as business impact.**

For example:

```text
Shipment A
Delay Probability = 90%
Inventory Coverage = 60 days
```

The delay may have limited immediate operational impact.

While:

```text
Shipment B
Delay Probability = 55%
Inventory Coverage = 2 days
```

could represent a more urgent situation.

Therefore, the system should consider both:

```text
Delay Risk
     +
Inventory Exposure
     +
Shipment Criticality
     ↓
Disruption Priority
```

The final implementation may use a transparent business-rule score rather than a separate ML model.

---

# 13. Data Architecture

The project will combine multiple data sources.

```text
                  DATA SOURCES
                       │
       ┌───────────────┼────────────────┐
       │               │                │
       ▼               ▼                ▼
   Shipment         Inventory        Supplier
     Data              Data            Data
       │               │                │
       └───────────────┼────────────────┘
                       │
                       ▼
                Data Processing
                       │
                       ▼
              Feature Engineering
                       │
                       ▼
                 ML Data Layer
                       │
                       ▼
               Risk Prediction
```

External signals:

```text
Weather APIs
News / disruption signals
Public logistics datasets
Shipping datasets
```

---

# 14. Technology Stack

| Layer            | Technology                     |
| ---------------- | ------------------------------ |
| Frontend         | React                          |
| Backend          | FastAPI / Python               |
| Programming      | Python / JavaScript            |
| Machine Learning | Scikit-learn / XGBoost         |
| AI Agent         | Agent framework / tool calling |
| LLM              | Azure/OpenAI-compatible LLM    |
| RAG              | Embeddings + Vector Database   |
| Data Processing  | Pandas / NumPy                 |
| APIs             | REST                           |
| Cloud            | Microsoft Azure                |
| Version Control  | Git / GitHub                   |
| Documentation    | Markdown                       |
| Testing          | Pytest / API testing           |

Specific Azure services will be finalized during implementation based on project requirements, free-credit constraints, and deployment architecture.

---

# 15. Repository Structure

The repository should follow a modular structure:

```text
supply-chain-disruption-agent/
│
├── README.md
├── .gitignore
├── .env.example
├── requirements.txt
├── docker-compose.yml
├── Dockerfile
│
├── data/
│   ├── raw/
│   ├── processed/
│   └── external/
│
├── notebooks/
│   ├── 01_data_exploration.ipynb
│   ├── 02_feature_engineering.ipynb
│   ├── 03_model_training.ipynb
│   └── 04_model_evaluation.ipynb
│
├── backend/
│   ├── main.py
│   ├── api/
│   │   ├── routes_shipments.py
│   │   ├── routes_predictions.py
│   │   ├── routes_agent.py
│   │   └── routes_briefing.py
│   │
│   ├── models/
│   │   ├── schemas.py
│   │   └── database_models.py
│   │
│   ├── services/
│   │   ├── shipment_service.py
│   │   ├── weather_service.py
│   │   ├── supplier_service.py
│   │   └── inventory_service.py
│   │
│   └── config.py
│
├── agent/
│   ├── agent.py
│   ├── tools/
│   │   ├── shipment_tool.py
│   │   ├── weather_tool.py
│   │   ├── supplier_tool.py
│   │   └── inventory_tool.py
│   │
│   └── prompts/
│       └── system_prompt.txt
│
├── ml/
│   ├── preprocessing.py
│   ├── features.py
│   ├── train.py
│   ├── predict.py
│   ├── evaluate.py
│   └── artifacts/
│
├── rag/
│   ├── ingestion.py
│   ├── chunking.py
│   ├── embeddings.py
│   ├── retrieval.py
│   └── documents/
│
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   ├── pages/
│   │   ├── services/
│   │   └── App.jsx
│   ├── package.json
│   └── README.md
│
├── tests/
│   ├── test_api.py
│   ├── test_ml.py
│   ├── test_tools.py
│   ├── test_agent.py
│   └── test_rag.py
│
├── docs/
│   ├── architecture/
│   ├── api/
│   └── demo/
│
└── deployment/
    ├── azure/
    └── docker/
```

The structure can evolve as implementation progresses.

---

# 16. Development Roadmap

## Week 5 — Foundation & ML

### Objectives

Build the data and prediction foundation.

### Deliverables

* [ ] Identify datasets
* [ ] Define data schema
* [ ] Clean datasets
* [ ] Integrate shipment/inventory/supplier data
* [ ] Engineer ML features
* [ ] Build baseline model
* [ ] Train improved model
* [ ] Evaluate model
* [ ] Save trained model
* [ ] Create prediction API
* [ ] Define agent tools

### Week 5 Target

The team should be able to provide:

```text
Shipment ID
       ↓
ML Model
       ↓
Delay Probability
       ↓
Risk Classification
```

---

# Week 6 — Agent + RAG

### Objectives

Turn the prediction system into an intelligent investigation system.

### Deliverables

* [ ] Implement shipment tool
* [ ] Implement weather tool
* [ ] Implement supplier tool
* [ ] Implement inventory tool
* [ ] Connect ML model to agent
* [ ] Build knowledge base
* [ ] Implement document ingestion
* [ ] Implement embeddings
* [ ] Implement vector search
* [ ] Implement RAG
* [ ] Build agent workflow
* [ ] Generate explanations

### Week 6 Target

The agent should be able to:

```text
Identify Risk
     ↓
Investigate Cause
     ↓
Retrieve Relevant Knowledge
     ↓
Explain Findings
```

---

# Week 7 — Product + Azure + Demo

### Objectives

Turn the technical components into a working product.

### Deliverables

* [ ] Build React dashboard
* [ ] Connect frontend to FastAPI
* [ ] Connect agent to frontend
* [ ] Add risk visualization
* [ ] Add shipment investigation screen
* [ ] Add recommendations
* [ ] Add briefing generation
* [ ] Deploy application to Azure
* [ ] Test production environment
* [ ] Fix integration issues
* [ ] Prepare Demo Day presentation
* [ ] Prepare technical documentation

### Week 7 Target

A user should be able to open the application and:

```text
View shipments
      ↓
Identify high-risk shipment
      ↓
Investigate shipment
      ↓
Understand why it is at risk
      ↓
View possible alternatives
      ↓
Generate disruption briefing
```

---

# 17. Team Responsibilities

Team members should own specific components while collaborating across interfaces.

| Area             | Primary Responsibility                          |
| ---------------- | ----------------------------------------------- |
| Project Lead     | Architecture, coordination, integration         |
| Data Engineering | Data collection, cleaning, integration          |
| ML Engineering   | Feature engineering, model training, evaluation |
| AI Engineering   | Agent, tool calling, orchestration              |
| RAG / LLM        | Knowledge base, retrieval, prompts, briefing    |
| Frontend         | React dashboard and UX                          |
| Cloud / DevOps   | Azure deployment and infrastructure             |

> Responsibilities can overlap depending on team size.

---

# 18. Getting Started

## 18.1 Clone the repository

```bash
git clone <REPOSITORY_URL>
cd supply-chain-disruption-agent
```

## 18.2 Create a virtual environment

```bash
python -m venv .venv
```

### Windows

```bash
.venv\Scripts\activate
```

### macOS / Linux

```bash
source .venv/bin/activate
```

---

## 18.3 Install dependencies

```bash
pip install -r requirements.txt
```

---

## 18.4 Configure environment variables

Copy:

```bash
.env.example
```

to:

```bash
.env
```

Then configure the required API keys and service credentials.

**Never commit `.env` to GitHub.**

---

## 18.5 Start the backend

```bash
uvicorn backend.main:app --reload
```

The API should then be available locally.

---

## 18.6 Start the frontend

```bash
cd frontend
npm install
npm run dev
```

---

# 19. Environment Variables

Example:

```env
# Application
ENVIRONMENT=development

# LLM
LLM_API_KEY=
LLM_ENDPOINT=
LLM_MODEL=

# Weather
WEATHER_API_KEY=

# Database
DATABASE_URL=

# Vector Database
VECTOR_DB_URL=
VECTOR_DB_API_KEY=

# Azure
AZURE_SUBSCRIPTION_ID=
AZURE_RESOURCE_GROUP=
AZURE_REGION=
```

Actual variables will depend on the services selected by the team.

---

# 20. Development Principles

## 20.1 Data Before AI

Ensure the underlying data is reliable before adding advanced AI functionality.

---

## 20.2 ML Predicts — Agent Investigates

The ML model should provide the risk prediction.

The agent should determine how to investigate the prediction.

---

## 20.3 RAG Grounds Knowledge

The RAG system should provide relevant operational knowledge and procedures.

---

## 20.4 LLM Explains

The LLM should transform structured findings into understandable operational communication.

---

## 20.5 Human-in-the-Loop

The system provides recommendations and decision support.

Final operational decisions remain with human users.

```text
AI
 ↓
Detect
 ↓
Investigate
 ↓
Recommend
 ↓
Human
 ↓
Decide
```

---

## 20.6 Modular Architecture

Each component should be independently testable.

```text
ML
Agent
Tools
RAG
LLM
API
Frontend
```

should not become one tightly coupled application.

---

## 20.7 Reproducibility

All team members should be able to reproduce the development environment and run the core application.

---

# 21. Expected Demo

The final Demo Day should demonstrate a complete operational scenario.

## Scenario

A shipment is approaching its expected delivery date.

The system detects a high probability of delay.

### Step 1 — Dashboard

```text
12 HIGH-RISK SHIPMENTS
```

### Step 2 — Select Shipment

```text
SHP001

Delay Probability: 87%
Risk Level: HIGH
```

### Step 3 — Investigate

The agent calls:

```text
get_shipment_status()
get_weather()
get_inventory_status()
get_supplier_information()
```

### Step 4 — Identify Causes

Example:

```text
Potential Causes

• Severe weather
• Supplier historical delays
• Route congestion
• Low inventory coverage
```

### Step 5 — Assess Impact

```text
Inventory Coverage: 3 days
Expected Delay: 5 days

Potential Stockout: YES
```

### Step 6 — Find Alternatives

The agent calls:

```text
find_alternative_supplier()
```

### Step 7 — Retrieve Procedure

RAG retrieves the relevant disruption/escalation procedure.

### Step 8 — Generate Briefing

The LLM produces:

```text
SUPPLY-CHAIN DISRUPTION BRIEFING

Shipment: SHP001
Risk: HIGH
Delay Probability: 87%

Primary Risk Factors:
1. Weather
2. Supplier performance
3. Route congestion

Business Impact:
Inventory coverage may be insufficient
to absorb the expected delay.

Recommended Actions:
1. Contact alternative supplier.
2. Evaluate alternative route.
3. Escalate shipment to operations.
```

This demonstrates the complete system rather than isolated technical components.

---

# 22. Future Improvements

Potential future enhancements include:

* Real-time shipment tracking
* More advanced time-series forecasting
* Port congestion monitoring
* Real-time news analysis
* Geospatial route risk
* Supplier risk scoring
* Automated alerts
* Email/Teams notifications
* What-if simulation
* Multi-agent architecture
* Reinforcement learning for routing decisions
* Automated procurement workflows
* Advanced supply-chain digital twin
* Continuous model monitoring
* Model drift detection

These features are outside the initial MVP unless the team completes the core system early.

---

# 23. Team

## Project

**Logistics: Supply-Chain Disruption Agent**

### Project Lead

**[Team Lead Name]**

### Team Members

* [Member 1]
* [Member 2]
* [Member 3]
* [Member 4]
* [Member 5]

---

# 🎯 Project Vision

The ultimate goal is to move from:

```text
Reactive Logistics
       ↓
"Shipment has been delayed."
```

to:

```text
Predictive Logistics
       ↓
"Shipment is likely to be delayed."
       ↓
Prescriptive Support
       ↓
"Here is why it is at risk,
what it may affect,
and what alternatives are available."
```

The **Supply-Chain Disruption Agent** is designed to help operations teams identify potential disruptions earlier, understand their causes, and make better-informed decisions.

---

## ⭐ Core Architecture Principle

```text
       DATA
        ↓
    ML PREDICTION
        ↓
   AI INVESTIGATION
        ↓
   TOOL CALLING
        ↓
       RAG
        ↓
       LLM
        ↓
 ACTIONABLE BRIEFING
        ↓
 HUMAN DECISION
```

**Detect → Investigate → Explain → Recommend → Decide**
