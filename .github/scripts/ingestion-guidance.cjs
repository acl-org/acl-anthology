const fs = require('node:fs');
const path = require('node:path');
const { createHash } = require('node:crypto');

const START = '<!-- anthology-ingestion:start -->';
const END = '<!-- anthology-ingestion:end -->';
const DAY_MS = 24 * 60 * 60 * 1000;
const CONDITIONS = new Set([
  'current', 'historical', 'acl', 'new-venue', 'softconf', 'openreview',
  'easychair', 'unknown-platform', 'unknown-affiliation',
]);
const DATE_VARIABLES = ['publication_date', 'delivery_date', 'freeze_date'];
const TASK_PATTERN = /^- \[([ xX])\] (.+) <!-- ingestion-task:([a-z][a-z0-9-]*):([a-f0-9]{16})(:reconfirm)? -->$/gm;

class ConfigurationError extends Error {}
class IssueStateError extends Error {}

function check(condition, message) {
  if (!condition) throw new ConfigurationError(message);
}

function objectKeys(value, keys, file) {
  check(value !== null && typeof value === 'object' && !Array.isArray(value),
    `${file}: expected an object`);
  check(Object.keys(value).every(key => keys.includes(key)),
    `${file}: unknown setting`);
  check(keys.every(key => Object.hasOwn(value, key)), `${file}: missing setting`);
}

function strings(value, keys, file) {
  objectKeys(value, keys, file);
  check(Object.values(value).every(item => typeof item === 'string' && item.trim()),
    `${file}: values must be nonempty strings`);
}

function validatePlaceholders(text, allowed, file) {
  const rest = text.replace(/\{\{([a-z_]+)\}\}/g, (_, name) => {
    check(allowed.includes(name), `${file}: unknown placeholder {{${name}}}`);
    return '';
  });
  check(!rest.includes('{{') && !rest.includes('}}'), `${file}: malformed placeholder`);
}

function substitute(text, variables) {
  return text.replace(/\{\{([a-z_]+)\}\}/g, (_, name) => {
    check(Object.hasOwn(variables, name), `Missing template value: ${name}`);
    return variables[name];
  });
}

function compileChecklist(text, file, milestones) {
  validatePlaceholders(text, DATE_VARIABLES, file);
  return text.trimEnd().split('\n').map((line, index) => {
    if (!/^- \[[ xX]\]/.test(line)) return { line };
    const match = line.match(/^- \[ \] (.+?) <!-- (task:[^<>]+) -->$/);
    check(match, `${file}:${index + 1}: tasks need an unchecked box and task metadata`);
    const attributes = {};
    for (const item of match[2].split(/\s+/)) {
      const attribute = item.match(/^(task|due|when|context):([a-z][a-z0-9-]*)$/);
      check(attribute && !Object.hasOwn(attributes, attribute[1]),
        `${file}:${index + 1}: invalid or duplicate task attribute`);
      attributes[attribute[1]] = attribute[2];
    }
    check(attributes.task, `${file}:${index + 1}: missing task ID`);
    check(!attributes.due || Object.hasOwn(milestones, attributes.due),
      `${file}:${index + 1}: unknown milestone ${attributes.due}`);
    check(!attributes.when || CONDITIONS.has(attributes.when),
      `${file}:${index + 1}: unknown condition ${attributes.when}`);
    check(!attributes.context || attributes.context === 'submission',
      `${file}:${index + 1}: unknown task context`);
    return {
      task: {
        id: attributes.task, text: match[1], due: attributes.due,
        when: attributes.when, context: attributes.context,
      },
    };
  });
}

