# Geography Data Dictionary

## Common Codes

- **state_code**: LGD identifier for a State/UT. (Type: Int64, Nullable: No)
- **state_name**: Official name of the State/UT. (Type: String, Nullable: No)
- **district_code**: LGD identifier for a District. (Type: Int64, Nullable: No)
- **district_name**: Official name of the District. (Type: String, Nullable: No)
- **subdistrict_code**: LGD identifier for a Subdistrict. (Type: Int64, Nullable: No)
- **subdistrict_name**: Official name of the Subdistrict. (Type: String, Nullable: No)
- **local_body_code**: LGD identifier for an Urban Local Body (ULB). (Type: Int64, Nullable: No)
- **local_body_name**: Official name of the Urban Local Body. (Type: String, Nullable: No)
- **ward_code**: LGD identifier for a Ward. (Type: Int64, Nullable: No)
- **ward_name**: Official name of the Ward. (Type: String, Nullable: Yes)
- **ward_number**: Ward number, may contain string values like "1A". (Type: String, Nullable: Yes)

## Ward Dataset Specific
- **ward_source_state**: The state from which this ward data originated (e.g., 'maharashtra', 'karnataka', 'tamil_nadu', 'delhi'). (Type: String, Nullable: No)
- **district_census_code**: Census 2011 code for the district. (Type: Int64, Nullable: Yes)
- **subdistrict_census_code**: Census 2011 code for the subdistrict. (Type: Int64, Nullable: Yes)
- **village_code**: LGD identifier for the village (if mapped). (Type: Int64, Nullable: Yes)
- **village_name**: Name of the village. (Type: String, Nullable: Yes)
- **village_census_code**: Census code of the village. (Type: Int64, Nullable: Yes)
