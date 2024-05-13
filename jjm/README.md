
Code to pull habitation/facilities from [Jal Jeevan Mission](https://ejalshakti.gov.in/jjmreport/JJMIndia.aspx)

python requirements are in `requirements.txt`. Install with `pip install -r requirements.txt`

# Files

## data/habs.csv
- Description: Habitation list with hierarchy data with ids and habitation ids and household count information
- Run:
    ```
    python scrape.py
    python compose_habs.py
    ```
    
## data/hab_pop.csv
- Description:  Habitation list with hierarchy data with ids and ST, SC and General population data
 - Run:
    ```
    python scrape_population.py
    python clean_pop.py
    ```
     
## data/lgd_mapping_composed/*.csv
- Description: Various files related to mapping of JJM ids to LGD ids
 - Run:
    ```
    python scrape_lgd_mapping.py
    # to fix problems with thoubal district village mapping
    # assumes presence of LGD data, read file before executing
    python thoubal_mapping.py
    python compose_lgd_mappings.py
    ```
 - Files:
    - data/lgd_mapping_composed/mapped_blocks.csv
        - Description: Community Development Block id mappings
    - data/lgd_mapping_composed/mapped_gps.csv
        - Description: Gram Panchayat id mappings
    - data/lgd_mapping_composed/mapped_vills.csv
        - Description: Village id mappings
    - data/lgd_mapping_composed/unmapped_blocks.csv
        - Description: Community Development Block ids without corresponding LGD ids
    - data/lgd_mapping_composed/unmapped_gps.csv
        - Description: Gram Panchayat ids without corresponding LGD ids mappings
    - data/lgd_mapping_composed/unmapped_vills.csv
        - Description: Village ids without corresponding LGD ids mappings
    - data/lgd_mapping_composed/urbanised_to_be_deleted_vills.csv
        - Description: ??
    - data/lgd_mapping_composed/urbanized_not_to_be_deleted_vills.csv
        - Description: ??
    - data/lgd_mapping_composed/wrong_entry_to_be_deleted_vills.csv
        - Description: ??

## data/facilities/schools.csv
 - Description: schools mapped to habitations geotagged in some cases
 - Run:
    ```
    python scrape_facilties.py schools
    python compose.py data/facilities/schools
    ```

## data/facilities/anganwadis.csv
 - Description: anganwadis mapped to habitations geotagged in some cases 
 - Run:
    ```
    python scrape_facilties.py anganwadis
    python compose.py data/facilities/anganwadis
    ```
## data/facilities/water_sources.csv
 - Description: water sources mapped to habitations geotagged in some cases 
 - Run:
    ```
    python scrape_water_sources.py
    python clean_water_sources.py
    ```
 - Notes:
    - some intermittent failures may occur which lead to unexplored village entries( marked with NA in the csv file ) after the first step.
      In this case run `python undo_na_villages.py` and rerun the first step before continuing

Data published at https://github.com/ramSeraph/indian_admin_boundaries/releases/download/habitations/JJM.zip  
