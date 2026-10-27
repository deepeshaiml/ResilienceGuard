import pptxgen from 'pptxgenjs'
import fs from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../..')
const EVAL_PATH = path.join(ROOT, 'artifacts/evaluation-results.json')
const evaluation = fs.existsSync(EVAL_PATH) ? JSON.parse(fs.readFileSync(EVAL_PATH, 'utf8')) : {}
const checks = Object.fromEntries((evaluation.checks || []).map((row) => [row.name, row]))
const pct = (name) => {
  const row = checks[name]
  return row ? `${row.passed}/${row.total} · ${(row.rate * 100).toFixed(0)}%` : 'not recorded'
}
const restore = evaluation.restore_duration_seconds || {}
const meanMs = Number.isFinite(restore.mean) ? `${(restore.mean * 1000).toFixed(3)} ms` : 'not measured'
const suite = evaluation.test_suite || { passed: 'not recorded', failed: 'not recorded', total: 'not recorded' }

const pptx = new pptxgen()
pptx.layout = 'LAYOUT_WIDE'
pptx.author = 'ResilienceGuard'
pptx.subject = 'Eureka hackathon submission: cyber and disaster recovery readiness'
pptx.title = 'ResilienceGuard | Know what comes back'
pptx.company = 'ResilienceGuard'
pptx.lang = 'en-US'
pptx.theme = { headFontFace: 'Aptos Display', bodyFontFace: 'Aptos', lang: 'en-US' }
pptx.defineSlideMaster({
  title: 'LIGHT',
  background: { color: 'F5F8FA' },
  objects: [
    { rect: { x: 0, y: 0, w: 13.333, h: 0.07, line: { color: '16827E', transparency: 100 }, fill: { color: '16827E' } } },
    { text: { text: 'RESILIENCEGUARD  /  EUREKA HACKATHON', options: { x: 0.58, y: 7.18, w: 4.4, h: 0.15, fontFace: 'Aptos', fontSize: 7, bold: true, charSpacing: 1, color: '80929D', margin: 0 } } },
    { text: { text: 'SYNTHETIC MVP  ·  EVIDENCE BEFORE ACTION', options: { x: 8.6, y: 7.18, w: 3.98, h: 0.15, fontFace: 'Aptos', fontSize: 7, bold: true, charSpacing: 0.6, color: '80929D', align: 'right', margin: 0 } } },
  ],
  slideNumber: { x: 12.84, y: 7.16, w: 0.25, h: 0.16, color: '80929D', fontFace: 'Aptos', fontSize: 7 },
})

const C = { navy: '142C43', navy2: '1D4055', teal: '16827E', teal2: '32A092', ink: '203B50', muted: '718692', line: 'DCE6E9', white: 'FFFFFF', bg: 'F5F8FA', pale: 'ECF3F5', mint: 'E4F2EC', green: '27826B', amber: 'B7781E', paleAmber: 'FBF3E6', red: 'BF5851', paleRed: 'F8EBE9', blue: '557E9C' }
const SH = pptx.ShapeType

function addText(slide, value, x, y, w, h, options = {}) {
  slide.addText(value, { x, y, w, h, fontFace: 'Aptos', fontSize: 12, color: C.ink, margin: 0, breakLine: false, fit: 'shrink', valign: 'mid', ...options })
}
function rect(slide, x, y, w, h, fill, line = fill, radius = true) {
  slide.addShape(radius ? SH.roundRect : SH.rect, { x, y, w, h, rectRadius: 0.08, radius: 0.08, fill: { color: fill }, line: { color: line, width: 0.8 } })
}
function circle(slide, x, y, d, fill, line = fill) {
  slide.addShape(SH.ellipse, { x, y, w: d, h: d, fill: { color: fill }, line: { color: line, width: 1 } })
}
function line(slide, x1, y1, x2, y2, color = C.line, width = 1.4, dash = 'solid', endArrowType) {
  slide.addShape(SH.line, { x: x1, y: y1, w: x2 - x1, h: y2 - y1, line: { color, width, dashType: dash, endArrowType } })
}
function note(slide, text) { slide.addNotes(text) }
function header(slide, eyebrow, title, subtitle) {
  addText(slide, eyebrow.toUpperCase(), 0.62, 0.42, 11.9, 0.18, { fontSize: 8, bold: true, charSpacing: 1.6, color: C.teal })
  addText(slide, title, 0.62, 0.76, 12.0, 0.48, { fontFace: 'Aptos Display', fontSize: 25, bold: true, color: C.navy, charSpacing: -0.6 })
  if (subtitle) addText(slide, subtitle, 0.64, 1.33, 12.0, 0.28, { fontSize: 10, color: C.muted })
}
function card(slide, x, y, w, h, title, body, opts = {}) {
  rect(slide, x, y, w, h, opts.fill || C.white, opts.line || C.line)
  if (opts.icon) {
    circle(slide, x + 0.18, y + 0.18, 0.33, opts.iconFill || C.mint)
    addText(slide, opts.icon, x + 0.18, y + 0.2, 0.33, 0.26, { fontSize: 11, bold: true, color: opts.iconColor || C.teal, align: 'center' })
    addText(slide, title, x + 0.62, y + 0.19, w - 0.8, 0.24, { fontSize: opts.titleSize || 12, bold: true, color: C.navy })
    addText(slide, body, x + 0.2, y + 0.67, w - 0.4, h - 0.79, { fontSize: opts.bodySize || 9, color: opts.bodyColor || C.muted, valign: 'top', breakLine: false, lineSpacingMultiple: 1.04 })
  } else {
    addText(slide, title, x + 0.2, y + 0.17, w - 0.4, 0.27, { fontSize: opts.titleSize || 12, bold: true, color: C.navy })
    addText(slide, body, x + 0.2, y + 0.55, w - 0.4, h - 0.7, { fontSize: opts.bodySize || 9, color: opts.bodyColor || C.muted, valign: 'top', lineSpacingMultiple: 1.04 })
  }
}
function bullet(slide, text, x, y, w, opts = {}) {
  circle(slide, x, y + 0.06, 0.075, opts.dot || C.teal)
  addText(slide, text, x + 0.18, y, w - 0.18, opts.h || 0.42, { fontSize: opts.fontSize || 10, color: opts.color || C.ink, valign: 'top', breakLine: false })
}
function pill(slide, text, x, y, w, fill = C.mint, color = C.green) {
  rect(slide, x, y, w, 0.27, fill, fill)
  addText(slide, text.toUpperCase(), x + 0.06, y + 0.015, w - 0.12, 0.22, { fontSize: 7, bold: true, charSpacing: 0.5, color, align: 'center' })
}

