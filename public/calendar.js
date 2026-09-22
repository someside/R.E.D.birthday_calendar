export const MIN_YEAR = 2020;
export const MAX_YEAR = 2100;
export const isLeapYear = year => year % 4 === 0 && (year % 100 !== 0 || year % 400 === 0);
export function observedDay(member, year) {
  return member.month === 2 && member.day === 29 && !isLeapYear(year) ? 28 : member.day;
}
export function monthMembers(members, selected, year, month) {
  return members.filter(m => selected.has(m.group) && m.month === month)
    .map(m => ({ ...m, displayDay: observedDay(m, year), shifted: observedDay(m, year) !== m.day }))
    .sort((a, b) => a.displayDay - b.displayDay || a.name.localeCompare(b.name, 'zh-CN'));
}
export function monthCells(year, month) {
  const offset = (new Date(year, month - 1, 1).getDay() + 6) % 7;
  const days = new Date(year, month, 0).getDate();
  const length = Math.ceil((offset + days) / 7) * 7;
  return Array.from({ length }, (_, i) => {
    const date = new Date(year, month - 1, i - offset + 1);
    return { day: date.getDate(), current: i >= offset && i < offset + days };
  });
}