function loadPolicy(root = path.resolve(__dirname, '../ingestion')) {
  const file = path.join(root, 'settings.json');
  let settings;
  try {
    settings = JSON.parse(fs.readFileSync(file, 'utf8'));
  } catch (error) {
    if (error instanceof SyntaxError) {
      throw new ConfigurationError(`${file}: ${error.message}`);
    }
    throw error;
  }
  objectKeys(settings, [
    'fields', 'checkboxes', 'platforms', 'delivery_days_before_publication',
    'reminder_days_before_deadline', 'overdue_reminder_interval_days',
    'milestones', 'labels', 'templates', 'checklists',
  ], file);
  strings(settings.fields,
    ['general', 'venue', 'title', 'affiliation', 'publication', 'cutoff', 'platforms'], file);
  check(new Set(Object.values(settings.fields)).size === Object.keys(settings.fields).length,
    `${file}: question labels must be unique`);
  strings(settings.checkboxes, ['new_venue', 'historical'], file);
  strings(settings.platforms, ['openreview', 'softconf', 'easychair', 'other'], file);
  strings(settings.milestones, ['publication', 'delivery', 'freeze'], file);
  strings(settings.labels, ['pending', 'historical', 'reconfirmation'], file);
  strings(settings.templates, ['timeline', 'reminder'], file);
  check(Number.isSafeInteger(settings.delivery_days_before_publication)
    && settings.delivery_days_before_publication > 0, `${file}: invalid delivery offset`);
  check(Array.isArray(settings.reminder_days_before_deadline)
    && settings.reminder_days_before_deadline.length > 0
    && settings.reminder_days_before_deadline.every(day => Number.isSafeInteger(day) && day > 0)
    && new Set(settings.reminder_days_before_deadline).size
      === settings.reminder_days_before_deadline.length, `${file}: invalid reminder lead days`);
  check(Number.isSafeInteger(settings.overdue_reminder_interval_days)
    && settings.overdue_reminder_interval_days > 0, `${file}: invalid overdue interval`);
  check(Array.isArray(settings.checklists) && settings.checklists.length > 0,
    `${file}: no checklists configured`);

  function readMarkdown(name) {
    check(typeof name === 'string' && name.endsWith('.md')
      && !path.isAbsolute(name) && !name.split(/[\\/]/).includes('..'),
    `${file}: Markdown paths must stay inside the content directory`);
    return fs.readFileSync(path.join(root, name), 'utf8').replace(/\r\n/g, '\n');
  }

  const templates = {
    timeline: readMarkdown(settings.templates.timeline),
    reminder: readMarkdown(settings.templates.reminder),
  };
  const timelineVariables = [
    ...DATE_VARIABLES, 'notes', 'checklists', 'reminder_lead_days', 'overdue_interval_days',
  ];
  validatePlaceholders(templates.timeline, timelineVariables,
    settings.templates.timeline);
  validatePlaceholders(templates.reminder, ['issue_creator', 'issue_url', 'reminders'],
    settings.templates.reminder);
  for (const name of timelineVariables) {
    check(templates.timeline.includes(`{{${name}}}`),
      `${settings.templates.timeline}: missing {{${name}}}`);
  }
  for (const name of ['issue_creator', 'issue_url', 'reminders']) {
    check(templates.reminder.includes(`{{${name}}}`),
      `${settings.templates.reminder}: missing {{${name}}}`);
  }
  const ids = new Set();
  const checklists = settings.checklists.map(entry => {
    objectKeys(entry, ['file', 'when'], file);
    check(Array.isArray(entry.when) && entry.when.every(condition => CONDITIONS.has(condition)),
      `${file}: unknown checklist condition`);
    const parts = compileChecklist(readMarkdown(entry.file), entry.file, settings.milestones);
    check(parts.some(part => part.task), `${entry.file}: checklist has no tasks`);
    for (const { task } of parts) {
      if (!task) continue;
      check(!ids.has(task.id), `${entry.file}: duplicate task ID ${task.id}`);
      ids.add(task.id);
    }
    return { ...entry, parts };
  });
  return { settings, templates, checklists };
}