// 1. Opening
{
  const s = pptx.addSlide(); s.background = { color: C.navy }
  s.addShape(SH.rect, { x: 0, y: 0, w: 0.13, h: 7.5, fill: { color: C.teal2 }, line: { color: C.teal2 } })
  s.addShape(SH.ellipse, { x: 8.3, y: -1.1, w: 6.1, h: 6.1, fill: { color: C.navy2, transparency: 14 }, line: { color: C.navy2, transparency: 100 } })
  s.addShape(SH.ellipse, { x: 9.7, y: 0.45, w: 3.2, h: 3.2, fill: { color: C.teal, transparency: 82 }, line: { color: C.teal, transparency: 100 } })
  pill(s, 'EUREKA HACKATHON · 2026', 0.75, 0.73, 2.28, '21495C', 'A9E7DB')
  addText(s, 'ResilienceGuard', 0.75, 1.55, 8.3, 0.88, { fontFace: 'Aptos Display', fontSize: 43, bold: true, color: C.white, charSpacing: -1.4 })
  addText(s, 'Know what comes back.', 0.78, 2.68, 7.8, 0.5, { fontSize: 24, bold: true, color: 'CBEDE4' })
  addText(s, 'See which critical services can return after a cyberattack or physical disaster.', 0.8, 3.35, 7.9, 0.56, { fontSize: 16, color: 'D0DCE4', valign: 'top' })
  line(s, 0.8, 4.32, 5.8, 4.32, '4D7387', 1)
  addText(s, 'Backup evidence  ·  dependency blockers  ·  isolated restore proof', 0.8, 4.61, 8.2, 0.3, { fontSize: 11, color: '9FB6C2' })
  addText(s, 'Synthetic MVP  /  Version 0.1.0  /  26 October 2026', 0.8, 6.83, 7.4, 0.2, { fontSize: 8, color: '829AA9', charSpacing: 0.35 })
  // concentric readiness mark
  s.addShape(SH.ellipse, { x: 9.1, y: 2.0, w: 2.45, h: 2.45, fill: { color: C.navy2, transparency: 100 }, line: { color: '4B8D8B', width: 1.5 } })
  s.addShape(SH.ellipse, { x: 9.45, y: 2.35, w: 1.75, h: 1.75, fill: { color: C.navy2, transparency: 100 }, line: { color: '60B3A4', width: 1.5 } })
  s.addShape(SH.ellipse, { x: 9.78, y: 2.68, w: 1.09, h: 1.09, fill: { color: '1A6470' }, line: { color: '4EB8A9', width: 1 } })
  addText(s, 'RG', 9.78, 2.98, 1.09, 0.35, { fontFace: 'Aptos Display', fontSize: 18, bold: true, color: C.white, align: 'center' })
  note(s, 'Open with the operator question: a successful backup job does not tell a hospital or utility whether the system can be restored after a compound disruption. ResilienceGuard is a readiness and evidence layer, not a new backup vendor. The demo uses synthetic fixtures and allows only a human-approved file copy to an isolated local directory. We will show deterministic results first, then an actual restore check and its limits.')
}

// 2. Problem
{
  const s = pptx.addSlide('LIGHT'); header(s, 'The recovery gap', 'A backup is only useful if it can be recovered', 'The evidence teams need is usually spread across inventories, backup consoles, runbooks and exercise notes.')
  card(s, 0.65, 1.9, 3.75, 1.48, 'Copy exists', 'Is the expected recovery point present, and can responders reach its location after the site is lost?', { icon: '01', bodySize: 9 })
  card(s, 0.65, 3.57, 3.75, 1.48, 'Copy can be trusted', 'Is it fresh enough? Does its digest match? Has malware cleanliness actually been established?', { icon: '02', iconFill: C.paleAmber, iconColor: C.amber, bodySize: 9 })
  card(s, 0.65, 5.24, 3.75, 1.25, 'Service can return', 'Are identity, networks, storage and upstream applications available in the right order?', { icon: '03', bodySize: 9 })
  rect(s, 4.83, 1.9, 7.82, 4.59, C.navy, C.navy)
  addText(s, 'WHEN A CRISIS HITS', 5.2, 2.25, 2.7, 0.2, { fontSize: 8, bold: true, charSpacing: 1.2, color: '86B7B3' })
  addText(s, '“Which saved copy can we test,\nand what blocks the service?”', 5.2, 2.78, 6.8, 1.12, { fontFace: 'Aptos Display', fontSize: 25, bold: true, color: C.white, valign: 'top' })
  line(s, 5.2, 4.2, 12.2, 4.2, '3A5669', 1)
  const labels = [['CYBER', 'ransomware', C.paleRed, C.red], ['PHYSICAL', 'facility loss', 'E9F1F6', C.blue], ['COMPOUND', 'power + network', C.paleAmber, C.amber]]
  labels.forEach((item, i) => { const x = 5.2 + i * 2.25; pill(s, item[0], x, 4.57, 1.38, item[2], item[3]); addText(s, item[1], x, 4.99, 1.8, 0.25, { fontSize: 9, color: 'B8C8D0' }) })
  addText(s, 'Preparedness is observable evidence, not a backup-job status.', 5.2, 5.83, 6.8, 0.25, { fontSize: 11, bold: true, color: 'D5E6E8' })
  note(s, 'Describe the gap without making unsupported outage statistics. A backup inventory alone misses at least four independent questions: existence, freshness, integrity and access across failure domains. Even a good copy does not make a dependent service recoverable if identity or a network path is missing. Hashes do not scan malware, so a single green “backup healthy” badge hides meaningful uncertainty. ResilienceGuard keeps these observations separate and ties them to a tested next step.')
}

