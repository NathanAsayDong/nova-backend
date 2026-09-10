import unittest
from unittest.mock import patch

from prompting import host_environment_prompt as host


class HostEnvironmentPromptTests(unittest.TestCase):
    def test_windows_describes_two_machines(self):
        with patch.object(host.platform, "system", return_value="Windows"), patch.dict(
            "os.environ", {}, clear=False
        ) as _:
            host.os.environ.pop("NOVA_HOST", None)
            text = host.host_environment_prompt()

        self.assertIn("tower", text)
        self.assertIn("run_mac_command", text)
        # On the tower the Mac really is remote, so the caveat belongs here.
        self.assertIn("awake and connected", text)

    def test_mac_says_both_shell_tools_are_the_same_machine(self):
        with patch.object(host.platform, "system", return_value="Darwin"), patch.dict(
            "os.environ", {}, clear=False
        ):
            host.os.environ.pop("NOVA_HOST", None)
            text = host.host_environment_prompt()

        self.assertIn("ON Nate's Mac", text)
        self.assertIn("both run right here", text)
        # The whole point: no pretending the laptop is somewhere else.
        self.assertNotIn("through the link", text)

    def test_env_override_wins_over_the_platform(self):
        with patch.object(host.platform, "system", return_value="Darwin"), patch.dict(
            "os.environ", {"NOVA_HOST": "tower"}
        ):
            text = host.host_environment_prompt()

        self.assertIn("Windows tower", text)

    def test_names_the_box(self):
        text = host.host_environment_prompt()
        self.assertIn("Host: ", text)


if __name__ == "__main__":
    unittest.main()
