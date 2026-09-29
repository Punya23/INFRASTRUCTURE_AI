# Step 0: Duplicate Report

## States
- Exact duplicate rows (all columns): 0
- Duplicate keys ['state_code']: 0 rows affected.

## Districts
- Exact duplicate rows (all columns): 0
- Duplicate keys ['district_code']: 0 rows affected.

## ULBs
- Exact duplicate rows (all columns): 0
- Duplicate keys ['local_body_code']: 0 rows affected.

## Wards (ward_code)
- Exact duplicate rows (all columns): 1060
- Duplicate keys ['ward_code']: 1976 rows affected.

Example duplicates:
|   localbody_code |   ward_code | localbody_name   | ward_number   | ward_name   |   district_code | district_name   |   district_census_code |   subdistrict_code | subdistrict_name   |   subdistrict_census_code |   village_code |   village_census_code | ward_source_state   |   village_name |
|-----------------:|------------:|:-----------------|:--------------|:------------|----------------:|:----------------|-----------------------:|-------------------:|:-------------------|--------------------------:|---------------:|----------------------:|:--------------------|---------------:|
|           276618 |     1295614 | Ainapur          | ward No.15    | Ward No.15  |             527 | Belagavi        |                    555 |               5434 | Athni              |                      5434 |              0 |                     0 | karnataka           |            nan |
|           276618 |     1295614 | Ainapur          | ward No.15    | Ward No.15  |             527 | Belagavi        |                    555 |               5434 | Athni              |                      5434 |              0 |                     0 | karnataka           |            nan |
|           276618 |     1295615 | Ainapur          | ward No.16    | Ward No.16  |               0 | nan             |                      0 |                  0 | nan                |                         0 |         929147 |                     0 | karnataka           |            nan |
|           276618 |     1295615 | Ainapur          | ward No.16    | Ward No.16  |               0 | nan             |                      0 |                  0 | nan                |                         0 |         929147 |                     0 | karnataka           |            nan |
|           276618 |     1295616 | Ainapur          | ward No.17    | Ward No.17  |               0 | nan             |                      0 |                  0 | nan                |                         0 |         929147 |                     0 | karnataka           |            nan |

