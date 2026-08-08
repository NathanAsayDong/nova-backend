import os
import shutil
import tempfile
import unittest
from pathlib import Path
from uuid import uuid4

from src.model.conversation import Conversation
from src.model.project import Project
from src.service.code_service import CodeService


class FakeProjectDao:
    def __init__(self, projects):
        self.projects = {p.id: p for p in projects}

    def get(self, id):
        return self.projects.get(int(id))


class FakeConversationDao:
    def __init__(self, conversations=()):
        self.conversations = {c.uuid: c for c in conversations}

    def get_by_uuid(self, uuid):
        return self.conversations.get(uuid)


class CodeServiceTestCase(unittest.TestCase):
    def setUp(self):
        self.workspace_root = Path(tempfile.mkdtemp(prefix="nova-code-test-"))
        self.addCleanup(shutil.rmtree, self.workspace_root, ignore_errors=True)

        self.project = Project(id=1, name="Test Project")
        self.conversation = Conversation(id=1, uuid=uuid4(), project_id=1)
        self.orphan_conversation = Conversation(id=2, uuid=uuid4(), project_id=None)

        self.service = CodeService.__new__(CodeService)
        self.service.project_dao = FakeProjectDao([self.project])
        self.service.conversation_dao = FakeConversationDao(
            [self.conversation, self.orphan_conversation]
        )
        self.service.workspace_root = self.workspace_root

        self.cid = str(self.conversation.uuid)

    def workspace(self) -> Path:
        return self.workspace_root / "project-1"


class ProjectResolutionTests(CodeServiceTestCase):
    def test_resolves_project_from_conversation(self):
        result = self.service.list_project_files(conversation_uuid=self.cid)
        self.assertEqual(result["project"]["id"], 1)

    def test_explicit_project_id_wins(self):
        result = self.service.list_project_files(project_id=1)
        self.assertEqual(result["project"]["id"], 1)

    def test_conversation_without_project_is_refused(self):
        with self.assertRaises(ValueError) as ctx:
            self.service.list_project_files(
                conversation_uuid=str(self.orphan_conversation.uuid)
            )
        self.assertIn("not attached to a project", str(ctx.exception))

    def test_no_context_at_all_is_refused(self):
        with self.assertRaises(ValueError) as ctx:
            self.service.list_project_files()
        self.assertIn("No project context", str(ctx.exception))

    def test_unknown_project_is_refused(self):
        with self.assertRaises(ValueError):
            self.service.list_project_files(project_id=999)

    def test_each_project_gets_its_own_folder(self):
        self.service.project_dao.projects[2] = Project(id=2, name="Other")
        a = self.service.list_project_files(project_id=1)["project"]["workspace"]
        b = self.service.list_project_files(project_id=2)["project"]["workspace"]
        self.assertNotEqual(a, b)
        self.assertTrue(a.endswith("project-1"))
        self.assertTrue(b.endswith("project-2"))


class PathContainmentTests(CodeServiceTestCase):
    def test_parent_traversal_is_refused(self):
        with self.assertRaises(ValueError) as ctx:
            self.service.read_project_file("../../etc/passwd", project_id=1)
        self.assertIn("escapes the project workspace", str(ctx.exception))

    def test_absolute_path_is_refused(self):
        with self.assertRaises(ValueError) as ctx:
            self.service.read_project_file("/etc/passwd", project_id=1)
        self.assertIn("must be relative", str(ctx.exception))

    def test_write_cannot_escape(self):
        with self.assertRaises(ValueError):
            self.service.write_project_file("../escaped.py", "x", project_id=1)
        self.assertFalse((self.workspace_root / "escaped.py").exists())

    def test_delete_cannot_escape(self):
        outside = self.workspace_root / "outside.txt"
        outside.write_text("keep me")
        with self.assertRaises(ValueError):
            self.service.delete_project_file("../outside.txt", project_id=1)
        self.assertTrue(outside.exists())

    def test_symlink_escape_is_refused(self):
        root = self.workspace()
        root.mkdir(parents=True, exist_ok=True)
        secret = self.workspace_root / "secret.txt"
        secret.write_text("classified")
        os.symlink(secret, root / "link.txt")

        with self.assertRaises(ValueError) as ctx:
            self.service.read_project_file("link.txt", project_id=1)
        self.assertIn("escapes the project workspace", str(ctx.exception))

    def test_nested_traversal_that_stays_inside_is_allowed(self):
        self.service.write_project_file("src/deep/file.py", "ok", project_id=1)
        result = self.service.read_project_file("src/deep/../deep/file.py", project_id=1)
        self.assertEqual(result["content"], "ok")

    def test_empty_path_is_refused(self):
        with self.assertRaises(ValueError):
            self.service.read_project_file("  ", project_id=1)


