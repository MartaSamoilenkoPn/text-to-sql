echo "Downloading Spider database files..."
gdown 1403EGqzIDoHMdQF4c9Bkyl7dZLZ5Wt6J -O ./spider_templates.db

echo "Unzipping..."
unzip spider_templates.db -d ./benchmark/

echo "Deleting zip file..."
rm spider_templates.db
rm -rf ./benchmark/__MACOSX

echo "Setup complete."
