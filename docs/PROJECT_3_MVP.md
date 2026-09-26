# Project 3 MVP
## Supply Chain Disruption Agent

## 1. MVP Objective

Build a responsive supply chain control tower that helps a supply chain user:

**Detect → Prioritize → Investigate → Explain → Recommend → Decide**

The MVP identifies high risk shipments, investigates likely disruption causes using operational tools and a news signal, assesses business impact, recommends alternative suppliers or routes where supported by the available data, and presents the result for human decision making.

The MVP is intentionally small, but it is **not an isolated or disposable demo**. The product should be designed from the beginning to fit into a real supply chain workflow and evolve toward integration with existing systems such as TMS, ERP, WMS, supplier systems, and collaboration tools.

---

## 2. Problem

A shipment delay can create downstream inventory shortages and operational disruption.

The problem is not only detecting that a shipment may be late. A supply chain user also needs to understand:

- What is happening?
- Why is it happening?
- What will be affected?
- What alternatives are available?
- What action should be considered?

The MVP brings these steps into one workflow.

---

## 3. Target User

Primary user:

**Supply chain planner / logistics or operations professional**

The user is responsible for monitoring shipments and responding to exceptions.

The MVP should reduce the need to manually investigate multiple signals before deciding what requires attention.

---

# 4. Core User Journey

### Step 1: Detect

The system uses the ML model to identify shipments with elevated disruption or delay risk.

### Step 2: Prioritize

Risk is presented together with business impact so the user can focus on the exceptions that matter most.

### Step 3: Investigate

The user selects a shipment and starts an investigation.

The AI agent uses the available tools to gather relevant information.

### Step 4: Explain

The system presents the likely disruption cause and supporting findings.

### Step 5: Recommend

The agent identifies possible alternatives and provides a recommended response.

### Step 6: Decide

The human user reviews the evidence and recommendation and decides what to do.

The agent recommends. The human remains in control.

---

# 5. MVP Features

## 5.1 Responsive Control Tower

The MVP uses **one primary responsive workspace**, not separate dashboard and investigation pages.

### Desktop

The shipment list and investigation panel may appear side by side.

### Mobile

Selecting a shipment opens the investigation experience as a full screen view or equivalent mobile panel.

The information architecture remains the same across devices.

### Control Tower should show

- Total shipments
- At risk shipments
- Critical shipments
- On time shipments
- Attention Required shipment list
- Risk level
- Estimated delay / ETA impact
- Business impact
- Investigate action

The primary purpose is to answer:

> **What needs my attention right now?**

Charts and secondary analytics should not compete with the exception workflow.

---

# 6. Investigation Experience

Selecting **Investigate** opens the shipment investigation within the same product experience.

The information should be revealed progressively:

1. Risk
2. Investigation activity
3. Findings
4. Business impact
5. Alternatives
6. Recommendation
7. Briefing

Example:

```text
SHP1042
Critical risk · ETA +2 days

INVESTIGATION
✓ Shipment status checked
✓ Weather checked
✓ Inventory checked
✓ Alternative suppliers checked

FINDINGS
Severe weather is affecting the shipment route.

BUSINESS IMPACT
Inventory coverage may fall below the required level.

ALTERNATIVES
Supplier C · 2 day lead time
Supplier B · 4 day lead time

RECOMMENDATION
Consider expediting Supplier C.

[Generate Briefing]
```

The technical details of agent execution should remain secondary to the business outcome.

---

# 7. MVP Agent Tools and Signals

The MVP is built around the four operational tools defined in the team README, supported by news and external disruption signals. The four tools are the core tool calling interface for the agent; news is treated as an additional disruption signal rather than requiring a separate tool unless the implementation needs one.

## 7.1 `get_shipment_status()`

Answers:

> **What is happening with the shipment?**

Provides relevant shipment status, ETA, route or delay information available to the MVP.

---

## 7.2 `get_weather()`

Answers:

> **Could external conditions explain the disruption?**

Provides relevant weather information for the shipment location or route.

---

## 7.3 `get_inventory_status()`

Answers:

> **What happens if the shipment is late?**

Provides inventory information needed to assess potential business impact.

---

## 7.4 `find_alternative_supplier()`

Answers:

> **What supplier alternatives are available?**

Returns potential supplier alternatives and relevant information available to the MVP.

## 7.5 News Signal

Answers:

> **Is there an external event that helps explain the disruption?**

The agent should use a relevant news or external disruption signal where available. This can be implemented through the project data source or an appropriate retrieval/tool interface without making news a separate required tool in the MVP.

## 7.6 Alternative Routes

The MVP should support alternative route recommendations where route information and supporting data are available. A separate route optimization tool is not required for the first version. The agent may use shipment, weather and other available information to surface a viable alternative route, or clearly state when route alternatives are not supported by the available data.

---

# 8. ML Risk Prediction

The existing ML model provides shipment delay/disruption risk.

The product should expose the prediction as decision support rather than as a technical model output.

For example:

**High disruption risk**

rather than making the user interpret a raw probability alone.

Where appropriate, risk should be combined with business impact.

Example:

> **High delay risk**
>
> **Potential stockout in 2 days**

This makes the prediction operationally meaningful.

---

# 9. Business Impact

The MVP should connect shipment risk to inventory impact.

The user should be able to understand:

**Shipment delay → inventory risk → potential operational impact**

This is important because not every delayed shipment has the same business consequence.

A shipment with low inventory coverage should receive greater attention than an otherwise similar shipment with sufficient stock.

---

# 10. RAG

The MVP should use a small, controlled knowledge base containing relevant supply chain procedures or operational guidance.