class FileOperationTests(CodeServiceTestCase):
    def test_write_then_read_roundtrip(self):
        written = self.service.write_project_file("main.py", "print(1)\n", project_id=1)
        self.assertEqual(written["status"], "created")

        read = self.service.read_project_file("main.py", project_id=1)
        self.assertEqual(read["content"], "print(1)\n")
        self.assertFalse(read["truncated"])

    def test_write_reports_overwrite(self):
        self.service.write_project_file("main.py", "v1", project_id=1)
        second = self.service.write_project_file("main.py", "v2", project_id=1)
        self.assertEqual(second["status"], "overwritten")
        self.assertEqual(
            self.service.read_project_file("main.py", project_id=1)["content"], "v2"
        )

    def test_write_creates_parent_directories(self):
        self.service.write_project_file("a/b/c/deep.py", "x", project_id=1)
        self.assertTrue((self.workspace() / "a/b/c/deep.py").exists())

    def test_read_missing_file_is_refused(self):
        with self.assertRaises(ValueError):
            self.service.read_project_file("nope.py", project_id=1)

    def test_listing_reports_files_and_skips_noise(self):
        self.service.write_project_file("main.py", "x", project_id=1)
        self.service.write_project_file("src/util.py", "y", project_id=1)
        (self.workspace() / "__pycache__").mkdir(parents=True, exist_ok=True)
        (self.workspace() / "__pycache__" / "junk.pyc").write_text("noise")

        listing = self.service.list_project_files(project_id=1)
        paths = {entry["path"] for entry in listing["files"]}
        self.assertEqual(paths, {"main.py", "src/util.py"})
        self.assertEqual(listing["file_count"], 2)

    def test_empty_project_listing_has_note(self):
        listing = self.service.list_project_files(project_id=1)
        self.assertEqual(listing["files"], [])
        self.assertIsNotNone(listing["note"])

    def test_delete_file(self):
        self.service.write_project_file("gone.py", "x", project_id=1)
        result = self.service.delete_project_file("gone.py", project_id=1)
        self.assertEqual(result["status"], "deleted")
        self.assertFalse((self.workspace() / "gone.py").exists())

    def test_delete_directory_requires_recursive(self):
        self.service.write_project_file("pkg/mod.py", "x", project_id=1)
        with self.assertRaises(ValueError) as ctx:
            self.service.delete_project_file("pkg", project_id=1)
        self.assertIn("recursive", str(ctx.exception))
        self.assertTrue((self.workspace() / "pkg/mod.py").exists())

    def test_delete_directory_with_recursive(self):
        self.service.write_project_file("pkg/mod.py", "x", project_id=1)
        result = self.service.delete_project_file("pkg", recursive=True, project_id=1)
        self.assertEqual(result["files_deleted"], 1)
        self.assertFalse((self.workspace() / "pkg").exists())

    def test_cannot_delete_workspace_root(self):
        with self.assertRaises(ValueError) as ctx:
            self.service.delete_project_file(".", project_id=1)
        self.assertIn("workspace itself", str(ctx.exception))


class EditTests(CodeServiceTestCase):
    def test_command_edit_changes_file_and_reports_diff(self):
        self.service.write_project_file("app.py", "value = 1\n", project_id=1)

        result = self.service.edit_project_file(
            "app.py",
            "python3 -c \"import pathlib; p=pathlib.Path('app.py'); "
            "p.write_text(p.read_text().replace('1', '2'))\"",
            project_id=1,
        )

        self.assertEqual(result["exit_code"], 0)
        self.assertTrue(result["file_changed"])
        self.assertIn("-value = 1", result["diff"])
        self.assertIn("+value = 2", result["diff"])
        self.assertEqual(
            self.service.read_project_file("app.py", project_id=1)["content"],
            "value = 2\n",
        )

    def test_failing_command_reports_exit_code_without_changing_file(self):
        self.service.write_project_file("app.py", "value = 1\n", project_id=1)

        result = self.service.edit_project_file(
            "app.py", "false", project_id=1
        )

        self.assertNotEqual(result["exit_code"], 0)
        self.assertFalse(result["file_changed"])
        self.assertEqual(result["diff"], "")

    def test_edit_runs_in_project_workspace(self):
        self.service.write_project_file("marker.py", "x", project_id=1)
        result = self.service.edit_project_file("marker.py", "pwd", project_id=1)
        self.assertEqual(result["stdout"].strip(), str(self.workspace().resolve()))

    def test_edit_missing_file_is_refused(self):
        with self.assertRaises(ValueError):
            self.service.edit_project_file("nope.py", "true", project_id=1)

    def test_edit_requires_command(self):
        self.service.write_project_file("app.py", "x", project_id=1)
        with self.assertRaises(ValueError):
            self.service.edit_project_file("app.py", "   ", project_id=1)


if __name__ == "__main__":
    unittest.main()