// 3. Users
{
  const s = pptx.addSlide('LIGHT'); header(s, 'Who needs this', 'Critical-service teams need one shared recovery picture', 'Start with operators who must prove continuity across fragmented systems and teams.')
  const users = [
    ['HOSPITALS', 'Clinical applications', 'Coordinate database, identity, network and facility recovery around clinical priorities.', 'H'],
    ['UTILITIES', 'Energy and water', 'See backup and control-system dependencies across sites and critical services.', 'U'],
    ['PUBLIC SERVICES', 'Government and emergency', 'Prepare evidence for continuity exercises and cross-agency dependencies.', 'G'],
  ]
  users.forEach((u, i) => {
    const x = 0.7 + i * 4.1; rect(s, x, 2.0, 3.73, 2.35, C.white, C.line)
    circle(s, x + 0.2, 2.2, 0.38, C.mint); addText(s, u[3], x + 0.2, 2.3, 0.38, 0.14, { fontSize: 9, bold: true, color: C.teal, align: 'center' })
    addText(s, u[0], x + 0.7, 2.24, 2.6, 0.16, { fontSize: 8, bold: true, charSpacing: 0.7, color: C.teal })
    addText(s, u[1], x + 0.22, 2.92, 3.28, 0.28, { fontFace: 'Aptos Display', fontSize: 14, bold: true, color: C.navy })
    addText(s, u[2], x + 0.22, 3.42, 3.22, 0.65, { fontSize: 9.5, color: C.muted, valign: 'top' })
  })
  addText(s, 'BUYER', 0.73, 4.9, 1.1, 0.18, { fontSize: 8, bold: true, charSpacing: 1, color: C.teal })
  addText(s, 'Technology  ·  security  ·  operations  ·  risk  ·  continuity leaders', 0.73, 5.2, 8.2, 0.29, { fontSize: 14, bold: true, color: C.navy })
  addText(s, 'USERS', 0.73, 5.83, 1.1, 0.18, { fontSize: 8, bold: true, charSpacing: 1, color: C.teal })
  addText(s, 'Backup teams  ·  recovery planners  ·  security responders  ·  auditors', 0.73, 6.12, 9.8, 0.29, { fontSize: 11, color: C.muted })
  pill(s, 'PILOT FIT: FRAGMENTED RECOVERY EVIDENCE', 9.7, 5.25, 2.86, C.mint, C.green)
  note(s, 'The first economic buyer is likely accountable for service continuity, cyber risk or operational resilience; the day-to-day user is the person who assembles service and backup evidence and runs the exercise. Hospitals are a compelling first demo because the application, clinical data and identity dependencies are easy to understand, but no real hospital information is used. Utilities and public services share the same cross-site, cross-domain readiness problem. We are seeking pilot collaborators, not claiming validated purchase demand.')
}

// 4. Research
{
  const s = pptx.addSlide('LIGHT'); header(s, 'Why now', 'Resilience guidance points to tested recovery evidence', 'The product maps a narrow workflow to recognized recovery and civil resilience themes.')
  const refs = [
    ['NIST SP 1339', 'OT Backup Quick Start Guide · June 2026', 'Create backups regularly, integrate them with change processes, validate integrity and repeat non-production restore tests.', 'N'],
    ['NIST SP 800-34 Rev. 1', 'Contingency planning guidance', 'Prioritize critical systems and establish recovery strategies that fit business impact and outage requirements.', '34'],
    ['CSF 2.0 + NATO 2026', 'Recovery and civil preparedness', 'Recovery planning sits within CSF; NATO highlights essential services, cyber/physical risk and cascading disruption.', 'R'],
  ]
  refs.forEach((r, i) => {
    const x = 0.68 + i * 4.12; card(s, x, 2.0, 3.7, 2.53, r[0], r[2], { icon: r[3], titleSize: 11, bodySize: 10 })
    addText(s, r[1], x + 0.2, 4.6, 3.25, 0.2, { fontSize: 7.5, color: C.teal, bold: true })
  })
  rect(s, 0.7, 4.95, 11.95, 1.2, C.navy, C.navy)
  addText(s, 'Product boundary', 1.0, 5.2, 1.7, 0.2, { fontSize: 9, bold: true, color: '9EDBD0' })
  addText(s, 'Readiness evidence and a supervised test; not a compliance certification or backup replacement.', 2.77, 5.15, 9.4, 0.42, { fontSize: 15, bold: true, color: C.white })
  addText(s, 'Sources: csrc.nist.gov/pubs/sp/1339/final · csrc.nist.gov/pubs/sp/800/34/r1/upd1/final · nist.gov/cyberframework · nato.int, 15 Sep 2026', 0.75, 6.45, 11.9, 0.22, { fontSize: 7, color: C.muted })
  note(s, 'NIST is the US National Institute of Standards and Technology. OT means operational technology: equipment and software that monitor or control physical processes. NIST SP 1339 was finalized in June 2026 and recommends recurring restore tests on non-production systems, along with integrity checks. NIST SP 800-34 Rev. 1 is older contingency-planning guidance. CSF means NIST Cybersecurity Framework; version 2.0 names recovery as one function. NATO is the North Atlantic Treaty Organization; its September 2026 resilience baseline highlights essential services, physical and cyber risks, cascading dependencies and recovery capability. These sources inform the product idea; no organization has certified or endorsed this demo.')
}

