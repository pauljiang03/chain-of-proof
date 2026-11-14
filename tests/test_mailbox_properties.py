"""Missing mailbox properties must not become negative factual answers."""
import json
from pathlib import Path
from types import SimpleNamespace
import tempfile
import unittest
from unittest.mock import patch

from extractor import windows
from extractor.store import Evidence


def entry(value, property_id=windows.MAPI_SENDER_SMTP, value_type=0x1F):
    return SimpleNamespace(entry_type=property_id, data=value, value_type=value_type)


def message(*entries):
    return SimpleNamespace(record_sets=[SimpleNamespace(entries=list(entries))])


class MailboxProperties(unittest.TestCase):
    def test_missing_empty_and_unreadable_properties_are_distinct(self):
        self.assertEqual(windows._mapi_text_property(message(), windows.MAPI_SENDER_SMTP), (None, "missing"))
        self.assertEqual(windows._mapi_text_property(message(entry(b"\x00\x00")), windows.MAPI_SENDER_SMTP), ("", "empty"))
        self.assertEqual(windows._mapi_text_property(message(entry(b"")), windows.MAPI_SENDER_SMTP), ("", "empty"))
        self.assertEqual(windows._mapi_text_property(message(entry(None)), windows.MAPI_SENDER_SMTP), (None, "unavailable"))
        self.assertEqual(windows._mapi_text_property(message(entry(b"binary", value_type=0x102)), windows.MAPI_SENDER_SMTP), (None, "unavailable"))
        text = "different.person@example.test"
        self.assertEqual(windows._mapi_text_property(message(entry(text.encode("utf-16-le"))), windows.MAPI_SENDER_SMTP), (text, "present"))

    def test_mailbox_reader_preserves_sender_availability_and_does_not_use_owner(self):
        recipient = entry("Recipient".encode("utf-16-le"), windows.MAPI_DISPLAY_TO)
        messages = [message(recipient), message(recipient, entry(b"\x00\x00")),
                    message(recipient, entry("sender@example.test".encode("utf-16-le")))]
        for i, item in enumerate(messages):
            item.subject = f"Subject {i}"
            item.sender_name = "Display Name"
            item.get_client_submit_time_as_integer = lambda i=i: 133_000_000_000_000_000 + i * 10_000_000
            item.number_of_attachments = 0
        folder = SimpleNamespace(name="Sent Items", number_of_sub_messages=len(messages),
                                 get_sub_message=lambda i: messages[i], number_of_sub_folders=0)
        mailbox = SimpleNamespace(open_file_object=lambda handle: None, get_root_folder=lambda: folder)
        with tempfile.TemporaryDirectory(dir="/private/tmp") as temporary:
            users = Path(temporary) / "Users"
            container = users / "OtherOwner" / "AppData/Local/Microsoft/Outlook/mail.ost"
            container.parent.mkdir(parents=True)
            container.write_bytes(b"synthetic container")
            target = SimpleNamespace(fs=SimpleNamespace(path=lambda _: users))
            evidence = Evidence()
            with patch.dict("sys.modules", {"pypff": SimpleNamespace(file=lambda: mailbox)}):
                self.assertEqual(windows._email(evidence, target, {"image": "fiction.E01"}), 3)
        self.assertFalse(evidence.problems)
        metadata = [json.loads(row[-1]) for row in evidence.rows()]
        self.assertEqual([p["sender_address"] for p in metadata], [None, "", "sender@example.test"])
        self.assertEqual([p["sender_address_status"] for p in metadata], ["missing", "empty", "present"])
        self.assertTrue(all(p["mailbox_user"] == "OtherOwner" for p in metadata))


if __name__ == "__main__":
    unittest.main()
