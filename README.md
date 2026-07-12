# Deutschlandticket Commute Analysis, J&J Norderstedt

## What this is

This is my submission for the Data Science Intern technical assessment. The task was to estimate how attractive public transport would be for employees commuting to J&J Medical GmbH in Norderstedt, using synthetic employee data since real employee addresses cannot be used, and to figure out how likely those employees would be to pick up a Deutschlandticket.

All the notebook cells have already been run and their outputs (tables, charts, the interactive maps) are saved in notebook.ipynb. You do not need to run anything yourself to see the results. If you do want to run it, see the setup section below, but it is optional.

A note on the interactive maps
The maps in this project are interactive HTML content embedded in the notebook. GitHub does not render this kind of embedded content when you view the notebook directly on github.com, so the maps will appear blank there even though the rest of the notebook, including all the tables and charts, displays correctly. To see the notebook with the maps rendering properly, view it through nbviewer instead:
https://nbviewer.org/github/fkhan9/deutschlandticket-commute-analysis/blob/a35a7441607996696ac54b71b7a4393d8c7c4127/notebook.ipynb

## Summary findings

Percentage of employees by commute time
About 2 to 3 percent of employees commute in 30 minutes or less, another 3 to 7 percent take 31 to 45 minutes, roughly 6 to 11 percent take 46 to 60 minutes, and the large majority, 78 to 84 percent, face a commute over 60 minutes.

Deutschlandticket adoption potential
Roughly 13 to 20 percent of employees fall into the High adoption category, meaning a short commute, a short walk to the nearest stop, and few transfers. Around 46 to 51 percent fall into Medium, and the remaining 34 to 36 percent fall into Low, where a Deutschlandticket alone is unlikely to change behavior much.

Areas with strong public transport connectivity
Employees living in or near Norderstedt itself have by far the best outcomes, average commute under 45 minutes and adoption scores above 80. Nearby towns such as Tangstedt, Barsbüttel, and Ahrensburg also do well, each averaging adoption scores above 55.

Areas where public transport is less attractive
Towns such as Lutzhorn, Barmstedt, and Seeth-Ekholt consistently show weak outcomes, average commutes over 100 minutes, several transfers, and adoption scores below 30.

Key factors influencing adoption
Total commute time matters most, followed by number of transfers, then walking distance to the nearest stop. Employees near Norderstedt benefit from short trips with under one transfer on average, while employees in weaker areas often face three or more transfers on top of an already long commute.

## Business takeaway

Promoting the Deutschlandticket is likely to land best with employees already living near Norderstedt and a handful of well connected towns nearby, such as Tangstedt, Barsbüttel, and Ahrensburg. For employees further out with multiple transfers and long walks to a stop, the ticket mostly solves cost, not convenience, so other measures like carpooling support or flexible hours might matter more for that group. One thing worth flagging directly, "lives in Hamburg" is not a reliable stand in for "has a good commute here." The data shows a large spread within Hamburg itself, some Hamburg employees have decent commutes and others have some of the worst in the whole dataset, depending on which part of the city they are in.

## The approach, in short

1. Geocoded the J&J Norderstedt address to get a fixed workplace location
2. Defined a study area around it, 26km radius, covering Hamburg and the surrounding commuter towns
3. Generated synthetic employees inside that area and snapped each one to a real residential building using OpenStreetMap data, so nobody ends up living in a lake or a forest
4. Found each employee's nearest real public transport stop using the Google Places API
5. Calculated real door to door commute times using the Google Directions API in transit mode, set to a realistic weekday morning departure
6. Grouped employees into commute time bands (30, 45, 60, over 60 minutes)
7. Built a simple, transparent Deutschlandticket adoption score based on commute time, walking distance to the stop, and number of transfers
8. Clustered employees geographically and summarized adoption potential by area
9. Put it all on interactive maps

## A note on methodology before the details

To check that the findings above are not just an artifact of how the synthetic employee data happened to be generated, I built two different sampling approaches and ran both through the same downstream pipeline, a simple uniform approach and a population weighted approach. Both are documented in full below. The two approaches agreed closely on the overall picture, so the findings above should be reasonably solid rather than a coincidence of how the fake data was created.

## Two sampling approaches

Method A, the baseline, scatters employees randomly and evenly across the whole 26km study area. Simple to build, but it has a real weakness. Since the outer ring of a circle covers much more area than the center, uniform sampling ends up placing too many synthetic employees in sparse rural areas relative to how people actually live. That skews results toward longer commute times than reality would likely show.

Method B tries to fix this by placing employees near real towns and cities in proportion to their actual population, pulled from Wikidata, so busier places get more employees and small villages get fewer.

Method B did not actually perform better overall. Method B had a slightly higher share of employees in the over 60 minute band than the baseline, not lower. The reason turned out to be geographic rather than statistical. Hamburg is the biggest population center in the study area, so population weighted sampling pulls a lot of employees toward it, but Hamburg's city center is further from Norderstedt than several smaller towns like Tangstedt or Ahrensburg that the uniform method can pick just as easily. Living in a big city does not automatically mean a short commute to a specific suburban office outside that city. I checked this directly and found that employees grouped inside the single "Hamburg" label had commute times ranging from about 49 to 144 minutes, so one label was quietly hiding a huge range of real experiences.

