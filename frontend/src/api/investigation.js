// Consumes the backend investigation stream and converts its events
// into the frontend shipment fields used by React components.

const NA = "Not available";
const FAILED = "Investigation failed";




export class ApiError extends Error {
  constructor(
    status,
    message,
    detail,
    code,
  ) {
    super(message);

    this.name = "ApiError";
    this.status = status;
    this.detail = detail;
    this.code = code;
  }
}


const MESSAGES = {
  investigation_not_required:
    "Low risk — no investigation needed",

  shipment_not_found:
    "Shipment not found",

  investigation_failed:
    "Investigation failed",

  404:
    "Shipment not found",
};


const messageFor = (
  code,
  status,
) => (
  MESSAGES[code]
  || MESSAGES[status]
  || FAILED
);


const malformed = () =>
  new ApiError(
    0,
    FAILED,
    (
      "The server sent a response "
      + "that could not be understood."
    ),
  );


const isObject = (
  value,
) => (
  value !== null
  && typeof value === "object"
  && !Array.isArray(value)
);


const capitalize = (
  value,
) => {
  const text = String(
    value ?? "",
  )
    .replace(/_/g, " ")
    .toLowerCase();

  return (
    text.charAt(0).toUpperCase()
    + text.slice(1)
  );
};


const percent = (
  probability,
) => {
  const value = Number(
    probability,
  );

  if (!Number.isFinite(value)) {
    return NA;
  }

  return `${(
    value * 100
  ).toFixed(1)}%`;
};


async function* readEvents(
  body,
) {
  const reader = body.getReader();
  const decoder = new TextDecoder();

  let buffer = "";

  try {
    for (;;) {
      const {
        value,
        done,
      } = await reader.read();

      if (done) {
        return;
      }

      buffer = (
        buffer
        + decoder.decode(
          value,
          {
            stream: true,
          },
        )
      ).replace(
        /\r\n/g,
        "\n",
      );

      let eventEnd;

      while (
        (
          eventEnd = buffer.indexOf(
            "\n\n",
          )
        ) !== -1
      ) {
        const block = buffer.slice(
          0,
          eventEnd,
        );

        buffer = buffer.slice(
          eventEnd + 2,
        );

        let event = "message";
        const dataLines = [];

        for (
          const line
          of block.split("\n")
        ) {
          if (
            line.startsWith("event:")
          ) {
            event = line
              .slice(6)
              .trim();
          } else if (
            line.startsWith("data:")
          ) {
            dataLines.push(
              line
                .slice(5)
                .replace(/^ /, ""),
            );
          }
        }

        // Ignore comments and keep-alive blocks.
        if (dataLines.length) {
          yield {
            event,
            data: dataLines.join("\n"),
          };
        }
      }
    }
  } finally {
    reader
      .cancel()
      .catch(() => {});
  }
}


const toEvidence = (
  toolCall,
) => ({
  tool:
    toolCall.tool
    ?? toolCall.name,

  input:
    toolCall.input
    ?? {},

  output:
    toolCall.status === "error"
      ? toolCall.error
      : toolCall.output,

  status:
    toolCall.status,
});


const uniqueStrings = (
  values,
) => {
  if (!Array.isArray(values)) {
    return [];
  }

  return [
    ...new Set(
      values
        .filter(
          (value) =>
            typeof value === "string"
            && value.trim(),
        )
        .map(
          (value) =>
            value.trim(),
        ),
    ),
  ];
};


const citationTitle = (
  filename,
) => String(
  filename,
)
  .replace(
    /\.pdf$/i,
    "",
  )
  .replace(
    /^\d+_/,
    "",
  )
  .replace(
    /_/g,
    " ",
  )
  .replace(
    /\b\w/g,
    (character) =>
      character.toUpperCase(),
  );


const toRecommendation = (
  action,
  index,
  shipmentId,
) => ({
  id:
    `${shipmentId}-${index + 1}`,

  title:
    action,

  detail:
    (
      "Generated from the collected "
      + "evidence and retrieved "
      + "synthetic operational guidance."
    ),

  cost:
    null,

  time:
    null,

  risk:
    null,

  source:
    "Grounded disruption briefing",
});


