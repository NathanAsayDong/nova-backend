import unittest
from unittest import mock

# worker.py calls dotenv.load_dotenv() at import time, which would otherwise
# populate os.environ from the real .env file the moment this test module is
# collected — polluting every other test in the suite with whatever secrets
# happen to be in it (e.g. this has been observed to flip on a latent bug in
# an unrelated CursorService test). Patch it out before importing.
with mock.patch("dotenv.load_dotenv"):
    import worker


class BuildJobsTests(unittest.TestCase):
    def test_includes_stale_conversation_job_every_5_minutes(self):
        jobs = worker.build_jobs()
        by_name = {job.name: job for job in jobs}

        self.assertIn("check_for_stale_conversations", by_name)
        self.assertEqual(by_name["check_for_stale_conversations"].interval_seconds, 5 * 60)
        self.assertIs(
            by_name["check_for_stale_conversations"].run,
            worker._run_check_for_stale_conversations,
        )

    def test_process_conversations_runs_every_5_minutes(self):
        jobs = worker.build_jobs()
        by_name = {job.name: job for job in jobs}

        self.assertIn("process_conversations", by_name)
        self.assertEqual(by_name["process_conversations"].interval_seconds, 5 * 60)

    def test_all_jobs_due_immediately_on_startup(self):
        jobs = worker.build_jobs()
        for job in jobs:
            self.assertTrue(job.due(0.0))

    def test_mark_ran_pushes_next_run_out_by_interval(self):
        job = worker.ScheduledJob(name="x", interval_seconds=300, run=lambda: None)
        job.mark_ran(1000.0)
        self.assertEqual(job.next_run_at, 1300.0)
        self.assertFalse(job.due(1299.0))
        self.assertTrue(job.due(1300.0))


if __name__ == "__main__":
    unittest.main()