function parseAnswers(body, fields) {
  const known = new Set(Object.values(fields));
  const answers = new Map();
  let heading = null;
  let fence = null;
  for (const line of body.replace(/\r\n/g, '\n').split('\n')) {
    const fenceMatch = line.match(/^ {0,3}(`{3,}|~{3,})/);
    if (fenceMatch) {
      const marker = fenceMatch[1];
      if (!fence) fence = marker;
      else if (marker[0] === fence[0] && marker.length >= fence.length) fence = null;
    }
    const match = !fence && !fenceMatch && line.match(/^### (.+?)\s*$/);
    if (match) {
      heading = known.has(match[1]) ? match[1] : null;
      if (heading) {
        if (answers.has(heading)) throw new IssueStateError(`Duplicate form question: ${heading}`);
        answers.set(heading, []);
      }
    } else if (heading) {
      answers.get(heading).push(line);
    }
  }
  return new Map([...answers].map(([key, lines]) => {
    const value = lines.join('\n').trim();
    return [key, /^(?:_No response_|No response)?$/.test(value) ? '' : value];
  }));
}

function checkedOptions(value) {
  return [...value.matchAll(/^\s*[-*] \[[xX]\] (.+)$/gm)]
    .map(match => match[1].replace(/[*`]/g, '').toLowerCase());
}

function validDate(value) {
  if (!/^\d{4}-\d{2}-\d{2}$/.test(value) || value.startsWith('0000')) return false;
  const date = new Date(`${value}T00:00:00.000Z`);
  return Number.isFinite(date.getTime()) && date.toISOString().slice(0, 10) === value;
}

function addDays(value, days) {
  const date = new Date(`${value}T00:00:00.000Z`);
  date.setUTCDate(date.getUTCDate() + days);
  const result = date.toISOString().slice(0, 10);
  if (!validDate(result)) throw new IssueStateError('Calculated deadline is outside YYYY-MM-DD range');
  return result;
}

function daysBetween(first, second) {
  return (Date.parse(`${second}T00:00:00.000Z`) - Date.parse(`${first}T00:00:00.000Z`)) / DAY_MS;
}

function todayUTC(now) {
  if (!(now instanceof Date) || !Number.isFinite(now.getTime())) {
    throw new TypeError('A valid clock date is required');
  }
  return now.toISOString().slice(0, 10);
}

function hash(text) {
  return createHash('sha256').update(text).digest('hex');
}

function contentHash(text) {
  // Checkbox toggles are the only edits allowed inside the managed section.
  return hash(text.replace(/\r\n/g, '\n').replace(TASK_PATTERN,
    (_, checked, text, id, signature, reconfirm) =>
      `- [ ] ${text} <!-- ingestion-task:${id}:${signature}${reconfirm || ''} -->`));
}

function readManaged(body) {
  const starts = body.split(START).length - 1;
  const ends = body.split(END).length - 1;
  if (!starts && !ends) return { prefix: body, suffix: '', tasks: new Map(), exists: false };
  if (starts !== 1 || ends !== 1 || body.indexOf(END) < body.indexOf(START)) {
    throw new IssueStateError('Malformed ingestion section markers; original issue left untouched');
  }
  const start = body.indexOf(START);
  const end = body.indexOf(END);
  const inner = body.slice(start + START.length, end).replace(/\r\n/g, '\n');
  const match = inner.match(/^\n<!-- anthology-ingestion:content ([a-f0-9]{64}) -->\n([\s\S]*)$/);
  if (!match || contentHash(match[2]) !== match[1]) {
    throw new IssueStateError(
      'Generated checklist text was edited outside its checkboxes. Move notes outside the '
      + 'managed section and restore its text before rerunning; original issue left untouched.',
    );
  }
  const tasks = new Map();
  for (const task of match[2].matchAll(TASK_PATTERN)) {
    if (tasks.has(task[3])) throw new IssueStateError(`Duplicate generated task: ${task[3]}`);
    tasks.set(task[3], {
      checked: task[1].toLowerCase() === 'x', signature: task[4], reconfirm: Boolean(task[5]),
    });
  }
  return {
    prefix: body.slice(0, start), suffix: body.slice(end + END.length), tasks, exists: true,
  };
}

