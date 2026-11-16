export function windowSentence(dayOnFeed: number, packageName?: string) {
  const day = Math.min(Math.max(dayOnFeed, 0), 45);
  const match = packageName ? /vet_day_(\d)/.exec(packageName) : null;
  if (!match) {
    const last = Math.min(day + 6, 45);
    const detail = packageName
      ? `Day ${day} of 45. Pen checks in this package run from day ${day} through day ${last}.`
      : `Day ${day} of 45. The risk window is the first 45 days after arrival.`;
    return { day, actionDay: null as number | null, detail };
  }
  const falls = day + Number(match[1]);
  if (falls > 45) {
    return {
      day,
      actionDay: null,
      detail: `Day ${day} of 45. The veterinary review would fall on day ${falls}, outside this window.`,
    };
  }
  return {
    day,
    actionDay: falls,
    detail: `Day ${day} of 45. The veterinary review falls on day ${falls} of 45.`,
  };
}
