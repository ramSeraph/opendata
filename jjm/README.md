
Code to pull habitation/facilities from [Jal Jeevan Mission](https://ejalshakti.gov.in/jjmreport/JJMIndia.aspx)

python requirements are in `requirements.txt`. Install with `pip install -r requirements.txt`

To pull habitations data - `python scrape.py`. the scraping is resumable( if it fails because of network issues, rerun it)

To pull schools data - `python scrape_facilties.py schools`. the scraping is resumable( if it fails because of network issues, rerun it)

To pull anganwadi data - `python scrape_facilties.py anganwadis`. the scraping is resumable( if it fails because of network issues, rerun it)

Data ends up in `data/habitations`, `data/facilities/schools`, `data/facilities/anganwadis` respectively

Data can be then composed into csv using `compose.py`, `python compose.py data/facilities/schools` collects the data under `data/facilities/schools` to a common csv at `data/facilities/schools.csv`

Please read [JJM Website policy](https://jalshakti-ddws.gov.in/website-policies-0) before considering publishing data
