# How to Write a Scientific Paper — Conventions for Spain
## Field focus: Chemical / Thermal Engineering (absorption refrigeration, CO₂ capture, biobased / ionic-liquid & deep-eutectic-solvent research)

*Last updated: 2026-06-05. This guide combines the international IMRaD standard with the specific bibliographic, doctoral, and language conventions used in Spain, and with the house styles of the target journals in this field (Elsevier, IIR, ASME, ASHRAE). All factual claims are cited with URLs at the end.*

---

## 0. Quick orientation

- **In this field, write in English.** Spanish thermal/chemical-engineering research is published almost exclusively in English in indexed (JCR/Scopus) journals, because the Spanish research-evaluation system (ANECA sexenios and accreditation) rewards high-impact international visibility. Spanish is used mainly for the thesis "front matter" (introduction, summary, conclusions) when required by the university, and for outreach/teaching. See §2.3.
- **Structure every original paper as IMRaD** (Introduction, Methods, Results and Discussion) plus Title, Abstract, Keywords, Highlights, Nomenclature, Conclusions, References, and the mandatory declarations (CRediT, data availability, competing interests, funding). See §1.
- **Citations: two parallel worlds.** International journals in this field use a *numbered* style — Elsevier's "elsarticle-num" (Vancouver-type) for IJR / Applied Thermal Engineering / Energy etc. Spanish institutional documents (theses front matter, official reports, undergraduate/master TFG–TFM) often require **UNE-ISO 690**, the Spanish national citation standard (2024 version now in force). See §2.1 and §3.
- **Units: strict SI**, italic variables, roman subscripts, equations numbered on the right. See §3.

---

## 1. The IMRaD structure, section by section

IMRaD (Introduction, Methods, Results, and Discussion) is the dominant structure for original research articles in STEM and engineering; most journals expect it. Each section has one job — do not mix them (e.g. never interpret data inside Results).

### 1.1 Title
- **Purpose:** be found and be understood in one line. It is the most-read part of the paper.
- **Best practice:**
  - Specific and informative; include the working pair / system and the key result or method. *Good:* "Vapour–liquid equilibrium and absorption performance of a CO₂ + biobased deep-eutectic-solvent working pair for absorption refrigeration." *Weak:* "A study of a new refrigeration cycle."
  - 10–15 words; avoid "Study of…", "Investigation into…", non-standard abbreviations, and question marks unless deliberate.
  - Put the most distinctive term early (keyword loading for search).

### 1.2 Abstract
- **Purpose:** a self-contained miniature of the whole paper; often the only part read.
- **Best practice:**
  - Typically **150–250 words**, unstructured single paragraph for Elsevier journals (some allow structured abstracts — check the specific Guide for Authors).
  - Follow the IMRaD arc in miniature: context/objective → method → key *quantitative* results → conclusion/implication. Include numbers (e.g. "COP increased from 0.71 to 0.78"; "CO₂ uptake of 0.14 g g⁻¹ at 313 K, 100 kPa").
  - No citations, no undefined abbreviations, no figures/tables, written in past tense for what was done.

### 1.3 Keywords / Highlights
- **Keywords:** usually 4–6 terms, not repeating the title verbatim, chosen for indexing (e.g. *Absorption refrigeration; Deep eutectic solvent; CO₂; Vapour–liquid equilibrium; Coefficient of performance*).
- **Highlights (Elsevier requirement):** exactly **3–5 bullet points, each ≤ 85 characters including spaces**, capturing the novel results — not methods. They appear in search results and must stand alone.

### 1.4 Introduction
- **Purpose:** justify *why* the work matters and state precisely *what* you did.
- **Best practice (the "funnel" / CARS move):**
  1. Establish the territory (the problem/context: e.g. need for low-GWP, energy-efficient cooling).
  2. Establish a niche — review current state and reveal the **gap** (what is unknown/unresolved).
  3. Occupy the niche — state objective, scope, novelty, and a brief roadmap of the paper.
- The **literature review lives here** (or in a short separate "State of the art" section), critically synthesised, not a list. End with an explicit objective sentence: "The aim of this work is to…".

### 1.5 Materials and Methods (Experimental / Modelling)
- **Purpose:** enough detail for an independent group to **reproduce** the work. This is the reproducibility section.
- **Best practice:**
  - Chemicals: supplier, CAS number, purity, water content, drying/handling. Equipment: model, manufacturer, calibration, **measurement uncertainties** (essential for thermophysical-property and equilibrium work).
  - Procedures step-by-step; experimental conditions (T, p, composition ranges).
  - Models: governing equations, equation-of-state / activity-coefficient model (e.g. PC-SAFT, NRTL, UNIFAC), thermodynamic assumptions, solver, convergence criteria, software and versions.
  - State the **uncertainty / error propagation** method explicitly. Past tense, passive or "we" both acceptable.

