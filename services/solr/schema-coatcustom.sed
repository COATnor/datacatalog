# Comma-tokenized text field type, so multivalued values can be split into
# individual facet tokens (used by the locations / scientific_names fields,
# ckanext-coatcustom).
\@<types>@a <fieldType name="TextWithCommaTokenizer" class="solr.TextField"><analyzer><tokenizer class="solr.PatternTokenizerFactory" pattern=","/></analyzer></fieldType>

# Multivalued, comma-tokenized copies of the location and scientific_name
# fields, powering the "Locations" and "Scientific names" search facets
# (ckanext-coatcustom).
\@<fields>@a <field name="locations" type="TextWithCommaTokenizer" indexed="true" stored="true" multiValued="true"/>
\@<fields>@a <field name="scientific_names" type="TextWithCommaTokenizer" indexed="true" stored="true" multiValued="true"/>
\@</fields>@a <copyField source="location" dest="locations"/>
\@</fields>@a <copyField source="scientific_name" dest="scientific_names"/>