// 5. What it does
{
  const s = pptx.addSlide('LIGHT'); header(s, 'The product', 'Turn inventory into an evidence-backed recovery decision', 'One local workflow from scenario selection to a measured sandbox restore.')
  const steps = [
    ['01', 'Import', 'Services · backups\nmanifest · targets'],
    ['02', 'Assess', 'Hash · freshness\nlocation · blockers'],
    ['03', 'Sequence', 'Dependencies first\nuncertainties shown'],
    ['04', 'Approve', 'Human reviews\nfixed sandbox action'],
    ['05', 'Prove', 'Copy · checksum\nhealth · report'],
  ]
  steps.forEach((st, i) => {
    const x = 0.72 + i * 2.52; circle(s, x + 0.53, 2.18, 0.48, i === 3 ? C.paleAmber : C.mint, i === 3 ? 'EDDAB6' : 'CFE7DF')
    addText(s, st[0], x + 0.53, 2.29, 0.48, 0.19, { fontSize: 9, bold: true, color: i === 3 ? C.amber : C.teal, align: 'center' })
    if (i < steps.length - 1) line(s, x + 1.2, 2.42, x + 2.15, 2.42, 'ADC7C9', 1.5, 'solid', 'triangle')
    addText(s, st[1], x, 2.92, 1.55, 0.27, { fontSize: 12, bold: true, color: C.navy, align: 'center' })
    addText(s, st[2], x - 0.2, 3.34, 1.95, 0.58, { fontSize: 9, color: C.muted, align: 'center', valign: 'top' })
  })
  rect(s, 0.78, 4.48, 11.75, 1.15, C.white, C.line)
  const columns = [['PRESENT', 'file found?'], ['FRESH ENOUGH', 'within data-loss target?'], ['FILE MATCH', 'fingerprint matches?'], ['MALWARE', 'unknown unless scanned'], ['RESTORE', 'tested only after copy']]
  columns.forEach((col, i) => {
    const x = 0.98 + i * 2.31; addText(s, col[0], x, 4.73, 2.08, 0.18, { fontSize: 8, bold: true, charSpacing: 0.65, color: i === 3 ? C.amber : C.teal, align: 'center' })
    addText(s, col[1], x, 5.05, 2.08, 0.23, { fontSize: 9, color: C.ink, align: 'center' })
    if (i) line(s, x - 0.1, 4.7, x - 0.1, 5.4, C.line, 0.8)
  })
  addText(s, 'No green hash badge is allowed to imply malware cleanliness.', 1.0, 6.09, 10.9, 0.28, { fontSize: 12, bold: true, color: C.navy, align: 'center' })
  note(s, 'Walk through the user journey. First import service and backup data. The system checks separately whether a file is present, its age versus the recovery point objective (RPO, the acceptable data-loss window), whether its SHA-256 fingerprint matches the saved reference, and whether its storage location can be reached. The fingerprint is not a malware scan. A person may propose and explicitly approve a specific synthetic file copy into the isolated test folder. A successful file copy is not a service recovery time objective (RTO) result: RTO is the target time to resume a service. Malware status remains unknown because no scanner runs.')
}

// 6. Differentiation
{
  const s = pptx.addSlide('LIGHT'); header(s, 'Market context', 'Complement recovery platforms with a vendor-neutral evidence layer', 'Rubrik, Veeam and Cohesity already offer substantial recovery capabilities; ResilienceGuard targets a different entry point.')
  const rows = [
    ['Rubrik', 'Recovery simulation, isolated recovery environments, threat containment and reporting.', 'Assess evidence across current backup sources; start with a small operator-owned catalog.'],
    ['Veeam', 'Recovery orchestration, plan checks, isolated labs, malware scans and RPO/RTO reports.', 'Normalize recovery prerequisites across vendors and compound physical/cyber scenarios.'],
    ['Cohesity', 'Clean-room investigation, cyber vaulting, threat analytics and recovery orchestration.', 'Lightweight readiness assessment layer; integrate rather than replace mature platforms.'],
  ]
  rect(s, 0.72, 1.9, 11.9, 0.49, C.navy, C.navy)
  addText(s, 'EXISTING OFFERING', 0.98, 2.06, 2.0, 0.15, { fontSize: 8, bold: true, color: 'B6D0D6', charSpacing: 0.6 })
  addText(s, 'OBSERVED OFFICIAL EMPHASIS', 3.05, 2.06, 4.45, 0.15, { fontSize: 8, bold: true, color: 'B6D0D6', charSpacing: 0.6 })
  addText(s, 'PROPOSED RESILIENCEGUARD POSITION', 7.76, 2.06, 4.5, 0.15, { fontSize: 8, bold: true, color: 'B6D0D6', charSpacing: 0.6 })
  rows.forEach((row, i) => {
    const y = 2.5 + i * 1.02; rect(s, 0.72, y, 11.9, 0.88, i % 2 ? 'F0F5F7' : C.white, C.line, false)
    addText(s, row[0], 0.99, y + 0.18, 1.65, 0.25, { fontSize: 12, bold: true, color: C.navy })
    addText(s, row[1], 3.05, y + 0.14, 4.3, 0.54, { fontSize: 9, color: C.muted, valign: 'mid' })
    line(s, 7.57, y + 0.14, 7.57, y + 0.73, C.line, 0.8)
    addText(s, row[2], 7.82, y + 0.14, 4.48, 0.54, { fontSize: 9, color: C.ink, valign: 'mid' })
  })
  pill(s, 'HYPOTHESIS · NOT MARKET-VALIDATED', 0.75, 5.77, 2.64, C.paleAmber, C.amber)
  addText(s, 'Differentiation to test: cross-source evidence normalization for simultaneous physical and cyber disruption.', 3.7, 5.8, 8.65, 0.28, { fontSize: 11, bold: true, color: C.navy })
  addText(s, 'Official references: rubrik.com/products/cyber-recovery · helpcenter.veeam.com/docs/vro/userguide/overview.html · cohesity.com/solutions/clean-room', 0.75, 6.43, 11.9, 0.2, { fontSize: 7, color: C.muted })
  note(s, 'Be precise about differentiation: the enterprise vendors named here already offer strong recovery verification, isolated labs, clean rooms, threat analysis or reporting. Do not claim they lack evidence or orchestration. ResilienceGuard proposes an entry point for smaller critical operators who may need a lightweight, vendor-independent view across existing tools, particularly when cyber and physical failures occur together. That buyer need, the product gap and any willingness to pay remain to be validated through interviews and pilots.')
}