RAG should help the agent ground its explanation or recommendation in the available procedures.

Example knowledge:

- Disruption response procedure
- Supplier substitution procedure
- Inventory escalation procedure
- Weather disruption procedure

The knowledge base should remain small and focused for the MVP.

---

# 11. LLM Briefing

The LLM converts the investigation results into a concise operational briefing.

The briefing should contain:

- Shipment
- Risk
- Likely cause
- Business impact
- Alternatives
- Recommended action

The briefing should be understandable to a supply chain professional without requiring technical AI knowledge.

---

# 12. Data Strategy

The current ML dataset can support the risk prediction component, but it does not contain every operational field required by the four tools.

Therefore, the MVP may use:

- Existing historical shipment data for ML
- Small supporting datasets for shipment status
- Inventory data
- Weather data or a controlled weather dataset/API
- Supplier data
- News or external disruption signals
- A small RAG knowledge base

Where real data is unavailable, synthetic or derived supporting data may be used for the MVP.

The product should clearly distinguish demonstration data from real external integrations.

We should not pretend that fields exist in the current ML dataset when they do not.

---

# 13. Integration and Existing Workflow Strategy

## 13.1 The MVP is integration aware

The MVP is not intended to replace the systems a supply chain team already uses.

In a real deployment, shipment, inventory, supplier and order information would typically come from existing operational systems.

The MVP should therefore use clean interfaces between:

- ML prediction
- Shipment data
- Weather data
- Inventory data
- Supplier data
- News / external disruption signals
- RAG knowledge
- Agent tools
- API layer
- Frontend

This allows the underlying data sources to be replaced later without redesigning the user experience.

---

## 13.2 Future workflow integration

The product should eventually be able to receive or surface intelligence through existing workflows such as:

- TMS
- ERP
- WMS
- Supplier systems
- Email
- Microsoft Teams
- Slack
- APIs

The user should not have to manually move information between systems just to investigate a disruption.

For the MVP, these integrations are **not implemented**. The MVP should instead demonstrate an architecture and tool interface that can support them later.

---

# 14. Post MVP Product Direction

The following features are intentionally outside the MVP but should inform the architecture.

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

Potential actions could include:

- Notify procurement
- Request supplier quote
- Create purchase request
- Update shipment plan
- Notify warehouse
- Update connected systems

Actions should remain human controlled unless explicitly authorised.

## Phase 6: Network Visibility

Expand from individual shipments to the wider supply chain network:

**Supplier → Factory → Carrier → Port → Warehouse → Customer**

The system can then identify disruption cascades rather than isolated shipment problems.

## Phase 7: Learning from Outcomes

Capture:

**Prediction → Recommendation → Human decision → Actual outcome**

This can support:

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

# 15. What Is Out of Scope for MVP

The following are deliberately excluded from the first working version:

- Full ERP integration
- Full TMS integration
- Full WMS integration
- Automated purchasing
- Autonomous supply chain actions
- Complex scenario simulation
- Full network digital twin
- Advanced collaboration workflows
- Multi tenant enterprise architecture
- Large scale notification infrastructure
- Extensive analytics dashboards
- Complex role and permission management

These may become future capabilities.

They should not distract from proving the core disruption workflow.

---

# 16. MVP Architecture Principle

The architecture should be **simple enough to build quickly but structured enough to evolve**.

```text
Data Sources
    ↓
ML Risk Prediction
    ↓
FastAPI
    ↓
Control Tower
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
RAG Knowledge
    ↓
LLM
    ↓
Findings + Impact + Recommendation + Briefing
    ↓
Human Decision
```

The tool interfaces should be designed so that today's local/demo data sources can later be replaced by real APIs or enterprise systems.

---

# 17. MVP Acceptance Criteria

The MVP is complete when a user can:

- Open the responsive control tower
- See shipments and their risk levels
- Identify shipments requiring attention
- Select a high risk shipment
- Start an investigation
- See the agent use the four MVP tools
- Understand the likely disruption cause
- Understand the potential inventory/business impact
- See alternative suppliers or routes where supported by the available data
- See an AI generated recommendation
- Generate a concise disruption briefing
- Review the recommendation and make the final decision

The complete experience should work on both desktop and mobile screen sizes.

---

# 18. Demo Scenario

The demo should tell one clear story.

### Scenario

A shipment is predicted to arrive late.

The control tower flags it as high risk.

The user selects **Investigate**.

The agent:

1. Checks shipment status
2. Checks weather
3. Checks inventory
4. Checks alternative suppliers and available route options
5. Checks relevant news or external disruption signals
6. Retrieves relevant disruption procedure
7. Explains the likely cause
8. Shows the business impact
9. Recommends an alternative
10. Generates a short disruption briefing

The user reviews the recommendation and decides what to do.

### Demo story

> **Detect → Investigate → Explain → Recommend → Decide**

This should be the centre of the MVP demo.

---

# 19. Definition of Done

The MVP is done when the core disruption workflow is usable end to end:

**Risk prediction → Control Tower → Investigation → Tool Calls → RAG → Business Impact → Recommendation → Briefing → Human Decision**

The product should be:

- Responsive
- Simple to understand
- Demonstrable end to end
- Grounded in available data
- Transparent about AI generated recommendations
- Structured for future integration
- Small enough to maintain and explain

---

# 20. Product Principle

> **Build the smallest useful product, but design it as the first version of a real product.**

The MVP should prove the value of disruption intelligence without attempting to reproduce the complexity of an enterprise supply chain platform.

Its long term direction is not to become another isolated dashboard.

It should become an intelligence layer that fits into the supply chain team's existing workflow, connects to the systems they already use, and helps them move from disruption detection to informed action.
