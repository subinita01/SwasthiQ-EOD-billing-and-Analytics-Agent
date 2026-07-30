const RUPEE_FORMATTER = new Intl.NumberFormat("en-IN", {
  style: "currency",
  currency: "INR",
  minimumFractionDigits: 2,
  maximumFractionDigits: 2,
});

export function formatPaise(paise) {
  return RUPEE_FORMATTER.format(paise / 100);
}

export function formatHour(hour) {
  const h = ((hour % 24) + 24) % 24;
  const period = h < 12 ? "AM" : "PM";
  const twelveHour = h % 12 === 0 ? 12 : h % 12;
  return `${twelveHour}:00 ${period}`;
}
