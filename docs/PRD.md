# Product Requirements Document
## Supply Chain Disruption Agent

**Project:** TAG AI Engineering Bootcamp Project 3  
**MVP:** Supply Chain Disruption Control Tower  
**Primary user:** Supply chain planner / logistics or operations professional

---

# 1. Product Overview

The Supply Chain Disruption Agent is a responsive control tower that helps supply chain users identify risky shipments, investigate likely disruption causes, understand business impact, and decide how to respond.

The core product journey is:

**Detect → Prioritize → Investigate → Explain → Recommend → Decide**

The MVP is deliberately small, but it is not intended to be an isolated demo.

The product should be designed from the beginning as a potential **intelligence layer within an existing supply chain workflow**, with a future ability to connect to systems such as TMS, ERP, WMS, supplier systems and collaboration tools.

---

# 2. Problem

A late shipment can create downstream inventory shortages and operational disruption.

A supply chain user needs more than an alert that a shipment may be late. They need to understand:

- What is happening?
- Why is it happening?
- What will be affected?
- What alternatives are available?
- What action should be considered?

Today, these questions may require information from multiple sources.

The product brings the core investigation into one workflow.

---

# 3. Product Vision

The long term product is not simply a dashboard or chatbot.

It is an **intelligent decision layer** that:

1. Detects potential disruptions
2. Prioritizes them by risk and business impact
3. Investigates relevant signals
4. Explains likely causes
5. Recommends possible responses
6. Fits into the user's existing operational workflow
7. Eventually supports approved actions through connected systems

The MVP proves the first complete vertical slice of this vision.

---

# 4. MVP Scope

## 4.1 In Scope

The MVP must support:

- Shipment risk prediction
- Risk prioritization
- Responsive control tower
- Attention Required shipment list
- Shipment investigation
- Four operational agent tools
- News and external disruption signal
- Business impact assessment
- RAG grounded operational guidance
- Alternative supplier or route recommendations
- LLM generated disruption briefing
- Human review and decision

## 4.2 Out of Scope

The MVP does not include:

- Full ERP integration
- Full TMS integration
- Full WMS integration
- Automated purchasing
- Autonomous supply chain actions
- Complex scenario simulation
- Full network digital twin
- Advanced collaboration workflows
- Large scale notification infrastructure
- Extensive analytics dashboards
- Complex enterprise role and permission management

These are future product capabilities, not MVP requirements.

---

# 5. Target User

### Primary user

**Supply chain planner / logistics or operations professional**

The user monitors shipments and responds to exceptions.

### User need

The user needs to quickly move from:

> **Something may go wrong**

to:

> **I understand what is happening, what it affects, what I can do, and what action I should consider.**

---

# 6. Core User Journey

## Step 1: Detect

The ML model identifies shipments with elevated delay/disruption risk.

## Step 2: Prioritize

The system presents risk together with business impact.

## Step 3: Investigate

The user selects a shipment and starts an investigation.

The AI agent uses the available operational tools.

## Step 4: Explain

The system presents the likely cause and supporting findings.

## Step 5: Recommend

The agent identifies possible alternatives and recommends a response.

## Step 6: Decide

The human reviews the findings and recommendation and makes the final decision.

**The agent recommends. The human remains in control.**

---

# 7. Functional Requirements

## FR1. Shipment Risk Prediction

The system shall use the ML model to classify shipment delay/disruption risk.

The UI should communicate risk in business friendly terms such as:

- Critical
- High
- Medium
- Low

Raw model probabilities may be shown as supporting information but should not be the primary user experience.

---

## FR2. Risk and Business Impact

The system shall allow the user to understand both:

- Likelihood of disruption
- Potential business consequence

Example:

> **High delay risk**  
> **Potential stockout in 2 days**

A shipment with high delay risk but sufficient inventory should not necessarily receive the same priority as a shipment that could cause a stockout.

---

## FR3. Responsive Control Tower

The system shall provide one primary responsive workspace.

### Desktop

The shipment list and investigation panel may appear side by side.

### Mobile

Selecting a shipment shall open the investigation experience as a full screen view or equivalent mobile panel.

The same information hierarchy shall be preserved across devices.

---

## FR4. Attention Required

The control tower shall show shipments requiring attention.

Minimum information:

- Shipment ID
- Risk level
- ETA / estimated delay
- Business impact
- Investigation action

The primary question answered by the screen is:

> **What needs my attention right now?**

---

## FR5. Shipment Investigation

