# Gaps in Existing Government Projects and Data Systems in India

**Prepared:** 27 September 2026  
**Purpose:** Identify where existing Indian government platforms, programmes, and datasets leave room for a multilingual citizen-feedback and infrastructure-prioritisation platform.

## Executive summary

India already has grievance portals, sector dashboards, district-development indicators, and project-monitoring systems. The gap is not an absence of government activity. The gap is that these systems generally serve separate purposes and do not provide one public, location-linked path from **citizen need → verified service gap → existing/planned investment → priority decision → project outcome**.

The most material gaps for the proposed platform are:

1. **Citizen feedback is not openly available in a reusable, case-level form.** CPGRAMS accepts grievances and exposes aggregate statistics, but the grievance-detail dataset is described as restricted in the OGD access guide.
2. **Sector data is fragmented.** Water, roads, schools, health and district indicators live in separate systems, with different update cycles and geographic units.
3. **Feedback is not consistently connected to capital planning.** Grievance redressal systems primarily route and resolve individual cases; they do not, by themselves, show whether repeated requests should change infrastructure investment priorities.
4. **Demand and need are different signals.** Complaint counts can be biased by awareness, connectivity, language, and ability to use a reporting channel. They need to be interpreted with population and service-gap data.
5. **Project tracking does not automatically establish public impact.** A project record or completed connection is not the same as reliable service, quality, accessibility, or a measured improvement in residents’ lives.
6. **Data sharing and interoperability remain active policy concerns.** Government materials identify institutional data silos and the need for common standards, metadata, and APIs.

These points describe gaps relative to the challenge’s intended end-to-end platform. They are not a claim that every Indian government project is ineffective or that every agency lacks internal data.

## Existing systems and their gaps