This still feels like a useful finding even though Method B did not "win," since it depicts something concrete: an employee living in Hamburg does not automatically have good transit access to this specific office, it depends heavily on which part of Hamburg.

## Methodology comparison

| Metric | Method A (Baseline) | Method B (Population Weighted) |
|---|---|---|
| Median commute time | 93.0 min | 87.0 min |
| Mean commute time | 88.1 min | 90.3 min |
| Percent employees over 60 min | 78.0% | 84.0% |
| Percent employees 30 min or under | 3.0% | 1.7% |
| Mean adoption score | 44.8 | 43.9 |
| Percent High adoption tier | 20.0% | 13.0% |
| Strongest area | Tangstedt | Norderstedt |
| Weakest area | Lutzhorn | Barmstedt |
| Approx runtime (300 employees) | about 150 minutes | about 65 to 100 minutes, varied across runs |

The baseline run took a long time because of a retry step I added partway through. An earlier, faster version snapped each synthetic employee to the nearest real building using one small search radius, 400 meters. That worked fine in towns but failed in genuinely rural spots, and when it failed it just fell back to the raw random point instead, which sometimes landed in a field, a forest, or open water once I checked it on a map. I fixed this by retrying at wider radii if the first search came back empty, first 500 meters, then 1500 meters, then 3000 meters, only falling back to the raw point if even that came up empty. This was much more reliable, out of 300 employees only 10 still needed the raw fallback, but it was slower, since a chunk of rural points needed two or three separate lookups against a shared public OpenStreetMap server instead of just one.

## Assumptions and limitations

No employee count was specified in the brief, so I went with 300 as a sample size big enough to show real patterns without excessive API usage.

Real employee addresses were never used or seen anywhere in this project. Only the workplace address is real. Everything about the employees is synthetic, though snapped to real building footprints so the geography makes sense.

Commute times use the Google Directions API set to the next available weekday 8am departure, so they reflect a realistic commute rather than whatever time the API happened to be called at. An earlier version without this fix produced commute times of several hours, since it was defaulting to whatever time of night I happened to run the code, when most transit was not running.

Public transport and building data come from a mix of OpenStreetMap and Google Places, since no single free source reliably covered both without running into timeouts along the way.

The adoption score is a simple weighted formula, not a machine learning model. That was a deliberate choice to keep it interpretable rather than a black box.

Population weighting in Method B uses town level population figures treated as a single point per place. This is a real simplification for a city as large as Hamburg, whose population is spread across many boroughs with very different distances to Norderstedt. A more precise version would weight by borough level population inside large cities specifically.

Method A samples within a clearly defined 26km radius circle around the workplace. Method B does not use a single fixed radius in the same way. Instead, its coverage comes from searching for real towns and cities outward from the workplace in several directions, then weighting how often each one gets sampled by its population. This was intentional rather than an oversight, the goal for Method B was a distribution shaped by where people actually live, not a hard geographic cutoff, so a strict radius match to Method A was not the priority. In practice the two methods end up covering a similar overall area, roughly 25 to 30km out from the workplace, but Method B's edge is softer and follows real population centers rather than a clean circle.

Geographic clustering, grouping employees by home location using KMeans, an imperfect stand in for "similar commute experience." Two employees can live close together but have different commutes depending on which side of a transit line they happen to be on. Increasing the number of clusters from 8 to 16 noticeably reduced this problem after I checked the actual spread of commute times inside each cluster, though it did not remove it entirely.

## Running this notebook (optional)

You will need Python 3.10 or later and the packages in requirements.txt.

```
pip install -r requirements.txt
```

Then create a .env file in the project root with your own credentials.

```
GOOGLE_API_KEY=your_google_cloud_api_key
```

The Google key needs Geocoding API, Places API (New), and Directions API enabled. A free tier Google Cloud account has more than enough quota for this project's scale.

Data files are cached in the data folder so re-running the notebook does not repeat API calls unnecessarily. I ran the full notebook top to bottom after adding this caching logic, and confirmed every cell loads from the existing cache files instead of redoing the slow steps, the full run finishes in a few minutes rather than the several hours the original data generation took. Delete a specific cache file if you want to force a fresh fetch for that step.

## Project structure

```
project/
  notebook.ipynb          main analysis, already executed with saved outputs
  config.py                 constants and API key loading
  utils.py                  reusable helper functions
  data/                       cached datasets, buildings, stops, commute times, places
  outputs/                   exported charts and the interactive HTML maps
  requirements.txt
```

> **Note on AI Use:** I utilized Claude while building this project. I made the decisions, the approach, the sampling design, the scoring formula, and the interpretation of the results. AI helped mainly with syntax, learning the specific APIs I had not used before, and working with a few libraries I was less familiar with, so I could spend more time on the analysis itself.
