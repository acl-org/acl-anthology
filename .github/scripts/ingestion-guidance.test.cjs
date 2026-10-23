const assert = require('node:assert/strict');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const { test } = require('node:test');
const {
  START, END, ConfigurationError, IssueStateError, loadPolicy, parseAnswers,
  validDate, addDays, readManaged, renderGuidance, dueReminders, renderReminder,
  applyGuidance, sendReminders,
} = require('./ingestion-guidance.cjs');

const ROOT = path.resolve(__dirname, '../..');
const CONTENT = path.join(ROOT, '.github/ingestion');
const policy = loadPolicy();
const fields = policy.settings.fields;

function form({
  platforms = ['openreview'], affiliation = 'Yes', publication = '2027-01-15',
  cutoff = '', newVenue = false, historical = false,
} = {}) {
  const question = (name, answer) => `### ${fields[name]}\n\n${answer || '_No response_'}\n\n`;
  return question('general', [
    '- [x] I will keep this issue up to date and check off tasks.',
    `- [${newVenue ? 'x' : ' '}] This request includes a **new venue**.`,
    `- [${historical ? 'x' : ' '}] This submission is historical material.`,
  ].join('\n'))
    + question('venue', 'example')
    + question('affiliation', affiliation)
    + question('title', 'Proceedings of the Example Conference')
    + question('publication', publication)
    + question('cutoff', cutoff)
    + question('platforms', Object.entries(policy.settings.platforms)
      .map(([key, label]) => `- [${platforms.includes(key) ? 'x' : ' '}] ${label}`)
      .join('\n'))
    + '### Supporting Information\n\nA provisional list of volumes and notes.\n';
}

function generated(options) {
  return renderGuidance(form(options), policy);
}

function toggle(body, id, checked = true) {
  let found = false;
  const result = body.split('\n').map(line => {
    if (!line.includes(`<!-- ingestion-task:${id}:`)) return line;
    found = true;
    return line.replace(/^- \[[ xX]\]/, `- [${checked ? 'x' : ' '}]`);
  }).join('\n');
  assert(found, `Missing generated task ${id}`);
  return result;
}

function completeDated(body) {
  const model = renderGuidance(body, policy).model;
  for (const task of model.tasks.filter(task => task.deadline)) body = toggle(body, task.id);
  return body;
}

function botComment(body) {
  return { body, user: { login: 'github-actions[bot]' } };
}

function policyFixture(t, edit) {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), 'anthology-ingestion-test-'));
  fs.cpSync(CONTENT, root, { recursive: true });
  t.after(() => fs.rmSync(root, { recursive: true, force: true }));
  edit(root);
  return root;
}

function editSettings(root, edit) {
  const file = path.join(root, 'settings.json');
  const value = JSON.parse(fs.readFileSync(file, 'utf8'));
  edit(value);
  fs.writeFileSync(file, JSON.stringify(value));
}

function editFile(root, name, edit) {
  const file = path.join(root, name);
  fs.writeFileSync(file, edit(fs.readFileSync(file, 'utf8')));
}

function apiHarness(body = generated().body) {
  const issue = {
    number: 42, body, state: 'open', labels: [{ name: 'ingestion' }],
    user: { login: 'organizer' },
    html_url: 'https://github.com/acl-org/acl-anthology/issues/42',
    assignees: [{ login: 'anthology-assist' }],
  };
  const issues = new Map([[42, issue]]);
  const comments = new Map();
  const writes = { updates: [], comments: [] };
  const logs = { info: [], warning: [], error: [] };
  const hooks = {};
  const core = Object.fromEntries(Object.keys(logs).map(level =>
    [level, message => logs[level].push(message)]));
  const endpoints = {
    get: async params => {
      if (hooks.get) hooks.get(params);
      return { data: structuredClone(issues.get(params.issue_number)) };
    },
    update: async params => {
      if (hooks.update) hooks.update(params);
      writes.updates.push(params);
      Object.assign(issues.get(params.issue_number), { body: params.body });
      return { data: structuredClone(issues.get(params.issue_number)) };
    },
    createComment: async params => {
      if (hooks.comment) hooks.comment(params);
      writes.comments.push(params);
      if (!comments.has(params.issue_number)) comments.set(params.issue_number, []);
      comments.get(params.issue_number).push(botComment(params.body));
      return { data: { id: writes.comments.length } };
    },
    listForRepo: () => {},
    listComments: () => {},
  };
  const github = {
    rest: { issues: endpoints },
    paginate: async (endpoint, params) => {
      assert.equal(params.per_page, 100);
      if (endpoint === endpoints.listForRepo) return [...issues.values()];
      assert.equal(endpoint, endpoints.listComments);
      if (hooks.comments) hooks.comments(params);
      return structuredClone(comments.get(params.issue_number) || []);
    },
  };
  const context = {
    repo: { owner: 'acl-org', repo: 'acl-anthology' },
    eventName: 'issues', payload: { action: 'opened', sender: { type: 'User' } },
  };
  return { github, context, core, number: 42, policy, issue, issues, comments, writes, logs, hooks };
}

