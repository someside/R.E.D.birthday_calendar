import test from 'node:test';
import assert from 'node:assert/strict';
import { isLeapYear, monthMembers, monthCells } from '../public/calendar.js';
test('Gregorian century boundary: 2100 is not a leap year', () => {
  assert.equal(isLeapYear(2020), true);
  assert.equal(isLeapYear(2100), false);
  const member = { name: 'A', group: 'one', month: 2, day: 29 };
  assert.equal(monthMembers([member], new Set(['one']), 2020, 2)[0].displayDay, 29);
  assert.equal(monthMembers([member], new Set(['one']), 2100, 2)[0].displayDay, 28);
});
test('Multi-select uses union and empty selection returns no birthdays', () => {
  const members = [{ name:'A',group:'one',month:1,day:20 },{ name:'B',group:'two',month:1,day:4 },{ name:'C',group:'three',month:1,day:4 }];
  assert.deepEqual(monthMembers(members,new Set(['one','two']),2020,1).map(m=>m.name),['B','A']);
  assert.deepEqual(monthMembers(members,new Set(),2020,1),[]);
});
test('Every supported month has exactly the right dates, on Monday-first weeks', () => {
  for(let y=2020;y<=2100;y++) for(let m=1;m<=12;m++) {
    const cells=monthCells(y,m), current=cells.filter(c=>c.current);
    assert.equal(cells.length%7,0);
    assert.equal(current.length,new Date(y,m,0).getDate());
    assert.equal(current[0].day,1);
    assert.equal(cells.findIndex(c=>c.current),(new Date(y,m-1,1).getDay()+6)%7);
    assert.equal(current.at(-1).day,current.length);
  }
});