// 7. Architecture
{
  const s = pptx.addSlide('LIGHT'); header(s, 'How it works', 'Rules decide recovery; optional AI explains results', 'The original sample files stay read-only; test copies go to a separate folder.')
  const boxes = [
    [0.72, 2.02, 2.52, 2.68, 'DASHBOARD', 'Choose a disruption\nSee service status\nReview evidence\nHuman approval', 'EAF3F4', C.teal],
    [3.63, 2.02, 3.1, 2.68, 'RULES ENGINE', 'File fingerprint + age\nService dependencies\nData-loss / return-time targets\nRecovery proposal', C.white, C.navy],
    [7.12, 2.02, 2.45, 2.68, 'SAVED RECORDS', 'PostgreSQL 18\nDecisions\nTest results\nAudit history', C.white, C.blue],
    [9.98, 2.02, 2.62, 2.68, 'EVIDENCE / TEST', 'Original files read-only\nSeparate test folder\nFile + structure check\nPDF report', C.mint, C.green],
  ]
  boxes.forEach((b) => {
    rect(s, b[0], b[1], b[2], b[3], b[4] === 'FASTAPI ASSURANCE' ? C.navy : b[6], b[7])
    addText(s, b[4], b[0] + 0.2, b[1] + 0.22, b[2] - 0.4, 0.22, { fontSize: 8, bold: true, charSpacing: 0.9, color: b[4] === 'FASTAPI ASSURANCE' ? '9EDBD0' : b[7] })
    addText(s, b[5], b[0] + 0.2, b[1] + 0.73, b[2] - 0.4, 1.52, { fontSize: 12, bold: true, color: b[4] === 'FASTAPI ASSURANCE' ? C.white : C.navy, breakLine: false, valign: 'top', lineSpacingMultiple: 1.16 })
  })
  line(s, 3.25, 3.34, 3.56, 3.34, '77A6A4', 1.8, 'solid', 'triangle')
  line(s, 6.74, 3.34, 7.05, 3.34, '77A6A4', 1.8, 'solid', 'triangle')
  line(s, 9.58, 3.34, 9.91, 3.34, '77A6A4', 1.8, 'solid', 'triangle')
  rect(s, 3.63, 5.1, 5.95, 0.83, 'E9F4F1', 'D5EAE2')
  addText(s, 'OPTIONAL LOCAL AI MODEL', 3.9, 5.27, 2.75, 0.17, { fontSize: 8, bold: true, charSpacing: 0.6, color: C.green })
  addText(s, 'Explains supplied evidence; cannot approve or run a restore', 6.55, 5.26, 2.75, 0.2, { fontSize: 8, color: C.ink, align: 'right' })
  line(s, 6.6, 4.73, 6.6, 5.02, '79A8A1', 1.2, 'dash', 'triangle')
  rect(s, 0.74, 6.13, 11.84, 0.48, C.navy, C.navy)
  addText(s, 'NO PRODUCTION CONNECTOR  ·  NO MODEL-EXECUTED ACTION  ·  SOURCE FILES READ-ONLY', 1.0, 6.28, 11.3, 0.15, { fontSize: 8, bold: true, charSpacing: 0.55, color: 'C5D8DE', align: 'center' })
  note(s, 'The dashboard and API are separate local services. The API applies fixed rules for file fingerprints, backup age, disruption filters and service dependencies. The named React, FastAPI, PostgreSQL and NetworkX components are implementation choices: the web dashboard, data/API service, saved workflow records and graph checks. Original synthetic files are read-only; restore output uses a separate directory or volume. An optional local model only summarizes evidence; it has no recovery tools. The optional Ollama/Qwen3 path was not run in the evaluation. PostgreSQL stores demo workflow state, not backup files.')
}

// 8. Scenarios
{
  const s = pptx.addSlide('LIGHT'); header(s, 'Possible disruptions', 'Test three ways a critical service could fail', 'The same inventory is checked against each scenario; the demo does not simulate a real attack or disaster.')
  const scenarios = [
    ['01', 'PRIMARY SITE LOST', 'Physical disaster', 'Primary building, systems and East backup location are unavailable. West and recovery sites remain.', C.paleRed, C.red, 'DC'],
    ['02', 'RANSOMWARE', 'New copy is altered', 'Newest database file is present and recent, but its fingerprint fails and the scenario distrusts it.', C.paleAmber, C.amber, 'CY'],
    ['03', 'COMBINED FAILURE', 'Power, network, site', 'Primary power and network fail, along with the East backup location. West remains reachable.', 'EAF3F6', C.blue, 'P+N'],
  ]
  scenarios.forEach((r, i) => {
    const x = 0.72 + i * 4.08; rect(s, x, 2.0, 3.72, 3.43, C.white, C.line)
    circle(s, x + 0.2, 2.22, 0.48, r[4], r[4]); addText(s, r[0], x + 0.2, 2.35, 0.48, 0.18, { fontSize: 9, bold: true, color: r[5], align: 'center' })
    addText(s, r[1], x + 0.82, 2.24, 2.6, 0.18, { fontSize: 8, bold: true, charSpacing: 0.75, color: r[5] })
    addText(s, r[2], x + 0.22, 2.98, 3.22, 0.35, { fontFace: 'Aptos Display', fontSize: 15, bold: true, color: C.navy })
    addText(s, r[3], x + 0.22, 3.54, 3.22, 0.92, { fontSize: 10, color: C.muted, valign: 'top' })
    pill(s, i === 1 ? 'INTEGRITY FAILURE' : 'DOMAIN FILTERED', x + 0.22, 4.87, i === 1 ? 1.65 : 1.6, r[4], r[5])
  })
  addText(s, 'For each: Is a copy reachable? Is it within the data-loss target? What else is missing?', 1.05, 5.98, 11.2, 0.3, { fontSize: 12, bold: true, color: C.navy, align: 'center' })
  note(s, 'The three scenarios share the same fixed synthetic catalog and reference time. Scenario one removes the primary data center and East backup location. Scenario two marks the newest database copy as altered and untrusted while an older copy remains. Scenario three removes primary power/network plus the East location, but leaves a different copy reachable through an independent network. A vault here means a separate backup storage location. The engine recalculates reachable candidates and service blockers. The scenarios are rule-based examples, not a simulation of a real attack or physical event.')
}

