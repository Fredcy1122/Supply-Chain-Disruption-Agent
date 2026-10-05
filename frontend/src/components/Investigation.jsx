import {
  failureDetail,
  investigate,
  toSteps,
} from "../api/investigation.js";

import {
  Empty,
  EvidenceCard,
  RiskBadge,
  StatusChip,
  precisePct,
} from "./ui.jsx";


// Active investigations remain outside the component so navigation
// between tabs does not stop a running stream.
const active = new Map();


const STEP_STATUS = {
  running:
    "In progress",

  done:
    "Done",

  failed:
    "Unavailable",

  complete:
    "Briefing ready",
};


function getSupplierResult(
  shipment,
) {
  const trace = (
    shipment.toolTrace
    || shipment.evidence
    || []
  );

  return trace.find(
    (entry) =>
      entry.tool
        === "find_alternative_supplier"
      && entry.status
        === "success",
  )?.output;
}


function CitationList({
  citations,
}) {
  if (!citations?.length) {
    return (
      <p className="muted-text">
        Operational guidance will appear after the
        investigation retrieves relevant documents.
      </p>
    );
  }

  return (
    <div className="citation-list">
      {citations.map(
        (citation) => (
          <article
            className="citation-card"
            key={
              citation.filename
              || citation.title
            }
          >
            <span
              className="citation-type"
            >
              {citation.sourceType}
            </span>

            <strong>
              {citation.title}
            </strong>

            <small>
              {citation.filename}
            </small>
          </article>
        ),
      )}
    </div>
  );
}


function InvestigationEvidence({
  shipment,
}) {
  const structured = (
    shipment.structuredEvidence
  );

  const supplierResult = (
    getSupplierResult(
      shipment,
    )
  );

  const supplier = (
    supplierResult
      ?.recommended_supplier
  );

  if (
    !structured
    && !supplierResult
  ) {
    return null;
  }

  const inventoryCoverage = (
    structured
      ?.inventoryCoverageDays
  );

  return (
    <section className="investigation-evidence">
      <div className="section-copy">
        <small className="eyebrow">
          Collected evidence
        </small>

        <h3>
          What the investigation found
        </h3>

        <p>
          Evidence is collected by backend tools and
          remains separate from the generated briefing.
        </p>
      </div>

      <div className="evidence-grid">
        <EvidenceCard title="Historical delay">
          {structured
            ?.historicalDelaySummary
            ? (
              <p>
                {
                  structured
                    .historicalDelaySummary
                }
              </p>
            )
            : (
              <p className="muted-text">
                Historical-delay evidence was not
                available.
              </p>
            )}
        </EvidenceCard>

        <EvidenceCard title="Destination weather">
          {structured
            ?.weatherSummary
            ? (
              <p>
                {
                  structured
                    .weatherSummary
                }
              </p>
            )
            : (
              <p className="muted-text">
                Destination-weather evidence was not
                available.
              </p>
            )}
        </EvidenceCard>

        <EvidenceCard
          title="Alternative supplier"
          tone="synthetic"
        >
          {supplier
            ? (
              <>
                <div className="supplier-heading">
                  <div>
                    <strong>
                      {
                        supplier
                          .supplier_name
                      }
                    </strong>

                    <span>
                      {
                        supplier
                          .supplier_id
                      }
                    </span>
                  </div>

                  <RiskBadge
                    level={
                      supplier
                        .supplier_risk_level
                    }
                  />
                </div>

                <dl className="evidence-facts">
                  <div>
                    <dt>Country</dt>

                    <dd>
                      {
                        supplier
                          .supplier_country
                      }
                    </dd>
                  </div>

                  <div>
                    <dt>Category</dt>

                    <dd>
                      {
                        supplier
                          .product_category
                      }
                    </dd>
                  </div>

                  <div>
                    <dt>Average lead time</dt>

                    <dd>
                      {
                        supplier
                          .average_lead_time_days
                      } days
                    </dd>
                  </div>

                  <div>
                    <dt>On-time delivery</dt>

                    <dd>
                      {precisePct(
                        supplier
                          .on_time_delivery_rate,
                      )}
                    </dd>
                  </div>

                  <div>
                    <dt>Capacity utilization</dt>

                    <dd>
                      {precisePct(
                        supplier
                          .capacity_utilization,
                      )}
                    </dd>
                  </div>

                  <div>
                    <dt>Risk score</dt>

                    <dd>
                      {
                        supplier
                          .supplier_risk_score
                      } / 100
                    </dd>
                  </div>
                </dl>

                <p className="disclosure">
                  Synthetic supplier candidate. Geographic
                  suitability, available unit capacity,
                  contractual terms, and live availability
                  require human validation.
                </p>
              </>
            )
            : structured
              ?.supplierStatus
              ? (
                <>
                  <p>
                    {
                      structured
                        .supplierStatus
                    }
                  </p>

                  <p className="disclosure">
                    Synthetic supplier evidence requires
                    human review before operational use.
                  </p>
                </>
              )
              : (
                <p className="muted-text">
                  No supplier evidence was collected.
                </p>
              )}
        </EvidenceCard>

        <EvidenceCard title="Inventory coverage">
          {inventoryCoverage !== null
            && inventoryCoverage !== undefined
            ? (
              <>
                <strong className="evidence-value">
                  {inventoryCoverage} days
                </strong>

                <p>
                  Compare available coverage with the
                  expected disruption duration.
                </p>
              </>
            )
            : (
              <p className="muted-text">
                Inventory coverage is unavailable. The
                investigation cannot confirm stockout
                exposure.
              </p>
            )}
        </EvidenceCard>
      </div>
    </section>
  );
}


