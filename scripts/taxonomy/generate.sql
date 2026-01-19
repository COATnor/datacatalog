install excel;
load excel;

copy (
    with unified as (
        from read_xlsx('species.xlsx', sheet='Arthropods')
        union all by name
        from read_xlsx('species.xlsx', sheet='Birds')
        union all by name
        from read_xlsx('species.xlsx', sheet='Mammals')
        union all by name
        from read_xlsx('species.xlsx', sheet='Plants (bryophytes)')
        union all by name
        from read_xlsx('species.xlsx', sheet='Plants (vascular)')
    ), parsed as (
        select
            nullif(trim("Family"), 'NA') as family,
            nullif(trim("Genus"), 'NA') as genus,
            nullif(trim("Species"), 'NA') as species,
            nullif(trim("Latin"), 'NA') as latin,
            nullif(trim("English"), 'NA') as english,
            nullif(trim("Norwegian"), 'NA') as norwegian
        from unified
    ), merged as (
        select
            family,
            coalesce(latin, species, genus) as specie,
            nullif(lower(concat_ws('/', english, norwegian)), '') as local_names
        from parsed
    )
    select
        concat_ws(
            ' - ',
            family,
            specie
        ) || if(local_names is null, '', concat(' (', local_names, ')')) as full_name
    from merged
    order by full_name asc
)
to 'taxonomy.json' (array)
;