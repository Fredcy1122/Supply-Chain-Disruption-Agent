import {
  NA,
  RiskBadge,
  number,
} from "./ui.jsx";


const units = (
  value,
  suffix = "units",
) => (
  typeof value === "number"
  && Number.isFinite(value)
    ? `${value.toLocaleString()} ${suffix}`
    : NA
);


const dateText = (
  value,
) => {
  if (!value) {
    return NA;
  }

  const parsed = new Date(
    `${value}T00:00:00`,
  );

  if (Number.isNaN(
    parsed.getTime(),
  )) {
    return value;
  }

  return parsed.toLocaleDateString(
    undefined,
    {
      year: "numeric",
      month: "short",
      day: "numeric",
    },
  );
};


export default function InventoryEvidence({
  inventory,
  coverage,
  compact = false,
}) {
  if (!inventory) {
    if (
      coverage !== null
      && coverage !== undefined
    ) {
      return (
        <>
          <strong className="evidence-value">
            {number(
              coverage,
              2,
            )} days
          </strong>

          <p>
            Inventory coverage was collected, but
            detailed stock evidence was not available.
          </p>
        </>
      );
    }

    return (
      <p className="muted-text">
        Inventory coverage is unavailable. Stockout
        exposure cannot be confirmed.
      </p>
    );
  }

  const risk = String(
    inventory.stockoutRisk
    || "unknown",
  ).toLowerCase();

  const thresholdAlerts = [];

  if (inventory.belowSafetyStock) {
    thresholdAlerts.push(
      "Available stock is at or below safety stock.",
    );
  }

  if (inventory.belowReorderPoint) {
    thresholdAlerts.push(
      "Available stock is at or below the reorder point.",
    );
  }

  if (
    inventory.destinationCountryMatch
    === false
  ) {
    thresholdAlerts.push(
      "Warehouse country does not match the shipment destination.",
    );
  }

  return (
    <div
      className={
        `inventory-evidence ${compact ? "compact" : ""}`
      }
    >
      <div className="inventory-heading">
        <div>
          <strong>
            {inventory.productName}
          </strong>

          <span>
            {inventory.warehouseId}
            {" · "}
            {inventory.warehouseLocation}
            {inventory.warehouseCountry
              ? `, ${inventory.warehouseCountry}`
              : ""}
          </span>
        </div>

        <RiskBadge
          level={risk}
        />
      </div>

      <dl className="inventory-facts">
        <div>
          <dt>Available stock</dt>
          <dd>
            {units(
              inventory.availableStock,
            )}
          </dd>
        </div>

        <div>
          <dt>Reserved stock</dt>
          <dd>
            {units(
              inventory.reservedStock,
            )}
          </dd>
        </div>

        <div>
          <dt>Daily demand</dt>
          <dd>
            {units(
              inventory.dailyDemand,
              "units/day",
            )}
          </dd>
        </div>

        <div>
          <dt>Coverage</dt>
          <dd>
            {number(
              inventory
                .inventoryCoverageDays,
              2,
            )} days
          </dd>
        </div>

        <div>
          <dt>Safety stock</dt>
          <dd>
            {units(
              inventory.safetyStock,
            )}
          </dd>
        </div>

        <div>
          <dt>Reorder point</dt>
          <dd>
            {units(
              inventory.reorderPoint,
            )}
          </dd>
        </div>

        <div>
          <dt>Incoming inventory</dt>
          <dd>
            {units(
              inventory.incomingQuantity,
            )}
          </dd>
        </div>

        <div>
          <dt>Expected replenishment</dt>
          <dd>
            {dateText(
              inventory
                .expectedReplenishmentDate,
            )}
          </dd>
        </div>
      </dl>

      {thresholdAlerts.length > 0 && (
        <div
          className={
            `inventory-alert ${risk}`
          }
        >
          {thresholdAlerts.map(
            (
              alert,
            ) => (
              <p key={alert}>
                {alert}
              </p>
            ),
          )}
        </div>
      )}

      <p className="inventory-disclosure">
        Warehouse
        quantities, reservations, replenishment timing,
        and transfer feasibility require operational
        validation.
      </p>
    </div>
  );
}