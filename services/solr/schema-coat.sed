# Numeric copy of the version field: lets package_search collapse results
# to the latest version ({!collapse field=base_name max=version_i},
# ckanext-coat).
\@<fields>@a <field name="version_i" type="int" indexed="true" stored="true"/>
\@</fields>@a <copyField source="version" dest="version_i"/>
