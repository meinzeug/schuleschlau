import test from 'node:test';
import assert from 'node:assert/strict';
import {hasActivePreparation, pagePreparationSettled, preparationFailureCode} from './school_day_status.mjs';

const pages = [{status: 'review'}, {status: 'confirmed'}];
test('recognition alone does not mean counterchecking has finished', () => {
  assert.equal(pagePreparationSettled({pages, active_job: {status: 'running'}, preparation: {status: 'processing'}}), false);
  assert.equal(pagePreparationSettled({pages, preparation: {status: 'processing'}}), false);
  assert.equal(pagePreparationSettled({pages, preparation: {status: 'ready'}}), true);
  assert.equal(pagePreparationSettled({pages: [{status: 'uploaded'}, pages[1]], preparation: {status: 'ready'}}), false);
  assert.equal(pagePreparationSettled({preparation: {status: 'ready'}}), false);
});

test('a later package failure is not misreported as failed recognition', () => {
  assert.equal(preparationFailureCode({preparation: {phase: 'package'}}, 'real_page_recognition'), 'automatic_package_failed_no_automatic_retry');
  assert.equal(preparationFailureCode({preparation: {phase: 'extract'}}, 'real_page_recognition'), 'real_page_recognition_failed_no_automatic_retry');
});

test('an older error does not hide a currently running explicit retry', () => {
  assert.equal(hasActivePreparation({last_error: 'old error', preparation: {status: 'processing'}}), true);
  assert.equal(hasActivePreparation({last_error: 'old error', active_job: {status: 'queued'}}), true);
  assert.equal(hasActivePreparation({last_error: 'new error', preparation: {status: 'failed'}}), false);
});
