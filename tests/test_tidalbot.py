"""Suite unit ermetica per TidalBot: solo logica pura, nessuna rete/sessione Tidal."""

import json
import os
import tempfile
import unittest
from datetime import datetime
from types import SimpleNamespace

from tidalbot import TidalBot


def make_bot(**attrs):
    """Istanza senza __init__ (che crea Session Tidal e legge la config)."""
    bot = TidalBot.__new__(TidalBot)
    bot.config = {}
    bot.debug_mode = False
    bot.tidal_search_limit = 3
    bot.similarity_threshold = 0.75
    bot.session = SimpleNamespace(track=lambda _id: None)
    for key, value in attrs.items():
        setattr(bot, key, value)
    return bot


class ParseRawTracklistTests(unittest.TestCase):
    def setUp(self):
        self.bot = make_bot()

    def test_timestamped_line_with_label(self):
        result = self.bot.parse_raw_tracklist(["[00:02] Artist - Title [Label]"])
        self.assertEqual(result, ["Artist - Title"])

    def test_timestamped_line_without_label(self):
        result = self.bot.parse_raw_tracklist(["[01:30] Artist Two - Another Title"])
        self.assertEqual(result, ["Artist Two - Another Title"])

    def test_plain_song_line_is_kept(self):
        self.assertEqual(self.bot.parse_raw_tracklist(["Artist - Title"]), ["Artist - Title"])

    def test_header_and_urls_and_blanks_are_dropped(self):
        raw = [
            "Live @ Tomorrowland",
            "https://1001tracklists.com/set/123",
            "",
            "   ",
            "[00:00] A - B",
        ]
        self.assertEqual(self.bot.parse_raw_tracklist(raw), ["A - B"])

    def test_timestamp_only_line_is_dropped(self):
        self.assertEqual(self.bot.parse_raw_tracklist(["[00:20]"]), [])


class DatetimeSerializerTests(unittest.TestCase):
    def test_datetime_is_isoformatted(self):
        bot = make_bot()
        dt = datetime(2026, 10, 7, 12, 30, 0)
        self.assertEqual(bot._datetime_serializer(dt), dt.isoformat())

    def test_other_types_raise(self):
        with self.assertRaises(TypeError):
            make_bot()._datetime_serializer(object())


class FullTrackTitleTests(unittest.TestCase):
    def test_complete_track(self):
        track = SimpleNamespace(name="Title", artist=SimpleNamespace(name="Artist"))
        self.assertEqual(make_bot().get_full_track_title(track), "Artist - Title")

    def test_missing_artist_falls_back_to_unknown(self):
        track = SimpleNamespace(id=1, name="Title", artist=SimpleNamespace())
        self.assertEqual(make_bot().get_full_track_title(track), "Unknown Artist - Title")

    def test_unresolvable_track_returns_id(self):
        def boom(_id):
            raise RuntimeError("no session")

        bot = make_bot(session=SimpleNamespace(track=boom))
        track = SimpleNamespace(id=7)
        self.assertEqual(bot.get_full_track_title(track), "Track ID: 7")


class SimilarityScoreTests(unittest.TestCase):
    def setUp(self):
        self.bot = make_bot()

    def test_exact_match_scores_high(self):
        score = self.bot.calculate_similarity_score("Artist - Title", "Title", "Artist")
        self.assertGreaterEqual(score, 0.85)

    def test_unrelated_match_scores_low(self):
        score = self.bot.calculate_similarity_score("Zzz - Qqq", "Title", "Artist")
        self.assertLess(score, 0.6)

    def test_score_is_bounded_and_case_insensitive(self):
        high = self.bot.calculate_similarity_score("Artist - Title", "Title", "Artist")
        low = self.bot.calculate_similarity_score("artist - title", "TITLE", "ARTIST")
        for score in (high, low):
            self.assertGreaterEqual(score, 0.0)
            self.assertLessEqual(score, 1.0)
        self.assertAlmostEqual(high, low, places=6)


class LocalFileTests(unittest.TestCase):
    def test_load_configuration_reads_json(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "config.json")
            with open(path, "w", encoding="utf-8") as handle:
                json.dump({"SONG_LIST": ["a"]}, handle)
            self.assertEqual(make_bot(config_file=path).load_configuration(), {"SONG_LIST": ["a"]})

    def test_load_configuration_missing_file_exits(self):
        bot = make_bot(config_file="/nonexistent/config.json")
        with self.assertRaises(SystemExit):
            bot.load_configuration()

    def test_load_session_converts_expiry_to_datetime(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "session.json")
            with open(path, "w", encoding="utf-8") as handle:
                json.dump({"expiry_time": "2026-10-07T12:30:00"}, handle)
            data = make_bot(session_file=path).load_session()
            self.assertIsInstance(data["expiry_time"], datetime)


if __name__ == "__main__":
    unittest.main()
