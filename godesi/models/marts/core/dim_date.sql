-- One row per calendar day, Jan 2024 - Dec 2025, with Indian fiscal year and festival flags.

with spine as (

    {{ dbt_utils.date_spine(
        datepart="day",
        start_date="cast('2024-01-01' as date)",
        end_date="cast('2026-01-01' as date)"
    ) }}

),

days as (

    select date_day::date as date_day from spine

),

festivals as (

    select * from {{ ref('festival_calendar') }}

),

festival_season as (

    -- a day is "festival season" if a festival falls within the next 14 days
    select
        days.date_day,
        max(festivals.festival_name) as upcoming_festival
    from days
    left join festivals
        on festivals.festival_date between days.date_day and dateadd(day, 14, days.date_day)
    group by days.date_day

)

select
    days.date_day,
    year(days.date_day)                                         as year,
    quarter(days.date_day)                                      as quarter,
    month(days.date_day)                                        as month,
    monthname(days.date_day)                                    as month_name,
    date_trunc('month', days.date_day)::date                    as month_start,
    date_trunc('week', days.date_day)::date                     as week_start,
    dayname(days.date_day)                                      as day_name,
    dayofweekiso(days.date_day) in (6, 7)                       as is_weekend,
    -- Indian financial year runs April to March: 2024-05-10 is in FY25
    'FY' || right(iff(month(days.date_day) >= 4, year(days.date_day) + 1, year(days.date_day))::varchar, 2) as fiscal_year,
    festivals.festival_name,
    festivals.festival_name is not null                         as is_festival_day,
    festival_season.upcoming_festival,
    festival_season.upcoming_festival is not null               as is_festival_season

from days
left join festivals       on days.date_day = festivals.festival_date
left join festival_season on days.date_day = festival_season.date_day
