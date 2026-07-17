"""Two authenticated users sharing the same database must never see or
affect each other's data. `client` is user 1, `other_client` is user 2,
both wired to the same `test_db`."""


def test_weights_are_isolated_between_users(client, other_client):
    client.post("/api/weight", json={"date": "2026-01-01", "weight_lbs": 180})
    assert other_client.get("/api/weights").get_json() == []

    other_client.post("/api/weight", json={"date": "2026-01-02", "weight_lbs": 200})
    client_dates = {r["date"] for r in client.get("/api/weights").get_json()}
    assert client_dates == {"2026-01-01"}


def test_settings_are_isolated_between_users(client, other_client):
    client.post("/api/setting", json={"key": "goal", "value_lbs": 170})
    assert other_client.get("/api/settings").get_json() == {}

    other_client.post("/api/setting", json={"key": "goal", "value_lbs": 220})
    client_settings = client.get("/api/settings").get_json()
    assert client_settings["goal"]["value_lbs"] == 170


def test_preferences_are_isolated_between_users(client, other_client):
    client.post("/api/preference", json={"key": "fight_name", "value": "Client One"})
    assert other_client.get("/api/preferences").get_json() == {}

    other_client.post("/api/preference", json={"key": "fight_name", "value": "Client Two"})
    client_prefs = client.get("/api/preferences").get_json()
    assert client_prefs["fight_name"] == "Client One"


def test_workouts_are_isolated_between_users(client, other_client):
    client.post("/api/workout", json={
        "date": "2026-01-01", "type": "Run", "duration_min": 30, "kcal": 300, "note": "",
    })
    assert other_client.get("/api/workouts").get_json() == []

    other_client.post("/api/workout", json={
        "date": "2026-01-02", "type": "Bike", "duration_min": 45, "kcal": 400, "note": "",
    })
    client_workouts = client.get("/api/workouts").get_json()
    assert len(client_workouts) == 1
    assert client_workouts[0]["type"] == "Run"


def test_workout_day_notes_are_isolated_between_users(client, other_client):
    client.post("/api/workout-day-note", json={"date": "2026-01-01", "note": "felt great"})
    assert other_client.get("/api/workout-day-notes").get_json() == {}

    other_client.post("/api/workout-day-note", json={"date": "2026-01-02", "note": "rough one"})
    client_notes = client.get("/api/workout-day-notes").get_json()
    assert client_notes == {"2026-01-01": "felt great"}


def test_cannot_delete_another_users_workout(client, other_client):
    r = other_client.post("/api/workout", json={
        "date": "2026-01-03", "type": "Swim", "duration_min": 20, "kcal": 150, "note": "",
    })
    other_workout_id = r.get_json()["id"]

    client.delete(f"/api/workout/{other_workout_id}")

    other_workouts = other_client.get("/api/workouts").get_json()
    assert len(other_workouts) == 1
    assert other_workouts[0]["id"] == other_workout_id
