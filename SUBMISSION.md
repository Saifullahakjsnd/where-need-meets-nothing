---
title: "Where Need Meets Nothing: finding Florida's aid deserts with Snowflake"
published: false
tags: weekendchallenge, snowflake, datascience, showdev
---

*This is a submission for the [Weekend Challenge: Generosity Edition](https://dev.to/challenges/weekend-challenge-generosity)*

## What I Built

Two Florida counties, side by side:

| County | FEMA disasters (10yr) | Poverty rate | Doctors per 10k |
|---|---|---|---|
| **Alachua** | 21 | 21.2% | **351.0** |
| **Glades** | 14 | 17.2% | **20.7** |

Alachua has *more* disasters and *more* poverty than Glades. It also has **17 times the doctor
density**. Alachua contains Gainesville and a teaching hospital. Glades contains Lake Okeechobee's
western shore and not much else.

That gap is invisible in any single dataset. FEMA knows where the hurricanes landed. The Census
knows who is poor. NPPES knows where the doctors are. Nobody joins them — so nobody can point at
the counties where high need meets thin resources and say *there, send help there*.

**Aid Desert Finder** joins those three datasets into one county-level view of Florida and ranks
all 67 counties by how badly need outruns resources. It answers the question a donor actually has:
not "where is it bad" but "where is it bad *and* nobody is already there."

The answer for Florida: **9 counties, about 258,000 people**, averaging 22 disaster declarations
in ten years, 1 in 5 residents below the poverty line, and roughly half the state's median doctor
density.

## Demo

- **Live map:** https://aid-desert-finder.vercel.app
- **Source:** https://github.com/Saifullahakjsnd/where-need-meets-nothing

Hover any county for its full numbers, or recolour the map by need score, doctor density, poverty,
or disaster count.

![Aid desert map of Florida](PLACEHOLDER_SCREENSHOT)

The panhandle and the rural interior light up. The coasts and the university towns do not.

## How I Used Snowflake

The whole thing runs on the **Snowflake Public Data (Free)** Marketplace share. No ETL, no
pipelines, no downloads — three federal datasets already sitting in queryable views:

- `FEMA_DISASTER_DECLARATION_AREAS_INDEX` — which counties each declared disaster touched
- `AMERICAN_COMMUNITY_SURVEY_TIMESERIES` — ACS poverty and population estimates
- `NPPES_PROVIDER_ADDRESSES` — every registered healthcare practitioner's practice location

The thing that makes this join tractable is that **all three share one `GEO_ID` spine** (Data
Commons style — Florida is `geoId/12`, Alachua County is `geoId/12001`). No FIPS wrangling, no
ZIP-to-county crosswalk CSV from some university's website. The join is just `GEO_ID = GEO_ID`.

Even the map geometry is in there. `GEOGRAPHY_CHARACTERISTICS` carries `coordinates_geojson` rows
— real county polygons — so the choropleth uses zero external geodata. `ST_SIMPLIFY` at a 300m
tolerance takes 4.5MB of boundaries down to 190KB with no visible difference at state zoom.

**Cortex Analyst** handles the plain-English layer, over a deliberately tiny semantic model — one
view, six measures. Asked *"Which counties had disasters but fewest doctors?"*, it chose
`providers_per_10k` over the raw headcount **on its own**, because the semantic model's description
of that field says it's the right one for per-capita questions:

```sql
SELECT county_name, disaster_count, providers_per_10k, poverty_rate_pct, aid_desert_score
FROM aid_desert
WHERE disaster_count > 0
ORDER BY providers_per_10k ASC
LIMIT 10
```

It also generalises past its verified queries — *"more than 1 in 5 people in poverty"* became
`poverty_rate_pct > 20` unprompted.

## The three traps

The first version of this produced numbers that looked completely plausible and were wrong. Each
of these only surfaced by checking results against reality:

**1. Providers counted twice.** NPPES stores three address rows per practitioner — `Mailing`,
`Primary Practice`, `Secondary Practice`. Counting all of them credits a doctor to both the county
they live in and the county they work in. Gadsden County dropped from 542 doctors to 436 once
filtered to primary practice.

**2. Two counties that structurally could not have doctors.** Union County reported **zero**
practitioners. Not "few" — zero, in a county of 15,700 people. The cause: Union has no ZIP children
in the geography hierarchy, so a ZIP-based rollup can never assign it anyone. It ranked as a
perfect aid desert because it was invisible. All 67 counties *do* have city children, so the fix
was a city-level fallback. Union actually has 70.

**3. A view built on temp tables.** My first draft assembled the join in `TEMPORARY` tables and
created a view over them. That compiles fine and breaks the moment the session ends.

The check that caught the rest: county populations sum to **22.4M** against Florida's actual
~22.6M. If that number had been off by millions, something in the join was dropping rows.

## The score

A composite of percentile ranks across the 67 counties — 35% disaster frequency, 35% poverty rate,
30% scarcity of doctors per capita. Percentile ranks rather than divide-by-max, so one extreme
county can't compress everyone else into the bottom of the scale. Miami-Dade has 85,714 doctors;
against that maximum, every rural county would round to zero.

It's a judgement call, and I'd defend the weights only as a starting point. They live in one line
of SQL for exactly that reason.

## What I'd do differently with more than a weekend

- **It's one state.** The geography lookup resolves Florida by name, so other states are a one-line
  change — but the score is percentile-ranked *within* the state, so cross-state comparison needs a
  different normalisation.
- **"Doctor" is doing a lot of work.** NPPES counts every individual practitioner — nurses,
  therapists, chiropractors. Filtering by NUCC taxonomy to primary-care physicians would sharpen
  the access measure considerably.
- **Practice location isn't service area.** A county with no doctors bordering a county with a
  hospital is less isolated than one that's 60 miles from anything. Drive-time isochrones would
  capture that; county boundaries don't.
- **Disaster counts aren't disaster severity.** A 22-declaration county might have had 22 minor
  events. FEMA's public-assistance dollars are in the same share and would weight this properly.

## Notes and credits

- The Cortex Analyst REST call pattern (`send_snow_api_request`) is adapted from Snowflake's own
  [Cortex Analyst quickstart](https://github.com/Snowflake-Labs/sfguide-getting-started-with-cortex-analyst).
- Everything else — the SQL, the semantic model, the map — was written for this challenge, in the
  challenge window.
- Built with Claude Code as a pair. It found trap #2 by questioning a result that looked wrong
  rather than accepting it.
- All figures in this post are live query results, not estimates.
