# deutschlandticket-commute-analysis

# Deutschlandticket Commute Analysis, J&J Norderstedt

## What this is

This is my submission for the Johnson & Johnson Data Science Intern technical assessment. The task was to estimate how attractive public transport would be for employees commuting to J&J Medical GmbH in Norderstedt, using synthetic employee data since real employee addresses obviously cannot be used, and figure out how likely those employees would be to pick up a Deutschlandticket.

All the notebook cells have already been run and their outputs (tables, charts, the interactive maps) are saved in notebook.ipynb. You do not need to run anything yourself to see the results. If you do want to run it, see the setup section below, but it is optional.

## The approach, in short

1. Geocoded the J&J Norderstedt address to get a fixed workplace location
2. Defined a study area around it (25km radius) covering Hamburg and the surrounding commuter towns
3. Generated synthetic employees inside that area and snapped each one to a real residential building using OpenStreetMap data, so nobody ends up living in a lake or a forest
4. Found each employee's nearest real public transport stop using Google Places API
5. Calculated real door to door commute times using Google Directions API in transit mode, set to a realistic weekday morning departure
6. Grouped employees into commute time bands (30, 45, 60, over 60 minutes)
7. Built a simple, transparent Deutschlandticket adoption score based on commute time, walking distance to the stop, and number of transfers
8. Clustered employees geographically and summarized adoption potential by area
9. Put it all on interactive maps

## Two sampling approaches, and an honest result

I built this two ways on purpose because the first version had a real limitation worth being upfront about.

Method A, the baseline, scatters employees randomly and evenly across the whole 25km study area. Simple and easy to defend, but it has a real weakness. Since the outer ring of a circle covers much more area than the center, uniform sampling ends up placing too many synthetic employees in sparse rural areas relative to how people actually live. That skews results toward longer commute times than reality would likely show.

Method B tries to fix this by placing employees near real towns and cities in proportion to their actual population (pulled from Wikidata), so busier places get more employees and small villages get fewer.

Here is the honest part. Method B did not actually perform better. The numbers below show Method B had a slightly higher share of employees in the over 60 minute band than the baseline, not lower. The reason turned out to be geographic rather than statistical. Hamburg is the biggest population center in the study area, so population weighted sampling pulls a lot of employees toward it, but Hamburg's city center is genuinely further from Norderstedt than several smaller towns like Tangstedt or Ahrensburg that the simple uniform method can pick just as easily. Living in a big city does not automatically mean a short commute to a specific suburban office outside that city. I checked this directly and found that employees grouped inside the single "Hamburg" label had commute times ranging from about 49 to 144 minutes, so one label was quietly hiding a huge range of real experiences.

I think this is a more useful finding than if Method B had simply "won," since it tells J&J something concrete: you cannot assume an employee living in Hamburg has good transit access to this specific office.

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

The baseline run took a long time because of a retry mechanism I added partway through. An earlier, faster version snapped employees to real buildings using one small search radius, but that occasionally failed in genuinely rural spots and silently fell back to a raw random point instead, which sometimes landed in a field or forest. Fixing that meant retrying at wider radii (500m, then 1500m, then 3000m) before giving up, which is much more reliable but slower, since some rural points needed two or three attempts each against a shared public OpenStreetMap server.

## Key findings

Across both methods, roughly 78 to 84 percent of employees face a commute over 60 minutes by public transport. Total commute time was the biggest driver of adoption score, followed by number of transfers, then walking distance to the nearest stop. Employees living in or right around Norderstedt itself stood out clearly, averaging under a 1 hour commute and a 92.9 percent high adoption rate, by far the best result in the dataset. On the other end, towns like Lutzhorn and Barmstedt showed consistently weak adoption potential no matter which sampling method was used.

## Business takeaway

Promoting the Deutschlandticket is likely to land best with employees already living near Norderstedt and a handful of well connected towns nearby (Tangstedt, Barsbüttel, Ahrensburg). For employees further out with multiple transfers and long walks to a stop, the ticket mostly solves cost, not convenience, so other measures like carpooling support or flexible hours might matter more for that group. And importantly, "lives in Hamburg" is not a reliable stand in for "has a good commute here," since the data shows a huge spread within Hamburg itself.

## Assumptions and limitations, honestly stated

No employee count was specified in the brief, so I went with 300 as a sample size big enough to show real patterns without excessive API usage.

Real employee addresses were never used or seen anywhere in this project. Only the workplace address is real. Everything about the employees is synthetic, though snapped to real building footprints so the geography makes sense.

Commute times use Google Directions API set to the next available weekday 8am departure, so they reflect a realistic commute rather than whatever time the API happened to be called. An earlier version without this fix produced commute times of several hours, since it was defaulting to whatever time of night I happened to run the code.

Public transport and building data come from a mix of OpenStreetMap and Google Places, since no single free source reliably covered both without running into timeouts along the way.

The adoption score is a simple weighted formula, not a machine learning model. That was a deliberate choice to keep it interpretable and explainable to a business audience rather than a black box.

Population weighting in Method B uses town level population figures treated as a single point per place. This is a real simplification for a city as large as Hamburg, whose population is spread across many boroughs with very different distances to Norderstedt. A more precise version would weight by borough level population inside large cities specifically, which was out of scope given the time available.

Geographic clustering (grouping employees by home location using KMeans) is an imperfect stand in for "similar commute experience." Two employees can live close together but have different commutes depending on which side of a transit line they happen to be on. Increasing the number of clusters from 8 to 16 noticeably reduced this problem after I checked the actual spread of commute times inside each cluster, though it did not remove it entirely.

## A note on AI assistance

This project was built with heavy use of AI coding assistance for writing and debugging code. Every design decision, methodology choice, and interpretation of the results is my own, including catching and fixing several real bugs along the way (an unrealistic departure time default, employees landing in water or forest, a population figure that turned out to belong to an administrative district rather than an actual town). I am comfortable explaining or defending any part of this project.

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

Data files are cached in the data folder so re-running the notebook does not repeat API calls unnecessarily. Delete a specific cache file if you want to force a fresh fetch for that step.

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