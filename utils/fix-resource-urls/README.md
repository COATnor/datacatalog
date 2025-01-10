# 🔧 Fix broken resource URLs in COAT

This is a utility script to identify and fix invalid resource URLs in the COAT portal. The script checks resources in a dataset, identifies those with broken or incorrect URLs, and attempts to update them with correct URLs.

This script addresses an issue with invalid URLs to data files in CKAN datasets. The problem arises when a new version of a dataset is created (e.g., `V_air_temperature_snowbed`, `V_air_temperature_meadow`), and data from previous years (e.g., 2023).

In some cases, the URLs to older data files in these new versions are broken or incorrectly formatted. For example: `http://v_air_temperature_snowbed_2021.txt/` instead of referencing the file which was uploaded the first time.

This script helps identify and correct these broken URLs, ensuring they point to the correct data files.

## ✨ Features

This utility aims to:

1. **🔍 Detect Invalid Resource URLs**: Identify resources with broken URLs by validating them.
2. **🔧 Fix Resource URLs**: Generate and update corrected URLs for invalid resources.
3. **📝 Log the Process**: Provide detailed logs of actions taken, errors encountered, and resources updated.

## 🚀 Usage

In order to use this script you have to:

1. Set up the environment variables in a `.env` file, a `template.env` can be found inside this folder. The `CKAN_USER_API_KEY` can be found in the profile for the user.
2. Set up and run the COAT portal locally. Referring to the first `README.md` file in the root of this repository.
3. 🏃 Run the script using the following command:

```bash
python utils/fix-resource-urls/fix_resource_urls.py --dataset_id <DATASET_ID>
```

### 🔎 Finding the dataset ID's with broken URLs

For finding the dataset ID's with broken URLs, the following SQL query can be used:

```sql
SELECT p.id, p."name", COUNT(r.id) AS resource_count
FROM package p
INNER JOIN resource r ON r.package_id = p.id
WHERE r."url_type" IS NULL
    AND r."url" = CONCAT('http://', lower(r."name"))
GROUP BY p.id, p."name";
```

!! Note: The dataset (or package which the resource belongs to) should be set private before running the script.
