"""
Tests for the tasks endpoints.
"""
import pytest


@pytest.fixture(autouse=True)
def reset_tasks():
    """Snapshot/restore tasks so create/delete/toggle tests don't leak state across the run."""
    from mock_data import tasks
    snapshot = list(tasks)
    yield
    tasks.clear()
    tasks.extend(snapshot)


class TestGetTasksEndpoint:
    """Test suite for GET /api/tasks."""

    def test_get_tasks_returns_list(self, client):
        """Test getting tasks returns a list."""
        response = client.get("/api/tasks")
        assert response.status_code == 200
        assert isinstance(response.json(), list)


class TestCreateTaskEndpoint:
    """Test suite for POST /api/tasks."""

    def test_create_task_success(self, client):
        """Test creating a task with the fields the frontend sends."""
        response = client.post("/api/tasks", json={
            "title": "Review Q4 inventory levels",
            "priority": "high",
            "dueDate": "2025-11-01"
        })
        assert response.status_code == 201

        data = response.json()
        assert "id" in data
        assert data["title"] == "Review Q4 inventory levels"
        assert data["priority"] == "high"
        assert data["dueDate"] == "2025-11-01"
        assert data["status"] == "pending"

    def test_created_task_appears_in_get_tasks(self, client):
        """Test that a created task shows up in the GET listing."""
        create_response = client.post("/api/tasks", json={
            "title": "Approve Tokyo warehouse orders",
            "priority": "medium",
            "dueDate": "2025-11-02"
        })
        created_id = create_response.json()["id"]

        list_response = client.get("/api/tasks")
        ids = [t["id"] for t in list_response.json()]
        assert created_id in ids

    def test_create_task_missing_required_field(self, client):
        """Test that missing required fields are rejected."""
        response = client.post("/api/tasks", json={"title": "Missing fields"})
        assert response.status_code == 422


class TestDeleteTaskEndpoint:
    """Test suite for DELETE /api/tasks/{task_id}."""

    def test_delete_task_success(self, client):
        """Test deleting a task removes it from the listing."""
        create_response = client.post("/api/tasks", json={
            "title": "Temporary task",
            "priority": "low",
            "dueDate": "2025-11-03"
        })
        task_id = create_response.json()["id"]

        delete_response = client.delete(f"/api/tasks/{task_id}")
        assert delete_response.status_code == 200

        ids = [t["id"] for t in client.get("/api/tasks").json()]
        assert task_id not in ids

    def test_delete_nonexistent_task(self, client):
        """Test deleting a task that doesn't exist returns 404."""
        response = client.delete("/api/tasks/nonexistent-task-999")
        assert response.status_code == 404


class TestToggleTaskEndpoint:
    """Test suite for PATCH /api/tasks/{task_id}."""

    def test_toggle_task_marks_completed(self, client):
        """Test toggling a pending task marks it completed."""
        create_response = client.post("/api/tasks", json={
            "title": "Toggle me",
            "priority": "medium",
            "dueDate": "2025-11-04"
        })
        task_id = create_response.json()["id"]
        assert create_response.json()["status"] == "pending"

        toggle_response = client.patch(f"/api/tasks/{task_id}")
        assert toggle_response.status_code == 200
        assert toggle_response.json()["status"] == "completed"

    def test_toggle_task_twice_returns_to_pending(self, client):
        """Test toggling a task twice returns it to pending."""
        create_response = client.post("/api/tasks", json={
            "title": "Toggle twice",
            "priority": "low",
            "dueDate": "2025-11-05"
        })
        task_id = create_response.json()["id"]

        client.patch(f"/api/tasks/{task_id}")
        second_toggle = client.patch(f"/api/tasks/{task_id}")
        assert second_toggle.json()["status"] == "pending"

    def test_toggle_nonexistent_task(self, client):
        """Test toggling a task that doesn't exist returns 404."""
        response = client.patch("/api/tasks/nonexistent-task-999")
        assert response.status_code == 404