| System or programme | What it already provides | Gap relative to the challenge | Evidence / source |
|---|---|---|---|
| **CPGRAMS** (Centralized Public Grievance Redress and Monitoring System) | Online grievance submission, routing to ministries/states, status tracking, appeal and post-closure feedback. The portal lists support for many Indian languages. | It is primarily a grievance redress workflow, not a unified citizen-demand analytics and infrastructure investment platform. Publicly searchable grievance figures are aggregate. The OGD guide labels case-level grievance and feedback details as restricted; therefore an open case-level training corpus cannot be assumed. | [CPGRAMS](https://pgportal.gov.in/); [CPGRAMS OGD access guide](https://event.data.gov.in/wp-content/uploads/2019/12/CPGRAMS_accessing_API_HelpGuide_User.pdf); [CPGRAMS datasets on OGD](https://www.data.gov.in/keywords/CPGRAMS) |
| **Jal Jeevan Mission (JJM)** | Public dashboard with household tap-water status, village-level views, water-quality information, and school/anganwadi views. OGD also catalogs JJM datasets. | Water-only; connection coverage does not by itself establish continuity, quantity, quality, affordability, or whether the source works during different seasons. Citizen reports are not shown as a unified demand layer alongside water assets, works, and outcomes. | [JJM dashboard](https://ejalshakti.gov.in/JJMreport/); [JJM OGD catalogue](https://tn.data.gov.in/catalog/jal-jeevan-mission-jjm) |
| **PMGSY / rural roads** | Core-network planning and programme information for rural connectivity; the core network is intended to provide basic access to habitations. | Road access is a specific sector measure. To rank needs across sectors, road status needs to be joined with population, access to schools/health/markets, road condition, project status, and citizen-reported issues in a shared geography. | [PMGSY Core Network](https://www.pmgsy.nic.in/core-network); [PMGSY GIS information](https://www.pib.gov.in/Pressreleaseshare.aspx?PRID=1909253&lang=2&reg=48) |
| **UDISE+** | Annual school information, including school infrastructure, enrolment, and teachers; provides dashboards and reports. | Education-only. Indicators can identify facilities or resource gaps but do not represent all community demand, validate condition in real time, or connect a school need to cross-sector investment ranking. | [UDISE+](https://udiseplus.gov.in/); [UDISE+ 2023–24 report](https://www.education.gov.in/sites/upload_files/mhrd/files/statistics-new/udise_report_nep_23_24.pdf) |
| **Health Dynamics of India** | State-level statistics on public health infrastructure and human resources, including reported shortfalls. | Useful for sector planning but not a single geospatial feed of local citizen needs, facility condition, planned works, and resulting service improvement. Publicly available aggregate tables may not be sufficient for block/village-level project selection. | [Health Dynamics of India 2022–23](https://www.mohfw.gov.in/sites/default/files/Health%20Dynamics%20of%20India%20%28Infrastructure%20%26%20Human%20Resources%29%202022-23_RE%20%281%29.pdf) |
| **Aspirational Districts Programme (ADP)** | District progress across 49 key performance indicators under five broad themes: health and nutrition, education, agriculture and water, financial inclusion and skills, and infrastructure. | A high-level district-monitoring and competition framework, not an intake system for voice/text requests or a case-level map of infrastructure demand. District aggregation can hide underserved blocks, villages, wards, or groups. | [NITI Aayog ADP](https://www.niti.gov.in/aspirational-districts-programme) |
| **Census / demographic datasets** | Population and household context, including historical household amenities and village/district information. | Census 2011 household amenity data is dated for current operational decisions. Newer sources differ in geography and definitions, so data must be versioned and harmonised rather than treated as a single current baseline. | [Census tables](https://censusindia.gov.in/census.website/data/census-tables); [Census HL-11 amenities table](https://censusindia.gov.in/nada/index.php/catalog/8939) |
| **Open Government Data Platform (data.gov.in)** | Catalog and APIs for a large number of government datasets, including some JJM and CPGRAMS aggregate data. | A catalogue is not by itself an integrated analytical layer. Availability, geographic detail, machine-readability, update frequency, metadata quality, licensing, and APIs vary by dataset. Restricted data remains unavailable to public users. | [data.gov.in](https://www.data.gov.in/); [CPGRAMS OGD catalogue](https://www.data.gov.in/keywords/CPGRAMS) |
| **National data-sharing and interoperability initiatives** | National policy work aimed at improving data sharing, standards, metadata, APIs, and governance. | The need for these initiatives reflects that interoperability and institutional silos are still material challenges. The proposed platform would need to align with standards and permissions rather than assume that separate departmental records can simply be joined. | [National Data Governance framework](https://www.negd.gov.in/ndg/ndg); [MeitY metadata/data standards](https://docs.apisetu.gov.in/document-central/mdds/Introduction.html) |

## Cross-cutting gaps

### 1. No shared, location-linked view across all signals

Citizen submissions, demographic data, infrastructure indicators, and investment records often use different identifiers and geographic levels. A request may refer to a neighbourhood or habitation, while a programme dashboard reports at village, block, district, or state level. Without a common geography and crosswalks, hotspots can be misplaced, obscured, or double-counted.

**Platform implication:** use official administrative codes where possible; preserve the original reported location and geocoding confidence; retain source, date, and geographic resolution for every joined record.

### 2. Citizen demand data is incomplete and hard to reuse

The public CPGRAMS surface confirms multilingual access and grievance status functions, but the open data catalog primarily exposes totals and department/state summaries. A historical OGD guide labels case-level grievance text and feedback as restricted. Openly accessible citizen reports suitable for training a national infrastructure model are therefore not established by the sources reviewed.

**Platform implication:** seek an approved, privacy-preserving data-sharing arrangement or run a consented pilot. Do not scrape personal grievance records or infer that the ability to lodge a grievance means the underlying records are open.

### 3. Digital-channel participation can leave people out

A platform that relies on internet forms or app use will under-represent people with limited connectivity, literacy, device access, or comfort with official portals. Multilingual interface support helps, but does not prove that speech recognition or issue classification works well for local accents, code-switching, dialects, or low-resource languages.

**Platform implication:** support voice and assisted/offline submission where feasible; measure participation by language and geography; provide human review and a way to correct transcription or classification.

### 4. Complaint volume is not the same as severity or unmet need

A high count may reflect a widespread service failure, greater awareness of a portal, or easier access to that channel. A low count may mean a community is underserved or cannot report. Complaint volume alone would therefore reproduce participation bias.

**Platform implication:** combine feedback volume with population, deprivation, service coverage, facility capacity/condition, severity, urgency, and access barriers. Display each component so officials can understand why a location ranks highly.

### 5. Project and budget records may not show whether residents benefited

A planned, approved, or completed project record describes an administrative milestone. It does not necessarily demonstrate that a service is reliable, safe, accessible, or meeting demand. For example, a water connection count is different from continuous safe water, and the presence of a school facility is different from functional access or adequate staffing.

**Platform implication:** connect budgets and project status with operational indicators and post-completion outcomes; record the date and method used to verify improvement.

### 6. Cross-sector prioritisation is not transparent in one place

Sector dashboards can show a need within their own programme. ADP offers broad district indicators. The reviewed sources do not establish a single public tool that ranks local projects by combining citizen demand, infrastructure deficit, equity, cost, readiness, and ongoing investment across sectors.

**Platform implication:** present recommendations as explainable decision support, with configurable weights, uncertainty, existing-project checks, and human approval—not as an automatic funding decision.

### 7. Project overlap and duplication are difficult to rule out without portfolio integration

If the platform recommends a project without joining approved, ongoing, and recently completed works, it can recommend duplicative investment or overlook an already-funded intervention. Public project records are spread across schemes, ministries, states, and funders.

**Platform implication:** ingest project identifiers, sector, location, status, budget, timeline, funding source, intended beneficiaries, and completion/outcome fields; flag missing or stale entries.

### 8. Data freshness and definitions vary

Some sources are frequently updated administrative dashboards; others are annual reports or older census tables. Terms such as “coverage,” “functional,” “access,” “served,” and “completed” may not mean the same thing across systems.

**Platform implication:** retain source metadata and reference dates; expose staleness; harmonise definitions carefully and do not silently treat unlike indicators as directly comparable.

### 9. Feedback-to-action and impact measurement are not one continuous loop

Grievance systems can track whether a case was disposed; scheme dashboards can track outputs; district frameworks can track indicators. Those are useful but distinct. A unified record linking a citizen need to a selected project, delivery milestone, and measured change is still needed for the proposed impact-tracking use case.

**Platform implication:** use a traceable chain: request → verification → issue cluster → decision → funded project → implementation → outcome → citizen follow-up.

### 10. Privacy, security, and trust are core implementation requirements

Case-level grievances can contain names, addresses, phone numbers, health or financial details, and sensitive allegations. Combining that data with fine-grained location and demographics can create re-identification risks. Public release of raw feedback is not necessary for the system to provide aggregate planning insights.

**Platform implication:** minimise collection, separate identity from issue records, control access, aggregate small groups, document consent and purpose, and publish only privacy-reviewed outputs.

## Priority gap list for a project proposal

1. **Interoperability:** Build connectors and a shared geographic/data model for existing datasets.
2. **Open citizen demand:** Create an authorised path for privacy-protected request data, since public complaint-level access is limited.
3. **Inclusive intake:** Add multilingual text/voice channels and human correction, then audit coverage and quality by language and region.
4. **Cross-sector hotspot identification:** Combine requests with population, deprivation, infrastructure condition, and service coverage.
5. **Investment alignment:** Match hotspots against planned, approved, active, and completed projects before recommending anything new.
6. **Explainable prioritisation:** Show the evidence, uncertainty, equity effect, cost/readiness assumptions, and reason for each priority.
7. **Outcome tracking:** Measure whether a project improved service after completion and whether the original need was resolved.
8. **Governance and privacy:** Define data ownership, lawful access, retention, appeals/corrections, security, and audit processes.

## Suggested first pilot

Choose one state or district and one infrastructure sector, such as rural drinking water. Join:

- consented, de-identified citizen requests with date, language, channel, issue, location, and status;
- village-level water coverage and quality data from JJM;
- population and vulnerability data;
- planned and ongoing water works with cost, schedule, and status;
- post-work functionality and resident follow-up.

This pilot would test the hardest integration question—whether citizen demand can be joined to verified local need and investment progress—before expanding to roads, education, or health.

## Scope and caveat

This is a **gap analysis relative to the proposed platform**, not a comprehensive audit of every Indian public programme, state portal, or implementation outcome. The cited sources establish system functions, dataset availability, and data-governance/interoperability concerns. Where a row describes a missing end-to-end capability, that is an assessment from comparing those documented functions with the challenge requirements; it should be validated with the relevant agencies and state-level systems.

## Sources

- [CPGRAMS official portal](https://pgportal.gov.in/)
- [Open CPGRAMS datasets catalogue](https://www.data.gov.in/keywords/CPGRAMS)
- [CPGRAMS OGD access guide](https://event.data.gov.in/wp-content/uploads/2019/12/CPGRAMS_accessing_API_HelpGuide_User.pdf)
- [JJM dashboard](https://ejalshakti.gov.in/JJMreport/)
- [JJM Open Government Data catalogue](https://tn.data.gov.in/catalog/jal-jeevan-mission-jjm)
- [PMGSY Core Network](https://www.pmgsy.nic.in/core-network)
- [UDISE+ official portal](https://udiseplus.gov.in/)
- [UDISE+ 2023–24 report](https://www.education.gov.in/sites/upload_files/mhrd/files/statistics-new/udise_report_nep_23_24.pdf)
- [Health Dynamics of India 2022–23](https://www.mohfw.gov.in/sites/default/files/Health%20Dynamics%20of%20India%20%28Infrastructure%20%26%20Human%20Resources%29%202022-23_RE%20%281%29.pdf)
- [NITI Aayog Aspirational Districts Programme](https://www.niti.gov.in/aspirational-districts-programme)
- [Census of India tables](https://censusindia.gov.in/census.website/data/census-tables)
- [National Data Governance framework](https://www.negd.gov.in/ndg/ndg)
- [MeitY metadata and data standards](https://docs.apisetu.gov.in/document-central/mdds/Introduction.html)

## Additional research: gaps documented by audits and evaluations

The earlier sections identified gaps by comparing what existing portals publish with what the proposed platform needs. The following primary-source evaluations add concrete, bounded examples. Audit findings below are **specific to the audited state, time period, and sample**; they should not be generalized to every state or every project.

### Citizen grievance handling: closure can be mistaken for resolution

A Parliamentary Standing Committee reviewing public grievances noted that some departments closed cases by telling citizens to contact another agency or portal; it also observed that valid reasons for closure were not provided in many such cases. The Committee specifically described cases related to State governments where petitioners were told to approach the State and the grievance was disposed instead of being forwarded, leaving no redressal. This demonstrates a gap between **administrative disposal** and **verified resolution**.

**Implication:** a platform should track the citizen’s reported outcome and follow-up, not count a “closed” status alone as proof that the need was met. It should also surface recurring issues across agencies instead of simply routing each report in isolation.

Source: [Rajya Sabha Department-related Parliamentary Standing Committee report on grievances (PDF)](https://sansad.in/getFile/rsnew/Committee_site/Committee_File/ReportFile/18/164/111_2022_3_18.pdf?source=rajyasabha), especially paragraphs 2.6 and 2.12.

### Drinking water: infrastructure completion and functional service can diverge

The CAG’s **Kerala-specific** performance audit of Jal Jeevan Mission (Report No. 10 of 2025) found that, as of 15 March 2024, 72 schemes (13.46% of the schemes in the relevant audit table) had at least one critical component not awarded; the report concluded these schemes could not be made functional. The audit also reported water-test data gaps: WQMIS records lacked key sampling/report dates, sampling location, and remedial-action information, with test-result turnaround times of 33–45 days in test-checked districts. It further found that results were not shared with GPs, limiting community awareness of contaminated sources.

This is evidence for three separate planning risks: a household connection count may not establish a functioning end-to-end scheme; monitoring records may not carry the fields needed to act on a quality problem; and local communities may not receive the information needed to respond.

**Implication:** link connections to scheme components, operational status, service continuity, water-quality test metadata, remedial action, and village-level communication. Keep the audit’s state and period explicit when using its figures.

Sources: [CAG Kerala JJM audit landing page](https://cag.gov.in/ag2/gujarat/en/audit-report/details/123724) and [full report PDF](https://cag.gov.in/webroot/uploads/download_audit_report/2025/1.PA-on-JJM--English-0699d4ee1651af6.08263828.pdf). The report cover identifies Government of Kerala, Report No. 10 of 2025.

### Rural roads: maintenance and quality need to be tracked after construction

A CAG audit report for **Sikkim** states that joint physical inspection visited 21 of 34 sampled roads under maintenance; all inspected PMGSY roads completed during 2017–21 were found in dilapidated condition. Reported defects included damaged road surfaces, blocked drains and culverts, and slips/landslides. A separate Odisha audit (2012–17) found that contractors had not maintained 23 of 84 inspected completed roads; the report also recorded pending action on quality-monitor findings. These are state-specific samples, not a national failure rate, but they show why road length constructed is an incomplete measure of service.

**Implication:** connect road project records to maintenance responsibility, condition inspections, accessibility during monsoon/disasters, repair history, and community reports after handover.

Sources: [CAG audit report for Sikkim, year ended March 2023](https://cag.gov.in/uploads/download_audit_report/2025/Report-of-the-Comptroller-and-Auditor-General-of-India-on-Social%2C-Economic%2C-Revenue%2C-General-Sectors-and-Local-Bodies-for-the-year-ended-March-2023-%28Report-No.-3-of-2025%29-0693c04b885ca95.29034188.pdf); [CAG Odisha audit report, year ended March 2017](https://cag.gov.in/uploads/download_audit_report/2018/Chapter_2_Performance_Audit_of_Report_No_2_of_2018_-_General_and_Social_Sector_Government_of_Odisha.pdf).

### Schools: facility counts can miss functionality and maintenance

A Union CAG audit of school toilets constructed by central public-sector enterprises reported that, in the audit sample, 75% received a three-star or lower rating under the grading criteria used. The audit identified maintenance, dedicated funding, and water availability as issues. The report is historical and limited to its sampled schools; it is best used as evidence that an asset count is not a complete functionality measure, rather than as a current national estimate.

**Implication:** when identifying school infrastructure gaps, distinguish “facility exists” from “facility functional, accessible, supplied, and maintained.”

Source: [CAG Report No. 21 of 2019 on construction of toilets in schools](https://cag.gov.in/uploads/download_audit_report/2019/Report_No_21_of_2019_Construction_of_toilets_in_schools_by_CPSEs_Union_Government_Commercial.pdf).

### District monitoring: indicators and rankings need context

NITI Aayog’s published assessment of the Aspirational Districts Programme describes the use of 49 indicators/81 data points and a mix of district-entered and third-party-validated information. The UNDP appraisal notes that some data is uploaded by district officials while some indicators come from central ministries. The appraisal also reports that remote districts faced more difficulty implementing infrastructure projects than districts near highways or cities, and identifies scope to strengthen collaboration and technical support. A separate NITI-hosted assessment recommends peer-group comparisons and baseline studies, and notes that indicators already near saturation may show little incremental improvement.

These findings do not mean the programme lacks value: the appraisal also reports progress and describes data-driven monitoring and convergence as strengths. The design lesson is that a rank or delta score alone can conceal starting conditions, remoteness, indicator maturity, and differences in local implementation capacity.

**Implication:** show absolute service levels as well as change-over-time; compare like districts where appropriate; add remoteness/access costs and uncertainty; avoid rewarding only easy-to-improve indicators.

Sources: [NITI Aayog / UNDP appraisal of ADP](https://www.niti.gov.in/node/694) (published report text includes the appraisal’s data and remote-area observations); [NITI Aayog assessment of ADP](https://www.niti.gov.in/node/693).

### What this evidence changes in the platform gap analysis

These audits sharpen the earlier gap list:

- **Resolution quality:** case closure needs outcome confirmation and a valid-action trail.
- **Functionality:** count usable service, not only installed assets or completed works.
- **Maintenance:** include post-construction responsibility and condition over time.
- **Data quality:** store location, timestamps, completeness, source, verification, and remedial action for monitoring data.
- **Equity and comparability:** account for remoteness, starting baseline, and unequal reporting access when ranking.
- **Evidence scope:** preserve state, period, and sample metadata so local audit observations are not misrepresented as national prevalence.

## Research notes and evidence limits

- The CAG reports are strong sources for the issues found in their specific audit scope; they are not all-India prevalence studies.
- The ADP appraisal and assessment are valuable implementation/evaluation references, but findings are tied to the programme and evaluation period stated in each report.
- Current dashboard values and historical audit findings answer different questions. A dashboard may show current reported coverage; an audit can reveal weaknesses in verification, quality, maintenance, or implementation in a specific sample.
- Before using a finding to rank present-day districts, refresh the underlying data and verify whether the relevant deficiency has since been corrected.
