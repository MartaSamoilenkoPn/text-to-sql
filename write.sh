#!/bin/bash

# Define the output file
OUTPUT="out.txt"

# Clear the output file if it already exists
> "$OUTPUT"

# Loop through all .py files in the current directory
for file in *.py *.yaml; do
    # Check if file exists to handle cases where no .py files are found
    if [[ -f "$file" ]]; then
        echo "Processing $file..."

        # Write formatting and filename to output
        echo "==========================================" >> "$OUTPUT"
        echo "FILE: $file" >> "$OUTPUT"
        echo "==========================================" >> "$OUTPUT"

        # Append file contents
        cat "$file" >> "$OUTPUT"

        # Add a few newlines for spacing
        echo -e "\n\n" >> "$OUTPUT"
    fi
done

echo "All files have been written to $OUTPUT"