// 9. Dependencies
{
  const s = pptx.addSlide('LIGHT'); header(s, 'Service dependencies', 'Restore prerequisites before the hospital app', 'The app needs its database and identity service; identity needs directory data.')
  const nodes = [
    [1.0, 2.28, 2.45, 0.78, 'HOSPITAL APP', 'BLOCKED', C.paleAmber, C.amber],
    [4.3, 2.28, 2.45, 0.78, 'CLINICAL DB', 'TESTABLE · OLD', C.mint, C.green],
    [4.3, 4.13, 2.45, 0.78, 'IDENTITY', 'BLOCKED', C.paleAmber, C.amber],
    [8.0, 4.13, 2.45, 0.78, 'DIRECTORY STORE', 'NO BACKUP', C.paleRed, C.red],
    [8.0, 5.45, 2.45, 0.58, 'RECOVERY NETWORK', 'AVAILABLE', 'EAF3F6', C.blue],
  ]
  line(s, 3.5, 2.68, 4.2, 2.68, '95B4B5', 1.8, 'solid', 'triangle')
  line(s, 3.5, 2.76, 4.2, 4.35, '95B4B5', 1.8, 'solid', 'triangle')
  line(s, 6.8, 4.48, 7.9, 4.48, 'D3A956', 1.8, 'dash', 'triangle')
  nodes.forEach((n) => {
    rect(s, n[0], n[1], n[2], n[3], C.white, C.line)
    addText(s, n[4], n[0] + 0.16, n[1] + 0.12, n[2] - 0.32, 0.18, { fontSize: 9, bold: true, charSpacing: 0.35, color: C.navy })
    pill(s, n[5], n[0] + 0.16, n[1] + 0.42, Math.min(1.25, n[2] - 0.32), n[6], n[7])
  })
  rect(s, 10.85, 2.28, 1.75, 2.05, C.navy, C.navy)
  addText(s, 'BLOCKER', 11.08, 2.55, 1.25, 0.17, { fontSize: 8, bold: true, charSpacing: 0.7, color: '9DDCCF', align: 'center' })
  addText(s, 'No Directory Store backup record', 11.05, 2.95, 1.35, 0.72, { fontSize: 12, bold: true, color: C.white, align: 'center', valign: 'mid' })
  addText(s, 'Identity cannot be rebuilt; app remains blocked.', 10.97, 3.8, 1.5, 0.4, { fontSize: 8, color: 'B8CAD2', align: 'center', valign: 'top' })
  pill(s, 'RULE-BASED RECOVERY ORDER', 0.93, 6.37, 2.68, 'E9F1F5', C.blue)
  addText(s, 'Example at 08:00: the 05:00 database file is one hour beyond its two-hour data-loss target.', 3.88, 6.36, 8.3, 0.25, { fontSize: 9, color: C.muted })
  note(s, 'In this primary data-center scenario, Hospital Care Coordination depends on the clinical database and identity service. The database has a West-location copy whose saved fingerprint matches, but the file is three hours old at 08:00. The data-loss target is two hours, so it is one hour outside target. It can be tested in the demo, but the age gap must be accepted by the service owner. Identity depends on Directory Store, and there is no backup record for that directory data. That missing prerequisite blocks identity and therefore the app. The dependency graph means a map of which service needs which other service; the rules determine the same restore order each time.')
}

// 10. Governed AI
{
  const s = pptx.addSlide('LIGHT'); header(s, 'AI assistant', 'AI explains evidence; a person controls action', 'Fixed rules decide what may be tested. The optional model cannot approve or run a restore.')
  rect(s, 0.75, 2.0, 4.25, 3.55, C.navy, C.navy)
  pill(s, 'OPTIONAL LOCAL MODEL', 1.0, 2.24, 1.8, '21495C', 'A9E7DB')
  addText(s, 'Evidence in', 1.02, 2.9, 2.6, 0.28, { fontSize: 15, bold: true, color: C.white })
  addText(s, 'Scenario findings\npermitted evidence IDs\nrule-only baseline plan', 1.05, 3.37, 3.35, 0.92, { fontSize: 11, color: 'B6C8D1', valign: 'top' })
  line(s, 1.05, 4.52, 4.48, 4.52, '35596A', 1)
  addText(s, 'Ollama 0.40.11 · Qwen3 8B', 1.05, 4.78, 3.4, 0.25, { fontSize: 11, bold: true, color: 'C5EEE4' })
  addText(s, 'Local and optional · Apache-2.0 model', 1.05, 5.1, 3.35, 0.18, { fontSize: 8, color: '92AEB9' })
  const gates = [
    ['01', 'Use only supplied facts', 'Do not invent recovery details'],
    ['02', 'Cite evidence references', 'Reject unknown references'],
    ['03', 'Say what is unknown', 'A matching fingerprint is not a malware scan'],
    ['04', 'Wait for a person', 'The person approves or rejects a test copy'],
  ]
  gates.forEach((g, i) => {
    const y = 2.02 + i * 0.93; circle(s, 5.62, y + 0.09, 0.34, i === 3 ? C.paleAmber : C.mint)
    addText(s, g[0], 5.62, y + 0.16, 0.34, 0.14, { fontSize: 7, bold: true, color: i === 3 ? C.amber : C.teal, align: 'center' })
    addText(s, g[1], 6.13, y + 0.07, 4.6, 0.22, { fontSize: 11, bold: true, color: C.navy })
    addText(s, g[2], 6.13, y + 0.39, 4.6, 0.21, { fontSize: 9, color: C.muted })
    if (i < 3) line(s, 5.79, y + 0.48, 5.79, y + 0.87, 'A9C8C2', 1.2)
  })
  pill(s, 'DETERMINISTIC FALLBACK WHEN MODEL IS OFFLINE', 6.12, 5.91, 3.55, 'E9F1F5', C.blue)
  addText(s, 'No model execution occurred in the measured evaluation.', 6.12, 6.38, 5.7, 0.2, { fontSize: 9, color: C.muted })
  note(s, 'The model is an optional local summarizer. It sees current scenario facts, a baseline plan and the evidence IDs that already exist. The API validates the response format and allowed evidence/action IDs. It has no recovery tools. The deterministic engine owns backup eligibility, dependency blockers and action control. If no model is running, the assistant returns a deterministic fallback. In this evaluation no Qwen3 inference was run, so do not claim measured generative accuracy; natural-language text remains advisory and may need correction.')
}

