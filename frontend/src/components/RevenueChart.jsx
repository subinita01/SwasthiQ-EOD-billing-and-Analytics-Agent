import { useMemo, useState } from "react";
import { formatHour, formatPaise } from "../utils/format";

const CHART_HEIGHT = 200;
// Reserve space at the top and bottom of the plot so the tallest positive
// bar and the deepest negative bar never render flush against the plot's
// edge - without this, a negative bar can legitimately reach y=CHART_HEIGHT
// exactly and visually run into the axis labels sitting just below it.
const PLOT_PADDING = 14;
const DRAWABLE_HEIGHT = CHART_HEIGHT - PLOT_PADDING * 2;
const MAX_BAR_WIDTH = 24;
const BAR_GAP = 2;
const CORNER_RADIUS = 4;

function barPath(x, barWidth, yTop, barHeight, roundedAtTop) {
  const w = barWidth;
  const h = Math.max(barHeight, 0.0001);
  const r = Math.min(CORNER_RADIUS, w / 2, h);

  if (roundedAtTop) {
    return `
      M ${x} ${yTop + h}
      L ${x} ${yTop + r}
      Q ${x} ${yTop} ${x + r} ${yTop}
      L ${x + w - r} ${yTop}
      Q ${x + w} ${yTop} ${x + w} ${yTop + r}
      L ${x + w} ${yTop + h}
      Z
    `;
  }
  return `
    M ${x} ${yTop}
    L ${x} ${yTop + h - r}
    Q ${x} ${yTop + h} ${x + r} ${yTop + h}
    L ${x + w - r} ${yTop + h}
    Q ${x + w} ${yTop + h} ${x + w} ${yTop + h - r}
    L ${x + w} ${yTop}
    Z
  `;
}

export default function RevenueChart({ hourly, peakHour }) {
  const [hoveredHour, setHoveredHour] = useState(null);

  const hasNegative = hourly.some((h) => h.revenue_paise < 0);
  const maxPositive = Math.max(0, ...hourly.map((h) => h.revenue_paise));
  const maxNegativeMagnitude = Math.max(0, ...hourly.map((h) => -h.revenue_paise));
  const totalRange = maxPositive + maxNegativeMagnitude || 1;
  const baselineY = PLOT_PADDING + (maxPositive / totalRange) * DRAWABLE_HEIGHT;

  const slotWidth = 100 / hourly.length;
  const barWidth = Math.min(MAX_BAR_WIDTH, slotWidth - BAR_GAP);

  const bars = useMemo(
    () =>
      hourly.map((h, i) => {
        const barHeight = (Math.abs(h.revenue_paise) / totalRange) * DRAWABLE_HEIGHT;
        const yTop = h.revenue_paise >= 0 ? baselineY - barHeight : baselineY;
        return {
          ...h,
          index: i,
          xPercent: i * slotWidth + (slotWidth - barWidth) / 2,
          yTop,
          barHeight,
          isPeak: h.hour === peakHour,
        };
      }),
    [hourly, totalRange, baselineY, slotWidth, barWidth, peakHour],
  );

  const peakBar = bars.find((b) => b.isPeak);
  const hoveredBar = bars.find((b) => b.hour === hoveredHour);

  return (
    <div className="panel">
      <div className="revenue-chart__header">
        <h3 className="panel__title">Revenue by hour of day (UTC)</h3>
        {hasNegative && (
          <div className="legend">
            <span className="legend__item">
              <span className="legend__swatch legend__swatch--positive" /> Net revenue
            </span>
            <span className="legend__item">
              <span className="legend__swatch legend__swatch--negative" /> Net refund
            </span>
          </div>
        )}
      </div>

      {peakBar && (
        <p className="revenue-chart__peak">
          Peak hour: <strong>{formatHour(peakBar.hour)}</strong> (
          {formatPaise(peakBar.revenue_paise)})
        </p>
      )}

      <div className="revenue-chart__plot">
        <svg
          className="revenue-chart__svg"
          viewBox={`0 0 100 ${CHART_HEIGHT}`}
          preserveAspectRatio="none"
          role="img"
          aria-label="Bar chart of net revenue by hour of day"
        >
          <line
            x1="0"
            x2="100"
            y1={baselineY}
            y2={baselineY}
            className="revenue-chart__baseline"
            vectorEffect="non-scaling-stroke"
          />
          {bars.map((bar) => (
            <g
              key={bar.hour}
              onMouseEnter={() => setHoveredHour(bar.hour)}
              onMouseLeave={() => setHoveredHour(null)}
              className="revenue-chart__bar-group"
            >
              <rect
                x={bar.xPercent}
                y="0"
                width={barWidth}
                height={CHART_HEIGHT}
                fill="transparent"
              />
              <path
                d={barPath(bar.xPercent, barWidth, bar.yTop, bar.barHeight, bar.revenue_paise >= 0)}
                className={
                  bar.revenue_paise >= 0
                    ? "revenue-chart__bar revenue-chart__bar--positive"
                    : "revenue-chart__bar revenue-chart__bar--negative"
                }
                data-hovered={bar.hour === hoveredHour}
                data-peak={bar.isPeak}
              />
            </g>
          ))}
        </svg>

        {hoveredBar && (
          <div
            className="revenue-chart__tooltip"
            style={{ left: `${hoveredBar.xPercent + barWidth / 2}%` }}
          >
            <strong>{formatHour(hoveredBar.hour)}</strong>
            <span>{formatPaise(hoveredBar.revenue_paise)}</span>
          </div>
        )}
      </div>

      <div className="revenue-chart__axis">
        {bars
          .filter((b) => b.hour % 3 === 0)
          .map((b) => (
            <span key={b.hour} style={{ left: `${b.xPercent + barWidth / 2}%` }}>
              {b.hour}
            </span>
          ))}
      </div>

      <details className="table-toggle">
        <summary>View as table</summary>
        <div className="table-scroll">
          <table className="data-table">
            <thead>
              <tr>
                <th>Hour (UTC)</th>
                <th className="num">Net revenue</th>
              </tr>
            </thead>
            <tbody>
              {hourly.map((h) => (
                <tr key={h.hour} className={h.hour === peakHour ? "is-peak-row" : undefined}>
                  <td>
                    {formatHour(h.hour)}
                    {h.hour === peakHour ? " (peak)" : ""}
                  </td>
                  <td className="num tabular">{formatPaise(h.revenue_paise)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </details>
    </div>
  );
}
