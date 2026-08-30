A4_PRINT_CSS = """
:root {
  color-scheme: light;
  font-family: "Noto Sans CJK SC", "Source Han Sans SC", "PingFang SC",
    "Microsoft YaHei", "SimSun", sans-serif;
  color: #1f1f1f;
  background: #ffffff;
}

* {
  box-sizing: border-box;
}

html,
body {
  margin: 0;
  padding: 0;
  background: #ffffff;
}

body {
  font-size: 10.5pt;
  line-height: 1.65;
  -webkit-font-smoothing: antialiased;
}

.report {
  width: 100%;
  max-width: 182mm;
  margin: 0 auto;
}

h1,
h2,
h3,
h4,
p,
li,
th,
td {
  overflow-wrap: anywhere;
  word-break: break-word;
}

h1 {
  margin: 0 0 7mm;
  padding-bottom: 4mm;
  border-bottom: 1.2pt solid #1f1f1f;
  font-size: 23pt;
  line-height: 1.25;
  letter-spacing: 0.02em;
}

h2 {
  margin: 8mm 0 4mm;
  padding-bottom: 2mm;
  border-bottom: 0.8pt solid #6b6b6b;
  font-size: 16pt;
  line-height: 1.3;
}

h3 {
  margin: 5mm 0 2.5mm;
  font-size: 12.5pt;
  line-height: 1.35;
}

h4 {
  margin: 4mm 0 2mm;
  font-size: 11pt;
  line-height: 1.4;
}

h2,
h3,
h4 {
  break-after: avoid-page;
  page-break-after: avoid;
}

p {
  margin: 0 0 3mm;
  orphans: 3;
  widows: 3;
}

ul,
ol {
  margin: 1.5mm 0 3mm;
  padding-left: 6mm;
}

li {
  margin: 0 0 1.3mm;
}

strong {
  font-weight: 700;
}

code {
  padding: 0.2mm 0.8mm;
  border: 0.5pt solid #d4d4d4;
  background: #f4f4f4;
  font-family: "Noto Sans Mono CJK SC", "SFMono-Regular", Consolas, monospace;
  font-size: 8.8pt;
  white-space: normal;
}

.report-section {
  width: 100%;
  break-inside: auto;
}

.decision-snapshot {
  min-height: 205mm;
  break-after: page;
  page-break-after: always;
}

.decision-snapshot > h2 {
  margin-top: 3mm;
  font-size: 18pt;
}

.causal-bridge p {
  padding: 4mm;
  border-left: 2.2pt solid #3f3f3f;
  background: #f2f2f2;
  font-weight: 600;
}

.table-wrap {
  width: 100%;
  margin: 2.5mm 0 5mm;
  overflow: visible;
}

table {
  width: 100%;
  border-collapse: collapse;
  table-layout: fixed;
  break-inside: auto;
  page-break-inside: auto;
  font-size: 9pt;
}

thead {
  display: table-header-group;
}

tfoot {
  display: table-footer-group;
}

tr {
  break-inside: avoid;
  page-break-inside: avoid;
}

th,
td {
  padding: 2mm 2.2mm;
  border: 0.55pt solid #9a9a9a;
  vertical-align: top;
  text-align: left;
}

th {
  background: #e8e8e8;
  color: #1f1f1f;
  font-weight: 700;
}

tbody tr:nth-child(even) td {
  background: #f7f7f7;
}

.audit-appendix {
  break-before: page;
  page-break-before: always;
  font-size: 8.4pt;
  line-height: 1.5;
}

.audit-appendix h2 {
  border-bottom-style: double;
}

.audit-appendix table,
.audit-appendix code,
.audit-appendix li,
.audit-appendix p {
  overflow-wrap: anywhere;
  word-break: break-all;
}

@page {
  size: A4;
  margin: 15mm 14mm 18mm;
}

@page :first {
  margin-top: 14mm;
}

@media print {
  html,
  body {
    color: #1f1f1f;
    background: #ffffff;
  }

  .report {
    width: 100%;
    max-width: 100%;
  }

  a {
    color: #1f1f1f;
    text-decoration: underline;
  }
}
""".strip() + "\n"
