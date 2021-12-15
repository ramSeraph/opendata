from .report import get_all_report_downloaders
from .directory import get_all_directory_downloaders
from .dwr import get_all_dwr_downloaders

def get_all_downloaders(params, ctx):
    directory_downloaders = get_all_directory_downloaders(params, ctx)
    dwr_downloaders = get_all_dwr_downloaders(params, ctx)
    report_downloaders = get_all_report_downloaders(params, ctx)
    return directory_downloaders + dwr_downloaders + report_downloaders