function validateDonePayload(
  briefing,
) {
  if (
    !isObject(briefing)
    || typeof briefing.shipment_id
      !== "string"
    || typeof briefing.risk_level
      !== "string"
    || typeof briefing.delay_probability
      !== "number"
    || typeof briefing.summary
      !== "string"
    || !isObject(
      briefing.evidence,
    )
    || !Array.isArray(
      briefing.tool_trace,
    )
    || !Array.isArray(
      briefing.recommended_actions,
    )
    || !Array.isArray(
      briefing.rag_policy_citations,
    )
    || !Array.isArray(
      briefing.limitations,
    )
  ) {
    throw malformed();
  }
}


function toResult(
  briefing,
) {
  validateDonePayload(
    briefing,
  );

  const toolTrace = (
    briefing.tool_trace
      .map(toEvidence)
  );

  const structuredEvidence = {
    shipmentSummary:
      briefing.evidence
        .shipment_summary
      ?? null,

    historicalDelaySummary:
      briefing.evidence
        .historical_delay_summary
      ?? null,

    weatherSummary:
      briefing.evidence
        .weather_summary
      ?? null,

    supplierStatus:
      briefing.evidence
        .supplier_status
      ?? null,

    inventoryCoverageDays:
      briefing.evidence
        .inventory_coverage_days
      ?? null,
  };

  const cause = [
    structuredEvidence
      .historicalDelaySummary,

    structuredEvidence
      .weatherSummary,

    structuredEvidence
      .supplierStatus,
  ]
    .filter(Boolean)
    .join(" ");

  const actions = uniqueStrings(
    briefing.recommended_actions,
  );

  const citations = uniqueStrings(
    briefing.rag_policy_citations,
  );

  const limitations = uniqueStrings(
    briefing.limitations,
  );

  const citationCards = citations.map(
    (filename) => ({
      filename,

      title:
        citationTitle(
          filename,
        ),

      sourceType:
        "Synthetic operational guidance",
    }),
  );

  const recommendations = actions.map(
    (
      action,
      index,
    ) =>
      toRecommendation(
        action,
        index,
        briefing.shipment_id,
      ),
  );

  const inventoryImpact = (
    structuredEvidence
      .inventoryCoverageDays
    !== null
  )
    ? (
      "Inventory coverage is "
      + `${structuredEvidence
        .inventoryCoverageDays} days.`
    )
    : (
      "Inventory impact cannot be "
      + "confirmed because inventory "
      + "coverage is unavailable."
    );

  return {
    shipmentId:
      briefing.shipment_id,

    riskLevel:
      briefing.risk_level
        .toLowerCase(),

    delayProbability:
      briefing.delay_probability,

    requiresInvestigation:
      true,

    investigationStatus:
      "complete",

    // Compatibility field used by the current Investigation component.
    evidence:
      toolTrace,

    toolTrace,

    structuredEvidence,

    conclusion:
      briefing.summary,

    briefing: {
      summary:
        briefing.summary,

      cause:
        cause || NA,

      impact:
        inventoryImpact,

      actions:
        actions.join(" "),

      recommendedActions:
        actions,

      citations,

      citationCards,

      limitations,

      generatedAt:
        new Date()
          .toLocaleString(),
    },

    recommendations,

    recommendedActions:
      actions,

    recommendationsPending:
      false,

    ragPolicyCitations:
      citations,

    citationCards,

    limitations,

    rawBriefing:
      briefing,
  };
}


function lowRiskDetail(
  evidence,
) {
  const risk = evidence.find(
    (item) =>
      item.tool === "get_delay_risk"
      && item.status === "success",
  )?.output;

  if (
    typeof risk?.shipment_id
      !== "string"
    || typeof risk
      ?.delay_probability
      !== "number"
  ) {
    return null;
  }

  return (
    `Shipment ${risk.shipment_id} `
    + "has a low risk of delay "
    + `(${percent(
      risk.delay_probability,
    )}) and does not require `
    + "further investigation."
  );
}


