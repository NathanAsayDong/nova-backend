import json

from src.dao.base_dao import BaseDao
from src.model.person import Person


class PersonDao(BaseDao):
    """
    DAO for enrolled people and their face samples (`person`, `face_sample`).
    """
    _table = "person"
    _samples_table = "face_sample"
    _model_class = Person

    def _person(self, row: dict) -> Person:
        # PostgREST returns an embedded count as [{"count": n}].
        counted = row.pop("face_sample", None)
        samples = counted[0].get("count", 0) if counted else 0
        return Person(**row, samples=samples)

    def list_people(self) -> list[Person]:
        response = (
            self.client.table(self._table)
            .select("*, face_sample(count)")
            .order("name")
            .execute()
        )
        return [self._person(row) for row in response.data or []]

    def get(self, id: int) -> Person | None:
        response = (
            self.client.table(self._table)
            .select("*, face_sample(count)")
            .eq("id", id)
            .maybe_single()
            .execute()
        )
        if response is None or response.data is None:
            return None
        return self._person(response.data)

    def create(self, person: Person) -> Person:
        response = self.client.table(self._table).insert(person.to_payload()).execute()
        return Person(**response.data[0])

    def delete(self, id: int) -> bool:
        """Delete a person; their samples go with them (on delete cascade)."""
        response = self.client.table(self._table).delete().eq("id", id).execute()
        return bool(response.data)

    def add_sample(self, person_id: int, embedding: list[float]) -> None:
        self.client.table(self._samples_table).insert(
            {"person_id": person_id, "embedding": embedding}
        ).execute()

    def count_samples(self, person_id: int) -> int:
        response = (
            self.client.table(self._samples_table)
            .select("id", count="exact")
            .eq("person_id", person_id)
            .execute()
        )
        return response.count or 0

    def all_samples(self) -> list[tuple[int, str, list[float]]]:
        """Every sample as (person_id, name, embedding), for the matcher's gallery."""
        response = (
            self.client.table(self._samples_table)
            .select("person_id, embedding, person(name)")
            .execute()
        )
        samples = []
        for row in response.data or []:
            embedding = row.get("embedding")
            # pgvector comes back over PostgREST as its text form, "[0.1,...]".
            if isinstance(embedding, str):
                embedding = json.loads(embedding)
            person = row.get("person") or {}
            samples.append((row["person_id"], person.get("name") or "", embedding))
        return samples
