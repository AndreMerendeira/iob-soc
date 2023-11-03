import os

# Find python modules
if __name__ == "__main__":
    import sys

    sys.path.append("./scripts")
from iob_module import iob_module

if __name__ == "__main__":
    iob_module.find_modules()

from iob_counter import iob_counter
from iob_reg import iob_reg


class iob_sipo_reg(iob_module):
    @classmethod
    def _init_attributes(cls):
        """Init module attributes"""
        cls.name = "iob_sipo_reg"
        cls.version = "V0.10"
        cls.flows = "sim"
        cls.setup_dir = os.path.dirname(__file__)
        cls.submodules = [
            {"interface": "clk_en_rst"},
            iob_counter,
            iob_reg,
        ]


if __name__ == "__main__":
    iob_sipo_reg.setup_as_top_module()
