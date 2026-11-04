"""Synthetic signed replay of visual-review erasures; caller owns isolated DB."""


def probe(db, key):
    from schulpilot.db import Child, Family, Material, User
    from schulpilot.erasure import reconcile, signed, verify
    from schulpilot.source_lineage_models import VisualObservationReview

    rows = []
    for n in range(4):
        family = Family(name=f"Synthetic restore family {n}", synthetic=True)
        user = User(username=f"visual-restore-probe-{n}", display_name="Synthetic", password_hash="unused", role="child")
        db.add_all((family, user))
        db.flush()
        child = Child(family_id=family.id, user_id=user.id, grade=6)
        db.add(child)
        db.flush()
        material = Material(child_id=child.id, title="Synthetic", visual_observations=[{"note": "synthetic"}])
        db.add(material)
        db.flush()
        review = VisualObservationReview(material_id=material.id, child_id=child.id,
            actor_id=user.id, source_revision=1, observations_digest="a" * 64,
            observation_index=0, version=1, decision="confirmed", observation={"note": "synthetic"})
        db.add(review)
        db.flush()
        rows.append((family.id, child.id, material.id, review.id))
    records = [verify(signed({"id": str(i) * 32, "scope": scope, "target": target, "created": 1}, key), key)
               for i, (scope, target) in enumerate((("material", rows[0][2]), ("child", rows[1][1]),
                                                     ("family", rows[2][0])), start=1)]
    reconcile(db, records + list(reversed(records)))
    db.flush()
    for index in range(3):
        if db.get(VisualObservationReview, rows[index][3]) is not None:
            raise RuntimeError("A deleted source retained a visual observation review")
    if db.get(Material, rows[0][2]) is not None or db.get(Child, rows[1][1]) is not None or db.get(Family, rows[2][0]) is not None:
        raise RuntimeError("Signed source or household erasure failed")
    survivor = db.get(VisualObservationReview, rows[3][3])
    material = db.get(Material, rows[3][2])
    if survivor is None or material is None or material.visual_observations != [{"note": "synthetic"}]:
        raise RuntimeError("Unrelated visual review or observation was lost")