function deriveSubmission(answers, settings) {
  const answer = key => answers.get(settings.fields[key]) || '';
  const general = checkedOptions(answer('general'));
  const historical = general.some(text => text.includes(settings.checkboxes.historical.toLowerCase()));
  const newVenue = general.some(text => text.includes(settings.checkboxes.new_venue.toLowerCase()));
  const selections = checkedOptions(answer('platforms'));
  const platforms = Object.entries(settings.platforms)
    .filter(([, label]) => selections.some(text => text.includes(label.toLowerCase())))
    .map(([key]) => key).sort();
  const affiliation = answer('affiliation');
  const errors = [];
  function dateAnswer(key) {
    const value = answer(key);
    if (!value) return null;
    if (validDate(value)) return value;
    errors.push(`**${settings.fields[key]}:** enter a real date in YYYY-MM-DD format.`);
    return null;
  }
  const publication = dateAnswer('publication');
  const cutoff = dateAnswer('cutoff');
  const delivery = !historical && publication
    ? addDays(publication, -settings.delivery_days_before_publication) : null;
  let freeze = null;
  if (delivery) {
    if (cutoff && cutoff > delivery) {
      errors.push(`**${settings.fields.cutoff}:** must be no later than delivery (${delivery}).`);
    } else if (cutoff || !answer('cutoff')) {
      freeze = cutoff || delivery;
    }
  }
  const facts = {
    current: !historical, historical, acl: affiliation === 'Yes', 'new-venue': newVenue,
    openreview: platforms.includes('openreview'), softconf: platforms.includes('softconf'),
    easychair: platforms.includes('easychair'),
    'unknown-platform': platforms.length === 0 || platforms.includes('other')
      || selections.some(text => !Object.values(settings.platforms)
        .some(label => text.includes(label.toLowerCase()))),
    'unknown-affiliation': !historical && !['Yes', 'No'].includes(affiliation),
  };
  return {
    facts, errors, dates: { publication, delivery, freeze },
    submission: {
      venue: answer('venue'), title: answer('title'), platforms,
      newVenue, historical,
    },
  };
}

function renderGuidance(body, policy) {
  const managed = readManaged(body);
  const { settings } = policy;
  const answers = parseAnswers(managed.prefix, settings.fields);
  const recognized = ['general', 'venue', 'title', 'publication', 'platforms']
    .every(key => answers.has(settings.fields[key]));
  if (!recognized) {
    if (managed.exists) throw new IssueStateError('Original ingestion-form questions are missing');
    return { recognized: false, body, changed: false };
  }
  const model = deriveSubmission(answers, settings);
  const variables = {
    publication_date: model.dates.publication || settings.labels.pending,
    delivery_date: model.facts.historical ? settings.labels.historical
      : model.dates.delivery || settings.labels.pending,
    freeze_date: model.facts.historical ? settings.labels.historical
      : model.dates.freeze || settings.labels.pending,
  };
  const rawDates = {
    publication_date: model.dates.publication,
    delivery_date: model.dates.delivery,
    freeze_date: model.dates.freeze,
  };
  const tasks = [];
  const sections = [];
  for (const checklist of policy.checklists) {
    if (!checklist.when.every(condition => model.facts[condition])) continue;
    const lines = [];
    let count = 0;
    for (const part of checklist.parts) {
      if (!part.task) {
        lines.push(substitute(part.line, variables));
        continue;
      }
      const task = part.task;
      if (task.when && !model.facts[task.when]) continue;
      const dates = Object.fromEntries(
        [...task.text.matchAll(/\{\{([a-z_]+)\}\}/g)].map(match => [match[1], rawDates[match[1]]]),
      );
      const deadline = task.due ? model.dates[task.due] : null;
      const signature = hash(JSON.stringify({
        id: task.id, due: task.due, deadline, dates, when: task.when,
        conditions: checklist.when,
        submission: task.context ? model.submission : null,
      })).slice(0, 16);
      const old = managed.tasks.get(task.id);
      const checked = Boolean(old && old.checked && old.signature === signature);
      const reconfirm = Boolean(old && !checked
        && (old.reconfirm || (old.checked && old.signature !== signature)));
      const text = substitute(task.text, variables);
      lines.push(`- [${checked ? 'x' : ' '}] ${text} <!-- ingestion-task:${task.id}:${signature}${reconfirm ? ':reconfirm' : ''} -->`);
      tasks.push({ id: task.id, text, milestone: task.due, deadline, checked, reconfirm });
      count++;
    }
    if (count) sections.push(lines.join('\n').trim());
  }
  const notes = model.errors.map(error => `- ${error}`);
  if (tasks.some(task => task.reconfirm)) notes.push(`- ${settings.labels.reconfirmation}`);
  const content = substitute(policy.templates.timeline, {
    ...variables, notes: notes.join('\n'), checklists: sections.join('\n\n'),
    reminder_lead_days: [...settings.reminder_days_before_deadline].sort((a, b) => b - a).join(', '),
    overdue_interval_days: String(settings.overdue_reminder_interval_days),
  }).trimEnd() + '\n';
  const section = `${START}\n<!-- anthology-ingestion:content ${contentHash(content)} -->\n${content}${END}`;
  const separator = managed.exists || !body ? ''
    : body.endsWith('\n\n') ? '' : body.endsWith('\n') ? '\n' : '\n\n';
  const updated = managed.prefix + separator + section + managed.suffix;
  if (updated.length > 65536) throw new IssueStateError('Generated issue exceeds GitHub body limit');
  return {
    recognized: true, changed: updated !== body, body: updated, section,
    model: { ...model, tasks },
  };
}