export async function investigate(
  id,
  onUpdate,
  {
    signal,
    fetch: fetchFn = fetch,
  } = {},
) {
  let response;

  try {
    response = await fetchFn(
      (
        "/api/agent/investigate/"
        + `${encodeURIComponent(id)}`
        + "/stream"
      ),
      {
        method:
          "GET",

        headers: {
          Accept:
            "text/event-stream",
        },

        signal,
      },
    );
  } catch (error) {
    if (signal?.aborted) {
      throw error;
    }

    throw new ApiError(
      0,
      FAILED,
      "The backend could not be reached.",
    );
  }

  if (!response.ok) {
    const body = await response
      .json()
      .catch(() => ({}));

    const detail = (
      typeof body.detail === "string"
        ? body.detail
        : undefined
    );

    throw new ApiError(
      response.status,
      messageFor(
        body.code,
        response.status,
      ),
      detail,
      body.code,
    );
  }

  const contentType = (
    response.headers.get(
      "content-type",
    )
    || ""
  );

  if (
    !response.body
    || !contentType.includes(
      "text/event-stream",
    )
  ) {
    throw malformed();
  }

  let evidence = [];

  const update = (
    patch,
  ) => {
    if (
      typeof onUpdate
      === "function"
    ) {
      onUpdate(patch);
    }
  };

  const finishTool = (
    data,
  ) => {
    const completedCall = (
      toEvidence(
        data,
      )
    );

    const lastIndex = (
      evidence.length - 1
    );

    const lastEntry = (
      evidence[lastIndex]
    );

    if (
      lastEntry?.tool
        === completedCall.tool
      && lastEntry.status
        === "running"
    ) {
      evidence = [
        ...evidence.slice(
          0,
          lastIndex,
        ),
        completedCall,
      ];
    } else {
      evidence = [
        ...evidence,
        completedCall,
      ];
    }

    update({
      evidence,
      toolTrace:
        evidence,
    });
  };

  try {
    for await (
      const {
        event,
        data: rawData,
      }
      of readEvents(
        response.body,
      )
    ) {
      let data;

      try {
        data = JSON.parse(
          rawData,
        );
      } catch {
        throw malformed();
      }

      if (!isObject(data)) {
        throw malformed();
      }

      if (
        event === "tool_start"
      ) {
        if (
          typeof data.name
          !== "string"
        ) {
          throw malformed();
        }

        evidence = [
          ...evidence,
          {
            tool:
              data.name,

            input:
              data.input
              ?? {},

            status:
              "running",
          },
        ];

        update({
          investigationStatus:
            "running",

          evidence,

          toolTrace:
            evidence,
        });
      } else if (
        event === "tool_complete"
        || event === "tool_error"
      ) {
        if (
          typeof data.name
          !== "string"
        ) {
          throw malformed();
        }

        finishTool({
          ...data,

          status:
            event === "tool_error"
              ? "error"
              : "success",
        });
      } else if (
        event === "message"
      ) {
        if (
          typeof data.content
          !== "string"
        ) {
          throw malformed();
        }

        update({
          conclusion:
            data.content,

          investigationStatus:
            "generating_briefing",
        });
      } else if (
        event === "done"
      ) {
        const result = (
          toResult(
            data,
          )
        );

        update(result);

        return result;
      } else if (
        event === "error"
      ) {
        const detail = (
          typeof data.detail
            === "string"
            ? data.detail
            : undefined
        );

        throw new ApiError(
          typeof data.status
            === "number"
            ? data.status
            : 0,

          messageFor(
            data.code,
            data.status,
          ),

          (
            data.code
              === "investigation_not_required"
            && lowRiskDetail(
              evidence,
            )
          )
          || detail,

          data.code,
        );
      }

      // Unknown event names are ignored so the backend can add
      // new progress events without breaking older frontends.
    }
  } catch (error) {
    if (
      error instanceof ApiError
      || signal?.aborted
    ) {
      throw error;
    }

    throw new ApiError(
      0,
      FAILED,
      (
        "The connection to the "
        + "backend was lost."
      ),
    );
  }

  throw new ApiError(
    0,
    FAILED,
    (
      "The connection closed before "
      + "the investigation finished."
    ),
  );
}


export function failureDetail(
  error,
) {
  if (
    error.status === 0
    || error.code
      === "investigation_not_required"
    || error.code
      === "shipment_not_found"
  ) {
    return error.detail;
  }

  if (error.status === 404) {
    return undefined;
  }

  return (
    "Something went wrong while "
    + "investigating this shipment. "
    + "Please try again."
  );
}


