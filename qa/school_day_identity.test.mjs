import test from 'node:test';
import assert from 'node:assert/strict';
import {isArtificialFreeAccount, ownsArtificialBeta} from './school_day_identity.mjs';

test('paid beta requires the exact generated family and recovery journal', () => {
  const nonce = 'a'.repeat(20), email = `owner+schuleschlau-beta-qa-${nonce}@gmail.com`, child = `beta-qa-${nonce}`;
  const account = {normal_account: true, verified: true, child_id: 'child',
    credentials: {parent_username: email, child_username: child}, user: {id: 'parent', families: [{id: 'family'}]}};
  const journal = {verified: true, email, child, child_id: 'child', user_id: 'parent', family_id: 'family'};
  assert.equal(ownsArtificialBeta(account, journal), true);
  for (const altered of [{...journal, child_id: 'other'}, {...journal, family_id: 'other'},
    {...journal, email: 'other@gmail.com'}, {...journal, verified: false}, null]) {
    assert.equal(ownsArtificialBeta(account, altered), false);
  }
  assert.equal(ownsArtificialBeta({...account, credentials: {...account.credentials, child_username: 'actual-child'}}, journal), false);
});

test('existing free path accepts only its artificial alias', () => {
  assert.equal(isArtificialFreeAccount({normal_account: true, verified: true, credentials: {parent_username: 'owner+schulpilot-normal-qa-aaaaaaaaaaaa@gmail.com'}}), true);
  assert.equal(isArtificialFreeAccount({normal_account: true, verified: true, credentials: {parent_username: 'owner@gmail.com'}}), false);
});