The user shall be able to select a shipment and start an investigation without leaving the primary product experience.

The investigation should progressively reveal:

1. Risk
2. Investigation activity
3. Findings
4. Business impact
5. Alternatives
6. Recommendation
7. Briefing

---

# 8. Agent Tools

The MVP shall use the four operational tools defined in the team project direction, supported by news and external disruption signals. The four tools are the core tool calling interface; news does not need to be a separate required tool for the MVP unless the implementation requires it.

## FR6. Shipment Status Tool

### `get_shipment_status()`

Purpose:

> What is happening with the shipment?

The tool should provide relevant status, ETA, route or delay information available to the MVP.

---

## FR7. Weather Tool

### `get_weather()`

Purpose:

> Could external conditions explain the disruption?

The tool should provide relevant weather information for the shipment location or route.

---

## FR8. Inventory Tool

### `get_inventory_status()`

Purpose:

> What happens if the shipment is late?

The tool should provide inventory information needed to assess potential business impact.

---

## FR9. Alternative Supplier Tool

### `find_alternative_supplier()`

Purpose:

> What supplier alternatives are available?

The tool should return potential supplier alternatives and relevant information available to the MVP.

## FR10. News and External Disruption Signal

The investigation shall consider relevant news or external disruption signals where available. This may be implemented through the project data source or an appropriate retrieval/tool interface. A separate news tool is not required for the MVP unless needed by the implementation.

## FR11. Alternative Route Support

The investigation shall support alternative route recommendations where route information and supporting data are available. A separate route optimization service is not required for the MVP. If route alternatives cannot be supported by the available data, the system should state that clearly rather than inventing an alternative.

---

# 9. Agent Investigation Experience

The UI should make agent activity visible without turning the product into a technical debugging console.

Example:

```text
INVESTIGATION

✓ Shipment status checked
✓ Weather checked
✓ Inventory checked
✓ Alternative suppliers checked

FINDINGS
Severe weather is affecting the route.

BUSINESS IMPACT
Inventory coverage may fall below the required level.

ALTERNATIVES
Supplier C · 2 day lead time
Supplier B · 4 day lead time

RECOMMENDATION
Consider expediting Supplier C.
```

The user should understand the result without needing to understand the underlying AI implementation.

---

# 10. RAG Requirements

The MVP shall use a small controlled knowledge base containing relevant supply chain procedures or operational guidance.

Potential knowledge areas:

- Disruption response procedure
- Supplier substitution procedure
- Inventory escalation procedure
- Weather disruption procedure

RAG should ground relevant explanations and recommendations in the available procedures.

The knowledge base should remain small and focused for the MVP.

---

# 11. LLM Briefing

The system shall generate a concise operational disruption briefing.

The briefing should contain:

- Shipment
- Risk
- Likely cause
- Business impact
- Alternatives
- Recommended action

The briefing must be understandable to a supply chain professional without requiring technical AI knowledge.

---

# 12. UI / UX Requirements

## 12.1 Design Principle

The product should be **exception first**.

The user should see what requires attention before secondary analytics.

## 12.2 Information Hierarchy

The investigation experience should follow:

**Risk → Cause → Impact → Alternatives → Recommendation → Briefing**

## 12.3 Progressive Disclosure

Do not expose every detail simultaneously.

The user should first see the information needed to decide whether an exception requires attention, then progressively see supporting detail.

## 12.4 One Primary Workspace

Avoid unnecessary navigation between:

Dashboard → Shipment Details → Agent → Recommendation.

The MVP should use one responsive control tower experience with an investigation panel or mobile equivalent.

## 12.5 Human Control

AI recommendations must be presented as decision support.

The MVP must not imply that the AI has independently executed a supply chain decision.

---

# 13. Data Requirements

The existing ML dataset supports the risk prediction component but does not contain every operational field required by the four agent tools.

The MVP may therefore use:

- Existing historical shipment data for ML
- Supporting shipment status data
- Inventory data
- Weather data or a controlled weather dataset/API
- Supplier data
- News or external disruption signals
- RAG knowledge

Supporting data may be synthetic or derived where real open data is not available.

The product must clearly distinguish demonstration data from real external integrations.

---

# 14. Integration and Existing Workflow Strategy

## 14.1 Product Principle

**Meet users where they work.**

The product should not assume that supply chain professionals will abandon their existing systems to use a new dashboard.

In a real deployment, the product could receive information from or surface intelligence through:

