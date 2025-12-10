echo "Downloading Spider database files..."
gdown 1403EGqzIDoHMdQF4c9Bkyl7dZLZ5Wt6J -O ./spider_data.zip

echo "Unzipping..."
unzip -q spider_data.zip -d ./benchmark/

echo "Fixing database schema issues..."
python3 ./benchmark/fix_table.py

echo "Deleting zip file..."
rm spider_data.zip
rm -rf ./benchmark/__MACOSX

echo "Setup complete."
