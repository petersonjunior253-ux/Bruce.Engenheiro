import unittest
from main import offline_intent

class OfflineIntentTests(unittest.TestCase):
    def test_open_app(self):
        tool, args, answer = offline_intent("BRUCE, abrir WhatsApp")
        self.assertEqual(tool, "open_app")
        self.assertEqual(args["app_name"].lower(), "whatsapp")
        self.assertTrue(answer)

    def test_wifi_settings(self):
        tool, args, _ = offline_intent("abrir configurações do Wi-Fi")
        self.assertEqual(tool, "open_device_settings")
        self.assertEqual(args["section"], "wifi")

    def test_alarm(self):
        tool, args, _ = offline_intent("definir alarme para 7h30")
        self.assertEqual(tool, "set_alarm")
        self.assertEqual(args["hour"], 7)
        self.assertEqual(args["minute"], 30)

    def test_list_downloads(self):
        tool, args, _ = offline_intent("listar arquivos na pasta Download")
        self.assertEqual(tool, "list_files")
        self.assertEqual(args["path"], "download")

    def test_local_time(self):
        tool, args, answer = offline_intent("que horas são?")
        self.assertIsNone(tool)
        self.assertIn("Agora são", answer)

    def test_unknown_intent(self):
        tool, args, answer = offline_intent("explique a teoria da relatividade")
        self.assertIsNone(tool)
        self.assertIsNone(answer)

if __name__ == "__main__":
    unittest.main()
