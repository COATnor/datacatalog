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

create macro initcap(str) AS (
    list_aggr(
        list_transform(
            string_split(str, ' '),
            x -> upper(x[1]) || lower(x[2:])
        ),
        'string_agg', ' '
    )
);

copy (
    with parsed as (
        select
            row_number() over () as row_id,
            nullif(sn_region, 'NA') as region,
            nullif(sn_sub_region, 'NA') as sub_region,
            nullif(sn_locality, 'NA') as locality,
            nullif(sn_section, 'NA') as section,
            cast(nullif(E_dd_wgs84, 'NA') as double) as longitude,
            cast(nullif(N_dd_wgs84, 'NA') as double) as latitude
        from read_xlsx('localities.xlsx', sheet='variable spelling data portal', all_varchar=true)
    )
    select
        concat_ws(
            ' - ',
            initcap(replace(region, '_', ' ')),
            initcap(replace(sub_region, '_', ' ')),
            initcap(replace(locality, '_', ' ')),
            initcap(replace(section, '_', ' '))
        ) as label,
        last_value(latitude ignore nulls) over (order by row_id) as lat,
        last_value(longitude ignore nulls) over (order by row_id) as lon
    from parsed
)
to 'localities.json' (array)
;
