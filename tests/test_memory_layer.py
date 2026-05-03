import sys
import os
import unittest
import tempfile
import json
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

from memory_layer import SemanticMemory, EpisodicMemory, ProceduralMemory, TriggerMemory, MemoryStore


class TestSemanticMemory(unittest.TestCase):
    def test_store_and_retrieve_fact(self):
        mem = SemanticMemory()
        mem.store("project_name", "agent-skill-chain")
        self.assertEqual(mem.retrieve("project_name"), "agent-skill-chain")

    def test_retrieve_nonexistent_returns_none(self):
        mem = SemanticMemory()
        self.assertIsNone(mem.retrieve("unknown_key"))

    def test_update_existing_fact(self):
        mem = SemanticMemory()
        mem.store("version", "1.0")
        mem.store("version", "2.0")
        self.assertEqual(mem.retrieve("version"), "2.0")

    def test_list_all_facts(self):
        mem = SemanticMemory()
        mem.store("a", 1)
        mem.store("b", 2)
        result = mem.list_all()
        self.assertEqual(len(result), 2)
        self.assertIn(("a", 1), result)

    def test_persistence_to_file(self):
        """语义记忆应持久化到 JSON 文件"""
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            path = f.name
        try:
            mem = SemanticMemory(path)
            mem.store("key", "value")
            mem.save()
            with open(path) as fp:
                data = json.load(fp)
            self.assertEqual(data["key"], "value")
        finally:
            os.unlink(path)


class TestEpisodicMemory(unittest.TestCase):
    def test_store_and_retrieve_episode(self):
        mem = EpisodicMemory()
        ep_id = mem.store(
            event_type="task_complete",
            data={"task": "phase1.2", "steps": 14, "tests_passed": 290},
            tags=["milestone", "phase1"]
        )
        result = mem.retrieve(ep_id)
        self.assertEqual(result["event_type"], "task_complete")
        self.assertEqual(result["data"]["steps"], 14)

    def test_search_by_event_type(self):
        mem = EpisodicMemory()
        mem.store("task_start", {"task": "a"}, [])
        mem.store("task_complete", {"task": "a"}, [])
        mem.store("task_complete", {"task": "b"}, [])
        results = mem.search(event_type="task_complete")
        self.assertEqual(len(results), 2)

    def test_search_by_tags(self):
        mem = EpisodicMemory()
        mem.store("event", {"x": 1}, ["tag1", "tag2"])
        mem.store("event", {"x": 2}, ["tag2", "tag3"])
        mem.store("event", {"x": 3}, ["tag1"])
        results = mem.search(tags=["tag2"])
        self.assertEqual(len(results), 2)

    def test_search_by_time_range(self):
        mem = EpisodicMemory()
        t1 = time.time() - 100
        mem.store("event", {"x": 1}, [])
        mem.store("event", {"x": 2}, [])
        results = mem.search(time_start=t1)
        self.assertGreaterEqual(len(results), 2)

    def test_episode_has_timestamp(self):
        mem = EpisodicMemory()
        ep_id = mem.store("test_event", {"key": "val"}, [])
        result = mem.retrieve(ep_id)
        self.assertIn("timestamp", result)


class TestProceduralMemory(unittest.TestCase):
    def test_store_and_retrieve_procedure(self):
        mem = ProceduralMemory()
        proc_id = mem.store(
            task_type="api_integration",
            procedure=["auth first", "then call endpoint", "handle errors"],
            success_rate=0.85,
            prerequisites=["valid credentials", "network access"]
        )
        result = mem.retrieve(proc_id)
        self.assertEqual(result["task_type"], "api_integration")
        self.assertEqual(len(result["procedure"]), 3)

    def test_find_by_task_type(self):
        mem = ProceduralMemory()
        mem.store("api_integration", ["step1"], 0.8, [])
        mem.store("api_integration", ["step1", "step2"], 0.9, [])
        mem.store("data_validation", ["validate"], 0.95, [])
        results = mem.find_by_task_type("api_integration")
        self.assertEqual(len(results), 2)

    def test_find_best_procedure(self):
        """应返回成功率最高的 procedure"""
        mem = ProceduralMemory()
        mem.store("api_integration", ["a"], 0.7, [])
        mem.store("api_integration", ["a", "b"], 0.9, [])
        best = mem.find_best("api_integration")
        self.assertEqual(best["success_rate"], 0.9)

    def test_update_success_rate(self):
        mem = ProceduralMemory()
        proc_id = mem.store("test", ["step1"], 0.5, [])
        mem.update_success_rate(proc_id, 1.0)
        result = mem.retrieve(proc_id)
        self.assertAlmostEqual(result["success_rate"], 0.75)


class TestTriggerMemory(unittest.TestCase):
    def test_register_and_fire_trigger(self):
        mem = TriggerMemory()
        fired = []
        mem.register("task_start", "api_integration", lambda ctx: fired.append(ctx))
        mem.fire("task_start", {"task": "test"})
        self.assertEqual(len(fired), 1)
        self.assertEqual(fired[0]["task"], "test")

    def test_multiple_triggers_same_event(self):
        mem = TriggerMemory()
        count = {"a": 0, "b": 0}
        mem.register("task_start", "api", lambda ctx: count.update(a=count["a"] + 1))
        mem.register("task_start", "data", lambda ctx: count.update(b=count["b"] + 1))
        mem.fire("task_start", {})
        self.assertEqual(count["a"], 1)
        self.assertEqual(count["b"], 1)

    def test_no_match_does_nothing(self):
        mem = TriggerMemory()
        mem.register("task_start", "api", lambda ctx: None)
        mem.fire("task_complete", {})

    def test_list_triggers(self):
        mem = TriggerMemory()
        mem.register("task_start", "api", lambda ctx: None)
        mem.register("task_start", "data", lambda ctx: None)
        mem.register("task_complete", "api", lambda ctx: None)
        triggers = mem.list_triggers("task_start")
        self.assertEqual(len(triggers), 2)


class TestMemoryStore(unittest.TestCase):
    def test_memory_store_has_all_layers(self):
        store = MemoryStore()
        self.assertIsNotNone(store.semantic)
        self.assertIsNotNone(store.episodic)
        self.assertIsNotNone(store.procedural)
        self.assertIsNotNone(store.trigger)

    def test_task_lifecycle_through_layers(self):
        """端到端：任务完成后的记忆流转"""
        store = MemoryStore()
        store.semantic.store("last_phase", "1.2")
        ep_id = store.episodic.store("task_complete", {
            "task": "phase1.2", "tests": 290
        }, ["milestone"])
        proc_id = store.procedural.store(
            "doc_converter", ["convert", "batch", "report", "cli"], 0.95, ["stdlib"]
        )
        self.assertEqual(store.semantic.retrieve("last_phase"), "1.2")
        self.assertIsNotNone(store.episodic.retrieve(ep_id))
        self.assertIsNotNone(store.procedural.retrieve(proc_id))


if __name__ == "__main__":
    unittest.main()