- TMS
- ERP
- WMS
- Supplier systems
- Order management systems
- APIs
- Email
- Microsoft Teams
- Slack

The MVP does not need to implement these integrations.

However, the product architecture, data model and tool interfaces should avoid assuming that the current local/demo datasets are the permanent source of truth.

---

## 14.2 Integration Ready

The MVP should separate:

- Data sources
- ML prediction
- Agent tools
- RAG
- LLM
- API layer
- Frontend

This allows future data sources to be connected without redesigning the core user experience.

The four MVP tools should therefore be treated as interfaces to operational information, not as permanently hard coded demo functions. News or external disruption signals should be handled through a similarly replaceable interface where used.

---

## 14.3 Future Workflow

The long term experience could look like:

```text
Existing Supply Chain Systems
        ↓
ERP / TMS / WMS / Supplier Systems
        ↓
Supply Chain Intelligence Layer
        ↓
Risk Detection
        ↓
Investigation
        ↓
Recommendation
        ↓
Existing User Workflow
        ↓
Human Approval
        ↓
Optional Connected Action
```

The MVP proves the intelligence and decision support layer.

---

# 15. System Architecture

```text
Data Sources
    ↓
ML Risk Prediction
    ↓
FastAPI
    ↓
Responsive Control Tower
    ↓
User selects risky shipment
    ↓
AI Agent
    ↓
┌───────────────┬───────────────┬────────────────┬───────────────────┐
│ Shipment      │ Weather       │ Inventory      │ Alternative       │
│ Tool          │ Tool          │ Tool           │ Supplier Tool     │
└───────────────┴───────────────┴────────────────┴───────────────────┘
    ↓
News / External Disruption Signal
    ↓
RAG Knowledge
    ↓
LLM
    ↓
Findings + Impact + Recommendation + Briefing
    ↓
Human Decision
```

The architecture should remain simple enough for the bootcamp but should not prevent future replacement of local/demo data sources with real APIs.

---

# 16. API Requirements

Minimum MVP endpoints:

```text
GET  /health
GET  /shipments
GET  /shipments/{shipment_id}/risk
POST /agent/investigate
```

### `GET /health`

Confirms that the backend is available.

### `GET /shipments`

Returns shipment records required by the control tower.

### `GET /shipments/{shipment_id}/risk`

Returns risk information for a shipment.

### `POST /agent/investigate`

Starts an investigation for a selected shipment and returns the investigation result.

The API design should keep data access separate from the UI so future integrations can replace the underlying sources.

---

# 17. Non Functional Requirements

## Simplicity

The implementation should use the smallest reasonable number of components and dependencies.

## Responsiveness

The core workflow must work on desktop and mobile screen sizes.

## Explainability

The user should understand why a shipment was flagged and why a recommendation was produced.

## Reliability

Tool failures should not crash the entire investigation experience.

## Transparency

The product should distinguish:

- Model prediction
- Retrieved information
- Agent generated explanation
- AI recommendation

## Maintainability

Components should have clear responsibilities and simple interfaces.

## Integration readiness

Data sources should be replaceable without redesigning the core user experience.

---

# 18. Post MVP Roadmap

The following capabilities are deliberately outside the MVP but should influence product and architecture decisions.

## Phase 2: Workflow Integration

- TMS integration
- ERP integration
- WMS integration
- Supplier system integration
- API based data ingestion

## Phase 3: Proactive Exception Management

- Automated alerts
- Role based notifications
- Email / Teams / Slack notifications
- Exception routing
- Escalation rules

## Phase 4: Decision Intelligence

- Scenario comparison
- Cost impact
- Service level impact
- Alternative route analysis
- Alternative supplier analysis
- What if analysis

## Phase 5: Workflow Execution

Move from:

**Recommendation**

to:

**Recommendation → Human approval → Action**

Potential actions:

- Notify procurement
- Request supplier quote
- Create purchase request
- Update shipment plan
- Notify warehouse
- Update connected systems

Actions should remain human controlled unless explicitly authorised.

## Phase 6: Network Visibility

Expand from individual shipments to:

**Supplier → Factory → Carrier → Port → Warehouse → Customer**

The system can then identify disruption cascades.

## Phase 7: Outcome Learning

Capture:

**Prediction → Recommendation → Human decision → Actual outcome**

Use this to support:

- Model monitoring
- Recommendation evaluation
- Supplier performance analysis
- Carrier performance analysis
- False alert analysis
- Continuous improvement

## Phase 8: Collaboration

Support:

