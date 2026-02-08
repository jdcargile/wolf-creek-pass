"""Tests for analyze.py -- image analysis and response parsing."""

from analyze import detect_media_type, parse_analysis_response


class TestDetectMediaType:
    def test_jpeg(self):
        assert detect_media_type(b"\xff\xd8\xff\xe0" + b"\x00" * 100) == "image/jpeg"

    def test_png(self):
        assert detect_media_type(b"\x89PNG\r\n\x1a\n" + b"\x00" * 100) == "image/png"

    def test_gif(self):
        assert detect_media_type(b"GIF89a" + b"\x00" * 100) == "image/gif"

    def test_webp(self):
        data = b"RIFF\x00\x00\x00\x00WEBP" + b"\x00" * 100
        assert detect_media_type(data) == "image/webp"

    def test_unknown_defaults_to_jpeg(self):
        assert detect_media_type(b"\x00\x00\x00\x00" * 10) == "image/jpeg"

    def test_empty_bytes(self):
        assert detect_media_type(b"") == "image/jpeg"


class TestParseAnalysisResponse:
    def test_all_yes(self):
        text = (
            "SNOW: yes\nCARS: yes\nTRUCKS: yes\nANIMALS: yes\nNOTES: Everything visible"
        )
        result = parse_analysis_response(text)
        assert result.has_snow is True
        assert result.has_car is True
        assert result.has_truck is True
        assert result.has_animal is True
        assert result.notes == "Everything visible"

    def test_all_no(self):
        text = "SNOW: no\nCARS: no\nTRUCKS: no\nANIMALS: no\nNOTES: Clear road"
        result = parse_analysis_response(text)
        assert result.has_snow is False
        assert result.has_car is False
        assert result.has_truck is False
        assert result.has_animal is False
        assert result.notes == "Clear road"

    def test_mixed(self):
        text = "SNOW: yes\nCARS: no\nTRUCKS: yes\nANIMALS: no\nNOTES: Snow with trucks"
        result = parse_analysis_response(text)
        assert result.has_snow is True
        assert result.has_car is False
        assert result.has_truck is True
        assert result.has_animal is False

    def test_case_insensitive(self):
        text = "snow: YES\ncars: No\ntrucks: YES\nanimals: NO\nnotes: test"
        result = parse_analysis_response(text)
        assert result.has_snow is True
        assert result.has_car is False
        assert result.has_truck is True
        assert result.has_animal is False

    def test_missing_fields_stay_none(self):
        text = "SNOW: yes\nNOTES: partial response"
        result = parse_analysis_response(text)
        assert result.has_snow is True
        assert result.has_car is None
        assert result.has_truck is None
        assert result.has_animal is None

    def test_empty_response(self):
        result = parse_analysis_response("")
        assert result.has_snow is None
        assert result.has_car is None
        assert result.notes == ""

    def test_notes_with_colon(self):
        text = "SNOW: no\nCARS: yes\nTRUCKS: no\nANIMALS: no\nNOTES: Road is clear: no issues"
        result = parse_analysis_response(text)
        assert result.notes == "Road is clear: no issues"
