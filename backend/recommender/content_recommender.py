"""Reusable catalogue retrieval for TripGenie; no Flask or notebook dependencies."""
from pathlib import Path
import json
import re
import unicodedata

import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


def normalize_text(value):
    """Apply the same Unicode/whitespace conventions as preprocessing."""
    text = unicodedata.normalize("NFKC", str(value)).casefold().replace("_", " ")
    return " ".join(re.sub(r"[^\w\s]", " ", text).split())


def destination_key(value):
    """Conservative name identity; preserve punctuation when grouping entries."""
    return " ".join(unicodedata.normalize("NFKC", str(value)).casefold().split())


class ContentBasedRecommender:
    """Fit once at application startup, then reuse for destination/interest queries.

    Documents remain separate. Results retain the highest-scoring entry per
    normalized destination name, without merging facts or altering source data.
    Scores are cosine similarities (or a weighted blend), not probabilities.
    """

    RESULT_COLUMNS = ["id", "destination_name", "state", "region", "trip_types_clean",
                      "ideal_days", "similarity_score", "destination_similarity", "interest_similarity"]

    def __init__(self, records):
        self.catalogue = pd.DataFrame(records).copy(deep=True).reset_index(drop=True)
        required = {"id", "destination_name", "state", "region", "trip_types_clean", "ideal_days", "tfidf_text"}
        if not required.issubset(self.catalogue.columns):
            raise ValueError(f"Missing required fields: {sorted(required - set(self.catalogue.columns))}")
        if self.catalogue.empty or self.catalogue.id.isna().any() or not self.catalogue.id.is_unique:
            raise ValueError("Catalogue must have records with unique, non-null IDs.")
        if not self.catalogue.destination_name.map(lambda v: isinstance(v, str) and bool(v.strip())).all():
            raise ValueError("Destination names must be nonempty strings.")
        if not self.catalogue.tfidf_text.map(lambda v: isinstance(v, str) and bool(v.strip())).all():
            raise ValueError("tfidf_text must contain nonempty strings.")
        self._name_keys = self.catalogue.destination_name.map(destination_key)
        self.vectorizer = TfidfVectorizer(stop_words="english", ngram_range=(1, 2),
                                          sublinear_tf=True, norm="l2")
        self.tfidf_matrix = self.vectorizer.fit_transform(self.catalogue.tfidf_text)
        if np.any(self.tfidf_matrix.getnnz(axis=1) == 0):
            raise ValueError("A catalogue document has no usable TF-IDF terms.")

    @classmethod
    def from_json(cls, path):
        with Path(path).open(encoding="utf-8") as handle:
            records = json.load(handle)
        if not isinstance(records, list):
            raise ValueError("Expected a JSON array of processed catalogue records.")
        return cls(records)

    def _destination_position(self, selected_destination):
        if isinstance(selected_destination, str):
            positions = np.flatnonzero(self._name_keys.eq(destination_key(selected_destination)))
            if len(positions) and self.catalogue.iloc[positions].state.map(destination_key).nunique() > 1:
                raise ValueError("Destination name is ambiguous across locations; select a record ID.")
        else:
            positions = np.flatnonzero(self.catalogue.id.eq(selected_destination))
        if not len(positions):
            raise ValueError(f"Unknown destination: {selected_destination!r}")
        # A name selects the first source entry. An ID selects an explicit variant.
        return int(positions[0])

    def recommend(self, selected_destination=None, interests=None, top_n=5, destination_weight=0.5):
        """Return positive-scoring, unique destinations ordered by score then ID.

        selected_destination: source ID or exact name (case/whitespace insensitive).
        interests: free text or a list/tuple of strings. For combined queries,
        destination_weight controls the blend; single-source queries use weight 1.
        Unknown-vocabulary interests return no results alone and raise for a
        combined query, so ignored interests cannot silently look personalized.
        """
        if isinstance(top_n, bool) or not isinstance(top_n, int) or top_n < 1:
            raise ValueError("top_n must be a positive integer.")
        if not np.isfinite(destination_weight) or not 0 <= destination_weight <= 1:
            raise ValueError("destination_weight must be between 0 and 1.")
        if interests is None:
            interest_text = ""
        elif isinstance(interests, str):
            interest_text = normalize_text(interests)
        elif isinstance(interests, (list, tuple)) and all(isinstance(v, str) for v in interests):
            interest_text = normalize_text(" ".join(interests))
        else:
            raise ValueError("interests must be text or a list/tuple of strings.")
        if selected_destination is None and not interest_text:
            raise ValueError("Supply a destination or nonempty interests.")

        n = len(self.catalogue)
        destination_scores = np.zeros(n)
        interest_scores = np.zeros(n)
        excluded_name = None
        if selected_destination is not None:
            position = self._destination_position(selected_destination)
            excluded_name = self._name_keys.iloc[position]
            destination_scores = cosine_similarity(self.tfidf_matrix[position], self.tfidf_matrix).ravel()
        if interest_text:
            query_vector = self.vectorizer.transform([interest_text])
            if query_vector.nnz == 0:
                if selected_destination is not None:
                    raise ValueError("Interests contain no recognized catalogue terms.")
                return pd.DataFrame(columns=self.RESULT_COLUMNS)
            interest_scores = cosine_similarity(query_vector, self.tfidf_matrix).ravel()

        if selected_destination is None:
            scores = interest_scores
        elif not interest_text:
            scores = destination_scores
        else:
            scores = destination_weight * destination_scores + (1 - destination_weight) * interest_scores
        result = self.catalogue[[c for c in self.RESULT_COLUMNS if c in self.catalogue]].copy()
        result["similarity_score"] = np.clip(scores, 0, 1)
        result["destination_similarity"] = np.clip(destination_scores, 0, 1)
        result["interest_similarity"] = np.clip(interest_scores, 0, 1)
        result["_destination_key"] = self._name_keys
        result = result.loc[result.similarity_score > 0]
        if excluded_name is not None:
            result = result.loc[result._destination_key != excluded_name]
        return (result.sort_values(["similarity_score", "id"], ascending=[False, True], kind="stable")
                .drop_duplicates("_destination_key").head(top_n)
                .loc[:, self.RESULT_COLUMNS].reset_index(drop=True))