- Ownership
- Assignment
- Comments
- Status
- Escalation
- Shared disruption briefings

---

# 19. User Stories

### US1: Monitor risk

As a supply chain planner, I want to see shipments at risk so that I can focus on exceptions requiring attention.

### US2: Understand impact

As a supply chain planner, I want to see the potential business impact of a delayed shipment so that I can prioritize appropriately.

### US3: Investigate

As a supply chain planner, I want the agent to investigate shipment, weather, inventory, supplier and relevant news signals so that I do not have to gather them manually.

### US4: Understand cause

As a supply chain planner, I want to understand the likely cause of a disruption so that I can make an informed decision.

### US5: Evaluate alternatives

As a supply chain planner, I want to see alternative suppliers or routes where supported so that I can consider response options.

### US6: Receive a recommendation

As a supply chain planner, I want a concise recommendation based on the investigation so that I can decide what action to take.

### US7: Remain in control

As a supply chain planner, I want to review the AI recommendation before taking action so that I remain responsible for the final decision.

### US8: Use the product anywhere

As a supply chain planner, I want the core experience to work on both desktop and mobile so that the product is useful across working environments.

---

# 20. MVP Acceptance Criteria

The MVP is accepted when a user can:

1. Open the responsive control tower.
2. See shipment risk levels.
3. Identify shipments requiring attention.
4. Select a high risk shipment.
5. Start an investigation.
6. See the agent use the four MVP tools.
7. See relevant news or external disruption signals considered where available.
8. Understand the likely disruption cause.
9. Understand the potential inventory/business impact.
10. See alternative suppliers or routes where supported.
11. See an AI generated recommendation.
12. Generate a concise disruption briefing.
13. Review the recommendation and make the final decision.
14. Complete the core workflow on both desktop and mobile screen sizes.

---

# 21. Demo Scenario

The primary mentor demo should tell one clear operational story using **SHP1042**.

### Scenario

The ML model flags SHP1042 as high disruption risk. The control tower shows the shipment and its potential inventory impact.

The user selects **Investigate**.

The agent:

1. Checks shipment status
2. Checks weather
3. Checks inventory
4. Checks alternative suppliers and available route options
5. Considers relevant news or external disruption signals
6. Retrieves relevant disruption procedure through RAG
7. Explains the likely cause
8. Shows the business impact
9. Recommends an alternative where supported
10. Generates a concise disruption briefing

The user reviews the evidence and recommendation and makes the final decision.

### Demo story

**Detect → Prioritize → Investigate → Explain → Recommend → Decide**

---

# 22. Assumptions to Validate

Before implementation is fully locked, the team should validate:

- Which supporting datasets will be used for shipment, inventory and supplier tools?
- Which weather source will be used?
- How will shipment IDs map between the ML dataset and tool datasets?
- Which agent framework will be used?
- Which LLM will be used locally or through the chosen deployment approach?
- Which RAG implementation is sufficient for the MVP?
- Which Azure services are required for deployment?
- How will the model be served?
- Which team members own frontend, backend, ML, agent and deployment work?

These questions should be resolved without expanding the MVP unnecessarily.

---

# 23. Definition of Done

The product is ready for MVP demonstration when:

- The ML model can be served by the backend.
- Shipment risk can be displayed in the control tower.
- A user can select a risky shipment.
- The agent can execute the four MVP tools.
- Relevant news or external disruption signals can be considered where available.
- RAG can provide relevant operational guidance.
- The system can explain the disruption.
- Business impact can be shown.
- Alternative suppliers or routes can be presented where supported by the available data.
- The LLM can generate a concise briefing.
- The human can review the recommendation.
- The responsive UI works on desktop and mobile.
- The core workflow works end to end.
- The architecture does not prevent future integration with external supply chain systems.

---

# 24. Product Success

For the MVP, success is not measured by the number of enterprise features implemented.

The MVP succeeds if a user can quickly understand:

> **What is at risk?**

> **Why is it at risk?**

> **What will it affect?**

> **What can I do?**

> **What does the system recommend?**

and then make a decision.

The longer term product succeeds by becoming part of the user's existing supply chain workflow rather than another isolated system.

---

# 25. Guiding Product Principle

> **Build the smallest useful product, but design it as the first version of a real product.**

The MVP should prove the value of disruption intelligence without attempting to reproduce the complexity of an enterprise supply chain platform.

Its long term direction is to become an intelligence layer that connects to the systems supply chain teams already use and helps them move from:

**Disruption → Understanding → Decision → Action**