### 1.6 Results
- **Purpose:** present findings objectively — *what was found*, not *what it means*.
- **Best practice:** lead with the data via well-designed figures and tables (do not duplicate data in both); report values with uncertainties and significant figures consistent with precision; use past tense. Reserve interpretation for the Discussion.

### 1.7 Discussion
- **Purpose:** interpret results, relate them to the literature and to the gap stated in the Introduction.
- **Best practice:** explain mechanisms; compare quantitatively with prior work; account for unexpected results; state **limitations** honestly; give implications for design/practice. Strong papers may merge "Results and Discussion" — common in this field — but keep description and interpretation distinguishable.

### 1.8 Conclusions
- **Purpose:** the take-home messages, tightly tied to the objectives.
- **Best practice:** short, numbered or bulleted, quantitative, no new data or citations; end with concrete future-work directions. Do not merely repeat the abstract.

### 1.9 Nomenclature
- **Purpose:** define every symbol once.
- **Best practice:** a dedicated table, usually split into Latin symbols, Greek symbols, Subscripts/Superscripts, and Abbreviations/Acronyms; give SI units. Variables italic, units and subscripts roman (e.g. *T* in K, *h*<sub>fg</sub>). Required by IIR and standard in ATE/Energy.

### 1.10 References
- Numbered, in citation order, in the journal's house style (see §3 and §2.1). Every in-text number must have a list entry and vice versa.

### 1.11 Back-matter declarations (now effectively mandatory)
- **CRediT author statement** — see §4.3.
- **Declaration of competing interest** (state "none" if none).
- **Funding** statement (grant agency + grant number; e.g. "Funded by MICIU/AEI grant PIDxxxx").
- **Acknowledgements** — non-author help, facilities, language editing. Keep separate from Funding.
- **Data availability statement** — where the data are (repository + DOI/accession, or a stated reason if not shared). Mandated by ICMJE and adopted by virtually all international journals.

---

## 2. Conventions specific to Spain

### 2.1 UNE-ISO 690 — the Spanish bibliographic standard

UNE-ISO 690 is the Spanish national adaptation (by UNE/AENOR) of the international ISO 690. **The 2013 version (UNE-ISO 690:2013) has been replaced by UNE-ISO 690:2024**, which is equivalent to ISO 690:2021 and is the version Spanish universities now reference. Use it for thesis front-matter, TFG/TFM, and official documents when your university mandates it.

**Key features of the standard:**
- It is **style-agnostic about layout but defines the elements and order**; it supports three citation systems: (a) **numeric**, (b) **author–date** (Harvard), and (c) **running notes / footnotes**.
- **2024 changes vs 2013:** much more detailed; **place of publication is now optional**; **author identifiers (ORCID, ISNI)** may be added in parentheses after the author; clearer treatment of medium/content type; the thesis director/advisor is **no longer a mandatory field**.

**Worked examples (UNE-ISO 690, author–date system):**

- **Book:** `MANKIW, N. Gregory, 2014. Macroeconomía. 4ª ed. Barcelona: Antoni Bosch. ISBN 9788495348944.` → in text: *(Mankiw 2014)*.
- **Journal article:** `ESCAPA, Sandra, 2017. Los efectos del conflicto parental… Revista Española de Investigaciones Sociológicas [en línea]. No. 158, pp. 41-58 [consulta: abril de 2018]. ISSN 0210-5233.` → *(Escapa 2017)*.
- **Book chapter:** `ALARCÓN DEL AMO, M.ª C., 2013. El Plan de Marketing. En: ESTEBAN TALAYA, Á. y LORENZO ROMERO, C., coord. Dirección comercial. Madrid: ESIC, pp. 13-30. ISBN 9788473569538.`
- **Thesis:** `LANDAETA OLIVO, J. F., 2016. Marco de referencia… [en línea]. Tesis doctoral. Universidad Carlos III de Madrid. Disponible en: http://hdl.handle.net/10016/23113.`
- **Conference paper:** `ALONSO MAGDALENO, M.ª L. y GARCÍA GARCÍA, J., 2015. Transparencia en la administración pública… En: Actas XIV Jornadas FESABID'15. Madrid: FESABID, pp. 41-58.`
- **Web page:** `AYUSO, Bárbara, 2018. El talento en tiempos del coaching. En: Jot Down [en línea]. Disponible en: https://… [consulta: 12 enero 2019].`