const HIGHEST_FACTOR = {
  product:
    "Product",

  market:
    "Market",

  shipping_mode:
    "Shipping mode",
};


const supplierFinding = (
  output,
) => {
  const supplier = (
    output?.recommended_supplier
  );

  if (!supplier) {
    const candidateCount = Number(
      output?.candidate_count,
    );

    if (
      Number.isFinite(
        candidateCount,
      )
      && candidateCount > 0
    ) {
      return (
        `${candidateCount} comparison `
        + (
          candidateCount === 1
            ? "candidate"
            : "candidates"
        )
        + " found; human review required"
      );
    }

    return (
      "No suitable synthetic "
      + "supplier candidate found"
    );
  }

  return (
    `${supplier.supplier_name} `
    + `· ${supplier.supplier_country} `
    + `· ${capitalize(
      supplier.supplier_risk_level,
    )} risk`
  );
};


const STEPS = {
  get_delay_risk: {
    label:
      "Assessing delay risk",

    finding: (output) =>
      (
        `${capitalize(
          output.risk_level,
        )} risk · `
        + `${percent(
          output.delay_probability,
        )} probability`
      ),
  },

  get_shipment: {
    label:
      "Checking shipment details",

    finding: (output) =>
      (
        `${output.destination_city}, `
        + `${output.destination_country} `
        + `· ${output.shipping_mode}`
      ),
  },

  get_historical_delay_context: {
    label:
      "Reviewing historical delay patterns",

    finding: (output) => {
      const factor = (
        output
          .highest_delay_rate_factor
      );

      return (
        `${HIGHEST_FACTOR[factor]} `
        + "has the highest historical "
        + "delay rate "
        + `(${percent(
          output
            .historical_delay_rates[
              factor
            ],
        )})`
      );
    },
  },

  get_destination_weather: {
    label:
      "Checking destination weather",

    finding: (output) =>
      (
        `${capitalize(
          output
            .worst_weather_description,
        )} · `
        + `${capitalize(
          output.severity,
        )} severity`
      ),
  },

  find_alternative_supplier: {
    label:
      "Checking alternative suppliers",

    finding:
      supplierFinding,
  },
};


const OTHER_STEP = {
  label:
    "Gathering additional evidence",

  finding:
    () => null,
};


function findingFor(
  step,
  output,
) {
  try {
    const text = step.finding(
      output,
    );

    if (
      typeof text !== "string"
      || /undefined|null|NaN/.test(
        text,
      )
    ) {
      return null;
    }

    return text;
  } catch {
    return null;
  }
}


export function toSteps(
  shipment,
) {
  const running = (
    shipment.investigationStatus
      === "running"
    || shipment.investigationStatus
      === "generating_briefing"
  );

  const toolTrace = (
    shipment.toolTrace
    || shipment.evidence
    || []
  );

  const steps = toolTrace.map(
    (entry) => {
      const step = (
        Object.hasOwn(
          STEPS,
          entry.tool,
        )
      )
        ? STEPS[entry.tool]
        : OTHER_STEP;

      if (
        entry.status === "success"
      ) {
        return {
          tool:
            entry.tool,

          label:
            step.label,

          finding:
            findingFor(
              step,
              entry.output,
            ),

          status:
            "done",
        };
      }

      if (
        entry.status === "running"
        && running
      ) {
        return {
          tool:
            entry.tool,

          label:
            step.label,

          finding:
            null,

          status:
            "running",
        };
      }

      return {
        tool:
          entry.tool,

        label:
          step.label,

        finding:
          (
            "This information could "
            + "not be retrieved."
          ),

        status:
          "failed",
      };
    },
  );

  if (shipment.briefing) {
    steps.push({
      tool:
        "generate_briefing",

      label:
        "Generating disruption briefing",

      finding:
        shipment.briefing.summary,

      status:
        "complete",
    });
  } else if (
    shipment.investigationStatus
      === "generating_briefing"
  ) {
    steps.push({
      tool:
        "generate_briefing",

      label:
        "Generating disruption briefing",

      finding:
        null,

      status:
        "running",
    });
  }

  return steps;
}