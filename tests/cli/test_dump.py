"""Tests for dump command utilities"""

import pathlib
import pytest

from macnotesapp.cli.commands.dump import _safe_filename, _note_short_id


class TestSafeFilename:
    def test_normal_name(self):
        assert _safe_filename("My Note") == "My Note"

    def test_slash_replaced(self):
        assert _safe_filename("folder/note") == "folder_note"

    def test_backslash_replaced(self):
        assert _safe_filename("folder\\note") == "folder_note"

    def test_colon_replaced(self):
        assert _safe_filename("folder:note") == "folder_note"

    def test_multiple_special_chars(self):
        assert _safe_filename("folder/sub:note\\name") == "folder_sub_note_name"


class TestNoteShortId:
    def test_full_coredata_id(self):
        assert _note_short_id("x-coredata://A1B2C3/ICNote/p87") == "p87"

    def test_display_id_format(self):
        assert _note_short_id("Notes/p87") == "p87"

    def test_partial_id(self):
        assert _note_short_id("p87") == "p87"

    def test_folder_slash_short(self):
        assert _note_short_id("Archive/p5631") == "p5631"