**Worked examples (UNE-ISO 690, numeric system):**

- In text the number is inserted as `(1)`, `[1]` or superscript ¹; consecutive sources as `(2,3)` or `(4-7)`; with page for quotes `(1, p. 23)`.
- The reference list is ordered **by order of appearance**, not alphabetically.
- **Book:** `APELLIDOS, N. Título. Edición. Lugar: Editor, año. ISBN.` e.g. `AGUDO, S. y PONS, A. Mejorar las búsquedas de información. Barcelona: UOC, 2013. ISBN 9788490291726.`
- **Journal article:** `APELLIDOS, N. Título del artículo. Título revista. Lugar: Editor, año, vol., (núm.), pp. x-y. ISSN.`
- **Electronic resources:** add `[en línea]`, `[consulta: día mes año]` and `Disponible en: URL`.
- Titles of the larger work (book/journal) are italicised; variables of style (period vs comma) must be applied consistently.

> Practical note: the numeric UNE-ISO 690 system is visually close to the Vancouver/IEEE numbered styles used by international journals, which is why Spanish engineering students transition easily between them.

### 2.2 Spanish doctoral thesis norms — Real Decreto 99/2011 and "tesis por compendio"

**Legal frame:** Doctoral studies in Spain are regulated by **Real Decreto 99/2011** (28 January 2011), later modified (notably by **RD 576/2023**). Each university issues its own development regulations within this frame, so **always check your university's normativa** — thresholds vary.

**Thesis by compendium of publications ("tesis por compendio de publicaciones"):**
- Requires **express authorisation** from the thesis director(s) and the program's Academic Commission.
- **Minimum of 3 articles** published or accepted in journals/venues of recognised impact (per ANECA criteria for the field), produced during enrolment in the doctoral program.
- **Authorship:** under the newer rules (e.g. enrolments from 2024-25 at universities such as UAM), the candidate must be **principal (first) author in at least two** of the publications; older enrolments may have no such restriction.
- **Open Access** is increasingly required (gold/diamond or institutional repository) for publications after 1 October 2024.
- **Required document structure** of a compendium thesis: a general **Introduction** justifying the topic and the thematic unity; **objectives**; **integrated summary of results and discussion**; **conclusions**; full **copies of the published/accepted articles** with complete references; and a **co-author declaration** in which co-authors consent to inclusion and **waive ("renuncian") the use of that material in another doctoral thesis**.
- A report on the impact indices (JCR/Scopus quartile) of each journal is normally attached.

**Defence (defensa / lectura):** public act before a tribunal; some programs require part of the thesis or the summary in Spanish; **international mention / "mención internacional"** requires a stay abroad, part of the thesis written and defended in another language, and external reviewers from foreign institutions.

**Industrial doctorate ("doctorado industrial", RD 99/2011):** a variant tied to an R&D contract with a company; the candidate's activity is the basis of the thesis.

### 2.3 Language & style: Spanish academic writing vs English — and which to use here

- **Publish in English in this field.** Spanish physical-science and engineering researchers overwhelmingly publish in English because the evaluation system (ANECA sexenios/accreditation) values JCR/Scopus high-quartile (Q1/Q2) journals, virtually all of which are English-language. English dominance is stronger in the physical/engineering sciences than in the social sciences.
- **Use Spanish for:** the thesis front-matter if your university requires it, TFG/TFM, national reports, dissemination, and (optionally) the abstract/resumen.
- **Stylistic contrasts to manage when switching from Spanish to English:**
  - Spanish academic prose tolerates **long, subordinate-rich sentences and a more impersonal/elaborate register**; English scientific style rewards **short, direct sentences, active voice where natural, one idea per sentence**.
  - Watch **false friends** (actual ≠ "actual" → current; eventual; realize/realise; "sensible" → sensitive), **decimal commas vs points** (Spanish uses comma; English/SI papers use the point — but SI permits either, be consistent), and **non-breaking spaces between number and unit** (10 kPa, 313 K).
  - Spanish capitalises fewer title words; English journal titles use title case. Use a professional **language-editing** pass and acknowledge it.

### 2.4 Which citation styles are common in Spanish science/engineering — and when