test('editable policy and issue form have a consistent contract', () => {
  const text = fs.readFileSync(path.join(ROOT, '.github/ISSUE_TEMPLATE/04-ingestion-request.yml'), 'utf8');
  for (const label of Object.values(fields)) assert(text.includes(`label: ${label}`), label);
  for (const label of Object.values(policy.settings.platforms)) {
    assert(text.includes(`label: ${label}`), label);
  }
  for (const marker of Object.values(policy.settings.checkboxes)) {
    assert(text.toLowerCase().includes(marker.toLowerCase()), marker);
  }
  const ids = [...text.matchAll(/^\s+id: (\S+)/gm)].map(match => match[1]);
  assert.equal(new Set(ids).size, ids.length);
  assert(text.includes('assignees:\n  - anthology-assist'));
  assert(text.includes('labels: ["ingestion"]'));
});

test('guide preserves reference anchors and fronts the existing table', () => {
  const guide = fs.readFileSync(path.join(ROOT, 'hugo/content/info/contrib.md'), 'utf8');
  const anchors = new Set([...guide.matchAll(/^#{2,6} (.+)$/gm)]
    .map(match => match[1].toLowerCase().replace(/[^\w\s-]/g, '').replace(/\s+/g, '-')));
  for (const anchor of [
    'overview-of-the-submission-process', 'about-venues', 'register-your-meeting',
    'new-venues', 'submit-your-data', 'copyright', 'isbn-numbers', 'errata-and-corrections',
  ]) assert(anchors.has(anchor), anchor);
  assert(guide.indexOf('<table') < guide.indexOf('## About Venues'));
  assert(guide.indexOf('Open an ingestion request') < guide.indexOf('<table'));
  for (const file of fs.readdirSync(path.join(CONTENT, 'checklists'))) {
    const text = fs.readFileSync(path.join(CONTENT, 'checklists', file), 'utf8');
    for (const link of text.matchAll(/https:\/\/aclanthology\.org\/info\/contrib\/#([a-z-]+)/g)) {
      assert(anchors.has(link[1]), `${file}: ${link[1]}`);
    }
  }
});

for (const platform of ['openreview', 'softconf', 'easychair']) {
  for (const affiliation of ['Yes', 'No']) {
    for (const newVenue of [false, true]) {
      test(`routes ${platform}, ACL=${affiliation}, new venue=${newVenue}`, () => {
        const { model, body } = generated({ platforms: [platform], affiliation, newVenue });
        const ids = model.tasks.map(task => task.id);
        assert.equal(new Set(ids).size, ids.length);
        assert.equal(ids.includes('request-isbns'), affiliation === 'Yes');
        assert.equal(ids.includes('approve-venue'), newVenue);
        assert.equal(ids.includes('softconf-export'), platform === 'softconf');
        assert.equal(ids.includes('aclpub2-check'), platform === 'openreview');
        assert.equal(ids.includes('easychair-orcids'), platform === 'easychair');
        if (platform === 'softconf') assert.match(body, /Do not convert it to aclpub2/);
        if (platform === 'easychair') assert.match(body, /no aclpub2 conversion is required/);
        if (platform === 'openreview') {
          assert.match(body, /aclpub2_format_check\.py --import-dir \/path\/to\/volume/);
        }
      });
    }
  }
}

test('mixed platforms share common tasks without duplicates', () => {
  const { model } = generated({ platforms: ['openreview', 'softconf', 'easychair'] });
  const ids = model.tasks.map(task => task.id);
  assert.equal(ids.filter(id => id === 'collect-orcids').length, 1);
  for (const id of ['aclpub2-check', 'softconf-export', 'easychair-export']) assert(ids.includes(id));
});

test('undecided or other platforms and ACL affiliation get clarification tasks', () => {
  for (const platforms of [[], ['other'], ['openreview', 'other']]) {
    const { model } = generated({ platforms, affiliation: 'Not sure yet' });
    assert(model.tasks.some(task => task.id === 'clarify-platform'));
    assert(model.tasks.some(task => task.id === 'clarify-affiliation'));
    assert(!model.tasks.some(task => task.id === 'request-isbns'));
  }
});

test('historical material keeps its exemption, but overdue current proceedings do not', () => {
  const historical = generated({ publication: '2020-01-15', historical: true });
  assert.equal(historical.model.dates.delivery, null);
  assert.equal(historical.model.dates.freeze, null);
  assert(!historical.model.tasks.some(task => task.id === 'collect-orcids'));
  assert(!historical.model.tasks.some(task => task.id === 'request-isbns'));
  assert(historical.model.tasks.some(task => task.id === 'historical-publication'));
  assert.deepEqual(dueReminders(historical.model, policy.settings, '', '2027-01-02'), []);
  const current = generated({ publication: '2026-01-15' });
  assert.equal(current.model.dates.delivery, '2026-01-01');
  assert(dueReminders(current.model, policy.settings, '', '2026-01-02').length > 0);
});

test('calendar dates are strict and subtraction crosses year and leap-day boundaries', () => {
  assert(validDate('2028-02-29'));
  for (const date of ['2027-02-29', '2027-02-30', '2027-13-01', '27-01-01', '0000-01-01', 'TBD']) {
    assert(!validDate(date), date);
  }
  assert.equal(addDays('2027-01-05', -14), '2026-12-22');
  assert.equal(addDays('2028-03-10', -14), '2028-02-25');
  assert.equal(generated().model.dates.delivery, '2027-01-01');
});

test('blank and invalid dates never fabricate deadlines', () => {
  for (const publication of ['', '_No response_', '2027-02-30']) {
    const { model, body } = generated({ publication });
    assert.equal(model.dates.delivery, null);
    assert.equal(model.dates.freeze, null);
    assert.match(body, /Not yet agreed/);
    assert.deepEqual(dueReminders(model, policy.settings, '', '2027-01-02'), []);
    assert.equal(model.errors.length, publication === '2027-02-30' ? 1 : 0);
  }
});

test('earlier cutoffs are respected; later or invalid cutoffs are flagged without a fallback', () => {
  assert.equal(generated({ cutoff: '2026-12-30' }).model.dates.freeze, '2026-12-30');
  for (const cutoff of ['2027-01-02', '2026-02-30']) {
    const { model } = generated({ cutoff });
    assert.equal(model.dates.delivery, '2027-01-01');
    assert.equal(model.dates.freeze, null);
    assert.equal(model.errors.length, 1);
  }
});

test('fenced supporting text cannot spoof form headings', () => {
  const body = form() + '\n```markdown\n### Date of Publication\n\n2040-01-01\n```\n';
  assert.equal(renderGuidance(body, policy).model.dates.publication, '2027-01-15');
  assert.equal(parseAnswers(form().replaceAll('\n', '\r\n'), fields).get(fields.venue), 'example');
  assert.throws(() => renderGuidance(form() + '\n### Date of Publication\n2030-01-01', policy),
    IssueStateError);
});

test('initial generation and repeat edits are idempotent and preserve original text', () => {
  const original = form() + '\nNotes before automation:  two spaces.\n';
  const first = renderGuidance(original, policy);
  assert(first.body.startsWith(original));
  assert.equal(renderGuidance(first.body, policy).body, first.body);
  const withNotes = first.body + '\n\nAdditional organizer notes and delivery link.\n';
  assert.equal(renderGuidance(withNotes, policy).body, withNotes);
  assert.equal(readManaged(withNotes).suffix, '\n\nAdditional organizer notes and delivery link.\n');
});

test('task toggles, including uppercase X, preserve valid managed content', () => {
  let body = toggle(generated().body, 'deliver-snapshot');
  assert(readManaged(body).tasks.get('deliver-snapshot').checked);
  assert.equal(renderGuidance(body, policy).body, body);
  body = body.replace('- [x]', '- [X]');
  assert(readManaged(body).tasks.get('deliver-snapshot').checked);
  assert(renderGuidance(body, policy).model.tasks.find(task => task.id === 'deliver-snapshot').checked);
});

test('wording-only changes retain completed tasks without workflow edits', t => {
  const body = toggle(generated().body, 'deliver-snapshot');
  const root = policyFixture(t, root => editFile(root, 'checklists/common.md',
    text => text.replace('Post an accessible link', 'Share an accessible download link')));
  const changed = renderGuidance(body, loadPolicy(root));
  assert.match(changed.body, /Share an accessible download link/);
  assert(changed.model.tasks.find(task => task.id === 'deliver-snapshot').checked);
  assert(!changed.model.tasks.some(task => task.reconfirm));
  assert.equal(renderGuidance(changed.body, loadPolicy(root)).body, changed.body);
});

test('changed dates reopen affected tasks, preserve unrelated completion, and remain idempotent', () => {
  let body = toggle(generated().body, 'deliver-snapshot');
  body = toggle(body, 'request-isbns');
  body = body.replace('2027-01-15', '2027-02-15');
  const changed = renderGuidance(body, policy);
  const delivery = changed.model.tasks.find(task => task.id === 'deliver-snapshot');
  assert(!delivery.checked);
  assert(delivery.reconfirm);
  assert(changed.model.tasks.find(task => task.id === 'request-isbns').checked);
  assert.match(changed.body, /affected tasks have been reopened/);
  assert.equal(renderGuidance(changed.body, policy).body, changed.body);
  const confirmed = renderGuidance(toggle(changed.body, 'deliver-snapshot'), policy);
  assert(confirmed.model.tasks.find(task => task.id === 'deliver-snapshot').checked);
  assert(!confirmed.model.tasks.find(task => task.id === 'deliver-snapshot').reconfirm);
  assert.equal(renderGuidance(confirmed.body, policy).body, confirmed.body);
});

test('platform changes replace platform tasks and request delivery reconfirmation', () => {
  let body = toggle(generated().body, 'deliver-snapshot');
  body = body.replace('- [x] OpenReview', '- [ ] OpenReview')
    .replace('- [ ] Softconf/START', '- [x] Softconf/START');
  const { model } = renderGuidance(body, policy);
  assert(!model.tasks.some(task => task.id === 'aclpub2-check'));
  assert(model.tasks.some(task => task.id === 'softconf-export'));
  assert(model.tasks.find(task => task.id === 'deliver-snapshot').reconfirm);
});

test('unexpected edits and malformed blocks are rejected rather than overwritten', () => {
  for (const body of [
    form() + START,
    form() + END + START,
    generated().body + START,
    generated().body.replace('### Timeline', '### Organizer notes'),
    generated().body.replace('### Timeline', 'I added a note inside the generated block.\n### Timeline'),
  ]) assert.throws(() => renderGuidance(body, policy), IssueStateError);
  assert.throws(() => renderGuidance(generated().body.replace('### Venue Identifier', '### Removed'), policy),
    IssueStateError);
});

test('unrelated issues are not recognized and oversized generated issues fail explicitly', () => {
  assert.equal(renderGuidance('Please ingest this.', policy).recognized, false);
  assert.throws(() => renderGuidance(form() + 'a'.repeat(65536), policy), /body limit/);
});

for (const [name, edit, message] of [
  ['delivery offset', root => editSettings(root, value => { value.delivery_days_before_publication = 0; }), /delivery offset/],
  ['lead days', root => editSettings(root, value => { value.reminder_days_before_deadline = [7, 7]; }), /lead days/],
  ['overdue interval', root => editSettings(root, value => { value.overdue_reminder_interval_days = 0; }), /overdue interval/],
  ['unknown setting', root => editSettings(root, value => { value.typo = true; }), /unknown setting/],
  ['unknown condition', root => editSettings(root, value => { value.checklists[0].when = ['typo']; }), /unknown checklist condition/],
  ['missing template', root => editSettings(root, value => { value.templates.reminder = 'missing.md'; }), /missing\.md/],
  ['path escape', root => editSettings(root, value => { value.templates.reminder = '../other.md'; }), /inside the content directory/],
  ['unknown placeholder', root => editFile(root, 'timeline.md', text => text + '{{typo}}'), /unknown placeholder/],
  ['missing placeholder', root => editFile(root, 'timeline.md', text => text.replace('{{notes}}', '')), /missing \{\{notes\}\}/],
  ['duplicate ID', root => editFile(root, 'checklists/acl.md', text => text.replace('task:request-isbns', 'task:volume-roster')), /duplicate task ID/],
  ['unknown milestone', root => editFile(root, 'checklists/acl.md', text => text.replace('task:request-isbns', 'task:request-isbns due:typo')), /unknown milestone/],
  ['missing ID', root => editFile(root, 'checklists/acl.md', text => text.replace('<!-- task:request-isbns -->', '')), /task metadata/],
  ['invalid JSON', root => fs.writeFileSync(path.join(root, 'settings.json'), '{'), /settings\.json/],
]) {
  test(`invalid policy: ${name}`, t => {
    const root = policyFixture(t, edit);
    assert.throws(() => loadPolicy(root), message);
  });
}

test('configuration changes drive both rendered dates and reminder cadence', t => {
  const root = policyFixture(t, root => editSettings(root, value => {
    value.delivery_days_before_publication = 21;
    value.reminder_days_before_deadline = [3];
    value.overdue_reminder_interval_days = 2;
  }));
  const changed = loadPolicy(root);
  const { model, body } = renderGuidance(form(), changed);
  assert.equal(model.dates.delivery, '2026-12-25');
  assert.match(body, /2026-12-25/);
  assert(body.includes('**3 day(s) before**'));
  assert(body.includes('**2 day(s)**'));
  assert.equal(dueReminders(model, changed.settings, '', '2026-12-21').length, 0);
  assert(dueReminders(model, changed.settings, '', '2026-12-22').length > 0);
  const markers = '<!-- anthology-ingestion-reminder:delivery:2026-12-25:overdue-2026-12-26 -->\n'
    + '<!-- anthology-ingestion-reminder:freeze:2026-12-25:overdue-2026-12-26 -->';
  assert.equal(dueReminders(model, changed.settings, markers, '2026-12-27').length, 0);
  assert(dueReminders(model, changed.settings, markers, '2026-12-28').length > 0);
});

test('exact reminder stages: one seven-day warning, no deadline-day ping, then daily overdue', () => {
  const { model } = generated();
  assert.equal(dueReminders(model, policy.settings, '', '2026-12-24').length, 0);
  const early = dueReminders(model, policy.settings, '', '2026-12-25');
  assert.equal(early.length, 2);
  const markers = early.map(reminder => reminder.marker).join('\n');
  for (const day of ['2026-12-26', '2026-12-31', '2027-01-01']) {
    assert.equal(dueReminders(model, policy.settings, markers, day).length, 0, day);
  }
  const overdue = dueReminders(model, policy.settings, markers, '2027-01-02');
  assert.equal(overdue.length, 2);
  assert(overdue.every(reminder => reminder.remaining === -1));
  const sent = renderReminder(apiHarness().issue, overdue, policy, '2027-01-02');
  assert.equal(dueReminders(model, policy.settings, sent, '2027-01-02').length, 0);
  assert.equal(dueReminders(model, policy.settings, sent, '2027-01-03').length, 2);
});

test('missed runs catch up once without replaying a backlog', () => {
  const { model } = generated();
  assert.equal(dueReminders(model, policy.settings, '', '2026-12-28').length, 2);
  const overdue = dueReminders(model, policy.settings, '', '2027-02-01');
  assert.equal(overdue.length, 2);
  assert(overdue.every(reminder => reminder.marker.endsWith('overdue-2027-02-01 -->')));
});

test('completed dated tasks stop pings; undated ISBN and registration tasks do not get invented dates', () => {
  const model = renderGuidance(completeDated(generated().body), policy).model;
  assert(model.tasks.some(task => !task.checked));
  assert.deepEqual(dueReminders(model, policy.settings, '', '2027-01-02'), []);
});

test('earlier freeze has its own date and comments group milestones with creator mention', () => {
  const { model } = generated({ cutoff: '2026-12-28' });
  const due = dueReminders(model, policy.settings, '', '2026-12-21');
  assert.deepEqual(due.map(reminder => reminder.milestone), ['freeze']);
  const both = dueReminders(model, policy.settings, '', '2027-01-02');
  const text = renderReminder(apiHarness().issue, both, policy, '2027-01-02');
  assert.match(text, /@organizer/);
  assert.match(text, /2026-12-28 \(5 day\(s\) overdue\)/);
  assert.match(text, /2027-01-01 \(1 day\(s\) overdue\)/);
  assert.match(text, /issues\/42#your-submission-checklist/);
  assert(!text.includes('- [ ]'), 'Reminder comments should link to editable tasks, not duplicate boxes');
});

test('new deadlines are not suppressed by markers for an older date', () => {
  const { model } = generated({ publication: '2027-02-15' });
  const old = '<!-- anthology-ingestion-reminder:delivery:2027-01-01:advance-7 -->';
  assert(dueReminders(model, policy.settings, old, '2027-01-25').length > 0);
});

test('issue application appends the plan without changing assignees', async () => {
  const api = apiHarness(form());
  await applyGuidance(api);
  assert.equal(api.writes.updates.length, 1);
  assert(api.issue.body.includes(START));
  assert.deepEqual(api.issue.assignees, [{ login: 'anthology-assist' }]);
  assert.deepEqual(Object.keys(api.writes.updates[0]).sort(), ['body', 'issue_number', 'owner', 'repo']);
  await applyGuidance(api);
  assert.equal(api.writes.updates.length, 1);
});

test('legacy requests require explicit opt-in; label intake and manual dry runs are supported', async () => {
  const api = apiHarness(form());
  api.context.payload.action = 'edited';
  await applyGuidance(api);
  assert.equal(api.writes.updates.length, 0);
  api.context.eventName = 'workflow_dispatch';
  await applyGuidance({ ...api, dryRun: true });
  assert.equal(api.writes.updates.length, 0);
  assert(api.logs.info.some(line => line.includes('[dry run]')));
  api.context.eventName = 'issues';
  api.context.payload.action = 'labeled';
  api.context.payload.label = { name: 'ingestion' };
  await applyGuidance(api);
  assert.equal(api.writes.updates.length, 1);
});

test('bot events, closed issues, unlabeled requests, and pull requests are not modified', async () => {
  for (const change of [
    api => { api.context.payload.sender.type = 'Bot'; },
    api => { api.issue.state = 'closed'; },
    api => { api.issue.labels = []; },
    api => { api.issue.pull_request = {}; },
  ]) {
    const api = apiHarness(form());
    change(api);
    await applyGuidance(api);
    assert.equal(api.writes.updates.length, 0);
  }
});

test('invalid date answers are visible in the issue and workflow warnings', async () => {
  const api = apiHarness(form({ publication: 'not a date' }));
  await applyGuidance(api);
  assert.match(api.issue.body, /enter a real date/);
  assert.equal(api.logs.warning.length, 1);
});

test('concurrent organizer edits are retried, never overwritten', async () => {
  const api = apiHarness(form());
  let reads = 0;
  api.hooks.get = () => {
    if (++reads % 2 === 0) api.issue.body += `\nOrganizer edit ${reads}\n`;
  };
  await assert.rejects(applyGuidance(api), /changed during generation/);
  assert.equal(reads, 6);
  assert.equal(api.writes.updates.length, 0);
  assert(api.issue.body.includes('Organizer edit 6'));
});

test('API failures propagate and invalid issue numbers fail before writes', async () => {
  const api = apiHarness(form());
  api.hooks.update = () => { throw new Error('GitHub unavailable'); };
  await assert.rejects(applyGuidance(api), /GitHub unavailable/);
  await assert.rejects(applyGuidance({ ...api, number: 'not a number' }), /Invalid issue number/);
});

test('scheduled reminders mention the creator once per day and stop on completion/closure', async () => {
  const api = apiHarness();
  await sendReminders({ ...api, dryRun: false, now: new Date('2027-01-02T09:00:00Z') });
  assert.equal(api.writes.comments.length, 1);
  assert.match(api.writes.comments[0].body, /@organizer/);
  await sendReminders({ ...api, dryRun: false, now: new Date('2027-01-02T12:00:00Z') });
  assert.equal(api.writes.comments.length, 1);
  await sendReminders({ ...api, dryRun: false, now: new Date('2027-01-03T09:00:00Z') });
  assert.equal(api.writes.comments.length, 2);
  api.issue.body = completeDated(api.issue.body);
  await sendReminders({ ...api, dryRun: false, now: new Date('2027-01-04T09:00:00Z') });
  assert.equal(api.writes.comments.length, 2);
  api.issue.state = 'closed';
  await sendReminders({ ...api, dryRun: false, now: new Date('2027-01-05T09:00:00Z') });
  assert.equal(api.writes.comments.length, 2);
});

test('human-authored marker lookalikes cannot suppress reminders', async () => {
  const api = apiHarness();
  api.comments.set(42, [{
    body: '<!-- anthology-ingestion-reminder-day:2027-01-02 -->',
    user: { login: 'organizer' },
  }]);
  await sendReminders({ ...api, dryRun: false, now: new Date('2027-01-02T09:00:00Z') });
  assert.equal(api.writes.comments.length, 1);
});

test('reminder dry runs have no writes, including when templates need refreshing', async t => {
  const api = apiHarness();
  const root = policyFixture(t, root => editFile(root, 'timeline.md',
    text => text.replace('## Your submission checklist', '## Your submission checklist\n\nUpdated instructions.')));
  await sendReminders({
    ...api, policy: loadPolicy(root), dryRun: true, now: new Date('2027-01-02T09:00:00Z'),
  });
  assert.equal(api.writes.updates.length, 0);
  assert.equal(api.writes.comments.length, 0);
  assert(api.logs.info.some(line => line.includes('Would update')));
  assert(api.logs.info.some(line => line.includes('Would remind')));
});

test('scheduled refreshes apply editable content while retaining checkbox state', async t => {
  const api = apiHarness(toggle(generated().body, 'deliver-snapshot'));
  const root = policyFixture(t, root => editFile(root, 'timeline.md',
    text => text.replace('## Your submission checklist', '## Your submission checklist\n\nUpdated instructions.')));
  await sendReminders({
    ...api, policy: loadPolicy(root), dryRun: false, now: new Date('2027-01-01T09:00:00Z'),
  });
  assert.equal(api.writes.updates.length, 1);
  assert.match(api.issue.body, /Updated instructions/);
  assert(readManaged(api.issue.body).tasks.get('deliver-snapshot').checked);
  assert.equal(api.writes.comments.length, 0);
});

test('a task checked off during the reminder scan prevents a stale ping', async () => {
  const api = apiHarness();
  api.hooks.comments = () => { api.issue.body = completeDated(api.issue.body); };
  await sendReminders({ ...api, dryRun: false, now: new Date('2027-01-02T09:00:00Z') });
  assert.equal(api.writes.comments.length, 0);
  assert(api.logs.info.some(line => line.includes('changed during this check')));
});

test('schedules never opt legacy requests in and still process healthy issues after a damaged block', async () => {
  const api = apiHarness(form() + START);
  api.issues.set(43, { ...structuredClone(api.issue), number: 43, body: form() });
  api.issues.set(44, {
    ...structuredClone(api.issue), number: 44, body: generated().body,
    html_url: 'https://github.com/acl-org/acl-anthology/issues/44',
  });
  await assert.rejects(sendReminders({
    ...api, number: '', dryRun: false, now: new Date('2027-01-02T09:00:00Z'),
  }), AggregateError);
  assert.equal(api.logs.error.length, 1);
  assert.equal(api.writes.comments.length, 1);
  assert.equal(api.writes.comments[0].issue_number, 44);
  assert.equal(api.issues.get(43).body, form());
});

test('the reminder clock uses UTC calendar dates rather than local time', async () => {
  const api = apiHarness();
  await sendReminders({ ...api, dryRun: false, now: new Date('2027-01-02T00:30:00+09:00') });
  assert.equal(api.writes.comments.length, 0);
  await sendReminders({ ...api, dryRun: false, now: new Date('2027-01-02T00:30:00Z') });
  assert.equal(api.writes.comments.length, 1);
});
