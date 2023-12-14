import os

from iob_module import iob_module

from iob_reg_re import iob_reg_re


class iob_acc_ld(iob_module):
    name = "iob_acc_ld"
    version = "V0.10"
    setup_dir = os.path.dirname(__file__)

    @classmethod
    def _create_submodules_list(cls):
        """Create submodules list with dependencies of this module"""
        super()._create_submodules_list(
            [
                {"interface": "clk_en_rst_s_s_portmap"},
                {"interface": "clk_en_rst_s_port"},
                iob_reg_re,
            ]
        )