| Style | Type | Where used in Spain |
|---|---|---|
| **Elsevier numbered / Vancouver-type** | numeric `[1]` | Default for international thermal/chemical-engineering papers (IJR, ATE, Energy, ECM, FPE) — see §3 |
| **IEEE** | numeric `[1]` | Electrical/electronic, computing, control; IEEE conferences (valued by ANECA in Engineering) |
| **Vancouver** | numeric | Biomedical/health, some engineering journals |
| **APA (7th)** | author–date | Social sciences, education, psychology; some engineering coursework |
| **ACS** | numeric or author–date | Chemistry-heavy work (solvent synthesis, CO₂ absorption mechanisms) — relevant to biobased-solvent papers submitted to ACS journals |
| **UNE-ISO 690 (2024)** | numeric / author–date / notes | Spanish institutional documents: doctoral thesis front-matter, TFG/TFM, official/library-mandated work |

**Rule of thumb:** the *target journal's* Guide for Authors overrides everything for the article itself; use **UNE-ISO 690** only where a Spanish university or body specifically requires it.

---

## 3. International journal conventions in this field

### 3.1 Typical target journals
- **International Journal of Refrigeration** (IIR/Elsevier, ISSN 0140-7007) — core venue for absorption-refrigeration cycles and working pairs.
- **Applied Thermal Engineering** (Elsevier, ISSN 1359-4311) — broad thermal systems.
- **Energy**; **Energy Conversion and Management** (Elsevier) — system-level and energy-efficiency framing.
- **Fluid Phase Equilibria** (Elsevier) — VLE/thermodynamic-property data for CO₂ + solvent pairs.
- **International Journal of Thermal Sciences** (Elsevier) — heat/mass transfer fundamentals.
- Also relevant for solvent chemistry: **ACS Sustainable Chemistry & Engineering**, **Journal of Chemical & Engineering Data**, **Separation and Purification Technology**.

### 3.2 Elsevier house style (ATE, IJR, Energy, ECM, FPE)
- **Structure:** title page, abstract, keywords, **Highlights**, IMRaD body, conclusions, nomenclature, declarations, references.
- **Highlights:** 3–5 bullets, ≤ 85 characters each.
- **References:** **elsarticle-num** numbered (Vancouver-type) — in text `[1]`, list **in order of appearance**. Example list entry: `Z.-N. Xiao, S. Dong, Q. Zhong, Numerical simulation of climate response…, Adv. Clim. Chang. Res. 10 (2019) 133–142.` (authors, title, abbreviated journal, vol (year) pages).
- **Mandatory:** full **CRediT** author-contribution statement, **data-availability** statement, **declaration of competing interest**, funding.
- **Article length / figures:** check per journal — e.g. **IJR research papers ≤ 5000 words at first submission, ≤ 25 figures**.

### 3.3 IIR / International Journal of Refrigeration specifics
- **SI units mandatory.** **Avoid the solidus (/):** write `kg m⁻²`, not `kg/m²`. BS 350/3763 or ISO/R31 may be consulted for symbols.
- **Nomenclature list required** when several symbols are used; **all parameters in italics except subscripts**.
- **Equations** centred, numbered sequentially `(1), (2)…` on the right, cited by number in text; vectors/tensors marked clearly.
- **Figures** numbered (Figure 1, 2…), **caption below** the figure; tables with caption above.

### 3.4 ASME and ASHRAE (if you target these venues)
- **ASME** (e.g. *Journal of Heat and Mass Transfer*, conference proceedings): numbered references in ASME format `[1]`; figures and tables called out in order; SI units (US customary may appear in parentheses).
- **ASHRAE** (HVAC&R, refrigeration): SI primary with I-P (inch-pound) often in parentheses; follows ASHRAE author guidelines and terminology (e.g. standardised refrigerant designations).

### 3.5 Units, equations, figures, tables — general SI rules
- **Strict SI**; non-breaking space between value and unit (313 K, 100 kPa); roman unit symbols; variables italic; subscripts/superscripts roman when they are labels (*T*<sub>gen</sub>), italic when they are running indices.
- Define every symbol in the **Nomenclature**; do not redefine in text.
- One concept per figure; axis labels with quantity *and* unit; vector graphics for line plots; greyscale-readable or colourblind-safe palettes; report uncertainties.
- Tables: self-explanatory caption above, footnotes for conditions/uncertainties; do not duplicate figure data.

---

## 4. Practical writing guidance

