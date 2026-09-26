# Product Research

## 1. Objective

Understand how existing supply chain control towers handle disruption detection, investigation, impact assessment, and response.

## 2. Products Reviewed

| Product | Relevant Pattern |
|---|---|
| project44 | Shipment visibility, ETA prediction, exception management |
| FourKites | Proactive disruption detection and risk visibility |
| Kinaxis | Risk → business impact → response |
| Blue Yonder | Predictive and agentic investigation |
| Oracle | Detect → Decide → Execute |
| SAP | See → Decide → Act |

## 3. Key Patterns Identified

### 3.1 Exception First

Users need to know what requires attention rather than inspect every shipment.

### 3.2 Risk Needs Business Context

A delay probability alone is insufficient. Users need to understand the potential operational impact.

### 3.3 Investigation Matters

The system should help answer **why** something is happening, not just report that it is happening.

### 3.4 Recommendations Should Follow Investigation

The useful sequence is:

> Detect → Investigate → Recommend → Decide

### 3.5 Human Remains in the Loop

The system supports the operations user rather than automatically making the final business decision.

## 4. Implications for Our MVP

| Research Finding | Our MVP Decision |
|---|---|
| Exception focused control towers | Show high risk shipments prominently |
| Risk needs context | Include business impact |
| Investigation is important | Add an Investigate workflow |
| Modern systems use multiple signals | Agent uses shipment + weather + supplier tools |
| Recommendations need evidence | Use RAG for procedures |
| AI supports decisions | Generate recommendations, not autonomous execution |

## 5. Product Principle

> **Detect → Prioritize → Investigate → Explain → Recommend → Decide**

## 6. Purpose of This Research

This research is intended to inform the Project 3 MVP rather than serve as a comprehensive competitive analysis.

The key takeaway is that our product should not be positioned as an AI chatbot for supply chain or simply an ML model with a dashboard. It should provide an exception focused control tower where AI investigates supply chain risks and helps an operations user understand the situation and decide what to do.