function hasIngestionLabel(issue) {
  return issue.labels.some(label => (typeof label === 'string' ? label : label.name) === 'ingestion');
}

function issueNumber(value, optional = false) {
  if (optional && (value === '' || value === undefined)) return null;
  const number = Number(value);
  if (!Number.isSafeInteger(number) || number <= 0) throw new TypeError('Invalid issue number');
  return number;
}

async function syncIssue({ github, context, core, policy, number, dryRun, requireManaged }) {
  const params = { ...context.repo, issue_number: number };
  for (let attempt = 0; attempt < 3; attempt++) {
    const { data: issue } = await github.rest.issues.get(params);
    if (issue.pull_request || issue.state !== 'open' || !hasIngestionLabel(issue)) {
      core.info(`Skipping #${number}: not an open ingestion issue.`);
      return null;
    }
    const body = issue.body || '';
    const managed = readManaged(body);
    if (requireManaged && !managed.exists) {
      core.info(`Skipping #${number}: no generated checklist; manual opt-in is available.`);
      return null;
    }
    const guidance = renderGuidance(body, policy);
    if (!guidance.recognized) {
      core.info(`Skipping #${number}: not an ingestion-form request.`);
      return null;
    }
    for (const error of guidance.model.errors) core.warning(`#${number}: ${error}`);
    if (!guidance.changed) return { issue, guidance };
    if (dryRun) {
      core.info(`[dry run] Would update #${number}:\n${guidance.section}`);
      return { issue: { ...issue, body: guidance.body }, guidance };
    }
    const { data: latest } = await github.rest.issues.get(params);
    if (latest.body !== issue.body || latest.state !== issue.state
      || !hasIngestionLabel(latest)) continue;
    await github.rest.issues.update({ ...params, body: guidance.body });
    core.info(`Updated submission checklist on #${number}.`);
    return { issue: { ...latest, body: guidance.body }, guidance };
  }
  throw new IssueStateError(`#${number} changed during generation; rerun instead of overwriting edits`);
}

async function applyGuidance({ github, context, core, number, dryRun = false, policy = loadPolicy() }) {
  if (context.eventName === 'issues' && context.payload.sender?.type === 'Bot') {
    core.info('Ignoring a bot event.');
    return null;
  }
  const action = context.payload.action;
  const initialize = context.eventName === 'workflow_dispatch' || action === 'opened'
    || (action === 'labeled' && context.payload.label?.name === 'ingestion');
  return syncIssue({
    github, context, core, policy, number: issueNumber(number),
    dryRun, requireManaged: !initialize,
  });
}

function reminderMarkers(comments) {
  return comments.filter(comment => comment.user?.login === 'github-actions[bot]')
    .map(comment => comment.body || '').join('\n');
}