### 4.1 Building the argument
- Write the paper around **one clear research question** and a single storyline; every section should advance it.
- Draft order that works well: Methods → Results → Discussion → Introduction → Conclusions → Abstract → Title. Write the Abstract last.
- Use **signposting**: "The aim of this work is…", "Our results show…", "In contrast to [3], we observe…".
- Ensure **alignment**: the gap in the Introduction, the analyses in Methods/Results, and the claims in Discussion/Conclusions must correspond exactly.

### 4.2 Literature review & reproducibility
- The review must be **critical and synthetic** (group by theme/mechanism, compare, expose the gap) — not an annotated list. Prefer primary, recent, high-quartile sources; cite the originators of methods (NRTL, PC-SAFT, etc.).
- **Reproducibility:** report chemical purities/CAS, calibration, full operating ranges, model equations and parameters, software versions, and **measurement uncertainties with their propagation**. Deposit raw data/code in a repository and cite it (data-availability statement).

### 4.3 Authorship & contributions (ICMJE + CRediT)
- **First decide authorship using ICMJE-type criteria** (substantial contribution; drafting/revising; final approval; accountability). **Then document contributions with CRediT** — CRediT does *not* by itself confer authorship.
- The **14 CRediT roles:** Conceptualization, Methodology, Software, Validation, Formal analysis, Investigation, Resources, Data curation, Writing – original draft, Writing – review & editing, Visualization, Supervision, Project administration, Funding acquisition. Format: author name followed by their roles, placed above the Acknowledgements.

### 4.4 Research ethics
- **Plagiarism / self-plagiarism:** no copied text without quotation+citation; do not reuse your own prior text/data without disclosure (critical for compendium theses where articles are reproduced — get the co-author waivers).
- **No duplicate or salami submission**; one paper, one journal at a time.
- **Data integrity:** no fabrication/falsification; no improper image manipulation.
- **Disclose** competing interests and all funding; obtain co-author approval of the final version.
- Bodies to know: **COPE** (publication-ethics guidance), **ICMJE** (authorship/disclosures), **CRediT/NISO** (contributions).

### 4.5 Common reviewer pitfalls (avoid these)
- Objective/novelty not stated explicitly; gap not established.
- Interpretation leaking into Results; data duplicated in figure *and* table.
- Missing measurement uncertainties or insufficient method detail (irreproducible).
- Units with solidus or non-SI; inconsistent significant figures; undefined symbols.
- Over-claiming in Conclusions beyond what data support; outdated or self-citation-heavy reference list.
- Highlights that describe methods instead of results; abstract without quantitative findings.
- Missing declarations (CRediT, data availability, competing interest, funding).

---

## 5. Reusable paper-section checklist / template

```
TITLE
  [ ] Specific, ≤15 words, working pair + key result/method, searchable

ABSTRACT (150–250 words, no citations/abbrevs)
  [ ] Context/objective  [ ] Method  [ ] Quantitative results  [ ] Conclusion

KEYWORDS (4–6)        [ ] Indexing terms, not verbatim title
HIGHLIGHTS (3–5)      [ ] ≤85 chars each, results-focused

1. INTRODUCTION
  [ ] Territory/problem  [ ] Critical lit review  [ ] GAP  [ ] Objective + novelty + roadmap

2. MATERIALS & METHODS
  [ ] Chemicals (supplier, CAS, purity, water)  [ ] Equipment + calibration
  [ ] Procedures + T/p/composition ranges
  [ ] Models (EoS/activity model, assumptions, solver, software+version)
  [ ] Measurement uncertainties + propagation

3. RESULTS
  [ ] Findings only (no interpretation)  [ ] Figures/tables (no duplication)
  [ ] Values with uncertainties + consistent sig figs

4. DISCUSSION
  [ ] Mechanism/interpretation  [ ] Quantitative comparison vs literature
  [ ] Unexpected results addressed  [ ] Limitations

5. CONCLUSIONS
  [ ] Tied to objectives  [ ] Quantitative  [ ] No new data/citations  [ ] Future work

NOMENCLATURE   [ ] Latin/Greek/Subscripts/Acronyms, SI units, italics for variables

DECLARATIONS
  [ ] CRediT statement (ICMJE authorship first, then roles)
  [ ] Declaration of competing interest
  [ ] Funding (agency + grant no.)
  [ ] Acknowledgements (non-author help, language editing)
  [ ] Data availability statement (repository + DOI)

REFERENCES
  [ ] Journal house style (Elsevier numbered for IJR/ATE/Energy/ECM/FPE)
  [ ] OR UNE-ISO 690:2024 for Spanish institutional documents
  [ ] Every in-text number ↔ list entry; ordered by appearance (numbered styles)

UNITS/FORMAT GLOBAL CHECK
  [ ] Strict SI, no solidus (kg m⁻² not kg/m²)
  [ ] Non-breaking space value–unit (313 K, 100 kPa)
  [ ] Equations centred, numbered right, cited by number
  [ ] Figures: caption below; Tables: caption above
  [ ] Language edited (English); decimal point consistent
```