// 11. Actual restore
{
  const s = pptx.addSlide('LIGHT'); header(s, 'Isolated test', 'A real sample file copy is measured and checked', 'A person approved the copy; the source stayed unchanged; the test folder is separate.')
  rect(s, 0.75, 1.97, 4.2, 4.15, C.navy, C.navy)
  addText(s, 'RESTORE OBSERVATION', 1.03, 2.26, 2.3, 0.18, { fontSize: 8, bold: true, charSpacing: 1, color: '9FD7CC' })
  addText(s, meanMs, 1.02, 2.8, 3.5, 0.65, { fontFace: 'Aptos Display', fontSize: 31, bold: true, color: C.white, charSpacing: -0.7 })
  addText(s, `mean over ${restore.samples || 0} actual local copy runs`, 1.06, 3.51, 3.25, 0.22, { fontSize: 9, color: 'A7BDC6' })
  line(s, 1.05, 4.02, 4.55, 4.02, '3B5A6E', 1)
  addText(s, 'Scope', 1.05, 4.33, 0.75, 0.19, { fontSize: 8, bold: true, color: '9FD7CC' })
  addText(s, 'file copy + fingerprint\n+ sample data structure check', 1.05, 4.68, 3.3, 0.67, { fontSize: 14, bold: true, color: C.white, valign: 'top' })
  addText(s, 'Not service recovery time', 1.05, 5.65, 2.7, 0.22, { fontSize: 10, bold: true, color: 'F0C985' })
  const results = [
    ['Source file', 'clinical database sample · West location', 'verified'],
    ['Approval', 'person approved the pending test', 'recorded'],
    ['Copy target', 'unique isolated test folder', 'separate volume'],
    ['File check', 'source and copy fingerprints match', 'matched'],
    ['Data check', 'expected JSON fields and record count', 'passed'],
    ['Malware status', 'no scanner executed', 'unknown'],
  ]
  results.forEach((r, i) => {
    const y = 2.03 + i * 0.62; if (i) line(s, 5.55, y, 12.5, y, C.line, 0.7)
    addText(s, r[0], 5.64, y + 0.16, 1.45, 0.2, { fontSize: 9, bold: true, color: C.navy })
    addText(s, r[1], 7.12, y + 0.16, 3.48, 0.2, { fontSize: 9, color: C.muted })
    addText(s, r[2].toUpperCase(), 10.88, y + 0.16, 1.45, 0.2, { fontSize: 8, bold: true, color: r[2] === 'unknown' ? C.amber : C.green, align: 'right' })
  })
  note(s, `The evaluation script performed ${restore.samples || 0} actual copies of the registered synthetic clinical database JSON into temporary isolated directories. The measured mean for copying the file, comparing source and destination SHA-256 fingerprints, and checking expected sample-data fields was ${meanMs}. The API workflow separately requires an explicit human approval, records the decision and audit event, and exposes the output for download. A fingerprint match means the file matches the saved reference; it does not mean the file is malware-free. This validates a small file fixture, not a PostgreSQL restore, application start, malware scan or target time to recover the service.`)
}

// 12. Evaluation
{
  const s = pptx.addSlide('LIGHT'); header(s, 'Evaluation', 'Measured against known synthetic truth', 'Automated tests check the explicit rules; the experiment is intentionally small and reproducible.')
  const metrics = [
    ['pytest suite', `${suite.passed}/${suite.total}`, `${suite.failed} failures`, C.green],
    ['File fingerprint', pct('SHA-256 expected good/bad classification'), 'expected match / mismatch', C.green],
    ['Backup age', pct('RPO freshness classification'), 'age vs data-loss target', C.green],
    ['Service blockers', pct('Recovery dependency matrix (4 services × 3 scenarios)'), '4 services × 3 scenarios', C.green],
    ['Approved test copy', pct('Approved isolated restore copy + hash + fixture health'), 'copy + file/data checks', C.green],
    ['Unsafe copy denied', pct('Unauthorized/untrusted restore prevention'), 'pending or untrusted', C.green],
  ]
  metrics.forEach((m, i) => {
    const x = 0.72 + (i % 3) * 4.08; const y = 2.0 + Math.floor(i / 3) * 1.45
    rect(s, x, y, 3.72, 1.2, C.white, C.line)
    addText(s, m[0].toUpperCase(), x + 0.18, y + 0.16, 2.6, 0.16, { fontSize: 7.5, bold: true, charSpacing: 0.55, color: C.teal })
    addText(s, m[1], x + 0.18, y + 0.43, 2.65, 0.32, { fontFace: 'Aptos Display', fontSize: 19, bold: true, color: C.navy })
    addText(s, m[2], x + 0.18, y + 0.84, 3.15, 0.16, { fontSize: 8, color: C.muted })
  })
  rect(s, 0.74, 5.16, 11.9, 0.94, C.paleAmber, 'EEDFC3')
  addText(s, 'AI BASELINE', 0.99, 5.42, 1.1, 0.16, { fontSize: 8, bold: true, charSpacing: 0.6, color: C.amber })
  addText(s, `Fallback actions ${evaluation.plan_action_parity ? 'match' : 'differ from'} rule-only baseline · evidence/action IDs constrained · local model accuracy not run`, 2.24, 5.34, 9.92, 0.32, { fontSize: 10, bold: true, color: C.ink })
  addText(s, 'npm audit: 0 findings after image-size override  ·  pip-audit: 0 findings  ·  synthetic only', 0.95, 6.43, 11.4, 0.2, { fontSize: 8, color: C.muted, align: 'center' })
  note(s, `The test suite recorded ${suite.passed} passing tests out of ${suite.total}, with ${suite.failed} failures. Each fraction on the slide is correct expected answers divided by checked examples, not a claim about real-world service readiness. The synthetic evaluation matched known file fingerprint, backup age and missing-backup labels. It checks four services under each of three disruption scenarios. Actual isolated copies passed file and sample-data checks. Pending and scenario-untrusted copies were denied. The assistant's allowed actions matched the rule-based baseline and its evidence references stayed within the supplied set, but this used the deterministic fallback only. No AI model inference was measured. Dependency audits report zero findings at this snapshot; that is not a full security assessment.`)
}

