'''
The spec's table of mod log kinds (MOD_LOG_KINDS in spec/admin/test_mod_log.py) lists exactly the kinds the site knows. The spec's cells check each listed kind; only this can see a kind the table leaves out.
'''
from files.classes.mod_logs import ACTIONTYPES
from files.tests.spec.admin.test_mod_log import MOD_LOG_KINDS


def test_the_table_lists_exactly_the_sites_kinds():
	assert set(MOD_LOG_KINDS) == set(ACTIONTYPES), {"unlisted": sorted(set(ACTIONTYPES) - set(MOD_LOG_KINDS)), "not kinds": sorted(set(MOD_LOG_KINDS) - set(ACTIONTYPES))}