---

## Key sources (with URLs)

**UNE-ISO 690 (Spanish citation standard)**
- UNE-ISO 690:2024 (official catalogue, UNE/AENOR): https://www.une.org/encuentra-tu-norma/busca-tu-norma/norma?c=norma-une-iso-690-2024-n0072823
- UNE-ISO 690:2013 (superseded; official record): https://www.une.org/encuentra-tu-norma/busca-tu-norma/norma?c=N0051162
- Numeric system worked examples (Univ. Pablo de Olavide): https://guiasbib.upo.es/iso6902013/sistema_numerico
- 2024 reference examples & changes (UPO): https://guiasbib.upo.es/iso690/referencias_bibliograficas
- Author–date worked examples (UC3M): https://uc3m.libguides.com/guias_tematicas/citas_bibliograficas/une-iso-690
- 2013 vs 2024 changes (UC3M): https://uc3m.libguides.com/guias_tematicas/citas_bibliograficas/norma-une-iso-690

**Spanish doctoral thesis / Real Decreto 99/2011**
- RD 99/2011 consolidated text (BOE): https://www.boe.es/buscar/act.php?id=BOE-A-2011-2541
- Tesis por compendio de publicaciones — requirements (UAM Escuela de Doctorado): https://www.uam.es/EscuelaDoctorado/(es_ES)-Tesis_Compendio_Publicaciones/1446833378081.htm
- Doctorado industrial (RD 99/2011), Univ. de Burgos: https://www.ubu.es/escuela-de-doctorado/tesis-doctoral/doctorado-industrial/doctorado-industrial-rd-992011

**ANECA evaluation / sexenios (why English & quartiles matter)**
- CNEAI criterios de evaluación 2025 (BOE): https://www.boe.es/diario_boe/txt.php?id=BOE-A-2025-26118
- Indicios de impacto, acreditación ingeniería (Univ. de Sevilla): https://guiasbus.us.es/acreditacion_ingenieria/indicios

**Language: English vs Spanish in research**
- Why Spanish researchers publish in English (Scientometrics): https://link.springer.com/article/10.1007/s11192-015-1570-1
- Spanish scholars' academic writing needs (ScienceDirect): https://www.sciencedirect.com/science/article/abs/pii/S0889490614000325

**IMRaD & section best practices**
- "Writing a scientific paper: where to start from?" (PMC): https://www.ncbi.nlm.nih.gov/pmc/articles/PMC4299424/
- IMRaD report guide (George Mason Univ. Writing Center): https://writingcenter.gmu.edu/writing-resources/imrad/writing-an-imrad-report
- IMRaD format explained (AMWA): https://blog.amwa.org/imrad-format-explained
- Structure of a research paper: IMRaD (Univ. of Minnesota): https://libguides.umn.edu/StructureResearchPaper

**Journal house styles (this field)**
- Applied Thermal Engineering — Guide for Authors (Elsevier): https://www.sciencedirect.com/journal/applied-thermal-engineering/publish/guide-for-authors
- International Journal of Refrigeration — Guide for Authors (Elsevier): https://www.sciencedirect.com/journal/international-journal-of-refrigeration/publish/guide-for-authors
- International Journal of Refrigeration (IIR portal): https://iifiir.org/en/international-journal-of-refrigeration-ijr
- Elsevier numbered/Vancouver style reference: https://citationsy.com/styles/elsevier-vancouver

**Ethics, authorship, contributions**
- CRediT author statement & 14 roles (Elsevier): https://www.elsevier.com/researcher/author/policies-and-guidelines/credit-author-statement
- CRediT taxonomy (CASRAI / ANSI-NISO Z39.104-2022): https://casrai.org/credit/

**Field background (absorption refrigeration / CO₂ / DES / ILs)**
- Reviewing & screening ILs and DESs for CO₂ capture (Frontiers in Chemistry): https://www.frontiersin.org/journals/chemistry/articles/10.3389/fchem.2022.951951/full
- CO₂ absorption by biobased deep eutectic solvents (PMC): https://www.ncbi.nlm.nih.gov/pmc/articles/PMC8658771/