// 13. Business model
{
  const s = pptx.addSlide('LIGHT'); header(s, 'Commercial model', 'Services-led pilots can fund a recurring assurance layer', 'Illustrative first-year planning model · all figures are assumptions, not market pricing.')
  const x0 = 0.74; const y0 = 2.0; const colW = [2.6, 2.25, 2.25, 2.25, 2.25]
  const heads = ['CUSTOMERS', 'REVENUE', 'DIRECT COST', 'GROSS PROFIT*', 'NET RESULT*']
  let x = x0; heads.forEach((h, i) => { rect(s, x, y0, colW[i], 0.46, C.navy, C.navy, false); addText(s, h, x + 0.06, y0 + 0.15, colW[i] - 0.12, 0.13, { fontSize: 7, bold: true, charSpacing: 0.45, color: 'C5D7DE', align: i ? 'right' : 'left' }); x += colW[i] })
  const rows = [
    ['1', '$78k', '$18k', '$60k', '-$200k'],
    ['5', '$390k', '$90k', '$300k', '-$60k'],
    ['10', '$780k', '$180k', '$600k', '$80k'],
    ['25', '$1.95m', '$450k', '$1.50m', '$750k'],
  ]
  rows.forEach((row, r) => { let cx = x0; row.forEach((v, i) => { rect(s, cx, y0 + 0.47 + r * 0.54, colW[i], 0.53, r % 2 ? 'F0F5F7' : C.white, C.line, false); addText(s, v, cx + 0.07, y0 + 0.63 + r * 0.54, colW[i] - 0.14, 0.17, { fontSize: 11, bold: i === 0 || i === 4, color: i === 4 && v.startsWith('-') ? C.red : C.navy, align: i ? 'right' : 'left' }); cx += colW[i] }) })
  addText(s, 'Per customer first year: $18k implementation + $48k license + $12k support = $78k revenue.', 0.83, 4.9, 11.8, 0.25, { fontSize: 10, bold: true, color: C.navy })
  addText(s, '*Gross profit = revenue minus direct delivery costs. Net result also subtracts assumed fixed business overhead. Pre-tax; excludes tax, financing, and customer acquisition/churn costs.', 0.83, 5.32, 11.8, 0.26, { fontSize: 8, color: C.muted })
  rect(s, 0.83, 5.86, 11.75, 0.54, C.mint, 'D8EBE3')
  addText(s, 'Measure customer ROI with validated outage costs, recovery labor and evidence-preparation hours; do not use generic loss claims.', 1.02, 6.04, 11.3, 0.17, { fontSize: 9, bold: true, color: C.green, align: 'center' })
  note(s, 'These assumptions make the business case transparent. First-year revenue per customer is modeled as an $18,000 implementation fee plus a $48,000 annual license and $12,000 annual support fee. Direct costs are assumed at $18,000 per customer. The table subtracts estimated fixed product, sales and administrative overhead to show an illustrative net result. None of these prices or costs are market-verified, and this is not a forecast. ROI should be calculated using the customer’s own outage impact and labor baseline.')
}

// 14. Ask and close
{
  const s = pptx.addSlide(); s.background = { color: C.navy }
  s.addShape(SH.rect, { x: 0, y: 0, w: 13.333, h: 0.08, fill: { color: C.teal2 }, line: { color: C.teal2 } })
  pill(s, 'WHAT WE NEED NEXT', 0.78, 0.82, 1.72, '21495C', 'A9E7DB')
  addText(s, 'Pilot the evidence layer\nwith a critical-service team.', 0.78, 1.55, 8.8, 1.2, { fontFace: 'Aptos Display', fontSize: 31, bold: true, color: C.white, valign: 'top', charSpacing: -0.65 })
  const asks = [
    ['01', 'One service catalog', '3–5 services, owners, data-loss/time-to-recover targets and dependencies'],
    ['02', 'One joint exercise', 'Physical loss + ransomware + a compound disruption scenario'],
    ['03', 'One measured result', 'Known gaps, approved isolated test, observed duration and report'],
  ]
  asks.forEach((a, i) => { const y = 3.48 + i * 0.77; circle(s, 0.85, y + 0.05, 0.34, '1D5C64'); addText(s, a[0], 0.85, y + 0.13, 0.34, 0.13, { fontSize: 7, bold: true, color: 'A9E7DB', align: 'center' }); addText(s, a[1], 1.42, y + 0.01, 2.1, 0.22, { fontSize: 12, bold: true, color: C.white }); addText(s, a[2], 3.4, y + 0.02, 5.9, 0.28, { fontSize: 9, color: 'AFC3CC' }) })
  line(s, 0.85, 6.1, 11.9, 6.1, '3B5A6E', 1)
  addText(s, 'ResilienceGuard', 0.85, 6.43, 4.5, 0.35, { fontFace: 'Aptos Display', fontSize: 19, bold: true, color: 'A7E3D7' })
  addText(s, 'Know what comes back.', 8.4, 6.49, 3.3, 0.22, { fontSize: 11, color: 'B9CCD4', align: 'right' })
  note(s, 'Close with a practical pilot request. RPO means recovery point objective: how much data age the organization is willing to lose. RTO means recovery time objective: the target time for restoring a service. We need an operator willing to test a small service catalog and validate whether the evidence model and dependency questions fit its recovery process. The first pilot should agree on three to five services, one tabletop covering physical loss, ransomware and combined disruption, and one controlled isolated restore. Success measures could include backup coverage and age, blockers identified, approval traceability, observed test duration, and time to assemble an evidence report. Avoid production access until security and governance controls are designed and reviewed.')
}

await pptx.writeFile({ fileName: path.join(ROOT, 'ResilienceGuard_Pitch_Deck.pptx') })
console.log(`Generated 14-slide deck with notes: ${path.join(ROOT, 'ResilienceGuard_Pitch_Deck.pptx')}`)
