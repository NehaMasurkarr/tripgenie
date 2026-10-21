# Indian Tourism Dataset

TripGenie uses a structured catalogue of Indian tourist destinations for exploration, content-based matching, and personalized hybrid recommendations.

## Source and attribution

- **Dataset:** [Indian Tourism Dataset — Kaggle](https://www.kaggle.com/datasets/sushanthnaidu24/indian-tourism-dataset)
- **Creator / publisher:** Venkata Sai Sushanth Bongarala ([sushanthnaidu24](https://www.kaggle.com/sushanthnaidu24))
- **Release:** Version 1, published January 12, 2026.
- **License:** Apache License, Version 2.0; full text in [LICENSE-2.0.txt](LICENSE-2.0.txt).

Source and license were verified against Kaggle metadata on October 11, 2026. The downloaded version-1 `india_tourism_dataset.json` matches this repository's original file as parsed JSON. The upstream archive also contains `dataset_schema.json` and `destination_names.txt`, which are not included here.

Suggested attribution: “Indian Tourism Dataset, Venkata Sai Sushanth Bongarala, Kaggle, version 1 (2026), Apache License 2.0. Processed features and recommendation applications by TripGenie.”

## Files and TripGenie usage

| File | Purpose |
|---|---|
| [india_tourism_dataset.json](india_tourism_dataset.json) | Original catalogue: 100 entries, 54 top-level fields, and 93 distinct exact destination names. Preserved as the source input. |
| [processed/india_tourism_processed.json](processed/india_tourism_processed.json) | TripGenie-derived catalogue with flattened nested fields, cleaned text and tags, explicit missing indicators, cost endpoints, duplicate-review flags, and TF-IDF input text. |
| [processed/duplicate_destination_report.json](processed/duplicate_destination_report.json) | Differences between seven repeated destination/location pairs, preserving conflicting source values for review. |
| [processed/preprocessing_metadata.json](processed/preprocessing_metadata.json) | Transformation policies, aliases, quality audits, feature contract, dependency versions, and original-file SHA-256. |

[Notebook 01](../notebooks/01_data_exploration.ipynb) explores the original catalogue. [Notebook 02](../notebooks/02_data_preprocessing.ipynb) regenerates the processed artifacts; run its cells in order from within the repository. All 100 entries and original IDs are retained—duplicate destinations are investigated rather than automatically removed.

[Notebook 03](../notebooks/03_content_based_recommendation.ipynb) uses TF-IDF and cosine similarity. [Notebook 04](../notebooks/04_hybrid_recommendation.ipynb) adds popularity and budget, interest, season, and duration preferences. Both use reusable code in [backend/recommender/](../backend/recommender/) and suppress repeated destination names in returned results. There is no collaborative filtering or user-interaction dataset.

## License and notices

Keep [LICENSE-2.0.txt](LICENSE-2.0.txt) and [NOTICE](NOTICE) with redistributed data. Apache 2.0 section 4 requires a license copy, prominent change notices for modified files, and retention of applicable upstream copyright, patent, trademark, and attribution notices. If an upstream distribution includes a `NOTICE`, preserve its applicable attribution notices as well.

No upstream `LICENSE` or `NOTICE` file was present in the inspected version-1 archive. The included license is the official Apache text; this repository's `NOTICE` supplies TripGenie attribution and identifies the processed artifacts as modified derivatives. Retain those change notices with the artifacts and carry them into any further modified files. This dataset documentation does not assign a license to TripGenie's application code.

## Data limitations

The catalogue contains descriptive and estimated travel information, not verified real-time availability or observed user preferences. The publisher describes daily budget estimates as INR; confirm costing assumptions before product use. Popularity methodology is unspecified, season labels can be conditional, and repeated entries can disagree. Preserve source tokens such as `web:185` for provenance, but do not treat them as independently resolvable citations.
