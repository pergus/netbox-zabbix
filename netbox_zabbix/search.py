# search.py
#
# Defines how plugin models are indexed and displayed in NetBox's global search.
# Each SearchIndex class maps model fields to searchable attributes and controls
# how results appear in search output.
#
# Key attributes for each SearchIndex class:
# fields: defines which model fields are searchable and their weight for ranking results.
# display_attrs: defines which additional model fields are shown in the search results
#                next to the object name as badges or extra info.
#

from netbox.search import SearchIndex
from .models import (
    HostConfig
)

class HostConfigIndex(SearchIndex):
    """
    Defines the search index configuration for the HostConfig model.
    
    This class specifies which fields of the HostConfig model are indexed
    for NetBox's global search and how they are weighted for relevance.
    It also defines which fields are displayed alongside each result in
    the search UI.
    
    Attributes:
        model (Model): The model being indexed (HostConfig).
        fields (tuple): A tuple of tuples mapping field names to their search weights.
        display_attrs (tuple): Additional fields displayed with each search result.
    """
    model = HostConfig
    fields = (
        ('name', 100),
        ('description', 500),
    )
    display_attrs = ('status', 'description' )

indexes = [ HostConfigIndex ]


# end 