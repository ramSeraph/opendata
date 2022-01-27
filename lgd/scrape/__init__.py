
from .report import get_all_report_downloaders
from .directory import get_all_directory_downloaders
from .dwr import get_all_dwr_downloaders

def get_all_downloaders(ctx):
    directory_downloaders = get_all_directory_downloaders(ctx)
    dwr_downloaders = get_all_dwr_downloaders(ctx)
    report_downloaders = get_all_report_downloaders(ctx)

    all_downloaders = directory_downloaders + dwr_downloaders + report_downloaders
    return all_downloaders
