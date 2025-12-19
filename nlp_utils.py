from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import linear_kernel
import re


def simple_preprocess(text):
    if not text:
        return ""
    text = text.lower()
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


class SimpleNLP:
    def __init__(self, docs=None):
        self.vectorizer = TfidfVectorizer(stop_words="english", ngram_range=(1, 2))
        self.corpus = []
        self.tfidf_matrix = None
        if docs:
            self.fit(docs)

    def fit(self, docs):
        self.corpus = [simple_preprocess(d) for d in docs]
        self.tfidf_matrix = self.vectorizer.fit_transform(self.corpus)

    def query(self, q, top_k=5):
        if self.tfidf_matrix is None:
            return []
        q_clean = simple_preprocess(q)
        q_vec = self.vectorizer.transform([q_clean])
        sims = linear_kernel(q_vec, self.tfidf_matrix).flatten()
        idxs = sims.argsort()[::-1][:top_k]
        return [(self.corpus[i], float(sims[i]), i) for i in idxs if sims[i] > 0.0]

    def suggest_category(self, text, categories_map, top_k=1):
        """
        categories_map: {id: name}
        Returns (category_id, score) or (None, 0.0)
        """
        if not categories_map:
            return None, 0.0

        cat_texts = [simple_preprocess(v) for v in categories_map.values()]
        self.vectorizer = TfidfVectorizer(stop_words="english", ngram_range=(1, 2))
        self.tfidf_matrix = self.vectorizer.fit_transform(cat_texts)

        q_clean = simple_preprocess(text)
        q_vec = self.vectorizer.transform([q_clean])
        sims = linear_kernel(q_vec, self.tfidf_matrix).flatten()
        best_idx = sims.argmax()
        best_score = float(sims[best_idx])

        if best_score <= 0:
            return None, 0.0

        # get id by index
        ids = list(categories_map.keys())
        return ids[best_idx], best_score
