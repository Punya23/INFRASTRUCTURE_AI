# PRISM Datasets and Layers

## Purpose
Feeds
1. Geographic Foundation: The join key for everything (All graphs)
2. Citizen Demand: Raw citizen voice (Demand Graph)
3. Demographic & Socio-Economic: Population context (Demand + Outcome Graph)
4. Infrastructure & Public Investment: What's been funded/built (Intervention Graph)
5. Sector Data: Health, education, water, roads depth (Intervention + Outcome Graph)
6. Geospatial & Environmental: Physical change detection (Outcome Graph)
7. Derived / AI-Generated: PRISM's own outputs (All graphs)
8. AI & Language Rails: Multilingual + multimodal engines (Ingestion layer)

## Master Summary Table

| # | Dataset | Layer | Primary Use | Link |
|---|---|---|---|---|
| 1 | LGD — Local Government Directory | Geographic | Universal join key | [lgdirectory.gov.in](https://lgdirectory.gov.in/) |
| 2 | india-geodata (GitHub) | Geographic | Boundaries, GeoJSON layers | [github.com/yashveeeeeeer/india-geodata](https://github.com/yashveeeeeeer/india-geodata) |
| 3 | Census 2011 — Primary Census Abstract | Demographic | Population, literacy, SC/ST, workers | [data.gov.in PCA](https://www.data.gov.in/catalog/primary-census-abstract-2011-india-and-states-0) |
| 4 | Census 2011 — NADA Catalog | Demographic | Village/town amenities, DCHB | [censusindia.gov.in/nada](https://censusindia.gov.in/nada/index.php/catalog) |
| 5 | Dataful — Census 2011 Master | Demographic | Cleaned CSV/Parquet | [dataful.in/collections/42](https://dataful.in/collections/42/) |
| 6 | NFHS-5 District Factsheets | Demographic | Health, nutrition, sanitation | [rchiips.org/nfhs](http://rchiips.org/nfhs/districtfactsheet_NFHS-5.shtml) |
| 7 | NITI SDG India Index | Demographic | District SDG scores | [sdgindiaindex.niti.gov.in](https://sdgindiaindex.niti.gov.in/) |
| 8 | NITI Multidimensional Poverty Index | Demographic | Poverty weights for prioritization | [niti.gov.in SDG](https://www.niti.gov.in/divisions/division/sustainable-development-goal) |
| 9 | Mission Antyodaya | Infrastructure | Village-level infra gaps (6L villages) | [missionantyodaya.nic.in](https://missionantyodaya.nic.in/) |
| 10 | PCMC Grievance Data (2025) | Demand | City-level grievance format proxy | [data.gov.in PCMC](https://www.data.gov.in/resource/pcmc-grievance-data-during-2025) |
| 11 | CPGRAMS (DARPG) | Demand | National grievance reference | [darpg.gov.in](https://darpg.gov.in/) |
| 12 | MPLADS — 18th Lok Sabha work-wise | Investment | MP-funded projects, vendor, cost | [dataful.in/datasets/22565](https://dataful.in/datasets/22565/) |
| 13 | MPLADS — State/Constituency/MP-wise | Investment | Fund allocation & expenditure | [dataful.in/datasets/18542](https://dataful.in/datasets/18542/) |
| 14 | MPLADS — OpenCity 17th LS | Investment | Historical 2019–2024 CSV | [data.opencity.in](https://data.opencity.in/dataset/lok-sabha-mp-local-area-development-funds-details) |
| 15 | MPLADS — Empowered Indian | Investment | Dashboard + data | [empoweredindian.in/mplads](https://empoweredindian.in/mplads) |
| 16 | PMGSY — GeoSadak Open Data | Infrastructure | Rural roads GIS | [geosadak-pmgsy.nic.in/opendata](https://geosadak-pmgsy.nic.in/opendata) |
| 17 | PMGSY — OMMAS | Infrastructure | Facility & road datasets | [omms.nic.in](https://omms.nic.in/Home/PMGSYRuralDataset/) |
| 18 | PMGSY — Dataful district-wise | Infrastructure | Sanctioned/completed road length | [dataful.in/datasets/21251](https://dataful.in/datasets/21251/) |
| 19 | PMGSY — AI Kosh schema | Infrastructure | Schema & field reference | [aikosh.indiaai.gov.in](https://aikosh.indiaai.gov.in/home/datasets/details/pradhan_mantri_gram_sadak_yojna_pmgsy.html) |
| 20 | Jal Jeevan Mission (JJM) | Infrastructure | Tap-water connections, coverage | [ejalshakti.gov.in](https://ejalshakti.gov.in/) |
| 21 | Swachh Bharat Mission (Gramin) | Infrastructure | IHHL, CSC construction | [data.gov.in](https://artefacts.data.gov.in/) |
| 22 | MGNREGA Public Data | Infrastructure | Rural assets, employment | [nreganarep.nic.in](https://nreganarep.nic.in/netnrega/MISreport4.aspx) |
| 23 | PMAY (Urban + Rural) | Infrastructure | Housing sanctions/completions | [data.gov.in](https://artefacts.data.gov.in/) |
| 24 | Government Project Registry | Investment | Project ID, budget, status | [data.gov.in](https://www.data.gov.in/) |
| 25 | PM GatiShakti | Investment | National infra planning | [pmgatishakti.gov.in](https://pmgatishakti.gov.in/) |
| 26 | Infrastructure Sector Catalog | Investment | Transport, power, water | [data.gov.in/sector/Infrastructure](https://www.data.gov.in/sector/Infrastructure) |
| 27 | MoSPI Compendium of Datasets 2024 | Reference | Master catalog of Indian data | [mospi.gov.in](https://www.mospi.gov.in/uploads/documents/documents/1758028143436-Compendium_of_Datasets_and_Registries_in_India_2024_0.pdf) |
| 28 | HMIS | Health | Facility-level service delivery | [hmis.mohfw.gov.in](https://hmis.mohfw.gov.in/) |
| 29 | Health Facility Registry (ABDM) | Health | PHC/CHC/hospital inventory | [facility.ndhm.gov.in](https://facility.ndhm.gov.in/) |
| 30 | UDISE+ Portal | Education | School infra, enrolment, PTR | [udiseplus.gov.in](https://udiseplus.gov.in/) |
| 31 | UDISE+ Dashboard | Education | Live dashboards | [dashboard.udiseplus.gov.in](https://dashboard.udiseplus.gov.in/) |
| 32 | UDISE+ State/UT Highlights 2023–24 | Education | Aggregated stats | [data.gov.in UDISE](https://www.data.gov.in/resource/stateuts-wise-details-schools-enrolments-and-teachers-highlights-udise-data-during-2023-24) |
| 33 | UDISE+ Enrolment Catalog | Education | Social category splits | [data.gov.in UDISE catalog](https://www.data.gov.in/catalog/enrolment-location-school-management-school-category-and-social-category-udise-plus) |
| 34 | OpenCity UDISE+ district CSVs | Education | Bengaluru, Delhi, Hyderabad | [data.opencity.in Education](https://data.opencity.in/dataset/?res_format=CSV&tags=Education) |
| 35 | Bhuvan (ISRO) | Geospatial | Land use, water bodies, flood hazard | [bhuvan.nrsc.gov.in](https://bhuvan.nrsc.gov.in/) |
| 36 | Bhuvan Thematic Data | Geospatial | Erosion, wasteland, geomorphology | [bhuvan thematic](https://bhuvan.nrsc.gov.in/bhuvan_links.php) |
| 37 | Google Earth Engine | Geospatial | Satellite change detection | [earthengine.google.com](https://earthengine.google.com/) |
| 38 | Bhashini APIs | AI Rails | Indian language ASR/TTS/translation | [bhashini.gitbook.io](https://dibd-bhashini.gitbook.io/) |
| 39 | Google Gemini | AI Rails | Multimodal reasoning | [aistudio.google.com](https://aistudio.google.com/) |

## Layer 1 — Geographic Foundation
This is the spine of PRISM. Every other dataset joins to it via LGD codes.

**1. LGD — Local Government Directory**
* **Link:** [https://lgdirectory.gov.in/](https://lgdirectory.gov.in/)
* **What it is:** The Government of India's official registry of every state, district, sub-district (tehsil/block), village, urban local body, and panchayat — each with a unique LGD code and PIN code mapping.
* **How PRISM uses it:** LGD is the universal join key. A citizen complaint from Muzaffarpur arrives with a PIN code or village name — we map it to an LGD code. A PMGSY road project has an LGD district code. Census data has LGD codes. UDISE+ has LGD codes. Without LGD, none of these datasets can be joined. This is the single most important dataset in the entire project.

**2. india-geodata (GitHub)**
* **Link:** [https://github.com/yashveeeeeeer/india-geodata](https://github.com/yashveeeeeeer/india-geodata)
* **What it is:** Community-maintained repository of India's administrative boundaries — district polygons, census geometries, roads, health facilities, education layers — all in GeoJSON and Parquet formats.
* **How PRISM uses it:** Provides the spatial polygons for the Collector dashboard and MP constituency view. When we visualize a demand hotspot in Ward 14, we need the ward polygon. When we show infrastructure exposure, we need district boundaries. This repo gives us all of it ready-to-use.

## Layer 2 — Citizen Demand
This is the raw input to the Demand Graph. You will generate most of this yourself.

**3. PCMC Grievance Data (2025)**
* **Link:** [https://www.data.gov.in/resource/pcmc-grievance-data-during-2025](https://www.data.gov.in/resource/pcmc-grievance-data-during-2025)
* **What it is:** Real grievance data from Pimpri-Chinchwad Municipal Corporation — complaint text, category, location, timestamp, resolution status.
* **How PRISM uses it:** Serves as the format reference for how Indian municipal grievance data actually looks. When you build the synthetic citizen request generator, you mirror this schema. It also gives you real category taxonomy (road, water, light, drainage, health, school) to train your intent classifier.

**4. CPGRAMS (DARPG)**
* **Link:** [https://darpg.gov.in/](https://darpg.gov.in/)
* **What it is:** India's national grievance redressal system. Public API is restricted, but aggregate reports and scheme-wise grievance data are published.
* **How PRISM uses it:** Reference for national-scale grievance patterns — what categories dominate, how they vary by state, seasonal patterns. Useful for calibrating your synthetic data generator so it produces realistic demand distributions.

**5. Citizen Requests (You Create This)**
* **What it is:** The primary input dataset. Fields: complaint text (original language), language code, location (LGD code), category, severity, duration, affected population, source channel (IVR/WhatsApp/SMS/photo), timestamp, citizen ID (Aadhaar-hashed).
* **How PRISM uses it:** This is the Demand Graph's raw material. Every downstream insight — root cause, hotspot, priority — derives from this dataset. In the hackathon, you simulate it; in production, it flows in live from WhatsApp, IVR, SMS, and the citizen app.

**6. Demand Clusters (AI-Derived)**
* **What it is:** Gemini-clustered groups of semantically similar requests. Fields: cluster ID, location, sector, request count, unique citizens, average severity, trend (rising/falling), language distribution.
* **How PRISM uses it:** Raw complaints are noise. Clusters are signal. A Collector doesn't need to read 4,200 complaints — they need to see 47 demand clusters ranked by severity. This dataset is the first derived output of the ingestion pipeline.

## Layer 3 — Demographic & Socio-Economic
Provides population context. Without this, you can't tell if 100 complaints in a ward is a lot or a little.

**7. Census 2011 — Primary Census Abstract**
* **Links:**
[https://www.data.gov.in/catalog/primary-census-abstract-2011-india-and-states-0](https://www.data.gov.in/catalog/primary-census-abstract-2011-india-and-states-0)
[https://www.data.gov.in/resource/primary-census-abstract-2011-india](https://www.data.gov.in/resource/primary-census-abstract-2011-india)
* **What it is:** The foundational Indian demographic dataset. Households, total population, age 0–6, SC/ST population, literacy, illiteracy, workers, cultivators, agricultural labourers — at state, district, and sub-district level.
* **How PRISM uses it:** Normalizes demand. 50 complaints in a ward of 5,000 people is a crisis. 50 complaints in a ward of 50,000 is normal. Census gives us the denominator for every demand signal. It also gives us SC/ST share and literacy for equity constraints in the optimizer — we can ensure projects aren't systematically biased toward literate or upper-caste neighborhoods.

**8. Census 2011 — NADA Catalog**
* **Link:** [https://censusindia.gov.in/nada/index.php/catalog](https://censusindia.gov.in/nada/index.php/catalog)
* **What it is:** Detailed census tables including District Census Handbooks (DCHB) and village/town amenity data — which villages have electricity, tap water, drainage, etc.
* **How PRISM uses it:** Village-level amenity data tells us the baseline infrastructure state. If a village already has tap water per Census 2011 but citizens are complaining about water, something broke. This is essential for the Outcome Graph.

**9. Dataful — Census 2011 Master Collection**
* **Link:** [https://dataful.in/collections/42/](https://dataful.in/collections/42/)
* **What it is:** Cleaned, analysis-ready Census 2011 data in CSV and Parquet formats.
* **How PRISM uses it:** Saves weeks of data cleaning. Load directly into BigQuery. This is your primary Census source for the hackathon.

**10. NFHS-5 District Factsheets**
* **Link:** [http://rchiips.org/nfhs/districtfactsheet_NFHS-5.shtml](http://rchiips.org/nfhs/districtfactsheet_NFHS-5.shtml)
* **What it is:** National Family Health Survey round 5 — district-level data on health, nutrition, sanitation, women's empowerment, child mortality.
* **How PRISM uses it:** Links infrastructure gaps to health outcomes. If a district has poor sanitation (NFHS-5) and high citizen complaints about drainage (Demand Graph), that's a causal chain worth surfacing. Also provides outcome metrics for the Attribution Engine.

**11. NITI SDG India Index**
* **Link:** [https://sdgindiaindex.niti.gov.in/](https://sdgindiaindex.niti.gov.in/)
* **What it is:** District and state-level scores across all 17 SDGs.
* **How PRISM uses it:** Provides a development gap proxy. Districts with low SDG scores get higher priority weight in the optimizer. Also gives policymakers a familiar frame — "this project improves SDG 6 (water) and SDG 11 (cities)."

**12. NITI Multidimensional Poverty Index**
* **Link:** [https://www.niti.gov.in/divisions/division/sustainable-development-goal](https://www.niti.gov.in/divisions/division/sustainable-development-goal)
* **What it is:** National MPI measuring poverty across health, education, and standard of living dimensions.
* **How PRISM uses it:** Weights demand hotspots by poverty intensity. A water complaint in a high-MPI district carries more weight than the same complaint in a low-MPI district. This is a core equity constraint.

**13. Mission Antyodaya**
* **Link:** [https://missionantyodaya.nic.in/](https://missionantyodaya.nic.in/)
* **What it is:** A comprehensive survey of village-level infrastructure and socio-economic indicators for nearly 600,000 villages — covering 200+ parameters.
* **How PRISM uses it:** This is the single richest village-level infrastructure dataset in India. It gives us baseline for every village — roads, water, electricity, schools, health facilities. When a citizen complains, we cross-reference with Mission Antyodaya to see if the gap already exists in official data or is a new failure.

## Layer 4 — Infrastructure & Public Investment
The Intervention Graph. This shows what's already been funded, so we don't double-allocate or miss gaps.

**14. MPLADS — 18th Lok Sabha Work-wise**
* **Link:** [https://dataful.in/datasets/22565/](https://dataful.in/datasets/22565/)
* **What it is:** Work-level data on every MPLADS-funded project in the 18th Lok Sabha — work name, constituency, vendor, amount, status.
* **How PRISM uses it:** This is the primary Intervention Graph input. When a citizen requests a road, we check: has the MP already sanctioned a road project here? If yes, when? If no, why not? If a different sector, we show the tradeoff. This dataset turns PRISM from a complaint box into a budget alignment engine.

**15. MPLADS — State/Constituency/MP-wise**
* **Link:** [https://dataful.in/datasets/18542/](https://dataful.in/datasets/18542/)
* **What it is:** Aggregated MPLADS fund allocation and expenditure by state, constituency, and MP.
* **How PRISM uses it:** Shows spending patterns. If an MP has spent 80% of MPLADS on roads but citizens are complaining about water, that's a misalignment signal. This is exactly the kind of insight that makes a policymaker sit up.

**16. MPLADS — OpenCity 17th Lok Sabha**
* **Link:** [https://data.opencity.in/dataset/lok-sabha-mp-local-area-development-funds-details](https://data.opencity.in/dataset/lok-sabha-mp-local-area-development-funds-details)
* **What it is:** Historical MPLADS data for 2019–2024 in CSV format.
* **How PRISM uses it:** Backtesting. Did MPLADS projects in a district actually reduce citizen complaints in that sector? This is your attribution ground truth for the past 5 years.

**17. MPLADS — Empowered Indian**
* **Link:** [https://empoweredindian.in/mplads](https://empoweredindian.in/mplads)
* **What it is:** Dashboard and processed MPLADS data.
* **How PRISM uses it:** Cross-validation and alternative view of the same data. Useful when Dataful has gaps.

**18. Government Project Registry**
* **Link:** [https://www.data.gov.in/](https://www.data.gov.in/)
* **What it is:** Registry of government projects with project ID, name, sector, location, agency, budget, start date, completion date, status, beneficiaries.
* **How PRISM uses it:** Extends the Intervention Graph beyond MPLADS to all government projects — central, state, and local. This is what makes PRISM a national-scale platform, not just an MP tool.

**19. PM GatiShakti**
* **Link:** [https://pmgatishakti.gov.in/](https://pmgatishakti.gov.in/)
* **What it is:** India's national master planning platform for multimodal infrastructure — integrating 16 ministries' data on roads, rail, ports, waterways, and more.
* **How PRISM uses it:** Provides the national infrastructure planning context. If PM GatiShakti already has a highway planned for a corridor, PRISM shouldn't recommend a parallel road. Conversely, PRISM's citizen demand signals can feed into GatiShakti's planning process — this is a genuinely valuable bidirectional integration.

**20. Infrastructure Sector Catalog**
* **Link:** [https://www.data.gov.in/sector/Infrastructure](https://www.data.gov.in/sector/Infrastructure)
* **What it is:** Aggregated catalog of all infrastructure datasets on [data.gov.in](https://data.gov.in/) — transport, power, water, telecom, etc.
* **How PRISM uses it:** Extension catalog. As PRISM scales beyond roads/water/health/education, this is where you find datasets for power, telecom, and other sectors. For the hackathon, note it as your scaling path.

**21. MoSPI Compendium of Datasets 2024**
* **Link:** [https://www.mospi.gov.in/uploads/documents/documents/1758028143436-Compendium_of_Datasets_and_Registries_in_India_2024_0.pdf](https://www.mospi.gov.in/uploads/documents/documents/1758028143436-Compendium_of_Datasets_and_Registries_in_India_2024_0.pdf)
* **What it is:** Government of India's official master catalog of all datasets and registries available in India.
* **How PRISM uses it:** Reference document. When a judge asks "how will you scale this to all of India?" — this is your answer. Every dataset you'd ever need is listed here with its custodian ministry.

## Layer 5 — Sector Data (Health, Education, Water, Roads)
Depth data for specific sectors in the Intervention and Outcome Graphs.

**22. HMIS — Health Management Information System**
* **Link:** [https://hmis.mohfw.gov.in/](https://hmis.mohfw.gov.in/)
* **What it is:** Monthly data from over 200,000 health facilities on service delivery — OPD, IPD, deliveries, C-sections, immunisation, and other health indicators.
* **How PRISM uses it:** When citizens complain about health services, HMIS tells us the actual service load. If a PHC is seeing 300 OPD patients/day when designed for 100, that's a capacity gap. This links Demand Graph (citizen complaints) to Outcome Graph (health indicators).

**23. Health Facility Registry (ABDM)**
* **Link:** [https://facility.ndhm.gov.in/](https://facility.ndhm.gov.in/)
* **What it is:** Official registry of all public and private health facilities in India under the Ayushman Bharat Digital Mission.
* **How PRISM uses it:** Counts PHCs, CHCs, and hospitals per district. When a citizen requests a new sub-centre, we check the HFR to see what exists. This prevents duplicate recommendations and identifies true gaps.

**24. UDISE+ Portal**
* **Link:** [https://udiseplus.gov.in/](https://udiseplus.gov.in/)
* **Dashboard:** [https://dashboard.udiseplus.gov.in/](https://dashboard.udiseplus.gov.in/)
* **What it is:** Unified District Information System for Education — school-level data on infrastructure (classrooms, toilets, libraries, electricity, computers, internet, ramps, playgrounds), enrolment, teachers, PTR, dropout.
* **How PRISM uses it:** Education infrastructure baseline. Every school request from a citizen is checked against UDISE+. A school without girls' toilets is a specific, measurable gap — UDISE+ tells us exactly which schools have this gap.

**25. UDISE+ State/UT Highlights 2023–24**
* **Link:** [https://www.data.gov.in/resource/stateuts-wise-details-schools-enrolments-and-teachers-highlights-udise-data-during-2023-24](https://www.data.gov.in/resource/stateuts-wise-details-schools-enrolments-and-teachers-highlights-udise-data-during-2023-24)
* **What it is:** Aggregated UDISE+ statistics by state and UT.
* **How PRISM uses it:** State-level comparison for the national dashboard view. Shows which states have the biggest education infrastructure gaps.

**26. UDISE+ Enrolment Catalog**
* **Link:** [https://www.data.gov.in/catalog/enrolment-location-school-management-school-category-and-social-category-udise-plus](https://www.data.gov.in/catalog/enrolment-location-school-management-school-category-and-social-category-udise-plus)
* **What it is:** Enrolment data split by location (rural/urban), school management, school category, and social category.
* **How PRISM uses it:** Equity analysis. Are SC/ST students enrolled in schools with worse infrastructure? This feeds directly into the fairness audit and the optimizer's equity constraints.

**27. OpenCity UDISE+ District CSVs**
* **Link:** [https://data.opencity.in/dataset/?res_format=CSV&tags=Education](https://data.opencity.in/dataset/?res_format=CSV&tags=Education)
* **What it is:** Cleaned UDISE+ district datasets for specific cities (Bengaluru, Delhi, Hyderabad).
* **How PRISM uses it:** Ready-to-use education data for urban pilots. Useful if you decide to pilot in a metro instead of a rural Aspirational District.

**28. PMGSY — GeoSadak Open Data**
* **Link:** [https://geosadak-pmgsy.nic.in/opendata](https://geosadak-pmgsy.nic.in/opendata)
* **What it is:** GIS data for all PMGSY rural roads — roads, habitations, facilities.
* **How PRISM uses it:** Road connectivity baseline. When a citizen requests a road, we check: is this habitation already connected per PMGSY? If yes, why are citizens still complaining (road quality? last-mile?)? If no, is it planned? This is the road layer of the Intervention Graph.

**29. PMGSY — OMMAS**
* **Link:** [https://omms.nic.in/Home/PMGSYRuralDataset/](https://omms.nic.in/Home/PMGSYRuralDataset/)
* **What it is:** Online Management, Monitoring and Accounting System for PMGSY — facility details and road datasets.
* **How PRISM uses it:** Project-level detail on PMGSY roads — sanctioned, completed, expenditure, status. Essential for attribution: did the road actually get built? Did it reduce complaints?

**30. PMGSY — Dataful District-wise**
* **Link:** [https://dataful.in/datasets/21251/](https://dataful.in/datasets/21251/)
* **What it is:** District-wise sanctioned and completed road length under PMGSY.
* **How PRISM uses it:** District-level road gap analysis. Compare sanctioned vs completed to identify districts where PMGSY delivery is lagging.

**31. PMGSY — AI Kosh Schema**
* **Link:** [https://aikosh.indiaai.gov.in/home/datasets/details/pradhan_mantri_gram_sadak_yojna_pmgsy.html](https://aikosh.indiaai.gov.in/home/datasets/details/pradhan_mantri_gram_sadak_yojna_pmgsy.html)
* **What it is:** Schema and field description for PMGSY datasets.
* **How PRISM uses it:** Data dictionary. Use this to understand field names and types before ingesting into BigQuery.

**32. Jal Jeevan Mission (JJM)**
* **Link:** [https://ejalshakti.gov.in/](https://ejalshakti.gov.in/)
* **What it is:** Data on rural household tap water connections — villages, households, coverage, functional connections, water-supply schemes, and status.
* **How PRISM uses it:** Water infrastructure baseline. This is one of the highest-impact datasets for PRISM because water complaints dominate Indian grievance data. JJM tells us which villages have tap water and which don't. When a citizen complains about water, we check JJM status first.

**33. Swachh Bharat Mission (Gramin)**
* **Link:** [https://artefacts.data.gov.in/](https://artefacts.data.gov.in/)
* **What it is:** Data on construction of Individual Household Latrines (IHHLs) and Community Sanitary Complexes.
* **How PRISM uses it:** Sanitation baseline. Links to NFHS-5 health outcomes. If a district has high open defecation (NFHS-5) and SBM shows low IHHL coverage, that's a clear priority.

**34. MGNREGA Public Data Portal**
* **Link:** [https://nreganarep.nic.in/netnrega/MISreport4.aspx](https://nreganarep.nic.in/netnrega/MISreport4.aspx)
* **What it is:** Data on rural employment and creation of durable assets — water conservation, rural roads, land development.
* **How PRISM uses it:** Asset creation baseline. MGNREGA creates water conservation structures, check dams, ponds — exactly the kind of recharge infrastructure PRISM might recommend. This prevents duplicate recommendations and shows what's already been built.

**35. PMAY (Urban + Rural)**
* **Link:** [https://artefacts.data.gov.in/](https://artefacts.data.gov.in/)
* **What it is:** Pradhan Mantri Awas Yojana housing data — sanctions and completions for both urban and rural.
* **How PRISM uses it:** Housing baseline. When citizens request housing, PMAY tells us what's already sanctioned. Links to Outcome Graph via housing quality indicators.

## Layer 6 — Geospatial & Environmental
Physical change detection. Independent verification of whether projects actually happened.

**36. Bhuvan (ISRO)**
* **Link:** [https://bhuvan.nrsc.gov.in/](https://bhuvan.nrsc.gov.in/)
* **What it is:** ISRO's geoportal — land use, water bodies, flood hazard, waterlogging, urban sprawl, erosion, wasteland, geomorphology.
* **How PRISM uses it:** Environmental context layer. Flood hazard maps determine which water/drainage complaints are urgent. Urban sprawl tells us where demand will grow. Wasteland maps identify potential sites for new infrastructure.

**37. Bhuvan Thematic Data**
* **Link:** [https://bhuvan.nrsc.gov.in/bhuvan_links.php](https://bhuvan.nrsc.gov.in/bhuvan_links.php)
* **What it is:** Thematic layers within Bhuvan — erosion, wasteland, geomorphology, and more.
* **How PRISM uses it:** Specialized environmental analysis. Erosion data links to agriculture complaints. Geomorphology links to water recharge potential. Wasteland links to land availability for projects.

**38. Google Earth Engine (GEE)**
* **Link:** [https://earthengine.google.com/](https://earthengine.google.com/)
* **What it is:** Google's planetary-scale satellite imagery and geospatial analysis platform.
* **How PRISM uses it:** Independent change detection. After a PMGSY road is claimed complete, GEE can verify the road actually exists. After a JJM water scheme, GEE can detect new water bodies or recharge structures. After a PMAY housing project, GEE can detect new built-up area. This is the Outcome Graph's verification engine — it doesn't trust government claims, it verifies them.
*GEE is also a Google hackathon requirement — using it deeply is a competitive advantage.*

## Layer 7 — Derived / AI-Generated
PRISM's own outputs. These are what make it a decision engine, not a portal.

**39. Demand Clusters (see #6)**
*Already covered above.*

**40. Infrastructure Gap Signal**
* **What it is:** Per location and sector: demand score, infrastructure score, population score, accessibility score, trend, existing-project score, final gap signal.
* **How PRISM uses it:** The core prioritization output. This is the number that tells a Collector: "Ward 14 water = gap score 87/100 — highest priority." It combines demand (citizen complaints), supply (infrastructure data), context (population, poverty), and constraint (existing projects).

**41. Evidence Package**
* **What it is:** For every recommendation — citizen requests + population + infrastructure coverage + project status + source/date/confidence.
* **How PRISM uses it:** Explainability. When PRISM says "build a recharge structure in Ward 14," the Evidence Package shows exactly why: 47 complaints, 4,200 affected, no JJM coverage, groundwater -4.2m, no existing project. This is what makes the recommendation defensible to a policymaker and auditable to a citizen.

**42. Impact Assessment**
* **What it is:** Before/after requests, severity, accessibility, beneficiaries, intervention, impact measurement.
* **How PRISM uses it:** Closes the loop. 18 months after a project, PRISM measures: did complaints drop? Did severity decrease? Did accessibility improve? Did beneficiaries get served? This is the attribution output — the thing no existing system does.

## Layer 8 — AI & Language Rails
The engines that make PRISM multilingual and multimodal.

**43. Bhashini APIs**
* **Link:** [https://dibd-bhashini.gitbook.io/](https://dibd-bhashini.gitbook.io/)
* **What it is:** Government of India's AI platform for Indian language ASR, TTS, and translation — covering 22+ scheduled languages.
* **How PRISM uses it:** Primary language engine for Indian languages. A Bhojpuri voice complaint → Bhashini ASR → Hindi text → Bhashini translation → English for processing. Response back to citizen in Bhojpuri via Bhashini TTS. Using Bhashini instead of only Gemini is the India-first signal— it shows you're building on Indian DPI, not just American AI.

**44. Google Gemini**
* **Link:** [https://aistudio.google.com/](https://aistudio.google.com/)
* **What it is:** Google's multimodal AI model — text, image, audio, video reasoning.
* **How PRISM uses it:**
    * Intent extraction — what is the citizen actually asking for?
    * Entity resolution — which ward, which road, which school?
    * Multimodal analysis — photo of a pothole → defect classification
    * Astroturf detection — coordinated burst, template similarity
    * Natural-language policy explanations — "here's why this project matters, in plain language"
    * Counterfactual reasoning — "what if we funded X instead of Y?"
*Gemini is the reasoning brain. Bhashini is the language bridge. Together they make PRISM genuinely multilingual and genuinely Indian.*

## How They All Connect — The Join Architecture

```text
LGD code (universal key)
│
├── Census 2011 ──────────── population, literacy, SC/ST
├── NFHS-5 ───────────────── health, sanitation outcomes
├── NITI SDG + MPI ───────── development gap weights
├── Mission Antyodaya ────── village infra baseline
├── MPLADS ───────────────── MP-funded projects
├── PMGSY ────────────────── rural roads
├── JJM ──────────────────── rural water
├── SBM ──────────────────── sanitation
├── MGNREGA ──────────────── rural assets
├── PMAY ─────────────────── housing
├── HMIS + HFR ───────────── health facilities
├── UDISE+ ───────────────── schools
├── Bhuvan + GEE ─────────── physical verification
│
↓
DEVELOPMENT IMPACT GRAPH
├── Demand Graph ← Citizen Requests + Demand Clusters
├── Intervention Graph ← MPLADS + PMGSY + JJM + SBM + PMAY + Registry
└── Outcome Graph ← HMIS + UDISE+ + NFHS-5 + GEE + Citizen Loop
↓
COUNTERFACTUAL SIMULATOR
→ OR-Tools optimizer
→ Ranked portfolio
↓
ATTRIBUTION ENGINE
→ Impact Assessment
→ Evidence Package
↓
DELIVERY: Collector dashboard · MP view · Citizen WhatsApp loop.
```
