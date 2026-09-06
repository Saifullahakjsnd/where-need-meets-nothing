---
title: "Where Need Meets Nothing: finding Florida's aid deserts with Snowflake"
published: false
description: Joining FEMA disaster declarations, Census poverty data, and the national provider registry to find the counties where high need meets the fewest resources.
tags: weekendchallenge, snowflake, datascience, showdev
---

*This is a submission for [Weekend Challenge: Generosity Edition](https://dev.to/challenges/weekend-2026-09-03)*

## What I Built

Generosity has a targeting problem. Money follows attention, attention follows disasters, and
disasters get covered where the cameras already are. The places that quietly need the most are
often the places nobody is looking.

So I went looking for them. Two Florida counties:

| County | FEMA disasters (10yr) | Poverty rate | Doctors per 10k |
|---|---|---|---|
| **Alachua** | 21 | 21.2% | **351.0** |
| **Glades** | 14 | 17.2% | **20.7** |

Alachua has *more* disasters and *more* poverty than Glades. It also has **17 times the doctor
density**. Alachua contains Gainesville and a teaching hospital. Glades contains the western shore
of Lake Okeechobee and not much else.

That gap is invisible in any single dataset. FEMA knows where the storms landed. The Census knows
who is poor. The national provider registry knows where the doctors are. Nobody joins them — so
nobody can point at a map and say *there, send help there*.

**Aid Desert Finder** joins those three datasets into one county-level view and ranks all 67
Florida counties by how badly need outruns resources. It answers the question a donor actually
has: not "where is it bad," but "where is it bad **and nobody is already there**."

The answer for Florida: **9 counties, about 258,000 people**, averaging 22 disaster declarations
in ten years, one in five residents below the poverty line, and roughly half the state's median
doctor density.

## Demo

**Live map → https://aid-desert-finder.vercel.app**

<!-- UPLOAD media/hero.png HERE -->

The panhandle and the rural interior light up. The coasts and the university towns do not.

Hovering a county — on the map or in the table — dims the rest of the state and pulls up its
numbers. The toggle asks the same 67 counties four different questions.

<!-- UPLOAD media/demo.gif HERE -->

There is also a natural-language box running on Cortex Analyst, which I'll come back to below.

## Code

{% embed https://github.com/Saifullahakjsnd/where-need-meets-nothing %}

Everything is there: the SQL that builds the joined view, the Cortex Analyst semantic model, the
Streamlit in Snowflake app, and the generator for the standalone page.

## How I Built It

### Three federal datasets, zero ETL

The whole thing runs on the **Snowflake Public Data (Free)** Marketplace share. No pipelines, no
downloads, no CSVs — three federal datasets already sitting there as queryable views:

- `FEMA_DISASTER_DECLARATION_AREAS_INDEX` — which counties each declared disaster touched
- `AMERICAN_COMMUNITY_SURVEY_TIMESERIES` — ACS poverty and population estimates
- `NPPES_PROVIDER_ADDRESSES` — every registered healthcare practitioner's practice location

What makes the join tractable is that **all three share one `GEO_ID` spine** (Data Commons style —
Florida is `geoId/12`, Alachua County is `geoId/12001`). No FIPS wrangling, no ZIP-to-county
crosswalk scraped off a university website. The join is `GEO_ID = GEO_ID`.

Even the map geometry is in there. `GEOGRAPHY_CHARACTERISTICS` carries `coordinates_geojson` rows
— real county polygons — so the choropleth uses **zero external geodata**. `ST_SIMPLIFY` at a 300m
tolerance takes 4.5MB of boundaries down to 190KB with no visible difference at state zoom.

### Asking it in English

**Cortex Analyst** handles the plain-English layer over a deliberately tiny semantic model — one
view, six measures. The interesting part is what it does unprompted:

<!-- UPLOAD media/cortex.png HERE -->

Asked *"Which counties had disasters but fewest doctors?"*, it chose `providers_per_10k` over the
raw headcount **on its own** — because the semantic model's description of that field says it's the
right one for per-capita questions. Nothing in the question mentioned per-capita anything.

It generalises past its verified queries too: *"more than 1 in 5 people in poverty"* became
`poverty_rate_pct > 20`, and *"show me counties where fewer than 60 doctors per 10k"* composed
correctly with it. The semantic model is 80 lines of YAML.

### Three traps that produced convincing wrong answers

The first working version gave numbers that looked entirely plausible and were wrong. Each of
these only surfaced by checking output against reality rather than trusting it:

**1. Doctors counted twice.** The provider registry stores three address rows per practitioner —
`Mailing`, `Primary Practice`, `Secondary Practice`. Counting all of them credits a doctor to both
the county they live in and the county they work in. Gadsden County fell from 542 doctors to 436
once filtered to primary practice.

**2. Two counties that structurally could not have doctors.** Union County reported **zero**
practitioners. Not "few" — zero, in a county of 15,700 people. Union has no ZIP children in the
geography hierarchy, so a ZIP-based rollup can never assign it anyone. It ranked as a perfect aid
desert *because it was invisible*. All 67 counties do have city children, so the fix was a
city-level fallback. Union actually has 70.

**3. A view built on temp tables.** My first draft assembled the join in `TEMPORARY` tables and
created a view over them. That compiles fine and breaks the moment the session ends.

The check that caught the rest: county populations sum to **22.4M** against Florida's actual
~22.6M. Had that been off by millions, something in the join was silently dropping rows.

### Scoring, and one map bug

The composite is a percentile rank across the 67 counties — 35% disaster frequency, 35% poverty
rate, 30% scarcity of doctors per capita. Percentile ranks rather than divide-by-max, because
Miami-Dade has 85,714 doctors and against that maximum every rural county rounds to zero.

The same skew bit the map. My first choropleth used equal-interval colour bins, and since Alachua
sits at 351 doctors per 10k against a median of 118, nearly every county collapsed into the same
two shades. Quantile bins fixed it — each of the seven steps now holds roughly a seventh of the
counties, and the distribution is actually readable.

### Honest limits

- **It's one state.** The geography lookup resolves Florida by name, so another state is a one-line
  change — but the score is percentile-ranked *within* the state, so cross-state comparison needs a
  different normalisation.
- **"Doctor" is doing a lot of work.** The registry counts every individual practitioner — nurses,
  therapists, chiropractors. Filtering by taxonomy to primary-care physicians would sharpen this a
  lot.
- **Practice location isn't service area.** A county with no doctors next door to a hospital is
  less isolated than one 60 miles from anything. Drive-time isochrones would capture that; county
  lines don't.
- **Disaster counts aren't severity.** A 22-declaration county might have had 22 minor events.
  FEMA's public-assistance dollars are in the same share and would weight this properly.

## Prize Categories

**Best Use of Snowflake.** Three federal datasets joined through the free public data share with no
ETL, Cortex Analyst for the natural-language layer, Streamlit in Snowflake for the in-platform app,
and the county boundary geometry pulled from the same share so the map needs no external geodata.

---

*Credits: the Cortex Analyst REST call pattern (`send_snow_api_request`) is adapted from
Snowflake's own [Cortex Analyst quickstart](https://github.com/Snowflake-Labs/sfguide-getting-started-with-cortex-analyst).
Everything else was written for this challenge, in the challenge window. Built with Claude Code as
a pair — it caught trap #2 by questioning a result that looked wrong instead of accepting it. Every
figure in this post is a live query result.*
