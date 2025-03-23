import os
from io import BytesIO
from pathlib import Path
from unittest import TestCase

import pytest

from froide.helper.redaction import _redact_file

redaction_test_data_path = (
    Path(os.path.dirname(os.path.realpath(__file__))) / "testdata" / "redaction"
)
hello_world_pdf_path = redaction_test_data_path / "minimal_hello_world.pdf"
hello_world_pdf_redacted_path = (
    redaction_test_data_path / "minimal_hello_world_redacted.pdf"
)


def get_file_content(file):
    file.seek(0)
    return file.read()


class Test(TestCase):
    def setUp(self):
        self.input = hello_world_pdf_path.open("rb", buffering=0)
        self.expected = hello_world_pdf_redacted_path.read_bytes()

    def tearDown(self):
        self.input.close()

    @pytest.mark.asyncio(loop_scope="session")
    def test__redact_file_empty_instructions(self):
        in_memory_outfile = BytesIO()
        empty_instructions = {"pages": [{"width": 1, "rects": []}]}

        _redact_file(self.input, in_memory_outfile, empty_instructions)

        self.assertEqual(
            hello_world_pdf_redacted_path.read_bytes(),
            get_file_content(in_memory_outfile),
        )