function dueReminders(model, settings, markers, today) {
  if (markers.includes(`<!-- anthology-ingestion-reminder-day:${today} -->`)) return [];
  const groups = new Map();
  for (const task of model.tasks) {
    if (task.checked || !task.deadline) continue;
    const key = `${task.milestone}:${task.deadline}`;
    if (!groups.has(key)) groups.set(key, { milestone: task.milestone, date: task.deadline, tasks: [] });
    groups.get(key).tasks.push(task);
  }
  const reminders = [];
  for (const [key, group] of groups) {
    const remaining = daysBetween(today, group.date);
    const prefix = `<!-- anthology-ingestion-reminder:${key}:`;
    let stage;
    if (remaining > 0) {
      const lead = settings.reminder_days_before_deadline.filter(day => remaining <= day)
        .sort((a, b) => a - b)[0];
      if (lead === undefined) continue;
      stage = `advance-${lead}`;
      if (markers.includes(`${prefix}${stage} -->`)) continue;
    } else if (remaining < 0) {
      const previous = [...markers.matchAll(
        /<!-- anthology-ingestion-reminder:([a-z][a-z0-9-]*):(\d{4}-\d{2}-\d{2}):overdue-(\d{4}-\d{2}-\d{2}) -->/g,
      )].filter(match => `${match[1]}:${match[2]}` === key && match[3] <= today)
        .map(match => match[3]).sort().at(-1);
      if (previous && daysBetween(previous, today) < settings.overdue_reminder_interval_days) continue;
      stage = `overdue-${today}`;
    } else continue;
    reminders.push({
      ...group, remaining, marker: `${prefix}${stage} -->`,
    });
  }
  return reminders;
}

function renderReminder(issue, reminders, policy, today) {
  const sections = reminders.map(reminder => {
    const status = reminder.remaining > 0
      ? `${reminder.remaining} day(s) remaining` : `${-reminder.remaining} day(s) overdue`;
    return `### ${policy.settings.milestones[reminder.milestone]}: ${reminder.date} (${status})\n\n`
      + reminder.tasks.map(task => `- ${task.text}`).join('\n');
  });
  const text = substitute(policy.templates.reminder, {
    issue_creator: issue.user.login, issue_url: issue.html_url, reminders: sections.join('\n\n'),
  }).trimEnd();
  const body = `${text}\n\n<!-- anthology-ingestion-reminder-day:${today} -->\n`
    + reminders.map(reminder => reminder.marker).join('\n');
  if (body.length > 65536) throw new IssueStateError('Generated reminder exceeds GitHub body limit');
  return body;
}

async function sendReminders({
  github, context, core, number, dryRun = true, now = new Date(), policy = loadPolicy(),
}) {
  const today = todayUTC(now);
  const target = issueNumber(number, true);
  const issues = target ? [{ number: target }] : await github.paginate(
    github.rest.issues.listForRepo, { ...context.repo, labels: 'ingestion', state: 'open', per_page: 100 },
  );
  const errors = [];
  for (const issue of issues) {
    if (issue.pull_request) continue;
    try {
      const synced = await syncIssue({
        github, context, core, policy, number: issue.number, dryRun, requireManaged: true,
      });
      if (!synced) continue;
      const comments = await github.paginate(github.rest.issues.listComments, {
        ...context.repo, issue_number: issue.number, per_page: 100,
      });
      const { data: latest } = await github.rest.issues.get({
        ...context.repo, issue_number: issue.number,
      });
      if (latest.state !== 'open' || !hasIngestionLabel(latest)
        || (!dryRun && latest.body !== synced.issue.body)) {
        core.info(`Skipping reminder for #${issue.number}: issue changed during this check.`);
        continue;
      }
      const guidance = renderGuidance(latest.body || '', policy);
      const due = dueReminders(guidance.model, policy.settings, reminderMarkers(comments), today);
      if (!due.length) continue;
      const body = renderReminder(latest, due, policy, today);
      if (dryRun) core.info(`[dry run] Would remind #${issue.number}:\n${body}`);
      else {
        await github.rest.issues.createComment({
          ...context.repo, issue_number: issue.number, body,
        });
        core.info(`Posted deadline reminder on #${issue.number}.`);
      }
    } catch (error) {
      if (!(error instanceof IssueStateError)) throw error;
      core.error(`#${issue.number}: ${error.message}`);
      errors.push(error);
    }
  }
  if (errors.length) throw new AggregateError(errors, 'Some ingestion issues need checklist repair');
}

module.exports = {
  START, END, ConfigurationError, IssueStateError, loadPolicy, parseAnswers,
  validDate, addDays, readManaged, renderGuidance, dueReminders, renderReminder,
  applyGuidance, sendReminders,
};