export default function Investigation({
  shipment,
  onUpdate,
}) {
  if (!shipment) {
    return (
      <Empty>
        Select a shipment first.
      </Empty>
    );
  }

  const run = async () => {
    const id = shipment.id;

    active.get(id)?.abort();

    const controller = (
      new AbortController()
    );

    active.set(
      id,
      controller,
    );

    const update = (
      patch,
    ) => {
      if (
        active.get(id)
        === controller
      ) {
        onUpdate(
          id,
          patch,
        );
      }
    };

    update({
      investigationStatus:
        "running",

      investigationError:
        null,

      conclusion:
        null,

      evidence:
        [],

      toolTrace:
        [],

      structuredEvidence:
        null,

      briefing:
        null,

      recommendations:
        [],

      recommendedActions:
        [],

      recommendationsPending:
        false,

      ragPolicyCitations:
        [],

      citationCards:
        [],

      limitations:
        [],
    });

    try {
      await investigate(
        id,
        update,
        {
          signal:
            controller.signal,
        },
      );

      update({
        investigationStatus:
          "complete",
      });
    } catch (error) {
      if (
        controller.signal.aborted
      ) {
        return;
      }

      update({
        investigationStatus:
          error.code
            === "investigation_not_required"
            ? "not_required"
            : "failed",

        investigationError: {
          message:
            error.message,

          detail:
            failureDetail(
              error,
            ),
        },
      });
    } finally {
      if (
        active.get(id)
        === controller
      ) {
        active.delete(
          id,
        );
      }
    }
  };

  const shown = toSteps(
    shipment,
  );

  const status = (
    shipment.investigationStatus
  );

  const failure = (
    shipment.investigationError
  );

  const limitations = (
    shipment.limitations
    || []
  );

  const citations = (
    shipment.citationCards
    || []
  );

  const busy = (
    status === "running"
    || status
      === "generating_briefing"
  );

  const buttonLabel = (
    status === "none"
      ? "Start investigation"
      : busy
        ? "Investigation running"
        : "Run again"
  );

  return (
    <div className="investigation-layout">
      <section className="panel">
        <header className="investigation-header">
          <div>
            <small className="eyebrow">
              AI investigation
            </small>

            <h2>
              {shipment.id}
            </h2>

            <p>
              Follow the backend tools as evidence is
              collected, operational guidance is retrieved,
              and the disruption briefing is generated.
            </p>
          </div>

          <div className="header-actions">
            <StatusChip
              status={status}
            />

            <button
              className="btn"
              onClick={run}
              disabled={busy}
            >
              {buttonLabel}
            </button>
          </div>
        </header>

        {busy && (
          <div className="investigation-banner">
            <span className="pulse-dot" />

            <div>
              <strong>
                {status
                  === "generating_briefing"
                  ? "Generating grounded briefing"
                  : "Investigation in progress"}
              </strong>

              <p>
                {status
                  === "generating_briefing"
                  ? (
                    "The agent is combining collected "
                    + "evidence with retrieved operational "
                    + "guidance."
                  )
                  : (
                    "The agent is gathering shipment, "
                    + "history, weather, and supplier "
                    + "evidence."
                  )}
              </p>
            </div>
          </div>
        )}

        {failure && !busy && (
          <div
            className={
              (
                "empty "
                + (
                  status === "failed"
                    ? "err"
                    : ""
                )
              )
            }
          >
            <b>
              {failure.message}
            </b>

            {failure.detail && (
              <p>
                {failure.detail}
              </p>
            )}
          </div>
        )}

        {!failure
          && !busy
          && shown.length === 0
          && (
            <Empty>
              No evidence yet. Start an investigation to
              see what the agent finds.
            </Empty>
          )}

        {shown.length > 0 && (
          <>
            <h3 className="timeline-heading">
              Investigation progress
            </h3>

            <ol className="trace">
              {shown.map(
                (
                  entry,
                  index,
                ) => (
                  <li
                    key={
                      entry.tool
                      || `${entry.label}-${index}`
                    }
                    className={
                      entry.status
                    }
                  >
                    <small>
                      {
                        STEP_STATUS[
                          entry.status
                        ]
                      }
                    </small>

                    <b>
                      {entry.label}
                    </b>

                    {entry.finding && (
                      <span>
                        {entry.finding}
                      </span>
                    )}
                  </li>
                ),
              )}
            </ol>
          </>
        )}
      </section>

      <InvestigationEvidence
        shipment={shipment}
      />

      {(citations.length > 0 || busy) && (
        <section className="panel knowledge-panel">
          <div className="section-copy">
            <small className="eyebrow">
              RAG knowledge
            </small>

            <h3>
              Operational guidance used
            </h3>

            <p>
              These synthetic demonstration documents were
              retrieved from the operational knowledge base.
            </p>
          </div>

          <CitationList
            citations={citations}
          />
        </section>
      )}

      {limitations.length > 0 && (
        <section className="panel limitations-panel">
          <div className="section-copy">
            <small className="eyebrow">
              Decision boundaries
            </small>

            <h3>
              Limitations and required validation
            </h3>

            <p>
              Review these constraints before approving any
              mitigation action.
            </p>
          </div>

          <ul className="limitations-list">
            {limitations.map(
              (
                limitation,
                index,
              ) => (
                <li
                  key={
                    `${index}-${limitation}`
                  }
                >
                  {limitation}
                </li>
              ),
            )}
          </ul>
        </section>
      )}
    </div>
  );
}